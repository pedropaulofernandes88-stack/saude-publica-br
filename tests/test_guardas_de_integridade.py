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


# ---------------------------------------------------------------------------
# 7. as guardas que eu tinha chamado de "operacionais" — e duas não são
# ---------------------------------------------------------------------------
# Na primeira varredura deixei cinco de fora dizendo que testá-las exercitaria o
# mock e não a lógica. Estava errado em pelo menos duas: "consulta devolveu zero
# linhas" impede publicar uma tabela VAZIA, e o HTTP do SIOPS impede reportar
# sucesso sem ter escrito nada. As duas são a classe de defeito que o projeto
# mais teme — processo que termina com exit 0 tendo perdido o dado.
#
# As outras três são de credencial, e mesmo essas valem: a mensagem é o que
# distingue "faltou configurar" de "está quebrado", e mensagem errada custa uma
# investigação inteira no lugar errado.


class _Resposta:
    """Resposta HTTP mínima, no formato que o código consome."""

    def __init__(self, status=200, corpo=None, texto=""):
        self.status_code = status
        self._corpo = corpo if corpo is not None else []
        self.text = texto

    def json(self):
        return self._corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_exportar_tabela_sem_pk_aborta_antes_de_consultar(monkeypatch):
    """Sem PK não há ORDER BY determinístico, e paginar assim corrompe.

    É a guarda nascida do defeito que originou este projeto de integridade:
    `mart_internacoes_municipio` saiu com 334.769 linhas e 212.893 chaves
    distintas, e o TOTAL bateu com o banco porque as repetidas ocuparam o lugar
    das que sumiram.
    """
    import _publicacao

    monkeypatch.setattr(_publicacao, "chaves_primarias", lambda: {})
    chamou = []
    monkeypatch.setattr(_publicacao.requests, "get",
                        lambda *a, **k: chamou.append(1) or _Resposta())
    with pytest.raises(RuntimeError, match="sem chave primária conhecida"):
        _publicacao.exportar_do_postgres(
            "mart_x", {"SUPABASE_URL": "http://x", "SUPABASE_ANON_KEY": "k"},
            Path("/tmp/x.parquet"))
    assert not chamou, "abortou, mas ainda assim consultou o banco"


def test_consulta_vazia_aborta_em_vez_de_gravar_parquet_vazio(tmp_path, monkeypatch):
    """Tabela vazia gravada com sucesso é o pior resultado possível.

    Ela passa em contagem (0 == 0), tem SHA-256 válido, e substitui um arquivo
    bom por um vazio sem que nada acuse. É a mesma família de
    "ausência tratada como sucesso" que fez MA/2023 perder cinco meses.
    """
    import _publicacao

    monkeypatch.setattr(_publicacao, "chaves_primarias",
                        lambda: {"mart_x": ["municipio_cod"]})
    monkeypatch.setattr(_publicacao.requests, "get", lambda *a, **k: _Resposta(corpo=[]))
    destino = tmp_path / "mart_x.parquet"
    with pytest.raises(RuntimeError, match="zero linhas"):
        _publicacao.exportar_do_postgres(
            "mart_x", {"SUPABASE_URL": "http://x", "SUPABASE_ANON_KEY": "k"}, destino)
    assert not destino.exists(), "abortou, mas o arquivo vazio foi gravado"


def test_exportacao_normal_grava_e_ordena_pela_pk(tmp_path, monkeypatch):
    """A guarda tem de deixar o caminho bom passar, e ordenado pela chave."""
    import _publicacao

    monkeypatch.setattr(_publicacao, "chaves_primarias",
                        lambda: {"mart_x": ["municipio_cod"]})
    parametros = {}

    def _get(*a, **k):
        parametros.update(k.get("params", {}))
        return _Resposta(corpo=[{"municipio_cod": "350280", "v": 1}])

    monkeypatch.setattr(_publicacao.requests, "get", _get)
    destino = tmp_path / "mart_x.parquet"
    _publicacao.exportar_do_postgres(
        "mart_x", {"SUPABASE_URL": "http://x", "SUPABASE_ANON_KEY": "k"}, destino)
    assert destino.exists()
    assert parametros.get("order") == "municipio_cod.asc"


