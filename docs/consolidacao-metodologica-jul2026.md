# Consolidação metodológica — julho/2026

Registro completo de uma sessão de trabalho que partiu de "consolide tudo que temos"
(Visão Hospitalar + Cobertura da APS, ambos recém-lançados) e terminou em cinco
peças interligadas: correção estatística do HSMR, teste rigoroso (e nulo) de
equidade na atenção primária, um artigo-síntese, e um preprint novo. Este
documento existe para que qualquer pessoa (ou sessão futura) retome o trabalho
sem precisar reconstruir o raciocínio do zero.

## Como tudo começou

Duas features já existiam no site quando esta sessão começou: **Visão Hospitalar**
(`/hospitalar` — HSMR, LOS, forecast) e **Cobertura da APS** (`/atencao-basica`,
então recém-criada). O pedido foi: consolidar as duas, decidir se cruzar com
ICSAP, decidir se cobertura merecia página própria, e "ver o que mais deve ser
feito" como "ultra especialista em metodologia, saúde e tecnologia".

A resposta não foi só arquitetura de produto — foi ciência: cada decisão de
design (o que exibir, como classificar, o que NÃO publicar) só foi tomada depois
de medir o dado real, nunca por suposição.

## As cinco peças, em ordem de execução

### 1. HSMR ganha IC95% exato (Poisson/gamma)

**Problema:** o HSMR (mortalidade hospitalar ajustada por case-mix) tinha só uma
flag binária `estavel` (óbitos esperados ≥ 5). Isso não dizia se a mortalidade de
um hospital *diferia* do esperado.

**Solução:** IC95% exato — `[qgamma(0,025;O)/E ; qgamma(0,975;O+1)/E]` — mesmo
método gamma/Poisson já usado nas taxas brutas de mortalidade do projeto.
Script: `scripts/hsmr_intervalo_confianca.py`.

**Achado colateral (viés de case-mix):** hospitais "acima do esperado" são ~5×
maiores que os "abaixo" (mediana 5.350 vs. 1.136 internações) e concentram 58,9%
de todos os óbitos hospitalares. O ajuste por capítulo CID-10 é grosseiro demais
— um capítulo cobre desde hipertensão até cirurgia cardíaca complexa — e
terciários concentram os casos graves *dentro* do capítulo. HSMR alto pode ser
case-mix residual, não pior assistência. Declarado com destaque na UI e na
metodologia.

### 2. Correção de múltiplas comparações (FDR) no HSMR

**Problema descoberto ao testar:** publicar ~4.600 hospitais/ano é testar ~4.600
hipóteses simultaneamente. Testar cada um a 5% sem correção gera falsos positivos
só por acaso.

**Solução:** p-valor exato de Poisson (bilateral) + correção **Benjamini-Hochberg**
por ano civil. A classificação `significancia` (acima/abaixo/esperado/indeterminado)
passou a exigir **q-valor < 0,05**, não IC bruto isolado.

**Efeito medido (não estimado):** de 10.046 hospitais-ano "significativos" sem
correção (2022-2024), **282 (2,8%) perdem a classificação** após o FDR. Note que
minha estimativa inicial no terminal (~15%) estava errada — ela assumia "nenhum
sinal real" (pior caso); o BH usa a distribuição empírica dos p-valores, que
mostra que a maior parte do sinal é genuíno. **Lição: sempre medir, nunca
extrapolar de uma heurística rápida.**

Colunas novas no mart: `hsmr_pvalor`, `hsmr_q_valor`. UI mostra `*` com o q-valor
no hover; `≈` para "dentro do esperado".

### 3. ICSAP checado contra o mesmo problema — resultado: não tem

Antes de assumir que o ICSAP (`/internacoes`, flag ▲ de outlier via IC de Wilson)
tinha o mesmo problema do HSMR, medi. **Não tem**, e por um motivo estrutural
específico: a flag só é aplicada às 30 linhas já pré-filtradas (top 30 por
%ICSAP, ≥200 internações) — nunca ao universo de ~5.200 municípios elegíveis.
Nesse recorte os efeitos são enormes (60–72% vs. 19,5% de média nacional) e os
30 sobrevivem integralmente à correção FDR (nenhuma mudança). Documentado como
comentário no código (`site/app/internacoes/page.tsx`) para não reabrir a dúvida
numa sessão futura — mas com o aviso explícito: **se a flag um dia for aplicada
a um recorte maior que o top-30, reavaliar.**

