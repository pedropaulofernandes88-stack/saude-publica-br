const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, LevelFormat, TableOfContents,
} = require("docx");
const fs = require("fs");

const TINTA = "101521", INDIGO = "1F4FA8", BRASA = "B8461E", NEUTRO = "45506A";
const SERIF = "Cambria", SANS = "Calibri";

const P = (texto, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 160, line: 300 },
  alignment: o.centro ? AlignmentType.CENTER : AlignmentType.JUSTIFIED,
  indent: o.recuo ? { left: 360 } : undefined,
  children: (Array.isArray(texto) ? texto : [{ t: texto }]).map((r) => new TextRun({
    text: r.t, bold: r.forte, italics: r.italico,
    color: r.cor || (o.suave ? NEUTRO : TINTA), font: SANS, size: o.tamanho || 21,
  })),
});

const H1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 480, after: 220 }, pageBreakBefore: false,
  children: [new TextRun({ text: t, font: SERIF, size: 34, bold: true, color: TINTA })],
});
const H2 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 340, after: 160 },
  children: [new TextRun({ text: t, font: SERIF, size: 27, bold: true, color: TINTA })],
});
const H3 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_3, spacing: { before: 260, after: 120 },
  children: [new TextRun({ text: t, font: SANS, size: 22, bold: true, color: INDIGO })],
});
const LI = (t) => new Paragraph({
  numbering: { reference: "marcadores", level: 0 }, spacing: { after: 110, line: 300 },
  children: (Array.isArray(t) ? t : [{ t }]).map((r) => new TextRun({
    text: r.t, bold: r.forte, color: r.cor || TINTA, font: SANS, size: 21,
  })),
});
const NOTA = (t) => new Paragraph({
  spacing: { before: 140, after: 200, line: 300 },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: BRASA, space: 14 } },
  indent: { left: 220 },
  children: [new TextRun({ text: t, font: SANS, size: 20, color: NEUTRO, italics: true })],
});

function tabela(cabecalho, linhas, larguras) {
  const total = larguras.reduce((a, b) => a + b, 0);
  const celula = (texto, forte, fundo) => new TableCell({
    width: { size: larguras[0], type: WidthType.DXA },
    shading: fundo ? { type: ShadingType.CLEAR, fill: fundo, color: "auto" } : undefined,
    margins: { top: 90, bottom: 90, left: 130, right: 130 },
    children: [new Paragraph({
      spacing: { after: 0, line: 260 },
      children: [new TextRun({ text: texto, bold: forte, font: SANS, size: 19, color: TINTA })],
    })],
  });
  const linha = (celulas, forte, fundo) => new TableRow({
    children: celulas.map((c, i) => {
      const cel = celula(c, forte, fundo);
      cel.root[1].root[1] = undefined;
      return new TableCell({
        width: { size: larguras[i], type: WidthType.DXA },
        shading: fundo ? { type: ShadingType.CLEAR, fill: fundo, color: "auto" } : undefined,
        margins: { top: 90, bottom: 90, left: 130, right: 130 },
        children: [new Paragraph({
          spacing: { after: 0, line: 260 },
          children: [new TextRun({ text: c, bold: forte, font: SANS, size: 19, color: TINTA })],
        })],
      });
    }),
  });
  return new Table({
    columnWidths: larguras,
    width: { size: total, type: WidthType.DXA },
    rows: [linha(cabecalho, true, "EEF1F6"), ...linhas.map((l) => linha(l, false))],
  });
}

const conteudo = [];
const add = (...xs) => xs.forEach((x) => conteudo.push(x));

