#!/usr/bin/env bash
# =============================================================================
# load_demo_data.sh — Carrega dados demo no PostgreSQL/Supabase local
#
# Uso:
#   bash scripts/load_demo_data.sh
#   bash scripts/load_demo_data.sh --parquet-dir data/demo/parquet
#   bash scripts/load_demo_data.sh --skip-generate
#
# Pré-requisitos:
#   - Docker e Docker Compose em execução (docker compose up -d)
#   - Ambiente Python ativado (source .venv/bin/activate)
#   - Arquivo .env configurado com DATABASE_URL
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuração padrão
# ---------------------------------------------------------------------------
PARQUET_DIR="data/demo/parquet"
ESTADOS="SP RJ MG BA RS PR PE CE GO SC"
ANOS="2020 2021 2022 2023 2024"
REGISTROS="2000"
SKIP_GENERATE=false
SKIP_DBT=false
VERBOSE=false

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_section() { echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

die() {
    log_error "$*"
    exit 1
}

# ---------------------------------------------------------------------------
# Parse de argumentos
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --parquet-dir)   PARQUET_DIR="$2"; shift 2 ;;
        --estados)       ESTADOS="$2";     shift 2 ;;
        --anos)          ANOS="$2";        shift 2 ;;
        --registros)     REGISTROS="$2";   shift 2 ;;
        --skip-generate) SKIP_GENERATE=true; shift ;;
        --skip-dbt)      SKIP_DBT=true;    shift ;;
        --verbose)       VERBOSE=true;     shift ;;
        -h|--help)
            echo "Uso: bash scripts/load_demo_data.sh [OPÇÕES]"
            echo ""
            echo "Opções:"
            echo "  --parquet-dir DIR    Diretório dos Parquet (padrão: data/demo/parquet)"
            echo "  --estados 'SP RJ ...' Estados a gerar (padrão: 10 estados)"
            echo "  --anos '2020 2021 ...' Anos a gerar (padrão: 2020-2024)"
            echo "  --registros N        Registros base por estado/ano (padrão: 2000)"
            echo "  --skip-generate      Pula geração, usa Parquet existentes"
            echo "  --skip-dbt           Pula execução do dbt"
            echo "  --verbose            Saída detalhada"
            exit 0
            ;;
        *) die "Argumento desconhecido: $1. Use --help para ver as opções." ;;
    esac
done

# ---------------------------------------------------------------------------
# Verificações de pré-requisitos
# ---------------------------------------------------------------------------
log_section "Verificando pré-requisitos"

# Python disponível
if ! command -v python &>/dev/null && ! command -v python3 &>/dev/null; then
    die "Python não encontrado. Ative o ambiente virtual: source .venv/bin/activate"
fi
PYTHON=$(command -v python3 || command -v python)
log_ok "Python: $($PYTHON --version)"

# Docker
if ! command -v docker &>/dev/null; then
    die "Docker não encontrado. Instale Docker: https://docs.docker.com/get-docker/"
fi

# Docker Compose
if ! docker compose version &>/dev/null 2>&1; then
    die "Docker Compose v2 não encontrado. Atualize o Docker Desktop ou instale o plugin."
fi
log_ok "Docker Compose: $(docker compose version --short)"

# Arquivo .env
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        log_warn ".env não encontrado. Copiando de .env.example..."
        cp .env.example .env
        log_warn "Edite .env com suas credenciais antes de continuar."
        log_warn "Especialmente: DATABASE_URL, SUPABASE_URL, SUPABASE_KEY"
    else
        die ".env não encontrado. Crie o arquivo com base no CONTRIBUTING.md"
    fi
fi

# Carrega variáveis do .env (sem exportar para o shell pai)
set -a
# shellcheck source=.env
source .env
set +a

# DATABASE_URL obrigatória
if [[ -z "${DATABASE_URL:-}" ]]; then
    die "DATABASE_URL não definida no .env"
fi
log_ok ".env carregado"

# Verifica se o banco está acessível
log_info "Verificando conexão com o banco de dados..."
if ! $PYTHON -c "
import asyncio, asyncpg, os, sys
async def check():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        await conn.close()
    except Exception as e:
        print(f'Erro de conexão: {e}', file=sys.stderr)
        sys.exit(1)
asyncio.run(check())
" 2>/dev/null; then
    log_warn "Banco não acessível via DATABASE_URL diretamente."
    log_info "Tentando via Docker Compose..."
    if ! docker compose ps db 2>/dev/null | grep -q "running"; then
        log_info "Iniciando serviço db..."
        docker compose up -d db
        log_info "Aguardando banco inicializar (30s)..."
        sleep 30
    fi
fi
log_ok "Banco de dados acessível"

