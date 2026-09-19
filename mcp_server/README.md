# Servidor MCP do Saúde em Dado — instalação

Consulte a saúde do Brasil (DataSUS + IBGE) em **linguagem natural**, direto do seu
assistente de IA. O servidor roda na **sua máquina**, consome a API pública do
projeto e devolve os mesmos números citáveis do site — com **regras anti-alucinação**
(todo número vem de uma ferramenta, com a fonte citada).

> **Custo zero.** Não há servidor a hospedar nem chave de API do mantenedor: você usa
> o seu próprio Claude (Desktop ou Code). Requer **Python 3.10+**.

---

## Instalação rápida — 1 linha (recomendada)

Publicado no PyPI: [`saudeemdado-mcp`](https://pypi.org/project/saudeemdado-mcp/).
Requer [uv](https://docs.astral.sh/uv/). No `claude_desktop_config.json`:

```json
{ "mcpServers": { "saudeemdado": { "command": "uvx", "args": ["saudeemdado-mcp"] } } }
```

O `uvx` baixa e roda o pacote automaticamente — nada a clonar. Alternativa com pip:
`pip install saudeemdado-mcp` e use `"command": "saudeemdado-mcp"`.

---

## Instalação a partir do código (funciona já)

### 1. Baixe os arquivos

O servidor usa o cliente Python do projeto, então clone o repositório:

```bash
git clone https://github.com/pedropaulofernandes88-stack/saude-publica-br.git
cd saude-publica-br
```

### 2. Instale as dependências

```bash
pip install mcp requests
```

### 3. Conecte ao seu cliente

### Opção A — Claude Desktop

Edite o arquivo de configuração (crie se não existir):

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Adicione o servidor (troque `CAMINHO` pelo caminho absoluto onde você clonou):

```json
{
  "mcpServers": {
    "saudeemdado": {
      "command": "python",
      "args": ["CAMINHO/saude-publica-br/mcp_server/server.py"]
    }
  }
}
```

**Reinicie o Claude Desktop.** O servidor "saudeemdado" aparece no ícone de
ferramentas (🔌). Pronto.

### Opção B — Claude Code (linha de comando)

```bash
claude mcp add saudeemdado -- python /CAMINHO/saude-publica-br/mcp_server/server.py
```

Verifique com `claude mcp list`.

## 4. Teste

Pergunte ao Claude, por exemplo:

- *"Quais os 10 municípios de MG com maior taxa padronizada de mortalidade em 2023?"*
- *"O registro de óbitos de Cruzeiro do Sul (AC) é confiável?"*
- *"Detecte anomalias de saúde no município 290200."*
- *"Qual foi o excesso de mortalidade no Brasil em 2021?"*
- *"Para onde os moradores de Penápolis viajam para se internar?"*

O Claude vai chamar as ferramentas e responder com os números e a fonte.

---

## Ferramentas disponíveis (41)

Toda ferramenta de dado devolve `{"dados": ..., "procedencia": {...}}` — a
citação viaja junto do número, porque instrução some quando a resposta é copiada.

### Comece por esta

| Ferramenta | O que faz |
|---|---|
| **`metodologia`** | **numerador, denominador, unidade, defasagem, o que o indicador NÃO mede e as leituras já testadas e REFUTADAS aqui.** Aceita o id do indicador ou o nome de uma ferramenta. É o que impede repetir uma explicação que a plataforma já descartou |

### Mortalidade e qualidade do registro

| Ferramenta | O que faz |
|---|---|
| `serie_mensal_obitos` | série mensal de óbitos 2015–2024 (UF/Brasil, por capítulo CID) |
| `municipios_indicadores` | óbitos, taxa bruta (IC95%) e **padronizada** por município |
| `principais_causas` | principais causas CID-10 (3 caracteres) por ano/UF |
| `descricao_cid10` | descrição oficial de códigos CID-10 |
| `excesso_mortalidade` | excesso mensal (2020+), baseline por tendência |
| **`qualidade_registro`** | **confiabilidade do registro de óbitos** (Bom/Regular/Ruim) |
| `mortalidade_infantil_uf` | TMI por UF e ano — só por UF, e de propósito |
| `anomalia_de_causa_municipio` | excesso por causa sobre a história do **próprio** município |
| `perfil_de_causas_municipio` | componentes do perfil de causas, sem porte, idade, registro e COVID |

### Internações e hospitais

| Ferramenta | O que faz |
|---|---|
| `internacoes_municipios` | internações SUS: AIHs aprovadas, permanência e custo **por episódio** |
| `internacoes_por_agravo` | por agravo traçador (diabetes, AVC, DPOC…) |
| `internacoes_evitaveis_icsap` | ICSAP por município |
| `hospitais` | visão por estabelecimento (CNES), mortalidade **bruta** |
| `hsmr_hospital` | mortalidade hospitalar **padronizada**, com IC95% e sinalizador de instabilidade |
| `permanencia_por_diagnostico` | permanência do hospital vs. mediana nacional, por CID |
| `demanda_mensal_hospital` | série mensal de internações por estabelecimento |
| `forecast_demanda_hospital` | projeção de até 3 meses — **leia a faixa, nunca o ponto** |
| `fluxo_pacientes` | para onde os moradores viajam para se internar |

### Rede, oferta e financiamento

| Ferramenta | O que faz |
|---|---|
| `rede_cadastrada_municipio` | estabelecimentos do CNES e composição por natureza |
| `saude_suplementar_municipio` | vínculos de planos (ANS) — vínculo **não é** pessoa |
| `gasto_saude_municipio` | gasto público em saúde (SIOPS), empenhado e autodeclarado |
| `cobertura_aps_municipio` | cobertura **potencial** da atenção primária, mensal |
| `vazio_assistencial` | leitos × local do óbito: sem leito local muda **onde** se morre |

### Vigilância e prevenção

| Ferramenta | O que faz |
|---|---|
| `dengue_municipios` / `dengue_semanal` | dengue (SINAN), anual e por semana epidemiológica |
| **`boletim_semanal`** | **situação atual**: nowcasting do InfoDengue nas 27 capitais |
| `vacinacao_doses` | doses do PNI por competência — **fonte mais atual do acervo** |
| `cobertura_vacinal_uf` | cobertura em menores de 1 ano, só por UF e só 5 indicadores |
| `natalidade_municipio` | nascidos vivos, baixo peso, prematuridade e pré-natal |
| `agua_vigilancia_municipio` | SISAGUA: **volume de análise**, não potabilidade |
| `agua_cobertura_da_coleta` | separa "não analisou" de "não coletamos" |

### Análise e comparação

| Ferramenta | O que faz |
|---|---|
| **`comparar_com_pares`** | compara com o **estrato de saúde**: valor, mediana dos pares e percentil |
| **`icsap_distancia_dos_pares`** | traduz o ICSAP em internações, leitos-ano e R$ — com as ressalvas que impedem ler isso como "economia disponível" |
| **`canal_endemico_dengue`** | diagrama de controle de uma UF: banda P25–P75 vs. observado |
| **`detectar_anomalias`** | copiloto: resumo priorizado de sinais de um município |
| `oferta_local_e_icsap` | o cruzamento que mediu a dependência do %ICSAP com leito local |
| `cobertura_aps_e_icsap` | o cruzamento APS × ICSAP — **deu nulo**, e serve para mostrar isso |
| `equidade_aps_no_porte` | teste de robustez do anterior, dentro do quartil de porte — **também nulo** |
| `contexto_social_municipio` | quatro eixos de contexto social e de sistema |
| `metadados_dataset` | fontes, métodos, licença, DOI e versão |

## Receitas — pergunte assim

O valor do servidor aparece quando as ferramentas se **combinam**. Exemplos que
funcionam bem como prompt único:

- *"Compare Sobral (CE) com municípios semelhantes. Em que ele está pior que os pares?"*
  → `comparar_com_pares` + `detectar_anomalias`
- *"O surto de dengue no Paraná em 2024 fugiu do padrão histórico? Em quantas semanas?"*
  → `canal_endemico_dengue`
- *"Resuma o boletim epidemiológico desta semana e aprofunde no estado com maior excesso."*
  → `boletim_semanal` + `excesso_mortalidade`
- *"As mortes por causas mal-definidas em Roraima permitem confiar no ranking de causas?"*
  → `qualidade_registro` + `principais_causas`
- *"Monte um briefing de saúde de Penápolis (SP): anomalias, pares, para onde os pacientes viajam."*
  → `detectar_anomalias` + `comparar_com_pares` + `fluxo_pacientes`

Cada resposta vem com número, fonte e ano — e o modelo é instruído a **não estimar
nada de cabeça** e a sinalizar quando o registro do município é pouco confiável.

## Solução de problemas

- **"servidor não aparece":** confirme o caminho absoluto no JSON e **reinicie** o
  cliente. No Windows, use barras normais (`/`) ou barras duplas (`\\`) no caminho.
- **`ModuleNotFoundError: mcp`:** rode `pip install mcp requests` no mesmo Python que
  o `command` do JSON aponta. Se usa vários Pythons, troque `"python"` pelo caminho
  absoluto do executável (ex.: `.venv/Scripts/python.exe`).
- **`ModuleNotFoundError: saudeemdado`:** o servidor precisa do repositório clonado
  (ele importa o cliente de `clients/python/`). Não mova o `server.py` para fora da
  pasta do projeto.

## Registry oficial MCP

O servidor está listado no [registry oficial do Model Context Protocol](https://registry.modelcontextprotocol.io)
como `io.github.pedropaulofernandes88-stack/saudeemdado` — clientes que integram o
registry (Claude, VS Code etc.) podem descobri-lo e instalá-lo diretamente por esse nome.

## Licença e citação

Dados originais em domínio público (DataSUS/MS; IBGE). Agregados sob **CC BY 4.0**;
código sob **MIT**. DOI: [10.5281/zenodo.20706845](https://doi.org/10.5281/zenodo.20706845).
Site e metodologia: https://saudeemdado.com.

mcp-name: io.github.pedropaulofernandes88-stack/saudeemdado
