"""
Sífilis do SINAN: código com espaço é outro código, e ausência não é zero.

Dois defeitos que a fonte serve de bandeja. O SIFA traz `' 1'` ao lado de `'1'`
em 2,5% dos registros — comparar sem `strip()` cria uma categoria fantasma. E o
SIFA só existe a partir de 2010: preencher 2007–2009 com zero publicaria
"nenhum caso de sífilis adquirida" onde o certo é "não há arquivo".

Executar: .venv311/Scripts/python -m pytest tests/test_sinan_sifilis.py
"""
from __future__ import annotations

import datetime as dt
from collections import Counter

import pandas as pd
import pytest

from scripts.pipeline_sinan_sifilis import (
    COLUNAS_CONGENITA,
    anotar_cobertura,
    meses_do_relatorio,
    _cod,
    _municipio,
    agregar,
    combinar,
    derivar,
    guardas,
)


def congenito(**kw):
    base = {"ID_MN_RESI": "431630", "DT_NOTIFIC": dt.date(2023, 5, 1),
            "ANT_PRE_NA": "1", "ANTSIFIL_N": "1", "TRA_ESQUEM": "1",
            "ANT_TRATAD": "1", "EVOLUCAO": "1"}
    base.update(kw)
    return base


def simples(**kw):
    base = {"ID_MN_RESI": "431630", "DT_NOTIFIC": dt.date(2023, 5, 1)}
    base.update(kw)
    return base


def so(registros, agravo="congenita", ano=2023):
    df, _ = agregar(registros, agravo, ano)
    return df.iloc[0]


TODOS = {"adquirida": {2023}, "gestante": {2023}, "congenita": {2023}}


def montar(registros_por_agravo, coletados=None, natalidade=None):
    partes = [agregar(regs, ag, 2023)[0] for ag, regs in registros_por_agravo.items()]
    return derivar(combinar(partes, coletados or TODOS), natalidade)


# ── a armadilha do espaço ──────────────────────────────────────────────────

def test_codigo_com_espaco_e_o_mesmo_codigo():
    """`' 1'` aparece 6.147 vezes em SIFABR23 ao lado de `'1'`."""
    assert _cod(" 1") == "1"
    assert _cod("1 ") == "1"
    assert _cod(None) == ""


def test_prenatal_com_espaco_nao_vira_categoria_fantasma():
    d = so([congenito(ANT_PRE_NA=" 1"), congenito(ANT_PRE_NA="1")])
    assert d["congenita_mae_com_prenatal"] == 2
    assert d["congenita_prenatal_ignorado"] == 0


# ── ausência não é zero ────────────────────────────────────────────────────

def test_ano_sem_arquivo_do_agravo_fica_nulo_e_nao_zero():
    """O SIFA começa em 2010; 2007–2009 não têm zero caso, têm zero arquivo."""
    partes = [agregar([simples()], "gestante", 2023)[0]]
    df = combinar(partes, {"adquirida": set(), "gestante": {2023}, "congenita": set()})
    assert pd.isna(df.iloc[0]["casos_adquirida"]), "sem arquivo tem de ser NA"
    assert pd.isna(df.iloc[0]["casos_congenita"])
    assert df.iloc[0]["casos_gestante"] == 1


def test_municipio_sem_o_agravo_num_ano_coletado_e_zero_de_verdade():
    """Coletado o arquivo nacional, ausência do município ali é zero real."""
    partes = [agregar([simples(ID_MN_RESI="431630")], "gestante", 2023)[0],
              agregar([congenito(ID_MN_RESI="355030")], "congenita", 2023)[0]]
    df = combinar(partes, {"adquirida": set(), "gestante": {2023}, "congenita": {2023}})
    linha = df[df["municipio_cod"] == "431630"].iloc[0]
    assert linha["casos_congenita"] == 0, "arquivo coletado e município ausente = zero"


def test_taxa_e_nula_sem_denominador_e_nao_zero():
    df = montar({"congenita": [congenito()]}, natalidade=None)
    assert pd.isna(df.iloc[0]["taxa_congenita_por_mil_nv"])


def test_taxa_por_mil_nascidos_vivos():
    nv = pd.DataFrame({"municipio_cod": ["431630"], "ano": [2023], "nascidos": [2000]})
    df = montar({"congenita": [congenito(), congenito()]}, natalidade=nv)
    assert df.iloc[0]["taxa_congenita_por_mil_nv"] == 1.0


