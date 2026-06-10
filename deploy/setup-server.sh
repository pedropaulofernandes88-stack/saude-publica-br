#!/bin/bash
# ============================================================
# setup-server.sh — saudeemdado.com com DADOS REAIS
# Ubuntu 22.04 | Hetzner CX31 (8 GB RAM) + Volume 300 GB
#
# O script:
#  1. Instala Docker, Python 3.12, dependências
#  2. Formata e monta o volume Hetzner em /mnt/dados
#  3. Obtém SSL com Let's Encrypt
#  4. Sobe toda a stack (PostgreSQL + API + Frontend + nginx)
#  5. Aplica as migrations SQL
#  6. Inicia a ingestão dos dados reais do DataSUS em background
# ============================================================
set -euo pipefail

DOMAIN="saudeemdado.com"
APP_DIR="/opt/saude-publica-br"
DADOS_DIR="/mnt/dados"
REPO_URL="${REPO_URL:-https://github.com/SEU_USUARIO/saude-publica-br.git}"
EMAIL="${CERTBOT_EMAIL:-admin@saudeemdado.com}"
VOLUME_DEVICE="${VOLUME_DEVICE:-/dev/sdb}"   # disco adicional Hetzner

# ── Cores para output ─────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅  $1${NC}"; }
info() { echo -e "${YELLOW}▶   $1${NC}"; }

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   saudeemdado.com — Setup com Dados Reais DataSUS       ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── 1. Sistema ────────────────────────────────────────────────────────────────
info "[1/9] Atualizando sistema..."
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq curl git unzip ufw fail2ban htop ncdu \
    ca-certificates gnupg lsb-release python3.12 python3.12-venv python3-pip
ok "Sistema atualizado"

# ── 2. Docker ─────────────────────────────────────────────────────────────────
info "[2/9] Instalando Docker..."
if ! command -v docker &>/dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
fi
ok "Docker $(docker --version | cut -d' ' -f3)"

# ── 3. Volume de dados (300 GB Hetzner) ───────────────────────────────────────
info "[3/9] Configurando volume de dados em $DADOS_DIR..."
if ! mountpoint -q "$DADOS_DIR" 2>/dev/null; then
    # Formatar se ainda não formatado
    if ! blkid "$VOLUME_DEVICE" &>/dev/null; then
        info "  Formatando $VOLUME_DEVICE como ext4..."
        mkfs.ext4 -L dados-saude "$VOLUME_DEVICE"
    fi
    mkdir -p "$DADOS_DIR"
    # Montar e adicionar ao fstab para persistência
    mount "$VOLUME_DEVICE" "$DADOS_DIR"
    VOLUME_UUID=$(blkid -s UUID -o value "$VOLUME_DEVICE")
    grep -q "$VOLUME_UUID" /etc/fstab || \
        echo "UUID=$VOLUME_UUID $DADOS_DIR ext4 defaults,nofail 0 2" >> /etc/fstab
fi
# Criar estrutura de diretórios no volume
mkdir -p "$DADOS_DIR"/{postgres,backups,dataraw,parquet,raw,logs}
ok "Volume montado em $DADOS_DIR ($(df -h $DADOS_DIR | awk 'NR==2{print $4}') livres)"

# ── 4. Firewall ────────────────────────────────────────────────────────────────
info "[4/9] Configurando firewall..."
ufw --force reset -y >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow ssh >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
ok "Firewall: SSH + HTTP + HTTPS"

# ── 5. Código do projeto ───────────────────────────────────────────────────────
info "[5/9] Clonando repositório..."
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" && git pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

# Criar .env com valores gerados automaticamente
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/deploy/.env.production" "$APP_DIR/.env"
    # Gerar senhas seguras
    POSTGRES_PASSWORD=$(openssl rand -hex 16)
    API_SECRET_KEY=$(openssl rand -hex 32)
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    GRAFANA_PASSWORD=$(openssl rand -hex 8)
    sed -i "s/GERE_COM_openssl_rand_hex_16/$POSTGRES_PASSWORD/g" "$APP_DIR/.env"
    sed -i "s/GERE_COM_openssl_rand_hex_32/$API_SECRET_KEY/g" "$APP_DIR/.env"
    # A segunda ocorrência de hex_32 (JWT)
    sed -i "0,/GERE_COM_openssl_rand_hex_32/! s/GERE_COM_openssl_rand_hex_32/$JWT_SECRET_KEY/" "$APP_DIR/.env"
    sed -i "s/TROQUE_ESTA_SENHA_DO_GRAFANA/$GRAFANA_PASSWORD/g" "$APP_DIR/.env"
    sed -i "s/MESMA_SENHA_ACIMA/$POSTGRES_PASSWORD/g" "$APP_DIR/.env"
    # Salvar as senhas geradas
    cat > /root/senhas-saude.txt << SENHAS
