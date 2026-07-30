"""
pipeline_ans_beneficiarios.py — Cobertura de saude suplementar por municipio (ANS)
===================================================================================

Baixa o cadastro consolidado de beneficiarios de planos de saude (ANS, dados
abertos, sem autenticacao) e calcula, por municipio e ano, o percentual da
populacao coberta por plano MEDICO-HOSPITALAR (exclui plano puramente
odontologico, que nao substitui internacao/SUS).

Motivacao: o preprint da cobertura da APS e os marts de ICSAP ja declaram a
limitacao de que "municipios com maior cobertura de saude suplementar podem
ter ICSAP subestimado, por razoes nao relacionadas a atencao primaria" — mas
nunca testamos isso, so declaramos. Este pipeline traz o dado que falta para
testar a limitacao em vez de so mencion*a-la.

Fonte: FTP publico da ANS (Dados Abertos), sem login:
  ftp://ftp.dadosabertos.ans.gov.br/FTP/PDA/informacoes_consolidadas_de_beneficiarios-024/
Um zip por UF por competencia (mes-ano). Usamos a competencia de DEZEMBRO de
cada ano (foto de fim de ano, coerente com o uso de populacao/beneficiarios
como variavel de estoque, nao fluxo).

NAO usamos o dataset "taxa_de_cobertura_de_planos_de_saude-047" (parecia
pronto, mas so tem o periodo corrente e as taxas vieram zeradas mesmo para
Sao Paulo na amostra verificada — problema de qualidade/atualizacao daquele
recorte especifico). Preferimos a granularidade menor (beneficiario x
operadora x municipio) e agregar nos mesmos, que e mais lento mas confiavel.

Uso:
  .venv311/Scripts/python scripts/pipeline_ans_beneficiarios.py --anos 2021 2022 2023 2024
"""
from __future__ import annotations

import argparse
import io
import json
import os
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests
from ftplib import FTP

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "ANS" / "beneficiarios_ckpt"
FTP_HOST = "ftp.dadosabertos.ans.gov.br"
FTP_DIR = "FTP/PDA/informacoes_consolidadas_de_beneficiarios-024"
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
       "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO", "XX"]

COLS = ["CD_MUNICIPIO", "COBERTURA_ASSIST_PLAN", "QT_BENEFICIARIO_ATIVO"]


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


def _baixar_uf(uf: str, competencia: str) -> pd.DataFrame | None:
    """Um zip de UF/competencia -> total de beneficiarios medico-hospitalar por municipio."""
    ck = CKPT / f"benef_{uf}_{competencia}.parquet"
    if ck.exists():
        return pd.read_parquet(ck)

    ano, mes = competencia[:4], competencia[4:]
    nome_zip = f"pda-024-icb-{uf}-{ano}_{mes}.zip"
    buf = io.BytesIO()
    for tentativa in range(4):
        try:
            ftp = FTP(FTP_HOST, timeout=60)
            ftp.login()
            ftp.cwd(f"{FTP_DIR}/{competencia}")
            ftp.retrbinary(f"RETR {nome_zip}", buf.write)
            ftp.quit()
            break
        except Exception as e:
            if tentativa == 3:
                print(f"  [{uf}] FALHOU apos 4 tentativas: {e}", flush=True)
                return None
            time.sleep(3 * (tentativa + 1))
            buf = io.BytesIO()

    if buf.tell() == 0:
        print(f"  [{uf}] arquivo vazio/ausente para {competencia}", flush=True)
        return None

    with zipfile.ZipFile(buf) as z:
        nome_csv = z.namelist()[0]
        with z.open(nome_csv) as f:
            df = pd.read_csv(f, sep=";", usecols=COLS, dtype={"CD_MUNICIPIO": str},
                              encoding="utf-8", low_memory=False)

    df = df[df.COBERTURA_ASSIST_PLAN == "Médico-hospitalar"]
    out = df.groupby("CD_MUNICIPIO", as_index=False)["QT_BENEFICIARIO_ATIVO"].sum()
    out = out.rename(columns={"CD_MUNICIPIO": "municipio_cod_ibge7",
                               "QT_BENEFICIARIO_ATIVO": "beneficiarios_medico_hospitalar"})
    CKPT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(ck, compression="zstd", index=False)
    print(f"  [{uf}] {competencia}: {int(out.beneficiarios_medico_hospitalar.sum()):,} beneficiarios "
          f"medico-hospitalar, {len(out):,} municipios", flush=True)
    return out


