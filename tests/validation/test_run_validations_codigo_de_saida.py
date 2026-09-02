"""O código de saída do executor de suites (`validation/run_validations.py`).

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Terceiro ponto cego da varredura de guardas de 2026-09-02. Ela procurava `raise`
e mensagens de erro classificáveis; aqui a guarda é

    sys.exit(1 if any_failure else 0)

— sem mensagem nenhuma, e por isso invisível para uma varredura que classifica
pelo texto levantado.

O executor não roda no CI: precisa de Great Expectations contra um banco vivo, e
o CI não tem banco. Os oito `tests/validation/test_suite_*.py` exercitam as
SUITES; ninguém exercitava o EXECUTOR — nem a agregação, nem o `--fail-fast`,
nem o código de saída que decide se uma validação reprovada derruba quem a
chamou.

Uma suite que falha e um executor que sai com 0 é o pior par possível: a
validação roda, encontra o problema, imprime em vermelho e mesmo assim informa
sucesso a quem a chamou. É a mesma família da régua do forecast, que media e
saía com 0.

A agregação é lógica pura — `run_suite` é substituída, e nenhum teste toca banco
ou Great Expectations.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from validation.run_validations import SuiteResult, main  # noqa: E402

pytestmark = pytest.mark.unit


def _resultado(nome: str, ok: bool) -> SuiteResult:
    return SuiteResult(suite_name=nome, success=ok, total=10,
                       passed=10 if ok else 7, failed=0 if ok else 3,
                       duration_s=0.1)


def _rodar(monkeypatch, resultados: list[SuiteResult], argv: list[str] | None = None) -> int:
    """Roda main() com `run_suite` substituída e devolve o código de saída."""
    fila = list(resultados)
    monkeypatch.setattr("validation.run_validations.run_suite",
                        lambda nome, **k: fila.pop(0))
    monkeypatch.setattr("validation.run_validations.SUITE_REGISTRY",
                        {r.suite_name: object() for r in resultados})
    monkeypatch.setattr(sys, "argv", ["validate-marts", *(argv or [])])
    with pytest.raises(SystemExit) as saida:
        main()
    return saida.value.code


def test_suite_reprovada_derruba_o_executor(monkeypatch):
    """O caso que a guarda existe para cobrir.

    Sem isto, a validação roda, imprime o erro em vermelho e informa sucesso.
    """
    assert _rodar(monkeypatch, [_resultado("mortalidade", False)]) == 1


def test_todas_aprovadas_saem_com_zero(monkeypatch):
    assert _rodar(monkeypatch, [_resultado("mortalidade", True),
                                _resultado("internacoes", True)]) == 0


def test_uma_reprovada_entre_varias_basta(monkeypatch):
    """A última suite passar não apaga a terceira ter falhado.

    `any_failure` é acumulador: um `=` no lugar de `|=` faria o resultado
    depender só da última suite executada, e o defeito passaria despercebido
    justamente quando a maioria passa.
    """
    assert _rodar(monkeypatch, [_resultado("a", True),
                                _resultado("b", False),
                                _resultado("c", True)]) == 1


def test_fail_fast_para_na_primeira_reprovada(monkeypatch):
    """Com --fail-fast, a segunda suite nem chega a ser executada."""
    executadas: list[str] = []
    resultados = [_resultado("a", False), _resultado("b", True)]
    fila = list(resultados)

    def _run(nome, **k):
        executadas.append(nome)
        return fila.pop(0)

    monkeypatch.setattr("validation.run_validations.run_suite", _run)
    monkeypatch.setattr("validation.run_validations.SUITE_REGISTRY",
                        {"a": object(), "b": object()})
    monkeypatch.setattr(sys, "argv", ["validate-marts", "--fail-fast"])
    with pytest.raises(SystemExit) as saida:
        main()
    assert saida.value.code == 1
    assert executadas == ["a"], f"--fail-fast não parou: rodou {executadas}"