# SENHAS GERADAS — guarde em local seguro e delete este arquivo!
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
API_SECRET_KEY=$API_SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
GRAFANA_PASSWORD=$GRAFANA_PASSWORD
SENHAS
    chmod 600 /root/senhas-saude.txt
    ok ".env criado com senhas geradas em /root/senhas-saude.txt"
fi

# ── 6. Instalar dependências Python (para ingestão) ────────────────────────────
info "[6/9] Instalando dependências Python..."
python3.12 -m venv /opt/venv-saude
/opt/venv-saude/bin/pip install -q --upgrade pip
/opt/venv-saude/bin/pip install -q -r "$APP_DIR/requirements.txt"
ln -sf /opt/venv-saude/bin/python /usr/local/bin/python-saude
ok "Python e dependências prontos"

# ── 7. SSL com Let's Encrypt ───────────────────────────────────────────────────
info "[7/9] Obtendo certificado SSL..."
apt-get install -y -qq certbot
certbot certonly \
    --standalone --non-interactive --agree-tos \
    --email "$EMAIL" -d "$DOMAIN" -d "www.$DOMAIN" \
    || echo "  ⚠️  Certbot falhou — DNS ainda não propagou? Tente depois: certbot certonly --standalone -d $DOMAIN"
# Renovação automática
(crontab -l 2>/dev/null; echo "0 3 * * 0 certbot renew --quiet && docker compose -f $APP_DIR/docker-compose.yml restart nginx") \
    | crontab -
ok "SSL configurado"

# ── 8. Subir a stack ───────────────────────────────────────────────────────────
info "[8/9] Iniciando serviços..."
cd "$APP_DIR"
docker compose pull --quiet
docker compose up -d postgres redis
info "  Aguardando PostgreSQL ficar pronto..."
sleep 20
# Aplicar migrations SQL
for migration in migrations/V*.sql; do
    docker compose exec -T postgres \
        psql -U saude -d saude_publica -f "/migrations/$(basename $migration)" \
        2>/dev/null && echo "  ✅ $(basename $migration)" || true
done
# Subir o resto
docker compose up -d
ok "Todos os serviços no ar"

# ── 9. Ingestão dos dados reais (background) ───────────────────────────────────
info "[9/9] Iniciando ingestão dos dados DataSUS em background..."
cat > /opt/ingest.sh << 'INGEST'
#!/bin/bash
cd /opt/saude-publica-br
source <(grep -v '^#' .env | xargs)
export DATABASE_URL="$DATABASE_URL_LOCAL"

LOG=/mnt/dados/logs/ingestao_$(date +%Y%m%d_%H%M%S).log
echo "Ingestão iniciada: $(date)" | tee "$LOG"

/opt/venv-saude/bin/python ingestion/ingest_all_states.py \
    --ano-inicio 2020 --ano-fim 2024 2>&1 | tee -a "$LOG"

echo "Ingestão concluída: $(date)" | tee -a "$LOG"
echo "Rodando dbt..." | tee -a "$LOG"
cd dbt && /opt/venv-saude/bin/dbt run 2>&1 | tee -a "$LOG"
echo "dbt concluído: $(date)" | tee -a "$LOG"
INGEST
chmod +x /opt/ingest.sh
nohup /opt/ingest.sh > /mnt/dados/logs/ingestao.log 2>&1 &
INGEST_PID=$!
echo $INGEST_PID > /tmp/ingest.pid

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🎉  saudeemdado.com publicado com dados reais!         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  API:     https://$DOMAIN/api/docs         ║"
echo "║  Site:    https://$DOMAIN                  ║"
echo "║  Grafana: ssh -L 3001:localhost:3001 root@$(hostname -I|awk '{print $1}')  ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  ⏳ Ingestão DataSUS rodando em background (PID: $INGEST_PID)"
echo "║  📊 Acompanhar: tail -f /mnt/dados/logs/ingestao.log   ║"
echo "║  ⏰ Estimativa: 2-8 horas para todos os estados         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Senhas geradas salvas em: /root/senhas-saude.txt"
echo "  Verificar status:  docker compose ps"
echo "  Logs da API:       docker compose logs -f api"
