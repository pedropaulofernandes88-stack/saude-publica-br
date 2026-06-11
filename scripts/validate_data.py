"""
validate_data.py — validação automática da base publicada (via API pública).

Checa invariantes que qualquer consumidor pode verificar de forma independente:
  1. Âncoras oficiais de anos consolidados (totais exatos do SIM);
  2. Conciliação entre marts (uf_mes TOTAL × municipio TOTAL × causa);
  3. Cobertura do excesso de mortalidade (27 UFs + BR, 2020+);
  4. Integridade dimensional (municípios, faixas, padrão etário).

Sai com código ≠ 0 se qualquer checagem falhar (uso em CI).
"""
from __future__ import annotations

import os
import sys

import requests

URL = os.environ.get("SUPABASE_URL", "https://zekjhmxjamatlxpkykde.supabase.co").rstrip("/")
KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpla2pobXhqYW1hdGx4cGt5a2RlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwNzY4MzIsImV4cCI6MjA5NjY1MjgzMn0.px8FcU0QK8w9v95kwGlGzASKpY3drsxAvFe0e6wUoCU",
)
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

# Totais oficiais de anos consolidados (óbitos não fetais, SIM)
ANCORAS = {2015: 1_264_175, 2022: 1_544_266}

FALHAS: list[str] = []


def check(nome: str, cond: bool, detalhe: str = "") -> None:
    status = "OK " if cond else "FALHOU"
    print(f"[{status}] {nome} {detalhe}")
    if not cond:
        FALHAS.append(nome)


def agg(table: str, params: dict) -> list[dict]:
    r = requests.get(f"{URL}/rest/v1/{table}", params=params, headers=H, timeout=120)
    r.raise_for_status()
    return r.json()


def main() -> None:
    # 1. Âncoras de anos consolidados
    por_ano = {
        int(x["ano"]): int(x["sum"])
        for x in agg("mart_mortalidade_uf_mes", {
            "select": "ano,sum:obitos.sum()",
            "capitulo_cid": "eq.TOTAL", "sexo": "eq.TOTAL", "faixa_etaria": "eq.TOTAL",
            "order": "ano",
        })
    }
    for ano, esperado in ANCORAS.items():
        obtido = por_ano.get(ano)
        check(f"âncora {ano}", obtido == esperado, f"esperado={esperado:,} obtido={obtido:,}" if obtido else "ano ausente")

    # 2. Conciliação uf_mes × municipio (por ano, tolerância zero)
    mun_ano = {
        int(x["ano"]): int(x["sum"])
        for x in agg("mart_mortalidade_municipio", {
            "select": "ano,sum:obitos.sum()",
            "capitulo_cid": "eq.TOTAL", "sexo": "eq.TOTAL", "order": "ano",
        })
    }
    for ano, total in sorted(por_ano.items()):
        check(f"conciliação municipio×uf_mes {ano}", mun_ano.get(ano) == total,
              f"municipio={mun_ano.get(ano):,} uf_mes={total:,}" if ano in mun_ano else "ausente")

    # 3. Causa ≈ total (causas vazias podem ficar de fora; tolerância 0,5%)
    causa_ano = {
        int(x["ano"]): int(x["sum"])
        for x in agg("mart_mortalidade_causa", {"select": "ano,sum:obitos.sum()", "order": "ano"})
    }
    for ano, total in sorted(por_ano.items()):
        c = causa_ano.get(ano, 0)
        check(f"conciliação causa {ano}", abs(c - total) / total < 0.005, f"causa={c:,} total={total:,}")

    # 4. Excesso: 28 séries (27 UFs + BR) por ano desde 2020
    exc = agg("mart_excesso_uf_mes", {"select": "ano,uf_sigla"})
    series = {(x["ano"], x["uf_sigla"]) for x in exc}
    anos_exc = sorted({a for a, _ in series})
    check("excesso cobre 2020+", min(anos_exc, default=0) == 2020, str(anos_exc))
    for a in anos_exc:
        n = len({u for aa, u in series if aa == a})
        check(f"excesso {a}: 28 séries", n == 28, f"obtido={n}")

    # 5. Dimensões
    n_mun = len(agg("dim_municipio", {"select": "municipio_cod", "limit": "10000"}))
    check("dim_municipio ≥ 5570", n_mun >= 5570, f"obtido={n_mun}")
    n_pad = len(agg("dim_pop_padrao", {"select": "faixa_etaria"}))
    check("dim_pop_padrao = 8 faixas", n_pad == 8, f"obtido={n_pad}")

    # 6. Sanidade da padronização (existe e é positiva em municípios grandes)
    tp = agg("mart_mortalidade_municipio", {
        "select": "taxa_padronizada_100k",
        "capitulo_cid": "eq.TOTAL", "sexo": "eq.TOTAL", "ano": "eq.2023",
        "populacao": "gte.500000", "limit": "50",
    })
    vals = [x["taxa_padronizada_100k"] for x in tp if x["taxa_padronizada_100k"] is not None]
    check("taxa padronizada presente (capitais 2023)", len(vals) >= 20 and all(100 < v < 2000 for v in vals),
          f"n={len(vals)}")

    print()
    if FALHAS:
        print(f"❌ {len(FALHAS)} checagem(ns) falharam: {FALHAS}")
        sys.exit(1)
    print("✅ todas as checagens passaram")


if __name__ == "__main__":
    main()
