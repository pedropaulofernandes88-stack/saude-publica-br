"""
pipeline_cnes_leitos.py — Leitos hospitalares por municipio (CNES grupo LT)

Complementa scripts/pipeline_cnes.py (que traz estabelecimentos via API e nao
tem leitos: aquele endpoint nao existe na API de dados abertos). Leito e a
medida de capacidade de internacao que realmente importa -- contar
estabelecimentos trata um hospital de 800 leitos e um posto pequeno como
iguais.

Fonte: FTP publico do DataSUS, grupo LT.
  ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/LT/
Nome do arquivo: LT{UF}{AA}{MM}.dbc -- ex.: LTSP2412.dbc = Sao Paulo, dez/2024.

RECORTE: dezembro de cada ano (2015-2024). O CNES e um CADASTRO fotografado
mensalmente, nao um fluxo de eventos -- somar competencias multiplicaria a
capacidade. Um snapshot anual e a agregacao correta, e dezembro alinha com o
denominador populacional anual do IBGE.

CLASSIFICACAO DE UTI -- por que nao usar faixa de codigo:
A tabela oficial de dominios (SCNES_DOMINIOS.ZIP, aba "LEITOS") mostra que os
codigos de UTI vao de 74 a 86, MAS o codigo 84 no meio da faixa e
"ACOLHIMENTO NOTURNO", que nao e UTI. Usar `74 <= cod <= 86` contaria leito de
acolhimento como terapia intensiva, silenciosamente. Por isso a lista de
codigos e explicita, nao um intervalo.

Uso:
  .venv311/Scripts/python scripts/pipeline_cnes_leitos.py --anos 2015 2016 ... 2024
  .venv311/Scripts/python scripts/pipeline_cnes_leitos.py --todos-os-anos
"""
from __future__ import annotations

import sys
import argparse
import json
import os
import time
from collections import defaultdict
from ftplib import FTP
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from _supabase_key import chave_escrita

# A linhagem viaja com os BYTES: `escrever_parquet` grava no proprio
# Parquet quem o produziu. Sem isso, um arquivo que veio do Postgres e um
# que veio do pipeline sao indistinguiveis, e o manifesto afirma o que
# ninguem verificou.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _publicacao import escrever_parquet  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "CNES" / "leitos_ckpt"
TMP = ROOT / "data" / "raw" / "CNES" / "_tmp"

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/CNES/200508_/Dados/LT"
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
       "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]

# Tabela oficial de dominios do CNES (aba "TIPOS DE LEITOS")
TIPO_LEITO = {
    "1": "cirurgico", "2": "clinico", "3": "complementar", "4": "obstetrico",
    "5": "pediatrico", "6": "outras_especialidades", "7": "hospital_dia",
}

# Codigos de UTI conforme a aba "LEITOS" da tabela oficial. Lista explicita e
# NAO intervalo: o codigo 84 (ACOLHIMENTO NOTURNO) fica no meio da faixa e nao
# e UTI. Ver docstring.
CODIGOS_UTI = {
    "74", "75", "76",  # UTI adulto tipo I, II, III
    "77", "78", "79",  # UTI pediatrica tipo I, II, III
    "80", "81", "82",  # UTI neonatal tipo I, II, III
    "83",              # UTI de queimados
    "85", "86",        # UTI coronariana (UCO) tipo II e III
}


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


