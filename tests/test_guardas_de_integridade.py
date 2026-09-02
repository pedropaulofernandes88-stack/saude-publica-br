"""Guardas de integridade exercitadas no sentido em que elas REPROVAM.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Uma varredura em 2026-09-02 inventariou todos os pontos do projeto que abortam
por corretude — divergência, duplicata, NULL indevido, limiar estourado — e
cruzou com os testes. De 25 guardas desse tipo, **14 nunca tinham sido vistas
reprovando.** Existiam, pareciam proteger, e ninguém sabia se fechavam.

Não é uma preocupação teórica. Na mesma sessão, três guardas foram encontradas
sem funcionar de fato:

  * a régua de publicação do forecast media, escrevia o relatório e saía com
    código 0 — reprovar não estava implementado;
  * o teto de tamanho do banco só valia com uma flag ligada, e o banco passou de
    700 MB sem que a execução local dissesse nada;
  * um verificador de defeitos procurava a palavra errada na saída do pytest e
    por isso aprovava cinco defeitos construídos de propósito.

Em todos os casos o código da guarda estava escrito. O que faltava era alguém
ter visto a guarda dizer não.

Cada teste aqui, por isso, constrói a entrada defeituosa e exige o aborto.
Nenhum acessa rede.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import _varredura  # noqa: E402
from _publicacao import acumular_parquet, conferir_nao_nulos  # noqa: E402
from _sim_obitos import sql_uniao_fontes  # noqa: E402
from _varredura import varrer_orfaos  # noqa: E402

# ---------------------------------------------------------------------------
# 1. NULL em coluna `not null` — a "terceira guarda", nunca vista reprovando
# ---------------------------------------------------------------------------
# O docstring dela conta o defeito que a motivou: mart_saude_suplementar_municipio
# passou na contagem de linhas E na unicidade de chave, e mesmo assim não
# recarregava, porque `razao_implausivel` saía NULL em 4 municípios (`NA > 100`
# devolve NA). Um arquivo que não recarrega no esquema que diz representar não é
# cópia canônica; é cópia parecida. A guarda existia desde então e nunca tinha
# sido testada.

def test_null_em_coluna_obrigatoria_impede_a_publicacao(monkeypatch):
    monkeypatch.setattr("_publicacao.colunas_obrigatorias",
                        lambda: {"mart_x": ["municipio_cod", "razao_implausivel"]})
    df = pd.DataFrame({"municipio_cod": ["350280", "353730"],
                       "razao_implausivel": [False, None]})
    with pytest.raises(RuntimeError, match="NÃO será publicado"):
        conferir_nao_nulos("mart_x", df)


def test_a_mensagem_nomeia_a_coluna_e_conta_os_nulos(monkeypatch):
    """Guarda que diz só "falhou" obriga a reabrir a investigação do zero."""
    monkeypatch.setattr("_publicacao.colunas_obrigatorias",
                        lambda: {"mart_x": ["a", "b"]})
    df = pd.DataFrame({"a": [1, None, None], "b": [1, 2, 3]})
    with pytest.raises(RuntimeError, match=r"a=2"):
        conferir_nao_nulos("mart_x", df)


def test_dataframe_integro_passa(monkeypatch):
    monkeypatch.setattr("_publicacao.colunas_obrigatorias",
                        lambda: {"mart_x": ["a"]})
    conferir_nao_nulos("mart_x", pd.DataFrame({"a": [1, 2, 3]}))


def test_coluna_obrigatoria_ausente_do_dataframe_nao_dispara(monkeypatch):
    """Coluna que não veio é outro problema, e a guarda de esquema é que o pega.

    Confundir "ausente" com "nula" faria esta guarda gritar no lugar errado.
    """
    monkeypatch.setattr("_publicacao.colunas_obrigatorias",
                        lambda: {"mart_x": ["nao_existe"]})
    conferir_nao_nulos("mart_x", pd.DataFrame({"a": [1]}))


# ---------------------------------------------------------------------------
# 2. ausência de fonte ≠ recorte silencioso
# ---------------------------------------------------------------------------
# `sql_uniao_fontes` foi escrita em 2026-09-02 com um docstring citando
# [[coleta-ausencia-vs-falha]] — o episódio em que MA/2023 perdeu cinco meses e o
# coletor terminou com exit 0. E não tinha teste. A guarda que existe para
# impedir "processar o que existe e publicar recorte incompleto" nunca havia
# sido vista impedindo.

def test_ano_sem_arquivo_local_aborta_em_vez_de_processar_o_que_existe():
    with pytest.raises(SystemExit, match="recorte incompleto"):
        sql_uniao_fontes([1998])          # nenhum arquivo do SIM para 1998


def test_a_mensagem_diz_qual_ano_falta_e_como_resolver():
    with pytest.raises(SystemExit, match=r"1998.*pipeline_v2"):
        sql_uniao_fontes([1998])


def test_um_ano_faltando_no_meio_de_anos_validos_ainda_aborta():
    """O caso perigoso: 9 de 10 anos presentes parece sucesso na contagem."""
    with pytest.raises(SystemExit, match="1998"):
        sql_uniao_fontes([2022, 2023, 1998, 2024])


# ---------------------------------------------------------------------------
# 3. varredura de órfãs: apagar demais é pior que não apagar
# ---------------------------------------------------------------------------

def _publicadas(n: int) -> pd.DataFrame:
    return pd.DataFrame({"municipio_cod": [f"{i:06d}" for i in range(n)],
                         "ano": [2024] * n})


def test_chave_ausente_no_dataframe_aborta_antes_de_tocar_no_banco():
    with pytest.raises(ValueError, match="colunas-chave ausentes"):
        varrer_orfaos("http://x", "k", "mart_x",
                      pd.DataFrame({"outra": [1]}), ["municipio_cod"])


def test_orfas_demais_abortam_e_nada_e_apagado(monkeypatch):
    """Acima de 20% de órfãs, quase sempre a chave é que está errada.

    Este é o caso em que a guarda IMPEDE uma perda de dado: sem ela, um conjunto
    de chaves errado apagaria a tabela quase inteira, e o DELETE não volta.
    """
    monkeypatch.setattr(_varredura, "_chaves_publicadas",
                        lambda *a, **k: _publicadas(100))
    apagou = []
    monkeypatch.setattr(_varredura.requests, "delete",
                        lambda *a, **k: apagou.append(1))
    novas = pd.DataFrame({"municipio_cod": [f"{i:06d}" for i in range(50)],
                          "ano": [2024] * 50})          # 50% órfãs
    with pytest.raises(RuntimeError, match="Nada foi apagado"):
        varrer_orfaos("http://x", "k", "mart_x", novas, ["municipio_cod", "ano"])
    assert not apagou, "a guarda abortou mas o DELETE chegou a ser chamado"


def test_poucas_orfas_passam_e_sao_removidas(monkeypatch):
    """A guarda tem de deixar o trabalho normal acontecer, senão vira travão."""
    monkeypatch.setattr(_varredura, "_chaves_publicadas",
                        lambda *a, **k: _publicadas(100))

    class _Resp:
        status_code = 204
        text = ""

    monkeypatch.setattr(_varredura.requests, "delete", lambda *a, **k: _Resp())
    novas = pd.DataFrame({"municipio_cod": [f"{i:06d}" for i in range(95)],
                          "ano": [2024] * 95})          # 5% órfãs
    assert varrer_orfaos("http://x", "k", "mart_x", novas,
                         ["municipio_cod", "ano"]) == 5


# ---------------------------------------------------------------------------
# 4. acumular sem chave primária duplicaria linhas a cada execução
# ---------------------------------------------------------------------------
# A segunda guarda desta função já tinha teste (`test_acumular_exige_chave_completa`);
# a primeira — tabela sem PK no schema.sql — não tinha.

def test_acumular_sem_pk_no_schema_aborta(tmp_path, monkeypatch):
    monkeypatch.setattr("_publicacao.chaves_primarias", lambda: {})
    with pytest.raises(RuntimeError, match="sem chave primária"):
        acumular_parquet(pd.DataFrame({"a": [1]}), tmp_path / "x.parquet",
                         "mart_sem_pk", origem="pipeline")


# ---------------------------------------------------------------------------
# 5. o dado já publicado não muda em silêncio
# ---------------------------------------------------------------------------

def test_divergencia_contra_o_publicado_aborta(tmp_path, monkeypatch):
    """`mart_qualidade_registro_municipio` foi publicado, baixado e tem checksum.

    Reproduzi-lo com número diferente não é atualização, é alterar um dado que
    alguém já citou. A guarda existe para isso e nunca tinha sido vista agindo.
    """
    import pipeline_qualidade_registro as pq

    colunas = ["municipio_cod", "obitos_total", "obitos_mal_definidas",
               "pct_mal_definidas", "classificacao"]
    antigo = pd.DataFrame([("350280", 1000, 50, 5.0, "Regular")], columns=colunas)
    antigo.to_parquet(tmp_path / "mart_qualidade_registro_municipio.parquet")
    monkeypatch.setattr(pq, "MARTS", tmp_path)

    novo = antigo.copy()
    novo.loc[0, "obitos_mal_definidas"] = 51        # um óbito de diferença
    with pytest.raises(SystemExit, match="divergências contra o publicado"):
        pq.conferir_contra_publicado(novo)


def test_municipio_a_mais_ou_a_menos_aborta(tmp_path, monkeypatch):
    import pipeline_qualidade_registro as pq

    colunas = ["municipio_cod", "obitos_total", "obitos_mal_definidas",
               "pct_mal_definidas", "classificacao"]
    antigo = pd.DataFrame([("350280", 1000, 50, 5.0, "Regular"),
                           ("353730", 500, 20, 4.0, "Bom")], columns=colunas)
    antigo.to_parquet(tmp_path / "mart_qualidade_registro_municipio.parquet")
    monkeypatch.setattr(pq, "MARTS", tmp_path)
    with pytest.raises(SystemExit, match="conjunto de municípios mudou"):
        pq.conferir_contra_publicado(antigo.head(1))


# ---------------------------------------------------------------------------
# 6. sem estrutura acima do ruído, não há o que agrupar
# ---------------------------------------------------------------------------

def test_matriz_sem_estrutura_impede_a_clusterizacao():
    """Se nenhum componente supera o nulo, agrupar seria agrupar ruído.

    É a guarda que impede o defeito clássico da análise não supervisionada: o
    k-means SEMPRE devolve k grupos, inclusive sobre dados sem grupo nenhum.
    """
    import analise_perfil_mortalidade as ap

    rng = np.random.default_rng(3)
    cids = [f"X{i:02d}" for i in range(30)]
    p = rng.dirichlet(np.ones(len(cids)) * 5)
    contagens = pd.DataFrame(
        np.vstack([rng.multinomial(600, p) for _ in range(200)]), columns=cids)
    conf = pd.DataFrame({"c": rng.normal(size=200)})
    resid = ap.residualizar(
        contagens.div(contagens.sum(axis=1), axis=0).values, conf)
    with pytest.raises(SystemExit, match="não há o que agrupar"):
        ap.escolher_componentes(resid, contagens, conf)
