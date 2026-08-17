"""
api_client.py — HTTP wrapper para a saude-publica-br FastAPI
Usa httpx (sync) + @st.cache_data para cache no Streamlit.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
import streamlit as st

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Exceção personalizada
# ──────────────────────────────────────────────────────────────────────────────

class APIError(Exception):
    """Erro retornado pela API (status != 2xx) ou falha de conexão."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


# ──────────────────────────────────────────────────────────────────────────────
# Cliente principal
# ──────────────────────────────────────────────────────────────────────────────

class APIClient:
    """
    Wrapper sobre httpx para a FastAPI saude-publica-br.

    Uso:
        client = APIClient("http://localhost:8000")
        data   = client.health()
    """

    DEFAULT_TIMEOUT = 30.0

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.DEFAULT_TIMEOUT,
            headers={"Accept": "application/json"},
        )

    # ── Baixo nível ──────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> Any:
        """GET com tratamento de erros uniforme."""
        try:
            resp = self._client.get(path, params=params)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise APIError(
                f"Não foi possível conectar à API ({self.base_url}): {exc}"
            )

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise APIError(
                f"API retornou {resp.status_code}: {detail}",
                status_code=resp.status_code,
            )

        return resp.json()

    def close(self):
        self._client.close()

    # ──────────────────────────────────────────────────────────────────────────
    # Health
    # ──────────────────────────────────────────────────────────────────────────

    def health(self) -> dict:
        return self._get("/health")

    def info(self) -> dict:
        return self._get("/info")

    # ──────────────────────────────────────────────────────────────────────────
    # Produção Ambulatorial
    # ──────────────────────────────────────────────────────────────────────────

    def producao(
        self,
        uf_sigla: str | None = None,
        municipio_cod: str | None = None,
        ano_inicio: int | None = None,
        ano_fim: int | None = None,
        mes_competencia: str | None = None,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> dict:
        params = _build_params(
            uf_sigla=uf_sigla,
            municipio_cod=municipio_cod,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            mes_competencia=mes_competencia,
            pagina=pagina,
            por_pagina=por_pagina,
        )
        return self._get("/producao", params=params)

    def producao_serie(
        self,
        municipio_cod: str,
        ano_inicio: int | None = None,
        ano_fim: int | None = None,
    ) -> dict:
        params = _build_params(ano_inicio=ano_inicio, ano_fim=ano_fim)
        return self._get(f"/producao/series/{municipio_cod}", params=params)

    def producao_mapa(
        self,
        uf_sigla: str,
        ano: int | None = None,
        mes: int | None = None,
        indicador: str = "taxa_proc_10k",
    ) -> dict:
        params = _build_params(ano=ano, mes=mes, indicador=indicador)
        return self._get(f"/producao/mapa/{uf_sigla}", params=params)

    # ──────────────────────────────────────────────────────────────────────────
    # Indicadores
    # ──────────────────────────────────────────────────────────────────────────

    def indicadores_municipio(self, municipio_cod: str, ano: int | None = None) -> dict:
        params = _build_params(ano=ano)
        return self._get(f"/indicadores/{municipio_cod}", params=params)

    def anomalias(
        self,
        sigma: float = 2.0,
        uf_sigla: str | None = None,
        ano: int | None = None,
        tipo: str | None = None,
        pagina: int = 1,
        por_pagina: int = 200,
    ) -> dict:
        params = _build_params(
            sigma=sigma,
            uf_sigla=uf_sigla,
            ano=ano,
            tipo=tipo,
            pagina=pagina,
            por_pagina=por_pagina,
        )
        return self._get("/indicadores/anomalias", params=params)

    # ──────────────────────────────────────────────────────────────────────────
    # Epidemiologia
    # ──────────────────────────────────────────────────────────────────────────

    def epi_cid10(
        self,
        uf_sigla: str | None = None,
        ano: int | None = None,
        top_n: int | None = 10,
        pagina: int = 1,
        por_pagina: int = 50,
    ) -> dict:
        params = _build_params(ano=ano, top_n=top_n, pagina=pagina, por_pagina=por_pagina)
        if uf_sigla:
            return self._get(f"/epidemiologia/cid10/{uf_sigla}", params=params)
        return self._get("/epidemiologia/cid10", params=params)

    # ──────────────────────────────────────────────────────────────────────────
    # Ranking
    # ──────────────────────────────────────────────────────────────────────────

    def ranking_uf(
        self,
        uf_sigla: str,
        ano: int | None = None,
        pagina: int = 1,
        por_pagina: int = 500,
    ) -> dict:
        params = _build_params(ano=ano, pagina=pagina, por_pagina=por_pagina)
        return self._get(f"/ranking/{uf_sigla}", params=params)

    def ranking_nacional(
        self,
        ano: int | None = None,
        top: int = 100,
        ordem: str = "melhor",
    ) -> dict:
        params = _build_params(ano=ano, top=top, ordem=ordem)
        return self._get("/ranking/nacional", params=params)


# ──────────────────────────────────────────────────────────────────────────────
# Helper interno
# ──────────────────────────────────────────────────────────────────────────────

def _build_params(**kwargs) -> dict:
    """Remove valores None para não poluir a query string."""
    return {k: v for k, v in kwargs.items() if v is not None}


# ──────────────────────────────────────────────────────────────────────────────
# Funções cacheadas — usadas pelas páginas Streamlit
# TTL alinhado com os TTLs do Redis na API
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_health(api_url: str) -> dict:
    return APIClient(api_url).health()


@st.cache_data(ttl=3_600, show_spinner=False)
def get_producao(
    api_url: str,
    uf_sigla: str | None = None,
    municipio_cod: str | None = None,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    pagina: int = 1,
    por_pagina: int = 200,
) -> dict:
    return APIClient(api_url).producao(
        uf_sigla=uf_sigla,
        municipio_cod=municipio_cod,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@st.cache_data(ttl=3_600, show_spinner=False)
def get_producao_serie(
    api_url: str,
    municipio_cod: str,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> dict:
    return APIClient(api_url).producao_serie(
        municipio_cod,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
    )


@st.cache_data(ttl=21_600, show_spinner=False)
def get_producao_mapa(
    api_url: str,
    uf_sigla: str,
    ano: int | None = None,
    mes: int | None = None,
    indicador: str = "taxa_proc_10k",
) -> dict:
    return APIClient(api_url).producao_mapa(uf_sigla, ano=ano, mes=mes, indicador=indicador)


@st.cache_data(ttl=3_600, show_spinner=False)
def get_indicadores_municipio(
    api_url: str,
    municipio_cod: str,
    ano: int | None = None,
) -> dict:
    return APIClient(api_url).indicadores_municipio(municipio_cod, ano=ano)


@st.cache_data(ttl=21_600, show_spinner=False)
def get_anomalias(
    api_url: str,
    sigma: float = 2.0,
    uf_sigla: str | None = None,
    ano: int | None = None,
    tipo: str | None = None,
    pagina: int = 1,
    por_pagina: int = 200,
) -> dict:
    return APIClient(api_url).anomalias(
        sigma=sigma,
        uf_sigla=uf_sigla,
        ano=ano,
        tipo=tipo,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@st.cache_data(ttl=86_400, show_spinner=False)
def get_epi_cid10(
    api_url: str,
    uf_sigla: str | None = None,
    ano: int | None = None,
    top_n: int = 15,
) -> dict:
    return APIClient(api_url).epi_cid10(uf_sigla=uf_sigla, ano=ano, top_n=top_n)


@st.cache_data(ttl=43_200, show_spinner=False)
def get_ranking_uf(
    api_url: str,
    uf_sigla: str,
    ano: int | None = None,
    por_pagina: int = 500,
) -> dict:
    return APIClient(api_url).ranking_uf(uf_sigla, ano=ano, por_pagina=por_pagina)


@st.cache_data(ttl=43_200, show_spinner=False)
def get_ranking_nacional(
    api_url: str,
    ano: int | None = None,
    top: int = 100,
    ordem: str = "melhor",
) -> dict:
    return APIClient(api_url).ranking_nacional(ano=ano, top=top, ordem=ordem)
