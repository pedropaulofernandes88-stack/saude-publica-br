"""
conftest.py — Fixtures compartilhadas para toda a suíte de testes.

Fornece:
  - DataFrames sintéticos válidos para cada mart (fixtures GE)
  - Mock de asyncpg Pool/Connection para testes de API
  - TestClient assíncrono (httpx + ASGITransport) para testes de endpoint
  - Mock de Redis para testes de cache
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _mk_df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Fixtures: DataFrames sintéticos válidos por mart
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def df_producao_amb_valid() -> pd.DataFrame:
    """300 rows cobrindo 3 UFs × 5 anos × 12 meses (parcial) — bem acima do min=1000 não,
    mas geramos o mínimo exigido (>1000) com 1001 linhas."""
    import numpy as np

    rng = np.random.default_rng(42)
    n = 1050
    ufs = ["SP", "RJ", "MG", "BA", "PR"]
    anos = [2020, 2021, 2022, 2023, 2024]
    rows = []
    for i in range(n):
        ano = anos[i % len(anos)]
        mes = (i % 12) + 1
        rows.append({
            "municipio_cod": f"{rng.integers(100000, 9999999):07d}",
            "municipio_nome": f"Município {i}",
            "uf_sigla": ufs[i % len(ufs)],
            "ano": ano,
            "mes": mes,
            "mes_competencia": f"{ano}{mes:02d}",
            "total_procedimentos": int(rng.integers(100, 50000)),
            "total_aprovados": int(rng.integers(50, 40000)),
            "taxa_proc_10k": round(float(rng.uniform(0.1, 500.0)), 2),
            "pct_aprovacao": round(float(rng.uniform(60.0, 100.0)), 2),
        })
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def df_acesso_cobertura_valid() -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(7)
    n = 600
    ufs = ["SP", "RJ", "MG", "BA", "RS"]
    anos = [2020, 2021, 2022, 2023, 2024]
    quartis = ["Q1", "Q2-Q3", "Q4"]
    rows = []
    for i in range(n):
        rows.append({
            "municipio_cod": f"{rng.integers(100000, 9999999):07d}",
            "uf_sigla": ufs[i % len(ufs)],
            "ano": anos[i % len(anos)],
            "populacao": int(rng.integers(1000, 5_000_000)),
            "taxa_cobertura": round(float(rng.uniform(0.0, 200.0)), 4),
            "indice_acesso": round(float(rng.uniform(0.0, 1.0)), 4),
            "quartil_acesso": quartis[i % len(quartis)],
            "flag_baixa_cobertura": int(rng.integers(0, 2)),  # 0 ou 1
        })
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def df_epi_cid10_valid() -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(13)
    capitulos = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
                 "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI"]
    descricoes = {c: f"Capítulo {c} CID-10" for c in capitulos}
    ufs = ["SP", "RJ", "MG"]
    anos = [2020, 2021, 2022, 2023, 2024]
    n = 200
    rows = []
    for i in range(n):
        cap = capitulos[i % len(capitulos)]
        rows.append({
            "uf_sigla": ufs[i % len(ufs)],
            "ano": anos[i % len(anos)],
            "capitulo_cid10": cap,
            "descricao_capitulo": descricoes[cap],
            "total_procedimentos": int(rng.integers(0, 100_000)),
            "pct_atend_uf": round(float(rng.uniform(0.0, 100.0)), 4),
            "rank_capitulo_uf": (i % 21) + 1,
            # variacao_anual_pct pode ser NULL no primeiro ano
            "variacao_anual_pct": None if anos[i % len(anos)] == 2020 else round(float(rng.uniform(-50.0, 200.0)), 2),
        })
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def df_mix_complexidade_valid() -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(99)
    niveis = ["Baixa", "Média", "Alta"]
    ufs = ["SP", "RJ", "MG", "BA", "PR"]
    anos = [2020, 2021, 2022, 2023, 2024]
    n = 600
    rows = []
    for i in range(n):
        ab = round(float(rng.uniform(10.0, 80.0)), 2)
        mc = round(float(rng.uniform(5.0, 60.0)), 2)
        # ac fechado para somar ~100
        ac = round(max(0.0, 100.0 - ab - mc), 2)
        rows.append({
            "municipio_cod": f"{rng.integers(100000, 9999999):07d}",
            "uf_sigla": ufs[i % len(ufs)],
            "ano": anos[i % len(anos)],
            "total_procedimentos": int(rng.integers(100, 200_000)),
            "pct_ab": ab,
            "pct_mc": mc,
            "pct_ac": ac,
            "indice_complexidade": round(float(rng.uniform(1.0, 3.0)), 4),
            "nivel_complexidade": niveis[i % len(niveis)],
        })
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def df_ranking_municipios_valid() -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(55)
    categorias = ["Excelente", "Bom", "Regular", "Crítico"]
    ufs = ["SP", "RJ", "MG", "BA", "RS"]
    anos = [2020, 2021, 2022, 2023, 2024]
    n = 600
    rows = []
    for i in range(n):
        rows.append({
            "municipio_cod": f"{rng.integers(100000, 9999999):07d}",
            "municipio_nome": f"Município {i}",
            "uf_sigla": ufs[i % len(ufs)],
            "ano": anos[i % len(anos)],
            "total_procedimentos": int(rng.integers(0, 500_000)),
            "total_aprovados": int(rng.integers(0, 400_000)),
            "taxa_proc_10k": round(float(rng.uniform(0.0, 1000.0)), 2),
            "pct_aprovacao": round(float(rng.uniform(0.0, 100.0)), 2),
            "ranking_estadual": (i % 300) + 1,
            "ranking_nacional": (i % 5000) + 1,
            "percentil_estadual": round(float(rng.uniform(0.0, 100.0)), 2),
            "percentil_nacional": round(float(rng.uniform(0.0, 100.0)), 2),
            "score_acesso": round(float(rng.uniform(0.0, 1.0)), 4),
            "score_producao": round(float(rng.uniform(0.0, 1.0)), 4),
            "score_geral": round(float(rng.uniform(0.0, 1.0)), 4),
            "categoria": categorias[i % len(categorias)],
        })
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def df_sazonalidade_valid() -> pd.DataFrame:
    import numpy as np

    rng = np.random.default_rng(77)
    classificacoes = ["Baixa", "Normal", "Alta", "Muito Alta"]
    ufs = ["SP", "RJ", "MG", "BA", "PR", "RS", "SC", "GO", "DF", "CE",
           "PE", "AM", "PA", "MA", "PB", "RN", "AL", "SE", "PI", "AC",
           "AP", "RO", "RR", "TO", "MT", "MS", "ES"]
    n = 350  # > 300 (12 meses × ≥25 UFs)
    rows = []
    for i in range(n):
        inf = round(float(rng.uniform(0.0, 500.0)), 2)
        sup = round(inf + float(rng.uniform(0.0, 200.0)), 2)
        rows.append({
            "uf_sigla": ufs[i % len(ufs)],
            "mes_num": (i % 12) + 1,
            "mes_nome": ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"][i % 12],
            "media_historica": round(float(rng.uniform(0.0, 1000.0)), 2),
            "desvio_padrao": round(float(rng.uniform(0.0, 300.0)), 2),
            "limite_inferior": inf,
            "limite_superior": sup,
            "indice_sazonalidade": round(float(rng.uniform(0.01, 2.5)), 4),
            "anos_historico": int(rng.integers(3, 10)),
            "classificacao_sazo": classificacoes[i % len(classificacoes)],
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Fixtures: asyncpg mock (para testes de API)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_asyncpg_conn():
    """Retorna um mock de asyncpg.Connection com métodos comuns mockados."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value="OK")
    return conn