// ══════════════════════════ CAPA ══════════════════════════
add(
  new Paragraph({ spacing: { before: 2400, after: 120 }, children: [new TextRun({
    text: "SAÚDE EM DADO", font: SANS, size: 20, bold: true, color: INDIGO, characterSpacing: 60 })] }),
  new Paragraph({ spacing: { after: 200 }, children: [new TextRun({
    text: "Documentação completa da plataforma\ne guia da apresentação".replace("\n", " "),
    font: SERIF, size: 48, bold: true, color: TINTA })] }),
  P([{ t: "Parte I — o que foi construído, com que fontes, por quais métodos e com quais resultados. " },
     { t: "Parte II — como a apresentação foi montada, o que dizer em cada slide e o que esperar de pergunta." }],
    { suave: true, tamanho: 23 }),
  new Paragraph({ spacing: { before: 600, after: 60 }, children: [new TextRun({
    text: "Pedro Paulo Fernandes", font: SANS, size: 22, bold: true, color: TINTA })] }),
  P("Mestrando em Saúde Coletiva no Instituto de Assistência Médica ao Servidor Público Estadual. Pós-graduando em Inteligência Artificial e Ciência de Dados em Saúde no Hospital Sírio-Libanês. Diretoria de Tecnologia da Informação da Prefeitura Municipal de Penápolis. Identificador aberto de pesquisador e colaborador: 0009-0008-6248-2486.",
    { suave: true, tamanho: 19 }),
  P("Endereço da plataforma: saudeemdado.com. Documento gerado em 25 de agosto de 2026. Todos os números apresentados foram medidos na própria plataforma; nenhum foi estimado.",
    { suave: true, tamanho: 19 }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ══════════════════════════ SUMÁRIO ══════════════════════════
add(H1("Sumário"), new TableOfContents("Sumário", { hyperlink: true, headingStyleRange: "1-3" }),
  new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════ PARTE I ══════════════════════════
add(H1("Parte I — A plataforma Saúde em Dado"));

add(H2("1. O que é, e o problema que ela resolve"));
add(P("O Saúde em Dado é uma plataforma aberta que transforma os microdados públicos do Sistema Único de Saúde e do Instituto Brasileiro de Geografia e Estatística em indicadores municipais validados, reprodutíveis e acompanhados de medida de incerteza."));
add(P("O problema que a motivou não é falta de dado. O Ministério da Saúde publica alguns dos maiores conjuntos de microdados de saúde abertos do mundo, e qualquer pessoa pode baixá-los. O problema é a distância entre o arquivo bruto e o indicador interpretável: extrair, limpar, harmonizar códigos, escolher denominador populacional, padronizar por idade, calcular intervalo de confiança e publicar de forma que outra pessoa chegue exatamente ao mesmo número é um trabalho que se repete em cada grupo de pesquisa, e cujo resultado raramente é conferível contra o de outro grupo."));
add(P("A plataforma existe para fechar essa distância uma vez, de forma pública e auditável, e para que os indicadores resultantes possam ser citados com identificador permanente e verificados por resumo criptográfico."));
add(NOTA("Princípio que organiza todo o projeto: o arquivo publicado é a verdade; o banco de dados é apenas uma cópia para consulta rápida, reconstruível a qualquer momento a partir dos arquivos."));

add(H2("2. As fontes de dados"));
add(P("São dez fontes de dados integradas. Cada um entra com um recorte próprio, e as diferenças entre eles — unidade de registro, período de cobertura, momento de fechamento — são declaradas em toda a saída, porque elas mudam o que cada indicador pode afirmar."));
add(tabela(
  ["Fonte", "O que fornece", "Período coberto"],
  [
    ["Sistema de Informações sobre Mortalidade", "Declarações de óbito individuais: data, sexo, idade, município de residência, local de ocorrência e causa básica pela Classificação Internacional de Doenças, décima revisão", "2015 a 2024"],
    ["Sistema de Informações Hospitalares", "Autorizações de internação hospitalar: município de residência, município de atendimento, estabelecimento, diagnóstico principal, dias de permanência, óbito e valor pago", "2021 a 2024"],
    ["Sistema de Informação de Agravos de Notificação", "Notificações de dengue: semana epidemiológica dos primeiros sintomas, classificação final, evolução e município de residência", "2015 a 2025"],
    ["Sistema de Informações sobre Nascidos Vivos", "Nascimentos: peso ao nascer, semanas de gestação, consultas de pré-natal e idade materna", "2021 a 2024"],
    ["Programa Nacional de Imunizações, alimentado pela Rede Nacional de Dados em Saúde", "Doses aplicadas em registro individual pseudonimizado: município de residência, município do estabelecimento, imunobiológico, tipo de dose, idade, sexo e raça ou cor", "2023 ao mês corrente"],
    ["Cadastro Nacional de Estabelecimentos de Saúde", "Estabelecimentos e leitos, incluindo leitos disponíveis ao Sistema Único de Saúde", "2015 a 2024"],
    ["Sistema de Informações sobre Orçamentos Públicos em Saúde", "Indicadores municipais de gasto público em saúde", "2021 a 2024"],
    ["e-Gestor Atenção Básica, da Secretaria de Atenção Primária à Saúde", "Cobertura potencial da atenção primária e número de equipes credenciadas por município", "2024"],
    ["Agência Nacional de Saúde Suplementar", "Beneficiários de planos privados por município, usados para testar se a cobertura privada explica parte do padrão observado", "2021 a 2024"],
    ["Instituto Brasileiro de Geografia e Estatística", "População municipal por ano, estrutura etária do Censo de 2022 e indicadores usados na construção do índice de vulnerabilidade", "2015 a 2024"],
  ],
  [2600, 4600, 1600]));
add(P("Duas observações importantes sobre as fontes. A primeira: os arquivos do Ministério da Saúde são reescritos depois de publicados — uma competência recebe registros atrasados, correções de causa e reclassificações, sem aviso. A segunda: o ano mais recente de qualquer sistema é preliminar. A plataforma trata as duas como fatos operacionais, não como imprevistos, e a arquitetura descrita na seção 6 existe em boa parte por causa disso.", { suave: true }));

add(P("A décima fonte, a de vacinação, merece uma observação à parte, porque ilustra o critério que governa toda a plataforma. Dela seria natural derivar cobertura vacinal por município, que é o indicador que gestores procuram. Essa tabela foi construída, testada e reprovada: a correlação entre dois anos consecutivos ficou em zero vírgula cinquenta e nove, e a cobertura mediana cai de cento e dois vírgula sete por cento nos municípios com cinquenta a cem nascidos para oitenta e seis vírgula dois por cento nos com mais de cinco mil. Ruído não tem direção, e portanto isso é viés sistemático de denominador. A hipótese mais provável — descasamento entre o município onde a dose foi registrada e o município onde o nascimento foi declarado — foi medida e refutada, com correlação de zero vírgula zero zero dois. O que se publica, então, é contagem de doses por município, que não depende de denominador, e cobertura apenas por unidade da federação. O critério foi fixado antes de olhar o resultado.", { suave: true }));

add(H2("3. O que a plataforma publica"));
add(P("São quarenta e seis tabelas, somando dezesseis milhões setecentas e noventa e cinco mil setecentas e setenta e cinco linhas em setenta e cinco megabytes de formato colunar. Elas se organizam em quatro famílias."));
add(H3("3.1 Mortalidade"));
add(LI([{ t: "Mortalidade municipal", forte: true }, { t: " — município por ano por capítulo da Classificação Internacional de Doenças por sexo, com taxa bruta, intervalo de confiança de noventa e cinco por cento e taxa padronizada por idade." }]));
add(LI([{ t: "Mortalidade por unidade da federação e mês", forte: true }, { t: " — a série mensal que sustenta o cálculo de excesso de mortalidade." }]));
add(LI([{ t: "Mortalidade por causa", forte: true }, { t: " — unidade da federação por ano por causa básica em três caracteres." }]));
add(LI([{ t: "Excesso de mortalidade", forte: true }, { t: " — observado menos esperado, por unidade da federação e mês, a partir de 2020." }]));
add(LI([{ t: "Mortalidade infantil", forte: true }, { t: " — óbitos de menores de um ano por mil nascidos vivos, por unidade da federação." }]));
add(H3("3.2 Assistência hospitalar"));
add(LI([{ t: "Internações por município", forte: true }, { t: " — município por ano por capítulo diagnóstico, com permanência média, mortalidade hospitalar, custo médio e taxa por cem mil habitantes." }]));
add(LI([{ t: "Internações por agravo traçador", forte: true }, { t: " — onze grupos de condições acompanhadas separadamente: diabetes, doença cerebrovascular, infarto agudo do miocárdio, insuficiência cardíaca, asma, doença pulmonar obstrutiva crônica, pneumonia, depressão, esquizofrenia, transtornos por álcool e outras drogas, e traumatismo cranioencefálico." }]));
add(LI([{ t: "Internações por condições sensíveis à atenção primária", forte: true }, { t: " — aproximação da Lista Brasileira, no nível de três caracteres da Classificação Internacional de Doenças, por município de residência e ano." }]));
add(LI([{ t: "Fluxo intermunicipal de pacientes", forte: true }, { t: " — pares de município de residência e município de atendimento com pelo menos cinco internações, o que permite ver para onde a população de cada cidade se desloca." }]));
add(LI([{ t: "Visão hospitalar", forte: true }, { t: " — razão de mortalidade hospitalar padronizada, tempo de permanência comparado à mediana nacional por diagnóstico, e demanda mensal por estabelecimento." }]));
add(LI([{ t: "Previsão de demanda", forte: true }, { t: " — projeção de internações para os três meses seguintes, por estabelecimento, com intervalo calibrado empiricamente." }]));
add(H3("3.3 Vigilância e atenção primária"));
add(LI([{ t: "Dengue por semana epidemiológica", forte: true }, { t: " — casos prováveis, casos graves e óbitos, por município e semana." }]));
add(LI([{ t: "Cobertura da atenção primária", forte: true }, { t: " — cobertura potencial publicada pela Secretaria de Atenção Primária à Saúde, cruzada com desfechos." }]));
add(LI([{ t: "Leitos e vazio assistencial", forte: true }, { t: " — oferta local de leitos do Sistema Único de Saúde e sua relação com internações sensíveis." }]));
add(LI([{ t: "Equidade e saúde suplementar", forte: true }, { t: " — testes de associação entre vulnerabilidade social, cobertura privada e desfechos." }]));
add(H3("3.4 Dimensões de apoio"));
add(P("Municípios, população total por ano, população por faixa etária, população padrão para padronização, capítulos e categorias da Classificação Internacional de Doenças, e o índice de vulnerabilidade social construído a partir do Censo de 2022."));

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("4. Os métodos epidemiológicos"));

add(H3("4.1 Padronização por idade"));
add(P("Comparar a mortalidade de duas cidades sem ajustar pela estrutura etária compara a idade das populações, não o risco de morrer. A plataforma aplica padronização direta, usando como padrão a população brasileira do Censo de 2022 dividida em nove faixas etárias. Óbitos com idade ignorada são redistribuídos proporcionalmente dentro do próprio município e ano, e não descartados."));
add(P("Para os anos diferentes de 2022, a estrutura etária do Censo é escalada pelo total municipal daquele ano. É uma aproximação, e está declarada como tal na metodologia publicada.", { suave: true }));

add(H3("4.2 Intervalo de confiança pelo método gama"));
add(P("Contagens de óbitos em municípios pequenos são baixas, e a aproximação normal produz intervalos irreais nesse regime — às vezes com limite inferior negativo. A plataforma usa o método gama, que é o intervalo exato para contagem de Poisson, em toda taxa bruta publicada."));

add(H3("4.3 Excesso de mortalidade"));
add(P("Excesso de mortalidade é a diferença entre os óbitos observados e os óbitos que seriam esperados na ausência do evento em estudo. Toda a dificuldade está em definir o esperado."));
add(P("O método mais comum toma a média histórica de cada mês e a escala pela razão entre a população do ano-alvo e a população do período de referência. Esse método herda integralmente qualquer erro da projeção populacional."));
add(P("A plataforma substituiu esse baseline por uma tendência linear por mês civil, ajustada por mínimos quadrados aos cinco pontos de 2015 a 2019 e projetada para o ano-alvo, por unidade da federação e para o Brasil. A vantagem decisiva é que esse método se apoia apenas nos óbitos observados, sem usar população em nenhum ponto do cálculo."));
add(P([{ t: "A análise de sensibilidade que motivou a escolha: " },
       { t: "uma variante padronizada por idade estima o excesso pandêmico em aproximadamente quinhentos e cinco mil óbitos, enquanto o método de tendência estima seiscentos e quarenta e três mil.", forte: true },
       { t: " A diferença não é preferência metodológica. A projeção populacional de 2018 superestima a população brasileira, e a série publicada após o Censo de 2022 introduz uma descontinuidade na série. A padronização por idade herda os dois problemas pelo denominador e, por isso, subestima o excesso." }]));

add(H3("4.4 Razão de mortalidade hospitalar padronizada"));
add(P("A razão de mortalidade hospitalar padronizada compara os óbitos observados em um hospital com os óbitos esperados, dado o perfil de casos que ele atende. A plataforma usa padronização indireta por faixa etária cruzada com capítulo diagnóstico, de modo que um hospital que atende casos mais graves não seja penalizado por isso."));
add(P("Três decisões metodológicas importam aqui. A primeira: o intervalo de confiança é calculado pelo método gama de Poisson, pelo mesmo motivo da seção 4.2. A segunda: autorizações de internação de continuação, que registram a mesma internação prolongada em várias linhas, são excluídas do cálculo, porque inflariam o denominador com linhas de mortalidade quase nula. A terceira, e a mais consequente: como se comparam cerca de dez mil hospitais simultaneamente, aplica-se correção da taxa de descobertas falsas."));
add(P([{ t: "O efeito da correção é grande: " },
       { t: "duzentos e oitenta e dois hospitais, de dez mil e quarenta e seis, perdem significância estatística quando ela é aplicada.", forte: true },
       { t: " Sem a correção, esses hospitais entrariam em um relatório público como tendo mortalidade acima do esperado sem que houvesse evidência para isso. A calibração nacional do modelo é de exatamente um inteiro nos três anos analisados, o que significa que o total de óbitos esperados reproduz o total observado." }]));

add(H3("4.5 Internações por condições sensíveis à atenção primária"));
add(P("São internações que, em tese, poderiam ter sido evitadas por uma atenção primária efetiva: pneumonia bacteriana, desidratação por gastroenterite, descompensação de insuficiência cardíaca, crise asmática, entre outras. A plataforma implementa uma aproximação da Lista Brasileira no nível de três caracteres da Classificação Internacional de Doenças, agrupada por município de residência e ano."));
add(P("O indicador é publicado de duas formas, e a distinção é relevante para os achados: a taxa por cem mil habitantes, que depende do acesso hospitalar geral do município, e a proporção sobre o total de internações do próprio município, que remove esse confundimento."));

add(H3("4.6 Fluxo intermunicipal e tempo de permanência"));
add(P("O fluxo intermunicipal aproveita o fato de que a autorização de internação registra tanto o município de residência quanto o município de atendimento. Pares com pelo menos cinco internações no ano são publicados, o que revela a rede real de deslocamento de pacientes. O tempo de permanência é comparado à mediana nacional daquele diagnóstico específico, e não a uma média geral, para que a comparação entre hospitais não seja dominada pelo perfil de casos."));

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("5. O modelo de previsão e como ele foi validado"));
add(P("A plataforma publica previsão de internações para os três meses seguintes, por estabelecimento. O que distingue esse componente não é o modelo, que é deliberadamente simples, e sim o regime de validação a que ele foi submetido."));
add(H3("5.1 O desenho da validação"));
add(P("A validação usa origem móvel: o modelo é treinado apenas com os dados anteriores a cada ponto de corte e avaliado no que vem depois, repetidamente ao longo da série. Nenhuma informação do futuro entra no treino, incluindo o denominador da métrica de erro e o fator de calibração do intervalo. Foram avaliados quatro mil quatrocentos e quarenta e cinco hospitais."));
add(H3("5.2 A métrica e o resultado"));
add(P("A régua é o erro absoluto médio escalonado, que divide o erro do modelo pelo erro de um modelo ingênuo sazonal calculado dentro do período de treino. Valor abaixo de um significa superar esse modelo ingênuo."));
add(tabela(
  ["Horizonte", "Erro escalonado do modelo publicado", "Leitura"],
  [["Um mês", "0,810", "supera o ingênuo em cerca de dezenove por cento"],
   ["Dois meses", "0,867", "supera o ingênuo em cerca de treze por cento"],
   ["Três meses", "0,922", "supera o ingênuo em cerca de oito por cento"]],
  [1900, 3400, 3500]));
add(H3("5.3 Os dois resultados que contrariaram a expectativa"));
add(P([{ t: "O primeiro: modelos sazonais, mais sofisticados, saíram piores.", forte: true },
       { t: " O erro escalonado deles ficou entre um vírgula zero três e um vírgula onze, ou seja, piores que o modelo ingênuo. No agregado nacional eles pareciam melhores, e foi a avaliação por unidade que revelou o contrário. A sazonalidade existe no Brasil inteiro somado, mas não se transfere para a série de um hospital específico." }]));
add(P([{ t: "O segundo: o intervalo declarado como de noventa e cinco por cento cobria de fato oitenta e cinco por cento das observações.", forte: true },
       { t: " Em vez de manter a suposição de normalidade, o fator do intervalo foi recalibrado empiricamente a partir da própria distribuição de erros observada, resultando em dois vírgula quarenta e dois, dois vírgula sessenta e quatro e dois vírgula oitenta para os horizontes de um, dois e três meses." }]));
add(NOTA("Os dois resultados foram publicados, e o segundo levou a plataforma a corrigir um intervalo que estava estreito demais desde o início. Uma validação que nunca reprova nada não está validando."));

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("6. A arquitetura de dados"));
add(H3("6.1 O eixo canônico"));
add(P("Até agosto de 2026, a camada canônica de fato era o banco de dados: os pipelines escreviam nele, o site lia dele, e o arquivo era subproduto. Isso tinha três consequências ruins. O banco não era reconstruível a partir do repositório; não havia histórico, porque cada publicação sobrescrevia a anterior; e a cobertura de arquivos publicados era parcial."));
add(P("O eixo foi invertido. Hoje o arquivo colunar datado é a verdade, e o banco é uma cópia para consulta, reconstruível a qualquer momento. Se as duas camadas divergirem, o arquivo está certo e o banco precisa ser recarregado — nunca o contrário."));
add(H3("6.2 Publicação imutável e manifesto"));
add(P("Cada publicação é um conjunto imutável de arquivos mais um manifesto que os descreve: por tabela, o número de linhas, o tamanho em bytes, o resumo criptográfico, as colunas, a faixa de competência coberta e a procedência. O manifesto é versionado no controle de versão; os arquivos ficam em armazenamento público, com um caminho estável para o estado atual e um caminho histórico imutável para cada publicação."));
add(P("Uma tabela que não muda entre duas publicações não duplica bytes: o manifesto novo aponta para a publicação em que ela mudou pela última vez. O resultado é que o histórico de publicações constitui, por construção, uma série temporal de instantâneos do que cada número valia em cada data."));
add(H3("6.3 Linhagem gravada nos bytes"));
add(P("Cada arquivo declara, nos próprios metadados internos, quem o produziu e de qual versão da fonte veio. Isso resolve um problema concreto: um arquivo exportado do banco e um arquivo gerado pelo pipeline são visualmente idênticos, e sem essa marca o manifesto afirmaria uma procedência que ninguém verificou."));
add(P("A escala de procedência tem quatro valores. O valor desejado é indicar que o arquivo saiu do pipeline que gera o dado. Os demais registram dívida declarada: reexportado do banco, publicado manualmente antes de existir pipeline de publicação, ou procedência desconhecida. Um quinto valor identifica visões do banco, que não têm produtor de arquivo por natureza."));
add(P([{ t: "A evolução dessa medida ao longo do trabalho descrito neste documento: de doze tabelas com procedência de pipeline para " },
       { t: "quarenta e cinco de quarenta e seis", forte: true },
       { t: ". As categorias de reexportação do banco, de publicação manual anterior ao pipeline e de procedência desconhecida foram todas zeradas: a única tabela que não declara produtor é a visão, que por natureza não tem arquivo próprio." }]));

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("7. As guardas de integridade"));
add(P("Esta seção descreve a parte do trabalho que tem menos visibilidade e mais consequência. Cada guarda descrita aqui nasceu de um defeito real que as anteriores não detectaram."));
add(H3("7.1 Por que contar linhas não basta"));
add(P("Uma exportação paginada do banco sem ordenação determinística produziu um arquivo com trezentas e trinta e quatro mil setecentas e sessenta e nove linhas, das quais apenas duzentas e doze mil oitocentas e noventa e três eram chaves distintas: cento e vinte e um mil oitocentas e setenta e seis linhas duplicadas. O total batia exatamente com o banco, porque as linhas repetidas ocuparam o lugar das que faltaram."));
add(P("A lição é geral: contagem de linhas não detecta corrupção, porque duplicata e ausência se cancelam no total. E o resumo criptográfico prova que o arquivo não mudou depois de escrito, não que ele foi escrito corretamente."));
add(P("Daí as três guardas aplicadas antes de qualquer publicação: contagem contra a fonte, unicidade da chave primária, e verificação das colunas obrigatórias do destino. As três leem o contrato do esquema versionado, não uma lista escrita à mão. A guarda mais forte, porém, é recarregar: um arquivo que não recarrega no esquema que diz representar não é cópia canônica. Isso roda em integração contínua, com banco descartável — cinco vírgula três milhões de linhas em trinta e oito tabelas, em pouco mais de um minuto."));
add(H3("7.2 O defeito mais sério encontrado: ausência confundida com falha"));
add(P("Os cinco pipelines que coletam dados hospitalares e de nascidos vivos tinham a mesma forma: qualquer exceção durante o download de um arquivo mensal era tratada como se aquela competência não existisse. Recusa de conexão, tempo esgotado e arquivo corrompido produziam exatamente o mesmo resultado que um mês ainda não publicado."));
add(P("O servidor de arquivos do Ministério da Saúde recusa conexões concorrentes, e o pipeline abria seis. Meses inteiros desapareciam, o checkpoint era gravado como se o ano estivesse completo, e — por ser checkpoint — nunca era refeito. A perda ficava congelada."));
add(tabela(
  ["Recorte afetado", "Perda medida", "Causa"],
  [["Maranhão, 2023", "menos quarenta e um por cento das internações", "cinco meses perdidos"],
   ["Amazonas, 2024", "menos dezessete por cento", "dois meses"],
   ["Paraíba, 2022", "menos dezoito por cento", "maio e junho"],
   ["Pernambuco, 2022", "menos oito por cento", "novembro"],
   ["Goiás, 2023", "menos oito por cento", "fevereiro"],
   ["Roraima, 2022", "menos sete por cento", "um mês"]],
  [2600, 3400, 2800]));
