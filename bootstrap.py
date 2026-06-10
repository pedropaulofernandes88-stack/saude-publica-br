#!/usr/bin/env python3
"""
bootstrap.py — Setup automatizado do saude-publica-br
=====================================================
O que este script faz (sem pedir nada além do básico):
  1.  Verifica Python e dependências essenciais
  2.  Instala todos os pacotes via pip
  3.  Cria e valida o arquivo .env
  4.  Sobe o Redis via Docker Compose
  5.  Cria as tabelas no Supabase (executa setup_supabase.sql)
  6.  Carrega tabelas de referência (municipios, CID-10)
  7.  Executa ingestão piloto: SP, Jan-Mar/2024 (~3 min)
  8.  Roda dbt build (cria todos os marts)
  9.  Valida todos os marts com Great Expectations
  10. Inicia a API FastAPI em background
  11. Abre o dashboard Streamlit no navegador

Uso:
  python bootstrap.py           # Setup completo
  python bootstrap.py --step 5  # Retomar a partir do passo 5
  python bootstrap.py --check   # Só verifica se tudo está OK
"""

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# ── rich é instalado no passo 2; antes disso, fallback simples ──
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    from rich import print as rprint
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    class Console:
        def print(self, *a, **kw): print(*a)
        def rule(self, *a, **kw): print("─" * 60)
    console = Console()
    def rprint(*a, **kw): print(*a)

ROOT = Path(__file__).parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def ok(msg: str):
    rprint(f"  [green]✅ {msg}[/green]" if RICH else f"  ✅ {msg}")

def warn(msg: str):
    rprint(f"  [yellow]⚠️  {msg}[/yellow]" if RICH else f"  ⚠️  {msg}")

def err(msg: str):
    rprint(f"  [red]❌ {msg}[/red]" if RICH else f"  ❌ {msg}")

def info(msg: str):
    rprint(f"  [cyan]ℹ  {msg}[/cyan]" if RICH else f"  ℹ  {msg}")

def step_header(n: int, title: str):
    if RICH:
        console.rule(f"[bold blue]Passo {n}/11 — {title}[/bold blue]")
    else:
        print(f"\n{'='*60}\nPasso {n}/11 — {title}\n{'='*60}")

def run(cmd: str, capture: bool = False, cwd: Path | None = None) -> subprocess.CompletedProcess:
    kwargs = dict(shell=True, cwd=str(cwd or ROOT))
    if capture:
        kwargs |= dict(capture_output=True, text=True)
    return subprocess.run(cmd, **kwargs)

def run_ok(cmd: str, cwd: Path | None = None) -> bool:
    result = run(cmd, capture=True, cwd=cwd)
    return result.returncode == 0

def abort(msg: str):
    err(msg)
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
# Passo 1 — Verificar Python
# ═══════════════════════════════════════════════════════════

def step1_check_python():
    step_header(1, "Verificando Python")
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        abort(f"Python 3.11+ necessário. Você tem {major}.{minor}.")
    ok(f"Python {major}.{minor} OK")

    # Docker
    if run_ok("docker --version"):
        ok("Docker encontrado")
    else:
        warn("Docker não encontrado — Redis precisará ser instalado manualmente.")
        warn("Instale em: https://docs.docker.com/get-docker/")

# ═══════════════════════════════════════════════════════════
# Passo 2 — Instalar dependências
# ═══════════════════════════════════════════════════════════

def step2_install_deps():
    step_header(2, "Instalando dependências Python")
    req = ROOT / "requirements.txt"
    if not req.exists():
        abort("requirements.txt não encontrado. Execute a partir da raiz do projeto.")

    info("Isso pode levar 2-5 minutos na primeira vez...")
    result = run(f'"{sys.executable}" -m pip install -r requirements.txt --quiet --no-warn-script-location')
    if result.returncode != 0:
        abort("Falha ao instalar dependências. Verifique sua conexão e tente novamente.")
    ok("Todas as dependências instaladas")

    # Agora importa rich se disponível
    global RICH, console, rprint
    try:
        from rich.console import Console as C
        from rich import print as rp
        RICH = True
        console = C()
        rprint = rp
        ok("rich ativado — output colorido habilitado")
    except ImportError:
        pass

