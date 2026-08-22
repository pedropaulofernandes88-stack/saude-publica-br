#!/usr/bin/env python3
"""
bootstrap.py — Setup automatizado do saude-publica-br
=====================================================
O que este script faz (sem pedir nada além do básico):
  1.  Verifica Python e dependências essenciais
  2.  Instala todos os pacotes via pip
  3.  Cria e valida o arquivo .env
  4.  Cria as tabelas no Supabase (executa setup_supabase.sql)
  5.  Carrega tabelas de referência (municipios, CID-10)
  6.  Executa ingestão piloto: SP, Jan-Mar/2024 (~3 min)
  7.  Roda dbt build (cria todos os marts)
  8.  Valida todos os marts com Great Expectations

Uso:
  python bootstrap.py           # Setup completo
  python bootstrap.py --step 5  # Retomar a partir do passo 5
  python bootstrap.py --check   # Só verifica se tudo está OK
"""

import argparse
import os
import subprocess
import sys
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

def _passo_arquivado(alvo: str, alternativa: str):
    """
    Passo que dependia da primeira arquitetura e não roda mais.

    Em 2026-08-22 `ingestion/ingest_*.py`, `ingestion/refs_loader.py`,
    `ingestion/setup_supabase.sql` e `flows/` foram para `archive/` — ver
    `archive/ingestion/README.md`. Estes passos avisam e seguem em vez de
    falhar, para que `--check` e os passos ainda válidos continuem utilizáveis.

    A versão anterior do passo 6 REGENERAVA `ingestion/refs_loader.py` quando
    não o encontrava. Depois da mudança isso recriaria código arquivado dentro
    de um diretório que agora passa pelo ruff no CI.
    """
    warn(f"Passo arquivado — {alvo} está em archive/ e não é mais executado.")
    info(alternativa)
    info("Contexto: archive/ingestion/README.md")

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
# Passo 5 — Criar tabelas no Supabase
# ═══════════════════════════════════════════════════════════

def step5_setup_database():
    step_header(5, "Criando tabelas no Supabase")
    _passo_arquivado(
        "ingestion/setup_supabase.sql",
        "As tabelas em uso hoje sao versionadas em migrations/ (V006..V026).",
    )


def step6_load_references():
    step_header(6, "Carregando tabelas de referencia")
    _passo_arquivado(
        "ingestion/refs_loader.py",
        "As dimensoes vivas saem de data/refs/*.parquet, carregadas por "
        "scripts/pipeline_v2.py.",
    )

# ═══════════════════════════════════════════════════════════
# Passo 7 — Ingestão piloto (SP, Jan-Mar 2024)
# ═══════════════════════════════════════════════════════════

def step7_pilot_ingestion():
    step_header(7, "Ingestao piloto")
    _passo_arquivado(
        "ingestion/ingest_sia_pa.py",
        "O SIA saiu do pipeline. Quem ingere hoje: python scripts/pipeline_v2.py.",
    )

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
# Passo 11 — Abrir Dashboard Streamlit
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
    step5_setup_database,     # 5
    step6_load_references,    # 6
    step7_pilot_ingestion,    # 7
    step8_dbt_build,          # 8
    step9_validate_marts,     # 9  ← Great Expectations
]

def main():
    parser = argparse.ArgumentParser(description="Bootstrap automatizado do saude-publica-br")
    parser.add_argument("--step", type=int, default=1, metavar="N",
                        help="Iniciar a partir do passo N (1-8)")
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
