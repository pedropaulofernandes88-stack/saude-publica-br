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
            <td>município × ano × capítulo CID-10 × sexo (+ taxas /100 mil hab.)</td>
            <td>~600 mil</td>
          </tr>
          <tr>
            <td><code>mart_mortalidade_uf_mes</code></td>
            <td>UF × mês × capítulo × sexo × faixa etária</td>
            <td>~324 mil</td>
          </tr>
          <tr>
            <td><code>mart_mortalidade_causa</code></td>
            <td>UF × ano × causa básica (CID-10, 3 caracteres)</td>
            <td>~62 mil</td>
          </tr>
          <tr>
            <td><code>dim_municipio</code></td>
            <td>municípios IBGE (códigos 6/7 dígitos, UF, região)</td>
            <td>5.571</td>
          </tr>
          <tr>
            <td><code>dim_populacao</code></td>
            <td>população municipal por ano</td>
            <td>~16,7 mil</td>
          </tr>
          <tr>
            <td><code>dim_cid10_capitulo</code></td>
            <td>capítulos da CID-10</td>
            <td>22</td>
          </tr>
          <tr>
            <td><code>meta_dataset</code></td>
            <td>metadados: fontes, datas, exclusões, licença</td>
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
            ["mart_mortalidade_municipio.parquet", "5,7 MB", "d9648fbd240033477a8854f2d3139d5fc1d434a601a997a386668fee88fb6b82"],
            ["mart_mortalidade_uf_mes.parquet", "1,2 MB", "3658cea00a05ba45f4379be35cc20b2000ddd31ef41fbc5aca440b0918fc4826"],
            ["mart_mortalidade_causa.parquet", "0,2 MB", "24179a19691f56447e8c903570a408271bece76fd9ee520c914c1ccf9f9ede2e"],
            ["dim_municipio.parquet", "0,06 MB", "c446195fc9c5aa637948efde3c79bcd84dd70e059893008bd43924f189e446ee"],
            ["dim_populacao.parquet", "0,05 MB", "0af1b438eb832284c220f91f0c3aab32a3d0b7ff7d9ee60454d81c8dffc2d9b6"],
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

      <h2>Licença e citação</h2>
      <p>
        Dados originais em domínio público (DATASUS/Ministério da Saúde e IBGE).
        Agregações e código sob licença MIT. Em publicações, cite as fontes
        primárias (SIM/DataSUS; IBGE) e, se desejar, esta plataforma.
      </p>
    </div>
  );
}
