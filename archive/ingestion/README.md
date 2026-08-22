# `ingestion/` — ingestão de microdados brutos do DataSUS

Aposentado em 2026-08-22. **Nada aqui é executado**: nem por CI, nem por
agendador, nem pelo site publicado.

Estes módulos baixavam microdados via PySUS e faziam `COPY` para tabelas `*_raw`
no Postgres, que o dbt transformava em marts. É a primeira arquitetura — a mesma
descrita em [`../base.md`](../base.md) e cujas outras camadas (API FastAPI,
Streamlit, Docker) já estavam em `archive/`.

O que ficou na raiz: **`ingestion/utils/`**, com `bulk_load.py` e
`ingestion_log.py`. Ver "O que NÃO veio junto", no fim.

---

## A evidência

### 1. `ingest_all_states.py` não é sequer importável

`SISTEMA_CONFIG` é um dicionário de módulo (linha 56): as chamadas
`_sia_pa_schema()`, `_sim_do_schema()`, `_sih_aih_schema()`, `_sinan_schema()` e
`_cnes_schema()` acontecem **no import**, e nenhuma dessas funções existe no
arquivo.

```
$ python -c "import ingestion.ingest_all_states"
  File "ingestion/ingest_all_states.py", line 62, in <module>
    "schema": _sia_pa_schema(),
NameError: name '_sia_pa_schema' is not defined
```

São os 5 `F821` que o `ruff` acusava. Foram introduzidos em `b50a10e`
(2026-06-10) e sobreviveram mais de dois meses sem ninguém notar — o que só é
possível se o módulo nunca foi executado. `flows/weekly_ingest_nacional.py`
importava justamente esse módulo, então aquele flow também nunca subiu.

### 2. Ninguém importa

Varredura em `scripts/`, `ml/`, `validation/`, `mcp_server/`, `clients/`,
`site/` e `tests/`: o único importador vivo é `tests/ingestion/test_utils.py`,
e ele importa apenas `ingestion.utils`. `flows/` importava `ingestion/` — um
laço fechado entre dois diretórios que ninguém mais chamava.

### 3. As tabelas são um namespace paralelo ao que está publicado

| escrito por | tabelas |
|---|---|
| `ingestion/` → dbt | `sim_do_raw`, `sih_aih_raw` → `mart_mortalidade`, `mart_internacoes`, `mart_producao_amb` |
| `scripts/` (vivo) | `mart_mortalidade_municipio`, `mart_mortalidade_uf_mes`, `mart_internacoes_municipio`, `mart_internacoes_hospital`, `dim_municipio` |

Os nomes são disjuntos. O servidor MCP — o produto publicado no PyPI — expõe só
os da segunda linha. E os comentários das próprias migrações confirmam para quem
os marts do dbt serviam: `V009__mart_mortalidade.sql` diz "Populado pelo pipeline
dbt", `V010__mart_internacoes.sql` diz "Consultado pelos endpoints
`GET /internacoes/*`" — endpoints da API FastAPI que já está em
[`../api/`](../api/).

### 4. `refs_loader.py` — o candidato mais provável a estar vivo, e não estava

Era a hipótese mais forte de sobrevivência: alguém precisa carregar as
dimensões. Não é este arquivo.

- Ele cria e popula `ref_cid10`, `ref_sigtap`, `ref_ibge_municipios` e
  `ref_ibge_populacao`, via `psycopg` sobre `DATABASE_URL`.
- **Nenhuma dessas quatro tabelas aparece em `migrations/`.** Não existem no
  Supabase de produção.
- A dimensão que existe de verdade, `dim_municipio`, sai de
  `data/refs/municipios.parquet` — construída em `scripts/pipeline_v2.py:236` e
  publicada pelo `SupabaseLoader.load_df` do próprio script.
- Doze pipelines em `scripts/` leem `data/refs/municipios.parquet`; nenhum
  consulta `ref_ibge_municipios`.

`ingestion_log`, a tabela do ledger de ingestão, também não está em
`migrations/`.

### 5. `ingest_sia_pa.py` mira uma fonte fora do pipeline

SIA (produção ambulatorial) não faz parte do conjunto atual — SIM, SINAN, SIH,
SINASC, CNES, SIOPS. Era o alvo dos entrypoints `ingest-sia` do `pyproject.toml`
e dos alvos `ingest-pilot`/`ingest-sp`/`ingest-full`/`ingest-uf` do `Makefile`,
todos removidos junto.

---

## O que NÃO veio junto

**`ingestion/utils/` continua na raiz** — `bulk_load.py` (DataFrame → Parquet →
`COPY`) e `ingestion_log.py` (o ledger). É a única parte com suíte de testes
real: 64 testes em `tests/ingestion/test_utils.py`, executados pelo CI, e zero
ocorrências de regra `F` no `ruff`.

Honestamente: **também não tem consumidor em produção hoje.** Os pipelines vivos
de `scripts/` têm o próprio `SupabaseLoader.load_df`, que fala com a API REST do
Supabase em vez de `COPY` direto no Postgres. `ingestion/utils/` ficou porque
arquivá-lo significaria descartar 64 testes que passam, em troca de nada — mas
se a decisão for que a infraestrutura de `COPY` não volta, ele e o teste descem
juntos para cá.

---

## Nota sobre os imports

Os arquivos deste diretório ainda dizem `from ingestion.utils.bulk_load import
...` e `from ingestion.ingest_sim import ...`. Esses caminhos não resolvem mais
a partir daqui. É intencional: código arquivado não roda, e reescrever os
imports daria a impressão de que roda. O histórico está intacto —
`git log --follow archive/ingestion/refs_loader.py`.