add(P([{ t: "Nenhuma dessas perdas disparou alarme: os pipelines terminaram com código de saída zero e imprimiram números plausíveis. O efeito visível para o público foi grande — as internações do Maranhão em 2023 subiram de duzentas e noventa e três mil duzentas e quarenta e três para " },
       { t: "quatrocentas e noventa e uma mil trezentas e cinquenta e cinco", forte: true },
       { t: " depois da correção, um aumento de sessenta e sete vírgula seis por cento." }]));
add(H3("7.3 O que foi construído para impedir a repetição"));
add(LI([{ t: "Ausência e falha são exceções diferentes. ", forte: true }, { t: "Uma indica competência ainda não publicada, e pular é correto; a outra indica que o arquivo existe e a coleta falhou, e abortar é correto." }]));
add(LI([{ t: "A lista de meses vem da fonte. ", forte: true }, { t: "O pipeline consulta a listagem do diretório remoto em vez de assumir doze meses, o que também faz a competência nova entrar sozinha." }]));
add(LI([{ t: "O ano só fecha completo. ", forte: true }, { t: "O que falha em paralelo é refeito em série, e se ainda faltar um mês publicado o pipeline levanta exceção sem gravar checkpoint." }]));
add(LI([{ t: "O checkpoint declara de onde veio. ", forte: true }, { t: "Ele carimba, nos próprios metadados, quais meses o produziram; nas bases anuais, carimba a versão do arquivo de origem. Um checkpoint que não cobre o que a fonte publica hoje é recalculado sozinho." }]));
add(LI([{ t: "Conferência cruzada entre famílias independentes. ", forte: true }, { t: "Duas famílias de checkpoint leem os mesmos arquivos de origem por caminhos diferentes; os totais têm que bater exatamente. Batem nos oitenta e um recortes comparados." }]));
add(H3("7.4 A reconstrução total"));
add(P("Para transformar a conferência cruzada, que é inferência, em prova direta, os trezentos e cinquenta e um recortes de unidade da federação por ano das quatro famílias hospitalares foram refeitos do zero: cada arquivo mensal baixado novamente, sem reaproveitar nenhum estado anterior. Foram cerca de doze horas de coleta."));
add(P([{ t: "Resultado: quatrocentos e cinquenta e nove de quatrocentos e cinquenta e nove checkpoints idênticos ao estado anterior, e oito de oito tabelas derivadas com conteúdo idêntico ao publicado. ", forte: true },
       { t: "Ou seja, fora os seis recortes corrigidos, não havia outra perda silenciosa na base. O mesmo exercício foi repetido para a dengue, com dezesseis vírgula sete milhões de registros relidos, e para o sistema de mortalidade, com cento e oitenta e nove arquivos estaduais e três arquivos nacionais: em ambos, reprodução exata." }]));

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("8. Qualidade de software e automação"));
add(LI([{ t: "Quinhentos e quarenta e sete testes automatizados", forte: true }, { t: ", executados a cada envio de código, cobrindo desde o cálculo de intervalo de confiança até as guardas de integridade e a coleta." }]));
add(LI([{ t: "Reconstrução do banco a partir do zero em integração contínua", forte: true }, { t: ", contra um banco descartável, provando que o repositório reproduz o ambiente publicado." }]));
add(LI([{ t: "Esquema do banco versionado e conferido automaticamente", forte: true }, { t: ": duzentos e um objetos, com detecção de divergência entre o que está no repositório e o que está em produção." }]));
add(LI([{ t: "Verificação de tamanho do banco", forte: true }, { t: ", porque cada carga incremental deixa espaço morto; a faxina periódica reduziu o banco de setecentos e quarenta para cerca de seiscentos megabytes." }]));
add(LI([{ t: "Observação diária das fontes", forte: true }, { t: ": uma rotina automática registra o tamanho e a data de cada arquivo remoto, o que permite detectar quando o Ministério reescreve um arquivo já publicado." }]));
add(LI([{ t: "Proteção do ramo principal", forte: true }, { t: " contra exclusão e reescrita de histórico, sem exigir revisão por pares — porque duas rotinas automáticas publicam diretamente e a exigência as quebraria." }]));
add(P("Um episódio dessa frente merece registro, porque ilustra um padrão. Ao configurar a credencial que faltava para o serviço de integração contínua, uma verificação que vivia marcada como “pulada” executou pela primeira vez — e falhou imediatamente, por falta de uma dependência. Ela estava quebrada desde que foi escrita, e ninguém podia saber, porque nunca havia executado. Verificação que não roda não é verificação que passa.", { suave: true }));

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("9. Os achados científicos"));
add(H3("9.1 A cobertura potencial da atenção primária mede porte populacional"));
add(P("A cobertura potencial da atenção primária é o indicador oficial mais usado para avaliar a extensão da atenção básica no país: a capacidade de atendimento estimada das equipes credenciadas dividida pela população do município. A hipótese testada foi simples — se ela mede o que diz medir, deveria associar-se negativamente às internações que a atenção primária deveria evitar."));
add(P([{ t: "Ela ultrapassa cem por cento em oitenta e seis vírgula um por cento dos municípios, com mediana de cento e quarenta e nove vírgula um por cento e máximo de oitocentos e três vírgula vinte e um por cento. Correlaciona-se fortemente com o porte populacional, com coeficiente de menos zero vírgula cinquenta e quatro, e " },
       { t: "não se correlaciona com as internações sensíveis", forte: true },
       { t: ": zero vírgula zero zero dois na correlação bruta e zero vírgula zero dezessete controlando porte e vulnerabilidade." }]));
