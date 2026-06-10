"""
validation — Great Expectations quality layer for saude-publica-br marts.

Estrutura:
  validation/
    __init__.py          — este arquivo
    loader.py            — carrega DataFrames dos marts via psycopg/Supabase
    run_validations.py   — CLI runner: executa todas as suites e imprime resumo
    suites/
      __init__.py
      mart_producao_amb.py
      mart_epi_cid10.py
      mart_ranking_municipios.py
      mart_acesso_cobertura.py
      mart_mix_complexidade.py
      mart_sazonalidade.py

Uso rápido:
  validate-marts                       # roda todas as suites
  validate-marts --suite producao_amb  # roda apenas uma suite
  validate-marts --fail-fast           # para no primeiro erro
"""
