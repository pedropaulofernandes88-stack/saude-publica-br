"""
gerar_figuras.py — as cinco figuras do artigo da água
======================================================

    .venv311/Scripts/python artigo-agua/gerar_figuras.py

Lê `artigo-agua/tabelas/*.csv` e escreve `artigo-agua/figuras/*.png`. Nenhuma
conta acontece aqui: se aparecer uma divisão neste arquivo, ela está no lugar
errado. A figura é leitura do que a tabela já diz — e cada legenda aponta a
tabela que a originou, para que qualquer valor lido no gráfico possa ser
conferido no número exato.

DECISÕES DE COR, E POR QUE NÃO SÃO GOSTO
-----------------------------------------
Mesma disciplina do artigo de neoplasias, pelas mesmas razões:

* **Divergente** (polaridade: razão acima × abaixo de 1) usa azul↔vermelho com
  cinza no meio. O valor 1 tem de parecer neutro, porque ele é o nada.
* **Categórica** (identidade: hídrica × respiratória) usa dois slots de paleta
  validada para daltonismo. As duas séries deste artigo são exatamente as duas
  entradas do subgrupo 1.2 da Lista, então a cor carrega a comparação inteira.
* Nenhuma figura tem dois eixos y. Onde duas grandezas de escala diferente
  precisam ser lidas juntas, são painéis lado a lado com o mesmo eixo x.
* Rótulo direto onde as séries são poucas: a cor identifica, o rótulo confirma,
  e nenhuma leitura depende de distinguir dois tons.

A LINHA DO ZERO DESTE ARTIGO É O 1
-----------------------------------
Três das cinco figuras mostram razões. Em todas elas o 1 é marcado com linha
cinza e rótulo — não como enfeite, mas porque a pergunta do artigo é se alguma
coisa se afasta dele. Gráfico de razão sem o 1 desenhado deixa o leitor estimar
a referência de cabeça, e é assim que se lê diferença onde não há.

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

AZUL, LARANJA = "#2a78d6", "#eb6834"
VERMELHO = "#e34948"
TINTA, TINTA2 = "#0b0b0b", "#52514e"
GRADE = "#e3e2de"
NEUTRO = "#c9c8c3"
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
            f"[figuras] falta {caminho.relative_to(RAIZ.parent)}. "
            "Rode `python artigo-agua/gerar_tabelas.py` antes.")
    return pd.read_csv(caminho)


def _br(v: float, casas: int = 2) -> str:
    """Número no padrão brasileiro: decimal com vírgula, milhar com ponto."""
    return f"{v:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _limpar(ax, eixo_y: bool = True) -> None:
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    if eixo_y:
        ax.grid(axis="y", color=GRADE, linewidth=0.7, zorder=0)
        ax.set_axisbelow(True)


def _salvar(fig, nome: str) -> None:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    destino = FIGURAS / f"{nome}.png"
    fig.savefig(destino)
    plt.close(fig)
    print(f"   {destino.relative_to(RAIZ.parent)}", flush=True)


# ── 1. a série que motiva o artigo ─────────────────────────────────────────
def figura_01_serie() -> None:
    """A alta de A00–A09, com o ano preliminar marcado e não escondido."""
    d = _ler("tabela_2_serie_anual")
    ano = d["Ano"].astype(int)
    val = d["A00-A09"].astype(float)
    prelim = d["Ano preliminar"].astype(str).str.lower().isin(["true", "sim", "1"])

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(LARGURA, 2.7))
    for ax, y, rot in ((a1, val, "Óbitos por A00–A09"),
                       (a2, d["A00-A09 por 10 mil óbitos"].astype(float),
                        "A00–A09 por 10 mil óbitos")):
        cons, pre = ~prelim, prelim
        ax.plot(ano[cons], y[cons], "-o", color=AZUL, lw=1.6, ms=3.4, zorder=3)
        if pre.any():
            # O preliminar NÃO é escondido nem somado à série sólida: ele entra
            # pontilhado e vazado. Omiti-lo esconderia o dado mais recente;
            # colá-lo na linha afirmaria consolidação que não existe.
            liga = [ano[cons].iloc[-1], ano[pre].iloc[0]]
            ligay = [y[cons].iloc[-1], y[pre].iloc[0]]
            ax.plot(liga, ligay, ":", color=AZUL, lw=1.2, zorder=2)
            ax.plot(ano[pre], y[pre], "o", mfc="white", mec=AZUL, ms=3.4, zorder=3)
        ax.set_ylabel(rot)
        ax.set_xticks([2015, 2018, 2021, 2024])
        _limpar(ax)

    a1.annotate("2020–21\npandemia", xy=(2021, val[ano == 2021].iloc[0]),
                xytext=(2018.4, val.min() * 0.86), fontsize=7.2, color=TINTA2,
                ha="center", arrowprops=dict(arrowstyle="-", color=NEUTRO, lw=0.8))
    a1.annotate("2025\npreliminar", xy=(2025, val[ano == 2025].iloc[0]),
                xytext=(2022.6, val.max() * 1.02), fontsize=7.2, color=TINTA2,
                ha="center", arrowprops=dict(arrowstyle="-", color=NEUTRO, lw=0.8))
    fig.suptitle("Óbitos por doenças infecciosas intestinais, Brasil, 2015–2025",
                 fontsize=9.8, fontweight="bold", color=TINTA, y=1.03)
    _salvar(fig, "figura_01_serie_nacional")


# ── 2. a alta é de todas as idades ─────────────────────────────────────────
def figura_02_por_faixa() -> None:
    """Se fosse envelhecimento, a alta seria dos idosos. Não é."""
    d = _ler("tabela_3_alta_por_faixa")
    fx = d["Faixa etária"].astype(str)
    var = d["Variação %"].astype(float)
    cor = [AZUL if v >= 0 else VERMELHO for v in var]

    fig, ax = plt.subplots(figsize=(LARGURA, 2.6))
    ax.bar(fx, var, color=cor, width=0.66, zorder=3)
    ax.axhline(0, color=NEUTRO, lw=0.9, zorder=2)
    for i, v in enumerate(var):
        ax.text(i, v + (1.6 if v >= 0 else -3.4), f"{v:+.0f}%".replace(".", ","),
                ha="center", fontsize=7.4, color=TINTA2)
    ax.set_ylabel("Variação 2019 → 2024")
    ax.set_ylim(min(0, var.min()) * 1.28, var.max() * 1.22)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.0f}%")
    _limpar(ax)
    ax.set_title("A alta não é de uma faixa etária: é de quase todas",
                 color=TINTA, loc="left")
    _salvar(fig, "figura_02_alta_por_faixa")


# ── 3. o gradiente das quatro classes ──────────────────────────────────────
def figura_03_gradiente() -> None:
    """As duas causas do subgrupo 1.2, lado a lado, contra a vigilância."""
    d = _ler("tabela_7_gradiente")
    cl = [c.replace(" (", "\n(") for c in d["Classe de vigilância"].astype(str)]
    x = range(len(cl))
    larg = 0.36

    fig, ax = plt.subplots(figsize=(LARGURA, 2.9))
    ax.bar([i - larg / 2 for i in x], d["RR A00-A09"].astype(float), larg,
           color=AZUL, label="A00–A09 (via hídrica)", zorder=3)
    ax.bar([i + larg / 2 for i in x], d["RR respiratória"].astype(float), larg,
           color=LARANJA, label="Infecção respiratória (controle)", zorder=3)
    ax.axhline(1, color=TINTA2, lw=0.9, ls="--", zorder=4)
    ax.text(len(cl) - 0.42, 1.02, "referência", fontsize=7, color=TINTA2, ha="right")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cl, fontsize=7.4)
    ax.set_ylabel("Razão contra vigilância regular")
    ax.legend(loc="upper right", ncols=1)
    _limpar(ax)
    ax.set_title("Duas causas do MESMO subgrupo da Lista Brasileira,\n"
                 "e só uma responde à ausência de vigilância da água",
                 color=TINTA, loc="left")
    _salvar(fig, "figura_03_gradiente")


# ── 4. os quatro critérios ─────────────────────────────────────────────────
def figura_04_criterios() -> None:
    """O gráfico que deixa a refutação visível: se o IC cruza 1, caiu."""
    d = _ler("tabela_8_criterios")
    nomes = [n.replace(" (", "\n(") for n in d["Critério"].astype(str)]
    v = d["RRR"].astype(float)
    lo = d["IC95% inferior"].astype(float)
    hi = d["IC95% superior"].astype(float)
    pre = d["Pré-declarado"].astype(str).str.lower().eq("sim")
    y = list(range(len(d)))[::-1]

    fig, ax = plt.subplots(figsize=(LARGURA, 2.5))
    ax.axvline(1, color=VERMELHO, lw=1.0, ls="--", zorder=2)
    ax.text(1.02, len(d) - 0.42, "RRR = 1\nrefuta", fontsize=7, color=VERMELHO)
    for i, yy in enumerate(y):
        # Pré-declarado é cheio; post-hoc é vazado. A distinção é a informação
        # mais importante da figura, e por isso está na FORMA, não na legenda.
        ax.plot([lo.iloc[i], hi.iloc[i]], [yy, yy], color=AZUL, lw=1.6, zorder=3)
        ax.plot(v.iloc[i], yy, "o", ms=6, zorder=4, color=AZUL if pre.iloc[i] else "white",
                mec=AZUL, mew=1.4)
        ax.text(hi.iloc[i] + 0.06, yy,
                f"{_br(v.iloc[i])}  [{_br(lo.iloc[i])}–{_br(hi.iloc[i])}]",
                va="center", fontsize=7.2, color=TINTA2)
    ax.set_yticks(y)
    ax.set_yticklabels(nomes, fontsize=7.4)
    ax.set_xlabel("Razão de razões (A00–A09 ÷ respiratória)")
    ax.set_xlim(0.9, hi.max() * 1.55)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRADE, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Marcador cheio = critério declarado antes; vazado = post-hoc",
                 color=TINTA, loc="left", fontsize=8.6)
    _salvar(fig, "figura_04_criterios")


# ── 5. o formato por idade ─────────────────────────────────────────────────
def figura_05_rrr_por_idade() -> None:
    """O que convence não é o total: é o pico onde a água mata criança."""
    d = _ler("tabela_9_rrr_por_idade")
    fx = d["Faixa etária"].astype(str)
    rrr = d["RRR"].astype(float)
    cor = [AZUL if v >= 1 else VERMELHO for v in rrr]

    fig, ax = plt.subplots(figsize=(LARGURA, 2.6))
    ax.bar(fx, rrr, color=cor, width=0.66, zorder=3)
    ax.axhline(1, color=TINTA2, lw=0.9, ls="--", zorder=4)
    for i, v in enumerate(rrr):
        ax.text(i, v + 0.045, _br(v), ha="center", fontsize=7.4, color=TINTA2)
    ax.set_ylabel("RRR dentro da faixa")
    ax.set_ylim(0, rrr.max() * 1.2)
    _limpar(ax)
    ax.set_title("Razão de razões dentro de cada faixa etária\n"
                 "(idade não pode explicar o que aparece em todas)",
                 color=TINTA, loc="left")
    _salvar(fig, "figura_05_rrr_por_idade")


#: Onde cada figura entra no .docx, e o que a legenda diz. A chave é o começo do
#: título da seção que a discute; a figura é inserida no FIM dessa seção. Mora
#: aqui, e não no gerador de Word, porque é aqui que a figura é mantida — quem
#: muda o desenho vê a legenda ao lado e não a deixa envelhecer sozinha.
LEGENDAS: tuple[tuple[str, str, str], ...] = (
    ("3.1", "figura_01_serie_nacional",
     "Óbitos por doenças infecciosas intestinais (CID-10 A00–A09), Brasil, "
     "2015–2025. (A) Contagem anual. (B) Óbitos por 10 mil óbitos do ano. O ano "
     "de 2025 é preliminar e aparece com marcador vazado e linha pontilhada; "
     "ele não entra em nenhuma estimativa. Fonte: Tabela S2."),
    ("3.2", "figura_02_alta_por_faixa",
     "Variação dos óbitos por A00–A09 entre 2019 e 2024, por faixa etária. A "
     "alta aparece em todas as faixas, o que afasta envelhecimento populacional "
     "como explicação. Fonte: Tabela S3."),
    ("3.4", "figura_03_gradiente",
     "Razão de mortalidade contra a classe de vigilância regular, para as duas "
     "entradas do subgrupo 1.2 da Lista Brasileira: doenças infecciosas "
     "intestinais (via hídrica) e infecções respiratórias (controle negativo). "
     "As duas causas são declaradas evitáveis pelo mesmo tipo de ação no "
     "instrumento oficial. Fonte: Tabela S7."),
    ("3.5", "figura_04_criterios",
     "Razão de razões e intervalo de confiança de 95% por bootstrap de "
     "município. Marcador cheio indica critério declarado antes da análise; "
     "marcador vazado indica teste post-hoc. A linha tracejada em 1 é o valor "
     "que refuta a interpretação hídrica. Fonte: Tabela S8."),
    ("3.7", "figura_05_rrr_por_idade",
     "Razão de razões dentro de cada faixa etária, o que neutraliza a "
     "composição etária sem exigir denominador populacional por idade. O valor "
     "é maior que 1 nas oito faixas, com o máximo em crianças de 1 a 4 anos. "
     "Fonte: Tabela S9."),
)

FIGURAS_DO_ARTIGO = [
    ("figura_01_serie_nacional", figura_01_serie),
    ("figura_02_alta_por_faixa", figura_02_por_faixa),
    ("figura_03_gradiente", figura_03_gradiente),
    ("figura_04_criterios", figura_04_criterios),
    ("figura_05_rrr_por_idade", figura_05_rrr_por_idade),
]


def main() -> None:
    _estilo()
    print(f"[figuras] artigo-agua — {len(FIGURAS_DO_ARTIGO)} figuras", flush=True)
    for _, fn in FIGURAS_DO_ARTIGO:
        fn()
    print("[ok] figuras geradas.")


if __name__ == "__main__":
    main()
