# Arquitetura de CI/CD

O que roda automaticamente, quando, e o que cada coisa garante.

---

## Visão geral

| workflow | gatilho | garante |
|---|---|---|
| `ci.yml` | push/PR nos caminhos de código | testes, lint, type-check, build, supply chain |
| `deploy-site.yml` | push em `main` tocando `site/**` | publica no GitHub Pages |
| `validate-data.yml` | mensal + manual | conciliação da base publicada, via API pública |
| `boletim-semanal.yml` | segundas 12h UTC | gera o boletim e envia alertas |
| `observar-fontes.yml` | segundas 09h UTC | detecta mudança nas fontes do DataSUS |
| `supabase-keepalive.yml` | a cada 6 dias | impede o Supabase free de hibernar |
| `dbt-docs.yml` | push em `main` tocando `dbt/**` | publica a documentação do dbt |
| `publish-mcp.yml` | tag `mcp-v*` | publica `saudeemdado-mcp` no PyPI e no registry |

Não há job de ML. **Isso é decisão, não omissão** — ver a seção final.

---

## `ci.yml` — três jobs

### `python` — matriz 3.11 × 3.12

```
setup-python (cache: pip)
  → pip install -r requirements-test.txt
  → pytest tests/ -v
  → ruff check scripts mcp_server clients validation --select F
  → import saudeemdado_mcp; import saudeemdado
```

**Por que `requirements-test.txt` e não `requirements.txt`:** a suíte não importa
dbt, prefect, streamlit nem pysus. Arrastá-los custou uma quebra real — `dbt-core`
puxou um beta sem wheel cuja metadata não compila, derrubando os testes em 3.11
por motivo sem relação com o código testado. São 68 pacotes em vez de 195.

**Custo declarado:** o CI deixa de provar que `requirements.txt` instala. Ver
"lacunas conhecidas".

**Por que só as regras `F` do ruff:** pyflakes acusa import morto, variável não
usada e nome indefinido — coisas que indicam bug. O ruleset completo do
`pyproject.toml` (E/I/N/UP/B/SIM) acusa 153 ocorrências de **estilo** em
`scripts/`, quase todas deliberadas (ponto-e-vírgula em scripts de análise, nomes
maiúsculos de matriz em código numérico). Travar o CI nisso exigiria uma
reescrita que ninguém pediu.

**Por que `validation` entrou e `ingestion`/`flows` não:** `validation` estava de
fora sem motivo e escondia um import morto. `ingestion` e `flows` acusam 30
ocorrências F, entre elas cinco `F821` (nome indefinido → `NameError` em
execução), em código da arquitetura antiga que nenhum workflow executa. Ligá-los
deixaria o CI vermelho por software que ninguém roda. O silêncio é **declarado**,
não acidental.

**Por que a matriz é 3.11 e 3.12:** `requires-python = ">=3.11"`, e 3.12 é o que
o job de supply chain usa. Duas versões cobrem o intervalo real de uso sem
inflar a matriz.

### `site` — Node 24

```
setup-node (cache: npm)
  → npm ci
  → npx tsc --noEmit
  → npm test            (node --test, 23 testes)
  → npm run build       (prebuild + next build → out/)
  → conferir que out/ tem ≥20 páginas HTML
  → conferir favicon.ico, icon.svg, opengraph-image.png e og:image
```

**Por que Node 24:** o `prebuild` (`build-static-data.mjs`) importa
`lib/completude.ts` direto, e os testes rodam em `.mts` no runner nativo. Type
stripping só existe a partir do 22.6. O 20 saiu do suporte em abril/2026.

**Por que os dois guards finais:** `deploy-site.yml` publica `site/out`; se o
build falhar sem falhar, o deploy publicaria vazio. O guard de ativos de marca
existe porque favicon e imagem OG são versionados e não regerados no build — a
única forma de descobrir que sumiram seria alguém compartilhar um link e ver o
cartão cinza, que foi exatamente como o problema anterior chegou até aqui.

### `supply-chain` — informativo

```
npm audit --audit-level=high
pip-audit --desc --strict
```

`continue-on-error: true`, por decisão explícita. O alerta que sobra é o do
Next.js 14, inalcançável numa aplicação `output: export` sem servidor. Um job
bloqueante travaria a main indefinidamente por um risco que não existe, e o
desfecho previsível seria alguém desligar o job. Informativo, ele continua
mostrando o que aparecer de **novo**.

