"""
pipeline_qualidade_registro.py — confiabilidade do registro de óbito
=====================================================================

Percentual de óbitos por **causas mal definidas** (capítulo XVIII da CID-10,
R00–R99: "sintomas, sinais e achados anormais não classificados em outra
parte") por município, acumulado em 2022–2024.

É o indicador clássico de qualidade do registro: onde a proporção é alta, a
causa básica declarada no atestado não identifica a doença, e toda análise por
causa naquele município fica menos confiável — inclusive as deste projeto.

POR QUE ESTE ARQUIVO PASSOU A EXISTIR
-------------------------------------
`mart_qualidade_registro_municipio` era a última tabela publicada **sem
produtor no repositório**: entrou pelo Storage antes de existir pipeline de
publicação e ficou marcada `storage-legado`, a única origem fora do padrão.
Tabela publicada sem produtor é número que ninguém pode refazer — e o projeto
inteiro se apoia em poder refazer.

Não baixa nada: deriva de `mart_mortalidade_municipio`, que já traz óbitos por
município, ano, capítulo CID e sexo.

REPRODUÇÃO DO QUE JÁ ESTAVA PUBLICADO
-------------------------------------
Conferido antes de escrever: óbitos totais e mal definidas batem em **5.595 de
5.595 municípios**. O percentual divergia em 12 linhas, todas por convenção de
arredondamento — 1/32 = 3,125 vira 3,12 com o arredondamento bancário do pandas
e 3,13 com meio-para-cima. O produtor original usou meio-para-cima, e este
reproduz isso de propósito: a tabela já foi publicada, baixada e tem checksum;
mudar 12 valores para adotar outra convenção seria alterar dado publicado sem
ganho de correção — nenhuma das duas é mais certa que a outra.

Uso:
  .venv311/Scripts/python scripts/pipeline_qualidade_registro.py [--no-upload]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _publicacao import escrever_parquet  # noqa: E402
from _supabase_key import chave_escrita  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
PRODUTOR = "scripts/pipeline_qualidade_registro.py"

ANOS = [2022, 2023, 2024]
PERIODO = "2022-2024"
CAPITULO_MAL_DEFINIDAS = "XVIII"       # R00–R99

# Cortes do indicador. Regular é fechado nas duas pontas: um município com
# exatamente 10,00% é Regular, não Ruim — conferido contra a tabela publicada,
# onde o máximo de Regular é 10,00 e o mínimo de Ruim é 10,02.
CORTE_BOM = Decimal("5")
CORTE_REGULAR = Decimal("10")


def meio_para_cima(valor: float) -> float:
    """Arredonda a duas casas com meio-PARA-CIMA, não bancário.

    `round()` do Python e `.round()` do pandas usam meio-para-par: 3,125 vira
    3,12. A tabela publicada usa 3,13. São 12 linhas em 5.595, e a diferença
    existe para preservar o dado já publicado, não porque uma seja correta.
    """
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def classificar(pct: float) -> str:
    p = Decimal(str(pct))
    if p < CORTE_BOM:
        return "Bom"
    if p <= CORTE_REGULAR:
        return "Regular"
    return "Ruim"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for linha in f.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, _, v = linha.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})
    return env


def construir() -> pd.DataFrame:
    mort = pd.read_parquet(MARTS / "mart_mortalidade_municipio.parquet")
    mort = mort[mort.ano.isin(ANOS) & (mort.sexo == "TOTAL")]

    total = (mort[mort.capitulo_cid == "TOTAL"]
             .groupby("municipio_cod", as_index=False).obitos.sum()
             .rename(columns={"obitos": "obitos_total"}))
    mal = (mort[mort.capitulo_cid == CAPITULO_MAL_DEFINIDAS]
           .groupby("municipio_cod", as_index=False).obitos.sum()
           .rename(columns={"obitos": "obitos_mal_definidas"}))

    # Município sem NENHUM óbito mal definido no período é zero, não ausência —
    # e a distinção importa: `NaN` viraria buraco no indicador de um município
    # que, na verdade, registrou bem.
    df = total.merge(mal, on="municipio_cod", how="left")
    df["obitos_mal_definidas"] = df["obitos_mal_definidas"].fillna(0).astype(int)

    df["pct_mal_definidas"] = [
        meio_para_cima(100 * m / t) if t else 0.0
        for m, t in zip(df.obitos_mal_definidas, df.obitos_total, strict=True)
    ]
    df["classificacao"] = df.pct_mal_definidas.map(classificar)

    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")
    pop = pd.read_parquet(MARTS / "dim_populacao.parquet")
    pop = pop[pop.ano == max(ANOS)][["municipio_cod", "populacao"]]

    df = (df.merge(dim[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]],
                   on="municipio_cod", how="left")
            .merge(pop, on="municipio_cod", how="left"))
    df["uf_sigla"] = df["uf_sigla"].fillna("ND")
    df["periodo"] = PERIODO
    df["populacao"] = df["populacao"].astype("Int64")
    return df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "periodo",
               "obitos_total", "obitos_mal_definidas", "pct_mal_definidas",
               "classificacao", "populacao"]].sort_values("municipio_cod").reset_index(drop=True)


def conferir_contra_publicado(novo: pd.DataFrame) -> None:
    """Compara com o Parquet que já estava publicado, se ele existir.

    Não aborta em divergência de população — ela vem de `dim_populacao`, que é
    reconstruída — mas ABORTA se óbito ou classificação mudarem: isso seria
    alterar em silêncio um número que já foi baixado e citado.
    """
    antigo_path = MARTS / "mart_qualidade_registro_municipio.parquet"
    if not antigo_path.exists():
        print("[qualidade] sem versão anterior para conferir", flush=True)
        return
    antigo = pd.read_parquet(antigo_path)
    j = antigo.merge(novo, on="municipio_cod", suffixes=("_antigo", "_novo"), how="outer")
    if len(j) != len(antigo) or len(j) != len(novo):
        raise SystemExit(f"conjunto de municípios mudou: {len(antigo)} -> {len(novo)}")
    for col in ("obitos_total", "obitos_mal_definidas", "pct_mal_definidas", "classificacao"):
        difs = j[j[f"{col}_antigo"] != j[f"{col}_novo"]]
        if len(difs):
            print(difs[["municipio_cod", f"{col}_antigo", f"{col}_novo"]].head(10).to_string(),
                  flush=True)
            raise SystemExit(f"{col}: {len(difs)} divergências contra o publicado")
    print(f"[qualidade] reproduz o publicado: {len(novo):,} municípios idênticos", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    df = construir()
    conferir_contra_publicado(df)
    print("[qualidade] classificação: "
          + ", ".join(f"{k}={v}" for k, v in df.classificacao.value_counts().items()), flush=True)

    escrever_parquet(df, MARTS / "mart_qualidade_registro_municipio.parquet",
                     origem="pipeline", produtor=PRODUTOR)
    print(f"[qualidade] {len(df):,} linhas gravadas", flush=True)
    if args.no_upload:
        return

    env = load_env()
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        corpo = json.dumps(recs[i:i + 5000], allow_nan=False,
                           default=lambda o: o.item() if hasattr(o, "item") else o)
        r = requests.post(f"{url}/rest/v1/mart_qualidade_registro_municipio",
                          headers=h, data=corpo, timeout=300)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload: HTTP {r.status_code} {r.text[:200]}")
    print(f"[supabase]   mart_qualidade_registro_municipio: {len(recs):,} OK", flush=True)

    meta = [{"chave": "fonte_qualidade_registro",
             "valor": "SIM/DataSUS — % de óbitos por causas mal definidas (CID-10 capítulo XVIII, "
                      f"R00–R99) por município, {PERIODO}. Bom <5%, Regular 5–10%, Ruim >10%."},
            {"chave": "gerado_em", "valor": datetime.now().isoformat(timespec="seconds")}]
    requests.post(f"{url}/rest/v1/meta_dataset", headers=h, data=json.dumps(meta), timeout=60)
    print("[done] qualidade do registro concluído.", flush=True)


if __name__ == "__main__":
    main()
