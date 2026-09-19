"""
O registro de fontes é a única declaração de onde cada fonte mora.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Antes de `scripts/_fontes.py`, o caminho de uma fonte estava digitado em toda
parte — o diretório do SIH em 8 arquivos, o do SINAN/FINAIS em 6. Cópia não é
só feiúra: ela diverge, e divergiu. O observador vigiava o SIM em
`SIM/CID10/DORES` e mais nada, enquanto o `pipeline_v2.py` lê também de
`SIM/PRELIM/DORES` — o diretório mais volátil do projeto, e o único do SIM que
ninguém observava. Nada acusou, porque fonte não observada não dá erro: ela só
deixa de avisar.

O registro resolve o estado atual. Estes testes impedem que ele volte:

  1. os ids do registro e de `site/lib/fontes.ts` são o MESMO conjunto;
  2. toda fonte ou é observável, ou traz o motivo escrito de não ser;
  3. nenhum pipeline volta a digitar um caminho `/dissemin/...` no código;
  4. todo diretório FTP que um pipeline lê está declarado — a regressão do SIM.

A varredura de (3) é por AST e ignora docstring: o cabeçalho de um pipeline
DEVE dizer de onde o dado vem, em prosa, para quem lê o arquivo. O que não pode
é o código ler de uma segunda cópia da string.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _fontes  # noqa: E402
from _fontes import FONTES, diretorios_ftp, fonte, nao_observadas, observadas  # noqa: E402

pytestmark = pytest.mark.unit

FONTES_TS = RAIZ / "site" / "lib" / "fontes.ts"

#: Script que ainda digita um caminho de fonte no código, com o motivo. Estar
#: aqui é uma decisão; não estar em lugar nenhum é esquecimento.
#:
#: Os de exploração ficam de fora de propósito: `probe_sources.py`,
#: `mapear_ftp_datasus.py` e `inspect_schema.py` existem para VARRER o FTP à
#: procura do que o projeto ainda não conhece. Prendê-los ao registro seria
#: impedi-los de olhar justamente onde o registro não chega.
FORA_DO_REGISTRO: dict[str, str] = {
    "probe_sources.py": "sonda: varre caminhos que o projeto ainda não adotou",
    "mapear_ftp_datasus.py": "mapeador: percorre o FTP inteiro por definição",
    "inspect_schema.py": "inspeção pontual de layout de arquivo",
    "sondar_sinan_agravos.py": "sondagem: descobre agravos fora do recorte atual",
    "analise_leitos_hsmr.py": "análise pontual, não coleta de rotina",
    "hsmr_estratos_uti.py": "análise pontual, não coleta de rotina",
}

#: Os arquivos que a varredura cobre: quem coleta de rotina.
def _vigiados() -> list[Path]:
    alvos = sorted(SCRIPTS.glob("pipeline_*.py"))
    alvos += [SCRIPTS / "observar_fontes.py", SCRIPTS / "_datasus_ftp.py",
              SCRIPTS / "_sisagua.py"]
    return [p for p in alvos if p.name not in FORA_DO_REGISTRO]


def ids_do_site() -> set[str]:
    texto = FONTES_TS.read_text(encoding="utf-8")
    corpo = texto.split("FONTE_DA_TABELA")[0]
    return set(re.findall(r'^\s*id:\s*"([a-z_]+)"', corpo, re.M))


# -- o registro e o site falam do mesmo conjunto -----------------------------

def test_ha_fontes_para_conferir():
    # Leitura quebrada faria os testes abaixo passarem vazios.
    assert len(FONTES) >= 10
    assert len(ids_do_site()) >= 10


def test_os_ids_do_registro_e_do_site_sao_o_mesmo_conjunto():
    registro = {f.id for f in FONTES}
    site = ids_do_site()
    assert registro == site, (
        f"só no registro: {sorted(registro - site)}; "
        f"só no site: {sorted(site - registro)}. O id é o elo entre a declaração "
        f"operacional (onde mora) e a editorial (o que o leitor lê)."
    )


def test_id_nao_se_repete():
    ids = [f.id for f in FONTES]
    assert len(set(ids)) == len(ids)


# -- observável ou dispensada, nunca as duas nem nenhuma ---------------------

def test_toda_fonte_e_observavel_ou_traz_motivo():
    mudas = [f.id for f in FONTES if not f.observavel and not f.dispensa.strip()]
    assert not mudas, (
        f"fonte sem local observável e sem motivo escrito: {mudas}. "
        f"Silêncio não é decisão."
    )


def test_fonte_observavel_tem_rotulo_de_base():
    sem_base = [f.id for f in FONTES if f.observavel and not f.base]
    assert not sem_base, f"fonte observável sem rótulo `base`: {sem_base}"


def test_observadas_e_dispensadas_nao_se_cruzam():
    assert not set(observadas()) & set(nao_observadas())


def test_observadas_mais_dispensadas_cobrem_tudo():
    assert set(observadas()) | set(nao_observadas()) == {f.id for f in FONTES}


def test_local_tem_nome_unico_dentro_da_fonte():
    for f in FONTES:
        nomes = [lo.nome for lo in f.locais]
        assert len(set(nomes)) == len(nomes), f"{f.id}: nome de local repetido"


def test_todo_padrao_compila():
    for base, diretorio, padrao in diretorios_ftp():
        re.compile(padrao)


def test_local_ftp_observavel_declara_padrao():
    """Sem padrão, o observador listaria o diretório inteiro como se fosse nosso."""
    for f in FONTES:
        for lo in f.locais:
            if lo.tipo == "ftp" and lo.observar:
                assert lo.padrao, f"{f.id}/{lo.nome}: observável sem padrão de nome"


def test_local_nao_observado_explica_por_que():
    for f in FONTES:
        for lo in f.locais:
            if not lo.observar:
                assert lo.nota.strip(), (
                    f"{f.id}/{lo.nome}: marcado para não observar sem dizer por quê")


def test_o_host_do_registro_e_o_do_cliente_ftp():
    """Duas constantes, um valor. `_datasus_ftp` precisa de padrão próprio para
    funcionar sozinho; o que não pode é os dois discordarem."""
    import _datasus_ftp

    assert _fontes.HOST_FTP == _datasus_ftp.HOST_PADRAO


# -- a regressão que motivou o registro --------------------------------------

def test_o_preliminar_do_sim_e_observado():
    """O `pipeline_v2.py` lê de CID10/DORES E de PRELIM/DORES. O observador só
    conhecia o primeiro, e o segundo é onde estão os anos que ainda mudam."""
    dirs = [d for base, d, _ in diretorios_ftp() if base == "SIM"]
    assert any("PRELIM" in d for d in dirs), (
        "o SIM voltou a ser observado só no consolidado; o preliminar é o que muda")
    assert any("CID10/DORES" in d for d in dirs)


def test_todo_diretorio_ftp_que_um_pipeline_le_esta_no_registro():
    """Generaliza o caso do SIM: se um pipeline lê de um diretório, ele está
    declarado — e então é observado ou tem nota dizendo por que não."""
    declarados = {lo.caminho for f in FONTES for lo in f.locais if lo.tipo == "ftp"}
    for p in _vigiados():
        for achado in _literais_com_caminho(p):
            assert any(achado.startswith(d) or d.startswith(achado)
                       for d in declarados), (
                f"{p.name}: usa {achado!r}, que não está no registro")


# -- a varredura: nenhum caminho digitado no código --------------------------

def _literais_com_caminho(caminho: Path) -> list[str]:
    """Strings com `/dissemin/` que o CÓDIGO usa — docstring não conta.

    O cabeçalho de um pipeline deve dizer de onde o dado vem, em prosa. O que
    não pode é o código ler de uma segunda cópia da string.
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    docstrings = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            corpo = getattr(no, "body", None)
            if corpo and isinstance(corpo[0], ast.Expr) and \
               isinstance(corpo[0].value, ast.Constant) and \
               isinstance(corpo[0].value.value, str):
                docstrings.add(id(corpo[0].value))
    achados = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) \
           and "/dissemin/publicos" in no.value and id(no) not in docstrings:
            achados.append(no.value)
    return achados