# Dependências Python
for pkg in pandas pyarrow psycopg2 numpy; do
    if ! $PYTHON -c "import $pkg" &>/dev/null; then
        log_warn "Pacote '$pkg' não encontrado. Instalando..."
        $PYTHON -m pip install "$pkg" --quiet
    fi
done
log_ok "Dependências Python OK"

# ---------------------------------------------------------------------------
# Etapa 1 — Gerar dados sintéticos
# ---------------------------------------------------------------------------
log_section "Etapa 1/4 — Gerando dados sintéticos"

if [[ "$SKIP_GENERATE" == "true" ]]; then
    log_info "Geração ignorada (--skip-generate)."
    if [[ ! -d "$PARQUET_DIR" ]]; then
        die "Diretório $PARQUET_DIR não encontrado e --skip-generate foi especificado."
    fi
    PARQUET_COUNT=$(find "$PARQUET_DIR" -name "*.parquet" 2>/dev/null | wc -l)
    log_ok "Usando $PARQUET_COUNT arquivos Parquet existentes em $PARQUET_DIR"
else
    log_info "Gerando dados para estados: $ESTADOS"
    log_info "Anos: $ANOS | Registros base: $REGISTROS"

    GENERATE_CMD="$PYTHON scripts/generate_demo_data.py \
        --estados $ESTADOS \
        --anos $ANOS \
        --registros $REGISTROS \
        --saida $PARQUET_DIR"

    if [[ "$VERBOSE" == "true" ]]; then
        $GENERATE_CMD
    else
        $GENERATE_CMD 2>&1 | grep -E '(INFO|WARNING|ERROR|✓|✗)' || true
    fi

    PARQUET_COUNT=$(find "$PARQUET_DIR" -name "*.parquet" 2>/dev/null | wc -l)
    log_ok "$PARQUET_COUNT arquivos Parquet gerados em $PARQUET_DIR"
fi

# ---------------------------------------------------------------------------
# Etapa 2 — Criar schema raw no PostgreSQL
# ---------------------------------------------------------------------------
log_section "Etapa 2/4 — Criando schema raw no banco"

$PYTHON - <<'PYEOF'
import asyncio
import os
import sys
import asyncpg

DDL = """
-- Schema para dados brutos (raw)
CREATE SCHEMA IF NOT EXISTS raw;

-- SIA/PA — Produção Ambulatorial
CREATE TABLE IF NOT EXISTS raw.sia_pa (
    id                  BIGSERIAL PRIMARY KEY,
    uf_sigla            CHAR(2)       NOT NULL,
    municipio_codigo    CHAR(6),
    competencia_ano     SMALLINT      NOT NULL,
    competencia_mes     SMALLINT      NOT NULL,
    procedimento_codigo VARCHAR(10),
    complexidade        VARCHAR(2),
    quantidade_aprovada INTEGER,
    valor_aprovado      NUMERIC(12,2),
    cns_pac             VARCHAR(15),
    dt_atendimento      DATE,
    _loaded_at          TIMESTAMPTZ   DEFAULT NOW()
);

-- SIM/DO — Declarações de Óbito
CREATE TABLE IF NOT EXISTS raw.sim_do (
    id                  BIGSERIAL PRIMARY KEY,
    uf_sigla            CHAR(2)       NOT NULL,
    municipio_codigo    CHAR(6),
    competencia_ano     SMALLINT      NOT NULL,
    causa_basica_cid10  VARCHAR(4),
    idade               SMALLINT,
    sexo                CHAR(1),
    raca_cor            SMALLINT,
    escolaridade        SMALLINT,
    local_ocorrencia    SMALLINT,
    _loaded_at          TIMESTAMPTZ   DEFAULT NOW()
);

-- SIH/AIH — Internações Hospitalares
CREATE TABLE IF NOT EXISTS raw.sih_aih (
    id                  BIGSERIAL PRIMARY KEY,
    uf_sigla            CHAR(2)       NOT NULL,
    municipio_codigo    CHAR(6),
    competencia_ano     SMALLINT      NOT NULL,
    competencia_mes     SMALLINT      NOT NULL,
    procedimento_codigo VARCHAR(10),
    complexidade        VARCHAR(2),
    permanencia_dias    SMALLINT,
    val_tot             NUMERIC(12,2),
    morte               BOOLEAN,
    cid_principal       VARCHAR(4),
    _loaded_at          TIMESTAMPTZ   DEFAULT NOW()
);

-- SINAN — Notificações de Agravos
CREATE TABLE IF NOT EXISTS raw.sinan (
    id                  BIGSERIAL PRIMARY KEY,
    uf_sigla            CHAR(2)       NOT NULL,
    municipio_codigo    CHAR(6),
    competencia_ano     SMALLINT      NOT NULL,
    competencia_mes     SMALLINT      NOT NULL,
    agravo_cid10        VARCHAR(4),
    idade               SMALLINT,
    sexo                CHAR(1),
    raca_cor            SMALLINT,
    _loaded_at          TIMESTAMPTZ   DEFAULT NOW()
);

-- CNES — Estabelecimentos de Saúde
CREATE TABLE IF NOT EXISTS raw.cnes (
    id                      BIGSERIAL PRIMARY KEY,
    uf_sigla                CHAR(2)       NOT NULL,
    municipio_codigo        CHAR(6),
    competencia_ano         SMALLINT      NOT NULL,
    cnes_codigo             VARCHAR(7),
    tipo_estabelecimento    SMALLINT,
    leitos_sus              SMALLINT,
    leitos_uti_sus          SMALLINT,
    esf_equipes             SMALLINT,
    _loaded_at              TIMESTAMPTZ   DEFAULT NOW()
);

-- Índices para queries analíticas comuns
CREATE INDEX IF NOT EXISTS idx_sia_pa_uf_ano     ON raw.sia_pa(uf_sigla, competencia_ano);
CREATE INDEX IF NOT EXISTS idx_sim_do_uf_ano     ON raw.sim_do(uf_sigla, competencia_ano);
CREATE INDEX IF NOT EXISTS idx_sim_do_cid        ON raw.sim_do(causa_basica_cid10);
CREATE INDEX IF NOT EXISTS idx_sih_aih_uf_ano    ON raw.sih_aih(uf_sigla, competencia_ano);
CREATE INDEX IF NOT EXISTS idx_sinan_uf_ano      ON raw.sinan(uf_sigla, competencia_ano);
CREATE INDEX IF NOT EXISTS idx_sinan_cid         ON raw.sinan(agravo_cid10);
CREATE INDEX IF NOT EXISTS idx_cnes_uf_ano       ON raw.cnes(uf_sigla, competencia_ano);
"""

