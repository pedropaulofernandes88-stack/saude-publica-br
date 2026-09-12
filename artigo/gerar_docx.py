"""
gerar_docx.py — o manuscrito em Word, sem identificação de autoria
===================================================================

    .venv311/Scripts/python artigo/gerar_docx.py --dir artigo-agua
    .venv311/Scripts/python artigo/gerar_docx.py --dir artigo-imunopreveniveis

Produz `<dir>/manuscrito.docx` a partir de `manuscrito.md`, das tabelas em
`tabelas/` e das figuras em `figuras/`. Não substitui o HTML nem o PDF: o
markdown continua sendo a fonte, e nada aqui edita o manuscrito.

POR QUE ELE MORA EM `artigo/` E RECEBE `--dir`
-----------------------------------------------
Ele nasceu dentro de `artigo-neoplasias/`, fixo àquela pasta. Quando o segundo e
o terceiro manuscritos precisaram da mesma saída, copiá-lo duas vezes teria
criado três cópias de 360 linhas que divergem no primeiro conserto feito só em
uma. `renderizar.py` e `sincronizar_tabelas.py` já moram aqui pelo mesmo motivo;
este segue a convenção.

O que é específico de cada artigo — onde cada figura entra e o que a legenda diz
— sai de `LEGENDAS`, declarada no `gerar_figuras.py` da pasta. A configuração
fica ao lado do código que desenha a figura, que é onde ela é mantida.

TRÊS TRANSFORMAÇÕES, E O MOTIVO DE CADA UMA
--------------------------------------------

1. **O bloco de autoria sai.** O arquivo destina-se a submissão cega. Sai o
   nome, sai a afiliação, sai o domínio do projeto. O que NÃO dá para remover
   daqui são os caminhos de script citados na seção de disponibilidade — eles
   identificam o repositório para quem procurar, e retirá-los quebraria a
   promessa de reprodutibilidade. Fica declarado em `_ALERTA_CEGO`, impresso a
   cada execução, para a decisão ser de quem submete e não deste script.

2. **As tabelas viram suplementares.** Elas continuam inteiras, com os mesmos
   números e o mesmo conteúdo — mudam de lugar e de rótulo (`Tabela 9` passa a
   `Tabela S9`), inclusive nas citações da prosa. O corpo do artigo fica com as
   figuras; quem quiser o valor exato acha na tabela de mesmo número.

3. **As figuras entram.** Cada uma é ancorada ao fim da seção que a discute, com
   legenda que aponta a tabela de origem. A numeração é a ordem de aparição, e
   os nomes de arquivo em `figuras/` seguem a mesma ordem — para a pasta e o
   documento não discordarem sobre qual é a Figura 3.

Depende de `python-docx`.
"""

from __future__ import annotations

import re
import argparse
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import docx
import pandas as pd
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Inches, Pt, RGBColor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Preenchidos por `main()` a partir de `--dir`. São módulo-globais porque as
#: funções abaixo já os liam assim quando o script era de um artigo só; trocar
#: para parâmetro exigiria enfiar o caminho em dez assinaturas sem ganhar nada.
RAIZ: Path = Path()
MD: Path = Path()
FIGURAS: Path = Path()
TABELAS: Path = Path()
DESTINO: Path = Path()
FIGURAS_DO_ARTIGO: tuple[tuple[str, str, str], ...] = ()


def _configurar(pasta: Path) -> None:
    """Aponta os caminhos e importa a configuração de figuras do artigo."""
    global RAIZ, MD, FIGURAS, TABELAS, DESTINO, FIGURAS_DO_ARTIGO
    RAIZ, MD = pasta, pasta / "manuscrito.md"
    FIGURAS, TABELAS = pasta / "figuras", pasta / "tabelas"
    DESTINO = pasta / "manuscrito.docx"
    if not MD.exists():
        raise SystemExit(f"{MD} não existe.")

    modulo = pasta / "gerar_figuras.py"
    if not modulo.exists():
        raise SystemExit(f"{modulo} não existe — sem ele não há legendas.")
    espec = importlib.util.spec_from_file_location(f"_figs_{pasta.name}", modulo)
    mod = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(mod)
    if not hasattr(mod, "LEGENDAS"):
        raise SystemExit(
            f"{modulo} não declara LEGENDAS. Ela diz em que seção cada figura "
            "entra e o que a legenda do documento vai dizer — sem ela o .docx "
            "sairia com as figuras soltas no fim, longe do texto que as discute.")
    FIGURAS_DO_ARTIGO = tuple(mod.LEGENDAS)

