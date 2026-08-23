"""
_baixar_mart_completo.py — Reconstrói um parquet local a partir do estado atual no Supabase.

Uso interno: os pipelines de reprocessamento (pipeline_sih_agravo.py,
pipeline_sih_hospitalar.py) sobrescrevem o parquet local a cada --ano
processado (só contêm o último ano rodado), mas fazem upsert cumulativo no
Supabase (merge-duplicates por PK, que inclui ano). Depois de rodar vários
anos em sequência, o parquet local fica desatualizado — este script baixa o
estado completo e atual da tabela via REST paginado, para uso por scripts
downstream (ex.: forecast) que precisam da série multi-ano local.

Uso:
  .venv311/Scripts/python scripts/_baixar_mart_completo.py mart_demanda_mensal_hospital
"""
from __future__ import annotations

import sys
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
PAGE = 1000


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


def baixar(table: str) -> pd.DataFrame:
    env = load_env()
    url, key = env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    rows: list[dict] = []
    offset = 0
    while True:
        r = requests.get(
            f"{url.rstrip('/')}/rest/v1/{table}",
            headers={**h, "Range-Unit": "items", "Range": f"{offset}-{offset + PAGE - 1}"},
            params={"select": "*"},
            timeout=60,
        )
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < PAGE:
            break
        offset += PAGE
    return pd.DataFrame(rows)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("uso: _baixar_mart_completo.py <nome_da_tabela>")
    table = sys.argv[1]
    df = baixar(table)
    MARTS.mkdir(exist_ok=True)
    df.to_parquet(MARTS / f"{table}.parquet", compression="zstd", index=False)
    print(f"[baixar] {table}: {len(df):,} linhas salvas em data/marts/{table}.parquet", flush=True)
    # Este arquivo veio do POSTGRES, nao de pipeline. Registrar a
    # origem impede que o publicador o rotule como produzido pelo
    # pipeline -- foi o que aconteceu com mart_demanda_mensal_hospital.
    from _publicacao import registrar_origem
    registrar_origem(table, "postgres-bootstrap")


if __name__ == "__main__":
    main()
