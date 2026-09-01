import { readFileSync } from "node:fs";
import path from "node:path";

import type { Metadata } from "next";
import { SUPABASE_ANON_KEY, SUPABASE_URL } from "@/lib/api";

type TabelaPublicada = { nome: string; linhas: number; bytes: number; sha256: string };

/**
 * Lê o manifesto da publicação corrente no momento do build.
 *
 * Esta tabela já foi uma lista de tamanhos e SHA-256 escrita à mão, e envelheceu
 * em silêncio: `mart_internacoes_municipio` aparecia com 6,0 MB quando o arquivo
 * publicado tinha 9,4 MB, e o hash não conferia com nada. Página que promete
 * verificação de integridade não pode inventar o hash — agora ela lê o mesmo
 * manifesto que o publicador escreve.
 */
function arquivosPublicados(): TabelaPublicada[] {
  const dir = path.join(process.cwd(), "..", "data", "publicacoes");
  const atual = JSON.parse(readFileSync(path.join(dir, "atual.json"), "utf8")) as { arquivo: string };
  const manifesto = JSON.parse(readFileSync(path.join(dir, atual.arquivo), "utf8")) as {
    tabelas: Record<string, TabelaPublicada>;
  };
  return Object.values(manifesto.tabelas).sort((a, b) => b.bytes - a.bytes);
}

function emMB(bytes: number): string {
  return `${(bytes / 1e6).toFixed(bytes < 1e5 ? 2 : 1).replace(".", ",")} MB`;
}

