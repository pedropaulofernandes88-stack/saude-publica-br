"""
ingest_all_states.py — Ingestão paralela para todos os 27 estados do Brasil
===========================================================================

Orquestra o download e carga de dados DataSUS para:
  - 27 estados (AC → TO)
  - 5 sistemas: SIA/PA, SIM/DO, SIH/AIH, SINAN, CNES
  - Anos 2019–2024 (configurável)

Estratégia de paralelismo:
  - ThreadPoolExecutor com max_workers configurável (padrão: 8)
  - Cada tarefa = 1 estado × 1 sistema × 1 ano
  - Idempotência via raw.ingestao_controle (skip se status='done')
  - Retry automático para status='error' (até --max-retries tentativas)

Uso:
  python ingestion/ingest_all_states.py
  python ingestion/ingest_all_states.py --estados SP RJ MG --anos 2023 2024
  python ingestion/ingest_all_states.py --sistemas SIA/PA SIM/DO --workers 16
  python ingestion/ingest_all_states.py --dry-run
  python ingestion/ingest_all_states.py --retry-errors
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import asyncpg
import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
ESTADOS_BR = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

SISTEMAS = ["SIA/PA", "SIM/DO", "SIH/AIH", "SINAN", "CNES"]

ANOS_DEFAULT = list(range(2019, 2025))  # 2019–2024 inclusive

# Mapa sistema → módulo PySUS e parâmetros
SISTEMA_CONFIG = {
    "SIA/PA": {
        "pysus_module": "pysus.online_data.SIA",
        "pysus_fn": "download",
        "file_prefix": "PA",
        "parquet_subdir": "SIA_PA",
        "schema": _sia_pa_schema(),
    },
    "SIM/DO": {
        "pysus_module": "pysus.online_data.SIM",
        "pysus_fn": "download",
        "file_prefix": "DO",
        "parquet_subdir": "SIM_DO",
        "schema": _sim_do_schema(),
    },
    "SIH/AIH": {
        "pysus_module": "pysus.online_data.SIH",
        "pysus_fn": "download",
        "file_prefix": "RD",
        "parquet_subdir": "SIH_AIH",
        "schema": _sih_aih_schema(),
    },
    "SINAN": {
        "pysus_module": "pysus.online_data.SINAN",
        "pysus_fn": "download",
        "file_prefix": "SN",
        "parquet_subdir": "SINAN",
        "schema": _sinan_schema(),
    },
    "CNES": {
        "pysus_module": "pysus.online_data.CNES",
        "pysus_fn": "download",
        "file_prefix": "LT",
        "parquet_subdir": "CNES",
        "schema": _cnes_schema(),
    },
}

# Mapa sistema → tabela raw
SISTEMA_TABELA = {
    "SIA/PA":  "raw.sia_pa",
    "SIM/DO":  "raw.sim_do",
    "SIH/AIH": "raw.sih_aih",
    "SINAN":   "raw.sinan",
    "CNES":    "raw.cnes",
}

# ---------------------------------------------------------------------------
# Schemas PyArrow para validação/cast antes do INSERT
# ---------------------------------------------------------------------------
def _sia_pa_schema() -> pa.Schema:
    return pa.schema([
        ("uf_sigla",              pa.string()),
        ("municipio_codigo",      pa.string()),
        ("competencia_ano",       pa.int16()),
        ("competencia_mes",       pa.int16()),
        ("procedimento_codigo",   pa.string()),
        ("complexidade",          pa.string()),
        ("quantidade_aprovada",   pa.int32()),
        ("valor_aprovado",        pa.float64()),
        ("cns_pac",               pa.string()),
        ("dt_atendimento",        pa.date32()),
    ])


def _sim_do_schema() -> pa.Schema:
    return pa.schema([
        ("uf_sigla",          pa.string()),
        ("municipio_codigo",  pa.string()),
        ("ano_obito",         pa.int16()),
        ("mes_obito",         pa.int16()),
        ("causa_basica",      pa.string()),
        ("causa_cap1",        pa.string()),
        ("sexo",              pa.string()),
        ("idade_anos",        pa.int16()),
        ("raca_cor",          pa.string()),
        ("escolaridade",      pa.string()),
    ])


def _sih_aih_schema() -> pa.Schema:
    return pa.schema([
        ("uf_sigla",                pa.string()),
        ("municipio_codigo",        pa.string()),
        ("competencia_ano",         pa.int16()),
        ("competencia_mes",         pa.int16()),
        ("diag_principal",          pa.string()),
        ("diag_secundario",         pa.string()),
        ("procedimento_realizado",  pa.string()),
        ("carater_internacao",      pa.string()),
        ("dias_permanencia",        pa.int16()),
        ("valor_total",             pa.float64()),
        ("valor_servicos",          pa.float64()),
        ("obito",                   pa.bool_()),
        ("sexo",                    pa.string()),
        ("idade_anos",              pa.int16()),
    ])


def _sinan_schema() -> pa.Schema:
    return pa.schema([
        ("uf_sigla",          pa.string()),
        ("municipio_codigo",  pa.string()),
        ("ano_notificacao",   pa.int16()),
        ("semana_epidemio",   pa.int16()),
        ("agravo_codigo",     pa.string()),
        ("classificacao",     pa.string()),
        ("evolucao",          pa.string()),
        ("sexo",              pa.string()),
        ("idade_anos",        pa.int16()),
        ("raca_cor",          pa.string()),
    ])


def _cnes_schema() -> pa.Schema:
    return pa.schema([
        ("uf_sigla",               pa.string()),
        ("cnes_codigo",            pa.string()),
        ("municipio_codigo",       pa.string()),
        ("nome_estabelecimento",   pa.string()),
        ("tipo_unidade",           pa.string()),
        ("gestao",                 pa.string()),
        ("leitos_sus",             pa.int32()),
        ("leitos_nao_sus",         pa.int32()),
        ("medicos",                pa.int32()),
        ("enfermeiros",            pa.int32()),
        ("equipamentos_tc",        pa.int32()),
        ("equipamentos_rm",        pa.int32()),
        ("competencia_ano",        pa.int16()),
        ("competencia_mes",        pa.int16()),
        ("latitude",               pa.float64()),
        ("longitude",              pa.float64()),
    ])


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class IngestTask:
    estado:  str
    sistema: str
    ano:     int
    mes:     Optional[int] = None  # None = anual; int = mensal (SIA/PA, SIH, CNES)
    retries: int = 0

    @property
    def key(self) -> str:
        m = f"/{self.mes:02d}" if self.mes else ""
        return f"{self.estado}/{self.sistema}/{self.ano}{m}"


@dataclass
class IngestResult:
    task:    IngestTask
    success: bool
    registros: int = 0
    duracao_s: float = 0.0
    erro:    Optional[str] = None


@dataclass
class IngestStats:
    total:     int = 0
    success:   int = 0
    skipped:   int = 0
    errors:    int = 0
    registros: int = 0
    inicio:    datetime = field(default_factory=datetime.now)

    @property
    def elapsed(self) -> str:
        d = (datetime.now() - self.inicio).total_seconds()
        h, r = divmod(int(d), 3600)
        m, s = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @property
    def throughput(self) -> str:
        d = (datetime.now() - self.inicio).total_seconds() or 1
        return f"{self.registros / d:,.0f} reg/s"


# ---------------------------------------------------------------------------
# Logging colorido
# ---------------------------------------------------------------------------
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\033[0;36m",   # cyan
        logging.INFO:     "\033[0;32m",   # green
        logging.WARNING:  "\033[0;33m",   # yellow
        logging.ERROR:    "\033[0;31m",   # red
        logging.CRITICAL: "\033[1;31m",   # bright red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        msg = super().format(record)
        return f"{color}{msg}{self.RESET}"


def setup_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger("ingest_all_states")
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)
    return logger


# ---------------------------------------------------------------------------
# Controle de ingestão (idempotência)
# ---------------------------------------------------------------------------
async def check_already_done(
    conn: asyncpg.Connection,
    task: IngestTask,
) -> bool:
    """Retorna True se a tarefa já foi concluída com sucesso."""
    row = await conn.fetchrow(
        """
        SELECT status FROM raw.ingestao_controle
        WHERE uf_sigla = $1 AND sistema = $2 AND ano = $3
          AND ($4::smallint IS NULL OR mes = $4)
        """,
        task.estado, task.sistema, task.ano, task.mes,
    )
    return row is not None and row["status"] == "done"


async def mark_running(conn: asyncpg.Connection, task: IngestTask) -> None:
    await conn.execute(
        """
        INSERT INTO raw.ingestao_controle
            (uf_sigla, sistema, ano, mes, status, iniciado_em)
        VALUES ($1, $2, $3, $4, 'running', NOW())
        ON CONFLICT (uf_sigla, sistema, ano, mes) DO UPDATE
          SET status = 'running', iniciado_em = NOW(), erro_mensagem = NULL
        """,
        task.estado, task.sistema, task.ano, task.mes,
    )


async def mark_done(
    conn: asyncpg.Connection, task: IngestTask, registros: int
) -> None:
    await conn.execute(
        """
        UPDATE raw.ingestao_controle
           SET status = 'done', registros_carga = $4, concluido_em = NOW()
         WHERE uf_sigla = $1 AND sistema = $2 AND ano = $3
           AND ($5::smallint IS NULL OR mes = $5)
        """,
        task.estado, task.sistema, task.ano, registros, task.mes,
    )


async def mark_error(
    conn: asyncpg.Connection, task: IngestTask, erro: str
) -> None:
    await conn.execute(
        """
        UPDATE raw.ingestao_controle
           SET status = 'error', erro_mensagem = $4, concluido_em = NOW()
         WHERE uf_sigla = $1 AND sistema = $2 AND ano = $3
           AND ($5::smallint IS NULL OR mes = $5)
        """,
        task.estado, task.sistema, task.ano, erro[:2000], task.mes,
    )


# ---------------------------------------------------------------------------
# Download PySUS → Parquet
# ---------------------------------------------------------------------------
def download_pysus(
    task: IngestTask,
    parquet_dir: Path,
    logger: logging.Logger,
) -> Path:
    """
    Baixa dados do DataSUS via PySUS e salva como Parquet hive-particionado.
    Retorna o caminho do diretório Parquet gerado.

    Hive path: parquet_dir/{sistema}/estado={UF}/ano={ANO}/data.parquet
    """
    try:
        from pysus.online_data import SIA, SIM, SIH, SINAN as SN, CNES as CN
    except ImportError:
        raise RuntimeError(
            "PySUS não instalado. Execute: pip install pysus --break-system-packages"
        )

    config = SISTEMA_CONFIG[task.sistema]
    subdir = config["parquet_subdir"]
    out_dir = parquet_dir / subdir / f"estado={task.estado}" / f"ano={task.ano}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.parquet"

    if out_file.exists():
        logger.debug(f"  [PARQUET CACHE] {task.key} — {out_file}")
        return out_file

    logger.info(f"  [DOWNLOAD] {task.key} via PySUS...")

    # Chamada PySUS específica por sistema
    if task.sistema == "SIA/PA":
        files = SIA.download(task.estado, task.ano, grupo="PA")
    elif task.sistema == "SIM/DO":
        files = SIM.download(task.estado, task.ano)
    elif task.sistema == "SIH/AIH":
        files = SIH.download(task.estado, task.ano, grupo="RD")
    elif task.sistema == "SINAN":
        files = SN.download(task.estado, task.ano)
    elif task.sistema == "CNES":
        files = CN.download(task.estado, task.ano, grupo="LT")
    else:
        raise ValueError(f"Sistema desconhecido: {task.sistema}")

    # PySUS retorna DataFrame(s) — consolida e salva como Parquet
    import pandas as pd

    if isinstance(files, list):
        df = pd.concat(files, ignore_index=True)
    elif hasattr(files, "to_dataframe"):
        df = files.to_dataframe()
    else:
        df = files

    if df.empty:
        logger.warning(f"  [VAZIO] {task.key} — nenhum registro retornado pelo PySUS")

    # Adiciona coluna uf_sigla se não existir (garantia)
    if "uf_sigla" not in df.columns:
        df["uf_sigla"] = task.estado

    # Salva Parquet com compressão snappy
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, out_file, compression="snappy")
    logger.info(f"  [PARQUET] {task.key} — {len(df):,} registros → {out_file}")

    return out_file


# ---------------------------------------------------------------------------
# Carga Parquet → PostgreSQL
# ---------------------------------------------------------------------------
async def load_parquet_to_pg(
    pool: asyncpg.Pool,
    task: IngestTask,
    parquet_file: Path,
    logger: logging.Logger,
    batch_size: int = 5_000,
) -> int:
    """
    Lê Parquet e insere em lotes no PostgreSQL via asyncpg.executemany.
    Retorna quantidade de registros inseridos.
    """
    import pandas as pd

    tabela = SISTEMA_TABELA[task.sistema]

    df = pd.read_parquet(parquet_file)
    if df.empty:
        return 0

    # Garante coluna uf_sigla
    if "uf_sigla" not in df.columns:
        df["uf_sigla"] = task.estado

    # Filtra somente colunas do schema da tabela
    config  = SISTEMA_CONFIG[task.sistema]
    schema  = config["schema"]
    cols    = [f.name for f in schema]
    present = [c for c in cols if c in df.columns]
    df      = df[present].copy()

    # Converte tipos NaN → None para compatibilidade asyncpg
    df = df.where(df.notna(), other=None)

    total_inserido = 0
    async with pool.acquire() as conn:
        await mark_running(conn, task)

        # DELETE idempotente antes de inserir (permite re-run)
        if task.mes:
            await conn.execute(
                f"DELETE FROM {tabela} WHERE uf_sigla=$1 AND competencia_ano=$2 AND competencia_mes=$3",
                task.estado, task.ano, task.mes,
            )
        else:
            year_col = "ano_obito" if task.sistema == "SIM/DO" else \
                       "ano_notificacao" if task.sistema == "SINAN" else \
                       "competencia_ano"
            await conn.execute(
                f"DELETE FROM {tabela} WHERE uf_sigla=$1 AND {year_col}=$2",
                task.estado, task.ano,
            )

        # INSERT em lotes
        placeholders = ", ".join(f"${i+1}" for i in range(len(present)))
        insert_sql = f"INSERT INTO {tabela} ({', '.join(present)}) VALUES ({placeholders})"

        for start in range(0, len(df), batch_size):
            batch = df.iloc[start : start + batch_size]
            records = [tuple(row) for row in batch.itertuples(index=False)]
            await conn.executemany(insert_sql, records)
            total_inserido += len(records)

        await mark_done(conn, task, total_inserido)

    return total_inserido


# ---------------------------------------------------------------------------
# Worker síncrono (executado em thread)
# ---------------------------------------------------------------------------
def run_ingest_task(
    task: IngestTask,
    parquet_dir: Path,
    db_url: str,
    logger: logging.Logger,
    dry_run: bool = False,
) -> IngestResult:
    """
    Função executada em cada thread do ThreadPoolExecutor.
    Combina download PySUS (IO-bound) + carga asyncpg (async).
    """
    t0 = time.monotonic()

    if dry_run:
        logger.info(f"  [DRY-RUN] {task.key}")
        return IngestResult(task=task, success=True, registros=0, duracao_s=0.0)

    try:
        # Verifica idempotência (nova conexão por thread)
        loop = asyncio.new_event_loop()
        already_done = loop.run_until_complete(
            _check_done_sync(db_url, task)
        )
        if already_done:
            logger.info(f"  [SKIP] {task.key} — já concluído (idempotência)")
            loop.close()
            return IngestResult(task=task, success=True, registros=0, duracao_s=0.0)

        # Download PySUS → Parquet
        parquet_file = download_pysus(task, parquet_dir, logger)

        # Carga Parquet → PostgreSQL
        registros = loop.run_until_complete(
            _load_sync(db_url, task, parquet_file, logger)
        )
        loop.close()

        elapsed = time.monotonic() - t0
        logger.info(
            f"  ✅ {task.key} — {registros:,} registros em {elapsed:.1f}s"
        )
        return IngestResult(
            task=task, success=True, registros=registros, duracao_s=elapsed
        )

    except Exception as exc:
        elapsed = time.monotonic() - t0
        erro_msg = str(exc)
        logger.error(f"  ❌ {task.key} — {erro_msg[:200]}")

        # Marca erro na tabela de controle
        try:
            loop2 = asyncio.new_event_loop()
            loop2.run_until_complete(_mark_error_sync(db_url, task, erro_msg))
            loop2.close()
        except Exception:
            pass

        return IngestResult(
            task=task, success=False, duracao_s=elapsed, erro=erro_msg
        )


async def _check_done_sync(db_url: str, task: IngestTask) -> bool:
    conn = await asyncpg.connect(db_url)
    try:
        return await check_already_done(conn, task)
    finally:
        await conn.close()


async def _load_sync(
    db_url: str, task: IngestTask, parquet_file: Path, logger: logging.Logger
) -> int:
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=3)
    try:
        return await load_parquet_to_pg(pool, task, parquet_file, logger)
    finally:
        await pool.close()


async def _mark_error_sync(db_url: str, task: IngestTask, erro: str) -> None:
    conn = await asyncpg.connect(db_url)
    try:
        await mark_error(conn, task, erro)
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------
def build_task_list(
    estados: list[str],
    sistemas: list[str],
    anos: list[int],
) -> list[IngestTask]:
    """Gera lista completa de tarefas: estados × sistemas × anos."""
    tasks = []
    for estado in estados:
        for sistema in sistemas:
            for ano in anos:
                tasks.append(IngestTask(estado=estado, sistema=sistema, ano=ano))
    return tasks


def print_progress(stats: IngestStats, logger: logging.Logger) -> None:
    pct = stats.success / max(stats.total, 1) * 100
    logger.info(
        f"  📊 Progresso: {stats.success}/{stats.total} ({pct:.1f}%) | "
        f"Erros: {stats.errors} | Skip: {stats.skipped} | "
        f"Registros: {stats.registros:,} | "
        f"Tempo: {stats.elapsed} | Throughput: {stats.throughput}"
    )


def run_all(
    estados:    list[str],
    sistemas:   list[str],
    anos:       list[int],
    parquet_dir: Path,
    db_url:     str,
    workers:    int = 8,
    dry_run:    bool = False,
    retry_errors: bool = False,
    max_retries:  int = 3,
    logger:     Optional[logging.Logger] = None,
) -> IngestStats:
    if logger is None:
        logger = setup_logging()

    tasks = build_task_list(estados, sistemas, anos)
    stats = IngestStats(total=len(tasks))

    logger.info("=" * 70)
    logger.info("🇧🇷 saude-publica-br — Ingestão Nacional (Fase 10)")
    logger.info(f"   Estados  : {len(estados)} ({', '.join(estados[:5])}{'...' if len(estados) > 5 else ''})")
    logger.info(f"   Sistemas : {', '.join(sistemas)}")
    logger.info(f"   Anos     : {min(anos)}–{max(anos)}")
    logger.info(f"   Tarefas  : {len(tasks):,}")
    logger.info(f"   Workers  : {workers}")
    logger.info(f"   Dry-run  : {dry_run}")
    logger.info("=" * 70)

    failed_tasks: list[IngestTask] = []
    progress_interval = max(1, len(tasks) // 20)  # log a cada ~5%

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                run_ingest_task, task, parquet_dir, db_url, logger, dry_run
            ): task
            for task in tasks
        }

        completed = 0
        for future in as_completed(futures):
            result: IngestResult = future.result()
            completed += 1

            if result.success:
                if result.registros > 0:
                    stats.success += 1
                    stats.registros += result.registros
                else:
                    stats.skipped += 1  # já estava done
            else:
                stats.errors += 1
                failed_tasks.append(result.task)

            if completed % progress_interval == 0:
                print_progress(stats, logger)

    # Retry automático para tarefas com erro
    if retry_errors and failed_tasks and max_retries > 0:
        logger.warning(
            f"\n⚠️  Retentando {len(failed_tasks)} tarefas com erro "
            f"(tentativa 2/{max_retries + 1})..."
        )
        retry_tasks = failed_tasks
        for attempt in range(1, max_retries + 1):
            if not retry_tasks:
                break
            still_failing = []
            with ThreadPoolExecutor(max_workers=min(workers, len(retry_tasks))) as ex:
                futs = {
                    ex.submit(
                        run_ingest_task, task, parquet_dir, db_url, logger, dry_run
                    ): task
                    for task in retry_tasks
                }
                for fut in as_completed(futs):
                    res: IngestResult = fut.result()
                    if res.success:
                        stats.errors -= 1
                        stats.success += 1
                        stats.registros += res.registros
                    else:
                        still_failing.append(res.task)
            retry_tasks = still_failing

    # Resumo final
    logger.info("\n" + "=" * 70)
    logger.info("📋 RESUMO FINAL — Ingestão Nacional")
    logger.info(f"   Total tarefas    : {stats.total:,}")
    logger.info(f"   ✅ Concluídas    : {stats.success:,}")
    logger.info(f"   ⏭️  Ignoradas     : {stats.skipped:,}")
    logger.info(f"   ❌ Erros         : {stats.errors:,}")
    logger.info(f"   📦 Registros     : {stats.registros:,}")
    logger.info(f"   ⏱️  Tempo total   : {stats.elapsed}")
    logger.info(f"   🚀 Throughput    : {stats.throughput}")
    logger.info("=" * 70)

    if failed_tasks:
        logger.error("\nTarefas com falha:")
        for t in failed_tasks:
            logger.error(f"  - {t.key}")

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Ingestão paralela DataSUS — 27 estados (Fase 10)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--estados", nargs="+", default=ESTADOS_BR, metavar="UF",
        help="Siglas dos estados (padrão: todos os 27)",
    )
    p.add_argument(
        "--sistemas", nargs="+", default=SISTEMAS, metavar="SIS",
        choices=SISTEMAS + [s.replace("/", "_") for s in SISTEMAS],
        help="Sistemas DataSUS (padrão: todos os 5)",
    )
    p.add_argument(
        "--anos", nargs="+", type=int, default=ANOS_DEFAULT, metavar="ANO",
        help="Anos a ingerir (padrão: 2019–2024)",
    )
    p.add_argument(
        "--parquet-dir", type=Path,
        default=Path(os.environ.get("PARQUET_DIR", "data/parquet")),
        help="Diretório base para arquivos Parquet",
    )
    p.add_argument(
        "--db-url",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/saude_publica"
        ),
        help="URL de conexão PostgreSQL",
    )
    p.add_argument(
        "--workers", type=int, default=8,
        help="Número de threads paralelas (padrão: 8)",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Simula execução sem downloads ou inserts",
    )
    p.add_argument(
        "--retry-errors", action="store_true",
        help="Retentar automaticamente tarefas com erro",
    )
    p.add_argument(
        "--max-retries", type=int, default=3,
        help="Número máximo de tentativas por tarefa (padrão: 3)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true",
        help="Logging detalhado (DEBUG)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logger = setup_logging(args.verbose)

    # Normaliza sistemas (aceita SIA_PA ou SIA/PA)
    sistemas = [s.replace("_", "/") for s in args.sistemas]

    stats = run_all(
        estados=args.estados,
        sistemas=sistemas,
        anos=args.anos,
        parquet_dir=args.parquet_dir,
        db_url=args.db_url,
        workers=args.workers,
        dry_run=args.dry_run,
        retry_errors=args.retry_errors,
        max_retries=args.max_retries,
        logger=logger,
    )

    sys.exit(0 if stats.errors == 0 else 1)


if __name__ == "__main__":
    main()
