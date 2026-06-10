"""
run_validations.py — CLI para executar as suites Great Expectations nos marts.

Uso:
    validate-marts                          # roda todas as suites
    validate-marts --suite producao_amb     # roda somente uma suite
    validate-marts --fail-fast              # aborta na primeira falha
    validate-marts --limit 5000             # limita linhas carregadas (dev/CI)
    validate-marts --no-color               # saída sem ANSI (logs/CI)

Exit codes:
    0  — todas as suites passaram
    1  — ao menos uma suite falhou
    2  — erro de configuração / ambiente
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapa de suites disponíveis
# ---------------------------------------------------------------------------

SUITE_REGISTRY: dict[str, str] = {
    "producao_amb":        "mart_producao_amb",
    "epi_cid10":           "mart_epi_cid10",
    "ranking_municipios":  "mart_ranking_municipios",
    "acesso_cobertura":    "mart_acesso_cobertura",
    "mix_complexidade":    "mart_mix_complexidade",
    "sazonalidade":        "mart_sazonalidade",
    "anomalias_prophet":   "mart_anomalias_prophet",
    "mortalidade":         "mart_mortalidade",
    "internacoes":         "mart_internacoes",
}


# ---------------------------------------------------------------------------
# Estruturas de resultado
# ---------------------------------------------------------------------------

@dataclass
class ExpectationResult:
    expectation_type: str
    column: str
    success: bool
    details: str = ""


@dataclass
class SuiteResult:
    suite_name: str
    success: bool
    total: int
    passed: int
    failed: int
    duration_s: float
    expectations: list[ExpectationResult] = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Execução de uma suite
# ---------------------------------------------------------------------------

def run_suite(
    short_name: str,
    limit: Optional[int],
) -> SuiteResult:
    """Carrega o mart e executa a suite correspondente."""
    from validation.loader import MART_LOADERS
    from validation import suites as suite_module

    # Loader
    loader = MART_LOADERS.get(short_name)
    if loader is None:
        return SuiteResult(
            suite_name=short_name,
            success=False,
            total=0, passed=0, failed=0,
            duration_s=0.0,
            error=f"Suite '{short_name}' não encontrada no registro.",
        )

    # Build-function
    builder_name = f"suite_{short_name}"
    build_fn = getattr(suite_module, builder_name, None)
    if build_fn is None:
        return SuiteResult(
            suite_name=short_name,
            success=False,
            total=0, passed=0, failed=0,
            duration_s=0.0,
            error=f"Builder '{builder_name}' não encontrado em validation.suites.",
        )

    t0 = time.perf_counter()
    try:
        import great_expectations as gx

        df = loader(limit=limit)
        suite, batch_def = build_fn(df)

        # Executa validação
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})
        results = batch.validate(suite)

        expectations: list[ExpectationResult] = []
        for r in results.results:
            col = r.expectation_config.kwargs.get("column", "<table>")
            exp_type = r.expectation_config.type
            details = ""
            if not r.success and r.result:
                details = str(r.result)
            expectations.append(
                ExpectationResult(
                    expectation_type=exp_type,
                    column=col,
                    success=r.success,
                    details=details,
                )
            )

        passed = sum(1 for e in expectations if e.success)
        failed = len(expectations) - passed

        return SuiteResult(
            suite_name=short_name,
            success=results.success,
            total=len(expectations),
            passed=passed,
            failed=failed,
            duration_s=time.perf_counter() - t0,
            expectations=expectations,
        )

    except Exception as exc:
        logger.exception("Erro ao executar suite '%s'", short_name)
        return SuiteResult(
            suite_name=short_name,
            success=False,
            total=0, passed=0, failed=0,
            duration_s=time.perf_counter() - t0,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Apresentação dos resultados
# ---------------------------------------------------------------------------

_RESET  = "\033[0m"
_GREEN  = "\033[32m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"


def _color(text: str, code: str, use_color: bool) -> str:
    return f"{code}{text}{_RESET}" if use_color else text


def _status_icon(success: bool, use_color: bool) -> str:
    if success:
        return _color("✓ PASS", _GREEN, use_color)
    return _color("✗ FAIL", _RED, use_color)


def print_suite_result(r: SuiteResult, use_color: bool, verbose: bool) -> None:
    icon = _status_icon(r.success, use_color)
    suite_label = _color(r.suite_name, _BOLD, use_color)
    print(f"\n{icon}  {suite_label}  ({r.duration_s:.1f}s | {r.passed}/{r.total} expectations)")

    if r.error:
        print(f"     {_color('ERRO: ' + r.error, _RED, use_color)}")
        return

    # Mostra expectativas falhas sempre; passadas apenas em verbose
    for exp in r.expectations:
        if exp.success and not verbose:
            continue
        prefix = "  ✓" if exp.success else "  ✗"
        col_part = f"[{exp.column}]" if exp.column != "<table>" else "[tabela]"
        line = f"     {prefix} {exp.expectation_type} {_color(col_part, _DIM, use_color)}"
        if not exp.success and exp.details:
            line += f"\n         {_color(exp.details[:120], _YELLOW, use_color)}"
        print(line)


def print_summary(results: list[SuiteResult], use_color: bool) -> None:
    total_suites   = len(results)
    passed_suites  = sum(1 for r in results if r.success)
    failed_suites  = total_suites - passed_suites
    total_exps     = sum(r.total for r in results)
    passed_exps    = sum(r.passed for r in results)
    total_duration = sum(r.duration_s for r in results)

    print("\n" + "─" * 60)
    status = _color("PASSED", _GREEN, use_color) if failed_suites == 0 else _color("FAILED", _RED, use_color)
    print(
        f"  {_color('Resultado final:', _BOLD, use_color)} {status}  "
        f"({passed_suites}/{total_suites} suites | "
        f"{passed_exps}/{total_exps} expectations | "
        f"{total_duration:.1f}s total)"
    )
    print("─" * 60 + "\n")


# ---------------------------------------------------------------------------
# Argparse + entrypoint
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="validate-marts",
        description="Executa suites Great Expectations nos marts do saude-publica-br.",
    )
    p.add_argument(
        "--suite",
        choices=list(SUITE_REGISTRY.keys()),
        metavar="SUITE",
        help=(
            "Nome curto da suite a executar. "
            f"Opções: {', '.join(SUITE_REGISTRY)}. "
            "Padrão: todas."
        ),
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Máximo de linhas a carregar por mart (útil em dev/CI).",
    )
    p.add_argument(
        "--fail-fast",
        action="store_true",
        help="Aborta na primeira suite que falhar.",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Exibe também as expectations que passaram.",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="Desativa saída colorida (útil em pipelines CI sem TTY).",
    )
    p.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log Python (padrão: WARNING).",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    use_color = not args.no_color and sys.stdout.isatty()

    suites_to_run = [args.suite] if args.suite else list(SUITE_REGISTRY.keys())

    print(
        f"\n{'─' * 60}\n"
        f"  saude-publica-br — Great Expectations Validation\n"
        f"  Suites: {', '.join(suites_to_run)}"
        + (f"  |  limit={args.limit}" if args.limit else "")
        + f"\n{'─' * 60}"
    )

    all_results: list[SuiteResult] = []
    any_failure = False

    for short_name in suites_to_run:
        result = run_suite(short_name, limit=args.limit)
        all_results.append(result)
        print_suite_result(result, use_color=use_color, verbose=args.verbose)

        if not result.success:
            any_failure = True
            if args.fail_fast:
                print(
                    f"\n  {_color('--fail-fast ativado: abortando.', _YELLOW, use_color)}"
                )
                break

    print_summary(all_results, use_color=use_color)
    sys.exit(1 if any_failure else 0)


if __name__ == "__main__":
    main()