add(P("Municípios com menos de dez mil habitantes têm, ao mesmo tempo, a maior cobertura mediana e a maior taxa de internações sensíveis — exatamente o oposto do que a lógica do indicador prevê. O achado sobrevive a um desenho mais estrito: trocando o percentual por densidade real de equipes por dez mil habitantes, trocando a taxa por proporção sobre o total de internações do próprio município, e comparando cada município apenas aos pares do seu quartil de porte, a correlação fica entre menos zero vírgula zero dois e zero vírgula dezoito."));
add(H3("9.2 A oferta local de leitos induz a internação que o indicador mede"));
add(P("Este é o achado mais forte da sequência, e ele derrubou uma afirmação que a própria metodologia da plataforma carregava sem nunca ter testado. A afirmação antiga era que, onde faltam leitos, a internação eletiva desaparece e a fatia de internações sensíveis sobe mecanicamente — o que prevê menos leitos e mais internações sensíveis."));
add(P("Os dados mostram o contrário, e por outro mecanismo. A correlação entre leitos do Sistema Único de Saúde por mil habitantes e proporção de internações sensíveis é de mais zero vírgula trinta e dois bruta, mais zero vírgula trinta e quatro controlando porte e vulnerabilidade, e entre mais zero vírgula dezesseis e mais zero vírgula quarenta e sete dentro de cada quartil de porte — positiva nos quatro. Municípios sem leito local têm proporção menor, dezessete vírgula oito por cento, do que os com leito, vinte e um vírgula cinco por cento."));
add(P("O teste decisivo foi decompor as internações por habitante, separando o que é sensível do que não é:"));
add(tabela(
  ["Quartil de porte", "Internações sensíveis por cem mil", "Internações não sensíveis por cem mil"],
  [["Segundo quartil", "de 1.156 para 1.745, mais cinquenta e um por cento", "de 5.483 para 5.887, mais sete por cento"],
   ["Terceiro quartil", "de 961 para 1.782, mais oitenta e cinco por cento", "de 5.145 para 5.728, mais onze por cento"],
   ["Quarto quartil", "de 877 para 1.343, mais cinquenta e três por cento", "de 5.604 para 5.571, menos um por cento"]],
  [2200, 3300, 3300]));
