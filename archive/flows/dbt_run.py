"""
flows/dbt_run.py
================
Prefect flow para execução do pipeline dbt (run + test).

Executa após a conclusão da ingestão semanal (toda segunda às 06:00 BRT).
Pode ser encadeado com weekly_ingest.py ou rodado isoladamente.

Uso:
    # Executar diretamente:
    python flows/dbt_run.py

    # Executar modelo específico:
    python flows/dbt_run.py --select mart_producao_amb+

    # Apenas testes:
    python flows/dbt_run.py --test-only

    # Deploy no Prefect:
    prefect deploy flows/dbt_run.py:pipeline_dbt \
        --name "pipeline-dbt-semanal"
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from prefect import flow, task, get_run_logger
from prefect.artifacts import create_markdown_artifact

PROJECT_ROOT = Path(__file__).parent.parent
DBT_DIR = PROJECT_ROOT / "dbt"

load_dotenv()


# ────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────

def _run_dbt(
    command: str,
    select: Optional[str] = None,
    exclude: Optional[str] = None,
    vars_override: Optional[dict] = None,
    target: str = "dev",
) -> tuple[int, str, str]:
    """
    Executa um comando dbt e retorna (returncode, stdout, stderr).
    """
    cmd = ["dbt", command, "--project-dir", str(DBT_DIR), "--target", target]

    if select:
        cmd += ["--select", select]
    if exclude:
        cmd += ["--exclude", exclude]
    if vars_override:
        import json
        cmd += ["--vars", json.dumps(vars_override)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(DBT_DIR),
        env={**os.environ},
    )
    return result.returncode, result.stdout, result.stderr


def _parse_dbt_results(stdout: str) -> dict:
    """Extrai métricas resumidas da saída do dbt."""
    import re

    stats = {"pass": 0, "fail": 0, "error": 0, "skip": 0, "warn": 0}
    # Linha do tipo: "Completed with X warnings, Y errors"
    # Ou "Done. PASS=X WARN=Y ERROR=Z SKIP=W TOTAL=T"
    patterns = {
        "pass": r"PASS=(\d+)",
        "warn": r"WARN=(\d+)",
        "error": r"ERROR=(\d+)",
        "skip": r"SKIP=(\d+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, stdout)
        if m:
            stats[key] = int(m.group(1))
    return stats


# ────────────────────────────────────────────────
# Tasks
# ────────────────────────────────────────────────

@task(
    name="dbt-deps",
    description="Instala packages dbt (dbt_utils, codegen)",
    retries=2,
    retry_delay_seconds=15,
)
def dbt_deps(target: str = "dev") -> bool:
    """Executa dbt deps para instalar/atualizar packages."""
    log = get_run_logger()
    log.info("📦 Instalando packages dbt...")
    rc, out, err = _run_dbt("deps", target=target)
    if rc != 0:
        log.error(f"dbt deps FALHOU:\n{err}")
        raise RuntimeError(f"dbt deps falhou com código {rc}")
    log.info("✅ dbt deps OK")
    return True


@task(
    name="dbt-run-staging",
    description="Materializa as views de staging",
    retries=2,
    retry_delay_seconds=30,
)
def dbt_run_staging(
    target: str = "dev",
    vars_override: Optional[dict] = None,
) -> dict:
    """Executa dbt run no layer de staging."""
    log = get_run_logger()
    log.info("▶️  dbt run — staging...")
    rc, out, err = _run_dbt("run", select="staging", target=target, vars_override=vars_override)
    stats = _parse_dbt_results(out)
    if rc != 0:
        log.error(f"dbt run staging FALHOU:\n{err}\n{out}")
        raise RuntimeError(f"dbt run staging falhou (errors={stats['error']})")
    log.info(f"✅ staging OK — PASS={stats['pass']} WARN={stats['warn']}")
    return {"layer": "staging", **stats}


@task(
    name="dbt-run-intermediate",
    description="Materializa as tabelas intermediate",
    retries=2,
    retry_delay_seconds=30,
)
def dbt_run_intermediate(
    target: str = "dev",
    vars_override: Optional[dict] = None,
) -> dict:
    """Executa dbt run no layer intermediate."""
    log = get_run_logger()
    log.info("▶️  dbt run — intermediate...")
    rc, out, err = _run_dbt("run", select="intermediate", target=target, vars_override=vars_override)
    stats = _parse_dbt_results(out)
    if rc != 0:
        log.error(f"dbt run intermediate FALHOU:\n{err}\n{out}")
        raise RuntimeError(f"dbt run intermediate falhou (errors={stats['error']})")
    log.info(f"✅ intermediate OK — PASS={stats['pass']} WARN={stats['warn']}")
    return {"layer": "intermediate", **stats}


@task(
    name="dbt-run-marts",
    description="Materializa as tabelas de marts (indicadores finais)",
    retries=2,
    retry_delay_seconds=30,
)
def dbt_run_marts(
    select: Optional[str] = None,
    target: str = "dev",
    vars_override: Optional[dict] = None,
) -> dict:
    """Executa dbt run no layer de marts."""
    log = get_run_logger()
    _select = select or "marts"
    log.info(f"▶️  dbt run — {_select}...")
    rc, out, err = _run_dbt("run", select=_select, target=target, vars_override=vars_override)
    stats = _parse_dbt_results(out)
    if rc != 0:
        log.error(f"dbt run marts FALHOU:\n{err}\n{out}")
        raise RuntimeError(f"dbt run marts falhou (errors={stats['error']})")
    log.info(f"✅ marts OK — PASS={stats['pass']} WARN={stats['warn']}")
    return {"layer": "marts", **stats}


@task(
    name="dbt-test",
    description="Executa testes de qualidade dbt",
    retries=1,
    retry_delay_seconds=15,
)
def dbt_test(
    select: Optional[str] = None,
    target: str = "dev",
) -> dict:
    """Executa dbt test. Falha se houver erros (não apenas warnings)."""
    log = get_run_logger()
    _select = select or ""
    log.info("🧪 dbt test...")
    rc, out, err = _run_dbt("test", select=_select or None, target=target)
    stats = _parse_dbt_results(out)

    if stats["error"] > 0:
        log.error(f"dbt test: {stats['error']} FALHAS de teste!\n{out}")
        raise RuntimeError(f"dbt test falhou: {stats['error']} erros")

    if stats["warn"] > 0:
        log.warning(f"dbt test: {stats['warn']} warnings")
    else:
        log.info(f"✅ dbt test OK — PASS={stats['pass']}")

    return stats


@task(
    name="validar-marts-gx",
    description="Valida qualidade dos marts com Great Expectations 1.x",
    retries=1,
    retry_delay_seconds=10,
)
def validar_marts(
    suites: Optional[list[str]] = None,
    limit: Optional[int] = None,
    fail_on_error: bool = False,
) -> dict:
    """
    Executa as suites Great Expectations em todos os marts (ou numa lista específica).

    Parameters
    ----------
    suites        : lista de nomes curtos (ex: ["producao_amb", "epi_cid10"]).
                    None = executa todas as 6 suites.
    limit         : máximo de linhas a carregar por mart (None = tabela inteira).
    fail_on_error : se True, levanta RuntimeError quando qualquer suite falha
                    (útil para bloquear deploy em produção).

    Returns
    -------
    dict com chaves:
        "success"  — True se todas passaram
        "summary"  — {suite_name: {"passed": int, "failed": int, "success": bool}}
        "total"    — total de expectations avaliadas
        "passed"   — total de expectations passadas
        "failed"   — total de expectations falhas
    """
    import sys
    import os

    log = get_run_logger()

    from validation.loader import MART_LOADERS
    from validation import suites as suite_module

    suites_to_run = suites or list(MART_LOADERS.keys())
    log.info(f"🔬 GX: validando {len(suites_to_run)} suite(s): {', '.join(suites_to_run)}")

    summary: dict[str, dict] = {}
    total_exp = 0
    total_pass = 0
    total_fail = 0
    any_failure = False

    for short_name in suites_to_run:
        loader = MART_LOADERS.get(short_name)
        build_fn = getattr(suite_module, f"suite_{short_name}", None)

        if loader is None or build_fn is None:
            log.warning(f"  ⚠️  Suite '{short_name}' não encontrada — ignorada")
            summary[short_name] = {"passed": 0, "failed": 0, "success": False, "error": "not_found"}
            continue

        try:
            import great_expectations as gx

            df = loader(limit=limit)
            suite, batch_def = build_fn(df)
            batch = batch_def.get_batch(batch_parameters={"dataframe": df})
            results = batch.validate(suite)

            passed = sum(1 for r in results.results if r.success)
            failed = len(results.results) - passed
            total_exp  += len(results.results)
            total_pass += passed
            total_fail += failed

            summary[short_name] = {
                "passed": passed,
                "failed": failed,
                "total":  len(results.results),
                "success": results.success,
                "rows": len(df),
            }

            icon = "✅" if results.success else "❌"
            log.info(f"  {icon} {short_name}: {passed}/{len(results.results)} ({len(df):,} linhas)")

            if not results.success:
                any_failure = True
                for r in results.results:
                    if not r.success:
                        col = r.expectation_config.kwargs.get("column", "<table>")
                        log.warning(f"     FALHA: {r.expectation_config.type} [{col}]")

        except Exception as exc:
            log.error(f"  ❌ {short_name}: erro inesperado — {exc}")
            summary[short_name] = {"passed": 0, "failed": 0, "success": False, "error": str(exc)}
            any_failure = True

    result = {
        "success": not any_failure,
        "summary": summary,
        "total":  total_exp,
        "passed": total_pass,
        "failed": total_fail,
    }

    if any_failure:
        log.warning(f"🔬 GX concluído com falhas: {total_fail}/{total_exp} expectations falharam")
        if fail_on_error:
            raise RuntimeError(
                f"Great Expectations: {total_fail} expectation(s) falharam — "
                "pipeline bloqueado (fail_on_error=True)"
            )
    else:
        log.info(f"🔬 GX OK: {total_pass}/{total_exp} expectations passaram")

    return result


@task(
    name="dbt-generate-docs",
    description="Gera documentação dbt",
)
def dbt_generate_docs(target: str = "dev") -> bool:
    """Gera docs dbt (opcional, para publicação)."""
    log = get_run_logger()
    log.info("📚 Gerando docs dbt...")
    rc, out, err = _run_dbt("docs", target=target)
    if rc != 0:
        log.warning(f"dbt docs gerou avisos (não fatal): {err}")
    return rc == 0


@task(
    name="publicar-resumo-dbt",
    description="Publica artefato Prefect com resumo da execução dbt + GX",
)
def publicar_resumo_dbt(
    results_staging: dict,
    results_intermediate: dict,
    results_marts: dict,
    results_test: dict,
    gx_results: Optional[dict] = None,
) -> None:
    """Publica markdown artifact no Prefect com resumo da execução dbt e GX."""
    log = get_run_logger()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_pass = (
        results_staging.get("pass", 0)
        + results_intermediate.get("pass", 0)
        + results_marts.get("pass", 0)
    )
    total_err = (
        results_staging.get("error", 0)
        + results_intermediate.get("error", 0)
        + results_marts.get("error", 0)
    )

    md = f"""## 🧱 Resumo dbt — {agora}

