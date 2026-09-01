"""Converte o .docx gerado para HTML paginavel, para virar PDF pelo Chrome.

Nao e um conversor generico: cobre exatamente o que este documento usa —
titulos de tres niveis, paragrafos com trechos em negrito, listas com marcador,
tabelas, a nota lateral e a quebra de pagina.
"""
import html
import re
import zipfile
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
import xml.etree.ElementTree as ET

base = Path(__file__).parent / "saida"
raiz = ET.fromstring(zipfile.ZipFile(base / "Saude-em-Dado-documentacao.docx").read("word/document.xml"))
corpo = raiz.find(f"{W}body")

partes: list[str] = []
lista_aberta = False


def fecha_lista():
    global lista_aberta
    if lista_aberta:
        partes.append("</ul>")
        lista_aberta = False


def runs_para_html(p) -> tuple[str, bool]:
    """Devolve o HTML dos runs e se houve quebra de pagina."""
    saida, quebra = [], False
    for r in p.iter(f"{W}r"):
        if r.find(f"{W}br") is not None and r.find(f"{W}br").get(f"{W}type") == "page":
            quebra = True
        t = r.find(f"{W}t")
        if t is None or t.text is None:
            continue
        texto = html.escape(t.text)
        rpr = r.find(f"{W}rPr")
        if rpr is not None:
            if rpr.find(f"{W}b") is not None:
                texto = f"<strong>{texto}</strong>"
            if rpr.find(f"{W}i") is not None:
                texto = f"<em>{texto}</em>"
        saida.append(texto)
    return "".join(saida), quebra


for elemento in corpo:
    if elemento.tag == f"{W}tbl":
        fecha_lista()
        linhas = []
        for i, tr in enumerate(elemento.findall(f"{W}tr")):
            celulas = []
            for tc in tr.findall(f"{W}tc"):
                txt = "".join(runs_para_html(p)[0] for p in tc.findall(f"{W}p"))
                celulas.append(f"<{'th' if i == 0 else 'td'}>{txt}</{'th' if i == 0 else 'td'}>")
            linhas.append("<tr>" + "".join(celulas) + "</tr>")
        partes.append("<table>" + "".join(linhas) + "</table>")
        continue
    if elemento.tag != f"{W}p":
        continue

    ppr = elemento.find(f"{W}pPr")
    estilo = ""
    if ppr is not None:
        ps = ppr.find(f"{W}pStyle")
        if ps is not None:
            estilo = ps.get(f"{W}val") or ""
    texto, quebra = runs_para_html(elemento)
    if quebra:
        fecha_lista()
        partes.append('<div class="quebra"></div>')
    if not texto.strip():
        continue

    e_lista = ppr is not None and ppr.find(f"{W}numPr") is not None
    tem_borda = ppr is not None and ppr.find(f"{W}pBdr") is not None

    if estilo.startswith("Heading"):
        fecha_lista()
        n = estilo[-1]
        partes.append(f"<h{n}>{texto}</h{n}>")
    elif e_lista:
        if not lista_aberta:
            partes.append("<ul>")
            lista_aberta = True
        partes.append(f"<li>{texto}</li>")
    elif tem_borda:
        fecha_lista()
        partes.append(f'<p class="nota">{texto}</p>')
    else:
        fecha_lista()
        partes.append(f"<p>{texto}</p>")
fecha_lista()

def alvo_de(titulo: str) -> str:
    limpo = re.sub(r"<[^>]+>", "", titulo).lower()
    return re.sub(r"[^a-z0-9]+", "-", limpo).strip("-")


# --- capa: tudo antes da primeira quebra vira bloco proprio -----------------
primeira = next(i for i, b in enumerate(partes) if b == '<div class="quebra"></div>')
capa = list(partes[:primeira])
capa[0] = capa[0].replace("<p>", '<p class="eixo-capa">', 1)
capa[1] = capa[1].replace("<p>", '<p class="titulo-capa">', 1)
capa[2] = capa[2].replace("<p>", '<p class="linha-capa">', 1)
partes = ['<section class="capa">'] + capa + ["</section>"] + partes[primeira + 1:]

