# Cemitério Digital — integração como subdomínio

Estado em 2026-09-06: **integração do lado do site pronta e verificada; serviço
não publicado.** Três impedimentos reais, todos fora do alcance deste
repositório, estão descritos abaixo com o que cada um exige.

O pacote de origem é `cemiterio_digital_subdominio_kit_ia.zip` (variante
**compacta**, 82 arquivos, 1,76 MB). Conferi os SHA-256 dos 82 contra o
`MANIFESTO_PACK.json`: **82 conferem, 0 divergem, 0 ausentes**.

## O que foi confirmado sobre a infraestrutura atual

Medido, não presumido:

| Fato | Como foi verificado |
|---|---|
| O site é export estático no **GitHub Pages** | `.github/workflows/deploy-site.yml` publica `site/out` via `actions/deploy-pages` |
| `saudeemdado.com` → `185.199.108–111.153` | consulta DNS; são os IPs do GitHub Pages |
| DNS administrado na **HostGator** | NS = `dns3.hostgator.com.br`, `dns4.hostgator.com.br` |
| `cemiterio.saudeemdado.com` **não existe** | consulta A sem resposta |
| Não há wildcard `*.saudeemdado.com` | consulta a nome inexistente sem resposta |
| O pacote **não traz os dados** | `MANIFESTO_PACK.json`: `dataset_included: false` |
| Não há Docker nesta máquina | `docker --version` → comando não encontrado |

**Consequência:** o GitHub Pages serve arquivo e nada mais. Ele não executa
Python, não sobe container e não termina TLS para um host que não seja o do
`CNAME`. O motor do Cemitério lê Parquet com pandas e precisa de processo
persistente, mais um gateway que injeta a credencial no lado do servidor.
Não há como hospedá-lo na plataforma atual — e isso **não é uma limitação do
pacote**, é a natureza do Pages.

Como não há wildcard e o `CNAME` do Pages reivindica apenas o domínio raiz,
criar um registro `A` para `cemiterio` é **independente** e não afeta o site
principal.

## Arquitetura adotada

```
Visitante
   ├── https://saudeemdado.com          → GitHub Pages (estático, como hoje)
   └── https://cemiterio.saudeemdado.com → VPS
            Caddy (TLS) → gateway Nginx → ASGI interno (Bearer, rede privada)
                                              └── dataset Parquet, somente leitura
```

Duas hospedagens, um domínio. O site principal permanece intocado; o
subdomínio é um serviço à parte. O navegador fala com `/api/` da **mesma
origem** do subdomínio, então a chave interna nunca chega ao cliente.

O que este repositório contém da integração é só o **ponto de entrada**:
`site/lib/cemiterio.ts` guarda um endereço, e o menu passa a exibir o acesso
quando esse endereço existe.

### Por que o acesso falha fechado

`site/lib/cemiterio.ts` devolve `null` quando a variável está ausente ou não
merece confiança, e o item some do menu. Recusa `http:`, credencial embutida
na URL, caminho, query e fragmento. O motivo é direto: o subdomínio ainda não
resolve, e um link morto num site que se apresenta como confiável custa mais
do que a ausência do link.

Verificado nos dois estados, com build real:

- com `NEXT_PUBLIC_CEMITERIO_URL` definida → `<a href="…" target="_blank"
  rel="noreferrer">` aparece em Explorar, no desktop (1440px) e no menu móvel
  (390px), com rótulo acessível "(serviço externo, abre em nova aba)";
- sem a variável → **zero ocorrências** de "cemitério" em todo o `site/out`.

## Variáveis que o titular precisa cadastrar

Nenhum valor aparece aqui, e nenhum deles deve ser enviado a um assistente.

**No GitHub, em Settings → Secrets and variables → Actions → Variables:**

| Nome | Conteúdo | Observação |
|---|---|---|
| `NEXT_PUBLIC_CEMITERIO_URL` | `https://` + o host escolhido | *Variable*, não *secret*: é URL pública e vai para o HTML. Sem ela o menu fica como hoje. |

