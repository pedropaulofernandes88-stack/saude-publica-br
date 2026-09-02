const pptxgen = require("pptxgenjs");

const TINTA = "101521", PAPEL = "FFFFFF", SUAVE = "EEF1F6";
const INDIGO = "1F4FA8", BRASA = "B8461E", VERDE = "1C6B4C";
const NEUTRO = "5A6478", CLARO = "C9D2E2", NEUTRO_ESCURO = "94A0B8";
const SERIF = "Cambria", SANS = "Calibri";

const p = new pptxgen();
p.layout = "LAYOUT_WIDE";                 // 13,3 x 7,5 polegadas
p.author = "Pedro Paulo Fernandes";
p.title = "O leito que cria a internacao";
p.subject = "Saude em Dado — plataforma aberta de indicadores do SUS";

const M = 0.85;                            // margem lateral
const L = 13.33 - 2 * M;                   // largura util

function eixo(s, texto, sub, escuro) {
  s.addText(
    [{ text: texto, options: { color: escuro ? CLARO : INDIGO } },
     ...(sub ? [{ text: "   " + sub, options: { color: escuro ? NEUTRO_ESCURO : NEUTRO } }] : [])],
    { x: M, y: 0.42, w: L, h: 0.3, fontFace: SANS, fontSize: 11, bold: true, charSpacing: 1.6, margin: 0 }
  );
}

function titulo(s, texto, escuro, y) {
  s.addText(texto, {
    x: M, y: y || 0.88, w: L, h: 1.15, fontFace: SERIF, fontSize: 34, bold: true,
    color: escuro ? PAPEL : TINTA, margin: 0, valign: "top",
  });
}

function paragrafos(s, itens, y, largura) {
  s.addText(
    itens.map((t, i) => ({
      text: typeof t === "string" ? t : t.text,
      options: {
        breakLine: i < itens.length - 1,
        bold: typeof t === "object" && t.forte,
        color: typeof t === "object" && t.forte ? TINTA : NEUTRO,
        paraSpaceAfter: 10,
      },
    })),
    { x: M, y, w: largura || 7.9, h: 3.2, fontFace: SANS, fontSize: 15, margin: 0, valign: "top", lineSpacing: 22 }
  );
}

function numeros(s, dados, y) {
  const larg = L / dados.length;
  dados.forEach((d, i) => {
    s.addText(d.n, {
      x: M + i * larg, y, w: larg - 0.25, h: 0.75, fontFace: SERIF, fontSize: d.n.length > 7 ? 30 : 40,
      bold: true, color: d.calmo ? INDIGO : BRASA, margin: 0, valign: "bottom",
    });
    s.addText(d.r, {
      x: M + i * larg, y: y + 0.8, w: larg - 0.25, h: 1.1, fontFace: SANS, fontSize: 12,
      color: NEUTRO, margin: 0, valign: "top", lineSpacing: 16,
    });
  });
}

function cartoes(s, itens, y, colunas) {
  const cols = colunas || 2;
  const larg = (L - 0.35 * (cols - 1)) / cols;
  const alt = itens.length > cols ? 2.0 : 2.2;
  itens.forEach((it, i) => {
    const cx = M + (i % cols) * (larg + 0.35);
    const cy = y + Math.floor(i / cols) * (alt + 0.3);
    s.addShape(p.ShapeType.rect, { x: cx, y: cy, w: larg, h: alt, fill: { color: SUAVE }, line: { color: SUAVE } });
    s.addText(it.t, { x: cx + 0.28, y: cy + 0.2, w: larg - 0.56, h: 0.6, fontFace: SERIF, fontSize: 16,
      bold: true, color: TINTA, margin: 0, valign: "top" });
    s.addText(it.d, { x: cx + 0.28, y: cy + 0.82, w: larg - 0.56, h: alt - 1.02, fontFace: SANS, fontSize: 12,
      color: NEUTRO, margin: 0, valign: "top", lineSpacing: 16 });
  });
}

