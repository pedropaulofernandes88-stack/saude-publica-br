# Guia de publicação — passo a passo (para fazer sozinho, primeira vez)

Tudo o que depende de código já está pronto no repositório. Este guia cobre **só a
parte externa** (que exige suas credenciais). Faça na ordem abaixo. Cada bloco em
`caixa` é para **copiar e colar**.

**Seus dados (use em todos os formulários):**
- Nome: **Pedro Paulo Fernandes**
- E-mail: **pedropaulofernandes88@gmail.com**
- ORCID: **0009-0008-6248-2486**
- Afiliação: **IAMSPE — Mestrado em Saúde Coletiva** (use esta como principal)
- DOI (conceito, todas as versões): **10.5281/zenodo.20706845**
- DOI (versão v3.1.0): **10.5281/zenodo.21036341**
- Repositório: `https://github.com/pedropaulofernandes88-stack/saude-publica-br`
- Site: `https://saudeemdado.com`

---

## 0. Gerar o PDF do manuscrito (5 minutos, faça primeiro)

Os preprints estão prontos em HTML. Para virar PDF:

1. Abra o arquivo no navegador (duplo-clique):
   `docs/preprint/preprint.html` (português) — para a SciELO.
   `docs/preprint/preprint-en.html` (inglês) — para o medRxiv.
2. Pressione **Ctrl+P** (imprimir).
3. Em "Destino/Impressora", escolha **"Salvar como PDF"**.
4. Salve. Pronto — esse PDF é o que você envia.

---

## 1. SciELO Preprints (faça primeiro — português, DOI em dias)

**Por quê primeiro:** é gratuito, rápido (moderação em poucos dias), em português, e
dá um DOI próprio — o "carimbo" público imediato.

### Passos
1. Acesse **https://preprints.scielo.org** → clique em **"Cadastro"** (ou "Login").
2. **Cadastre-se com o ORCID** (botão ORCID) — isso já vincula sua identidade.
   Preencha nome, e-mail e afiliação (IAMSPE).
3. No painel, clique em **"Nova submissão"** (ou "Submeter").
4. **Seção/área:** escolha **Ciências da Saúde**.
5. **Checklist de condições:** marque todas (trabalho original; concorda com a
   licença CC-BY; não está sob avaliação sigilosa em periódico).
6. **Metadados** — cole exatamente:

**Título:**
```
Saúde em Dado: uma plataforma aberta e reprodutível de indicadores epidemiológicos do SUS, com baseline de excesso de mortalidade robusto ao denominador populacional
```

**Resumo:** (cole o texto da seção "Resumo" de `docs/preprint/preprint.md`)

**Palavras-chave:**
```
saúde coletiva; DataSUS; mortalidade; excesso de mortalidade; padronização por idade; dados abertos; reprodutibilidade; Brasil
```

**Autor:** Pedro Paulo Fernandes · ORCID 0009-0008-6248-2486 · IAMSPE.

7. **Arquivos:** faça upload do **PDF** (gerado no passo 0) como "texto principal".
8. **Declarações:** Financiamento = **nenhum**; Conflito de interesse = **nenhum**.
9. **Disponibilidade de dados** (cole):
```
Dados agregados sob CC BY 4.0 e código sob MIT em https://github.com/pedropaulofernandes88-stack/saude-publica-br. Dados originais em domínio público (DataSUS/Ministério da Saúde; IBGE). DOI: 10.5281/zenodo.20706845.
```
10. **Finalizar submissão.** Você recebe um e-mail; a moderação leva poucos dias;
    ao publicar, o preprint ganha um **DOI da SciELO** — anote-o (vai para o Lattes).

---

## 2. medRxiv (depois — inglês, alcance internacional, indexa no Google Scholar)

**Atenção:** o medRxiv triaga cada submissão (24–48h) e exige declarações específicas
— é onde a maioria trava. Siga certinho.

### Passos
1. Acesse **https://www.medrxiv.org** → **"Submit"** → crie conta (pode usar ORCID).
2. **"Submit a new manuscript"**.
3. **Categoria (Subject Area):** escolha **Health Informatics** (alternativas:
   *Epidemiology* ou *Public and Global Health*).