def processar_ano(ano: int) -> pd.DataFrame:
    competencia = f"{ano}12"
    print(f"=== ANO {ano} (competencia {competencia}) ===", flush=True)
    partes = [df for uf in UFS if (df := _baixar_uf(uf, competencia)) is not None]
    benef = pd.concat(partes, ignore_index=True)

    # CD_MUNICIPIO da ANS tem 6 digitos (mesmo padrao IBGE usado no resto do projeto)
    municipios = pd.read_parquet(REFS / "municipios.parquet")
    pop = pd.read_parquet(next(REFS.glob("populacao_*.parquet")))
    pop = pop[pop.ano == ano][["municipio_cod", "populacao"]]

    benef["municipio_cod"] = benef["municipio_cod_ibge7"].astype(str)
    df = (municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]
          .merge(benef[["municipio_cod", "beneficiarios_medico_hospitalar"]], on="municipio_cod", how="left")
          .merge(pop, on="municipio_cod", how="left"))
    df["beneficiarios_medico_hospitalar"] = df["beneficiarios_medico_hospitalar"].fillna(0).astype("Int64")
    df["pct_saude_suplementar"] = (df["beneficiarios_medico_hospitalar"] / df["populacao"] * 100).round(2)
    df["populacao"] = df["populacao"].round().astype("Int64")
    df["ano"] = ano
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", type=int, nargs="+", default=[2021, 2022, 2023, 2024])
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    partes = [processar_ano(ano) for ano in args.anos]
    out = pd.concat(partes, ignore_index=True)
    out = out[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano",
               "populacao", "beneficiarios_medico_hospitalar", "pct_saude_suplementar"]]

    MARTS.mkdir(exist_ok=True)
    out.to_parquet(MARTS / "mart_saude_suplementar_municipio.parquet", compression="zstd", index=False)
    print(f"\n[mart] mart_saude_suplementar_municipio: {len(out):,} linhas "
          f"({out.municipio_cod.nunique():,} municipios x {out.ano.nunique()} anos)")
    print(f"  pct_saude_suplementar mediano: {out.pct_saude_suplementar.median():.1f}%")

    if args.no_upload:
        return
    env = load_env()
    url, key = env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}

    recs = out.astype(object).where(pd.notna(out), None).to_dict("records")
    for i in range(0, len(recs), 8000):
        body = json.dumps(recs[i:i + 8000], default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
        for a in range(4):
            r = requests.post(f"{url.rstrip('/')}/rest/v1/mart_saude_suplementar_municipio",
                               headers=h, data=body, timeout=300)
            if r.status_code in (200, 201):
                break
            if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"mart_saude_suplementar_municipio: HTTP {r.status_code} {r.text[:200]}")
            time.sleep(3 * (a + 1))
    print(f"[supabase] mart_saude_suplementar_municipio: {len(recs):,} OK")

    meta = [{"chave": "fonte_saude_suplementar",
             "valor": f"ANS Dados Abertos, informacoes_consolidadas_de_beneficiarios (competencia dez/ano), "
                      f"filtrado a COBERTURA_ASSIST_PLAN=Medico-hospitalar. Anos: {args.anos}."}]
    requests.post(f"{url.rstrip('/')}/rest/v1/meta_dataset", headers=h, data=json.dumps(meta), timeout=60)
    print("[done] saude suplementar concluido.")


if __name__ == "__main__":
    main()