function rodape(s, n) {
  s.addText(`${n} / 16`, { x: 13.33 - M - 1.2, y: 6.85, w: 1.2, h: 0.3, fontFace: SANS, fontSize: 10,
    color: NEUTRO, align: "right", margin: 0 });
  s.addText("saudeemdado.com", { x: M, y: 6.85, w: 4, h: 0.3, fontFace: SANS, fontSize: 10,
    color: NEUTRO, margin: 0 });
}

// ───────────────────────── 1. capa ─────────────────────────
let s = p.addSlide();
s.background = { color: TINTA };
eixo(s, "SAÚDE EM DADO", "saudeemdado.com", true);
s.addText("O leito que cria\na internação", { x: M, y: 1.5, w: L, h: 2.0, fontFace: SERIF, fontSize: 52,
  bold: true, color: PAPEL, margin: 0, lineSpacing: 56 });
s.addText("Uma plataforma aberta de indicadores do Sistema Único de Saúde — e três achados que contrariam a leitura corrente sobre atenção primária, com o método que os tornou possíveis.",
  { x: M, y: 3.7, w: 8.6, h: 1.0, fontFace: SANS, fontSize: 16, color: CLARO, margin: 0, lineSpacing: 24 });
s.addText([
  { text: "Pedro Paulo Fernandes", options: { bold: true, color: PAPEL, fontSize: 15, breakLine: true } },
  { text: "Mestrando em Saúde Coletiva · Instituto de Assistência Médica ao Servidor Público Estadual", options: { breakLine: true } },
  { text: "Pós-graduando em Inteligência Artificial e Ciência de Dados em Saúde · Hospital Sírio-Libanês", options: { breakLine: true } },
  { text: "Diretoria de Tecnologia da Informação · Prefeitura de Penápolis · ORCID 0009-0008-6248-2486", options: {} },
], { x: M, y: 5.0, w: 9.5, h: 1.4, fontFace: SANS, fontSize: 12, color: NEUTRO_ESCURO, margin: 0, lineSpacing: 18 });
s.addNotes("Apresentação de 20 minutos. Objetivo declarado: colaboração científica. Abrir pelo achado, não pela ferramenta.");

// ───────────────────────── 2. o problema ─────────────────────────
s = p.addSlide(); rodape(s, 2);
eixo(s, "O PROBLEMA");
titulo(s, "O microdado é público há décadas.\nO indicador reprodutível, não.");
paragrafos(s, [
  "O Sistema Único de Saúde publica alguns dos maiores conjuntos de microdados de saúde abertos do mundo — mortalidade, internações hospitalares, agravos de notificação, nascidos vivos. Qualquer pessoa pode baixar.",
  { text: "O que quase ninguém consegue é sair do arquivo bruto para um indicador municipal interpretável, versionado, com intervalo de confiança e com procedência auditável — e repetir isso seis meses depois obtendo o mesmo número.", forte: true },
  "Sem isso, cada grupo refaz o pipeline, cada refazimento produz um número ligeiramente diferente, e nenhum deles é conferível contra o outro.",
], 2.35, 10.2);
s.addNotes("Não falar da plataforma ainda. Estabelecer que o problema é reprodutibilidade, não disponibilidade.");

// ───────────────────────── 3. achado 1, montagem ─────────────────────────
s = p.addSlide(); rodape(s, 3);
eixo(s, "ACHADO 1", "Sistema de Informações Hospitalares + Cadastro Nacional de Estabelecimentos de Saúde · 5.570 municípios");
titulo(s, "A hipótese que a própria metodologia carregava — e que os dados derrubaram");
paragrafos(s, [
  "A leitura corrente diz: onde faltam leitos, a internação eletiva desaparece e a fatia de internações por condições sensíveis à atenção primária sobe mecanicamente. Isso prevê menos leitos, mais internações sensíveis.",
  { text: "Medido, dá o contrário.", forte: true },
], 2.45, 10.2);
numeros(s, [
  { n: "+0,32", r: "correlação bruta entre leitos por mil habitantes e proporção de internações sensíveis", calmo: true },
  { n: "+0,34", r: "controlando porte populacional e vulnerabilidade social", calmo: true },
  { n: "+0,16 a +0,47", r: "dentro de cada quartil de porte — positiva nos quatro" },
  { n: "17,8% vs 21,5%", r: "proporção de internações sensíveis: sem leito local contra com leito local" },
], 4.3);
s.addNotes("O ponto central: a correlação é positiva e sobrevive a todos os controles. Preparar o teste decisivo do próximo slide.");

