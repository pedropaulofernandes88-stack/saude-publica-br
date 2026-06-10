# ============================================================
# saude-publica-br — Makefile
# ============================================================
# Comandos principais:
#   make setup          → Setup completo (primeira vez)
#   make api            → Inicia API FastAPI
#   make dashboard      → Abre dashboard Streamlit
#   make all            → API + Dashboard juntos
#   make ingest-pilot   → Ingestão piloto (SP 2024, ~5 min)
#   make ingest-full    → Ingestão completa (todos estados 2020-2024)
#   make check          → Verifica saúde de todos os componentes
# ============================================================

PYTHON     := python3
PIP        := $(PYTHON) -m pip
UVICORN    := $(PYTHON) -m uvicorn
STREAMLIT  := $(PYTHON) -m streamlit
DBT        := dbt
ROOT       := .
API_PORT   := 8000
DASH_PORT  := 8501

.PHONY: help setup check install redis-up redis-down db-setup refs \
        ingest-pilot ingest-full dbt-build api dashboard all \
        test lint format clean logs

# ── Default: mostra ajuda ─────────────────────────────────
help:
	@echo ""
	@echo "  saude-publica-br — Comandos disponíveis"
	@echo "  ─────────────────────────────────────────"
	@echo "  make setup          Setup completo (1ª vez)"
	@echo "  make check          Verifica todos os componentes"
	@echo "  make api            Inicia API FastAPI (porta $(API_PORT))"
	@echo "  make dashboard      Abre Streamlit (porta $(DASH_PORT))"
	@echo "  make all            API + Dashboard juntos"
	@echo "  make ingest-pilot   Ingestão: SP, Jan-Mar 2024"
	@echo "  make ingest-full    Ingestão: todos estados 2020-2024"
	@echo "  make dbt-build      Reconstrói todos os marts"
	@echo "  make redis-up       Sobe Redis via Docker"
	@echo "  make redis-down     Para Redis"
	@echo "  make test           Roda testes"
	@echo "  make logs           Mostra logs da API"
	@echo "  make clean          Remove arquivos temporários"
	@echo ""

# ── Setup completo ────────────────────────────────────────
setup:
	@echo "🚀 Iniciando setup automatizado..."
	$(PYTHON) bootstrap.py

# ── Health check ─────────────────────────────────────────
check:
	$(PYTHON) bootstrap.py --check

# ── Dependências ─────────────────────────────────────────
install:
	$(PIP) install -r requirements.txt

# ── Redis ────────────────────────────────────────────────
redis-up:
	docker compose up -d redis
	@echo "✅ Redis rodando em localhost:6379"

redis-down:
	docker compose down redis

redis-ui:
	docker compose --profile debug up -d redis-commander
	@echo "✅ Redis Commander em http://localhost:8081"

# ── Banco de dados ───────────────────────────────────────
db-setup:
	$(PYTHON) bootstrap.py --step 5

refs:
	$(PYTHON) ingestion/refs_loader.py

# ── Ingestão ─────────────────────────────────────────────
ingest-pilot:
	@echo "📥 Ingestão piloto: SP, Jan-Mar 2024..."
	$(PYTHON) -m ingestion.ingest_sia_pa --estados SP --anos 2024 --meses 1 2 3

ingest-sp:
	@echo "📥 Ingestão SP completa: 2020-2024..."
	$(PYTHON) -m ingestion.ingest_sia_pa --estados SP --anos 2020 2021 2022 2023 2024

ingest-full:
	@echo "📥 Ingestão completa: todos estados 2020-2024..."
	@echo "⏱  Estimativa: 2-4 horas dependendo da conexão"
	$(PYTHON) -m ingestion.ingest_sia_pa --all

ingest-uf:
	@echo "Uso: make ingest-uf UF=RJ ANO=2023"
	$(PYTHON) -m ingestion.ingest_sia_pa --estados $(UF) --anos $(ANO)

# ── dbt ──────────────────────────────────────────────────
dbt-build:
	cd dbt && $(DBT) build

dbt-run:
	cd dbt && $(DBT) run

dbt-test:
	cd dbt && $(DBT) test

dbt-docs:
	cd dbt && $(DBT) docs generate && $(DBT) docs serve

# ── API ──────────────────────────────────────────────────
api:
	@echo "🚀 API FastAPI em http://localhost:$(API_PORT)"
	@echo "   Docs: http://localhost:$(API_PORT)/docs"
	$(UVICORN) api.main:app --host 0.0.0.0 --port $(API_PORT) --reload

api-prod:
	$(UVICORN) api.main:app --host 0.0.0.0 --port $(API_PORT) --workers 4

# ── Dashboard ────────────────────────────────────────────
dashboard:
	@echo "📊 Streamlit em http://localhost:$(DASH_PORT)"
	$(STREAMLIT) run dashboard/app.py --server.port $(DASH_PORT)

# ── Tudo junto ───────────────────────────────────────────
all: redis-up
	@echo "🚀 Iniciando API + Dashboard..."
	$(UVICORN) api.main:app --host 0.0.0.0 --port $(API_PORT) --reload &
	sleep 3
	$(STREAMLIT) run dashboard/app.py --server.port $(DASH_PORT)

# ── Testes ───────────────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-api:
	$(PYTHON) -m pytest tests/test_api/ -v

test-fast:
	$(PYTHON) -m pytest tests/ -v -m "not slow"

# ── Qualidade de código ───────────────────────────────────
lint:
	$(PYTHON) -m ruff check . --fix

format:
	$(PYTHON) -m ruff format .

# ── Logs ─────────────────────────────────────────────────
logs:
	tail -f api.log 2>/dev/null || echo "api.log não encontrado. API rodando?"

logs-docker:
	docker logs saude_redis -f

# ── Limpeza ──────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	find . -name ".DS_Store" -delete 2>/dev/null; true
	@echo "✅ Limpeza concluída"

clean-data:
	@echo "⚠️  Remove dados locais (Parquet). Supabase não é afetado."
	rm -rf data/staging/ data/intermediate/
	@echo "✅ Dados locais removidos"

# ── Utilitários ──────────────────────────────────────────
env-example:
	cp .env.example .env
	@echo "✅ .env criado a partir de .env.example"

status:
	$(PYTHON) bootstrap.py --check


# ── Deploy ────────────────────────────────────────────────────────────────

.PHONY: publish
publish: ## Publicar saudeemdado.com do zero (Railway + Vercel + Supabase)
	@chmod +x deploy/bootstrap.sh && ./deploy/bootstrap.sh

.PHONY: deploy
deploy: ## Fazer push e disparar deploy manual
	@git add -A && git commit -m "deploy: $(shell date +%Y-%m-%d)" --allow-empty
	@git push origin main
	@gh workflow run deploy.yml
	@echo "✅ Deploy disparado — acompanhe em: gh run list"

.PHONY: logs
logs: ## Ver logs da API no Railway
	@railway logs --service api

.PHONY: open
open: ## Abrir o site no browser
	@open https://saudeemdado.com
