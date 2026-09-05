/**
 * Slug estável para âncoras de seção.
 *
 * Estável importa mais que bonito: a âncora entra em citação, e-mail e artigo,
 * então mudar o slug quebra link de terceiro. Derivamos do título sem o número
 * da seção — renumerar a metodologia não deve invalidar links existentes.
 */
export function slugify(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "") // remove acentos
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/**
 * Índice da página de metodologia — fonte única para o sumário e para as
 * âncoras dos títulos.
 *
 * A página tem 22 seções e ~150 KB. Sem âncora, não dá para mandar a alguém
 * "veja como padronizamos a taxa": só "está em algum lugar dessa página". Para
 * um projeto que pede para ser citado, a seção precisa ter endereço próprio.
 *
 * Os grupos são contíguos e seguem a ordem do documento — o sumário nunca
 * reordena o que está na página.
 */
export interface SecaoMetodologia {
  n: number;
  titulo: string;
  /** Âncora estável, derivada do título (sem o número da seção). */
  slug: string;
  grupo: string;
}

/**
 * Um título pode vir sozinho (o slug sai dele) ou como par
 * `[título, slugFixo]`. O par existe para quando o TÍTULO precisa mudar sem
 * levar a âncora junto — foi o caso de "Arquétipos de saúde municipal
 * (k-means)" em 2026-08-29: o método deixou de ser k-means, então o título
 * mentia, mas o slug já circulava em citação. Corrigir o texto e preservar o
 * endereço são duas necessidades legítimas, e sem esta forma só dá para
 * atender uma.
 */
type EntradaTitulo = string | [titulo: string, slugFixo: string];

const TITULOS: [grupo: string, titulos: EntradaTitulo[]][] = [
  [
    "Método base",
    [
      "Fontes de dados",
      "Critérios de inclusão e derivações",
      "Granularidade por período",
      "Taxa padronizada por idade",
      "Intervalos de confiança (IC95%)",
      "Excesso de mortalidade",
      "Validação automática",
      "Limitações conhecidas",
    ],
  ],
  [
    "Domínios de dados",
    [
      "Dengue (SINAN)",
      "Internações hospitalares (SIH/AIH)",
      "Vulnerabilidade social (proxy, Censo 2022)",
      "Internações evitáveis (ICSAP) e fluxo de pacientes",
      "Agravos traçadores e visão hospitalar (SIH 2024)",
      "Mortalidade ajustada (HSMR), permanência esperada e projeção de demanda",
      "Cobertura da Atenção Primária (e-Gestor AB)",
      "Vacinação (PNI/RNDS) e os limites da cobertura municipal",
    ],
  ],
  [
    "Análises derivadas",
    [
      ["Arquétipos de saúde municipal", "arquetipos-de-saude-municipal-k-means"],
      "Distância até os pares em internações evitáveis (ICSAP)",
      "Estabelecimentos de saúde (CNES)",
      "Leitos × ICSAP: o indicador responde à oferta hospitalar",
      "Vazio assistencial e mortalidade: um achado nulo, testado a fundo",
      "Gasto público em saúde (SIOPS) × ICSAP: o quarto achado nulo",
      "Perfil de causas por município: seis eixos, nenhum grupo, e a codificação",
    ],
  ],
  ["Governança", ["Privacidade e células de contagem pequena"]],
];

export const SECOES: SecaoMetodologia[] = TITULOS.flatMap(([grupo, titulos]) =>
  titulos.map((entrada) => {
    const [titulo, slugFixo] = Array.isArray(entrada) ? entrada : [entrada, undefined];
    return { titulo, grupo, slug: slugFixo ?? slugify(titulo), n: 0 };
  }),
).map((s, i) => ({ ...s, n: i + 1 }));

/** Seção pelo número exibido (1-based); lança se o número não existir. */
export function secao(n: number): SecaoMetodologia {
  const s = SECOES[n - 1];
  if (!s) throw new Error(`metodologia: seção ${n} não existe`);
  return s;
}

/**
 * Título de uma seção pelo slug, ou `null` se o slug não existe mais.
 *
 * Mora aqui, e não no catálogo de indicadores, porque é conhecimento sobre
 * seções — e porque o contrário criaria um import entre dois módulos de `lib/`
 * que o runner de teste do Node só resolve com extensão explícita. Dependência
 * que existe por conveniência de um consumidor tende a apontar para o lado
 * errado.
 */
export function tituloDoSlug(slug: string): string | null {
  return SECOES.find((s) => s.slug === slug)?.titulo ?? null;
}

/** Grupos na ordem do documento, para montar o sumário. */
export function gruposOrdenados(): { grupo: string; secoes: SecaoMetodologia[] }[] {
  const out: { grupo: string; secoes: SecaoMetodologia[] }[] = [];
  for (const s of SECOES) {
    const ultimo = out[out.length - 1];
    if (ultimo?.grupo === s.grupo) ultimo.secoes.push(s);
    else out.push({ grupo: s.grupo, secoes: [s] });
  }
  return out;
}
