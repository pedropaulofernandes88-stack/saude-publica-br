# saudeemdado — cliente Python

Acesso programático à API pública do [Saúde em Dado](https://saudeemdado.com):
mortalidade no Brasil (SIM/DataSUS, 2015–2024), com taxas padronizadas por
idade, IC95% e excesso de mortalidade. Sem cadastro.

## Instalação

```bash
pip install saudeemdado            # quando publicado no PyPI
# ou, direto do repositório:
pip install "git+https://github.com/pedropaulofernandes88-stack/saude-publica-br#subdirectory=clients/python"
```

## Uso

```python
import saudeemdado as sd

# Série mensal de óbitos em SP (todas as causas)
df = sd.serie_mensal(uf="SP", as_df=True)

# Municípios de MG em 2023 com população ≥ 50 mil, com taxa padronizada e IC95%
mg = sd.municipios(uf="MG", ano=2023, pop_min=50_000, as_df=True)
mg.nlargest(10, "taxa_padronizada_100k")

# Top 20 causas básicas (CID-10) em 2024
causas = sd.causas(ano=2024, top=20, as_df=True)

# Excesso de mortalidade no Brasil (pandemia e pós)
exc = sd.excesso("BR", as_df=True)

# Dengue: incidência municipal na epidemia de 2024
deng = sd.dengue(uf="MG", ano=2024, as_df=True)
deng.nlargest(10, "incidencia_100k")

# Dengue por semana epidemiológica (curva sazonal de SP)
sem = sd.dengue(uf="SP", ano=2024, nivel="semana", as_df=True)

# Internações SUS: permanência média e custo por município
intern = sd.internacoes(uf="SP", ano=2023, as_df=True)
intern.nlargest(10, "permanencia_media")

# Dicionário CID-10 e metadados do dataset
cid = sd.cid10(as_df=True)
sd.metadados()
```

## Citação

Cite as fontes primárias (SIM/DataSUS — Ministério da Saúde; IBGE) e a
plataforma. Ver `CITATION.cff` na raiz do repositório e
[saudeemdado.com/sobre](https://saudeemdado.com/sobre/).