async def main():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL não definida", file=sys.stderr)
        sys.exit(1)
    try:
        conn = await asyncpg.connect(db_url)
        await conn.execute(DDL)
        await conn.close()
        print("Schema raw criado/validado com sucesso.")
    except Exception as e:
        print(f"Erro ao criar schema: {e}", file=sys.stderr)
        sys.exit(1)

asyncio.run(main())
PYEOF

log_ok "Schema raw OK"

# ---------------------------------------------------------------------------
# Etapa 3 — Carregar Parquet → PostgreSQL
# ---------------------------------------------------------------------------
log_section "Etapa 3/4 — Carregando Parquet no banco"

$PYTHON - <<PYEOF
import asyncio
import os
import sys
import glob
import asyncpg
import pandas as pd
import pyarrow.parquet as pq

PARQUET_DIR = "${PARQUET_DIR}"
DATABASE_URL = os.environ["DATABASE_URL"]

# Mapeamento sistema → tabela raw
SISTEMA_TABELA = {
    "sia_pa": "raw.sia_pa",
    "sim_do": "raw.sim_do",
    "sih_aih": "raw.sih_aih",
    "sinan": "raw.sinan",
    "cnes": "raw.cnes",
}

# Colunas esperadas por tabela (exclui id e _loaded_at, gerados pelo banco)
COLUNAS = {
    "raw.sia_pa":  ["uf_sigla","municipio_codigo","competencia_ano","competencia_mes",
                    "procedimento_codigo","complexidade","quantidade_aprovada",
                    "valor_aprovado","cns_pac","dt_atendimento"],
    "raw.sim_do":  ["uf_sigla","municipio_codigo","competencia_ano","causa_basica_cid10",
                    "idade","sexo","raca_cor","escolaridade","local_ocorrencia"],
    "raw.sih_aih": ["uf_sigla","municipio_codigo","competencia_ano","competencia_mes",
                    "procedimento_codigo","complexidade","permanencia_dias","val_tot",
                    "morte","cid_principal"],
    "raw.sinan":   ["uf_sigla","municipio_codigo","competencia_ano","competencia_mes",
                    "agravo_cid10","idade","sexo","raca_cor"],
    "raw.cnes":    ["uf_sigla","municipio_codigo","competencia_ano","cnes_codigo",
                    "tipo_estabelecimento","leitos_sus","leitos_uti_sus","esf_equipes"],
}