4. **Título** (cole):
```
Saúde em Dado: an open, reproducible platform of epidemiological indicators from Brazil's Unified Health System, with an excess-mortality baseline robust to population-denominator error
```
5. **Abstract:** cole o texto da seção "Abstract" de `docs/preprint/preprint-en.md`.
6. **Keywords:**
```
collective health; DataSUS; mortality; excess mortality; age standardization; open data; reproducibility; Brazil
```
7. **Autor:** Pedro Paulo Fernandes · ORCID 0009-0008-6248-2486 · afiliação IAMSPE.
8. **Arquivo:** upload do **PDF em inglês** (`preprint-en.html` → PDF).
9. **Declarações obrigatórias** (o ponto crítico — cole):
   - *Funding statement:* `The author received no specific funding for this work.`
   - *Competing interest statement:* `The author declares no competing interests.`
   - *Ethics / IRB:* marque que o estudo usa **apenas dados públicos, agregados e
     anonimizados**. Cole no campo de ética:
     `This study used only publicly available, aggregated and de-identified data (DataSUS, IBGE); no ethics committee approval was required.`
   - *Data availability:* `All aggregated data (CC BY 4.0) and code (MIT) are available at https://github.com/pedropaulofernandes88-stack/saude-publica-br. DOI: 10.5281/zenodo.20706845.`
10. **Licença:** escolha **CC-BY 4.0**.
11. **Submeta.** Após a triagem (~2 dias úteis), o preprint é postado com **DOI medRxiv**.

---

## 3. Lattes (torna tudo visível para banca/academia)

Faça **depois** de ter os DOIs dos preprints.

1. Acesse **http://lattes.cnpq.br** → entre com CPF/senha.
2. Menu **"Dados gerais" → ORCID** → vincule o ORCID `0009-0008-6248-2486`
   (sincroniza produções automaticamente).
3. **Cadastrar o software:** menu **"Produção técnica" → "Software"** →
   - Título: `Saúde em Dado: inteligência epidemiológica aberta sobre os microdados do SUS`
   - Ano: `2026` · Plataforma/URL: `https://saudeemdado.com`
   - No campo de disponibilidade/registro, informe o DOI: `10.5281/zenodo.20706845`
   - Descrição curta:
     ```
     Plataforma aberta e reprodutível que transforma microdados do DataSUS (SIM, SIH, SINAN, SINASC) e do IBGE em indicadores municipais, com API pública, servidor MCP e DOI versionado.
     ```
4. **Cadastrar os preprints:** menu **"Produção bibliográfica"** → o tipo mais
   adequado é **"Demais tipos de produção bibliográfica"** (ou "Artigo" se houver
   opção de preprint) → informe título, ano `2026`, e o **DOI da SciELO/medRxiv**.
5. Clique em **"Enviar currículo"** (salvar) no topo.

---

## 4. Publicar o pacote no PyPI (instalação em 1 linha: `uvx saudeemdado-mcp`)

São **dois pacotes** (o servidor MCP depende do cliente). Publique o **cliente
primeiro**. Feito uma vez, qualquer pessoa instala o agente com uma linha.

### 4.1. Conta e token (uma vez)
1. Crie conta em **https://pypi.org/account/register/** e **confirme o e-mail**.
2. Ative **2FA** (obrigatório) em *Account settings*.
3. Crie um **API token:** *Account settings → API tokens → Add API token* →
   escopo "Entire account" (na primeira vez) → **copie o token** (começa com
   `pypi-...`; só aparece uma vez).

### 4.2. Construir os pacotes
No terminal, na pasta do projeto:
```bash
uv build clients/python
uv build mcp_server
```
Isso gera os arquivos em `clients/python/dist/` e `mcp_server/dist/`.

### 4.3. Publicar (cliente primeiro, depois o MCP)
```bash
uv publish --token pypi-COLE_SEU_TOKEN_AQUI clients/python/dist/*
uv publish --token pypi-COLE_SEU_TOKEN_AQUI mcp_server/dist/*
```
> Se `uv publish` pedir usuário/senha em vez do token: usuário = `__token__`,
> senha = o token `pypi-...`.

