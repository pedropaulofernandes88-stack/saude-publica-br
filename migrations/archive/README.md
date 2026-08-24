# Migrações escritas e não aplicadas

O que está aqui **não faz parte do banco** e não deve ser aplicado. Fica
versionado porque o raciocínio custou caro e a pergunta que motivou cada
arquivo continua válida — só a resposta mudou.

---

## V026 — `snapshot_publicacao`

**Aposentada em 2026-08-24. Nunca foi aplicada em produção.**

### A pergunta que ela fazia, e que continua boa

O DataSUS revisa dado já publicado: óbito registrado com atraso, causa mal
definida corrigida. O número muda sem aviso, e nenhuma fonte pública guarda a
série das próprias revisões — o TABNET entrega o valor de hoje e não tem
memória. "2024 é preliminar" é um aviso qualitativo; a pergunta certa é
**preliminar quanto**.

A tabela guardaria, por `(base, métrica, competência, UF, data de extração)`, o
valor que aquela competência tinha em cada leitura da fonte, e a view
`vw_revisao_publicacao` calcularia a revisão entre leituras consecutivas.

### Por que ela não é mais o caminho

Quando ela foi escrita, o Postgres era a camada canônica de facto e cada
publicação sobrescrevia a anterior — não havia registro do que um número valia
no mês passado. Guardar snapshots numa tabela à parte era a única forma de ter
memória.

Em 2026-08-23 o eixo foi invertido: **o Parquet datado passou a ser canônico**, e
toda publicação vira uma cópia imutável em `dados/hist/{id}/{tabela}.parquet`,
com manifesto versionado no git. Isso já é a série de snapshots — e é melhor do
que a tabela seria em três pontos:

- **sem perda.** A tabela guardaria UF × competência, agregado escolhido de
  antemão. O histórico guarda a tabela inteira: qualquer recorte, inclusive os
  que ninguém previu, continua calculável depois.
- **sem segunda via de escrita.** Uma tabela alimentada por outro caminho pode
  divergir do arquivo que ela diz resumir. O histórico é o próprio arquivo.
- **retroativo.** Toda publicação já feita conta como ponto da série, sem
  precisar que alguém tivesse lembrado de gravar snapshot naquele dia.

A análise de revisão passa a ser uma **leitura** sobre `hist/`, não uma
tabela nova: baixar duas publicações da mesma tabela e comparar. Quando houver
publicações suficientes espaçadas no tempo para a resposta ser honesta, o lugar
dela é um script de análise — não um write path permanente.

### O que a série ainda não permite dizer

Em 2026-08-24 existem 10 publicações, quase todas do mesmo par de dias. Série
curta não prevê: enquanto não houver reingestões espaçadas de uma mesma
competência, qualquer projeção de "quanto ainda falta" é chute com aparência de
estatística. O que mudou é que agora **haverá** o que observar — os checkpoints
carimbam a versão da fonte e se invalidam sozinhos quando o DataSUS reescreve,
então reingerir passou a produzir diferença real em vez de repetir o valor
anterior.

### `backfill_snapshot.py`

Arquivado junto. A hipótese dele era que `site/public/sdata/*.json`, por ser
gerado no build e versionado, já conteria uma série temporal de extrações
acumulada sem querer. **A hipótese foi medida e refutada:** dois commits por
série, conteúdo idêntico, zero revisões observáveis — e cinco boletins semanais
entre 2026-07-23 e 2026-08-17 repetindo os mesmos dígitos, o que mostrava não
que a fonte era estável, mas que o projeto não estava reingerindo.

O arquivo continua aqui pelo registro do método: a hipótese, a medição que a
derrubou e a confirmação independente.
