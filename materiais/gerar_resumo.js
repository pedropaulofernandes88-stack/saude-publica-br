// Resumo objetivo do Saúde em Dado, para ENTREGAR — não para apresentar.
//
// O deck de 16 slides existe para ser narrado; este existe para ser lido
// sozinho, depois, possivelmente por alguém do grupo que não esteve na
// conversa. Muda o que entra: nada de arco narrativo, nada de suspense entre
// slides, cada página se sustenta isolada. Sete páginas.
//
// Mesma linguagem visual dos outros materiais, de propósito: quem receber os
// dois reconhece que vieram do mesmo lugar.
const pptxgen = require("pptxgenjs");

const TINTA = "101521", PAPEL = "FFFFFF", SUAVE = "EEF1F6";
const INDIGO = "1F4FA8", BRASA = "B8461E";
const NEUTRO = "5A6478", CLARO = "C9D2E2", NEUTRO_ESCURO = "94A0B8";
const SERIF = "Cambria", SANS = "Calibri";

const p = new pptxgen();
p.layout = "LAYOUT_WIDE";
p.author = "Pedro Paulo Fernandes";
p.title = "Saude em Dado — resumo";
p.subject = "Plataforma aberta de indicadores do SUS: escopo, metodo, limites e frentes de colaboracao";

const M = 0.85, L = 13.33 - 2 * M, TOTAL = 7;

function eixo(s, texto, sub, escuro) {
  s.addText([{ text: texto, options: { color: escuro ? CLARO : INDIGO } },
             ...(sub ? [{ text: "   " + sub, options: { color: escuro ? NEUTRO_ESCURO : NEUTRO } }] : [])],
    { x: M, y: 0.42, w: L, h: 0.3, fontFace: SANS, fontSize: 11, bold: true, charSpacing: 1.6, margin: 0 });
}
function titulo(s, texto, escuro, y) {
  s.addText(texto, { x: M, y: y || 0.88, w: L, h: 1.05, fontFace: SERIF, fontSize: 30, bold: true,
    color: escuro ? PAPEL : TINTA, margin: 0, valign: "top" });
}
function paragrafos(s, itens, y, largura, tam) {
  s.addText(itens.map((t, i) => ({
      text: typeof t === "string" ? t : t.text,
      options: { breakLine: i < itens.length - 1, bold: typeof t === "object" && t.forte,
        color: typeof t === "object" && t.forte ? TINTA : NEUTRO, paraSpaceAfter: 9 },
    })),
    { x: M, y, w: largura || 11.6, h: 3.4, fontFace: SANS, fontSize: tam || 14, margin: 0,
      valign: "top", lineSpacing: (tam || 14) + 7 });
}
function numeros(s, dados, y) {
  const larg = L / dados.length;
  dados.forEach((d, i) => {
    s.addText(d.n, { x: M + i * larg, y, w: larg - 0.25, h: 0.7, fontFace: SERIF,
      fontSize: d.n.length > 7 ? 26 : 34, bold: true, color: d.calmo ? INDIGO : BRASA,
      margin: 0, valign: "bottom" });
    s.addText(d.r, { x: M + i * larg, y: y + 0.74, w: larg - 0.25, h: 1.0, fontFace: SANS,
      fontSize: 11.5, color: NEUTRO, margin: 0, valign: "top", lineSpacing: 15 });
  });
}
function cartoes(s, itens, y, colunas, altura) {
  const cols = colunas || 3;
  const larg = (L - 0.32 * (cols - 1)) / cols;
  const alt = altura || 2.4;
  itens.forEach((it, i) => {
    const cx = M + (i % cols) * (larg + 0.32);
    const cy = y + Math.floor(i / cols) * (alt + 0.28);
    s.addShape(p.ShapeType.rect, { x: cx, y: cy, w: larg, h: alt, fill: { color: SUAVE }, line: { color: SUAVE } });
    s.addText(it.t, { x: cx + 0.26, y: cy + 0.18, w: larg - 0.52, h: 0.62, fontFace: SERIF,
      fontSize: 14.5, bold: true, color: TINTA, margin: 0, valign: "top" });
    s.addText(it.d, { x: cx + 0.26, y: cy + 0.8, w: larg - 0.52, h: alt - 0.98, fontFace: SANS,
      fontSize: 11.5, color: NEUTRO, margin: 0, valign: "top", lineSpacing: 15 });
  });
}
function rodape(s, n) {
  s.addText(`${n} / ${TOTAL}`, { x: 13.33 - M - 1.2, y: 6.9, w: 1.2, h: 0.3, fontFace: SANS,
    fontSize: 10, color: NEUTRO, align: "right", margin: 0 });
  s.addText("saudeemdado.com · CC BY 4.0 · DOI 10.5281/zenodo.20706845", { x: M, y: 6.9, w: 8, h: 0.3,
    fontFace: SANS, fontSize: 10, color: NEUTRO, margin: 0 });
}