### 4.4. Testar
```bash
uvx saudeemdado-mcp --help    # baixa e roda; se abrir sem erro, funcionou
```
Depois, no `claude_desktop_config.json`, os usuários usam:
```json
{ "mcpServers": { "saudeemdado": { "command": "uvx", "args": ["saudeemdado-mcp"] } } }
```

---

## 5. LinkedIn (3 posts prontos — 1 por semana; comece pelo primeiro)

**Post 1 — o achado que diferencia (método):**
```
643 mil. Não 702 mil.

Esse é o número de mortes em excesso no Brasil no auge da pandemia (2020–2021) — depois que corrigi um viés que quase ninguém discute: o de que a população envelhece, e um "esperado" que ignora isso infla o excesso.

Fui além e testei o método "mais sofisticado" (padronização por idade). Deu ~505 mil — abaixo do consenso internacional. Investiguei e descobri o motivo: a população anual por idade do Brasil é frágil (a projeção de 2018 superestimou; o Censo 2022 corrigiu para baixo). O método mais simples venceu por ser o mais robusto.

A escolha do baseline pode mudar a conclusão em centenas de milhares de vidas. Publiquei o código, a tabela e o raciocínio — qualquer um reproduz.

🔗 saudeemdado.com/artigos/643-mil-nao-702-mil-baseline-excesso-mortalidade

#SaúdeColetiva #CiênciaDeDados #Epidemiologia #SUS #DadosAbertos
```

**Post 2 — o ângulo de gestor (autoridade prática):**
```
R$ 4,2 bilhões. É quanto o Brasil gastou, só em 2024, com internações que boa atenção primária poderia ter evitado (ICSAP).

Não é opinião: é o nº de internações por condições sensíveis à atenção básica × o custo real dessas internações no SUS. E dá para ver por município, com sinalização estatística de quem está acima da média.

Como diretor de TI numa prefeitura, aprendi que gestor não muda o que não enxerga. Por isso construí isso aberto e gratuito: qualquer secretaria pode olhar seu município hoje.

🔗 saudeemdado.com/internacoes

#GestãoEmSaúde #SUS #AtençãoPrimária #DadosAbertos
```

**Post 3 — a autoridade metodológica (didático):**
```
Santos tem mortalidade 2,8× maior que Parauapebas (PA). Certo? Errado.

Essa é a taxa bruta — e ela mente. Santos é uma cidade envelhecida; Parauapebas é jovem. Quando padronizo por idade (comparando maçãs com maçãs), a relação se inverte: Parauapebas tem mortalidade maior.

Rankings de saúde na imprensa quase sempre usam a taxa bruta — e por isso quase sempre estão errados. Padronizar por idade não é preciosismo: é a diferença entre uma conclusão correta e uma injustiça com um município.

🔗 saudeemdado.com/artigos/taxa-bruta-vs-padronizada-rankings-municipais

#Epidemiologia #Estatística #SaúdeColetiva #Dados
```

---

## 6. Bônus — alcance (opcional, alto retorno)

- **Agência Bori** (`abori.com.br`): cadastro gratuito de pesquisador; quando o
  preprint sair, eles pautam a imprensa. Cadastre-se e informe o DOI do preprint.
- **E-mail ao COSEMS-SP** (secretarias municipais) — modelo:
```
Assunto: Ferramenta aberta e gratuita de indicadores de saúde por município

Prezados, sou Pedro Fernandes (Mestrando em Saúde Coletiva, IAMSPE; Diretor de TI
no setor público). Desenvolvi uma plataforma aberta e sem custos —
saudeemdado.com — que transforma os microdados do DataSUS em indicadores municipais
prontos: mortalidade padronizada, internações evitáveis (ICSAP) com gasto evitável
estimado, fluxo de pacientes e qualidade do registro. Tudo por município, com API
pública e metodologia documentada. Gostaria de apresentá-la ao COSEMS e às
secretarias interessadas. Fico à disposição.
```

---

## Ordem recomendada (resumo)
1. Gerar os 2 PDFs (passo 0).
2. Submeter na SciELO Preprints (PT) → anotar o DOI.
3. Submeter no medRxiv (EN) → anotar o DOI.
4. Cadastrar software + preprints no Lattes.
5. Publicar os pacotes no PyPI.
6. Postar no LinkedIn (1/semana) e cadastrar na Bori.