### 4. Teste de equidade: cobertura da APS × ICSAP × vulnerabilidade

Este foi o item que mais evoluiu durante a execução — vale contar a sequência
real, porque o raciocínio importa mais que o resultado final.

**Rodada 1 — correlação simples.** Cobertura potencial da APS (já sabíamos que
satura acima de 100% em 86% dos municípios — achado anterior, Caso 3 do artigo)
correlacionada com ICSAP: ρ bruto = +0,004 (nulo), ρ parcial (controlando porte e
IVS) = +0,018. Estratificado por porte: municípios <10 mil têm cobertura mediana
167% **e** o maior ICSAP — o oposto da hipótese de política pública.

**Rodada 2 — "mas será que dentro do mesmo porte funciona?"** Testei a objeção
óbvia com o desenho mais rigoroso que consegui desenhar:
- Densidade real de equipes (ESF por 10 mil hab., **sem teto**) em vez da
  cobertura % que satura;
- Cada município comparado só aos pares do **próprio quartil de porte**
  (nunca ao Brasil inteiro);
- Percentil dentro do porte para densidade de ESF e para o desfecho.

Primeira tentativa usou ICSAP/100k como desfecho. Resultado aparente:
municípios mais vulneráveis tinham ICSAP/100k mais baixo (parecia bom sinal).
**Mas testei a explicação alternativa antes de comemorar**: internações totais
per capita TAMBÉM caem com a vulnerabilidade (78,6 → 63,4 por mil hab.) — ou
seja, é barreira de acesso hospitalar geral, não atenção primária melhor.
Corrigi trocando ICSAP/100k por **%ICSAP** (proporção do total de internações do
próprio município, que remove esse confundimento). Com a métrica certa, o
gradiente por vulnerabilidade **desaparece** (19–21% em todos os quartis).

**Teste decisivo — é sinergia real ou coincidência?** Calculei a taxa de
co-ocorrência entre "baixa densidade de ESF" (terço inferior, no próprio porte) e
"alto %ICSAP" (terço superior, no próprio porte): observada 10,50%. Se as duas
variáveis fossem estatisticamente independentes, o esperado seria 11,12% (33,3%
× 33,4%). **Razão observado/esperado = 0,94×** — abaixo do acaso, não acima.
Correlação direta (Brasil inteiro, sem estratificar) esf_10k × %ICSAP: ρ=+0,034
(também nula).

**Decisão de produto — a mais importante da sessão:** não construí nenhum
flag/ranking de "município em situação de atenção". Os números mostram que isso
seria estatisticamente indistinguível de ruído, e publicá-lo como achado seria
repetir exatamente o erro que a sessão inteira estava corrigindo. Em vez disso, o
teste virou: (a) seção de robustez em `/atencao-basica`, (b) parágrafo novo no
Caso 3 do artigo, (c) parágrafo na metodologia §15, (d)
`mart_equidade_aps_municipio` publicado no Supabase **explicitamente rotulado**
como "não é ranking" no `comment on table`.

Script: `scripts/analise_equidade_aps.py`.

### 5. O artigo-síntese e o preprint novo

O artigo **"O que os indicadores não comparam"** (já existia, criado antes desta
sessão específica de FDR/equidade) foi atualizado com: (a) o parágrafo de
robustez do Caso 3, (b) números corrigidos do Caso 4 (HSMR) refletindo a
classificação por q-valor, (c) o parágrafo sobre múltiplas comparações no HSMR.

Novo preprint: **`docs/preprint/preprint-cobertura-aps.md`** +
`.html` (pronto para gerar PDF, mesmo fluxo do preprint anterior — abrir no
navegador, Ctrl+P, salvar como PDF). Título: *"Cobertura potencial da Atenção
Primária no Brasil: um indicador que mede porte municipal, não desempenho
assistencial"*. Contém os três níveis de evidência (bruta, parcial, teste de
robustez pareado) e é submissível de forma independente à SciELO Preprints —
**ainda não foi submetido**, aguarda revisão do autor.