export const metadata: Metadata = {
  title: "Dados & API pública",
  description:
    "API REST pública e gratuita (PostgREST), downloads em Parquet com SHA-256, cliente Python e "
    + "servidor MCP para consultar os indicadores de saúde do Brasil (DataSUS + IBGE) sem cadastro.",
  alternates: { canonical: "/dados/" },
};

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
      <div className="mt-4 rounded-lg border border-accent-200 bg-accent-50 px-4 py-3 text-sm text-ink-800">
        <strong>🔌 Consulte por IA (MCP).</strong> Conecte o Claude Desktop/Code e pergunte a saúde do
        Brasil em linguagem natural — 19 ferramentas, camada de confiabilidade do dado e detector de
        anomalias, com regras anti-alucinação (todo número vem com fonte). Roda na sua máquina, custo zero.{" "}
        <a href="https://github.com/pedropaulofernandes88-stack/saude-publica-br/tree/main/mcp_server" target="_blank" rel="noreferrer" className="font-medium text-accent-700 underline">Guia de instalação →</a>
      </div>

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
            <td><code>mart_vacinacao_municipio</code></td>
            <td>
              doses aplicadas do PNI por município, ano e imunobiológico (2023–2026, alimentado pela RNDS).{" "}
              <strong>Só por download</strong> — é a maior das três e nenhuma tela a consulta, então fica
              fora do banco servido pela API para caber no orçamento de armazenamento; o Parquet, o
              checksum e o histórico continuam completos.{" "}
              <strong>É contagem, não cobertura:</strong> a taxa por município foi construída, testada e
              reprovada — a cobertura mediana cai de 102,7% nos municípios com 50 a 100 nascidos para 86,2%
              nos com mais de 5 mil, o que é viés de denominador, não variação real.
            </td>
            <td>~933 mil</td>
          </tr>
          <tr>
            <td><code>mart_vacinacao_uf_mes</code></td>
            <td>
              doses aplicadas por competência mensal, UF e imunobiológico. É a série mais atual do
              projeto — vai até o mês passado.
            </td>
            <td>~72 mil</td>
          </tr>
          <tr>
            <td><code>mart_cobertura_vacinal_uf</code></td>
            <td>
              cobertura vacinal em menores de 1 ano por UF e ano, só onde há nascidos vivos definitivos
              (2023–2024) e só para cinco indicadores da atenção básica. BCG e hepatite B ao nascer ficam
              de fora: aplicadas na maternidade, não têm denominador adequado nem por UF.
            </td>
            <td>270</td>
          </tr>
          <tr>
            <td><code>mart_qualidade_registro_municipio</code></td>
            <td>índice de confiabilidade do registro de óbitos por município (% causas mal-definidas, 2022–2024) com classificação Bom/Regular/Ruim</td>
            <td>5.595</td>
          </tr>
          <tr>
            <td><code>dim_ivs</code></td>
            <td>vulnerabilidade social municipal (proxy Censo 2022: analfabetismo + água; z-score)</td>
            <td>5.570</td>
          </tr>
          <tr>
            <td><code>dim_cluster_municipio</code></td>
            <td>
              estrato de saúde municipal: cruzamento dos tercis de mortalidade × vulnerabilidade ×
              internações (2023), em 27 grupos, com os cortes congelados no repositório.{" "}
              <strong>Determinístico:</strong> o estrato depende só dos valores do próprio município, então
              a mesma consulta devolve sempre a mesma resposta. Substituiu em 29/08/2026 o agrupamento por
              k-means, que foi medido e reprovado (índice de Rand ajustado 0,571 entre reamostragens; 16% dos
              municípios trocavam de grupo sem que o dado deles mudasse).
            </td>
            <td>~1,7 mil</td>
          </tr>
          <tr>
            <td><code>mart_icsap_municipio</code></td>
            <td>internações evitáveis (ICSAP) por município, 2021–2024: total, ICSAP, % e por 100k hab. Inclui o <strong>grupo 1 da Lista Brasileira</strong> — doenças preveníveis por imunização (<code>internacoes_g1</code>, <code>g1_100k</code>), exibido no boletim municipal e cruzável com as doses do PNI.</td>
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
        <strong>Importante:</strong> nem toda linha é uma observação. Algumas são
        subtotais pré-calculados (<code>TOTAL</code>) e outras são marcadores de
        ausência (<code>IGN</code>, <code>ND</code>, códigos <code>&lt;UF&gt;0000</code>).
        Somar sem filtrá-los produz dupla contagem ou município fantasma — a lista
        completa está em <a href="#sentinelas">Valores sentinela</a>, adiante.
      </p>

      <h2 id="sistemas-de-codigo">Sistemas de código</h2>
      <p>
        As colunas de código não carregam identificadores internos: seguem sistemas
        externos padronizados. Isso torna a base unível a qualquer outra fonte que use
        os mesmos sistemas — inclusive prontuários e sistemas clínicos conformes aos
        perfis da{" "}
        <a href="https://rnds-fhir.saude.gov.br/" target="_blank" rel="noreferrer">RNDS</a>{" "}
        (BR Core). São quatro os sistemas com URI canônico — os demais são convenção
        desta base e estão marcados como tal.
      </p>
      <pre>
        <code>{`# URIs canônicos, para bindings FHIR / terminologia
IBGE, município-UF-região   https://rnds-fhir.saude.gov.br/CodeSystem/BRDivisaoGeograficaBrasil
CID-10                      https://rnds-fhir.saude.gov.br/NamingSystem/BRCID10
CNES                        https://rnds-fhir.saude.gov.br/NamingSystem/cnes
Sexo                        http://hl7.org/fhir/administrative-gender`}</code>
      </pre>
      <p className="text-sm text-ink-500">
        Definições:{" "}
        <a href="https://rnds-fhir.saude.gov.br/CodeSystem-BRDivisaoGeograficaBrasil.html" target="_blank" rel="noreferrer">BRDivisaoGeograficaBrasil</a>{" · "}
        <a href="https://rnds-fhir.saude.gov.br/NamingSystem-BRCID10.html" target="_blank" rel="noreferrer">BRCID10</a>{" · "}
        <a href="https://rnds-fhir.saude.gov.br/NamingSystem-cnes.html" target="_blank" rel="noreferrer">CNES</a>{" · "}
        <a href="https://rnds-fhir.saude.gov.br/ValueSet-BRSexo-1.0.html" target="_blank" rel="noreferrer">BRSexo-1.0</a>.
      </p>
      <table>
        <thead>
          <tr>
            <th>Coluna</th>
            <th>Sistema</th>
            <th>Formato nesta base</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>municipio_cod</code>, <code>municipio_res</code>, <code>municipio_mov</code></td>
            <td>IBGE, nível município</td>
            <td><strong>6 dígitos</strong>, sem dígito verificador (<code>355030</code>). É o mesmo nível adotado pela RNDS — junta sem conversão</td>
          </tr>
          <tr>
            <td><code>municipio_cod7</code> (só em <code>dim_municipio</code>)</td>
            <td>IBGE, nível município</td>
            <td>7 dígitos, <em>com</em> dígito verificador (<code>3550308</code>). Use <code>dim_municipio</code> para converter entre as duas formas</td>
          </tr>
          <tr>
            <td><code>uf_sigla</code>, <code>uf_res</code>, <code>uf_mov</code></td>
            <td>IBGE, nível UF</td>
            <td>sigla de 2 letras (<code>SP</code>). <strong>Não</strong> é o código numérico: o equivalente da RNDS são os <strong>2 primeiros dígitos</strong> de <code>municipio_cod</code> (<code>35</code>)</td>
          </tr>
          <tr>
            <td><code>regiao</code></td>
            <td>IBGE, nível região</td>
            <td>nome da macrorregião. O código de 1 dígito é o <strong>primeiro</strong> de <code>municipio_cod</code></td>
          </tr>
          <tr>
            <td><code>capitulo_cid</code>, <code>capitulo_principal</code></td>
            <td>CID-10, capítulo</td>
            <td>numeral romano, <code>I</code>–<code>XXII</code>. A faixa correspondente está em <code>dim_cid10_capitulo.faixa</code> (<code>O00-O99</code>)</td>
          </tr>
          <tr>
            <td><code>causabas_3</code></td>
            <td>CID-10, categoria</td>
            <td><strong>3 caracteres</strong> (<code>G31</code>). Vem de <code>CAUSABAS</code> no SIM e <code>DIAG_PRINC</code> no SIH; descrições em <code>dim_cid10_categoria</code></td>
          </tr>
          <tr>
            <td><code>cnes</code></td>
            <td>CNES</td>
            <td>7 dígitos, <strong>string com zeros à esquerda</strong> (<code>0000035</code>). Converter para número destrói a chave</td>
          </tr>
          <tr>
            <td><code>sexo</code></td>
            <td>HL7 <code>administrative-gender</code></td>
            <td><code>M</code> / <code>F</code> / <code>I</code> equivalem a <code>male</code> / <code>female</code> / <code>unknown</code> — os mesmos três valores do <code>BRSexo-1.0</code></td>
          </tr>
          <tr>
            <td><code>ano_epi</code> + <code>semana_epi</code></td>
            <td>semana epidemiológica (MS)</td>
            <td>SE de 1 a 53, com ano epidemiológico próprio — <strong>não coincide</strong> com o ano civil na virada. Sem equivalente FHIR</td>
          </tr>
          <tr>
            <td><code>mes_competencia</code></td>
            <td>ISO 8601</td>
            <td>primeiro dia do mês (<code>2023-03-01</code>), não uma data de evento</td>
          </tr>
          <tr>
            <td><code>faixa_etaria</code></td>
            <td>convenção desta base</td>
            <td><code>&lt;1</code>, <code>1-4</code>, <code>5-14</code>, <code>15-29</code>, <code>30-44</code>, <code>45-59</code>, <code>60-74</code>, <code>75+</code>. Escolhida para a padronização por idade; <strong>não</strong> é sistema externo</td>
          </tr>
          <tr>
            <td><code>agravo</code>, <code>agravo_label</code>, <code>grupo</code></td>
            <td>convenção desta base</td>
            <td>chaves derivadas de prefixos CID-10 de 3 caracteres. O mapa canônico é o dicionário <code>AGRAVOS</code> em <code>scripts/pipeline_sih_agravo.py</code></td>
          </tr>
          <tr>
            <td><code>internacoes_icsap</code>, <code>pct_icsap</code></td>
            <td>Lista Brasileira de ICSAP</td>
            <td>Portaria SAS/MS 221/2008, aproximada no nível de CID-10 de 3 caracteres</td>
          </tr>
        </tbody>
      </table>

      <h3 id="sentinelas">Valores sentinela</h3>
      <p>
        Estes valores ocupam colunas de código sem serem códigos. Tratá-los como
        categoria real é o erro mais comum cometido em cima desta base:
      </p>
      <table>
        <thead>
          <tr><th>Valor</th><th>Colunas</th><th>Significa</th></tr>
        </thead>
        <tbody>
          <tr>
            <td><code>TOTAL</code></td>
            <td><code>capitulo_cid</code>, <code>sexo</code>, <code>faixa_etaria</code></td>
            <td>subtotal pré-calculado. Somado junto com as partes, <strong>dobra a contagem</strong> — filtre explicitamente</td>
          </tr>
          <tr>
            <td><code>I</code> / <code>IGN</code></td>
            <td><code>sexo</code> / <code>faixa_etaria</code></td>
            <td>atributo ignorado no registro de origem. É um evento real com campo ausente — descartá-lo subestima o total</td>
          </tr>
          <tr>
            <td><code>ND</code></td>
            <td><code>uf_sigla</code></td>
            <td>UF não identificada</td>
          </tr>
          <tr>
            <td><code>&lt;UF&gt;0000</code></td>
            <td><code>municipio_cod</code></td>
            <td>agregado de &quot;município ignorado&quot; da UF. <code>110000</code> é Rondônia sem município identificado, não uma cidade — há um código desses por UF</td>
          </tr>
        </tbody>
      </table>
      <p>
        O IBGE tem <strong>5.571</strong> municípios; as tabelas municipais trazem mais
        linhas justamente por causa dos agregados acima. A regra de exclusão usada pelo
        site é pública em{" "}
        <a href="https://github.com/pedropaulofernandes88-stack/saude-publica-br/blob/main/site/lib/municipios.ts" target="_blank" rel="noreferrer">
          <code>site/lib/municipios.ts</code>
        </a>{" "}
        (<code>ehCodigoAgregado</code> e <code>municipioIdentificado</code>).
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
          {arquivosPublicados().map(({ nome, bytes, sha256, linhas }) => (
            <tr key={nome}>
              <td>
                <a href={`${SUPABASE_URL}/storage/v1/object/public/dados/${nome}.parquet`} download>
                  {nome}.parquet
                </a>
                <br />
                <span style={{ fontSize: "0.78em", opacity: 0.7 }}>
                  {linhas.toLocaleString("pt-BR")} linhas
                </span>
              </td>
              <td>{emMB(bytes)}</td>
              <td>
                <code style={{ fontSize: "0.7em", wordBreak: "break-all" }}>{sha256}</code>
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
          <tr><td>Dengue</td><td>SINAN</td><td>2015–2025</td><td>2025 fechado (FINAIS)</td></tr>
          <tr><td>Nascimentos</td><td>SINASC</td><td>2021–2023</td><td>2024 não liberado pelo MS</td></tr>
          <tr><td>Vulnerabilidade / população</td><td>IBGE Censo 2022 + estimativas</td><td>2022 (2023 interpolado)</td><td>renda municipal 2022 ainda não liberada</td></tr>
        </tbody>
      </table>

      <h2>Observatório de qualidade do registro</h2>
      <p>
        A transparência exige medir o que é incerto. Publicamos um{" "}
        <strong>índice de confiabilidade do registro de óbitos por município</strong>{" "}
        (<code>mart_qualidade_registro_municipio</code>), baseado na proporção de{" "}
        <strong>causas mal-definidas</strong> (capítulo XVIII — sintomas e sinais),
        indicador clássico de qualidade da informação em mortalidade (padrão RIPSA/OPAS).
        No agregado nacional a proporção é de <strong>5,2%</strong> (2022–2024), mas o
        número esconde a desigualdade: <strong>1.096 municípios (1 em cada 5)</strong>{" "}
        estão na classe <strong>Ruim</strong> (&gt; 10%), onde a causa de morte é pouco
        confiável — concentrados no Norte e Nordeste.
      </p>
      <p>
        Classificação: <strong>Bom</strong> (&lt; 5%), <strong>Regular</strong> (5–10%),{" "}
        <strong>Ruim</strong> (&gt; 10%). Não redistribuímos causas mal-definidas entre
        causas específicas — elas permanecem visíveis. Use as taxas causa-específicas com
        essa ressalva onde a confiabilidade é menor. O índice serve para{" "}
        <strong>direcionar busca ativa de óbitos</strong> e para ponderar comparações.
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
DOI: 10.5281/zenodo.20706845. Acesso em: AAAA-MM-DD.
Fontes primárias: DATASUS (SIM, SIH, SINAN, SINASC) e IBGE.`}</code>
      </pre>
      <p className="text-sm text-ink-500">
        DOI de conceito (todas as versões) no Zenodo:{" "}
        <a href="https://doi.org/10.5281/zenodo.20706845" target="_blank" rel="noreferrer">10.5281/zenodo.20706845</a>.
        O repositório traz <code>CITATION.cff</code> para citação automática (botão "Cite this
        repository" no GitHub). Cada release versiona o dataset e publica os checksums acima.
      </p>
    </div>
  );
}
