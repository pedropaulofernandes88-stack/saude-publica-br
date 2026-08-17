# ============================================================
# saude-publica-br — Makefile
# ============================================================
# Comandos principais:
#   make setup          → Setup completo (primeira vez)
#   make ingest-pilot   → Ingestão piloto (SP 2024, ~5 min)
#   make ingest-full    → Ingestão completa (todos estados 2020-2024)
#   make dbt-build      → Reconstrói os marts
#   make check          → Verifica saúde de todos os componentes
#
# Os alvos de API, dashboard Streamlit e Redis saíram junto com a stack
# legada — ver archive/README.md. O site publica por deploy-site.yml.
# ============================================================

PYTHON     := python3
PIP        := $(PYTHON) -m pip
DBT        := dbt
ROOT       := .

.PHONY: help setup check install db-setup refs \
        ingest-pilot ingest-full dbt-build \
        test lint format clean

# ── Default: mostra ajuda ─────────────────────────────────
help:
	@echo ""
	@echo "  saude-publica-br — Comandos disponíveis"
	@echo "  ─────────────────────────────────────────"
	@echo "  make setup          Setup completo (1ª vez)"
	@echo "  make check          Verifica todos os componentes"
	@echo "  make ingest-pilot   Ingestão: SP, Jan-Mar 2024"
	@echo "  make ingest-full    Ingestão: todos estados 2020-2024"
	@echo "  make dbt-build      Reconstrói todos os marts"
	@echo "  make test           Roda testes"
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

# ── Testes ───────────────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-fast:
	$(PYTHON) -m pytest tests/ -v -m "not slow"

# ── Qualidade de código ───────────────────────────────────
lint:
	$(PYTHON) -m ruff check . --fix

format:
	$(PYTHON) -m ruff format .

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

.PHONY: deploy
deploy: ## Publicar: push em main dispara deploy-site.yml
	@git push origin main

.PHONY: open
open: ## Abrir o site no browser
	@open https://saudeemdado.com
