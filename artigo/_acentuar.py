"""
_acentuar.py — devolve os acentos aos rótulos na camada de apresentação
========================================================================

Usado pelo transporte de tabelas do artigo da água.

POR QUE OS RÓTULOS CHEGAM SEM ACENTO
-------------------------------------
`scripts/analise_agua_painel.py` e `analise_agua_ecoli.py` escrevem rótulos em
ASCII: "Municipios", "Obitos", "hipotese", "respiratorias". Dentro do
repositório isso não incomoda — são identificadores de linha num CSV de
trabalho. Num manuscrito em português, incomoda: "Sem municipios com menos de
5.000 hab." numa tabela ao lado de um texto acentuado parece descuido, e é.

POR QUE AQUI, E NÃO NA ANÁLISE
-------------------------------
Porque a análise leva meia hora de bootstrap e o rótulo é apresentação, não
resultado. É a mesma separação que `CURTO`, no gerador de figuras, já faz: o CSV
guarda o nome longo e a figura mostra o curto. O que esta camada **não** pode
fazer é mudar número — ela só acrescenta diacrítico, e a conferência abaixo
garante isso comparando as duas versões sem acento.

A GUARDA É O QUE TORNA ISTO SEGURO
-----------------------------------
Um mapa de tradução silencioso é a forma clássica de um rótulo novo passar
despercebido: ele simplesmente não é traduzido, e a tabela sai metade acentuada.
Por isso `acentuar` **aborta** quando encontra um rótulo que parece português
sem acento e não está no mapa, em vez de deixá-lo passar.
"""
from __future__ import annotations

import re
import unicodedata

#: ASCII → acentuado. Só diacrítico: nenhuma entrada muda palavra ou número.
MAPA = {
    # colunas
    "Municipios": "Municípios",
    "Obitos por A00-A09": "Óbitos por A00–A09",
    "Observado por 10 mil obitos": "Observado por 10 mil óbitos",
    "Projetado por 10 mil obitos": "Projetado por 10 mil óbitos",
    "Observado por milhao de habitantes": "Observado por milhão de habitantes",
    "Projetado por milhao de habitantes": "Projetado por milhão de habitantes",
    "Excesso relativo % (obitos)": "Excesso relativo % (óbitos)",
    "Muda de direcao": "Muda de direção",
    # grupos de causa
    "A00-A09 intestinais (hipotese)": "A00–A09 intestinais (hipótese)",
    "J00-J22 respiratorias (subgrupo 1.2)": "J00–J22 respiratórias (subgrupo 1.2)",
    "outras infecciosas do subgrupo 1.2": "outras infecciosas do subgrupo 1.2",
    "I20-I25 isquemicas do coracao": "I20–I25 isquêmicas do coração",
    "V01-Y98 causas externas": "V01–Y98 causas externas",
    # recortes do painel
    "Sem municipios com menos de 5.000 hab.":
        "Sem municípios com menos de 5.000 hab.",
    "Sem o DF e sem municipios pequenos": "Sem o DF e sem municípios pequenos",
    "Sem 2022 e 2023 (troca de base populacional)":
        "Sem 2022 e 2023 (troca de base populacional)",
    # linhas descritivas do painel
    "Municipios no painel": "Municípios no painel",
    "Linhas municipio-ano": "Linhas município-ano",
    "Municipio-ano sem vigilancia no ano anterior":
        "Município-ano sem vigilância no ano anterior",
    "Municipio-ano sem vigilancia no ano anterior (%)":
        "Município-ano sem vigilância no ano anterior (%)",
    "Municipios com vigilancia em TODOS os anos":
        "Municípios com vigilância em TODOS os anos",
    "Municipios sem vigilancia em TODOS os anos":
        "Municípios sem vigilância em TODOS os anos",
    "Municipios que MUDARAM de estado no periodo":
        "Municípios que MUDARAM de estado no período",
    # linhas descritivas do painel do E. coli
    "Municipios com alguma amostra reportada":
        "Municípios com alguma amostra reportada",
    "Municipio-ano no recorte (condicional a reportar)":
        "Município-ano no recorte (condicional a reportar)",
    "Municipio-ano com E. coli detectada no ano anterior":
        "Município-ano com E. coli detectada no ano anterior",
    "Municipio-ano com E. coli detectada (%)":
        "Município-ano com E. coli detectada (%)",
    "Deteccoes de E. coli no periodo": "Detecções de E. coli no período",
    "Amostras analisadas no periodo": "Amostras analisadas no período",
    "Municipios que MUDARAM de estado de deteccao":
        "Municípios que MUDARAM de estado de detecção",
}

#: Prefixos compostos: "Obitos: <grupo>" e "Municipios que mudam E tem obito:
#: <grupo>" variam com o grupo, e listar as dez combinações seria convidar a
#: esquecer uma quando um grupo mudar.
PREFIXOS = {
    "Obitos: ": "Óbitos: ",
    "Municipios com algum obito: ": "Municípios com algum óbito: ",
    "Municipios que mudam E tem obito: ": "Municípios que mudam e têm óbito: ",
}

#: Palavras que denunciam português sem acento. Um rótulo que contenha uma
#: delas e não tenha sido traduzido aborta o transporte.
SUSPEITAS = re.compile(
    r"\b(municipi\w*|obito\w*|deteccao|deteccoes|periodo|vigilancia|"
    r"hipotese|respiratori\w*|isquemic\w*|coracao|milhao|direcao|populacion\w*)\b",
    re.IGNORECASE)


def _tem_acento(s: str) -> bool:
    return any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", s))


def acentuar(s: str) -> str:
    """Devolve o rótulo acentuado. Aborta se parecer português sem acento."""
    if s in MAPA:
        return MAPA[s]
    for cru, bom in PREFIXOS.items():
        if s.startswith(cru):
            return bom + acentuar(s[len(cru):])
    if SUSPEITAS.search(s) and not _tem_acento(s):
        raise SystemExit(
            f"rótulo sem acento e fora do mapa: {s!r}. Acrescente-o a "
            "`artigo/_acentuar.py`. Traduzir em silêncio deixaria a tabela "
            "metade acentuada, que é pior que toda em ASCII — parece revisão "
            "feita pela metade, e é.")
    return s


def acentuar_tabela(d):
    """Aplica `acentuar` a colunas e a toda célula de texto de um DataFrame."""
    d = d.rename(columns={c: acentuar(str(c)) for c in d.columns})
    for c in d.columns:
        if d[c].dtype == object:
            d[c] = d[c].map(lambda v: acentuar(v) if isinstance(v, str) else v)
    return d
