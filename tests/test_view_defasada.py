"""A quarta guarda de integridade: a única que alcança VIEW.

As três guardas de `test_publicacao.py` comparam o arquivo publicado com a
FONTE que o produziu — contagem, unicidade de chave e `not null`. Nenhuma
alcança view, porque view não tem produtor: ela é recalculada a cada consulta,
e republicar uma base altera todos os VALORES sem alterar a CONTAGEM nem as
COLUNAS.

`mart_icsap_pares` já ficou seis dias publicado assim: 22.280 linhas antes e
depois, SHA-256 coerente com o próprio arquivo, e 9.346 linhas (42%) diferentes
do que o banco devolvia.

O que torna a detecção possível é `publicada_em`: ela aponta para a publicação
em que os BYTES daquele arquivo entraram, e é herdada enquanto o conteúdo não
muda. Base cuja publicação está À FRENTE da do arquivo da view é exatamente a
condição de defasagem.

A primeira versão desta guarda comparava contra o carimbo `bases_em`, e teria
nascido DORMENTE: a única view do projeto é sempre herdada, nunca receberia
carimbo, e a conferência passaria para sempre sem nada a comparar. `bases_em`
ficou pelo que de fato acrescenta — deixar a conferência auditável offline por
quem lê o JSON no git, sem o banco nem a definição da view à mão.

  1. as bases saem do `schema.sql` versionado, e CTE não conta como base;
  2. base à frente do arquivo da view reprova; base atrás ou igual, não;
  3. a conferência do estado publicado roda SEMPRE — é a que importa.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from _publicacao import (  # noqa: E402
    ORIGEM_VIEW,
    Tabela,
    bases_de_view,
    conferir_view_atual,
)


def _t(nome: str, publicada_em: str, bases: dict[str, str] | None = None) -> Tabela:
    return Tabela(
        nome=nome, linhas=1, bytes=1, sha256="x", colunas=["a"],
        origem=ORIGEM_VIEW if bases is not None else "pipeline",
        publicada_em=publicada_em, bases_em=bases or {},
    )


# --------------------------------------------------------------------------
# 1. as bases vêm do esquema versionado
# --------------------------------------------------------------------------
def test_as_bases_saem_do_schema_e_batem_com_a_view_real():
    bases = bases_de_view("mart_icsap_pares")
    assert bases == ["dim_cluster_municipio", "mart_icsap_municipio",
                     "mart_internacoes_agravo"], bases


def test_cte_nao_e_confundido_com_base():
    """A view usa `FROM base b` e `JOIN medianas m`, que são CTEs.

    Eles caem na interseção com as tabelas que o `schema.sql` declara — e é por
    isso que a lista sai do esquema, não de um regex sobre o FROM.
    """
    bases = bases_de_view("mart_icsap_pares")
    for cte in ("base", "medianas", "calc", "parametros"):
        assert cte not in bases


def test_view_inexistente_devolve_lista_vazia_em_vez_de_explodir():
    assert bases_de_view("mart_que_nao_existe") == []


# --------------------------------------------------------------------------
# 2. a conferência
# --------------------------------------------------------------------------
def test_base_a_frente_da_view_reprova():
    tabelas = {
        "mart_icsap_municipio": _t("mart_icsap_municipio", "2026-09-10"),
        "v": _t("v", "2026-09-06", {"mart_icsap_municipio": "2026-08-31"}),
    }
    motivos = conferir_view_atual(tabelas["v"], tabelas, ["mart_icsap_municipio"])
    assert len(motivos) == 1
    assert "2026-08-31" in motivos[0] and "2026-09-10" in motivos[0]


def test_base_igual_ou_atras_passa():
    tabelas = {
        "mart_icsap_municipio": _t("mart_icsap_municipio", "2026-08-31"),
        "v": _t("v", "2026-09-06", {"mart_icsap_municipio": "2026-08-31"}),
    }
    assert conferir_view_atual(tabelas["v"], tabelas, ["mart_icsap_municipio"]) == []


def test_sufixo_de_republicacao_no_mesmo_dia_e_detectado():
    """Os ids são "2026-09-06" e "2026-09-06.2" — a ordem alfabética resolve,
    e é como o resto do módulo já os compara."""
    tabelas = {
        "b": _t("b", "2026-09-06.2"),
        "v": _t("v", "2026-09-06", {"b": "2026-09-06"}),
    }
    assert conferir_view_atual(tabelas["v"], tabelas, ["b"]) != []


def test_base_ausente_do_manifesto_nao_gera_falso_alarme():
    """Base fora do manifesto (ex.: recorte `--tabelas`) não é evidência de
    defasagem — é ausência de evidência."""
    v = _t("v", "2026-09-06", {"sumiu": "2026-08-31"})
    assert conferir_view_atual(v, {"v": v}, ["sumiu"]) == []


def test_view_sem_bases_registradas_passa():
    """Manifesto antigo, anterior ao campo, não pode reprovar retroativamente."""
    v = _t("v", "2026-09-06", {})
    assert conferir_view_atual(v, {"v": v}, []) == []


# --------------------------------------------------------------------------
# 3. o estado publicado hoje
# --------------------------------------------------------------------------
@pytest.mark.skipif(not (RAIZ / "data" / "publicacoes" / "atual.json").exists(),
                    reason="sem publicação local")
def test_a_view_publicada_hoje_nao_esta_defasada():
    import json
    d = RAIZ / "data" / "publicacoes"
    atual = json.loads((d / "atual.json").read_text(encoding="utf-8"))
    man = json.loads((d / atual["arquivo"]).read_text(encoding="utf-8"))
    tabelas = {n: Tabela(**v) for n, v in man["tabelas"].items()}
    views = [n for n, t in tabelas.items() if t.origem == ORIGEM_VIEW]
    assert views, "nenhuma view no manifesto — a guarda perdeu o alvo"
    for nome in views:
        # Roda mesmo sem `bases_em`: a comparação é contra `publicada_em`, que
        # todo manifesto sempre teve. Pular aqui por falta de carimbo deixaria
        # justamente o caso real sem conferência.
        motivos = conferir_view_atual(tabelas[nome], tabelas, bases_de_view(nome))
        assert motivos == [], f"{nome}: " + "; ".join(motivos)


# --------------------------------------------------------------------------
# 4. a armadilha OPOSTA à dormência: a guarda insatisfazível
#
# O desenho original comparava a base contra `publicada_em` da própria view,
# justamente para não depender de um carimbo que nunca chegaria. O problema é
# que `publicada_em` avança apenas quando os BYTES da view mudam — e existe um
# caso legítimo em que eles não mudam: quando a view não usa a coluna que mudou
# na base.
#
# Aconteceu em 2026-09-12. A família SIH ganhou `meses_cobertos`;
# `mart_icsap_pares` não lê essa coluna; a reexportação do banco vivo devolveu
# byte por byte o arquivo de 2026-09-06. A view estava PROVADAMENTE derivada do
# banco atual e a conferência reprovava — sem reexportação capaz de satisfazê-la.
# --------------------------------------------------------------------------
def test_view_regerada_que_sai_identica_deixa_de_travar_a_publicacao():
    """Derivar é o que conta, não mudar. Este é o caso que travava."""
    tabelas = {
        "mart_icsap_municipio": _t("mart_icsap_municipio", "2026-09-12.6"),
        # bytes idênticos aos de 2026-09-06, mas derivada AGORA, das bases atuais
        "v": _t("v", "2026-09-06", {"mart_icsap_municipio": "2026-09-12.6"}),
    }
    assert conferir_view_atual(tabelas["v"], tabelas, ["mart_icsap_municipio"]) == []


def test_a_guarda_nao_ficou_dormente_sem_carimbo():
    """A metade que o desenho original protegia, e que tem de continuar valendo.

    View sem `bases_em` — nunca derivada desde que o campo existe — cai no
    `publicada_em` e continua sendo conferida. Sem este teste, a correção acima
    poderia ter trocado uma guarda insatisfazível por uma que nunca reprova.
    """
    tabelas = {
        "mart_icsap_municipio": _t("mart_icsap_municipio", "2026-09-12"),
        "v": Tabela(nome="v", linhas=1, bytes=1, sha256="x", colunas=["a"],
                    origem=ORIGEM_VIEW, publicada_em="2026-09-06"),
    }
    motivos = conferir_view_atual(tabelas["v"], tabelas, ["mart_icsap_municipio"])
    assert len(motivos) == 1
    assert "2026-09-06" in motivos[0]


def test_carimbo_anterior_a_base_continua_reprovando():
    """Carimbo velho não absolve: derivação ANTES da base ainda é defasagem."""
    tabelas = {
        "mart_icsap_municipio": _t("mart_icsap_municipio", "2026-09-12"),
        "v": _t("v", "2026-09-11", {"mart_icsap_municipio": "2026-09-01"}),
    }
    assert conferir_view_atual(tabelas["v"], tabelas, ["mart_icsap_municipio"])
