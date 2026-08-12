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

## Ferramentas disponíveis (19)

### Consulta

| Ferramenta | O que faz |
|---|---|
| `serie_mensal_obitos` | série mensal de óbitos 2015–2024 (UF/Brasil, por capítulo CID) |
| `municipios_indicadores` | óbitos, taxa bruta (IC95%) e **padronizada** por município |
| `principais_causas` | principais causas CID-10 (3 caracteres) por ano/UF |
| `descricao_cid10` | descrição oficial de códigos CID-10 |
| `excesso_mortalidade` | excesso mensal (2020+), baseline por tendência |
| **`qualidade_registro`** | **confiabilidade do registro de óbitos** (Bom/Regular/Ruim) |
| `internacoes_municipios` | internações SUS: volume (AIHs aprovadas), permanência e custo **por episódio**, mortalidade |
| `internacoes_evitaveis_icsap` | ICSAP (internações evitáveis) por município |
| `internacoes_por_agravo` | internações por agravo traçador (diabetes, AVC, DPOC…) |

| `hospitais` | visão por estabelecimento (CNES) |
| `fluxo_pacientes` | para onde os moradores viajam para se internar |
| `dengue_municipios` / `dengue_semanal` | dengue (SINAN) anual e por semana epidemiológica |
| `metadados_dataset` | fontes, métodos, licença, DOI e versão |

### Análise

| Ferramenta | O que faz |
|---|---|
| **`comparar_com_pares`** | compara um município com o seu **arquétipo de saúde** (k-means: mortalidade × vulnerabilidade × internações) — valor, mediana dos pares e **percentil no grupo** |
| **`icsap_distancia_dos_pares`** | **tradução:** quanto o município está acima de comparáveis em internações evitáveis, convertido em **internações, leitos ocupados o ano inteiro e R$** — com as ressalvas que impedem ler isso como "economia disponível" |
| **`canal_endemico_dengue`** | **diagrama de controle** de uma UF: banda P25–P75 histórica vs. observado, semanas acima do P75 e status de surto |
| **`boletim_semanal`** | a edição vigente (ou qualquer edição) do [boletim epidemiológico semanal](https://saudeemdado.com/boletim-semanal/) gerado automaticamente pelo pipeline |
| **`detectar_anomalias`** | **copiloto:** resumo priorizado de sinais de um município |

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
