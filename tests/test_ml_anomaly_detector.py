"""
Testes unitários — ml/anomaly_detector.py
==========================================
Cobrem:
  - zscore_fallback: detecção básica, limites customizados, série vazia
  - ProphetAnomalyDetector.detect: fallback automático, resultado completo
  - detect_anomalies: wrapper AnomalyResult, metodo field, n_pontos
  - Auto-fallback para séries curtas (< min_periods)
  - Robustez: série constante, valores nulos, variância zero

Marcadores: @pytest.mark.unit (roda sem DB, sem Prophet instalado quando
            relevant tests são skippados)
"""
from __future__ import annotations

import math
import warnings
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _make_series(
    n: int = 36,
    start: str = "2021-01",
    mean: float = 1000.0,
    std: float = 100.0,
    seed: int = 42,
    spike_at: Optional[int] = None,
    spike_mult: float = 4.0,
) -> pd.DataFrame:
    """Cria DataFrame de série temporal sintética com colunas ds/y."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start, periods=n, freq="MS")
    values = rng.normal(mean, std, size=n).clip(0)
    if spike_at is not None:
        values[spike_at] = mean + spike_mult * std
    return pd.DataFrame({"ds": dates, "y": values})


def _make_short_series(n: int = 12) -> pd.DataFrame:
    return _make_series(n=n)


# ---------------------------------------------------------------------------
# zscore_fallback
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestZscoreFallback:
    def test_importa(self):
        from ml.anomaly_detector import zscore_fallback  # noqa: F401

    def test_retorna_dataframe(self):
        from ml.anomaly_detector import zscore_fallback
        df = _make_series(n=24)
        result = zscore_fallback(df)
        assert isinstance(result, pd.DataFrame)

    def test_colunas_obrigatorias(self):
        from ml.anomaly_detector import zscore_fallback
        df = _make_series(n=24)
        result = zscore_fallback(df)
        required = {"ds", "y", "yhat", "yhat_lower", "yhat_upper",
                    "z_score", "tipo_anomalia", "pct_desvio", "metodo", "is_anomaly"}
        assert required.issubset(result.columns), f"Faltam colunas: {required - set(result.columns)}"

    def test_metodo_zscore(self):
        from ml.anomaly_detector import zscore_fallback
        df = _make_series(n=24)
        result = zscore_fallback(df)
        assert (result["metodo"] == "zscore").all()

    def test_yhat_igual_a_media(self):
        from ml.anomaly_detector import zscore_fallback
        df = _make_series(n=24, std=0.0)  # série constante
        result = zscore_fallback(df)
        # yhat = mean(y) para todos os pontos
        assert result["yhat"].nunique() == 1

    def test_spike_detectado(self):
        from ml.anomaly_detector import zscore_fallback
        df = _make_series(n=36, spike_at=20, spike_mult=5.0)
        result = zscore_fallback(df, sigma=2.5)
        anomalias = result[result["is_anomaly"]]
        assert len(anomalias) >= 1
        assert anomalias.iloc[0]["tipo_anomalia"] == "alta"

    def test_sigma_customizado(self):
        from ml.anomaly_detector import zscore_fallback
        df = _make_series(n=36)
        r_permissivo = zscore_fallback(df, sigma=1.0)
        r_restrito = zscore_fallback(df, sigma=3.5)
        # sigma menor → mais anomalias ou igual; nunca menos
        assert r_permissivo["is_anomaly"].sum() >= r_restrito["is_anomaly"].sum()

    def test_serie_vazia_retorna_vazio(self):
        from ml.anomaly_detector import zscore_fallback
        df = pd.DataFrame({"ds": pd.Series([], dtype="datetime64[ns]"),
                           "y": pd.Series([], dtype=float)})
        result = zscore_fallback(df)
        assert len(result) == 0

    def test_serie_tamanho_um(self):
        from ml.anomaly_detector import zscore_fallback
        df = pd.DataFrame({"ds": [pd.Timestamp("2024-01-01")], "y": [500.0]})
        result = zscore_fallback(df)
        assert len(result) == 1
        # Sem desvio padrão calculável: nenhum ponto deve ser anomalia
        assert result["is_anomaly"].sum() == 0

    def test_variancia_zero_sem_anomalias(self):
        from ml.anomaly_detector import zscore_fallback
        df = _make_series(n=12, std=0.0)  # todos iguais
        result = zscore_fallback(df)
        assert result["is_anomaly"].sum() == 0

    def test_pct_desvio_positivo_para_alta(self):
        from ml.anomaly_detector import zscore_fallback
        df = _make_series(n=36, spike_at=10, spike_mult=5.0)
        result = zscore_fallback(df, sigma=2.0)
        altas = result[result["tipo_anomalia"] == "alta"]
        assert (altas["pct_desvio"] > 0).all()

    def test_pct_desvio_negativo_para_baixa(self):
        from ml.anomaly_detector import zscore_fallback
        # Cria uma queda brusca
        df = _make_series(n=36, mean=1000.0, std=50.0, seed=7)
        df.loc[15, "y"] = 100.0  # muito abaixo da média
        result = zscore_fallback(df, sigma=2.0)
        baixas = result[result["tipo_anomalia"] == "baixa"]
        if len(baixas) > 0:
            assert (baixas["pct_desvio"] < 0).all()


# ---------------------------------------------------------------------------
# ProphetAnomalyDetector — com fallback automático
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestProphetAnomalyDetectorFallback:
    """Testa o comportamento de fallback quando n_pontos < min_periods."""

    def test_detect_serie_curta_usa_zscore(self):
        from ml.anomaly_detector import ProphetAnomalyDetector
        detector = ProphetAnomalyDetector(min_periods=24)
        df = _make_short_series(n=12)
        result = detector.detect(df)
        # Deve retornar DataFrame com metodo='zscore'
        assert isinstance(result, pd.DataFrame)
        assert (result["metodo"] == "zscore").all()

    def test_detect_serie_curta_colunas_completas(self):
        from ml.anomaly_detector import ProphetAnomalyDetector
        detector = ProphetAnomalyDetector(min_periods=24)
        df = _make_short_series(n=10)
        result = detector.detect(df)
        required = {"ds", "y", "yhat", "yhat_lower", "yhat_upper",
                    "z_score", "is_anomaly", "metodo"}
        assert required.issubset(result.columns)


# ---------------------------------------------------------------------------
# ProphetAnomalyDetector — com Prophet real (skip se não instalado)
# ---------------------------------------------------------------------------

prophet_available = False
try:
    import prophet  # noqa: F401
    prophet_available = True
except ImportError:
    pass

requires_prophet = pytest.mark.skipif(
    not prophet_available,
    reason="prophet não instalado (extras [ml] necessários)",
)


@pytest.mark.unit
@requires_prophet
class TestProphetAnomalyDetectorFull:
    def test_fit_predict_basico(self):
        from ml.anomaly_detector import ProphetAnomalyDetector
        detector = ProphetAnomalyDetector(min_periods=24)
        df = _make_series(n=36)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            forecast = detector.fit(df).predict()
        assert isinstance(forecast, pd.DataFrame)
        assert "yhat" in forecast.columns
        assert len(forecast) == len(df)

    def test_detect_serie_longa_usa_prophet(self):
        from ml.anomaly_detector import ProphetAnomalyDetector
        detector = ProphetAnomalyDetector(min_periods=24)
        df = _make_series(n=36)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = detector.detect(df)
        assert isinstance(result, pd.DataFrame)
        assert (result["metodo"] == "prophet").all()

    def test_detect_colunas_esperadas(self):
        from ml.anomaly_detector import ProphetAnomalyDetector
        detector = ProphetAnomalyDetector(min_periods=24)
        df = _make_series(n=36)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = detector.detect(df)
        required = {
            "ds", "y", "yhat", "yhat_lower", "yhat_upper",
            "z_score", "tipo_anomalia", "pct_desvio", "is_anomaly", "metodo",
        }
        assert required.issubset(result.columns)

    def test_spike_detectado_prophet(self):
        from ml.anomaly_detector import ProphetAnomalyDetector
        detector = ProphetAnomalyDetector(min_periods=24, sigma_fallback=2.0)
        df = _make_series(n=48, spike_at=35, spike_mult=6.0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = detector.detect(df)
        anomalias = result[result["is_anomaly"]]
        # O spike deve ser detectado
        assert len(anomalias) >= 1

    def test_is_anomaly_bool(self):
        from ml.anomaly_detector import ProphetAnomalyDetector
        detector = ProphetAnomalyDetector(min_periods=24)
        df = _make_series(n=36)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = detector.detect(df)
        assert result["is_anomaly"].dtype == bool

    def test_zscore_bounds_prophet(self):
        from ml.anomaly_detector import ProphetAnomalyDetector
        detector = ProphetAnomalyDetector(min_periods=24)
        df = _make_series(n=36)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = detector.detect(df)
        # yhat_lower <= yhat <= yhat_upper para cada ponto
        assert (result["yhat_lower"] <= result["yhat"]).all()
        assert (result["yhat"] <= result["yhat_upper"]).all()


# ---------------------------------------------------------------------------
# detect_anomalies (wrapper AnomalyResult)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDetectAnomalies:
    def test_importa(self):
        from ml.anomaly_detector import detect_anomalies  # noqa: F401

    def test_retorna_anomaly_result(self):
        from ml.anomaly_detector import AnomalyResult, detect_anomalies
        df = _make_short_series(n=12)
        result = detect_anomalies(
            df=df,
            municipio_cod="355030",
            uf_sigla="SP",
            sigma=2.0,
            min_periods=24,
            future_periods=0,
        )
        assert isinstance(result, AnomalyResult)

    def test_success_serie_curta(self):
        from ml.anomaly_detector import detect_anomalies
        df = _make_short_series(n=12)
        result = detect_anomalies(
            df=df, municipio_cod="355030", uf_sigla="SP",
            sigma=2.0, min_periods=24, future_periods=0,
        )
        assert result.success is True
        assert result.metodo == "zscore"
        assert result.n_pontos == 12

    def test_municipio_cod_preservado(self):
        from ml.anomaly_detector import detect_anomalies
        df = _make_short_series(n=12)
        result = detect_anomalies(
            df=df, municipio_cod="999999", uf_sigla="RJ",
            sigma=2.0, min_periods=24, future_periods=0,
        )
        assert result.municipio_cod == "999999"
        assert result.uf_sigla == "RJ"

    def test_erro_df_none(self):
        from ml.anomaly_detector import detect_anomalies
        result = detect_anomalies(
            df=None, municipio_cod="123456", uf_sigla="MG",  # type: ignore[arg-type]
            sigma=2.0, min_periods=24, future_periods=0,
        )
        assert result.success is False
        assert result.erro is not None

    def test_erro_df_sem_colunas(self):
        from ml.anomaly_detector import detect_anomalies
        df = pd.DataFrame({"x": [1, 2, 3]})  # colunas erradas
        result = detect_anomalies(
            df=df, municipio_cod="123456", uf_sigla="MG",
            sigma=2.0, min_periods=24, future_periods=0,
        )
        assert result.success is False

    def test_anomalias_dataframe_presente(self):
        from ml.anomaly_detector import detect_anomalies
        df = _make_short_series(n=18)
        result = detect_anomalies(
            df=df, municipio_cod="355030", uf_sigla="SP",
            sigma=2.0, min_periods=24, future_periods=0,
        )
        assert isinstance(result.anomalies, pd.DataFrame)

    def test_forecast_dataframe_presente(self):
        from ml.anomaly_detector import detect_anomalies
        df = _make_short_series(n=18)
        result = detect_anomalies(
            df=df, municipio_cod="355030", uf_sigla="SP",
            sigma=2.0, min_periods=24, future_periods=0,
        )
        assert isinstance(result.forecast, pd.DataFrame)
        assert len(result.forecast) == len(df)

    def test_n_anomalias_coerente(self):
        from ml.anomaly_detector import detect_anomalies
        df = _make_short_series(n=18)
        result = detect_anomalies(
            df=df, municipio_cod="355030", uf_sigla="SP",
            sigma=2.0, min_periods=24, future_periods=0,
        )
        assert result.n_anomalias == len(result.anomalies)

    @requires_prophet
    def test_metodo_prophet_serie_longa(self):
        from ml.anomaly_detector import detect_anomalies
        df = _make_series(n=36)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = detect_anomalies(
                df=df, municipio_cod="355030", uf_sigla="SP",
                sigma=2.0, min_periods=24, future_periods=0,
            )
        assert result.success is True
        assert result.metodo == "prophet"
        assert result.n_pontos == 36


# ---------------------------------------------------------------------------
# AnomalyResult dataclass
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAnomalyResult:
    def test_success_sem_erro(self):
        from ml.anomaly_detector import AnomalyResult
        r = AnomalyResult(
            municipio_cod="123", uf_sigla="SP", metodo="zscore",
            n_pontos=12, n_anomalias=0,
            anomalies=pd.DataFrame(), forecast=pd.DataFrame(),
            erro=None,
        )
        assert r.success is True

    def test_success_com_erro(self):
        from ml.anomaly_detector import AnomalyResult
        r = AnomalyResult(
            municipio_cod="123", uf_sigla="SP", metodo="zscore",
            n_pontos=0, n_anomalias=0,
            anomalies=pd.DataFrame(), forecast=pd.DataFrame(),
            erro="Série inválida",
        )
        assert r.success is False