def _baixar_uf_ano(uf: str, ano: int) -> pd.DataFrame | None:
    """Um arquivo LT (UF x dezembro/ano) agregado por municipio. Checkpoint resumivel."""
    import datasus_dbc
    import dbfread

    ck = CKPT / f"leitos_{uf}_{ano}.parquet"
    if ck.exists():
        return pd.read_parquet(ck)

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
            if "550" in str(e):  # arquivo inexistente para essa competencia
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

    # (municipio) -> acumuladores. CNES e cadastro: agregamos DENTRO da
    # competencia, nunca somando competencias diferentes.
    agg: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in registros:
        mun = str(r.get("CODUFMUN") or "").strip()
        if not mun:
            continue
        exist = int(r.get("QT_EXIST") or 0)
        sus = int(r.get("QT_SUS") or 0)
        nsus = int(r.get("QT_NSUS") or 0)
        a = agg[mun]
        a["leitos_total"] += exist
        a["leitos_sus"] += sus
        a["leitos_nao_sus"] += nsus
        tipo = TIPO_LEITO.get(str(r.get("TP_LEITO") or "").strip())
        if tipo:
            a[f"leitos_{tipo}"] += exist
        if str(r.get("CODLEITO") or "").strip() in CODIGOS_UTI:
            a["leitos_uti"] += exist
            a["leitos_uti_sus"] += sus

    linhas = [{"municipio_cod": m, "ano": ano, **dict(v)} for m, v in agg.items()]
    df = pd.DataFrame(linhas)
    CKPT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ck, compression="zstd", index=False)
    print(f"  [{uf} {ano}] {len(df):,} municipios, {int(df.get('leitos_total', pd.Series([0])).sum()):,} leitos "
          f"({int(df.get('leitos_uti', pd.Series([0])).sum()):,} UTI)", flush=True)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", type=int, nargs="+", default=None)
    ap.add_argument("--todos-os-anos", action="store_true")
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    anos = args.anos or (list(range(2015, 2025)) if args.todos_os_anos else [2024])

    partes = []
    for ano in anos:
        print(f"=== ANO {ano} (competencia {ano}12) ===", flush=True)
        for uf in UFS:
            df = _baixar_uf_ano(uf, ano)
            if df is not None and len(df):
                partes.append(df)

    bruto = pd.concat(partes, ignore_index=True)
    colunas_num = [c for c in bruto.columns if c.startswith("leitos_")]
    bruto[colunas_num] = bruto[colunas_num].fillna(0).astype(int)

    # Um municipio pode aparecer em mais de um arquivo do MESMO ano? Nao deveria
    # (o arquivo e por UF), mas agregamos por seguranca -- sempre dentro do ano.
    agg = bruto.groupby(["municipio_cod", "ano"], as_index=False)[colunas_num].sum()

    municipios = pd.read_parquet(REFS / "municipios.parquet")[
        ["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]
    pop = pd.read_parquet(next(REFS.glob("populacao_*.parquet")))[["municipio_cod", "ano", "populacao"]]

    # Grade completa municipio x ano: municipio sem leito nenhum precisa aparecer
    # com zero, nao sumir -- e exatamente o "vazio assistencial" que interessa.
    grade = municipios.merge(pd.DataFrame({"ano": anos}), how="cross")
    out = (grade.merge(agg, on=["municipio_cod", "ano"], how="left")
                .merge(pop, on=["municipio_cod", "ano"], how="left"))
    for c in colunas_num:
        out[c] = out[c].fillna(0).astype(int)

    out["leitos_por_mil"] = (out.leitos_total / out.populacao * 1_000).round(2)
    out["leitos_sus_por_mil"] = (out.leitos_sus / out.populacao * 1_000).round(2)
    out["leitos_uti_por_100k"] = (out.get("leitos_uti", 0) / out.populacao * 100_000).round(1)
    out["pct_leitos_sus"] = (out.leitos_sus / out.leitos_total.replace(0, np.nan) * 100).round(1)
    out["populacao"] = out["populacao"].round().astype("Int64")

    ultimo = out[out.ano == max(anos)]
    print(f"\n[mart] {len(out):,} linhas municipio-ano ({out.municipio_cod.nunique():,} municipios x {len(anos)} anos)")
    print(f"  {max(anos)}: {int(ultimo.leitos_total.sum()):,} leitos totais, "
          f"{int(ultimo.leitos_sus.sum()):,} SUS, {int(ultimo.get('leitos_uti', pd.Series([0])).sum()):,} UTI")
    print(f"  municipios com ZERO leitos em {max(anos)}: {(ultimo.leitos_total == 0).sum():,} "
          f"({(ultimo.leitos_total == 0).mean()*100:.1f}%)")
    print(f"  mediana leitos_sus_por_mil: {ultimo.leitos_sus_por_mil.median():.2f}")

    MARTS.mkdir(exist_ok=True)
    escrever_parquet(
        out, MARTS / "mart_leitos_municipio.parquet",
        origem="pipeline", produtor="scripts/pipeline_cnes_leitos.py")

    if args.no_upload:
        return
    env = load_env()
    url, key = env["SUPABASE_URL"], chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = out.astype(object).where(pd.notna(out), None).to_dict("records")
    for i in range(0, len(recs), 8000):
        body = json.dumps(recs[i:i + 8000], default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
        for a in range(4):
            r = requests.post(f"{url.rstrip('/')}/rest/v1/mart_leitos_municipio", headers=h, data=body, timeout=300)
            if r.status_code in (200, 201):
                break
            if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"mart_leitos_municipio: HTTP {r.status_code} {r.text[:200]}")
            time.sleep(3 * (a + 1))
    print(f"[supabase] mart_leitos_municipio: {len(recs):,} OK")

    meta = [{"chave": "fonte_leitos",
             "valor": f"CNES grupo LT (FTP DataSUS), competencia de dezembro de cada ano {min(anos)}-{max(anos)}. "
                      "Cadastro fotografado mensalmente -- snapshot anual, nunca soma de competencias. "
                      "UTI por lista explicita de codigos da tabela oficial de dominios (o codigo 84, "
                      "no meio da faixa de UTI, e acolhimento noturno e fica de fora)."}]
    requests.post(f"{url.rstrip('/')}/rest/v1/meta_dataset", headers=h, data=json.dumps(meta), timeout=60)
    print("[done] leitos concluido.")


if __name__ == "__main__":
    main()
