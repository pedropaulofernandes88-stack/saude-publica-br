"""
_sanity_check_ano.py — Valida o parquet local recém-processado antes do upload real.

Uso:
  .venv311/Scripts/python scripts/_sanity_check_ano.py agravo 2022
  .venv311/Scripts/python scripts/_sanity_check_ano.py hospitalar 2022

Sai com código != 0 e mensagem clara se algo parecer errado — a cadeia de
orquestração aborta nesse caso, antes de tocar o Supabase.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"


def checar_agravo(ano: int) -> None:
    hosp = pd.read_parquet(MARTS / "mart_internacoes_hospital.parquet")
    agr = pd.read_parquet(MARTS / "mart_internacoes_agravo.parquet")
    assert (hosp.ano == ano).all(), f"mart_internacoes_hospital tem anos != {ano}"
    assert (agr.ano == ano).all(), f"mart_internacoes_agravo tem anos != {ano}"
    assert len(hosp) > 1000, f"mart_internacoes_hospital com poucas linhas: {len(hosp)}"
    assert len(agr) > 1000, f"mart_internacoes_agravo com poucas linhas: {len(agr)}"
    assert hosp.cnes.notna().all(), "cnes nulo em mart_internacoes_hospital"
    assert hosp.mortalidade_pct.between(0, 100).all(), "mortalidade_pct fora de [0,100]"
    print(f"[sanity] agravo {ano}: hospital={len(hosp):,} agravo={len(agr):,} — OK", flush=True)


def checar_hospitalar(ano: int) -> None:
    hsmr = pd.read_parquet(MARTS / "mart_hsmr_hospital.parquet")
    los = pd.read_parquet(MARTS / "mart_los_hospital.parquet")
    dem = pd.read_parquet(MARTS / "mart_demanda_mensal_hospital.parquet")
    assert (hsmr.ano == ano).all(), f"mart_hsmr_hospital tem anos != {ano}"
    assert len(hsmr) > 1000, f"mart_hsmr_hospital com poucas linhas: {len(hsmr)}"
    agregado = hsmr.obitos_observados.sum() / hsmr.obitos_esperados.sum()
    assert 0.9 <= agregado <= 1.1, f"HSMR agregado nacional fora do esperado: {agregado:.4f} (deveria ser ~1.0)"
    assert len(los) > 1000, f"mart_los_hospital com poucas linhas: {len(los)}"
    assert len(dem) > 1000, f"mart_demanda_mensal_hospital com poucas linhas: {len(dem)}"
    assert dem.ano_mes.str.startswith(str(ano)).all(), f"mart_demanda_mensal_hospital tem meses fora de {ano}"
    print(f"[sanity] hospitalar {ano}: hsmr_agregado={agregado:.4f} hsmr={len(hsmr):,} "
          f"los={len(los):,} demanda={len(dem):,} — OK", flush=True)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("uso: _sanity_check_ano.py <agravo|hospitalar> <ano>")
    kind, ano = sys.argv[1], int(sys.argv[2])
    if kind == "agravo":
        checar_agravo(ano)
    elif kind == "hospitalar":
        checar_hospitalar(ano)
    else:
        raise SystemExit(f"kind desconhecido: {kind}")


if __name__ == "__main__":
    main()
