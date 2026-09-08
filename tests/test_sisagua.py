"""
O pipeline do SISAGUA: ausência não pode virar zero, e falha não pode virar mart.

A camada ambiental é onde a confusão custa mais caro. Município que não analisa
a água aparece na fonte como ausência — e ausência de análise é a FALTA da
prova, não a prova de que está tudo bem. Estes testes fixam essa distinção nos
três pontos em que ela pode se perder: na agregação, nas guardas, e na coleta.

Executar: .venv311/Scripts/python -m pytest tests/test_sisagua.py
"""
from __future__ import annotations

import pytest

from scripts import _sisagua as sis
from scripts._sisagua import Fatia, Relatorio
from scripts.pipeline_sisagua import agregar, cobertura, guardas


def reg(**kw):
    """Um registro do SISAGUA com os campos que a agregação lê."""
    base = {
        "codigo_ibge": "430730", "municipio": "ERVAL SECO", "uf": "RS",
        "regiao_geografica": "SUL", "ano_de_referencia": 2024,
        "mes_de_referencia": 4, "parametro": "Escherichia coli",
        "campo": "Número de amostras analisadas", "valor": 10.0,
        "tipo_da_forma_de_abastecimento": "SAC",
    }
    base.update(kw)
    return base


# ── agregação ──────────────────────────────────────────────────────────────

def test_volume_e_regularidade_sao_medidas_diferentes():
    """300 amostras num mês não é o mesmo que 12 meses de 25."""
    campanha = [reg(mes_de_referencia=4, valor=300.0)]
    regular = [reg(mes_de_referencia=m, valor=25.0) for m in range(1, 13)]

    a = agregar(campanha).iloc[0]
    b = agregar(regular).iloc[0]
    assert a["amostras_analisadas"] == 300 and a["meses_com_analise"] == 1
    assert b["amostras_analisadas"] == 300 and b["meses_com_analise"] == 12


def test_mes_sem_amostra_nao_conta_como_mes_com_analise():
    """Linha com zero amostras é registro de que NÃO se analisou naquele mês."""
    d = agregar([
        reg(mes_de_referencia=1, valor=10.0),
        reg(mes_de_referencia=2, valor=0.0),
    ]).iloc[0]
    assert d["amostras_analisadas"] == 10
    assert d["meses_com_analise"] == 1, "mês com zero amostras não é mês analisado"


def test_municipio_ausente_nao_vira_linha_zerada():
    """O mart não inventa linha para quem a fonte não trouxe.

    É a regra central: ausência fica ausente, e quem lê o mart descobre pela
    cobertura, não por um zero que pareceria 'analisou e não achou nada'.
    """
    df = agregar([reg(codigo_ibge="430730")])
    assert set(df["municipio_cod"]) == {"430730"}
    assert len(df) == 1


def test_campo_de_presenca_nao_e_confundido_com_analisadas():
    """Os dois textos começam parecido; comparar por prefixo somaria errado."""
    df = agregar([
        reg(campo="Número de amostras analisadas", valor=100.0),
        reg(campo="N de amostras com presença para Escherichia coli", valor=3.0),
    ])
    d = df.iloc[0]
    assert d["amostras_analisadas"] == 100
    assert d["escherichia_coli"] == 3


def test_presenca_ausente_fica_nula_e_nao_zero():
    """Não medir presença e medir zero presença são coisas diferentes."""
    d = agregar([reg(campo="Número de amostras analisadas", valor=50.0)]).iloc[0]
    assert d["amostras_analisadas"] == 50
    assert d["escherichia_coli"] is None or pytest.approx(d["escherichia_coli"], nan_ok=True) != 0


def test_valor_nao_numerico_nao_vira_zero():
    d = agregar([
        reg(valor="indisponível"),
        reg(valor=7.0, mes_de_referencia=5),
    ]).iloc[0]
    assert d["amostras_analisadas"] == 7
    assert d["meses_com_analise"] == 1


def test_agrega_por_municipio_ano_e_parametro():
    df = agregar([
        reg(parametro="Escherichia coli", valor=10.0),
        reg(parametro="Turbidez (uT)", valor=20.0),
        reg(parametro="Escherichia coli", ano_de_referencia=2023, valor=5.0),
    ])
    assert len(df) == 3
    assert set(df["parametro"]) == {"Escherichia coli", "Turbidez (uT)"}


