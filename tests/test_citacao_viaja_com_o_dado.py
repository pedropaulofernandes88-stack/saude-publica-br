"""
A citação viaja com o dado, e a frase é uma só.

MOTIVO DE EXISTIR
-----------------
Os marts derivados estão sob **CC BY 4.0**, em que atribuição é condição da
licença — e, apesar disso, nada no caminho do dado dizia como citar. As 19
ferramentas do MCP devolviam `list[dict]` cru; só a vigésima trazia licença e
DOI, e um assistente raramente a chama sozinho. Quem copiava a resposta ficava
com números sem procedência, sem má-fé nenhuma: a superfície não oferecia a
citação.

A frase, por sua vez, existia duas vezes — escrita à mão em `/dados/` e
estruturada em `CITATION.cff`, que é o que o GitHub e os gerenciadores de
referência leem. Duas cópias de uma citação divergem em silêncio, e a
divergência é cara: DOI ou nome de autor errados numa citação copiada por
terceiro não voltam. Foi assim que `CITATION.cff` ficou com
`given-names: Pedro` enquanto o autor assina Pedro Paulo.

Estes testes prendem as três pontas: o CFF é a fonte, `_citacao.py` deriva, e
nem o MCP nem o site podem divergir dela.

Nenhum acesso a rede: tudo lê arquivo do repositório.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RAIZ = Path(__file__).resolve().parents[1]
MCP = RAIZ / "mcp_server" / "saudeemdado_mcp" / "__init__.py"
DADOS = RAIZ / "site" / "app" / "dados" / "page.tsx"
sys.path.insert(0, str(RAIZ / "scripts"))

from _citacao import LICENCA, como_citar, dados_da_citacao, linhas_meta  # noqa: E402


@pytest.fixture(scope="module")
def texto_mcp() -> str:
    return MCP.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# A frase derivada do CITATION.cff
# ---------------------------------------------------------------------------
def test_citacao_traz_autor_titulo_doi_e_a_condicao_da_licenca():
    frase = como_citar()
    d = dados_da_citacao()
    assert d["doi"] in frase, "citação sem DOI não permite recuperar a obra"
    assert d["url"] in frase
    assert "CC BY 4.0" in frase, "a licença TEM nome; omiti-lo transforma condição em pedido"
    assert "atribuição" in frase.lower()
    assert "\n" not in frase, "a frase viaja dentro de JSON e CSV — uma linha só"


def test_o_autor_sai_do_cff_com_todas_as_iniciais():
    """`given-names: Pedro` produzia "Fernandes, P." e o autor assina "P. P.".

    O campo é o que o GitHub e o Zenodo leem; errado ali, ele erra em toda
    citação automática gerada por terceiro.
    """
    assert dados_da_citacao()["autor"] == "Fernandes, P. P."


def test_linhas_meta_traz_as_tres_chaves_que_o_dado_carrega():
    chaves = dict(linhas_meta())
    assert set(chaves) == {"como_citar", "doi", "licenca"}
    assert chaves["licenca"] == LICENCA
    assert "CC BY 4.0" in chaves["licenca"]


# ---------------------------------------------------------------------------
# O MCP: toda ferramenta de DADO envelopa a procedência
# ---------------------------------------------------------------------------
#: A única ferramenta que não leva envelope, e por quê: ela JÁ É a procedência,
#: e envelopá-la produziria `{"dados": {...metadados...}, "procedencia": {...}}`
#: com a mesma informação nos dois níveis.
SEM_ENVELOPE = {"metadados_dataset"}


def _ferramentas(texto: str) -> list[tuple[str, bool]]:
    """(nome, tem `@procedencia`) para cada `@mcp.tool()` do arquivo."""
    fora = []
    for m in re.finditer(r"@mcp\.tool\(\)\n(@procedencia\([^)]*\)\n)?def (\w+)\(", texto):
        fora.append((m.group(2), m.group(1) is not None))
    return fora


def test_o_arquivo_tem_as_ferramentas_esperadas(texto_mcp: str):
    """Se a varredura parar de casar, os testes abaixo aprovam por vacuidade."""
    assert len(_ferramentas(texto_mcp)) >= 19, "a varredura de @mcp.tool() deixou de casar"


def test_toda_ferramenta_de_dado_devolve_procedencia(texto_mcp: str):
    nuas = [n for n, tem in _ferramentas(texto_mcp) if not tem and n not in SEM_ENVELOPE]
    assert not nuas, (
        "ferramenta de dado sem `@procedencia`: ela devolve números sem dizer de onde "
        f"vieram nem como citar — {', '.join(nuas)}. Se for exceção legítima, "
        "acrescente a SEM_ENVELOPE com o motivo."
    )


def test_a_guarda_reprovaria_uma_ferramenta_nua():
    """Vista reprovando: sem isto, a varredura poderia estar sempre vazia."""
    falso = '@mcp.tool()\ndef ferramenta_nova(uf: str = "") -> list[dict]:\n'
    assert _ferramentas(falso) == [("ferramenta_nova", False)]


def test_a_procedencia_carrega_licenca_e_como_citar(texto_mcp: str):
    trecho = texto_mcp[texto_mcp.index("def _procedencia("):texto_mcp.index("def procedencia(")]
    for campo in ("fonte_primaria", "licenca", "como_citar", "dado_gerado_em"):
        assert f'"{campo}"' in trecho, f"a procedência deixou de trazer {campo}"


def test_procedencia_degrada_sem_derrubar_a_consulta(texto_mcp: str):
    """Rede fora não pode transformar uma consulta que funcionava em erro."""
    trecho = texto_mcp[texto_mcp.index("def _meta("):texto_mcp.index("def _procedencia(")]
    assert "except Exception" in trecho and "_META_CACHE = {}" in trecho


# ---------------------------------------------------------------------------
# O site não pode ter uma terceira versão da frase
# ---------------------------------------------------------------------------
def test_o_doi_do_site_e_o_do_cff():
    doi = dados_da_citacao()["doi"]
    texto = DADOS.read_text(encoding="utf-8")
    assert doi in texto, (
        f"a página /dados/ não cita o DOI do CITATION.cff ({doi}) — são duas citações, "
        "e a que os gerenciadores de referência leem é a do CFF"
    )


def test_o_site_nomeia_a_licenca_dos_marts():
    texto = DADOS.read_text(encoding="utf-8")
    assert "CC BY 4.0" in texto
