import type { Metadata } from "next";

export const metadata: Metadata = { title: "Sobre o projeto" };

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
            <p className="mt-1 text-sm text-ink-800">Diretor de TI — Prefeitura de Penápolis (SP)</p>
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
          ["5 sistemas", "SIM · SIH · SINAN · SINASC · IBGE"],
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
            <td>API REST sem cadastro; painel, mapa e boletim imediatos; mortalidade (SIM), dengue (SINAN) e internações (SIH); taxa padronizada, IC95% e excesso de mortalidade; pacote Python e servidor MCP; pipeline 100% reproduzível; downloads Parquet com checksum</td>
            <td>Cobre 3 dos sistemas do DataSUS (2015–2024); outros (CNES, nascidos vivos) no roadmap</td>
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
