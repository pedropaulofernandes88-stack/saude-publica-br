# Auditoria de segurança e supply chain

**Data:** 2026-08-22 · **Escopo:** dependências Node e Python, workflows,
segredos, superfície de exposição do banco e das Edge Functions.

---

## Resumo executivo

O `npm audit` acusava **3 vulnerabilidades de alta severidade**. Duas foram
corrigidas dentro do mesmo major, sem risco; a terceira **não é alcançável nesta
arquitetura** e foi reclassificada com justificativa, em vez de "corrigida" com
um salto de dois majors no único componente que gera o site.

O `pip-audit` — que nunca havia sido executado neste projeto — encontrou **5
vulnerabilidades em 3 pacotes** que ninguém sabia existirem. Todas corrigidas.

| | antes | depois |
|---|---:|---:|
| npm audit (alta) | 3 | **1** (reclassificada, documentada) |
| pip-audit | não executado | **0** |
| Dependabot | ausente | 3 ecossistemas, cadência mensal |
| audit no CI | ausente | job informativo (npm + pip) |
| advisors do Supabase | 1 INFO | 1 INFO (correto por desenho) |

A postura de segurança do **banco** já era boa e continua: chave `anon` tratada
como pública, escrita separada por `service_role`, migrações revogando escrita e
`TRUNCATE` do `anon`, e nenhuma tabela de microdado exposta.

---

## 1. Node — o que foi encontrado

`site/package.json`, Next.js 14.2.33, exportação estática.

### 1.1 `postcss` ≤8.5.22 — **corrigido**

| | |
|---|---|
| Advisories | GHSA-qx2v-qp2m-jg93, GHSA-6g55-p6wh-862q, GHSA-fxqj-rqcc-2cmp, GHSA-r28c-9q8g-f849 |
| Instalada | 8.4.49 (direta) + 8.4.31 (transitiva, via `next`) |
| Superfície | **build**, não runtime |
| Risco real | **baixo** — exige CSS não confiável entrando no build; o CSS vem do repositório e do Tailwind |
| Ação | direta → `8.5.26`; transitiva coberta por `overrides` |

### 1.2 `nanoid` ≤3.3.17 — **corrigido**

| | |
|---|---|
| Advisories | GHSA-28wg-ghj8-5hjv, GHSA-2v37-7h3g-55p8 |
| Instalada | 3.3.12 (transitiva, via `postcss` ← `next`) |
| Superfície | build |
| Risco real | **muito baixo** — loop infinito com `size` negativo ou zero; nada no build passa `size` controlado externamente |
| Ação | `overrides` → `3.3.18` |

Verificação após a mudança:

```
+-- next@14.2.33
| `-- postcss@8.5.26 deduped
+-- postcss@8.5.26 overridden
| `-- nanoid@3.3.18 overridden
```

### 1.3 `next` 14.2.33 — **reclassificado, não corrigido**

23 advisories, entre eles SSRF em rewrites e Server Actions, cache poisoning de
RSC, DoS no Image Optimizer, bypass de middleware com i18n, XSS com nonce de CSP.

**Todos exigem o runtime de servidor do Next.** Esta aplicação não tem um:

| condição verificada | evidência |
|---|---|
| exportação estática | `site/next.config.mjs`: `output: "export"` |
| sem otimizador de imagem | `images: { unoptimized: true }` |
| sem middleware | nenhum `site/middleware.*` |
| sem Server Actions | zero ocorrências de `"use server"` em `site/` |
| hospedagem | GitHub Pages — servidor de arquivos estáticos, sem Node |
| API | PostgREST do Supabase, não rota do Next |

O que o `npm audit` oferece como correção é **`next@16.3.2` — dois majors**, no
único componente que produz as 28 páginas publicadas. Risco de regressão real,
ganho de segurança em produção nulo.

**Decisão: não atualizar agora.** Registrada como decisão consciente, não como
alerta ignorado. O `next` está no `ignore` do Dependabot para major, justamente
para que o salto, quando acontecer, seja deliberado e com build comparado.

**Risco residual:** a superfície de *build* permanece. Se um dia o build passar a
consumir conteúdo de terceiro (CSS, MDX ou dado remoto), esta análise precisa ser
refeita — a conclusão depende da arquitetura, não do pacote.

