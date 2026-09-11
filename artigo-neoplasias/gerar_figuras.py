"""
gerar_figuras.py — as figuras do manuscrito, a partir dos mesmos CSVs das tabelas
=================================================================================

    .venv311/Scripts/python artigo-neoplasias/gerar_figuras.py

Lê `artigo-neoplasias/tabelas/*.csv` e grava PNG em 300 dpi em
`artigo-neoplasias/figuras/`. Nenhum valor é digitado aqui: se a análise mudar,
a figura muda junto, pela mesma razão que as tabelas do manuscrito são
sincronizadas em vez de copiadas.

AS TABELAS NÃO SAEM DO ARTIGO
------------------------------
A figura é a leitura; a tabela é o dado. As 22 tabelas continuam publicadas como
material suplementar, e cada legenda de figura aponta a tabela que a originou —
de modo que qualquer valor lido no gráfico pode ser conferido no número exato.
Substituir tabela por gráfico perderia precisão sem ganhar nada; acrescentar o
gráfico ganha a leitura sem perder a precisão.

DECISÕES DE COR, E POR QUE ELAS NÃO SÃO GOSTO
----------------------------------------------
* **Categórica** (identidade: taxa bruta × padronizada) usa os três primeiros
  slots de uma paleta validada para daltonismo — pior par ΔE 9,2 (deutan) e 24,0
  na visão normal, medido, não estimado.
* **Divergente** (polaridade: subiu × caiu, razão acima × abaixo de 1) usa
  azul↔vermelho com cinza no meio. Nunca arco-íris, e nunca uma cor no ponto
  neutro — o zero tem de parecer zero.
* Nenhuma figura tem dois eixos y. Onde duas grandezas de escala diferente
  precisam ser lidas juntas (§3.11), são dois painéis lado a lado com o mesmo
  eixo x, e não duas escalas empilhadas no mesmo desenho.
* Rótulos diretos onde a série é poucas: a cor identifica, o rótulo confirma, e
  nenhuma leitura depende de distinguir dois tons.

Depende de `matplotlib`. Uso: sem argumentos.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent
TABELAS = RAIZ / "tabelas"
FIGURAS = RAIZ / "figuras"

#: Paleta categórica validada (slots 1–3) e o par divergente. Ver o cabeçalho.
AZUL, LARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
VERMELHO = "#e34948"
#: Tinta do texto. Valor e rótulo NUNCA vestem a cor da série — quem carrega
#: identidade é a marca ao lado, não a letra.
TINTA, TINTA2 = "#0b0b0b", "#52514e"
GRADE = "#e3e2de"
NEUTRO = "#c9c8c3"

#: Largura útil de uma página A4 com margens de 2,5 cm, em polegadas. Toda
#: figura nasce nesta largura para não ser reescalada pelo Word — reescalar
#: depois é o que produz texto de eixo ilegível em artigo impresso.
LARGURA = 6.3


def _estilo() -> None:
    plt.rcParams.update({
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8.5,
        "axes.titlesize": 9.5,
        "axes.labelsize": 8.5,
        "axes.titleweight": "bold",
        "axes.edgecolor": NEUTRO,
        "axes.labelcolor": TINTA2,
        "axes.linewidth": 0.8,
        "xtick.color": TINTA2,
        "ytick.color": TINTA2,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
    })


def _ler(nome: str) -> pd.DataFrame:
    caminho = TABELAS / f"{nome}.csv"
    if not caminho.exists():
        raise SystemExit(
            f"{caminho.name} não existe. Rode `python artigo-neoplasias/gerar_tabelas.py` "
            "antes — a figura sai da tabela, e não de um número digitado aqui.")
    return pd.read_csv(caminho, encoding="utf-8-sig")


def _limpar(ax, *, eixo: str = "y") -> None:
    """Grade recessiva num eixo só, moldura aberta. O dado é a tinta forte."""
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis=eixo, color=GRADE, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)


def _virgula(ax, eixo: str, casas: int = 1) -> None:
    """Vírgula decimal nos ticks. O texto é em português; o eixo também é."""
    from matplotlib.ticker import FuncFormatter

    def _fmt(v, _):
        inteiro, _sep, dec = f"{v:,.{casas}f}".partition(".")
        inteiro = inteiro.replace(",", ".")
        return f"{inteiro},{dec}" if dec else inteiro

    fmt = FuncFormatter(_fmt)
    (ax.xaxis if eixo == "x" else ax.yaxis).set_major_formatter(fmt)


def _salvar(fig, nome: str) -> None:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    destino = FIGURAS / f"{nome}.png"
    fig.savefig(destino)
    plt.close(fig)
    kb = destino.stat().st_size / 1024
    print(f"[figura] {nome}.png — {kb:,.0f} kB", flush=True)


# ── figura 1 ────────────────────────────────────────────────────────────────

def figura_1_serie() -> None:
    """A tese do artigo num desenho: a contagem sobe, o risco não."""
    d = _ler("tabela_2_serie_nacional")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(LARGURA, 2.9))

    ax1.plot(d["Ano"], d["Óbitos"] / 1000, color=TINTA, linewidth=2,
             marker="o", markersize=4, markerfacecolor="white",
             markeredgewidth=1.4, zorder=3)
    ax1.set_title("A. Óbitos por câncer (milhares)", loc="left", color=TINTA)
    ax1.set_ylim(bottom=0)
    _limpar(ax1)

    # As variações são CALCULADAS da tabela, não digitadas. Cada série carrega a
    # sua no próprio rótulo: um número solto no meio do desenho não diz a qual
    # das três linhas pertence, e foi o que a primeira versão desta figura fez.
    def _var(col: str) -> str:
        v = 100 * (d[col].iloc[-1] / d[col].iloc[0] - 1)
        return f"{v:+.1f}%".replace(".", ",").replace("-", "−")

    ax1.text(0.04, 0.93, _var("Óbitos"), transform=ax1.transAxes,
             fontsize=11, color=TINTA, fontweight="bold", va="top")

    # As duas séries terminam a menos de 3 por 100 mil uma da outra — que é
    # exatamente o achado — e os rótulos se sobrepõem se ancorados no valor.
    # O deslocamento vertical é fixo e declarado, não ajustado no olho.
    for coluna, cor, dy in (("Taxa bruta", AQUA, 7),
                            ("Padronizada (Brasil)", AZUL, -7),
                            ("Padronizada (OMS)", LARANJA, 0)):
        ax2.plot(d["Ano"], d[coluna], color=cor, linewidth=2, zorder=3)
        # A marca colorida no fim da linha é o que liga o rótulo à série. Sem
        # ela a identidade dependeria só da proximidade, e duas das três linhas
        # terminam a menos de 3 por 100 mil uma da outra.
        ax2.plot(d["Ano"].iloc[-1], d[coluna].iloc[-1], "o", color=cor,
                 markersize=5, markeredgecolor="white", markeredgewidth=1.0,
                 zorder=4)
        # Rótulo direto: a paleta tem um slot abaixo de 3:1 contra o branco, e a
        # regra de alívio exige rótulo visível em vez de depender só da cor.
        ax2.annotate(f"{coluna.replace('Padronizada ', 'Padr. ')}  {_var(coluna)}",
                     xy=(d["Ano"].iloc[-1], d[coluna].iloc[-1]),
                     xytext=(4, dy), textcoords="offset points",
                     va="center", fontsize=7.5, color=TINTA2)
    ax2.set_title("B. Taxa por 100 mil habitantes", loc="left", color=TINTA)
    ax2.set_ylim(0, 145)
    ax2.set_xlim(d["Ano"].min(), d["Ano"].max() + 5.6)
    _limpar(ax2)

    for ax in (ax1, ax2):
        ax.set_xticks(list(range(int(d["Ano"].min()), int(d["Ano"].max()) + 1, 3)))
    fig.tight_layout(w_pad=2.0)
    _salvar(fig, "figura_01_serie_nacional")


# ── figura 2 ────────────────────────────────────────────────────────────────

def figura_2_decomposicao() -> None:
    """Cascata: de onde vêm os 53 mil óbitos a mais entre 2015 e 2024."""
    d = _ler("tabela_4_decomposicao")
    comp = d[d["Componente"].str.lower().str.startswith(("cresc", "envelh", "risco"))]
    total = d[d["Componente"].str.lower().str.startswith("varia")]["Óbitos"].iloc[0]

    rotulos = ["Crescimento\npopulacional", "Envelhecimento\n(estrutura etária)",
               "Risco\n(taxas por idade)", "Variação\ntotal"]
    valores = list(comp["Óbitos"]) + [total]

    fig, ax = plt.subplots(figsize=(LARGURA, 3.1))
    base = 0.0
    for i, v in enumerate(valores):
        final = i == len(valores) - 1
        inicio = 0.0 if final else base
        # Divergente: vermelho acrescenta morte, azul retira. O neutro é o zero,
        # e por isso ele é uma linha, não uma cor.
        cor = TINTA if final else (VERMELHO if v > 0 else AZUL)
        ax.bar(i, v, bottom=inicio, color=cor, width=0.62, zorder=3)
        alvo = inicio + v
        ax.annotate(f"{v:+,.0f}".replace(",", ".").replace("-", "−"),
                    xy=(i, alvo), xytext=(0, 5 if v > 0 else -13),
                    textcoords="offset points", ha="center",
                    fontsize=8.5, color=TINTA, fontweight="bold")
        if not final:
            base += v
            ax.plot([i + 0.31, i + 0.69], [base, base], color=NEUTRO,
                    linewidth=0.9, linestyle=(0, (3, 2)), zorder=2)

    ax.axhline(0, color=NEUTRO, linewidth=0.9, zorder=2)
    ax.set_xticks(range(len(rotulos)))
    ax.set_xticklabels(rotulos, fontsize=8)
    ax.set_ylabel("Óbitos")
    ax.set_ylim(0, 70_000)
    ax.set_yticks([0, 20_000, 40_000, 60_000])
    ax.set_yticklabels(["0", "20.000", "40.000", "60.000"])
    _limpar(ax)
    fig.tight_layout()
    _salvar(fig, "figura_04_decomposicao")


# ── figura 3 ────────────────────────────────────────────────────────────────

def figura_3_faixa() -> None:
    """Onde o risco subiu: duas faixas, e são as jovens."""
    d = _ler("tabela_3_taxa_por_faixa")
    fig, ax = plt.subplots(figsize=(LARGURA, 2.8))

    y = range(len(d))
    cores = [VERMELHO if v > 0 else AZUL for v in d["Variação (%)"]]
    ax.barh(list(y), d["Variação (%)"], color=cores, height=0.62, zorder=3)
    for i, v in enumerate(d["Variação (%)"]):
        ax.annotate(f"{v:+.1f}%".replace(".", ",").replace("-", "−"),
                    xy=(v, i), xytext=(5 if v > 0 else -5, 0),
                    textcoords="offset points", va="center",
                    ha="left" if v > 0 else "right",
                    fontsize=8, color=TINTA)
    ax.axvline(0, color=NEUTRO, linewidth=0.9, zorder=2)
    ax.set_yticks(list(y))
    ax.set_yticklabels(d["Faixa etária"])
    ax.invert_yaxis()
    ax.set_xlabel("Variação da taxa específica por idade, 2015 → 2024 (%)")
    ax.set_xlim(-16, 11)
    _limpar(ax, eixo="x")
    fig.tight_layout()
    _salvar(fig, "figura_02_variacao_por_faixa")


# ── figura 4 ────────────────────────────────────────────────────────────────

def figura_4_contragradiente() -> None:
    """Os dois gradientes, lado a lado. Nunca no mesmo eixo."""
    vul = _ler("tabela_9_vulnerabilidade")
    caso = _ler("tabela_20_obito_por_caso")
    rot = ["Q1\n(menos\nvulnerável)", "Q2", "Q3", "Q4\n(mais\nvulnerável)"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(LARGURA, 3.2))

    ax1.bar(range(4), vul["Taxa padronizada"], color=AZUL, width=0.6, zorder=3)
    for i, v in enumerate(vul["Taxa padronizada"]):
        ax1.annotate(f"{v:.1f}".replace(".", ","), xy=(i, v), xytext=(0, 4),
                     textcoords="offset points", ha="center", fontsize=8.5,
                     color=TINTA, fontweight="bold")
    ax1.set_title("A. Mortalidade padronizada\npor 100 mil habitantes",
                  loc="left", color=TINTA)
    ax1.set_ylim(0, 150)

    ax2.bar(range(4), caso["Padronizada por idade"], color=LARANJA,
            width=0.6, zorder=3)
    for i, v in enumerate(caso["Padronizada por idade"]):
        ax2.annotate(f"{v:.3f}".replace(".", ","), xy=(i, v), xytext=(0, 4),
                     textcoords="offset points", ha="center", fontsize=8.5,
                     color=TINTA, fontweight="bold")
    ax2.set_title("B. Óbitos por caso diagnosticado\n(padronizado por idade)",
                  loc="left", color=TINTA)
    ax2.set_ylim(0, 0.72)
    _virgula(ax2, "y")

    for ax in (ax1, ax2):
        ax.set_xticks(range(4))
        ax.set_xticklabels(rot, fontsize=7.5)
        _limpar(ax)
    fig.tight_layout(w_pad=2.2)
    _salvar(fig, "figura_07_contragradiente")


# ── figura 5 ────────────────────────────────────────────────────────────────

def figura_5_sitio_vulnerabilidade() -> None:
    """Razão Q4/Q1 da mortalidade por sítio: a dispersão que o agregado esconde."""
    d = _ler("tabela_10_sitio_por_vulnerabilidade").sort_values("Razão Q4/Q1")
    fig, ax = plt.subplots(figsize=(LARGURA, 5.4))

    y = list(range(len(d)))
    for i, (_, r) in enumerate(d.iterrows()):
        cor = VERMELHO if r["Razão Q4/Q1"] > 1 else AZUL
        ax.plot([1, r["Razão Q4/Q1"]], [i, i], color=cor, linewidth=1.6, zorder=3)
        ax.plot(r["Razão Q4/Q1"], i, "o", color=cor, markersize=5.5,
                markeredgecolor="white", markeredgewidth=0.8, zorder=4)

    # A linha de referência não leva rótulo: o eixo já diz que a grandeza é uma
    # razão, e a legenda diz o que é estar de cada lado. A nota que estava aqui
    # caía por cima do primeiro sítio.
    ax.axvline(1, color=TINTA2, linewidth=1.0, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['Sítio']} ({r['CID']})" for _, r in d.iterrows()],
                       fontsize=7.5)
    ax.set_xlabel("Razão entre a taxa padronizada do quartil mais vulnerável e a do menos")
    ax.set_xlim(0.2, 1.6)
    _virgula(ax, "x")
    _limpar(ax, eixo="x")

    ax.legend(handles=[
        Line2D([], [], color=VERMELHO, marker="o", linestyle="", markersize=5.5,
               label="mais mortalidade onde há mais vulnerabilidade"),
        Line2D([], [], color=AZUL, marker="o", linestyle="", markersize=5.5,
               label="menos mortalidade onde há mais vulnerabilidade")],
        loc="upper left", fontsize=7.5, labelcolor=TINTA2)
    fig.tight_layout()
    _salvar(fig, "figura_05_sitio_por_vulnerabilidade")


# ── figura 6 ────────────────────────────────────────────────────────────────

def figura_6_idoso_jovem() -> None:
    """Forest plot da razão idoso/jovem: onde o colo do útero cai na lista."""
    d = _ler("tabela_19_razao_sitio").sort_values("log2 da razão")
    ic = d["IC95%"].str.replace(",", ".", regex=False).str.split(" a ", expand=True)
    inf = ic[0].astype(float)
    sup = ic[1].astype(float)

    fig, ax = plt.subplots(figsize=(LARGURA, 8.2))
    y = list(range(len(d)))
    for i, (idx, r) in enumerate(d.iterrows()):
        destaque = r["causabas_3"] == "C53"
        cor = LARANJA if destaque else AZUL
        ax.plot([inf[idx], sup[idx]], [i, i], color=cor,
                linewidth=2.4 if destaque else 1.3, zorder=3)
        ax.plot(r["log2 da razão"], i, "o", color=cor,
                markersize=6 if destaque else 4.2,
                markeredgecolor="white", markeredgewidth=0.8, zorder=4)

    # O valor do capítulo inteiro vem da Tabela 18, não digitado aqui: é a mesma
    # regra da prosa do manuscrito — número sem tabela é número sem procedência.
    cap = _ler("tabela_18_razao_capitulo")
    neo = cap[cap["capitulo"] == "II"]["log2 da razão"].iloc[0]
    ax.axvline(neo, color=TINTA2, linewidth=1.0, linestyle=(0, (4, 2)), zorder=2)
    ax.annotate(f"capítulo das neoplasias\ncomo um todo: {neo:.2f}".replace(".", ","),
                xy=(neo, 1.2), xytext=(5, 0), textcoords="offset points",
                fontsize=7, color=TINTA2)

    ax.set_yticks(y)
    rotulos = [f"{r['Sítio']} ({r['causabas_3']})" for _, r in d.iterrows()]
    ax.set_yticklabels(rotulos, fontsize=7)
    for tick, (_, r) in zip(ax.get_yticklabels(), d.iterrows(), strict=True):
        if r["causabas_3"] == "C53":
            tick.set_color(TINTA)
            tick.set_fontweight("bold")
    ax.set_xlabel("Razão entre a mortalidade aos 60+ e a de 15–49 anos (log2), com IC95%")
    ax.set_xlim(1.2, 10.0)
    _virgula(ax, "x")
    _limpar(ax, eixo="x")
    fig.tight_layout()
    _salvar(fig, "figura_03_razao_idoso_jovem")


# ── figura 7 ────────────────────────────────────────────────────────────────

def figura_7_teste_reprovado() -> None:
    """O teste pré-especificado, e o desenho de como ele reprovou."""
    d = _ler("tabela_21_obito_por_caso_sitio")
    contraste = _ler("tabela_22_contraste_deteccao")
    grupos = ["depende de detecção", "apresentação clínica"]
    cores = {"depende de detecção": AZUL, "apresentação clínica": LARANJA}

    fig, ax = plt.subplots(figsize=(LARGURA, 2.6))
    for j, g in enumerate(grupos):
        sub = d[d["Grupo pré-especificado"] == g]
        ax.plot(sub["Razão Q4/Q1"], [j] * len(sub), "o", color=cores[g],
                markersize=7, markeredgecolor="white", markeredgewidth=1.0,
                alpha=0.9, zorder=4)
        # Só o grupo de detecção é rotulado, e só os dois que FOGEM da mediana
        # dele: são o colo do útero e a próstata, o argumento do artigo. Rotular
        # também o grupo clínico marcaria pontos que estão onde se esperava.
        # Os dois quase coincidem no eixo, então os rótulos se alternam de lado
        # em vez de empilhar — foi o que os fez sair impressos um sobre o outro.
        if g == "depende de detecção":
            fora = sub[sub["Razão Q4/Q1"] > 1.3].sort_values("Razão Q4/Q1")
            for k, (_, r) in enumerate(fora.iterrows()):
                ax.annotate(r["CID"], xy=(r["Razão Q4/Q1"], j),
                            xytext=(-16 if k % 2 == 0 else 16, 9),
                            textcoords="offset points", ha="center",
                            fontsize=7.5, color=TINTA, fontweight="bold")
        med = contraste[contraste["Grupo pré-especificado"] == g][
            "Razão Q4/Q1 mediana"].iloc[0]
        ax.plot([med, med], [j - 0.26, j + 0.26], color=TINTA,
                linewidth=2.0, zorder=5)
        ax.annotate(f"mediana {med:.3f}".replace(".", ","),
                    xy=(med, j + 0.30), ha="center", fontsize=7.5, color=TINTA)

    ax.axvline(1, color=NEUTRO, linewidth=1.0, zorder=2)
    ax.set_yticks(range(len(grupos)))
    ax.set_yticklabels(["Depende de detecção\n(rastreamento ou imagem)",
                        "Apresentação clínica\n(sintomático de qualquer forma)"],
                       fontsize=8)
    ax.set_ylim(-0.55, 1.62)
    ax.set_xlabel("Razão Q4/Q1 dos óbitos por caso diagnosticado, por sítio")
    ax.set_xlim(0.75, 1.55)
    _virgula(ax, "x", 2)
    _limpar(ax, eixo="x")
    # A nota não pode se referir a "grupo de cima": a previsão era sobre os
    # dependentes de detecção, e nomear a posição em vez do grupo já trocou o
    # sentido da frase uma vez.
    ax.annotate("previsão: razão MAIOR nos dependentes de detecção — deu o oposto",
                xy=(0.76, 1.55), fontsize=7.5, color=TINTA2, va="top")
    fig.tight_layout()
    _salvar(fig, "figura_08_teste_pre_especificado")


# ── figura 8 ────────────────────────────────────────────────────────────────

def figura_8_raca() -> None:
    """A inversão por cor/raça: o agregado e o colo do útero em painéis."""
    geral = _ler("tabela_11_raca").sort_values("Taxa padronizada", ascending=False)
    sitio = _ler("tabela_12_sitio_por_raca")
    colo = sitio[sitio["Sítio"].str.startswith("Colo")].sort_values(
        "Taxa padronizada", ascending=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(LARGURA, 3.0))

    ax1.barh(range(len(geral)), geral["Taxa padronizada"], color=AZUL,
             height=0.62, zorder=3)
    ax1.set_yticks(range(len(geral)))
    ax1.set_yticklabels(geral["Cor ou raça"], fontsize=8)
    ax1.invert_yaxis()
    ax1.set_title("A. Todas as neoplasias malignas", loc="left", color=TINTA)
    ax1.set_xlim(0, 158)
    for i, v in enumerate(geral["Taxa padronizada"]):
        ax1.annotate(f"{v:.1f}".replace(".", ","), xy=(v, i), xytext=(4, 0),
                     textcoords="offset points", va="center", fontsize=7.5,
                     color=TINTA)

    ax2.barh(range(len(colo)), colo["Taxa padronizada"], color=LARANJA,
             height=0.62, zorder=3)
    ax2.set_yticks(range(len(colo)))
    ax2.set_yticklabels(colo["Cor ou raça"], fontsize=8)
    ax2.invert_yaxis()
    ax2.set_title("B. Colo do útero (C53)", loc="left", color=TINTA)
    ax2.set_xlim(0, 13)
    for i, v in enumerate(colo["Taxa padronizada"]):
        ax2.annotate(f"{v:.2f}".replace(".", ","), xy=(v, i), xytext=(4, 0),
                     textcoords="offset points", va="center", fontsize=7.5,
                     color=TINTA)

    for ax in (ax1, ax2):
        ax.set_xlabel("Taxa padronizada por 100 mil")
        _limpar(ax, eixo="x")
    fig.tight_layout(w_pad=1.6)
    _salvar(fig, "figura_06_cor_raca")


FIGURAS_DO_ARTIGO = (
    figura_1_serie, figura_2_decomposicao, figura_3_faixa,
    figura_4_contragradiente, figura_5_sitio_vulnerabilidade,
    figura_6_idoso_jovem, figura_7_teste_reprovado, figura_8_raca,
)


def _empacotar() -> None:
    """Zip das figuras, montado no MESMO passo que as desenha.

    Mesma razão do `tabelas-do-artigo.zip`: pacote feito à mão envelhece
    sozinho, e quem recebe o anexo fica com figura diferente da do manuscrito
    da mesma mensagem, sem nada indicando isso.
    """
    import zipfile
    pngs = sorted(FIGURAS.glob("figura_*.png"))
    alvo = FIGURAS.parent / "figuras-do-artigo.zip"
    with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
        for p in pngs:
            z.write(p, p.name)
    print(f"[pacote] {alvo.name}: {len(pngs)} PNGs, {alvo.stat().st_size:,} bytes",
          flush=True)


def main() -> None:
    _estilo()
    for f in FIGURAS_DO_ARTIGO:
        f()
    _empacotar()
    print(f"\n[done] {len(FIGURAS_DO_ARTIGO)} figuras em "
          f"{FIGURAS.relative_to(RAIZ.parent).as_posix()}")


if __name__ == "__main__":
    main()
