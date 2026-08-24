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

## Integridade da coleta

A validação entre camadas confere que o Parquet, o Storage e o Postgres contam
a mesma história. Ela **não** confere que a história está completa: se o mês de
fevereiro nunca entrou no cálculo, as três camadas concordam em um número
errado.

Foi o que aconteceu. Os pipelines do SIH tinham, todos, esta forma:

```python
try:
    ftp.size(f"{FTP_DIR}/{nome}.dbc")
except Exception:
    return None          # "mês inexistente"
```

Qualquer falha — recusa de conexão, timeout, DBC truncado — virava o mesmo
`None` de um mês que ainda não foi publicado, e o laço seguia adiante. Como o
FTP do DataSUS recusa conexões concorrentes e o pipeline abria seis, meses
inteiros sumiam. O checkpoint era gravado como se o ano estivesse completo, e
checkpoint não se refaz: a perda ficava congelada.

Medido em 2026-08-23, comparando os checkpoints de julho com os de 11 de agosto:

| checkpoint | perda | causa |
|---|---|---|
| fluxo/ICSAP `MA 2023` | −41% (198.854 internações) | 5 meses |
| fluxo/ICSAP `AM 2024` | −17% (37.799) | 2 meses |
| demanda `PB 2022` | −18% | meses 05 e 06 |
| demanda `PE 2022` | −8% | mês 11 |
| demanda `GO 2023` | −8% | mês 02 |
| agravo `RR 2022` | −7% | 1 mês |

Nada disso disparou alarme: os pipelines terminaram com código 0 e números
plausíveis. O que denunciou foi um resíduo — 210 pares de fluxo que existiam no
Postgres e não no Parquet recalculado. A investigação começou supondo revisão do
DataSUS; a fonte estava intacta, quem perdia dado era o nosso lado.

`scripts/_datasus_ftp.py` fecha isso com três invariantes:

1. **ausência e falha são exceções diferentes.** `ArquivoAusente` quando o nome
   não está na listagem do diretório (competência futura — pular é correto);
   `FalhaDeColeta` quando ele está e a coleta falhou, depois de 4 tentativas com
   espera crescente.
2. **o ano só fecha completo.** Os meses vêm da listagem do FTP, não de
   `range(1, 13)`; o que falhar em paralelo é refeito em série (uma conexão
   costuma passar onde seis foram recusadas); e se ainda faltar um mês
   publicado, o pipeline levanta exceção **sem gravar checkpoint**.
3. **o checkpoint declara de quantos meses veio.** A lista fica nos metadados
   Arrow do próprio arquivo — como a linhagem, viaja com os bytes. Na execução
   seguinte, um checkpoint que não cobre os meses hoje publicados é recalculado
   em vez de reaproveitado; é assim que a competência nova entra sozinha.

Checkpoints anteriores a essa guarda não têm o carimbo e seguem válidos — quem
quer certeza apaga o arquivo e deixa refazer.

### A reconstrução total, e o que ela provou

Em 2026-08-24 os **351 anos-UF** das quatro famílias foram refeitos do zero:
cada arquivo RD de 2021–2024 baixado de novo, nenhum estado anterior
reaproveitado. Doze horas de coleta, e o resultado é o seguinte:

| comparação | resultado |
|---|---|
| checkpoints refeitos × backup | **459 de 459 idênticos** |
| marts reconstruídos × publicados | 8 de 8 com conteúdo idêntico |
| anos-UF com carimbo de 12 meses | 351 de 351 |

Nenhuma divergência. Isso encerra a dúvida que a conferência cruzada só
podia indicar por inferência: **fora os seis anos-UF corrigidos em 2026-08-23,
não havia outra perda silenciosa na base**. E, como todo checkpoint passou a
declarar de que meses veio, a garantia deixa de depender de comparação com um
backup — passa a ser propriedade do próprio arquivo.

Os marts refeitos **não** foram republicados: o conteúdo é o mesmo, e trocar
bytes idênticos invalidaria os SHA-256 já divulgados sem entregar nada. A única
diferença encontrada foi cosmética — em `mart_internacoes_municipio`, a coluna
`populacao` saiu como `Int64` em vez de `Float64`, com valores iguais.