def test_chave_de_escrita_ausente_aborta_a_publicacao():
    """Subir ao Storage sem chave falharia adiante, com erro pior de ler."""
    import _publicacao

    with pytest.raises(SystemExit, match="chave de escrita"):
        _publicacao._chave_escrita({})


def test_cobertura_sem_chave_de_servico_aborta_e_explica_por_que(monkeypatch):
    """A mensagem é a parte útil: sem ela alguém troca a chave certa por outra.

    O OpenAPI do PostgREST só responde ao `service_role`; com a chave anônima a
    resposta é um erro que NÃO parece de permissão.
    """
    import validar_camadas

    with pytest.raises(RuntimeError, match="OpenAPI do PostgREST"):
        validar_camadas.tabelas_servidas({"SUPABASE_URL": "http://x"})


def test_upload_do_siops_com_erro_do_cliente_aborta_sem_repetir(monkeypatch):
    """4xx não melhora com retentativa: repetir só atrasa o erro.

    E o essencial é que ABORTE — um upload que falha e não levanta faz o
    pipeline imprimir "concluído" tendo escrito nada.
    """
    import pipeline_siops

    tentativas = []
    monkeypatch.setattr(pipeline_siops, "chave_escrita", lambda env: "k")
    monkeypatch.setattr(pipeline_siops.requests, "post",
                        lambda *a, **k: tentativas.append(1) or _Resposta(400, texto="ruim"))
    monkeypatch.setattr(pipeline_siops.time, "sleep", lambda s: None)
    df = pd.DataFrame({"municipio_cod": ["350280"], "ano": [2024]})
    with pytest.raises(RuntimeError, match="HTTP 400"):
        pipeline_siops.publicar(df, {"SUPABASE_URL": "http://x"}, [2024])
    assert len(tentativas) == 1, f"4xx não deve ser repetido, houve {len(tentativas)}"


def test_upload_do_siops_repete_erro_de_servidor_e_desiste_no_limite(monkeypatch):
    """5xx é transitório e merece retentativa — mas com fim.

    Sem o limite, uma indisponibilidade prolongada travaria o pipeline em vez de
    falhar. Quatro tentativas é o que o código promete.
    """
    import pipeline_siops

    tentativas = []
    monkeypatch.setattr(pipeline_siops, "chave_escrita", lambda env: "k")
    monkeypatch.setattr(pipeline_siops.requests, "post",
                        lambda *a, **k: tentativas.append(1) or _Resposta(503, texto="fora"))
    monkeypatch.setattr(pipeline_siops.time, "sleep", lambda s: None)
    df = pd.DataFrame({"municipio_cod": ["350280"], "ano": [2024]})
    with pytest.raises(RuntimeError, match="HTTP 503"):
        pipeline_siops.publicar(df, {"SUPABASE_URL": "http://x"}, [2024])
    assert len(tentativas) == 4, f"esperado 4 tentativas, houve {len(tentativas)}"


# --------------------------------------------------------------------------
# o denominador é resolvido por padrão, não por ano cravado
#
# `populacao_2015_2024.parquet` virou `populacao_2015_2025.parquet` quando 2025
# entrou, e dois scripts que liam o nome literal passaram a apontar para um
# arquivo inexistente — sem que nada acusasse, porque eles só rodam sob demanda.
# --------------------------------------------------------------------------
def test_populacao_escolhe_a_janela_mais_recente(tmp_path):
    from _sim_obitos import caminho_populacao
    for nome in ("populacao_2015_2024.parquet", "populacao_2015_2025.parquet",
                 "populacao_2010_2014.parquet"):
        (tmp_path / nome).touch()
    assert caminho_populacao(tmp_path).name == "populacao_2015_2025.parquet"