Detalhes em [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md).

---

## Gatilhos

`ci.yml` dispara em **qualquer branch**, não só em `main`, e também em
`pull_request`. O repositório trabalha direto na main e nunca abriu PR; um CI
preso a `pull_request` simplesmente não rodaria — que era o defeito dos workflows
que ele substituiu.

Filtro de caminhos: `site/**`, `scripts/**`, `tests/**`, `validation/**`,
`mcp_server/**`, `clients/**`, `requirements*.txt`, `pytest.ini`, o próprio
workflow.

`concurrency` com `cancel-in-progress` evita fila em pushes seguidos.

---

## Cache

| ecossistema | chave | efeito na reprodutibilidade |
|---|---|---|
| pip | `requirements*.txt` | nenhum — cache de download, resolução idêntica |
| npm | `site/package-lock.json` | nenhum — o lockfile fixa a árvore |

O cache acelera; não altera o que é instalado.

---

## Política de merge

O repositório não usa PR. Na prática:

- **`ci.yml` verde é a régua.** Push que o deixa vermelho tem de ser corrigido
  antes de qualquer publicação.
- **`deploy-site.yml` só roda em `main`**, e só quando `site/**` muda.
- O job `supply-chain` **não** bloqueia, por desenho.

Se o fluxo passar a usar PR, os jobs `python` e `site` devem virar checks
obrigatórios; `supply-chain`, não.

---

## Validação de modelo preditivo

`scripts/validate_forecast.py` **não roda no CI**, e o motivo é concreto: ele
precisa de `mart_demanda_mensal_hospital` (164 mil linhas), que não está
versionado — os marts são saída regenerável, distribuída pelo Storage do
Supabase.

O que o CI garante em lugar disso é o **núcleo**:
`tests/test_forecast_validacao.py` (60 testes) exercita todos os modelos, o motor
de backtest e as invariantes científicas — inclusive o teste de ausência de
vazamento temporal, que roda duas séries idênticas até certo ponto e divergentes
depois, exigindo previsões idênticas nas origens anteriores à divergência.

A barreira que impede publicação sem validação **não é o CI**: é o próprio
pipeline. `forecast_demanda_hospitalar.py` encerra com erro se
`data/validacao/forecast_backtest.json` não existir. Ver
[`ML_VALIDATION.md`](ML_VALIDATION.md).

---

## Por que não existe job de ML

O plano original previa um `CI ML` que instalasse `pip install -e ".[ml]"` e
rodasse os testes de Prophet, para que nenhum ficasse silenciosamente skipado.

A investigação mostrou que o alvo estava errado. Os 7 testes skipados cobriam
`ml/anomaly_detector.py`, que detectava anomalias em **produção ambulatorial
(SIA/PA)** — fonte que não está no pipeline atual. Nenhum script importava o
módulo, o site não consultava anomalias, e `mart_anomalias_prophet` **não existia
em produção** (a migração V006 nunca foi aplicada).

Instalar Prophet a cada commit para exercitar código que nada executa é gastar
minuto de CI validando software morto. O módulo foi arquivado em
`archive/ml-prophet/`, os 7 skips desapareceram, e o esforço de validação foi
para onde há código publicado: o forecast de demanda hospitalar.

**Se a detecção de anomalias voltar** — sobre SIH ou SINAN, que estão no pipeline
—, aí sim um job de ML se justifica, e o `archive/ml-prophet/README.md` descreve
o caminho de volta.

---

## Lacunas conhecidas

| lacuna | consequência |
|---|---|
| `requirements.txt` completo não é instalado no CI | um conflito de dependência de deploy (como o `loguru` × `pysus`) só aparece na máquina de quem roda o pipeline |
| sem lockfile Python | duas instalações em datas diferentes podem divergir |
| `supabase/functions/` sem execução de teste | correções nas Edge Functions são verificadas por leitura |
| `ingestion/` e `flows/` fora do lint | 5 `F821` conhecidos e não corrigidos |
| pipelines de dado não rodam no CI | dependem de rede, credencial e dezenas de GB; a rede de proteção é `validate-data.yml`, que confere a base **já publicada** |

A última é deliberada: validar a saída publicada contra invariantes conhecidas
(âncoras oficiais, conciliação entre marts, cobertura do excesso) é mais barato e
mais próximo do que interessa do que reexecutar ingestão no CI.
