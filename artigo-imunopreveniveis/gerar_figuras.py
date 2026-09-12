"""
gerar_figuras.py — as seis figuras do artigo das mortes imunopreveníveis
=========================================================================

    .venv311/Scripts/python artigo-imunopreveniveis/gerar_figuras.py

Lê `artigo-imunopreveniveis/tabelas/*.csv` e escreve `figuras/*.png`. Nenhuma
conta acontece aqui — se aparecer uma divisão neste arquivo, ela está no lugar
errado. Cada legenda aponta a tabela que originou a figura, de modo que todo
valor lido no gráfico possa ser conferido no número exato.

O QUE ESTAS FIGURAS PRECISAM MOSTRAR
-------------------------------------
O argumento do artigo é sobre um INSTRUMENTO, não sobre uma doença. Cada figura
existe para tornar visível uma das três falhas medidas:

  1. o instrumento não se move (série plana por uma década);
  2. ele para aos 74 anos, e é acima disso que se morre;
  3. metade do que ele conta é tuberculose de adulto, que a BCG não previne.

E duas sobre o limite do instrumento: os três eventos da década — dois deles
JÁ NA LISTA, o que mostra que incluir o código não era o que faltava — e o teto
de codificação que limita qualquer medição de doença bacteriana no Brasil.

A SEXTA MOSTRA UM RESULTADO NULO
---------------------------------
O cruzamento entre doses de influenza e mortalidade em 60+ deu nulo pelo
critério declarado antes. Ele vai desenhado com o mesmo cuidado das outras —
resultado nulo escondido em apêndice é como um achado positivo vira norma sem
nunca ter sido testado. A figura mostra também POR QUE ele é frágil: a própria
fonte registra 16,6 milhões de doses em 2023 contra 54,2 milhões em 2024.

DECISÕES DE COR
----------------
* Categórica (identidade) usa slots de paleta validada para daltonismo.
* Divergente (polaridade) usa azul↔vermelho com cinza no meio.
* Nenhuma figura tem dois eixos y.
* Rótulo direto onde as séries são poucas.

Depende de `matplotlib`. Uso: sem argumentos.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent
TABELAS = RAIZ / "tabelas"
FIGURAS = RAIZ / "figuras"

AZUL, LARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
VERMELHO = "#e34948"
TINTA, TINTA2 = "#0b0b0b", "#52514e"
GRADE, NEUTRO = "#e3e2de", "#c9c8c3"
LARGURA = 6.3


def _estilo() -> None:
    plt.rcParams.update({
        "figure.dpi": 300, "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8.5, "axes.titlesize": 9.5, "axes.labelsize": 8.5,
        "axes.titleweight": "bold", "axes.edgecolor": NEUTRO,
        "axes.labelcolor": TINTA2, "axes.linewidth": 0.8,
        "xtick.color": TINTA2, "ytick.color": TINTA2,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "legend.frameon": False,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
    })


def _ler(nome: str) -> pd.DataFrame:
    caminho = TABELAS / f"{nome}.csv"
    if not caminho.exists():
        raise SystemExit(
            f"[figuras] falta {caminho.name}. Rode "
            "`python artigo-imunopreveniveis/gerar_tabelas.py` antes.")
    return pd.read_csv(caminho)


def _br(v: float, casas: int = 1) -> str:
    """Número no padrão brasileiro: milhar com ponto, decimal com vírgula."""
    return f"{v:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _so_anos(d: pd.DataFrame, col: str = "Ano") -> pd.DataFrame:
    """Descarta a linha de TOTAL que várias tabelas trazem no fim.

    Ela põe "2015–2024" na coluna do ano, e um gráfico de série que a inclua
    desenha o total como se fosse mais um ponto — erro que não quebra nada e
    multiplica a última barra por dez.
    """
    return d[d[col].astype(str).str.fullmatch(r"\d{4}")].copy()


def _limpar(ax, eixo_y: bool = True) -> None:
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    if eixo_y:
        ax.grid(axis="y", color=GRADE, linewidth=0.7, zorder=0)
        ax.set_axisbelow(True)


def _salvar(fig, nome: str) -> None:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURAS / f"{nome}.png")
    plt.close(fig)
    print(f"   figuras/{nome}.png", flush=True)


# ── 1. o instrumento não se move ───────────────────────────────────────────
def figura_01_serie_oficial() -> None:
    """Uma década plana — e a linha de 75+ que o instrumento não vê."""
    d = _so_anos(_ler("tabela_3_subgrupo_1_1_por_ano"))
    ano = d["Ano"].astype(int)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(LARGURA, 2.7))
    a1.plot(ano, d["Óbitos do subgrupo 1.1"].astype(float), "-o",
            color=AZUL, lw=1.6, ms=3.4, label="subgrupo 1.1 (o que a lista conta)")
    a1.plot(ano, d["Mesmos códigos em 75 anos ou mais"].astype(float), "-o",
            color=LARANJA, lw=1.6, ms=3.4,
            label="mesmos códigos, 75+ (fora da lista)")
    a1.set_ylim(0)
    a1.set_ylabel("Óbitos no ano")
    a1.legend(loc="lower left", fontsize=7.2)
    _limpar(a1)

    a2.plot(ano, d["Subgrupo 1.1 por 10 mil óbitos"].astype(float), "-o",
            color=AZUL, lw=1.6, ms=3.4)
    a2.set_ylim(0)
    a2.set_ylabel("Por 10 mil óbitos do ano")
    _limpar(a2)
    for ax in (a1, a2):
        ax.set_xticks([2015, 2018, 2021, 2024])

    fig.suptitle("O instrumento oficial não se move em uma década",
                 fontsize=9.8, fontweight="bold", color=TINTA, y=1.03)
    _salvar(fig, "figura_01_serie_oficial")


# ── 2. o que a lista vê e o que existe ─────────────────────────────────────
def figura_02_panorama() -> None:
    """4,79x fora do instrumento, e a COVID-19 numa escala à parte."""
    d = _ler("tabela_4_panorama")
    nomes = [n.replace(", ", ",\n") for n in d["Conjunto"].astype(str)]
    v = d["Óbitos 2015–2024"].astype(float)
    y = list(range(len(d)))[::-1]

    fig, ax = plt.subplots(figsize=(LARGURA, 2.6))
    # Escala log: a COVID-19 é duas ordens de grandeza acima do resto, e numa
    # escala linear ela achataria as outras barras contra o zero — que é
    # exatamente a comparação que o artigo precisa deixar legível.
    ax.barh(y, v, color=[AZUL if i == 0 else NEUTRO for i in range(len(d))],
            height=0.62, zorder=3)
    ax.set_xscale("log")
    for i, yy in enumerate(y):
        ax.text(v.iloc[i] * 1.14, yy, _br(v.iloc[i], 0),
                va="center", fontsize=7.4, color=TINTA2)
    ax.set_yticks(y)
    ax.set_yticklabels(nomes, fontsize=7.2)
    ax.set_xlabel("Óbitos 2015–2024 (escala logarítmica)")
    ax.set_xlim(v.min() * 0.5, v.max() * 4)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRADE, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("O que o instrumento conta (azul) e o que existe ao lado dele",
                 color=TINTA, loc="left")
    _salvar(fig, "figura_02_panorama")


# ── 3. a lista para aos 74 anos ────────────────────────────────────────────
def figura_03_corte_etario() -> None:
    """35,8% dos óbitos com vacina disponível estão acima do corte."""
    d = _ler("tabela_5_estrutura_etaria")
    d = d[~d["Faixa etária"].astype(str).str.lower().str.contains("total")]
    fx = d["Faixa etária"].astype(str)
    y = list(range(len(d)))[::-1]

    fig, ax = plt.subplots(figsize=(LARGURA, 2.3))
    esq = [0.0] * len(d)
    for col, cor, rot in (("Subgrupo 1.1", AZUL, "subgrupo 1.1"),
                          ("Ampliado sem COVID-19", AQUA, "ampliado (sem COVID-19)"),
                          ("COVID-19", LARANJA, "COVID-19")):
        v = d[col].astype(float).tolist()
        ax.barh(y, v, left=esq, color=cor, height=0.58, label=rot, zorder=3)
        esq = [a + b for a, b in zip(esq, v)]
    for i, yy in enumerate(y):
        ax.text(esq[i] * 1.02, yy,
                f"{_br(d['% do total'].astype(float).iloc[i])}%",
                va="center", fontsize=7.4, color=TINTA2)
    ax.set_yticks(y)
    ax.set_yticklabels(fx, fontsize=7.6)
    ax.set_xlabel("Óbitos 2015–2024")
    ax.legend(loc="lower right", fontsize=7.2)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRADE, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("A lista termina aos 74 anos — e é acima disso que se morre",
                 color=TINTA, loc="left")
    _salvar(fig, "figura_03_corte_etario")


# ── 4. metade do que a lista conta é tuberculose ───────────────────────────
def figura_04_composicao() -> None:
    d = _ler("tabela_6_composicao_subgrupo_1_1")
    # Quebrar em duas linhas, NAO truncar: a parte cortada destes rotulos e'
    # exatamente a que diz por que a linha esta ali ("idade em que a BCG
    # protege", "sem protecao estabelecida").
    nomes = []
    for n in d["Componente"].astype(str):
        n = n.replace("… destes", "destes").replace(", no subgrupo 1.1", "")
        if len(n) > 40 and " (" in n:
            cabeca, _, cauda = n.partition(" (")
            n = cabeca + chr(10) + "(" + cauda
        nomes.append(n)
    v = d["Óbitos 2015–2024"].astype(float)
    pct = d["% do subgrupo 1.1"].astype(float)
    y = list(range(len(d)))[::-1]
    # A cor marca O QUE O ARTIGO QUESTIONA, não o tamanho da barra. Vermelho é
    # tuberculose em idade sem proteção estabelecida pela BCG — o que a lista
    # conta e a evidência não sustenta. Azul é o que resta de pé. Cinza é o
    # total, que não é parte nem contraparte.
    #
    # A primeira versão pintava de vermelho tudo acima de 40%, e com isso
    # "subgrupo 1.1 excluída a tuberculose" — justamente a parte legítima —
    # saía da mesma cor do problema. Cor por magnitude diz a coisa errada
    # quando o eixo do argumento não é magnitude.
    componente = d["Componente"].astype(str).str.lower()
    cor = []
    for i, nome in enumerate(componente):
        if i == 0:
            cor.append(NEUTRO)                       # o total nao e' parte
        elif "menores de 5" in nome or "exclu" in nome:
            cor.append(AZUL)                         # o que se sustenta
        elif "tuberculose" in nome or "sem prote" in nome:
            cor.append(VERMELHO)                     # o que o artigo questiona
        else:
            cor.append(AZUL)

    fig, ax = plt.subplots(figsize=(LARGURA, 2.5))
    ax.barh(y, v, color=cor, height=0.6, zorder=3)
    for i, yy in enumerate(y):
        ax.text(v.iloc[i] * 1.02 + 30, yy,
                f"{_br(v.iloc[i], 0)}  ({_br(pct.iloc[i])}%)",
                va="center", fontsize=7.2, color=TINTA2)
    ax.set_yticks(y)
    ax.set_yticklabels(nomes, fontsize=7.2)
    ax.set_xlabel("Óbitos 2015–2024")
    ax.set_xlim(0, v.max() * 1.5)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRADE, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Metade do que a lista conta é tuberculose em idade\n"
                 "sem proteção estabelecida pela BCG", color=TINTA, loc="left")
    _salvar(fig, "figura_04_composicao")


# ── 5. o que acontece fora do instrumento ──────────────────────────────────
def figura_05_eventos() -> None:
    """Febre amarela, sarampo e coqueluche: surtos que a lista não registra."""
    d = _so_anos(_ler("tabela_8_eventos_serie_anual"))
    ano = d["Ano"].astype(int)

    fig, eixos = plt.subplots(1, 3, figsize=(LARGURA, 2.2), sharex=True)
    series = [("Febre amarela", AZUL, None),
              ("Sarampo", LARANJA, "Sarampo em menores de 1 ano"),
              ("Coqueluche", AQUA, "Coqueluche em menores de 1 ano")]
    for ax, (col, cor, col_bebe) in zip(eixos, series):
        v = d[col].astype(float)
        ax.bar(ano, v, color=cor, width=0.66, zorder=3)
        if col_bebe and col_bebe in d.columns:
            # A parte em menores de 1 ano vai HACHURADA dentro da barra, e não
            # como segunda barra: ela é subconjunto, não categoria paralela.
            ax.bar(ano, d[col_bebe].astype(float), color="none", width=0.66,
                   edgecolor="white", hatch="///", lw=0, zorder=4)
        ax.set_title(col, fontsize=8.6, color=TINTA)
        ax.set_xticks([2015, 2019, 2023])
        _limpar(ax)
    eixos[0].set_ylabel("Óbitos no ano")
    # No canto ESQUERDO do painel do sarampo, que e' a unica regiao dos tres
    # paineis sem barra alta. Centralizado em cima, como estava, o rotulo caia
    # exatamente sobre o pico de 2021.
    eixos[1].text(0.02, 0.88, "hachurado: < 1 ano", transform=eixos[1].transAxes,
                  ha="left", fontsize=6.8, color=TINTA2)
    # O TITULO ANTERIOR ERA FALSO, e o revisor o pegou: dizia "Fora do subgrupo
    # 1.1", mas A37 (coqueluche) e B05 (sarampo) ESTAO no subgrupo — quem esta
    # fora e' so' a febre amarela. O ponto verdadeiro e' mais forte que o falso:
    # essas duas doencas ressurgiram COM a lista ja' as incluindo, o que mostra
    # que incluir o codigo nao e' o que faltava.
    fig.suptitle("A lista já inclui sarampo e coqueluche, e as duas ressurgiram na"
                 " década. Só a febre amarela está fora do subgrupo 1.1",
                 fontsize=9.2, fontweight="bold", color=TINTA, y=1.08)
    _salvar(fig, "figura_05_tres_eventos")


# ── 6. o teto de codificação ───────────────────────────────────────────────
def figura_06_teto() -> None:
    """Doença pneumocócica invasiva é incontável por causa básica no Brasil."""
    d = _ler("tabela_12_teto_codificacao")
    nomes = [n.split(" — ")[0] + " — " + n.split(" — ")[-1][:34]
             for n in d["Código e descrição"].astype(str)]
    v = d["Óbitos 2015–2024"].astype(float)
    nomeado = d["Agente etiológico nomeado"].astype(str).str.lower().eq("sim")
    y = list(range(len(d)))[::-1]

    fig, ax = plt.subplots(figsize=(LARGURA, 2.6))
    ax.barh(y, v, color=[AZUL if n else NEUTRO for n in nomeado],
            height=0.6, zorder=3)
    ax.set_xscale("log")
    for i, yy in enumerate(y):
        ax.text(v.iloc[i] * 1.16, yy, _br(v.iloc[i], 0),
                va="center", fontsize=7.2, color=TINTA2)
    ax.set_yticks(y)
    ax.set_yticklabels(nomes, fontsize=7.0)
    ax.set_xlabel("Óbitos 2015–2024 (escala logarítmica)")
    ax.set_xlim(max(v.min() * 0.4, 1), v.max() * 5)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRADE, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Azul: agente etiológico nomeado. Cinza: não nomeado.\n"
                 "O teto de medição é de codificação, não de epidemiologia",
                 color=TINTA, loc="left", fontsize=8.8)
    _salvar(fig, "figura_06_teto_de_codificacao")


#: Onde cada figura entra no .docx, e o que a legenda diz. A chave é o começo do
#: título da seção que a discute; a figura é inserida no FIM dessa seção. Mora
#: aqui, ao lado do código que desenha, para que legenda e desenho envelheçam
#: juntos.
LEGENDAS: tuple[tuple[str, str, str], ...] = (
    ("3.2", "figura_01_serie_oficial",
     "Óbitos identificados pelo subgrupo 1.1 da Lista Brasileira, 2015–2024. "
     "(A) Contagem anual, com os mesmos códigos em 75 anos ou mais — faixa que "
     "o instrumento não alcança por construção. (B) Óbitos por 10 mil óbitos do "
     "ano. A série não tem tendência na década. Fonte: Tabela S3."),
    ("3.3", "figura_03_corte_etario",
     "Distribuição etária dos óbitos por causas com vacina disponível, "
     "2015–2024. A Lista Brasileira termina aos 74 anos; 35,8% dos óbitos estão "
     "acima desse corte, invisíveis ao instrumento. Fonte: Tabela S5."),
    ("3.4", "figura_04_composicao",
     "Composição interna do subgrupo 1.1. Em vermelho, a tuberculose miliar e "
     "do sistema nervoso em idade sem proteção estabelecida pela BCG; em azul, "
     "o que resta do subgrupo. Fonte: Tabela S6."),
    ("3.5", "figura_02_panorama",
     "O que o subgrupo 1.1 identifica, comparado ao conjunto ampliado de "
     "doenças com vacina disponível no país e à COVID-19. Escala logarítmica: a "
     "COVID-19 está duas ordens de grandeza acima das demais categorias, e uma "
     "escala linear achataria a comparação entre elas. Fonte: Tabela S4."),
    ("3.6", "figura_05_tres_eventos",
     "Óbitos anuais por febre amarela, sarampo e coqueluche. A porção hachurada "
     "é a fração em menores de 1 ano. Sarampo (B05) e coqueluche (A37) JÁ "
     "constam do subgrupo 1.1 da Lista Brasileira; a febre amarela não. As duas "
     "primeiras ressurgiram no período com a lista já as incluindo, o que "
     "indica que a limitação do instrumento não se resolve apenas "
     "acrescentando códigos. Fonte: Tabela S8."),
    ("3.9", "figura_06_teto_de_codificacao",
     "Óbitos por código da CID-10 segundo o agente etiológico seja nomeado "
     "(azul) ou não (cinza). Escala logarítmica. O teto de medição de doença "
     "bacteriana invasiva no Brasil é de codificação, não de epidemiologia. "
     "Fonte: Tabela S12."),
)

FIGURAS_DO_ARTIGO = [
    ("figura_01_serie_oficial", figura_01_serie_oficial),
    ("figura_02_panorama", figura_02_panorama),
    ("figura_03_corte_etario", figura_03_corte_etario),
    ("figura_04_composicao", figura_04_composicao),
    ("figura_05_eventos_fora_da_lista", figura_05_eventos),
    ("figura_06_teto_de_codificacao", figura_06_teto),
]


def main() -> None:
    _estilo()
    print(f"[figuras] artigo-imunopreveniveis — {len(FIGURAS_DO_ARTIGO)} figuras",
          flush=True)
    for _, fn in FIGURAS_DO_ARTIGO:
        fn()
    print("[ok] figuras geradas.")


if __name__ == "__main__":
    main()
