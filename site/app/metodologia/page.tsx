import type { Metadata } from "next";

export const metadata: Metadata = { title: "Metodologia" };

export default function Metodologia() {
  return (
    <div className="prose-doc mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
        Metodologia
      </h1>
      <p>
        Esta página documenta integralmente como os indicadores são produzidos,
        para permitir avaliação crítica e reprodução independente dos resultados.
      </p>

      <h2>1. Fontes de dados</h2>
      <ul>
        <li>
          <strong>Óbitos</strong> — Sistema de Informações sobre Mortalidade
          (SIM), Ministério da Saúde. Microdados nacionais abertos publicados no{" "}
          <a href="https://opendatasus.saude.gov.br/dataset/sim" target="_blank" rel="noreferrer">OpenDataSUS</a>{" "}
          (arquivos <code>DO22OPEN.csv</code>, <code>DO23OPEN.csv</code>,{" "}
          <code>DO24OPEN.csv</code>). Total processado:{" "}
          <strong>4.436.222 óbitos não fetais</strong> (2022–2024).
        </li>
        <li>
          <strong>População</strong> — IBGE: Censo Demográfico 2022 (SIDRA,
          tabela 4709) e Estimativas de População 2024 (SIDRA, tabela 6579).
        </li>
        <li>
          <strong>Malha municipal</strong> — IBGE, API de localidades (5.571
          municípios, códigos de 6 e 7 dígitos).
        </li>
      </ul>

      <h2>2. Critérios de inclusão e exclusão</h2>
      <ul>
        <li>
          <strong>Óbitos fetais excluídos</strong> (<code>TIPOBITO = 1</code>),
          seguindo a convenção de mortalidade geral do DATASUS/TabNet.
        </li>
        <li>
          Registros com mês inválido ou ano fora da cobertura são descartados.
        </li>
        <li>
          O município de referência é o de <strong>residência do falecido</strong>{" "}
          (<code>CODMUNRES</code>), não o de ocorrência.
        </li>
        <li>
          Dados de <strong>2024 podem ser preliminares</strong>, sujeitos a
          revisão pelo Ministério da Saúde.
        </li>
      </ul>

      <h2>3. Derivação de variáveis</h2>
      <ul>
        <li>
          <strong>Causa básica</strong> (<code>CAUSABAS</code>): truncada à
          categoria CID-10 de 3 caracteres; capítulos (I–XXII) atribuídos pelas
          faixas oficiais de códigos (ex.: IX = I00–I99, circulatório).
        </li>
        <li>
          <strong>Idade</strong>: decodificada do campo composto <code>IDADE</code>{" "}
          do SIM — primeiro dígito 4 = idade em anos; 5 = 100 + anos; 0–3
          (minutos/horas/dias/meses) = menor de 1 ano; demais = ignorada.
          Faixas: &lt;1, 1–4, 5–14, 15–29, 30–44, 45–59, 60–74, 75+, IGN.
        </li>
        <li>
          <strong>Sexo</strong>: 1 = masculino, 2 = feminino; demais = ignorado.
        </li>
        <li>
          <strong>Local do óbito</strong> (<code>LOCOCOR</code>, dicionário
          oficial SIM): 1 = hospital; 3 = domicílio.
        </li>
      </ul>

      <h2>4. Taxas de mortalidade</h2>
      <p>
        Taxa bruta por 100 mil habitantes ={" "}
        <code>óbitos ÷ população × 100.000</code>, calculada apenas no nível
        município × ano × causa quando sexo = total (a população utilizada não é
        desagregada por sexo). População por ano:
      </p>
      <ul>
        <li>2022 — Censo Demográfico 2022;</li>
        <li>2024 — Estimativas IBGE 2024;</li>
        <li>2023 — interpolação linear entre os dois pontos anteriores.</li>
      </ul>
      <p>
        <strong>Atenção:</strong> taxas brutas não são padronizadas por idade.
        Comparações entre municípios com estruturas etárias muito distintas
        devem considerar esse limite (padronização direta está no roadmap).
      </p>

      <h2>5. Pipeline e reprodução</h2>
      <p>
        Todo o processamento é feito por um único script aberto
        (<code>scripts/pipeline_custo_zero.py</code>): download dos CSVs
        oficiais → derivação de variáveis e agregação em DuckDB → publicação
        dos agregados em PostgreSQL (Supabase). Nenhum microdado individual é
        publicado — apenas agregados, o que também elimina risco de
        reidentificação.
      </p>
      <pre>
        <code>{`pip install duckdb pandas pyarrow requests
python scripts/pipeline_custo_zero.py --anos 2022 2023 2024`}</code>
      </pre>

      <h2>6. Validação</h2>
      <ul>
        <li>
          Totais anuais conferidos contra os volumes esperados do SIM
          (≈1,54M em 2022; ≈1,47M em 2023; ≈1,43M em 2024, preliminar).
        </li>
        <li>
          Distribuição por capítulo compatível com o perfil epidemiológico
          brasileiro (circulatórias &gt; neoplasias &gt; respiratórias).
        </li>
        <li>
          A soma de qualquer recorte da API é conciliável com os subtotais
          (<code>TOTAL</code>) pré-calculados — verificado de ponta a ponta.
        </li>
      </ul>

      <h2>7. Limitações conhecidas</h2>
      <ul>
        <li>Subnotificação e qualidade de preenchimento variam por região;</li>
        <li>Causas garbage codes (ex.: R99) não são redistribuídas;</li>
        <li>Taxas brutas, sem padronização etária;</li>
        <li>2024 sujeito a revisão (dado preliminar do MS).</li>
      </ul>
    </div>
  );
}
