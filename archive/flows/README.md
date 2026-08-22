# `flows/` — orquestração Prefect

Aposentado em 2026-08-22. **Nada aqui é executado**: nenhum agendador, nenhum
deployment, nenhum workflow do GitHub Actions.

Sete flows do Prefect 2.x que orquestravam a ingestão semanal (`weekly_ingest*`)
e o `dbt build` (`dbt_run.py`).

---

## A evidência

### 1. Não existe agendador — em lugar nenhum

Varredura por `prefect` no repositório inteiro, fora deste diretório: nenhum
`prefect deployment`, nenhum `serve()`, nenhum `.prefect/`, nenhum workflow que
chame um flow. As únicas ocorrências são a dependência em `requirements.txt`,
uma menção em `docs/architecture/adr-002-dbt-supabase.md` e o
`docs/architecture/c4-diagram.md` — os dois documentos **históricos**, que
descrevem a arquitetura planejada em 2023.

O próprio `README.md` já registrava o fato: *"flows Prefect (sem agendador ativo
hoje)"*.

### 2. Orquestravam código que não roda

Todos os sete importam `ingestion/`, agora em [`../ingestion/`](../ingestion/) —
ver a evidência lá. Dois casos são conclusivos por si:

- `weekly_ingest_nacional.py` importa `ingestion.ingest_all_states`, um módulo
  que levanta `NameError` no import desde 2026-06-10.
- `dbt_run.py` dispara `dbt build`, cujos marts (`mart_mortalidade`,
  `mart_internacoes`) alimentavam a API FastAPI que já está em
  [`../api/`](../api/).

Fora de `ingestion/`, ninguém importa `flows/`.

### 3. O CI exclui o Prefect de propósito

`requirements-test.txt` deixa `prefect` de fora, com o motivo escrito no próprio
arquivo: a suíte não importa nada disso. Um flow que o ambiente de teste não
consegue nem importar não é código que alguém pretenda executar.

### 4. Cronologia

Último commit tocando `flows/`: `b50a10e`, 2026-06-10. `scripts/` — os pipelines
que realmente publicam — seguiu até 2026-08-18.

---

## Por que só agora

O `archive/README.md` registrava esta decisão como pendente:

> **`flows/` continua na raiz** — flows do Prefect que orquestram `ingestion/`,
> que é código vivo. [...] Arquivá-los é decisão de produto (o Prefect foi
> abandonado ou é caminho a retomar?), não conclusão de evidência.

A premissa estava errada. `ingestion/` não era código vivo: nada o importava,
as tabelas que escrevia não são as que estão publicadas, e seu módulo de entrada
não era nem importável. Com isso, arquivar `flows/` deixa de ser decisão de
produto e passa a ser o que aquela nota pedia — conclusão de evidência.

Retomar orquestração continua possível; o histórico está intacto. Mas o ponto de
partida seria orquestrar `scripts/`, que é o que publica hoje, e não estes flows,
que apontam para uma camada `*_raw` → dbt que ninguém consome.

---

## Nota sobre os imports

Os arquivos ainda dizem `from ingestion.ingest_sim import ...`. Esses caminhos
não resolvem mais. É intencional: código arquivado não roda, e reescrever os
imports daria a impressão de que roda.
