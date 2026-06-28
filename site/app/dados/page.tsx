import type { Metadata } from "next";
import { SUPABASE_ANON_KEY, SUPABASE_URL } from "@/lib/api";

export const metadata: Metadata = { title: "Dados & API" };

export default function Dados() {
  return (
    <div className="prose-doc mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
        Dados &amp; API
      </h1>
      <p>
        Toda a base é acessível por uma <strong>API REST pública e gratuita</strong>{" "}
        (PostgREST), sem cadastro. A chave abaixo é pública por design e dá
        acesso <em>somente leitura</em>.
      </p>

      <h2>Acesso rápido</h2>
      <pre>
        <code>{`BASE="${SUPABASE_URL}/rest/v1"
KEY="${SUPABASE_ANON_KEY}"

# Série mensal de óbitos no Brasil (todas as causas)
curl "$BASE/mart_mortalidade_uf_mes?select=mes_competencia,uf_sigla,obitos&capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&faixa_etaria=eq.TOTAL&order=mes_competencia" \\
  -H "apikey: $KEY"

# Municípios de MG com maior taxa em 2023 (pop >= 50 mil)
curl "$BASE/mart_mortalidade_municipio?uf_sigla=eq.MG&ano=eq.2023&capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&populacao=gte.50000&order=taxa_obitos_100k.desc&limit=20" \\
  -H "apikey: $KEY"

# Soma de óbitos por causa (agregação no servidor)
curl "$BASE/mart_mortalidade_causa?select=causabas_3,obitos.sum()&ano=eq.2024&uf_sigla=eq.SP&order=causabas_3" \\
  -H "apikey: $KEY"`}</code>
      </pre>
      <p>
        Filtros seguem a sintaxe do{" "}
        <a href="https://postgrest.org/en/stable/references/api/tables_views.html" target="_blank" rel="noreferrer">
          PostgREST
        </a>{" "}
        (<code>eq.</code>, <code>gte.</code>, <code>neq.</code>, <code>order=</code>,{" "}
        <code>limit=</code>, <code>select=</code>). Respostas são paginadas em até
        1.000 linhas — use o cabeçalho <code>Range</code> com ordenação
        determinística para obter conjuntos maiores.
      </p>

      <h2>Tabelas disponíveis</h2>
      <table>
        <thead>
          <tr>
            <th>Tabela</th>
            <th>Granularidade</th>
            <th>Linhas</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>mart_mortalidade_municipio</code></td>
            <td>município × ano (2015–2024) × capítulo CID-10 × sexo; taxa bruta + IC95% + <b>taxa padronizada por idade</b></td>
            <td>~1,3 mi</td>
          </tr>
          <tr>
            <td><code>mart_mortalidade_uf_mes</code></td>
            <td>UF × mês (2015–2024) × capítulo × sexo × faixa etária</td>
            <td>~400 mil</td>
          </tr>
          <tr>
            <td><code>mart_mortalidade_causa</code></td>
            <td>UF × ano (2015–2024) × causa básica (CID-10, 3 caracteres)</td>
            <td>~200 mil</td>
          </tr>
          <tr>
            <td><code>mart_excesso_uf_mes</code></td>
            <td>excesso de mortalidade: observado × esperado por UF/BR × mês (2020+)</td>
            <td>~1,7 mil</td>
          </tr>
          <tr>
            <td><code>mart_dengue_semana</code></td>
            <td>dengue (SINAN): casos prováveis, graves e óbitos por município × ano × semana epidemiológica</td>
            <td>centenas de mil</td>
          </tr>
          <tr>
            <td><code>mart_dengue_municipio_ano</code></td>
            <td>dengue anual por município: casos, incidência /100k e letalidade</td>
            <td>dezenas de mil</td>
          </tr>
          <tr>
            <td><code>mart_internacoes_municipio</code></td>
            <td>internações SUS (SIH): volume, permanência média, mortalidade hospitalar e custo, por município × ano × capítulo CID-10</td>
            <td>centenas de mil</td>
          </tr>
          <tr>
            <td><code>mart_natalidade_municipio</code></td>
            <td>nascidos vivos (SINASC): peso ao nascer, prematuridade, pré-natal, idade da mãe, por município × ano</td>
            <td>~11 mil</td>
          </tr>
          <tr>
            <td><code>mart_mortalidade_infantil_uf</code></td>
            <td>Taxa de Mortalidade Infantil por UF e ano (óbitos &lt;1 ano ÷ nascidos vivos)</td>
            <td>54</td>
          </tr>
          <tr>
            <td><code>dim_ivs</code></td>
            <td>vulnerabilidade social municipal (proxy Censo 2022: analfabetismo + água; z-score)</td>
            <td>5.570</td>
          </tr>
          <tr>
            <td><code>dim_cluster_municipio</code></td>
            <td>arquétipos de saúde por k-means (mortalidade × vulnerabilidade × internações, 2023)</td>
            <td>~1,7 mil</td>
          </tr>
          <tr>
            <td><code>mart_icsap_municipio</code></td>
            <td>internações evitáveis (ICSAP) por município, 2024: total, ICSAP, % e por 100k hab.</td>
            <td>~5,5 mil</td>
          </tr>
          <tr>
            <td><code>mart_fluxo_intermunicipal</code></td>
            <td>fluxo de pacientes residência→atendimento (SIH 2024, fluxos ≥ 5)</td>
            <td>dezenas de mil</td>
          </tr>
          <tr>
            <td><code>mart_internacoes_agravo</code></td>
            <td>internações por agravo traçador (CID-3) por município, 2024: volume, permanência, mortalidade, custo</td>
            <td>~53 mil</td>
          </tr>
          <tr>
            <td><code>mart_internacoes_hospital</code></td>
            <td>internações por estabelecimento (CNES), 2024: volume, permanência, mortalidade, custo, capítulo principal</td>
            <td>~4,7 mil</td>
          </tr>
          <tr>
            <td><code>dim_municipio</code></td>
            <td>municípios IBGE (códigos 6/7 dígitos, UF, região)</td>
            <td>5.571</td>
          </tr>
          <tr>
            <td><code>dim_populacao</code></td>
            <td>população municipal por ano (2015–2024)</td>
            <td>~56 mil</td>
          </tr>
          <tr>
            <td><code>dim_pop_faixa</code></td>
            <td>população municipal por faixa etária (Censo 2022)</td>
            <td>~44,6 mil</td>
          </tr>
          <tr>
            <td><code>dim_pop_padrao</code></td>
            <td>população padrão da padronização (Brasil, Censo 2022)</td>
            <td>8</td>
          </tr>
          <tr>
            <td><code>dim_cid10_capitulo</code> / <code>dim_cid10_categoria</code></td>
            <td>capítulos e descrições das categorias CID-10</td>
            <td>22 / ~2 mil</td>
          </tr>
          <tr>
            <td><code>meta_dataset</code></td>
            <td>metadados: fontes, métodos, datas, exclusões, licença, versão</td>
            <td>—</td>
          </tr>
        </tbody>
      </table>
      <p>
        <strong>Importante:</strong> linhas com <code>capitulo_cid=&#39;TOTAL&#39;</code>,{" "}
        <code>sexo=&#39;TOTAL&#39;</code> ou <code>faixa_etaria=&#39;TOTAL&#39;</code> são
        subtotais pré-calculados. Filtre-os explicitamente para evitar dupla contagem.
      </p>

      <h2>Uso em Python e R</h2>
      <pre>
        <code>{`# Python
import requests, pandas as pd
r = requests.get(
    "${SUPABASE_URL}/rest/v1/mart_mortalidade_causa",
    params={"ano": "eq.2024", "uf_sigla": "eq.SP", "order": "obitos.desc", "limit": "100"},
    headers={"apikey": "<KEY>"},
)
df = pd.DataFrame(r.json())

# R
library(httr2); library(dplyr)
resp <- request("${SUPABASE_URL}/rest/v1/mart_mortalidade_causa") |>
  req_url_query(ano = "eq.2024", uf_sigla = "eq.SP", order = "obitos.desc", limit = "100") |>
  req_headers(apikey = "<KEY>") |> req_perform()
df <- resp |> resp_body_json(simplifyVector = TRUE)`}</code>
      </pre>

      <h2>Repositório de dados (download em lote)</h2>
      <p>
        A base completa está disponível em <strong>Parquet</strong> — ideal para
        DuckDB, pandas, Arrow ou R. O repositório é <strong>somente leitura</strong>{" "}
        e cada arquivo tem hash SHA-256 publicado para verificação de integridade.
      </p>
      <table>
        <thead>
          <tr>
            <th>Arquivo</th>
            <th>Tamanho</th>
            <th>SHA-256</th>
          </tr>
        </thead>
        <tbody>
          {[
            ["mart_mortalidade_municipio.parquet", "14,2 MB", "748310975375de33d289cb72a54c7d52d63a7118af8df2b2a7477f0bc97c3071"],
            ["mart_mortalidade_uf_mes.parquet", "1,6 MB", "3958450095820478e582ee30fae57be1c49e6c9f91e174865e00bd0ed9f06db3"],
            ["mart_mortalidade_causa.parquet", "0,7 MB", "c51f2c553810eaf92d996aa52fb7b436da2a80a971526d060c7beacc341fa4ad"],
            ["mart_excesso_uf_mes.parquet", "0,04 MB", "37feefc7694bbf055f271552942c0ccbd9c1de40185002548514dcdbcc7810a9"],
            ["mart_dengue_semana.parquet", "1,1 MB", "4e9eb4d9a87efc8ded2f3d692252b24d59091ca62ae4f29c1163b996d78d113f"],
            ["mart_dengue_municipio_ano.parquet", "0,3 MB", "1bf5f4d31d395428219b065ea80d68fa138cd8476d3dda1b9734ddfbedb40fcb"],
            ["mart_internacoes_municipio.parquet", "6,0 MB", "09d129d5bbe344f1e3fc12ed9ee9413035e7600b0e1dd9ce6dbdb868857c56d3"],
            ["mart_icsap_municipio.parquet", "0,2 MB", "90b65857b3717e1479310ff68a1f717bbbb91fef8c3aae55599e45c97ebd2efd"],
            ["mart_fluxo_intermunicipal.parquet", "0,3 MB", "233d3ec76916fd9efb73fafe2dbeb33419816d032e5c8dfcc2e4dd54fd313b29"],
            ["mart_internacoes_agravo.parquet", "1,2 MB", "8690e2df0586337a34f66fe493b7c443ee4e931d4d8fcef8aeabf4719baafe35"],
            ["mart_internacoes_hospital.parquet", "0,2 MB", "31e39b7793d5e811f784a9da3578ea7fecd3e8d51c862e2da0b3ab0b2158c58c"],
            ["mart_natalidade_municipio.parquet", "0,2 MB", "d6f064c2230322368bdf11553b89c9439b86240a2bf223f309ee82a0d25f5294"],
            ["mart_mortalidade_infantil_uf.parquet", "0,01 MB", "73665f2f9cce2adec1a0431ff67c7ee1ec5a92412baca1ac838bdeb8b7d40732"],
            ["dim_ivs.parquet", "0,12 MB", "76f386873403eb7aad4d1099eceb05169a737f80083f57d1ba45ecec774517d2"],
            ["dim_cluster_municipio.parquet", "0,05 MB", "f02e5be4fd3efccefb18cd671742f1ab5090c22a6d44bed21179caa2ea081646"],
            ["dim_municipio.parquet", "0,09 MB", "a7f3f66aad10ef9bd99f6d1f0dc919f9017dcc3ae7e55de9da65344790e2d7e4"],
            ["dim_populacao.parquet", "0,29 MB", "c88335c58dc4e45c46a91512d749cc6f40d00d4659cdcb289921a54467c0456d"],
            ["dim_pop_faixa.parquet", "0,13 MB", "a7aaa140fd70bfea6f18c77ec5ebdeb25a26bd26437ca8289b355ba3e05c3b0a"],
            ["dim_pop_padrao.parquet", "0,01 MB", "bee34904f471812432ac2d047ed56a4eed5a88d905a28a55c24c02fb0153aebc"],
            ["dim_cid10_categoria.parquet", "0,04 MB", "3202eca9d645ae8bdb6ba98aa4dda940a1e878fc267bb6d6a711629fcc4ebf3f"],
          ].map(([nome, tamanho, sha]) => (
            <tr key={nome}>
              <td>
                <a href={`${SUPABASE_URL}/storage/v1/object/public/dados/${nome}`} download>
                  {nome}
                </a>
              </td>
              <td>{tamanho}</td>
              <td>
                <code style={{ fontSize: "0.7em", wordBreak: "break-all" }}>{sha}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <pre>
        <code>{`# Verificar integridade após o download
sha256sum mart_mortalidade_municipio.parquet

# Ler direto da URL com DuckDB (sem baixar)
duckdb -c "SELECT uf_sigla, sum(obitos) FROM read_parquet('${SUPABASE_URL}/storage/v1/object/public/dados/mart_mortalidade_uf_mes.parquet') WHERE capitulo_cid='TOTAL' AND sexo='TOTAL' AND faixa_etaria='TOTAL' GROUP BY 1 ORDER BY 2 DESC"`}</code>
      </pre>

      <h2>Pacote Python</h2>
      <p>
        Cliente oficial com paginação automática e suporte a pandas — ideal
        para notebooks de pesquisa:
      </p>
      <pre>
        <code>{`pip install "git+https://github.com/pedropaulofernandes88-stack/saude-publica-br#subdirectory=clients/python"

import saudeemdado as sd
mg = sd.municipios(uf="MG", ano=2023, pop_min=50_000, as_df=True)
mg.nlargest(10, "taxa_padronizada_100k")`}</code>
      </pre>

      <h2>Servidor MCP (pesquise via assistentes de IA)</h2>
      <p>
        O dataset também é acessível por assistentes de IA via{" "}
        <a href="https://modelcontextprotocol.io" target="_blank" rel="noreferrer">Model Context Protocol</a>:
        aponte o Claude Desktop/Code para <code>mcp_server/server.py</code> do
        repositório e pergunte em linguagem natural ("compare o excesso de
        mortalidade de SP e AM em 2021") — as respostas usam exatamente os
        números citáveis desta base.
      </p>

      <h2>Boletim municipal</h2>
      <p>
        Cada município tem um boletim imprimível (PDF via navegador) com série
        de taxas 2015–2024, IC95% e principais grupos de causas:{" "}
        <code>/boletim/?m=&lt;código IBGE 6 dígitos&gt;</code> — ou clique no
        nome do município no painel.
      </p>

      <h2>Vigência por base (data-fonte)</h2>
      <p>
        Cada sistema tem cobertura e atualidade próprias — uma análise deve sempre
        confrontar o ano disponível de cada base:
      </p>
      <table>
        <thead>
          <tr><th>Base</th><th>Sistema</th><th>Cobertura</th><th>Observação</th></tr>
        </thead>
        <tbody>
          <tr><td>Mortalidade</td><td>SIM</td><td>2015–2024</td><td>2024 preliminar</td></tr>
          <tr><td>Internações</td><td>SIH/AIH</td><td>2022–2024</td><td>2024 preliminar; só rede SUS</td></tr>
          <tr><td>Dengue</td><td>SINAN</td><td>2015–2024</td><td>2024 em classificação</td></tr>
          <tr><td>Nascimentos</td><td>SINASC</td><td>2021–2023</td><td>2024 não liberado pelo MS</td></tr>
          <tr><td>Vulnerabilidade / população</td><td>IBGE Censo 2022 + estimativas</td><td>2022 (2023 interpolado)</td><td>renda municipal 2022 ainda não liberada</td></tr>
        </tbody>
      </table>

      <h2>Qualidade do registro</h2>
      <p>
        A transparência exige medir o que é incerto. Cerca de{" "}
        <strong>5,4% dos óbitos têm causa mal-definida</strong> (capítulo XVIII —
        sintomas e sinais), e essa proporção <strong>varia entre regiões</strong>{" "}
        (maior no Norte/Nordeste), o que afeta comparações de mortalidade
        causa-específica. Não redistribuímos esses códigos entre causas; eles
        permanecem visíveis. Use as taxas causa-específicas com essa ressalva onde
        a qualidade de registro é menor.
      </p>

      <h2>Licença e citação</h2>
      <p>
        <strong>Dados originais</strong> em domínio público (DATASUS/Ministério da
        Saúde e IBGE). <strong>Agregações e marts derivados</strong> sob{" "}
        <a href="https://creativecommons.org/licenses/by/4.0/deed.pt-br" target="_blank" rel="noreferrer">CC BY 4.0</a>{" "}
        (uso livre com atribuição); <strong>código</strong> sob licença MIT. Em
        publicações, cite as fontes primárias (DataSUS; IBGE) e, se a agregação for
        usada, esta plataforma.
      </p>
      <p><strong>Como citar:</strong></p>
      <pre>
        <code>{`Fernandes, P. P. Saúde em Dado: inteligência epidemiológica aberta
sobre os microdados do SUS. https://saudeemdado.com
DOI: 10.5281/zenodo.20706846. Acesso em: AAAA-MM-DD.
Fontes primárias: DATASUS (SIM, SIH, SINAN, SINASC) e IBGE.`}</code>
      </pre>
      <p className="text-sm text-ink-500">
        DOI de conceito (todas as versões) no Zenodo:{" "}
        <a href="https://doi.org/10.5281/zenodo.20706846" target="_blank" rel="noreferrer">10.5281/zenodo.20706846</a>.
        O repositório traz <code>CITATION.cff</code> para citação automática (botão "Cite this
        repository" no GitHub). Cada release versiona o dataset e publica os checksums acima.
      </p>
    </div>
  );
}