// ───────────────────────── 4. achado 1, tabela ─────────────────────────
s = p.addSlide(); rodape(s, 4);
eixo(s, "ACHADO 1", "o teste decisivo: numerador ou denominador?");
titulo(s, "O efeito está quase todo no numerador");
s.addTable([
  [{ text: "Quartil de porte", options: { bold: true } }, { text: "Oferta local", options: { bold: true } },
   { text: "Internações sensíveis por 100 mil", options: { bold: true } },
   { text: "Internações não sensíveis por 100 mil", options: { bold: true } }],
  ["Q2", "sem leito → com leito", { text: "1.156 → 1.745   (+51%)", options: { color: BRASA, bold: true } }, { text: "5.483 → 5.887   (+7%)", options: { color: NEUTRO } }],
  ["Q3", "sem leito → com leito", { text: "961 → 1.782   (+85%)", options: { color: BRASA, bold: true } }, { text: "5.145 → 5.728   (+11%)", options: { color: NEUTRO } }],
  ["Q4", "sem leito → com leito", { text: "877 → 1.343   (+53%)", options: { color: BRASA, bold: true } }, { text: "5.604 → 5.571   (−1%)", options: { color: NEUTRO } }],
], { x: M, y: 2.3, w: L, colW: [1.9, 3.0, 3.4, 3.33], fontFace: SANS, fontSize: 13, color: TINTA,
     border: { type: "solid", color: "DCE2EC", pt: 1 }, rowH: 0.45, valign: "middle", margin: 6 });
paragrafos(s, [
  { text: "Não é a eletiva que some por falta de leito — é a internação sensível que aparece quando há leito na cidade.", forte: true },
  "Pneumonia, desidratação e descompensação de insuficiência cardíaca são exatamente o que um hospital pequeno interna. Ressalva declarada em toda a saída: as internações são contadas por município de residência e os leitos por município do estabelecimento; sem leito significa sem oferta local, não sem acesso.",
], 4.5, 11.6);
s.addNotes("Este é o slide que sustenta a apresentação inteira. Deixar o público ler a tabela antes de falar.");

// ───────────────────────── 5. achado 1, implicação ─────────────────────────
s = p.addSlide(); rodape(s, 5);
eixo(s, "ACHADO 1", "implicação");
titulo(s, "Insumo e desfecho medem o município,\nnão o desempenho");
s.addShape(p.ShapeType.rect, { x: M, y: 2.7, w: 10.6, h: 1.5, fill: { color: "F8E9E2" }, line: { color: "F8E9E2" } });
s.addText("Um município que abre um hospital pequeno vê sua proporção de internações sensíveis subir e, pela leitura convencional — internação sensível alta significa atenção básica fraca —, seria classificado como tendo piorado.",
  { x: M + 0.35, y: 2.9, w: 9.9, h: 1.1, fontFace: SERIF, fontSize: 19, italic: true, color: TINTA, margin: 0, lineSpacing: 26 });
paragrafos(s, [
  "É oferta induzindo demanda, concentrada justamente nas internações discricionárias que o indicador se propõe a medir.",
  { text: "O indicador não deixa de servir. Deixa de servir como ranking entre municípios de portes e ofertas diferentes.", forte: true },
], 4.6, 10.6);
s.addNotes("Aqui está a consequência de política pública. É o momento de pausar.");

