"""
Testes de integração da API para GET /indicadores/anomalias.

Cobre os três modos de detecção (prophet / zscore / auto), filtros,
paginação, validação de parâmetros e estrutura do schema de resposta.

Usa httpx.AsyncClient com ASGITransport + mocks de asyncpg/Redis
via fixtures de conftest.py — sem banco de dados real.

Estrutura:
  _mk_zscore_row()        — factory: linha de anomalia (modo zscore)
  _mk_prophet_row()       — factory: linha de anomalia (modo prophet)
  TestAnomaliaZscoreMode  — testes exclusivos do mode=zscore
  TestAnomaliaProphetMode — testes exclusivos do mode=prophet
  TestAnomaliaAutoMode    — testes do mode=auto (padrão)
  TestAnomaliaFilters     — filtros uf_sigla / mes_competencia / ano / tipo / sigma
  TestAnomaliaPaginacao   — paginação e metadados PaginacaoMeta
  TestAnomaliaValidacao   — parâmetros inválidos → 422
  TestAnomaliaSchema      — estrutura e tipos da resposta
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio]

# ---------------------------------------------------------------------------
# Factories de dados sintéticos
# ---------------------------------------------------------------------------


def _mk_zscore_row(**overrides) -> dict[str, Any]:
    """Linha de anomalia no formato Z-score (sem campos Prophet)."""
    base: dict[str, Any] = {
        "municipio_cod": "3550308",
        "municipio_nome": "São Paulo",
        "uf_sigla": "SP",
        "mes_competencia": "202301",
        "ano": 2023,
        "mes": 1,
        "total_procedimentos": 50_000,
        "media_historica": 30_000.0,
        "desvio_padrao": 5_000.0,
        "z_score": 4.0,
        "tipo_anomalia": "alta",
        "pct_desvio": 66.67,
        "yhat": None,
        "yhat_lower": None,
        "yhat_upper": None,
        "metodo": "zscore",
        "n_pontos": None,
    }
    base.update(overrides)
    return base


def _mk_prophet_row(**overrides) -> dict[str, Any]:
    """Linha de anomalia no formato Prophet (sem campos de média histórica)."""
    base: dict[str, Any] = {
        "municipio_cod": "2927408",
        "municipio_nome": "Salvador",
        "uf_sigla": "BA",
        "mes_competencia": "202307",
        "ano": 2023,
        "mes": 7,
        "total_procedimentos": 12_000,
        "media_historica": None,
        "desvio_padrao": None,
        "z_score": -3.1,
        "tipo_anomalia": "baixa",
        "pct_desvio": -40.0,
        "yhat": 18_500.0,
        "yhat_lower": 15_000.0,
        "yhat_upper": 22_000.0,
        "metodo": "prophet",
        "n_pontos": 48,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Utilitário de setup de mocks
# ---------------------------------------------------------------------------


def _setup_mock(mock_conn, rows: list[dict], total: int = None):
    """Configura fetchval (count) e fetch (rows) no conn mock."""
    if total is None:
        total = len(rows)
    mock_conn.fetchval = AsyncMock(return_value=total)
    mock_conn.fetch = AsyncMock(return_value=rows)


# ---------------------------------------------------------------------------
# TestAnomaliaZscoreMode
# ---------------------------------------------------------------------------


class TestAnomaliaZscoreMode:
    """Testa o endpoint com method=zscore."""

    async def test_zscore_returns_200(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        resp = await async_client.get("/indicadores/anomalias?method=zscore")
        assert resp.status_code == 200

    async def test_zscore_method_used_field(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        body = (await async_client.get("/indicadores/anomalias?method=zscore")).json()
        assert body["method_used"] == "zscore"

    async def test_zscore_row_has_media_historica(self, async_client, mock_asyncpg_conn):
        row = _mk_zscore_row(media_historica=30_000.0, desvio_padrao=5_000.0)
        _setup_mock(mock_asyncpg_conn, [row])
        body = (await async_client.get("/indicadores/anomalias?method=zscore")).json()
        item = body["data"][0]
        assert item["media_historica"] == 30_000.0
        assert item["desvio_padrao"] == 5_000.0

    async def test_zscore_row_yhat_is_none(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        body = (await async_client.get("/indicadores/anomalias?method=zscore")).json()
        item = body["data"][0]
        assert item["yhat"] is None
        assert item["yhat_lower"] is None
        assert item["yhat_upper"] is None

    async def test_zscore_metodo_field(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        body = (await async_client.get("/indicadores/anomalias?method=zscore")).json()
        assert body["data"][0]["metodo"] == "zscore"

    async def test_zscore_empty_result(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [], total=0)
        resp = await async_client.get("/indicadores/anomalias?method=zscore")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["paginacao"]["total"] == 0

    async def test_zscore_threshold_sigma_field(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [], total=0)
        body = (await async_client.get("/indicadores/anomalias?method=zscore&sigma=2.5")).json()
        assert body["threshold_sigma"] == 2.5

    async def test_zscore_multiple_rows(self, async_client, mock_asyncpg_conn):
        rows = [
            _mk_zscore_row(municipio_cod=f"35000{i:02d}", z_score=float(2 + i))
            for i in range(5)
        ]
        _setup_mock(mock_asyncpg_conn, rows)
        body = (await async_client.get("/indicadores/anomalias?method=zscore")).json()
        assert len(body["data"]) == 5


# ---------------------------------------------------------------------------
# TestAnomaliaProphetMode
# ---------------------------------------------------------------------------


class TestAnomaliaProphetMode:
    """Testa o endpoint com method=prophet."""

    async def test_prophet_returns_200(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_prophet_row()])
        resp = await async_client.get("/indicadores/anomalias?method=prophet")
        assert resp.status_code == 200

    async def test_prophet_method_used_field(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_prophet_row()])
        body = (await async_client.get("/indicadores/anomalias?method=prophet")).json()
        assert body["method_used"] == "prophet"

    async def test_prophet_row_has_yhat_fields(self, async_client, mock_asyncpg_conn):
        row = _mk_prophet_row(yhat=18_500.0, yhat_lower=15_000.0, yhat_upper=22_000.0)
        _setup_mock(mock_asyncpg_conn, [row])
        body = (await async_client.get("/indicadores/anomalias?method=prophet")).json()
        item = body["data"][0]
        assert item["yhat"] == 18_500.0
        assert item["yhat_lower"] == 15_000.0
        assert item["yhat_upper"] == 22_000.0

    async def test_prophet_row_media_historica_is_none(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [_mk_prophet_row()])
        body = (await async_client.get("/indicadores/anomalias?method=prophet")).json()
        item = body["data"][0]
        assert item["media_historica"] is None
        assert item["desvio_padrao"] is None

    async def test_prophet_metodo_field(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_prophet_row()])
        body = (await async_client.get("/indicadores/anomalias?method=prophet")).json()
        assert body["data"][0]["metodo"] == "prophet"

    async def test_prophet_n_pontos_present(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_prophet_row(n_pontos=48)])
        body = (await async_client.get("/indicadores/anomalias?method=prophet")).json()
        assert body["data"][0]["n_pontos"] == 48

    async def test_prophet_empty_result(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [], total=0)
        resp = await async_client.get("/indicadores/anomalias?method=prophet")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []

    async def test_prophet_tipo_baixa(self, async_client, mock_asyncpg_conn):
        row = _mk_prophet_row(tipo_anomalia="baixa", z_score=-3.5, pct_desvio=-45.0)
        _setup_mock(mock_asyncpg_conn, [row])
        body = (await async_client.get(
            "/indicadores/anomalias?method=prophet&tipo=baixa"
        )).json()
        assert body["data"][0]["tipo_anomalia"] == "baixa"


# ---------------------------------------------------------------------------
# TestAnomaliaAutoMode
# ---------------------------------------------------------------------------


class TestAnomaliaAutoMode:
    """Testa o endpoint com method=auto (padrão)."""

    async def test_auto_is_default(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert body["method_used"] == "auto"

    async def test_auto_explicit_returns_200(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        resp = await async_client.get("/indicadores/anomalias?method=auto")
        assert resp.status_code == 200

    async def test_auto_method_used_field(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [])
        body = (await async_client.get("/indicadores/anomalias?method=auto")).json()
        assert body["method_used"] == "auto"

    async def test_auto_mixed_methods_accepted(self, async_client, mock_asyncpg_conn):
        """Auto pode retornar rows com metodo=zscore e metodo=prophet misturados."""
        rows = [
            _mk_zscore_row(municipio_cod="3550308"),
            _mk_prophet_row(municipio_cod="2927408"),
        ]
        _setup_mock(mock_asyncpg_conn, rows, total=2)
        body = (await async_client.get("/indicadores/anomalias?method=auto")).json()
        assert len(body["data"]) == 2
        metodos = {r["metodo"] for r in body["data"]}
        # ambos métodos estão representados no resultado
        assert "zscore" in metodos
        assert "prophet" in metodos

    async def test_auto_empty_result(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [], total=0)
        body = (await async_client.get("/indicadores/anomalias?method=auto")).json()
        assert body["data"] == []
        assert body["paginacao"]["total"] == 0


# ---------------------------------------------------------------------------
# TestAnomaliaFilters
# ---------------------------------------------------------------------------


class TestAnomaliaFilters:
    """Testa os filtros de query do endpoint."""

    async def test_filter_uf_sigla_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get(
            "/indicadores/anomalias?uf_sigla=SP&method=zscore"
        )
        assert resp.status_code == 200

    async def test_filter_uf_sigla_lowercase_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        """UF em minúsculas deve ser aceita (FastAPI valida min_length=2)."""
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get(
            "/indicadores/anomalias?uf_sigla=sp&method=zscore"
        )
        assert resp.status_code == 200

    async def test_filter_mes_competencia_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get(
            "/indicadores/anomalias?mes_competencia=202301&method=zscore"
        )
        assert resp.status_code == 200

    async def test_filter_ano_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get(
            "/indicadores/anomalias?ano=2023&method=zscore"
        )
        assert resp.status_code == 200

    async def test_filter_tipo_alta_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row(tipo_anomalia="alta")])
        resp = await async_client.get(
            "/indicadores/anomalias?tipo=alta&method=zscore"
        )
        assert resp.status_code == 200

    async def test_filter_tipo_baixa_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row(tipo_anomalia="baixa", z_score=-3.2)])
        resp = await async_client.get(
            "/indicadores/anomalias?tipo=baixa&method=zscore"
        )
        assert resp.status_code == 200

    async def test_filter_sigma_custom_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get(
            "/indicadores/anomalias?sigma=3.0&method=zscore"
        )
        assert resp.status_code == 200

    async def test_filter_sigma_reflected_in_threshold(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        body = (await async_client.get(
            "/indicadores/anomalias?sigma=2.5&method=prophet"
        )).json()
        assert body["threshold_sigma"] == 2.5

    async def test_combined_filters_returns_200(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get(
            "/indicadores/anomalias?uf_sigla=RJ&ano=2023&tipo=alta&sigma=2.0&method=zscore"
        )
        assert resp.status_code == 200

    async def test_filter_uf_single_char_returns_422(self, async_client):
        """UF com 1 caractere deve falhar na validação (min_length=2)."""
        resp = await async_client.get("/indicadores/anomalias?uf_sigla=S")
        assert resp.status_code == 422

    async def test_filter_uf_three_chars_returns_422(self, async_client):
        """UF com 3 caracteres deve falhar (max_length=2)."""
        resp = await async_client.get("/indicadores/anomalias?uf_sigla=SPX")
        assert resp.status_code == 422

    async def test_filter_mes_competencia_invalid_format_returns_422(
        self, async_client
    ):
        """mes_competencia deve ser 6 dígitos (padrão AAAAMM)."""
        resp = await async_client.get(
            "/indicadores/anomalias?mes_competencia=2023-01"
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TestAnomaliaPaginacao
# ---------------------------------------------------------------------------


class TestAnomaliaPaginacao:
    """Testa a paginação e os metadados de PaginacaoMeta."""

    async def test_paginacao_meta_present(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [], total=0)
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert "paginacao" in body
        pag = body["paginacao"]
        for key in ("total", "pagina", "por_pagina", "paginas"):
            assert key in pag, f"Chave '{key}' ausente em paginacao"

    async def test_paginacao_total_reflete_mock(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()], total=42)
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert body["paginacao"]["total"] == 42

    async def test_paginacao_paginas_calculada(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [], total=25)
        body = (await async_client.get(
            "/indicadores/anomalias?por_pagina=10"
        )).json()
        assert body["paginacao"]["paginas"] == 3  # ceil(25/10) = 3

    async def test_paginacao_paginas_minimo_um(
        self, async_client, mock_asyncpg_conn
    ):
        """Mesmo com 0 registros, paginas deve ser ≥ 1."""
        _setup_mock(mock_asyncpg_conn, [], total=0)
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert body["paginacao"]["paginas"] >= 1

    async def test_paginacao_pagina_atual_refletida(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [], total=100)
        body = (await async_client.get(
            "/indicadores/anomalias?pagina=3&por_pagina=20"
        )).json()
        assert body["paginacao"]["pagina"] == 3
        assert body["paginacao"]["por_pagina"] == 20

    async def test_pagina_zero_returns_422(self, async_client):
        resp = await async_client.get("/indicadores/anomalias?pagina=0")
        assert resp.status_code == 422

    async def test_por_pagina_zero_returns_422(self, async_client):
        resp = await async_client.get("/indicadores/anomalias?por_pagina=0")
        assert resp.status_code == 422

    async def test_por_pagina_acima_limite_returns_422(self, async_client):
        resp = await async_client.get("/indicadores/anomalias?por_pagina=501")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TestAnomaliaValidacao
# ---------------------------------------------------------------------------


class TestAnomaliaValidacao:
    """Testa validação de parâmetros inválidos (espera 422)."""

    async def test_method_invalido_returns_422(self, async_client):
        resp = await async_client.get(
            "/indicadores/anomalias?method=xgboost"
        )
        assert resp.status_code == 422

    async def test_sigma_abaixo_limite_returns_422(self, async_client):
        """sigma < 1.0 deve ser rejeitado (ge=1.0)."""
        resp = await async_client.get("/indicadores/anomalias?sigma=0.5")
        assert resp.status_code == 422

    async def test_sigma_acima_limite_returns_422(self, async_client):
        """sigma > 4.0 deve ser rejeitado (le=4.0)."""
        resp = await async_client.get("/indicadores/anomalias?sigma=5.0")
        assert resp.status_code == 422

    async def test_sigma_limite_inferior_ok(
        self, async_client, mock_asyncpg_conn
    ):
        """sigma = 1.0 deve ser aceito."""
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get("/indicadores/anomalias?sigma=1.0")
        assert resp.status_code == 200

    async def test_sigma_limite_superior_ok(
        self, async_client, mock_asyncpg_conn
    ):
        """sigma = 4.0 deve ser aceito."""
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get("/indicadores/anomalias?sigma=4.0")
        assert resp.status_code == 200

    async def test_ano_abaixo_limite_returns_422(self, async_client):
        """ano < 2000 deve ser rejeitado."""
        resp = await async_client.get("/indicadores/anomalias?ano=1999")
        assert resp.status_code == 422

    async def test_ano_acima_limite_returns_422(self, async_client):
        """ano > 2030 deve ser rejeitado."""
        resp = await async_client.get("/indicadores/anomalias?ano=2031")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TestAnomaliaSchema
# ---------------------------------------------------------------------------


class TestAnomaliaSchema:
    """Testa a estrutura e tipos dos campos da resposta."""

    async def test_response_top_level_keys(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert set(body.keys()) >= {"data", "paginacao", "threshold_sigma", "method_used"}

    async def test_data_is_list(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert isinstance(body["data"], list)

    async def test_item_required_fields_present(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        body = (await async_client.get("/indicadores/anomalias")).json()
        item = body["data"][0]
        required = {
            "municipio_cod", "uf_sigla", "mes_competencia",
            "ano", "mes", "total_procedimentos",
            "z_score", "tipo_anomalia", "pct_desvio", "metodo",
        }
        for field in required:
            assert field in item, f"Campo obrigatório '{field}' ausente no item"

    async def test_item_optional_fields_present_even_if_none(
        self, async_client, mock_asyncpg_conn
    ):
        """Campos opcionais devem aparecer na resposta (como null se ausentes)."""
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row()])
        body = (await async_client.get("/indicadores/anomalias")).json()
        item = body["data"][0]
        optional = {
            "municipio_nome", "media_historica", "desvio_padrao",
            "yhat", "yhat_lower", "yhat_upper", "n_pontos",
        }
        for field in optional:
            assert field in item, f"Campo opcional '{field}' ausente no item"

    async def test_item_z_score_is_numeric(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [_mk_zscore_row(z_score=3.14)])
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert isinstance(body["data"][0]["z_score"], (int, float))

    async def test_item_tipo_anomalia_values(
        self, async_client, mock_asyncpg_conn
    ):
        rows = [
            _mk_zscore_row(tipo_anomalia="alta"),
            _mk_zscore_row(municipio_cod="3550309", tipo_anomalia="baixa", z_score=-3.0),
        ]
        _setup_mock(mock_asyncpg_conn, rows, total=2)
        body = (await async_client.get("/indicadores/anomalias")).json()
        for item in body["data"]:
            assert item["tipo_anomalia"] in ("alta", "baixa"), (
                f"tipo_anomalia inesperado: {item['tipo_anomalia']!r}"
            )

    async def test_threshold_sigma_is_float(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert isinstance(body["threshold_sigma"], (int, float))

    async def test_method_used_is_string(
        self, async_client, mock_asyncpg_conn
    ):
        _setup_mock(mock_asyncpg_conn, [])
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert isinstance(body["method_used"], str)

    async def test_paginacao_tipos(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [], total=10)
        body = (await async_client.get(
            "/indicadores/anomalias?pagina=1&por_pagina=5"
        )).json()
        pag = body["paginacao"]
        assert isinstance(pag["total"], int)
        assert isinstance(pag["pagina"], int)
        assert isinstance(pag["por_pagina"], int)
        assert isinstance(pag["paginas"], int)

    async def test_prophet_row_yhat_bounds_consistency(
        self, async_client, mock_asyncpg_conn
    ):
        """yhat_lower ≤ yhat ≤ yhat_upper quando presentes."""
        row = _mk_prophet_row(yhat=18_500.0, yhat_lower=15_000.0, yhat_upper=22_000.0)
        _setup_mock(mock_asyncpg_conn, [row])
        body = (await async_client.get("/indicadores/anomalias?method=prophet")).json()
        item = body["data"][0]
        if item["yhat"] is not None:
            assert item["yhat_lower"] <= item["yhat"] <= item["yhat_upper"]

    async def test_content_type_is_json(self, async_client, mock_asyncpg_conn):
        _setup_mock(mock_asyncpg_conn, [])
        resp = await async_client.get("/indicadores/anomalias")
        assert resp.headers["content-type"].startswith("application/json")

    async def test_no_data_without_method_param(
        self, async_client, mock_asyncpg_conn
    ):
        """Sem parâmetro method → modo auto → method_used=auto."""
        _setup_mock(mock_asyncpg_conn, [])
        body = (await async_client.get("/indicadores/anomalias")).json()
        assert body["method_used"] == "auto"
