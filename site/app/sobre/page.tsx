import type { Metadata } from "next";

export const metadata: Metadata = { title: "Sobre o projeto" };

export default function Sobre() {
  return (
    <div className="prose-doc mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
        Sobre o Saúde em Dado
      </h1>
      <p>
        O <strong>Saúde em Dado</strong> é uma plataforma aberta, independente e
        sem fins lucrativos que transforma microdados públicos do SUS em
        indicadores acessíveis para pesquisa, jornalismo e gestão. Não há
        anúncios, cadastro, paywall ou uso comercial dos dados.
      </p>

      <h2>Quem mantém</h2>
      <p>
        Mantido por <strong>Pedro Fernandes</strong> — Mestrando em Saúde Coletiva
        (IAMSPE), Pós-graduando em IA e Ciência de Dados em Saúde (Hospital
        Sírio-Libanês) e Diretor de TI da Prefeitura Municipal de Penápolis (SP).
        Contato: <a href="mailto:pedropaulofernandes88@gmail.com">pedropaulofernandes88@gmail.com</a>.
      </p>
      <p>
        <a href="https://orcid.org/0009-0008-6248-2486" target="_blank" rel="noreferrer">ORCID</a> ·{" "}
        <a href="http://lattes.cnpq.br/6641343625206093" target="_blank" rel="noreferrer">Currículo Lattes</a> ·{" "}
        <a href="https://www.linkedin.com/in/pedro-f-540154408/" target="_blank" rel="noreferrer">LinkedIn</a>
      </p>
      <p>
        Todo o código — do download dos microdados ao site — é aberto (licença
        MIT) e auditável no repositório público do projeto no GitHub
        (<code>saude-publica-br</code>). Correções, críticas metodológicas e
        contribuições são bem-vindas via issues.
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
