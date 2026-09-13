"""
gerar_tabelas_painel.py — as cinco tabelas da reanálise em painel
==================================================================

    .venv311/Scripts/python artigo-agua/gerar_tabelas_painel.py

Copia `data/analises/agua-painel/tab0*.csv` para `artigo-agua/tabelas/` com o
nome que o manuscrito cita, conferindo que cada tabela tem as colunas que o
texto lê.

POR QUE COPIAR, E POR QUE CONFERIR AS COLUNAS
----------------------------------------------
O outro gerador deste artigo — `gerar_tabelas.py` — **reexecuta** a análise, por
decisão explícita: ali a conta é barata. Aqui não é: o painel leva meia hora de
bootstrap, e reexecutar a cada formatação de tabela convidaria a não formatar.
Então a análise escreve uma vez em `data/analises/`, e este script transporta.

Transporte é o momento em que os nomes silenciosamente divergem: a análise
renomeia uma coluna, o manuscrito continua citando a antiga, e o CSV do pacote
passa a ter cabeçalho que o texto não menciona. Nada nisso quebra. Por isso cada
tabela declara abaixo as colunas que o manuscrito lê, e a falta de qualquer uma
**aborta** em vez de copiar o arquivo mesmo assim.

A numeração é P1 a P5 — "P" de painel — para não colidir com as onze tabelas do
desenho transversal, que continuam no pacote como material do desenho anterior.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "artigo"))
from _acentuar import acentuar_tabela  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent
ANALISE = RAIZ.parent / "data" / "analises" / "agua-painel"
ANALISE_EC = RAIZ.parent / "data" / "analises" / "agua-ecoli"
TABELAS = RAIZ / "tabelas"

#: origem → (destino no artigo, colunas que o manuscrito lê)
MAPA = {
    "tab01_painel": ("tabela_p1_painel", ("Recorte", "Valor")),
    "tab02_especificidade": (
        "tabela_p2_especificidade",
        ("Grupo de causa", "IRR", "IC95% inferior", "IC95% superior",
         "Exclui 1")),
    "tab03_efeito_fixo": (
        "tabela_p3_efeito_fixo",
        ("Grupo de causa", "IRR sem efeito fixo", "IRR com efeito fixo",
         "Removido pelo efeito fixo",
         "RRR contra o controle, sem efeito fixo",
         "RRR contra o controle, com efeito fixo")),
    "tab04_tendencia": (
        "tabela_p4_tendencia",
        ("Ano", "Obitos por A00-A09",
         "Observado por 10 mil obitos", "Projetado por 10 mil obitos",
         "Excesso relativo % (obitos)",
         "Observado por milhao de habitantes",
         "Projetado por milhao de habitantes",
         "Excesso relativo % (habitantes)", "Base do ajuste")),
    "tab05_robustez": (
        "tabela_p5_robustez",
        ("Recorte", "Municipios", "IRR", "IC95% inferior", "IC95% superior")),
}

#: A serie E: a analise do E. coli, condicional a reportar. Mora em outra pasta
#: de analise porque e' outro painel — desbalanceado, com outro universo — e
#: misturar as duas saidas no mesmo diretorio convidaria a comparar linhas que
#: nao descrevem os mesmos municipios.
MAPA_EC = {
    "tab01_painel": ("tabela_e1_painel", ("Recorte", "Valor")),
    "tab02_especificidade": (
        "tabela_e2_especificidade",
        ("Grupo de causa", "IRR", "IC95% inferior", "IC95% superior", "Exclui 1")),
    "tab03_efeito_fixo": (
        "tabela_e3_efeito_fixo",
        ("Grupo de causa", "IRR sem efeito fixo", "IRR com efeito fixo",
         "Removido pelo efeito fixo",
         "RRR contra o controle, sem efeito fixo",
         "RRR contra o controle, com efeito fixo")),
    "tab04_intensidade": (
        "tabela_e4_intensidade",
        ("Grupo de causa", "IRR sem ajuste por amostras",
         "IRR ajustado por log(amostras)", "Deslocamento", "Muda de direcao")),
    "tab05_robustez": (
        "tabela_e5_robustez",
        ("Recorte", "Municipios", "IRR", "IC95% inferior", "IC95% superior")),
}


def main() -> None:
    TABELAS.mkdir(parents=True, exist_ok=True)
    for pasta, script in ((ANALISE, "analise_agua_painel.py"),
                          (ANALISE_EC, "analise_agua_ecoli.py")):
        if not pasta.exists():
            raise SystemExit(
                f"{pasta} não existe. Rode `scripts/{script}` antes — este "
                "script transporta tabela, não a produz.")

    for pasta, mapa in ((ANALISE, MAPA), (ANALISE_EC, MAPA_EC)):
        _transportar(pasta, mapa)

    total = len(MAPA) + len(MAPA_EC)
    print(f"[ok] {total} tabelas em {TABELAS.relative_to(RAIZ.parent)}")


def _transportar(pasta: Path, mapa: dict) -> None:
    """Copia um conjunto de tabelas conferindo as colunas que o texto cita."""
    for origem, (destino, colunas) in mapa.items():
        caminho = pasta / f"{origem}.csv"
        if not caminho.exists():
            raise SystemExit(
                f"{caminho} não existe. A análise do painel escreve as cinco "
                "tabelas juntas; se falta uma, ela não terminou.")
        d = pd.read_csv(caminho)
        faltam = [c for c in colunas if c not in d.columns]
        if faltam:
            raise SystemExit(
                f"{origem}.csv não tem {faltam}. O manuscrito cita essas "
                f"colunas; as que existem são {list(d.columns)}. Copiar assim "
                "poria no pacote uma tabela que o texto não descreve.")
        # Acentuar na camada de apresentação, e não copiar cru: a análise
        # escreve rótulos em ASCII, e o manuscrito é em português. `acentuar`
        # aborta se aparecer rótulo novo fora do mapa. Ver `artigo/_acentuar.py`.
        acentuar_tabela(d).to_csv(TABELAS / f"{destino}.csv", index=False,
                                  encoding="utf-8")
        print(f"[tab] {destino}.csv — {len(d)} linhas, {len(d.columns)} colunas")


if __name__ == "__main__":
    main()