add(P("A comparação, em cada linha, é entre municípios sem leito local e municípios com leito local do mesmo quartil de porte. O efeito está quase todo no numerador: não é a internação eletiva que desaparece por falta de leito, é a internação sensível que aparece quando há leito na cidade. Pneumonia, desidratação e descompensação de insuficiência cardíaca são precisamente o que um hospital de pequeno porte interna; sem leito local, esses casos são resolvidos em ambulatório ou não se deslocam, enquanto o caso complexo se desloca de qualquer forma."));
add(NOTA("Implicação de política pública: um município que abre um hospital de pequeno porte vê sua proporção de internações sensíveis subir e, pela leitura convencional de que internação sensível alta significa atenção básica fraca, seria classificado como tendo piorado. Insumo e desfecho medem característica do município, não desempenho da assistência."));
add(P("Ressalva declarada em toda a saída: as internações são contadas por município de residência e os leitos por município do estabelecimento. “Sem leito” significa sem oferta local, não sem acesso — o morador interna em outra cidade e a internação é atribuída à residência dele. O efeito opera por barreira de deslocamento.", { suave: true }));
add(H3("9.3 O resultado nulo de equidade"));
add(P("A proporção de internações sensíveis por quartil de vulnerabilidade social é de dezenove vírgula um, vinte e um vírgula um, vinte vírgula seis e dezenove vírgula oito por cento — praticamente plana. A co-ocorrência de baixa densidade de equipes com alta proporção de internações sensíveis é zero vírgula noventa e quatro vezes o esperado ao acaso, ou seja, abaixo do acaso."));
add(P("O resultado é apresentado como nulo, e não como tendência fraca. Um resultado nulo bem medido é informação sobre o indicador: se tanto o insumo quanto o desfecho medem porte e oferta, a desigualdade que existe no território simplesmente não aparece neles."));

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("10. Publicação, licenças e reprodutibilidade"));
add(LI("Dado agregado sob licença Creative Commons Atribuição, versão quatro ponto zero."));
add(LI("Código-fonte sob a licença do Instituto de Tecnologia de Massachusetts."));
add(LI("Identificador digital de objeto de conceito: dez ponto cinco dois oito um barra zenodo ponto dois zero sete zero seis oito quatro cinco."));
add(LI("Resumo criptográfico de cada arquivo publicado, exibido na própria página de dados, lido do manifesto no momento da construção do site."));
add(LI("Interface de programação de aplicações pública, sem necessidade de cadastro, servida diretamente sobre o banco de consulta."));
add(LI("Servidor de contexto para modelos de linguagem, publicado no repositório oficial de pacotes da linguagem Python, que dá acesso citável aos indicadores."));
add(LI("Dois manuscritos em preparação: uma nota de métodos sobre a plataforma e o baseline de excesso de mortalidade, e uma nota de pesquisa sobre a cobertura potencial da atenção primária."));
add(LI("Custo de infraestrutura igual a zero: a plataforma opera inteiramente dentro de camadas gratuitas de serviços de nuvem."));

