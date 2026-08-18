# Política de segurança

## Como relatar

Vulnerabilidades devem ir para **pedropaulofernandes88@gmail.com**, não para uma
issue pública. Descreva o que observou, como reproduzir e o impacto que enxerga.
Respondo em até 7 dias.

Se preferir o canal do GitHub, use
[Security advisories](https://github.com/pedropaulofernandes88-stack/saude-publica-br/security/advisories/new),
que fica privado até a publicação.

## Antes de relatar: o que *não* é vazamento aqui

Este projeto já consumiu uma investigação inteira por causa de um alarme falso.
Vale ler esta seção antes de abrir um relato.

### A chave `anon` do Supabase é pública por desenho

Ela aparece em código, no HTML do site e nesta documentação — **de propósito**.
É o mecanismo do PostgREST para expor uma API de leitura sem cadastro, e é o que
permite consultar a base com um `curl` só. O que a protege não é o segredo, é a
RLS: o banco aceita apenas `SELECT`, e as migrations que fecham escrita e
`TRUNCATE` para o papel `anon` estão versionadas (`V022`, `V023`, `V025`).

Encontrar essa chave em um arquivo não é um achado de segurança.

### Arquivos `.env` versionados são *templates*

`.env.example` e `archive/deploy/.env.production.example` contêm apenas
placeholders (`GERE_COM_openssl_rand_hex_32`, `TROQUE_ESTA_SENHA`). O
`.gitignore` bloqueia `.env` e `.env.*`, reabrindo só o sufixo `.example` — um
arquivo real preenchido fica invisível ao `git add`.

Se você encontrar um valor concreto num arquivo versionado, aí sim é relato
válido: descreva **qual arquivo e qual linha**, sem reproduzir o valor.

## O que é levado a sério

- Chave `service_role` do Supabase exposta em qualquer lugar — ela escreve.
- Qualquer caminho que permita escrita, `UPDATE`, `DELETE` ou `TRUNCATE` pela
  chave `anon`.
- Falha na RLS que exponha a tabela `alertas.assinantes` (endereços de e-mail de
  quem assina o boletim).
- Execução de código no pipeline a partir de dado baixado do DataSUS.
- Comprometimento da publicação no PyPI (`saudeemdado-mcp`) ou do deploy do site.

## O que este projeto não tem

Não há autenticação de usuário, sessão, pagamento nem dado pessoal identificável.
Os microdados do DataSUS entram já desidentificados e **só agregados** são
publicados — nenhum registro individual sai da máquina de processamento.

## Escopo

| Componente | Coberto |
|---|---|
| `site/`, `scripts/`, `mcp_server/`, `clients/` | sim |
| Migrations e políticas RLS em `migrations/` | sim |
| Edge Functions em `supabase/` | sim |
| `archive/` | **não** — código aposentado, não implantado em lugar nenhum |
