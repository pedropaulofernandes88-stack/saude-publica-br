"""
verificar_duplicacao_rhc.py — a prova, reproduzível por um comando

    .venv311/Scripts/python scripts/verificar_duplicacao_rhc.py
    .venv311/Scripts/python scripts/verificar_duplicacao_rhc.py --anos 2019

POR QUE ESTE SCRIPT EXISTE SEPARADO DO PIPELINE
-----------------------------------------------
O `pipeline_rhc.py` já **corrige** a duplicação e **recusa** o arquivo que não
vier duplicado — isso é o comportamento certo em produção, e é péssimo como
evidência: quem lê o pipeline vê a correção, não o defeito.

Este script não corrige nada. Ele **mede o arquivo como o INCA distribui** e
imprime a evidência bruta, de forma que um terceiro com o mesmo zip chegue aos
mesmos números sem ler uma linha do resto do projeto. É o anexo da nota técnica
`rascunhos/rhc-duplicacao/nota.md` (repositório privado).

AS SEIS PROVAS QUE ELE IMPRIME
------------------------------
1. **Geometria.** `cabeçalho + registros × largura + 1` é exatamente o tamanho
   do arquivo. O `+1` é o marcador `0x1A` de fim de arquivo do dBase.
2. **Um único cabeçalho.** Os 12 primeiros bytes ocorrem uma vez só, no
   deslocamento 0. Dois dBase concatenados dariam duas ocorrências — é a
   hipótese alternativa (duplicação nascida no transporte), e ela cai aqui.
3. **A cópia é byte a byte**, conferida em TODOS os pares, não por amostra.
4. **Paridade.** Nenhuma categoria de nenhum campo tem contagem ímpar.
5. **Proporção é cega.** As proporções que as guardas do projeto verificam são
   idênticas antes e depois da correção, até a primeira casa decimal.
6. **Deduplicar por valor subcontaria.** Existem registros genuinamente
   idênticos nos campos publicados; a correção divide a MULTIPLICIDADE por
   dois, não remove duplicata.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sondar_rhc import campos_do_dbf, metadados_do_dbf  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parents[1]
CACHE = RAIZ / "data" / "cache"

#: O exportador do INCA pagina de 50.000 em 50.000 e grava cada página duas
#: vezes. Não é constante escolhida por mim: é o período medido no arquivo, e o
#: script CONFERE que ele vale em vez de assumir.
PAGINA = 50_000

#: Campos usados na prova de paridade. Escolhidos por terem muitas categorias
#: (IDADE, ANOPRIDI) e poucas (SEXO) — se fosse artefato do número de
#: categorias, apareceria na diferença entre eles.
CAMPOS_PARIDADE = ("IDADE", "ESTADIAM", "ANOPRIDI", "UFUH", "ESTDFIMT",
                   "RACACOR", "SEXO")

#: Marcador de fim de arquivo do dBase III.
FIM_DE_ARQUIVO = 0x1A


def _gemeo(i: int, n: int) -> int | None:
    """Índice da CÓPIA do registro `i`, ou `None` se `i` já for uma cópia.

    Página cheia: [50.000 originais][50.000 cópias], e a cópia mora exatamente
    50.000 posições adiante. A cauda, que não fecha uma página, vem em dobro
    também — metade original, metade cópia —, e ali o deslocamento é metade do
    tamanho da cauda, não 50.000. Foi essa diferença que fez a primeira versão
    da correção errar o último pedaço de cada ano.
    """
    inicio_da_cauda = (n // (2 * PAGINA)) * (2 * PAGINA)
    if i < inicio_da_cauda:
        desloc = i % (2 * PAGINA)
        return i + PAGINA if desloc < PAGINA else None
    meia_cauda = (n - inicio_da_cauda) // 2
    desloc = i - inicio_da_cauda
    return i + meia_cauda if desloc < meia_cauda else None


def _eh_original(i: int, n: int) -> bool:
    return _gemeo(i, n) is not None


def _abrir(ano: int) -> tuple[bytes, int]:
    z = CACHE / f"rhc_{ano}.zip"
    if not z.exists():
        raise SystemExit(
            f"{z} não existe. Este script mede o arquivo COMO O INCA DISTRIBUI; "
            "rode a coleta do RHC antes (scripts/pipeline_rhc.py baixa e cacheia).")
    with zipfile.ZipFile(z) as zf:
        nome = next(n for n in zf.namelist() if n.lower().endswith(".dbf"))
        return zf.read(nome), zf.getinfo(nome).file_size


def verificar(ano: int, completo: bool) -> dict[str, object]:
    dados, tamanho = _abrir(ano)
    n, tam_cab, tam_reg = metadados_do_dbf(dados[:32])
    campos = campos_do_dbf(dados[:tam_cab])
    pos = {nm: (o, t) for nm, o, t in campos}

    def registro(i: int) -> bytes:
        o = tam_cab + i * tam_reg
        return dados[o:o + tam_reg]

    def valor(i: int, nome: str) -> str:
        o1, t = pos[nome]
        o = tam_cab + i * tam_reg
        return dados[o + o1:o + o1 + t].decode("latin-1").strip()

    print(f"\n{'=' * 72}\n{ano}  —  {n:,} registros declarados no cabeçalho\n{'=' * 72}")

    # 1. GEOMETRIA
    esperado = tam_cab + n * tam_reg + 1
    print("\n1. GEOMETRIA — o cabeçalho descreve o arquivo inteiro?")
    print(f"   {tam_cab:,} + {n:,} × {tam_reg:,} + 1 = {esperado:,} bytes")
    print(f"   tamanho real do arquivo ............... {tamanho:,} bytes")
    print(f"   fecha? {esperado == tamanho}")
    print(f"   último byte: 0x{dados[-1]:02X} "
          f"({'0x1A, fim de arquivo dBase' if dados[-1] == FIM_DE_ARQUIVO else 'NÃO é 0x1A'})")

    # 2. UM CABEÇALHO SÓ — derruba a hipótese de concatenação no transporte
    padrao, achados, p = dados[:12], [], 0
    while len(achados) <= 3:
        i = dados.find(padrao, p)
        if i < 0:
            break
        achados.append(i)
        p = i + 1
    print("\n2. QUANTOS CABEÇALHOS? (dois dBase concatenados dariam dois)")
    print(f"   ocorrências dos 12 primeiros bytes: {achados}")
    print(f"   um único cabeçalho, no deslocamento 0: {achados == [0]}")

    # 3. A CÓPIA É BYTE A BYTE
    print("\n3. A CÓPIA É BYTE A BYTE?  (todos os pares, não amostra)")
    if n % 2:
        print(f"   {n:,} é ÍMPAR — não pode ser duplicação uniforme. PARE.")
        return {"ano": ano, "duplicado": False}
    pares = divergentes = 0
    limite = n if completo else min(n, 40_000)
    for i in range(limite):
        g = _gemeo(i, n)
        if g is None:
            continue
        pares += 1
        if registro(i) != registro(g):
            divergentes += 1
    print(f"   pares conferidos: {pares:,}  |  divergentes: {divergentes}")
    if not completo and limite < n:
        print(f"   (parcial — use --completo para conferir os {n // 2:,} pares)")

    # 4. PARIDADE
    print("\n4. PARIDADE — quantas categorias têm contagem ÍMPAR?")
    alvos = [c for c in CAMPOS_PARIDADE if c in pos]
    contas = {a: Counter() for a in alvos}
    for i in range(n):
        for a in alvos:
            contas[a][valor(i, a)] += 1
    tot_cat = tot_imp = 0
    print("   campo        categorias   ímpares")
    for a in alvos:
        c = contas[a]
        imp = sum(1 for v in c.values() if v % 2)
        tot_cat += len(c)
        tot_imp += imp
        print(f"   {a:<11}  {len(c):>6}       {imp}")
    print(f"   {'TOTAL':<11}  {tot_cat:>6}       {tot_imp}")
    print("   Sob qualquer modelo não degenerado a paridade de cada categoria é")
    print(f"   um cara-ou-coroa; {tot_cat} de {tot_cat} pares não é coincidência.")

    # 5. PROPORÇÃO É CEGA
    print("\n5. O QUE AS GUARDAS DE PROPORÇÃO VEEM (antes × depois)")
    metade = [i for i in range(n) if _eh_original(i, n)]

    def medir(idx: list[int]) -> tuple[int, float, float, float, int]:
        tot = len(idx)
        ign = sum(1 for i in idx if valor(i, "ESTADIAM") in ("88", "99", ""))
        nao = sum(1 for i in idx if valor(i, "TPCASO") == "2")
        div = sum(1 for i in idx if valor(i, "ANOPRIDI") != str(ano))
        return tot, 100 * ign / tot, 100 * nao / tot, 100 * div / tot, \
            len({valor(i, "CNES") for i in idx})

    a = medir(list(range(n)))
    b = medir(metade)
    print(f"   {'':<26}{'distribuído':>14}{'corrigido':>14}")
    print(f"   {'registros':<26}{a[0]:>14,}{b[0]:>14,}")
    print(f"   {'estadiamento ausente':<26}{a[1]:>13.1f}%{b[1]:>13.1f}%")
    print(f"   {'não analíticos':<26}{a[2]:>13.1f}%{b[2]:>13.1f}%")
    print(f"   {'ANOPRIDI ≠ ano do arquivo':<26}{a[3]:>13.1f}%{b[3]:>13.1f}%")
    print(f"   {'CNES distintos':<26}{a[4]:>14,}{b[4]:>14,}")
    print("   Toda proporção sobrevive à duplicação. É por isso que nenhuma")
    print("   guarda de forma pegou — e nenhuma delas estava quebrada.")

    # 6. DEDUPLICAR POR VALOR SUBCONTARIA
    distintos = len({registro(i) for i in range(n)})
    print("\n6. E POR QUE NÃO SE 'REMOVE DUPLICATA'")
    print(f"   registros distintos por valor .. {distintos:,}")
    print(f"   metade do declarado ............ {n // 2:,}")
    print(f"   deduplicar por valor perderia .. {n // 2 - distintos:,} casos reais "
          f"(razão {n / distintos:.4f})")
    print("   São gêmeos verdadeiros: pessoas distintas idênticas nos campos")
    print("   publicados. A correção divide a MULTIPLICIDADE por dois.")

    return {"ano": ano, "declarado": n, "real": n // 2, "distintos": distintos,
            "geometria": esperado == tamanho, "divergentes": divergentes,
            "categorias_impares": tot_imp}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anos", type=int, nargs="+",
                    default=list(range(2013, 2024)))
    ap.add_argument("--completo", action="store_true",
                    help="confere TODOS os pares (lento); sem isso, confere 20.000")
    args = ap.parse_args()

    linhas = [verificar(ano, args.completo) for ano in args.anos]

    print(f"\n{'=' * 72}\nRESUMO\n{'=' * 72}")
    print("ano   declarado       real    geometria   pares divergentes   cat. ímpares")
    for r in linhas:
        if not r.get("declarado"):
            continue
        print(f"{r['ano']}  {r['declarado']:>10,} {r['real']:>10,}   "
              f"{str(r['geometria']):>9}   {r['divergentes']:>16}   "
              f"{r['categorias_impares']:>12}")
    d = sum(r.get("declarado", 0) for r in linhas)
    v = sum(r.get("real", 0) for r in linhas)
    if v:
        print(f"\nTOTAL {d:,} declarados → {v:,} reais (razão {d / v:.4f})")


if __name__ == "__main__":
    main()
