"""
saude_publica_br — Python SDK para a API pública do SUS

Instalação:
    pip install saude-publica-br

Uso rápido:
    from saude_publica_br import Client

    client = Client(api_key="spbr_...")

    # Produção ambulatorial em SP, Q1 2024
    resp = client.producao.listar(uf="SP", competencia_inicio="2024-01", competencia_fim="2024-03")
    print(f"{resp.meta.total} registros")
    for item in resp.dados:
        print(item.procedimento_nome, item.quantidade_aprovada)

    # Async
    import asyncio
    async def main():
        async with Client(api_key="spbr_...") as c:
            resp = await c.producao.listar_async(uf="RJ")
    asyncio.run(main())
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Union
from urllib.parse import urlencode
import json

try:
    import httpx
except ImportError as e:
    raise ImportError(
        "O SDK requer httpx. Instale com: pip install saude-publica-br[httpx]"
    ) from e

__version__ = "1.0.0"
__all__ = ["Client", "SaudePublicaError", "RateLimitError", "AuthError"]

BASE_URL = "https://api.saudepublica.br"


# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------

class SaudePublicaError(Exception):
    """Erro base do SDK."""
    def __init__(self, message: str, status_code: int = 0, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class RateLimitError(SaudePublicaError):
    """Rate limit atingido. Veja retry_after para saber quando tentar novamente."""
    def __init__(self, retry_after: int = 3600):
        super().__init__(
            f"Rate limit atingido. Tente novamente em {retry_after}s.",
            status_code=429,
        )
        self.retry_after = retry_after


class AuthError(SaudePublicaError):
    """API key inválida ou expirada."""
    def __init__(self, detail: str = "API key inválida ou expirada."):
        super().__init__(detail, status_code=401)


# ---------------------------------------------------------------------------
# Modelos de resposta (dataclasses leves, sem dependência Pydantic)
# ---------------------------------------------------------------------------

@dataclass
class MetaPaginacao:
    total: int
    pagina: int
    por_pagina: int
    paginas: int


@dataclass
class RateLimitInfo:
    tier: str
    usadas_hora: int
    limite_hora: Optional[int] = None


@dataclass
class ProducaoItem:
    competencia: str
    uf: str
    procedimento_codigo: str
    procedimento_nome: str
    quantidade_aprovada: int
    valor_aprovado: float
    estabelecimentos: int
    municipio_codigo: Optional[str] = None


@dataclass
class ProducaoResponse:
    dados: list[ProducaoItem]
    meta: MetaPaginacao
    rate_limit: RateLimitInfo
    fonte: str = "SIA/DataSUS"
    ultima_atualizacao: str = ""


@dataclass
class MortalidadeItem:
    ano: int
    uf: str
    causa_cid10: str
    causa_descricao: str
    capitulo_cid: str
    obitos: int
    municipio_codigo: Optional[str] = None
    taxa_100k: Optional[float] = None
    idade_media: Optional[float] = None
    prop_feminino: Optional[float] = None


@dataclass
class MortalidadeResponse:
    dados: list[MortalidadeItem]
    meta: MetaPaginacao
    rate_limit: RateLimitInfo
    fonte: str = "SIM/DataSUS"
    ultima_atualizacao: str = ""


@dataclass
class DoencaItem:
    ano: int
    semana_epidemiologica: int
    uf: str
    agravo_cid10: str
    agravo_nome: str
    casos: int
    municipio_codigo: Optional[str] = None
    casos_graves: Optional[int] = None
    obitos: Optional[int] = None
    incidencia_100k: Optional[float] = None
    alertas: Optional[list[str]] = None


@dataclass
class DoencaResponse:
    dados: list[DoencaItem]
    meta: MetaPaginacao
    rate_limit: RateLimitInfo
    fonte: str = "SINAN/DataSUS"
    ultima_atualizacao: str = ""


# ---------------------------------------------------------------------------
# HTTP transport com retry automático
# ---------------------------------------------------------------------------

def _parse_rate_limit(data: dict) -> RateLimitInfo:
    rl = data.get("rate_limit", {})
    return RateLimitInfo(
        tier=rl.get("tier", "free"),
        usadas_hora=rl.get("usadas_hora", 0),
        limite_hora=rl.get("limite_hora"),
    )


def _parse_meta(data: dict) -> MetaPaginacao:
    m = data.get("meta", {})
    return MetaPaginacao(
        total=m.get("total", 0),
        pagina=m.get("pagina", 1),
        por_pagina=m.get("por_pagina", 100),
        paginas=m.get("paginas", 1),
    )


class _Transport:
    """HTTP transport síncrono e assíncrono com retry exponencial."""

    MAX_RETRIES = 3
    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self, api_key: str, base_url: str, timeout: float = 30.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    @property
    def _headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "User-Agent": f"saude-publica-br-python/{__version__}",
            "Accept": "application/json",
        }

    def _handle_response(self, resp: httpx.Response) -> dict:
        if resp.status_code == 401:
            raise AuthError(resp.json().get("detail", "API key inválida."))
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 3600))
            raise RateLimitError(retry_after=retry_after)
        if resp.status_code >= 400:
            detail = resp.json().get("detail", resp.text)
            raise SaudePublicaError(str(detail), status_code=resp.status_code, detail=detail)
        return resp.json()

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        """Requisição GET síncrona com retry."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=self.timeout)

        url = self.base_url + path
        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                resp = self._sync_client.get(url, params=params, headers=self._headers)
                if resp.status_code in self.RETRY_STATUSES and attempt < self.MAX_RETRIES - 1:
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        time.sleep(min(retry_after, 60))
                    else:
                        time.sleep(2 ** attempt)
                    continue
                return self._handle_response(resp)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exc = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)

        raise SaudePublicaError(f"Falha após {self.MAX_RETRIES} tentativas: {last_exc}")

    async def get_async(self, path: str, params: Optional[dict] = None) -> dict:
        """Requisição GET assíncrona com retry."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self.timeout)

        url = self.base_url + path
        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                resp = await self._async_client.get(url, params=params, headers=self._headers)
                if resp.status_code in self.RETRY_STATUSES and attempt < self.MAX_RETRIES - 1:
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        await asyncio.sleep(min(retry_after, 60))
                    else:
                        await asyncio.sleep(2 ** attempt)
                    continue
                return self._handle_response(resp)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exc = e
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)

        raise SaudePublicaError(f"Falha após {self.MAX_RETRIES} tentativas: {last_exc}")

    def close(self):
        if self._sync_client:
            self._sync_client.close()

    async def aclose(self):
        if self._async_client:
            await self._async_client.aclose()


# ---------------------------------------------------------------------------
# Sub-clientes por domínio
# ---------------------------------------------------------------------------

class _ProducaoClient:
    def __init__(self, transport: _Transport):
        self._t = transport

    def _clean(self, kwargs: dict) -> dict:
        return {k: v for k, v in kwargs.items() if v is not None}

    def _parse(self, data: dict) -> ProducaoResponse:
        return ProducaoResponse(
            dados=[ProducaoItem(**d) for d in data.get("dados", [])],
            meta=_parse_meta(data),
            rate_limit=_parse_rate_limit(data),
            fonte=data.get("fonte", "SIA/DataSUS"),
            ultima_atualizacao=data.get("ultima_atualizacao", ""),
        )

    def listar(
        self,
        *,
        uf: Optional[str] = None,
        municipio: Optional[str] = None,
        procedimento: Optional[str] = None,
        competencia_inicio: Optional[str] = None,
        competencia_fim: Optional[str] = None,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> ProducaoResponse:
        """Lista produção ambulatorial (síncrono)."""
        data = self._t.get("/v1/producao", self._clean(locals()))
        return self._parse(data)

    async def listar_async(
        self,
        *,
        uf: Optional[str] = None,
        municipio: Optional[str] = None,
        procedimento: Optional[str] = None,
        competencia_inicio: Optional[str] = None,
        competencia_fim: Optional[str] = None,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> ProducaoResponse:
        """Lista produção ambulatorial (assíncrono)."""
        data = await self._t.get_async("/v1/producao", self._clean(locals()))
        return self._parse(data)

    def resumo(
        self, competencia_inicio: str, competencia_fim: str
    ) -> dict:
        """Resumo de produção por UF."""
        return self._t.get(
            "/v1/producao/resumo",
            {"competencia_inicio": competencia_inicio, "competencia_fim": competencia_fim},
        )


class _MortalidadeClient:
    def __init__(self, transport: _Transport):
        self._t = transport

    def _clean(self, kwargs: dict) -> dict:
        return {k: v for k, v in kwargs.items() if v is not None and k != "self"}

    def _parse(self, data: dict) -> MortalidadeResponse:
        return MortalidadeResponse(
            dados=[MortalidadeItem(**d) for d in data.get("dados", [])],
            meta=_parse_meta(data),
            rate_limit=_parse_rate_limit(data),
            fonte=data.get("fonte", "SIM/DataSUS"),
            ultima_atualizacao=data.get("ultima_atualizacao", ""),
        )

    def listar(
        self,
        *,
        uf: Optional[str] = None,
        municipio: Optional[str] = None,
        cid10: Optional[str] = None,
        ano_inicio: Optional[int] = None,
        ano_fim: Optional[int] = None,
        com_taxa: bool = False,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> MortalidadeResponse:
        """Lista mortalidade por causa (síncrono)."""
        params = self._clean(locals())
        if not com_taxa:
            params.pop("com_taxa", None)
        data = self._t.get("/v1/mortalidade", params)
        return self._parse(data)

    async def listar_async(
        self,
        *,
        uf: Optional[str] = None,
        cid10: Optional[str] = None,
        ano_inicio: Optional[int] = None,
        ano_fim: Optional[int] = None,
        com_taxa: bool = False,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> MortalidadeResponse:
        """Lista mortalidade por causa (assíncrono)."""
        params = self._clean(locals())
        data = await self._t.get_async("/v1/mortalidade", params)
        return self._parse(data)

    def causas_principais(self, uf: str, ano: int, top_n: int = 10) -> dict:
        """Top-N causas de morte para UF/ano."""
        return self._t.get("/v1/mortalidade/causas-principais", {"uf": uf, "ano": ano, "top_n": top_n})

    def tendencia(self, uf: str, cid10: str) -> dict:
        """Série histórica anual para causa/UF."""
        return self._t.get("/v1/mortalidade/tendencia", {"uf": uf, "cid10": cid10})


class _DoencasClient:
    def __init__(self, transport: _Transport):
        self._t = transport

    def _clean(self, kwargs: dict) -> dict:
        return {k: v for k, v in kwargs.items() if v is not None and k != "self"}

    def _parse(self, data: dict) -> DoencaResponse:
        return DoencaResponse(
            dados=[DoencaItem(**d) for d in data.get("dados", [])],
            meta=_parse_meta(data),
            rate_limit=_parse_rate_limit(data),
            fonte=data.get("fonte", "SINAN/DataSUS"),
            ultima_atualizacao=data.get("ultima_atualizacao", ""),
        )

    def listar(
        self,
        *,
        uf: Optional[str] = None,
        agravo: Optional[str] = None,
        ano: Optional[int] = None,
        semana_inicio: Optional[int] = None,
        semana_fim: Optional[int] = None,
        apenas_alertas: bool = False,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> DoencaResponse:
        """Lista notificações (síncrono)."""
        params = self._clean(locals())
        data = self._t.get("/v1/doencas", params)
        return self._parse(data)

    def surtos(
        self,
        *,
        uf: Optional[str] = None,
        agravo: Optional[str] = None,
        nivel_minimo: str = "AMARELO",
    ) -> dict:
        """Surtos e alertas epidemiológicos ativos."""
        return self._t.get("/v1/doencas/surtos", self._clean(locals()))

    def agravos(self) -> dict:
        """Lista agravos disponíveis."""
        return self._t.get("/v1/doencas/agravos")

    def serie(self, uf: str, agravo: str, ano: int) -> dict:
        """Série temporal semanal para agravo/UF/ano."""
        return self._t.get("/v1/doencas/serie", {"uf": uf, "agravo": agravo, "ano": ano})


class _CapacidadeClient:
    def __init__(self, transport: _Transport):
        self._t = transport

    def estabelecimentos(
        self,
        *,
        uf: Optional[str] = None,
        municipio: Optional[str] = None,
        tipo: Optional[str] = None,
        gestao: Optional[str] = None,
        apenas_sus: bool = True,
        competencia: Optional[str] = None,
        com_coords: bool = False,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> dict:
        """Lista estabelecimentos de saúde."""
        params = {k: v for k, v in locals().items() if v is not None and k != "self"}
        return self._t.get("/v1/capacidade/estabelecimentos", params)

    def resumo(self, competencia: Optional[str] = None) -> dict:
        """Resumo de capacidade por UF."""
        params = {"competencia": competencia} if competencia else {}
        return self._t.get("/v1/capacidade/resumo", params)

    def leitos_uti(
        self,
        granularidade: str = "uf",
        competencia: Optional[str] = None,
        top_n: int = 27,
    ) -> dict:
        """Ranking de leitos UTI por 100k."""
        params = {k: v for k, v in locals().items() if v is not None and k != "self"}
        return self._t.get("/v1/capacidade/leitos-uti", params)


# ---------------------------------------------------------------------------
# Client principal
# ---------------------------------------------------------------------------

class Client:
    """
    Cliente principal do SDK saude-publica-br.

    Uso síncrono:
        client = Client(api_key="spbr_...")
        resp = client.producao.listar(uf="SP")
        client.close()

    Uso como context manager (síncrono):
        with Client(api_key="spbr_...") as c:
            resp = c.mortalidade.causas_principais("SP", 2023)

    Uso assíncrono:
        async with Client(api_key="spbr_...") as c:
            resp = await c.producao.listar_async(uf="SP")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
    ):
        self._transport = _Transport(api_key=api_key, base_url=base_url, timeout=timeout)
        self.producao = _ProducaoClient(self._transport)
        self.mortalidade = _MortalidadeClient(self._transport)
        self.doencas = _DoencasClient(self._transport)
        self.capacidade = _CapacidadeClient(self._transport)

    def status(self) -> dict:
        """Health check público da API (sem autenticação necessária)."""
        return self._transport.get("/v1/status")

    def me(self) -> dict:
        """Informações da API key autenticada."""
        return self._transport.get("/v1/me")

    def sistemas(self) -> dict:
        """Catálogo dos sistemas de informação disponíveis."""
        return self._transport.get("/v1/sistemas")

    def close(self):
        """Fecha as conexões HTTP síncronas."""
        self._transport.close()

    async def aclose(self):
        """Fecha as conexões HTTP assíncronas."""
        await self._transport.aclose()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(self, *args):
        await self.aclose()
