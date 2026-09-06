import type { Metadata } from "next";
import { SECOES, gruposOrdenados, secao } from "@/lib/metodologia-secoes";

export const metadata: Metadata = {
  title: "Metodologia",
  description:
    "Como cada indicador é produzido, em 24 seções com link permanente: fontes, critérios de inclusão, "
    + "taxa padronizada por idade, IC95%, excesso de mortalidade, validação automática e as limitações "
    + "conhecidas de cada base (SIM, SINAN, SIH, CNES, SINASC, SIOPS).",
  alternates: { canonical: "/metodologia/" },
};

/**
 * Título de seção com âncora própria. O link "#" ao lado deixa o endereço
 * copiável — é o que torna a seção citável isoladamente.
 */
function H2({ n }: { n: number }) {
  const s = secao(n);
  return (
    <h2 id={s.slug} className="group scroll-mt-24">
      {s.n}. {s.titulo}{" "}
      <a
        href={`#${s.slug}`}
        aria-label={`Link permanente para a seção ${s.n}, ${s.titulo}`}
        className="ml-1 text-ink-500 no-underline opacity-0 transition group-hover:opacity-100 focus:opacity-100"
      >
        #
      </a>
    </h2>
  );
}

function Sumario() {
  return (
    <nav aria-labelledby="sumario-titulo" className="sumario mt-8 rounded-lg border border-ink-200 bg-ink-50/60 p-5">
      <h2 id="sumario-titulo" className="font-serif text-lg font-semibold text-ink-900">
        Nesta página
      </h2>
      <p className="mt-1 text-xs text-ink-500">
        {SECOES.length} seções. Cada título tem link permanente — use-o para citar a seção.
      </p>
      <div className="mt-4 grid gap-x-8 gap-y-4 sm:grid-cols-2">
        {gruposOrdenados().map(({ grupo, secoes }) => (
          <div key={grupo}>
            <p className="text-xs font-semibold uppercase tracking-wider text-accent-700">{grupo}</p>
            <ul className="mt-1 space-y-1">
              {secoes.map((s) => (
                <li key={s.slug} className="text-sm leading-snug">
                  <a href={`#${s.slug}`} className="text-ink-700 hover:text-accent-700">
                    <span className="tabular-nums text-ink-500">{s.n}.</span> {s.titulo}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}

export default function Metodologia() {
  return (
    <div className="prose-doc mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
        Metodologia
      </h1>
      <p>
        Esta página documenta integralmente como os indicadores são produzidos,
        para permitir avaliação crítica e reprodução independente. O processamento
        é feito por scripts abertos e versionados em <code>scripts/</code>:{" "}
        <code>pipeline_v2.py</code> (mortalidade e população) e pipelines dedicados
        para dengue (SINAN), internações (SIH), nascimentos (SINASC) e os recortes
        de internação por agravo/hospital.
      </p>

      <Sumario />

      <H2 n={1} />
      <ul>
        <li>
          <strong>Óbitos 2022–2023</strong> — SIM/DataSUS, CSVs nacionais do{" "}
          <a href="https://opendatasus.saude.gov.br/dataset/sim" target="_blank" rel="noreferrer">OpenDataSUS</a>{" "}
          (<code>DO22OPEN</code>, <code>DO23OPEN</code>).
        </li>
        <li>
          <strong>Óbitos 2015–2021 e 2024</strong> — SIM/DataSUS, arquivos{" "}
          <code>.dbc</code> por UF/ano do FTP oficial (<code>SIM/CID10/DORES</code>),
          convertidos com a biblioteca aberta <code>datasus-dbc</code>.
        </li>
        <li>
          <strong>Óbitos 2025 — PRELIMINARES</strong> — mesma origem, mas do diretório{" "}
          <code>SIM/PRELIM/DORES</code>, que o DataSUS ainda não fechou. Entram na base{" "}
          <strong>marcados</strong> (coluna <code>preliminar</code>) e ficam{" "}
          <strong>fora de toda análise</strong>. Medimos 2025 e ele{" "}
          <em>não</em> exibe os defeitos típicos de ano aberto: os doze meses estão
          entre 1,07 e 1,14 vez a mediana de 2015–2024, dezembro inclusive, e as causas
          mal definidas somam 4,51% — igual a 2024. Ou seja, no agregado nacional o volume fechou
          e a codificação parece madura — mas não uniformemente: pela mesma régua de
          completude aplicada aos gráficos, Roraima ainda tem seis meses de 2025 abaixo do
          esperado, e Acre e Amapá, dois cada. Mesmo assim ele fica fora, porque o que sabemos de
          2024 é que a <em>versão</em> de um ano muda depois de fechado: ao consolidar,
          milhares de óbitos migraram de R99 para causas específicas. Parecer estável e
          ter sido verificado estável são coisas diferentes, e a segunda só é possível
          quando a versão consolidada existir. Servem para acompanhar o ano corrente,
          não para comparar com os anteriores.
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

      <H2 n={2} />
      <ul>
        <li>
          <strong>Óbitos fetais fora da base — pela fonte, não pelo filtro.</strong> A
          convenção de mortalidade geral exclui óbito fetal, e o pipeline mantém o filtro{" "}
          <code>TIPOBITO ≠ 1</code>. Mas conferindo o campo nos 14.484.496 registros,{" "}
          <strong>100% têm <code>TIPOBITO = 2</code></strong> nas duas fontes: o óbito
          fetal vive num arquivo separado do DataSUS (<code>SIM/CID10/DOFET</code>) que
          este projeto não coleta. Ou seja, a exclusão acontece na origem e o filtro
          nunca removeu nenhum registro — ele existe como defesa, para o dia em que uma
          fonte passar a misturar os dois;
        </li>
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

      <H2 n={3} />
      <p>
        Para caber em infraestrutura gratuita sem sacrificar o essencial, a base
        publica <strong>detalhe demográfico completo a partir de 2022</strong>{" "}
        (capítulo × sexo × faixa etária) e, para 2015–2021, totais e marginais
        (por capítulo, por sexo e por faixa — sem cruzamentos entre eles). Os
        marts de causa (3 caracteres) e as séries mensais por UF cobrem todos os anos.
      </p>

      <H2 n={4} />
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

      <H2 n={5} />
      <p>
        A taxa bruta acompanha IC95% pelo método <strong>gamma (Poisson exato)</strong>:
        limite inferior = <code>qgamma(0,025; d)/pop</code>, superior ={" "}
        <code>qgamma(0,975; d+1)/pop</code>. Em municípios pequenos o intervalo é
        largo — o painel sinaliza população &lt; 10 mil hab. com ⚠ para evitar
        leituras indevidas de taxas instáveis.
      </p>

      <H2 n={6} />
      <p>
        Para cada UF (e Brasil), o <strong>esperado</strong> do mês <em>m</em> do ano{" "}
        <em>a</em> vem de uma <strong>tendência linear ajustada ao período 2015–2019</strong>,
        por mês civil: regredimos os óbitos daquele mês contra o ano (mínimos quadrados, 5 pontos)
        e projetamos para <em>a</em>. Isso captura tanto o crescimento populacional quanto o{" "}
        <strong>envelhecimento</strong> — que elevam o número esperado de óbitos ano a ano —,
        corrigindo um viés do método anterior (média 2015–2019 × razão populacional), que ignorava
        a tendência secular e por isso <em>superestimava</em> o excesso nos anos recentes.{" "}
        <strong>Excesso = observado − esperado</strong>; método transparente e replicável.
      </p>
      <p>
        <strong>Efeito da correção (Brasil):</strong> o pico pandêmico permanece robusto
        (2020–2021 ≈ <strong>643 mil</strong> óbitos em excesso, ~8% abaixo do método anterior),
        mas o "excesso persistente" de 2022–2023 encolhe muito — era em boa parte artefato da
        tendência não modelada — e <strong>2024 fica próximo de zero</strong>.{" "}
        <strong>Cautela com 2024:</strong> a extrapolação é menos confiável no extremo da série{" "}
        <em>e</em> os dados de 2024 ainda são preliminares (subcontagem que puxa o observado para
        baixo) — não interpretar o valor literalmente.
      </p>
      <p>
        Limitações remanescentes: a extrapolação linear assume que a tendência pré-pandemia teria
        continuado e não modela <em>harvesting</em> (deslocamento de mortalidade).
      </p>
      <p>
        <strong>Robustez (padronização por idade).</strong> Testamos uma variante do esperado{" "}
        <em>padronizada por idade</em>, usando a população por idade/UF/ano da projeção do IBGE
        (revisão 2018). Ela estima o pico pandêmico em ~505 mil — <em>abaixo</em> do nosso valor
        (643 mil) <em>e</em> do consenso de estimativas independentes (~680 mil) — e gera excesso
        fortemente negativo em 2023–2024. Nossa primeira hipótese foi o <strong>denominador</strong>:
        a projeção 2018 superestima a população (o Censo 2022 a revisou para baixo) e a série pós-Censo
        tem uma <strong>descontinuidade em 2022</strong>.
      </p>
      <p>
        <strong>Teste de convergência.</strong> Para isolar a causa, reconciliamos o denominador —
        interpolando o total populacional por UF entre os Censos 2010 e 2022 (removendo o overcount e o
        degrau; a população de 2020 cai de 211,8 para ~200,9 milhões) — e recomputamos o excesso. Ele
        subiu, mas <strong>não convergiu</strong>: permaneceu em ~530 mil, ainda ~18% abaixo da tendência.
        Ou seja, o denominador é <em>um</em> fator, mas não o todo — parte do gap é <strong>metodológica</strong>
        (como cada método projeta o esperado sob envelhecimento acelerado). Por isso <strong>retivemos o
        método de tendência</strong>, que tem a melhor concordância com as estimativas independentes e não
        depende do denominador. Scripts e séries de ambas as análises estão no repositório.
      </p>

      <H2 n={7} />
      <ul>
        <li>Totais anuais conferidos contra os volumes oficiais do SIM (ex.: 2015 = 1.264.175; 2022 ≈ 1,54M);</li>
        <li>Subtotais (linhas TOTAL) conciliáveis com qualquer recorte da API;</li>
        <li>Perfil por capítulo compatível com a literatura (circulatórias &gt; neoplasias &gt; respiratórias);</li>
        <li>Checagens executadas também em CI (GitHub Actions) a cada atualização.</li>
      </ul>

      <H2 n={8} />
      <ul>
        <li>Qualidade de registro e cobertura do SIM variam regionalmente e melhoraram ao longo do tempo — parte das tendências longas reflete melhora de captação;</li>
        <li>Garbage codes (ex.: R99) não são redistribuídos entre causas;</li>
        <li>A taxa padronizada usa estrutura etária fixa (Censo 2022) escalada — aproximação para anos distantes de 2022;</li>
        {/* Esta linha dizia "O baseline do excesso não modela tendência de longo
            prazo" — verdade do método ANTIGO (média 2015–2019 × razão populacional),
            que a §6 declara ter sido substituído justamente por não modelar a
            tendência. Ficou para trás na troca, afirmando ao leitor o oposto do que
            o §6 descreve, dentro da seção de limitações — o lugar onde a
            contradição custa mais caro. O que segue é a limitação que o método
            atual de fato tem. */}
        <li>
          O baseline do excesso ajusta a tendência sobre <strong>5 pontos</strong> por mês
          civil (2015–2019) e a extrapola até 5 anos à frente, <strong>sem intervalo de
          incerteza publicado</strong>: o valor é uma estimativa pontual segundo este baseline,
          e a extrapolação perde confiabilidade no extremo da série — ver a cautela com 2024
          na §6;
        </li>
        <li>2024 preliminar; revisões do MS alteram os números do último ano.</li>
      </ul>

      <H2 n={9} />
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

      <H2 n={10} />
      <ul>
        <li>
          <strong>Fonte</strong>: SIH/DataSUS, arquivos <code>RD{"{UF}{AAMM}"}.dbc</code>
          (AIH aprovadas, rede SUS). Cobre apenas internações pagas pelo SUS — não
          inclui rede privada/suplementar;
        </li>
        <li>Município de <strong>residência</strong> (<code>MUNIC_RES</code>); causa pelo <strong>diagnóstico principal</strong> (<code>DIAG_PRINC</code>), agrupado em capítulos CID-10;</li>
        <li><strong>Permanência média</strong> = <code>dias_permanencia_normal</code> / <code>aih_normal</code> (ver tipo de AIH abaixo);</li>
        <li><strong>Mortalidade intra-hospitalar</strong> = <code>MORTE</code> / internações;</li>
        <li><strong>Custo</strong> = valor total aprovado (<code>VAL_TOT</code>); custo médio = <code>valor_normal</code> / <code>aih_normal</code>;</li>
        <li>2024 preliminar; meses podem estar incompletos no processamento mais recente.</li>
        <li>
          <strong>Tipo de AIH — a AIH de continuação (importante):</strong> o arquivo RD
          mistura a AIH normal (<code>IDENT=1</code>) com a AIH de{" "}
          <strong>continuação</strong> (<code>IDENT=5</code>), emitida quando a internação
          se prolonga além do período coberto pela AIH anterior. Uma mesma internação longa
          vira, portanto, <em>várias linhas</em>. Contar linhas é a aproximação correta para{" "}
          <em>produção aprovada</em> — e é o que <code>internacoes</code> mede — mas distorce
          qualquer média por episódio. Numa amostra de 808.470 AIHs (SP, MG, BA, PA e RS,
          2024), a continuação é 1,26% das linhas e <strong>6,57% dos dias</strong> de
          permanência, concentrada em dois capítulos:
          <table className="my-3 w-full text-sm">
            <thead>
              <tr>
                <th className="text-left">Capítulo</th>
                <th className="text-right">Internações</th>
                <th className="text-right">Permanência média</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>VI — sistema nervoso</td>
                <td className="text-right">−19,9%</td>
                <td className="text-right">10,98 → 6,21 dias</td>
              </tr>
              <tr>
                <td>V — transtornos mentais</td>
                <td className="text-right">−23,7%</td>
                <td className="text-right">14,43 → 11,72 dias</td>
              </tr>
              <tr>
                <td>demais 17 capítulos</td>
                <td className="text-right">≤ 0,8%</td>
                <td className="text-right">≤ 2,1%</td>
              </tr>
            </tbody>
          </table>
          Publicamos os dois: <code>internacoes</code> (produção, todas as AIHs) e{" "}
          <code>aih_normal</code>, <code>dias_permanencia_normal</code>,{" "}
          <code>valor_normal</code> (base por episódio). As médias por episódio usam a
          segunda. O <strong>HSMR</strong> (§14) e a <strong>permanência esperada</strong>{" "}
          também passam a ser calculados só sobre AIH normal, porque são métricas por
          episódio — a continuação carrega 0,21% dos óbitos para 1,26% das linhas e diluiria
          o estrato de <em>case-mix</em>. O <strong>%ICSAP</strong> quase não muda (+0,93%
          relativo): só I69 e G40 da Lista Brasileira geram continuação em volume.
          Fundamentação: R. F. Saldanha,{" "}
          <a href="https://rfsaldanha.github.io/sis/sih.html">
            Sistemas de Informação em Saúde no Brasil
          </a>
          , cap. SIH.
        </li>
        <li>
          <strong>Confundimento por cobertura suplementar (importante):</strong> a base só
          enxerga internações pagas pelo SUS. Cerca de um quarto da população tem plano de
          saúde (ANS), concentrado em municípios mais ricos e urbanos. Logo,{" "}
          <em>internações SUS por 100 mil habitantes não são comparáveis entre municípios
          sem considerar a fração coberta por planos</em> — um valor baixo pode refletir alta
          cobertura privada, não menos adoecimento. Vale para internações/100k, ICSAP e a
          visão hospitalar.
        </li>
        <li>
          <strong>Mortalidade hospitalar é taxa bruta, sem ajuste de risco:</strong> reflete
          fortemente o perfil de casos (<em>case-mix</em>) de cada hospital — um terciário de
          alta complexidade tende a mortalidade maior que uma maternidade. Não comparar
          hospitais por mortalidade bruta como se fosse qualidade; a razão ajustada por
          case-mix (HSMR) está na <strong>§14</strong>.
        </li>
      </ul>

      <H2 n={11} />
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

      <H2 n={12} />
      <ul>
        <li>
          <strong>ICSAP</strong> — Internações por Condições Sensíveis à Atenção Primária:
          classificamos cada internação do SIH (2024) pelo diagnóstico principal e marcamos
          as condições da <strong>Lista Brasileira de ICSAP</strong> (Portaria SAS/MS 221/2008),
          em aproximação no nível de CID-10 de 3 caracteres (hipertensão, diabetes, ICC,
          pneumonias, asma/DPOC, gastroenterites, ITU, etc.). A proporção de ICSAP é um
          indicador-proxy da qualidade da atenção básica: quanto maior, mais internações que
          bom acesso à atenção primária poderia ter evitado. A aproximação por 3 caracteres
          difere marginalmente da lista oficial (que tem exceções em 4 caracteres) e tende a
          incluir um pouco a mais (leve sobrecontagem) — <code>G00</code>, por exemplo, abrange
          toda meningite bacteriana onde a portaria pede apenas <code>G00.0</code>.
        </li>
        <li>
          <strong>Correção de 30 de agosto de 2026.</strong> O grupo 1 da lista estava
          incompleto: faltavam catorze códigos — tuberculose pulmonar e outras
          (<code>A15</code>, <code>A16</code>, <code>A18</code>), sífilis
          (<code>A51</code>–<code>A53</code>), malária (<code>B50</code>–<code>B54</code>) e
          febre reumática (<code>I00</code>–<code>I02</code>). Medido antes de corrigir, a
          lista antiga capturava só <strong>20,7% do grupo 1 em São Paulo e 14,3% no Rio de
          Janeiro</strong> em 2024, porque tuberculose pulmonar sozinha é cerca de 65% do
          grupo. O efeito no %ICSAP total é pequeno — entre <strong>+1,04% e +1,21%</strong>
          relativos, conforme o ano —, mas é espacialmente estruturado (tuberculose urbana,
          malária amazônica), então os achados publicados foram <em>refeitos</em> sobre o dado
          corrigido, não presumidos: leitos × %ICSAP ficou em <strong>+0,319</strong> (parcial,
          <strong>+0,340</strong>) — os mesmos +0,32 e +0,34 quando arredondados a duas casas —
          e cobertura da APS × ICSAP passou de +0,004 para <strong>+0,002</strong> (parcial, de
          +0,018 para +0,017). Nenhuma conclusão muda. Todos os checkpoints foram
          recontados da fonte, porque acrescentar código sem recontar deixaria a série antiga
          por baixo.
        </li>
        <li>
          <strong>Grupo 1 — imunopreveníveis</strong> (<code>internacoes_g1</code>,
          <code>g1_100k</code>): internações por doenças preveníveis por imunização e condições
          sensíveis, publicadas em separado desde a mesma data. São <strong>1,3% a 1,5% do
          ICSAP</strong> (38.535 internações em 2024) e existem para permitir o cruzamento com
          as doses aplicadas do PNI — o desfecho populacional do lado da vacinação. Como todo
          o resto desta base, a associação é <em>municipal</em> e não sustenta inferência
          individual.
        </li>
        <li>
          <strong>Gasto potencialmente evitável (estimativa):</strong> nº de internações ICSAP
          × custo médio das internações por condições sensíveis (≈ R$ 1,5 mil/internação,
          calculado a partir das próprias condições no SIH — não da média geral, que é inflada
          por cirurgia/UTI). É uma <em>estimativa de ordem de grandeza</em>, não valor contábil.
        </li>
        <li>
          <strong>Sinalização de outlier (▲):</strong> um município só é marcado como acima da
          média do recorte quando o <strong>limite inferior do IC95% (método de Wilson)</strong>
          da sua proporção de ICSAP supera essa média — com piso de 200 internações. Isso evita
          confundir ruído de amostra pequena com sinal real.
        </li>
        <li>
          <strong>Leitura com equidade:</strong> ICSAP alto e gasto evitável não são, por si,
          "má gestão" do município — frequentemente refletem subfinanciamento e barreiras de
          acesso à atenção básica. São indicadores de sistema, não de culpa local.
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

      <H2 n={13} />
      <p>
        Além do recorte por capítulo, isolamos <strong>condições traçadoras</strong> no nível de
        CID-10 de 3 caracteres (diagnóstico principal), com internações, óbitos, permanência e
        custo por município:
      </p>
      <ul>
        <li>Diabetes (E10–E14); AVC/cerebrovascular (I60–I69); infarto (I21–I22); insuficiência cardíaca (I50);</li>
        <li>Asma (J45–J46); DPOC (J40–J44); pneumonia (J12–J18);</li>
        <li>Depressão (F32–F33); esquizofrenia e outras psicoses (F20–F29); transtornos por álcool/drogas (F10–F19);</li>
        <li>Traumatismo cranioencefálico (S02, S06, S07).</li>
      </ul>
      <p>
        <strong>Causas externas — limitação:</strong> acidentes de transporte (códigos V) não
        entram, porque na AIH o diagnóstico principal registra a <em>natureza da lesão</em>{" "}
        (S/T), não o <em>mecanismo</em> (V). As causas externas ficam representadas pelo TCE.
      </p>
      <p>
        <strong>Visão hospitalar (CNES):</strong> agregamos as internações por estabelecimento
        (≥ 12 internações), com volume, permanência, mortalidade bruta, custo médio e capítulo
        predominante. Os hospitais são identificados pelo código CNES — o nome do estabelecimento
        não consta nos arquivos RD. <strong>Não estimamos ocupação de leitos</strong>: ela não
        deriva de forma confiável da AIH (exigiria o cadastro de leitos do CNES).
      </p>

      <H2 n={14} />
      <p>
        Página <a href="/hospitalar/">Visão hospitalar</a>. Três indicadores adicionais por
        estabelecimento (CNES), a partir do mesmo SIH 2024 já usado nas seções 10–13.
      </p>
      <p>
        <strong>HSMR (Hospital Standardized Mortality Ratio) — padronização indireta.</strong>{" "}
        Para cada hospital, os <strong>óbitos esperados</strong> são a soma, por estrato
        (<strong>faixa etária × capítulo CID-10</strong>), do número de internações do hospital
        naquele estrato multiplicado pela <strong>taxa de mortalidade nacional</strong> do mesmo
        estrato. <code>HSMR = óbitos observados / óbitos esperados</code>. HSMR acima de 1 indica
        mortalidade acima do esperado dado o case-mix do hospital; abaixo de 1, o inverso. Faixas
        etárias: &lt;1, 1–4, 5–14, 15–29, 30–44, 45–59, 60–69, 70–79, 80+ (idade só é considerada
        quando o campo <code>COD_IDADE</code> indica anos; demais casos entram como &lt;1 ano).
      </p>
      <p>
        <strong>Limiar de estabilidade — óbitos esperados &lt; 5:</strong> hospitais abaixo desse
        valor são marcados como instáveis (⚠), não ocultados. É a regra geral de epidemiologia
        para razões padronizadas (SMR/HSMR): com esperado &lt; 5, a razão fica hipersensível a um
        único óbito a mais e o intervalo de confiança exato de Poisson deixa de ser confiável.
        Estudos específicos de HSMR por vezes usam corte mais conservador (ex.: 20 óbitos
        esperados) — mas nesses estudos o hospital é <em>excluído</em> do relatório. Optamos por
        não excluir: hospitais pequenos continuam no mart, apenas sinalizados como instáveis,
        coerente com o princípio de não ocultar unidades pequenas do dado público (mesma lógica
        do IC95% em municípios pequenos, §5).
      </p>
      <p>
        <strong>Intervalo de confiança (IC95%) — desde julho de 2026.</strong> O HSMR passou a ser
        publicado com intervalo de confiança exato, e não apenas com a sinalização binária acima.
        Como os óbitos observados seguem distribuição de Poisson e o esperado é tratado como
        constante conhecida, o intervalo é{" "}
        <code>[qgamma(0,025; O) / E ; qgamma(0,975; O+1) / E]</code> — o mesmo método
        gamma/Poisson exato já usado nas taxas brutas municipais (§5), e não uma segunda
        convenção. O ganho é concreto: um hospital com HSMR 5,94 e IC [0,13 – 27,86] deixa de
        parecer alarme e passa a ser lido como o que é — poucos casos, nenhuma conclusão possível.
      </p>
      <p>
        <strong>Correção para múltiplas comparações (FDR).</strong> Publicar ~4.600 hospitais por
        ano significa testar ~4.600 hipóteses simultaneamente. Um teste isolado a 5% erra 5% das
        vezes; 4.600 testes simultâneos a 5%, se nenhum hospital realmente diferisse do esperado,
        ainda produziriam centenas de “achados” só por acaso. Por isso a classificação{" "}
        <code>significancia</code> não usa o IC bruto isoladamente: calculamos o p-valor exato de
        Poisson (bilateral) para cada hospital-ano e aplicamos a correção{" "}
        <strong>Benjamini-Hochberg</strong> (controle da taxa de falsas descobertas), separadamente
        para cada ano civil. Um hospital só é classificado <strong>acima</strong> ou{" "}
        <strong>abaixo</strong> do esperado quando o q-valor (p ajustado) é menor que 0,05;
        hospitais com esperado = 0 ficam <strong>indeterminado</strong> — não “dentro do
        esperado”, pois não há teste possível. Em 2024: 16,0% acima, 53,2% abaixo, 28,6% dentro do
        esperado. O efeito da correção é honesto, não dramático: de 10.046 hospitais-ano
        significativos sem correção (nos três anos), 282 (2,8%) perdem a classificação após o FDR
        — a maior parte do sinal bruto é real, mas nem todo. Reprodutível em{" "}
        <code>scripts/hsmr_intervalo_confianca.py</code>.
      </p>
      <p>
        <strong>Viés conhecido: o ajuste por capítulo é grosseiro.</strong> A calibração nacional é
        exata (razão agregada = 1,0000 nos três anos), mas calibração não elimina confundimento
        residual. Um capítulo da CID-10 é uma categoria larga — o capítulo IX vai de hipertensão a
        cirurgia cardíaca complexa — e hospitais terciários concentram os casos graves{" "}
        <em>dentro</em> de cada capítulo. O ajuste enxerga <strong>diagnóstico, não gravidade</strong>.
      </p>
      <p>
        <strong>Quanto isso pesava — medido com os leitos do CNES (§18).</strong> Cruzando o HSMR
        com a existência de UTI no estabelecimento, o desequilíbrio ficou explícito: em 2024 a razão
        observado/esperado agregada era <strong>1,163</strong> nos hospitais com UTI e{" "}
        <strong>0,542</strong> nos sem UTI. Nenhum dos dois grupos estava em 1 — só o total nacional
        estava, por construção. A consequência para a classificação era grave: <strong>86,1%</strong>{" "}
        dos hospitais marcados “acima do esperado” tinham UTI, e a taxa de marcação ia de{" "}
        <strong>1,7%</strong> no menor quartil de porte a <strong>43,4%</strong> no maior. Na
        prática, a flag sinalizava “este hospital é grande e tem UTI”.
      </p>
      <p>
        <strong>Correção adotada: comparação dentro do estrato.</strong> Cada hospital passa a ser
        comparado apenas aos hospitais do próprio estrato de complexidade (com UTI / sem UTI),
        recalibrando o esperado pela razão O/E agregada do grupo — mesmo princípio de “comparar
        pares reais” já usado no ICSAP (§17) e na cobertura da APS (§15). O p-valor de Poisson e a
        correção de Benjamini-Hochberg passam a ser calculados <em>dentro</em> de cada família
        (ano × estrato), e o IC95% publicado usa a mesma régua da classificação. O estrato é
        reavaliado ano a ano: um hospital que abre UTI muda de grupo no ano em que abre.
      </p>
      <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
        <strong>Viés residual declarado — a correção melhora, mas não elimina.</strong> Após a
        estratificação, os marcados “acima” com UTI caem de 86,1% para <strong>48,2%</strong> e o
        gradiente por porte achata de 1,7%→43,4% para 5,6%→32,1%. Mas testamos se a estimativa
        ficou <em>livre</em> de viés, e não ficou: o HSMR mediano ainda cresce com o tamanho mesmo
        dentro do estrato (<strong>0,39</strong> no menor quartil de leitos a <strong>0,93</strong>{" "}
        no maior). Tentamos estratificar também por porte (UTI × quartil de leitos) e o gradiente
        persiste (0,54 → 0,91), com estratos degenerados nas pontas. A conclusão honesta é que{" "}
        <strong>recalibração posterior não recupera a informação de gravidade que o ajuste por
        capítulo nunca capturou</strong> — ela desloca o centro, não corrige a medida. Corrigir de
        fato exigiria ajuste por procedimento, gravidade ou comorbidade, variáveis que a AIH
        pública não fornece. Compare apenas hospitais de porte e complexidade semelhantes; use para
        levantar hipóteses, <strong>nunca para ranquear</strong>. Reprodutível em{" "}
        <code>scripts/hsmr_estratos_uti.py</code> e{" "}
        <code>scripts/analise_leitos_hsmr.py</code>.
      </p>
      <p>
        <strong>Permanência esperada (LOS).</strong> Para cada diagnóstico (CID-10, 3 caracteres),
        calculamos a <strong>mediana nacional</strong> de dias de internação e comparamos à
        mediana do hospital para o mesmo diagnóstico. Por volume, não guardamos a duração
        individual de cada internação — a mediana é <em>aproximada</em> por um histograma de
        faixas de dias (0-1, 2-3, 4-7, 8-14, 15-21, 22-30, 31-60, 61+), tomando o ponto médio da
        faixa onde a frequência acumulada cruza 50%. Hospitais com menos de 30 internações no
        diagnóstico não entram (ruído).
      </p>
      <p>
        <strong>Projeção de demanda.</strong> Tendência linear sobre a série mensal de
        internações de cada hospital, ajustada sobre o <strong>tempo de calendário</strong> —
        mês ausente conta como ausente, não como vizinho do seguinte. O intervalo é o de
        predição da regressão (cresce com a distância da extrapolação) multiplicado por um
        fator de calibração medido em backtest: z = 2,42 / 2,64 / 2,80 para 1, 2 e 3 meses,
        no lugar do 1,96 da normal.
      </p>
      <p>
        <strong>A projeção é validada antes de ser publicada.</strong> Por{" "}
        <strong>origem móvel</strong> (o modelo só vê o passado de cada origem), sobre 4.445
        hospitais, contra cinco alternativas: naive, ingênuo sazonal, média móvel de 3 meses,
        sazonal com deriva e tendência com sazonalidade. A tendência linear supera o baseline
        sazonal em todos os horizontes (MASE 0,810 / 0,867 / 0,922) e em todos os estratos de
        volume. O pipeline <em>recusa-se a publicar</em> se o relatório de backtest não existir.
      </p>
      <p>
        <strong>Três coisas que o backtest mudou, e uma que ele impediu.</strong> Mudou: (a) a
        projeção passou a partir de uma <em>âncora única</em> — a última competência da base —,
        e não do último mês de cada hospital, o que vinha publicando previsões para meses já
        passados; (b) o intervalo, antes declarado como 95%, cobria de fato{" "}
        <strong>85,0%</strong> no horizonte de 3 meses, e a calibração corrigiu isso; (c){" "}
        <code>confianca</code> — que só refletia o comprimento da série — deu lugar a{" "}
        <code>status_validacao</code>, derivado do erro <em>medido</em> no estrato de volume do
        hospital. Impediu: os modelos <em>sazonais</em> pareciam a melhoria óbvia, já que no
        agregado nacional a sazonalidade é nítida (fevereiro fica 5,9% abaixo da tendência);
        medidos por hospital, ficaram <strong>piores</strong> (MASE 1,03 a 1,11). A amplitude
        sazonal é menor que o ruído de um estabelecimento isolado. O que vale no agregado não
        transferiu para a unidade.
      </p>
      <p>
        <strong>O intervalo é largo, e isso é o resultado.</strong> Mediana de 74% da previsão
        nos hospitais acima de 500 internações/mês e 217% nos de 6 a 20. Demanda mensal de um
        hospital é intrinsecamente ruidosa; a banda estreita anterior não era mais precisa, era
        menos honesta. Hospitais abaixo de 5 internações/mês <strong>não são publicados</strong>{" "}
        (erro medido acima de 50%), e os que pararam de reportar antes da última competência
        também não. Método completo, métricas e limitações no{" "}
        <a href="https://github.com/pedropaulofernandes88-stack/saude-publica-br/blob/main/docs/MODEL_CARD_FORECAST.md">
          model card
        </a>.
      </p>
      <p>
        <strong>O que não fazemos, e por quê:</strong> não estimamos risco de readmissão ou
        reinternação por paciente. A AIH pública <strong>não tem identificador estável de
        paciente</strong> (removido por LGPD) — ligar duas internações à mesma pessoa exigiria
        dado que não é público. Preferimos declarar essa limitação a produzir uma métrica que
        pareça precisa sem sustentação nos dados abertos.
      </p>

      <H2 n={15} />
      <p>
        Página <a href="/atencao-basica/">Atenção Primária</a>. Publicamos a{" "}
        <strong>cobertura potencial da APS</strong> por município e mês, de janeiro de 2021 à
        competência mais recente (65 competências, 5.571 municípios).
      </p>
      <ul>
        <li>
          <strong>Fonte:</strong> API pública que abastece o relatório oficial de Cobertura da APS
          do Ministério da Saúde (<code>relatorioaps.saude.gov.br</code>), servida por{" "}
          <code>relatorioaps-prd.saude.gov.br/cobertura/aps</code>. Retorna JSON por município e
          competência, sem autenticação. Não é um endpoint formalmente documentado como API
          pública — é o que o próprio relatório público consome.
        </li>
        <li>
          <strong>Definição oficial:</strong> capacidade de atendimento estimada das equipes
          credenciadas (ESF, EAP 20h e 30h, eSFR, eCR, EAPP) dividida pela população do município.
          Como cada tipo de equipe tem capacidade padronizada, o indicador é essencialmente uma
          contagem de equipes reescalada pela população.
        </li>
        <li>
          <strong>Denominador:</strong> a população usada é a estimativa oficial adotada pelo
          próprio relatório (campo de ano de referência e origem informados pela API), e{" "}
          <em>não</em> a série populacional do projeto — para que o número publicado aqui seja
          idêntico ao do relatório oficial.
        </li>
      </ul>
      <p>
        <strong>Limitação central — o indicador satura e vira proxy de porte.</strong> Como poucas
        equipes já cobrem toda a população de um município pequeno, a cobertura potencial
        ultrapassa 100% em <strong>86% dos municípios</strong> brasileiros, chegando a 800%. A
        consequência é que a variação entre municípios reflete sobretudo o tamanho do município,
        não a força da atenção primária: a correlação de postos entre cobertura e população é{" "}
        <strong>ρ = −0,54</strong>.
      </p>
      <p>
        <strong>Teste contra ICSAP.</strong> Testamos a hipótese de que maior cobertura implicaria
        menos internações evitáveis (§12). A correlação bruta com ICSAP por 100 mil habitantes é{" "}
        <strong>ρ = +0,002</strong> — nula, e no sinal contrário ao esperado. Controlando porte
        populacional e vulnerabilidade social, ρ parcial = +0,017. Estratificando, os municípios de
        menor porte têm simultaneamente a <em>maior</em> cobertura mediana (167%) e o{" "}
        <em>maior</em> ICSAP. Conclusão: a cobertura potencial, como publicada, não sustenta
        comparação entre municípios nem inferência sobre qualidade da atenção básica. Publicamos o
        dado porque ele é válido e útil para <strong>acompanhar um município ao longo do tempo</strong>{" "}
        e para contar equipes — e declaramos a limitação no topo da página, não em rodapé.
        Reprodutível em <code>scripts/analise_cobertura_icsap.py</code>; discussão completa no
        artigo <a href="/artigos/o-que-os-indicadores-nao-comparam/">“O que os indicadores não comparam”</a>.
      </p>
      <p>
        <strong>Teste de robustez — comparando só pares do mesmo porte.</strong> Testamos a objeção
        óbvia ao resultado acima: talvez a comparação só faça sentido dentro do mesmo porte
        populacional. Refizemos a análise com o desenho mais rigoroso disponível: densidade real de
        equipes (<strong>ESF por 10 mil habitantes</strong>, sem o teto de capacidade padronizada, em
        vez do percentual saturado), cada município comparado apenas ao seu{" "}
        <strong>quartil de população</strong>, e <strong>%ICSAP</strong> em vez de ICSAP por 100 mil
        habitantes — porque testamos e o ICSAP por 100 mil cai em municípios vulneráveis apenas
        porque o acesso hospitalar geral é menor lá (internações totais por mil habitantes também
        caem com a vulnerabilidade), não porque a atenção primária seja melhor; %ICSAP normaliza
        esse confundimento e fica praticamente constante entre quartis de vulnerabilidade (19–21%).
        Resultado: a correlação entre densidade de equipes e %ICSAP dentro do mesmo porte é ρ entre
        −0,02 e +0,18 conforme o quartil — sem relação prática. A co-ocorrência de baixa densidade
        de equipe com alto %ICSAP (campo <code>atencao</code> do mart) é <strong>0,94×</strong> o que
        a independência estatística preveria — abaixo do acaso, não acima. Por isso o mart{" "}
        <code>mart_equidade_aps_municipio</code> é publicado como registro do teste, não como
        ranking: qualquer classificação individual de município a partir dele seria estatisticamente
        indistinguível de ruído. Reprodutível em <code>scripts/analise_equidade_aps.py</code>.
      </p>
      <p>
        <strong>Teste longitudinal — e se o efeito de equipes novas demorar a aparecer?</strong> O
        teste acima usa um único ano (2024) e não captura efeito defasado de equipes recém-
        implantadas. Reprocessamos o ICSAP por município para 2021, 2022 e 2023 (2024 já disponível),
        montando um painel balanceado de <strong>5.568 municípios × 4 anos</strong> (22.272
        observações). O primeiro teste (efeito fixo só por município) deu ρ = +0,132 — sinal
        aparente, na direção errada, crescente com o porte. Investigamos e encontramos outro
        confundimento: ESF e %ICSAP subiram juntos no Brasil inteiro no período (ESF médio 3,67→4,05
        por 10 mil hab.; %ICSAP médio 17,9%→21,2%), provável retomada pós-pandemia — uma tendência de
        calendário comum às duas variáveis, não relação causal entre si. Ao remover também o efeito
        de ano (<strong>efeito fixo duplo</strong>, município + ano), ρ cai para <strong>+0,006</strong>.
        A primeira diferença ano a ano (demeada por ano) e a versão defasada em 1 ano confirmam:
        |ρ| ≤ 0,032 em todos os desenhos corretamente especificados. O achado nulo se confirma também
        no tempo — e o episódio é, ele mesmo, um sexto caso do problema central deste projeto: uma
        tendência temporal compartilhada produz associação espúria do mesmo jeito que o porte
        municipal produzia antes; a correção (efeito fixo duplo) é o equivalente temporal do desenho
        pareado por porte. Reprodutível em{" "}
        <code>scripts/analise_equidade_aps_longitudinal.py</code>; discussão completa no{" "}
        <a href="https://github.com/pedropaulofernandes88-stack/saude-publica-br/blob/main/docs/preprint/preprint-cobertura-aps.md">
          preprint
        </a>.
      </p>
      <p>
        <strong>A limitação de saúde suplementar é real, mas concentrada nos grandes municípios.</strong>{" "}
        O ICSAP só enxerga internações do SUS — uma limitação que declarávamos sem testar. Trouxemos
        os <strong>vínculos ativos a plano médico-hospitalar por 100 habitantes</strong> por município
        (ANS, Dados Abertos, dez/2024, sem autenticação —{" "}
        <code>scripts/pipeline_ans_beneficiarios.py</code>) e
        cruzamos com %ICSAP dentro de cada quartil de porte (mesmo desenho do teste de robustez
        acima). O resultado é um <strong>gradiente monotônico por porte</strong>, não ruído: ρ =
        +0,05 (Q1, menores) → −0,00 (Q2) → −0,08 (Q3) → <strong>−0,29</strong> (Q4, maiores) — quase
        nulo nos municípios pequenos (onde a cobertura suplementar é baixa e homogênea, ~4-5%) e
        moderado nos grandes (onde chega a 32% e varia bastante). A co-ocorrência de alta saúde
        suplementar com baixo %ICSAP, dentro do porte, é 1,00× o esperado ao acaso — nula no
        agregado nacional. Conclusão: a limitação é real, mas <strong>localizada</strong> em grandes
        municípios/capitais, e não afeta a leitura do achado nulo APS × ICSAP para a maioria dos
        municípios brasileiros. Descartamos antes um dataset pronto da ANS (
        <code>taxa_de_cobertura_de_planos_de_saude</code>) por trazer só o período corrente e taxas
        zeradas mesmo em São Paulo na amostra verificada — problema de qualidade daquele recorte
        específico, não deste teste. Reprodutível em{" "}
        <code>scripts/analise_saude_suplementar_icsap.py</code>.
      </p>
      <p>
        <strong>Por que "vínculos por 100 hab." e não "% da população com plano".</strong> O SIB/ANS
        tem como unidade o <em>vínculo</em> (beneficiário × produto × operadora), não a pessoa, e
        localiza o registro pelo <strong>endereço do contrato</strong>, não pela residência. Uma
        pessoa com dois produtos conta duas vezes, e um contrato coletivo empresarial pode alocar
        vínculos ao município da sede da empresa. A razão vínculos/população, portanto,{" "}
        <em>não é uma proporção de pessoas e pode legitimamente passar de 100</em> — e passa: Belém/AL
        (4.226 hab.) marcou 115,9 vínculos/100 hab. em 2021. Por isso a coluna se chama{" "}
        <code>vinculos_plano_por_100_hab</code>, e não <code>pct_saude_suplementar</code> como na
        versão anterior deste mart; municípios com razão &gt; 100 recebem a flag{" "}
        <code>razao_implausivel</code>.{" "}
        <strong>Isso não altera nenhum resultado acima</strong>: como os testes usam Spearman (só a
        ordem importa), excluir o caso implausível e os 33 municípios com menos de 20 mil hab. e mais
        de 40 vínculos/100 hab. — candidatos a artefato de endereço de contrato — move ρ de +0,054
        para +0,061 (Q1) e deixa Q4 em −0,286, inalterado. A distinção é de rigor na
        <em> leitura</em> do indicador, não de correção de viés. Fundamentação: R. F. Saldanha,{" "}
        <a href="https://rfsaldanha.github.io/sis/ans.html">
          Sistemas de Informação em Saúde no Brasil
        </a>
        , cap. ANS.
      </p>

      <H2 n={16} />
      <p>
        Doses aplicadas do <strong>Programa Nacional de Imunizações</strong>, alimentadas pela{" "}
        <strong>Rede Nacional de Dados em Saúde (RNDS)</strong>. A RNDS em si não é fonte
        consumível — exige CNES, certificado ICP-Brasil e credenciamento no DATASUS, e trafega
        registro individual identificado. O que é aberto é o derivado: um arquivo mensal com
        registro individual <em>pseudonimizado</em>, publicado no portal de dados abertos do SUS.
        Processamos janeiro de 2023 a agosto de 2026 — <strong>638 milhões de doses</strong>, lidas
        em streaming sem materializar os ~320 GB de CSV.
      </p>
      <p>
        <strong>É a série mais atual do projeto.</strong> O arquivo de agosto de 2026 estava
        disponível em agosto de 2026: cerca de um mês de defasagem, contra três anos da mortalidade
        consolidada.
      </p>
      <p>
        <strong>Integridade.</strong> Quarenta e quatro arquivos mensais independentes, cada um
        conferido: zero documentos duplicados dentro do mês, zero duplicados entre competências
        distintas, zero registros fora da própria competência, e os 5.571 municípios presentes em
        todos os meses. Entre 1,11% e 1,81% das doses por mês não trazem município do paciente.
      </p>
      <p>
        <strong>Limpeza do vocabulário.</strong> O campo de imunobiológico traz 115 rótulos e nem
        todos são vacina: 11 são diluentes (<code>DILBCG</code>, <code>NaCl 0,9%</code>) e 18 são
        soros e imunoglobulinas (<code>SAT</code>, <code>IGHAT</code>), que são profilaxia
        pós-exposição. Outros três (<code>FTp</code>, <code>Fta</code>, <code>Tétano</code>) não
        classificamos com segurança e ficam de fora, listados em vez de sumirem em silêncio. Ao
        todo 1,47% das doses saem da contagem de vacinação.
      </p>
      <p>
        <strong>Cobertura vacinal municipal: testada e reprovada.</strong> É a tabela que se
        esperaria aqui, e ela não existe de propósito. O critério foi fixado antes de olhar o
        resultado: correlação abaixo de 0,50 entre 2023 e 2024 significaria ruído. Deu{" "}
        <strong>0,591</strong>. O detalhe por porte mostra o motivo — a cobertura mediana cai de
        102,7% nos municípios com 50 a 100 nascidos para 86,2% nos com mais de 5 mil. Ruído não tem
        direção; isso é viés sistemático de denominador. Mesmo acima de 300 nascidos, onde a
        correlação passa de 0,70, quase 30% dos municípios seguem acima de 100%: onde o indicador é
        estável, o nível continua errado.
      </p>
      <p>
        A hipótese óbvia foi testada e <em>refutada</em>. Suspeitávamos de descasamento geográfico —
        o numerador conta a dose pela residência declarada na vacinação, o denominador conta o
        nascimento pela residência da mãe no parto. A mediana dos municípios aplica 15,8% das doses
        dos seus residentes fora do próprio território, mas a correlação disso com o excesso de
        cobertura é <strong>+0,002</strong>. Não explica nada, porque o numerador já é por
        residência. Também comparamos BCG (aplicada na maternidade) com pentavalente (aplicada na
        unidade básica): se o problema fosse o local de nascimento, a diferença cresceria nos
        municípios pequenos — ela fica entre 0,8 e 2,6 pontos em todas as faixas de porte.
      </p>
      <p>
        Por isso o recorte municipal publicado é <strong>contagem de doses</strong>, não taxa.
        Contagem não depende de denominador e não herda nada disso. Cobertura sai apenas{" "}
        <strong>por UF</strong>, apenas nos anos com nascidos vivos definitivos (2023 e 2024) e
        apenas para cinco indicadores da atenção básica. Cada indicador declara qual tipo de dose
        conta: somar tipos diferentes conta a mesma criança duas vezes, e um conjunto genérico
        produziu 110,6% de cobertura de BCG. Cobertura acima de 100% é usada como guarda automática.
        BCG e hepatite B ao nascer ficam de fora mesmo por UF — aplicadas na maternidade, chegam a
        127,8% no Ceará e 121,0% em Alagoas em 2024, enquanto as cinco de atenção básica ficam
        contidas em 104,2%.
      </p>
      <p>
        <strong>Incerteza que permanece.</strong> A composição do indicador move o número: incluir
        hexavalente e pentavalente acelular na cobertura de pentavalente levou 2024 de 92,2% para
        96,4% — quatro pontos por uma decisão de rótulo. E o arquivo inclui doses de
        estabelecimentos privados integrados à RNDS, sem que saibamos se a cobertura oficial as
        considera. As duas ficam registradas em vez de escolhidas em silêncio.
      </p>

      <H2 n={17} />
      <p>
        Classificamos municípios (população ≥ 20 mil) em <strong>27 estratos</strong> pelo
        cruzamento dos tercis de três dimensões: mortalidade padronizada por idade (2023),
        vulnerabilidade-proxy (Censo 2022) e internações por 100 mil hab. (2023). Cada município
        recebe um rótulo interpretável (ex.: &quot;mortalidade alta, vulnerabilidade média, muita
        internação&quot;), exibido no boletim, e um código legível (<code>M3V2I3</code>). Os cortes
        dos tercis estão <strong>congelados no repositório</strong>: o estrato de um município é
        função apenas dos três valores dele, e não da companhia que ele tem na base.
      </p>
      <p>
        <strong>Por que não é mais k-means.</strong> Até 28 de agosto de 2026 esta seção descrevia
        um agrupamento por k-means (k=5). Ele foi submetido a teste de estabilidade e reprovado: a
        silhueta cai monotonicamente a partir de K=2 — sinal de que os dados não têm grumos, e sim
        um contínuo que o algoritmo era obrigado a cortar em algum lugar —, o índice de Rand
        ajustado entre reamostragens ficou em <strong>0,571</strong> e{" "}
        <strong>280 municípios (16%) trocavam de grupo sem que o dado deles mudasse</strong>. Quem
        consultasse o boletim duas vezes podia ler dois arquétipos diferentes. A estratificação por
        tercis fixos tem Rand ajustado <strong>1,000 por construção</strong>. Reamostrando a base e
        recalculando os próprios cortes — teste mais duro, que pergunta o quanto o corte depende da
        amostra — o Rand ajustado fica em 0,899 e apenas 10 municípios (0,6%) trocariam de estrato
        em mais da metade das reamostragens. Esses continuam sendo municípios de fronteira; a
        diferença é que agora eles não se movem sozinhos entre duas visitas.
      </p>
      <p>
        <strong>Cuidado com a falácia ecológica:</strong> estratos, o cruzamento
        vulnerabilidade × mortalidade e demais associações desta base são{" "}
        <em>municipais</em> (agregadas). Uma associação no nível do município não implica
        relação no nível do indivíduo, nem causalidade — servem para descrever padrões e
        levantar hipóteses, não para inferir risco individual.
      </p>

      <H2 n={18} />
      <p>
        Traduz o indicador ICSAP na pergunta que um gestor de fato faz: <em>quanto
        estou acima de municípios comparáveis, e o que isso representa?</em>
      </p>
      <p>
        <strong>Métrica.</strong> Usamos a <em>proporção</em> de internações que são
        sensíveis à atenção primária (<code>pct_icsap</code>), não a taxa por habitante.
        A taxa por 100 mil é confundida pelo <strong>acesso</strong>: um município onde
        as pessoas não conseguem internar tem taxa baixa sem que a atenção primária seja
        boa. A proporção pergunta outra coisa — &quot;das internações que de fato
        ocorreram, quantas eram evitáveis?&quot; — e é bem menos sensível a isso.
      </p>
      <p>
        <strong>Pares.</strong> A referência é a mediana do <em>estrato de saúde</em>
        do município (tercis fixos de mortalidade × vulnerabilidade × internações,
        seção 17); onde não há estrato, usa-se faixa populacional × região. Comparar
        com a média nacional seria injusto: municípios diferem em estrutura, não apenas
        em gestão. Municípios com menos de 100 internações no ano ficam fora do cálculo
        da mediana do grupo (proporção instável), mas recebem a própria comparação
        sinalizada.
      </p>
      <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <strong>Correção em 2026-09-06 — números anteriores mudaram.</strong> Até esta
        data a mediana de referência era calculada sobre 2021–2024 <em>somados</em>, e
        não sobre o ano de cada linha: um município de 2021 era comparado com uma
        referência que incluía o futuro dos seus pares. A proporção de ICSAP não é
        estável no intervalo — 2021 é o ano em que a internação eletiva desabou —, então
        o efeito não é pequeno: <strong>945 municípios trocaram de lado</strong> em 2021
        (de abaixo da mediana para acima, ou o contrário), 366 em 2022, 353 em 2023 e
        275 em 2024. O total nacional de internações acima dos pares em 2021 passou de
        146.800 para 273.435. Também mudou <code>n_pares</code>, que contava
        município-ano e agora conta município. Quem citou estes números antes de
        2026-09-06 deve conferir contra a versão atual: veja a V042 em{" "}
        <code>migrations/</code> e a entrada 3.6.0 do CHANGELOG.
      </p>
      <p>
        <strong>Conversão.</strong> As internações acima dos pares são
        (<code>pct_icsap</code> − mediana dos pares) × internações totais. Custo e
        permanência por internação vêm dos agravos traçadores da Lista Brasileira
        presentes na base (asma, DPOC, pneumonia, diabetes, insuficiência cardíaca e
        doença cerebrovascular). Esses seis <strong>pendem para o lado caro</strong> da
        lista — condições baratas como gastroenterite, infecção urinária e anemia não
        estão representadas —, então o valor em reais é um <strong>teto</strong>, não
        uma média fiel.
      </p>
      <p>
        <strong>O que este número não é.</strong> Quatro limites que precisam acompanhar
        qualquer citação:
      </p>
      <ul>
        <li>
          <strong>Não é economia disponível.</strong> Alcançar a mediana exige
          <em> investir</em> em atenção primária — mais equipes, mais acompanhamento de
          condições crônicas —, não cortar. O valor dimensiona o problema; não é caixa a
          resgatar.
        </li>
        <li>
          <strong>Nem toda ICSAP é evitável.</strong> A Lista Brasileira reúne condições
          <em> sensíveis</em> à atenção primária: boa cobertura reduz, não zera. Por isso
          a referência é a mediana dos pares, e nunca zero.
        </li>
        <li>
          <strong>A associação é ecológica.</strong> Descreve um padrão municipal
          agregado — não risco individual, não relação causal.
        </li>
        <li>
          <strong>O ICSAP responde à oferta hospitalar local — medimos, e o efeito é
          grande.</strong> Esta advertência já existia aqui como hipótese ("onde faltam
          leitos, a internação eletiva desaparece e a fatia de ICSAP sobe mecanicamente").
          Com os dados de leitos (§18) testamos, e o resultado foi na{" "}
          <em>direção oposta</em> e por outro mecanismo: ter leito local{" "}
          <strong>quase dobra</strong> a internação por ICSAP (+85% no 3º quartil de porte)
          sem alterar as demais. Não é a eletiva que some — é a internação sensível que
          <em> aparece</em> quando existe leito na cidade. Detalhes na seção 20.
        </li>
      </ul>
      <p>
        Disponível na view <code>mart_icsap_pares</code> da API pública, no boletim
        municipal e na ferramenta MCP <code>icsap_distancia_dos_pares</code>.
      </p>

      <H2 n={19} />
      <p>
        Exibido como KPI no <a href="/mapa/">mapa</a>. É a primeira camada de{" "}
        <strong>oferta</strong> da plataforma: até aqui todos os indicadores contavam{" "}
        <em>eventos</em> (óbitos, casos, internações), nunca capacidade instalada. Sem
        denominador de oferta não dá para perguntar se um município tem estrutura para
        atender sua população.
      </p>
      <ul>
        <li>
          <strong>Fonte:</strong> API pública de dados abertos do Ministério da Saúde
          (<code>apidadosabertos.saude.gov.br/cnes/estabelecimentos</code>), sem
          autenticação. É o <em>cadastro corrente</em> — não tem série histórica.
        </li>
        <li>
          <strong>Cobertura:</strong> 629.987 estabelecimentos cadastrados no Brasil, dos
          quais <strong>492.200 ativos</strong> nos 5.571 municípios. Publicamos apenas os
          ativos.
        </li>
        <li>
          <strong>Perfil hospitalar:</strong> estabelecimento com atendimento hospitalar
          declarado ou tipo de unidade com internação (tabela de domínio do CNES).
        </li>
      </ul>
      <p>
        <strong>Armadilha 1 — cadastros desabilitados não são sinalizados como tal.</strong>{" "}
        Não existe campo de status óbvio: o que marca a desabilitação é o preenchimento de{" "}
        <code>codigo_motivo_desabilitacao_estabelecimento</code>. Contar sem filtrar infla a
        oferta com cadastros mortos — no Brasil inteiro são <strong>137.787 registros
        desabilitados</strong> (22% da base) misturados aos ativos.
      </p>
      <p>
        <strong>Armadilha 2 — "esfera administrativa" não significa propriedade pública.</strong>{" "}
        O campo <code>descricao_esfera_administrativa</code> indica qual ente{" "}
        <em>gere/contratualiza</em> o estabelecimento, não quem é o dono. Em Alta Floresta
        d'Oeste/RO, 67 dos 67 estabelecimentos aparecem como "MUNICIPAL" — mas só{" "}
        <strong>32 (48%) são de fato públicos</strong> pela natureza jurídica; os demais são
        clínicas LTDA e consultórios de pessoa física. Ler esse campo como propriedade{" "}
        <em>mais que dobra</em> a rede pública aparente. Usamos o primeiro dígito de{" "}
        <code>descricao_natureza_juridica_estabelecimento</code> (tabela CONCLA: 1=público,
        2=privado com fins lucrativos, 3=sem fins lucrativos, 4=pessoa física,
        5=internacional).
      </p>
      <p>
        <strong>Limitações declaradas.</strong> (a) Sem série histórica: o cadastro é uma foto
        do presente, e comparações ao longo do tempo exigem o FTP (ver leitos, abaixo).
        (b) Contagem de estabelecimentos não pondera porte — um hospital de 800 leitos e um
        posto pequeno contam igual; por isso a camada de leitos existe. Reprodutível em{" "}
        <code>scripts/pipeline_cnes.py</code>; mart público{" "}
        <code>mart_cnes_municipio</code>.
      </p>
      <p>
        <strong>Leitos hospitalares (grupo LT, 2015–2024).</strong> A API de dados abertos não
        expõe leitos; o dado vem do FTP do DataSUS (arquivos <code>LT{"{UF}{AAMM}"}.dbc</code>),
        na competência de <strong>dezembro de cada ano</strong>. Exibido na{" "}
        <a href="/hospitalar/">visão hospitalar</a>; mart público{" "}
        <code>mart_leitos_municipio</code> (55.710 linhas município-ano). Em 2024: 535.566
        leitos totais, 357.084 SUS (66,7%) e 63.837 de UTI — e{" "}
        <strong>1.971 municípios (35,4%) sem nenhum leito</strong>.
      </p>
      <p>
        <strong>Cadastro não se soma no tempo.</strong> O CNES fotografa o mesmo
        estabelecimento todo mês; somar as 12 competências de um ano multiplicaria a
        capacidade por 12. Cada linha do mart é um <em>snapshot</em> de dezembro. As operações
        válidas são snapshot, média do período ou série mensal preservada — nunca soma.
      </p>
      <p>
        <strong>UTI: por que a lista de códigos é explícita.</strong> A tabela oficial de
        domínios (<code>SCNES_DOMINIOS</code>, aba "LEITOS") coloca os códigos de UTI na faixa
        74–86, mas o <strong>código 84 no meio dela é "acolhimento noturno"</strong>, que não é
        terapia intensiva. Usar o intervalo <code>74 ≤ código ≤ 86</code> contaria leito de
        acolhimento como UTI, silenciosamente. Enumeramos os códigos um a um.
      </p>
      <p>
        <strong>Descontinuidade declarada — a série de UTI entre 2020 e 2022.</strong> Os leitos
        do tipo "complementar" saltam de 59,8 mil (2019) para 99,4 mil (2021) e caem a 76,9 mil
        (2022), enquanto a fração deles sob códigos de UTI vai de 77% → 51% → 79%. A leitura
        mais provável é que leito emergencial da pandemia foi cadastrado fora dos códigos de
        UTI e depois desmobilizado. Consequência: o salto de UTI em 2022 (+20% em um ano) é em
        parte <em>reclassificação</em>, não expansão real. A tendência de dez anos (40,4 mil →
        63,8 mil) é consistente; a variação ano a ano nessa janela não é comparável. Optamos por
        exibir a descontinuidade em vez de suavizá-la — quebra visível é informação, não defeito.
        Reprodutível em <code>scripts/pipeline_cnes_leitos.py</code>.
      </p>

      <H2 n={20} />
      <p>
        Com a camada de leitos (§18) foi possível testar uma advertência que esta
        metodologia carregava desde o início <em>sem nunca ter sido medida</em>: a de que
        o %ICSAP poderia estar inflado onde falta leito, porque "a internação eletiva
        desaparece e a fatia de ICSAP sobe mecanicamente". Cruzamos as duas bases para os{" "}
        <strong>5.570 municípios</strong> (2024). O resultado contradiz a hipótese na
        direção <em>e</em> no mecanismo.
      </p>
      <p>
        <strong>Direção oposta.</strong> A correlação entre leitos SUS por mil habitantes e
        %ICSAP é <strong>positiva</strong>: ρ = +0,32 bruta, +0,34 controlando porte e
        vulnerabilidade, e entre +0,16 e +0,47 dentro de cada quartil de porte (positiva nos
        quatro). Municípios <em>sem</em> leito local têm %ICSAP <em>menor</em> (mediana
        17,8%), não maior, que os municípios com leito (21,5%).
      </p>
      <p>
        <strong>Mecanismo: é o numerador, não o denominador.</strong> Decompondo as
        internações em ICSAP e não-ICSAP por habitante, dentro de cada quartil de porte,
        o efeito da presença de leito local aparece quase inteiramente sobre o ICSAP:
      </p>
      <table>
        <thead>
          <tr>
            <th>Porte</th><th>Oferta local</th><th>ICSAP /100 mil</th>
            <th>Não-ICSAP /100 mil</th><th>%ICSAP</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>Q2</td><td>sem leito</td><td>1.156</td><td>5.483</td><td>17,3%</td></tr>
          <tr><td>Q2</td><td>com leito</td><td><strong>1.745</strong> (+51%)</td><td>5.887 (+7%)</td><td>22,8%</td></tr>
          <tr><td>Q3</td><td>sem leito</td><td>961</td><td>5.145</td><td>15,4%</td></tr>
          <tr><td>Q3</td><td>com leito</td><td><strong>1.782</strong> (+85%)</td><td>5.728 (+11%)</td><td>23,5%</td></tr>
          <tr><td>Q4</td><td>sem leito</td><td>877</td><td>5.604</td><td>14,6%</td></tr>
          <tr><td>Q4</td><td>com leito</td><td><strong>1.343</strong> (+53%)</td><td>5.571 (−1%)</td><td>19,4%</td></tr>
        </tbody>
      </table>
      <p>
        Não é a internação eletiva que some por falta de leito — é a internação sensível à
        atenção primária que <strong>aparece</strong> quando existe leito na cidade.
        Pneumonia, desidratação e descompensação de insuficiência cardíaca são exatamente o
        que um hospital pequeno interna. Sem leito local, esses casos são resolvidos em
        ambulatório ou simplesmente não viajam; só o caso complexo viaja. É oferta induzindo
        demanda, concentrada nas internações discricionárias que o ICSAP mede.
      </p>
      <p>
        <strong>Consequência para o uso do indicador.</strong> Um município que abre um
        hospital pequeno verá seu %ICSAP <em>subir</em> — e, pela leitura convencional
        ("ICSAP alto = atenção primária fraca"), seria classificado como tendo{" "}
        <em>piorado</em> a atenção básica, quando o que mudou foi a oferta hospitalar. Assim
        como a cobertura potencial da APS mede porte municipal (§15), o %ICSAP mede, em
        parte relevante, <strong>a existência de leito na cidade</strong>. Comparações de
        ICSAP entre municípios devem considerar a oferta hospitalar local; a comparação
        pareada da §17 já vai nessa direção, mas o par ideal também controlaria leitos.
      </p>
      <p>
        <strong>Ressalva semântica declarada.</strong> O ICSAP é medido por município de{" "}
        <em>residência</em> do paciente; os leitos, por município do{" "}
        <em>estabelecimento</em>. "Sem leito" significa sem oferta <em>local</em>, não sem
        acesso: o morador se interna em outro município e a internação conta para a
        residência dele. O efeito medido, portanto, opera por barreira de deslocamento — não
        por ausência absoluta de leito. Reprodutível em{" "}
        <code>scripts/analise_leitos_icsap.py</code>; mart público{" "}
        <code>mart_leitos_icsap_municipio</code>.
      </p>

      <H2 n={21} />
      <p>
        1.994 municípios (35,8% em 2023) não têm nenhum leito hospitalar local. A pergunta
        óbvia — isso mata mais gente? — exige separar duas hipóteses com implicações opostas:
        (a) <strong>sobrevida</strong>, o caso grave morre por falta de leito perto (assinatura:
        taxa <em>padronizada</em> por idade maior); ou (b) <strong>local da morte</strong>, a
        mesma morte ocorre em casa em vez do hospital, sem mudar a taxa total. Cruzamos leitos
        (CNES-LT) com mortalidade (SIM), ano de 2023 (consolidado), para os 5.570 municípios.
      </p>
      <p>
        <strong>Nenhuma das duas se confirma.</strong> A taxa padronizada é praticamente igual
        entre municípios com e sem leito local, dentro de cada quartil de porte, e a diferença
        que existe favorece levemente o grupo sem leito (−8,6 a −4,6 por 100 mil). O efeito bruto
        sobre o local da morte (+1,9 p.p. de óbitos domiciliares) também colapsa dentro do porte
        (+0,7 a −0,3 p.p.) — era majoritariamente confundimento de porte, o mesmo padrão já
        visto em cobertura da APS e ICSAP.
      </p>
      <p>
        <strong>Teste de robustez decisivo — a região Norte.</strong> Se a falta de leito local
        matasse por barreira de deslocamento, o efeito deveria aparecer onde as distâncias até um
        hospital de referência são maiores. Na região Norte, a taxa padronizada mediana é{" "}
        <strong>627,3</strong> sem leito local contra <strong>662,5</strong> com — mesma direção
        nula, sem inversão. Checamos também sub-registro (municípios pequenos podem notificar
        menos óbitos, o que enviesaria a taxa bruta para baixo): a taxa <em>bruta</em> por
        habitante é de fato menor sem leito, mas a padronizada — que corrige composição etária —
        não é, indicando que a diferença bruta é população mais jovem, não subnotificação.
      </p>
      <p>
        <strong>Coerência com o achado de ICSAP (§19).</strong> Leito local quase dobra a
        internação por causas sensíveis à atenção primária, mas não muda a mortalidade
        padronizada — dois achados independentes sugerindo que o hospital pequeno interna muito
        caso de baixa complexidade sem alterar desfecho de sobrevida.
      </p>
      <p>
        <strong>Limitação declarada, não resolvida.</strong> "Sem leito local" não mede{" "}
        <em>distância</em> até o leito mais próximo — um município a 20 km de um hospital
        regional e outro a 300 km entram no mesmo grupo. O teste regional atenua essa
        preocupação, mas não a substitui; medir distância exigiria geocodificação não realizada.
        Reprodutível em <code>scripts/analise_vazio_assistencial.py</code>; mart público{" "}
        <code>mart_vazio_assistencial_municipio</code>.
      </p>

      <H2 n={22} />
      <p>
        Até aqui a plataforma media <em>desfecho</em> (mortalidade, ICSAP, HSMR) e{" "}
        <em>oferta física</em> (leitos), nunca o <strong>insumo financeiro</strong>. O{" "}
        <strong>SIOPS</strong> é a única base nacional com orçamento público de saúde por
        município, e permite testar a hipótese mais intuitiva de todas: gastar mais está
        associado a internar menos por condição evitável?
      </p>
      <p>
        <strong>De onde vem.</strong> O SIOPS não está no FTP do DataSUS, não está na API de
        dados abertos do Ministério (85 rotas, nenhuma financeira) e não está no SICONFI — o
        Anexo 12 do RREO, que é o demonstrativo de saúde, é transmitido pelo próprio SIOPS e
        não aparece na API do Tesouro. A via pública é o TABNET da série histórica de
        indicadores municipais, um arquivo de definição por UF. Extraímos gasto próprio por
        habitante, percentual da receita própria aplicado em ASPS (o piso de 15% da EC 29 /
        LC 141), despesa total e transferências do SUS, para 2021–2024:{" "}
        <strong>22.276 linhas, 5.569 municípios</strong>.
      </p>
      <p>
        <strong>O confundidor mais forte que já medimos.</strong> População × gasto próprio
        por habitante dá ρ = <strong>−0,578</strong>. Município pequeno gasta muito mais por
        habitante — mediana de R$ 1.544 no quartil dos menores contra R$ 633 no dos maiores —
        porque custo fixo se dilui em menos gente. Qualquer correlação bruta entre gasto e
        desfecho carrega isso dentro.
      </p>
      <p>
        <strong>Resultado.</strong> Dentro de cada quartil de porte, ρ entre gasto próprio e
        %ICSAP é −0,00 (Q1), +0,03 (Q2), −0,02 (Q3) e −0,14 (Q4). O sinal troca de direção e
        só o quartil superior mostra algo — padrão de resíduo de porte, não de efeito estável.
        A co-ocorrência de alto gasto com baixo %ICSAP, dentro do porte, é{" "}
        <strong>1,01×</strong> o esperado ao acaso. Somando aos anteriores, é o{" "}
        <strong>quarto achado nulo</strong> sobre o %ICSAP: nem cobertura da APS, nem saúde
        suplementar, nem vazio assistencial, nem gasto explicam sua variação entre municípios
        comparáveis. O que move o indicador segue sendo porte e{" "}
        <a href="#">oferta hospitalar local</a> (§19).
      </p>
      <p>
        <strong>A armadilha do agregado: um gradiente que não existe.</strong> Vale registrar uma leitura que <em>parece</em> contradizer o achado nulo da
        vulnerabilidade, porque quem refizer as contas vai encontrá-la. Somando internações em
        vez de comparar municípios, o %ICSAP por quartil de vulnerabilidade fica monotônico e
        forte:
      </p>
      <div className="rolo">
        <table>
          <thead>
            <tr><th>%ICSAP por quartil de IVS (2024)</th><th>Q1</th><th>Q2</th><th>Q3</th><th>Q4</th></tr>
          </thead>
          <tbody>
            <tr><td>mediana entre municípios — <em>o que publicamos</em></td>
              <td>19,1%</td><td>21,1%</td><td>20,6%</td><td>19,8%</td></tr>
            <tr><td>agregado, ponderado por internação</td>
              <td>18,1%</td><td>21,0%</td><td>22,5%</td><td>23,7%</td></tr>
          </tbody>
        </table>
      </div>
      <p>
        A segunda linha sobe do menos para o mais vulnerável nos quatro anos da série, e é
        tentador lê-la como a desigualdade que a primeira não mostra.{" "}
        <strong>Ela não é isso.</strong> O quartil menos vulnerável concentra{" "}
        <strong>59,7% de todas as internações do país em 25,2% dos municípios</strong> — é onde
        estão as cidades grandes, com população mediana de 20.512 contra cerca de 10 mil nos
        demais quartis. E município grande tem %ICSAP baixo, pelo motivo já medido na §19: o
        indicador responde a porte e oferta hospitalar. O agregado, ao ponderar por internação,
        mede <strong>porte disfarçado de vulnerabilidade</strong>.
      </p>
      <p>
        O teste que desmonta é o padrão-ouro do projeto — comparar dentro da mesma faixa de
        porte. O sinal <em>troca de direção</em>: ρ = <strong>−0,054</strong> nos municípios com
        menos de 20 mil habitantes (n = 3.794), <strong>+0,166</strong> entre 20 e 100 mil
        (n = 1.411) e +0,048 acima de 100 mil (n = 336, p = 0,38, não significativo). Não há
        gradiente consistente; há paradoxo de Simpson.
      </p>
      <p>
        Publicamos as duas linhas de propósito. Esconder a segunda não a impediria de existir —
        qualquer pessoa que baixe <code>mart_icsap_municipio</code> e some as colunas chega nela
        em dois minutos. O que evita a leitura errada não é omitir o número, é mostrar de onde
        ele vem.
      </p>

      <p>
        <strong>Limitações declaradas.</strong> O dado é <strong>autodeclarado</strong> pelo
        ente e homologado pelo gestor — não há verificação externa das transações. É despesa{" "}
        <strong>empenhada</strong>, que difere de liquidada e paga. Per capita em município
        pequeno oscila muito: uma obra desloca o indicador sem mudança estrutural. E{" "}
        <strong>gasto não é acesso nem qualidade</strong> — um município pode gastar muito e
        mal; o SIOPS não mede produção assistencial nem necessidade. Os indicadores de
        subfunção (atenção básica, assistência hospitalar), que seriam os mais interessantes
        para este cruzamento, existem no sistema mas <strong>vêm vazios de 2016 em diante</strong>{" "}
        — medimos: 22 de 23 municípios do Acre preenchidos em 2015, zero em 2020 e em 2024.
        Reprodutível em <code>scripts/pipeline_siops.py</code> e{" "}
        <code>scripts/analise_siops_icsap.py</code>; marts públicos{" "}
        <code>mart_siops_municipio</code> e <code>mart_siops_icsap_municipio</code>.
        Fundamentação da leitura do sistema: R. F. Saldanha,{" "}
        <a href="https://rfsaldanha.github.io/sis/siops.html">
          Sistemas de Informação em Saúde no Brasil
        </a>
        , cap. SIOPS.
      </p>

      <H2 n={23} />
      <p>
        A pergunta que motiva esta seção veio de fora: tratar cada município como um ponto,
        as coordenadas sendo a composição de causas de morte, e perguntar quem morre de forma
        parecida. É análise não supervisionada clássica — e é justamente o tipo de análise que
        sempre devolve alguma coisa. PCA sempre acha componentes; k-means sempre acha grupos.
        Nada disso falha com erro: falha produzindo resultado bonito e vazio. Por isso cada
        etapa aqui foi comparada com um <strong>nulo multinomial</strong>, em que cada município
        sorteia os <em>seus</em> óbitos da composição nacional.
      </p>
      <p>
        <strong>O grão que faltava.</strong> Até 2026-09, a base tinha município × capítulo da
        CID (22 categorias) e CID de três caracteres × UF — nunca os dois cruzados. A tabela
        nova tem 3.612.357 células município × CID × ano e 7.759.402 no grão mensal, e não
        exigiu coleta: o grão já existia dentro do pipeline e era agregado para cima antes de
        virar tabela. Ela reconcilia exatamente com a mortalidade já publicada — 14.484.496
        óbitos, 55.940 pares município-ano, divergência zero.
      </p>
      <p>
        <strong>B34 é COVID-19, não "infecção viral não especificada".</strong> O SIM brasileiro
        nunca usou U07: são zero registros em dez anos. A COVID foi codificada como B34.2, que
        truncada em três caracteres vira B34 — cuja descrição oficial na CID-10 é exatamente o
        texto que um filtro de "causas inespecíficas" descartaria. Foram 60 a 240 óbitos por ano
        entre 2015 e 2019, contra <strong>425.218 em 2021</strong>. Quem rodar esta análise sem
        saber disso apaga a pandemia da matriz, ou a mantém e a interpreta errado.
      </p>
      <p>
        <strong>Quatro confundidores saem antes de qualquer conclusão:</strong> log da população,
        fração com 60 anos ou mais, percentual de causas mal definidas e fração de B34. Com os
        quatro controles o primeiro componente cai de 6,3% para 3,3% da variância — quase metade
        do que pareceria "padrão de mortalidade" era porte, idade, qualidade do registro e
        pandemia. <strong>A estrutura sobrevive</strong>: seis componentes ainda superam duas
        vezes o nulo.
      </p>
      <p>
        <strong>Não há grupos discretos — há um contínuo estruturado.</strong> Duas medidas
        discordam de um jeito que só tem uma leitura: o índice Rand ajustado entre partições de
        subamostras de 80% é <strong>0,93</strong> (a partição se reproduz), enquanto a silhueta
        média é <strong>0,17</strong> (os grupos não se separam). Partição reprodutível com
        silhueta baixa é a assinatura de um gradiente: o mesmo corte reaparece porque a direção é
        real, não porque existam ilhas. A fração de soma de quadrados não explicada também cai
        sem cotovelo de k=2 a k=20. Por isso o produto publicado são as <em>coordenadas</em>, e o
        rótulo de grupo vai declarado como discretização, não como tipologia descoberta.
      </p>
      <p>
        <strong>O eixo principal é, em quase um terço, como se codifica.</strong> O polo negativo
        do primeiro componente reúne I64, I10, E14 e V29; o positivo, C18, C34, C25 e C43. Lidos
        como doença seriam "cerebrovascular e metabólico" contra "câncer". Lidos pelo texto da
        CID, os quatro do lado negativo terminam em <em>NE — não especificado</em>, e os do
        positivo são diagnósticos precisos. Construindo um índice de inespecificidade (fração dos
        óbitos em CID cuja descrição traz NE, NCOP ou SOE, excluído o B34 por ser COVID), a
        correlação com o primeiro componente é <strong>−0,54</strong> (r² = 0,29) — enquanto o
        indicador clássico de qualidade, o percentual de causas mal definidas, correlaciona
        apenas <strong>+0,37</strong> com esse índice. São coisas diferentes: um mede o balde do
        R99, o outro mede a granularidade de todo o resto. Uma clusterização publicada sem esse
        controle descreveria, em boa parte, cultura de codificação médica — e seria lida como
        epidemiologia.
      </p>
      <p>
        <strong>Correlação entre causas: o contemporâneo vale, a defasagem não.</strong> Nas
        séries mensais nacionais (120 pontos), sem tendência e sem efeito de mês civil, o par de
        maior correlação de toda a matriz é <strong>A90 × A91 = +0,97</strong> — dengue e dengue
        hemorrágica, o único par do qual se pode afirmar de antemão que tem de correlacionar.
        O controle positivo passa. Já a correlação <em>cruzada</em>, com defasagem de −6 a +6
        meses, não se sustenta: o pico de |r| se empilha nas bordas da janela (4.413 pares contra
        1.287 por lag intermediário), assinatura de busca sobreajustada, e os pares "revelados"
        são clinicamente implausíveis. <strong>Publicado como achado negativo.</strong>
      </p>
      <p>
        <strong>Detecção de mudança de padrão, e por que não é z-score.</strong> A mediana é de
        77 óbitos por município-ano e a maioria das células é 0, 1 ou 2: a distribuição normal
        não aproxima isso. O teste é binomial negativa, com dispersão estimada pela variação ano
        a ano dentro do próprio município. Os controles positivos são dengue e COVID — e a dengue
        aparece <strong>apenas em 2024</strong>, o ano da maior epidemia registrada, com São Paulo
        marcando 422 óbitos contra 6,5 esperados. Mas o resultado mais útil é outro: sem descontar
        a tendência nacional, o que mais aparece não são epidemias e sim <strong>deriva de
        codificação</strong> — N39, E11, G30 e I10 encabeçam a lista, e os sinais crescem
        monotonicamente de 203 em 2020 para 644 em 2024. Por isso a tabela traz dois escores, um
        contra a própria história e outro descontando o que o Brasil fez.
      </p>
      <p>
        <strong>Limitações declaradas.</strong> O desenho é ecológico e nada aqui é individual.
        O corte de 500 óbitos no período deixa 3.430 dos 5.570 municípios — os menores ficam de
        fora porque seu perfil é ruído multinomial, não porque não importem. A estrutura etária
        entra pelo Censo 2022 e é tratada como estática. E o índice de inespecificidade depende
        do texto da descrição da CID-10, não de uma classificação oficial de imprecisão.
        Reprodutível em <code>scripts/pipeline_mortalidade_causa_municipio.py</code>,{" "}
        <code>scripts/analise_perfil_mortalidade.py</code> e{" "}
        <code>scripts/analise_anomalia_causas.py</code>; marts públicos{" "}
        <code>mart_mortalidade_causa_municipio</code>,{" "}
        <code>mart_perfil_mortalidade_municipio</code>,{" "}
        <code>mart_correlacao_causas</code> e <code>mart_anomalia_causa_municipio</code>.
      </p>
      <H2 n={24} />
      <p>
        Nenhum microdado individual é publicado: o banco recebe apenas agregados
        (município × período × categoria). Não há registros individuais, datas exatas
        de óbito, nem qualquer chave que permita ligar dois eventos à mesma pessoa.
      </p>
      <p>
        <strong>Sobre células pequenas.</strong> Em recortes finos (município × capítulo
        CID × sexo × ano) existem cerca de 206 mil células com 1 a 4 óbitos. Optamos
        deliberadamente por <em>não</em> suprimi-las, e é importante explicitar o porquê:
        a fonte primária — os microdados do SIM, publicados pelo próprio Ministério da
        Saúde no OpenDataSUS — contém <em>registros individuais</em> com município de
        residência, sexo, idade, escolaridade, raça/cor e CID-10 de 4 caracteres. Ou seja,
        o dado de origem é substancialmente mais granular e mais identificável do que
        qualquer agregado aqui publicado. O próprio DATASUS oferece o TABNET, ferramenta
        pública que produz exatamente essas tabulações de forma interativa.
      </p>
      <p>
        Nesse contexto, suprimir células pequenas ofereceria uma <em>aparência</em> de
        proteção sem ganho real de privacidade, enquanto destruiria justamente a
        informação dos municípios pequenos — que são os menos servidos pelas ferramentas
        existentes e os que mais precisam de dados acessíveis. A regra que seguimos é
        outra e, entendemos, mais honesta: <strong>nunca publicar nada mais granular do
        que a fonte pública de origem</strong>.
      </p>
      <p>
        Isso não elimina a cautela analítica: contagens pequenas geram taxas instáveis.
        Por isso toda taxa bruta vem com IC95% e há alerta explícito para municípios com
        menos de 10 mil habitantes (seção 5).
      </p>
    </div>
  );
}