## Números de referência rápida

| Métrica | Valor |
|---|---|
| HSMR agregado nacional (calibração) | 1,0000 nos 3 anos (2022-2024) |
| HSMR "acima do esperado" 2024 (pós-FDR) | 757 hospitais (16,0%) |
| Hospitais que perdem significância após FDR | 282 de 10.046 (2,8%) |
| Mediana internações: hospitais acima vs. abaixo | 5.350 vs. 1.136 (~5×) |
| Cobertura APS acima de 100% | 86,1% dos municípios (mediana 149,1%) |
| Cobertura × população (correlação) | ρ = −0,54 |
| Cobertura × ICSAP/100k (bruta / parcial) | ρ = +0,004 / +0,018 |
| Densidade ESF × %ICSAP, dentro do porte | ρ entre −0,02 e +0,18 |
| Co-ocorrência observada/esperada (equidade) | 0,94× (abaixo do acaso) |
| %ICSAP por quartil de vulnerabilidade | 18,9% / 20,9% / 20,6% / 19,7% (flat) |

## Arquivos criados ou modificados nesta sessão

**Scripts (Python):**
- `scripts/hsmr_intervalo_confianca.py` — IC95%, p-valor, FDR do HSMR
- `scripts/analise_cobertura_icsap.py` — cruzamento bruto cobertura×ICSAP (sessão anterior)
- `scripts/analise_equidade_aps.py` — teste pareado por porte (equidade)
- `scripts/pipeline_cobertura_aps.py` — ingestão da API de cobertura APS (sessão anterior)

**Marts (Supabase, todos com RLS `leitura_publica` apenas):**
- `mart_hsmr_hospital` — colunas novas: `hsmr_pvalor`, `hsmr_q_valor`
- `mart_cobertura_aps_municipio`
- `mart_cobertura_icsap_municipio`
- `mart_equidade_aps_municipio` (rotulado "não é ranking" no comentário da tabela)

**Site (Next.js):**
- `site/app/hospitalar/page.tsx` — exibe IC95%+q-valor em vez de flag binária
- `site/app/atencao-basica/page.tsx` — seção nova de teste de robustez
- `site/app/internacoes/page.tsx` — comentário documentando que ICSAP não precisou de FDR
- `site/app/metodologia/page.tsx` — §14 (HSMR/FDR) e §15 (APS/robustez) atualizadas
- `site/content/artigos.tsx` — Caso 3 e Caso 4 atualizados com os números corrigidos
- `site/lib/api.ts` — tipos `EquidadeApsMunicipio` e campos novos de `HsmrHospital`

**Docs:**
- `docs/preprint/preprint-cobertura-aps.md` + `.html` — preprint novo, não submetido

## Commits desta sessão (ordem cronológica)

1. `a572ed0` — fix(hsmr): corrige múltiplas comparações com FDR
2. `6bce70a` — feat: teste de robustez da equidade APS + confirma que ICSAP não tem o problema
3. `c0bd4a8` — docs(preprint): novo preprint — cobertura potencial da APS mede porte, não desempenho
4. `2e875c0` — feat(aps): painel longitudinal 2021-2024 confirma achado nulo
5. `f6072ec` — feat(aps): testa saúde suplementar como explicação do ICSAP residual
6. `25decf3` — fix(mapa): retângulo de moldura do d3-geo escondia o choropleth
7. `d47abf7` — feat(mapa): KPI de estabelecimentos hospitalares (CNES)
8. `d46c7cf` — fix(mapa): enquadramento também precisa evitar o pipeline do geoPath
9. `d0cd844` — docs(metodologia): seção 18 documenta o CNES e suas duas armadilhas
10. `071ddc5` — feat(hospitalar): leitos por município (CNES-LT, 2015-2024)

Todos no ar, com deploy confirmado (os docs-only não disparam deploy).

