"""
pipeline_sih.py — SIH/AIH (internações SUS) → mart agregado (streaming)
=======================================================================

Arquivos RD{UF}{AAMM}.dbc são mensais por UF (~17 MB cada). Para cobrir N anos
são 27×12×N arquivos. Estratégia: baixar → descomprimir → agregar em streaming
→ descartar o bruto, mantendo apenas contadores por (município, ano, capítulo CID).
Disco e memória permanecem baixos; o custo é tempo/banda.

Fonte: SIH/DataSUS, /dissemin/publicos/SIHSUS/200801_/Dados/RD{UF}{AAMM}.dbc

Mart:
  mart_internacoes_municipio — município × ano × capítulo CID-10 (e TOTAL):
    internações, óbitos (MORTE=1), dias de permanência, valor aprovado (R$),
    permanência média, mortalidade intra-hospitalar, custo médio, internações/100k.

Convenções:
  - Município = residência do paciente (MUNIC_RES).
  - Capítulo CID-10 pelo diagnóstico principal (DIAG_PRINC).
  - Valores = VAL_TOT (valor total aprovado da AIH).

Uso:
  .venv311/Scripts/python scripts/pipeline_sih.py --anos 2023 2024 --workers 8
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
from datetime import date, datetime
from ftplib import FTP
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS_DIR = ROOT / "data" / "marts"

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


def _process_file(uf: str, ano: int, mes: int) -> dict | None:
    """Baixa e agrega um RD mensal. Retorna dict[(mun6, cap)] = [n, obitos, dias, valor].
    None em erro/ausência (meses futuros)."""
    import datasus_dbc
    import dbfread

    yymm = f"{ano % 100:02d}{mes:02d}"
    nome = f"RD{uf}{yymm}"
    try:
        ftp = FTP(FTP_HOST, timeout=180)
        ftp.login()
        try:
            ftp.size(f"{FTP_DIR}/{nome}.dbc")
        except Exception:
            ftp.quit()
            return None  # mês inexistente
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {FTP_DIR}/{nome}.dbc", buf.write)
        ftp.quit()
    except Exception:
        return None

    tmp = Path(tempfile.gettempdir())
    dbc = tmp / f"{nome}.dbc"
    dbf = tmp / f"{nome}.dbf"
    dbc.write_bytes(buf.getvalue())
    try:
        datasus_dbc.decompress(str(dbc), str(dbf))
        agg: dict = defaultdict(lambda: [0, 0, 0, 0.0])
        for rec in dbfread.DBF(str(dbf), encoding="latin-1", char_decode_errors="replace", load=False):
            mun = (str(rec.get("MUNIC_RES") or "")).strip()[:6]
            if len(mun) < 6:
                continue
            cid = (str(rec.get("DIAG_PRINC") or "")).strip().upper()[:3]
            cap = _capitulo(cid) if cid else "N/D"
            try:
                dias = int(rec.get("DIAS_PERM") or 0)
            except (ValueError, TypeError):
                dias = 0
            try:
                val = float(rec.get("VAL_TOT") or 0)
            except (ValueError, TypeError):
                val = 0.0
            morte = 1 if str(rec.get("MORTE") or "0").strip() in ("1",) else 0
            c = agg[(mun, cap)]
            c[0] += 1; c[1] += morte; c[2] += dias; c[3] += val
        return dict(agg)
    finally:
        dbc.unlink(missing_ok=True)
        dbf.unlink(missing_ok=True)


def build(anos: list[int], workers: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    tarefas = [(uf, a, m) for a in anos for uf in UFS for m in range(1, 13)]
    total: dict = defaultdict(lambda: [0, 0, 0, 0.0])  # (mun, ano, cap) -> [...]
    ok = err = 0
    print(f"[sih] {len(tarefas)} arquivos (UF×mês×ano), {workers} workers", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_process_file, uf, a, m): (uf, a, m) for uf, a, m in tarefas}
        for fut in as_completed(futs):
            uf, a, m = futs[fut]
            res = fut.result()
            if res is None:
                err += 1
            else:
                ok += 1
                for (mun, cap), c in res.items():
                    t = total[(mun, a, cap)]
                    t[0] += c[0]; t[1] += c[1]; t[2] += c[2]; t[3] += c[3]
            if (ok + err) % 50 == 0:
                print(f"[sih]   {ok+err}/{len(tarefas)} (ok={ok}, vazios={err})", flush=True)

    rows = [(mun, a, cap, c[0], c[1], c[2], round(c[3], 2))
            for (mun, a, cap), c in total.items()]
    det = pd.DataFrame(rows, columns=[
        "municipio_cod", "ano", "capitulo_cid", "internacoes", "obitos", "dias_permanencia", "valor_total"])

    # linha TOTAL (todos os capítulos) por município/ano
    tot = (det.groupby(["municipio_cod", "ano"], as_index=False)[
        ["internacoes", "obitos", "dias_permanencia", "valor_total"]].sum())
    tot["capitulo_cid"] = "TOTAL"
    mart = pd.concat([det, tot], ignore_index=True)

    # enriquecimento
    municipios = pd.read_parquet(REFS / "municipios.parquet")
    pop = pd.read_parquet(next(REFS.glob("populacao_*.parquet")))[["municipio_cod", "ano", "populacao"]]
    mart = mart.merge(municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]],
                      on="municipio_cod", how="left")
    mart["uf_sigla"] = mart["uf_sigla"].fillna("ND")
    mart = mart.merge(pop, on=["municipio_cod", "ano"], how="left")

    mart["permanencia_media"] = (mart["dias_permanencia"] / mart["internacoes"]).round(2)
    mart["mortalidade_pct"] = (mart["obitos"] / mart["internacoes"] * 100).round(2)
    mart["custo_medio"] = (mart["valor_total"] / mart["internacoes"]).round(2)
    mart["internacoes_100k"] = None
    m_tot = mart["capitulo_cid"] == "TOTAL"
    mart.loc[m_tot, "internacoes_100k"] = (
        mart.loc[m_tot, "internacoes"] / mart.loc[m_tot, "populacao"] * 100_000
    ).round(1)
    mart.loc[mart["capitulo_cid"] != "TOTAL", "populacao"] = None
    mart["populacao"] = mart["populacao"].where(m_tot)

    mart = mart.sort_values(["municipio_cod", "ano", "capitulo_cid"]).reset_index(drop=True)
    print(f"[sih] mart_internacoes: {len(mart):,} linhas")
    print(f"[sih] internações {min(anos)}–{max(anos)}: {int(det['internacoes'].sum()):,} | "
          f"valor total R$ {det['valor_total'].sum()/1e9:.1f} bi")
    return mart, municipios


class SupabaseLoader:
    def __init__(self, url: str, key: str, batch: int = 8_000):
        self.url = url.rstrip("/")
        self.h = {"apikey": key, "Authorization": f"Bearer {key}",
                  "Content-Type": "application/json",
                  "Prefer": "return=minimal,resolution=merge-duplicates"}
        self.batch = batch

    def load_df(self, table: str, df: pd.DataFrame) -> None:
        df = df.copy()
        recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
        nb = math.ceil(len(recs) / self.batch)
        for i in range(nb):
            body = json.dumps(recs[i*self.batch:(i+1)*self.batch], default=_jd, allow_nan=False)
            for a in range(4):
                r = requests.post(f"{self.url}/rest/v1/{table}", headers=self.h, data=body, timeout=300)
                if r.status_code in (200, 201):
                    break
                if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                    raise RuntimeError(f"{table} lote {i+1}/{nb}: HTTP {r.status_code} {r.text[:200]}")
                time.sleep(3 * (a + 1))
            print(f"[supabase]   {table}: {min((i+1)*self.batch, len(recs)):,}/{len(recs):,}", end="\r", flush=True)
        print(f"[supabase]   {table}: {len(recs):,} OK            ")


def _jd(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(str(type(o)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="+", type=int, default=[2022, 2023, 2024])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    anos = sorted(args.anos)
    env = load_env()

    mart, _ = build(anos, args.workers)

    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    mart.to_parquet(MARTS_DIR / "mart_internacoes_municipio.parquet", compression="zstd", index=False)

    if args.no_upload:
        return

    url, key = env.get("SUPABASE_URL"), env.get("SUPABASE_ANON_KEY")
    if not url or not key:
        sys.exit("Defina SUPABASE_URL e SUPABASE_ANON_KEY no .env")
    loader = SupabaseLoader(url, key)
    loader.load_df("mart_internacoes_municipio", mart)

    meta = pd.DataFrame([
        ("fonte_sih", "SIH/DataSUS — AIH (RD), FTP SIHSUS/200801_"),
        ("sih_cobertura", f"{min(anos)}–{max(anos)}"),
        ("sih_definicoes", "Internações por residência (MUNIC_RES) e capítulo CID-10 do diagnóstico principal; valor=VAL_TOT aprovado; mortalidade intra-hospitalar=MORTE/internações"),
        ("gerado_em", datetime.now().isoformat(timespec="seconds")),
    ], columns=["chave", "valor"])
    loader.load_df("meta_dataset", meta)
    print("[done] pipeline SIH concluído.")


if __name__ == "__main__":
    main()