// ── 1. capa ──────────────────────────────────────────────────────────────────
let s = p.addSlide();
s.background = { color: TINTA };
eixo(s, "SAÚDE EM DADO", "saudeemdado.com", true);
s.addText("Indicadores do SUS,\nreprodutíveis e datados", { x: M, y: 1.55, w: L, h: 1.9,
  fontFace: SERIF, fontSize: 44, bold: true, color: PAPEL, margin: 0, lineSpacing: 50 });
s.addText("Dez fontes oficiais integradas em 47 tabelas públicas, com procedência gravada em cada arquivo e histórico imutável de publicações. Resumo de escopo, método, limites e frentes de colaboração.",
  { x: M, y: 3.65, w: 9.4, h: 1.0, fontFace: SANS, fontSize: 15, color: CLARO, margin: 0, lineSpacing: 23 });
s.addText([
  { text: "Preparado para o Dr. Helder Nakaya", options: { bold: true, color: PAPEL, fontSize: 14, breakLine: true } },
  { text: "Pedro Paulo Fernandes · Mestrando em Saúde Coletiva, IAMSPE", options: { breakLine: true } },
  { text: "Pós-graduando em IA e Ciência de Dados em Saúde, Hospital Sírio-Libanês", options: { breakLine: true } },
  { text: "ORCID 0009-0008-6248-2486 · pedropaulofernandes88@gmail.com", options: {} },
], { x: M, y: 5.05, w: 9.5, h: 1.3, fontFace: SANS, fontSize: 12, color: NEUTRO_ESCURO,
     margin: 0, lineSpacing: 18 });

// ── 2. o que é ───────────────────────────────────────────────────────────────
s = p.addSlide(); rodape(s, 2);
eixo(s, "ESCOPO", "o que existe hoje");
titulo(s, "Uma base nacional, aberta e conferível");
paragrafos(s, [
  "Microdados oficiais do SUS transformados em indicadores municipais interpretáveis: taxas padronizadas por idade, intervalos de confiança, excesso de mortalidade, mortalidade hospitalar ajustada com correção para comparações múltiplas.",
], 2.05, 11.6);
numeros(s, [
  { n: "10", r: "fontes: SIM, SIH, SINAN, SINASC, PNI/RNDS, CNES, SIOPS, e-Gestor AB, ANS, IBGE", calmo: true },
  { n: "39", r: "tabelas publicadas, 5,33 milhões de linhas em formato colunar", calmo: true },
  { n: "5.570", r: "municípios, todos, sem amostragem", calmo: true },
  { n: "R$ 0", r: "custo de infraestrutura — opera em camadas gratuitas", calmo: true },
], 3.05);
paragrafos(s, [
  { text: "Cobertura temporal: mortalidade 2015–2024 · internações 2021–2024 · dengue 2015–2025 · nascimentos 2021–2024 · vacinação 2023 até o mês passado.", forte: true },
], 5.35, 11.6, 13);