# ═══════════════════════════════════════════════════════════
# Passo 3 — Configurar .env
# ═══════════════════════════════════════════════════════════

def step3_configure_env():
    step_header(3, "Configurando variáveis de ambiente (.env)")

    # Cria .env a partir do .env.example se não existir
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            import shutil
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
            info(f".env criado a partir de .env.example")
        else:
            _create_minimal_env()
            info(".env minimal criado")

    # Lê o .env atual
    env_vars = _read_env()

    # Verifica DATABASE_URL (obrigatório)
    db_url = env_vars.get("DATABASE_URL", "")
    if not db_url or "xxxx" in db_url or "SEU_" in db_url:
        _guide_supabase_setup()
        if RICH:
            db_url = Prompt.ask(
                "\n  [bold yellow]Cole aqui o DATABASE_URL do Supabase[/bold yellow]"
            ).strip()
        else:
            db_url = input("\n  Cole aqui o DATABASE_URL do Supabase: ").strip()

        if not db_url.startswith("postgresql://"):
            abort("DATABASE_URL inválida. Deve começar com postgresql://")
        _update_env("DATABASE_URL", db_url)
        ok("DATABASE_URL salva no .env")
    else:
        ok(f"DATABASE_URL já configurada: {db_url[:40]}...")

    # Verifica REDIS_URL (tem default OK)
    redis_url = env_vars.get("REDIS_URL", "redis://localhost:6379/0")
    if not env_vars.get("REDIS_URL"):
        _update_env("REDIS_URL", redis_url)
        info(f"REDIS_URL definida como padrão: {redis_url}")
    else:
        ok(f"REDIS_URL: {redis_url}")

    # Confirma estados e período
    estados = env_vars.get("ESTADOS_INGESTAO", "AC,AL,AM,AP,BA,CE,DF,ES,GO,MA,MG,MS,MT,PA,PB,PE,PI,PR,RJ,RN,RO,RR,RS,SC,SE,SP,TO")
    if not env_vars.get("ESTADOS_INGESTAO"):
        _update_env("ESTADOS_INGESTAO", estados)

    for key, default in [("ANO_INICIO", "2020"), ("ANO_FIM", "2024"), ("DATA_DIR", "./data")]:
        if not env_vars.get(key):
            _update_env(key, default)

    ok(".env configurado com sucesso")

def _guide_supabase_setup():
    lines = [
        "",
        "  📋 COMO OBTER O DATABASE_URL DO SUPABASE:",
        "  ─────────────────────────────────────────",
        "  1. Acesse https://supabase.com e faça login (grátis)",
        "  2. Clique em 'New project'",
        "  3. Nome: saude-publica-br | Senha: (anote, não importa aqui)",
        "  4. Aguarde ~2 minutos o projeto subir",
        "  5. Vá em: Settings → Database → Connection string → URI",
        "  6. Copie a URL (começa com postgresql://postgres:...)",
        "  7. Substitua [YOUR-PASSWORD] pela senha que você definiu",
        "",
    ]
    for line in lines:
        print(line)

def _create_minimal_env():
    content = """# saude-publica-br — Variáveis de ambiente
# Gerado automaticamente por bootstrap.py

DATABASE_URL=postgresql://postgres:SENHA@db.PROJETO.supabase.co:5432/postgres
REDIS_URL=redis://localhost:6379/0
DATA_DIR=./data
ESTADOS_INGESTAO=AC,AL,AM,AP,BA,CE,DF,ES,GO,MA,MG,MS,MT,PA,PB,PE,PI,PR,RJ,RN,RO,RR,RS,SC,SE,SP,TO
ANO_INICIO=2020
ANO_FIM=2024
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
"""
    ENV_FILE.write_text(content, encoding="utf-8")

