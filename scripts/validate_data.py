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

# O console do Windows usa cp1252: sem isto, o primeiro '≥' de um nome de checagem
# derruba a validação inteira com UnicodeEncodeError — e o CI passa a falhar por
# codificação, não por dado errado.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


class Bloco:
    """Agrupa checagens que dependem de uma consulta, sem transformar erro em skip.

    Antes, os blocos de dengue e de internações eram `try/except Exception` que
    imprimiam `[skip]` e seguiam. Isso significava que uma queda da API, uma coluna
    renomeada ou um filtro quebrado deixavam a validação VERDE sem ter validado
    nada — o modo de falha mais perigoso que um verificador pode ter, porque ele
    afirma que checou. As duas tabelas existem e sustentam páginas publicadas;
    não há motivo para tolerar ausência.

    Uso:
        with Bloco("dengue"):
            ...            # exceção aqui vira FALHA, não skip
    """

    def __init__(self, nome: str) -> None:
        self.nome = nome

    def __enter__(self) -> Bloco:
        return self

    def __exit__(self, tipo, valor, _tb) -> bool:
        if tipo is not None:
            check(f"{self.nome}: consulta respondeu", False, f"{tipo.__name__}: {valor}")
            return True  # registrado como falha; segue para os demais blocos
        return False

    def exige_dados(self, linhas: list[dict]) -> bool:
        """Resultado vazio é falha, não silêncio.

        `if linhas:` deixava o bloco inteiro passar sem imprimir uma linha sequer
        quando a consulta voltava vazia — indistinguível de sucesso no log do CI.
        """
        check(f"{self.nome}: consulta retornou linhas", bool(linhas), f"n={len(linhas)}")
        return bool(linhas)


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
    n_mun = int(agg("dim_municipio", {"select": "count"})[0]["count"])
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

    # 7. Dengue: epidemia 2024 ~6,5M casos prováveis (concilia com MS ~6,6M)
    with Bloco("dengue") as b:
        deng = agg("mart_dengue_municipio_ano", {
            "select": "ano_epi,casos:casos_provaveis.sum()", "ano_epi": "eq.2024"})
        if b.exige_dados(deng):
            casos24 = int(deng[0]["casos"])
            check("dengue 2024 ~ 6,5M casos", 6_000_000 <= casos24 <= 7_000_000, f"obtido={casos24:,}")

    # 8. Internações: sanidade da permanência e coerência dos contadores por tipo de AIH.
    #    A permanência é POR EPISÓDIO, então o denominador é aih_normal — usar
    #    `internacoes` aqui reintroduziria a definição que fracionava internação longa
    #    em várias AIHs. Ver §10 da metodologia.
    with Bloco("internações") as b:
        intern = agg("mart_internacoes_municipio", {
            "select": "internacoes,dias_permanencia,aih_continuacao,aih_normal,"
                      "dias_permanencia_normal,valor_total,valor_normal",
            "capitulo_cid": "eq.TOTAL", "ano": "eq.2023", "populacao": "gte.500000", "limit": "30"})
        if b.exige_dados(intern):
            tot_i = sum(x["internacoes"] for x in intern)
            tot_n = sum(x["aih_normal"] or 0 for x in intern)
            tot_dn = sum(x["dias_permanencia_normal"] or 0 for x in intern)
            pm = tot_dn / tot_n if tot_n else 0
            check("internações: permanência média 2–12 dias (capitais 2023)", 2 <= pm <= 12, f"pm={pm:.1f}")
            check("internações: aih_normal = internacoes − aih_continuacao",
                  all((x["aih_normal"] or 0) == x["internacoes"] - (x["aih_continuacao"] or 0)
                      for x in intern), "identidade dos contadores por tipo de AIH")
            check("internações: contadores da AIH normal são subconjunto do total",
                  all((x["aih_continuacao"] or 0) <= x["internacoes"]
                      and (x["dias_permanencia_normal"] or 0) <= x["dias_permanencia"]
                      and (x["valor_normal"] or 0) <= x["valor_total"] + 1e-6
                      for x in intern), "dias/valor normais ≤ totais")
            frac = sum(x["aih_continuacao"] or 0 for x in intern) / tot_i if tot_i else 0
            check("internações: continuação entre 0,1% e 5% do total (capitais)",
                  0.001 <= frac <= 0.05, f"fração={frac:.3%}")

    print()
    if FALHAS:
        print(f"❌ {len(FALHAS)} checagem(ns) falharam: {FALHAS}")
        sys.exit(1)
    print("✅ todas as checagens passaram")


if __name__ == "__main__":
    main()
