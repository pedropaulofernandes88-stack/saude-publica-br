<div align="center">

# 🏥 Saúde em Dado

### Inteligência epidemiológica aberta sobre os microdados do SUS

**Mortalidade · Dengue · Internações · Natalidade · Vulnerabilidade social — do Brasil inteiro, a custo zero.**

[![Site](https://img.shields.io/badge/site-saudeemdado.com-107752)](https://saudeemdado.com)
[![Licença](https://img.shields.io/badge/licença-MIT-green.svg)](LICENSE)
[![Custo](https://img.shields.io/badge/custo-R%24%200%2Fmês-success.svg)](#-arquitetura-a-custo-zero)
[![Dados](https://img.shields.io/badge/DataSUS-SIM·SINAN·SIH·SINASC-009688.svg)](#-fontes-de-dados)
[![Release](https://img.shields.io/badge/release-v3.0.0-blue.svg)](https://github.com/pedropaulofernandes88-stack/saude-publica-br/releases)

[**Site**](https://saudeemdado.com) · [**API**](https://saudeemdado.com/dados/) · [**Análises**](https://saudeemdado.com/artigos/) · [**Metodologia**](https://saudeemdado.com/metodologia/)

</div>

---

## 🎯 O que é

Os dados do SUS são **públicos por lei, mas inacessíveis na prática**: microdados em formato
proprietário (DBC), fragmentados por estado e competência, somando dezenas de gigabytes. Pesquisadores,
jornalistas e gestores gastam semanas em engenharia de dados antes de qualquer análise.

O **Saúde em Dado** elimina essa barreira. Ele transforma os microdados oficiais do **DataSUS** e do
**IBGE** em indicadores agregados, validados e consultáveis por **API pública gratuita**, **painéis
navegáveis** e **downloads abertos** — com pipeline 100% reproduzível e **custo de manutenção zero**.

> Mais de **14,4 milhões de óbitos** (2015–2024), **6,56 milhões de casos de dengue** (recorde de 2024),
> **39,9 milhões de internações** (R$ 63,2 bi) e **5,2 milhões de nascimentos** — em uma consulta.

---

## 📊 Fontes de dados

| Sistema | Conteúdo | Cobertura | Indicadores derivados |
|---|---|---|---|
| **SIM** | Mortalidade (óbitos) | 2015–2024 | Taxa bruta + **IC95%**, **taxa padronizada por idade**, **excesso de mortalidade** |
| **SINAN** | Dengue (notificações) | 2015–2024 | Incidência, gravidade, letalidade, **canal endêmico** |
| **SIH** | Internações hospitalares (AIH) | 2022–2024 | Permanência média, mortalidade intra-hospitalar, custo |
| **SINASC** | Nascidos vivos | 2021–2022 | Baixo peso, prematuridade, pré-natal, **mortalidade infantil** |
| **IBGE** | População (Censo 2022, Estimativas) e malhas | — | Denominadores, padronização, mapas |
| **IPEA / IBGE** | Vulnerabilidade social (proxy Censo 2022) | 2022 | Cruzamento desigualdade × saúde |

Todas as fontes são de **domínio público**. Apenas **agregados** são publicados — nenhum microdado
individual sai da máquina de processamento (privacidade por desenho).

---

## 🧮 Indicadores e métodos

- **Taxa padronizada por idade** (método direto, padrão Brasil/Censo 2022) — comparação legítima entre municípios, corrigindo o efeito da estrutura etária.
- **Intervalo de confiança de 95%** (método gama / Poisson exato) em toda taxa bruta; alerta para municípios &lt; 10 mil hab.
- **Excesso de mortalidade** — observado vs. esperado (baseline 2015–2019 ajustado por população), por UF e Brasil.
- **Canal endêmico de dengue** (diagrama de controle) — faixa esperada P25–P75 de 2015–2023 vs. ano observado.
- **Taxa de Mortalidade Infantil** — óbitos &lt; 1 ano (SIM) ÷ nascidos vivos (SINASC).
- **Índice de vulnerabilidade social (proxy)** — z-score de analfabetismo + falta de água (Censo 2022).

Documentação completa, fórmulas e **limitações declaradas**: **[saudeemdado.com/metodologia](https://saudeemdado.com/metodologia/)**.

---

## 🏗️ Arquitetura (a custo zero)

```
   Microdados DataSUS (.dbc/.csv)        IBGE (SIDRA / localidades / malhas)
              │                                      │
              ▼                                      ▼
   ┌───────────────────────────────────────────────────────┐
   │  Pipelines Python (local) — streaming + DuckDB         │
   │  scripts/pipeline_*.py · agregação · validação         │
   └───────────────────────────────────────────────────────┘
              │  (sobem apenas marts agregados, ~400 MB)
              ▼
   ┌───────────────────────────────────────────────────────┐
   │  Supabase (Postgres free tier) — somente leitura (RLS) │
   │     ├── API REST automática (PostgREST)                │
   │     └── Storage (Parquet com SHA-256)                  │
   └───────────────────────────────────────────────────────┘
              │
              ▼
   ┌───────────────────────────────────────────────────────┐
   │  Next.js estático (GitHub Pages) → saudeemdado.com     │
   │  JSON estático no build = egress ~zero no banco        │
   └───────────────────────────────────────────────────────┘

   Automação (GitHub Actions): deploy · keep-alive (≤6 dias) · validação de dados
```

**Princípios:** (1) agregar localmente, publicar só o essencial; (2) nenhum servidor de aplicação para
manter; (3) reprodutibilidade radical — todo número regenerável das fontes oficiais por um script aberto.

---

## 🚀 Como acessar

**Site:** [saudeemdado.com](https://saudeemdado.com) — painéis de mortalidade, dengue, internações,
nascimentos, mapa municipal, tendências e boletim por município.

**API REST pública** (sem cadastro; chave de leitura em [`.env.example`](.env.example)):

```bash
URL="https://zekjhmxjamatlxpkykde.supabase.co/rest/v1"; KEY="<anon key>"

# Municípios de MG por taxa padronizada de mortalidade (2023)
curl "$URL/mart_mortalidade_municipio?uf_sigla=eq.MG&ano=eq.2023&capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&order=taxa_padronizada_100k.desc&limit=10" -H "apikey: $KEY"

# Dengue por município/ano (incidência e letalidade)
curl "$URL/mart_dengue_municipio_ano?uf_sigla=eq.SP&ano_epi=eq.2024&order=incidencia_100k.desc&limit=10" -H "apikey: $KEY"
```

**Pacote Python** ([`clients/python`](clients/python/)):

```python
import saudeemdado as sd
sd.municipios(uf="MG", ano=2023, as_df=True).nlargest(10, "taxa_padronizada_100k")
sd.dengue(uf="SP", ano=2024, as_df=True)
```

**Servidor MCP** ([`mcp_server/server.py`](mcp_server/server.py)) — consulte a base por assistentes de IA
(Claude Desktop/Code) em linguagem natural.

**Downloads** — marts completos em **Parquet** com **SHA-256** na [página Dados & API](https://saudeemdado.com/dados/).

---

## 🔁 Reprodutibilidade

```bash
# Python 3.10–3.12 (datasus-dbc não compila no 3.13+)
pip install duckdb pandas pyarrow requests scipy datasus-dbc dbfread

python scripts/pipeline_v2.py        # SIM 2015–2024 (padronização, IC95%, excesso)
python scripts/pipeline_sinan.py     # Dengue 2015–2024
python scripts/pipeline_sih.py       # Internações 2022–2024
python scripts/pipeline_sinasc.py    # Nascimentos + mortalidade infantil
python scripts/pipeline_ivs.py       # Vulnerabilidade social (proxy Censo 2022)
python scripts/validate_data.py      # validação contra âncoras oficiais
```

Os pipelines fazem download, agregam em streaming com **checkpoint resumível** e publicam via API.
A rotina de validação ([`.github/workflows/validate-data.yml`](.github/workflows/validate-data.yml))
confere mensalmente totais oficiais e conciliação entre marts.

---

## 📁 Estrutura

```
saude-publica-br/
├── scripts/              # pipelines (SIM, SINAN, SIH, SINASC, IVS) + validação
├── site/                # Next.js 14 (estático) → saudeemdado.com
│   ├── app/             # páginas: painel, dengue, internacoes, nascimentos,
│   │                    #          mapa, tendencias, artigos, dados, metodologia
│   ├── components/      # gráficos (Recharts), KPIs, byline
│   ├── content/         # artigos assinados (seção Análises)
│   └── scripts/         # geração de JSON estático no build
├── clients/python/      # pacote `saudeemdado` (PyPI-ready)
├── mcp_server/          # servidor Model Context Protocol
├── data/marts/          # marts agregados (Parquet)
├── .github/workflows/   # deploy, keep-alive, validação
├── CITATION.cff · LICENSE · .zenodo.json
```

---

## 📰 Análises

A seção **[Análises](https://saudeemdado.com/artigos/)** reúne artigos que cruzam os dados da plataforma
com leitura epidemiológica e estatística — da anatomia da epidemia de dengue de 2024 ao paradoxo do
sub-registro na relação vulnerabilidade × mortalidade.

---

## 🗺️ Roadmap

- [x] Mortalidade (SIM) 2015–2024 · taxa padronizada · IC95% · excesso
- [x] Dengue (SINAN) · Internações (SIH) · Nascimentos/Mortalidade infantil (SINASC)
- [x] Vulnerabilidade social (proxy Censo 2022) e cruzamento com mortalidade
- [x] Pacote Python · servidor MCP · boletim municipal · seção de Análises
- [ ] IVS **oficial** do IPEA (Atlas da Vulnerabilidade Social)
- [ ] SIH anos anteriores (2015–2021) e SINASC 2023+
- [ ] SINAN outros agravos (chikungunya, zika) · CNES (leitos/estabelecimentos)
- [ ] Imagens de capa próprias para a seção de Análises · DOI via Zenodo

---

## 🤝 Créditos e projetos relacionados

- **[LabSUS](https://github.com/goldenluke/labsus)** (Lucas Amaral Dourado, Universidade Federal do Tocantins) — projeto acadêmico de inteligência em saúde pública que inspirou aqui o cruzamento saúde × vulnerabilidade, a detecção de surtos por canal endêmico e a nota de uso ético. Métodos de domínio público; nenhum código foi copiado.
- **Fontes primárias:** DATASUS/Ministério da Saúde (SIM, SINAN, SIH, SINASC), **IBGE** (Censo 2022, Estimativas, malhas) e **IPEA**.

---

## ⚖️ Uso ético

Os indicadores são **agregados e descritivos** — não substituem julgamento técnico. Pede-se, de boa-fé,
que a plataforma não seja usada para discriminação no acesso à saúde, vigilância em massa de indivíduos
ou automação de decisões clínicas/de política pública sem supervisão profissional. Detalhes na [LICENSE](LICENSE).

## 📄 Licença

Código sob licença **MIT**. Dados originais em **domínio público** (DATASUS/MS, IBGE, IPEA) — cite as
fontes primárias. Para citar a plataforma, veja [`CITATION.cff`](CITATION.cff).

---

## 👤 Autor

**Pedro Fernandes**
Mestrando em Saúde Coletiva (IAMSPE) · Pós-graduando em Inteligência Artificial e Ciência de Dados em
Saúde (Hospital Sírio-Libanês) · Diretor de Tecnologia da Informação — Prefeitura Municipal de Penápolis (SP)

[![Lattes](https://img.shields.io/badge/Currículo-Lattes-1f6feb)](http://lattes.cnpq.br/6641343625206093)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-pedro--f-0a66c2)](https://www.linkedin.com/in/pedro-f-540154408/)

<div align="center">

—

**[saudeemdado.com](https://saudeemdado.com)** · dados públicos, abertos e a custo zero para a pesquisa em saúde no Brasil

</div>
