"""Os números que o site AFIRMA precisam bater com os que ele TEM.

Esta guarda nasceu de três casos no mesmo dia. O site anunciava 547 testes
tendo 556; `docs/ARQUITETURA_DADOS.md` descrevia 4,2 milhões de linhas em 36
tabelas quando eram 4,37 milhões em 37; o deck e os PDFs diziam nove fontes
depois de a décima entrar. Nenhum deles quebrou nada — número em prosa não tem
quem o contradiga, e por isso envelhece em silêncio.

O padrão é sempre o mesmo: alguém mede, copia o resultado para um texto, e a
medida segue andando sem o texto. A correção pontual não resolve a classe; a
guarda resolve.

O que se pode derivar de uma fonte de verdade é derivado aqui:

  tabelas  <- manifesto de publicação (data/publicacoes/atual.json)
  testes   <- coleta real do pytest
  fontes   <- não há lista canônica legível por máquina, então a checagem é de
              CONSISTÊNCIA INTERNA: as três declarações no site têm de
              concordar entre si e com a lista de siglas de /sobre

A checagem de fontes é mais fraca de propósito. Inventar um
`data/refs/fontes.json` só para ter o que conferir criaria mais um número
escrito à mão para envelhecer — trocaria o problema de lugar em vez de
resolvê-lo. Consistência entre três lugares já teria pego o defeito real: um
revisor encontrou o site dizendo cinco fontes enquanto o PDF dizia oito.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
HOME = RAIZ / "site" / "app" / "page.tsx"
SOBRE = RAIZ / "site" / "app" / "sobre" / "page.tsx"
PUBLICACOES = RAIZ / "data" / "publicacoes"

# Só os números que este projeto de fato escreve por extenso.
POR_EXTENSO = {
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
}


def _texto(caminho: Path) -> str:
    if not caminho.exists():
        pytest.skip(f"{caminho.relative_to(RAIZ)} não existe nesta árvore")
    return caminho.read_text(encoding="utf-8")


def _manifesto_atual() -> dict:
    atual = PUBLICACOES / "atual.json"
    if not atual.exists():
        pytest.skip("sem publicação local para conferir")
    ponteiro = json.loads(atual.read_text(encoding="utf-8"))
    return json.loads((PUBLICACOES / ponteiro["arquivo"]).read_text(encoding="utf-8"))


def _declarado_na_home() -> tuple[int, int]:
    """(tabelas, fontes) do cartão 'N tabelas · M fontes'."""
    m = re.search(r"(\d+)\s+tabelas\s*·\s*(\d+)\s+fontes", _texto(HOME))
    assert m, "a home não declara mais 'N tabelas · M fontes' — a guarda precisa saber onde olhar"
    return int(m.group(1)), int(m.group(2))


def test_tabelas_declaradas_batem_com_o_manifesto():
    tabelas, _ = _declarado_na_home()
    real = len(_manifesto_atual()["tabelas"])
    assert tabelas == real, (
        f"a home anuncia {tabelas} tabelas e o manifesto publicado tem {real}. "
        f"Corrigir o cartão em site/app/page.tsx."
    )


def test_fontes_sao_consistentes_entre_as_declaracoes_do_site():
    _, fontes_home = _declarado_na_home()
    sobre = _texto(SOBRE)

    m = re.search(r'\["(\d+)\s+fontes",\s*"([^"]+)"\]', sobre)
    assert m, "/sobre não declara mais '[N fontes, lista]' — a guarda precisa saber onde olhar"
    fontes_sobre, lista = int(m.group(1)), m.group(2)
    siglas = [s.strip() for s in lista.split("·") if s.strip()]

    palavra = re.search(r"(\w+) fontes integradas em (\d+) tabelas", sobre)
    assert palavra, "a linha de comparação de /sobre mudou de forma"
    fontes_prosa = POR_EXTENSO.get(palavra.group(1).lower())
    assert fontes_prosa, f"número por extenso desconhecido: {palavra.group(1)!r}"
    tabelas_prosa = int(palavra.group(2))

    assert fontes_home == fontes_sobre == len(siglas) == fontes_prosa, (
        f"contagem de fontes divergente — home={fontes_home}, /sobre cartão={fontes_sobre}, "
        f"siglas listadas={len(siglas)} ({', '.join(siglas)}), prosa={fontes_prosa}"
    )
    tabelas_home, _ = _declarado_na_home()
    assert tabelas_prosa == tabelas_home, (
        f"a prosa de /sobre diz {tabelas_prosa} tabelas e a home diz {tabelas_home}"
    )


# ── coeficientes ─────────────────────────────────────────────────────────────
# Um coeficiente publicado tem duas formas de envelhecer, e a segunda é a que
# passou despercebida: (a) alguém edita o texto e erra, ou (b) o DADO muda e a
# análise não é refeita. A correção da Lista Brasileira de ICSAP em 2026-08-31
# foi o caso (b) — os coeficientes descreviam um dado que deixara de existir.
#
# O valor de verdade vem de `data/marts/achados.json`, gravado pelos próprios
# scripts de análise (ver scripts/_achados.py). Recalcular aqui duplicaria a
# lógica da análise, e duas cópias divergem.
COEFICIENTES = {
    # chave em achados.json -> (arquivo do site, regex, casas decimais)
    "aps_x_icsap_bruta": (SOBRE, r"ρ = ([+-]\d,\d+); [+-]\d,\d+ controlando", 3),
    "aps_x_icsap_parcial": (SOBRE, r"ρ = [+-]\d,\d+; ([+-]\d,\d+) controlando", 3),
}


def _achados() -> dict:
    caminho = RAIZ / "data" / "marts" / "achados.json"
    if not caminho.exists():
        pytest.skip("sem achados.json — rode os scripts de análise")
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.mark.parametrize("chave", sorted(COEFICIENTES))
def test_coeficiente_publicado_bate_com_a_analise(chave):
    reg = _achados().get(chave)
    if reg is None:
        pytest.skip(f"{chave} ainda não foi registrado por nenhuma análise")
    caminho, padrao, casas = COEFICIENTES[chave]
    m = re.search(padrao, _texto(caminho))
    assert m, f"não achei {chave} em {caminho.name} com o padrão {padrao!r}"
    declarado = float(m.group(1).replace(",", "."))
    real = round(reg["valor"], casas)
    assert abs(declarado - real) < 10 ** -casas / 2, (
        f"{chave}: o site declara {declarado:+.3f} e a análise calculou {real:+.3f}. "
        f"Recalculado em {reg['calculado_em']}."
    )


def test_nenhuma_analise_ficou_atras_do_dado():
    """O defeito que motivou tudo isto: mart regravado, análise não refeita.

    Não confere valor — confere FRESCOR. Um coeficiente pode estar copiado
    corretamente e ainda assim descrever dado que não existe mais.
    """
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _achados import desatualizados  # noqa: PLC0415

    atrasados = desatualizados()
    assert not atrasados, (
        "análise mais velha que o mart que ela leu — rodar de novo os scripts "
        f"analise_*.py: {'; '.join(atrasados)}"
    )


def _coletar_testes() -> int:
    """Conta os testes que o pytest coleta, num processo separado.

    Processo separado, e não `pytest.main` aqui dentro, porque coletar de
    dentro de uma sessão em andamento mexe em estado global do pytest.
    """
    codigo = (
        "import io,contextlib,pytest\n"
        "class C:\n"
        "    def __init__(self): self.n=0\n"
        "    def pytest_collection_modifyitems(self, items): self.n=len(items)\n"
        "c=C()\n"
        "b=io.StringIO()\n"
        "with contextlib.redirect_stdout(b), contextlib.redirect_stderr(b):\n"
        "    pytest.main(['tests/','--collect-only','-q','-p','no:cacheprovider'], plugins=[c])\n"
        "print(c.n)\n"
    )
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ,
                       capture_output=True, text=True, timeout=600)
    saida = (r.stdout or "").strip().splitlines()
    if not saida or not saida[-1].isdigit():
        pytest.skip(f"não foi possível coletar: {(r.stderr or r.stdout)[-200:]}")
    return int(saida[-1])


def test_testes_declarados_batem_com_a_coleta():
    m = re.search(r'\["(\d+)\s+testes"', _texto(HOME))
    assert m, "a home não declara mais 'N testes' — a guarda precisa saber onde olhar"
    declarado = int(m.group(1))
    real = _coletar_testes()
    assert declarado == real, (
        f"a home anuncia {declarado} testes e a suíte tem {real}. "
        f"Corrigir o cartão em site/app/page.tsx. "
        f"Falhar aqui ao adicionar um teste é o comportamento pretendido: "
        f"é o que impede o número de envelhecer."
    )



# --------------------------------------------------------------------------
# Rótulo de estado não pode depender de ano escrito à mão
#
# Mesmo defeito da classe acima, num disfarce: em vez de um número copiado, uma
# CONDIÇÃO copiada. `a === 2024 ? " (preliminar)"` estava certo quando foi
# escrito e passou a mentir em 2026-09-03, quando 2024 consolidou e 2025 entrou.
# O site ficou anunciando exatamente o inverso da verdade — 2024 marcado como
# preliminar, 2025 sem marca — e ninguém viu, porque a linha não quebrou nada.
#
# Fato histórico cravado é legítimo: "2024 (epidemia recorde)" continua verdade
# para sempre. O que não pode é ESTADO — preliminar, provisório, parcial —,
# porque estado muda e o literal não acompanha.
# --------------------------------------------------------------------------
ESTADOS_QUE_MUDAM = ("preliminar", "provisório", "provisorio", "parcial",
                     "incompleto", "atual", "corrente")

def test_nenhum_rotulo_de_estado_preso_a_ano_literal():
    ofensas = []
    for tsx in sorted((RAIZ / "site" / "app").rglob("*.tsx")):
        for n, linha in enumerate(_texto(tsx).splitlines(), 1):
            if not re.search(r"===\s*20\d\d\s*\?", linha):
                continue
            if any(e in linha.lower() for e in ESTADOS_QUE_MUDAM):
                ofensas.append(f"{tsx.relative_to(RAIZ)}:{n}: {linha.strip()[:110]}")
    assert not ofensas, (
        "rótulo de estado comparado a ano literal — use ehPreliminar() (mortalidade) "
        "ou derive do próprio vetor de anos (Math.max(...ANOS_X)):\n  "
        + "\n  ".join(ofensas))


# --------------------------------------------------------------------------
# O catálogo de dados não pode ter contagem escrita à mão
#
# /dados tinha DUAS tabelas: uma descritiva com aproximações digitadas e outra
# gerada do manifesto, com o número exato — na mesma página, uma certa e outra
# errada. A digitada anunciava 53 mil linhas para mart_internacoes_agravo, que
# tem 158.042; natalidade e internações por hospital estavam por um terço do
# real, e isso não veio de uma atualização: era drift desde que foi escrita.
# --------------------------------------------------------------------------
CATALOGO = RAIZ / "site" / "app" / "dados" / "page.tsx"

def test_catalogo_nao_tem_contagem_de_linhas_digitada():
    ofensas = [f"linha {n}: {l.strip()}"
               for n, l in enumerate(_texto(CATALOGO).splitlines(), 1)
               if re.match(r"\s*<td>~[\d.,]+\s*(mil|mi|milh)", l)]
    assert not ofensas, (
        "contagem de linhas digitada no catálogo — use linhasDe(\"nome\"), que lê "
        "o manifesto de publicação:\n  " + "\n  ".join(ofensas))


def test_toda_tabela_citada_no_catalogo_existe_no_manifesto():
    """linhasDe() devolve '—' para nome ausente, e isso não pode passar calado."""
    nomes = set(re.findall(r'linhasDe\("([a-z0-9_]+)"\)', _texto(CATALOGO)))
    assert nomes, "nenhuma chamada a linhasDe — a guarda perdeu o alvo"
    atual = json.loads((RAIZ / "data" / "publicacoes" / "atual.json").read_text("utf-8"))
    man = json.loads((RAIZ / "data" / "publicacoes" / atual["arquivo"]).read_text("utf-8"))
    faltando = sorted(nomes - set(man["tabelas"]))
    assert not faltando, f"citadas em /dados e ausentes do manifesto: {faltando}"


# --------------------------------------------------------------------------
# O site não pode descrever o método de excesso que foi substituído
#
# Pior que número envelhecido: /tendencias explicava o excesso como "média
# 2015–2019 do mesmo mês, ajustada pela população do ano" e a legenda do
# gráfico repetia "baseline 2015–2019 com ajuste populacional". Esse método foi
# trocado por TENDÊNCIA LINEAR por mês civil no 3.1.0 — a troca está no
# CHANGELOG, na metodologia, nos artigos e no preprint, e esta página ficou na
# versão velha por mais de um ano. Não é um número que envelheceu: é a
# descrição de um cálculo que o código não faz.
#
# O método antigo superestimava o excesso nos anos recentes, então a página
# explicava um viés que o projeto já tinha corrigido.
# --------------------------------------------------------------------------
METODO_ANTIGO = (
    "ajuste populacional",
    "ajustada pela população",
    "razão populacional",
    "média 2015–2019",
    "média 2015-2019",
)

#: Falar do método antigo COMO antigo é legítimo e desejável — a §6 da
#: metodologia explica o que foi trocado e por quê. O que a guarda proíbe é
#: apresentá-lo como o cálculo corrente, e a diferença está numa marca
#: histórica perto da menção.
MARCA_HISTORICA = ("anterior", "antigo", "substitu", "trocad", "deixou de",
                   "ficou para trás", "3.1.0")


def test_site_nao_descreve_o_metodo_de_excesso_antigo():
    ofensas = []
    for arq in sorted((RAIZ / "site").rglob("*.tsx")):
        if "node_modules" in arq.parts:
            continue
        texto = _texto(arq)
        if "excesso" not in texto.lower():
            continue
        linhas = texto.splitlines()
        for n, linha in enumerate(linhas, 1):
            if not any(t in linha for t in METODO_ANTIGO):
                continue
            # a marca pode estar nas linhas vizinhas: o texto é JSX quebrado
            volta = " ".join(linhas[max(0, n - 4):n + 3]).lower()
            if any(m in volta for m in MARCA_HISTORICA):
                continue
            ofensas.append(f"{arq.relative_to(RAIZ)}:{n}: {linha.strip()[:100]}")
    assert not ofensas, (
        "método de excesso ANTERIOR ao 3.1.0 apresentado como o corrente — o "
        "esperado vem de tendência linear por mês civil ajustada a 2015–2019. "
        "Se a menção for histórica, diga isso perto dela:\n  "
        + "\n  ".join(ofensas))


# --------------------------------------------------------------------------
# A cobertura da base não pode ser afirmada por texto digitado
#
# "14,4 milhões de óbitos (2015–2024)" aparecia em oito lugares: a descrição
# que o link mostra ao ser compartilhado, o nome no schema.org, o herói da
# home, o cartão de mortalidade, o rótulo de um KPI, a citação sugerida para
# trabalhos acadêmicos e o quadro do /sobre. Todos digitados, todos defasados
# no mesmo dia — e o KPI ao lado de um deles já exibia o número certo, porque
# esse era calculado a partir da série.
#
# Anos vêm de ANOS (lib/api.ts) no cliente e de cobertura() (lib/cobertura.ts,
# que lê sdata/serie_total.json no build) no servidor.
# --------------------------------------------------------------------------
#: Onde um intervalo iniciado em 2015 é legítimo, e por quê. Cada isenção é uma
#: afirmação: "este recorte NÃO acompanha a base". Acrescentar exige dizer isso.
RECORTES_FIXOS = {
    # o baseline do excesso de mortalidade: janela fixa por metodologia, citada
    # em muitas páginas. Não acompanha a base por definição — se acompanhasse,
    # o "esperado" passaria a ser ajustado pelos anos que ele deveria julgar.
    (None, "2015", "2019"): "baseline do excesso de mortalidade",
    # a série é dada por metodologia, não pela cobertura
    ("site/app/dengue/dengue-cliente.tsx", "2015", "2023"):
        "baseline do diagrama de controle da dengue",
    # descrevem a DIVISÃO DE FONTE, não o alcance
    ("site/app/metodologia/page.tsx", "2015", "2021"):
        "anos que vêm do .dbc / que têm só totais e marginais",
    ("site/app/metodologia/page.tsx", "2015", "2024"):
        "mediana de comparação para julgar 2025, e leitos CNES",
}

#: Artigo publicado é registro datado: ele expõe `datePublished` e afirma a
#: cobertura DA ÉPOCA. Reescrever o período de um artigo depois falsifica o
#: registro — a correção certa seria um novo artigo, nunca uma edição silenciosa.
FORA_DA_GUARDA = ("site/content/artigos.tsx",)


def test_nenhuma_pagina_crava_o_periodo_da_base():
    """Intervalo digitado que comece no 1º ano da base e termine antes do último.

    Fontes que de fato param antes (SIH, ICSAP, PNI) começam depois de 2015 e
    por isso não entram aqui — cravar o intervalo delas está correto.
    """
    anos = re.search(r"export const ANOS = \[([^\]]+)\]",
                     _texto(RAIZ / "site" / "lib" / "api.ts"))
    assert anos, "ANOS sumiu de lib/api.ts — a guarda perdeu a referência"
    todos = [int(a) for a in re.findall(r"\d{4}", anos.group(1))]
    primeiro, ultimo = min(todos), max(todos)

    ofensas = []
    for arq in sorted((RAIZ / "site").rglob("*.tsx")):
        if "node_modules" in arq.parts:
            continue
        rel = arq.relative_to(RAIZ).as_posix()
        if rel in FORA_DA_GUARDA:
            continue
        for n, linha in enumerate(_texto(arq).splitlines(), 1):
            if linha.lstrip().startswith(("//", "*", "/*", "#:")):
                continue
            for ini, fim in re.findall(r"(20\d\d)\s*[–-]\s*(20\d\d)", linha):
                if int(ini) != primeiro or int(fim) >= ultimo:
                    continue
                if (rel, ini, fim) in RECORTES_FIXOS or (None, ini, fim) in RECORTES_FIXOS:
                    continue
                ofensas.append(f"{rel}:{n}: {ini}–{fim} (a base vai até {ultimo})")
    assert not ofensas, (
        "período da base cravado em texto — derive de ANOS/PERIODO (cliente) ou "
        "de cobertura() (servidor). Se for recorte fixo por metodologia, "
        "declare em RECORTES_FIXOS com o motivo:\n  " + "\n  ".join(ofensas))


# --------------------------------------------------------------------------
# Os anos que a interface OFERECE têm que ser os que a base TEM
#
# /nascimentos trazia `const ANOS = [2022, 2021]` dentro do próprio arquivo da
# página, e `mart_natalidade_municipio` já publicava 2021–2024: dois anos
# inteiros de dado publicado eram inalcançáveis por quem usava o site. Ao lado
# do seletor, o texto anunciava um TERCEIRO intervalo, 2021–2023. Três
# afirmações, nenhuma igual à outra, nenhuma igual ao dado.
#
# Nada quebrou, nada apareceu em log: um seletor com menos opções é apenas um
# seletor com menos opções. Só comparando com a fonte dá para ver.
# --------------------------------------------------------------------------
#: vetor declarado em lib/api.ts -> mart de onde os anos têm de vir
VETORES_DE_ANO = {
    "ANOS": "mart_mortalidade_municipio",
    "ANOS_SINASC": "mart_natalidade_municipio",
}


def _anos_do_vetor(nome: str) -> set[int]:
    m = re.search(rf"export const {nome}(?::[^=]+)? = \[([^\]]+)\]",
                  _texto(RAIZ / "site" / "lib" / "api.ts"))
    assert m, f"{nome} sumiu de lib/api.ts — a guarda perdeu a referência"
    return {int(a) for a in re.findall(r"\d{4}", m.group(1))}


@pytest.mark.parametrize("vetor,mart", sorted(VETORES_DE_ANO.items()))
def test_anos_declarados_batem_com_o_publicado(vetor: str, mart: str):
    caminho = RAIZ / "data" / "marts" / f"{mart}.parquet"
    if not caminho.exists():
        pytest.skip(f"{mart}.parquet ausente")
    import pandas as pd
    tem = set(pd.read_parquet(caminho, columns=["ano"]).ano.unique().tolist())
    oferece = _anos_do_vetor(vetor)
    escondidos = sorted(tem - oferece)
    inventados = sorted(oferece - tem)
    assert not escondidos, (
        f"{vetor} não oferece {escondidos}, que {mart} publica — "
        "o site esconde dado que ele tem")
    assert not inventados, (
        f"{vetor} oferece {inventados}, que {mart} não tem — "
        "o seletor levaria a uma tela vazia")


# --------------------------------------------------------------------------
# O catálogo tem que dizer quais tabelas a API NÃO serve
#
# "Publicada" e "servida" são coisas diferentes aqui: cinco tabelas ficam
# deliberadamente fora do Postgres. O catálogo listava todas igual, então quem
# chamasse `mart_vacinacao_municipio` na API recebia um 404 seco — com o
# download, que é o caminho certo para ela, ali do lado na mesma página.
# --------------------------------------------------------------------------
def test_o_catalogo_marca_as_tabelas_que_a_api_nao_serve():
    texto = _texto(CATALOGO)
    assert "servida === false" in texto, (
        "o catálogo não distingue publicada de servida — quem tentar a API numa "
        "tabela só-Parquet recebe 404 sem explicação")
    # e a marca tem de vir do manifesto, não de uma lista escrita à mão aqui
    assert "NomeTabela" in texto and 'n="mart_' in texto, (
        "as células de nome deixaram de passar por NomeTabela, que é onde a "
        "marca é derivada")


def test_toda_tabela_do_manifesto_declara_se_e_servida():
    atual = json.loads((RAIZ / "data" / "publicacoes" / "atual.json").read_text("utf-8"))
    man = json.loads((RAIZ / "data" / "publicacoes" / atual["arquivo"]).read_text("utf-8"))
    sem = sorted(n for n, v in man["tabelas"].items() if "servida" not in v)
    assert not sem, f"sem o campo `servida` no manifesto: {sem}"
