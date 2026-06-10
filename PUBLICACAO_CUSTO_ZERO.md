# 🆓 Publicação a custo zero — guia oficial

Este projeto está publicado **sem nenhum custo mensal**, com **dados reais e
abertos** do DataSUS e IBGE, acessíveis a qualquer pesquisador.

## Arquitetura (custo: R$ 0/mês)

```
OpenDataSUS (CSV nacional, SIM)      IBGE (API localidades + SIDRA)
        │                                     │
        └────────────┬────────────────────────┘
                     ▼
   scripts/pipeline_custo_zero.py  (roda na sua máquina)
        DuckDB agrega 4,4M+ óbitos → marts compactos (~1M linhas)
                     │  upload via REST
                     ▼
        Supabase free tier (Postgres, 500MB)
                     │
        ┌────────────┴─────────────┐
        ▼                          ▼
  API pública REST           Dashboard Streamlit
  (PostgREST, sem servidor)  (Streamlit Community Cloud, grátis)
```

O que **não** sobe para o banco: microdados brutos (1,5GB ficam só na sua
máquina). O que é público: marts agregados + dimensões + metadados.

## API pública — uso imediato, sem cadastro

Base: `https://zekjhmxjamatlxpkykde.supabase.co/rest/v1/`

Cabeçalho obrigatório (chave pública de leitura):

```
apikey: <SUPABASE_ANON_KEY do .env.example>
```

Exemplos:

```bash
# Óbitos totais por mês no Brasil (todas as causas)
curl "$URL/rest/v1/mart_mortalidade_uf_mes?select=mes_competencia,uf_sigla,obitos&capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&faixa_etaria=eq.TOTAL" -H "apikey: $KEY"

# Taxa de mortalidade por 100k hab — municípios de MG em 2023, maiores taxas
curl "$URL/rest/v1/mart_mortalidade_municipio?select=municipio_nome,obitos,taxa_obitos_100k&uf_sigla=eq.MG&ano=eq.2023&capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&populacao=gte.50000&order=taxa_obitos_100k.desc&limit=20" -H "apikey: $KEY"

# Principais causas básicas (CID-10) em SP, 2024
curl "$URL/rest/v1/mart_mortalidade_causa?uf_sigla=eq.SP&ano=eq.2024&order=obitos.desc&limit=15" -H "apikey: $KEY"

# Metadados (fontes, metodologia, licença)
curl "$URL/rest/v1/meta_dataset" -H "apikey: $KEY"
```

Sintaxe de filtros: [PostgREST](https://postgrest.org/en/stable/references/api/tables_views.html)
(`eq.`, `gte.`, `like.`, `order=`, `limit=`, `select=`).

## Tabelas publicadas

| Tabela | Grain | Linhas |
|--------|-------|--------|
| `mart_mortalidade_municipio` | município × ano × capítulo CID-10 × sexo | ~600 mil |
| `mart_mortalidade_uf_mes` | UF × mês × capítulo × sexo × faixa etária | ~324 mil |
| `mart_mortalidade_causa` | UF × ano × causa básica (CID-10 3 chars) | ~62 mil |
| `dim_municipio` | municípios IBGE (código 6 e 7 dígitos, UF, região) | 5.571 |
| `dim_populacao` | população municipal por ano (Censo 2022 / Estimativas) | ~16,7 mil |
| `dim_cid10_capitulo` | capítulos da CID-10 | 22 |
| `meta_dataset` | metadados, fontes e licença | — |

Linhas com `capitulo_cid='TOTAL'`, `sexo='TOTAL'` ou `faixa_etaria='TOTAL'`
são subtotais pré-calculados — filtre-os para evitar dupla contagem.

## Atualizar / regerar os dados

```bash
pip install duckdb pandas pyarrow requests
python scripts/pipeline_custo_zero.py --anos 2022 2023 2024
```

O script é idempotente (upsert pela chave primária). Para adicionar um ano novo
quando o Ministério da Saúde publicar (ex.: DO25OPEN.csv), basta incluir o ano.

> Nota: a carga usa a anon key e só funciona enquanto a tabela permitir escrita.
> Após a publicação, a escrita anônima foi revogada (RLS somente leitura).
> Para recarregar: rode a migração `permitir_escrita_temporaria` (ver
> `migrations/` no Supabase) ou use a service key no dashboard do Supabase.

## Dashboard público (Streamlit Community Cloud)

1. Suba este repositório para o GitHub (público)
2. Acesse [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Repositório: seu fork · Branch: `main` · Main file: `dashboard_publico/app.py`
4. Deploy — pronto, URL pública `https://<app>.streamlit.app`

Sem variáveis obrigatórias: a URL/chave pública de leitura já têm default no app.

## Limites do free tier (e o que acontece se estourar)

| Recurso | Limite free | Uso atual |
|---------|-------------|-----------|
| Banco Supabase | 500 MB | ~150 MB |
| Egress Supabase | 5 GB/mês | depende do tráfego |
| Pausa por inatividade | 7 dias sem requisições | dashboard/API mantêm ativo |
| Streamlit Cloud | 1 GB RAM | suficiente |

Se o projeto Supabase pausar por inatividade, reative no dashboard
([app.supabase.com](https://app.supabase.com)) — os dados não são perdidos.

## Fontes e licença

- **SIM/DataSUS** — Ministério da Saúde, microdados abertos
  ([OpenDataSUS](https://opendatasus.saude.gov.br/dataset/sim)), domínio público.
- **IBGE** — Censo 2022 e Estimativas de população (SIDRA), uso livre.
- Óbitos fetais excluídos; ano mais recente pode ser preliminar.
- Cite as fontes originais em trabalhos acadêmicos.
