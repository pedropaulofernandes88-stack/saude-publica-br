"""
pipeline_sinan.py — SINAN/dengue → marts agregados (streaming)
===============================================================

Os arquivos nacionais DENGBR{AA}.dbc são GIGANTES (2024 ≈ 6 milhões de casos,
1,7 GB descomprimido). Por isso a agregação é feita em *streaming*: itera o DBF
registro a registro, sem carregar em memória, acumulando contadores por
(município, semana epidemiológica).

Fonte: SINAN/DataSUS, /dissemin/publicos/SINAN/DADOS/{FINAIS,PRELIM}/DENGBR{AA}.dbc
Denominador populacional: dim_populacao (IBGE), já carregado pela base.

Saídas:
  - mart_dengue_semana          : município × ano × semana (casos, graves, óbitos)
  - mart_dengue_municipio_ano   : município × ano (+ incidência/100k e letalidade)

Convenções (documentadas em saudeemdado.com/metodologia):
  - Caso provável = notificação NÃO descartada (CLASSI_FIN != '5').
  - Grave = CLASSI_FIN em {11 (alarme), 12 (grave)} ou legado {3 (FHD), 4 (SCD)}.
  - Óbito = EVOLUCAO == '2' (óbito pelo agravo).
  - Município e semana pela RESIDÊNCIA e DATA DOS PRIMEIROS SINTOMAS (SEM_PRI).

Uso:
  .venv311/Scripts/python scripts/pipeline_sinan.py --anos 2015 2016 ... 2024
  .venv311/Scripts/python scripts/pipeline_sinan.py --no-upload
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
from datetime import date, datetime
from ftplib import FTP
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "SINAN"
REFS = ROOT / "data" / "refs"
MARTS_DIR = ROOT / "data" / "marts"

FTP_HOST = "ftp.datasus.gov.br"
FTP_FINAIS = "/dissemin/publicos/SINAN/DADOS/FINAIS"
FTP_PRELIM = "/dissemin/publicos/SINAN/DADOS/PRELIM"

GRAVE = {"11", "12", "3", "4"}
DESCARTADO = "5"


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


def _download_dbc(ano: int) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    yy = f"{ano % 100:02d}"
    dest = RAW / f"DENGBR{yy}.dbc"
    if dest.exists() and dest.stat().st_size > 100_000:
        return dest
    ftp = FTP(FTP_HOST, timeout=180)
    ftp.login()
    buf = io.BytesIO()
    base = FTP_FINAIS
    try:
        ftp.size(f"{base}/DENGBR{yy}.dbc")
    except Exception:
        base = FTP_PRELIM
    print(f"[download] DENGBR{yy}.dbc ({base.split('/')[-1]})...", flush=True)
    ftp.retrbinary(f"RETR {base}/DENGBR{yy}.dbc", buf.write)
    ftp.quit()
    dest.write_bytes(buf.getvalue())
    print(f"[download]   {dest.stat().st_size // 1_000_000} MB", flush=True)
    return dest


CKPT = ROOT / "data" / "raw" / "SINAN" / "ckpt"


def _aggregate_year(ano: int) -> pd.DataFrame:
    """Stream do DBF de um ano → DataFrame agregado (mun, ano_epi, semana).
    Resiliente: salva checkpoint parquet por ano; re-runs pulam anos prontos."""
    CKPT.mkdir(parents=True, exist_ok=True)
    ckpt = CKPT / f"dengue_{ano}.parquet"
    if ckpt.exists():
        print(f"[dengue {ano}] checkpoint encontrado, pulando", flush=True)
        return pd.read_parquet(ckpt)

    import subprocess
    import dbfread

    dbc = _download_dbc(ano)
    dbf = Path(tempfile.gettempdir()) / f"DENG{ano}.dbf"
    # SEMPRE descomprime do zero (um .dbf truncado de um run morto produz contagem errada).
    # Descompressão em subprocesso isola eventual segfault do datasus_dbc.
    dbf.unlink(missing_ok=True)
    ok = False
    for tent in range(3):
        r = subprocess.run(
            [sys.executable, "-c",
             f"import datasus_dbc; datasus_dbc.decompress(r'{dbc}', r'{dbf}')"],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and dbf.exists() and dbf.stat().st_size > 10_000:
            ok = True
            break
        print(f"[dengue {ano}] decompress falhou (tent {tent+1}, rc={r.returncode}) {r.stderr[:150]}", flush=True)
        dbf.unlink(missing_ok=True)
    if not ok:
        raise RuntimeError(f"não foi possível descomprimir DENGBR{ano % 100:02d}.dbc")

    counts: dict = defaultdict(lambda: [0, 0, 0])
    n = 0
    for rec in dbfread.DBF(str(dbf), encoding="latin-1", char_decode_errors="replace", load=False):
        n += 1
        mun = (rec.get("ID_MN_RESI") or rec.get("ID_MUNICIP") or "").strip()
        if len(mun) < 6:
            continue
        mun = mun[:6]
        sem_pri = (rec.get("SEM_PRI") or "").strip()        # 'AAAASS'
        if len(sem_pri) == 6 and sem_pri.isdigit():
            ano_epi = int(sem_pri[:4])
            semana = int(sem_pri[4:])
        else:
            ano_epi, semana = ano, 0
        if semana < 1 or semana > 53:
            semana = 0
        classi = (str(rec.get("CLASSI_FIN") or "")).strip()
        evol = (str(rec.get("EVOLUCAO") or "")).strip()
        if classi == DESCARTADO:
            continue
        c = counts[(mun, ano_epi, semana)]
        c[0] += 1
        if classi in GRAVE:
            c[1] += 1
        if evol == "2":
            c[2] += 1
        if n % 500_000 == 0:
            print(f"[dengue {ano}]   {n:,} registros...", flush=True)

    dbf.unlink(missing_ok=True)
    df = pd.DataFrame(
        [(m, ae, s, c[0], c[1], c[2]) for (m, ae, s), c in counts.items()],
        columns=["municipio_cod", "ano_epi", "semana_epi", "casos_provaveis", "casos_graves", "obitos"],
    )
    df.to_parquet(ckpt, compression="zstd", index=False)
    print(f"[dengue {ano}] {n:,} registros processados → checkpoint", flush=True)
    return df


def build(anos: list[int]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    partes = [_aggregate_year(ano) for ano in anos]
    semana = pd.concat(partes, ignore_index=True)
    # consolida (um ano pode aparecer em checkpoints vizinhos via SEM_PRI)
    semana = (semana.groupby(["municipio_cod", "ano_epi", "semana_epi"], as_index=False)
              [["casos_provaveis", "casos_graves", "obitos"]].sum())

    # dimensões
    municipios = pd.read_parquet(REFS / "municipios.parquet")
    pop = pd.read_parquet(next(REFS.glob("populacao_*.parquet")))

    semana = semana.merge(
        municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]],
        on="municipio_cod", how="left",
    )
    semana["uf_sigla"] = semana["uf_sigla"].fillna("ND")
    # filtra anos de interesse (SEM_PRI pode escapar 1 ano)
    semana = semana[semana["ano_epi"].isin(anos)].copy()

    # anual
    anual = (
        semana.groupby(["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano_epi"],
                       dropna=False, as_index=False)[["casos_provaveis", "casos_graves", "obitos"]]
        .sum()
    )
    pop_y = pop.rename(columns={"ano": "ano_epi"})[["municipio_cod", "ano_epi", "populacao"]]
    anual = anual.merge(pop_y, on=["municipio_cod", "ano_epi"], how="left")
    anual["populacao"] = anual["populacao"].astype("Int64")  # nullable int (evita 25578.0)
    anual["incidencia_100k"] = (
        anual["casos_provaveis"] / anual["populacao"] * 100_000
    ).round(1).where(anual["populacao"] > 0)
    anual["letalidade_pct"] = (
        anual["obitos"] / anual["casos_provaveis"] * 100
    ).round(2).where(anual["casos_provaveis"] > 0)

    # ordena semana para chave determinística
    semana = semana.sort_values(["municipio_cod", "ano_epi", "semana_epi"]).reset_index(drop=True)

    print(f"[dengue] semana: {len(semana):,} linhas | anual: {len(anual):,} linhas")
    print(f"[dengue] total casos prováveis {min(anos)}–{max(anos)}: {int(semana['casos_provaveis'].sum()):,}")
    return semana, anual, municipios


class SupabaseLoader:
    def __init__(self, url: str, key: str, batch: int = 8_000):
        self.url = url.rstrip("/")
        self.h = {"apikey": key, "Authorization": f"Bearer {key}",
                  "Content-Type": "application/json",
                  "Prefer": "return=minimal,resolution=merge-duplicates"}
        self.batch = batch

    def load_df(self, table: str, df: pd.DataFrame) -> None:
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
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
    ap.add_argument("--anos", nargs="+", type=int, default=list(range(2015, 2025)))
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    anos = sorted(args.anos)
    env = load_env()

    semana, anual, _ = build(anos)

    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    semana.to_parquet(MARTS_DIR / "mart_dengue_semana.parquet", compression="zstd", index=False)
    anual.to_parquet(MARTS_DIR / "mart_dengue_municipio_ano.parquet", compression="zstd", index=False)

    if args.no_upload:
        return

    url, key = env.get("SUPABASE_URL"), env.get("SUPABASE_ANON_KEY")
    if not url or not key:
        sys.exit("Defina SUPABASE_URL e SUPABASE_ANON_KEY no .env")
    loader = SupabaseLoader(url, key)
    loader.load_df("mart_dengue_semana", semana)
    loader.load_df("mart_dengue_municipio_ano", anual)

    # marca metadados de dengue
    meta = pd.DataFrame([
        ("fonte_dengue", "SINAN/DataSUS — DENGBR (notificações de dengue), FTP CID10 FINAIS/PRELIM"),
        ("dengue_cobertura", f"{min(anos)}–{max(anos)}"),
        ("dengue_definicoes", "Caso provável = notificação não descartada (CLASSI_FIN≠5); grave = alarme/grave (11,12) ou FHD/SCD (3,4); óbito = EVOLUCAO=2; município/semana por residência e 1º sintoma (SEM_PRI)"),
        ("gerado_em", datetime.now().isoformat(timespec="seconds")),
    ], columns=["chave", "valor"])
    loader.load_df("meta_dataset", meta)
    print("[done] pipeline SINAN-dengue concluído.")


if __name__ == "__main__":
    main()
