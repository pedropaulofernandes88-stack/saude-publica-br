"""
_subir_mart.py — Publica um parquet local na tabela correspondente do Supabase.

Contraparte de _baixar_mart_completo.py. Os scripts de análise
(analise_cobertura_icsap.py, analise_leitos_icsap.py, analise_equidade_aps.py…)
gravam só o parquet local — não têm rotina de upload própria, porque nasceram
como análise pontual. Quando o insumo é reprocessado, o parquet local fica
correto e a tabela publicada fica velha. Este script fecha essa lacuna sem
espalhar mais um bloco de upload por script.

Upsert com merge-duplicates (mesma convenção dos pipelines): linhas com a mesma
PK são atualizadas, linhas novas são inseridas. NÃO apaga o que existe e não
está no parquet — se a intenção for substituir a tabela inteira, use --truncar.

Uso:
  .venv311/Scripts/python scripts/_subir_mart.py mart_cobertura_icsap_municipio
  .venv311/Scripts/python scripts/_subir_mart.py mart_leitos_icsap_municipio --truncar
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests
from _supabase_key import chave_escrita

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
LOTE = 8_000


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _jd(o):
    """Serializa o que o json não conhece.

    Data/hora vem ANTES do `.item()`: `pd.Timestamp` tem `.item()`, e ele
    devolve um objeto que o json também não serializa, então o `default`
    reentrava para sempre e o erro saía como "Circular reference detected" —
    mensagem que não aponta para data nenhuma. Foi assim que
    `mart_excesso_uf_mes` e `mart_mortalidade_uf_mes` falharam ao subir.
    """
    if isinstance(o, datetime | date):
        return o.isoformat()
    if hasattr(o, "isoformat"):          # pd.Timestamp, np.datetime64 via pandas
        return o.isoformat()
    return o.item() if hasattr(o, "item") else o


def subir(table: str, df: pd.DataFrame, truncar: bool = False) -> None:
    env = load_env()
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}",
         "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}

    if truncar:
        r = requests.delete(f"{url}/rest/v1/{table}", headers=h,
                            params={"municipio_cod": "not.is.null"}, timeout=120)
        if r.status_code not in (200, 204):
            raise RuntimeError(f"{table}: DELETE HTTP {r.status_code} {r.text[:200]}")
        print(f"[subir] {table}: tabela esvaziada antes da carga", flush=True)

    recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
    lotes = math.ceil(len(recs) / LOTE)
    for i in range(lotes):
        body = json.dumps(recs[i * LOTE:(i + 1) * LOTE], default=_jd, allow_nan=False)
        for tentativa in range(4):
            r = requests.post(f"{url}/rest/v1/{table}", headers=h, data=body, timeout=300)
            if r.status_code in (200, 201):
                break
            if tentativa == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"{table}: HTTP {r.status_code} {r.text[:300]}")
            time.sleep(3 * (tentativa + 1))
        print(f"[subir] {table}: lote {i + 1}/{lotes}", flush=True)
    print(f"[subir] {table}: {len(recs):,} linhas publicadas", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tabela")
    ap.add_argument("--truncar", action="store_true",
                    help="apaga a tabela antes de carregar (para marts sem PK estável)")
    args = ap.parse_args()

    caminho = MARTS / f"{args.tabela}.parquet"
    if not caminho.exists():
        raise SystemExit(f"parquet não encontrado: {caminho}")
    df = pd.read_parquet(caminho)
    print(f"[subir] {args.tabela}: {len(df):,} linhas em {caminho.name}", flush=True)
    subir(args.tabela, df, truncar=args.truncar)


if __name__ == "__main__":
    main()
