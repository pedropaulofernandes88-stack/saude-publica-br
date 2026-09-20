"""Guardas do mart de convênios federais de saúde.

O que estes testes protegem, em ordem de dano:

 1. **dinheiro que some na agregação** — somar por grupo e por ano é onde um
    `groupby` errado tira zeros sem avisar;
 2. **UF não coletada virando "estado sem convênio"** — é
    `coleta-ausencia-vs-falha` com o gatilho pronto: a varredura é por UF, e
    uma UF faltando no checkpoint sai do mart exatamente como uma UF sem
    convênio nenhum;
 3. **rótulo novo de convenente classificado em silêncio** — a API pode criar
    categoria, e cair num balde `outro` sem reclamar é publicar classificação
    errada;
 4. **`pct_executado` inventado** — dividir liberado por pactuado zero devolve
    0% ou infinito, e as duas leituras são falsas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import pipeline_convenios as pc  # noqa: E402


def _convenio(**kw) -> dict:
    base = {
        "convenente": {"tipo": "Administração Pública Municipal",
                       "cnpjFormatado": "12.345.678/0001-95"},
        "municipioConvenente": {"codigoIBGE": "3550308"},
        "dataInicioVigencia": "2019-03-01",
        "dataFinalVigencia": "2021-03-01",
        "valor": 100000.0, "valorLiberado": 48050.0, "valorContrapartida": 0.0,
    }
    base.update(kw)
    return base


@pytest.fixture
def ckpt(tmp_path, monkeypatch):
    """Um diretório de checkpoints completo (as 27 UFs), para os testes."""
    monkeypatch.setattr(pc, "CKPT", tmp_path)
    def escrever(uf: str, registros: list[dict]):
        (tmp_path / f"convenios_saude_{uf}.json").write_text(
            json.dumps(registros, ensure_ascii=False), encoding="utf-8")
    for uf in pc.UFS:
        escrever(uf, [])
    return escrever


def test_grupo_conhece_os_rotulos_da_api():
    assert pc._grupo("Administração Pública Municipal") == "publico"
    assert pc._grupo("Administração Pública Estadual ou do Distrito Federal") == "publico"
    assert pc._grupo("Entidades Sem Fins Lucrativos") == "sem_fins_lucrativos"
    assert pc._grupo("Entidades Empresariais Privadas") == "empresarial"


def test_rotulo_desconhecido_nao_vira_publico_por_engano():
    """O erro caro seria um rótulo novo cair silenciosamente num grupo real."""
    assert pc._grupo("Consórcio Público Intermunicipal") == "outro"
    assert pc._grupo(None) == "outro"
    assert pc._grupo("") == "outro"


def test_uf_sem_checkpoint_reprova(ckpt, monkeypatch, tmp_path):
    """Uma UF faltando NÃO pode sair como estado sem convênio."""
    (tmp_path / "convenios_saude_SP.json").unlink()
    bruto, cob = pc.ler_checkpoints()
    assert not cob.loc[cob["uf_sigla"] == "SP", "coletado"].item()
    with pytest.raises(SystemExit, match="SP"):
        pc.guardas(pd.DataFrame({"municipio_cod": [], "valor_liberado": [],
                                 "valor_pactuado": []}), bruto, cob)


def test_excesso_de_rotulo_desconhecido_reprova_e_NOMEIA(ckpt):
    ckpt("SP", [_convenio(convenente={"tipo": "Categoria Que Nao Existia"})] * 3)
    bruto, cob = pc.ler_checkpoints()
    mart = pc.agregar(bruto)
    with pytest.raises(SystemExit, match="Categoria Que Nao Existia"):
        pc.guardas(mart, bruto, cob)


def test_rotulo_raro_mas_CARO_reprova_ainda_que_a_contagem_passe(ckpt):
    """O caso real que a primeira versão desta guarda deixou passar.

    "Organizações Internacionais" eram 91 de 21.023 convênios — 0,43%, folgado
    num corte de 5% por contagem — e carregavam R$ 31,7 bi, 44% de todo o
    dinheiro. Uma guarda que só conta é cega para isso.
    """
    ckpt("SP", [_convenio(convenente={"tipo": "Administração Pública Municipal"},
                          valor=1.0, valorLiberado=1.0)] * 200
              + [_convenio(convenente={"tipo": "Rótulo Novo E Caro"},
                           valor=1_000_000.0, valorLiberado=1_000_000.0)])
    bruto, cob = pc.ler_checkpoints()
    mart = pc.agregar(bruto)
    assert (bruto["grupo_convenente"] == "outro").mean() < 0.05, (
        "o cenário do teste exige contagem ABAIXO do corte"
    )
    with pytest.raises(SystemExit, match="Rótulo Novo E Caro"):
        pc.guardas(mart, bruto, cob)


def test_organismo_internacional_tem_grupo_proprio():
    """Somá-los ao público ou jogá-los em `outro` apagaria 44% do dinheiro."""
    assert pc._grupo("Organizações Internacionais") == "organismo_internacional"


def test_a_agregacao_nao_perde_dinheiro(ckpt):
    """Invariante central: o total do mart é o total do bruto."""
    ckpt("SP", [_convenio(valor=100.0, valorLiberado=40.0),
                _convenio(valor=250.0, valorLiberado=250.0),
                _convenio(valor=7.0, valorLiberado=0.0,
                          convenente={"tipo": "Entidades Sem Fins Lucrativos"})])
    bruto, _ = pc.ler_checkpoints()
    mart = pc.agregar(bruto)
    assert mart["valor_pactuado"].sum() == pytest.approx(357.0)
    assert mart["valor_liberado"].sum() == pytest.approx(290.0)
    assert mart["convenios"].sum() == 3


def test_pct_executado_e_nulo_quando_nao_ha_pactuado(ckpt):
    """Zero pactuado não é 0% executado nem infinito — é indefinido."""
    ckpt("SP", [_convenio(valor=0.0, valorLiberado=0.0)])
    bruto, _ = pc.ler_checkpoints()
    mart = pc.agregar(bruto)
    assert mart["pct_executado"].isna().all()


def test_pct_executado_calcula_quando_ha_pactuado(ckpt):
    ckpt("SP", [_convenio(valor=200.0, valorLiberado=50.0)])
    bruto, _ = pc.ler_checkpoints()
    mart = pc.agregar(bruto)
    assert mart["pct_executado"].item() == pytest.approx(25.0)


def test_o_ano_vem_do_inicio_da_vigencia(ckpt):
    """E não de `dataReferencia`, que é o dia do retrato e traz 1900 como nulo."""
    ckpt("SP", [_convenio(dataInicioVigencia="2013-11-04",
                          dataReferencia="1900-01-01")])
    bruto, _ = pc.ler_checkpoints()
    mart = pc.agregar(bruto)
    assert mart["ano"].item() == 2013


def test_municipio_liga_pelo_codigo_de_SETE_digitos(ckpt):
    """A API devolve 7 dígitos; a dimensão do projeto guarda 6 e 7."""
    ckpt("SP", [_convenio(municipioConvenente={"codigoIBGE": "3550308"})])
    bruto, _ = pc.ler_checkpoints()
    mart = pc.agregar(bruto)
    assert mart["municipio_cod"].item() == "355030"
    assert mart["municipio_nome"].item()


def test_convenio_sem_data_de_vigencia_nao_derruba_nem_vira_ano_zero(ckpt):
    ckpt("SP", [_convenio(dataInicioVigencia=None),
                _convenio(dataInicioVigencia="2020-01-01")])
    bruto, _ = pc.ler_checkpoints()
    mart = pc.agregar(bruto)
    assert list(mart["ano"]) == [2020], "linha sem data sai, e não vira ano 0"
