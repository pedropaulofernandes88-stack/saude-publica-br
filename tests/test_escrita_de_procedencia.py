"""Procedência só se grava pelo caminho que confere a resposta.

POR QUE ESTA GUARDA EXISTE
--------------------------
Doze pontos do projeto gravavam procedência com `requests.post(...)` sem olhar o
retorno. Medido contra o banco em 2026-09-20: `fonte_cnes`, `fonte_leitos` e
`fonte_saude_suplementar` estavam declaradas no código e ausentes em produção,
com os pipelines terminando em exit 0.

A varredura é por **AST e sobre o diretório inteiro**, não por lista de arquivos
conhecidos, porque o defeito que ela persegue é justamente o do arquivo que
ninguém lembrou de incluir. Ver a memória `guarda-nunca-vista-reprovando`.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import requests

import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from _procedencia import gravar_procedencia  # noqa: E402

#: O único arquivo autorizado a falar com a tabela de metadados diretamente.
DONO = "_procedencia.py"


def _literais_de_texto(no: ast.AST) -> list[str]:
    """Todo texto literal dentro de um nó, inclusive dentro de f-strings."""
    return [n.value for n in ast.walk(no)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _escritas_cruas(caminho: Path) -> list[int]:
    """Linhas com `requests.post/put/patch` apontando para `meta_dataset`."""
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover
        return []
    achados: list[int] = []
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call) or not isinstance(no.func, ast.Attribute):
            continue
        if no.func.attr not in {"post", "put", "patch"}:
            continue
        if any("meta_dataset" in t for arg in no.args for t in _literais_de_texto(arg)):
            achados.append(no.lineno)
    return achados


def test_nenhum_script_grava_procedencia_por_fora():
    culpados: list[str] = []
    for caminho in sorted((RAIZ / "scripts").glob("*.py")):
        if caminho.name == DONO:
            continue
        for linha in _escritas_cruas(caminho):
            culpados.append(f"{caminho.name}:{linha}")
    assert not culpados, (
        "POST direto em meta_dataset, fora de _procedencia.gravar_procedencia(): "
        + ", ".join(culpados)
        + ". Escrita de metadado tem de conferir a resposta — sem isso, um 409 de "
        "chave duplicada é indistinguível de sucesso, que foi como três chaves "
        "declaradas nunca chegaram ao banco."
    )


class _Resposta:
    def __init__(self, status: int, texto: str = ""):
        self.status_code, self.text = status, texto


def test_helper_levanta_quando_o_banco_recusa(monkeypatch):
    """O ponto da guarda: recusa do PostgREST vira exceção, não silêncio."""
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _Resposta(409, "duplicate key value"))
    with pytest.raises(RuntimeError, match="fonte_teste"):
        gravar_procedencia("https://exemplo", {}, [{"chave": "fonte_teste", "valor": "x"}])


def test_helper_pede_merge_duplicates():
    """Regravar a mesma chave é o caso NORMAL, e não pode quebrar o pipeline.

    Sem `resolution=merge-duplicates`, conferir a resposta trocaria um modo de
    falha por outro: a segunda execução de qualquer pipeline morreria em 409.
    """
    capturado: dict = {}

    def _falso_post(url, **kw):
        capturado.update(kw)
        return _Resposta(200)

    import _procedencia
    original = _procedencia.requests.post
    _procedencia.requests.post = _falso_post
    try:
        gravar_procedencia("https://exemplo", {"apikey": "k"},
                           [{"chave": "fonte_teste", "valor": "x"}])
    finally:
        _procedencia.requests.post = original

    assert "resolution=merge-duplicates" in capturado["headers"]["Prefer"]


def test_lista_vazia_nao_faz_requisicao():
    import _procedencia
    original = _procedencia.requests.post

    def _explode(*a, **k):  # pragma: no cover
        raise AssertionError("não deveria ter feito requisição")

    _procedencia.requests.post = _explode
    try:
        assert gravar_procedencia("https://exemplo", {}, []) == 0
    finally:
        _procedencia.requests.post = original
