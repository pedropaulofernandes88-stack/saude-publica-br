"""
conferir_coleta.py — os checkpoints do SIH estão completos?
===========================================================

Complementa `validar_camadas.py`, que confere se as camadas concordam entre si.
Concordar não é bastar: se um mês nunca entrou no cálculo, Parquet, Storage e
Postgres concordam em um número errado. Foi exatamente o que aconteceu em
2026-08 — ver "Integridade da coleta" em `docs/ARQUITETURA_DADOS.md`.

Três conferências, nenhuma delas confiando na contagem de linhas:

  1. CARIMBO      checkpoint que declara menos meses do que o FTP publica hoje.
  2. CALENDÁRIO   a família `demanda` tem `ano_mes`: o mês faltante aparece
                  direto, sem precisar de referência externa.
  3. CRUZADA      `ckpt` (por município) e `hosp_ckpt` (por CNES) leem os mesmos
                  arquivos RD por caminhos independentes. Os totais de
                  internações têm que bater EXATO por UF/ano; divergir significa
                  que uma das duas perdeu arquivo.

Uso:
    .venv311/Scripts/python scripts/conferir_coleta.py            # sem rede
    .venv311/Scripts/python scripts/conferir_coleta.py --com-ftp  # inclui (1)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _datasus_ftp import FTP_DIR_SIH, meses_do_checkpoint, meses_publicados  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SIH = ROOT / "data" / "raw" / "SIH"


def _uf_ano(caminho: Path) -> tuple[str, int]:
    partes = caminho.stem.replace("_v2", "").split("_")
    return partes[-2], int(partes[-1])


def conferir_calendario() -> list[str]:
    """A família `demanda` carrega `ano_mes`: mês faltante se vê a olho nu."""
    problemas = []
    for f in sorted((SIH / "hosp_ckpt").glob("demanda_*_v2.parquet")):
        uf, ano = _uf_ano(f)
        meses = {int(str(x)[-2:]) for x in pd.read_parquet(f)["ano_mes"].unique()}
        faltando = sorted(set(range(1, 13)) - meses)
        if faltando and ano < pd.Timestamp.today().year - 1:
            problemas.append(f"demanda {uf} {ano}: sem os meses {faltando}")
    return problemas


def conferir_cruzada() -> list[str]:
    """`ckpt` e `hosp_ckpt` leem os mesmos RD por caminhos independentes."""
    problemas = []
    for f in sorted((SIH / "ckpt").glob("sih_*_v2.parquet")):
        uf, ano = _uf_ano(f)
        par = SIH / "hosp_ckpt" / f"demanda_{uf}_{ano}_v2.parquet"
        if not par.exists():
            continue
        a = int(pd.read_parquet(f)["internacoes"].sum())
        b = int(pd.read_parquet(par)["internacoes"].sum())
        if a != b:
            problemas.append(
                f"{uf} {ano}: ckpt={a:,} vs hosp_ckpt={b:,} (dif {a - b:+,}) — "
                "uma das duas famílias perdeu arquivo")
    return problemas


def conferir_carimbo() -> list[str]:
    """Checkpoint carimbado com menos meses do que o FTP publica hoje."""
    problemas = []
    for pasta, prefixos in (("fluxo_ckpt", ("fluxo", "icsap")),
                            ("ckpt", ("sih",)),
                            ("hosp_ckpt", ("demanda", "hsmr_hosp")),
                            ("agravo_ckpt", ("agravo",))):
        for prefixo in prefixos:
            for f in sorted((SIH / pasta).glob(f"{prefixo}_*_v2.parquet")):
                uf, ano = _uf_ano(f)
                meses = meses_do_checkpoint(f)
                if meses is None:
                    continue                     # legado, sem carimbo
                publicados = set(meses_publicados(FTP_DIR_SIH, f"RD{uf}", ano))
                if not publicados.issubset(meses):
                    problemas.append(
                        f"{f.name}: carimbado com {sorted(meses)}, o FTP publica "
                        f"{sorted(publicados)}")
    return problemas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--com-ftp", action="store_true",
                    help="também confere o carimbo contra a listagem do FTP")
    args = ap.parse_args()

    blocos = [("calendário (meses ausentes na demanda)", conferir_calendario()),
              ("cruzada (ckpt × hosp_ckpt)", conferir_cruzada())]
    if args.com_ftp:
        blocos.append(("carimbo × FTP", conferir_carimbo()))

    total = 0
    for nome, problemas in blocos:
        print(f"\n── {nome} " + "─" * max(0, 46 - len(nome)))
        if problemas:
            total += len(problemas)
            for p in problemas:
                print(f"[FALHA] {p}")
        else:
            print("[OK ] nada a relatar")

    print()
    if total:
        print(f"❌ {total} problema(s) de coleta — apague o checkpoint e refaça o ano")
        return 1
    print("✅ coleta completa em todos os checkpoints conferidos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
