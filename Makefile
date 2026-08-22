# ============================================================
# saude-publica-br — Makefile
# ============================================================
# Comandos principais:
#   make setup          → Setup completo (primeira vez)
#   make dbt-build      → Reconstrói os marts
#   make check          → Verifica saúde de todos os componentes
#
# Os alvos de API, dashboard Streamlit e Redis saíram junto com a stack
# legada — ver archive/README.md. O site publica por deploy-site.yml.
# Os alvos de ingestão saíram em 2026-08-22 com archive/ingestion/.
# ============================================================

PYTHON     := python3
PIP        := $(PYTHON) -m pip
DBT        := dbt
ROOT       := .

.PHONY: help setup check install db-setup dbt-build \
        test lint format clean

# ── Default: mostra ajuda ─────────────────────────────────
help:
	@echo ""
	@echo "  saude-publica-br — Comandos disponíveis"
	@echo "  ─────────────────────────────────────────"
	@echo "  make setup          Setup completo (1ª vez)"
	@echo "  make check          Verifica todos os componentes"
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

# ── Ingestão ─────────────────────────────────────────────
# Os alvos refs, ingest-pilot, ingest-sp, ingest-full e ingest-uf saíram em
# 2026-08-22 junto com ingestion/ingest_*.py e ingestion/refs_loader.py, hoje em
# archive/ingestion/ — ver o README de lá. Miravam o SIA, fonte fora do pipeline
# atual, e populavam tabelas que não existem em migrations/.
#
# Quem ingere hoje são os pipelines de scripts/ (SIM, SINAN, SIH, SINASC, CNES,
# SIOPS), rodados direto: `python scripts/pipeline_v2.py`.

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
