"""
pipeline_sih_agravo.py — Internações por agravo (CID-3) + visão hospitalar (CNES)
================================================================================

Reprocessa os RD do SIH 2024 numa única passada, capturando por internação:
  - município de RESIDÊNCIA (MUNIC_RES) + agravo traçador (DIAG_PRINC, CID-3)
  - estabelecimento (CNES) + município de ATENDIMENTO (MUNIC_MOV) + capítulo CID

Gera:
  - mart_internacoes_agravo   : (município, agravo) internações, óbitos, permanência, custo
  - mart_internacoes_hospital : (CNES) internações, óbitos, permanência, custo, capítulo principal

Agravos traçadores (mutuamente exclusivos por prefixo CID-3): diabetes, AVC, IAM,
insuficiência cardíaca, asma, DPOC, pneumonia, depressão, esquizofrenia/psicoses,
transtornos por álcool/drogas, acidentes de transporte, TCE.

Checkpoint por UF (resumível). Uso:
  .venv311/Scripts/python scripts/pipeline_sih_agravo.py --ano 2024 --workers 6
"""
from __future__ import annotations

import argparse
import io
import json
import os
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
CKPT = ROOT / "data" / "raw" / "SIH" / "agravo_ckpt"
FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SIHSUS/200801_/Dados"
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
       "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]

CID10_CAPITULOS = [
    ("I","A00","B99"),("II","C00","D48"),("III","D50","D89"),("IV","E00","E90"),
    ("V","F00","F99"),("VI","G00","G99"),("VII","H00","H59"),("VIII","H60","H95"),
    ("IX","I00","I99"),("X","J00","J99"),("XI","K00","K93"),("XII","L00","L99"),
    ("XIII","M00","M99"),("XIV","N00","N99"),("XV","O00","O99"),("XVI","P00","P96"),
    ("XVII","Q00","Q99"),("XVIII","R00","R99"),("XIX","S00","T98"),("XX","V01","Y98"),
    ("XXI","Z00","Z99"),("XXII","U00","U99"),
]

# Agravos traçadores → conjuntos de CID-10 (3 caracteres)
AGRAVOS: dict[str, set[str]] = {
    "diabetes": {"E10","E11","E12","E13","E14"},
    "avc": {"I60","I61","I62","I63","I64","I65","I66","I67","I68","I69"},
    "iam": {"I21","I22"},
    "icc": {"I50"},
    "asma": {"J45","J46"},
    "dpoc": {"J40","J41","J42","J43","J44"},
    "pneumonia": {"J12","J13","J14","J15","J16","J17","J18"},
    "depressao": {"F32","F33"},
    "esquizofrenia": {"F20","F21","F22","F23","F24","F25","F28","F29"},
    "alcool_drogas": {"F10","F11","F12","F13","F14","F15","F16","F17","F18","F19"},
    # NB: acidente de transporte (V01–V99) NÃO entra: na AIH o DIAG_PRINC registra a
    # natureza da lesão (S/T), não o mecanismo (V) — buscar V-codes aqui dá ~zero.
    # Causas externas ficam representadas pelo TCE.
    "tce": {"S02","S06","S07"},
}

AGRAVO_LABEL = {
    "diabetes": "Diabetes mellitus",
    "avc": "AVC (doença cerebrovascular)",
    "iam": "Infarto agudo do miocárdio",
    "icc": "Insuficiência cardíaca",
    "asma": "Asma",
    "dpoc": "DPOC",
    "pneumonia": "Pneumonia",
    "depressao": "Depressão",
    "esquizofrenia": "Esquizofrenia e outras psicoses",
    "alcool_drogas": "Transtornos por álcool e drogas",
    "acidente_transito": "Acidentes de transporte",
    "tce": "Traumatismo cranioencefálico",
}

AGRAVO_GRUPO = {
    "diabetes": "Crônicas", "avc": "Cardiovasculares", "iam": "Cardiovasculares",
    "icc": "Cardiovasculares", "asma": "Respiratórias", "dpoc": "Respiratórias",
    "pneumonia": "Respiratórias", "depressao": "Saúde mental",
    "esquizofrenia": "Saúde mental", "alcool_drogas": "Saúde mental",
    "acidente_transito": "Causas externas", "tce": "Causas externas",
}