_ALERTA_CEGO = (
    "[cego] o bloco de autoria foi removido. NÃO ficam anônimos: os caminhos de\n"
    "       script citados na seção de disponibilidade de dados. Se a revista\n"
    "       exigir cegamento estrito, essa seção precisa de uma versão neutra."
)

@dataclass
class Tabela:
    numero: int
    legenda: str
    csv: str


def _paragrafo_com_marcacao(p, texto: str) -> None:
    """Escreve texto com **negrito**, *itálico* e `código` em runs separados.

    Nunca insere `\\n`: quebra de linha em Word é parágrafo, não caractere.
    """
    for pedaco in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", texto):
        if not pedaco:
            continue
        if pedaco.startswith("**") and pedaco.endswith("**"):
            p.add_run(pedaco[2:-2]).bold = True
        elif pedaco.startswith("*") and pedaco.endswith("*"):
            p.add_run(pedaco[1:-1]).italic = True
        elif pedaco.startswith("`") and pedaco.endswith("`"):
            r = p.add_run(pedaco[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
        else:
            p.add_run(pedaco)


def _suplementar(texto: str) -> str:
    """`Tabela 9` vira `Tabela S9`, inclusive em `Tabelas 11 e 12`."""
    texto = re.sub(r"\bTabelas (\d+) e (\d+)\b", r"Tabelas S\1 e S\2", texto)
    return re.sub(r"\bTabela (\d+)\b", r"Tabela S\1", texto)


def carregar_markdown() -> tuple[str, list[str], list[Tabela]]:
    """Devolve (título, linhas do corpo sem autoria e sem tabelas, tabelas)."""
    linhas = MD.read_text(encoding="utf-8").splitlines()
    titulo = linhas[0].lstrip("# ").strip()

    # O bloco de autoria é tudo entre o título e o primeiro separador.
    corte = next(i for i, x in enumerate(linhas) if i > 0 and x.strip() == "---")
    corpo = linhas[corte + 1:]

    saida: list[str] = []
    tabelas: list[Tabela] = []
    i = 0
    # O separador entre o número e a legenda aceita PONTO ou TRAVESSÃO. Os
    # manuscritos do repositório usam as duas formas — `artigo-neoplasias` e
    # `artigo-agua` escrevem "Tabela 9. ...", `artigo-imunopreveniveis` escreve
    # "Tabela 3 — ...". Casar só uma delas fazia este gerador encontrar ZERO
    # tabelas num manuscrito que tem dezesseis, e a conferência abaixo pegou.
    # Reescrever dezesseis legendas para caber no regex seria dobrar o texto à
    # ferramenta; o regex é que cede.
    anuncio = re.compile(
        r"^\*\*Tabela (\d+)\s*[.—-]\s*(.+?)\s*\(`(tabela_[a-z0-9_]+\.csv)`\)\.?\*\*$")
    while i < len(corpo):
        m = anuncio.match(corpo[i].strip())
        if m:
            tabelas.append(Tabela(int(m.group(1)), m.group(2), m.group(3)))
            i += 1
            while i < len(corpo) and (not corpo[i].strip() or corpo[i].lstrip().startswith("|")):
                i += 1
            continue
        saida.append(corpo[i])
        i += 1
    return titulo, saida, tabelas


def _estilos(doc) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15
    for nome, tam in (("Heading 1", 15), ("Heading 2", 12.5), ("Title", 20)):
        st = doc.styles[nome]
        st.font.name = "Calibri"
        st.font.size = Pt(tam)
        st.font.color.rgb = RGBColor(0x0B, 0x0B, 0x0B)
        st.font.bold = True
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(2.5)
        s.left_margin = s.right_margin = Cm(2.5)


def _legenda(doc, texto: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run(texto)
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x52, 0x51, 0x4E)


def _inserir_figura(doc, indice: int, arquivo: str, legenda: str) -> None:
    caminho = FIGURAS / f"{arquivo}.png"
    if not caminho.exists():
        raise SystemExit(
            f"{caminho.name} não existe. Rode `python {RAIZ.name}/gerar_figuras.py`.")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    # Largura explícita: a figura nasce com 6,3 polegadas e é inserida com 6,3.
    # Deixar o Word escolher reescala e borra o texto dos eixos.
    p.add_run().add_picture(str(caminho), width=Inches(6.3))
    _legenda(doc, f"Figura {indice}. {legenda}")


def _inserir_tabela(doc, t: Tabela, indice: int) -> None:
    df = pd.read_csv(TABELAS / t.csv, encoding="utf-8-sig")
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(f"Tabela S{indice}. {_suplementar(t.legenda)}")
    r.bold = True
    r.font.size = Pt(10)

    tab = doc.add_table(rows=1, cols=len(df.columns))
    tab.style = "Light Grid Accent 1"
    tab.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Largura em DXA nos dois lugares — na tabela e em cada célula. Porcentagem
    # quebra fora do Word, e largura só na tabela é ignorada por alguns leitores.
    largura = Inches(6.3) / len(df.columns)
    tab.autofit = False
    for j, coluna in enumerate(df.columns):
        c = tab.rows[0].cells[j]
        c.width = largura
        c.text = ""
        run = c.paragraphs[0].add_run(str(coluna))
        run.bold = True
        run.font.size = Pt(8)
    for _, linha in df.iterrows():
        celulas = tab.add_row().cells
        for j, valor in enumerate(linha):
            celulas[j].width = largura
            texto = "—" if pd.isna(valor) else str(valor)
            celulas[j].text = ""
            celulas[j].paragraphs[0].add_run(texto).font.size = Pt(8)


def montar() -> None:
    titulo, corpo, tabelas = carregar_markdown()
    doc = docx.Document()
    _estilos(doc)

    doc.add_paragraph(titulo, style="Title")
    nota = doc.add_paragraph()
    nota.paragraph_format.space_after = Pt(18)
    r = nota.add_run(
        "Manuscrito submetido sem identificação de autoria. As tabelas citadas "
        "no texto estão no material suplementar, ao final, com a mesma "
        "numeração precedida de S.")
    r.italic = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = RGBColor(0x52, 0x51, 0x4E)

    #: Figuras pendentes por seção, na ordem em que aparecem.
    pendentes: dict[str, list[tuple[int, str, str]]] = {}
    for i, (secao, arquivo, legenda) in enumerate(FIGURAS_DO_ARTIGO, start=1):
        pendentes.setdefault(secao, []).append((i, arquivo, legenda))

    secao_atual = ""

    def _descarregar() -> None:
        for indice, arquivo, legenda in pendentes.pop(secao_atual, []):
            _inserir_figura(doc, indice, arquivo, legenda)

    for linha in corpo:
        crua = linha.rstrip()
        if crua.strip() == "---":
            continue
        if crua.startswith("### "):
            _descarregar()
            texto = _suplementar(crua[4:].strip())
            secao_atual = texto.split(" ")[0]
            doc.add_paragraph(texto, style="Heading 2")
        elif crua.startswith("## "):
            _descarregar()
            secao_atual = ""
            doc.add_paragraph(_suplementar(crua[3:].strip()), style="Heading 1")
        elif crua.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            _paragrafo_com_marcacao(p, _suplementar(crua[2:].strip()))
        elif crua.strip():
            p = doc.add_paragraph()
            _paragrafo_com_marcacao(p, _suplementar(crua.strip()))
    _descarregar()
    if pendentes:
        raise SystemExit(
            f"[docx] figuras sem âncora no manuscrito: {sorted(pendentes)}. "
            "A seção citada em FIGURAS_DO_ARTIGO mudou de número ou de nome.")

    doc.add_section(WD_SECTION.NEW_PAGE)
    doc.add_paragraph("Material suplementar", style="Heading 1")
    p = doc.add_paragraph()
    _paragrafo_com_marcacao(p, _suplementar(
        "As tabelas a seguir são as citadas no corpo do artigo, na mesma ordem e "
        "com a mesma numeração. Cada uma é gerada por script a partir dos "
        "microdados; nenhum valor foi transcrito à mão."))
    for t in sorted(tabelas, key=lambda x: x.numero):
        _inserir_tabela(doc, t, t.numero)

    doc.save(DESTINO)
    print(f"[docx] {DESTINO.name}: {len(corpo)} linhas de corpo, "
          f"{len(FIGURAS_DO_ARTIGO)} figuras, {len(tabelas)} tabelas suplementares")


def conferir() -> None:
    """Reabre o arquivo e compara contra as fontes. Sem isto, não há verificação."""
    doc = docx.Document(DESTINO)
    problemas: list[str] = []

    texto = "\n".join(p.text for p in doc.paragraphs)
    for proibido in ("Pedro Paulo Fernandes", "saudeemdado.com", "ORCID"):
        if proibido in texto:
            problemas.append(f"identificação de autoria sobrevivente: {proibido!r}")

    imagens = sum(1 for r in doc.part.rels.values() if "image" in r.reltype)
    if imagens != len(FIGURAS_DO_ARTIGO):
        problemas.append(f"{imagens} imagens embutidas, esperadas {len(FIGURAS_DO_ARTIGO)}")

    csvs = sorted(TABELAS.glob("tabela_*.csv"))
    if len(doc.tables) != len(csvs):
        problemas.append(f"{len(doc.tables)} tabelas no documento, {len(csvs)} CSVs")

    # Conteúdo, não só contagem: uma célula trocada passa por qualquer contagem.
    _, _, tabelas = carregar_markdown()
    for tab_doc, t in zip(doc.tables, sorted(tabelas, key=lambda x: x.numero), strict=True):
        df = pd.read_csv(TABELAS / t.csv, encoding="utf-8-sig")
        if len(tab_doc.rows) != len(df) + 1 or len(tab_doc.columns) != len(df.columns):
            problemas.append(f"{t.csv}: {len(tab_doc.rows) - 1}x{len(tab_doc.columns)} "
                             f"no documento, {len(df)}x{len(df.columns)} no CSV")
            continue
        for j, coluna in enumerate(df.columns):
            if tab_doc.rows[0].cells[j].text.strip() != str(coluna).strip():
                problemas.append(f"{t.csv}: cabeçalho {j} difere")
        primeira = [str(v) for v in df.iloc[0]]
        lidas = [c.text.strip() for c in tab_doc.rows[1].cells]
        if [x.strip() for x in primeira] != lidas:
            problemas.append(f"{t.csv}: primeira linha difere ({lidas} vs {primeira})")

    if re.search(r"\bTabela (?!S)\d+", texto):
        exemplo = re.search(r"\bTabela (?!S)\d+", texto).group(0)
        problemas.append(f"citação de tabela sem o S do suplementar: {exemplo!r}")

    if problemas:
        raise SystemExit("[docx] conferência reprovou:\n  - " + "\n  - ".join(problemas))
    print(f"[docx] conferido: sem autoria, {imagens} figuras, {len(doc.tables)} tabelas "
          "com cabeçalho e primeira linha idênticos aos CSVs")


def main() -> None:
    ap = argparse.ArgumentParser(description="Manuscrito em Word, sem autoria.")
    ap.add_argument("--dir", required=True, help="pasta do artigo (ex.: artigo-agua)")
    args = ap.parse_args()
    _configurar((Path.cwd() / args.dir).resolve())
    montar()
    conferir()
    print(_ALERTA_CEGO)


if __name__ == "__main__":
    main()
