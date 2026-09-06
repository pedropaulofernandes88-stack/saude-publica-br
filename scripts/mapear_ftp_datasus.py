"""
mapear_ftp_datasus.py — o que dá para pegar pelo FTP do DataSUS
================================================================

    .venv311/Scripts/python scripts/mapear_ftp_datasus.py
    .venv311/Scripts/python scripts/mapear_ftp_datasus.py --md docs/FTP_DATASUS.md

Inventaria os diretórios públicos do FTP: quantos arquivos, quanto pesam e que
período cobrem. Reexecutável de propósito — o FTP muda, e um mapa escrito à mão
envelhece em silêncio como toda coluna copiada neste projeto.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
As etapas 2, 3 e 4 do plano de evolução travaram todas no mesmo lugar: o portal
do OpenDataSUS em HTTP 500 e a API de dados abertos incapaz de entregar a
segunda página de qualquer recorte. Não é azar de uma fonte — é uma dependência
única de todo o roteiro de expansão.

O FTP é a rota que o projeto já usa com sucesso para SIM, SIH, CNES e PNI, e
ela responde. Este mapa mostra o que mais está lá, para que a escolha da
próxima fonte seja feita sobre disponibilidade medida em vez de catálogo.

A ARMADILHA DO ANO DE DOIS DÍGITOS
-----------------------------------
Os arquivos do SINAN terminam em dois dígitos de ano: `DENGBR25.dbc`. Decodificar
como `2000 + yy` parece óbvio e está errado: existe `HANTBR99.dbc`, que é
**1999**, ao lado de `HANTBR00`..`HANTBR24`. Um coletor ingênuo colocaria dado de
1999 em 2099 — um ano futuro solitário entre 741 arquivos, que ninguém repara.

`ano_de_dois_digitos` resolve pela única regra que se sustenta: ano maior que o
corrente pertence ao século passado.
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from datetime import date
from ftplib import FTP
from pathlib import Path

HOST = "ftp.datasus.gov.br"
RAIZ = "/dissemin/publicos"

#: Formato do `LIST` do IIS, que é o servidor do DataSUS:
#:     08-05-26  05:32PM              6871189 POBR2013.dbc
#: O parser de `ls` do Unix (permissões, dono, grupo…) não casa com isto e
#: devolve zero arquivos sem erro nenhum — o diretório parece vazio.
LINHA_IIS = re.compile(r"^(\d{2}-\d{2}-\d{2})\s+\S+\s+(<DIR>|\d+)\s+(.+)$")

#: As GRAMÁTICAS de nome de arquivo do DataSUS. Cada diretório declara a sua.
#:
#: Farejar "qualquer sequência 19xx/20xx no nome" parece funcionar e erra em
#: silêncio: `PASP2412.dbc` é São Paulo em 2024, mês 12, e um `re.search` solto
#: casa "2412"… ou pior, em `SADTO1901.dbc` (Tocantins, 2019, mês 01) casa
#: "1901" e lê o arquivo como do século retrasado. Medido: com o regex solto, o
#: maior diretório do FTP saía como "1901–2026".
#:
#: Nome de arquivo é CONTRATO da fonte, não texto para adivinhar. Diretório com
#: gramática desconhecida diz que não sabe.
GRAMATICAS: dict[str, re.Pattern[str]] = {
    # DENGBR25.dbc, HANTBR99.dbc — nacional, ano de dois dígitos
    "sinan": re.compile(r"^[A-Z]+BR(\d{2})\.dbc$", re.I),
    # PASP2412.dbc, RDAC0801.dbc, CIHAAC1101.dbc — grupo+UF+AA+MM.
    # O sufixo opcional cobre os arquivos PARTIDOS; ver PARTIDO abaixo.
    "uf_mes": re.compile(r"^[A-Z]+(\d{2})(\d{2})([a-z]|_\d)?\.dbc$", re.I),
    # POBR2013.dbc — nacional, ano de quatro dígitos
    "ano4_dbc": re.compile(r"^[A-Z]+(\d{4})\.dbc$", re.I),
    # SISCAN_CITO_COLO_2013.csv
    "ano4_csv": re.compile(r"_(\d{4})\.csv$", re.I),
    # RESPAC15.dbc — prefixo+UF+AA, sem mês
    "uf_ano2": re.compile(r"^[A-Z]+(\d{2})\.dbc$", re.I),
    # CPNIAC00.DBF — o PNI usa .DBF, não .dbc
    "uf_ano2_dbf": re.compile(r"^[A-Z]+(\d{2})\.dbf$", re.I),
}

#: ARQUIVOS PARTIDOS — duas convenções, e são armadilhas OPOSTAS.
#:
#: Competência grande demais para um arquivo é quebrada, e o DataSUS usa duas
#: formas incompatíveis no MESMO diretório do SIA. Medido em 2026-09-06:
#:
#:   PASP2412a/b/c.dbc (105+110+89 MB) — o base `PASP2412.dbc` NÃO EXISTE.
#:       Coletor que procure o base não acha nada e registra "competência
#:       ausente": some a produção ambulatorial inteira de SP em dez/2024.
#:
#:   BIMG2305_1/_2.dbc (216+28 MB) — o base `BIMG2305.dbc` EXISTE, com 247 MB
#:       ≈ a soma das partes. Coletor que pegue tudo que casa com o prefixo
#:       conta MG em maio/2023 DUAS VEZES.
#:
#: Uma convenção pune quem lê de menos, a outra pune quem lê de mais, e as duas
#: falham em silêncio: ausência vira "competência não publicada", duplicata vira
#: total plausível. São 977 arquivos assim no SIA — 1,8% dos nomes, concentrados
#: em SP, RJ e MG, que são justamente os que mais pesam em qualquer agregado.
PARTIDO = re.compile(r"^([A-Z]+\d{4})([a-z]|_\d)\.dbc$", re.I)

#: `DOAC1996.dbc` (SIM) e `PASP2412.dbc` (SIA) têm a MESMA forma — letras
#: seguidas de quatro dígitos — e significados diferentes: ano de quatro
#: dígitos num, ano+mês de dois no outro. Nenhuma regra lê os dois certo, e foi
#: assim que este script leu o SIM como "2019–2020" na primeira versão: a
#: gramática de AAMM casou `DOAC2019` e devolveu 2020.
#: É a razão de a gramática ser declarada POR DIRETÓRIO e não inferida.

#: Diretórios que interessam: caminho, rótulo, o que destrava, e a gramática.
#: O texto é editorial — não se deriva da listagem.
DIRETORIOS: list[tuple[str, str, str, str]] = [
    ("SINAN/DADOS/FINAIS", "SINAN consolidado", "45 agravos de notificação compulsória", "sinan"),
    ("SINAN/DADOS/PRELIM", "SINAN preliminar", "inclui sífilis (SIFA/SIFG/SIFC)", "sinan"),
    ("SISCAN/SISCAN", "SISCAN (CSV)", "citopatológico de colo e mamografia", "ano4_csv"),
    ("painel_oncologia/Dados", "Painel Oncologia", "nacional por ano", "ano4_dbc"),
    ("SIASUS/200801_/Dados", "SIA/SUS", "produção ambulatorial, por UF e competência", "uf_mes"),
    ("CIHA/201101_/Dados", "CIHA", "internações e atendimentos fora do SUS", "uf_mes"),
    ("RESP/DADOS", "RESP", "eventos de saúde pública (microcefalia/arbovirose)", "uf_ano2"),
    ("SISPRENATAL/201201_/Dados", "SISPRENATAL", "acompanhamento pré-natal", "uf_mes"),
    ("PNI/DADOS", "PNI", "imunização — já usado pelo projeto", "uf_ano2_dbf"),
    ("SIM/CID10/DORES", "SIM consolidado", "já usado pelo projeto", "ano4_dbc"),
    ("SIHSUS/200801_/Dados", "SIH/SUS", "já usado pelo projeto", "uf_mes"),
]


def ano_de_dois_digitos(yy: int, hoje: date | None = None) -> int:
    """`99` é 1999, `25` é 2025.

    A regra: se `2000 + yy` for FUTURO, o ano é do século passado. É a única
    que se sustenta sem tabela de exceções — e a que impede `HANTBR99.dbc`,
    que é de 1999, de entrar na série como 2099.
    """
    ano = 2000 + yy
    limite = (hoje or date.today()).year
    return ano - 100 if ano > limite else ano


def listar(ftp: FTP, caminho: str) -> dict[str, int] | None:
    """Nome → bytes. `None` quando o diretório não existe ou não abre."""
    try:
        ftp.cwd(caminho)
    except Exception:
        return None
    linhas: list[str] = []
    ftp.retrlines("LIST", linhas.append)
    saida: dict[str, int] = {}
    for linha in linhas:
        m = LINHA_IIS.match(linha.strip())
        if m and m.group(2) != "<DIR>":
            saida[m.group(3)] = int(m.group(2))
    return saida


def periodo(nomes: list[str], gramatica: str) -> tuple[str, int]:
    """O intervalo coberto e quantos nomes NÃO casaram com a gramática.

    Devolver os que não casaram é o ponto: um diretório onde metade dos
    arquivos escapa da regra não tem período conhecido, tem período de metade —
    e um mapa que informasse esse recorte como se fosse o todo seria pior que
    um mapa que diz não saber.
    """
    padrao = GRAMATICAS.get(gramatica)
    if padrao is None:
        return "gramática não declarada", len(nomes)
    anos: set[int] = set()
    fora = 0
    for n in nomes:
        m = padrao.match(n) if padrao.pattern.startswith("^") else padrao.search(n)
        if not m:
            fora += 1
            continue
        bruto = m.group(1)
        anos.add(int(bruto) if len(bruto) == 4 else ano_de_dois_digitos(int(bruto)))
    if not anos:
        return "nenhum nome casou com a gramática", fora
    return f"{min(anos)}–{max(anos)}", fora


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Inventário do FTP público do DataSUS.")
    ap.add_argument("--md", type=Path, help="grava o mapa em Markdown neste caminho")
    args = ap.parse_args()

    ftp = FTP(HOST, timeout=180)
    ftp.login()

    linhas_md = [
        "| diretório | o que traz | arquivos | tamanho | período |",
        "|---|---|---:|---:|---|",
    ]
    print(f"{'diretório':28} {'arquivos':>8} {'tamanho':>10}  período")
    print("-" * 72)
    for caminho, rotulo, traz, gramatica in DIRETORIOS:
        arqs = listar(ftp, f"{RAIZ}/{caminho}")
        if arqs is None:
            print(f"{rotulo:28} {'—':>8} {'—':>10}  diretório não abriu")
            linhas_md.append(f"| `{caminho}` | {traz} | — | — | não abriu |")
            continue
        if not arqs:
            print(f"{rotulo:28} {0:>8} {'—':>10}  sem arquivos")
            linhas_md.append(f"| `{caminho}` | {traz} | 0 | — | sem arquivos |")
            continue
        gb = sum(arqs.values()) / 1024 ** 3
        tam = f"{gb:.2f} GB" if gb >= 0.01 else f"{sum(arqs.values()) / 1024 ** 2:.0f} MB"
        per, fora = periodo(sorted(arqs), gramatica)
        partidos = sum(1 for n in arqs if PARTIDO.match(n))
        aviso = f"  ⚠ {fora} nome(s) fora da gramática" if fora else ""
        if partidos:
            aviso += f"  ⚠ {partidos} arquivo(s) PARTIDO(s)"
        print(f"{rotulo:28} {len(arqs):>8,} {tam:>10}  {per}{aviso}")
        obs = []
        if fora:
            obs.append(f"{fora} fora da gramática")
        if partidos:
            obs.append(f"**{partidos} partidos**")
        linhas_md.append(
            f"| `{caminho}` | {traz} | {len(arqs):,} | {tam} | {per}"
            f"{' — ' + ', '.join(obs) if obs else ''} |")

    # Detalhe do SINAN por agravo: é o diretório com mais opções e o único em
    # que a escolha da fonte é uma escolha de AGRAVO, não de sistema.
    agravos = listar(ftp, f"{RAIZ}/SINAN/DADOS/PRELIM") or {}
    porag: dict[str, list[int]] = collections.defaultdict(list)
    for nome in agravos:
        if m := re.match(r"^([A-Z]+?)BR(\d{2})\.dbc$", nome, re.I):
            porag[m.group(1).upper()].append(ano_de_dois_digitos(int(m.group(2))))
    if porag:
        print(f"\nSINAN/PRELIM — {len(porag)} agravos:")
        for ag in sorted(porag):
            a = porag[ag]
            print(f"   {ag:6} {min(a)}–{max(a)}")

    ftp.quit()

    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        cab = (f"# O que dá para pegar pelo FTP do DataSUS\n\n"
               f"Inventário gerado por `scripts/mapear_ftp_datasus.py` em "
               f"{date.today().isoformat()}. Reexecute em vez de editar à mão.\n\n")
        args.md.write_text(cab + "\n".join(linhas_md) + "\n", encoding="utf-8")
        print(f"\n[ok] mapa em {args.md}")


if __name__ == "__main__":
    main()
