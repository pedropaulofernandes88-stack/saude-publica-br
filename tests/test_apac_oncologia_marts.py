"""Guardas dos marts do SIA/APAC oncológico.

Cada guarda aparece aqui REPROVANDO e APROVANDO. Guarda que só se viu passar
não se sabe se detecta alguma coisa — este projeto já teve guarda declarada e
não implementada, guarda opt-in que ninguém ligava e guarda com detector
quebrado. Ver `tests/test_guardas_de_integridade.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import pipeline_siasus_oncologia_marts as pm  # noqa: E402


def _trat(**col) -> pd.DataFrame:
    base = {"municipio_cod": ["330455"], "ano": [2024], "modalidade": ["quimioterapia"],
            "cid3": ["C50"], "estadiamento": ["2"], "apacs": [100], "valor_aprovado": [1.0]}
    base.update(col)
    return pd.DataFrame(base)


# -- o carimbo de ano parcial -----------------------------------------------

def test_carimbo_REPROVA_ano_fechado_com_menos_de_doze_meses():
    """Ano do meio da série com 7 meses é coleta incompleta se passando por
    ano fechado — e contagem de linhas nunca pega isso."""
    m = pd.DataFrame({"ano": [2020, 2026], "modalidade": ["quimioterapia"] * 2,
                      "meses_cobertos": [7, 7]})
    with pytest.raises(SystemExit, match="menos de 12 meses"):
        pm._carimbo_so_cai_na_ponta(m)


def test_carimbo_APROVA_ultimo_ano_parcial():
    """Na ponta, ano parcial é o calendário, não defeito. Reprovar seria
    reprovar a atualidade da fonte."""
    m = pd.DataFrame({"ano": [2025, 2026], "modalidade": ["quimioterapia"] * 2,
                      "meses_cobertos": [12, 7]})
    pm._carimbo_so_cai_na_ponta(m)


# -- estadiamento: a guarda que existe por um defeito meu --------------------

def test_estadiamento_REPROVA_ano_sem_nenhum_ignorado():
    """O defeito real: `_estadio("")` devolvia "0" e a ausência sumia dentro do
    carcinoma in situ. O ano saía 100% estadiado, que é impossível nesta fonte."""
    df = pd.concat([_trat(estadiamento=["0"], apacs=[500]),
                    _trat(estadiamento=["2"], apacs=[500])])
    with pytest.raises(SystemExit, match="NENHUMA APAC com estadiamento"):
        pm._ausencia_de_estadiamento_tem_rotulo(df)


def test_estadiamento_REPROVA_ausencia_alta_demais():
    """O erro espelhado: ler o campo da outra modalidade devolve None em tudo,
    e aí o ano sai quase todo "ignorado" — também em silêncio."""
    df = pd.concat([_trat(estadiamento=["ignorado"], apacs=[900]),
                    _trat(estadiamento=["2"], apacs=[100])])
    with pytest.raises(SystemExit, match="sem estadiamento"):
        pm._ausencia_de_estadiamento_tem_rotulo(df)


def test_estadiamento_APROVA_a_faixa_medida_na_fonte():
    df = pd.concat([_trat(estadiamento=["ignorado"], apacs=[123]),
                    _trat(estadiamento=["2"], apacs=[877])])
    pm._ausencia_de_estadiamento_tem_rotulo(df)


def test_estadiamento_e_conferido_ANO_A_ANO_e_nao_no_agregado():
    """2014 sobreviveu ao conserto porque foi pulado por checkpoint. Um agregado
    nacional o teria escondido atrás dos outros treze anos."""
    bom = pd.concat([_trat(ano=[2013], estadiamento=["ignorado"], apacs=[120]),
                     _trat(ano=[2013], estadiamento=["2"], apacs=[880])])
    ruim = _trat(ano=[2014], estadiamento=["0"], apacs=[1000])
    with pytest.raises(SystemExit, match="2014"):
        pm._ausencia_de_estadiamento_tem_rotulo(pd.concat([bom, ruim]))


# -- duplicata ---------------------------------------------------------------

def test_duplicata_REPROVA_chave_repetida():
    df = pd.concat([_trat(), _trat()])
    with pytest.raises(SystemExit, match="duplicadas"):
        pm._sem_duplicata(df, pm.PK["tratamento"], "tratamento")


def test_duplicata_APROVA_chave_limpa():
    df = pd.concat([_trat(), _trat(cid3=["C34"])])
    pm._sem_duplicata(df, pm.PK["tratamento"], "tratamento")


# -- o nome carrega a fonte --------------------------------------------------

def test_os_marts_nao_colidem_com_os_do_painel_de_oncologia():
    """`mart_oncologia_estadiamento` (Painel) conta CASOS com 51% de
    estadiamento ausente; estes contam APACs com 12%. Mesmo prefixo faria a
    comparação parecer uma melhora de quatro vezes no registro."""
    texto = (RAIZ / "scripts" / "pipeline_siasus_oncologia_marts.py").read_text(encoding="utf-8")
    for nome in ("mart_apac_oncologia_tratamento", "mart_apac_oncologia_fluxo",
                 "mart_apac_oncologia_cobertura"):
        assert f'"{nome}.parquet"' in texto or f"{nome}.parquet" in texto
    for painel in ("mart_oncologia_municipio.parquet", "mart_oncologia_estadiamento.parquet"):
        assert f'MARTS / "{painel}"' not in texto, "não escreva por cima do mart do Painel"


# -- o mart gravado, quando existe -------------------------------------------

MART = RAIZ / "data" / "marts" / "mart_apac_oncologia_tratamento.parquet"
tem_mart = pytest.mark.skipif(not MART.exists(), reason="mart ainda não construído")


@tem_mart
def test_todo_ano_do_mart_tem_o_rotulo_de_ausencia():
    d = pd.read_parquet(MART, columns=["ano", "estadiamento", "apacs"])
    pm._ausencia_de_estadiamento_tem_rotulo(d)


@tem_mart
def test_uf_esta_preenchida_ate_nos_codigos_fora_da_dimensao():
    """As Regiões Administrativas do DF não são município do IBGE, mas a UF se
    sabe. Sem isso o DF perde 32 mil APACs numa agregação estadual."""
    d = pd.read_parquet(MART, columns=["municipio_cod", "municipio_nome", "uf_sigla"])
    orfas = d[d["municipio_nome"].isna()]
    assert len(orfas), "o mart deveria conter os códigos fora da dimensão, não descartá-los"
    assert orfas["uf_sigla"].notna().all(), "código sem município ainda tem UF conhecida"


@tem_mart
def test_o_ano_parcial_esta_carimbado_na_linha():
    d = pd.read_parquet(MART, columns=["ano", "meses_cobertos"])
    por_ano = d.groupby("ano")["meses_cobertos"].max()
    ultimo = int(por_ano.index.max())
    assert por_ano[ultimo] < 12, "o ano corrente não pode aparecer como fechado"
    assert (por_ano.drop(ultimo) == 12).all(), "ano fechado tem de trazer 12"
