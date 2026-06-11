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
        para permitir avaliação crítica e reprodução independente. Todo o
        processamento é feito por um único script aberto
        (<code>scripts/pipeline_v2.py</code>).
      </p>

      <h2>1. Fontes de dados</h2>
      <ul>
        <li>
          <strong>Óbitos 2022–2024</strong> — SIM/DataSUS, CSVs nacionais do{" "}
          <a href="https://opendatasus.saude.gov.br/dataset/sim" target="_blank" rel="noreferrer">OpenDataSUS</a>{" "}
          (<code>DO22OPEN</code>–<code>DO24OPEN</code>).
        </li>
        <li>
          <strong>Óbitos 2015–2021</strong> — SIM/DataSUS, arquivos <code>.dbc</code> por
          UF/ano do FTP oficial (<code>SIM/CID10/DORES</code>), convertidos com a
          biblioteca aberta <code>datasus-dbc</code>. Total da série:{" "}
          <strong>mais de 13 milhões de óbitos não fetais</strong>.
        </li>
        <li>
          <strong>População total</strong> — IBGE: Estimativas anuais (SIDRA t/6579),
          Censo 2022 (t/4709); 2023 por interpolação linear Censo↔Estimativas 2024.
        </li>
        <li>
          <strong>População por idade</strong> — Censo 2022 (SIDRA t/9514), agregada
          em 8 faixas etárias por município.
        </li>
        <li>
          <strong>Malha municipal e cadastro</strong> — IBGE (APIs de localidades e malhas).
        </li>
        <li>
          <strong>Descrições CID-10</strong> — tabela oficial <code>CID10.DBF</code> do
          FTP do SIM.
        </li>
      </ul>

      <h2>2. Critérios de inclusão e derivações</h2>
      <ul>
        <li>Óbitos fetais excluídos (<code>TIPOBITO=1</code>), convenção de mortalidade geral;</li>
        <li>Município de <strong>residência</strong> do falecido (<code>CODMUNRES</code>);</li>
        <li>Causa básica truncada à categoria CID-10 de 3 caracteres; capítulos (I–XXII) pelas faixas oficiais;</li>
        <li>
          Idade decodificada do campo composto <code>IDADE</code> (dígito 4 = anos;
          5 = 100+; 0–3 = menor de 1 ano; demais = ignorada). Faixas: &lt;1, 1–4,
          5–14, 15–29, 30–44, 45–59, 60–74, 75+;
        </li>
        <li>Local do óbito (<code>LOCOCOR</code>): 1 = hospital; 3 = domicílio;</li>
        <li>Dados de 2024 <strong>preliminares</strong>, sujeitos a revisão pelo MS.</li>
      </ul>

      <h2>3. Granularidade por período</h2>
      <p>
        Para caber em infraestrutura gratuita sem sacrificar o essencial, a base
        publica <strong>detalhe demográfico completo a partir de 2022</strong>{" "}
        (capítulo × sexo × faixa etária) e, para 2015–2021, totais e marginais
        (por capítulo, por sexo e por faixa — sem cruzamentos entre eles). Os
        marts de causa (3 caracteres) e as séries mensais por UF cobrem todos os anos.
      </p>

      <h2>4. Taxa padronizada por idade</h2>
      <p>
        Método <strong>direto</strong>: a taxa específica de cada faixa etária do
        município é ponderada pela estrutura etária de uma população padrão —
        aqui, a do <strong>Brasil no Censo 2022</strong>. Isso remove o efeito da
        composição etária e torna municípios comparáveis (um município
        envelhecido não aparece "pior" só por ser envelhecido).
      </p>
      <ul>
        <li>Óbitos com idade ignorada são redistribuídos pro-rata entre as faixas conhecidas do mesmo município/ano;</li>
        <li>
          Para anos ≠ 2022, a população por faixa é a estrutura do Censo 2022
          escalada pelo total municipal do ano (aproximação documentada — censos
          municipais por idade não existem anualmente);
        </li>
        <li>Calculada para o total de causas (capítulo = TOTAL, sexo = total).</li>
      </ul>

      <h2>5. Intervalos de confiança (IC95%)</h2>
      <p>
        A taxa bruta acompanha IC95% pelo método <strong>gamma (Poisson exato)</strong>:
        limite inferior = <code>qgamma(0,025; d)/pop</code>, superior ={" "}
        <code>qgamma(0,975; d+1)/pop</code>. Em municípios pequenos o intervalo é
        largo — o painel sinaliza população &lt; 10 mil hab. com ⚠ para evitar
        leituras indevidas de taxas instáveis.
      </p>

      <h2>6. Excesso de mortalidade</h2>
      <p>
        Para cada UF (e Brasil), o <strong>esperado</strong> do mês <em>m</em> do ano{" "}
        <em>a</em> é a média de óbitos do mesmo mês civil em 2015–2019,
        multiplicada pela razão entre a população de <em>a</em> e a população
        média 2015–2019. <strong>Excesso = observado − esperado</strong>. É um
        método transparente e replicável; não modela tendência secular nem
        sazonalidade além do mês civil (limitação declarada).
      </p>

      <h2>7. Validação automática</h2>
      <ul>
        <li>Totais anuais conferidos contra os volumes oficiais do SIM (ex.: 2015 = 1.264.175; 2022 ≈ 1,54M);</li>
        <li>Subtotais (linhas TOTAL) conciliáveis com qualquer recorte da API;</li>
        <li>Perfil por capítulo compatível com a literatura (circulatórias &gt; neoplasias &gt; respiratórias);</li>
        <li>Checagens executadas também em CI (GitHub Actions) a cada atualização.</li>
      </ul>

      <h2>8. Limitações conhecidas</h2>
      <ul>
        <li>Qualidade de registro e cobertura do SIM variam regionalmente e melhoraram ao longo do tempo — parte das tendências longas reflete melhora de captação;</li>
        <li>Garbage codes (ex.: R99) não são redistribuídos entre causas;</li>
        <li>A taxa padronizada usa estrutura etária fixa (Censo 2022) escalada — aproximação para anos distantes de 2022;</li>
        <li>O baseline do excesso não modela tendência de longo prazo;</li>
        <li>2024 preliminar; revisões do MS alteram os números do último ano.</li>
      </ul>

      <h2>9. Privacidade</h2>
      <p>
        Nenhum microdado individual é publicado: o banco recebe apenas agregados
        (município × período × categoria), eliminando risco de reidentificação.
      </p>
    </div>
  );
}