def _read_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def _update_env(key: str, value: str):
    content = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    lines = content.splitlines()
    new_line = f"{key}={value}"
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"# {key}="):
            lines[i] = new_line
            replaced = True
            break
    if not replaced:
        lines.append(new_line)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

# ═══════════════════════════════════════════════════════════
# Passo 4 — Subir Redis via Docker
# ═══════════════════════════════════════════════════════════

def step4_start_redis():
    step_header(4, "Iniciando Redis (Docker)")

    # Testa se Redis já está rodando
    if run_ok("redis-cli ping"):
        ok("Redis já está rodando")
        return

    if not run_ok("docker --version"):
        warn("Docker não encontrado. Redis não será iniciado automaticamente.")
        warn("Instale Docker ou Redis manualmente e execute novamente.")
        info("Continuando sem Redis (cache desabilitado)...")
        return

    info("Subindo Redis via docker compose...")
    result = run("docker compose up -d redis")
    if result.returncode != 0:
        warn("Falha ao subir Redis. Continuando sem cache...")
        return

    # Aguarda Redis ficar pronto
    for attempt in range(10):
        time.sleep(2)
        if run_ok("docker exec saude_redis redis-cli ping"):
            ok("Redis rodando em redis://localhost:6379")
            return
        info(f"Aguardando Redis... ({attempt + 1}/10)")

    warn("Redis pode não ter iniciado corretamente. Verifique com: docker logs saude_redis")

# ═══════════════════════════════════════════════════════════
# Passo 5 — Criar tabelas no Supabase
# ═══════════════════════════════════════════════════════════

def step5_setup_database():
    step_header(5, "Criando tabelas no Supabase")

    sql_file = ROOT / "ingestion" / "setup_supabase.sql"
    if not sql_file.exists():
        abort(f"Arquivo SQL não encontrado: {sql_file}")

    env_vars = _read_env()
    db_url = env_vars.get("DATABASE_URL", "")
    if not db_url:
        abort("DATABASE_URL não configurada. Execute novamente o bootstrap.")

    info("Conectando ao Supabase e criando schema...")

    try:
        import psycopg
        sql_content = sql_file.read_text(encoding="utf-8")

        with psycopg.connect(db_url, connect_timeout=30) as conn:
            with conn.cursor() as cur:
                # Remove comandos que precisam de superuser no Supabase
                safe_sql = _sanitize_sql_for_supabase(sql_content)
                cur.execute(safe_sql)
            conn.commit()

        ok("Schema criado: ingestion_log + sia_pa_raw + partições + índices")

    except ImportError:
        abort("psycopg não instalado. Execute: pip install psycopg[binary]")
    except Exception as e:
        err(f"Erro ao conectar ao banco: {e}")
        console.print()
        console.print(Panel(
            "[bold yellow]ALTERNATIVA: Execute o SQL diretamente no Supabase Dashboard[/bold yellow]\n\n"
            "1. Acesse: [link]https://supabase.com/dashboard/project/[PROJECT_REF]/sql/new[/link]\n"
            "   (substitua [PROJECT_REF] pelo ref do seu projeto)\n\n"
            "2. Copie todo o conteúdo de: [bold cyan]ingestion/setup_supabase.sql[/bold cyan]\n\n"
            "3. Cole no editor e clique [bold green]RUN[/bold green]\n\n"
            "4. Volte aqui e execute: [bold]python bootstrap.py --step 6[/bold]",
            title="📋 SQL Editor Fallback",
            border_style="yellow"
        ))
        import subprocess
        try:
            subprocess.run(["cat", str(sql_file)], check=True)
        except Exception:
            pass
        if RICH:
            if not Confirm.ask("\n  Já executou o SQL no dashboard? Continuar?", default=False):
                abort("Execute o SQL no Supabase SQL Editor e rode: python bootstrap.py --step 6")
        else:
            resp = input("  Já executou o SQL no dashboard? Continuar? (s/N): ").strip().lower()
            if resp != "s":
                abort("Execute o SQL no Supabase SQL Editor e rode: python bootstrap.py --step 6")

