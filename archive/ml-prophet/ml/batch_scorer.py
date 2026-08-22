"""
ml/batch_scorer.py
==================
Processador batch de anomalias via Prophet para todos os municípios do SUS.

Fluxo:
  1. Carrega lista de municípios com histórico em mart_producao_amb
  2. Para cada município, chama detect_anomalies() — Prophet se ≥24 meses,
     Z-score caso contrário
  3. Persiste resultados na tabela mart_anomalias_prophet via UPSERT

Execução via CLI:
  python -m ml.batch_scorer run
  python -m ml.batch_scorer run --uf SP --sigma 2.0 --workers 8
  python -m ml.batch_scorer run --since 202301   # apenas competências após jan/2023

Uso programático (Prefect / cron):
  from ml.batch_scorer import run_batch
  asyncio.run(run_batch(db_url, sigma=2.0))
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import pandas as pd

logger = logging.getLogger("saude-publica-br.ml.batch_scorer")


# ---------------------------------------------------------------------------
# DDL — tabela de resultados pré-computados
# ---------------------------------------------------------------------------

DDL_MART_ANOMALIAS_PROPHET = """
CREATE TABLE IF NOT EXISTS mart_anomalias_prophet (
    id                  BIGSERIAL    PRIMARY KEY,
    municipio_cod       TEXT         NOT NULL,
    municipio_nome      TEXT,
    uf_sigla            TEXT         NOT NULL,
    mes_competencia     TEXT         NOT NULL,  -- AAAAMM
    ano                 INTEGER      NOT NULL,
    mes                 INTEGER      NOT NULL,
    total_procedimentos INTEGER,
    yhat                DOUBLE PRECISION,
    yhat_lower          DOUBLE PRECISION,
    yhat_upper          DOUBLE PRECISION,
    z_score             DOUBLE PRECISION,
    tipo_anomalia       TEXT,
    pct_desvio          DOUBLE PRECISION,
    is_anomaly          BOOLEAN      NOT NULL DEFAULT FALSE,
    metodo              TEXT         NOT NULL DEFAULT 'prophet',
    n_pontos            INTEGER,
    scored_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_anomalia_prophet UNIQUE (municipio_cod, mes_competencia)
);
CREATE INDEX IF NOT EXISTS idx_anomalias_prophet_uf
    ON mart_anomalias_prophet (uf_sigla);
CREATE INDEX IF NOT EXISTS idx_anomalias_prophet_competencia
    ON mart_anomalias_prophet (mes_competencia);
CREATE INDEX IF NOT EXISTS idx_anomalias_prophet_anomalias
    ON mart_anomalias_prophet (is_anomaly, uf_sigla)
    WHERE is_anomaly = TRUE;
"""

# SQL para buscar a série histórica de um município
QUERY_SERIE = """
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        mes_competencia,
        ano,
        mes,
        total_procedimentos
    FROM mart_producao_amb
    WHERE municipio_cod = $1
    ORDER BY mes_competencia ASC
"""

# SQL para listar todos os municípios a processar
QUERY_MUNICIPIOS = """
    SELECT DISTINCT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        COUNT(*) AS n_meses
    FROM mart_producao_amb
    {where_extra}
    GROUP BY municipio_cod, municipio_nome, uf_sigla
    ORDER BY n_meses DESC
"""

# UPSERT na tabela de resultados
UPSERT_ROW = """
    INSERT INTO mart_anomalias_prophet (
        municipio_cod, municipio_nome, uf_sigla,
        mes_competencia, ano, mes,
        total_procedimentos,
        yhat, yhat_lower, yhat_upper,
        z_score, tipo_anomalia, pct_desvio, is_anomaly,
        metodo, n_pontos, scored_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6,
        $7, $8, $9, $10,
        $11, $12, $13, $14,
        $15, $16, NOW()
    )
    ON CONFLICT (municipio_cod, mes_competencia)
    DO UPDATE SET
        municipio_nome      = EXCLUDED.municipio_nome,
        total_procedimentos = EXCLUDED.total_procedimentos,
        yhat                = EXCLUDED.yhat,
        yhat_lower          = EXCLUDED.yhat_lower,
        yhat_upper          = EXCLUDED.yhat_upper,
        z_score             = EXCLUDED.z_score,
        tipo_anomalia       = EXCLUDED.tipo_anomalia,
        pct_desvio          = EXCLUDED.pct_desvio,
        is_anomaly          = EXCLUDED.is_anomaly,
        metodo              = EXCLUDED.metodo,
        n_pontos            = EXCLUDED.n_pontos,
        scored_at           = NOW()
