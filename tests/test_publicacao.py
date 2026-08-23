"""
Testes do núcleo de publicação (scripts/_publicacao.py).

Cada teste aqui existe por causa de um defeito real, encontrado quando o eixo
canônico passou do Postgres para o Parquet datado:

  * **nenhuma linha de código subia Parquet para o Storage** — a publicação de
    arquivo sempre foi manual, e 14 das 35 tabelas servidas pela API nunca
    tiveram arquivo, enquanto /dados chamava o conjunto de "a base completa";
  * dois arquivos publicados estavam DESATUALIZADOS sem ninguém saber:
    `mart_internacoes_agravo` tinha 52.861 linhas contra 158.041 no banco (66%
    do dado faltando) e `mart_internacoes_municipio` divergia em 167 linhas;
  * a chave `SUPABASE_SERVICE_ROLE_KEY` migrou para o formato opaco
    (`sb_secret_…`) e o Storage passou a rejeitá-la em `Authorization: Bearer`
    com "Invalid Compact JWS", aceitando-a apenas em `apikey`;
  * a flag `--semear` chegou a existir sem ponto de chamada: era aceita pelo
    argparse e não fazia nada.

Nenhum teste acessa rede: o manifesto e os Parquet são sintéticos.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from _publicacao import (  # noqa: E402
    Manifesto,
    Tabela,
    _cabecalho_escrita,
    descrever,
    sha256_de,
)

pytestmark = pytest.mark.unit


@pytest.fixture()
def parquet(tmp_path: Path) -> Path:
    df = pd.DataFrame({
        "municipio_cod": ["350000", "330000", "310000"],
        "ano_mes": ["2024-01", "2024-02", "2024-03"],
        "obitos": [10, 20, 30],
    })
    caminho = tmp_path / "mart_teste.parquet"
    df.to_parquet(caminho, compression="zstd", index=False)
    return caminho


# ---------------------------------------------------------------------------
# Autenticação do Storage
# ---------------------------------------------------------------------------

def test_chave_opaca_nao_vai_em_bearer() -> None:
    """A chave no formato novo só é aceita em `apikey`.

    Mandá-la em `Authorization: Bearer` fez o Storage devolver
    400/AccessDenied "Invalid Compact JWS" — ele tenta parsear como JWS. Foi o
    que quebrou a primeira publicação real.
    """
    cab = _cabecalho_escrita("sb_secret_abc123")
    assert cab["apikey"] == "sb_secret_abc123"
    assert "Authorization" not in cab


def test_jwt_legado_vai_nos_dois_cabecalhos() -> None:
    """Quem ainda usa a chave antiga não pode ser quebrado pela correção."""
    jwt = "eyJhbGciOi.eyJpc3MiOi.assinatura"
    cab = _cabecalho_escrita(jwt)
    assert cab["apikey"] == jwt
    assert cab["Authorization"] == f"Bearer {jwt}"


# ---------------------------------------------------------------------------
# Descrição de uma tabela
# ---------------------------------------------------------------------------

def test_descrever_extrai_linhas_colunas_e_competencia(parquet: Path) -> None:
    t = descrever("mart_teste", parquet, "pipeline", "2026-08-23")
    assert t.linhas == 3
    assert t.colunas == ["ano_mes", "municipio_cod", "obitos"]
    assert (t.competencia_min, t.competencia_max) == ("2024-01", "2024-03")
    assert t.origem == "pipeline"
    assert t.publicada_em == "2026-08-23"
    assert len(t.sha256) == 64


def test_sha256_muda_quando_o_conteudo_muda(tmp_path: Path, parquet: Path) -> None:
    """O SHA-256 é o que decide se uma tabela mudou entre publicações.

    Se ele não reagir ao conteúdo, uma publicação nova herdaria uma entrada
    velha e afirmaria que o dado não mudou quando mudou.
    """
    antes = sha256_de(parquet)
    df = pd.read_parquet(parquet)
    df.loc[0, "obitos"] = 999
    df.to_parquet(parquet, compression="zstd", index=False)
    assert sha256_de(parquet) != antes


def test_competencia_ausente_nao_quebra(tmp_path: Path) -> None:
    """Tabela sem coluna de tempo (dimensões) é descrita sem competência."""
    caminho = tmp_path / "dim_teste.parquet"
    pd.DataFrame({"codigo": ["a", "b"], "nome": ["A", "B"]}).to_parquet(caminho, index=False)
    t = descrever("dim_teste", caminho, "pipeline", "2026-08-23")
    assert t.competencia_min is None and t.competencia_max is None
    assert t.linhas == 2


# ---------------------------------------------------------------------------
# Manifesto
# ---------------------------------------------------------------------------

def _manifesto_exemplo() -> Manifesto:
    m = Manifesto(id="2026-08-23", gerado_em="2026-08-23 12:00 UTC",
                  commit="abc1234", anterior="2026-07-01")
    m.tabelas["mart_a"] = Tabela(
        nome="mart_a", linhas=100, bytes=1024, sha256="a" * 64,
        colunas=["x", "y"], origem="pipeline", publicada_em="2026-08-23",
        competencia_min="2024-01", competencia_max="2024-12")
    m.tabelas["mart_b"] = Tabela(
        nome="mart_b", linhas=50, bytes=512, sha256="b" * 64,
        colunas=["z"], origem="postgres-bootstrap", publicada_em="2026-07-01")
    return m


def test_manifesto_sobrevive_a_ida_e_volta() -> None:
    """Serializar e desserializar não pode perder nada.

    O manifesto é o artefato canônico versionado no git; se a ida e volta
    perder um campo, o repositório passa a descrever mal o que está publicado.
    """
    m = _manifesto_exemplo()
    volta = Manifesto.from_json(m.to_json())
    assert volta.id == m.id and volta.anterior == m.anterior
    assert volta.commit == m.commit
    assert set(volta.tabelas) == set(m.tabelas)
    for nome, t in m.tabelas.items():
        assert volta.tabelas[nome] == t


def test_resumo_conta_por_origem_e_marca_as_novas() -> None:
    """A dívida de proveniência precisa ser visível no resumo.

    `postgres-bootstrap` significa que o arquivo foi reexportado do banco — ou
    seja, o eixo ainda não migrou para aquela tabela. Contar por origem é o que
    torna essa dívida mensurável em vez de silenciosa.
    """
    r = _manifesto_exemplo().resumo()
    assert r["n_tabelas"] == 2
    assert r["n_linhas"] == 150
    assert r["por_origem"] == {"pipeline": 1, "postgres-bootstrap": 1}
    # Só `mart_a` entrou nesta publicação; `mart_b` foi herdada de julho.
    assert r["novas_nesta_publicacao"] == ["mart_a"]


def test_caminho_historico_aponta_para_a_publicacao_de_origem() -> None:
    """Tabela herdada aponta para onde os bytes realmente estão.

    É o que permite não duplicar no Storage o que não mudou, sem que o
    manifesto deixe de ser completo.
    """
    m = _manifesto_exemplo()
    assert m.tabelas["mart_a"].caminho_historico() == "hist/2026-08-23/mart_a.parquet"
    assert m.tabelas["mart_b"].caminho_historico() == "hist/2026-07-01/mart_b.parquet"


def test_manifesto_e_json_valido_e_ordenado() -> None:
    """Ordenar por nome mantém o diff do git legível entre publicações."""
    texto = _manifesto_exemplo().to_json()
    d = json.loads(texto)
    assert list(d["tabelas"]) == sorted(d["tabelas"])
    assert d["resumo"]["n_tabelas"] == 2


def test_salvar_grava_manifesto_e_ponteiro(tmp_path: Path, monkeypatch) -> None:
    """`atual.json` é ponteiro, não cópia.

    Duplicar o manifesto criaria duas verdades sobre qual é a publicação
    corrente, e elas divergiriam na primeira falha parcial.
    """
    import _publicacao
    monkeypatch.setattr(_publicacao, "PUBLICACOES", tmp_path)
    m = _manifesto_exemplo()
    destino = m.salvar()
    assert destino.name == "2026-08-23.json"
    ponteiro = json.loads((tmp_path / "atual.json").read_text(encoding="utf-8"))
    assert ponteiro == {"id": "2026-08-23", "arquivo": "2026-08-23.json"}
    # O ponteiro não contém as tabelas — só aponta.
    assert "tabelas" not in ponteiro


# ---------------------------------------------------------------------------
# Ambiente
# ---------------------------------------------------------------------------

def test_variavel_vazia_conta_como_ausente(monkeypatch, tmp_path: Path) -> None:
    """`${{ secrets.X }}` vira string VAZIA quando o segredo não existe.

    O repositório não tem nenhum segredo configurado, então o GitHub Actions
    exportou SUPABASE_URL="" e o `setdefault` não disparou — a chave existia,
    só estava vazia. O script montou URL a partir de "" e o primeiro job de CI
    quebrou com "Invalid URL: No schema supplied".
    """
    import _publicacao
    monkeypatch.setattr(_publicacao, "ROOT", tmp_path)   # sem .env
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")

    env = _publicacao.carregar_env()
    assert env["SUPABASE_URL"] == _publicacao.URL_PUBLICA
    assert env["SUPABASE_ANON_KEY"] == _publicacao.ANON_PUBLICA
    # A chave de ESCRITA nunca ganha padrão: vazia continua ausente.
    assert not env.get("SUPABASE_SERVICE_ROLE_KEY")


def test_chave_de_escrita_nunca_tem_padrao(monkeypatch, tmp_path: Path) -> None:
    """Um padrão para a chave de escrita seria um segredo no repositório."""
    import _publicacao
    monkeypatch.setattr(_publicacao, "ROOT", tmp_path)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert "SUPABASE_SERVICE_ROLE_KEY" not in _publicacao.carregar_env()


# ---------------------------------------------------------------------------
# Integridade da chave primária
# ---------------------------------------------------------------------------

def test_guarda_recusa_parquet_com_pk_duplicada() -> None:
    """Duplicata na PK é impossível na tabela de origem: se está no arquivo, o
    arquivo está errado.

    Esta guarda faltava, e custou caro. O exportador paginava com LIMIT/OFFSET
    sem ORDER BY — ordem indefinida no Postgres — e páginas consecutivas se
    sobrepuseram: `mart_internacoes_municipio` saiu com 334.769 linhas e apenas
    212.893 chaves distintas. O TOTAL bateu com o banco, porque as linhas
    repetidas ocuparam o lugar das que sumiram, então a checagem de contagem
    passou e o arquivo corrompido foi publicado. Só a violação de PK no rebuild
    pegou.
    """
    import _publicacao

    df = pd.DataFrame({
        "municipio_cod": ["350000", "350000", "330000"],
        "ano": [2024, 2024, 2024],
        "obitos": [10, 10, 20],
    })
    with pytest.raises(RuntimeError, match="corrompido"):
        _publicacao.conferir_chave_unica("mart_x", df, ["municipio_cod", "ano"])


def test_guarda_aceita_parquet_integro() -> None:
    import _publicacao

    df = pd.DataFrame({
        "municipio_cod": ["350000", "330000"],
        "ano": [2024, 2024],
        "obitos": [10, 20],
    })
    _publicacao.conferir_chave_unica("mart_x", df, ["municipio_cod", "ano"])


def test_pk_ausente_no_dataframe_nao_quebra() -> None:
    """View publicada pode não trazer todas as colunas da PK da tabela base."""
    import _publicacao

    _publicacao.conferir_chave_unica("v", pd.DataFrame({"a": [1, 1]}), ["b", "c"])


def test_chaves_primarias_saem_do_schema_versionado() -> None:
    """A ordenação da exportação segue o esquema, não uma lista escrita à mão."""
    import _publicacao

    pks = _publicacao.chaves_primarias()
    if not pks:
        pytest.skip("schema.sql ainda não foi gerado")
    assert pks["mart_mortalidade_municipio"] == [
        "municipio_cod", "ano", "capitulo_cid", "sexo"]
    assert all(isinstance(v, list) and v for v in pks.values())


# ---------------------------------------------------------------------------
# Linhagem gravada no arquivo
# ---------------------------------------------------------------------------

def test_proveniencia_viaja_com_os_bytes(tmp_path: Path) -> None:
    """A origem vai DENTRO do Parquet, não num sidecar ao lado.

    `data/marts/.origem.json` é ignorado pelo git e some quando alguém limpa o
    diretório ou publica de outra máquina. Quem recebe o arquivo precisa poder
    dizer de onde ele veio olhando só para ele.
    """
    import _publicacao

    caminho = tmp_path / "t.parquet"
    df = pd.DataFrame({"a": [1, 2, 3]})
    _publicacao.escrever_parquet(df, caminho, "pipeline", "scripts/x.py")

    assert _publicacao.origem_do_parquet(caminho) == "pipeline"
    # E o conteúdo continua intacto e legível por quem não sabe do metadado.
    assert len(pd.read_parquet(caminho)) == 3


def test_parquet_sem_metadado_nao_mente_origem(tmp_path: Path) -> None:
    """Arquivo sem proveniência declarada devolve None, nunca 'pipeline'.

    Assumir pipeline por omissão foi o defeito real:
    `mart_demanda_mensal_hospital` foi BAIXADO do Postgres e entrou no manifesto
    rotulado como produzido pelo pipeline.
    """
    import _publicacao

    caminho = tmp_path / "sem_meta.parquet"
    pd.DataFrame({"a": [1]}).to_parquet(caminho, index=False)
    assert _publicacao.origem_do_parquet(caminho) is None
    assert _publicacao.ORIGEM_DESCONHECIDA != "pipeline"


def test_acumular_funde_competencia_sem_duplicar(tmp_path: Path, monkeypatch) -> None:
    """O arquivo passa a acumular como o banco acumula por upsert.

    Os pipelines do SIH processam um ano por execução e SOBRESCREVIAM o
    Parquet. Medido antes da correção: `mart_internacoes_agravo` tinha 52.861
    linhas no arquivo contra 158.041 no banco. Era esta a razão estrutural de o
    arquivo não poder ser canônico.
    """
    import _publicacao

    monkeypatch.setattr(_publicacao, "chaves_primarias",
                        lambda: {"mart_x": ["municipio_cod", "ano"]})
    destino = tmp_path / "mart_x.parquet"

    a2022 = pd.DataFrame({"municipio_cod": ["350000", "330000"],
                          "ano": [2022, 2022], "v": [1, 2]})
    _, antes, depois = _publicacao.acumular_parquet(
        a2022, destino, "mart_x", "pipeline")
    assert (antes, depois) == (0, 2)

    a2023 = pd.DataFrame({"municipio_cod": ["350000", "330000"],
                          "ano": [2023, 2023], "v": [3, 4]})
    _, antes, depois = _publicacao.acumular_parquet(
        a2023, destino, "mart_x", "pipeline")
    assert (antes, depois) == (2, 4), "a competência nova tem de somar, não substituir"

    # Reprocessar 2022 SUBSTITUI aquele ano, não duplica — semântica do upsert.
    a2022_corrigido = pd.DataFrame({"municipio_cod": ["350000", "330000"],
                                    "ano": [2022, 2022], "v": [10, 20]})
    _, antes, depois = _publicacao.acumular_parquet(
        a2022_corrigido, destino, "mart_x", "pipeline")
    assert (antes, depois) == (4, 4)
    final = pd.read_parquet(destino)
    assert final[(final.ano == 2022) & (final.municipio_cod == "350000")].v.iloc[0] == 10
    assert _publicacao.origem_do_parquet(destino) == "pipeline"


def test_acumular_exige_chave_completa(tmp_path: Path, monkeypatch) -> None:
    """Sem a chave inteira não há como saber o que substituir."""
    import _publicacao

    monkeypatch.setattr(_publicacao, "chaves_primarias",
                        lambda: {"mart_x": ["municipio_cod", "ano"]})
    with pytest.raises(RuntimeError, match="chave completa"):
        _publicacao.acumular_parquet(
            pd.DataFrame({"municipio_cod": ["1"]}), tmp_path / "x.parquet",
            "mart_x", "pipeline")