def _sanitize_sql_for_supabase(sql: str) -> str:
    """Remove comandos que exigem superuser no Supabase Cloud."""
    skip_prefixes = (
        "CREATE EXTENSION",
        "ALTER SYSTEM",
        "CREATE TABLESPACE",
    )
    lines = []
    skip_block = False
    for line in sql.splitlines():
        stripped = line.strip().upper()
        if any(stripped.startswith(p) for p in skip_prefixes):
            continue  # pula esta linha
        lines.append(line)
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════
# Passo 6 — Carregar tabelas de referência
# ═══════════════════════════════════════════════════════════

def step6_load_references():
    step_header(6, "Carregando tabelas de referência (municípios, CID-10)")

    refs_script = ROOT / "ingestion" / "refs_loader.py"
    if not refs_script.exists():
        warn("refs_loader.py não encontrado — criando script de referências...")
        _create_refs_loader()

    info("Carregando municípios IBGE e tabela CID-10...")
    result = run(f'"{sys.executable}" ingestion/refs_loader.py')
    if result.returncode != 0:
        warn("refs_loader falhou. Verifique os logs acima.")
        warn("As referências podem ser carregadas manualmente depois.")
    else:
        ok("Municípios e CID-10 carregados com sucesso")

def _create_refs_loader():
    """Cria um refs_loader.py básico se não existir."""
    script = ROOT / "ingestion" / "refs_loader.py"
    content = '''#!/usr/bin/env python3
"""Carrega tabelas de referência: municípios IBGE e CID-10."""
import os, sys
from pathlib import Path
import pandas as pd
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
DB_URL = os.environ["DATABASE_URL"]

CREATE_MUNICIPIOS = """
CREATE TABLE IF NOT EXISTS municipios_ibge (
    codigo_ibge  CHAR(7)     PRIMARY KEY,
    nome         TEXT        NOT NULL,
    uf_sigla     CHAR(2)     NOT NULL,
    uf_nome      TEXT        NOT NULL,
    regiao       TEXT        NOT NULL,
    populacao    INTEGER,
    area_km2     NUMERIC(12,2)
);
"""

CREATE_CID10 = """
CREATE TABLE IF NOT EXISTS cid10_capitulos (
    codigo_inicio CHAR(3)    NOT NULL,
    codigo_fim    CHAR(3)    NOT NULL,
    descricao     TEXT       NOT NULL,
    capitulo      SMALLINT   PRIMARY KEY
);
"""

CAPITULOS_CID10 = [
    (1,  "A00","B99","Doenças infecciosas e parasitárias"),
    (2,  "C00","D48","Neoplasias (tumores)"),
    (3,  "D50","D89","Doenças do sangue e imunidade"),
    (4,  "E00","E90","Doenças endócrinas e metabólicas"),
    (5,  "F00","F99","Transtornos mentais e comportamentais"),
    (6,  "G00","G99","Doenças do sistema nervoso"),
    (7,  "H00","H59","Doenças dos olhos"),
    (8,  "H60","H95","Doenças do ouvido"),
    (9,  "I00","I99","Doenças do aparelho circulatório"),
    (10, "J00","J99","Doenças do aparelho respiratório"),
    (11, "K00","K93","Doenças do aparelho digestivo"),
    (12, "L00","L99","Doenças da pele"),
    (13, "M00","M99","Doenças osteomusculares"),
    (14, "N00","N99","Doenças do aparelho geniturinário"),
    (15, "O00","O99","Gravidez, parto e puerpério"),
    (16, "P00","P96","Afecções perinatais"),
    (17, "Q00","Q99","Malformações congênitas"),
    (18, "R00","R99","Sinais e sintomas anormais"),
    (19, "S00","T98","Lesões e envenenamentos"),
    (20, "V01","Y98","Causas externas"),
    (21, "Z00","Z99","Contatos com serviços de saúde"),
]

def main():
    print("Conectando ao banco...")
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # Cria tabelas
            cur.execute(CREATE_MUNICIPIOS)
            cur.execute(CREATE_CID10)

            # Insere capítulos CID-10
            cur.executemany(
                "INSERT INTO cid10_capitulos VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                [(cap, ci, cf, desc) for cap, ci, cf, desc in CAPITULOS_CID10]
            )
            print(f"  ✅ {len(CAPITULOS_CID10)} capítulos CID-10 inseridos")

            # Municípios via IBGE API (pequeno dataset)
            try:
                import httpx
                print("  Baixando municípios do IBGE API...")
                r = httpx.get(
                    "https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
                    timeout=30
                )
                municipios = r.json()
                rows = [
                    (
                        str(m["id"]),
                        m["nome"],
                        m["microrregiao"]["mesorregiao"]["UF"]["sigla"],
                        m["microrregiao"]["mesorregiao"]["UF"]["nome"],
                        m["microrregiao"]["mesorregiao"]["UF"]["regiao"]["nome"],
                        None, None
                    )
                    for m in municipios
                ]
                cur.executemany(
                    """INSERT INTO municipios_ibge
                       (codigo_ibge, nome, uf_sigla, uf_nome, regiao, populacao, area_km2)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT DO NOTHING""",
                    rows
                )
                print(f"  ✅ {len(rows)} municípios inseridos")
            except Exception as e:
                print(f"  ⚠️  Falha ao baixar municípios: {e}")
                print("  Execute manualmente: python ingestion/refs_loader.py")

        conn.commit()
    print("✅ Referências carregadas com sucesso!")

if __name__ == "__main__":
    main()
'''
    script.write_text(content, encoding="utf-8")
    print(f"  ℹ  refs_loader.py criado em {script}")

