"""
pipeline_sih_fluxo.py — Fluxo intermunicipal de pacientes + ICSAP (SIH)
=======================================================================

Reprocessa os arquivos RD do SIH capturando, por internação:
  - município de RESIDÊNCIA (MUNIC_RES) e de ATENDIMENTO (MUNIC_MOV) → fluxo
  - diagnóstico principal (DIAG_PRINC, 3 caracteres) → flag ICSAP

Gera:
  - mart_fluxo_intermunicipal : (ano, mun_res, mun_mov) internações [fluxos ≥5, intermunicipais]
  - mart_icsap_municipio      : (mun_res, ano) total, ICSAP, %ICSAP, ICSAP/100k

ICSAP = Internações por Condições Sensíveis à Atenção Primária (aproximação da
Lista Brasileira / Portaria SAS-MS 221/2008, no nível de CID-10 de 3 caracteres).

Crédito: a ideia de fluxo intermunicipal de pacientes segue o LabSUS (UFT).
Checkpoint por UF (resumível). Uso:
  .venv311/Scripts/python scripts/pipeline_sih_fluxo.py --ano 2024 --workers 6
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from ftplib import FTP
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "SIH" / "fluxo_ckpt"
FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SIHSUS/200801_/Dados"
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
       "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]

# Lista Brasileira de ICSAP (aproximação por CID-10 de 3 caracteres)
ICSAP3 = {
    # 1 imunizáveis e preveníveis
    "A33","A34","A35","A36","A37","B05","B06","B16","B26","A95","B77","G00","A17","A19",
    # 2 gastroenterites e desidratação
    "A00","A01","A02","A03","A04","A05","A06","A07","A08","A09","E86",
    # 3 anemia
    "D50",
    # 4 deficiências nutricionais
    "E40","E41","E42","E43","E44","E45","E46","E50","E51","E52","E53","E54","E55","E56","E58","E59","E60","E61","E63","E64",
    # 5 otite/ivas
    "H66","J00","J01","J02","J03","J06","J31",
    # 6 pneumonias bacterianas
    "J13","J14","J15","J18",
    # 7 asma
    "J45","J46",
    # 8 DPOC e bronquites
    "J20","J21","J40","J41","J42","J43","J44","J47",
    # 9 hipertensão
    "I10","I11",
    # 10 angina
    "I20",
    # 11 insuficiência cardíaca
    "I50","J81",
    # 12 cerebrovasculares
    "I63","I64","I65","I66","I67","I69","G45","G46",
    # 13 diabetes
    "E10","E11","E12","E13","E14",
    # 14 epilepsias
    "G40","G41",
    # 15 infecção rim/trato urinário
    "N10","N11","N12","N30","N34","N39",
    # 16 infecção pele/subcutâneo
    "A46","L01","L02","L03","L04","L08",
    # 17 DIP feminina
    "N70","N71","N72","N73","N75","N76",
    # 18 úlcera gastrointestinal
    "K25","K26","K27","K28","K92",
    # 19 pré-natal e parto
    "O23","A50","P35",
}


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})
    return env


def _process_file(uf: str, ano: int, mes: int):
    """Um RD mensal → (fluxo dict, icsap dict). None se ausente."""
    import datasus_dbc
    import dbfread
    yymm = f"{ano % 100:02d}{mes:02d}"
    nome = f"RD{uf}{yymm}"
    try:
        ftp = FTP(FTP_HOST, timeout=180); ftp.login()
        try:
            ftp.size(f"{FTP_DIR}/{nome}.dbc")
        except Exception:
            ftp.quit(); return None
        buf = io.BytesIO(); ftp.retrbinary(f"RETR {FTP_DIR}/{nome}.dbc", buf.write); ftp.quit()
    except Exception:
        return None
    tmp = Path(tempfile.gettempdir())
    dbc = tmp / f"{nome}.dbc"; dbf = tmp / f"{nome}.dbf"
    dbc.write_bytes(buf.getvalue())
    fluxo: dict = defaultdict(int)
    icsap: dict = defaultdict(lambda: [0, 0])  # mun_res -> [total, icsap]
    try:
        datasus_dbc.decompress(str(dbc), str(dbf))
        for rec in dbfread.DBF(str(dbf), encoding="latin-1", char_decode_errors="replace", load=False):
            res = (str(rec.get("MUNIC_RES") or "")).strip()[:6]
            mov = (str(rec.get("MUNIC_MOV") or "")).strip()[:6]
            if len(res) < 6:
                continue
            cid = (str(rec.get("DIAG_PRINC") or "")).strip().upper()[:3]
            c = icsap[res]; c[0] += 1
            if cid in ICSAP3:
                c[1] += 1
            if len(mov) == 6 and mov != res:
                fluxo[(res, mov)] += 1
        return dict(fluxo), dict(icsap)
    except Exception:
        return None
    finally:
        dbc.unlink(missing_ok=True); dbf.unlink(missing_ok=True)


def _process_uf(uf: str, ano: int, workers: int):
    CKPT.mkdir(parents=True, exist_ok=True)
    fck = CKPT / f"fluxo_{uf}_{ano}.parquet"
    ick = CKPT / f"icsap_{uf}_{ano}.parquet"
    if fck.exists() and ick.exists():
        return pd.read_parquet(fck), pd.read_parquet(ick)
    fluxo: dict = defaultdict(int)
    icsap: dict = defaultdict(lambda: [0, 0])
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_process_file, uf, ano, m): m for m in range(1, 13)}
        for fut in as_completed(futs):
            res = fut.result()
            if not res:
                continue
            fl, ic = res
            for k, v in fl.items():
                fluxo[k] += v
            for mun, c in ic.items():
                t = icsap[mun]; t[0] += c[0]; t[1] += c[1]
    fdf = pd.DataFrame([(ano, r, m, n) for (r, m), n in fluxo.items()],
                       columns=["ano", "municipio_res", "municipio_mov", "internacoes"])
    idf = pd.DataFrame([(mun, ano, c[0], c[1]) for mun, c in icsap.items()],
                       columns=["municipio_cod", "ano", "internacoes_total", "internacoes_icsap"])
    fdf.to_parquet(fck, compression="zstd", index=False)
    idf.to_parquet(ick, compression="zstd", index=False)
    print(f"[fluxo] {uf} {ano}: {len(fdf):,} pares de fluxo, {int(idf['internacoes_total'].sum()):,} internações", flush=True)
    return fdf, idf


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", type=int, default=2024)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    ano = args.ano
    env = load_env()

    fparts, iparts = [], []
    for uf in UFS:
        f, i = _process_uf(uf, ano, args.workers)
        fparts.append(f); iparts.append(i)

    municipios = pd.read_parquet(REFS / "municipios.parquet")
    pop = pd.read_parquet(next(REFS.glob("populacao_*.parquet")))
    pop = pop[pop.ano == ano][["municipio_cod", "populacao"]]
    mref = municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]

    # --- fluxo ---
    fluxo = pd.concat(fparts, ignore_index=True).groupby(
        ["ano", "municipio_res", "municipio_mov"], as_index=False)["internacoes"].sum()
    fluxo = fluxo[fluxo.internacoes >= 5].copy()
    fluxo = fluxo.merge(mref.rename(columns={"municipio_cod": "municipio_res",
            "municipio_nome": "municipio_res_nome", "uf_sigla": "uf_res"})[
            ["municipio_res", "municipio_res_nome", "uf_res"]], on="municipio_res", how="left")
    fluxo = fluxo.merge(mref.rename(columns={"municipio_cod": "municipio_mov",
            "municipio_nome": "municipio_mov_nome", "uf_sigla": "uf_mov"})[
            ["municipio_mov", "municipio_mov_nome", "uf_mov"]], on="municipio_mov", how="left")
    fluxo = fluxo[["ano", "municipio_res", "municipio_res_nome", "uf_res",
                   "municipio_mov", "municipio_mov_nome", "uf_mov", "internacoes"]]

    # --- ICSAP ---
    icsap = pd.concat(iparts, ignore_index=True).groupby(
        ["municipio_cod", "ano"], as_index=False)[["internacoes_total", "internacoes_icsap"]].sum()
    icsap = icsap.merge(mref, on="municipio_cod", how="left").merge(pop, on="municipio_cod", how="left")
    icsap["uf_sigla"] = icsap["uf_sigla"].fillna("ND")
    icsap["pct_icsap"] = (icsap.internacoes_icsap / icsap.internacoes_total * 100).round(2)
    icsap["icsap_100k"] = (icsap.internacoes_icsap / icsap.populacao * 100000).round(1)
    icsap["populacao"] = icsap["populacao"].astype("Int64")
    icsap = icsap[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano",
                   "internacoes_total", "internacoes_icsap", "pct_icsap", "populacao", "icsap_100k"]]

    MARTS.mkdir(exist_ok=True)
    fluxo.to_parquet(MARTS / "mart_fluxo_intermunicipal.parquet", compression="zstd", index=False)
    icsap.to_parquet(MARTS / "mart_icsap_municipio.parquet", compression="zstd", index=False)
    print(f"[fluxo] mart_fluxo: {len(fluxo):,} | mart_icsap: {len(icsap):,} | "
          f"ICSAP médio {icsap.pct_icsap.mean():.1f}%")

    if args.no_upload:
        return
    url, key = env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}

    def up(table, df):
        recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
        for i in range(0, len(recs), 8000):
            body = json.dumps(recs[i:i+8000], default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
            for a in range(4):
                r = requests.post(f"{url.rstrip('/')}/rest/v1/{table}", headers=h, data=body, timeout=300)
                if r.status_code in (200, 201):
                    break
                if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                    raise RuntimeError(f"{table}: HTTP {r.status_code} {r.text[:200]}")
                time.sleep(3 * (a + 1))
        print(f"[supabase]   {table}: {len(recs):,} OK")

    up("mart_fluxo_intermunicipal", fluxo)
    up("mart_icsap_municipio", icsap)
    meta = [{"chave": "fonte_fluxo_icsap", "valor": f"SIH/SUS {ano}: fluxo intermunicipal (MUNIC_RES→MUNIC_MOV, ≥5 internações) e ICSAP (aproximação Lista Brasileira, CID-10 3 caracteres). Ideia de fluxo inspirada no LabSUS (UFT)."},
            {"chave": "gerado_em", "valor": datetime.now().isoformat(timespec="seconds")}]
    requests.post(f"{url.rstrip('/')}/rest/v1/meta_dataset", headers=h, data=json.dumps(meta), timeout=60)
    print("[done] fluxo + ICSAP concluído.")


if __name__ == "__main__":
    main()