# --- sumario: o indice do Word e campo e nao renderiza em HTML --------------
# Sem isso o PDF traria um titulo "Sumario" seguido de nada.
# os titulos vem com os runs em <strong>, entao a busca ignora marcacao
i_sumario = next(i for i, b in enumerate(partes)
                 if b.startswith("<h1>") and "Sumário" in re.sub(r"<[^>]+>", "", b))
itens = []
for b in partes:
    m = re.fullmatch(r"<h([12])>(.*)</h\1>", b)
    if m and "Sumário" not in m.group(2):
        itens.append(f'<li class="n{m.group(1)}">'
                     f'<a href="#{alvo_de(m.group(2))}">{re.sub(r"<[^>]+>", "", m.group(2))}</a></li>')
partes.insert(i_sumario + 1, '<ul class="sumario">' + "".join(itens) + "</ul>")

# --- ancoras nos titulos, para o sumario funcionar como link ---------------
partes = [
    (lambda m: f'<h{m.group(1)} id="{alvo_de(m.group(2))}">{m.group(2)}</h{m.group(1)}>')(m)
    if (m := re.fullmatch(r"<h([12])>(.*)</h\1>", b)) else b
    for b in partes
]

corpo_html = "\n".join(partes)

CSS = """
@page { size: A4; margin: 22mm 20mm 20mm 20mm; }
body { font-family: Calibri, "Segoe UI", sans-serif; font-size: 10.5pt; line-height: 1.55;
       color: #101521; margin: 0; }
h1 { font-family: Cambria, Georgia, serif; font-size: 21pt; margin: 26pt 0 11pt; page-break-after: avoid; }
h2 { font-family: Cambria, Georgia, serif; font-size: 15pt; margin: 20pt 0 8pt; page-break-after: avoid; }
h3 { font-size: 11.5pt; color: #1F4FA8; margin: 14pt 0 6pt; page-break-after: avoid; }
p { margin: 0 0 8pt; text-align: justify; }
ul { margin: 0 0 10pt; padding-left: 16pt; }
li { margin-bottom: 5pt; text-align: justify; }
li::marker { color: #1F4FA8; }
p.nota { border-left: 2.5pt solid #B8461E; padding: 6pt 0 6pt 11pt; margin: 10pt 0 12pt;
         color: #45506A; font-style: italic; }
table { border-collapse: collapse; width: 100%; margin: 10pt 0 14pt; font-size: 9.5pt;
        page-break-inside: avoid; }
th { background: #EEF1F6; text-align: left; font-weight: 600; }
th, td { border: 0.5pt solid #D3D9E3; padding: 5pt 7pt; vertical-align: top; }
.quebra { page-break-after: always; }
/* Especificidade: as regras do bloco da capa usam .capa .classe para nao
   serem sobrepostas pela regra geral .capa p, que e mais especifica que
   uma classe sozinha. */
.capa { padding-top: 30mm; page-break-after: always; }
.capa p { text-align: left; font-size: 9.5pt; color: #45506A; }
.capa .eixo-capa { font-size: 9pt; letter-spacing: 2.6pt; color: #1F4FA8;
                   font-weight: 600; margin-bottom: 12pt; }
.capa .titulo-capa { font-family: Cambria, Georgia, serif; font-size: 29pt; line-height: 1.15;
                     font-weight: 700; margin: 0 0 16pt; color: #101521; }
.capa .linha-capa { font-size: 12pt; color: #45506A; margin-bottom: 30pt; }
.capa .titulo-capa strong, .capa .eixo-capa strong { font-weight: inherit; }
ul.sumario { list-style: none; padding: 0; margin: 6pt 0 0; }
ul.sumario li { margin: 0 0 5pt; }
ul.sumario li.n1 { font-weight: 600; margin-top: 12pt; font-family: Cambria, Georgia, serif; font-size: 11.5pt; }
ul.sumario li.n2 { padding-left: 14pt; font-size: 10pt; }
ul.sumario a { color: #101521; text-decoration: none; }
strong { font-weight: 600; }
"""

Path(base / "documentacao.html").write_text(
    f"<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
    f"<title>Saúde em Dado — documentação</title><style>{CSS}</style></head>"
    f"<body>{corpo_html}</body></html>", encoding="utf-8")
print("html gerado com", len(partes), "blocos")