def test_registro_sem_chave_e_descartado_sem_derrubar():
    df = agregar([reg(codigo_ibge=None), reg(parametro=None), reg(valor=9.0, mes_de_referencia=6)])
    assert len(df) == 1
    assert df.iloc[0]["amostras_analisadas"] == 9


# ── guardas ────────────────────────────────────────────────────────────────

def cob_ok():
    return cobertura(Relatorio(fatias=[Fatia("RS", 2024, [reg()], 1, False)]))


def test_guardas_passam_num_recorte_sao():
    """A metade que nenhuma guarda deste projeto pode ficar sem: dizer SIM."""
    guardas(agregar([reg(valor=10.0)]), cob_ok())


def test_guarda_reprova_mais_de_doze_meses():
    df = agregar([reg(mes_de_referencia=m, valor=1.0) for m in range(1, 13)])
    df.loc[0, "meses_com_analise"] = 13
    with pytest.raises(SystemExit, match="12 meses"):
        guardas(df, cob_ok())


def test_guarda_reprova_presenca_maior_que_analisado():
    """Razão impossível: mais amostras com E. coli do que amostras analisadas."""
    df = agregar([
        reg(campo="Número de amostras analisadas", valor=10.0),
        reg(campo="N de amostras com presença para Escherichia coli", valor=99.0),
    ])
    with pytest.raises(SystemExit, match="amostras analisadas"):
        guardas(df, cob_ok())


def test_guarda_reprova_amostras_negativas():
    df = agregar([reg(valor=5.0)])
    df.loc[0, "amostras_analisadas"] = -1
    with pytest.raises(SystemExit, match="negativas"):
        guardas(df, cob_ok())


def test_guarda_reprova_agregacao_vazia():
    import pandas as pd
    with pytest.raises(SystemExit, match="agregação vazia"):
        guardas(pd.DataFrame(), cob_ok())


# ── cobertura ──────────────────────────────────────────────────────────────

def test_cobertura_separa_vazio_de_fato_de_coletado():
    """É este arquivo que permite ler a ausência do mart sem adivinhar."""
    rel = Relatorio(fatias=[
        Fatia("RS", 2024, [reg()], 1, False),
        Fatia("AC", 2024, [], 1, True),
    ])
    c = cobertura(rel)
    assert len(c) == 2
    ac = c[c["uf_sigla"] == "AC"].iloc[0]
    assert ac["vazia_de_fato"] and ac["registros_brutos"] == 0
    rs = c[c["uf_sigla"] == "RS"].iloc[0]
    assert not rs["vazia_de_fato"]


def test_relatorio_lista_as_fatias_vazias():
    rel = Relatorio(fatias=[
        Fatia("RS", 2024, [reg()], 1, False),
        Fatia("AC", 2024, [], 1, True),
        Fatia("AP", 2023, [], 1, True),
    ])
    assert rel.vazias == [("AC", 2024), ("AP", 2023)]
    assert rel.registros == 1


# ── cache por fatia: retomar sem recomeçar, e sem afrouxar a guarda ─────────
#
# A coleta aborta inteira quando uma fatia falha, e isso está certo: fatia que
# falha não pode virar mart incompleto. O problema era outro — não havia
# persistência, então um 502 na fatia 1 de 162 jogava fora as outras 161 que já
# tinham vindo. Foi o que aconteceu em 2026-09-08, em AC/2020, offset 4000.
#
# O cache guarda SÓ fatia completa. A invariante que o sustenta: `coletar_fatia`
# grava depois do laço de paginação, e `_get` levanta no meio — então recorte
# parcial nunca chega à gravação.

import gzip  # noqa: E402


def _fatia(uf="AC", ano=2020, n=3):
    return sis.Fatia(uf=uf, ano=ano, registros=[{"i": i} for i in range(n)],
                     paginas=1, vazia_de_fato=not n)


def test_cache_ida_e_volta(tmp_path, monkeypatch):
    monkeypatch.setattr(sis, "CACHE", tmp_path)
    sis.gravar_cache("endp", _fatia())
    lida = sis.ler_cache("endp", "AC", 2020)
    assert lida is not None
    assert [r["i"] for r in lida.registros] == [0, 1, 2]
    assert lida.paginas == 1 and lida.vazia_de_fato is False


