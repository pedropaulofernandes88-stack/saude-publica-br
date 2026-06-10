"""
suites — um módulo por mart, cada um exporta build_suite(df) → ExpectationSuite.
"""
from .mart_producao_amb import build_suite as suite_producao_amb
from .mart_epi_cid10 import build_suite as suite_epi_cid10
from .mart_ranking_municipios import build_suite as suite_ranking_municipios
from .mart_acesso_cobertura import build_suite as suite_acesso_cobertura
from .mart_mix_complexidade import build_suite as suite_mix_complexidade
from .mart_sazonalidade import build_suite as suite_sazonalidade
from .mart_anomalias_prophet import build_suite as suite_anomalias_prophet
from .mart_mortalidade import build_suite as suite_mortalidade
from .mart_internacoes import build_suite as suite_internacoes

__all__ = [
    "suite_producao_amb",
    "suite_epi_cid10",
    "suite_ranking_municipios",
    "suite_acesso_cobertura",
    "suite_mix_complexidade",
    "suite_sazonalidade",
    "suite_anomalias_prophet",
    "suite_mortalidade",
    "suite_internacoes",
]
