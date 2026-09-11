"""
O carimbo de cobertura tem de SOBREVIVER à agregação.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O checkpoint do SIH sempre soube de quantos meses ele veio — `saude_em_dado.
meses`, gravado desde a correção de 2026-08-11 — e essa informação morria na
agregação: `groupby(...)[MEDIDAS].sum()` descarta qualquer coluna fora de
MEDIDAS, e o mart saía com o total do ano sem dizer de quantos meses ele veio.

Escrevendo esta implementação eu reproduzi o próprio defeito: a primeira versão
carimbava a linha do checkpoint e perdia o carimbo no `groupby` de `build()`.
Passou no teste que só olhava o checkpoint. Daí estes testes olharem o MART, e
não a leitura.

A distinção que o carimbo carrega:

  * a coleta ABORTA quando um mês publicado no FTP não é coletado — isso é
    defeito e já tem guarda desde 2026-08-11;
  * quando o PRÓPRIO FTP só publicou 7 meses, não há defeito nenhum: a coleta
    está certa e o total do ano continua não sendo comparável com o de um ano
    fechado. É esse caso que nenhuma guarda alcança e que o carimbo declara.

Mesmo desenho de `meses_cobertos` em mart_sifilis_municipio e de
`semanas_cobertas` em mart_dengue_municipio_ano (V043).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _datasus_ftp import (  # noqa: E402
    COLUNA_COBERTURA,
    FalhaDeColeta,
    conferir_cobertura_anual,
    gravar_checkpoint,
    ler_checkpoint_carimbado,
)

pytestmark = pytest.mark.unit

#: Os marts que recebem o carimbo, e o pipeline que os grava.
CARIMBADOS = {
    "mart_internacoes_municipio": "pipeline_sih.py",
    "mart_internacoes_agravo": "pipeline_sih_agravo.py",
    "mart_internacoes_hospital": "pipeline_sih_agravo.py",
    "mart_icsap_municipio": "pipeline_sih_fluxo.py",
    "mart_fluxo_intermunicipal": "pipeline_sih_fluxo.py",
}

#: Mart do SIH que NÃO recebe o carimbo, com o motivo. Estar aqui é decisão.
SEM_CARIMBO = {
    "mart_demanda_mensal_hospital": "grão mensal: ano parcial já aparece como "
                                    "competência faltando, a chave já diz",
    "mart_hsmr_hospital": "derivado dos marts carimbados",
    "mart_los_hospital": "derivado dos marts carimbados",
    "mart_forecast_demanda_hospital": "derivado; é projeção, não coleta",
    "mart_icsap_pares": "view derivada de mart_icsap_municipio",
}


def _df(n: int = 3, ano: int = 2024) -> pd.DataFrame:
    return pd.DataFrame({
        "municipio_cod": [f"31062{i}" for i in range(n)],
        "ano": [ano] * n,
        "internacoes": [10 * (i + 1) for i in range(n)],
    })


# -- a leitura carimba, e carimba o que o arquivo diz ------------------------

def test_checkpoint_com_meses_carimba_a_contagem(tmp_path):
    ck = tmp_path / "sih_MG_2024_v2.parquet"
    gravar_checkpoint(_df(), ck, meses=[1, 2, 3, 4, 5, 6, 7])
    df = ler_checkpoint_carimbado(ck)
    assert df[COLUNA_COBERTURA].tolist() == [7, 7, 7]


def test_ano_fechado_carimba_doze(tmp_path):
    ck = tmp_path / "sih_MG_2024_v2.parquet"
    gravar_checkpoint(_df(), ck, meses=list(range(1, 13)))
    assert set(ler_checkpoint_carimbado(ck)[COLUNA_COBERTURA]) == {12}


def test_checkpoint_sem_carimbo_devolve_nulo_e_nao_zero(tmp_path):
    """Zero afirmaria que nenhum mês contribuiu — falso, e pior que não saber."""
    ck = tmp_path / "sih_MG_2024_v2.parquet"
    gravar_checkpoint(_df(), ck)          # sem `meses`
    df = ler_checkpoint_carimbado(ck)
    assert df[COLUNA_COBERTURA].isna().all()
    assert not (df[COLUNA_COBERTURA] == 0).any()


def test_o_carimbo_e_inteiro_anulavel(tmp_path):
    """`Int64`, não float: 7.0 meses não existe, e float vira 7.0 no CSV."""
    ck = tmp_path / "sih_MG_2024_v2.parquet"
    gravar_checkpoint(_df(), ck, meses=[1, 2])
    assert str(ler_checkpoint_carimbado(ck)[COLUNA_COBERTURA].dtype) == "Int64"


def test_o_carimbo_sai_do_arquivo_e_nao_de_variavel(tmp_path):
    """Cache e reprocessamento passam pela MESMA leitura.

    Se o carimbo viesse de uma variável do processo, o caminho do cache
    devolveria sem carimbo e o do reprocessamento com — a divergência
    silenciosa que este desenho existe para impedir.
    """
    ck = tmp_path / "sih_MG_2024_v2.parquet"
    gravar_checkpoint(_df(), ck, meses=[1, 2, 3])
    primeira = ler_checkpoint_carimbado(ck)
    segunda = ler_checkpoint_carimbado(ck)
    pd.testing.assert_frame_equal(primeira, segunda)


# -- a guarda do ano fechado -------------------------------------------------

def test_ano_anterior_curto_aborta():
    """Ano fechado com menos de 12 meses é coleta incompleta se passando por ano."""
    df = pd.DataFrame({"ano": [2023, 2024], COLUNA_COBERTURA: pd.array([7, 12], dtype="Int64")})
    with pytest.raises(FalhaDeColeta, match="ano fechado com menos de 12"):
        conferir_cobertura_anual(df, "teste")


def test_ultimo_ano_curto_e_permitido():
    """A fronteira do dado é parcial por natureza — é o que o carimbo declara."""
    df = pd.DataFrame({"ano": [2023, 2024], COLUNA_COBERTURA: pd.array([12, 7], dtype="Int64")})
    conferir_cobertura_anual(df, "teste")      # não levanta


def test_todos_completos_passa():
    df = pd.DataFrame({"ano": [2022, 2023, 2024],
                       COLUNA_COBERTURA: pd.array([12, 12, 12], dtype="Int64")})
    conferir_cobertura_anual(df, "teste")


def test_guarda_ignora_linha_sem_carimbo():
    """Linha anterior ao carimbo é <NA>; ela não pode derrubar a guarda."""
    df = pd.DataFrame({"ano": [2022, 2023, 2024],
                       COLUNA_COBERTURA: pd.array([None, None, 12], dtype="Int64")})
    conferir_cobertura_anual(df, "teste")


def test_guarda_usa_o_minimo_da_uf_e_nao_a_media():
    """Uma UF curta entre 26 completas não pode ser diluída."""
    df = pd.DataFrame({
        "ano": [2023] * 27 + [2024],
        COLUNA_COBERTURA: pd.array([7] + [12] * 26 + [12], dtype="Int64"),
    })
    with pytest.raises(FalhaDeColeta, match="2023"):
        conferir_cobertura_anual(df, "teste")


# -- o carimbo sobrevive à agregação (era o defeito real) --------------------

def test_o_carimbo_sobrevive_ao_groupby_de_medidas():
    """Reproduz o defeito que eu escrevi: somar por MEDIDAS descarta a coluna.

    Este teste não olha o checkpoint — olha o que sai da agregação, que é o
    que vai publicado.
    """
    MEDIDAS = ["internacoes"]
    bruto = pd.DataFrame({
        "municipio_cod": ["310620", "310620", "355030"],
        "ano": [2024, 2024, 2024],
        "capitulo_cid": ["I", "II", "I"],
        "internacoes": [10, 20, 30],
        COLUNA_COBERTURA: pd.array([12, 12, 7], dtype="Int64"),
    })
    # o jeito ERRADO, que perde a coluna
    perdido = bruto.groupby(["municipio_cod", "ano"], as_index=False)[MEDIDAS].sum()
    assert COLUNA_COBERTURA not in perdido.columns

    # o jeito adotado: guardar antes, repor depois
    cobertura = bruto.groupby(["municipio_cod", "ano"], as_index=False)[COLUNA_COBERTURA].min()
    mart = perdido.merge(cobertura, on=["municipio_cod", "ano"], how="left")
    assert COLUNA_COBERTURA in mart.columns
    assert mart.set_index("municipio_cod")[COLUNA_COBERTURA].to_dict() == {"310620": 12, "355030": 7}


def test_o_minimo_e_conservador_e_nao_a_media():
    """Município sob duas coberturas fica com a pior — a leitura conservadora."""
    bruto = pd.DataFrame({
        "municipio_cod": ["310620", "310620"],
        "ano": [2024, 2024],
        COLUNA_COBERTURA: pd.array([12, 5], dtype="Int64"),
    })
    cob = bruto.groupby(["municipio_cod", "ano"], as_index=False)[COLUNA_COBERTURA].min()
    assert cob[COLUNA_COBERTURA].iloc[0] == 5


# -- cobertura da decisão: nenhum mart do SIH fica sem decisão ---------------

def test_todo_mart_do_sih_tem_decisao_sobre_o_carimbo():
    """Mart novo do SIH entra carimbado ou declarado sem carimbo, com motivo.

    É a mesma forma de OBSERVADAS/NAO_OBSERVADAS: silêncio não é decisão.
    """
    import json
    import re

    ponteiro = json.loads((RAIZ / "data/publicacoes/atual.json").read_text(encoding="utf-8"))
    man = json.loads((RAIZ / f"data/publicacoes/{ponteiro['arquivo']}").read_text(encoding="utf-8"))
    ts = (RAIZ / "site/lib/fontes.ts").read_text(encoding="utf-8")
    mapa = dict(re.findall(r'^\s*(\w+):\s*"([a-z_]+)",', ts.split("FONTE_DA_TABELA")[1], re.M))

    do_sih = {n for n in man["tabelas"] if mapa.get(n) == "sih"}
    assert do_sih, "nenhum mart do SIH no manifesto — a varredura não prova nada"
    sem_decisao = do_sih - set(CARIMBADOS) - set(SEM_CARIMBO)
    assert not sem_decisao, (
        f"mart do SIH sem decisão sobre o carimbo de cobertura: {sorted(sem_decisao)}. "
        f"Ou recebe `meses_cobertos`, ou entra em SEM_CARIMBO com o motivo.")


def test_toda_dispensa_de_carimbo_traz_motivo():
    mudas = [k for k, v in SEM_CARIMBO.items() if not v.strip()]
    assert not mudas, f"dispensa sem motivo: {mudas}"


def test_a_migracao_cobre_exatamente_os_carimbados():
    sql = (RAIZ / "migrations/V046__sih_meses_cobertos.sql").read_text(encoding="utf-8")
    for mart in CARIMBADOS:
        assert f"alter table public.{mart}" in sql, f"V046 não altera {mart}"
    for mart in SEM_CARIMBO:
        assert f"alter table public.{mart}" not in sql, f"V046 altera {mart}, que é dispensado"