# ═══════════════════════════════════════════════════════════
# Passo 7 — Ingestão piloto (SP, Jan-Mar 2024)
# ═══════════════════════════════════════════════════════════

def step7_pilot_ingestion():
    step_header(7, "Ingestão piloto — SP, Jan/Fev/Mar 2024")
    info("Baixando dados reais do DataSUS via PySUS (~3-8 min conforme conexão)...")
    info("Apenas SP + 3 meses para validar o pipeline rapidamente.")

    ingest_script = ROOT / "ingestion" / "ingest_sia_pa.py"
    if not ingest_script.exists():
        warn("ingest_sia_pa.py não encontrado. Pulando ingestão piloto.")
        warn("Execute manualmente depois: python -m ingestion.ingest_sia_pa --estados SP --anos 2024")
        return

    result = run(
        f'"{sys.executable}" -m ingestion.ingest_sia_pa '
        f'--estados SP --anos 2024 --meses 1 2 3'
    )
    if result.returncode != 0:
        warn("Ingestão piloto falhou.")
        warn("Possíveis causas: FTP DataSUS instável, sem conexão à internet.")
        warn("Tente mais tarde: python -m ingestion.ingest_sia_pa --estados SP --anos 2024")
    else:
        ok("Dados piloto carregados: SP Jan-Mar/2024")

# ═══════════════════════════════════════════════════════════
# Passo 8 — dbt build
# ═══════════════════════════════════════════════════════════

def step8_dbt_build():
    step_header(8, "Construindo marts com dbt")

    dbt_dir = ROOT / "dbt"
    if not dbt_dir.exists():
        warn("Diretório dbt/ não encontrado. Pulando dbt build.")
        return

    # Verifica se dbt está instalado
    if not run_ok("dbt --version"):
        warn("dbt não encontrado no PATH.")
        info("Tentando instalar: pip install dbt-postgres")
        run(f'"{sys.executable}" -m pip install dbt-postgres --quiet')

    info("Executando dbt deps + dbt build (staging → intermediate → marts)...")
    if not run_ok("dbt deps", cwd=dbt_dir):
        warn("dbt deps falhou — continuando mesmo assim.")

    result = run("dbt build --select +mart_producao_amb+", cwd=dbt_dir)
    if result.returncode != 0:
        warn("dbt build falhou. Verifique os logs acima.")
        warn("Execute manualmente: cd dbt && dbt build")
    else:
        ok("dbt build concluído — todos os marts criados")

