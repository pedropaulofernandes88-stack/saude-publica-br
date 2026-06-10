"""
ml/anomaly_detector.py
======================
Detecção de anomalias em séries temporais de produção ambulatorial do SUS.

Estratégia dual:
  1. **Prophet** (padrão) — treina modelo bayesiano com sazonalidade anual,
     captura tendências e fornece intervalos de confiança calibrados.
     Requer ao menos `min_periods` pontos históricos (padrão: 24 meses).
  2. **Z-score** (fallback) — estatística clássica para séries curtas
     (< min_periods). Usa média e desvio padrão do histórico disponível.

Ambas as funções retornam um DataFrame padronizado com colunas:
  ds, y, yhat, yhat_lower, yhat_upper, z_score,
  tipo_anomalia, pct_desvio, metodo, is_anomaly

Dependências (grupo [ml] no pyproject.toml):
  prophet>=1.1.5  |  scikit-learn>=1.4.0  |  statsmodels>=0.14.0
"""
from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    pass  # prophet importado sob demanda para não quebrar env sem ml extras

logger = logging.getLogger("saude-publica-br.ml")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MIN_PERIODS_PROPHET = 24       # 2 anos mensais mínimos para Prophet
INTERVAL_WIDTH_DEFAULT = 0.95  # 95% PI → ~2σ equivalente para dados normais
SIGMA_DEFAULT = 2.0            # Limiar padrão de desvios para anomalia
CHANGEPOINT_PRIOR = 0.05       # Regularização de tendência (menos = mais suave)
FOURIER_ORDER_YEARLY = 10      # Flexibilidade da sazonalidade anual


# ---------------------------------------------------------------------------
# Resultado padronizado
# ---------------------------------------------------------------------------

@dataclass
class AnomalyResult:
    """
    Resultado da detecção de anomalias para uma única série temporal.

    Attributes:
        municipio_cod: Código IBGE do município.
        uf_sigla: Sigla da UF.
        metodo: 'prophet' ou 'zscore'.
        n_pontos: Número de pontos na série histórica.
        n_anomalias: Número de anomalias detectadas.
        anomalies: DataFrame com as anomalias (subset de `forecast`).
        forecast: DataFrame completo com previsões e flags.
        erro: Mensagem de erro se a detecção falhou, None caso contrário.
    """
    municipio_cod: str
    uf_sigla: str
    metodo: str
    n_pontos: int
    n_anomalias: int
    anomalies: pd.DataFrame
    forecast: pd.DataFrame
    erro: str | None = None

    @property
    def success(self) -> bool:
        return self.erro is None


# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------

