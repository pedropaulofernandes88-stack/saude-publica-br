"""
analise_leitos_hsmr.py — o HSMR mede porte e complexidade do hospital?

A pagina /hospitalar ja declara que o HSMR tem vies de case-mix residual:
hospitais classificados "acima do esperado" sao ~5x maiores (mediana 5.350 vs
1.136 internacoes) e concentram 58,9% dos obitos hospitalares. O ajuste por
capitulo CID-10 e grosseiro -- um capitulo cobre desde hipertensao ate cirurgia
cardiaca complexa -- e hospitais terciarios concentram os casos graves DENTRO
do mesmo capitulo.

Ate agora essa era uma suspeita medida por proxy (numero de internacoes, que e
consequencia e nao causa). Com os leitos do CNES ha a medida DIRETA de porte e,
melhor ainda, de complexidade: a existencia de UTI.

Junção limpa: HSMR e por estabelecimento (CNES) e o grupo LT tambem traz CNES.
Nao ha aqui a armadilha residencia-x-estabelecimento do cruzamento com ICSAP.

DUAS HIPOTESES TESTAVEIS SEPARADAMENTE:
  (a) PORTE: HSMR sobe com o numero de leitos.
  (b) COMPLEXIDADE: hospital com UTI recebe o caso grave. O ajuste por capitulo
      CID nao enxerga gravidade, so diagnostico. Se (b) valer, ter UTI eleva o
      HSMR mesmo comparando hospitais de porte semelhante -- e isso e case-mix
      nao capturado, nao qualidade pior.

Se (b) se confirmar, a leitura "HSMR alto = assistencia pior" fica ainda mais
fragil do que a pagina ja declara: parte do sinal e "este hospital trata caso
grave".

Uso:
  .venv311/Scripts/python scripts/analise_leitos_hsmr.py
"""
from __future__ import annotations

import sys
import os
import time
from collections import defaultdict
from ftplib import FTP
from pathlib import Path

import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "CNES" / "leitos_cnes_ckpt"
TMP = ROOT / "data" / "raw" / "CNES" / "_tmp"

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/CNES/200508_/Dados/LT"
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
       "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
ANO = 2024

# Mesma lista explicita de pipeline_cnes_leitos.py: o codigo 84, no meio da
# faixa, e "acolhimento noturno" e nao e UTI.
CODIGOS_UTI = {"74", "75", "76", "77", "78", "79", "80", "81", "82", "83", "85", "86"}


def spearman(x: pd.Series, y: pd.Series) -> tuple[float, int]:
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 10:
        return float("nan"), len(d)
    return float(d["x"].corr(d["y"], method="spearman")), len(d)


def leitos_por_cnes(uf: str) -> pd.DataFrame | None:
    """Leitos agregados por ESTABELECIMENTO (não por município)."""
    import datasus_dbc
    import dbfread

    ck = CKPT / f"leitos_cnes_{uf}_{ANO}.parquet"
    if ck.exists():
        return pd.read_parquet(ck)

    nome = f"LT{uf}{ANO % 100:02d}12.dbc"
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
                return None
            if tentativa == 3:
                print(f"  [{uf}] FALHOU: {e}", flush=True)
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

    df = pd.DataFrame([{"cnes": c, **dict(v)} for c, v in agg.items()])
    CKPT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ck, compression="zstd", index=False)
    print(f"  [{uf}] {len(df):,} estabelecimentos com leito", flush=True)
    return df


def baixar_hsmr() -> pd.DataFrame:
    env = {}
    f = ROOT / ".env"
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})
    url, key = env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    rows, offset = [], 0
    while True:
        r = requests.get(f"{url.rstrip('/')}/rest/v1/mart_hsmr_hospital",
                         headers={**h, "Range-Unit": "items", "Range": f"{offset}-{offset+999}"},
                         params={"select": "cnes,municipio_nome,uf_sigla,ano,internacoes,"
                                           "obitos_observados,obitos_esperados,hsmr,estavel,significancia",
                                 "ano": f"eq.{ANO}"}, timeout=120)
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < 1000:
            break
        offset += 1000
    return pd.DataFrame(rows)


