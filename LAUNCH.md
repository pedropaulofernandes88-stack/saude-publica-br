# 🚀 Publicar saudeemdado.com — Guia Completo

Tempo estimado: **45–60 minutos** da primeira vez.

---

## Pré-requisitos

- [ ] Domínio `saudeemdado.com` comprado ✅
- [ ] Conta no [Supabase](https://supabase.com) (gratuita para começar)
- [ ] Conta no [Hetzner Cloud](https://hetzner.com/cloud) ou [DigitalOcean](https://digitalocean.com)
- [ ] Código do projeto em um repositório GitHub (público ou privado)

---

## Passo 1 — Criar banco de dados no Supabase (5 min)

1. Acesse [app.supabase.com](https://app.supabase.com) → **New Project**
2. Nome: `saude-em-dado` | Região: **South America (São Paulo)**
3. Anote a senha do banco — você vai precisar
4. Aguarde o projeto ser criado (~2 min)
5. Vá em **Settings → API** e copie:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY`
6. Vá em **Settings → Database → Connection string (URI)** e copie a URI
   - Substitua `[YOUR-PASSWORD]` pela senha que você definiu
   - Cole como `DATABASE_URL` no `.env`

---

## Passo 2 — Criar servidor na Hetzner (5 min)

1. Acesse [console.hetzner.com](https://console.hetzner.com) → **Servers → Create Server**
2. Configurações recomendadas:
   - **Localização**: Nuremberg ou Falkenstein (mais barato) — ou Helsinki
   - **Imagem**: Ubuntu 22.04
   - **Tipo**: `CX21` (2 vCPU, 4 GB RAM) = **€3,49/mês** para começar
   - **SSH Key**: adicione sua chave pública (`cat ~/.ssh/id_rsa.pub`)
3. Clique **Create & Buy** — anote o **IP público** do servidor

> 💡 Se precisar de mais RAM para carregar os dados reais, escale para `CX31` (8 GB) depois.

---

## Passo 3 — Apontar domínio para o servidor (5 min)

No painel do seu registrador de domínio (Registro.br, GoDaddy, Cloudflare...):

```
Tipo: A
Nome: @   (ou saudeemdado.com)
Valor: IP_DO_SERVIDOR_HETZNER
TTL: 300

Tipo: A
Nome: www
Valor: IP_DO_SERVIDOR_HETZNER
TTL: 300
```

> ⏳ Aguarde 5–10 minutos para o DNS propagar antes do próximo passo.

**Verificar propagação:**
```bash
nslookup saudeemdado.com
# Deve retornar o IP do seu servidor Hetzner
```

---

## Passo 4 — Fazer upload do código para GitHub (5 min)

Se ainda não tem o projeto no GitHub:

```bash
cd /caminho/para/saude-publica-br

git init
git add .
git commit -m "chore: initial commit — saudeemdado.com"
git remote add origin https://github.com/SEU_USUARIO/saude-publica-br.git
git push -u origin main
```

> ⚠️ Certifique-se que `.env` está no `.gitignore` — NUNCA suba senhas para o GitHub.

---

## Passo 5 — Preencher variáveis de ambiente (5 min)

Copie o arquivo `deploy/.env.production` para o servidor **ou** preencha-o localmente:

```bash
cp deploy/.env.production .env
nano .env  # ou use seu editor favorito
```

Preencha obrigatoriamente:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL` (string de conexão do Supabase)
- `API_SECRET_KEY` e `JWT_SECRET_KEY` (rode `openssl rand -hex 32` para cada)
- `GF_SECURITY_ADMIN_PASSWORD` (senha para o Grafana)

---

## Passo 6 — Executar o setup no servidor (20 min)

SSH no servidor e execute o script de instalação:

```bash
# 1. Conectar ao servidor
ssh root@IP_DO_SERVIDOR

# 2. Baixar e executar o script de setup
curl -sSL https://raw.githubusercontent.com/SEU_USUARIO/saude-publica-br/main/deploy/setup-server.sh \
  -o setup.sh && chmod +x setup.sh

# 3. Configurar variáveis (antes de rodar o script)
export REPO_URL="https://github.com/SEU_USUARIO/saude-publica-br.git"
export CERTBOT_EMAIL="seu@email.com"

# 4. Rodar o setup completo
./setup.sh
```

O script vai:
- ✅ Instalar Docker e Docker Compose
- ✅ Configurar firewall (UFW)
- ✅ Clonar o repositório
- ✅ Obter certificado SSL (Let's Encrypt) para `saudeemdado.com`
- ✅ Subir todos os serviços (API + Redis + Frontend + nginx + Prometheus + Grafana)

---

## Passo 7 — Verificar se está funcionando (2 min)

```bash
# Status dos serviços
docker compose ps

# Logs da API
docker compose logs -f api

# Testar a API
curl https://saudeemdado.com/api/health
# Deve retornar: {"status": "ok", "api_version": "0.7.0"}
```

**URLs após o deploy:**

| URL | O que é |
|-----|---------|
| `https://saudeemdado.com` | Site / Frontend |
| `https://saudeemdado.com/api/docs` | Swagger UI (documentação interativa) |
| `https://saudeemdado.com/api/health` | Health check da API |
| `http://IP:3001` | Grafana (monitoramento) |

---

## Passo 8 — Carregar os dados (opcional, para dados reais)

Com o ambiente funcionando com dados de demo, você pode carregar os dados reais:

```bash
# No servidor, dentro do diretório do projeto
cd /opt/saude-publica-br

# Instalar dependências Python
pip install -r requirements.txt

# Rodar a ingestão para um estado (teste)
python ingestion/ingest_all_states.py --estados SP --ano-inicio 2023 --ano-fim 2024

# Se OK, rodar para todos os estados
python ingestion/ingest_all_states.py --ano-inicio 2020 --ano-fim 2024
```

> ⏰ A ingestão completa (27 estados, 5 anos) leva de 2 a 8 horas dependendo da velocidade do servidor.

---

## Manutenção

### Atualizar a aplicação após mudanças no código:

```bash
ssh root@IP_DO_SERVIDOR
cd /opt/saude-publica-br
git pull
docker compose up -d --build api frontend
```

### Renovação de SSL (automática):
O Certbot já está configurado para renovar automaticamente todo domingo às 3h.

### Ver logs em tempo real:
```bash
docker compose logs -f api        # API
docker compose logs -f nginx      # nginx
docker compose logs -f frontend   # Frontend
```

### Escalar o servidor (se precisar de mais recursos):
No painel da Hetzner: **Servers → Seu servidor → Rescue → Resize**
- `CX21` → `CX31` (8 GB RAM) para dados pesados
- `CX31` → `CX41` (16 GB RAM) para produção com muitos usuários

---

## Custos estimados

| Serviço | Custo |
|---------|-------|
| Servidor Hetzner CX21 | €3,49/mês |
| Supabase (free tier, até 500MB) | Grátis |
| Supabase Pro (para dados reais) | $25/mês |
| Cloudflare DNS | Grátis |
| Certificado SSL (Let's Encrypt) | Grátis |
| **Total mínimo** | **~€4/mês** |
| **Total com Supabase Pro** | **~$30/mês** |

---

## Suporte

Problemas? Abra uma issue no repositório GitHub ou consulte:
- [Documentação FastAPI](https://fastapi.tiangolo.com)
- [Documentação Supabase](https://supabase.com/docs)
- [Hetzner Community](https://community.hetzner.com)