"""


# ---------------------------------------------------------------------------
# Dataclass de estatísticas do batch
# ---------------------------------------------------------------------------

@dataclass
class BatchStats:
    total: int = 0
    prophet: int = 0
    zscore: int = 0
    erros: int = 0
    rows_written: int = 0
    elapsed_s: float = 0.0

    @property
    def taxa_erro(self) -> float:
        return (self.erros / self.total * 100) if self.total else 0.0

    def log_summary(self) -> None:
        logger.info(
            "Batch concluído em %.1fs | municípios=%d prophet=%d zscore=%d erros=%d(%.1f%%) "
            "linhas_gravadas=%d",
            self.elapsed_s, self.total, self.prophet, self.zscore,
            self.erros, self.taxa_erro, self.rows_written,
        )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _float_or_none(v) -> Optional[float]:
    """Converte NaN/inf para None para compatibilidade com PostgreSQL."""
    if v is None:
        return None
    try:
        f = float(v)
        return f if (f == f and abs(f) < 1e15) else None  # NaN/inf → None
    except (TypeError, ValueError):
        return None


async def _ensure_table(conn) -> None:
    """Cria mart_anomalias_prophet se não existir."""
    await conn.execute(DDL_MART_ANOMALIAS_PROPHET)
    logger.info("Tabela mart_anomalias_prophet verificada/criada.")


async def _load_serie(conn, municipio_cod: str) -> pd.DataFrame:
    """Carrega série temporal de um município do banco."""
    rows = await conn.fetch(QUERY_SERIE, municipio_cod)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])


async def _list_municipios(conn, uf_sigla: Optional[str] = None) -> list[dict]:
    """Lista municípios a processar, opcionalmente filtrado por UF."""
    where = f"WHERE uf_sigla = '{uf_sigla.upper()}'" if uf_sigla else ""
    query = QUERY_MUNICIPIOS.format(where_extra=where)
    rows = await conn.fetch(query)
    return [dict(r) for r in rows]


async def _write_results(conn, municipio_nome: Optional[str], result) -> int:
    """
    Persiste AnomalyResult (anomalias + forecast) para um município.
    Retorna número de linhas gravadas.
    """
    if result.forecast is None or result.forecast.empty:
        return 0

    fc = result.forecast.copy()

    # Garante coluna mes_competencia no formato AAAAMM
    if "mes_competencia" not in fc.columns:
        fc["mes_competencia"] = (
            fc["ds"].dt.year.astype(str)
            + fc["ds"].dt.month.astype(str).str.zfill(2)
        )
    if "ano" not in fc.columns:
        fc["ano"] = fc["ds"].dt.year
    if "mes" not in fc.columns:
        fc["mes"] = fc["ds"].dt.month

    rows_written = 0
    async with conn.transaction():
        for _, row in fc.iterrows():
            is_anomaly = bool(row.get("is_anomaly", False))
            await conn.execute(
                UPSERT_ROW,
                result.municipio_cod,
                municipio_nome,
                result.uf_sigla,
                str(row["mes_competencia"]),
                int(row["ano"]),
                int(row["mes"]),
                int(row["y"]) if "y" in row and row["y"] == row["y"] else None,
                _float_or_none(row.get("yhat")),
                _float_or_none(row.get("yhat_lower")),
                _float_or_none(row.get("yhat_upper")),
                _float_or_none(row.get("z_score")),
                str(row["tipo_anomalia"]) if "tipo_anomalia" in row and row["tipo_anomalia"] else None,
                _float_or_none(row.get("pct_desvio")),
                is_anomaly,
                str(result.metodo),
                int(result.n_pontos),
            )
            rows_written += 1

    return rows_written


# ---------------------------------------------------------------------------
# Função principal de scoring de um município (roda em thread pool)
# ---------------------------------------------------------------------------


def _score_sync(
    df: pd.DataFrame,
    municipio_cod: str,
    uf_sigla: str,
    sigma: float,
    min_periods: int,
) -> object:
    """
    Executa detect_anomalies() de forma síncrona (para ser chamado via
    run_in_executor sem bloquear o event loop).
    """
    from ml.anomaly_detector import detect_anomalies
    return detect_anomalies(
        df=df,
        municipio_cod=municipio_cod,
        uf_sigla=uf_sigla,
        sigma=sigma,
        min_periods=min_periods,
        future_periods=0,
    )


async def _score_municipio(
    pool,
    mun: dict,
    sigma: float,
    min_periods: int,
    semaphore: asyncio.Semaphore,
    stats: BatchStats,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Processa um município: lê série → detecta → grava resultados."""
    municipio_cod: str = mun["municipio_cod"]
    municipio_nome: Optional[str] = mun.get("municipio_nome")
    uf_sigla: str = mun["uf_sigla"]

    async with semaphore:
        try:
            async with pool.acquire() as conn:
                df = await _load_serie(conn, municipio_cod)

            if df.empty:
                logger.debug("Série vazia: %s", municipio_cod)
                return

            # Executa Prophet (ou Z-score fallback) em thread pool para não
            # bloquear o event loop (Prophet usa scipy/numpy que liberam GIL)
            result = await loop.run_in_executor(
                None,
                _score_sync,
                df, municipio_cod, uf_sigla, sigma, min_periods,
            )

            if result.erro:
                logger.warning("Erro em %s: %s", municipio_cod, result.erro)
                stats.erros += 1
                return

            # Persiste
            async with pool.acquire() as conn:
                rows = await _write_results(conn, municipio_nome, result)

            stats.rows_written += rows
            if result.metodo == "prophet":
                stats.prophet += 1
            else:
                stats.zscore += 1

        except Exception as exc:
            logger.error("Exceção inesperada em %s: %s", municipio_cod, exc, exc_info=True)
            stats.erros += 1
        finally:
            stats.total += 1
            if stats.total % 100 == 0:
                logger.info(
                    "Progresso: %d/%d municípios (prophet=%d zscore=%d erros=%d)",
                    stats.total, stats.total + 1,  # aproximação
                    stats.prophet, stats.zscore, stats.erros,
                )