def test_populacao_ausente_falha_alto_em_vez_de_silenciar(tmp_path):
    from _sim_obitos import caminho_populacao
    with pytest.raises(SystemExit) as e:
        caminho_populacao(tmp_path)
    assert "pipeline_v2" in str(e.value)


def test_o_denominador_publicado_cobre_todos_os_anos_da_base():
    """Se a população parar antes dos óbitos, a taxa some ou fica errada."""
    import pandas as pd
    from _sim_obitos import ANOS_COBERTOS
    caminho = Path(__file__).resolve().parent.parent / "data" / "refs"
    from _sim_obitos import caminho_populacao
    if not caminho.exists():
        pytest.skip("data/refs ausente")
    pop = pd.read_parquet(caminho_populacao(caminho), columns=["ano"])
    faltando = sorted(set(ANOS_COBERTOS) - set(pop.ano.unique()))
    assert not faltando, f"sem denominador para {faltando}"


# --------------------------------------------------------------------------
# a carga confere LENDO DE VOLTA, não contando o que tentou enviar
#
# Em 2026-09-03 uma carga de mart_mortalidade_municipio foi interrompida no
# meio: 17.601 das 201.760 linhas de 2025 entraram. O log dizia "linhas
# publicadas" porque imprimia len(recs) — o tamanho do que saiu daqui, que não
# é evidência de nada sobre o outro lado.
# --------------------------------------------------------------------------
class _Resp:
    def __init__(self, status, headers=None):
        self.status_code, self.headers, self.text = status, headers or {}, ""


def _subir_com_banco_em(monkeypatch, no_banco: int, enviadas: int):
    import _subir_mart as sm
    monkeypatch.setattr(sm, "load_env",
                        lambda: {"SUPABASE_URL": "https://x", "SUPABASE_SERVICE_ROLE_KEY": "k"})
    monkeypatch.setattr(sm, "chave_escrita", lambda env: "k")
    monkeypatch.setattr(sm.requests, "post", lambda *a, **k: _Resp(201))
    monkeypatch.setattr(sm.requests, "get", lambda *a, **k:
                        _Resp(206, {"Content-Range": f"0-0/{no_banco}"}))
    df = pd.DataFrame({"municipio_cod": [f"{i:06d}" for i in range(enviadas)],
                       "obitos": range(enviadas)})
    sm.subir("mart_teste", df)


def test_carga_parcial_e_recusada(monkeypatch):
    with pytest.raises(RuntimeError) as e:
        _subir_com_banco_em(monkeypatch, no_banco=17_601, enviadas=201_760)
    msg = str(e.value)
    assert "INCOMPLETA" in msg and "184,159" in msg


def test_carga_completa_passa(monkeypatch):
    _subir_com_banco_em(monkeypatch, no_banco=500, enviadas=500)


def test_banco_maior_que_o_parquet_passa_mas_avisa(monkeypatch, capsys):
    """A tabela pode ter linhas que este parquet não cobre — isso não é falha."""
    _subir_com_banco_em(monkeypatch, no_banco=900, enviadas=500)
    assert "há linhas que este recorte não cobre" in capsys.readouterr().out


def test_recorte_de_um_ano_nao_acusa_carga_incompleta_falsa(monkeypatch):
    """Subir só 2025 não pode reprovar por causa dos anos que já estavam lá.

    Sem `ja_no_banco`, a conferência compararia 201.760 enviadas com 1.306.442
    no banco e diria que sobraram linhas — ou, no sentido contrário, subir um
    recorte pequeno num banco cheio pareceria sempre carga a mais.
    """
    import _subir_mart as sm
    monkeypatch.setattr(sm, "load_env",
                        lambda: {"SUPABASE_URL": "https://x", "SUPABASE_SERVICE_ROLE_KEY": "k"})
    monkeypatch.setattr(sm, "chave_escrita", lambda env: "k")
    monkeypatch.setattr(sm.requests, "post", lambda *a, **k: _Resp(201))
    monkeypatch.setattr(sm.requests, "get", lambda *a, **k:
                        _Resp(206, {"Content-Range": "0-0/1306442"}))
    df = pd.DataFrame({"municipio_cod": [f"{i:06d}" for i in range(201_760)],
                       "obitos": range(201_760)})
    sm.subir("mart_teste", df, ja_no_banco=1_104_682)  # não levanta