## Esquema

`migrations/` **não reproduz** este banco. Das 57 migrações aplicadas em
produção, 47 foram feitas ad-hoc, sem arquivo no repositório; 13 arquivos do
repositório nunca foram aplicados. Quem clonar e aplicar `migrations/` em ordem
obtém **outro banco**.

O artefato confiável é `migrations/schema/schema.sql` — **200 objetos** dos
schemas `public` e `alertas` (37 tabelas, 20 índices, 10 funções, 37 RLS, 36
policies, 1 view e 58 comentários), extraídos do catálogo:

```bash
python scripts/gerar_schema.py             # regera o arquivo
python scripts/gerar_schema.py --conferir  # falha se o banco divergiu do git
```

A extração é **por script, não manual** — passo manual é exatamente o que
produziu as 47 migrações ad-hoc. Ela chama `public.gerar_schema_ddl()`
(migrações V028–V030), uma função `SECURITY DEFINER` com `search_path` fixo, sem
parâmetros e executável apenas por `service_role`.

Ela cobre **apenas estrutura, nenhuma linha de dado** — inclusive em `alertas`,
cuja tabela de assinantes tem o esquema reproduzido e o conteúdo não. As três
lacunas que o preparo do rebuild revelou (opções da view, comentários e funções)
entraram nas V029 e V030.

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

`validate-data.yml` roda quatro jobs:

| job | credencial | o que garante |
|---|---|---|
| `dados` | nenhuma | invariantes da base publicada |
| `camadas` | nenhuma (4 de 5 checagens) | coerência manifesto × Storage × Postgres × sdata |
| `esquema` | `SUPABASE_SERVICE_ROLE_KEY` | `schema.sql` corresponde ao banco |
| `reconstrucao` | nenhuma | **o repositório reconstrói o banco** |

### O rebuild

`scripts/reconstruir.py` levanta um Postgres 17 descartável no runner, aplica as
200 instruções do `schema.sql` e carrega os Parquet do manifesto. Em **48
segundos** ele verifica 4,2 milhões de linhas em 36 tabelas, mais 36 policies,
58 comentários, 10 funções, 37 tabelas com RLS, o schema `alertas` e o
`security_invoker` da view.

As expectativas são **derivadas do próprio `schema.sql` aplicado**, não de
constantes: a checagem acompanha o esquema em vez de envelhecer com ele.

Guardas: recusa destino que contenha o identificador de produção ou pareça
Supabase gerenciado, e recusa banco que já tenha tabelas.

**O repositório não tem nenhum segredo configurado hoje** (`gh api …/secrets`
devolve `total_count: 0`). Por isso o job `camadas` foi desenhado para rodar sem
credencial: quatro checagens usam só a chave pública de leitura, já embutida em
`validate_data.py` e no site. A quinta — cobertura, que lê o OpenAPI do
PostgREST — se anuncia como **PULADA** em vez de falhar ou de passar em
silêncio, e o job emite um `::warning::`.

`SUPABASE_SERVICE_ROLE_KEY` foi configurado como segredo em **2026-08-24**, e a
primeira execução do job de esquema — que até então vivia **pulado** — falhou na
hora: ele instalava só `requests`, e `gerar_schema.py` importa `_publicacao`, que
importa pandas. O job estava quebrado desde que foi escrito, e ninguém podia
saber, porque nunca tinha executado. **Job que não roda não é job que passa** —
vale reler isso antes de confiar em qualquer check condicional.

## Consequências

**Banco pequeno** deixa de ser meta e vira decisão: se o arquivo é a verdade, o
que fica no Postgres é só o que precisa ser consultado por API, e nada mais. As
três maiores tabelas somam 50% dos 740 MB.

**dbt** fica incompatível com "uma única fonte canônica": uma segunda camada de
modelagem, com namespace disjunto e **zero objetos materializados** nos schemas
`staging`/`intermediate`/`marts` em dois meses, não tem lugar nesta arquitetura.