**No servidor do subdomínio**, geradas por `deploy/gerar_env.py` — nunca à mão,
nunca versionadas, nunca coladas numa conversa:

| Nome | Conteúdo |
|---|---|
| `CEMITERIO_API_KEY` | credencial interna entre gateway e ASGI; só existe no ambiente do gateway |
| `CEMITERIO_CORS_ORIGINS` | allowlist de origem, sem curinga |
| domínio, e-mail e caminho do dataset | parâmetros do `gerar_env.py` |

## O que falta para publicar, e o que cada item exige

1. **Os dados.** `dataset_included: false`. O `app/dataset/` do pacote
   **completo** (~217 MB antes de compactar) precisa ser transferido por canal
   privado para o servidor, fora da área web e fora de qualquer repositório —
   os Parquets internos guardam células com contagem abaixo de cinco, e
   oferecê-los para download contornaria a supressão que a API aplica.
   Sem eles o motor não responde, e não existe substituto: dado simulado aqui
   seria mentira apresentada como ferramenta.

2. **Um servidor com Docker.** Não há Docker nesta máquina, então build de
   imagem, subida dos containers e certificados **não foram testados** e não
   podem ser declarados. Requisito do pacote: Linux com Docker, 4 GB de RAM
   como piso e 8 GB com folga, portas 80/443 livres ou um proxy existente que
   aceite o novo host.

3. **O registro DNS.** Criar `cemiterio` como `A` apontando para o IPv4 do
   servidor, no painel da HostGator. Não mexer em `saudeemdado.com`, `www`,
   MX ou nameservers. Este documento não autoriza contratação nem alteração de
   DNS: a decisão é do titular.

## Sequência, quando os três estiverem resolvidos

```bash
python deploy/gerar_env.py --dominio <host> --email <contato real> --dataset <caminho privado>
python deploy/test_config.py
docker compose config --quiet
docker compose up -d --build
python qa/verificar_subdominio.py --url http://127.0.0.1:8080
```

Só depois do smoke pelo loopback: apontar o DNS, subir com
`compose.https.yaml`, e então

```bash
python qa/verificar_subdominio.py --url https://<host>
```

O verificador confere números reais, cabeçalhos e bloqueio de arquivos, e grava
`qa/RELATORIO_SUBDOMINIO.json`. Entre os valores esperados do snapshot
2026-09-06 / app 0.5.0: 5.571 municípios; Atlas Brasil 2024 com 1.529.725
óbitos; média 2015–2024 de 1.445.721,8; 1.581 categorias CID-10.

**Só ligar `NEXT_PUBLIC_CEMITERIO_URL` depois que a URL final responder**, com
certificado válido e com o bloqueio de `/dataset/`, `.env`, `.py` e `.parquet`
conferido. A ordem importa: a variável é o que faz o link aparecer para o
público.

## Limites que não se resolvem com configuração

Estes vêm do próprio pacote (`04_DADOS_E_LIMITES.md`) e devem sobreviver à
integração:

- 2015–2024 é a referência histórica; **2025 é preliminar** e **2026 cobre
  janeiro a maio, com maio parcial**. Não anualizar 2026.
- A supressão é aplicada **no servidor, depois da agregação**. Ela não é
  anonimização formal: continua havendo risco de inferência por diferenças
  entre consultas complementares, e limite de requisição não elimina isso.
- O limite atual é por processo (60/min no ASGI, 20/min no gateway), **não é
  quota por pessoa**. Uma API para parceiros exigiria identidade e quotas
  próprias.
- O Atlas cruza dimensões que coexistem no mesmo cubo. Marginais de raça/cor,
  escolaridade ou ocupação **não podem** ser combinadas com o cubo municipal
  para inventar cruzamentos individuais.
- Característica do município não é característica de quem morreu.

## O que este repositório não faz

Não hospeda o motor, não guarda o dataset, não guarda credencial e não altera
DNS. Guarda um endereço e um item de menu — e nem isso, enquanto o endereço
não for configurado.
