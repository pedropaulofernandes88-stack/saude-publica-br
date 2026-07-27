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
        para permitir avaliação crítica e reprodução independente. O processamento
        é feito por scripts abertos e versionados em <code>scripts/</code>:{" "}
        <code>pipeline_v2.py</code> (mortalidade e população) e pipelines dedicados
        para dengue (SINAN), internações (SIH), nascimentos (SINASC) e os recortes
        de internação por agravo/hospital.
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
          difere marginalmente da lista oficial (que tem exceções em 4 caracteres) e tende a
          incluir um pouco a mais (leve sobrecontagem).
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

      <h2>13. Agravos traçadores e visão hospitalar (SIH 2024)</h2>
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

      <h2>14. Mortalidade ajustada (HSMR), permanência esperada e projeção de demanda</h2>
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
        internações de cada hospital — o mesmo método de regressão usado no excesso de
        mortalidade (§6), aplicado por hospital em vez de por UF. A faixa de incerteza é
        indicativa (previsão ± 1,96 × desvio-padrão dos resíduos do ajuste), não um intervalo de
        predição formal. Hospitais com menos de 24 meses de histórico recebem
        <code> confianca=&quot;baixa&quot;</code>: uma tendência calculada sobre poucos pontos é
        instável — sinalizada, não ocultada.
      </p>
      <p>
        <strong>O que não fazemos, e por quê:</strong> não estimamos risco de readmissão ou
        reinternação por paciente. A AIH pública <strong>não tem identificador estável de
        paciente</strong> (removido por LGPD) — ligar duas internações à mesma pessoa exigiria
        dado que não é público. Preferimos declarar essa limitação a produzir uma métrica que
        pareça precisa sem sustentação nos dados abertos.
      </p>

      <h2>15. Arquétipos de saúde municipal (k-means)</h2>
      <p>
        Agrupamos municípios (população ≥ 20 mil) em cinco perfis por <strong>k-means</strong>
        sobre três dimensões padronizadas por z-score: mortalidade padronizada por idade (2023),
        vulnerabilidade-proxy (Censo 2022) e internações por 100 mil hab. (2023). Cada município
        recebe um rótulo interpretável (ex.: "mortalidade alta, vulnerabilidade média, muita
        internação"), exibido no boletim. Método de normalização z-score + k-means inspirado no LabSUS.
      </p>
      <p>
        <strong>Cuidado com a falácia ecológica:</strong> clusters, o cruzamento
        vulnerabilidade × mortalidade e demais associações desta base são{" "}
        <em>municipais</em> (agregadas). Uma associação no nível do município não implica
        relação no nível do indivíduo, nem causalidade — servem para descrever padrões e
        levantar hipóteses, não para inferir risco individual.
      </p>

      <h2>16. Privacidade e células de contagem pequena</h2>
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
