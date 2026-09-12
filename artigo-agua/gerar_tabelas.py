"""
gerar_tabelas.py — as tabelas do artigo da água
================================================

    .venv311/Scripts/python artigo-agua/gerar_tabelas.py
    .venv311/Scripts/python artigo-agua/gerar_tabelas.py --sem-recalcular

POR QUE ESTE SCRIPT RECALCULA EM VEZ DE LER O QUE ESTÁ EM DISCO
---------------------------------------------------------------
Ele **executa a análise** antes de formatar. A alternativa — ler os CSVs que já
estão em `data/analises/agua/` — parece equivalente e não é: bastaria alguém
recoletar o SIM ou o SISAGUA e esquecer de rodar a análise para o artigo passar
a descrever um dado que não existe mais, sem que nada avisasse. Aconteceu no
primeiro manuscrito do repositório quando 2024 foi recoletado do `.dbc`: doze
tabelas divergiram de uma vez, em silêncio.

`--sem-recalcular` existe para iterar formatação, não para gerar entrega.

O QUE ESTE SCRIPT FAZ, ENTÃO
-----------------------------
Traduz: nomes de coluna em português com acento, rótulos legíveis no lugar de
códigos, recorte de linhas quando a tabela inteira não caberia na página.
**Nenhuma conta nova** — se aparecer uma divisão aqui, ela está no lugar errado.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
PROJETO = RAIZ.parent
ANALISES = PROJETO / "data" / "analises" / "agua"
TABELAS = RAIZ / "tabelas"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: De onde cada tabela do artigo vem, e como ela se chama na página.
#: A ordem é a do manuscrito.
MAPA = [
    ("tabela_1_base", "tab01_base", "o recorte"),
    ("tabela_2_serie_anual", "tab02_serie_anual", "a série que motiva o artigo"),
    ("tabela_3_alta_por_faixa", "tab03_alta_por_faixa", "a alta por faixa etária"),
    ("tabela_4_alta_por_codigo", "tab04_alta_por_codigo", "a alta por código CID-10"),
    ("tabela_5_teste_codificacao", "tab05_teste_codificacao",
     "o teste de redistribuição de codificação"),
    ("tabela_6_exposicao", "tab06_exposicao", "as quatro classes de vigilância"),
    ("tabela_7_gradiente", "tab07_gradiente", "o gradiente, duas causas lado a lado"),
    ("tabela_8_criterios", "tab08_criterios", "os quatro critérios, com IC95%"),
    ("tabela_9_rrr_por_idade", "tab09_rrr_por_idade", "a razão de razões por faixa"),
    ("tabela_10_sem_vigilancia_por_uf", "tab10_sem_vigilancia_por_uf",
     "os municípios sem vigilância, por UF"),
    ("tabela_11_por_quartil_de_acesso", "tab11_por_quartil_de_acesso",
     "o RRR dentro de cada quartil de acesso"),
]

#: Colunas sem acento na análise -> como aparecem na página. A análise escreve
#: ASCII de propósito (ela roda em terminal Windows); o artigo é publicação.
ACENTOS = {
    "Faixa etaria": "Faixa etária", "Variacao %": "Variação %",
    "Descricao": "Descrição", "Criterio": "Critério",
    "Pre-declarado": "Pré-declarado", "Municipios": "Municípios",
    "Obitos totais": "Óbitos totais", "Obitos A00-A09": "Óbitos A00–A09",
    "Obitos respiratorios": "Óbitos respiratórios",
    "Infeccao respiratoria": "Infecção respiratória",
    "Classe de vigilancia": "Classe de vigilância",
    "RR respiratoria": "RR respiratória",
    "Taxa respiratoria por 100 mil": "Taxa respiratória por 100 mil",
    "Municipios sem vigilancia": "Municípios sem vigilância",
    "Municipios na UF": "Municípios na UF",
    "% da UF sem vigilancia": "% da UF sem vigilância",
    "Mal definidas": "Mal definidas",
    "A00-A09 por 10 mil obitos": "A00-A09 por 10 mil óbitos",
    "hidrica_por_10k_obitos": "A00-A09 por 10 mil óbitos",
    "Ano preliminar": "Ano preliminar",
    "% sem agua (mediana)": "% sem água (mediana)",
    "Analfabetismo % (mediana)": "Analfabetismo % (mediana)",
    "Quartil de acesso (Censo)": "Quartil de acesso (Censo)",
    "Obitos 2015-2024": "Óbitos 2015–2024",
    "A00-A09 sem vigilancia": "A00–A09 sem vigilância",
    "A00-A09 vigilancia regular": "A00–A09 vigilância regular",
    "Obitos por A00-A09 (subgrupo 1.2)": "Óbitos por A00–A09 (subgrupo 1.2)",
    "Pessoas-ano": "Pessoas-ano",
}

#: Rótulos, na página. A análise usa ASCII (ela roda em terminal Windows, onde
#: acento em stdout quebra); aqui vira texto legível. Isto cobre os VALORES das
#: células, não só os nomes de coluna — foi o que faltou na primeira versão, e
#: as figuras saíram com "acesso a agua" e "controle so pneumonia" no eixo.
ROTULOS = {
    "1. Especificidade (bruto)": "1. Especificidade (bruto)",
    "2. Ajustado por acesso a agua (MH)": "2. Ajustado por acesso à água (MH)",
    "Sensibilidade: controle so pneumonia/influenza":
        "Sensibilidade: controle só pneumonia/influenza",
    "4. Padronizado por idade (POST-HOC)": "4. Padronizado por idade (POST-HOC)",
    "Todos os municipios com base suficiente": "Todos os municípios com base suficiente",
    "Onde as mal definidas NAO cairam": "Onde as mal definidas NÃO caíram",
    "Onde as mal definidas cairam": "Onde as mal definidas caíram",
    "Municipios do pais": "Municípios do país",
    "Analisaveis (com denominador)": "Analisáveis (com denominador)",
    "Obitos totais 2015-2024": "Óbitos totais 2015–2024",
    "Obitos por A00-A09 (subgrupo 1.2)": "Óbitos por A00–A09 (subgrupo 1.2)",
    "Obitos por infeccao respiratoria (subgrupo 1.2)":
        "Óbitos por infecção respiratória (subgrupo 1.2)",
    "Colera": "Cólera", "Shiguelose": "Shiguelose",
    "Febres tifoide e paratifoide": "Febres tifoide e paratifoide",
    "Outras infeccoes por Salmonella": "Outras infecções por Salmonella",
    "Outras infeccoes intestinais bacterianas": "Outras infecções intestinais bacterianas",
    "Intoxicacoes alimentares bacterianas": "Intoxicações alimentares bacterianas",
    "Amebiase": "Amebíase",
    "Outras doencas intestinais por protozoarios":
        "Outras doenças intestinais por protozoários",
    "Infeccoes intestinais virais": "Infecções intestinais virais",
    "Diarreia e gastroenterite de origem infecciosa presumivel":
        "Diarreia e gastroenterite de origem infecciosa presumível",
    "sem vigilancia": "sem vigilância",
    "vigilancia rara (ate 6 meses)": "vigilância rara (até 6 meses)",
    "vigilancia parcial (7 a 11)": "vigilância parcial (7 a 11 meses)",
    "vigilancia regular (12)": "vigilância regular (12 meses)",
}


def recalcular() -> None:
    print("[tabelas] recalculando a análise (não é opcional para entrega)...", flush=True)
    r = subprocess.run(
        [sys.executable, str(PROJETO / "scripts" / "analise_agua_mortalidade.py")],
        cwd=PROJETO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"[tabelas] a análise falhou:\n{(r.stderr or r.stdout)[-2000:]}")
    print("[tabelas] análise concluída.", flush=True)


def traduzir(d: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas e traduz os VALORES de texto.

    O teste de tipo NÃO é `dtype == object`. O pandas moderno lê coluna de texto
    como `StringDtype`, e a comparação com `object` devolve `False` — de modo que
    a tradução dos valores não rodava e as células saíam "sem vigilancia" e
    "acesso a agua" no artigo, enquanto os nomes de coluna (que passam por
    `rename`, não por este laço) saíam certos. Um defeito que só aparece na
    página, e não quebra nada.
    """
    d = d.rename(columns=ACENTOS)
    for col in d.columns:
        d[col] = d[col].map(lambda v: ROTULOS.get(v, v) if isinstance(v, str) else v)
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description="Tabelas do artigo da água.")
    ap.add_argument("--sem-recalcular", action="store_true",
                    help="usa os CSVs já em disco; para iterar formatação, não para entregar")
    args = ap.parse_args()

    if not args.sem_recalcular:
        recalcular()

    TABELAS.mkdir(parents=True, exist_ok=True)
    faltando = []
    for destino, origem, descricao in MAPA:
        caminho = ANALISES / f"{origem}.csv"
        if not caminho.exists():
            faltando.append(origem)
            continue
        d = traduzir(pd.read_csv(caminho))
        d.to_csv(TABELAS / f"{destino}.csv", index=False, encoding="utf-8")
        print(f"   {destino}: {len(d):>3} linhas — {descricao}", flush=True)

    if faltando:
        raise SystemExit(
            f"[tabelas] a análise não produziu {faltando}. O artigo NÃO pode "
            "ser montado com tabela faltando: uma tabela ausente vira uma "
            "afirmação sem procedência no manuscrito.")
    print(f"\n[ok] {len(MAPA)} tabelas em {TABELAS.relative_to(PROJETO)}")


if __name__ == "__main__":
    main()