add(H2("11. Limites declarados"));
add(LI([{ t: "Desenho ecológico. ", forte: true }, { t: "Todas as associações são entre municípios. Correlação municipal não é efeito individual, e nenhum dos achados sustenta inferência sobre pessoas." }]));
add(LI([{ t: "Unidades de contagem diferentes. ", forte: true }, { t: "As internações são contadas por município de residência e os leitos por município do estabelecimento." }]));
add(LI([{ t: "Dado preliminar. ", forte: true }, { t: "O ano mais recente de cada sistema está sujeito a revisão pelo Ministério da Saúde." }]));
add(LI([{ t: "Índice de vulnerabilidade aproximado. ", forte: true }, { t: "É construído com dois indicadores do Censo de 2022 e não é o índice oficial do Instituto de Pesquisa Econômica Aplicada, que usa dezesseis indicadores." }]));
add(LI([{ t: "Classificação municipal por agrupamento suspensa. ", forte: true }, { t: "A estabilidade do agrupamento foi medida e reprovada: a silhueta cai a partir de dois grupos, o que indica ausência de estrutura natural de grupos, e o índice de Rand ajustado entre reamostragens ficou em zero vírgula quinhentos e setenta e um. A publicação foi congelada até ser substituída por estratificação determinística." }]));
add(LI([{ t: "Uma tabela sem produtor. ", forte: true }, { t: "A tabela de qualidade de registro é servida pela interface pública, mas nenhum script do repositório a gera. Ela permanece marcada como legado, que é o rótulo honesto para essa situação." }]));