## Atualização — painel longitudinal 2021-2024 (resolvido)

A limitação "dado longitudinal" abaixo foi resolvida nesta mesma sessão, em
seguida à consolidação inicial. Resumo:

- Baixamos ICSAP por município para 2021-2023 do zero (FTP DataSUS via
  `scripts/pipeline_sih_fluxo.py --ano {2021,2022,2023}`), completando o
  painel 2021-2024 (2024 já existia). RLS aberta/fechada temporariamente em
  `mart_icsap_municipio`/`mart_fluxo_intermunicipal`, seguindo o padrão do
  projeto.
- Novo script `scripts/analise_equidade_aps_longitudinal.py`: painel
  balanceado de 5.568 municípios × 4 anos (22.272 observações).
- **Achado notável:** o primeiro teste (efeito fixo só por município) deu
  ρ = +0,132 — sinal aparente, na direção errada, crescente com o porte. Causa:
  ESF e %ICSAP subiram juntos no Brasil inteiro em 2021-2024 (ESF médio
  3,67→4,05; %ICSAP médio 17,9%→21,2%, provável retomada pós-pandemia) — uma
  tendência de calendário comum às duas variáveis, não relação causal. Ao
  remover também o efeito de ano (**efeito fixo duplo**, município + ano),
  ρ caiu para +0,006. Diferença ano a ano e defasagem de 1 ano confirmaram:
  |ρ| ≤ 0,032 em todos os desenhos corretamente especificados.
- Isso é um **sexto caso** do problema central do projeto (confundimento
  disfarçado de achado) — desta vez temporal, não transversal. Documentado
  como tal no preprint (nova §2.5/§3.6) e na metodologia (§15).