# ---------------------------------------------------------------------------
# Entrypoint principal
# ---------------------------------------------------------------------------


async def run_batch(
    db_url: Optional[str] = None,
    uf_sigla: Optional[str] = None,
    sigma: float = 2.0,
    min_periods: int = 24,
    max_workers: int = 4,
    ensure_table: bool = True,
) -> BatchStats:
    """
    Executa o batch completo de scoring Prophet para todos os municípios.

    Args:
        db_url: Connection string PostgreSQL. Se None, usa DATABASE_URL env.
        uf_sigla: Filtro opcional por UF (ex: "SP").
        sigma: Limiar Z-score para classificar anomalia (padrão 2.0).
        min_periods: Mínimo de meses para usar Prophet (padrão 24).
        max_workers: Concorrência máxima de municípios em paralelo.
        ensure_table: Se True, cria a tabela se não existir.

    Returns:
        BatchStats com contadores de progresso.
    """
    import asyncpg

    url = db_url or os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL não definido.")

    t0 = time.monotonic()
    stats = BatchStats()
    loop = asyncio.get_event_loop()

    logger.info(
        "Iniciando batch scorer | uf=%s sigma=%.1f min_periods=%d workers=%d",
        uf_sigla or "ALL", sigma, min_periods, max_workers,
    )

    pool = await asyncpg.create_pool(
        url,
        min_size=2,
        max_size=max(2, max_workers + 2),
        command_timeout=120,
    )

    try:
        async with pool.acquire() as conn:
            if ensure_table:
                await _ensure_table(conn)
            municipios = await _list_municipios(conn, uf_sigla)

        if not municipios:
            logger.warning("Nenhum município encontrado para uf=%s", uf_sigla)
            return stats

        logger.info("Municípios a processar: %d", len(municipios))

        semaphore = asyncio.Semaphore(max_workers)
        tasks = [
            _score_municipio(pool, mun, sigma, min_periods, semaphore, stats, loop)
            for mun in municipios
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    finally:
        await pool.close()
        stats.elapsed_s = time.monotonic() - t0
        stats.log_summary()

    return stats


# ---------------------------------------------------------------------------
# CLI (click)
# ---------------------------------------------------------------------------

try:
    import click

    @click.group()
    def cli() -> None:
        """ml.batch_scorer — Pré-computa anomalias Prophet para todos os municípios."""
        logging.basicConfig(
            level="INFO",
            format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        )

    @cli.command()
    @click.option("--db-url", envvar="DATABASE_URL", required=False,
                  help="PostgreSQL connection string (fallback: DATABASE_URL env)")
    @click.option("--uf", default=None, help="Filtrar por sigla de UF (ex: SP)")
    @click.option("--sigma", default=2.0, show_default=True,
                  help="Limiar Z-score para anomalia")
    @click.option("--min-periods", default=24, show_default=True,
                  help="Mínimo de meses para usar Prophet (< usa Z-score)")
    @click.option("--workers", default=4, show_default=True,
                  help="Número de municípios processados em paralelo")
    @click.option("--no-create-table", is_flag=True, default=False,
                  help="Não tentar criar a tabela mart_anomalias_prophet")
    def run(
        db_url: Optional[str],
        uf: Optional[str],
        sigma: float,
        min_periods: int,
        workers: int,
        no_create_table: bool,
    ) -> None:
        """Executa o batch scorer para todos os municípios (ou apenas a UF indicada)."""
        import sys

        stats = asyncio.run(
            run_batch(
                db_url=db_url,
                uf_sigla=uf,
                sigma=sigma,
                min_periods=min_periods,
                max_workers=workers,
                ensure_table=not no_create_table,
            )
        )

        if stats.erros > 0 and stats.erros == stats.total:
            click.secho("FALHA: todos os municípios retornaram erros.", fg="red")
            sys.exit(1)

        click.secho(
            f"✓ Concluído: {stats.total} municípios | "
            f"prophet={stats.prophet} zscore={stats.zscore} erros={stats.erros} | "
            f"{stats.rows_written} linhas gravadas em {stats.elapsed_s:.1f}s",
            fg="green",
        )

    if __name__ == "__main__":
        cli()

except ImportError:
    # click não instalado — apenas o run_batch() programático fica disponível
    pass