def test_fatia_vazia_de_fato_sobrevive_ao_cache(tmp_path, monkeypatch):
    """Vazio verificado é resultado, não ausência — e tem de voltar como vazio."""
    monkeypatch.setattr(sis, "CACHE", tmp_path)
    sis.gravar_cache("endp", _fatia(n=0))
    lida = sis.ler_cache("endp", "AC", 2020)
    assert lida.vazia_de_fato is True and lida.registros == []


def test_cache_ausente_devolve_none(tmp_path, monkeypatch):
    monkeypatch.setattr(sis, "CACHE", tmp_path)
    assert sis.ler_cache("endp", "ZZ", 1999) is None


def test_cache_corrompido_e_tratado_como_ausente(tmp_path, monkeypatch):
    """Arquivo truncado por interrupção não pode passar por fatia completa."""
    monkeypatch.setattr(sis, "CACHE", tmp_path)
    alvo = sis._caminho_cache("endp", "AC", 2020)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(gzip.compress(b'{"registros": [1, 2'))  # JSON cortado
    assert sis.ler_cache("endp", "AC", 2020) is None


def test_fatia_interrompida_no_meio_nao_deixa_cache(tmp_path, monkeypatch):
    """A invariante central: erro na paginação levanta ANTES de gravar."""
    monkeypatch.setattr(sis, "CACHE", tmp_path)
    chamadas = {"n": 0}

    def falha_na_segunda(endpoint, params):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return [{"i": i} for i in range(sis.PAGINA)]   # página cheia: continua
        raise sis.FalhaDeColeta("502 no meio da paginação")

    monkeypatch.setattr(sis, "_get", falha_na_segunda)
    with pytest.raises(sis.FalhaDeColeta):
        sis.coletar_fatia("endp", "AC", 2020, quieto=True)
    assert not sis._caminho_cache("endp", "AC", 2020).exists(), (
        "fatia interrompida foi gravada — a próxima execução a leria como completa")


def test_cache_evita_a_segunda_ida_a_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(sis, "CACHE", tmp_path)
    idas = {"n": 0}

    def uma_pagina(endpoint, params):
        idas["n"] += 1
        return [{"i": 1}]

    monkeypatch.setattr(sis, "_get", uma_pagina)
    sis.coletar_fatia("endp", "AC", 2020, quieto=True)
    sis.coletar_fatia("endp", "AC", 2020, quieto=True)
    assert idas["n"] == 1, "a segunda chamada foi à rede apesar do cache"


def test_usar_cache_falso_ignora_o_disco(tmp_path, monkeypatch):
    """Quem suspeita do cache tem como refazer sem apagar arquivo."""
    monkeypatch.setattr(sis, "CACHE", tmp_path)
    sis.gravar_cache("endp", _fatia(n=99))
    monkeypatch.setattr(sis, "_get", lambda e, p: [{"i": 1}])
    f = sis.coletar_fatia("endp", "AC", 2020, quieto=True, usar_cache=False)
    assert len(f.registros) == 1


def test_cache_de_municipio_nao_sobrescreve_o_vizinho(tmp_path, monkeypatch):
    """Dois municípios da MESMA UF não podem cair no mesmo arquivo.

    Foi o que aconteceu em 2026-09-08: `gravar_cache` usava `f.uf`, então os 22
    municípios do Acre gravavam todos em AC_0.json.gz. Cinquenta coletados
    viraram três arquivos — e a execução seguinte leria o último como se fosse a
    fatia de cada um deles.
    """
    monkeypatch.setattr(sis, "CACHE", tmp_path)
    a = sis.Fatia(uf="AC", ano=0, registros=[{"x": 1}], paginas=1,
                  vazia_de_fato=False, municipio="120001")
    b = sis.Fatia(uf="AC", ano=0, registros=[{"x": 2}, {"x": 3}], paginas=1,
                  vazia_de_fato=False, municipio="120005")
    sis.gravar_cache("endp", a)
    sis.gravar_cache("endp", b)
    assert len(sis.ler_cache("endp", "120001", 0).registros) == 1
    assert len(sis.ler_cache("endp", "120005", 0).registros) == 2
    assert sis.municipios_em_cache("endp") == {"120001", "120005"}
