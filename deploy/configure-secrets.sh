#!/bin/bash
# ============================================================
# configure-secrets.sh
# Configura todos os secrets necessários no GitHub Actions
# 
# PRÉ-REQUISITOS:
#   brew install gh   (macOS)  ou   apt install gh  (Linux)
#   gh auth login
#
# USO:
#   chmod +x deploy/configure-secrets.sh
#   ./deploy/configure-secrets.sh
# ============================================================
set -euo pipefail

REPO="SEU_USUARIO/saude-publica-br"  # ← EDITE AQUI

echo "Configurando secrets para: $REPO"
echo ""

# ── Railway ────────────────────────────────────────────────────────────────
echo "1. RAILWAY_TOKEN"
echo "   Acesse: https://railway.app/account/tokens"
echo "   Clique em 'Create Token', copie e cole abaixo:"
read -rsp "   RAILWAY_TOKEN: " RAILWAY_TOKEN
echo ""
gh secret set RAILWAY_TOKEN --body "$RAILWAY_TOKEN" --repo "$REPO"
echo "   ✅ RAILWAY_TOKEN salvo"

# ── Vercel ─────────────────────────────────────────────────────────────────
echo ""
echo "2. VERCEL_TOKEN"
echo "   Acesse: https://vercel.com/account/tokens"
echo "   Clique em 'Create', copie e cole abaixo:"
read -rsp "   VERCEL_TOKEN: " VERCEL_TOKEN
echo ""
gh secret set VERCEL_TOKEN --body "$VERCEL_TOKEN" --repo "$REPO"
echo "   ✅ VERCEL_TOKEN salvo"

echo ""
echo "3. VERCEL_ORG_ID e VERCEL_PROJECT_ID"
echo "   Execute: cd frontend && npx vercel link"
echo "   Depois: cat frontend/.vercel/project.json"
read -rp "   VERCEL_ORG_ID: " VERCEL_ORG_ID
read -rp "   VERCEL_PROJECT_ID: " VERCEL_PROJECT_ID
gh secret set VERCEL_ORG_ID --body "$VERCEL_ORG_ID" --repo "$REPO"
gh secret set VERCEL_PROJECT_ID --body "$VERCEL_PROJECT_ID" --repo "$REPO"
echo "   ✅ Vercel IDs salvos"

# ── Variáveis da API (Railway as environment variables) ────────────────────
echo ""
echo "4. Variáveis de ambiente da API (Supabase)"
echo "   Cole os valores do seu projeto Supabase:"
read -rsp "   DATABASE_URL: " DATABASE_URL; echo ""
read -rsp "   SUPABASE_URL: " SUPABASE_URL; echo ""
read -rsp "   SUPABASE_ANON_KEY: " SUPABASE_ANON_KEY; echo ""
read -rsp "   SUPABASE_SERVICE_ROLE_KEY: " SUPABASE_SERVICE_ROLE_KEY; echo ""

# Gerar chaves automáticas
API_SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

gh secret set DATABASE_URL --body "$DATABASE_URL" --repo "$REPO"
gh secret set SUPABASE_URL --body "$SUPABASE_URL" --repo "$REPO"
gh secret set SUPABASE_ANON_KEY --body "$SUPABASE_ANON_KEY" --repo "$REPO"
gh secret set SUPABASE_SERVICE_ROLE_KEY --body "$SUPABASE_SERVICE_ROLE_KEY" --repo "$REPO"
gh secret set API_SECRET_KEY --body "$API_SECRET_KEY" --repo "$REPO"
gh secret set JWT_SECRET_KEY --body "$JWT_SECRET_KEY" --repo "$REPO"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅  Todos os secrets configurados!          ║"
echo "║  Agora faça git push para disparar o deploy  ║"
echo "╚══════════════════════════════════════════════╝"