- Atualizados: `docs/preprint/preprint-cobertura-aps.md`/`.html` (nova seção +
  tabela 4 + resumo/abstract + limitações), `site/app/metodologia/page.tsx`
  (§15), `site/app/atencao-basica/page.tsx` (nova seção "E equipes
  recém-implantadas?"). Build (`npm run build`) e verificação visual via
  preview local, ambos OK. Commit `2e875c0`, no ar.

## Atualização 2 — saúde suplementar explica a limitação do ICSAP? (parcialmente)

Testamos a limitação declarada "ICSAP subestimado onde a saúde suplementar é
relevante", que antes só era mencionada, nunca medida.

- Novo pipeline `scripts/pipeline_ans_beneficiarios.py`: baixa o cadastro de
  beneficiários de plano médico-hospitalar por município (ANS Dados Abertos,
  FTP público sem login, competência de dezembro de 2021-2024), filtra
  `COBERTURA_ASSIST_PLAN == "Médico-hospitalar"` (exclui odontológico puro).
  Novo mart `mart_saude_suplementar_municipio` (22.284 linhas).
- **Achado ruim documentado (a pedido do usuário, para qualificar o trabalho):**
  o dataset pronto `taxa_de_cobertura_de_planos_de_saude-047` da ANS foi
  descartado — só tinha o período corrente (sem histórico) e as taxas vieram
  zeradas mesmo para São Paulo na amostra verificada. Preferimos o cadastro
  bruto de beneficiários, mais trabalhoso mas confiável e histórico desde 2021.
- Novo script `scripts/analise_saude_suplementar_icsap.py`: cruza
  %saude_suplementar com %ICSAP/ICSAP-100k. Correlação bruta fraca (ρ=+0,06 e
  -0,09); parcial controlando porte+IVS por regressão linear sobre postos
  (ρ=-0,10, %ICSAP) sugeria efeito fraco mas enganava por não capturar
  não-linearidade.
- **Teste decisivo (dentro do quartil de porte, mesmo método do teste de
  robustez da Seção 2.4):** gradiente monotônico — ρ = +0,05 (Q1) → -0,00 (Q2)
  → -0,08 (Q3) → **-0,29** (Q4, maiores municípios). Co-ocorrência
  (alta saúde suplementar + baixo %ICSAP) = 1,00× o esperado ao acaso (nula no
  agregado nacional).
- **Conclusão:** a limitação é real, mas **localizada** nos municípios de
  maior porte (tipicamente capitais/metrópoles), e irrelevante para os ~75%
  dos municípios brasileiros menores que concentram a discussão do preprint.
  Não muda o achado nulo principal (APS × ICSAP), mas qualifica onde o ICSAP
  deve ser lido com mais cautela.
- Atualizados: preprint (nova §2.6/3.7, tabela 5, resumo/abstract, limitações,
  disponibilidade de dados) e metodologia (§15, novo parágrafo). Build OK,
  verificado visualmente. Commit `f6072ec`, no ar.

## Atualização 3 — CNES: a camada de oferta que faltava

Até aqui a plataforma só contava **eventos** (óbitos, casos, internações),
nunca **capacidade instalada**. Sem denominador de oferta não dá para
distinguir "assistência pior" de "falta de estrutura". Duas etapas:

### 3.1 Estabelecimentos (API de dados abertos)

- `scripts/pipeline_cnes.py` — API pública do MS, cadastro corrente, sem
  autenticação. 629.987 estabelecimentos, **492.200 ativos** nos 5.571
  municípios. Mart `mart_cnes_municipio`. KPI publicado em `/mapa`.
- **Armadilha 1 (medida):** desabilitados não têm campo de status — o que
  marca é `codigo_motivo_desabilitacao_estabelecimento` preenchido. São
  137.787 registros (22% da base) que inflariam a oferta se contados.
- **Armadilha 2 (medida):** `descricao_esfera_administrativa` é **gestão, não
  propriedade**. Em Alta Floresta d'Oeste/RO os 67 estabelecimentos vêm como
  "MUNICIPAL", mas só **32 (48%)** são públicos pela natureza jurídica — ler o
  campo errado mais que dobra a rede pública aparente. Correto: primeiro
  dígito de `descricao_natureza_juridica_estabelecimento` (CONCLA).

### 3.2 Leitos (FTP DataSUS, grupo LT, 2015-2024)

A API não expõe leitos; só o FTP tem. `scripts/pipeline_cnes_leitos.py`,
competência de **dezembro de cada ano** (270 arquivos, ~6 MB, zero falhas).
Mart `mart_leitos_municipio` (55.710 linhas município-ano). Publicado em
`/hospitalar`.

**Achado 1 — vazio assistencial.** Em 2024: 535.566 leitos totais, 357.084 SUS
(66,7%), 63.837 de UTI. E **1.971 municípios (35,4%) sem nenhum leito
hospitalar** — algo que a contagem de estabelecimentos não revelava, porque um
posto de saúde conta como estabelecimento mas não interna ninguém.

**Achado 2 — a lista de códigos de UTI não pode ser um intervalo.** A tabela
oficial de domínios (`SCNES_DOMINIOS`, aba "LEITOS") põe os códigos de UTI na
faixa 74-86, **mas o código 84 no meio dela é "acolhimento noturno"**. Usar
`74 <= cod <= 86` contaria leito de acolhimento como terapia intensiva, em
silêncio. Só foi detectado porque busquei a tabela oficial em vez de inferir a
faixa. Enumeramos os códigos um a um.

**Achado 3 — a série de UTI 2020-2022 não é comparável ano a ano.** O salto de
50.873 (2021) para 61.037 (2022) parecia expansão de +20%. Investigando a
composição: os leitos "complementares" vão de 59,8 mil (2019) → 99,4 mil
(2021) → 76,9 mil (2022), e a fração deles sob códigos de UTI faz
**77% → 51% → 79%**. Leitura: leito emergencial da pandemia foi cadastrado
fora dos códigos de UTI e depois desmobilizado. O salto de 2022 é em parte
**reclassificação**, não expansão real. A tendência de dez anos (40.448 →
63.837, +58%) se sustenta; a variação anual nessa janela, não. Publicado como
descontinuidade visível (caixa de alerta em `/hospitalar` + metodologia), não
suavizado — é o mesmo princípio dos casos anteriores.

**Regra dura registrada:** CNES é cadastro fotografado mensalmente, não fluxo
de eventos. Somar 12 competências multiplicaria a capacidade por 12. Cada
linha do mart é um snapshot de dezembro. Operações válidas: snapshot, média do
período ou série mensal preservada — nunca soma.

Commits: `d47abf7` (estabelecimentos + KPI no mapa), `d0cd844` (metodologia
§18), `071ddc5` (leitos + `/hospitalar` + metodologia). Todos no ar.

## Bug de renderização do mapa (corrigido)

Fora da linha metodológica, mas vale registrar porque custou tempo e o
diagnóstico é reaproveitável: o `/mapa` ficou **invisível** para os usuários.
Duas causas encadeadas, ambas no `geoPath()` do d3-geo, cujo pipeline de
clip/resampling esférico produz um **retângulo de moldura espúrio** com a
malha auto-hospedada do projeto:

1. A moldura era desenhada em cada um dos 853+ paths; o último do DOM
   (pintado por cima) escondia o mapa atrás de um bloco de cor sólida.
2. Corrigido isso, o mapa continuou invisível: o `fitSize()` mede os limites
   pelo **mesmo pipeline** e vinha ajustando a *moldura* (`[[90,0],[710,620]]`)
   ao viewBox — escala 98,7 e o estado inteiro comprimido em ~19×16 num canvas
   de 800×620.

Correção: projetar ponto a ponto (`proj([lon,lat])`) **e** calcular o
enquadramento na mão, sem tocar no `geoPath`. Municípios nunca cruzam o
antimeridiano, então nada se perde. Validado no DOM: MG 742×608, SP 784×525,
RR 526×608. Commits `25decf3` e `d46c7cf`.

## O que fica pendente (decisão do usuário, não da IA)

1. **Revisar e submeter (ou não) o novo preprint** — `docs/preprint/preprint-cobertura-aps.html`.
2. ~~Considerar dado longitudinal para o teste de equidade~~ — resolvido.
3. **Estender a correção FDR a outros indicadores do projeto** se algum dia
   publicar um ranking amplo (não top-N) baseado em teste estatístico por
   município — o padrão já está estabelecido em `scripts/hsmr_intervalo_confianca.py`.
4. ~~Aprovar commit/push do painel longitudinal~~ — feito e no ar.

### Oportunidades abertas pelo CNES (nenhuma iniciada)

5. **Cruzar leitos com ICSAP** — o preprint da APS já registra que "proporção
   alta de ICSAP pode ser efeito de acesso restrito: onde faltam leitos, a
   internação eletiva desaparece e a fatia de ICSAP sobe mecanicamente". Agora
   existe o dado para testar isso, que hoje é só uma hipótese declarada.
6. **Cruzar leitos com HSMR** — mortalidade hospitalar estratificada por porte
   (faixa de leitos) do estabelecimento. O HSMR já declara viés de case-mix
   residual por porte; leitos dariam a medida direta de porte.
7. **Vazio assistencial × mortalidade** — os 1.971 municípios sem leito
   cruzados com mortalidade por causas sensíveis à atenção hospitalar.
8. **Leitos por tipo no site** — o mart já tem cirúrgico/clínico/obstétrico/
   pediátrico/UTI separados, mas `/hospitalar` só exibe total, SUS e UTI.
9. **Série mensal de leitos** (em vez de snapshot anual) se algum dia
   interessar sazonalidade ou a curva mês a mês da pandemia — são ~3.240
   arquivos, ~72 MB, 1,5-2h de download. Custo zero, só tempo.

## Princípio geral que emergiu desta sessão

Every rodada desta sessão seguiu o mesmo protocolo, que vale nomear porque vai se
repetir: **(1) medir antes de decidir; (2) testar a explicação alternativa óbvia
antes de aceitar um resultado bom demais; (3) se o teste mostrar que um
achado seria ruído, não publicar como se fosse sinal — mesmo que isso signifique
não entregar a feature que foi pedida.** O item 3 foi decidido duas vezes nesta
sessão (o flag de equidade, e implicitamente ao não inflar a correção FDR além do
que os dados sustentavam) e é, mais que qualquer número específico, o que
diferencia este projeto de um dashboard comum.