// ───────────────────────── 6. achado 2 ─────────────────────────
s = p.addSlide(); rodape(s, 6);
eixo(s, "ACHADO 2", "e-Gestor Atenção Básica · Secretaria de Atenção Primária à Saúde · competência 2024");
titulo(s, "A cobertura potencial da atenção primária mede porte populacional");
numeros(s, [
  { n: "86,1%", r: "dos municípios com cobertura acima de 100% — mediana de 149,1% e máximo de 803,21%" },
  { n: "−0,54", r: "correlação com população: forte", calmo: true },
  { n: "+0,002", r: "correlação com internações sensíveis por 100 mil: bruta", calmo: true },
  { n: "+0,017", r: "parcial, controlando porte e vulnerabilidade", calmo: true },
], 2.4);
paragrafos(s, [
  { text: "Municípios com menos de 10 mil habitantes têm ao mesmo tempo a maior cobertura mediana (167,1%) e a maior taxa de internações sensíveis — o oposto da hipótese de política pública.", forte: true },
  "Robustez: trocando percentual por densidade de equipes por 10 mil habitantes, e taxa por proporção sobre o total de internações do próprio município, comparando cada município apenas aos pares do seu quartil de porte, a correlação fica entre −0,02 e +0,18.",
], 4.55, 11.6);
s.addNotes("Achado irmão do primeiro: os dois lados da equação medem característica do município.");

// ───────────────────────── 7. achado 3 ─────────────────────────
s = p.addSlide(); rodape(s, 7);
eixo(s, "ACHADO 3", "equidade — resultado nulo");
titulo(s, "O achado nulo que eu não queria encontrar");
s.addTable([
  [{ text: "Quartil de vulnerabilidade social", options: { bold: true } }, { text: "Q1", options: { bold: true } },
   { text: "Q2", options: { bold: true } }, { text: "Q3", options: { bold: true } }, { text: "Q4", options: { bold: true } }],
  ["Mediana entre municípios — o que publico", "19,1%", "21,1%", "20,6%", "19,8%"],
  ["Agregado, ponderado por internação", "18,1%", "21,0%", "22,5%", "23,7%"],
], { x: M, y: 2.25, w: L, colW: [5.0, 1.66, 1.66, 1.66, 1.65], fontFace: SANS, fontSize: 13, color: TINTA,
     border: { type: "solid", color: "DCE2EC", pt: 1 }, rowH: 0.42, valign: "middle", margin: 6 });
paragrafos(s, [
  "A segunda linha sobe do menos para o mais vulnerável, nos quatro anos da série. Parece a desigualdade que a primeira não mostra — e não é.",
  "O quartil menos vulnerável concentra 59,7% das internações do país em 25,2% dos municípios: é onde estão as cidades grandes, e cidade grande tem proporção baixa. O agregado mede porte disfarçado de vulnerabilidade.",
  { text: "Dentro da mesma faixa de porte o sinal troca de direção: ρ = −0,054 abaixo de 20 mil habitantes, +0,166 entre 20 e 100 mil. Paradoxo de Simpson. O resultado nulo se mantém — e publico as duas linhas, porque omitir a segunda não a impede de existir para quem baixar os dados.", forte: true },
], 3.75, 11.4);
s.addNotes("Não suavizar. O valor está em ter testado a fundo, reportado o nulo E documentado a armadilha que qualquer um encontraria sozinho.");

// ───────────────────────── 8. a plataforma ─────────────────────────
s = p.addSlide(); rodape(s, 8);
eixo(s, "A PLATAFORMA", "consequência dos achados, não vitrine");
titulo(s, "Os três achados só existem porque a base é reprodutível");
numeros(s, [
  { n: "10", r: "fontes integradas: mortalidade, internações, agravos, nascidos vivos, vacinação, estabelecimentos e leitos, gasto público, cobertura da atenção primária, saúde suplementar e censo demográfico", calmo: true },
  { n: "23,3 milhões", r: "de linhas publicadas em 47 tabelas, somando 86,9 megabytes em formato colunar", calmo: true },
  { n: "R$ 0", r: "de custo de infraestrutura: opera inteiramente em camadas gratuitas", calmo: true },
], 2.4);
paragrafos(s, [
  "Mortalidade de 2015 a 2024 · internações hospitalares de 2022 a 2024 · dengue de 2015 a 2025 · nascimentos de 2021 a 2023. Cinco domínios aparecem na interface; as demais tabelas ficam na interface de programação e nos downloads.",
  { text: "Dado agregado sob licença Creative Commons Atribuição 4.0, código sob licença do Instituto de Tecnologia de Massachusetts, resumo criptográfico de cada arquivo publicado e identificador digital de objeto 10.5281/zenodo.20706845.", forte: true },
  "Interface de programação pública sem cadastro e servidor de contexto para modelos de linguagem publicado no repositório oficial de pacotes Python.",
], 4.6, 11.6);
s.addNotes("Custo zero é a informação que costuma surpreender. Não vender: apenas registrar que a barreira não é orçamento.");

