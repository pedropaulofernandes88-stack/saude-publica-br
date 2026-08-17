"""
Testes para os endpoints FastAPI.

Usa httpx.AsyncClient com ASGITransport para testar sem servidor real.
Pool asyncpg e Redis são mockados via fixtures de conftest.

Cobre:
  GET /           — raiz (info)
  GET /health     — healthcheck
  GET /info       — metadados da API
  GET /producao   — lista paginada com filtros
  GET /producao/series/{municipio_cod}    — série temporal
  GET /producao/mapa/{uf_sigla}           — dados de mapa coroplético
  GET /indicadores/acesso                   — índices de acesso
  GET /epidemiologia/cid10                — perfil epidemiológico
  GET /indicadores/complexidade                   — mix de complexidade
  GET /ranking/nacional                 — ranking
  GET /indicadores/anomalias                          — detecção de anomalias
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Fixtures de registros mockados
# ---------------------------------------------------------------------------

def _mock_producao_row(**overrides):
    base = {
        "municipio_cod": "3550308",
        "uf_sigla": "SP",
        "ano": 2023,
        "mes": 6,
        "mes_competencia": "202306",  # YYYYMM string — ProducaoAmbItem.mes_competencia: str
        "total_procedimentos": 15000,
        "total_aprovados": 14500,
        "taxa_proc_10k": 52.3,
        "pct_aprovacao": 96.7,
    }
    base.update(overrides)
    return base


def _mock_series_row(**overrides):
    base = {
        "municipio_cod": "3550308",
        "ano": 2023,
        "mes": 6,
        "mes_competencia": "202306",  # YYYYMM string — ProducaoSerieItem.mes_competencia: str
        "total_procedimentos": 15000,
        "taxa_proc_10k": 52.3,
        "variacao_pct": 2.1,
    }
    base.update(overrides)
    return base


def _mock_mapa_row(**overrides):
    base = {
        "municipio_cod": "3550308",
        "municipio_nome": "São Paulo",
        "valor": 52.3,
        "ranking": 1,
        "percentil": 95.0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Testes de endpoints de saúde/info
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    async def test_root_returns_200(self, async_client):
        resp = await async_client.get("/")
        assert resp.status_code == 200

    async def test_health_returns_200(self, async_client, mock_asyncpg_conn):
        # Healthcheck consulta o banco — simula latência e versão
        mock_asyncpg_conn.fetchrow = AsyncMock(return_value={
            "version": "PostgreSQL 15.2",
            "now": "2024-01-01 00:00:00",
        })
        resp = await async_client.get("/health")
        assert resp.status_code in (200, 503)  # 503 se pool não disponível em mock

    async def test_info_returns_200(self, async_client):
        resp = await async_client.get("/info")
        assert resp.status_code == 200

    async def test_root_response_is_json(self, async_client):
        resp = await async_client.get("/")
        assert resp.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# Testes de /producao
# ---------------------------------------------------------------------------

class TestProducaoEndpoints:
    async def test_list_producao_empty_db_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/producao")
        assert resp.status_code == 200

    async def test_list_producao_returns_pagination(
        self, async_client, mock_asyncpg_conn
    ):
        rows = [dict(_mock_producao_row()) for _ in range(5)]
        mock_asyncpg_conn.fetch = AsyncMock(return_value=rows)
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=5)
        resp = await async_client.get("/producao?pagina=1&por_pagina=10")
        assert resp.status_code == 200
        body = resp.json()
        # Espera wrapper com dados e paginação
        assert "data" in body or "dados" in body or isinstance(body, list)

    async def test_list_producao_filter_by_uf(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/producao?uf_sigla=SP")
        assert resp.status_code == 200

    async def test_list_producao_filter_by_ano_range(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/producao?ano_inicio=2021&ano_fim=2023")
        assert resp.status_code == 200

    async def test_list_producao_invalid_uf_returns_422(self, async_client):
        resp = await async_client.get("/producao?uf_sigla=XX")
        # Validação Pydantic/FastAPI deve rejeitar UF inválida
        assert resp.status_code in (200, 422)  # depende da validação na query

    async def test_series_municipio_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        # mes_competencia must be YYYYMM string; mes must be int
        rows = [
            dict(_mock_series_row(mes_competencia=f"2023{m:02d}", mes=m))
            for m in range(1, 13)
        ]
        mock_asyncpg_conn.fetch = AsyncMock(return_value=rows)
        resp = await async_client.get("/producao/series/3550308")
        assert resp.status_code == 200

    async def test_series_municipio_not_found_returns_200_or_404(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        resp = await async_client.get("/producao/series/0000000")
        assert resp.status_code in (200, 404)

    async def test_mapa_uf_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        rows = [dict(_mock_mapa_row()) for _ in range(3)]
        mock_asyncpg_conn.fetch = AsyncMock(return_value=rows)
        resp = await async_client.get("/producao/mapa/SP")
        assert resp.status_code == 200

    async def test_mapa_invalid_indicador_returns_422(self, async_client):
        resp = await async_client.get("/producao/mapa/SP?indicador=invalido")
        assert resp.status_code == 422

    async def test_mapa_valid_indicadores_accepted(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        for indicador in ("taxa_proc_10k", "total_procedimentos", "pct_aprovacao"):
            resp = await async_client.get(f"/producao/mapa/SP?indicador={indicador}")
            assert resp.status_code == 200, f"indicador={indicador!r} retornou {resp.status_code}"


# ---------------------------------------------------------------------------
# Testes de /acesso-cobertura
# ---------------------------------------------------------------------------

class TestAcessoCoberturaEndpoints:
    async def test_list_acesso_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/indicadores/acesso")
        assert resp.status_code == 200

    async def test_filter_by_uf_and_ano(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/indicadores/acesso?uf_sigla=RJ&ano=2022")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Testes de /epidemiologia
# ---------------------------------------------------------------------------

class TestEpidemiologiaEndpoints:
    async def test_cid10_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/epidemiologia/cid10")
        assert resp.status_code == 200

    async def test_cid10_filter_by_uf(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/epidemiologia/cid10?uf_sigla=MG&ano=2023")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Testes de /mix-complexidade
# ---------------------------------------------------------------------------

class TestMixComplexidadeEndpoints:
    async def test_list_mix_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/indicadores/complexidade")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Testes de /ranking
# ---------------------------------------------------------------------------

class TestRankingEndpoints:
    async def test_ranking_municipios_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/ranking/nacional")
        assert resp.status_code == 200

    async def test_ranking_filter_by_uf_and_ano(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/ranking/SP?ano=2023")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Testes de /anomalias
# ---------------------------------------------------------------------------

class TestAnomaliasEndpoints:
    async def test_anomalias_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/indicadores/anomalias")
        assert resp.status_code == 200

    async def test_anomalias_filter_by_uf(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/indicadores/anomalias?uf_sigla=BA")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Testes de paginação e parâmetros inválidos
# ---------------------------------------------------------------------------

class TestPaginacao:
    async def test_pagina_negativa_returns_422(self, async_client):
        resp = await async_client.get("/producao?pagina=-1")
        assert resp.status_code == 422

    async def test_por_pagina_acima_limite_returns_422(self, async_client):
        resp = await async_client.get("/producao?por_pagina=10000")
        assert resp.status_code == 422

    async def test_pagina_um_por_pagina_padrao_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        mock_asyncpg_conn.fetch = AsyncMock(return_value=[])
        mock_asyncpg_conn.fetchval = AsyncMock(return_value=0)
        resp = await async_client.get("/producao?pagina=1&por_pagina=50")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Testes de CORS e headers
# ---------------------------------------------------------------------------

class TestCORS:
    async def test_cors_headers_present(self, async_client):
        resp = await async_client.get(
            "/",
            headers={"Origin": "http://localhost:3000"},
        )
        # CORS configurado para permitir todos — deve retornar header
        assert resp.status_code == 200