| Layer | PASS | WARN | ERROR | SKIP |
|-------|------|------|-------|------|
| Staging | {results_staging.get('pass',0)} | {results_staging.get('warn',0)} | {results_staging.get('error',0)} | {results_staging.get('skip',0)} |
| Intermediate | {results_intermediate.get('pass',0)} | {results_intermediate.get('warn',0)} | {results_intermediate.get('error',0)} | {results_intermediate.get('skip',0)} |
| Marts | {results_marts.get('pass',0)} | {results_marts.get('warn',0)} | {results_marts.get('error',0)} | {results_marts.get('skip',0)} |

### Testes dbt
- ✅ **PASS**: {results_test.get('pass', 0)}
- ⚠️ **WARN**: {results_test.get('warn', 0)}
- ❌ **ERROR**: {results_test.get('error', 0)}
"""

    # Seção Great Expectations (opcional — presente quando validar_marts foi executado)
    if gx_results:
        gx_status = "✅ OK" if gx_results.get("success") else "❌ FALHAS"
        gx_total  = gx_results.get("total", 0)
        gx_passed = gx_results.get("passed", 0)
        gx_failed = gx_results.get("failed", 0)

        suite_rows = ""
        for suite_name, s in gx_results.get("summary", {}).items():
            icon = "✅" if s.get("success") else "❌"
            rows_info = f"{s.get('rows', '?'):,}" if "rows" in s else "—"
            suite_rows += (
                f"| {suite_name} | {icon} | "
                f"{s.get('passed', 0)} | {s.get('failed', 0)} | "
                f"{rows_info} |\n"
            )

        md += f"""
