"""
ingestion_log.py
Controle incremental de ingestão — evita recarregar dados já processados.
Tabela: public.ingestion_log (estado, ano, mes, sistema, loaded_at, qtd_registros, status)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import psycopg
from loguru import logger

DATABASE_URL = os.getenv("DATABASE_URL", "")


class IngestionStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    ERROR     = "error"
    SKIPPED   = "skipped"


@dataclass
class IngestionEntry:
    estado:         str
    ano:            int
    mes:            int
    sistema:        str          # 'SIA_PA', 'SIM', 'SIH', etc.
    status:         IngestionStatus
    loaded_at:      Optional[datetime] = None
    qtd_registros:  Optional[int]      = None
    error_msg:      Optional[str]      = None
    elapsed_sec:    Optional[float]    = None


# ---------------------------------------------------------------------------
# DDL — cria tabela se não existir
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.ingestion_log (
    id              BIGSERIAL PRIMARY KEY,
    estado          VARCHAR(2)   NOT NULL,
    ano             SMALLINT     NOT NULL,
    mes             SMALLINT     NOT NULL,
    sistema         VARCHAR(20)  NOT NULL DEFAULT 'SIA_PA',
    status          VARCHAR(10)  NOT NULL DEFAULT 'pending',
    loaded_at       TIMESTAMPTZ,
    qtd_registros   INTEGER,
    error_msg       TEXT,
    elapsed_sec     NUMERIC(8,2),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (estado, ano, mes, sistema)
);

CREATE INDEX IF NOT EXISTS idx_ingestion_log_estado_ano
    ON public.ingestion_log (estado, ano, sistema);

CREATE INDEX IF NOT EXISTS idx_ingestion_log_status
    ON public.ingestion_log (status);

COMMENT ON TABLE public.ingestion_log IS
    'Controle incremental de ingestão DataSUS. '
    'Chave: (estado, ano, mes, sistema) — skipa se status=success.';
"""


def ensure_table(database_url: Optional[str] = None) -> None:
    """Cria a tabela ingestion_log se não existir."""
    db_url = database_url or DATABASE_URL
    with psycopg.connect(db_url) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
    logger.info("ingestion_log: tabela verificada/criada")


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def is_already_loaded(
    estado: str,
    ano: int,
    mes: int,
    sistema: str = "SIA_PA",
    database_url: Optional[str] = None,
) -> bool:
    """Retorna True se (estado, ano, mes, sistema) já foi carregado com sucesso."""
    db_url = database_url or DATABASE_URL
    with psycopg.connect(db_url) as conn:
        row = conn.execute(
            "SELECT 1 FROM public.ingestion_log "
            "WHERE estado = %s AND ano = %s AND mes = %s "
            "  AND sistema = %s AND status = 'success'",
            (estado.upper(), ano, mes, sistema),
        ).fetchone()
    return row is not None


def get_pending_combinations(
    estados: list[str],
    anos: list[int],
    meses: list[int],
    sistema: str = "SIA_PA",
    database_url: Optional[str] = None,
) -> list[tuple[str, int, int]]:
    """
    Retorna lista de (estado, ano, mes) ainda não carregados.
    Útil para retomar uma ingestão interrompida.
    """
    db_url = database_url or DATABASE_URL
    
    all_combos = {
        (e.upper(), a, m)
        for e in estados
        for a in anos
        for m in meses
    }
    
    if not all_combos:
        return []

    with psycopg.connect(db_url) as conn:
        rows = conn.execute(
            "SELECT estado, ano, mes FROM public.ingestion_log "
            "WHERE sistema = %s AND status = 'success'",
            (sistema,),
        ).fetchall()
    
    loaded = {(r[0], r[1], r[2]) for r in rows}
    pending = sorted(all_combos - loaded)
    logger.info(
        f"Combinações pendentes: {len(pending)}/{len(all_combos)} "
        f"({len(loaded)} já carregadas)"
    )
    return pending


# ---------------------------------------------------------------------------
# Escrita de log
# ---------------------------------------------------------------------------

def upsert_log(
    entry: IngestionEntry,
    database_url: Optional[str] = None,
) -> None:
    """Insere ou atualiza um registro no log de ingestão."""
    db_url = database_url or DATABASE_URL
    with psycopg.connect(db_url) as conn:
        conn.execute(
            """
            INSERT INTO public.ingestion_log
                (estado, ano, mes, sistema, status, loaded_at,
                 qtd_registros, error_msg, elapsed_sec, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (estado, ano, mes, sistema)
            DO UPDATE SET
                status        = EXCLUDED.status,
                loaded_at     = EXCLUDED.loaded_at,
                qtd_registros = EXCLUDED.qtd_registros,
                error_msg     = EXCLUDED.error_msg,
                elapsed_sec   = EXCLUDED.elapsed_sec,
                updated_at    = NOW()
            """,
            (
                entry.estado.upper(),
                entry.ano,
                entry.mes,
                entry.sistema,
                entry.status.value,
                entry.loaded_at,
                entry.qtd_registros,
                entry.error_msg,
                entry.elapsed_sec,
            ),
        )
        conn.commit()