---

## 2. Python — o que foi encontrado

`pip-audit` nunca havia sido executado. Cinco vulnerabilidades em três pacotes:

| pacote | versão | advisory | origem | risco real | ação |
|---|---|---|---|---|---|
| `cryptography` | 48.0.1 | PYSEC-2026-3552 | transitiva (`great-expectations`, `PyJWT`) | **baixo** — oráculo de padding em `pkcs7_decrypt_*`; o projeto não decifra PKCS#7 | → 50.0.0 |
| `cryptography` | 48.0.1 | PYSEC-2026-3553 | idem | **baixo** — blowup exponencial em cadeia de certificado inválida | → 50.0.0 |
| `cryptography` | 48.0.1 | PYSEC-2026-3554 | idem | **baixo** — curinga escapa restrição de nome de CA intermediária | → 50.0.0 |
| `pydantic-settings` | 2.14.1 | GHSA-4xgf-cpjx-pc3j | direta | **nulo** — exige `NestedSecretsSettingsSource` com `secrets_nested_subdir`; não usado | → 2.14.2 |
| `starlette` | 1.3.0 | PYSEC-2026-249 | transitiva (SDK `mcp`) | **baixo** — limites ignorados em `x-www-form-urlencoded`; o servidor MCP fala por **stdio**, sem parsing de formulário | → 1.3.1+ |

Após a correção: **`No known vulnerabilities found`**.

Pisos explícitos foram acrescentados a `requirements.txt` e
`requirements-test.txt` para que uma instalação nova não regrida às versões
vulneráveis.

**Risco residual:** o projeto **não tem lockfile Python**. `requirements.txt` usa
limites mínimos, então duas instalações em datas diferentes podem produzir
árvores diferentes. É a maior lacuna de reprodutibilidade que resta, e está na
lista de recomendações.

---

## 3. Segredos e credenciais

| item | situação |
|---|---|
| `.env` versionado? | **não** — `.gitignore` cobre `.env` e `.env.*`, exceto `*.example` |
| chave no código cliente | `site/lib/api.ts` traz a chave **`anon`** com `role: "anon"` — pública por desenho do PostgREST, é assim que se usa |
| `SERVICE_ROLE` | nunca no repositório; lida de ambiente por `scripts/_supabase_key.py` |
| segredos em workflow | via `secrets.*`; nenhum valor literal |
| `.env.example` | só nomes e formatos |

**A chave `anon` no código cliente só é segura se a autorização estiver no
banco.** Verificado:

- V022 revoga escrita do `anon`; V023 revoga `TRUNCATE` e escrita em views;
- V025 põe `security_invoker` na view de pares;
- advisor de segurança do Supabase: **1 INFO**, `alertas.assinantes` com RLS
  habilitado e sem policy — que é o comportamento correto (nega tudo ao `anon`;
  o acesso é por `service_role`).

### Achado: migrações de microdado reaproveitáveis

`migrations/V011` cria policy de leitura pública para `sinan_notificacoes`, que
contém data de nascimento, sexo, raça, gestação e datas clínicas. Consulta ao
`information_schema` de produção:

```
sinan_notificacoes, sim_do_raw, sih_aih_raw,
cnes_estabelecimentos, cnes_leitos, api_keys, dashboards  →  nenhuma existe
```

**Exposição atual: zero.** O risco é latente: aplicar essas migrações em outro
ambiente contradiria a promessa de "apenas agregados". Recomendação em aberto —
arquivar as migrações de microdado junto com a stack a que pertenciam, como já
foi feito com V006.

---

## 4. Edge Functions

### Corrigido — `alertas-envio` retornava sucesso com falha de entrega

`ok: true` era emitido incondicionalmente, com `falhas` num campo ao lado, e o
workflow decidia por `grep '"ok":true'`. **Uma edição em que todos os e-mails
falhassem saía verde no Actions.** Falha silenciosa em canal de alerta
epidemiológico é o pior modo de falha possível: o sistema afirma ter avisado.

Agora `ok` reflete a entrega, o status HTTP distingue os casos (200 completo ·
207 parcial · 502 nenhuma entrega) e o workflow lê o status além do corpo.

### Corrigido — HTML de e-mail sem escape

