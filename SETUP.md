# Setup — saude-publica-br

> **Você precisa fazer apenas 3 coisas.** O resto é automático.

---

## ✅ O que você faz (3 passos)

### Passo 1 — Criar conta gratuita no Supabase

1. Acesse **https://supabase.com** → clique em **Start your project** (gratuito)
2. Faça login com GitHub ou Google
3. Clique em **New project**
4. Preencha:
   - **Name:** `saude-publica-br`
   - **Database Password:** escolha uma senha (anote!)
   - **Region:** South America (São Paulo)
5. Aguarde ~2 minutos o projeto subir

### Passo 2 — Copiar o DATABASE_URL

1. No painel do Supabase, clique em **Settings** (engrenagem) → **Database**
2. Role até **Connection string** → selecione a aba **URI**
3. Copie a URL (parece com `postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres`)
4. **Substitua `[YOUR-PASSWORD]`** pela senha que você escolheu no Passo 1

### Passo 3 — Rodar o bootstrap

```bash
# Na pasta do projeto:
python bootstrap.py
```

Quando o script perguntar pelo `DATABASE_URL`, cole a URL do Passo 2.

---

## 🤖 O que o bootstrap faz automaticamente

| # | O que acontece | Tempo estimado |
|---|----------------|----------------|
| 1 | Verifica Python 3.11+ | < 1s |
| 2 | Instala todos os pacotes (`pip install`) | 2–5 min |
| 3 | Configura o `.env` com suas credenciais | < 1s |
| 5 | Cria as tabelas no Supabase (SQL) | 30s |
| 6 | Carrega municípios IBGE + CID-10 | 1 min |
| 7 | Baixa dados piloto: SP, Jan–Mar 2024 | 3–8 min |
| 8 | Roda `dbt build` — cria todos os marts | 2 min |

**Total: ~10–20 minutos na primeira execução.**

---

## 🔄 Se algo falhar no meio

O bootstrap pode ser retomado de qualquer passo:

```bash
python bootstrap.py --step 5   # retoma a partir do passo 5
python bootstrap.py --check    # verifica o que está funcionando
```

---

## 📥 Ingestão

Os pipelines que alimentam a base publicada estão em `scripts/` — SIM, SINAN,
SIH, SINASC, CNES e SIOPS. Rodam direto, calculam os marts em DuckDB local e
publicam o resultado agregado no Supabase:

```bash
python scripts/pipeline_v2.py
```

> ⚠️ `make ingest-full` e `python -m ingestion.ingest_sia_pa --all` saíram em
> 2026-08-22. Miravam o SIA (produção ambulatorial), fonte fora do pipeline
> atual, e faziam parte da primeira arquitetura — hoje em
> [`archive/ingestion/`](archive/ingestion/README.md).

---

## 🚀 Comandos do dia a dia

```bash
make check         # Verifica se tudo está OK
make dbt-build     # Reconstrói os marts
make test          # Roda a suíte de testes
```

Para rodar o site localmente:

```bash
cd site && npm ci && npm run dev    # http://localhost:3000
```

---

## 🌐 Onde os dados ficam

| O quê | Onde |
|-------|------|
| marts | Supabase (PostgREST) — API pública, somente leitura |
| site local | http://localhost:3000 (`npm run dev` em `site/`) |
| site publicado | https://saudeemdado.com |

> Não há API própria nem Redis. A stack anterior (FastAPI + Redis + Docker)
> está em [`archive/`](archive/README.md) e não é implantada.

---

## ❓ Dúvidas frequentes

**"Erro de conexão com o Supabase"**
Verifique se substituiu `[YOUR-PASSWORD]` na URL e se o projeto do Supabase está ativo.

**"dbt build falhou"**
Execute `cd dbt && dbt debug` para diagnosticar. Provavelmente é um problema de conexão.

**"O FTP do DataSUS está instável"**
Normal — o DataSUS tem quedas frequentes. Tente novamente com `make ingest-pilot`.
