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

#: Pasta do manuscrito. Virou argumento quando nasceu o segundo manuscrito
#: (`artigo-neoplasias/`): a regra "tabela do texto sai do CSV" vale para os
#: dois, e uma segunda cópia deste arquivo divergiria da primeira sem avisar.
#: Sem `--dir`, o comportamento é o de sempre.
RAIZ = Path(__file__).resolve().parent

#: Anúncio de tabela seguido do bloco Markdown que ela substitui.
#:
#: O nome do CSV é procurado em QUALQUER lugar da legenda em negrito, não só
#: entre parênteses no fim. A primeira versão exigia a forma exata e por isso
#: deixou TRÊS tabelas de fora — entre elas a do controle positivo de dengue,
#: citada como `(Tabela 8c, `x.csv`)`. Ferramenta de sincronia que cobre parte
#: das tabelas dá a garantia que não tem.
PADRAO = re.compile(
    r"(^\*\*[^\n]*`(tabela_[a-z0-9_]+\.csv)`[^\n]*\n\n)((?:\|.*\n)+)", re.M)


#: Colunas cujo inteiro é um RÓTULO, não uma contagem, e portanto não leva
#: separador de milhar. Sem isto, "2024" saía "2.024" na tabela do controle
#: positivo de dengue — erro que passa despercebido no código e salta na página.
COLUNAS_SEM_SEPARADOR = {"ano", "k", "cid", "cid a", "cid b", "uf", "componente"}


def formatar(valor, coluna: str = "") -> str:
    """Número no padrão do texto em português; texto vai como está."""
    if pd.isna(valor):
        return "—"
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, float) and not float(valor).is_integer():
        return f"{valor:,.4f}".rstrip("0").rstrip(".").replace(",", "\x00") \
                                              .replace(".", ",").replace("\x00", ".")
    if coluna.strip().lower() in COLUNAS_SEM_SEPARADOR:
        return str(int(valor))
    return f"{int(valor):,}".replace(",", ".")


def bloco_markdown(csv: pd.DataFrame) -> str:
    cabecalho = [str(c).strip() for c in csv.columns]
    linhas = ["| " + " | ".join(cabecalho) + " |",
              "|" + "|".join("---" for _ in cabecalho) + "|"]
    for _, r in csv.iterrows():
        linhas.append("| " + " | ".join(formatar(v, c)
                                        for c, v in zip(cabecalho, r, strict=True)) + " |")
    return "\n".join(linhas) + "\n"


def sincronizar(conferir: bool, raiz: Path = RAIZ) -> int:
    manuscrito, tabelas = raiz / "manuscrito.md", raiz / "tabelas"
    if not manuscrito.exists():
        raise SystemExit(f"{manuscrito} não existe")
    texto = manuscrito.read_text(encoding="utf-8")
    divergentes: list[str] = []

    def troca(m: re.Match) -> str:
        anuncio, nome, atual = m.group(1), m.group(2), m.group(3)
        caminho = tabelas / nome
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
            print(f"[conferir] {raiz.name}: {len(divergentes)} de {n} tabelas "
                  "divergem do CSV:")
            for d in divergentes:
                print(f"    {d}")
            print(f"\nRode `python artigo/sincronizar_tabelas.py --dir {raiz.name}` "
                  "para reescrevê-las.")
            return 1
        print(f"[conferir] {raiz.name}: as {n} tabelas do manuscrito batem com os CSVs")
        _prestar_contas(n, manuscrito, tabelas)
        return 0

    manuscrito.write_text(novo_texto, encoding="utf-8")
    print(f"[sincronizar] {raiz.name}: {n} tabelas processadas, "
          f"{len(divergentes)} reescritas")
    for d in divergentes:
        print(f"    {d}")
    _prestar_contas(n, manuscrito, tabelas)
    return 0


def _prestar_contas(n: int, manuscrito: Path, tabelas: Path) -> None:
    """Diz o que sobrou, em vez de deixar o total sem explicação.

    A ferramenta imprimia "15 tabelas processadas" havendo 16 CSVs, e o 16º era
    invisível: `tabela_4_cargas.csv` é citada em prosa, sem tabela embutida — o
    que é deliberado, são 36 linhas. O problema não é a exceção, é ela não
    aparecer: se alguém apagasse uma tabela do manuscrito por engano, o número
    cairia de 15 para 14 e não haveria nada a comparar. Total sem prestação de
    contas é número que ninguém consegue conferir.
    """
    csvs = {p.name for p in tabelas.glob("*.csv")}
    texto = manuscrito.read_text(encoding="utf-8")
    citados = {c for c in csvs if c in texto}
    if orfas := sorted(csvs - citados):
        print(f"[atenção] {len(orfas)} CSV sem nenhuma citação no manuscrito:")
        for o in orfas:
            print(f"    {o}")
    so_prosa = sorted(citados - _com_tabela(texto))
    if so_prosa:
        print(f"[contas] {n} embutidas + {len(so_prosa)} citada(s) só em prosa "
              f"= {len(csvs)} CSVs: {', '.join(so_prosa)}")


def _com_tabela(texto: str) -> set[str]:
    return {m.group(2) for m in PADRAO.finditer(texto)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conferir", action="store_true",
                    help="não escreve; sai != 0 se alguma tabela divergir")
    ap.add_argument("--dir", default=str(RAIZ),
                    help="pasta do manuscrito (padrão: artigo/)")
    args = ap.parse_args()
    raise SystemExit(sincronizar(args.conferir, Path(args.dir).resolve()))


if __name__ == "__main__":
    main()