add(H2("12. O que vem a seguir"));
add(P("Quatro frentes estão desenhadas e não iniciadas. A primeira, e a mais próxima de existir: publicar separadamente o grupo de internações por condições preveníveis por vacinação — coqueluche, difteria, tétano, sarampo, rubéola, hepatite B, caxumba, febre amarela, meningite e tuberculose. Os códigos já estão no pipeline; falta publicá-los como recorte próprio. Isso daria um desfecho populacional de impacto vacinal por município e ano, cruzável com cobertura vacinal e vulnerabilidade."));
add(P("A segunda: usar o histórico de publicações para medir quanto um número preliminar ainda se move entre uma leitura da fonte e a seguinte — pergunta que nenhuma fonte pública brasileira responde hoje. A terceira: incorporar o sistema de vigilância de síndrome respiratória aguda grave. A quarta: substituir o agrupamento municipal suspenso por estratificação determinística, com cortes congelados e versionados."));

// ══════════════════════════ PARTE II ══════════════════════════
add(new Paragraph({ children: [new PageBreak()] }));
add(H1("Parte II — A apresentação, slide a slide"));
add(P("Esta parte explica como a apresentação foi construída, o que cada slide faz, o que dizer em voz alta e o que esperar de pergunta. Ela é o roteiro; a apresentação é o apoio visual."));

add(H2("13. As decisões de construção"));
add(H3("13.1 Interlocutor e objetivo"));
add(P("A apresentação foi calibrada para o doutor Helder Nakaya: pesquisador sênior do Hospital Israelita Albert Einstein, professor da Faculdade de Ciências Farmacêuticas da Universidade de São Paulo, professor adjunto na Universidade Emory, consultor da Coalizão para Inovações em Preparação para Epidemias e da União Internacional das Sociedades de Imunologia. É um dos fundadores da vacinologia de sistemas, com índice h de sessenta e seis e cerca de vinte e cinco mil citações. O laboratório que ele lidera declara atuar em imunologia computacional, medicina de precisão e epidemiologia digital."));
add(P("O objetivo assumido foi colaboração científica, em formato de seminário de vinte minutos. Se o objetivo mudar, apenas o último slide precisa ser reescrito — ele foi mantido isolado exatamente por isso."));
add(H3("13.2 Por que a apresentação abre pelo achado, e não pela plataforma"));
add(P("Um pesquisador sênior decide nos primeiros noventa segundos se está diante de ciência ou de demonstração de produto. Abrir pela ferramenta convida à segunda leitura. Por isso a apresentação abre com o achado que contraria a intuição, e a plataforma só aparece no oitavo slide, apresentada como a condição que tornou o achado possível."));
add(H3("13.3 Por que os resultados nulos têm o mesmo peso"));
add(P("Três dos achados são nulos ou contrários à hipótese inicial. Eles foram apresentados com a mesma firmeza dos positivos, sem suavização para “tendência”. Para o público-alvo, essa escolha é sinal de método, não de fraqueza do trabalho."));
add(H3("13.4 As decisões visuais"));
add(P("Uma ideia por slide. Uma única cor de destaque, reservada exclusivamente aos números que carregam um achado, de modo que o olho vá direto para eles em projeção. Tipografia serifada nos títulos e sem serifa no corpo, com figuras alinhadas nas tabelas. Slides escuros apenas na abertura e no encerramento, o que delimita a apresentação sem exigir transições."));

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("14. O roteiro, slide a slide"));

