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

Todos com deploy confirmado com sucesso (exceto o último, docs-only, sem deploy).

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
  preview local, ambos OK. **Ainda não commitado/pushado** — aguardando
  confirmação do usuário.

## O que fica pendente (decisão do usuário, não da IA)

1. **Revisar e submeter (ou não) o novo preprint** — `docs/preprint/preprint-cobertura-aps.html`.
2. ~~Considerar dado longitudinal para o teste de equidade~~ — resolvido, ver acima.
3. **Estender a correção FDR a outros indicadores do projeto** se algum dia
   publicar um ranking amplo (não top-N) baseado em teste estatístico por
   município — o padrão já está estabelecido em `scripts/hsmr_intervalo_confianca.py`.
4. **Aprovar commit/push** das mudanças do painel longitudinal (scripts,
   preprint, metodologia, `/atencao-basica`).

## Princípio geral que emergiu desta sessão

Every rodada desta sessão seguiu o mesmo protocolo, que vale nomear porque vai se
repetir: **(1) medir antes de decidir; (2) testar a explicação alternativa óbvia
antes de aceitar um resultado bom demais; (3) se o teste mostrar que um
achado seria ruído, não publicar como se fosse sinal — mesmo que isso signifique
não entregar a feature que foi pedida.** O item 3 foi decidido duas vezes nesta
sessão (o flag de equidade, e implicitamente ao não inflar a correção FDR além do
que os dados sustentavam) e é, mais que qualquer número específico, o que
diferencia este projeto de um dashboard comum.
