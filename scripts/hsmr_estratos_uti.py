"""
hsmr_estratos_uti.py — tabela de estratos (com/sem UTI) por hospital e ano

O HSMR e padronizado indiretamente por faixa etaria x capitulo CID-10. Esse
ajuste enxerga DIAGNOSTICO, nao GRAVIDADE: dentro do mesmo capitulo cabem o
caso leve e o caso critico. Hospitais com UTI recebem sistematicamente o caso
critico, entao acumulam mais obitos do que o esperado nacional para aquele
capitulo -- sem que isso signifique pior assistencia.

Medido em 2024 (scripts/analise_leitos_hsmr.py):
  O/E agregado, hospitais COM UTI : 1,163
  O/E agregado, hospitais SEM UTI : 0,542
  (o nacional e 1,000 por construcao, mas nenhum dos dois grupos esta em 1)

Este script produz a chave de estratificacao que permite comparar cada
hospital aos seus pares reais, em vez de ao Brasil inteiro -- mesmo principio
ja aplicado ao ICSAP e a cobertura da APS.

Fonte: CNES grupo LT (FTP DataSUS), competencia de dezembro de cada ano, por
ESTABELECIMENTO. A condicao de ter UTI e avaliada ANO A ANO: um hospital que
abre UTI muda de estrato no ano em que abre.

Uso:
  .venv311/Scripts/python scripts/hsmr_estratos_uti.py --anos 2022 2023 2024
"""
from __future__ import annotations

import argparse
import time
from collections import defaultdict
from ftplib import FTP
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
CKPT = ROOT / "data" / "raw" / "CNES" / "leitos_cnes_ckpt"
TMP = ROOT / "data" / "raw" / "CNES" / "_tmp"

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/CNES/200508_/Dados/LT"
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
       "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]

# Lista explicita (o codigo 84, no meio da faixa, e "acolhimento noturno").
CODIGOS_UTI = {"74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "85", "86"}


def leitos_por_cnes(uf: str, ano: int) -> pd.DataFrame | None:
    import datasus_dbc
    import dbfread

    ck = CKPT / f"leitos_cnes_{uf}_{ano}.parquet"
    if ck.exists():
        d = pd.read_parquet(ck)
        # checkpoints gravados por analise_leitos_hsmr.py nao trazem a coluna
        # `ano` (era um script de ano unico) — o ano vem do nome do arquivo.
        if "ano" not in d.columns:
            d["ano"] = ano
        return d

    nome = f"LT{uf}{ano % 100:02d}12.dbc"
    TMP.mkdir(parents=True, exist_ok=True)
    dbc, dbf = TMP / nome, TMP / nome.replace(".dbc", ".dbf")
    for tentativa in range(4):
        try:
            ftp = FTP(FTP_HOST, timeout=90)
            ftp.login()
            ftp.cwd(FTP_DIR)
            with open(dbc, "wb") as f:
                ftp.retrbinary(f"RETR {nome}", f.write)
            ftp.quit()
            break
        except Exception as e:
            if "550" in str(e):
                print(f"  [{uf} {ano}] ausente no FTP", flush=True)
                return None
            if tentativa == 3:
                print(f"  [{uf} {ano}] FALHOU: {e}", flush=True)
                return None
            time.sleep(3 * (tentativa + 1))

    try:
        datasus_dbc.decompress(str(dbc), str(dbf))
        registros = list(dbfread.DBF(str(dbf), encoding="latin-1"))
    finally:
        for p in (dbc, dbf):
            p.unlink(missing_ok=True)

    agg: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in registros:
        cnes = str(r.get("CNES") or "").strip()
        if not cnes:
            continue
        a = agg[cnes]
        a["leitos_total"] += int(r.get("QT_EXIST") or 0)
        a["leitos_sus"] += int(r.get("QT_SUS") or 0)
        if str(r.get("CODLEITO") or "").strip() in CODIGOS_UTI:
            a["leitos_uti"] += int(r.get("QT_EXIST") or 0)

    df = pd.DataFrame([{"cnes": c, "ano": ano, **dict(v)} for c, v in agg.items()])
    CKPT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ck, compression="zstd", index=False)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", type=int, nargs="+", default=[2022, 2023, 2024])
    args = ap.parse_args()

    partes = []
    for ano in args.anos:
        print(f"=== ANO {ano} ===", flush=True)
        for uf in UFS:
            d = leitos_por_cnes(uf, ano)
            if d is not None and len(d):
                partes.append(d)
        print(f"  acumulado: {sum(len(p) for p in partes):,} linhas", flush=True)

    df = pd.concat(partes, ignore_index=True)
    for c in ["leitos_total", "leitos_sus", "leitos_uti"]:
        df[c] = df[c].fillna(0).astype(int)
    df = df.groupby(["cnes", "ano"], as_index=False)[["leitos_total", "leitos_sus", "leitos_uti"]].sum()
    df["tem_uti"] = df.leitos_uti > 0

    REFS.mkdir(parents=True, exist_ok=True)
    destino = REFS / "hsmr_estratos_uti.parquet"
    df.to_parquet(destino, compression="zstd", index=False)

    print(f"\n[estratos] {len(df):,} linhas hospital-ano salvas em {destino.name}")
    for ano, g in df.groupby("ano"):
        print(f"  {ano}: {len(g):,} estabelecimentos com leito | "
              f"com UTI {g.tem_uti.sum():,} ({g.tem_uti.mean()*100:.1f}%)")


if __name__ == "__main__":
    main()
