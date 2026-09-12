"""
gerar_figuras_painel.py — as figuras da reanálise em painel
============================================================

    .venv311/Scripts/python artigo-agua/gerar_figuras_painel.py

Lê `data/analises/agua-painel/*.csv` e escreve `artigo-agua/figuras/*.png`.
Nenhuma conta acontece aqui, pela mesma razão do outro gerador: se aparecer uma
divisão neste arquivo, ela está no lugar errado. A figura é leitura do que a
tabela já diz.

POR QUE ESTAS FIGURAS, E NÃO AS OUTRAS
---------------------------------------
As figuras do desenho transversal desenhavam a razão de razões contra o controle
negativo. O painel de efeitos fixos mede outra coisa — a variação DENTRO do
município ao longo do tempo —, e a comparação que importa passou a ser entre
**o mesmo estimador com e sem o efeito fixo**. Figura que não mostra as duas
colunas esconde justamente o que a reanálise descobriu.

A FIGURA DO MEIO É A QUE CARREGA O ARTIGO
------------------------------------------
`figura_p2_com_e_sem_efeito_fixo` põe, para cada causa, o IRR estimado sem
efeito fixo ao lado do estimado com efeito fixo, ligados por uma seta. O
comprimento da seta é a parte da associação que era diferença **entre**
municípios — confundimento não medido, absorvido pelo intercepto. Desenhar isso
é mais honesto que reportar apenas o número final, porque mostra o tamanho do
que foi descartado.

A LINHA DO ZERO DESTE ARTIGO É O 1
-----------------------------------
Todas as figuras de razão marcam o 1 com linha cinza e rótulo. A pergunta do
artigo é se alguma coisa se afasta dele, e razão desenhada sem o 1 deixa o
leitor estimar a referência de cabeça.

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
ANALISE = RAIZ.parent / "data" / "analises" / "agua-painel"
FIGURAS = RAIZ / "figuras"

AZUL, LARANJA = "#2a78d6", "#eb6834"
VERMELHO = "#e34948"
TINTA, TINTA2 = "#0b0b0b", "#52514e"
GRADE = "#e3e2de"
NEUTRO = "#c9c8c3"
LARGURA = 6.3

#: Rótulo curto por grupo de causa. O nome longo da análise não cabe no eixo, e
#: abreviar na figura — em vez de na análise — mantém o CSV legível sozinho.
CURTO = {
    "A00-A09 intestinais (hipotese)": "A00–A09\nintestinais",
    "J00-J22 respiratorias (subgrupo 1.2)": "J00–J22\nrespiratórias",
    "outras infecciosas do subgrupo 1.2": "outras infecciosas\ndo subgrupo 1.2",
    "I20-I25 isquemicas do coracao": "I20–I25\nisquêmicas",
    "V01-Y98 causas externas": "V01–Y98\ncausas externas",
}


def _base(fig, ax) -> None:
    """Moldura comum: sem caixa, grade discreta, tinta escura."""
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRADE)
    ax.tick_params(colors=TINTA2, labelsize=8, length=3)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")


def _linha_do_um(ax, horizontal: bool = False) -> None:
    """Marca o 1 e o rotula. O 1 é o nada deste artigo."""
    if horizontal:
        ax.axhline(1.0, color=NEUTRO, lw=1.0, zorder=0)
    else:
        ax.axvline(1.0, color=NEUTRO, lw=1.0, zorder=0)


def _ler(nome: str) -> pd.DataFrame:
    caminho = ANALISE / f"{nome}.csv"
    if not caminho.exists():
        raise SystemExit(
            f"{caminho} não existe. Rode `scripts/analise_agua_painel.py` "
            "antes: a figura não inventa o número que falta.")
    return pd.read_csv(caminho)


def fig1_especificidade() -> str:
    """Os cinco IRR do painel, com IC95%, ordenados como a análise os produziu."""
    d = _ler("tab02_especificidade")
    fig, ax = plt.subplots(figsize=(LARGURA, 3.2), dpi=300)
    _base(fig, ax)
    _linha_do_um(ax)

    y = range(len(d))[::-1]
    for yi, (_, r) in zip(y, d.iterrows()):
        hipotese = r["Grupo de causa"].endswith("(hipotese)")
        cor = VERMELHO if hipotese else TINTA2
        ax.plot([r["IC95% inferior"], r["IC95% superior"]], [yi, yi],
                color=cor, lw=1.6, solid_capstyle="butt", zorder=2)
        ax.plot([r["IRR"]], [yi], "o", color=cor, ms=6, zorder=3,
                markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate(f"{r['IRR']:.3f}  [{r['IC95% inferior']:.3f}, "
                    f"{r['IC95% superior']:.3f}]",
                    (r["IC95% superior"], yi), xytext=(7, 0),
                    textcoords="offset points", va="center", fontsize=7.5,
                    color=cor)

    ax.set_yticks(list(y))
    ax.set_yticklabels([CURTO.get(g, g) for g in d["Grupo de causa"]], fontsize=7.5)
    ax.set_xlabel("IRR da ausência de vigilância no ano anterior (escala log)",
                  fontsize=8, color=TINTA)
    ax.set_xscale("log")
    ax.set_xlim(0.80, 1.45)
    ax.set_xticks([0.85, 0.9, 1.0, 1.1, 1.2])
    ax.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_title("Marcador vermelho: a causa da hipótese hídrica",
                 fontsize=8, color=TINTA2, loc="left", pad=8)
    fig.tight_layout()
    nome = "figura_p1_especificidade.png"
    fig.savefig(FIGURAS / nome, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nome


def fig2_com_e_sem_efeito_fixo() -> str:
    """A figura que carrega o artigo: o que o efeito fixo remove, por causa."""
    d = _ler("tab03_efeito_fixo")
    fig, ax = plt.subplots(figsize=(LARGURA, 3.4), dpi=300)
    _base(fig, ax)
    _linha_do_um(ax)

    y = list(range(len(d)))[::-1]
    for yi, (_, r) in zip(y, d.iterrows()):
        sem, com = r["IRR sem efeito fixo"], r["IRR com efeito fixo"]
        hipotese = r["Grupo de causa"].endswith("(hipotese)")
        cor = VERMELHO if hipotese else TINTA2
        ax.annotate("", xy=(com, yi), xytext=(sem, yi),
                    arrowprops={"arrowstyle": "-|>", "color": cor,
                                "lw": 1.3, "shrinkA": 3, "shrinkB": 3})
        ax.plot([sem], [yi], "o", color="white", ms=7, zorder=3,
                markeredgecolor=cor, markeredgewidth=1.3)
        ax.plot([com], [yi], "o", color=cor, ms=7, zorder=3,
                markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate(f"{sem:.3f}", (sem, yi), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=7,
                    color=cor)
        ax.annotate(f"{com:.3f}", (com, yi), xytext=(0, -14),
                    textcoords="offset points", ha="center", fontsize=7,
                    color=cor)

    ax.set_yticks(y)
    ax.set_yticklabels([CURTO.get(g, g) for g in d["Grupo de causa"]], fontsize=7.5)
    # folga vertical: o rotulo da ultima linha e' desenhado 14 pontos ABAIXO do
    # marcador, e sem esta margem ele cai sobre o eixo x
    ax.set_ylim(-0.75, len(d) - 0.4)
    ax.set_xlabel("IRR: marcador vazado sem efeito fixo, cheio com efeito fixo "
                  "de município", fontsize=8, color=TINTA)
    ax.set_title("O comprimento da seta é a associação que era diferença ENTRE "
                 "municípios", fontsize=8, color=TINTA2, loc="left", pad=8)
    fig.tight_layout()
    nome = "figura_p2_com_e_sem_efeito_fixo.png"
    fig.savefig(FIGURAS / nome, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nome


def fig3_tendencia() -> str:
    """Observado contra a tendencia 2015-2019, nos DOIS denominadores.

    Dois paineis lado a lado, com o mesmo eixo x e escalas y proprias — e nao
    um grafico com dois eixos y, que a disciplina de cor deste artigo proibe:
    duas escalas no mesmo quadro deixam o leitor comparar alturas que nao sao
    comparaveis. Aqui a comparacao que importa e' de CADA serie com a sua
    propria projecao, e isso cada painel mostra sozinho.
    """
    d = _ler("tab04_tendencia")
    fig, eixos = plt.subplots(1, 2, figsize=(LARGURA, 2.9), dpi=300)
    base = d["Base do ajuste"] == "sim"
    fim = int(d.loc[base, "Ano"].max())

    for ax, (obs, proj, rotulo) in zip(eixos, (
            ("Observado por 10 mil obitos", "Projetado por 10 mil obitos",
             "por 10 mil óbitos do ano"),
            ("Observado por milhao de habitantes",
             "Projetado por milhao de habitantes",
             "por milhão de habitantes"))):
        _base(fig, ax)
        ax.axvspan(fim + 0.5, d["Ano"].max() + 0.4, color=GRADE, alpha=0.45,
                   zorder=0)
        ax.plot(d["Ano"], d[proj], "--", color=NEUTRO, lw=1.3, zorder=1,
                label="projeção de 2015–2019")
        ax.plot(d["Ano"], d[obs], "-", color=AZUL, lw=1.7, zorder=2,
                label="observado")
        ax.plot(d.loc[base, "Ano"], d.loc[base, obs], "o", color=AZUL, ms=4,
                zorder=3, markeredgecolor="white", markeredgewidth=0.7)
        ax.plot(d.loc[~base, "Ano"], d.loc[~base, obs], "o", color=LARANJA,
                ms=4, zorder=3, markeredgecolor="white", markeredgewidth=0.7)
        ax.set_title(rotulo, fontsize=8, color=TINTA, loc="left", pad=6)
        ax.set_xlabel("Ano", fontsize=8, color=TINTA)
        ax.set_xticks([2015, 2018, 2021, 2024])

    eixos[0].set_ylabel("Óbitos por A00–A09", fontsize=8, color=TINTA)
    eixos[0].legend(frameon=False, fontsize=7, loc="lower left")
    eixos[1].annotate("faixa sombreada:\nfora da base do ajuste",
                      (fim + 0.7, eixos[1].get_ylim()[1]), xytext=(0, -4),
                      textcoords="offset points", fontsize=6.5, color=TINTA2,
                      va="top")
    fig.tight_layout()
    nome = "figura_p3_tendencia.png"
    fig.savefig(FIGURAS / nome, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nome


def fig4_robustez() -> str:
    """O IRR da hipótese em cada recorte, com o painel completo destacado."""
    d = _ler("tab05_robustez")
    fig, ax = plt.subplots(figsize=(LARGURA, 0.34 * len(d) + 1.5), dpi=300)
    _base(fig, ax)
    _linha_do_um(ax)

    y = list(range(len(d)))[::-1]
    for yi, (_, r) in zip(y, d.iterrows()):
        completo = r["Recorte"] == "Painel completo"
        cor = VERMELHO if completo else TINTA2
        ax.plot([r["IC95% inferior"], r["IC95% superior"]], [yi, yi],
                color=cor, lw=1.5, solid_capstyle="butt", zorder=2)
        ax.plot([r["IRR"]], [yi], "o", color=cor, ms=5.5, zorder=3,
                markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate(f"{r['IRR']:.3f}", (r["IC95% superior"], yi), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=7,
                    color=cor)

    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['Recorte']}  (n={r['Municipios']:,})"
                        .replace(",", ".") for _, r in d.iterrows()],
                       fontsize=7.5)
    ax.set_xlabel("IRR da ausência de vigilância, óbitos por A00–A09",
                  fontsize=8, color=TINTA)
    ax.set_title("Marcador vermelho: o painel completo", fontsize=8,
                 color=TINTA2, loc="left", pad=8)
    fig.tight_layout()
    nome = "figura_p4_robustez.png"
    fig.savefig(FIGURAS / nome, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return nome


#: (seção do manuscrito, nome do arquivo sem extensão, legenda).
#:
#: `artigo/gerar_docx.py` le esta tupla — do `gerar_figuras.py` da pasta, que
#: concatena esta aqui — para saber em que seção cada figura entra no Word.
#: Sem a seção, as figuras sairiam soltas no fim, longe do texto que as
#: discute. A legenda vive junto do desenho porque mover uma sem a outra é o
#: modo de as duas discordarem.
LEGENDAS: tuple[tuple[str, str, str], ...] = (
    ("3.3", "figura_p1_especificidade",
     "Razão de taxas (IRR) da ausência de registro de vigilância da água no "
     "ano anterior, por grupo de causa, em Poisson condicional de efeitos "
     "fixos de município com indicadoras de ano. IC95% por bootstrap de "
     "município (400 reamostragens). Fonte: Tabela P2."),
    ("3.4", "figura_p2_com_e_sem_efeito_fixo",
     "O mesmo IRR estimado sem e com efeito fixo de município. O marcador "
     "vazado é a estimativa que compara municípios entre si; o cheio, a que "
     "compara cada município consigo mesmo ao longo do tempo. O comprimento "
     "da seta é a parte da associação atribuível a diferenças fixas entre "
     "municípios. Fonte: Tabela P3."),
    ("3.1", "figura_p3_tendencia",
     "Óbitos por doenças infecciosas intestinais (A00–A09), observados e "
     "projetados a partir da tendência log-linear ajustada apenas em 2015 a "
     "2019, em dois denominadores: por 10 mil óbitos do ano (esquerda) e por "
     "milhão de habitantes (direita). O primeiro cancela sub-registro e é "
     "sensível à inflação do denominador pela COVID-19 em 2020 e 2021; o "
     "segundo, o contrário. A faixa sombreada está fora da base do ajuste. "
     "Fonte: Tabela P4."),
    ("3.6", "figura_p4_robustez",
     "IRR da ausência de vigilância sobre a mortalidade por A00–A09 em cada "
     "recorte de sensibilidade, incluindo a exclusão do Distrito Federal e "
     "dos municípios com menos de 5.000 habitantes. Fonte: Tabela P5."),
)


def main() -> None:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    feitas = [fig1_especificidade(), fig2_com_e_sem_efeito_fixo(),
              fig3_tendencia(), fig4_robustez()]
    if [f"{n}.png" for _, n, _ in LEGENDAS] != feitas:
        raise SystemExit(
            f"as legendas não correspondem às figuras desenhadas.\n"
            f"  desenhadas: {feitas}\n  em LEGENDAS: {[n for n, _ in LEGENDAS]}\n"
            "Legenda apontando para a figura errada passa em qualquer revisão, "
            "e é por isso que a conferência é automática.")
    for nome in feitas:
        kb = (FIGURAS / nome).stat().st_size // 1024
        print(f"[fig] {nome} — {kb} kB")
    print(f"[ok] {len(feitas)} figuras em {FIGURAS.relative_to(RAIZ.parent)}")


if __name__ == "__main__":
    main()