@pytest.fixture
def mock_asyncpg_pool(mock_asyncpg_conn):
    """Pool mock que devolve o conn mock via acquire() como context manager."""
    pool = AsyncMock()
    # pool.acquire() é usado como async context manager
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_asyncpg_conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_redis():
    """Mock de redis.asyncio.Redis com get/set/delete mockados."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)   # cache miss por padrão
    r.set = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=1)
    r.ping = AsyncMock(return_value=True)
    return r


# ---------------------------------------------------------------------------
# Fixture: TestClient assíncrono via httpx
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_client(mock_asyncpg_conn, mock_asyncpg_pool, mock_redis):
    """
    Cliente de teste assíncrono que monta a aplicação FastAPI com
    pool e Redis mockados, sem precisar de banco real.
    """
    import httpx
    from httpx import ASGITransport

    # Importa a app e o módulo de database/cache
    from api.main import app
    import api.database as db_module

    # Injeta o pool mock
    db_module._pool = mock_asyncpg_pool

    # Override da dependency get_db — yield direto da conn mock,
    # evitando chamar acquire() (que é AsyncMock e retorna coroutine sem __aenter__)
    from api.database import get_db

    async def override_get_db():
        yield mock_asyncpg_conn

    app.dependency_overrides[get_db] = override_get_db

    # Mock do Redis (se existir módulo de cache)
    try:
        import api.cache as cache_module
        cache_module._redis = mock_redis
    except (ImportError, AttributeError):
        pass

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()
    db_module._pool = None


# ---------------------------------------------------------------------------
# Fixture: GE runner helper
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def run_ge_suite():
    """
    Helper de sessão para executar um build_suite e validar um DataFrame.

    Uso:
        result = run_ge_suite(build_suite_fn, df)
        assert result.success
    """
    def _run(build_suite_fn, df: pd.DataFrame):
        suite, batch_def = build_suite_fn(df)
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})
     