"""O portão de convênios sabe reprovar E sabe aprovar.

Portão que nunca foi visto aprovando é indistinguível de portão quebrado: ele
passaria a reprovar para sempre, inclusive depois de a fonte ficar pronta, e
ninguém notaria. É o espelho de `guarda-nunca-vista-reprovando`, e o mesmo
cuidado de `tests/test_sondagem_srag.py`.

Nada aqui toca a rede: a sondagem é injetada com respostas conhecidas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import sondar_convenios as sc  # noqa: E402

OPENAPI_OK = json.dumps({"paths": {
    "/api-de-dados/convenios": {}, "/api-de-dados/convenios/id": {},
}}).encode()

UM_CONVENIO = json.dumps([{
    "id": 1, "valor": 100000.0, "valorLiberado": 25000.0,
    "convenente": {"cnpjFormatado": "12.345.678/0001-95", "nome": "SANTA CASA"},
    "municipioConvenente": {"codigoIBGE": "355030"},
}]).encode()


def _respostas(mapa: dict[str, tuple[int, bytes]], padrao=(200, UM_CONVENIO)):
    """Substitui `_get` por uma tabela de respostas por trecho de URL."""
    def falso(url: str, chave: str | None = None, timeout: int = 90):
        for trecho, resposta in mapa.items():
            if trecho in url:
                return resposta
        return padrao
    return falso


def test_reprova_sem_chave(monkeypatch, capsys):
    monkeypatch.setattr(sc, "_get", _respostas({"api-docs": (200, OPENAPI_OK)}))
    monkeypatch.setattr(sc, "carregar_env", lambda: {})
    monkeypatch.setattr(sys, "argv", ["sondar_convenios.py"])
    assert sc.main() == 1
    saida = capsys.readouterr().out
    assert "cadastrar-email" in saida, "o portão tem de dizer COMO obter a chave"
    assert sc.VARIAVEL in saida, "e onde gravá-la"


def test_reprova_quando_a_api_deixa_de_declarar_convenios(monkeypatch, capsys):
    """Se a especificação mudar, o coletor quebra — melhor saber pelo portão."""
    vazio = json.dumps({"paths": {"/api-de-dados/despesas": {}}}).encode()
    monkeypatch.setattr(sc, "_get", _respostas({"api-docs": (200, vazio)}))
    monkeypatch.setattr(sc, "carregar_env", lambda: {sc.VARIAVEL: "k"})
    monkeypatch.setattr(sys, "argv", ["sondar_convenios.py"])
    assert sc.main() == 1
    assert "não declara mais endpoint" in capsys.readouterr().out


def test_reprova_quando_o_waf_devolve_html_com_200(monkeypatch, capsys):
    """200 não é sucesso: o portal de download responde 200 com CAPTCHA.

    O mesmo pode acontecer com a API, e status sozinho não distingue.
    """
    monkeypatch.setattr(sc, "_get", _respostas({"api-docs": (200, b"<!DOCTYPE html>")}))
    monkeypatch.setattr(sc, "carregar_env", lambda: {sc.VARIAVEL: "k"})
    monkeypatch.setattr(sys, "argv", ["sondar_convenios.py"])
    assert sc.main() == 1
    assert "não devolveu JSON" in capsys.readouterr().out


def test_reprova_quando_a_chave_e_recusada(monkeypatch, capsys):
    negado = b'{"Erro na API": "Chave de API invalida"}'
    monkeypatch.setattr(sc, "_get", _respostas(
        {"api-docs": (200, OPENAPI_OK)}, padrao=(401, negado)))
    monkeypatch.setattr(sc, "carregar_env", lambda: {sc.VARIAVEL: "errada"})
    monkeypatch.setattr(sys, "argv", ["sondar_convenios.py"])
    assert sc.main() == 1
    assert "respondeu 401" in capsys.readouterr().out


def test_APROVA_quando_a_fonte_serve(monkeypatch, capsys):
    """O caso que importa: com chave válida e API respondendo, sai 0."""
    monkeypatch.setattr(sc, "_get", _respostas({"api-docs": (200, OPENAPI_OK)}))
    monkeypatch.setattr(sc, "carregar_env", lambda: {sc.VARIAVEL: "boa"})
    monkeypatch.setattr(sys, "argv", ["sondar_convenios.py"])
    assert sc.main() == 0, "portão que nunca aprova é portão quebrado"
    saida = capsys.readouterr().out
    assert "apta" in saida
    # E mesmo aprovando, ele não deixa a decisão de grão passar em silêncio.
    assert "estabelecimentos públicos" in saida


def test_a_medicao_extrai_o_cnpj_do_convenente(monkeypatch):
    """A taxa de casamento depende deste campo; se ele mudar de nome, some."""
    monkeypatch.setattr(sc, "_get", _respostas({"api-docs": (200, OPENAPI_OK)}))
    medida = sc.medir_com_chave("boa")
    assert medida["registros_por_pagina"] == 1
    assert medida["cnpjs_distintos_na_amostra"] == 1, (
        "o CNPJ tem de sair de convenente.cnpjFormatado, só dígitos"
    )


def test_o_recorte_e_funcao_10(monkeypatch):
    """Saúde é função 10 no SIAFI. Trocar isso muda a fonte inteira."""
    vistas: list[str] = []

    def espiao(url, chave=None, timeout=90):
        vistas.append(url)
        return (200, OPENAPI_OK) if "api-docs" in url else (200, UM_CONVENIO)

    monkeypatch.setattr(sc, "_get", espiao)
    sc.medir_com_chave("boa")
    assert vistas, "nenhuma consulta foi feita"
    assert all("funcao=10" in u for u in vistas), (
        "toda consulta da sondagem tem de recortar saúde"
    )


@pytest.mark.parametrize("campo", ["cnpjFormatado", "codigoIBGE"])
def test_as_duas_chaves_de_cruzamento_estao_documentadas(campo):
    """As duas rotas de ligação têm de estar escritas no cabeçalho.

    A do CNPJ falha em 92% dos estabelecimentos públicos; a do município cobre
    o país. Quem ler o arquivo precisa encontrar as duas.
    """
    texto = (RAIZ / "scripts" / "sondar_convenios.py").read_text(encoding="utf-8")
    assert campo in texto
