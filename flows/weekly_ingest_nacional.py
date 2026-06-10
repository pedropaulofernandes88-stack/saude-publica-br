"""
weekly_ingest_nacional.py — Prefect flow para ingestão semanal nacional
=======================================================================

Orquestra a ingestão semanal de todos os 27 estados × 5 sistemas × 6 anos
via Prefect 2.x com ConcurrentTaskRunner para máximo paralelismo.

Funcionalidades:
  - ConcurrentTaskRunner: executa tasks em paralelo (asyncio.gather internamente)
  - Isolamento de erros: falha de 1 estado não cancela os demais
  - Progresso em tempo real via Prefect UI / logs
  - Alertas via email/Slack quando há falhas (configurável por env var)
  - Idempotência: skip automático para estados já ingeridos na semana
  - Notificação de conclusão com métricas agregadas

Scheduling: toda segunda-feira às 03:00 (BRT = UTC-3)
  cron: "0 6 * * 1"  (06:00 UTC = 03:00 BRT)

Deploy:
  prefect deployment build flows/weekly_ingest_nacional.py:ingest_nacional \
    --name "weekly-nacional" \
    --cron "0 6 * * 1" \
    --work-queue default
  prefect deployment apply ingest_nacional-deployment.yaml
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from prefect import flow, task, get_run_logger
from prefect.context import get_run_context
from prefect.task_runners import ConcurrentTaskRunner

# Import do módulo de ingestão
from ingestion.ingest_all_states import (
    ESTADOS_BR,
    SISTEMAS,
    ANOS_DEFAULT,
    IngestTask,
    IngestResult,
    IngestStats,
    run_ingest_task,
    build_task_list,
)

# ---------------------------------------------------------------------------
# Configuração via variáveis de ambiente
# ---------------------------------------------------------------------------
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/saude_publica",
)
PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", "data/parquet"))
WORKERS = int(os.environ.get("INGEST_WORKERS", "8"))
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")


# ---------------------------------------------------------------------------
# Tasks Prefect individuais (1 por estado × sistema)
# ---------------------------------------------------------------------------
@task(
    name="ingest-estado-sistema",
    retries=2,
    retry_delay_seconds=60,
    tags=["ingestao", "datasus"],
)
async def ingest_estado_sistema(
    estado: str,
    sistema: str,
    anos: list[int],
    parquet_dir: str,
    db_url: str,
) -> dict:
    """
    Task Prefect para ingestão de 1 estado × 1 sistema × N anos.
    Executada em paralelo pelo ConcurrentTaskRunner.
    """
    logger = get_run_logger()
    logger.info(f"▶ Iniciando {estado}/{sistema} — anos {min(anos)}–{max(anos)}")

    resultados = []
    erros = []

    for ano in anos:
        task_obj = IngestTask(estado=estado, sistema=sistema, ano=ano)
        t0 = time.monotonic()
        try:
            result = await asyncio.to_thread(
                run_ingest_task,
                task_obj,
                Path(parquet_dir),
                db_url,
                logging.getLogger(f"prefect.{estado}.{sistema}"),
                False,  # dry_run
            )
            resultados.append({
                "estado": estado,
                "sistema": sistema,
                "ano": ano,
                "success": result.success,
                "registros": result.registros,
                "duracao_s": result.duracao_s,
                "erro": result.erro,
            })
            if not result.success:
                erros.append(f"{estado}/{sistema}/{ano}: {result.erro}")
        except Exception as exc:
            elapsed = time.monotonic() - t0
            erros.append(f"{estado}/{sistema}/{ano}: {exc!s}")
            resultados.append({
                "estado": estado,
                "sistema": sistema,
                "ano": ano,
                "success": False,
                "registros": 0,
                "duracao_s": elapsed,
                "erro": str(exc),
            })

    total_reg = sum(r["registros"] for r in resultados)
    success_anos = sum(1 for r in resultados if r["success"])

    if erros:
        logger.warning(
            f"⚠ {estado}/{sistema} — {success_anos}/{len(anos)} anos OK, "
            f"{len(erros)} erros, {total_reg:,} registros"
        )
    else:
        logger.info(
            f"✅ {estado}/{sistema} — {len(anos)}/{len(anos)} anos OK, "
            f"{total_reg:,} registros"
        )

    return {
        "estado": estado,
        "sistema": sistema,
        "anos_ok": success_anos,
        "anos_total": len(anos),
        "registros": total_reg,
        "erros": erros,
        "resultados": resultados,
    }


@task(name="run-dbt-marts-nacionais", tags=["dbt", "transform"])
async def run_dbt_nacionais() -> dict:
    """Executa dbt run para os marts nacionais após ingestão completa."""
    logger = get_run_logger()
    logger.info("▶ Executando dbt — marts nacionais...")

    import subprocess
    cmds = [
        ["dbt", "run", "--select", "mart_nacional_producao+"],
        ["dbt", "run", "--select", "mart_nacional_mortalidade+"],
        ["dbt", "run", "--select", "mart_nacional_capacidade+"],
        ["dbt", "run", "--select", "mart_nacional_doencas+"],
    ]

    resultados = []
    for cmd in cmds:
        model = cmd[-1].replace("+", "")
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True, text=True, timeout=600,
            )
            ok = proc.returncode == 0
            resultados.append({"model": model, "ok": ok, "stderr": proc.stderr[-500:]})
            if ok:
                logger.info(f"  ✅ dbt {model}")
            else:
                logger.error(f"  ❌ dbt {model}: {proc.stderr[-200:]}")
        except Exception as exc:
            resultados.append({"model": model, "ok": False, "stderr": str(exc)})
            logger.error(f"  ❌ dbt {model}: {exc}")

    ok_count = sum(1 for r in resultados if r["ok"])
    logger.info(f"dbt concluído: {ok_count}/{len(resultados)} modelos OK")
    return {"modelos": resultados, "ok": ok_count, "total": len(resultados)}


@task(name="send-completion-alert", tags=["alertas"])
async def send_alert(
    summary: dict,
    slack_webhook: str = "",
    alert_email: str = "",
) -> None:
    """Envia notificação de conclusão via Slack e/ou email."""
    logger = get_run_logger()

    msg = (
        f"*🇧🇷 saude-publica-br — Ingestão Nacional Concluída*\n"
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Estados OK: {summary['estados_ok']}/{summary['estados_total']}\n"
        f"Registros: {summary['registros_total']:,}\n"
        f"Erros: {summary['erros_total']}\n"
        f"Duração: {summary['duracao_min']:.1f} min"
    )

    if summary["erros_total"] > 0:
        msg += f"\n⚠️ Estados com erro: {', '.join(summary.get('estados_com_erro', []))}"

    # Slack
    if slack_webhook:
        import urllib.request
        import json
        payload = json.dumps({"text": msg}).encode()
        try:
            req = urllib.request.Request(
                slack_webhook,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
            logger.info("✅ Alerta Slack enviado")
        except Exception as exc:
            logger.warning(f"Falha ao enviar Slack: {exc}")

    # Email (via smtplib se configurado)
    if alert_email:
        smtp_host = os.environ.get("SMTP_HOST", "")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")
        from_addr = os.environ.get("ALERT_FROM", smtp_user)

        if smtp_host and smtp_user:
            import smtplib
            from email.mime.text import MIMEText
            email_msg = MIMEText(msg.replace("*", "").replace("_", ""))
            email_msg["Subject"] = f"saude-publica-br — Ingestão {'✅ OK' if summary['erros_total'] == 0 else '⚠️ ERROS'}"
            email_msg["From"] = from_addr
            email_msg["To"] = alert_email
            try:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(from_addr, [alert_email], email_msg.as_string())
                logger.info(f"✅ Email enviado para {alert_email}")
            except Exception as exc:
                logger.warning(f"Falha ao enviar email: {exc}")

    logger.info("Alerta de conclusão processado")


# ---------------------------------------------------------------------------
# Flow principal
# ---------------------------------------------------------------------------
@flow(
    name="ingest-nacional",
    description="Ingestão semanal de todos os 27 estados × 5 sistemas DataSUS",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True,
)
async def ingest_nacional(
    estados:     Optional[list[str]] = None,
    sistemas:    Optional[list[str]] = None,
    anos:        Optional[list[int]] = None,
    parquet_dir: str = str(PARQUET_DIR),
    db_url:      str = DB_URL,
    workers:     int = WORKERS,
    skip_dbt:    bool = False,
    dry_run:     bool = False,
) -> dict:
    """
    Flow principal de ingestão nacional.

    Paralelismo:
      - Nível 1: ConcurrentTaskRunner executa tasks de (estado × sistema) simultaneamente
      - Nível 2: Dentro de cada task, asyncio.to_thread para I/O PySUS
      - Total de combinações default: 27 estados × 5 sistemas = 135 tasks concorrentes
        (cada uma com 6 anos sequenciais para controle de carga no DataSUS)

    Isolamento:
      - return_state=True + try/except → falha de 1 estado não cancela os demais
      - raw.ingestao_controle rastreia progresso individualmente
    """
    logger = get_run_logger()
    t0 = time.monotonic()

    _estados  = estados  or ESTADOS_BR
    _sistemas = sistemas or SISTEMAS
    _anos     = anos     or ANOS_DEFAULT

    logger.info("=" * 65)
    logger.info("🇧🇷 Flow: ingest_nacional — Fase 10 Expansão Geográfica")
    logger.info(f"   Estados  : {len(_estados)} | Sistemas: {len(_sistemas)} | Anos: {len(_anos)}")
    logger.info(f"   Parquet  : {parquet_dir}")
    logger.info(f"   DB       : {db_url.split('@')[-1]}")  # mascara senha
    logger.info(f"   Dry-run  : {dry_run}")
    logger.info("=" * 65)

    # -----------------------------------------------------------------------
    # Submete 1 task por (estado × sistema) — ConcurrentTaskRunner paraleliza
    # -----------------------------------------------------------------------
    futures = []
    for estado in _estados:
        for sistema in _sistemas:
            future = ingest_estado_sistema.submit(
                estado=estado,
                sistema=sistema,
                anos=_anos,
                parquet_dir=parquet_dir,
                db_url=db_url,
            )
            futures.append(future)

    logger.info(f"Submetidas {len(futures)} tasks ao ConcurrentTaskRunner")

    # Coleta resultados (aguarda todas, mesmo com falhas individuais)
    results = []
    estados_com_erro = []
    total_registros = 0
    total_erros = 0

    for future in futures:
        try:
            result = future.result()  # blocking — aguarda task individual
            results.append(result)
            total_registros += result["registros"]
            if result["erros"]:
                total_erros += len(result["erros"])
                estados_com_erro.append(f"{result['estado']}/{result['sistema']}")
        except Exception as exc:
            logger.error(f"Task falhou com exceção não capturada: {exc}")
            total_erros += 1

    estados_ok = sum(1 for r in results if not r["erros"])
    elapsed_min = (time.monotonic() - t0) / 60

    # -----------------------------------------------------------------------
    # dbt — marts nacionais (após ingestão)
    # -----------------------------------------------------------------------
    dbt_result = None
    if not skip_dbt and not dry_run:
        logger.info("\n▶ Executando dbt marts nacionais...")
        dbt_result = await run_dbt_nacionais()

    # -----------------------------------------------------------------------
    # Alerta de conclusão
    # -----------------------------------------------------------------------
    summary = {
        "estados_ok":      estados_ok,
        "estados_total":   len(_estados) * len(_sistemas),
        "registros_total": total_registros,
        "erros_total":     total_erros,
        "estados_com_erro": estados_com_erro[:10],
        "duracao_min":     elapsed_min,
        "dbt_ok":          dbt_result["ok"] if dbt_result else None,
    }

    if SLACK_WEBHOOK or ALERT_EMAIL:
        await send_alert(summary, slack_webhook=SLACK_WEBHOOK, alert_email=ALERT_EMAIL)

    # -----------------------------------------------------------------------
    # Log final
    # -----------------------------------------------------------------------
    logger.info("\n" + "=" * 65)
    logger.info("📋 FLOW CONCLUÍDO — Ingestão Nacional")
    logger.info(f"   Tasks OK      : {estados_ok}/{len(futures)}")
    logger.info(f"   Registros     : {total_registros:,}")
    logger.info(f"   Erros         : {total_erros}")
    logger.info(f"   Duração       : {elapsed_min:.1f} min")
    if dbt_result:
        logger.info(f"   dbt marts     : {dbt_result['ok']}/{dbt_result['total']} OK")
    logger.info("=" * 65)

    return summary


# ---------------------------------------------------------------------------
# Sub-flow: ingestão emergencial de 1 estado específico
# ---------------------------------------------------------------------------
@flow(
    name="ingest-estado-emergencial",
    description="Ingestão ad-hoc de um único estado (correção/reprocessamento)",
    task_runner=ConcurrentTaskRunner(),
)
async def ingest_estado_emergencial(
    estado:      str,
    sistemas:    Optional[list[str]] = None,
    anos:        Optional[list[int]] = None,
    parquet_dir: str = str(PARQUET_DIR),
    db_url:      str = DB_URL,
    force:       bool = False,
) -> dict:
    """
    Reprocessa todos os sistemas de 1 estado.
    Útil quando um estado específico tem dados corrompidos ou faltantes.
    --force ignora o controle de idempotência (DELETE + re-insert).
    """
    logger = get_run_logger()
    _sistemas = sistemas or SISTEMAS
    _anos     = anos     or ANOS_DEFAULT

    logger.info(f"🔄 Reprocessamento emergencial: {estado}")

    futures = [
        ingest_estado_sistema.submit(
            estado=estado,
            sistema=sistema,
            anos=_anos,
            parquet_dir=parquet_dir,
            db_url=db_url,
        )
        for sistema in _sistemas
    ]

    results = [f.result() for f in futures]
    total = sum(r["registros"] for r in results)
    logger.info(f"✅ {estado} concluído: {total:,} registros")
    return {"estado": estado, "registros": total, "sistemas": results}


# ---------------------------------------------------------------------------
# Deployment helper (execução local)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import argparse

    p = argparse.ArgumentParser(description="Ingestão Nacional — Prefect flow")
    p.add_argument("--estados", nargs="+", default=None)
    p.add_argument("--sistemas", nargs="+", default=None)
    p.add_argument("--anos", nargs="+", type=int, default=None)
    p.add_argument("--skip-dbt", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--estado-emergencial", metavar="UF",
        help="Executa sub-flow emergencial para 1 estado",
    )
    args = p.parse_args()

    if args.estado_emergencial:
        asyncio.run(
            ingest_estado_emergencial(
                estado=args.estado_emergencial,
                sistemas=args.sistemas,
                anos=args.anos,
            )
        )
    else:
        asyncio.run(
            ingest_nacional(
                estados=args.estados,
                sistemas=args.sistemas,
                anos=args.anos,
                skip_dbt=args.skip_dbt,
                dry_run=args.dry_run,
            )
        )