const ROTEIRO = [
  ["1. Capa", "Título, subtítulo e vinculação institucional.",
   "Diga o título em voz alta e explique que ele é literal, não metafórico: a apresentação vai mostrar que a oferta de leito cria a internação que se usa para julgar a atenção primária. Trinta segundos."],
  ["2. O problema", "O microdado é público há décadas; o indicador reprodutível, não.",
   "Não fale da plataforma ainda. Estabeleça que o problema não é disponibilidade de dado, e sim a distância entre o arquivo bruto e o indicador que outra pessoa consegue reproduzir. Um minuto."],
  ["3. Achado um, montagem", "A hipótese antiga e as quatro medidas de correlação.",
   "Enuncie a hipótese convencional primeiro, com clareza, para que a inversão tenha efeito. Depois mostre que a correlação é positiva e sobrevive a todos os controles. Dois minutos."],
  ["4. Achado um, o teste decisivo", "A tabela que separa numerador de denominador.",
   "Este é o slide que sustenta a apresentação. Fique em silêncio enquanto ele lê a tabela. Depois diga apenas a frase-chave: o efeito está quase todo no numerador. Dois minutos."],
  ["5. Achado um, implicação", "A consequência para política pública.",
   "Aqui está o argumento que interessa a quem faz avaliação de sistemas de saúde: insumo e desfecho medem característica do município. Pause depois de dizer isso. Um minuto e meio."],
  ["6. Achado dois", "A cobertura potencial da atenção primária mede porte.",
   "Apresente como achado irmão do primeiro, não como item novo de lista. É o outro lado da mesma equação. Dois minutos."],
  ["7. Achado três", "O resultado nulo de equidade.",
   "Diga explicitamente que é um resultado nulo e que ele é informativo. Não suavize. Um minuto e meio."],
  ["8. A plataforma", "Escala, fontes, custo zero, licenças e identificador permanente.",
   "Agora sim a ferramenta, e apresentada como consequência. O dado de custo zero costuma surpreender; registre sem vender. Dois minutos."],
  ["9. Excesso de mortalidade", "O baseline imune ao erro do denominador.",
   "Ponto metodológico transferível: qualquer análise escalada por população herda o erro da projeção. É um bom assunto entre pares. Dois minutos."],
  ["10. Razão de mortalidade hospitalar", "Intervalo exato e correção de múltiplas comparações.",
   "Se houver pergunta sobre estatística, ela virá aqui. O número a destacar é o dos duzentos e oitenta e dois hospitais que perdem significância com a correção. Dois minutos."],
  ["11. Previsão validada", "O backtest que reprovou o modelo preferido.",
   "Demonstra cultura de validação. Diga que os modelos sazonais pareciam melhores no agregado e saíram piores por unidade. Dois minutos."],
  ["12. Integridade da coleta", "A perda silenciosa encontrada e fechada.",
   "Apresente como tese metodológica, nunca como confissão. A frase a fixar: contagem de linhas não detecta corrupção, porque duplicata e ausência se cancelam. Dois minutos."],
  ["13. Proveniência", "Linhagem nos bytes, publicação imutável, checkpoint que se autoinvalida.",
   "Conecte com a pergunta de quanto um preliminar ainda se move — interessa a quem trabalha com dado que é revisado. Um minuto e meio."],
  ["14. Limites", "O que a plataforma não pode afirmar.",
   "Declare antes que perguntem. Inclua a classificação por agrupamento suspensa: mostrar que você mediu e congelou constrói mais credibilidade do que qualquer resultado positivo. Um minuto e meio."],
  ["15. Futuro", "As quatro frentes, com o gancho vacinal em primeiro lugar.",
   "Deixe explícito que o recorte de causas imunizáveis ainda não existe. É convite, não entrega. Um minuto e meio."],
  ["16. Encerramento", "A pergunta.",
   "Faça a pergunta e cale. Não preencha o silêncio. Trinta segundos."],
];
ROTEIRO.forEach(([t, o, d]) => {
  add(new Paragraph({ spacing: { before: 260, after: 60 },
    children: [new TextRun({ text: t, font: SANS, size: 22, bold: true, color: INDIGO })] }));
  add(P([{ t: "O que mostra: ", forte: true }, { t: o }], { after: 70 }));
  add(P([{ t: "O que dizer: ", forte: true }, { t: d }], { suave: true }));
});

add(new Paragraph({ children: [new PageBreak()] }));
add(H2("15. Perguntas prováveis, e como respondê-las"));
const PERGUNTAS = [
  ["“Isso não é apenas viés de detecção?”",
   "Em parte, e é justamente esse o argumento. O ponto não é que os municípios com leito adoeçam mais, e sim que o indicador registra a internação que ocorreu, e a internação sensível é a mais discricionária de todas. Por isso a decomposição entre sensível e não sensível importa: se fosse viés geral de detecção, as duas subiriam juntas, e as não sensíveis praticamente não sobem."],
  ["“Por que não usar modelo de regressão em vez de correlação?”",
   "A correlação parcial e a estratificação por quartil de porte foram escolhidas por serem transparentes e verificáveis por qualquer pessoa a partir dos dados publicados. Um modelo multinível é o próximo passo natural e é uma das frentes em que uma colaboração agregaria diretamente."],
  ["“Qual é a granularidade do dado? Dá para chegar ao indivíduo?”",
   "Não. A plataforma trabalha exclusivamente com dado agregado por município, estabelecimento ou unidade da federação. Não há dado identificado, e não há intenção de linkage individual."],
  ["“Como sei que os números não vão mudar amanhã?”",
   "Cada publicação é imutável e datada, com resumo criptográfico e manifesto versionado. O número citado hoje continua recuperável depois, mesmo que a fonte seja revista — e a diferença entre as duas versões é, ela própria, mensurável."],
  ["“Por que a previsão usa um modelo tão simples?”",
   "Porque os modelos mais sofisticados foram testados por origem móvel em quatro mil quatrocentos e quarenta e cinco hospitais e saíram piores por unidade. A simplicidade é resultado de medição, não de limitação."],
  ["“O que você quer de mim?”",
   "Responda com o slide dezesseis, sem rodeio: dizer qual das três frentes é útil ao grupo dele, e qual atacaria primeiro."],
];
PERGUNTAS.forEach(([q, r]) => {
  add(new Paragraph({ spacing: { before: 240, after: 60 },
    children: [new TextRun({ text: q, font: SANS, size: 21, bold: true, color: TINTA })] }));
  add(P(r, { suave: true }));
});

add(H2("16. O que muda se o objetivo da conversa mudar"));
add(P("A apresentação foi montada para colaboração científica. Se o objetivo for orientação ou mentoria, o slide dezesseis deve pedir leitura crítica de um recorte específico — por exemplo, do desenho do teste de leitos — em vez de propor frentes de trabalho. Se for oferecer a plataforma como infraestrutura, o encerramento deve terminar em acesso: interface pública, servidor de contexto e licença. Se for co-autoria, o encerramento deve nomear qual dos dois manuscritos em preparação está mais próximo do interesse dele. Em todos os casos, os quinze slides anteriores permanecem válidos."));

const doc = new Document({
  creator: "Pedro Paulo Fernandes",
  title: "Saúde em Dado — documentação da plataforma e guia da apresentação",
  description: "Parte I: a plataforma. Parte II: a apresentação, slide a slide.",
  numbering: { config: [{ reference: "marcadores", levels: [{
    level: 0, format: LevelFormat.BULLET, text: "▪", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 460, hanging: 240 } } } }] }] },
  styles: { default: { document: { run: { font: SANS, size: 21, color: TINTA } } } },
  sections: [{
    properties: { page: { margin: { top: 1300, right: 1300, bottom: 1300, left: 1300 } } },
    children: conteudo,
  }],
});

Packer.toBuffer(doc).then((b) => {
  const saida = require("path").join(__dirname, "saida", "Saude-em-Dado-documentacao.docx");
  fs.writeFileSync(saida, b);
  console.log("gravado, bytes:", b.length);
});