def main() -> None:
    print(f"=== Leitos por estabelecimento (CNES), {ANO} ===")
    partes = [d for uf in UFS if (d := leitos_por_cnes(uf)) is not None]
    leitos = pd.concat(partes, ignore_index=True)
    for c in ["leitos_total", "leitos_sus", "leitos_uti"]:
        leitos[c] = leitos[c].fillna(0).astype(int)
    print(f"  total: {len(leitos):,} estabelecimentos com leito no Brasil")

    hsmr = baixar_hsmr()
    print(f"\n=== HSMR {ANO}: {len(hsmr):,} hospitais ===")

    df = hsmr.merge(leitos, on="cnes", how="left")
    df["tem_leito_cnes"] = df.leitos_total.notna() & (df.leitos_total > 0)
    print(f"  casaram com o cadastro de leitos: {df.tem_leito_cnes.sum():,} "
          f"({df.tem_leito_cnes.mean()*100:.1f}%)")
    print("  (hospitais do SIH sem leito no CNES daquela competencia sao esperados:")
    print("   faturaram no ano mas podem ter fechado ou nao constar em dezembro)")

    d = df[df.tem_leito_cnes].copy()
    for c in ["leitos_total", "leitos_sus", "leitos_uti"]:
        d[c] = d[c].astype(int)
    d["tem_uti"] = d.leitos_uti > 0
    d["hsmr"] = pd.to_numeric(d.hsmr, errors="coerce")

    print("\n=== 1. HIPOTESE (a) — HSMR sobe com o PORTE (leitos)? ===")
    r1, n1 = spearman(d["leitos_total"], d["hsmr"])
    print(f"  leitos totais x HSMR: rho = {r1:+.3f}  (n={n1:,})")
    r2, _ = spearman(d["internacoes"], d["hsmr"])
    print(f"  internacoes x HSMR  : rho = {r2:+.3f}  (proxy antigo, para comparar)")

    print("\n=== 2. HIPOTESE (b) — ter UTI eleva o HSMR? ===")
    com_uti, sem_uti = d[d.tem_uti], d[~d.tem_uti]
    print(f"  hospitais COM UTI: {len(com_uti):,} | SEM UTI: {len(sem_uti):,}")
    print(f"  HSMR mediano -- COM UTI: {com_uti.hsmr.median():.3f} | "
          f"SEM UTI: {sem_uti.hsmr.median():.3f}")
    r3, n3 = spearman(d["leitos_uti"], d["hsmr"])
    print(f"  leitos de UTI x HSMR: rho = {r3:+.3f}  (n={n3:,})")

    print("\n=== 3. O teste decisivo: UTI importa DENTRO do mesmo porte? ===")
    print("  (se ter UTI eleva o HSMR mesmo entre hospitais de tamanho parecido,")
    print("   o sinal e complexidade do caso, nao porte nem qualidade)")
    d["porte_quartil"] = pd.qcut(d["leitos_total"], 4,
                                  labels=["Q1 (menores)", "Q2", "Q3", "Q4 (maiores)"], duplicates="drop")
    for _, g in d.groupby("porte_quartil", observed=True):
        cu, su = g[g.tem_uti], g[~g.tem_uti]
        if len(cu) < 10 or len(su) < 10:
            print(f"  {g['porte_quartil'].iloc[0]:16s} amostra insuficiente "
                  f"(com UTI {len(cu)}, sem UTI {len(su)})")
            continue
        print(f"  {g['porte_quartil'].iloc[0]:16s} leitos med={g.leitos_total.median():5.0f} | "
              f"HSMR com UTI={cu.hsmr.median():.3f} (n={len(cu):4,})  "
              f"sem UTI={su.hsmr.median():.3f} (n={len(su):4,})  "
              f"dif={cu.hsmr.median()-su.hsmr.median():+.3f}")

    print("\n=== 4. A flag 'acima do esperado' se concentra onde? ===")
    sig = d[d.significancia.isin(["acima", "abaixo", "esperado"])]
    if len(sig):
        for _, g in sig.groupby("porte_quartil", observed=True):
            acima = (g.significancia == "acima").mean() * 100
            print(f"  {g['porte_quartil'].iloc[0]:16s} n={len(g):4,}  "
                  f"'acima do esperado': {acima:5.1f}%  | leitos med={g.leitos_total.median():5.0f}  "
                  f"com UTI: {g.tem_uti.mean()*100:4.1f}%")

    print("\n=== Leitura ===")
    dif_medias = []
    for _, g in d.groupby("porte_quartil", observed=True):
        cu, su = g[g.tem_uti], g[~g.tem_uti]
        if len(cu) >= 10 and len(su) >= 10:
            dif_medias.append(cu.hsmr.median() - su.hsmr.median())
    if dif_medias and all(x > 0 for x in dif_medias):
        print("  => ter UTI eleva o HSMR em TODOS os quartis de porte testados")
        print(f"     (diferencas: {', '.join(f'{x:+.3f}' for x in dif_medias)}).")
        print("     Isso e case-mix nao capturado pelo ajuste por capitulo CID: o ajuste")
        print("     enxerga diagnostico, nao gravidade. Hospital com UTI recebe o caso")
        print("     grave do MESMO capitulo. Reforca a ressalva ja publicada de que HSMR")
        print("     alto nao deve ser lido como assistencia pior.")
    else:
        print("  => o efeito da UTI nao e consistente entre os quartis de porte")
        print(f"     (diferencas: {[f'{x:+.3f}' for x in dif_medias]}) — nao generalizar.")

    out = d[["cnes", "municipio_nome", "uf_sigla", "internacoes", "obitos_observados",
             "obitos_esperados", "hsmr", "significancia", "leitos_total", "leitos_sus",
             "leitos_uti", "tem_uti"]].copy()
    out["ano"] = ANO
    out.to_parquet(MARTS / "mart_leitos_hsmr_hospital.parquet", compression="zstd", index=False)
    print(f"\n[mart] mart_leitos_hsmr_hospital: {len(out):,} hospitais")


if __name__ == "__main__":
    main()
