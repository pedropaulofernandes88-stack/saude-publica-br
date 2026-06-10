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
| 4 | Sobe o Redis via Docker | 10s |
| 5 | Cria as tabelas no Supabase (SQL) | 30s |
| 6 | Carrega municípios IBGE + CID-10 | 1 min |
| 7 | Baixa dados piloto: SP, Jan–Mar 2024 | 3–8 min |
| 8 | Roda `dbt build` — cria todos os marts | 2 min |
| 9 | Inicia a API FastAPI | 5s |
| 10 | Abre o dashboard no navegador | automático |

**Total: ~10–20 minutos na primeira execução.**

---

## 🔄 Se algo falhar no meio

O bootstrap pode ser retomado de qualquer passo:

```bash
python bootstrap.py --step 5   # retoma a partir do passo 5
python bootstrap.py --check    # verifica o que está funcionando
```

---

## 📥 Ingestão completa (após validar o piloto)

Quando o piloto (SP/2024) funcionar e o dashboard carregar dados, rode a ingestão completa:

```bash
make ingest-full
# ou:
python -m ingestion.ingest_sia_pa --all
```

> ⏱️ **Estimativa:** 2–4 horas para todos os 27 estados × 2020–2024.
> O processo é incremental — se cair no meio, retoma de onde parou.

---

## 🚀 Comandos do dia a dia

```bash
make api           # Inicia a API FastAPI (porta 8000)
make dashboard     # Abre o Streamlit (porta 8501)
make all           # API + Dashboard juntos
make check         # Verifica se tudo está OK
make dbt-build     # Reconstrói os marts
make redis-up      # Sobe o Redis
```

---

## 🌐 URLs após o setup

| Serviço | URL |
|---------|-----|
| Dashboard | http://localhost:8501 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Redis (opcional) | http://localhost:8081 |

---

## ❓ Dúvidas frequentes

**"Docker não está instalado"**
Instale em https://docs.docker.com/get-docker/ — necessário apenas para o Redis.
Alternativa: `sudo apt install redis-server` (Linux) ou `brew install redis` (Mac).

**"Erro de conexão com o Supabase"**
Verifique se substituiu `[YOUR-PASSWORD]` na URL e se o projeto do Supabase está ativo.

**"dbt build falhou"**
Execute `cd dbt && dbt debug` para diagnosticar. Provavelmente é um problema de conexão.

**"O FTP do DataSUS está instável"**
Normal — o DataSUS tem quedas frequentes. Tente novamente com `make ingest-pilot`.
