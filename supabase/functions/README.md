# Edge Functions

Código-fonte das funções implantadas no Supabase, versionado aqui pelo mesmo
motivo que o SQL vive em [`migrations/`](../../migrations/): nada que o projeto
executa pode existir só no painel de um provedor.

| Função | O que faz | `verify_jwt` |
|---|---|---|
| [`alertas-assinatura`](alertas-assinatura/index.ts) | inscrição, confirmação e cancelamento do alerta epidemiológico | `false` |
| [`alertas-envio`](alertas-envio/index.ts) | entrega o alerta semanal aos assinantes confirmados | `false` |

## Por que `verify_jwt: false`

Ambas são chamadas por quem **não tem JWT**: a de assinatura, por um visitante
anônimo do site; a de envio, pelo workflow do GitHub Actions. Cada uma
implementa a própria autenticação:

- `alertas-assinatura` é a fronteira: valida entrada, usa `service_role`
  server-side e só chama RPCs de operação única. O schema com os dados pessoais
  (`alertas`) não é alcançável pelo PostgREST público.
- `alertas-envio` exige o header `x-alertas-secret`, conferido contra
  `ALERTAS_ENVIO_SECRET`.

## Segredos necessários

Configurados no painel do Supabase (Project Settings → Edge Functions → Secrets):

| Segredo | Usado por | Obrigatório |
|---|---|---|
| `RESEND_API_KEY` | ambas | sim — sem ele o formulário nem aparece no site |
| `ALERTAS_REMETENTE` | ambas | não (padrão: `Saúde em Dado <alertas@saudeemdado.com>`) |
| `ALERTAS_ENVIO_SECRET` | `alertas-envio` | sim, e o **mesmo valor** precisa existir nos secrets do GitHub |

`SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` são injetados automaticamente.

## Implantar

```bash
supabase functions deploy alertas-assinatura --no-verify-jwt --project-ref zekjhmxjamatlxpkykde
```

```bash
supabase functions deploy alertas-envio --no-verify-jwt --project-ref zekjhmxjamatlxpkykde
```

## Diagnóstico

O `console.error` das funções aparece em **Edge Functions → \<função\> → Logs**
no painel — não nos registros de invocação da API de logs, que só trazem
método, rota e status.

Quando o provedor de e-mail recusa um envio, `alertas-assinatura` responde
**502** (não 500), registra o status e o corpo devolvidos pelo provedor, e
**desfaz a inscrição pendente** — senão o assinante ficaria sem link para
confirmar e travado pelo anti-abuso de uma hora na próxima tentativa.

Ver também [`docs/alertas-por-assinatura.md`](../../docs/alertas-por-assinatura.md).
