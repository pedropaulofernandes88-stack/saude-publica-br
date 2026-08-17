#!/bin/bash
# ============================================================
# bootstrap.sh — Publica saudeemdado.com do zero em 4 comandos
#
# O que este script faz:
#   1. Cria o repositório no GitHub
#   2. Faz push do código
#   3. Cria o projeto no Railway e conecta ao GitHub
#   4. Cria o projeto no Vercel e conecta ao GitHub
#   5. Configura todos os secrets automáticamente
#
# PRÉ-REQUISITOS (instale antes):
#   - git                : já vem no sistema
#   - gh (GitHub CLI)    : https://cli.github.com
#   - railway (CLI)      : npm install -g @railway/cli
#   - vercel (CLI)       : npm install -g vercel
#
# USO:
#   chmod +x deploy/bootstrap.sh
#   ./deploy/bootstrap.sh
# ============================================================
set -euo pipefail

GITHUB_REPO="saude-publica-br"
DOMAIN="saudeemdado.com"

print_step() { echo ""; echo "══════════════════════════════════"; echo "  $1"; echo "══════════════════════════════════"; }

# ── Verificar dependências ────────────────────────────────────────────────
print_step "Verificando dependências..."
for cmd in git gh railway vercel; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "❌ '$cmd' não encontrado. Instale antes de continuar."
        case $cmd in
            gh)      echo "   → brew install gh  ou  https://cli.github.com" ;;
            railway) echo "   → npm install -g @railway/cli" ;;
            vercel)  echo "   → npm install -g vercel" ;;
        esac
        exit 1
    fi
    echo "  ✅ $cmd"
done

# ── Login nas plataformas ─────────────────────────────────────────────────
print_step "Login nas plataformas"
echo "  → GitHub:"
gh auth status 2>/dev/null || gh auth login
echo "  → Railway:"
railway whoami 2>/dev/null || railway login
echo "  → Vercel:"
vercel whoami 2>/dev/null || vercel login

# ── Coletar credenciais do Supabase ──────────────────────────────────────
print_step "Credenciais do Supabase"
echo "  Acesse https://app.supabase.com → seu projeto → Settings → API"
echo ""
read -rp "  SUPABASE_URL (https://xxx.supabase.co): " SUPABASE_URL
read -rsp "  SUPABASE_ANON_KEY: " SUPABASE_ANON_KEY; echo ""
read -rsp "  SUPABASE_SERVICE_ROLE_KEY: " SUPABASE_SERVICE_ROLE_KEY; echo ""
echo ""
echo "  Agora: Settings → Database → Connection string (URI)"
read -rsp "  DATABASE_URL (postgresql://postgres:...): " DATABASE_URL; echo ""

# Gerar chaves seguras
API_SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# ── Criar repositório no GitHub ───────────────────────────────────────────
print_step "Criando repositório no GitHub..."
GITHUB_USER=$(gh api user --jq .login)
FULL_REPO="$GITHUB_USER/$GITHUB_REPO"

if gh repo view "$FULL_REPO" &>/dev/null; then
    echo "  Repositório já existe: $FULL_REPO"
else
    gh repo create "$GITHUB_REPO" \
        --description "O Our World in Data do SUS — API de dados de saúde pública do Brasil" \
        --public \
        --source=. \
        --push
    echo "  ✅ Repositório criado: https://github.com/$FULL_REPO"
fi

# Push do código
git remote set-url origin "https://github.com/$FULL_REPO.git" 2>/dev/null || true
git add -A
git commit -m "chore: configurar deploy Railway + Vercel + saudeemdado.com" --allow-empty
git push -u origin main

# ── Criar projeto no Railway ──────────────────────────────────────────────
print_step "Configurando Railway..."
railway init --name "saude-em-dado-api" 2>/dev/null || true

# Configurar variáveis de ambiente no Railway
railway variables --set "DATABASE_URL=$DATABASE_URL" \
                  --set "SUPABASE_URL=$SUPABASE_URL" \
                  --set "SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" \
                  --set "SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY" \
                  --set "API_SECRET_KEY=$API_SECRET_KEY" \
                  --set "JWT_SECRET_KEY=$JWT_SECRET_KEY" \
                  --set "REDIS_URL=redis://localhost:6379/0" \
                  --set "ENV=production" \
                  --set "CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN"

# Adicionar Redis
railway add --plugin redis 2>/dev/null || echo "  Redis já adicionado"

# Pegar o token Railway para o GitHub Actions
RAILWAY_TOKEN=$(railway whoami --token 2>/dev/null || echo "")

echo "  ✅ Railway configurado"

# ── Criar projeto no Vercel ───────────────────────────────────────────────
print_step "Configurando Vercel..."
cd frontend
vercel link --yes 2>/dev/null || vercel --yes
VERCEL_ORG_ID=$(cat .vercel/project.json | python3 -c "import sys,json; print(json.load(sys.stdin)['orgId'])")
VERCEL_PROJECT_ID=$(cat .vercel/project.json | python3 -c "import sys,json; print(json.load(sys.stdin)['projectId'])")
VERCEL_TOKEN=$(vercel whoami --token 2>/dev/null || echo "")

# Definir domínio customizado no Vercel
vercel domains add "$DOMAIN" --yes 2>/dev/null || true
cd ..

echo "  ✅ Vercel configurado"

# ── Configurar secrets no GitHub Actions ─────────────────────────────────
print_step "Configurando secrets no GitHub Actions..."
set_secret() { gh secret set "$1" --body "$2" --repo "$FULL_REPO"; echo "  ✅ $1"; }

set_secret "DATABASE_URL" "$DATABASE_URL"
set_secret "SUPABASE_URL" "$SUPABASE_URL"
set_secret "SUPABASE_ANON_KEY" "$SUPABASE_ANON_KEY"
set_secret "SUPABASE_SERVICE_ROLE_KEY" "$SUPABASE_SERVICE_ROLE_KEY"
set_secret "API_SECRET_KEY" "$API_SECRET_KEY"
set_secret "JWT_SECRET_KEY" "$JWT_SECRET_KEY"
set_secret "VERCEL_TOKEN" "${VERCEL_TOKEN:-CONFIGURE_MANUALMENTE}"
set_secret "VERCEL_ORG_ID" "$VERCEL_ORG_ID"
set_secret "VERCEL_PROJECT_ID" "$VERCEL_PROJECT_ID"
[ -n "$RAILWAY_TOKEN" ] && set_secret "RAILWAY_TOKEN" "$RAILWAY_TOKEN"

# ── Deploy inicial ────────────────────────────────────────────────────────
print_step "Disparando deploy inicial..."
gh workflow run deploy.yml --repo "$FULL_REPO"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🎉  PUBLICAÇÃO INICIADA!                               ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  GitHub:   https://github.com/$FULL_REPO               ║"
echo "║  Railway:  https://railway.app/dashboard                ║"
echo "║  Vercel:   https://vercel.com/dashboard                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Acompanhar: gh run watch --repo $FULL_REPO             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "⏳ Deploy leva ~3-5 minutos. Quando terminar:"
echo "   API:      https://$DOMAIN/api/docs"
echo "   Site:     https://$DOMAIN"
echo ""
echo "📌 DNS — adicione no seu registrador de domínio:"
echo "   Tipo CNAME | Nome @ | Valor: cname.vercel-dns.com"
echo "   (ou o IP/CNAME que o Vercel/Railway mostrarem)"