Nome de município, nome de doença e rótulo de nível vinham do InfoDengue e eram
interpolados direto no HTML; `permalink` e link de cancelamento iam para `href`.
Adicionados `esc()` para texto e `escUrl()` para atributo — este último só aceita
`http(s)`, bloqueando `javascript:` e `data:`.

Origem hoje é confiável, mas o destino é a caixa de entrada de assinantes, onde
não há CSP para segurar nada.

### Em aberto — rate limiting da inscrição

Há limite por endereço, mas não por IP nem global. Um atacante pode consumir
quota do provedor disparando confirmações para muitos endereços. Não corrigido
nesta rodada.

### Em aberto — sem harness de teste

`supabase/functions/` não tem execução de teste em lugar nenhum. As correções
acima foram verificadas por leitura e checagem sintática, **não por teste
automatizado**. É a lacuna de verificação mais relevante que resta.

---

## 5. Cabeçalhos HTTP

O GitHub Pages não emite CSP, HSTS, `Referrer-Policy`, `Permissions-Policy` nem
proteção contra framing, e **não permite configurá-los**. Para um site estático
sem autenticação, sem cookie e sem formulário que envie dado a si próprio, o
risco é baixo. Um proxy (Cloudflare à frente do Pages) resolveria; hoje seria a
primeira dependência de infraestrutura externa do projeto. Não feito.

---

## 6. Automação criada

### Dependabot (`.github/dependabot.yml`)

Três ecossistemas — npm (`/site`), pip (`/`) e github-actions — em cadência
**mensal**, com agrupamento de minor+patch.

Mensal, e não semanal, porque o projeto tem um mantenedor: PR de dependência que
ninguém revisa não é segurança, é ruído que treina o mantenedor a ignorar a caixa
de entrada. Major de `next`, `react` e `react-dom` estão no `ignore` — são
decisões de arquitetura.

### Job `supply-chain` no CI

`npm audit --audit-level=high` e `pip-audit`, **`continue-on-error: true`**.

Informativo por decisão explícita: o alerta que sobra é o do Next, inalcançável
aqui. Um job bloqueante travaria a main indefinidamente por um risco que não
existe, e o desfecho previsível seria alguém desligar o job. Informativo, ele
continua mostrando o que aparecer de **novo** — que é o que se quer vigiar.

---

## 7. Testes executados

| verificação | resultado |
|---|---|
| `npm audit` (depois) | 1 alta (Next, reclassificada) |
| `npm ci` | ok, árvore com overrides aplicados |
| `npx tsc --noEmit` | ok |
| `npm test` | 23/23 |
| `npm run build` | ok, 28 páginas |
| `pip-audit` | `No known vulnerabilities found` |
| `pytest tests/` | 469/469, 0 skip |
| `ruff --select F` | limpo em `scripts`, `mcp_server`, `clients`, `validation` |
| advisors do Supabase | 1 INFO (correto) |
| YAML dos workflows | 8 arquivos válidos |

---

## 8. Riscos residuais

1. **Sem lockfile Python.** Instalações em datas diferentes produzem árvores
   diferentes. Maior lacuna de reprodutibilidade.
2. **Next 14 com advisories abertos.** Inalcançáveis hoje; a conclusão depende de
   o site continuar estático. Reavaliar se a arquitetura mudar.
3. **Edge Functions sem teste.** Correções verificadas por leitura.
4. **Migrações de microdado no repositório.** Zero exposição hoje, risco latente.
5. **Sem rate limiting por IP** na inscrição de alertas.
6. **Sem cabeçalhos de segurança**, por limitação do GitHub Pages.
7. **`ingestion/` e `flows/` fora do lint do CI**, com 30 ocorrências F —
   incluindo 5 `F821` que seriam `NameError`. Código da arquitetura antiga que
   nenhum workflow executa; decisão de arquivar ou consertar em aberto.

## 9. Recomendações

| prioridade | item |
|---|---|
| alta | lockfile Python (`uv.lock` ou `pip-compile` com hashes) |
| alta | harness de teste para as Edge Functions |
| média | arquivar as migrações de microdado da stack antiga |
| média | rate limiting por IP na inscrição |
| baixa | avaliar `next@16` em branch separada, com export comparado |
| baixa | cabeçalhos de segurança via proxy, se um dia houver proxy |
