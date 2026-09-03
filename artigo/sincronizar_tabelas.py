"""
sincronizar_tabelas.py — reescreve no manuscrito as tabelas geradas por CSV
===========================================================================

O manuscrito trazia doze tabelas em Markdown copiadas à mão dos CSVs de
`artigo/tabelas/`. É o padrão que este projeto já combateu em toda parte: número
copiado envelhece em silêncio. Quando 2024 foi recoletado do `.dbc` — 105.669
óbitos que o CSV do OpenDataSUS não trazia —, **as doze passaram a divergir de
uma vez**, e nenhuma delas avisou.

Aqui elas deixam de ser copiadas. Cada bloco Markdown anunciado por
`` (`tabela_x.csv`) `` é regerado a partir do CSV correspondente, que por sua vez
sai de `gerar_tabelas.py`. O caminho passa a ser único: mart → CSV → manuscrito.

O QUE SE PERDE, E POR QUE VALE
------------------------------
As versões manuais tinham negrito seletivo e, em algumas tabelas, um subconjunto
das linhas. A geração não reproduz isso: sai a tabela inteira, sem ênfase
tipográfica. É troca deliberada — a ênfase vive na prosa, que é escrita à mão de
propósito, e a tabela passa a ser verificável por máquina.

`tests/test_manuscrito.py` confere que nenhuma tabela divergiu do seu CSV, o que
transforma a sincronia em regressão em vez de disciplina.

Uso:
  .venv311/Scripts/python artigo/sincronizar_tabelas.py [--conferir]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent
MANUSCRITO = RAIZ / "manuscrito.md"
TABELAS = RAIZ / "tabelas"

#: Anúncio de tabela seguido do bloco Markdown que ela substitui.
PADRAO = re.compile(r"(\(`(tabela_[a-z0-9_]+\.csv)`\)\s*\n\n)((?:\|.*\n)+)")


def formatar(valor) -> str:
    """Número no padrão do texto em português; texto vai como está."""
    if pd.isna(valor):
        return "—"
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, float) and not float(valor).is_integer():
        return f"{valor:,.4f}".rstrip("0").rstrip(".").replace(",", "\x00") \
                                              .replace(".", ",").replace("\x00", ".")
    return f"{int(valor):,}".replace(",", ".")


def bloco_markdown(csv: pd.DataFrame) -> str:
    cabecalho = [str(c).strip() for c in csv.columns]
    linhas = ["| " + " | ".join(cabecalho) + " |",
              "|" + "|".join("---" for _ in cabecalho) + "|"]
    for _, r in csv.iterrows():
        linhas.append("| " + " | ".join(formatar(v) for v in r) + " |")
    return "\n".join(linhas) + "\n"


def sincronizar(conferir: bool) -> int:
    texto = MANUSCRITO.read_text(encoding="utf-8")
    divergentes: list[str] = []

    def troca(m: re.Match) -> str:
        anuncio, nome, atual = m.group(1), m.group(2), m.group(3)
        caminho = TABELAS / nome
        if not caminho.exists():
            divergentes.append(f"{nome}: CSV ausente")
            return m.group(0)
        novo = bloco_markdown(pd.read_csv(caminho))
        if novo != atual:
            divergentes.append(nome)
        return anuncio + novo

    novo_texto = PADRAO.sub(troca, texto)
    n = len(PADRAO.findall(texto))

    if conferir:
        if divergentes:
            print(f"[conferir] {len(divergentes)} de {n} tabelas divergem do CSV:")
            for d in divergentes:
                print(f"    {d}")
            print("\nRode `python artigo/sincronizar_tabelas.py` para reescrevê-las.")
            return 1
        print(f"[conferir] as {n} tabelas do manuscrito batem com os CSVs")
        return 0

    MANUSCRITO.write_text(novo_texto, encoding="utf-8")
    print(f"[sincronizar] {n} tabelas processadas, {len(divergentes)} reescritas")
    for d in divergentes:
        print(f"    {d}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conferir", action="store_true",
                    help="não escreve; sai != 0 se alguma tabela divergir")
    raise SystemExit(sincronizar(ap.parse_args().conferir))


if __name__ == "__main__":
    main()
