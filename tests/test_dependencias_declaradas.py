"""
Dependência que a suíte importa e o CI não instala derruba a COLETA inteira.

O CI ficou vermelho **40 execuções seguidas** porque `scripts/_sim_obitos.py`
passou a importar `duckdb` no nível do módulo e ninguém acrescentou a linha em
`requirements-test.txt`. Três arquivos de teste importam esse módulo, então o
pytest falhava em `collection` — a suíte não rodava um único teste, e o job
morria em 1m13s com `3 errors during collection`.

O que fez o defeito durar tanto: localmente passa. A `.venv311` tem duckdb
porque o `requirements.txt` completo o traz; só o ambiente do CI, que instala a
lista enxuta, não tinha. Quem roda `pytest` na própria máquina vê verde e empurra.

O cabeçalho do `requirements-test.txt` já ANTECIPAVA isto — "dependência usada e
não declarada quebra o CI no dia em que um teste toca o módulo que a importa" —
mas era uma previsão escrita, não uma checagem executada. Esta é a checagem.

Executar: .venv311/Scripts/python -m pytest tests/test_dependencias_declaradas.py
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REQ_TESTE = RAIZ / "requirements-test.txt"

#: Nome do import → nome do pacote no PyPI, quando diferem.
APELIDOS = {
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "dateutil": "python-dateutil",
    "psycopg": "psycopg",
}

#: Pacotes locais do repositório: não são dependência de terceiro.
LOCAIS = {"scripts", "tests", "validation", "ingestion", "ml", "clients",
          "saudeemdado", "saudeemdado_mcp", "mcp_server"}


def _modulos_locais() -> set[str]:
    return {p.stem for p in RAIZ.glob("scripts/*.py")} | LOCAIS


def _funcoes_citadas_pelos_testes() -> set[str]:
    """Nomes que aparecem em tests/ — a aproximação de "a suíte chama isto"."""
    nomes: set[str] = set()
    for p in RAIZ.glob("tests/**/*.py"):
        try:
            nomes |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", p.read_text(encoding="utf-8")))
        except OSError:
            continue
    return nomes


def _imports_lazy_alcancados(caminho: Path, citados: set[str]) -> set[str]:
    """Imports DENTRO de funções cujo nome a suíte menciona.

    Import lazy não derruba a coleta, e o `requirements-test.txt` deixa vários
    de fora acertadamente — a justificativa dele é precisa: "só acontece dentro
    de funções que a suíte NÃO chama". A condição é essa, e ela pode deixar de
    valer sem aviso: em 2026-09-06 um teste novo passou a chamar
    `_parser_de_data_tolerante`, que importa dbfread por dentro, e o CI quebrou
    com a lista intacta. Reprovar todo import lazy seria exagero; ignorá-los
    todos foi o que custou. O meio-termo é olhar só as funções mencionadas.
    """
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    achados: set[str] = set()
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if no.name not in citados:
            continue
        for interno in ast.walk(no):
            if isinstance(interno, ast.Import):
                achados |= {a.name.split(".")[0] for a in interno.names}
            elif isinstance(interno, ast.ImportFrom) and interno.level == 0 and interno.module:
                achados.add(interno.module.split(".")[0])
    return achados


def _imports_de_modulo(caminho: Path) -> set[str]:
    """Só imports no NÍVEL DO MÓDULO — os que derrubam a COLETA do pytest."""
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    achados: set[str] = set()
    for no in arvore.body:
        if isinstance(no, ast.Import):
            achados |= {a.name.split(".")[0] for a in no.names}
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            achados.add(no.module.split(".")[0])
    return achados


def _declarados() -> set[str]:
    texto = REQ_TESTE.read_text(encoding="utf-8")
    nomes = set()
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        nomes.add(re.split(r"[><=\[;]", linha)[0].strip().lower().replace("-", "_"))
    return nomes


def _externos_alcancados() -> set[str]:
    """Terceiros importados no nível do módulo por tests/ e pelos scripts que ele importa."""
    locais = _modulos_locais()
    alcancados: set[str] = set()
    for p in RAIZ.glob("tests/**/*.py"):
        alcancados |= _imports_de_modulo(p) & locais

    alvos = list(RAIZ.glob("tests/**/*.py"))
    alvos += [RAIZ / "scripts" / f"{m}.py" for m in alcancados]

    citados = _funcoes_citadas_pelos_testes()
    externos: set[str] = set()
    for p in alvos:
        if p.exists():
            externos |= _imports_de_modulo(p)
            externos |= _imports_lazy_alcancados(p, citados)
    return externos - set(sys.stdlib_module_names) - locais - {"__future__"}


def test_requirements_test_existe_e_e_legivel():
    """Sem isto, os testes abaixo passariam vazios."""
    assert REQ_TESTE.exists()
    assert len(_declarados()) >= 10


def test_toda_dependencia_da_suite_esta_declarada():
    declarados = _declarados()
    faltando = sorted(
        m for m in _externos_alcancados()
        if APELIDOS.get(m, m).lower().replace("-", "_") not in declarados
    )
    assert not faltando, (
        f"a suíte importa {faltando} no nível do módulo e requirements-test.txt "
        "não declara. O CI instala SÓ essa lista: a coleta do pytest falha antes "
        "de rodar um teste, e localmente passa despercebido porque a .venv311 "
        "tem o requirements.txt inteiro."
    )


def test_o_piso_bate_com_o_de_producao():
    """Suíte e produção na mesma versão — é a regra que o próprio arquivo declara."""
    prod = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    teste = REQ_TESTE.read_text(encoding="utf-8")

    def piso(texto: str, pacote: str) -> str | None:
        m = re.search(rf"^{pacote}(>=[\d.]+)", texto, re.M)
        return m.group(1) if m else None

    for pacote in ("duckdb", "scipy", "pandas"):
        p_prod, p_teste = piso(prod, pacote), piso(teste, pacote)
        if p_prod and p_teste:
            assert p_prod == p_teste, (
                f"{pacote}: produção {p_prod}, suíte {p_teste} — um teste pode "
                "passar usando API que não existe onde o código roda")


def test_a_guarda_reprova_uma_dependencia_ausente():
    """Vista REPROVANDO: reconstrói o caso real do duckdb.

    Sem isto, a checagem acima seria indistinguível de uma que sempre aprova.
    """
    declarados = _declarados() - {"duckdb"}
    faltando = [m for m in ("duckdb", "pandas")
                if APELIDOS.get(m, m).lower().replace("-", "_") not in declarados]
    assert faltando == ["duckdb"]


@pytest.mark.parametrize("modulo", ["duckdb", "dbfread"])
def test_dependencia_que_quebrou_o_ci_esta_declarada(modulo: str):
    """Regressão nomeada: foi este import que custou 40 execuções."""
    assert modulo in _declarados()