def _validate_series(df: pd.DataFrame, min_rows: int = 2) -> None:
    """Valida que o DataFrame tem as colunas ds e y e linhas suficientes."""
    required = {"ds", "y"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame deve conter colunas {required}. Faltando: {missing}")
    if len(df) < min_rows:
        raise ValueError(
            f"Série temporal muito curta: {len(df)} pontos (mínimo: {min_rows})."
        )


def _prepare_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza um DataFrame de série temporal:
      - Garante ds como datetime64[ns] e y como float64.
      - Remove NaN em y.
      - Ordena por ds.
      - Remove duplicatas (mantém a última ocorrência).
    """
    df = df.copy()
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = pd.to_numeric(df["y"], errors="coerce").astype(float)
    df = df.dropna(subset=["y"]).sort_values("ds").drop_duplicates(subset=["ds"], keep="last")
    df = df.reset_index(drop=True)
    return df[["ds", "y"]]


def _build_forecast_index(actuals: pd.DataFrame, future_periods: int) -> pd.DataFrame:
    """
    Constrói o DataFrame de datas para forecast cobrindo
    o histórico + `future_periods` meses adicionais.
    """
    freq = pd.infer_freq(actuals["ds"])
    if freq is None:
        freq = "MS"  # padrão mensal se não inferível
    last_date = actuals["ds"].max()
    future_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1),
        periods=future_periods,
        freq=freq,
    )
    all_dates = pd.concat(
        [actuals[["ds"]], pd.DataFrame({"ds": future_dates})], ignore_index=True
    )
    return all_dates.drop_duplicates().sort_values("ds").reset_index(drop=True)


def _add_anomaly_flags(
    merged: pd.DataFrame,
    sigma: float,
) -> pd.DataFrame:
    """
    Adiciona colunas is_anomaly, tipo_anomalia e pct_desvio ao DataFrame mesclado.

    O DataFrame `merged` deve ter: y, yhat, yhat_lower, yhat_upper, z_score.
    """
    merged = merged.copy()

    # is_anomaly: fora dos prediction intervals Prophet ou |z_score| >= sigma
    fora_pi = (merged["y"] > merged["yhat_upper"]) | (merged["y"] < merged["yhat_lower"])
    alto_zscore = merged["z_score"].abs() >= sigma
    merged["is_anomaly"] = (fora_pi | alto_zscore).astype(bool)

    # tipo: alta / baixa / normal
    merged["tipo_anomalia"] = np.where(
        ~merged["is_anomaly"],
        "normal",
        np.where(merged["y"] > merged["yhat"], "alta", "baixa"),
    )

    # pct_desvio: (real - esperado) / esperado * 100
    merged["pct_desvio"] = np.where(
        merged["yhat"].abs() > 0,
        ((merged["y"] - merged["yhat"]) / merged["yhat"].abs() * 100).round(2),
        np.nan,
    )
    return merged


# ---------------------------------------------------------------------------
# Z-score fallback (sem Prophet)
# ---------------------------------------------------------------------------

def zscore_fallback(
    df: pd.DataFrame,
    sigma: float = SIGMA_DEFAULT,
) -> pd.DataFrame:
    """
    Detecção de anomalias via Z-score puro (fallback para séries curtas).

    Parâmetros
    ----------
    df : pd.DataFrame
        Colunas obrigatórias: ds (datetime ou string AAAA-MM-DD), y (numérico).
        Colunas opcionais extra são preservadas na saída.
    sigma : float
        Número de desvios-padrão para classificar como anomalia.

    Retorna
    -------
    pd.DataFrame com colunas:
        ds, y, yhat (= média), yhat_lower, yhat_upper,
        z_score, tipo_anomalia, pct_desvio, metodo, is_anomaly
    """
    _validate_series(df, min_rows=2)
    df = _prepare_series(df)

    mu = df["y"].mean()
    std = df["y"].std(ddof=1)

    result = df.copy()
    result["yhat"] = mu
    result["yhat_lower"] = mu - sigma * (std if std > 0 else 0)
    result["yhat_upper"] = mu + sigma * (std if std > 0 else 0)
    result["z_score"] = np.where(std > 0, (df["y"] - mu) / std, 0.0).round(4)
    result["metodo"] = "zscore"

    result = _add_anomaly_flags(result, sigma=sigma)
    return result


# ---------------------------------------------------------------------------
# ProphetAnomalyDetector
# ---------------------------------------------------------------------------

class ProphetAnomalyDetector:
    """
    Detector de anomalias baseado em Meta Prophet para séries mensais.

    Usa Prophet para modelar tendência e sazonalidade anual, gerando
    intervalos de predição probabilísticos. Pontos fora do intervalo
    (yhat_lower, yhat_upper) são classificados como anomalias.

    Para séries com menos de `min_periods` pontos, faz fallback
    automático para Z-score.

    Parâmetros
    ----------
    seasonality_mode : str
        'multiplicative' (recomendado para dados de saúde com crescimento)
        ou 'additive'.
    yearly_seasonality : bool | int
        True habilita sazonalidade anual automática.
    changepoint_prior_scale : float
        Flexibilidade da tendência (0.01 = rígida, 0.5 = muito flexível).
    interval_width : float
        Largura do prediction interval (0.95 → ~2σ equiv. para dados normais).
    min_periods : int
        Mínimo de pontos históricos para usar Prophet (fallback Z-score abaixo).
    sigma_fallback : float
        Limiar Z-score usado no fallback e na lógica adicional is_anomaly.

    Exemplos
    --------
    >>> import pandas as pd
    >>> from ml.anomaly_detector import ProphetAnomalyDetector
    >>>
    >>> # Série com 36 meses
    >>> dates = pd.date_range("2021-01", periods=36, freq="MS")
    >>> df = pd.DataFrame({"ds": dates, "y": [1000 + i*10 for i in range(36)]})
    >>>
    >>> detector = ProphetAnomalyDetector()
    >>> result = detector.detect(df)
    >>> print(result[result.is_anomaly])
    """

    def __init__(
        self,
        seasonality_mode: str = "multiplicative",
        yearly_seasonality: bool | int = True,
        changepoint_prior_scale: float = CHANGEPOINT_PRIOR,
        interval_width: float = INTERVAL_WIDTH_DEFAULT,
        min_periods: int = MIN_PERIODS_PROPHET,
        sigma_fallback: float = SIGMA_DEFAULT,
    ) -> None:
        self.seasonality_mode = seasonality_mode
        self.yearly_seasonality = yearly_seasonality
        self.changepoint_prior_scale = changepoint_prior_scale
        self.interval_width = interval_width
        self.min_periods = min_periods
        self.sigma_fallback = sigma_fallback
        self._model = None

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def fit(self, df: pd.DataFrame) -> "ProphetAnomalyDetector":
        """
        Treina o modelo Prophet na série histórica.

        Parâmetros
        ----------
        df : pd.DataFrame
            Colunas: ds (datetime), y (float).

        Retorna
        -------
        self (para encadeamento).
        """
        _validate_series(df, min_rows=self.min_periods)
        df = _prepare_series(df)

        try:
            from prophet import Prophet  # type: ignore[import]
        except ImportError as e:
            raise ImportError(
                "Prophet não está instalado. "
                "Execute: pip install 'saude-publica-br[ml]'"
            ) from e

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = Prophet(
                seasonality_mode=self.seasonality_mode,
                yearly_seasonality=self.yearly_seasonality,
                weekly_seasonality=False,
                daily_seasonality=False,
                changepoint_prior_scale=self.changepoint_prior_scale,
                interval_width=self.interval_width,
            )
            # Sazonalidade anual customizada com Fourier de ordem mais alta
            # para capturar picos sazonais do SUS (ex: dengue em verão)
            if self.yearly_seasonality is True:
                model.add_seasonality(
                    name="yearly_custom",
                    period=365.25,
                    fourier_order=FOURIER_ORDER_YEARLY,
                )
                # Desabilita a automática para evitar duplicação
                model.yearly_seasonality = False

            model.fit(df, verbose=False)

        self._model = model
        return self

    def predict(self, df: pd.DataFrame | None = None, periods: int = 0) -> pd.DataFrame:
        """
        Gera previsões com intervalos de confiança.

        Se `df` for fornecido, faz previsão nas datas de `df`.
        Caso contrário, extende `periods` meses além do histórico.

        Parâmetros
        ----------
        df : pd.DataFrame | None
            DataFrame com coluna ds para previsão.
        periods : int
            Meses futuros a projetar (ignorado se df fornecido).

        Retorna
        -------
        pd.DataFrame com: ds, yhat, yhat_lower, yhat_upper (e demais
        colunas Prophet: trend, seasonal, etc.).
        """
        if self._model is None:
            raise RuntimeError("Modelo não treinado. Chame .fit() primeiro.")

        if df is not None:
            future = df[["ds"]].copy()
            future["ds"] = pd.to_datetime(future["ds"])
        else:
            future = self._model.make_future_dataframe(periods=periods, freq="MS")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            forecast = self._model.predict(future)

        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper", "trend"]]

    def detect(
        self,
        df: pd.DataFrame,
        future_periods: int = 0,
    ) -> pd.DataFrame:
        """
        Pipeline completo: fit → predict → flag anomalias.

        Se a série tiver menos de `min_periods` pontos, usa Z-score
        automaticamente como fallback (sem disparar exceção).

        Parâmetros
        ----------
        df : pd.DataFrame
            Colunas obrigatórias: ds, y. Colunas extras são preservadas.
        future_periods : int
            Meses adicionais a projetar além da série (padrão: 0 = apenas
            histórico).

        Retorna
        -------
        pd.DataFrame com colunas:
            ds, y, yhat, yhat_lower, yhat_upper,
            z_score, tipo_anomalia, pct_desvio, metodo, is_anomaly
        """
        _validate_series(df, min_rows=2)
        df_clean = _prepare_series(df)

        # Fallback automático para séries curtas
        if len(df_clean) < self.min_periods:
            logger.debug(
                "Série com %d pontos < min_periods=%d → usando Z-score fallback.",
                len(df_clean),
                self.min_periods,
            )
            result = zscore_fallback(df_clean, sigma=self.sigma_fallback)
            return result

        # Prophet
        try:
            self.fit(df_clean)

            if future_periods > 0:
                forecast_dates = _build_forecast_index(df_clean, future_periods)
            else:
                forecast_dates = df_clean[["ds"]].copy()

            forecast = self.predict(df=forecast_dates)

            # Mescla actuals + forecast
            merged = df_clean.merge(forecast, on="ds", how="inner")

            # Z-score sobre os resíduos (y - yhat) / desvio dos resíduos
            residuos = merged["y"] - merged["yhat"]
            std_res = residuos.std(ddof=1)
            merged["z_score"] = np.where(
                std_res > 0, (residuos / std_res).round(4), 0.0
            )
            merged["metodo"] = "prophet"

            merged = _add_anomaly_flags(merged, sigma=self.sigma_fallback)
            return merged

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Prophet falhou (%s) → fallback para Z-score.", exc
            )
            result = zscore_fallback(df_clean, sigma=self.sigma_fallback)
            return result


# ---------------------------------------------------------------------------
# Função de conveniência de alto nível
# ---------------------------------------------------------------------------

def detect_anomalies(
    df: pd.DataFrame,
    municipio_cod: str = "",
    uf_sigla: str = "",
    sigma: float = SIGMA_DEFAULT,
    min_periods: int = MIN_PERIODS_PROPHET,
    future_periods: int = 0,
) -> AnomalyResult:
    """
    Detecta anomalias em uma série temporal de um município.

    Orquestra Prophet (longa) ou Z-score (curta), retorna AnomalyResult
    com metadados para logging e persistência.

    Parâmetros
    ----------
    df : pd.DataFrame
        Colunas: ds (datetime ou AAAA-MM-01), y (total_procedimentos).
    municipio_cod : str
        Código IBGE do município (metadata apenas).
    uf_sigla : str
        Sigla da UF (metadata apenas).
    sigma : float
        Limiar de desvios para classificar como anomalia.
    min_periods : int
        Mínimo de pontos para usar Prophet.
    future_periods : int
        Meses futuros a projetar.

    Retorna
    -------
    AnomalyResult com .success, .metodo, .anomalies, .forecast.
    """
    try:
        _validate_series(df, min_rows=2)
    except ValueError as e:
        empty = pd.DataFrame(
            columns=["ds", "y", "yhat", "yhat_lower", "yhat_upper",
                     "z_score", "tipo_anomalia", "pct_desvio", "metodo", "is_anomaly"]
        )
        return AnomalyResult(
            municipio_cod=municipio_cod,
            uf_sigla=uf_sigla,
            metodo="erro",
            n_pontos=len(df),
            n_anomalias=0,
            anomalies=empty,
            forecast=empty,
            erro=str(e),
        )

    detector = ProphetAnomalyDetector(
        sigma_fallback=sigma,
        min_periods=min_periods,
    )

    try:
        forecast = detector.detect(df, future_periods=future_periods)
        metodo = forecast["metodo"].iloc[0] if len(forecast) else "zscore"
        anomalies = forecast[forecast["is_anomaly"]].reset_index(drop=True)

        return AnomalyResult(
            municipio_cod=municipio_cod,
            uf_sigla=uf_sigla,
            metodo=metodo,
            n_pontos=len(forecast),
            n_anomalias=len(anomalies),
            anomalies=anomalies,
            forecast=forecast,
        )

    except Exception as exc:  # noqa: BLE001
        empty = pd.DataFrame(
            columns=["ds", "y", "yhat", "yhat_lower", "yhat_upper",
                     "z_score", "tipo_anomalia", "pct_desvio", "metodo", "is_anomaly"]
        )
        return AnomalyResult(
            municipio_cod=municipio_cod,
            uf_sigla=uf_sigla,
            metodo="erro",
            n_pontos=len(df),
            n_anomalias=0,
            anomalies=empty,
            forecast=empty,
            erro=str(exc),
        )
