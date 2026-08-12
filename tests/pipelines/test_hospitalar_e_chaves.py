"""
Testes das funções puras do pipeline hospitalar e da seleção de chave do Supabase.

A seleção de chave está aqui porque foi o segundo defeito que derrubou o
reprocessamento em 11/08/2026: os pipelines escreviam com a chave `anon`, que é
pública, e o upload passou a levar 401 quando parte do schema foi endurecida.
Um teste de três linhas separa "escrevo com service_role" de "caí para anon".
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _supabase_key  # noqa: E402

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Seleção de chave — o defeito do 401
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _limpa_estado(monkeypatch):
    """Zera o aviso memorizado e o ambiente entre casos."""
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    _supabase_key._avisado = False
    yield
    _supabase_key._avisado = False


def test_escrita_prefere_service_role():
    env = {"SUPABASE_SERVICE_ROLE_KEY": "sb_secret_xxx", "SUPABASE_ANON_KEY": "anon_yyy"}
    assert _supabase_key.chave_escrita(env) == "sb_secret_xxx"


def test_escrita_cai_para_anon_com_aviso(capsys):
    """Fallback existe para não quebrar quem ainda não configurou — mas tem de avisar."""
    assert _supabase_key.chave_escrita({"SUPABASE_ANON_KEY": "anon_yyy"}) == "anon_yyy"
    saida = capsys.readouterr().out
    assert "AVISO" in saida and "PUBLICA" in saida


def test_aviso_sai_uma_vez_so(capsys):
    env = {"SUPABASE_ANON_KEY": "anon_yyy"}
    _supabase_key.chave_escrita(env)
    capsys.readouterr()
    _supabase_key.chave_escrita(env)
    assert capsys.readouterr().out == ""


def test_sem_chave_nenhuma_falha_alto():
    """Melhor parar do que tentar publicar sem credencial e receber 401 no meio."""
    with pytest.raises(SystemExit) as e:
        _supabase_key.chave_escrita({})
    assert "SUPABASE_SERVICE_ROLE_KEY" in str(e.value)


def test_variavel_de_ambiente_supre_o_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "do_ambiente")
    assert _supabase_key.chave_escrita({}) == "do_ambiente"


def test_leitura_usa_anon_e_nunca_a_de_escrita():
    """Ler com service_role só aumentaria o estrago de um vazamento."""
    env = {"SUPABASE_SERVICE_ROLE_KEY": "sb_secret_xxx", "SUPABASE_ANON_KEY": "anon_yyy"}
    assert _supabase_key.chave_leitura(env) == "anon_yyy"


# ---------------------------------------------------------------------------
# Funções puras do pipeline hospitalar
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def hosp():
    """Importa o módulo sem executar main() — ele só roda sob __main__."""
    return importlib.import_module("pipeline_sih_hospitalar")


@pytest.mark.parametrize("dias,bin_esperado", [
    (0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (7, 2), (8, 3), (14, 3),
    (15, 4), (21, 4), (22, 5), (30, 5), (31, 6), (60, 6), (61, 7), (900, 7),
])
def test_los_bin_cobre_as_faixas(hosp, dias, bin_esperado):
    assert hosp._los_bin(dias) == bin_esperado


def test_los_bins_nao_deixam_buraco(hosp):
    """Toda permanência de 0 a 400 dias tem de cair em exatamente uma faixa."""
    vistos = {hosp._los_bin(d) for d in range(0, 401)}
    assert vistos == set(range(8))


def test_mediana_vazia_e_none(hosp):
    assert hosp._mediana_aprox([0] * 8) is None


def test_mediana_aprox_escolhe_a_faixa_do_meio(hosp):
    # 10 internações todas na faixa 4-7 dias -> ponto médio 5,5
    bins = [0, 0, 10, 0, 0, 0, 0, 0]
    assert hosp._mediana_aprox(bins) == 5.5
    # metade em 0-1 e metade em 61+ -> a mediana cai na primeira que atinge 50%
    assert hosp._mediana_aprox([5, 0, 0, 0, 0, 0, 0, 5]) == 0.5


def test_mediana_e_monotonica_ao_deslocar_massa(hosp):
    """Mover internações para faixas mais longas não pode reduzir a mediana."""
    anterior = -1.0
    for i in range(8):
        bins = [0] * 8
        bins[i] = 10
        atual = hosp._mediana_aprox(bins)
        assert atual > anterior
        anterior = atual


@pytest.mark.parametrize("idade,cod,faixa", [
    (0, "4", 0), (1, "4", 1), (4, "4", 1), (5, "4", 2), (14, "4", 2),
    (15, "4", 3), (29, "4", 3), (30, "4", 4), (59, "4", 5),
    (60, "4", 6), (70, "4", 7), (80, "4", 8), (120, "4", 8),
])
def test_faixa_etaria_em_anos(hosp, idade, cod, faixa):
    assert hosp._faixa_etaria(idade, cod) == faixa


@pytest.mark.parametrize("cod", ["0", "1", "2", "3", "", None, "9"])
def test_idade_fora_de_anos_vira_menor_de_um(hosp, cod):
    """COD_IDADE != 4 significa minutos/horas/dias/meses — tudo é <1 ano."""
    assert hosp._faixa_etaria(30, cod) == 0


def test_idade_invalida_nao_estoura(hosp):
    assert hosp._faixa_etaria("xx", "4") == 0
    assert hosp._faixa_etaria(None, "4") == 0


# ---------------------------------------------------------------------------
# Lista ICSAP
# ---------------------------------------------------------------------------

def test_lista_icsap_tem_os_tracadores_conhecidos():
    fluxo = importlib.import_module("pipeline_sih_fluxo")
    for cid in ["I10", "J44", "E10", "G40", "I50", "J18", "A09"]:
        assert cid in fluxo.ICSAP3, f"{cid} deveria estar na Lista Brasileira aproximada"


def test_lista_icsap_so_tem_codigos_de_tres_caracteres():
    fluxo = importlib.import_module("pipeline_sih_fluxo")
    invalidos = [c for c in fluxo.ICSAP3 if len(c) != 3 or not c[0].isalpha()]
    assert not invalidos, f"códigos malformados na lista: {invalidos}"
