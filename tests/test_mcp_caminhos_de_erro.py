"""Os caminhos de ERRO do servidor MCP, exercitados.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
A varredura de guardas de 2026-09-02 procurava `raise` e `sys.exit`. O servidor
MCP não usa nenhum dos dois: quando não tem resposta, ele **retorna**
`{"erro": ...}` — que é o desenho certo para uma ferramenta que um modelo chama,
porque derrubar o servidor apagaria a conversa inteira em vez de informar o
modelo.

Consequência: a varredura declarou "zero guardas no mcp_server" e estava errada.
Havia quatro, e nenhuma tinha teste. O ponto cego era do detector, não do código.

Isso importa mais aqui do que num script interno. O pacote está publicado no
PyPI, e o consumidor é um LLM: se um caminho de erro quebrar, o modelo não recebe
uma exceção que alguém vá ler no log — recebe lixo, e responde com a autoridade
da plataforma em cima do lixo. `tests/test_mcp_consistencia.py` já guarda o TEXTO
das descrições pelo mesmo motivo; estes guardam o comportamento.

Nenhum teste acessa rede: `sd._get` e `requests.get` são substituídos.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "mcp_server"))

import saudeemdado_mcp as mcp  # noqa: E402

pytestmark = pytest.mark.unit


class _Resposta:
    def __init__(self, status=200, corpo=None):
        self.status_code = status
        self._corpo = corpo if corpo is not None else []

    def json(self):
        return self._corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


# ---------------------------------------------------------------------------
# 1. município fora da base de estratos — o caso que mais dispara na prática
# ---------------------------------------------------------------------------
# `dim_cluster_municipio` cobre ~1.700 dos 5.570 municípios. Ou seja: para a
# MAIORIA das consultas possíveis, este é o caminho normal, não a exceção. Se ele
# quebrasse, a ferramenta falharia em dois de cada três municípios do país.

def test_municipio_fora_dos_estratos_devolve_erro_explicativo(monkeypatch):
    monkeypatch.setattr(mcp.sd, "_get", lambda *a, **k: [])
    r = mcp.comparar_com_pares("999999")
    assert "erro" in r
    assert "fora da base de estratos" in r["erro"]


def test_o_erro_aponta_a_ferramenta_alternativa(monkeypatch):
    """Erro que só diz "não tenho" faz o modelo desistir da pergunta.

    Dizendo qual ferramenta serve, o modelo continua a conversa em vez de
    responder ao usuário que o dado não existe — que seria falso.
    """
    monkeypatch.setattr(mcp.sd, "_get", lambda *a, **k: [])
    assert "municipios_indicadores" in mcp.comparar_com_pares("999999")["erro"]


def test_municipio_coberto_nao_cai_no_caminho_de_erro(monkeypatch):
    """A guarda tem de deixar passar o caso bom, senão a ferramenta é inútil."""
    alvo = {"municipio_cod": "353730", "municipio_nome": "Penápolis",
            "uf_sigla": "SP", "regiao": "Sudeste", "cluster": 21,
            "estrato_cod": "M3V1I3", "perfil": "mortalidade alta",
            "taxa_padronizada_100k": 777.0, "ivs_score": 26.8,
            "internacoes_100k": 9241.0}
    monkeypatch.setattr(mcp.sd, "_get", lambda *a, **k: [alvo, dict(alvo, municipio_cod="350280")])
    assert "erro" not in mcp.comparar_com_pares("353730")


# ---------------------------------------------------------------------------
# 2. UF sem dado de dengue
# ---------------------------------------------------------------------------

def test_uf_sem_dengue_devolve_erro_nomeando_a_uf(monkeypatch):
    monkeypatch.setattr(mcp.sd, "_get", lambda *a, **k: [])
    r = mcp.canal_endemico_dengue("ZZ")
    assert "erro" in r and "ZZ" in r["erro"]


def test_uf_em_minusculas_e_normalizada_antes_de_reclamar(monkeypatch):
    """A mensagem devolve a UF em maiúsculas, como a consulta a enviou.

    Devolver o que o usuário digitou faria o modelo repetir 'sp' para alguém que
    depois não acha nada procurando por 'SP'.
    """
    monkeypatch.setattr(mcp.sd, "_get", lambda *a, **k: [])
    assert "SP" in mcp.canal_endemico_dengue("sp")["erro"]


# ---------------------------------------------------------------------------
# 3. boletim: índice vazio e edição inexistente são erros DIFERENTES
# ---------------------------------------------------------------------------
# Confundir os dois faria o modelo dizer "essa edição não existe" quando na
# verdade nenhuma existe ainda — e o usuário procuraria um erro de digitação que
# não está lá.

def test_indice_vazio_diz_que_nada_foi_publicado(monkeypatch):
    monkeypatch.setattr(mcp.requests, "get", lambda *a, **k: _Resposta(corpo=[]))
    r = mcp.boletim_semanal()
    assert "erro" in r and "nenhuma edição publicada" in r["erro"]


def test_edicao_inexistente_lista_as_disponiveis(monkeypatch):
    """Sem a lista, o modelo chuta a próxima edição e erra de novo."""
    def _get(url, **k):
        if url.endswith("index.json"):
            return _Resposta(corpo=[{"edicao": "2026-se30"}, {"edicao": "2026-se29"}])
        return _Resposta(status=404)

    monkeypatch.setattr(mcp.requests, "get", _get)
    r = mcp.boletim_semanal("2026-se99")
    assert "não encontrada" in r["erro"]
    assert r["disponiveis"] == ["2026-se30", "2026-se29"]


def test_edicao_existente_volta_com_permalink(monkeypatch):
    """O caminho bom: sem erro, com o link, e agora com a procedência ao lado.

    A partir da 0.6.0 as ferramentas de DADO devolvem
    `{"dados": ..., "procedencia": ...}` — a citação passou a viajar com o
    número, porque os marts derivados estão sob CC BY 4.0 e nada no caminho do
    dado dizia como creditar. O caminho de ERRO seguiu sem envelope (ver os
    testes acima): citação em cima de falha é procedência de dado que não
    existe.
    """
    def _get(url, **k):
        if url.endswith("index.json"):
            return _Resposta(corpo=[{"edicao": "2026-se30"}])
        return _Resposta(corpo={"titulo": "boletim"})

    monkeypatch.setattr(mcp.requests, "get", _get)
    r = mcp.boletim_semanal()
    assert "erro" not in r
    assert set(r) == {"dados", "procedencia"}
    assert "como_citar" in r["procedencia"]

    b = r["dados"]
    assert b["permalink"].endswith("?e=2026-se30")
    assert b["edicoes_disponiveis"] == ["2026-se30"]
