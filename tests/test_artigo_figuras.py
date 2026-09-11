"""
As figuras e o Word do artigo de neoplasias, presos ao manuscrito.

Duas coisas podem apodrecer em silêncio aqui, e nenhuma delas quebra nada na
hora em que acontece:

1. **A âncora da figura.** Cada figura é inserida ao fim de uma seção nomeada
   por número (`3.11`). Renumerar uma seção do manuscrito — coisa que já
   aconteceu duas vezes neste artigo — faria a figura simplesmente não entrar.
   `gerar_docx.py` reprova nesse caso, mas só quando alguém o executa; aqui a
   reprovação vem no CI.

2. **A renumeração para suplementar.** `Tabela 9` vira `Tabela S9` por regex, e
   a prosa tem tanto a forma singular quanto `Tabelas 11 e 12`. Uma regex que
   pegasse só a primeira deixaria metade das citações apontando para tabelas que
   não existem mais com aquele nome.

Executar: .venv311/Scripts/python -m pytest tests/test_artigo_figuras.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ARTIGO = RAIZ / "artigo-neoplasias"

# matplotlib nao e usado aqui: estes testes leem o manuscrito e conferem
# nomes de arquivo. `docx` entra porque gerar_docx.py o importa no topo,
# e esta declarado em requirements-test.txt para o CI nao pular o arquivo.
pytest.importorskip("docx")

import sys  # noqa: E402

sys.path.insert(0, str(ARTIGO))

from gerar_docx import FIGURAS_DO_ARTIGO, _suplementar, carregar_markdown  # noqa: E402


def _manuscrito() -> str:
    return (ARTIGO / "manuscrito.md").read_text(encoding="utf-8")


# ── as âncoras ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize(("secao", "arquivo", "_legenda"), FIGURAS_DO_ARTIGO)
def test_a_secao_ancora_existe_no_manuscrito(secao, arquivo, _legenda):
    """Se a seção sumiu ou mudou de número, a figura não entraria no artigo."""
    assert re.search(rf"^### {re.escape(secao)} ", _manuscrito(), re.M), (
        f"{arquivo} está ancorada na seção {secao}, que não existe mais no "
        "manuscrito. Atualize FIGURAS_DO_ARTIGO em gerar_docx.py.")


@pytest.mark.parametrize(("_secao", "arquivo", "_legenda"), FIGURAS_DO_ARTIGO)
def test_o_png_da_figura_existe(_secao, arquivo, _legenda):
    caminho = ARTIGO / "figuras" / f"{arquivo}.png"
    assert caminho.exists(), (
        f"{caminho.name} não existe. Rode artigo-neoplasias/gerar_figuras.py.")
    assert caminho.stat().st_size > 10_000, f"{caminho.name} está suspeitamente vazio"


def test_toda_figura_gerada_entra_no_artigo():
    """PNG na pasta e fora do documento é figura que ninguém vê."""
    na_pasta = {p.stem for p in (ARTIGO / "figuras").glob("figura_*.png")}
    no_artigo = {arquivo for _, arquivo, _ in FIGURAS_DO_ARTIGO}
    assert na_pasta == no_artigo, f"órfãs: {na_pasta ^ no_artigo}"


def test_a_numeracao_dos_arquivos_segue_a_ordem_do_documento():
    """`figura_03_*` tem de ser a Figura 3, senão a pasta contradiz o artigo."""
    for i, (_, arquivo, _) in enumerate(FIGURAS_DO_ARTIGO, start=1):
        assert arquivo.startswith(f"figura_{i:02d}_"), (
            f"{arquivo} aparece como Figura {i} no documento")


# ── a renumeração suplementar ──────────────────────────────────────────────

@pytest.mark.parametrize(("entrada", "esperado"), [
    ("(Tabela 9)", "(Tabela S9)"),
    ("Tabela 22", "Tabela S22"),
    ("Tabelas 11 e 12", "Tabelas S11 e S12"),
    ("Tabelas 18 e 19", "Tabelas S18 e S19"),
    ("ver Tabela 2 e Tabela 17", "ver Tabela S2 e Tabela S17"),
])
def test_citacao_de_tabela_vira_suplementar(entrada, esperado):
    assert _suplementar(entrada) == esperado


def test_nao_sobra_citacao_sem_o_s():
    """A varredura que o gerador faz, aplicada ao manuscrito inteiro."""
    _, corpo, _ = carregar_markdown()
    texto = _suplementar("\n".join(corpo))
    sobra = re.findall(r"\bTabela (?!S)\d+", texto)
    assert not sobra, f"citações sem S: {sorted(set(sobra))}"


# ── o que sai do markdown ──────────────────────────────────────────────────

def test_o_bloco_de_autoria_nao_entra_no_corpo():
    _, corpo, _ = carregar_markdown()
    texto = "\n".join(corpo)
    for proibido in ("Pedro Paulo Fernandes", "saudeemdado.com", "ORCID"):
        assert proibido not in texto, f"autoria vazou para o corpo: {proibido!r}"


def test_toda_tabela_do_manuscrito_e_extraida_com_o_seu_csv():
    _, corpo, tabelas = carregar_markdown()
    assert len(tabelas) == len(list((ARTIGO / "tabelas").glob("tabela_*.csv")))
    assert not any(linha.lstrip().startswith("|") for linha in corpo), (
        "sobrou tabela markdown no corpo — ela deveria ter ido para o suplementar")
    for t in tabelas:
        assert (ARTIGO / "tabelas" / t.csv).exists(), f"{t.csv} citado e ausente"


def test_os_numeros_das_tabelas_sao_uma_sequencia_sem_buraco():
    _, _, tabelas = carregar_markdown()
    assert sorted(t.numero for t in tabelas) == list(range(1, len(tabelas) + 1))