// ───────────────────────── 9. excesso de mortalidade ─────────────────────────
s = p.addSlide(); rodape(s, 9);
eixo(s, "MÉTODO", "excesso de mortalidade");
titulo(s, "Um baseline imune ao erro do denominador");
paragrafos(s, [
  "O baseline usual — média histórica escalada pela razão populacional — herda todo erro da projeção de população. Foi trocado por tendência linear por mês civil ajustada ao período de 2015 a 2019, que capta envelhecimento e se apoia apenas nos óbitos observados.",
], 2.4, 11.4);
numeros(s, [
  { n: "505 mil", r: "excesso pandêmico estimado pela variante padronizada por idade" },
  { n: "643 mil", r: "estimado pelo método de tendência, que foi o retido", calmo: true },
], 3.6);
paragrafos(s, [
  { text: "A diferença não é preferência de método.", forte: true },
  "A projeção populacional de 2018 superestima a população e a série publicada após o Censo de 2022 introduz descontinuidade. A padronização por idade herda os dois problemas pelo denominador e subestima o excesso.",
], 5.4, 11.4);
s.addNotes("Ponto metodológico transferível: qualquer análise escalada por população herda o erro do denominador.");

// ───────────────────────── 10. HSMR ─────────────────────────
s = p.addSlide(); rodape(s, 10);
eixo(s, "MÉTODO", "razão de mortalidade hospitalar padronizada");
titulo(s, "Intervalo exato e correção para dez mil comparações");
paragrafos(s, [
  "Padronização indireta por faixa etária e capítulo da Classificação Internacional de Doenças, intervalo de 95% pelo método gama de Poisson, e correção da taxa de descobertas falsas para as comparações simultâneas entre hospitais.",
], 2.4, 11.4);
numeros(s, [
  { n: "1,0000", r: "calibração nacional nos três anos: o esperado bate com o observado", calmo: true },
  { n: "757", r: "hospitais acima do esperado em 2024 após a correção — 16,0% do total", calmo: true },
  { n: "282", r: "de 10.046 perdem significância com a correção: seriam apontados por acaso" },
], 3.7);
paragrafos(s, [
  { text: "Sem a correção, 282 hospitais entrariam num relatório público como tendo mortalidade acima do esperado sem que houvesse evidência. Não é rigor decorativo: é a diferença entre acusar e medir.", forte: true },
], 5.6, 11.4);
s.addNotes("Se houver pergunta sobre método estatístico, é aqui que ela vem.");

// ───────────────────────── 11. previsão ─────────────────────────
s = p.addSlide(); rodape(s, 11);
eixo(s, "MÉTODO", "previsão de demanda hospitalar");
titulo(s, "A validação reprovou o modelo que eu preferia");
s.addTable([
  [{ text: "Horizonte", options: { bold: true } }, { text: "Erro escalonado do modelo publicado", options: { bold: true } },
   { text: "Erro dos modelos sazonais", options: { bold: true } }, { text: "Cobertura do intervalo de 95%", options: { bold: true } }],
  ["1 mês", "0,810", { text: "1,03 a 1,11", options: { color: NEUTRO } }, { text: "85% observada", options: { color: BRASA, bold: true } }],
  ["2 meses", "0,867", { text: "piores que o ingênuo", options: { color: NEUTRO } }, { text: "recalibrada empiricamente", options: { color: NEUTRO } }],
  ["3 meses", "0,922", { text: "apesar de parecerem melhores", options: { color: NEUTRO } }, { text: "para 2,42 · 2,64 · 2,80", options: { color: NEUTRO } }],
], { x: M, y: 2.3, w: L, colW: [1.9, 3.6, 3.2, 2.93], fontFace: SANS, fontSize: 13, color: TINTA,
     border: { type: "solid", color: "DCE2EC", pt: 1 }, rowH: 0.45, valign: "middle", margin: 6 });