def test_razao_e_nula_quando_nao_ha_gestante_notificada():
    """Congênito sem gestacional é falha de notificação, não razão infinita."""
    df = montar({"congenita": [congenito()], "gestante": []},
                coletados={"adquirida": set(), "gestante": {2023}, "congenita": {2023}})
    assert pd.isna(df.iloc[0]["congenita_por_100_gestante"])


# ── leitura dos campos da mãe ──────────────────────────────────────────────

def test_as_tres_categorias_de_prenatal_sao_exaustivas():
    d = so([congenito(ANT_PRE_NA="1"), congenito(ANT_PRE_NA="2"),
            congenito(ANT_PRE_NA="9"), congenito(ANT_PRE_NA="")])
    assert d["congenita_mae_com_prenatal"] == 1
    assert d["congenita_mae_sem_prenatal"] == 1
    assert d["congenita_prenatal_ignorado"] == 2, "vazio é ignorado, não 'sem pré-natal'"


def test_tratamento_materno_separa_inadequado_de_nao_realizado():
    """Inadequado e não realizado são falhas diferentes e não podem se somar."""
    d = so([congenito(TRA_ESQUEM="1"), congenito(TRA_ESQUEM="2"),
            congenito(TRA_ESQUEM="2"), congenito(TRA_ESQUEM="3"),
            congenito(TRA_ESQUEM="9")])
    assert d["congenita_trat_materno_adequado"] == 1
    assert d["congenita_trat_materno_inadequado"] == 2
    assert d["congenita_trat_materno_nao_realizado"] == 1


def test_desfecho_usa_os_codigos_do_dicionario_oficial():
    """EVOLUCAO: 1 vivo · 2 óbito por sífilis · 3 outras causas · 4 aborto · 5 natimorto."""
    d = so([congenito(EVOLUCAO="1"), congenito(EVOLUCAO="2"), congenito(EVOLUCAO="3"),
            congenito(EVOLUCAO="4"), congenito(EVOLUCAO="5")])
    assert d["congenita_obito"] == 1
    assert d["congenita_aborto"] == 1
    assert d["congenita_natimorto"] == 1
    assert d["casos_congenita"] == 5


def test_obito_por_outras_causas_nao_conta_como_obito_por_sifilis():
    d = so([congenito(EVOLUCAO="3")])
    assert d["congenita_obito"] == 0


# ── grão e chaves ──────────────────────────────────────────────────────────

def test_municipio_de_seis_digitos():
    assert _municipio("4316302") == "431630"
    assert _municipio("431630") == "431630"
    for v in ("", "43163", "abcdef", None):
        assert _municipio(v) is None


def test_registro_sem_residencia_e_contado_e_nao_some():
    df, rel = agregar([simples(), simples(ID_MN_RESI="")], "gestante", 2023)
    assert rel["sem_municipio"] == 1
    assert rel["lidos"] == 2
    assert df["casos_gestante"].sum() == 1


def test_ano_divergente_em_massa_aborta():
    fora = [simples(DT_NOTIFIC=dt.date(2019, 3, 1)) for _ in range(10)]
    with pytest.raises(SystemExit, match="fora do ano do arquivo"):
        agregar(fora, "gestante", 2023)


def test_uma_divergencia_isolada_nao_aborta():
    """Tolerância de 1%: ruído de digitação não pode derrubar o ano inteiro."""
    regs = [simples() for _ in range(200)] + [simples(DT_NOTIFIC=dt.date(2019, 3, 1))]
    df, rel = agregar(regs, "gestante", 2023)
    assert rel["ano_divergente"] == 1
    assert df["casos_gestante"].sum() == 201


def test_agravo_desconhecido_aborta():
    with pytest.raises(SystemExit, match="agravo desconhecido"):
        agregar([], "hanseniase", 2023)


# ── guardas ────────────────────────────────────────────────────────────────

def test_guardas_passam_num_recorte_sao():
    """A metade que nenhuma guarda deste projeto pode ficar sem: dizer SIM."""
    df = montar({"adquirida": [simples()], "gestante": [simples(), simples(), simples()],
                 "congenita": [congenito()]})
    guardas(df, {"431630"})


def test_criterio_c_reprova_municipio_fora_da_dimensao():
    df = montar({"congenita": [congenito(ID_MN_RESI="999999")]})
    with pytest.raises(SystemExit, match="CRITERIO C"):
        guardas(df, {"431630"})


def test_criterio_c_e_pulado_sem_dimensao_disponivel():
    df = montar({"congenita": [congenito()]})
    guardas(df, None)


def test_criterio_a_reprova_mais_congenitos_que_gestantes():
    df = montar({"gestante": [simples()],
                 "congenita": [congenito() for _ in range(3)]})
    with pytest.raises(SystemExit, match="CRITERIO A"):
        guardas(df)


