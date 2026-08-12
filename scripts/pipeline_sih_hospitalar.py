"""
pipeline_sih_hospitalar.py — HSMR, LOS esperado e demanda mensal por hospital
==============================================================================

Reprocessa os RD do SIH numa única passada adicional (além do
pipeline_sih_agravo.py), capturando por internação: IDADE, COD_IDADE,
DT_INTER, além dos campos já usados (DIAG_PRINC, DIAS_PERM, VAL_TOT, MORTE,
MUNIC_MOV, CNES).

Gera três marts:
  - mart_hsmr_hospital       : óbitos observados vs. esperados (padronização
                                indireta por faixa etária × capítulo CID),
                                por hospital (CNES)
  - mart_los_hospital        : tempo de permanência mediano do hospital vs.
                                mediana nacional, por diagnóstico (CID-3)
  - mart_demanda_mensal_hospital : série mensal de internações por hospital,
                                base para forecast de demanda

Metodologia (ver docs/metodologia hospitalar):
  - HSMR: padronização indireta. Óbitos esperados de um hospital = soma, por
    estrato (faixa etária × capítulo CID), do nº de internações do hospital
    naquele estrato × taxa de mortalidade NACIONAL do mesmo estrato.
    HSMR = óbitos observados / óbitos esperados. HSMR > 1 = mortalidade acima
    do esperado dado o case-mix; HSMR < 1 = abaixo.

    Limiar de estabilidade — óbitos esperados < 5 → `estavel=False`:
    é a regra geral de epidemiologia para razões padronizadas (SMR/HSMR): com
    esperado < 5 a razão fica hipersensível a um único óbito a mais e o IC
    exato de Poisson deixa de ser confiável (OpenEpi, "SMR and Confidence
    Interval", openepi.com/PDFDocs/SMRDoc.pdf). Estudos específicos de HSMR
    às vezes usam corte mais conservador (ex.: 20 óbitos esperados,
    Grant et al. 2016, PubMed 26443555) — mas esses estudos EXCLUEM o
    hospital do relatório. Aqui optamos por não excluir: hospitais pequenos
    continuam no mart, apenas sinalizados como instáveis — coerente com o
    princípio do projeto de não ocultar unidades pequenas, só declarar a
    incerteza.
  - LOS: mediana aproximada via histograma de faixas de dias (não guardamos
    dias individuais por internação, por volume). Faixas: 0-1, 2-3, 4-7,
    8-14, 15-21, 22-30, 31-60, 61+.
  - Faixas etárias (9): <1, 1-4, 5-14, 15-29, 30-44, 45-59, 60-69, 70-79, 80+.
    IDADE só é válida quando COD_IDADE=4 (anos); demais códigos (dias/meses)
    são tratados como <1 ano.
  - TIPO DE AIH: HSMR e LOS são calculados APENAS sobre a AIH normal (IDENT=1).
    A AIH de continuação (IDENT=5) é emitida quando a internação se prolonga
    além do período da AIH anterior — a mesma internação vira várias linhas, com
    mortalidade quase nula (0,21% dos óbitos para 1,26% das linhas) e permanência
    fracionada. Incluí-la dilui o estrato de case-mix e distorce a mediana de
    permanência: no capítulo VI a permanência média cai de 10,98 para 6,21 dias
    quando se restringe à AIH normal. `mart_demanda_mensal_hospital` continua
    contando todas as AIHs aprovadas, porque ali a pergunta é de produção.
    Ver https://rfsaldanha.github.io/sis/sih.html (cap. SIH).

Checkpoint por UF (resumível). Uso:
  .venv311/Scripts/python scripts/pipeline_sih_hospitalar.py --ano 2024 --workers 6
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from ftplib import FTP
from pathlib import Path

import pandas as pd
import requests

from _supabase_key import chave_escrita

# Windows: quando a saida e redirecionada para arquivo, o Python usa cp1252 e um
# unico caractere fora da tabela (ex.: a seta dos logs) derruba o pipeline inteiro
# no meio do processamento. Forca UTF-8 na saida.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "SIH" / "hosp_ckpt"
FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SIHSUS/200801_/Dados"
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
       "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]

CID10_CAPITULOS = [
    ("I","A00","B99"),("II","C00","D48"),("III","D50","D89"),("IV","E00","E90"),
    ("V","F00","F99"),("VI","G00","G99"),("VII","H00","H59"),("VIII","H60","H95"),
    ("IX","I00","I99"),("X","J00","J99"),("XI","K00","K93"),("XII","L00","L99"),
    ("XIII","M00","M99"),("XIV","N00","N99"),("XV","O00","O99"),("XVI","P00","P96"),
    ("XVII","Q00","Q99"),("XVIII","R00","R99"),("XIX","S00","T98"),("XX","V01","Y98"),
    ("XXI","Z00","Z99"),("XXII","U00","U99"),
]

# faixa etária: (label, idade_min_anos, idade_max_anos_inclusive)
FAIXAS = [
    (0, "<1 ano", 0, 0), (1, "1-4", 1, 4), (2, "5-14", 5, 14),
    (3, "15-29", 15, 29), (4, "30-44", 30, 44), (5, "45-59", 45, 59),
    (6, "60-69", 60, 69), (7, "70-79", 70, 79), (8, "80+", 80, 130),
]

# faixas de permanência (dias): (idx, label, min, max_inclusive_ou_None)
LOS_BINS = [
    (0, "0-1", 0, 1), (1, "2-3", 2, 3), (2, "4-7", 4, 7), (3, "8-14", 8, 14),
    (4, "15-21", 15, 21), (5, "22-30", 22, 30), (6, "31-60", 31, 60),
    (7, "61+", 61, None),
]
LOS_MID = [0.5, 2.5, 5.5, 11, 18, 26, 45, 75]  # ponto médio p/ mediana aproximada


def _capitulo(cid3: str) -> str:
    for cap, ini, fim in CID10_CAPITULOS:
        if ini <= cid3 <= fim:
            return cap
    return "N/D"


def _faixa_etaria(idade_raw, cod_idade) -> int:
    try:
        cod = str(cod_idade or "").strip()
        idade = int(idade_raw or 0)
    except (ValueError, TypeError):
        return 0
    if cod != "4":  # não está em anos (dias/meses) → <1 ano
        return 0
    for idx, _label, lo, hi in FAIXAS:
        if lo <= idade <= hi:
            return idx
    return 0


def _los_bin(dias: int) -> int:
    for idx, _label, lo, hi in LOS_BINS:
        if hi is None:
            if dias >= lo:
                return idx
        elif lo <= dias <= hi:
            return idx
    return 0


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})
    return env


def _process_file(uf: str, ano: int, mes: int):
    """Um RD mensal → (hsmr_nac, hsmr_hosp, los_nac, los_hosp, demanda_mensal). None se ausente."""
    import datasus_dbc
    import dbfread
    yymm = f"{ano % 100:02d}{mes:02d}"
    nome = f"RD{uf}{yymm}"
    try:
        ftp = FTP(FTP_HOST, timeout=180); ftp.login()
        try:
            ftp.size(f"{FTP_DIR}/{nome}.dbc")
        except Exception:
            ftp.quit(); return None
        buf = io.BytesIO(); ftp.retrbinary(f"RETR {FTP_DIR}/{nome}.dbc", buf.write); ftp.quit()
    except Exception:
        return None
    tmp = Path(tempfile.gettempdir())
    dbc = tmp / f"{nome}.dbc"; dbf = tmp / f"{nome}.dbf"
    dbc.write_bytes(buf.getvalue())

    hsmr_nac: dict = defaultdict(lambda: [0, 0])          # (faixa, capitulo) -> [n, obitos]
    hsmr_hosp: dict = defaultdict(lambda: [0, 0])          # (cnes, faixa, capitulo) -> [n, obitos]
    los_nac: dict = defaultdict(lambda: [0] * 8)            # cid3 -> [contagem por bin de dias]
    los_hosp: dict = defaultdict(lambda: [0] * 8)            # (cnes, cid3) -> [contagem por bin]
    demanda: dict = defaultdict(lambda: [0, 0, 0.0])         # (cnes, ano_mes) -> [n, obitos, valor]

    try:
        datasus_dbc.decompress(str(dbc), str(dbf))
        for rec in dbfread.DBF(str(dbf), encoding="latin-1", char_decode_errors="replace", load=False):
            cid = (str(rec.get("DIAG_PRINC") or "")).strip().upper()[:3]
            if not cid:
                continue
            cnes = (str(rec.get("CNES") or "")).strip()
            if not cnes or cnes == "0000000":
                continue
            try:
                dias = int(rec.get("DIAS_PERM") or 0)
            except (ValueError, TypeError):
                dias = 0
            try:
                val = float(rec.get("VAL_TOT") or 0)
            except (ValueError, TypeError):
                val = 0.0
            morte = 1 if str(rec.get("MORTE") or "0").strip() == "1" else 0
            faixa = _faixa_etaria(rec.get("IDADE"), rec.get("COD_IDADE"))
            cap = _capitulo(cid)
            # AIH de continuação (IDENT=5): a mesma internação prolongada emite várias
            # linhas. HSMR e LOS são métricas POR EPISÓDIO — contar as continuações
            # infla o denominador com linhas de mortalidade quase nula e fraciona a
            # permanência. A demanda mensal, que mede produção, segue com todas as AIHs.
            cont = str(rec.get("IDENT") or "").strip() == "5"

            if not cont:
                # --- HSMR: nacional + por hospital ---
                n = hsmr_nac[(faixa, cap)]; n[0] += 1; n[1] += morte
                h = hsmr_hosp[(cnes, faixa, cap)]; h[0] += 1; h[1] += morte

                # --- LOS: nacional + por hospital, por diagnóstico (CID-3) ---
                b = _los_bin(max(dias, 0))
                los_nac[cid][b] += 1
                los_hosp[(cnes, cid)][b] += 1

            # --- demanda mensal (produção: todas as AIHs aprovadas) ---
            ano_mes = f"{ano}-{mes:02d}"
            d = demanda[(cnes, ano_mes)]
            d[0] += 1; d[1] += morte; d[2] += val

        return dict(hsmr_nac), dict(hsmr_hosp), dict(los_nac), dict(los_hosp), dict(demanda)
    except Exception:
        return None
    finally:
        dbc.unlink(missing_ok=True); dbf.unlink(missing_ok=True)


def _process_uf(uf: str, ano: int, workers: int):
    CKPT.mkdir(parents=True, exist_ok=True)
    # sufixo _v2: checkpoints antigos incluíam a AIH de continuação em HSMR/LOS
    paths = {k: CKPT / f"{k}_{uf}_{ano}_v2.parquet" for k in
             ("hsmr_nac", "hsmr_hosp", "los_nac", "los_hosp", "demanda")}
    if all(p.exists() for p in paths.values()):
        return {k: pd.read_parquet(p) for k, p in paths.items()}

    hsmr_nac: dict = defaultdict(lambda: [0, 0])
    hsmr_hosp: dict = defaultdict(lambda: [0, 0])
    los_nac: dict = defaultdict(lambda: [0] * 8)
    los_hosp: dict = defaultdict(lambda: [0] * 8)
    demanda: dict = defaultdict(lambda: [0, 0, 0.0])

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_process_file, uf, ano, m): m for m in range(1, 13)}
        for fut in as_completed(futs):
            res = fut.result()
            if not res:
                continue
            hn, hh, ln, lh, dm = res
            for k, v in hn.items():
                t = hsmr_nac[k]; t[0] += v[0]; t[1] += v[1]
            for k, v in hh.items():
                t = hsmr_hosp[k]; t[0] += v[0]; t[1] += v[1]
            for k, v in ln.items():
                t = los_nac[k]
                for i in range(8): t[i] += v[i]
            for k, v in lh.items():
                t = los_hosp[k]
                for i in range(8): t[i] += v[i]
            for k, v in dm.items():
                t = demanda[k]; t[0] += v[0]; t[1] += v[1]; t[2] += v[2]

    out = {
        "hsmr_nac": pd.DataFrame([(f, c, n[0], n[1]) for (f, c), n in hsmr_nac.items()],
                                  columns=["faixa", "capitulo_cid", "internacoes", "obitos"]),
        "hsmr_hosp": pd.DataFrame([(cn, f, c, n[0], n[1]) for (cn, f, c), n in hsmr_hosp.items()],
                                   columns=["cnes", "faixa", "capitulo_cid", "internacoes", "obitos"]),
        "los_nac": pd.DataFrame([(cid, *bins) for cid, bins in los_nac.items()],
                                 columns=["cid3", *[f"bin{i}" for i in range(8)]]),
        "los_hosp": pd.DataFrame([(cn, cid, *bins) for (cn, cid), bins in los_hosp.items()],
                                  columns=["cnes", "cid3", *[f"bin{i}" for i in range(8)]]),
        "demanda": pd.DataFrame([(cn, am, n[0], n[1], round(n[2], 2)) for (cn, am), n in demanda.items()],
                                 columns=["cnes", "ano_mes", "internacoes", "obitos", "valor_total"]),
    }
    for k, p in paths.items():
        out[k].to_parquet(p, compression="zstd", index=False)
    print(f"[hospitalar] {uf} {ano}: {int(out['demanda']['internacoes'].sum()):,} internações | "
          f"{out['demanda']['cnes'].nunique():,} hospitais", flush=True)
    return out


def _mediana_aprox(bins: list[int]) -> float | None:
    """Mediana aproximada a partir de contagens por faixa (ponto médio da faixa)."""
    total = sum(bins)
    if total == 0:
        return None
    alvo = total / 2
    acumulado = 0
    for i, n in enumerate(bins):
        acumulado += n
        if acumulado >= alvo:
            return LOS_MID[i]
    return LOS_MID[-1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", type=int, default=2024)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--min-esperado", type=float, default=5.0,
                     help="óbitos esperados mínimos p/ HSMR ser considerado estável")
    ap.add_argument("--min-internacoes-los", type=int, default=30,
                     help="internações mínimas do hospital p/ diagnóstico entrar no LOS")
    args = ap.parse_args()
    ano = args.ano
    env = load_env()

    parts = {k: [] for k in ("hsmr_nac", "hsmr_hosp", "los_nac", "los_hosp", "demanda")}
    for uf in UFS:
        r = _process_uf(uf, ano, args.workers)
        for k in parts:
            parts[k].append(r[k])

    municipios = pd.read_parquet(REFS / "municipios.parquet")
    # precisamos de município/UF do hospital: reaproveita mart_internacoes_hospital já publicado
    hosp_ref_path = MARTS / "mart_internacoes_hospital.parquet"
    hosp_ref = (pd.read_parquet(hosp_ref_path)[["cnes", "municipio_cod", "municipio_nome", "uf_sigla"]]
                .drop_duplicates("cnes")) if hosp_ref_path.exists() else pd.DataFrame(
        columns=["cnes", "municipio_cod", "municipio_nome", "uf_sigla"])

    # ============================================================
    # 1) HSMR — padronização indireta por (faixa etária x capítulo CID)
    # ============================================================
    hsmr_nac = pd.concat(parts["hsmr_nac"], ignore_index=True).groupby(
        ["faixa", "capitulo_cid"], as_index=False)[["internacoes", "obitos"]].sum()
    hsmr_nac["taxa_nacional"] = hsmr_nac["obitos"] / hsmr_nac["internacoes"]
    taxa_map = hsmr_nac.set_index(["faixa", "capitulo_cid"])["taxa_nacional"].to_dict()

    hsmr_hosp = pd.concat(parts["hsmr_hosp"], ignore_index=True)
    hsmr_hosp["taxa_nacional_estrato"] = hsmr_hosp.apply(
        lambda r: taxa_map.get((r["faixa"], r["capitulo_cid"]), 0.0), axis=1)
    hsmr_hosp["obitos_esperados_estrato"] = hsmr_hosp["internacoes"] * hsmr_hosp["taxa_nacional_estrato"]

    hsmr = hsmr_hosp.groupby("cnes", as_index=False).agg(
        internacoes=("internacoes", "sum"),
        obitos_observados=("obitos", "sum"),
        obitos_esperados=("obitos_esperados_estrato", "sum"),
    )
    hsmr["hsmr"] = (hsmr["obitos_observados"] / hsmr["obitos_esperados"]).round(3)
    hsmr["estavel"] = hsmr["obitos_esperados"] >= args.min_esperado
    hsmr["obitos_esperados"] = hsmr["obitos_esperados"].round(1)
    hsmr["ano"] = ano
    hsmr = hsmr.merge(hosp_ref, on="cnes", how="left")
    hsmr = hsmr[hsmr.internacoes >= 12].copy()
    hsmr = hsmr[["cnes", "municipio_cod", "municipio_nome", "uf_sigla", "ano",
                 "internacoes", "obitos_observados", "obitos_esperados", "hsmr", "estavel"]]

    # ============================================================
    # 2) LOS esperado — mediana nacional vs. mediana do hospital, por CID-3
    # ============================================================
    bincols = [f"bin{i}" for i in range(8)]
    los_nac = pd.concat(parts["los_nac"], ignore_index=True).groupby("cid3", as_index=False)[bincols].sum()
    los_nac["mediana_nacional_dias"] = los_nac[bincols].apply(lambda r: _mediana_aprox(list(r)), axis=1)
    mediana_nac_map = los_nac.set_index("cid3")["mediana_nacional_dias"].to_dict()

    los_hosp = pd.concat(parts["los_hosp"], ignore_index=True).groupby(
        ["cnes", "cid3"], as_index=False)[bincols].sum()
    los_hosp["internacoes"] = los_hosp[bincols].sum(axis=1)
    los_hosp = los_hosp[los_hosp.internacoes >= args.min_internacoes_los].copy()
    los_hosp["mediana_hospital_dias"] = los_hosp[bincols].apply(lambda r: _mediana_aprox(list(r)), axis=1)
    los_hosp["mediana_nacional_dias"] = los_hosp["cid3"].map(mediana_nac_map)
    los_hosp["capitulo_cid"] = los_hosp["cid3"].map(_capitulo)
    los_hosp["desvio_dias"] = (los_hosp["mediana_hospital_dias"] - los_hosp["mediana_nacional_dias"]).round(1)
    los_hosp["ano"] = ano
    los_hosp = los_hosp.merge(hosp_ref, on="cnes", how="left")
    los = los_hosp[["cnes", "municipio_cod", "municipio_nome", "uf_sigla", "ano", "cid3",
                    "capitulo_cid", "internacoes", "mediana_hospital_dias",
                    "mediana_nacional_dias", "desvio_dias"]]

    # ============================================================
    # 3) Demanda mensal por hospital (base para forecast)
    # ============================================================
    demanda = pd.concat(parts["demanda"], ignore_index=True).groupby(
        ["cnes", "ano_mes"], as_index=False)[["internacoes", "obitos", "valor_total"]].sum()
    demanda = demanda.merge(hosp_ref, on="cnes", how="left")
    demanda = demanda[["cnes", "municipio_cod", "municipio_nome", "uf_sigla",
                       "ano_mes", "internacoes", "obitos", "valor_total"]]

    MARTS.mkdir(exist_ok=True)
    hsmr.to_parquet(MARTS / "mart_hsmr_hospital.parquet", compression="zstd", index=False)
    los.to_parquet(MARTS / "mart_los_hospital.parquet", compression="zstd", index=False)
    demanda.to_parquet(MARTS / "mart_demanda_mensal_hospital.parquet", compression="zstd", index=False)
    print(f"[hospitalar] mart_hsmr: {len(hsmr):,} | mart_los: {len(los):,} | "
          f"mart_demanda: {len(demanda):,}", flush=True)

    if args.no_upload:
        return
    url, key = env["SUPABASE_URL"], chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}

    def up(table, df):
        recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
        for i in range(0, len(recs), 8000):
            body = json.dumps(recs[i:i+8000], default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
            for a in range(4):
                r = requests.post(f"{url.rstrip('/')}/rest/v1/{table}", headers=h, data=body, timeout=300)
                if r.status_code in (200, 201):
                    break
                if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                    raise RuntimeError(f"{table}: HTTP {r.status_code} {r.text[:200]}")
                time.sleep(3 * (a + 1))
        print(f"[supabase]   {table}: {len(recs):,} OK", flush=True)

    up("mart_hsmr_hospital", hsmr)
    up("mart_los_hospital", los)
    up("mart_demanda_mensal_hospital", demanda)
    print("[done] HSMR + LOS + demanda mensal concluído.", flush=True)


if __name__ == "__main__":
    main()
