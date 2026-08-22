"""
gerar_assets_marca.py — favicon e imagem Open Graph a partir da marca já existente
==================================================================================

O site rodava sem favicon (`/favicon.ico` respondia 404) e sem imagem Open Graph:
todo link compartilhado em WhatsApp, Slack, LinkedIn ou X aparecia como cartão
cinza sem identidade. Não é cosmético — é a primeira impressão de uma plataforma
de dados públicos que pede para ser citada.

A marca NÃO é inventada aqui. Ela é a mesma do cabeçalho do site
(`site/app/layout.tsx`): quadrado de cantos arredondados em accent-700, "S" em
serifa branca. As cores saem de `site/tailwind.config.ts`.

Saídas (todas versionadas no repositório — este script roda uma vez, quando a
marca muda, não a cada build):
    site/app/icon.svg              → <link rel=icon>, escala sem perda
    site/public/favicon.ico        → o /favicon.ico que o browser pede sozinho
    site/app/opengraph-image.png   → 1200×630, detectada pelo Next automaticamente

Uso:
    .venv311/Scripts/python scripts/gerar_assets_marca.py

Requer Pillow e uma fonte serifada do sistema. Não roda no CI: os arquivos
gerados são commitados, e o build do site apenas os copia.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

# tailwind.config.ts — mantenha em sincronia se a paleta mudar.
ACCENT_700 = "#0b5f4c"
ACCENT_300 = "#6fbba0"
INK_950 = "#17150f"
INK_300 = "#c0b7a8"
BRANCO = "#ffffff"

# Georgia é o fallback declarado de `font-serif` no Tailwind do site, então usá-la
# aqui reproduz a marca em vez de inventar uma segunda tipografia.
FONTES_SERIF = [
    "C:/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/georgia.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
]
FONTES_SANS = [
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _fonte(candidatas: list[str], tamanho: int) -> ImageFont.FreeTypeFont:
    for caminho in candidatas:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    raise SystemExit(
        "nenhuma fonte encontrada entre "
        + ", ".join(candidatas)
        + " — instale uma delas ou acrescente o caminho da sua em FONTES_*"
    )


def _fonte_que_cabe(
    draw: ImageDraw.ImageDraw, texto: str, candidatas: list[str],
    largura_max: int, tamanho_ideal: int, tamanho_min: int = 24,
) -> ImageFont.FreeTypeFont:
    """Maior corpo que ainda cabe em `largura_max`.

    Tamanho fixo já cortou a chamada da imagem OG no meio de uma palavra — e
    ninguém vê, porque a imagem só aparece quando alguém compartilha o link.
    Ajustar aqui é mais barato que descobrir depois.
    """
    for tamanho in range(tamanho_ideal, tamanho_min - 1, -2):
        fonte = _fonte(candidatas, tamanho)
        if draw.textlength(texto, font=fonte) <= largura_max:
            return fonte
    return _fonte(candidatas, tamanho_min)


def _centralizar(draw: ImageDraw.ImageDraw, texto: str, fonte, cx: int, cy: int, cor: str) -> None:
    """Centra pela caixa real do glifo, não pela métrica da fonte.

    A diferença importa num "S" isolado dentro de um quadrado pequeno: usar a
    métrica deixa o glifo visivelmente alto por causa do espaço de ascendente.
    """
    x0, y0, x1, y1 = draw.textbbox((0, 0), texto, font=fonte)
    draw.text((cx - (x1 + x0) / 2, cy - (y1 + y0) / 2), texto, font=fonte, fill=cor)


# ---------------------------------------------------------------------------
# icon.svg — vetor, sem depender de fonte instalada no cliente
# ---------------------------------------------------------------------------

def gerar_icon_svg() -> Path:
    destino = SITE / "app" / "icon.svg"
    # O "S" vai como <text> com pilha de fallback: um glifo isolado tolera bem a
    # substituição de serifa, e converter para path aqui tornaria a marca ilegível
    # de editar quando o logo mudar.
    destino.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" '
        'aria-label="Saúde em Dado">\n'
        f'  <rect width="64" height="64" rx="14" fill="{ACCENT_700}"/>\n'
        f'  <text x="32" y="33" fill="{BRANCO}" font-family="Georgia, \'Times New Roman\', serif" '
        'font-size="40" font-weight="700" text-anchor="middle" '
        'dominant-baseline="central">S</text>\n'
        "</svg>\n",
        encoding="utf-8",
    )
    return destino


# ---------------------------------------------------------------------------
# favicon.ico — o pedido implícito que o browser faz sozinho
# ---------------------------------------------------------------------------

def gerar_favicon_ico() -> Path:
    destino = SITE / "public" / "favicon.ico"
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Desenha grande e reduz: o antialiasing do Pillow no raio do canto fica
    # sujo se o quadrado for montado direto em 16px.
    lado = 256
    img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, lado - 1, lado - 1], radius=int(lado * 0.22), fill=ACCENT_700)
    _centralizar(d, "S", _fonte(FONTES_SERIF, int(lado * 0.62)), lado // 2, int(lado * 0.47), BRANCO)
    img.save(destino, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    return destino


# ---------------------------------------------------------------------------
# opengraph-image.png — o cartão de link
# ---------------------------------------------------------------------------

def gerar_opengraph() -> Path:
    destino = SITE / "app" / "opengraph-image.png"
    L, A = 1200, 630
    img = Image.new("RGB", (L, A), INK_950)
    d = ImageDraw.Draw(img)

    # Faixa de acento no topo: o mesmo verde do link e do botão.
    d.rectangle([0, 0, L, 10], fill=ACCENT_700)

    # Marca, no mesmo desenho do cabeçalho do site.
    marca = 96
    mx, my = 80, 96
    d.rounded_rectangle([mx, my, mx + marca, my + marca], radius=22, fill=ACCENT_700)
    _centralizar(d, "S", _fonte(FONTES_SERIF, 62), mx + marca // 2, my + int(marca * 0.47), BRANCO)

    d.text((mx + marca + 26, my + 26), "Saúde em Dado",
           font=_fonte(FONTES_SERIF, 46), fill=BRANCO)

    # Chamada: descreve o que a plataforma entrega, sem número que envelheça.
    # Números concretos (14,4 mi de óbitos etc.) mudam a cada competência e
    # tornariam a imagem falsa sem ninguém perceber — ela não é regerada por build.
    margem = 80
    util = L - 2 * margem
    l1, l2 = "Inteligência epidemiológica", "aberta sobre os microdados do SUS"
    # Um único corpo para as duas linhas: tamanhos diferentes leriam como
    # hierarquia, e aqui é uma frase só quebrada em duas.
    corpo = min(
        _fonte_que_cabe(d, l1, FONTES_SERIF, util, 68).size,
        _fonte_que_cabe(d, l2, FONTES_SERIF, util, 68).size,
    )
    serif_chamada = _fonte(FONTES_SERIF, corpo)
    d.text((margem, 268), l1, font=serif_chamada, fill=BRANCO)
    d.text((margem, 268 + int(corpo * 1.18)), l2, font=serif_chamada, fill=ACCENT_300)

    for i, linha in enumerate((
        "Mortalidade · Dengue · Internações · Natalidade · Leitos",
        "API pública gratuita · dados abertos · pipeline reproduzível",
    )):
        d.text((margem, 470 + i * 50),
               linha, font=_fonte_que_cabe(d, linha, FONTES_SANS, util, 30), fill=INK_300)

    d.text((margem, A - 62), "saudeemdado.com", font=_fonte(FONTES_SANS, 28), fill=ACCENT_300)

    img.save(destino, format="PNG", optimize=True)
    return destino


def main() -> None:
    for gerar in (gerar_icon_svg, gerar_favicon_ico, gerar_opengraph):
        caminho = gerar()
        tamanho = caminho.stat().st_size
        print(f"[ok] {caminho.relative_to(ROOT)} ({tamanho:,} bytes)")
    print("\nLembre-se: os arquivos são versionados. Rode este script só quando a marca mudar.")


if __name__ == "__main__":
    main()