// ── 3. por que é confiável ───────────────────────────────────────────────────
s = p.addSlide(); rodape(s, 3);
eixo(s, "MÉTODO", "o que sustenta os números");
titulo(s, "A garantia não é a ausência de erro.\nÉ o mecanismo que o encontra.");
cartoes(s, [
  { t: "Um defeito real, achado e corrigido",
    d: "O coletor publicava competências incompletas com código de saída zero. O Maranhão de 2023 saiu com 41% das internações a menos. Corrigido, com 351 anos-UF refeitos da fonte: 459 de 459 checkpoints idênticos." },
  { t: "Contagem de linhas não detecta corrupção",
    d: "Duplicata e ausência se cancelam no total, e o checksum prova que o arquivo não mudou depois de escrito, não que foi escrito certo. A guarda que funciona é recarregar em banco vazio e deixar a chave primária reclamar." },
  { t: "Linhagem dentro dos bytes",
    d: "Cada Parquet declara quem o produziu e de qual versão da fonte veio. Publicação datada e imutável: o próprio histórico constitui a série de instantâneos, e responde quanto um número preliminar ainda se moveu." },
], 2.25, 3, 2.55);
paragrafos(s, [
  { text: "O banco inteiro é reconstruído do zero a cada alteração, em integração contínua: 213 instruções de esquema, 4,37 milhões de linhas em 37 tabelas, 51 segundos. 562 testes automatizados.", forte: true },
], 5.15, 11.6, 13);

// ── 4. achados ───────────────────────────────────────────────────────────────
s = p.addSlide(); rodape(s, 4);
eixo(s, "ACHADOS", "todos com desenho declarado e dado aberto");
titulo(s, "Três resultados, dois deles nulos");
cartoes(s, [
  { t: "O leito cria a internação evitável",
    d: "Leitos SUS por mil × proporção de ICSAP: ρ = +0,32 bruta, +0,34 controlando porte e vulnerabilidade, positiva nos quatro quartis de porte. Municípios sem leito local têm proporção MENOR (17,8%) que os com leito (21,5%). O efeito está no numerador: ICSAP sobe 51–85% quando há leito; não-ICSAP, 1–11%." },
  { t: "Cobertura da atenção primária não explica",
    d: "ρ = +0,002 com internações evitáveis por 100 mil; +0,017 controlando porte e vulnerabilidade. Testado em seis desenhos. A cobertura potencial satura acima de 100% em 86% dos municípios e correlaciona-se com população (ρ = −0,54): mede porte." },
  { t: "Vulnerabilidade também não — e a armadilha",
    d: "Mediana entre municípios: 19,1 / 21,1 / 20,6 / 19,8 por quartil de vulnerabilidade. O agregado ponderado por internação parece monotônico (18,1 → 23,7), mas é paradoxo de Simpson: o quartil menos vulnerável concentra 59,7% das internações. Dentro do porte, o sinal troca de direção." },
], 2.25, 3, 2.75);
paragrafos(s, [
  { text: "Publico as duas leituras do terceiro com o mecanismo que as separa. Omitir a segunda não a impediria de existir para quem baixa a tabela.", forte: true },
], 5.35, 11.6, 13);

