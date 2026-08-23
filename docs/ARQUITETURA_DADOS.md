# Arquitetura de dados — o que é canônico e por quê

Como o Saúde em Dado decide qual cópia dos dados é a verdade, como cada
publicação fica recuperável, e como as camadas são conferidas umas contra as
outras.

---

## O eixo

```
DataSUS / IBGE
      │
      ▼
scripts/ (DuckDB local)
      │
      ▼
Parquet datado + manifesto  ←──────────  CANÔNICO
      │
      ├──────────────┬──────────────────┐
      ▼              ▼                  ▼
Postgres         sdata (build)     download público
(servir)          derivado          o mesmo arquivo
```

**O arquivo é a verdade. O banco serve consultas.** Se as duas camadas
divergirem, o arquivo está certo e o banco precisa ser recarregado — nunca o
contrário.

## Por que o eixo mudou

Até 2026-08-23 a camada canônica de facto era o Postgres, e ela era a pior
candidata possível para o papel. Medido:

| | Postgres | Parquet |
|---|---:|---:|
| tamanho | **740 MB** | 26 MB |
| reconstruível a partir do repositório | **não** | sim |
| histórico de publicações | **nenhum** (sobrescrito) | por construção |
| cobertura | 35 tabelas | 21 arquivos (**60%**) |

Três coisas tornavam isso insustentável:

1. **57 migrações aplicadas, 47 delas com nome ad-hoc e sem arquivo no
   repositório.** Quem clonasse o repo e aplicasse `migrations/` em ordem não
   obtinha o banco que está no ar — obtinha outro banco.
2. **Nenhuma linha de código subia Parquet para o Storage.** A publicação de
   arquivo sempre foi manual. Daí as 14 tabelas sem arquivo nenhum, enquanto a
   página `/dados` chamava o conjunto de "a base completa".
3. **Marts sobrescritos no lugar.** O valor publicado em junho era
   irrecuperável em agosto.

Na primeira execução do publicador, dois arquivos publicados revelaram-se
desatualizados sem que ninguém soubesse: `mart_internacoes_agravo` tinha 52.861
linhas contra 158.041 no banco — **66% do dado faltando** — e
`mart_internacoes_municipio` divergia em 167 linhas. Os SHA-256 publicados
estavam corretos; os arquivos é que estavam velhos.

## O que é uma publicação

Um conjunto **imutável** de Parquet mais o manifesto que o descreve.

```
data/publicacoes/{id}.json     manifesto, versionado no git
data/publicacoes/atual.json    ponteiro para a publicação corrente
```

No Storage:

```
dados/{tabela}.parquet             estado ATUAL, caminho estável
dados/hist/{id}/{tabela}.parquet   cópia imutável daquela publicação
dados/publicacoes/{id}.json        o manifesto, também publicado
```

O caminho estável preserva todos os links e checksums já divulgados. O caminho
histórico só recebe cópia quando o conteúdo **muda** — tabela que não mudou entre
duas publicações não duplica bytes, e o manifesto aponta para a publicação em que
ela mudou pela última vez.

**O git guarda a verdade *sobre* os arquivos sem guardar os bytes.**

### O manifesto

Por tabela: linhas, bytes, SHA-256, colunas, faixa de competência, publicação de
origem e **linhagem**:

| origem | significado |
|---|---|
| `pipeline` | o Parquet saiu do pipeline que gera o dado — o estado desejado |
| `postgres-bootstrap` | foi reexportado do banco, porque era o único lugar onde o dado existia |
| `storage-legado` | já estava publicado à mão, antes de existir pipeline de publicação |

As duas últimas são **dívida declarada**. Reexportar do Postgres é justamente
devolver o eixo a ele; o campo existe para que isso seja mensurável em vez de
silencioso. A meta é `pipeline` em 100% das tabelas, e o resumo do manifesto
conta quantas faltam.

## Comandos

```bash
python scripts/publicar.py --simular        # mostra o plano, não envia nada
python scripts/publicar.py                  # publica o que mudou
python scripts/validar_camadas.py           # confere as quatro camadas
```

Na primeira publicação de uma máquina limpa:

```bash
python scripts/publicar.py --semear --bootstrap
```

`--semear` baixa do Storage o que já está publicado, em vez de reexportar do
Postgres: são 26 MB contra ~3.400 requisições ao PostgREST. E reexportar não é
neutro — um Parquet novo gerado das mesmas linhas pode ter SHA-256 diferente
(ordem de linhas, metadados do escritor), o que marcaria como "mudou" uma tabela
que não mudou e quebraria os checksums já publicados.

### Regra de segurança do publicador

Antes de publicar, cada Parquet é conferido contra a contagem da tabela servida
pela API. **Arquivo que não bate com o banco não é publicado** — é justamente
essa checagem que revelou os dois arquivos desatualizados.

