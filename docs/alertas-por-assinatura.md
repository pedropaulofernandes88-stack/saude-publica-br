# Alerta por assinatura — arquitetura e ativação

Avisa quando um município **entra em alerta** de arbovirose ou quando um alerta
**se agrava**. Não é newsletter: em semana sem mudança, ninguém recebe nada.

Há **dois canais**, e o segundo não depende de configuração nenhuma:

| Canal | Depende de | Estado |
|---|---|---|
| E-mail (opt-in duplo) | conta em provedor, domínio verificado, secrets | exige ativação |
| [Feed Atom](https://saudeemdado.com/alertas.xml) | nada | **sempre no ar** |

O e-mail é o elo mais frágil da entrega: exige conta em provedor, verificação de
domínio, SPF/DKIM, reputação de IP, e ainda pode cair em spam. O feed é arquivo
estático no mesmo GitHub Pages — sem credencial, sem cadastro e sem base de dados
pessoais. Gerado por [`build-feed.mjs`](../site/scripts/build-feed.mjs):

- `/alertas.xml` — só semanas com entrada ou agravamento (equivale ao e-mail)
- `/boletim.xml` — todas as edições

Também serve de matéria-prima para automação: qualquer leitor, IFTTT, Zapier, n8n
ou bot de Telegram consome Atom nativamente, então quem quiser outro canal monta o
próprio caminho sem depender do projeto.

## Por que só mudança

A rede sentinela tem 451 municípios e cerca de 13 ficam em alerta a cada semana —
mas em boa parte são os *mesmos* de sempre. Um e-mail semanal repetindo a mesma
lista seria ignorado em um mês e levaria a marcações de spam, destruindo a entrega
justamente quando um surto real acontecesse.

Por isso `build-alertas.mjs` compara a edição atual com a anterior e classifica:

| Classe | Critério | Gera e-mail? |
|---|---|---|
| **novo** | não estava em alerta (nível <3) e entrou | sim |
| **agravado** | já estava, mas piorou (laranja → vermelho) | sim |
| **resolvido** | estava em alerta e saiu | não (só informa no boletim) |
| sem mudança | continua no mesmo nível | não |

Quando a edição anterior não tem vigilância comparável, o script marca
`linha_de_base: true` e **nada é enviado** — senão tudo pareceria novidade e o
assinante levaria uma enxurrada na primeira semana.

## Onde os dados pessoais vivem

Decisão central: a `anon key` do projeto é **pública por design** (o dataset é
aberto). Dado pessoal não pode viver em `public`, nem com RLS.

```
schema alertas            ← NÃO exposto ao PostgREST
└── assinantes            ← RLS ligado, zero políticas (nega tudo)
                             GRANT apenas para service_role
```

Três camadas de defesa, todas verificadas:

1. **Schema fora do PostgREST** — `Accept-Profile: alertas` devolve
   `PGRST106 Invalid schema`. Não existe rota HTTP para a tabela.
2. **RLS sem política** — nega tudo por padrão a qualquer role que não contorne RLS.
   O linter do Supabase marca isso como `rls_enabled_no_policy` (INFO); aqui é
   **intencional**, não esquecimento.
3. **Grants** — `anon` e `authenticated` não têm nem `USAGE` no schema.

A Edge Function alcança os dados por funções `SECURITY DEFINER` em `public`, cada
uma fazendo *uma* operação (assinar, confirmar, cancelar, listar destinatários de um
envio). `EXECUTE` é revogado de `anon`/`authenticated` — chamá-las com a chave
pública devolve 404.

## LGPD

- **Coleta mínima**: e-mail e UF de interesse. Sem nome, telefone ou rastreio.
- **Finalidade única**, declarada no formulário e no e-mail de confirmação.
- **Opt-in duplo**: nada é enviado antes da confirmação por link.
- **Minimização**: inscrição não confirmada em 7 dias é apagada
  (`alertas.purgar_nao_confirmados()`).
- **Cancelamento** em um clique, sem login, e por `DELETE` — não guardamos registro
  de quem cancelou.
- **Anti-abuso**: no máximo um e-mail de confirmação por hora por endereço, e a
  resposta não revela se um e-mail já está cadastrado.

## Ativação — o que falta

Tudo está implantado e testado, menos o provedor de e-mail. São dois segredos:

### 1. Provedor de e-mail (Resend)

1. Crie conta em <https://resend.com> e gere uma API key.
2. Configure nos **secrets do Supabase** (Dashboard → Edge Functions → Secrets):

```
RESEND_API_KEY=re_xxxxxxxxxxxx
ALERTAS_REMETENTE=Saúde em Dado <alertas@saudeemdado.com>
```

**Atalho para destravar sem mexer em DNS.** Verificar domínio exige adicionar
SPF/DKIM no DNS e esperar propagação. Enquanto isso não acontece, use o
remetente de teste do próprio Resend:

```
ALERTAS_REMETENTE=Saúde em Dado <onboarding@resend.dev>
```

Funciona sem domínio verificado, com a limitação de **entregar apenas ao e-mail
da conta do Resend** — suficiente para validar a cadeia inteira. Trocar de volta
para o domínio próprio depois é alterar só este campo.

Sem domínio verificado e usando `@saudeemdado.com`, o Resend recusa o envio: a
função responde **502**, desfaz a inscrição pendente e registra o motivo em
Edge Functions → `alertas-assinatura` → Logs.

Sem `RESEND_API_KEY`, o formulário responde 503 com mensagem clara e **não**
grava inscrição inconfirmável.

### 2. Segredo do envio semanal

Gere um valor aleatório e configure nos **dois** lados:

```bash
openssl rand -hex 32
```

- **Supabase** (Edge Functions → Secrets): `ALERTAS_ENVIO_SECRET=<valor>`
- **GitHub** (Settings → Secrets → Actions): `ALERTAS_ENVIO_SECRET=<mesmo valor>`

O passo de envio no workflow só roda se esse secret existir, então nada quebra
enquanto não estiver configurado.

## Teste sem enviar de verdade

A função de envio aceita `dry_run`, que percorre destinatários e monta as mensagens
sem chamar o provedor:

```bash
curl -X POST "https://zekjhmxjamatlxpkykde.supabase.co/functions/v1/alertas-envio" \
  -H "Content-Type: application/json" \
  -H "x-alertas-secret: $ALERTAS_ENVIO_SECRET" \
  -d "$(jq '. + {dry_run: true}' site/public/sdata/boletins/alertas-2026-se30.json)"
```

## Peças

| Peça | Onde |
|---|---|
| Diff de alertas | [`site/scripts/build-alertas.mjs`](../site/scripts/build-alertas.mjs) |
| Formulário | [`site/components/assinar-alertas.tsx`](../site/components/assinar-alertas.tsx) |
| Inscrição/confirmação/cancelamento | Edge Function `alertas-assinatura` |
| Envio semanal | Edge Function `alertas-envio` |
| Orquestração | [`.github/workflows/boletim-semanal.yml`](../.github/workflows/boletim-semanal.yml) |
