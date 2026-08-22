"""
Consistência entre a metodologia publicada, o servidor MCP e o texto do site.

Motivo de existir: o MCP é a camada que um LLM lê antes de responder, e é vendido
como anti-alucinação. Quando a metodologia mudou de opinião sobre ICSAP — a §19
testou a hipótese "onde falta leito, a eletiva some e a fatia de ICSAP sobe"
contra os leitos do CNES e a REFUTOU na direção e no mecanismo —, o MCP continuou
ensinando a hipótese antiga. Um modelo consumindo essas descrições repetia, com a
autoridade da plataforma, exatamente a explicação causal que a plataforma já havia
descartado. O pacote está publicado no PyPI, então o erro viajava.

Estes testes não checam comportamento: checam que os três canais (metodologia do
site, docstrings do MCP, regras do servidor) não voltam a divergir. São de texto
porque o defeito era de texto.

Nenhum acesso a rede: tudo lê arquivo do repositório.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RAIZ = Path(__file__).resolve().parents[1]
MCP = RAIZ / "mcp_server" / "saudeemdado_mcp" / "__init__.py"
METODOLOGIA = RAIZ / "site" / "app" / "metodologia" / "page.tsx"


@pytest.fixture(scope="module")
def texto_mcp() -> str:
    return MCP.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def texto_metodologia() -> str:
    return METODOLOGIA.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# A conclusão da §19 continua sendo a que o MCP assume
# ---------------------------------------------------------------------------

def test_metodologia_ainda_afirma_direcao_oposta(texto_metodologia: str) -> None:
    """Se a §19 for reescrita, este teste cai e força revisitar o MCP.

    É o pareamento que faltava: o MCP passou a citar a §19 como fonte, então uma
    mudança na §19 sem mudança no MCP recria exatamente o defeito original.
    """
    assert "direção" in texto_metodologia and "oposta" in texto_metodologia, (
        "a §19 não afirma mais que o resultado foi na direção oposta — "
        "revise as descrições de ICSAP no MCP antes de ajustar este teste"
    )
    assert "quase dobra" in texto_metodologia, (
        "sumiu da metodologia a magnitude do efeito de leito local sobre ICSAP; "
        "o MCP cita '+51% a +85%' com base nela"
    )


# ---------------------------------------------------------------------------
# O MCP não pode afirmar fragilidade da APS a partir do %ICSAP
# ---------------------------------------------------------------------------

def test_mcp_nao_traduz_icsap_como_fragilidade_da_aps(texto_mcp: str) -> None:
    """A tradução proibida, na forma afirmativa em que existia."""
    proibidas = [
        "possível fragilidade da atenção primária",
        "sinaliza fragilidade da atenção básica",
        "indica fragilidade da atenção primária",
    ]
    achadas = [p for p in proibidas if p.lower() in texto_mcp.lower()]
    assert not achadas, (
        f"o MCP voltou a traduzir %ICSAP como qualidade da APS: {achadas}. "
        "A §19 mostra associação POSITIVA com leito local (ρ=+0,32); "
        "descreva como sinal que exige comparação com oferta hospitalar."
    )


def test_hipotese_refutada_so_aparece_marcada_como_refutada(texto_mcp: str) -> None:
    """A hipótese antiga pode ser citada — desde que rotulada.

    Citá-la é útil (evita que alguém a reintroduza por não saber que já foi
    testada), mas só acompanhada da refutação. Sem isso, volta a ser doutrina.
    """
    marcas_refutacao = ("refutad", "REFUTADA", "não se sustenta", "direção oposta",
                        "resultado foi na")
    for m in re.finditer(r"eletiva\s+some|fatia de ICSAP sobe", texto_mcp, re.IGNORECASE):
        janela = texto_mcp[max(0, m.start() - 700):m.end() + 700].lower()
        assert any(marca.lower() in janela for marca in marcas_refutacao), (
            f"a hipótese refutada aparece em {MCP.name} (offset {m.start()}) sem "
            "nenhuma marca de refutação por perto — um LLM lerá como verdade vigente"
        )


def test_ferramentas_icsap_mencionam_oferta_hospitalar(texto_mcp: str) -> None:
    """Toda superfície do MCP que expõe %ICSAP tem de trazer a ressalva de oferta."""
    for ferramenta in ("internacoes_evitaveis_icsap", "icsap_distancia_dos_pares"):
        i = texto_mcp.find(f"def {ferramenta}(")
        assert i != -1, f"ferramenta {ferramenta} sumiu do MCP"
        # A docstring vem logo após a assinatura; 2.500 chars cobrem as duas com folga.
        bloco = texto_mcp[i:i + 2500].lower()
        assert "leito" in bloco, (
            f"{ferramenta} não menciona leitos/oferta hospitalar na descrição — "
            "é a ressalva que impede a leitura errada do indicador"
        )


def test_regras_do_servidor_carregam_a_ressalva_icsap(texto_mcp: str) -> None:
    """As `instructions` são o que o modelo lê antes de qualquer ferramenta.

    A ressalva precisa estar ali, não só nas docstrings: um cliente pode listar
    ferramentas sem ler todas as descrições, mas as instruções vão sempre no
    contexto.
    """
    i = texto_mcp.find("instructions=(")
    fim = texto_mcp.find("website_url", i) if texto_mcp.find("website_url", i) > i else i + 4000
    bloco = texto_mcp[i:max(fim, i + 4000)].lower()
    assert "icsap" in bloco, "as instructions do servidor não citam ICSAP"
    assert "leito" in bloco, (
        "as instructions do servidor não citam a dependência do %ICSAP com a oferta "
        "de leitos — a regra mais fácil de um modelo violar"
    )


# ---------------------------------------------------------------------------
# O sinal do copiloto entrega a oferta junto com o número
# ---------------------------------------------------------------------------

def test_sinal_icsap_do_copiloto_busca_leitos(texto_mcp: str) -> None:
    """`detectar_anomalias` tem de consultar a oferta local, não só o %ICSAP.

    Sem isso a ressalva vira texto genérico; com isso o gestor recebe o número e
    o fator de confundimento na mesma linha.
    """
    i = texto_mcp.find("def detectar_anomalias(")
    assert i != -1, "detectar_anomalias sumiu do MCP"
    bloco = texto_mcp[i:i + 4000]
    assert "mart_leitos_municipio" in bloco, (
        "detectar_anomalias não consulta mart_leitos_municipio; o sinal de ICSAP "
        "voltaria a ser publicado sem o contexto de oferta"
    )
    assert "leitos_sus" in bloco, (
        "o achado de ICSAP não devolve o campo leitos_sus para o cliente"
    )
