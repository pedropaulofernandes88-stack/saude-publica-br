"""
renderizar.py — o manuscrito em HTML e PDF
===========================================

Converte `manuscrito.md` em uma página autocontida e, se o Chrome estiver
disponível, em PDF. O Markdown é a fonte; o HTML e o PDF são derivados e não se
editam à mão — a mesma regra de `materiais/`.

Por que um renderizador próprio e não um conversor genérico: o manuscrito usa
um subconjunto pequeno e estável (títulos, parágrafos, listas, tabelas, ênfase,
código inline, regra horizontal), e a tipografia importa — margens de leitura,
tabelas que não estouram, quebra de página sensata na impressão. Um conversor
genérico traria dependência e devolveria menos controle.

Uso:
  .venv311/Scripts/python artigo/renderizar.py
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

#: Diretório do manuscrito. Passa a ser argumento porque existe um SEGUNDO
#: manuscrito (`artigo-neoplasias/`) com o mesmo subconjunto de Markdown e a
#: mesma tipografia. Copiar este arquivo para lá seria criar duas versões do
#: renderizador que divergem em silêncio — o mesmo motivo de `_sim_obitos.py`
#: existir. Sem argumento, o comportamento é o de sempre.
AQUI = Path(__file__).resolve().parent

MARCA_ITEM = re.compile(r"^\s*[-*]\s+")
BLOCO = re.compile(r"^(#{1,4}\s|\s*[-*]\s|\|)")

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

CSS = """
:root { --tinta:#1a1a1a; --suave:#5a5a5a; --linha:#d8d8d8; --realce:#0b5c8a;
        --fundo:#fff; --caixa:#f6f7f9; }
* { box-sizing:border-box; }
body { margin:0 auto; padding:3.5rem 1.5rem 6rem; max-width:46rem; background:var(--fundo);
       color:var(--tinta); font:16px/1.68 Georgia,"Times New Roman",serif;
       text-rendering:optimizeLegibility; }
h1 { font-size:1.95rem; line-height:1.25; margin:0 0 1.6rem; letter-spacing:-.01em; }
h2 { font-size:1.35rem; margin:3.2rem 0 1rem; padding-bottom:.4rem;
     border-bottom:2px solid var(--linha); }
h3 { font-size:1.1rem; margin:2.2rem 0 .7rem; color:var(--realce); }
h4 { font-size:1rem; margin:1.6rem 0 .5rem; font-style:italic; }
p { margin:0 0 1.05rem; text-align:justify; hyphens:auto; }
strong { font-weight:700; }
em { font-style:italic; }
ul,ol { margin:0 0 1.05rem; padding-left:1.4rem; }
li { margin-bottom:.4rem; }
hr { border:0; border-top:1px solid var(--linha); margin:2.6rem 0; }
code { font:.88em ui-monospace,"SFMono-Regular",Consolas,monospace;
       background:var(--caixa); padding:.12em .35em; border-radius:3px; }
.tabela { overflow-x:auto; margin:0 0 1.4rem; }
table { border-collapse:collapse; width:100%; font-family:system-ui,-apple-system,sans-serif;
        font-size:.83rem; line-height:1.45; }
th,td { padding:.42rem .6rem; border-bottom:1px solid var(--linha); text-align:left;
        vertical-align:top; }
th { background:var(--caixa); font-weight:600; border-bottom:2px solid #bbb;
     white-space:nowrap; }
tbody tr:last-child td { border-bottom:1px solid #bbb; }
td:not(:first-child) { text-align:right; font-variant-numeric:tabular-nums; }
th:not(:first-child) { text-align:right; }
.autor { color:var(--suave); font-size:.95rem; margin-bottom:.2rem; }
.nota { color:var(--suave); font-size:.9rem; font-style:italic; }
@media print {
  body { padding:0; max-width:none; font-size:10.5pt; }
  h2 { break-after:avoid; } h3 { break-after:avoid; }
  table,.tabela { break-inside:avoid; }
  p { orphans:3; widows:3; }
}
@media (prefers-color-scheme: dark) {
  :root { --tinta:#e8e6e3; --suave:#a8a29e; --linha:#3a3a3a; --realce:#7cc4ea;
          --fundo:#161615; --caixa:#232322; }
}
"""


def _inline(texto: str) -> str:
    """Ênfase, código e escape.

    Os trechos de código saem primeiro, mas viram MARCADOR em vez de HTML —
    e só voltam no fim. Processar cada pedaço isoladamente quebrava a ênfase
    que atravessa código: `**Controle positivo (`arquivo.csv`).**` tinha o
    abre-negrito num pedaço e o fecha-negrito noutro, e os asteriscos vazavam
    para a página.
    """
    codigos: list[str] = []

    def guardar(m: re.Match[str]) -> str:
        codigos.append(html.escape(m.group(1)))
        return f"\x00{len(codigos) - 1}\x00"

    p = re.sub(r"`([^`]+)`", guardar, texto)
    p = html.escape(p)
    p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
    p = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", p)
    return re.sub(r"\x00(\d+)\x00",
                  lambda m: f"<code>{codigos[int(m.group(1))]}</code>", p)


def _tabela(linhas: list[str]) -> str:
    def celulas(linha: str) -> list[str]:
        return [c.strip() for c in linha.strip().strip("|").split("|")]

    cabecalho = celulas(linhas[0])
    corpo = [celulas(x) for x in linhas[2:]]
    th = "".join(f"<th>{_inline(c)}</th>" for c in cabecalho)
    tr = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in linha) + "</tr>"
                 for linha in corpo)
    return f'<div class="tabela"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def para_html(md: str) -> str:
    linhas = md.split("\n")
    fora: list[str] = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]

        if linha.strip().startswith("|") and i + 1 < len(linhas) and set(
                linhas[i + 1].replace("|", "").replace(" ", "")) <= {"-", ":"}:
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            fora.append(_tabela(bloco))
            continue

        if m := re.match(r"^(#{1,4})\s+(.*)$", linha):
            n = len(m.group(1))
            fora.append(f"<h{n}>{_inline(m.group(2))}</h{n}>")
            i += 1
            continue

        if linha.strip() in ("---", "***", "___"):
            fora.append("<hr>")
            i += 1
            continue

        if MARCA_ITEM.match(linha):
            itens = []
            while i < len(linhas) and MARCA_ITEM.match(linhas[i]):
                itens.append("<li>" + _inline(MARCA_ITEM.sub("", linhas[i])) + "</li>")
                i += 1
            fora.append("<ul>" + "".join(itens) + "</ul>")
            continue

        if not linha.strip():
            i += 1
            continue

        bloco = []
        while (i < len(linhas) and linhas[i].strip()
               and not BLOCO.match(linhas[i]) and linhas[i].strip() != "---"):
            bloco.append(linhas[i].strip())
            i += 1
        texto = " ".join(bloco)
        classe = ""
        if texto.startswith("**Pedro Paulo") or texto.startswith("¹"):
            classe = ' class="autor"'
        elif texto.startswith("*Coautoria"):
            classe = ' class="nota"'
        fora.append(f"<p{classe}>{_inline(texto)}</p>")
    return "\n".join(fora)


def main() -> None:
    ap = argparse.ArgumentParser(description="Renderiza um manuscrito em HTML e PDF.")
    ap.add_argument("diretorio", nargs="?", default=str(AQUI),
                    help="pasta com o manuscrito.md (padrão: artigo/)")
    raiz = Path(ap.parse_args().diretorio).resolve()
    entrada = raiz / "manuscrito.md"
    saida_html = raiz / "manuscrito.html"
    saida_pdf = raiz / "manuscrito.pdf"

    if not entrada.exists():
        raise SystemExit(f"{entrada} não existe")
    md = entrada.read_text(encoding="utf-8")
    titulo = next((x[2:].strip() for x in md.split("\n") if x.startswith("# ")), "Manuscrito")
    saida_html.write_text(
        "<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(titulo)}</title><style>{CSS}</style></head><body>\n"
        + para_html(md) + "\n</body></html>\n", encoding="utf-8")
    print(f"[html] {raiz.name}/{saida_html.name} — "
          f"{saida_html.stat().st_size / 1024:.0f} kB", flush=True)

    chrome = next((c for c in CHROME if Path(c).exists()), None)
    if not chrome:
        print("[pdf] Chrome não encontrado — só HTML", flush=True)
        return
    r = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={saida_pdf}", saida_html.as_uri()],
        capture_output=True, text=True, timeout=180)
    if saida_pdf.exists():
        print(f"[pdf] {raiz.name}/{saida_pdf.name} — "
              f"{saida_pdf.stat().st_size / 1024:.0f} kB", flush=True)
    else:
        print(f"[pdf] falhou: {(r.stderr or '')[-200:]}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