// ── 5. limites ───────────────────────────────────────────────────────────────
s = p.addSlide(); rodape(s, 5);
eixo(s, "LIMITES", "declarados, não escondidos em rodapé");
titulo(s, "O que esta base NÃO pode afirmar");
paragrafos(s, [
  { text: "Nada é individual.", forte: true },
  "Tudo é agregado municipal. Não há vinculação de registros, nem meio de fazê-la: o banco recebe apenas contagens por município, período e categoria.",
  { text: "Nada é molecular.", forte: true },
  "É dado administrativo do sistema de saúde. Não substitui coorte nem fenotipagem.",
  { text: "O desenho é ecológico.", forte: true },
  "Correlação municipal não implica efeito individual. Nenhum achado sustenta inferência sobre pessoas.",
  { text: "Cobertura vacinal municipal não é publicável — testada e reprovada.", forte: true },
  "Correlação de 0,591 entre dois anos consecutivos, e cobertura mediana caindo de 102,7% nos municípios com 50 a 100 nascidos para 86,2% nos com mais de 5 mil: viés sistemático de denominador. A hipótese de descasamento geográfico foi medida e refutada (ρ = +0,002). Publico contagem de doses por município, e cobertura apenas por unidade da federação.",
], 2.05, 11.6, 13.5);

// ── 6. colaboração ───────────────────────────────────────────────────────────
s = p.addSlide(); rodape(s, 6);
eixo(s, "COLABORAÇÃO", "três frentes concretas");
titulo(s, "Onde esta base encontra a pesquisa em imunologia de sistemas");
cartoes(s, [
  { t: "1 · O elo populacional do impacto vacinal",
    d: "A vacinologia de sistemas prediz resposta individual — assinatura precoce, título de anticorpo. Falta o desfecho populacional. A base tem 638 milhões de doses aplicadas (2023 a agosto de 2026, por município, imunobiológico, dose, idade, sexo e raça) e internações por doença imunoprevenível — grupo 1 da Lista Brasileira, 38.535 em 2024, por município e ano." },
  { t: "2 · Camada de contexto para coortes",
    d: "Estudos de imunologia têm N de dezenas a centenas, de um ou dois centros, e a heterogeneidade de resposta fica sem explicação territorial. A base oferece contexto municipal validado: mortalidade padronizada, internações evitáveis, oferta de leitos, gasto público em saúde, vulnerabilidade social e cobertura da atenção primária." },
  { t: "3 · Epidemiologia digital com procedência",
    d: "Vigilância corrente — vacinação com um mês de defasagem, arboviroses com nowcasting semanal — somada a histórico datado e imutável. Permite responder quanto um número preliminar ainda se move por competência e unidade da federação, o que nenhuma fonte pública brasileira responde hoje." },
], 2.2, 3, 2.95);

// ── 7. acesso ────────────────────────────────────────────────────────────────
s = p.addSlide(); rodape(s, 7);
eixo(s, "ACESSO", "sem cadastro, sem custo");
titulo(s, "Como usar, verificar e citar");
cartoes(s, [
  { t: "API REST pública",
    d: "PostgREST sobre as 47 tabelas, sem cadastro, com filtros por município, ano, causa e faixa etária. Chave pública de leitura documentada em saudeemdado.com/dados." },
  { t: "Arquivos e checksum",
    d: "Parquet por tabela, com SHA-256 e histórico datado de cada publicação. Permite refazer qualquer número e comparar versões ao longo do tempo." },
  { t: "Servidor MCP",
    d: "Acesso nativo por modelo de linguagem, com regra anti-alucinação: todo número retorna com a fonte. Instalável a partir do PyPI, roda na máquina do usuário." },
  { t: "Metodologia aberta",
    d: "Vinte e três seções com âncora permanente por seção, incluindo os achados nulos e as limitações. Código sob licença MIT, dados sob CC BY 4.0." },
  { t: "Citável",
    d: "DOI de conceito versionado no Zenodo: 10.5281/zenodo.20706845. Cada publicação datada mantém sua cópia imutável." },
  { t: "Contato",
    d: "Pedro Paulo Fernandes · pedropaulofernandes88@gmail.com · ORCID 0009-0008-6248-2486 · repositório aberto no GitHub." },
], 2.2, 3, 2.1);

const saida = require("path").join(__dirname, "saida", "Saude-em-Dado-resumo.pptx");
p.writeFile({ fileName: saida }).then(() => console.log("gravado:", saida));
