"""
_metricas_aih.py — regras compartilhadas de agregação do SIH.

Existe para que a matemática que define os números publicados fique separada do
código que fala com o FTP e com o Supabase. Enquanto ela morava dentro das
funções de rede, não havia como testá-la sem baixar 16 GB — e foi exatamente
uma linha dessa matemática que derrubou o reprocessamento em produção.

Reúne o que estava triplicado em pipeline_sih.py, pipeline_sih_agravo.py e
pipeline_sih_hospitalar.py:
  - a tabela de capítulos CID-10 e o mapeamento a partir do CID de 3 caracteres;
  - a derivação das médias por episódio a partir dos contadores por tipo de AIH.

TIPO DE AIH — o RD mistura AIH normal (IDENT=1) com AIH de CONTINUAÇÃO
(IDENT=5), emitida quando a internação se prolonga além do período da AIH
anterior. Uma internação longa vira várias linhas. Contar linhas é a
aproximação correta para PRODUÇÃO aprovada, mas distorce média por episódio:
no capítulo VI a permanência cai de 8,78 para 6,40 dias quando se restringe à
AIH normal. Ver https://rfsaldanha.github.io/sis/sih.html (cap. SIH).
"""
from __future__ import annotations

import pandas as pd

CID10_CAPITULOS: list[tuple[str, str, str]] = [
    ("I", "A00", "B99"), ("II", "C00", "D48"), ("III", "D50", "D89"), ("IV", "E00", "E90"),
    ("V", "F00", "F99"), ("VI", "G00", "G99"), ("VII", "H00", "H59"), ("VIII", "H60", "H95"),
    ("IX", "I00", "I99"), ("X", "J00", "J99"), ("XI", "K00", "K93"), ("XII", "L00", "L99"),
    ("XIII", "M00", "M99"), ("XIV", "N00", "N99"), ("XV", "O00", "O99"), ("XVI", "P00", "P96"),
    ("XVII", "Q00", "Q99"), ("XVIII", "R00", "R99"), ("XIX", "S00", "T98"), ("XX", "V01", "Y98"),
    ("XXI", "Z00", "Z99"), ("XXII", "U00", "U99"),
]

#: Colunas de contagem que os checkpoints do SIH carregam, na ordem de acumulação.
MEDIDAS = ["internacoes", "obitos", "dias_permanencia", "valor_total",
           "aih_continuacao", "dias_permanencia_normal", "valor_normal"]


def capitulo(cid3: str) -> str:
    """Capítulo CID-10 de um código de 3 caracteres. 'N/D' quando não cai em nenhum."""
    for cap, ini, fim in CID10_CAPITULOS:
        if ini <= cid3 <= fim:
            return cap
    return "N/D"


def aplica_metricas_por_episodio(df: pd.DataFrame, casas_permanencia: int = 2) -> pd.DataFrame:
    """Deriva `aih_normal` e as médias por episódio, no lugar.

    Espera as colunas de MEDIDAS. Convenções:

    - `internacoes` permanece sendo toda a produção aprovada (inclui continuação);
    - `mortalidade_pct` usa `internacoes` — o óbito é do episódio, mas a AIH em
      que ele cai é a última da sequência, então dividir por AIH normal
      superestimaria a taxa;
    - `permanencia_media` e `custo_medio` usam `aih_normal`, porque são médias
      POR EPISÓDIO;
    - quando `aih_normal` é 0 (todo o volume daquele recorte é continuação), a
      média por episódio não existe e o resultado é NaN — não 0, não erro.

    O `.where(x > 0)` sem `other` é deliberado: ele zera para NaN e sobe a série
    para float64. Um `.replace(0, pd.NA)` devolveria dtype object com NAType, que
    quebra o `.round()` seguinte com "float() argument must be a string or a real
    number, not 'NAType'".
    """
    df["aih_normal"] = (df["internacoes"] - df["aih_continuacao"]).astype("int64")
    denom = df["aih_normal"].where(df["aih_normal"] > 0)
    df["permanencia_media"] = (df["dias_permanencia_normal"] / denom).round(casas_permanencia)
    df["mortalidade_pct"] = (df["obitos"] / df["internacoes"].where(df["internacoes"] > 0) * 100).round(2)
    df["custo_medio"] = (df["valor_normal"] / denom).round(2)
    return df