# ═══════════════════════════════════════════════════════════
# Passo 9 — Validar marts com Great Expectations
# ═══════════════════════════════════════════════════════════

def step9_validate_marts():
    step_header(9, "Validando marts com Great Expectations")

    runner = ROOT / "validation" / "run_validations.py"
    if not runner.exists():
        warn("validation/run_validations.py não encontrado. Pulando validação.")
        warn("Execute manualmente: python -m validation.run_validations")
        return

    info("Executando suítes Great Expectations para todos os 7 marts...")
    info("(Isso pode levar ~30-60 s dependendo do volume de dados)")

    result = run(
        f'"{sys.executable}" -m validation.run_validations --fail-fast',
        cwd=ROOT,
    )

    if result.returncode == 0:
        ok("Todos os marts passaram na validação Great Expectations ✅")
    elif result.returncode == 1:
        warn("Uma ou mais suítes GX falharam. Verifique os detalhes acima.")
        warn("A instalação continuará, mas inspecione os dados antes de usar em produção.")
        warn("Para detalhes: python -m validation.run_validations --verbose")
    else:
        warn(f"Validação encerrou com código {result.returncode}. Continuando...")

# ═══════════════════════════════════════════════════════════
# Passo 10 — Iniciar API FastAPI
# ═══════════════════════════════════════════════════════════

def step10_start_api():
    step_header(10, "Iniciando API FastAPI")

    api_main = ROOT / "api" / "main.py"
    if not api_main.exists():
        warn("api/main.py não encontrado. Pulando inicialização da API.")
        return

    env_vars = _read_env()
    port = env_vars.get("API_PORT", "8000")

    info(f"Iniciando API em http://localhost:{port} (background)...")
    info("Logs da API em: api.log")

    # Inicia em background
    log_file = open(ROOT / "api.log", "w")
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app",
         "--host", "0.0.0.0", "--port", port, "--reload"],
        cwd=str(ROOT),
        stdout=log_file,
        stderr=log_file,
    )

    # Aguarda API ficar pronta
    import urllib.request
    for attempt in range(15):
        time.sleep(2)
        try:
            urllib.request.urlopen(f"http://localhost:{port}/health", timeout=3)
            ok(f"API rodando em http://localhost:{port}")
            ok(f"Docs da API: http://localhost:{port}/docs")
            return
        except Exception:
            info(f"Aguardando API... ({attempt + 1}/15)")

    warn("API pode não ter iniciado. Verifique: tail -f api.log")

# ═══════════════════════════════════════════════════════════
# Passo 11 — Abrir Dashboard Streamlit
# ═══════════════════════════════════════════════════════════

def step11_open_dashboard():
    step_header(11, "Abrindo Dashboard Streamlit")

    home_page = ROOT / "dashboard" / "app.py"
    if not home_page.exists():
        warn("dashboard/app.py não encontrado.")
        return

    info("Iniciando Streamlit em http://localhost:8501 ...")
    info("Pressione Ctrl+C para encerrar o dashboard.")

    print()
    if RICH:
        console.print(Panel.fit(
            "[bold green]🎉 Setup concluído com sucesso![/bold green]\n\n"
            "[cyan]Dashboard:[/cyan] http://localhost:8501\n"
            "[cyan]API:[/cyan]       http://localhost:8000\n"
            "[cyan]API Docs:[/cyan]  http://localhost:8000/docs\n\n"
            "[yellow]Para ingestão completa (todos os estados 2020-2024):[/yellow]\n"
            "  make ingest-full\n"
            "  (estimativa: 2-4h dependendo da conexão)",
            title="saude-publica-br",
            border_style="green"
        ))
    else:
        print("=" * 60)
        print("🎉 Setup concluído com sucesso!")
        print(f"  Dashboard: http://localhost:8501")
        print(f"  API:       http://localhost:8000")
        print(f"  API Docs:  http://localhost:8000/docs")
        print("=" * 60)

    time.sleep(2)
    webbrowser.open("http://localhost:8501")

    # Streamlit no foreground (bloqueia até Ctrl+C)
    run(f'"{sys.executable}" -m streamlit run {home_page} --server.port 8501')

