"""A guarda do identificador de pessoa, vista reprovando E aprovando.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Em 2026-09-21 o projeto passou a ligar registros do SIA/SUS por `AP_CNSPCN`.
O campo é **ofuscado, não criptografado** — 15 bytes na faixa `0x7B`–`0x84`, que
é a assinatura de dígito deslocado por constante. Não existe barreira técnica
entre ele e o CNS real; existe uma decisão.

Enquanto essa decisão for disciplina de quem escreve o script, ela vale até o
primeiro dia distraído. Aqui ela vira guarda, e a guarda é exercitada nos dois
sentidos, porque este projeto já inventariou 14 guardas que nunca tinham sido
vistas dizendo não — e três delas não funcionavam.

O teste de mutação no fim é o que impede a guarda de virar enfeite: ele quebra
o detector de propósito e exige que algum teste acuse.

Nenhum teste aqui acessa rede.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import _identificador  # noqa: E402
from _identificador import (  # noqa: E402
    AMOSTRA,
    COMPRIMENTO_CNS,
    FAIXA_OFUSCADA,
    IdentificadorVazado,
    conferir_sem_identificador,
)

# Valores com a assinatura real, construídos a partir da faixa documentada em
# vez de copiados do dado — copiar seria versionar identificador para testar a
# guarda que proíbe versionar identificador.
FAIXA = sorted(FAIXA_OFUSCADA)


def cns_ofuscado(semente: int) -> str:
    return "".join(FAIXA[(semente * (i + 3)) % len(FAIXA)]
                   for i in range(COMPRIMENTO_CNS))


def coluna_ofuscada(n: int = 200) -> list[str]:
    return [cns_ofuscado(i) for i in range(n)]


# ---------------------------------------------------------------------------
# 1. A guarda REPROVA pela forma, que é o detector principal
# ---------------------------------------------------------------------------

def test_reprova_o_caso_obvio():
    """O caso que motivou o módulo: a chave de junção sobreviveu ao agregado.

    Aqui o nome basta, e a guarda para nele — por isso a mensagem fala do nome
    e não da forma. O teste seguinte é o que exercita o detector principal.
    """
    df = pd.DataFrame({"uf": ["PE"] * 200, "cns": coluna_ofuscada()})
    with pytest.raises(IdentificadorVazado, match="nome reservado"):
        conferir_sem_identificador(df, "mart_ficticio")


def test_reprova_mesmo_com_a_coluna_renomeada():
    """Renomear derrota a lista de nomes. É exatamente o ponto do detector."""
    df = pd.DataFrame({"chave_opaca": coluna_ofuscada(), "apacs": range(200)})
    with pytest.raises(IdentificadorVazado, match="0x7B"):
        conferir_sem_identificador(df, "mart_ficticio")


def test_reprova_cns_em_claro():
    """Decodificar é pior, não melhor — e a guarda precisa dizer isso."""
    df = pd.DataFrame({"id_pac": [f"1{i:014d}" for i in range(200)]})
    with pytest.raises(IdentificadorVazado, match="em claro"):
        conferir_sem_identificador(df, "mart_ficticio")


def test_reprova_pelo_nome_quando_a_forma_nao_denuncia():
    """Segunda linha: coluna vazia ou truncada não tem assinatura nenhuma."""
    df = pd.DataFrame({"ap_cnspcn": [None] * 200, "apacs": range(200)})
    with pytest.raises(IdentificadorVazado, match="nome reservado"):
        conferir_sem_identificador(df, "mart_ficticio")


def test_a_mensagem_diz_o_que_fazer():
    """Guarda que aborta sem dizer o conserto vira contorno na próxima vez."""
    df = pd.DataFrame({"cns": coluna_ofuscada()})
    with pytest.raises(IdentificadorVazado) as e:
        conferir_sem_identificador(df, "mart_ficticio")
    assert "Agregue por pessoa" in str(e.value)


# ---------------------------------------------------------------------------
# 2. A guarda APROVA o dado legítimo — a metade que quase nunca se escreve
# ---------------------------------------------------------------------------

def test_aprova_mart_tipico_do_projeto():
    df = pd.DataFrame({
        "municipio_cod": ["261160", "330455", "355030"],
        "municipio_nome": ["Recife", "Rio de Janeiro", "São Paulo"],
        "uf_sigla": ["PE", "RJ", "SP"],
        "ano": [2024, 2024, 2024],
        "cid3": ["C50", "C61", "C18"],
        "estadiamento": ["ignorado", "4", "2"],
        "apacs": [17867, 20220, 31004],
        "valor_aprovado": [1.2e7, 1.4e7, 2.1e7],
        "meses_cobertos": [12, 12, 12],
    })
    conferir_sem_identificador(df, "mart_apac_oncologia_tratamento")


def test_aprova_codigo_longo_que_nao_e_cns():
    """CNPJ (14) e chave de acesso (44) não podem disparar a guarda."""
    df = pd.DataFrame({
        "cnpj": [f"{i:014d}" for i in range(200)],
        "chave": ["3" * 44] * 200,
    })
    conferir_sem_identificador(df, "mart_ficticio")


def test_aprova_quinze_digitos_com_inicial_invalida():
    """A exigência do dígito inicial é o que torna o detector em claro usável."""
    df = pd.DataFrame({"codigo": [f"3{i:014d}" for i in range(200)]})
    conferir_sem_identificador(df, "mart_ficticio")


def test_aprova_texto_livre_com_acento_e_simbolo():
    """Nome de município tem til e cedilha, e nenhum deles está na faixa."""
    df = pd.DataFrame({
        "nome": ["São Paulo", "Açu", "Poção", "Itaobim~", "Brasília|"] * 40,
    })
    conferir_sem_identificador(df, "mart_ficticio")


def test_aprova_coluna_esparsa_abaixo_do_limiar():
    """Um punhado de valores estranhos não é vazamento — metade da coluna é."""
    df = pd.DataFrame({"campo": coluna_ofuscada(40) + ["C50"] * 160})
    conferir_sem_identificador(df, "mart_ficticio")


@pytest.mark.parametrize("nome", sorted(_identificador.NOMES_PROIBIDOS))
def test_cada_nome_proibido_reprova(nome):
    """Lista de nomes que não é exercitada envelhece sem ninguém notar."""
    df = pd.DataFrame({nome: ["x"] * 10})
    with pytest.raises(IdentificadorVazado):
        conferir_sem_identificador(df, "mart_ficticio")


# ---------------------------------------------------------------------------
# 3. A guarda está PLUGADA — não basta existir no módulo
# ---------------------------------------------------------------------------

def test_escrever_parquet_recusa_o_identificador(tmp_path):
    """O caminho por onde todo mart nasce. Se ela não fecha aqui, não fecha."""
    from _publicacao import escrever_parquet

    df = pd.DataFrame({"cns": coluna_ofuscada(), "apacs": range(200)})
    destino = tmp_path / "mart_ficticio.parquet"
    with pytest.raises(IdentificadorVazado):
        escrever_parquet(df, destino, origem="pipeline")
    assert not destino.exists(), (
        "o arquivo foi criado antes do aborto — a guarda precisa vir ANTES da "
        "escrita, senão o identificador chega ao disco de qualquer jeito")


def test_escrever_parquet_aprova_mart_legitimo(tmp_path):
    from _publicacao import escrever_parquet

    df = pd.DataFrame({"municipio_cod": ["261160"], "apacs": [1]})
    destino = tmp_path / "mart_ficticio.parquet"
    escrever_parquet(df, destino, origem="pipeline")
    assert destino.exists()


def test_publicar_chama_a_guarda():
    """`postgres-bootstrap` não passa por `escrever_parquet`; precisa da 2a passada."""
    fonte = (RAIZ / "scripts" / "publicar.py").read_text(encoding="utf-8")
    assert "conferir_sem_identificador" in fonte, (
        "publicar.py não chama a guarda — tabela reexportada do banco iria ao "
        "Storage sem conferência, e o Storage tem URL pública")


# ---------------------------------------------------------------------------
# 4. Teste de mutação: quebrar o detector tem que fazer algum teste acusar
# ---------------------------------------------------------------------------

def _df_forma_ofuscada() -> pd.DataFrame:
    return pd.DataFrame({"chave_opaca": coluna_ofuscada()})


def _df_forma_em_claro() -> pd.DataFrame:
    return pd.DataFrame({"id_pac": [f"2{i:014d}" for i in range(200)]})


def _df_so_nome() -> pd.DataFrame:
    return pd.DataFrame({"ap_cnspcn": [None] * 200})


#: (peça do detector, valor que a quebra, entrada que SÓ ela pega).
#: Cada linha é a afirmação "sem esta peça, esta entrada passa" — que é o que
#: torna a peça necessária em vez de decorativa.
MUTACOES = [
    ("LIMIAR", 1.01, _df_forma_ofuscada),
    ("LIMIAR", 1.01, _df_forma_em_claro),
    ("FAIXA_OFUSCADA", frozenset("z"), _df_forma_ofuscada),
    ("NOMES_PROIBIDOS", frozenset(), _df_so_nome),
    ("AMOSTRA", 0, _df_forma_ofuscada),
]


@pytest.mark.parametrize("atributo,valor,constroi", MUTACOES,
                         ids=[f"{a}->{c.__name__}" for a, _, c in MUTACOES])
def test_cada_peca_do_detector_carrega_peso(monkeypatch, atributo, valor, constroi):
    """Quebrar a peça tem que deixar passar a entrada que só ela pega.

    Se a entrada continua reprovando com a peça quebrada, ou a peça é redundante
    — e então é código morto se fingindo de guarda — ou o teste está mirando a
    entrada errada. Nos dois casos, alguém precisa olhar.
    """
    df = constroi()

    # Antes da mutação: reprova. Sem isto, o teste passaria mesmo se a entrada
    # nunca tivesse sido detectada por ninguém.
    with pytest.raises(IdentificadorVazado):
        conferir_sem_identificador(df, "mart_ficticio")

    monkeypatch.setattr(_identificador, atributo, valor)
    try:
        conferir_sem_identificador(df, "mart_ficticio")
    except IdentificadorVazado:
        pytest.fail(
            f"com {atributo}={valor!r} a entrada AINDA reprova: essa peça não "
            "é o que a detecta, e pode ser removida sem nenhum teste acusar")


def test_amostra_zero_nao_e_falso_negativo_silencioso():
    """AMOSTRA=0 desliga o detector de forma — o teste acima prova isso.

    Esta asserção fixa a fronteira para que reduzir a amostra por desempenho
    nunca chegue a zero sem alguém ver.
    """
    assert AMOSTRA > 0, "amostra nula desliga o detector principal"


# ---------------------------------------------------------------------------
# 5. A regressão do pandas 3: o detector ficou morto onde ele roda
# ---------------------------------------------------------------------------
#
# A primeira versão pulava a coluna com `if serie.dtype != object: continue`.
# Em pandas 2.3 (local) coluna de texto é `object` e tudo passava; em pandas 3
# (CI) ela é `str`, e o `continue` desligava o detector de forma INTEIRO. A
# guarda de nomes continuava funcionando, o que é o pior caso: parte da suíte
# verde, e a proteção principal desligada.

@pytest.mark.parametrize("dtype", ["object", "string"])
def test_detecta_independente_do_dtype_de_texto(dtype):
    """Pandas muda o dtype padrão de texto entre versões maiores.

    `string` aqui reproduz, em pandas 2, o que pandas 3 faz por padrão.
    """
    s = pd.Series(coluna_ofuscada(), dtype=dtype)
    df = pd.DataFrame({"chave_opaca": s})
    with pytest.raises(IdentificadorVazado, match="0x7B"):
        conferir_sem_identificador(df, "mart_ficticio")


@pytest.mark.parametrize("dtype", ["object", "string"])
def test_detecta_cns_em_claro_independente_do_dtype(dtype):
    s = pd.Series([f"1{i:014d}" for i in range(200)], dtype=dtype)
    with pytest.raises(IdentificadorVazado, match="em claro"):
        conferir_sem_identificador(pd.DataFrame({"id_pac": s}), "mart_ficticio")


@pytest.mark.parametrize("valores,dtype", [
    (list(range(200)), "int64"),
    ([float(i) for i in range(200)], "float64"),
    ([True, False] * 100, "bool"),
    (pd.date_range("2020-01-01", periods=200).tolist(), "datetime64[ns]"),
])
def test_coluna_nao_textual_e_pulada_sem_custo(valores, dtype):
    """A exclusão tem que continuar pulando o que não pode carregar texto."""
    df = pd.DataFrame({"campo": pd.Series(valores, dtype=dtype)})
    conferir_sem_identificador(df, "mart_ficticio")


def test_a_exclusao_por_kind_cobre_os_tipos_numericos():
    """Regressão do critério: `kind` é a letra do numpy, e trocar a lista por
    `!= object` devolve o defeito."""
    import numpy as np

    for valores, esperado_pulado in [
        (np.arange(5), True),
        (np.arange(5, dtype="float32"), True),
        (np.array([True, False]), True),
        (np.array(["a", "b"], dtype=object), False),
    ]:
        s = pd.Series(valores)
        assert (s.dtype.kind in "biufcMm") is esperado_pulado, s.dtype