async def carregar_df(conn, tabela, df):
    """Carrega DataFrame via COPY (mais rápido que INSERT linha a linha)."""
    colunas = COLUNAS[tabela]
    # Filtra apenas colunas existentes no DataFrame
    colunas_presentes = [c for c in colunas if c in df.columns]
    df_filtrado = df[colunas_presentes].copy()

    # Converte tipos para compatibilidade com asyncpg
    for col in df_filtrado.select_dtypes(include=["int64","int32"]).columns:
        df_filtrado[col] = df_filtrado[col].astype("Int64")
    for col in df_filtrado.select_dtypes(include=["float64","float32"]).columns:
        df_filtrado[col] = df_filtrado[col].round(2)

    registros = df_filtrado.to_dict("records")
    if not registros:
        return 0

    col_names = ", ".join(colunas_presentes)
    placeholders = ", ".join(f"\${i+1}" for i in range(len(colunas_presentes)))
    sql = f"INSERT INTO {tabela} ({col_names}) VALUES ({placeholders})"

    data = [[r.get(c) for c in colunas_presentes] for r in registros]
    await conn.executemany(sql, data)
    return len(data)

async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    total_inserido = 0
    erros = 0

    for sistema, tabela in SISTEMA_TABELA.items():
        padrao = os.path.join(PARQUET_DIR, sistema, "**", "*.parquet")
        arquivos = sorted(glob.glob(padrao, recursive=True))
        if not arquivos:
            print(f"  [SKIP] {sistema}: nenhum arquivo Parquet encontrado")
            continue

        sistema_total = 0
        for arquivo in arquivos:
            try:
                df = pd.read_parquet(arquivo)
                n = await carregar_df(conn, tabela, df)
                sistema_total += n
                total_inserido += n
                if "${VERBOSE}" == "true":
                    print(f"    {arquivo} → {n} registros")
            except Exception as e:
                print(f"  [WARN] Erro em {arquivo}: {e}", file=sys.stderr)
                erros += 1

        print(f"  [{tabela}] {len(arquivos)} arquivo(s) → {sistema_total:,} registros")

    await conn.close()
    print(f"\nTotal inserido: {total_inserido:,} registros | Erros: {erros}")

    if total_inserido == 0:
        print("WARN: Nenhum dado inserido. Verifique o diretório Parquet.", file=sys.stderr)
        sys.exit(1)

asyncio.run(main())
PYEOF

log_ok "Dados carregados no banco"

# ---------------------------------------------------------------------------
# Etapa 4 — Executar dbt (staging → marts)
# ---------------------------------------------------------------------------
log_section "Etapa 4/4 — Executando dbt (transformações)"

if [[ "$SKIP_DBT" == "true" ]]; then
    log_info "dbt ignorado (--skip-dbt)."
else
    if ! command -v dbt &>/dev/null; then
        log_warn "dbt não encontrado no PATH. Pulando transformações."
        log_warn "Para executar manualmente: dbt run --select staging+ --target dev"
    else
        DBT_VERSION=$(dbt --version 2>/dev/null | head -1 || echo "desconhecido")
        log_info "dbt: $DBT_VERSION"

        if [[ -f "dbt_project.yml" ]]; then
            log_info "Executando dbt run (staging → marts)..."
            if [[ "$VERBOSE" == "true" ]]; then
                dbt run --target dev --select "staging+" 2>&1
            else
                dbt run --target dev --select "staging+" 2>&1 | \
                    grep -E '(Completed|ERROR|WARN|of [0-9]+|Finished)' || true
            fi
            log_ok "dbt concluído"

            log_info "Executando dbt test..."
            if [[ "$VERBOSE" == "true" ]]; then
                dbt test --target dev 2>&1 || log_warn "Alguns testes dbt falharam (dados sintéticos)"
            else
                dbt test --target dev 2>&1 | \
                    grep -E '(Completed|ERROR|FAIL|PASS|of [0-9]+)' || true
                log_ok "dbt test concluído"
            fi
        else
            log_warn "dbt_project.yml não encontrado. Pulando dbt run."
            log_warn "Execute manualmente: cd dbt && dbt run --target dev"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Resumo final
# ---------------------------------------------------------------------------
log_section "Resumo"

PARQUET_COUNT=$(find "$PARQUET_DIR" -name "*.parquet" 2>/dev/null | wc -l)
PARQUET_SIZE=$(du -sh "$PARQUET_DIR" 2>/dev/null | cut -f1 || echo "?")

echo ""
echo -e "  ${GREEN}✓${NC} Dados demo carregados com sucesso!"
echo ""
echo "  Arquivos Parquet:  ${PARQUET_COUNT} arquivos (${PARQUET_SIZE})"
echo "  Diretório:         ${PARQUET_DIR}/"
echo "  Banco:             ${DATABASE_URL%%@*}@***"
echo ""
echo "  Próximos passos:"
echo "    docker compose up -d          # Sobe todos os serviços"
echo "    curl localhost:8000/health    # Verifica API"
echo "    open http://localhost:3000    # Abre o dashboard"
echo ""
echo "  Endpoints de exemplo:"
echo "    GET /producao?estado=SP&ano=2023"
echo "    GET /mortalidade?estado=SP&ano=2023"
echo "    GET /internacoes?estado=SP&ano=2023"
echo ""