### 🔬 Great Expectations — {gx_status} ({gx_passed}/{gx_total})

| Suite | Status | Passed | Failed | Linhas |
|-------|--------|--------|--------|--------|
{suite_rows}"""

    md += f"\n### Status geral: {'✅ OK' if total_err == 0 else f'❌ {total_err} erros dbt'}"
    if gx_results and not gx_results.get("success"):
        md += f" + ❌ {gx_results.get('failed', 0)} falhas GX"

    create_markdown_artifact(
        key="dbt-pipeline-resumo",
        markdown=md,
        description=f"Execução dbt — {agora}",
    )
    log.info("📋 Artefato publicado no Prefect")


# ────────────────────────────────────────────────
# Flow principal
# ────────────────────────────────────────────────

@flow(
    name="pipeline-dbt",
    description="Executa o pipeline dbt completo (staging → intermediate → marts → test → GX)",
    log_prints=True,
)
def pipeline_dbt(
    select: Optional[str] = None,
    test_only: bool = False,
    skip_deps: bool = False,
    skip_gx: bool = False,
    target: str = "dev",
    ano_inicio: Optional[int] = None,
    ano_fim: Optional[int] = None,
    gx_limit: Optional[int] = None,
    gx_fail_on_error: bool = False,
) -> dict:
    """
    Flow dbt completo para saude-publica-br.

    Args:
        select: Seletor dbt (ex: "mart_producao_amb+", "staging.*").
                None = executa tudo na ordem correta.
        test_only: Se True, pula o run e apenas executa os testes.
        skip_deps: Se True, pula o dbt deps (útil em re-runs rápidos).
        skip_gx: Se True, pula a validação Great Expectations.
        target: Profile target (dev/prod).
        ano_inicio: Sobrescreve var dbt ano_inicio.
        ano_fim: Sobrescreve var dbt ano_fim.
        gx_limit: Máximo de linhas por mart na validação GX (None = tabela inteira).
        gx_fail_on_error: Se True, levanta erro e bloqueia o flow quando GX falha.
    """
    log = get_run_logger()
    log.info(f"🚀 Iniciando pipeline dbt | target={target} | select={select or 'all'}")

    # Vars dbt opcionais
    vars_override = {}
    if ano_inicio:
        vars_override["ano_inicio"] = ano_inicio
    if ano_fim:
        vars_override["ano_fim"] = ano_fim

    # 1. deps
    if not skip_deps:
        dbt_deps(target=target)

    # Se apenas testes, pula os runs
    if test_only:
        log.info("🧪 Modo test-only — pulando runs")
        results_test = dbt_test(select=select, target=target)
        return {"test_only": True, "test": results_test}

    # 2. Run por layer (garante ordem de dependência)
    if not select:
        r_staging = dbt_run_staging(target=target, vars_override=vars_override or None)
        r_intermediate = dbt_run_intermediate(target=target, vars_override=vars_override or None)
        r_marts = dbt_run_marts(target=target, vars_override=vars_override or None)
    else:
        # Select manual: roda tudo com o seletor (usuário sabe o que faz)
        log.info(f"▶️  dbt run — select={select}")
        rc, out, err = _run_dbt("run", select=select, target=target,
                                vars_override=vars_override or None)
        stats = _parse_dbt_results(out)
        if rc != 0:
            log.error(f"dbt run FALHOU:\n{err}")
            raise RuntimeError(f"dbt run falhou (errors={stats['error']})")
        r_staging = r_intermediate = r_marts = stats

    # 3. Testes dbt
    results_test = dbt_test(select=select, target=target)

    # 4. Validação Great Expectations (opcional, não-bloqueante por padrão)
    gx_results: Optional[dict] = None
    if not skip_gx:
        log.info("🔬 Iniciando validação Great Expectations...")
        gx_results = validar_marts(
            limit=gx_limit,
            fail_on_error=gx_fail_on_error,
        )

    # 5. Publicar resumo no Prefect
    publicar_resumo_dbt(r_staging, r_intermediate, r_marts, results_test, gx_results)

    log.info("🎉 Pipeline dbt concluído com sucesso!")
    return {
        "staging": r_staging,
        "intermediate": r_intermediate,
        "marts": r_marts,
        "test": results_test,
        "gx": gx_results,
    }


# ────────────────────────────────────────────────
# Flow encadeado: ingestão + dbt
# ────────────────────────────────────────────────

@flow(
    name="pipeline-completo",
    description=(
        "Pipeline completo: ingestão incremental SIA/PA + SIM/DO + SIH/AIH "
        "+ dbt run + dbt test"
    ),
    log_prints=True,
)
def pipeline_completo(
    estados: Optional[list[str]] = None,
    force: bool = False,
    target: str = "dev",
) -> dict:
    """
    Orquestra a pipeline completa em sequência:
    1a. Ingestão incremental SIA/PA  (mensal — ambulatorial)
    1b. Ingestão incremental SIM/DO  (anual  — mortalidade)
    1c. Ingestão incremental SIH/AIH (mensal — internações)
    2.  dbt run + test (somente se houver novos dados ou force=True)

    Ideal para o scheduler semanal de produção.
    """
    from flows.weekly_ingest import ingestao_semanal_sia_pa
    from flows.weekly_ingest_sim import ingestao_anual_sim_do
    from flows.weekly_ingest_sih import ingestao_semanal_sih_aih

    log = get_run_logger()
    log.info("=" * 60)
    log.info("🏥 PIPELINE COMPLETO — saude-publica-br")
    log.info("=" * 60)

    # ── Passo 1a: SIA/PA (ambulatorial) ──────────────────────────────────
    log.info("📥 PASSO 1a/2 — Ingestão incremental SIA/PA (ambulatorial)")
    resultado_sia = ingestao_semanal_sia_pa(estados=estados, force=force)

    # ── Passo 1b: SIM/DO (mortalidade) ───────────────────────────────────
    log.info("📥 PASSO 1b/2 — Ingestão incremental SIM/DO (mortalidade)")
    resultado_sim = ingestao_anual_sim_do(estados=estados, force=force)

    # ── Passo 1c: SIH/AIH (internações) ──────────────────────────────────
    log.info("📥 PASSO 1c/2 — Ingestão incremental SIH/AIH (internações)")
    resultado_sih = ingestao_semanal_sih_aih(estados=estados, force=force)

    # ── Passo 2: dbt (só roda se houver novos dados ou force=True) ────────
    novos_registros = (
        resultado_sia.get("total_registros_carregados", 0)
        + resultado_sim.get("total_registros_carregados", 0)
        + resultado_sih.get("total_registros_carregados", 0)
    )

    if novos_registros > 0 or force:
        log.info(
            f"🧱 PASSO 2/2 — dbt run "
            f"({novos_registros:,} novos registros entre SIA/SIM/SIH)"
        )
        resultado_dbt = pipeline_dbt(target=target)
    else:
        log.info("⏭️  PASSO 2/2 — dbt pulado (sem novos dados em nenhum sistema)")
        resultado_dbt = {"skipped": True, "reason": "sem novos registros"}

    return {
        "ingestao_sia": resultado_sia,
        "ingestao_sim": resultado_sim,
        "ingestao_sih": resultado_sih,
        "dbt": resultado_dbt,
        "concluido_em": datetime.now().isoformat(),
    }


# ────────────────────────────────────────────────
# Execução direta para teste
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Execução do pipeline dbt")
    parser.add_argument("--select", default=None, help="Seletor dbt (ex: marts.*)")
    parser.add_argument("--test-only", action="store_true", help="Apenas testes dbt")
    parser.add_argument("--skip-deps", action="store_true", help="Pular dbt deps")
    parser.add_argument("--skip-gx", action="store_true", help="Pular validação Great Expectations")
    parser.add_argument("--gx-limit", type=int, default=None, metavar="N",
                        help="Máximo de linhas por mart na validação GX (dev/CI)")
    parser.add_argument("--gx-fail-on-error", action="store_true",
                        help="Bloqueia o pipeline se GX detectar falhas")
    parser.add_argument("--target", default="dev", choices=["dev", "prod"])
    parser.add_argument("--completo", action="store_true", help="Pipeline completo (ingestão + dbt)")
    args = parser.parse_args()

    if args.completo:
        pipeline_completo(target=args.target)
    else:
        pipeline_dbt(
            select=args.select,
            test_only=args.test_only,
            skip_deps=args.skip_deps,
            skip_gx=args.skip_gx,
            target=args.target,
            gx_limit=args.gx_limit,
            gx_fail_on_error=args.gx_fail_on_error,
        )