def test_recorte_de_um_ano_ainda_pega_carga_curta(monkeypatch):
    import _subir_mart as sm
    monkeypatch.setattr(sm, "load_env",
                        lambda: {"SUPABASE_URL": "https://x", "SUPABASE_SERVICE_ROLE_KEY": "k"})
    monkeypatch.setattr(sm, "chave_escrita", lambda env: "k")
    monkeypatch.setattr(sm.requests, "post", lambda *a, **k: _Resp(201))
    monkeypatch.setattr(sm.requests, "get", lambda *a, **k:
                        _Resp(206, {"Content-Range": "0-0/1122283"}))
    df = pd.DataFrame({"municipio_cod": [f"{i:06d}" for i in range(201_760)],
                       "obitos": range(201_760)})
    with pytest.raises(RuntimeError, match="INCOMPLETA"):
        sm.subir("mart_teste", df, ja_no_banco=1_104_682)


# --------------------------------------------------------------------------
# "Publicada ≠ servida" precisa valer nos DOIS sentidos
#
# NAO_SERVIDAS lista as tabelas que ficam só em Parquet — cada uma saiu do
# Postgres por uma decisão medida (custo em MB contra buscas no índice), e o
# motivo está escrito ao lado da lista.
#
# Em 2026-09-03 um script tentou subir `mart_correlacao_causas` e recebeu
# PGRST205, "could not find the table". Eu li isso como tabela faltando e a
# recriei — desfazendo a decisão documentada dez linhas acima da lista, e
# devolvendo 12 MB a um banco que estava a 10 MB do teto.
#
# Um 404 pode significar "falta criar" ou "não deve existir". As duas coisas
# são indistinguíveis pela mensagem; quem decide é a lista. Esta guarda faz a
# lista valer.
# --------------------------------------------------------------------------
def test_nenhum_script_sobe_tabela_que_nao_deve_ser_servida():
    """Nenhum POST ao PostgREST pode ter por alvo uma tabela de NAO_SERVIDAS."""
    from _publicacao import NAO_SERVIDAS
    ofensas = []
    for arq in sorted((RAIZ / "scripts").glob("*.py")):
        for n, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
            if linha.lstrip().startswith("#"):
                continue
            if "rest/v1/" not in linha:
                continue
            for nome in NAO_SERVIDAS:
                if f"rest/v1/{nome}" in linha:
                    ofensas.append(f"{arq.name}:{n}: sobe {nome}")
    assert not ofensas, (
        "script subindo tabela declarada NAO_SERVIDA — ela é publicada em "
        "Parquet e deliberadamente fora do Postgres. Se a decisão mudou, tire "
        "o nome de NAO_SERVIDAS dizendo por quê:\n  " + "\n  ".join(ofensas))


def test_subir_mart_recusa_tabela_nao_servida(monkeypatch, capsys):
    """`_subir_mart.py <nao_servida>` tem de parar antes de tocar na rede."""
    import _subir_mart as sm
    from _publicacao import NAO_SERVIDAS
    alvo = sorted(NAO_SERVIDAS)[0]
    monkeypatch.setattr(sys, "argv", ["_subir_mart.py", alvo])
    def _explode(*a, **k):
        raise AssertionError("chegou à rede — a recusa não aconteceu")
    monkeypatch.setattr(sm.requests, "post", _explode)
    with pytest.raises(SystemExit) as e:
        sm.main()
    assert "NAO_SERVIDA" in str(e.value) or "não servida" in str(e.value)
