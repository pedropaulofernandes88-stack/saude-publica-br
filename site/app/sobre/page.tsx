import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sobre o projeto",
  description:
    "Plataforma aberta e sem fins lucrativos que transforma microdados do SUS em indicadores "
    + "reproduzíveis, publicando a limitação junto do número. Pipeline em código aberto (MIT), "
    + "agregados em CC BY 4.0. Por Pedro Paulo Fernandes.",
  alternates: { canonical: "/sobre/" },
};

export default function Sobre() {
  return (
    <div className="prose-doc mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
        Sobre o Saúde em Dado
      </h1>

      {/* Cartão do autor — posicionamento em 5 segundos */}
      <div className="mt-6 rounded-xl border border-ink-200 bg-ink-50 p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-accent-700">
          Concebido e mantido por
        </p>
        <p className="mt-1 font-serif text-2xl font-semibold text-ink-950">Pedro Fernandes</p>
        <p className="mt-1 text-ink-700">
          Trabalho na interseção de <strong>saúde coletiva</strong>,{" "}
          <strong>inteligência artificial</strong> e <strong>gestão pública</strong> —
          transformando o dado bruto do SUS em evidência que gestor, pesquisador e
          jornalista conseguem usar.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-white p-3 ring-1 ring-ink-200">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Saúde</p>
            <p className="mt-1 text-sm text-ink-800">Mestrando em Saúde Coletiva — IAMSPE</p>
          </div>
          <div className="rounded-lg bg-white p-3 ring-1 ring-ink-200">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">IA &amp; Dados</p>
            <p className="mt-1 text-sm text-ink-800">Pós em IA e Ciência de Dados em Saúde — Hospital Sírio-Libanês</p>
          </div>
          <div className="rounded-lg bg-white p-3 ring-1 ring-ink-200">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Gestão pública</p>
            <p className="mt-1 text-sm text-ink-800">Diretor de TI — Setor Público (SP)</p>
          </div>
        </div>
        <p className="mt-4 text-sm">
          <a href="https://orcid.org/0009-0008-6248-2486" target="_blank" rel="noreferrer" className="font-medium text-accent-700 hover:underline">ORCID</a> ·{" "}
          <a href="http://lattes.cnpq.br/6641343625206093" target="_blank" rel="noreferrer" className="font-medium text-accent-700 hover:underline">Lattes</a> ·{" "}
          <a href="https://www.linkedin.com/in/pedro-f-540154408/" target="_blank" rel="noreferrer" className="font-medium text-accent-700 hover:underline">LinkedIn</a> ·{" "}
          <a href="mailto:pedropaulofernandes88@gmail.com" className="font-medium text-accent-700 hover:underline">e-mail</a>
        </p>
      </div>

      {/* Proof points */}
      <div className="mt-6 grid gap-4 sm:grid-cols-4">
        {[
          ["14,4 mi", "óbitos processados (SIM 2015–2024)"],
          ["10 fontes", "SIM · SIH · SINAN · SINASC · PNI · CNES · SIOPS · e-Gestor AB · ANS · IBGE"],
          ["DOI", "citável e versionado (Zenodo)"],
          ["100%", "pipeline aberto e reproduzível"],
        ].map(([n, d]) => (
          <div key={d} className="rounded-lg border border-ink-200 p-4 text-center">
            <p className="font-serif text-2xl font-semibold text-accent-800">{n}</p>
            <p className="mt-1 text-xs text-ink-600">{d}</p>
          </div>
        ))}
      </div>

      <p className="mt-6">
        O <strong>Saúde em Dado</strong> é uma plataforma aberta, independente e
        sem fins lucrativos que transforma microdados públicos do SUS em
        indicadores acessíveis para pesquisa, jornalismo e gestão. Não há
        anúncios, cadastro, paywall ou uso comercial dos dados. Todo o código — do
        download dos microdados ao site — é aberto e auditável no{" "}
        <a href="https://github.com/pedropaulofernandes88-stack/saude-publica-br" target="_blank" rel="noreferrer">repositório público</a>{" "}
        (MIT); os dados agregados são livres sob CC BY 4.0. Correções e críticas
        metodológicas são bem-vindas via issues.
      </p>

      <h2>Pesquisa &amp; achados</h2>
      <p>
        Além de agregar dado, este projeto produziu achados metodológicos próprios — todos
        surgidos de testar cada indicador antes de publicá-lo. Quatro deles compartilham a mesma
        estrutura de falha, consolidada no artigo{" "}
        <a href="/artigos/o-que-os-indicadores-nao-comparam/" className="font-medium text-accent-700 hover:underline">
          “O que os indicadores não comparam”
        </a>: um ajuste que aparenta tornar o indicador comparável, mas deixa passar uma variável
        estrutural (tamanho da população, do município ou do hospital).
      </p>
      <ul>
        <li>
          <strong>O denominador do excesso de mortalidade.</strong> Padronizar por idade o
          excesso de mortalidade da pandemia no Brasil <strong>subestima</strong> o resultado
          (~505 mil vs. 643 mil óbitos) por contaminação do denominador populacional — a
          projeção IBGE 2018 superestima a população, e o Censo 2022 introduz uma
          descontinuidade. Reconciliar o denominador não resolve o gap sozinho: parte é
          metodológica. Publicado como preprint na SciELO Preprints. Ver{" "}
          <a href="/artigos/643-mil-nao-702-mil-baseline-excesso-mortalidade/" className="font-medium text-accent-700 hover:underline">artigo</a>.
        </li>
        <li>
          <strong>HSMR calibrado — e o viés que a calibração não remove.</strong> A mortalidade
          hospitalar ajustada por case-mix converge, por construção, a 1,0000 nos três anos
          publicados (2022–2024). Mas ao classificar por intervalo de confiança, os hospitais
          significativamente acima do esperado são <strong>~5× maiores</strong> que os abaixo:
          o ajuste por capítulo CID é grosseiro e penaliza terciários. Calibração não é ausência
          de viés. Ver{" "}
          <a href="/artigos/visao-hospitalar-hsmr-los-forecast/" className="font-medium text-accent-700 hover:underline">artigo</a>{" "}
          e <a href="/hospitalar/" className="font-medium text-accent-700 hover:underline">página</a>.
        </li>
        <li>
          <strong>A cobertura da atenção primária mede porte, não atenção primária.</strong> A
          cobertura potencial da APS satura acima de 100% em 86% dos municípios e correlaciona-se
          com a população (ρ = −0,54), mas praticamente nada com internações evitáveis
          (ρ = +0,002; +0,017 controlando porte e vulnerabilidade). Publicamos o dado com a
          limitação no topo da página, não em rodapé. Ver{" "}
          <a href="/atencao-basica/" className="font-medium text-accent-700 hover:underline">página</a>.
        </li>
      </ul>

      <h2>Ferramentas &amp; código aberto</h2>
      <p>
        Além do site, o projeto publica dois artefatos reutilizáveis por terceiros:
      </p>
      <ul>
        <li>
          <strong>Agente MCP</strong> (<code>saudeemdado-mcp</code>, publicado no PyPI) —
          permite consultar os mesmos indicadores em linguagem natural via Claude, com
          regras anti-alucinação: todo número retornado cita a ferramenta e a fonte que o gerou.
        </li>
        <li>
          <strong>API REST pública</strong> (PostgREST/Supabase), sem cadastro, e{" "}
          <strong>downloads em Parquet</strong> com checksum SHA-256 — ver{" "}
          <a href="/dados/" className="font-medium text-accent-700 hover:underline">Dados &amp; API</a>.
        </li>
      </ul>

      <h2>Artigos &amp; publicações</h2>
      <p>
        A seção <a href="/artigos/" className="font-medium text-accent-700 hover:underline">Análises</a>{" "}
        reúne as investigações completas por trás dos indicadores — metodologia, tabelas e
        limitações declaradas, não só o número. O achado do denominador também está em
        preprint na SciELO Preprints, com submissão em periódico revisado por pares em andamento.
      </p>

      <h2>Política de atualização</h2>
      <ul>
        <li>Novos anos são incorporados quando o Ministério da Saúde publica os microdados;</li>
        <li>O ano mais recente é marcado como <em>preliminar</em> até a consolidação oficial;</li>
        <li>Cada atualização gera uma nova versão do dataset (com data em <code>meta_dataset</code>), preservando a rastreabilidade de números citados.</li>
      </ul>

      <h2>Como nos comparamos às alternativas</h2>
      <p>
        Existem ótimas iniciativas de acesso a dados de saúde no Brasil — e
        recomendamos todas. A comparação abaixo é honesta sobre o nicho de cada uma:
      </p>
      <table>
        <thead>
          <tr><th>Ferramenta</th><th>Pontos fortes</th><th>Limitações para o nosso público</th></tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>TabNet (DATASUS)</strong></td>
            <td>Fonte oficial; dezenas de sistemas; séries longas</td>
            <td>Sem API; exportação manual; interface de difícil automação; sem taxas padronizadas prontas</td>
          </tr>
          <tr>
            <td><strong>Base dos Dados</strong></td>
            <td>Muitos conjuntos tratados; ótimo para quem domina SQL/BigQuery</td>
            <td>Exige conta Google Cloud e SQL; consultas grandes podem ter custo; não é um painel</td>
          </tr>
          <tr>
            <td><strong>IEPS Data</strong></td>
            <td>Indicadores curados com rigor; foco em políticas de saúde</td>
            <td>Conjunto fechado de indicadores; menos flexível para recortes próprios</td>
          </tr>
          <tr>
            <td><strong>Saúde em Dado</strong></td>
            <td>API REST sem cadastro; painel, mapa e boletim imediatos; dez fontes integradas em 39 tabelas — mortalidade (SIM), dengue (SINAN), internações (SIH), nascimentos (SINASC), vacinação (PNI/RNDS), estabelecimentos e leitos (CNES), gasto público (SIOPS), cobertura da APS (e-Gestor AB) e saúde suplementar (ANS); taxa padronizada, IC95%, excesso de mortalidade e HSMR com correção de múltiplas comparações; pacote Python e servidor MCP; pipeline reproduzível com procedência gravada em cada arquivo</td>
            <td>Cinco domínios expostos na interface (mortalidade, dengue, assistência hospitalar, atenção primária e nascimentos); vacinação e as demais tabelas ficam na API e nos downloads. Projeto de um autor só</td>
          </tr>
        </tbody>
      </table>

      <h2>Uso ético</h2>
      <p>
        Os indicadores aqui são <strong>agregados e descritivos</strong> — não
        substituem julgamento técnico. Pedimos, de boa-fé, que a plataforma não
        seja usada para discriminação no acesso à saúde, vigilância em massa de
        indivíduos, ou automação de decisões clínicas/de política pública sem
        supervisão profissional. Nenhum microdado individual é publicado.
      </p>

      <h2>Projetos relacionados e créditos</h2>
      <p>
        O ecossistema de dados abertos de saúde no Brasil é colaborativo.
        Reconhecemos especialmente o{" "}
        <a href="https://github.com/goldenluke/labsus" target="_blank" rel="noreferrer">LabSUS</a>{" "}
        (Lucas Amaral Dourado, Universidade Federal do Tocantins), de quem
        partiram inspirações incorporadas aqui — o cruzamento de saúde com{" "}
        <strong>vulnerabilidade social</strong> (publicamos um proxy do Censo 2022,
        não o IVS oficial do IPEA — ver{" "}
        <a href="/metodologia/" className="font-medium text-accent-700 hover:underline">metodologia</a>), a{" "}
        <strong>detecção de surtos por canal endêmico</strong> e a{" "}
        <strong>nota de uso ético</strong>. Os métodos são de domínio público
        (epidemiologia clássica) e nenhum código do LabSUS foi copiado; o crédito
        é pela influência metodológica.
      </p>

      <h2>Princípios</h2>
      <ul>
        <li><strong>Reprodutibilidade</strong> — qualquer número pode ser regenerado das fontes oficiais com um script aberto;</li>
        <li><strong>Honestidade metodológica</strong> — limitações declaradas com o mesmo destaque dos resultados;</li>
        <li><strong>Privacidade</strong> — publicamos apenas agregados; nenhum microdado individual sai da máquina de processamento;</li>
        <li><strong>Permanência</strong> — arquitetura de custo zero, desenhada para não depender de financiamento para continuar no ar.</li>
      </ul>

      <h2>Como citar</h2>
      <p>
        A plataforma tem <strong>DOI</strong> permanente no Zenodo:{" "}
        <a href="https://doi.org/10.5281/zenodo.20706845" target="_blank" rel="noreferrer">
          10.5281/zenodo.20706845
        </a>.
      </p>
      <pre><code>{`FERNANDES, Pedro. Saúde em Dado: inteligência epidemiológica aberta sobre
os microdados do SUS. Zenodo, 2026. DOI: 10.5281/zenodo.20706845.
Disponível em: https://saudeemdado.com. Acesso em: [data].

Fontes primárias: BRASIL. Ministério da Saúde. SIM, SINAN, SIH, SINASC
(microdados, DataSUS). IBGE. Censo Demográfico 2022 e Estimativas de
População (SIDRA).`}</code></pre>
      <p>
        O arquivo <code>CITATION.cff</code> do repositório fornece a citação (com DOI)
        em formato legível por gerenciadores de referência.
      </p>
    </div>
  );
}
