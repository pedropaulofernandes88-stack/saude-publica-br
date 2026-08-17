"""
api/routers/exports.py
Exportação de dados em CSV, Excel e JSON com streaming e log de auditoria.
"""

from __future__ import annotations

import io
import json
import time
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from api.database import get_db
from api.middleware.auth import get_optional_user
from api.models.user import ExportFormat, ExportRequest, ExportResponse, UserPublic

router = APIRouter(prefix="/exports", tags=["Exportação de Dados"])

# URL interna da própria API (para buscar os dados antes de exportar)
_API_BASE = "http://localhost:8000"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    return fwd.split(",")[0].strip() if fwd else (request.client.host or "unknown")


async def _fetch_endpoint_data(endpoint: str, filtros: Dict[str, Any]) -> list[dict]:
    """Busca dados de um endpoint nacional interno."""
    params = {k: v for k, v in filtros.items() if v is not None}
    params["limite"] = 10_000   # exportação completa
    params["offset"] = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{_API_BASE}/nacional/{endpoint}", params=params)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erro ao buscar dados do endpoint /{endpoint}: {resp.text}",
            )
        payload = resp.json()

    # A API nacional retorna {"data": [...], "total": N, ...}
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def _to_csv_bytes(records: list[dict]) -> bytes:
    """Converte lista de dicts para CSV em bytes."""
    if not records:
        return b""
    import csv

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode("utf-8-sig")   # BOM para Excel reconhecer UTF-8


def _to_excel_bytes(records: list[dict]) -> bytes:
    """Converte lista de dicts para XLSX em bytes usando openpyxl."""
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="openpyxl não instalado. Use formato CSV ou JSON.",
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dados"

    if not records:
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    headers = list(records[0].keys())
    ws.append(headers)

    # Cabeçalho em negrito
    from openpyxl.styles import Font
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in records:
        ws.append([str(v) if v is not None else "" for v in row.values()])

    # Ajuste automático de colunas
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _to_json_bytes(records: list[dict]) -> bytes:
    return json.dumps(records, ensure_ascii=False, default=str, indent=2).encode("utf-8")


# ─── Endpoint de Exportação ───────────────────────────────────────────────────

@router.post("", response_model=ExportResponse, status_code=202)
async def solicitar_exportacao(
    body: ExportRequest,
    request: Request,
    conn: Connection = Depends(get_db),
    current_user: Optional[UserPublic] = Depends(get_optional_user),
):
    """
    Inicia exportação assíncrona.
    Para exportações pequenas (< 10k linhas) retorna redirect para download direto.
    Para exportações grandes, enfileira e retorna export_id para polling.
    """
    user_id = current_user.id if current_user else None

    # Log inicial com status 'queued'
    export_id = await conn.fetchval(
        """
        INSERT INTO public.exports_log
               (user_id, endpoint, formato, filtros, status, ip_origem)
        VALUES ($1, $2, $3, $4::jsonb, 'queued', $5::inet)
        RETURNING id
        """,
        user_id,
        body.endpoint,
        body.formato.value,
        json.dumps(body.filtros),
        _get_ip(request),
    )

    # Para MVP: processamento síncrono (substituir por fila Celery/Prefect em prod)
    return ExportResponse(
        export_id=export_id,
        status="queued",
        mensagem=(
            f"Exportação iniciada. "
            f"Acesse GET /exports/{export_id}/download para baixar o arquivo."
        ),
    )


@router.get("/{export_id}/download")
async def download_exportacao(
    export_id: UUID,
    request: Request,
    conn: Connection = Depends(get_db),
    current_user: Optional[UserPublic] = Depends(get_optional_user),
):
    """
    Executa e retorna o arquivo de exportação como streaming download.
    Atualiza o registro de log com status final.
    """
    row = await conn.fetchrow(
        "SELECT * FROM public.exports_log WHERE id = $1",
        export_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Exportação não encontrada")

    # Restrição: exportações de usuários autenticados são privadas
    user_id = current_user.id if current_user else None
    if row["user_id"] and row["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Sem permissão para este download")

    endpoint = row["endpoint"]
    formato  = ExportFormat(row["formato"])
    filtros  = row["filtros"] or {}

    # Atualizar para 'processing'
    await conn.execute(
        "UPDATE public.exports_log SET status = 'processing' WHERE id = $1", export_id
    )

    try:
        t0 = time.perf_counter()
        records = await _fetch_endpoint_data(endpoint, filtros)
        total   = len(records)

        if formato == ExportFormat.csv:
            data     = _to_csv_bytes(records)
            media    = "text/csv"
            filename = f"saude_publica_{endpoint.replace('/', '_')}.csv"
        elif formato == ExportFormat.excel:
            data     = _to_excel_bytes(records)
            media    = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"saude_publica_{endpoint.replace('/', '_')}.xlsx"
        else:   # json
            data     = _to_json_bytes(records)
            media    = "application/json"
            filename = f"saude_publica_{endpoint.replace('/', '_')}.json"

        tamanho = len(data)

        # Atualizar log com sucesso
        await conn.execute(
            """
            UPDATE public.exports_log
               SET status = 'done', total_linhas = $1,
                   tamanho_bytes = $2, atualizado_em = NOW()
             WHERE id = $3
            """,
            total, tamanho, export_id,
        )

        elapsed = time.perf_counter() - t0
        print(f"[EXPORT] {export_id} | {endpoint} | {formato.value} | {total} linhas | {tamanho} bytes | {elapsed:.2f}s")

        return StreamingResponse(
            io.BytesIO(data),
            media_type=media,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(tamanho),
                "X-Total-Records": str(total),
            },
        )

    except Exception as exc:
        await conn.execute(
            """
            UPDATE public.exports_log
               SET status = 'error', erro_msg = $1, atualizado_em = NOW()
             WHERE id = $2
            """,
            str(exc)[:500],
            export_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na exportação: {exc}",
        )


@router.get("/{export_id}/status", response_model=ExportResponse)
async def status_exportacao(
    export_id: UUID,
    conn: Connection = Depends(get_db),
):
    """Verifica status de uma exportação."""
    row = await conn.fetchrow(
        "SELECT * FROM public.exports_log WHERE id = $1", export_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Exportação não encontrada")

    download_url = None
    if row["status"] == "done":
        download_url = f"/exports/{export_id}/download"

    return ExportResponse(
        export_id=row["id"],
        status=row["status"],
        mensagem=f"Status: {row['status']}",
        download_url=download_url,
        total_linhas=row["total_linhas"],
        tamanho_bytes=row["tamanho_bytes"],
    )
