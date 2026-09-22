"""Os mapas do RHC valem o que o dicionário do INCA disser, e não o contrário.

`scripts/_rhc_codigos.py` declara os códigos à mão, por uma razão escrita lá.
Declaração sem verificação é o que este projeto chama de guarda que só foi
vista aprovando, então aqui o `.cnv` que vem DENTRO do zip anual do INCA é
aberto e comparado, código a código.

O teste é offline quando o zip já está em `data/cache/`; sem ele, pula. O que
NÃO pula é a parte de forma — `decodificar`, `faixa_etaria` e `tem_data` são
exercitadas sempre, cada uma vista devolvendo e vista recusando.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import _rhc_codigos as rc  # noqa: E402

CACHE = RAIZ / "data" / "cache"

#: O `.cnv` é posicional: 7 colunas de índice, 2 de espaço, 50 de rótulo, e o
#: resto são os códigos. O índice da linha NÃO é o código — ver a armadilha
#: documentada em `_rhc_codigos`.
INICIO_DO_ROTULO = 9
INICIO_DOS_CODIGOS = 59


def ler_cnv(zip_path: Path, nome: str) -> dict[str, str]:
    """{código: rótulo do INCA}, lido do dicionário embarcado no zip."""
    with zipfile.ZipFile(zip_path) as z:
        texto = z.read(nome).decode("latin-1")
    linhas = [l for l in texto.splitlines()
              if l.strip() and not l.strip().startswith(";")]
    fora = {}
    for linha in linhas[1:]:                       # [0] é o cabeçalho "N W"
        rotulo = linha[INICIO_DO_ROTULO:INICIO_DOS_CODIGOS].strip()
        for codigo in re.findall(r"-?\w+", linha[INICIO_DOS_CODIGOS:]):
            fora[codigo] = rotulo
    return fora


def _zip_disponivel() -> Path | None:
    for ano in range(2023, 2012, -1):
        p = CACHE / f"rhc_{ano}.zip"
        if p.exists():
            return p
    return None


ZIP = _zip_disponivel()
precisa_do_zip = pytest.mark.skipif(
    ZIP is None, reason="nenhum zip do RHC em data/cache — teste é offline")


# ---------------------------------------------------------------------------
# 1. Os mapas contra o dicionário do INCA
# ---------------------------------------------------------------------------

@precisa_do_zip
@pytest.mark.parametrize("mapa,arquivo", [
    (rc.SEXO, "r_sexo.cnv"),
    (rc.RACA_COR, "r_racacor.cnv"),
    (rc.ESCOLARIDADE, "r_ginstruc.cnv"),
    (rc.ESTADO_FIM_TRATAMENTO, "r_estdoenfimtrat.cnv"),
    (rc.RAZAO_NAO_TRATAMENTO, "r_razaonaotrat.cnv"),
    (rc.PRIMEIRO_TRATAMENTO, "r_pritrathosp.cnv"),
])
def test_todo_codigo_do_inca_esta_no_mapa(mapa, arquivo):
    """Código que o INCA define e eu não conheço vira 'ignorado' calado."""
    do_inca = ler_cnv(ZIP, arquivo)
    faltam = sorted(set(do_inca) - set(mapa))
    assert not faltam, (
        f"{arquivo}: códigos no dicionário do INCA e ausentes do mapa: "
        f"{[(c, do_inca[c]) for c in faltam]}")


@precisa_do_zip
@pytest.mark.parametrize("mapa,arquivo", [
    (rc.SEXO, "r_sexo.cnv"),
    (rc.RACA_COR, "r_racacor.cnv"),
    (rc.ESCOLARIDADE, "r_ginstruc.cnv"),
    (rc.ESTADO_FIM_TRATAMENTO, "r_estdoenfimtrat.cnv"),
    (rc.RAZAO_NAO_TRATAMENTO, "r_razaonaotrat.cnv"),
    (rc.PRIMEIRO_TRATAMENTO, "r_pritrathosp.cnv"),
])
def test_nenhum_codigo_inventado_por_mim(mapa, arquivo):
    """O inverso: código meu que o INCA não define é rótulo inventado."""
    do_inca = ler_cnv(ZIP, arquivo)
    sobram = sorted(set(mapa) - set(do_inca))
    assert not sobram, f"{arquivo}: códigos no meu mapa e fora do INCA: {sobram}"


@precisa_do_zip
def test_o_indice_da_linha_nao_e_o_codigo():
    """A armadilha que motivou o arquivo, presa pelo caso concreto.

    Em raça/cor, a linha 6 é o código 9. Ler pela ordem apagaria os 9,0% de
    'sem informação' de 2019 e inventaria uma sexta categoria.
    """
    do_inca = ler_cnv(ZIP, "r_racacor.cnv")
    assert do_inca["9"] == "Sem Informacao"
    assert "6" not in do_inca


@precisa_do_zip
def test_a_assimetria_do_pritrath_e_do_inca_e_fica_como_esta():
    """334 existe; 343 e 433 não. Reproduzir é o certo; 'consertar' inventaria."""
    do_inca = ler_cnv(ZIP, "r_pritrathosp.cnv")
    assert "334" in do_inca
    assert "343" not in do_inca and "433" not in do_inca
    assert "343" not in rc.PRIMEIRO_TRATAMENTO


@precisa_do_zip
def test_permutacao_de_tres_modalidades_cai_no_mesmo_rotulo():
    for c in ("234", "243", "324", "342", "432", "423"):
        assert rc.PRIMEIRO_TRATAMENTO[c] == "cirurgia+radioterapia+quimioterapia"


# ---------------------------------------------------------------------------
# 2. "Nenhum" não é "sem informação", e nenhum dos dois é nulo
# ---------------------------------------------------------------------------

def test_nenhum_tratamento_tem_rotulo_proprio():
    """83.956 registros em 2019. Confundi-los com ausência apaga o denominador
    de qualquer estudo de acesso."""
    assert rc.PRIMEIRO_TRATAMENTO["1"] == "nenhum"
    assert rc.PRIMEIRO_TRATAMENTO["9"] == rc.IGNORADO
    assert rc.PRIMEIRO_TRATAMENTO["1"] != rc.PRIMEIRO_TRATAMENTO["9"]


def test_obito_aparece_em_dois_campos_e_sao_coisas_diferentes():
    """`ESTDFIMT=6` é morrer durante o primeiro tratamento; `RZNTR=6` é morrer
    antes dele. Somar os dois conta gente duas vezes."""
    assert rc.ESTADO_FIM_TRATAMENTO["6"] == "obito"
    assert rc.RAZAO_NAO_TRATAMENTO["6"] == "obito"
    assert rc.ESTADO_FIM_TRATAMENTO is not rc.RAZAO_NAO_TRATAMENTO


# ---------------------------------------------------------------------------
# 3. `decodificar`, vista devolvendo e vista recusando
# ---------------------------------------------------------------------------

def test_decodifica_o_que_conhece():
    assert rc.decodificar(rc.RACA_COR, "4") == "parda"
    assert rc.decodificar(rc.SEXO, "2") == "feminino"


def test_espaco_em_volta_nao_impede_a_decodificacao():
    assert rc.decodificar(rc.RACA_COR, " 4 ") == "parda"


@pytest.mark.parametrize("valor", ["0", "7", "", "X", "99"])
def test_codigo_fora_do_dicionario_vira_ignorado_e_nao_o_codigo_cru(valor):
    """Devolver o código cru é o que faz um '88' aparecer numa figura."""
    assert rc.decodificar(rc.RACA_COR, valor) == rc.IGNORADO


def test_o_zero_que_existe_no_dado_e_nao_no_dicionario():
    """SEXO='0' e INSTRUC='0' aparecem em 2019, dois registros cada."""
    assert rc.decodificar(rc.SEXO, "0") == rc.IGNORADO
    assert rc.decodificar(rc.ESCOLARIDADE, "0") == rc.IGNORADO


# ---------------------------------------------------------------------------
# 4. Faixa etária
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("idade,esperado", [
    ("000", "00-04"), ("004", "00-04"), ("005", "05-09"),
    ("020", "20-24"), ("019", "15-19"),          # o corte de Jomar et al.
    ("084", "80-84"), ("085", "85+"), ("120", "85+"),
])
def test_faixa_etaria_nos_cortes_do_inca(idade, esperado):
    assert rc.faixa_etaria(idade) == esperado


@pytest.mark.parametrize("idade", ["999", "", "  ", "abc", "-1", None])
def test_idade_sem_informacao_nao_vira_zero_anos(idade):
    """999 é 'sem informação' no dicionário; vazio não é recém-nascido."""
    assert rc.faixa_etaria(idade) == "ignorada"


# ---------------------------------------------------------------------------
# 5. A máscara de data vazia — o defeito que mediu 99,6% de preenchimento
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valor", ["/  /", "  /  /  ", "//", "", "   ",
                                   "99/99/9999", "9999"])
def test_mascara_vazia_nao_conta_como_data(valor):
    assert rc.tem_data(valor) is False


@pytest.mark.parametrize("valor", ["16/05/2019", "01/01/2013", " 10/08/2020 "])
def test_data_de_verdade_conta(valor):
    assert rc.tem_data(valor) is True


def test_o_strip_sozinho_teria_aprovado_a_mascara():
    """A regressão em uma linha: foi `if valor.strip():` que mediu 99,6% de
    DATAOBITO preenchido quando o real é 15,9%."""
    mascara = "/  /"
    assert bool(mascara.strip()) is True      # o que o código ingênuo via
    assert rc.tem_data(mascara) is False      # o que a fonte quer dizer