paragrafos(s, [
  "Validação por origem móvel em 4.445 hospitais. Erro escalonado abaixo de 1 significa superar o modelo ingênuo sazonal calculado dentro do período de treino.",
  { text: "Os modelos sazonais pareciam melhores no agregado nacional e saíram piores por unidade. E o intervalo declarado como de 95% cobria de fato 85% — foi recalibrado empiricamente em vez de confiar na normalidade.", forte: true },
], 4.5, 11.6);
s.addNotes("Modelo que reprova o próprio autor. É o slide que demonstra cultura de validação.");

// ───────────────────────── 12. integridade da coleta ─────────────────────────
s = p.addSlide(); rodape(s, 12);
eixo(s, "MÉTODO", "integridade da coleta");
titulo(s, "O defeito que a contagem de linhas não pega");
paragrafos(s, [
  "Os pipelines tratavam a falha de download como se a competência não existisse. Seis anos-unidade da federação entraram no ar incompletos, com código de saída zero e números plausíveis.",
], 2.35, 11.4);
numeros(s, [
  { n: "−41%", r: "das internações do Maranhão em 2023, publicadas a menos" },
  { n: "+67,6%", r: "correção aplicada na interface pública: de 293.243 para 491.355", calmo: true },
  { n: "459 de 459", r: "checkpoints idênticos ao refazer os 351 anos-unidade da federação do zero", calmo: true },
], 3.5);
paragrafos(s, [
  { text: "Contagem de linhas não detecta corrupção — duplicata e ausência se cancelam no total. E o resumo criptográfico prova que o arquivo não mudou depois de escrito, não que foi escrito certo.", forte: true },
  "A guarda que funciona é recarregar o dado num banco vazio e deixar a chave primária reclamar.",
], 5.35, 11.4);
s.addNotes("Apresentar como tese metodológica, não como confissão. É evidência de cultura de método.");

// ───────────────────────── 13. proveniência ─────────────────────────
s = p.addSlide(); rodape(s, 13);
eixo(s, "MÉTODO", "proveniência");
titulo(s, "A linhagem viaja dentro dos bytes");
cartoes(s, [
  { t: "Cada arquivo se declara", d: "O arquivo colunar carrega, nos próprios metadados, quem o produziu e de qual versão da fonte veio. Um arquivo exportado do banco e um gerado pelo pipeline deixam de ser indistinguíveis." },
  { t: "Cada publicação é imutável", d: "Publicação datada, com manifesto versionado e cópia histórica preservada. O histórico de publicações é a própria série de instantâneos." },
  { t: "O checkpoint se autoinvalida", d: "Carimba de quais meses veio. Se a fonte for reescrita, ele deixa de servir sozinho na execução seguinte, em vez de ser reaproveitado indefinidamente." },
  { t: "Preliminar quanto?", d: "Pergunta que nenhuma fonte pública responde hoje: o sistema oficial de tabulação entrega o número de hoje e não guarda memória do mês passado." },
], 2.2, 2);
s.addNotes("Ligar com a pergunta de revisão da fonte, que interessa a quem trabalha com dado preliminar.");

// ───────────────────────── 14. limites ─────────────────────────
s = p.addSlide(); rodape(s, 14);
eixo(s, "LIMITES", "declarados em toda a saída");
titulo(s, "O que esta plataforma não pode afirmar");
const LIMITES = [
  ["Desenho ecológico. ", "Correlação municipal não é efeito individual. Nenhum dos achados sustenta inferência sobre pessoas."],
  ["Unidades diferentes nos dois lados. ", "As internações são contadas por município de residência; os leitos, por município do estabelecimento."],
  ["O ano mais recente é preliminar ", "e sujeito a revisão pelo Ministério da Saúde."],
  ["O índice de vulnerabilidade é aproximação ", "construída com dois indicadores do Censo de 2022 — não é o índice oficial do Instituto de Pesquisa Econômica Aplicada."],
  ["A classificação municipal por agrupamento está suspensa. ", "A estabilidade foi medida — o índice de Rand ajustado ficou em 0,571 entre reamostragens — e a publicação foi congelada até ser substituída por estratificação determinística."],
];
s.addText(
  LIMITES.flatMap(([forte, resto], i) => ([
    { text: forte, options: { bold: true, color: TINTA, bullet: { code: "25AA" }, paraSpaceAfter: 14 } },
    { text: resto, options: { color: NEUTRO, breakLine: i < LIMITES.length - 1, paraSpaceAfter: 14 } },
  ])),
  { x: M, y: 2.3, w: 11.4, h: 4.0, fontFace: SANS, fontSize: 14, margin: 0, valign: "top", lineSpacing: 21 }
);
s.addNotes("Declarar os limites antes que perguntem. Constrói credibilidade com público sênior.");