# Mapa reverso CID-3 → chave de agravo (prefixos não se sobrepõem)
CID2AGRAVO: dict[str, str] = {}
for _k, _cids in AGRAVOS.items():
    for _c in _cids:
        CID2AGRAVO[_c] = _k


def _capitulo(cid3: str) -> str:
    for cap, ini, fim in CID10_CAPITULOS:
        if ini <= cid3 <= fim:
            return cap
    return "N/D"


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
    """Um RD mensal → (agravo dict, hospital dict). None se ausente."""
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
    agravo: dict = defaultdict(lambda: [0, 0, 0, 0.0])   # (mun_res, agravo) -> [n, obitos, dias, valor]
    hosp: dict = defaultdict(lambda: [0, 0, 0, 0.0])     # (cnes, mun_mov, cap) -> [n, obitos, dias, valor]
    try:
        datasus_dbc.decompress(str(dbc), str(dbf))
        for rec in dbfread.DBF(str(dbf), encoding="latin-1", char_decode_errors="replace", load=False):
            cid = (str(rec.get("DIAG_PRINC") or "")).strip().upper()[:3]
            if not cid:
                continue
            try:
                dias = int(rec.get("DIAS_PERM") or 0)
            except (ValueError, TypeError):
                dias = 0
            try:
                val = float(rec.get("VAL_TOT") or 0)
            except (ValueError, TypeError):
                val = 0.0
            morte = 1 if str(rec.get("MORTE") or "0").strip() == "1" else 0

            # --- agravo (por residência) ---
            ag = CID2AGRAVO.get(cid)
            if ag:
                res = (str(rec.get("MUNIC_RES") or "")).strip()[:6]
                if len(res) == 6:
                    c = agravo[(res, ag)]
                    c[0] += 1; c[1] += morte; c[2] += dias; c[3] += val

            # --- hospital (por CNES / atendimento) ---
            cnes = (str(rec.get("CNES") or "")).strip()
            if cnes and cnes not in ("", "0000000"):
                mov = (str(rec.get("MUNIC_MOV") or "")).strip()[:6]
                cap = _capitulo(cid)
                h = hosp[(cnes, mov, cap)]
                h[0] += 1; h[1] += morte; h[2] += dias; h[3] += val
        return dict(agravo), dict(hosp)
    except Exception:
        return None
    finally:
        dbc.unlink(missing_ok=True); dbf.unlink(missing_ok=True)