def test_criterio_b_reprova_maioria_sem_prenatal():
    df = montar({"gestante": [simples() for _ in range(20)],
                 "congenita": [congenito(ANT_PRE_NA="2") for _ in range(3)]
                              + [congenito(ANT_PRE_NA="1")]})
    with pytest.raises(SystemExit, match="CRITERIO B"):
        guardas(df)


def test_guarda_pega_categorias_de_prenatal_que_nao_fecham():
    df = montar({"congenita": [congenito()]})
    df.loc[0, "congenita_prenatal_ignorado"] = 7
    with pytest.raises(SystemExit, match="pré-natal ≠ casos_congenita"):
        guardas(df)


def test_guarda_pega_subconjunto_maior_que_o_total():
    df = montar({"congenita": [congenito()]})
    df.loc[0, "congenita_obito"] = 9
    with pytest.raises(SystemExit, match="congenita_obito > casos_congenita"):
        guardas(df)


def test_guarda_pega_contagem_negativa():
    df = montar({"congenita": [congenito()]})
    df.loc[0, "casos_adquirida"] = -1
    with pytest.raises(SystemExit, match="contagem negativa"):
        guardas(df)


def test_guarda_reprova_agregacao_vazia():
    with pytest.raises(SystemExit, match="vazia"):
        guardas(pd.DataFrame())


def test_combinar_sem_partes_aborta():
    with pytest.raises(SystemExit, match="nada a combinar"):
        combinar([], TODOS)


def test_todas_as_colunas_congenitas_existem_no_mart():
    """Guarda contra coluna declarada e nunca preenchida."""
    df = montar({"congenita": [congenito()]})
    for col in COLUNAS_CONGENITA:
        assert col in df.columns


# ── ano parcial: fronteira do dado, não buraco ─────────────────────────────
#
# SIFCBR25 tem 12.630 casos contra 24.631 em 2024 e o arquivo acaba em junho.
# Sem `meses_cobertos`, essa metade de ano entra na série com cara de queda de
# 49%. A guarda precisa distinguir as duas coisas: parcial na PONTA é atualidade
# e tem de passar; parcial no MEIO é coleta incompleta e tem de reprovar.

def com_cobertura(df, meses_por_ano):
    return anotar_cobertura(df, meses_por_ano)


def _serie(anos):
    partes = [agregar([congenito(DT_NOTIFIC=dt.date(a, 3, 1))], "congenita", a)[0]
              for a in anos]
    coletados = {"adquirida": set(), "gestante": set(), "congenita": set(anos)}
    return derivar(combinar(partes, coletados), None)


def test_meses_cobertos_vira_coluna_do_mart():
    df = com_cobertura(_serie([2024]), {2024: set(range(1, 13))})
    assert df.iloc[0]["meses_cobertos"] == 12


def test_ultimo_ano_pode_ser_parcial_sem_reprovar():
    """A ponta da série é retrato em andamento — reprovar seria reprovar a atualidade."""
    df = com_cobertura(_serie([2024, 2025]),
                       {2024: set(range(1, 13)), 2025: {1, 2, 3, 4, 5, 6}})
    guardas(df)
    assert df[df["ano"] == 2025].iloc[0]["meses_cobertos"] == 6


def test_ano_fechado_incompleto_reprova():
    """Ano do meio com menos de 12 meses é coleta incompleta, não calendário."""
    df = com_cobertura(_serie([2023, 2024, 2025]),
                       {2023: {1, 2, 3}, 2024: set(range(1, 13)), 2025: {1, 2}})
    with pytest.raises(SystemExit, match="menos de 12 meses"):
        guardas(df)


def test_meses_do_relatorio_le_so_os_meses_com_notificacao():
    rel = Counter({"lidos": 9, "mes:01": 5, "mes:06": 4, "mes:07": 0})
    assert meses_do_relatorio(rel) == {1, 6}


def test_agregar_conta_o_mes_da_notificacao():
    _, rel = agregar([congenito(DT_NOTIFIC=dt.date(2023, 6, 2)),
                      congenito(DT_NOTIFIC=dt.date(2023, 6, 9)),
                      congenito(DT_NOTIFIC=dt.date(2023, 11, 1))], "congenita", 2023)
    assert meses_do_relatorio(rel) == {6, 11}


def test_guarda_de_meses_e_pulada_quando_a_coluna_nao_existe():
    """Frames antigos, sem o carimbo, não podem derrubar a guarda inteira."""
    guardas(_serie([2024]))