# ═══════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════

def check_health():
    """Verifica o estado de todos os componentes."""
    import urllib.request

    if RICH:
        console.rule("[bold]Health Check — saude-publica-br[/bold]")
    else:
        print("\n" + "="*60 + "\nHealth Check\n" + "="*60)

    checks = {
        "Python 3.11+": (sys.version_info >= (3, 11), ""),
        ".env existe": (ENV_FILE.exists(), "Execute: python bootstrap.py"),
        "DATABASE_URL": ("DATABASE_URL" in _read_env(), "Configure no .env"),
        "Redis ping": (run_ok("redis-cli ping") or run_ok("docker exec saude_redis redis-cli ping"), "Execute: docker compose up -d redis"),
    }

    try:
        urllib.request.urlopen("http://localhost:8000/health", timeout=3)
        checks["API FastAPI"] = (True, "")
    except Exception:
        checks["API FastAPI"] = (False, "Execute: make api")

    try:
        urllib.request.urlopen("http://localhost:8501", timeout=3)
        checks["Streamlit"] = (True, "")
    except Exception:
        checks["Streamlit"] = (False, "Execute: make dashboard")

    all_ok = True
    for name, (status, hint) in checks.items():
        if status:
            ok(name)
        else:
            err(f"{name} — {hint}")
            all_ok = False

    print()
    if all_ok:
        ok("Todos os componentes operacionais! 🎉")
    else:
        warn("Alguns componentes não estão rodando. Execute: python bootstrap.py")

# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

STEPS = [
    step1_check_python,       # 1
    step2_install_deps,       # 2
    step3_configure_env,      # 3
    step4_start_redis,        # 4
    step5_setup_database,     # 5
    step6_load_references,    # 6
    step7_pilot_ingestion,    # 7
    step8_dbt_build,          # 8
    step9_validate_marts,     # 9  ← Great Expectations
    step10_start_api,         # 10
    step11_open_dashboard,    # 11
]

def main():
    parser = argparse.ArgumentParser(description="Bootstrap automatizado do saude-publica-br")
    parser.add_argument("--step", type=int, default=1, metavar="N",
                        help="Iniciar a partir do passo N (1-11)")
    parser.add_argument("--check", action="store_true",
                        help="Verificar saúde do sistema sem instalar nada")
    parser.add_argument("--skip-gx", action="store_true",
                        help="Pular validação Great Expectations (passo 9)")
    args = parser.parse_args()

    if args.check:
        check_health()
        return

    if RICH:
        console.print(Panel.fit(
            "[bold cyan]saude-publica-br — Bootstrap Automatizado[/bold cyan]\n\n"
            "O Our World in Data do SUS 🇧🇷\n\n"
            "[dim]Você precisará de:\n"
            "  • Conta gratuita em supabase.com\n"
            "  • ~15 minutos para o setup completo[/dim]",
            border_style="cyan"
        ))
    else:
        print("\n" + "="*60)
        print("saude-publica-br — Bootstrap Automatizado")
        print("O Our World in Data do SUS 🇧🇷")
        print("="*60 + "\n")

    # Constrói lista de passos, opcionalmente sem GX
    active_steps = list(STEPS)
    if args.skip_gx:
        active_steps = [fn for fn in active_steps if fn is not step9_validate_marts]
        warn("--skip-gx: validação GX será pulada.")

    start = max(1, min(args.step, 11))
    for i, fn in enumerate(active_steps[start-1:], start=start):
        try:
            fn()
        except SystemExit:
            raise
        except KeyboardInterrupt:
            warn("\nInterrompido pelo usuário.")
            info(f"Para retomar do passo atual: python bootstrap.py --step {i}")
            sys.exit(0)
        except Exception as e:
            err(f"Erro inesperado no passo {i}: {e}")
            info(f"Para retomar: python bootstrap.py --step {i}")
            raise

if __name__ == "__main__":
    main()
