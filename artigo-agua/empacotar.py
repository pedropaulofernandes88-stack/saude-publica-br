"""
empacotar.py — o pacote que acompanha o manuscrito da água
===========================================================

    .venv311/Scripts/python artigo-agua/empacotar.py

Produz `artigo-agua/dados-do-artigo.zip`: as onze tabelas, as cinco figuras, o
manuscrito e o código que produz as três coisas.

POR QUE UM SCRIPT, E NÃO UM ZIP FEITO À MÃO
--------------------------------------------
Zip montado uma vez não envelhece bem: quando os CSVs mudam, ele não muda junto,
e ninguém percebe porque zip não reprova em teste. Aqui o pacote é derivado — se
apagar e rodar de novo, sai igual.

**Manifesto com SHA-256.** Cada arquivo entra com tamanho, linhas, colunas e
hash. É o idioma do resto do projeto, e serve a quem recebe o pacote fora do
git: dá para conferir que o CSV que se está lendo é o que foi empacotado.

**Datas fixas nas entradas.** O zip é reprodutível byte a byte: duas execuções
sobre os mesmos arquivos produzem o mesmo hash. Sem isso o carimbo de tempo
mudaria o SHA a cada execução, e o manifesto perderia a função.

ABORTA EM VEZ DE EMPACOTAR PELA METADE
---------------------------------------
Falta de tabela ou de figura interrompe. Pacote incompleto é pior que pacote
nenhum, porque parece completo para quem recebe.
"""
from __future__ import annotations

import csv
import hashlib
import io
import sys
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
DESTINO = AQUI / "dados-do-artigo.zip"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: O que entra além das tabelas e figuras, e como se chama no pacote.
CONTEUDO = [
    (AQUI / "manuscrito.md", "manuscrito.md", "O manuscrito, em Markdown"),
    (AQUI / "manuscrito.docx", "manuscrito.docx",
     "O manuscrito em Word, SEM identificação de autoria, com as figuras no corpo e as tabelas como material suplementar"),
    (ROOT / "scripts" / "analise_agua_mortalidade.py",
     "codigo/analise_agua_mortalidade.py",
     "A análise: critérios declarados no cabeçalho, e as onze tabelas"),
    (AQUI / "gerar_tabelas.py", "codigo/gerar_tabelas.py",
     "Reexecuta a análise e formata as tabelas do artigo"),
    (AQUI / "gerar_figuras.py", "codigo/gerar_figuras.py",
     "Desenha as cinco figuras a partir das tabelas"),
    (ROOT / "data" / "refs" / "Obitos_Evitaveis_5_a_74_anos.pdf",
     "referencia/Obitos_Evitaveis_5_a_74_anos.pdf",
     "Nota técnica do TabNet/DataSUS com a Lista Brasileira (5 a 74 anos)"),
]

LEIA_ME = """# Mortes evitáveis por doença infecciosa intestinal no Brasil, 2015–2024

Pacote de dados, figuras e código do manuscrito.

## O que tem aqui

    manuscrito.md            o texto
    tabelas/                 as onze tabelas, em CSV
    figuras/                 as cinco figuras, em PNG a 300 dpi
    codigo/                  a análise e os dois geradores
    referencia/              a nota técnica oficial da Lista Brasileira
    MANIFESTO.csv            inventário com SHA-256 de cada arquivo

## Como reproduzir

    python codigo/analise_agua_mortalidade.py     # reescreve as tabelas
    python codigo/gerar_tabelas.py                # formata para o artigo
    python codigo/gerar_figuras.py                # redesenha as figuras

A análise reexecuta a partir dos marts publicados do projeto. Os critérios de
refutação estão escritos no cabeçalho de `analise_agua_mortalidade.py`, antes de
qualquer resultado — inclusive o quarto, que está rotulado como **post-hoc**
porque foi concebido depois de observar os dados.

## O que este desenho NÃO autoriza

É ecológico. A unidade é o município, e nada aqui autoriza afirmar que a pessoa
que morreu consumiu água não vigiada. E ausência de registro de vigilância não é
água contaminada: é ausência da prova.
"""


def _perfil(dados: bytes, nome: str) -> tuple[str, str, str]:
    """Linhas, colunas e SHA-256. Linhas e colunas só fazem sentido em CSV."""
    sha = hashlib.sha256(dados).hexdigest()
    if not nome.endswith(".csv"):
        return "", "", sha
    texto = dados.decode("utf-8", errors="replace").strip().split("\n")
    return str(len(texto) - 1), str(len(texto[0].split(","))) if texto else "", sha


def main() -> None:
    itens: list[tuple[str, bytes, str]] = []

    for origem, destino, descricao in CONTEUDO:
        if not origem.exists():
            raise SystemExit(
                f"{origem} não existe. Pacote com arquivo faltando é pior que "
                "pacote nenhum, porque parece completo.")
        itens.append((destino, origem.read_bytes(), descricao))

    tabelas = sorted((AQUI / "tabelas").glob("*.csv"))
    if len(tabelas) != 11:
        raise SystemExit(
            f"esperava 11 tabelas em tabelas/, achei {len(tabelas)}. "
            "Rode `gerar_tabelas.py` antes.")
    for t in tabelas:
        itens.append((f"tabelas/{t.name}", t.read_bytes(),
                      "Tabela do manuscrito"))

    figuras = sorted((AQUI / "figuras").glob("*.png"))
    if len(figuras) != 5:
        raise SystemExit(
            f"esperava 5 figuras em figuras/, achei {len(figuras)}. "
            "Rode `gerar_figuras.py` antes.")
    for f in figuras:
        itens.append((f"figuras/{f.name}", f.read_bytes(),
                      "Figura do manuscrito (PNG, 300 dpi)"))

    manifesto = io.StringIO()
    w = csv.writer(manifesto, lineterminator="\n")
    w.writerow(["arquivo", "descricao", "bytes", "linhas", "colunas", "sha256"])
    for destino, dados, descricao in itens:
        linhas, colunas, sha = _perfil(dados, destino)
        w.writerow([destino, descricao, len(dados), linhas, colunas, sha])

    itens.insert(0, ("LEIA-ME.md", LEIA_ME.encode("utf-8"), "Este arquivo"))
    itens.insert(1, ("MANIFESTO.csv", manifesto.getvalue().encode("utf-8"),
                     "Inventário com SHA-256 de cada arquivo"))

    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for destino, dados, _ in itens:
            info = zipfile.ZipInfo(destino, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, dados)

    tamanho = DESTINO.stat().st_size
    print(f"[zip] {DESTINO.name} — {len(itens)} arquivos, {tamanho // 1024} kB")
    print(f"[sha] {hashlib.sha256(DESTINO.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
