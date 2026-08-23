"""
pipeline_cobertura_aps.py — Cobertura potencial da Atenção Primária (e-Gestor AB)
==================================================================================

Fonte: API pública do relatório de Cobertura da APS do Ministério da Saúde
(https://relatorioaps.saude.gov.br/cobertura/aps), servida por
https://relatorioaps-prd.saude.gov.br/cobertura/aps — JSON, sem autenticação,
descoberta via engenharia reversa do bundle Angular do front-end público
(rota `qn_apiUrl + "/cobertura/aps"`, parâmetros construídos pelo próprio
formulário do relatório). Não é um endpoint formalmente documentado como API
pública, mas é o que abastece o relatório público oficial — mesmo princípio
de uso já aplicado a outras fontes DataSUS deste projeto.

Metodologia oficial do indicador (nota técnica do Ministério, linkada no
relatório): cobertura potencial = capacidade de atendimento estimada das
equipes credenciadas (ESF, EAP, eSFR, eCR, EAPP) dividida pela população do
município. Pode superar 100% em municípios pequenos com capacidade instalada
maior que a população local (visto em Acrelândia/AC, 149,77% em jan/2024) —
não é erro, é a definição do indicador; documentado como limitação.

Uma chamada por ano civil retorna todos os ~5.570 municípios × 12 meses;
checkpoint por ano (resumível). Cobertura: jan/2021 até a competência mais
recente publicada.

Uso:
  .venv311/Scripts/python scripts/pipeline_cobertura_aps.py --ano-inicio 2021 --ano-fim 2026
"""
from __future__ import annotations

import sys
import argparse
import json
import os
import time
from datetime import date
from pathlib import Path

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
CKPT = ROOT / "data" / "raw" / "cobertura_aps" / "ckpt"
API = "https://relatorioaps-prd.saude.gov.br/cobertura/aps"

COLMAP = {
    "coMunicipioIbge": "municipio_cod",
    "qtPopulacao": "populacao",
    "qtEsf": "qt_esf",
    "qtEap20": "qt_eap20",
    "qtEap30": "qt_eap30",
    "qtEsfr": "qt_esfr",
    "qtEcr": "qt_ecr",
    "qtEapp20": "qt_eapp20",
    "qtEapp30": "qt_eapp30",
    "qtCapacidadeEquipe": "capacidade_equipe",
    "qtCobertura": "cobertura_pct",
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


def _fetch_ano(ano: int) -> pd.DataFrame | None:
    """Um ano civil (jan-dez) -> DataFrame bruto, ou None se a API não tiver nada."""
    params = {
        "unidadeGeografica": "MUNICIPIO",
        "nuCompInicio": f"{ano}01",
        "nuCompFim": f"{ano}12",
    }
    for attempt in range(4):
        try:
            r = requests.get(API, params=params, timeout=180)
            if r.status_code == 200:
                data = r.json()
                return pd.DataFrame(data) if data else None
            if r.status_code in (400, 404):
                return None
        except requests.RequestException:
            pass
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"falha ao buscar competencia {ano}: sem resposta valida apos 4 tentativas")


def _fetch_ano_ckpt(ano: int) -> pd.DataFrame | None:
    CKPT.mkdir(parents=True, exist_ok=True)
    ck = CKPT / f"cobertura_{ano}.parquet"
    if ck.exists():
        return pd.read_parquet(ck)
    df = _fetch_ano(ano)
    if df is None or df.empty:
        return None
    df.to_parquet(ck, compression="zstd", index=False)
    print(f"[cobertura_aps] {ano}: {len(df):,} linhas | "
          f"{df['coMunicipioIbge'].nunique():,} municipios | "
          f"competencias {sorted(df['nuComp'].unique())[0]}-{sorted(df['nuComp'].unique())[-1]}", flush=True)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano-inicio", type=int, default=2021)
    ap.add_argument("--ano-fim", type=int, default=date.today().year)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    env = load_env()

    municipios = pd.read_parquet(REFS / "municipios.parquet")
    mref = municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]

    partes = []
    for ano in range(args.ano_inicio, args.ano_fim + 1):
        df = _fetch_ano_ckpt(ano)
        if df is not None:
            partes.append(df)

    if not partes:
        raise SystemExit("nenhum dado retornado pela API para o intervalo pedido")

    bruto = pd.concat(partes, ignore_index=True)
    bruto = bruto.rename(columns=COLMAP)
    bruto["mes_competencia"] = pd.to_datetime(bruto["nuComp"], format="%m/%Y").dt.strftime("%Y-%m-01")
    bruto["ano"] = pd.to_datetime(bruto["mes_competencia"]).dt.year.astype("int16")
    bruto["mes"] = pd.to_datetime(bruto["mes_competencia"]).dt.month.astype("int16")
    bruto["municipio_cod"] = bruto["municipio_cod"].astype(str).str[:6]

    numericas = ["populacao", "qt_esf", "qt_eap20", "qt_eap30", "qt_esfr", "qt_ecr",
                 "qt_eapp20", "qt_eapp30", "capacidade_equipe", "cobertura_pct"]
    for c in numericas:
        bruto[c] = pd.to_numeric(bruto[c], errors="coerce")

    cobertura = bruto[["municipio_cod", "ano", "mes", "mes_competencia", *numericas]].merge(
        mref, on="municipio_cod", how="left")
    cobertura["uf_sigla"] = cobertura["uf_sigla"].fillna("ND")
    cobertura["cobertura_pct"] = cobertura["cobertura_pct"].round(2)
    cobertura = cobertura.drop_duplicates(["municipio_cod", "mes_competencia"])
    cobertura = cobertura[["municipio_cod", "municipio_nome", "uf_sigla", "regiao",
                           "ano", "mes", "mes_competencia", "populacao",
                           "qt_esf", "qt_eap20", "qt_eap30", "qt_esfr", "qt_ecr",
                           "qt_eapp20", "qt_eapp30", "capacidade_equipe", "cobertura_pct"]]

    MARTS.mkdir(exist_ok=True)
    escrever_parquet(
        cobertura, MARTS / "mart_cobertura_aps_municipio.parquet",
        origem="pipeline", produtor="scripts/pipeline_cobertura_aps.py")
    print(f"[cobertura_aps] mart final: {len(cobertura):,} linhas | "
          f"{cobertura.municipio_cod.nunique():,} municipios | "
          f"{cobertura.mes_competencia.nunique():,} competencias", flush=True)

    if args.no_upload:
        return
    url, key = env["SUPABASE_URL"], chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}

    def up(table: str, df: pd.DataFrame):
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

    up("mart_cobertura_aps_municipio", cobertura)
    print("[done] cobertura APS concluido.", flush=True)


if __name__ == "__main__":
    main()
