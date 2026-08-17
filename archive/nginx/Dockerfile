# ============================================================
# nginx/Dockerfile
# Multi-stage: gera certificado self-signed + configura nginx
# ============================================================
FROM nginx:1.25-alpine

# Instala openssl para geração de certificado self-signed
RUN apk add --no-cache openssl

# Cria diretório de certificados
RUN mkdir -p /etc/nginx/ssl

# Gera certificado self-signed (substituir por Let's Encrypt em produção)
# Para produção: use Certbot ou acme.sh e monte o volume /etc/letsencrypt
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/privkey.pem \
    -out /etc/nginx/ssl/fullchain.pem \
    -subj "/C=BR/ST=SP/L=Sao Paulo/O=SaudePublicaBR/CN=localhost"

# Copia configuração principal
COPY nginx.conf /etc/nginx/nginx.conf

# Remove configuração default
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80 443

# Testa configuração antes de subir
RUN nginx -t

CMD ["nginx", "-g", "daemon off;"]
