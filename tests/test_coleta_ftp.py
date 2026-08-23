"""
Guardas da coleta do FTP do DataSUS.

Nasceram de um estrago real: em 2026-08-11 os pipelines do SIH gravaram
checkpoints incompletos porque `except Exception: return None` tratava
"mês falhou" como "mês não existe". MA 2023 perdeu 5 dos 12 meses (-41% das
internações) e o pipeline terminou com código 0.

Os testes aqui cobrem as duas invariantes que impedem a repetição:
  1. ausência e falha são exceções DIFERENTES;
  2. checkpoint carrega os meses que o produziram e não é reaproveitado
     quando o FTP já publica um mês que ele não tem.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import _datasus_ftp as ftp  # noqa: E402

DIR = "/dissemin/publicos/SIHSUS/200801_/Dados"


@pytest.fixture(autouse=True)
def _sem_rede(monkeypatch):
    """Nenhum teste deste arquivo pode tocar a rede."""
    monkeypatch.setattr(ftp, "_listagens", {})

    def _proibido(*a, **k):
        raise AssertionError("teste tentou abrir conexão FTP")

    monkeypatch.setattr(ftp, "FTP", _proibido)


def _listagem(monkeypatch, nomes: set[str]) -> None:
    monkeypatch.setattr(ftp, "listar", lambda diretorio, host=ftp.HOST_PADRAO: nomes)


def _df() -> pd.DataFrame:
    return pd.DataFrame({"municipio_cod": ["210010"], "internacoes": [7]})


# -- ausência não é falha ---------------------------------------------------

def test_arquivo_fora_da_listagem_e_ausencia_e_nao_falha(monkeypatch):
    _listagem(monkeypatch, {"RDMA2301.DBC"})
    with pytest.raises(ftp.ArquivoAusente):
        ftp.baixar(DIR, "RDMA2302.dbc")


def test_ausencia_e_falha_sao_classes_distintas():
    # o pipeline decide "pular" ou "abortar" por esta diferença; se um dia
    # virarem a mesma classe, o `except ArquivoAusente` engole a falha.
    assert not issubclass(ftp.FalhaDeColeta, ftp.ArquivoAusente)
    assert not issubclass(ftp.ArquivoAusente, ftp.FalhaDeColeta)


def test_meses_publicados_ignora_competencia_futura(monkeypatch):
    _listagem(monkeypatch, {f"RDMA26{m:02d}.DBC" for m in range(1, 7)} | {"RDBA2601.DBC"})
    assert ftp.meses_publicados(DIR, "RDMA", 2026) == [1, 2, 3, 4, 5, 6]
    assert ftp.meses_publicados(DIR, "RDBA", 2026) == [1]
    assert ftp.meses_publicados(DIR, "RDMA", 2023) == []


def test_existe_e_insensivel_a_caixa(monkeypatch):
    _listagem(monkeypatch, {"RDMA2301.DBC"})
    assert ftp.existe(DIR, "rdma2301.dbc")
    assert not ftp.existe(DIR, "RDMA2302.dbc")


# -- o checkpoint sabe de quantos meses veio --------------------------------

def test_checkpoint_guarda_os_meses_que_o_produziram(tmp_path):
    alvo = tmp_path / "fluxo_MA_2023_v2.parquet"
    ftp.gravar_checkpoint(_df(), alvo, [1, 2, 3])
    assert ftp.meses_do_checkpoint(alvo) == {1, 2, 3}
    assert pd.read_parquet(alvo).equals(_df())


def test_checkpoint_incompleto_nao_e_reaproveitado(tmp_path):
    # o caso MA 2023: 7 meses coletados, 12 publicados
    alvo = tmp_path / "fluxo_MA_2023_v2.parquet"
    ftp.gravar_checkpoint(_df(), alvo, [1, 2, 3, 4, 5, 6, 7])
    assert not ftp.checkpoint_utilizavel(alvo, list(range(1, 13)))


def test_checkpoint_completo_e_reaproveitado(tmp_path):
    alvo = tmp_path / "fluxo_MA_2023_v2.parquet"
    ftp.gravar_checkpoint(_df(), alvo, list(range(1, 13)))
    assert ftp.checkpoint_utilizavel(alvo, list(range(1, 13)))


def test_checkpoint_do_ano_corrente_basta_cobrir_o_publicado(tmp_path):
    alvo = tmp_path / "fluxo_MA_2026_v2.parquet"
    ftp.gravar_checkpoint(_df(), alvo, [1, 2, 3, 4, 5, 6])
    assert ftp.checkpoint_utilizavel(alvo, [1, 2, 3, 4, 5, 6])
    # e deixa de bastar assim que o DataSUS publica julho
    assert not ftp.checkpoint_utilizavel(alvo, [1, 2, 3, 4, 5, 6, 7])


def test_checkpoint_sem_carimbo_e_tratado_como_legado(tmp_path):
    # os 100+ checkpoints gravados antes desta guarda continuam válidos;
    # quem quer certeza apaga o arquivo e deixa refazer.
    alvo = tmp_path / "antigo.parquet"
    _df().to_parquet(alvo, compression="zstd", index=False)
    assert ftp.meses_do_checkpoint(alvo) is None
    assert ftp.checkpoint_utilizavel(alvo, list(range(1, 13)))


def test_checkpoint_inexistente_nunca_e_utilizavel(tmp_path):
    assert not ftp.checkpoint_utilizavel(tmp_path / "nao_existe.parquet", [1])
    assert ftp.meses_do_checkpoint(tmp_path / "nao_existe.parquet") is None


# -- os pipelines usam mesmo a guarda ---------------------------------------

@pytest.mark.parametrize("modulo", [
    "pipeline_sih", "pipeline_sih_fluxo", "pipeline_sih_hospitalar",
    "pipeline_sih_agravo", "pipeline_sinasc",
])
def test_pipeline_nao_engole_falha_de_coleta(modulo):
    """Nenhum pipeline do SIH/SINASC pode voltar ao `except Exception: return None`."""
    fonte = (Path(__file__).resolve().parents[1] / "scripts" / f"{modulo}.py").read_text(encoding="utf-8")
    assert "from _datasus_ftp import" in fonte, f"{modulo} não usa a coleta que falha alto"
    assert "ftp.size(" not in fonte, f"{modulo} voltou a tratar erro de FTP como ausência"


# -- o conferidor de coleta precisa REPROVAR quando há defeito ---------------
#
# Um verificador que só sabe dizer "OK" é um verde mentiroso. Cada checagem de
# `conferir_coleta.py` é exercitada aqui contra um defeito construído.

import conferir_coleta as cc  # noqa: E402


def _monta_sih(raiz: Path, meses_demanda: list[int], total_sih: int,
               total_demanda: int) -> None:
    (raiz / "hosp_ckpt").mkdir(parents=True, exist_ok=True)
    (raiz / "ckpt").mkdir(parents=True, exist_ok=True)
    n = len(meses_demanda)
    por_mes = [total_demanda // n] * n
    por_mes[0] += total_demanda - sum(por_mes)      # o resto não pode sumir
    pd.DataFrame({
        "cnes": ["2077485"] * n,
        "ano_mes": [f"2023-{m:02d}" for m in meses_demanda],
        "internacoes": por_mes,
    }).to_parquet(raiz / "hosp_ckpt" / "demanda_GO_2023_v2.parquet", index=False)
    pd.DataFrame({"municipio_cod": ["520870"], "internacoes": [total_sih]}).to_parquet(
        raiz / "ckpt" / "sih_GO_2023_v2.parquet", index=False)


def test_conferidor_acusa_mes_ausente_na_demanda(tmp_path, monkeypatch):
    _monta_sih(tmp_path, [m for m in range(1, 13) if m != 2], 120, 120)
    monkeypatch.setattr(cc, "SIH", tmp_path)
    problemas = cc.conferir_calendario()
    assert problemas and "GO 2023" in problemas[0] and "[2]" in problemas[0]


def test_conferidor_aprova_ano_completo(tmp_path, monkeypatch):
    _monta_sih(tmp_path, list(range(1, 13)), 120, 120)
    monkeypatch.setattr(cc, "SIH", tmp_path)
    assert cc.conferir_calendario() == []


def test_conferidor_acusa_divergencia_entre_familias(tmp_path, monkeypatch):
    # as duas famílias leem os mesmos RD; discordar significa perda de arquivo
    _monta_sih(tmp_path, list(range(1, 13)), 423932, 391084)
    monkeypatch.setattr(cc, "SIH", tmp_path)
    problemas = cc.conferir_cruzada()
    assert problemas and "GO 2023" in problemas[0]


def test_conferidor_aprova_familias_que_batem(tmp_path, monkeypatch):
    _monta_sih(tmp_path, list(range(1, 13)), 423932, 423932)
    monkeypatch.setattr(cc, "SIH", tmp_path)
    assert cc.conferir_cruzada() == []


def test_conferidor_acusa_carimbo_incompleto(tmp_path, monkeypatch):
    alvo = tmp_path / "fluxo_ckpt" / "fluxo_MA_2023_v2.parquet"
    ftp.gravar_checkpoint(_df(), alvo, [1, 2, 3, 4, 5, 6, 7])
    monkeypatch.setattr(cc, "SIH", tmp_path)
    monkeypatch.setattr(cc, "meses_publicados",
                        lambda *a, **k: list(range(1, 13)))
    problemas = cc.conferir_carimbo()
    assert problemas and "fluxo_MA_2023_v2.parquet" in problemas[0]