O publicador **não escreve no Postgres**. Enquanto o eixo migra, publicar não
pode ser capaz de corromper a cópia que ainda é canônica de facto.

## Validação entre camadas

`validar_camadas.py` confere cinco coisas, e sai com código ≠ 0 em qualquer
divergência:

| # | checagem | o que pegaria |
|---|---|---|
| 1 | manifesto → Storage | arquivo ausente ou SHA-256 diferente |
| 2 | manifesto → Postgres | contagem de linhas divergente |
| 3 | histórico | cópia imutável apagada, quebrando uma publicação antiga |
| 4 | **cobertura** | tabela servida pela API sem arquivo publicado |
| 5 | manifesto → `sdata` | série congelada no site que envelheceu |

O item 4 lê o **OpenAPI do próprio PostgREST**, não uma lista escrita à mão:
tabela nova aparece sozinha e passa a exigir explicação. É o item que teria
pego o defeito original — 14 tabelas servidas sem arquivo, por dois meses.

## Esquema

`migrations/` **não reproduz** este banco. Das 57 migrações aplicadas em
produção, 47 foram feitas ad-hoc, sem arquivo no repositório; 13 arquivos do
repositório nunca foram aplicados. Quem clonar e aplicar `migrations/` em ordem
obtém **outro banco**.

O artefato confiável é `migrations/schema/schema.sql` — **126 objetos** (36
tabelas, 17 índices, 36 RLS, 36 policies, 1 view), extraídos do catálogo:

```bash
python scripts/gerar_schema.py             # regera o arquivo
python scripts/gerar_schema.py --conferir  # falha se o banco divergiu do git
```

A extração é **por script, não manual** — passo manual é exatamente o que
produziu as 47 migrações ad-hoc. Ela chama `public.gerar_schema_ddl()`
(migração V028), uma função `SECURITY DEFINER` com `search_path` fixo, sem
parâmetros e executável apenas por `service_role`.

`--conferir` é o modo de CI: compara o arquivo versionado com o banco e emite um
diff unificado da divergência. Verificado injetando uma coluna fantasma no
arquivo — o detector apontou a linha exata e saiu com código 1.

**Migrações continuam valendo.** Elas registram a *intenção* e o *porquê* de cada
mudança; `schema.sql` registra o *estado*. Um não substitui o outro — o que não
existia era o segundo.

A separação é deliberada: **esquema e conteúdo são camadas distintas**. O esquema
vem de `schema.sql`; o conteúdo vem dos Parquet descritos em
`data/publicacoes/`. Reconstruir o banco é aplicar um e carregar o outro.

## No CI

`validate-data.yml` roda três jobs:

| job | credencial | o que garante |
|---|---|---|
| `dados` | nenhuma | invariantes da base publicada |
| `camadas` | nenhuma (4 de 5 checagens) | coerência manifesto × Storage × Postgres × sdata |
| `esquema` | `SUPABASE_SERVICE_ROLE_KEY` | `schema.sql` corresponde ao banco |

**O repositório não tem nenhum segredo configurado hoje** (`gh api …/secrets`
devolve `total_count: 0`). Por isso o job `camadas` foi desenhado para rodar sem
credencial: quatro checagens usam só a chave pública de leitura, já embutida em
`validate_data.py` e no site. A quinta — cobertura, que lê o OpenAPI do
PostgREST — se anuncia como **PULADA** em vez de falhar ou de passar em
silêncio, e o job emite um `::warning::`.

Enquanto `SUPABASE_SERVICE_ROLE_KEY` não for configurado como segredo, a
checagem de cobertura e a de deriva de esquema **não rodam em CI** — só na
máquina de quem publica.

## Consequências

**Banco pequeno** deixa de ser meta e vira decisão: se o arquivo é a verdade, o
que fica no Postgres é só o que precisa ser consultado por API, e nada mais. As
três maiores tabelas somam 50% dos 740 MB.

**dbt** fica incompatível com "uma única fonte canônica": uma segunda camada de
modelagem, com namespace disjunto e **zero objetos materializados** nos schemas
`staging`/`intermediate`/`marts` em dois meses, não tem lugar nesta arquitetura.

## O que ainda não está pronto

| item | estado |
|---|---|
| pipelines escrevendo Parquet canônico direto | parcial — 3 de 36 (`pipeline`); 17 em `postgres-bootstrap`, 16 em `storage-legado` |
| rebuild do Postgres a partir dos Parquet | **não implementado** — é o que provaria a reprodutibilidade de ponta a ponta |
| redução do banco | não iniciada — depende do rebuild |
| segredo `SUPABASE_SERVICE_ROLE_KEY` no CI | ausente: cobertura e deriva de esquema não rodam em CI |
| `snapshot_publicacao` (V026) | continua sem aplicar — o histórico agora vem das publicações, e a tabela precisa ser reavaliada ou aposentada |
| dbt | decisão pendente; incompatível com fonte canônica única |
