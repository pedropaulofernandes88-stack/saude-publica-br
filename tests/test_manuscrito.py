"""As tabelas do manuscrito continuam sendo as que os CSVs dizem.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O manuscrito trazia doze tabelas em Markdown copiadas à mão de
`artigo/tabelas/*.csv`. Enquanto o dado não mudava, a cópia parecia inofensiva.

Em 2026-09-02, 2024 foi recoletado do `.dbc` do DataSUS — 105.669 óbitos que o
CSV do OpenDataSUS não trazia, com 63% de dezembro ausente. **As doze tabelas
passaram a divergir de uma vez, e nenhuma avisou.** Um artigo cujas tabelas
descrevem um dado que não existe mais é pior que um artigo sem tabelas.

`artigo/sincronizar_tabelas.py` passou a regerá-las do CSV, e este teste
transforma a sincronia em regressão: quem regerar os CSVs sem sincronizar o
manuscrito vê vermelho aqui, não numa revisão por pares.

O teste é rápido e não toca rede nem banco: compara texto com CSV.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MANUSCRITO = RAIZ / "artigo" / "manuscrito.md"
SINCRONIZADOR = RAIZ / "artigo" / "sincronizar_tabelas.py"

pytestmark = pytest.mark.unit


def _ocorrencias(texto: str, alvo: str) -> list[int]:
    fora, i = [], texto.find(alvo)
    while i != -1:
        fora.append(i)
        i = texto.find(alvo, i + 1)
    return fora


@pytest.mark.skipif(not MANUSCRITO.exists(), reason="manuscrito ausente")
def test_tabelas_do_manuscrito_batem_com_os_csvs() -> None:
    r = subprocess.run([sys.executable, str(SINCRONIZADOR), "--conferir"],
                       cwd=RAIZ, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (
        "alguma tabela do manuscrito divergiu do CSV que a gera.\n"
        + (r.stdout or "") + (r.stderr or "")
    )


@pytest.mark.skipif(not MANUSCRITO.exists(), reason="manuscrito ausente")
def test_o_total_de_obitos_e_o_mesmo_no_texto_e_na_tabela() -> None:
    """O número mais citado do artigo aparece na prosa E na Tabela 1.

    Sincronizar a tabela não sincroniza o parágrafo: o total de óbitos é escrito
    à mão em três lugares do texto corrido. Foi um deles que ficou em
    14.378.827 depois da recoleta.
    """
    texto = MANUSCRITO.read_text(encoding="utf-8")
    csv = (RAIZ / "artigo" / "tabelas" / "tabela_1_base.csv").read_text(encoding="utf-8")
    linha = next(x for x in csv.splitlines() if x.startswith("Óbitos não fetais"))
    total = linha.split(",")[1].strip()
    assert total in texto, f"a Tabela 1 diz {total} óbitos e a prosa não repete esse número"
    assert "14.378.827" not in texto, (
        "o total da coleta anterior (14.378.827) ainda aparece no texto. "
        "Ele não tem uso legítimo: era o total com 2024 incompleto."
    )

    # 1.426.346 — o 2024 do CSV — PODE aparecer, e aparece de propósito na §2.2,
    # que explica por que a fonte mudou. O que não pode é aparecer como se fosse
    # o dado corrente. A regra é de contexto: toda ocorrência tem de estar perto
    # da palavra que a qualifica.
    for pos in _ocorrencias(texto, "1.426.346"):
        janela = texto[max(0, pos - 400):pos + 400]
        assert "CSV" in janela, (
            "1.426.346 (o 2024 incompleto do CSV) aparece sem o contexto que o "
            f"qualifica, perto de: …{texto[max(0, pos - 120):pos + 120]}…"
        )