// ───────────────────────── 15. futuro ─────────────────────────
s = p.addSlide(); rodape(s, 15);
eixo(s, "FUTURO", "convite, não promessa");
titulo(s, "O que está a um passo de existir");
cartoes(s, [
  { t: "Internações por causas imunizáveis", d: "O grupo de condições preveníveis por vacinação — coqueluche, difteria, tétano, sarampo, rubéola, hepatite B, caxumba, febre amarela, meningite e tuberculose — já está codificado no pipeline, mas ainda não é publicado em separado. Publicá-lo daria um desfecho populacional de impacto vacinal." },
  { t: "Contexto para estudos individuais", d: "Indicadores municipais validados — mortalidade padronizada, internações sensíveis, oferta de leitos e gasto público — para situar coortes e interpretar heterogeneidade." },
  { t: "Medir a revisão da fonte", d: "Quanto um número preliminar ainda se move, por competência e unidade da federação. Hoje impossível em qualquer fonte pública brasileira." },
  { t: "Vigilância de síndrome respiratória", d: "O sistema de vigilância de síndrome respiratória aguda grave como próxima fonte. O boletim semanal já consome estimativa em tempo quase real de arboviroses." },
], 2.2, 2);
s.addNotes("O primeiro cartão é o gancho para vacinologia. Deixar claro que ainda não existe.");

// ───────────────────────── 16. encerramento ─────────────────────────
s = p.addSlide();
s.background = { color: TINTA };
eixo(s, "ENCERRAMENTO", "a pergunta", true);
titulo(s, "O que eu vim propor", true, 1.15);
s.addText([
  { text: "A plataforma já entrega, hoje, um desfecho populacional validado e reprodutível para os 5.570 municípios brasileiros. O que ela não tem é a pergunta biológica.", options: { color: PAPEL, bold: true, breakLine: true, paraSpaceAfter: 14 } },
  { text: "Vejo três frentes onde isso encontra o seu trabalho: internação por doença prevenível por vacina como desfecho populacional de impacto vacinal; epidemiologia digital com procedência auditável para preparação a epidemias; e a camada de contexto municipal para estudos de sistemas que hoje têm amostra pequena e território pobre.", options: { color: CLARO, breakLine: true, paraSpaceAfter: 14 } },
  { text: "Minha pergunta é direta: alguma dessas frentes é útil ao que o seu grupo está fazendo — e, se for, qual delas você atacaria primeiro?", options: { color: PAPEL, bold: true } },
], { x: M, y: 2.5, w: 10.8, h: 3.2, fontFace: SANS, fontSize: 16, margin: 0, valign: "top", lineSpacing: 24 });
s.addText("saudeemdado.com   ·   pedropaulofernandes88@gmail.com   ·   ORCID 0009-0008-6248-2486   ·   dados sob Creative Commons Atribuição 4.0   ·   código sob licença MIT",
  { x: M, y: 6.4, w: 11.6, h: 0.4, fontFace: SANS, fontSize: 11, color: NEUTRO_ESCURO, margin: 0 });
s.addNotes("Este é o único slide que muda se o objetivo da conversa mudar. Fazer a pergunta e calar.");

const saida = require("path").join(__dirname, "saida", "Saude-em-Dado-apresentacao.pptx");
p.writeFile({ fileName: saida })
  .then((f) => console.log("gravado:", f));
