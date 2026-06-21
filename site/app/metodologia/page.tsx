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

      <h2>9. Dengue (SINAN)</h2>
      <ul>
        <li>
          <strong>Fonte</strong>: SINAN/DataSUS, arquivos nacionais <code>DENGBR{"{AA}"}.dbc</code>
          (FINAIS e PRELIM). 2024 corresponde à maior epidemia já registrada (6,6 milhões
          de casos prováveis) — número conciliável com os boletins do Ministério da Saúde.
        </li>
        <li>
          <strong>Caso provável</strong> = notificação não descartada
          (<code>CLASSI_FIN ≠ 5</code>), convenção da vigilância epidemiológica;
        </li>
        <li>
          <strong>Caso grave</strong> = dengue com sinais de alarme ou grave
          (<code>CLASSI_FIN</code> 11, 12) ou, no padrão legado, FHD/SCD (3, 4);
        </li>
        <li><strong>Óbito por dengue</strong> = <code>EVOLUCAO = 2</code>;</li>
        <li>
          Município de <strong>residência</strong> (<code>ID_MN_RESI</code>) e semana
          epidemiológica pela <strong>data dos primeiros sintomas</strong> (<code>SEM_PRI</code>);
        </li>
        <li>
          <strong>Incidência</strong> = casos prováveis por 100 mil hab.;
          <strong>letalidade</strong> = óbitos / casos prováveis;
        </li>
        <li>Em anos recentes a classificação ainda está em andamento, o que pode reduzir descartes.</li>
      </ul>

      <h2>10. Internações hospitalares (SIH/AIH)</h2>
      <ul>
        <li>
          <strong>Fonte</strong>: SIH/DataSUS, arquivos <code>RD{"{UF}{AAMM}"}.dbc</code>
          (AIH aprovadas, rede SUS). Cobre apenas internações pagas pelo SUS — não
          inclui rede privada/suplementar;
        </li>
        <li>Município de <strong>residência</strong> (<code>MUNIC_RES</code>); causa pelo <strong>diagnóstico principal</strong> (<code>DIAG_PRINC</code>), agrupado em capítulos CID-10;</li>
        <li><strong>Permanência média</strong> = soma de <code>DIAS_PERM</code> / nº de internações;</li>
        <li><strong>Mortalidade intra-hospitalar</strong> = <code>MORTE</code> / internações;</li>
        <li><strong>Custo</strong> = valor total aprovado (<code>VAL_TOT</code>); custo médio = valor / internações;</li>
        <li>2024 preliminar; meses podem estar incompletos no processamento mais recente.</li>
      </ul>

      <h2>11. Vulnerabilidade social (proxy, Censo 2022)</h2>
      <p>
        Para permitir cruzar saúde com desigualdade, calculamos um{" "}
        <strong>índice-proxy de vulnerabilidade social</strong> por município, a
        partir de dois indicadores oficiais e atuais do <strong>Censo 2022 (IBGE/SIDRA)</strong>:
      </p>
      <ul>
        <li><strong>Taxa de analfabetismo</strong> (15 anos ou mais) — tabela SIDRA 9543;</li>
        <li><strong>% de domicílios sem ligação à rede geral de água</strong> — tabela SIDRA 6803.</li>
      </ul>
      <p>
        Cada indicador é padronizado por <strong>z-score</strong>
        (<code>z = (x − μ) / σ</code>) e o índice é a média dos dois z-scores,
        reescalada de 0 a 100 (maior = mais vulnerável); os municípios são
        classificados em quartis (Q1 = menos vulnerável … Q4 = mais vulnerável).
      </p>
      <p>
        <strong>Transparência — o que este índice é e o que não é:</strong> trata-se
        de um <em>proxy</em> transparente, reproduzível e <strong>atual (2022)</strong>,
        não do <strong>IVS oficial do IPEA</strong> (Atlas da Vulnerabilidade Social),
        que combina 16 indicadores em três dimensões e tem ano-base 2010. Usamos
        apenas duas dimensões disponíveis municipalmente no Censo 2022 (a renda per
        capita municipal de 2022 ainda não foi liberada). O método de composição por
        z-score segue a linha do{" "}
        <a href="https://github.com/goldenluke/labsus" target="_blank" rel="noreferrer">LabSUS</a>.
        Incorporar o IVS oficial do IPEA está no roadmap.
      </p>

      <h2>12. Internações evitáveis (ICSAP) e fluxo de pacientes</h2>
      <ul>
        <li>
          <strong>ICSAP</strong> — Internações por Condições Sensíveis à Atenção Primária:
          classificamos cada internação do SIH (2024) pelo diagnóstico principal e marcamos
          as condições da <strong>Lista Brasileira de ICSAP</strong> (Portaria SAS/MS 221/2008),
          em aproximação no nível de CID-10 de 3 caracteres (hipertensão, diabetes, ICC,
          pneumonias, asma/DPOC, gastroenterites, ITU, etc.). A proporção de ICSAP é um
          indicador-proxy da qualidade da atenção básica: quanto maior, mais internações que
          bom acesso à atenção primária poderia ter evitado. A aproximação por 3 caracteres
          difere marginalmente da lista oficial (que tem exceções em 4 caracteres).
        </li>
        <li>
          <strong>Fluxo intermunicipal de pacientes</strong> — o SIH registra o município de
          residência (<code>MUNIC_RES</code>) e o de internação (<code>MUNIC_MOV</code>).
          Cruzando os dois, mapeamos para onde os moradores de cada município se internam
          (fluxos intermunicipais com 5+ internações em 2024), revelando dependência de polos
          regionais e evasão da rede local. A ideia segue a linha do{" "}
          <a href="https://github.com/goldenluke/labsus" target="_blank" rel="noreferrer">LabSUS</a>.
        </li>
      </ul>

      <h2>13. Arquétipos de saúde municipal (k-means)</h2>
      <p>
        Agrupamos municípios (população ≥ 20 mil) em cinco perfis por <strong>k-means</strong>
        sobre três dimensões padronizadas por z-score: mortalidade padronizada por idade (2023),
        vulnerabilidade-proxy (Censo 2022) e internações por 100 mil hab. (2023). Cada município
        recebe um rótulo interpretável (ex.: "mortalidade alta, vulnerabilidade média, muita
        internação"), exibido no boletim. Método de normalização z-score + k-means inspirado no LabSUS.
      </p>

      <h2>14. Privacidade</h2>
      <p>
        Nenhum microdado individual é publicado: o banco recebe apenas agregados
        (município × período × categoria), eliminando risco de reidentificação.
      </p>
    </div>
  );
}