## Tamanho do banco

**740 MB → 607 MB** em 2026-08-23: 133 MB (18%) recuperados por `VACUUM FULL`,
sem perder uma linha e com a API verificada depois.

| tabela | antes | depois | bytes/linha |
|---|---:|---:|---|
| `mart_internacoes_agravo` | 61 MB | 35 MB | 323 → 194 |
| `mart_internacoes_municipio` | 111 MB | 67 MB | 200 → 154 |
| `mart_los_hospital` | 59 MB | 31 MB | 180 → 95 |

`mart_internacoes_municipio` chegou a reportar 411 mil linhas vivas tendo
334.769 — 76 mil fantasmas. O inchaço veio dos upserts e do `DELETE + INSERT`
que o pipeline de forecast faz a cada execução.

```bash
python scripts/diagnostico_banco.py --limite-mb 700
```

Ganho de faxina volta, então a medição virou parte do CI. A **medição** é
automatizável por RPC (`diagnostico_banco()`, V031); a **ação** não — `VACUUM`
não roda dentro de função nem de transação, e o projeto não guarda senha de
banco. O script mede, avisa e imprime os comandos exatos; compactar é manual.
Declarar a limitação é melhor que fingir automação que não existe.

### O que ainda pesa, e por que não foi mexido

| oportunidade | ganho | por que não |
|---|---:|---|
| texto denormalizado (`municipio_nome`, `uf_sigla`, `regiao` repetidos linha a linha) | ~61 MB | remover quebra o contrato da API pública, que serve essas colunas |
| `numeric` → `real` nas colunas de taxa | dezenas de MB | muda a precisão de dado publicado |
| linhas `sexo != 'TOTAL'` em `mart_mortalidade_municipio` | ~2/3 de 180 MB | reduz a granularidade que a plataforma publica |
| `idx_mm_uf_ano` e `idx_intern_uf_ano` | ~10 MB | 38 e 6 buscas em 3 meses, mas o site filtra por UF; o ganho não paga o risco |

As três primeiras são decisões de produto, não de engenharia: mudam o que a
plataforma entrega. Ficam registradas com o número ao lado para que a escolha
seja informada.

## Medir a revisão da fonte

O DataSUS revisa dado já publicado, e nenhuma fonte pública guarda a série das
próprias revisões: o TABNET entrega o número de hoje e não tem memória. Saber
**quanto** um preliminar ainda se move era o objetivo da V026
`snapshot_publicacao`, escrita quando cada publicação sobrescrevia a anterior.

Com o eixo invertido, a tabela virou cópia pior de algo que já existe. Toda
publicação deixa uma cópia imutável em `dados/hist/{id}/{tabela}.parquet`, e
isso é a série de snapshots — sem perda (guarda a tabela inteira, não um
agregado escolhido de antemão), sem segunda via de escrita que possa divergir
do arquivo, e retroativa. A análise de revisão passa a ser uma **leitura** sobre
o histórico, não uma tabela nova. A V026 foi aposentada em
`migrations/archive/`, com o raciocínio preservado.

O que ainda falta para a resposta ser honesta é tempo: em 2026-08-24 são 10
publicações, quase todas do mesmo par de dias. A diferença é que agora **haverá**
o que observar — os checkpoints carimbam a versão da fonte e se invalidam
sozinhos quando ela é reescrita, então reingerir produz diferença real em vez de
repetir o valor anterior.

## O que ainda não está pronto

| item | estado |
|---|---|
| pipelines escrevendo Parquet canônico direto | **19 de 36** em `pipeline`; 2 em `postgres-bootstrap`, 14 em `storage-legado` |
| segredo `SUPABASE_SERVICE_ROLE_KEY` no CI | **configurado** em 2026-08-24; os quatro jobs rodam de verdade |
| `snapshot_publicacao` (V026) | **aposentada** — ver `migrations/archive/README.md` |
| dbt | decisão pendente; incompatível com fonte canônica única |
