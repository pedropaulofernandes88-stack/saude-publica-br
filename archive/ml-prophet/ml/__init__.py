"""
ml — Módulo de Machine Learning para saude-publica-br.

Fornece detecção de anomalias em séries temporais de produção ambulatorial
usando Meta Prophet como modelo principal, com Z-score estatístico como
fallback para séries curtas (< min_periods).

Uso rápido:
    from ml.anomaly_detector import ProphetAnomalyDetector, zscore_fallback

    detector = ProphetAnomalyDetector()
    result = detector.detect(series_df)           # DataFrame com ds, y

    # Fallback para séries curtas
    flags = zscore_fallback(series_df, sigma=2.0)

Uso em batch (pré-computação para todos os municípios):
    from ml.batch_scorer import score_and_persist
    await score_and_persist(database_url="postgresql://...")
"""
from __future__ import annotations

from ml.anomaly_detector import ProphetAnomalyDetector, zscore_fallback

__all__ = ["ProphetAnomalyDetector", "zscore_fallback"]