def _process_uf(uf: str, ano: int, workers: int):
    CKPT.mkdir(parents=True, exist_ok=True)
    ack = CKPT / f"agravo_{uf}_{ano}.parquet"
    hck = CKPT / f"hosp_{uf}_{ano}.parquet"
    if ack.exists() and hck.exists():
        return pd.read_parquet(ack), pd.read_parquet(hck)
    agravo: dict = defaultdict(lambda: [0, 0, 0, 0.0])
    hosp: dict = defaultdict(lambda: [0, 0, 0, 0.0])
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_process_file, uf, ano, m): m for m in range(1, 13)}
        for fut in as_completed(futs):
            res = fut.result()
            if not res:
                continue
            ag, hs = res
            for k, v in ag.items():
                t = agravo[k]; t[0] += v[0]; t[1] += v[1]; t[2] += v[2]; t[3] += v[3]
            for k, v in hs.items():
                t = hosp[k]; t[0] += v[0]; t[1] += v[1]; t[2] += v[2]; t[3] += v[3]
    adf = pd.DataFrame([(r, ag, c[0], c[1], c[2], round(c[3], 2)) for (r, ag), c in agravo.items()],
                       columns=["municipio_cod", "agravo", "internacoes", "obitos", "dias_permanencia", "valor_total"])
    hdf = pd.DataFrame([(cn, mv, cap, c[0], c[1], c[2], round(c[3], 2)) for (cn, mv, cap), c in hosp.items()],
                       columns=["cnes", "municipio_cod", "capitulo_cid", "internacoes", "obitos", "dias_permanencia", "valor_total"])
    adf.to_parquet(ack, compression="zstd", index=False)
    hdf.to_parquet(hck, compression="zstd", index=False)
    print(f"[agravo] {uf} {ano}: {int(adf['internacoes'].sum()):,} intern. em agravos | {hdf['cnes'].nunique():,} hospitais", flush=True)
    return adf, hdf


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", type=int, default=2024)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    ano = args.ano
    env = load_env()

    aparts, hparts = [], []
    for uf in UFS:
        a, h = _process_uf(uf, ano, args.workers)
        aparts.append(a); hparts.append(h)

    municipios = pd.read_parquet(REFS / "municipios.parquet")
    pop = pd.read_parquet(next(REFS.glob("populacao_*.parquet")))
    pop = pop[pop.ano == ano][["municipio_cod", "populacao"]]
    mref = municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]

    # --- agravo (por município de residência) ---
    agravo = pd.concat(aparts, ignore_index=True).groupby(
        ["municipio_cod", "agravo"], as_index=False)[
        ["internacoes", "obitos", "dias_permanencia", "valor_total"]].sum()
    agravo["ano"] = ano
    agravo["agravo_label"] = agravo["agravo"].map(AGRAVO_LABEL)
    agravo["grupo"] = agravo["agravo"].map(AGRAVO_GRUPO)
    agravo = agravo.merge(mref, on="municipio_cod", how="left").merge(pop, on="municipio_cod", how="left")
    agravo["uf_sigla"] = agravo["uf_sigla"].fillna("ND")
    agravo["permanencia_media"] = (agravo.dias_permanencia / agravo.internacoes).round(1)
    agravo["mortalidade_pct"] = (agravo.obitos / agravo.internacoes * 100).round(2)
    agravo["custo_medio"] = (agravo.valor_total / agravo.internacoes).round(2)
    agravo["internacoes_100k"] = (agravo.internacoes / agravo.populacao * 100000).round(1)
    agravo["populacao"] = agravo["populacao"].astype("Int64")
    agravo = agravo[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano",
                     "agravo", "agravo_label", "grupo", "internacoes", "obitos",
                     "dias_permanencia", "valor_total", "permanencia_media",
                     "mortalidade_pct", "custo_medio", "populacao", "internacoes_100k"]]

    # --- hospital (por CNES) ---
    hraw = pd.concat(hparts, ignore_index=True).groupby(
        ["cnes", "municipio_cod", "capitulo_cid"], as_index=False)[
        ["internacoes", "obitos", "dias_permanencia", "valor_total"]].sum()
    # totais por hospital
    htot = hraw.groupby(["cnes", "municipio_cod"], as_index=False)[
        ["internacoes", "obitos", "dias_permanencia", "valor_total"]].sum()
    # capítulo principal (argmax de internações por hospital)
    cap_principal = (hraw.sort_values("internacoes", ascending=False)
                     .drop_duplicates("cnes")[["cnes", "capitulo_cid"]]
                     .rename(columns={"capitulo_cid": "capitulo_principal"}))
    hosp = htot.merge(cap_principal, on="cnes", how="left")
    hosp = hosp[hosp.internacoes >= 12].copy()  # filtra ruído (<1 internação/mês)
    hosp["ano"] = ano
    hosp = hosp.merge(mref, on="municipio_cod", how="left")
    hosp["uf_sigla"] = hosp["uf_sigla"].fillna("ND")
    hosp["permanencia_media"] = (hosp.dias_permanencia / hosp.internacoes).round(1)
    hosp["mortalidade_pct"] = (hosp.obitos / hosp.internacoes * 100).round(2)
    hosp["custo_medio"] = (hosp.valor_total / hosp.internacoes).round(2)
    hosp = hosp[["cnes", "municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano",
                 "capitulo_principal", "internacoes", "obitos", "dias_permanencia",
                 "valor_total", "permanencia_media", "mortalidade_pct", "custo_medio"]]

    MARTS.mkdir(exist_ok=True)
    agravo.to_parquet(MARTS / "mart_internacoes_agravo.parquet", compression="zstd", index=False)
    hosp.to_parquet(MARTS / "mart_internacoes_hospital.parquet", compression="zstd", index=False)
    print(f"[agravo] mart_agravo: {len(agravo):,} | mart_hospital: {len(hosp):,} hospitais", flush=True)

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
        print(f"[supabase]   {table}: {len(recs):,} OK", flush=True)

    up("mart_internacoes_agravo", agravo)
    up("mart_internacoes_hospital", hosp)
    print("[done] agravo + hospital concluído.", flush=True)


if __name__ == "__main__":
    main()