@pytest.mark.parametrize("caminho", _vigiados(), ids=[p.name for p in _vigiados()])
def test_nenhum_coletor_digita_caminho_de_fonte(caminho: Path):
    achados = _literais_com_caminho(caminho)
    assert not achados, (
        f"{caminho.name}: caminho de fonte digitado no código: {achados}. "
        f"Use `fonte(...).local(...).caminho` — foi a segunda cópia que deixou "
        f"o preliminar do SIM fora da observação."
    )


def test_excecao_declarada_existe_de_fato():
    nomes = {p.name for p in SCRIPTS.glob("*.py")}
    sobrando = set(FORA_DO_REGISTRO) - nomes
    assert not sobrando, f"declarado fora do registro mas inexistente: {sobrando}"


# -- a guarda vista REPROVANDO ----------------------------------------------
#
# Um teste que só sabe aprovar é indistinguível de um teste quebrado.

def test_a_varredura_pega_caminho_digitado(tmp_path):
    falso = tmp_path / "pipeline_falso.py"
    falso.write_text(
        '"""Fonte: /dissemin/publicos/SIM/CID10/DORES — isto e docstring."""\n'
        'FTP_DIR = "/dissemin/publicos/SIHSUS/200801_/Dados"\n',
        encoding="utf-8")
    achados = _literais_com_caminho(falso)
    assert achados == ["/dissemin/publicos/SIHSUS/200801_/Dados"], (
        "a varredura tem de pegar a atribuição e ignorar a docstring")


def test_a_varredura_ignora_docstring_de_funcao(tmp_path):
    falso = tmp_path / "pipeline_falso.py"
    falso.write_text(
        'def baixar():\n'
        '    """Le de /dissemin/publicos/SINAN/DADOS/FINAIS."""\n'
        '    return 1\n',
        encoding="utf-8")
    assert _literais_com_caminho(falso) == []


def test_a_guarda_pega_fonte_que_so_existe_de_um_lado():
    registro = {"sim", "sih"}
    site = {"sim", "oncologia"}
    assert registro - site == {"sih"}
    assert site - registro == {"oncologia"}


def test_fonte_desconhecida_falha_alto():
    with pytest.raises(KeyError, match="não existe no registro"):
        fonte("inexistente")


def test_local_desconhecido_falha_alto():
    with pytest.raises(KeyError, match="não declara o local"):
        fonte("sim").local("inexistente")
