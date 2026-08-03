"""
pipeline_cnes.py — Estabelecimentos de saude por municipio (CNES)

Traz a camada de OFERTA que falta no projeto: ate agora so contamos eventos
(obitos, casos, internacoes), nunca capacidade instalada. Sem isso nao da para
responder "este municipio tem estrutura para atender sua populacao?".

Fonte: API publica de dados abertos do Ministerio da Saude (cadastro CORRENTE,
sem serie historica, sem autenticacao):
  https://apidadosabertos.saude.gov.br/cnes/estabelecimentos

Nao usamos o FTP do DataSUS (serie historica 2005-hoje + leitos, grupo LT)
nesta primeira fase — a API cobre o indicador de vitrine (estabelecimentos
hospitalares por 10 mil hab.) com uma fracao do esforco. Leitos ficam para uma
fase 2, se fizer sentido.

Armadilhas verificadas contra a API ao vivo (nao levantam excecao, so geram
numero errado se ignoradas):

  1. `codigo_municipio` ja vem no padrao DataSUS de 6 digitos (nao IBGE de 7) —
     mesmo assim canonizamos defensivamente via to6().
  2. `descricao_esfera_administrativa` NAO significa "publico" — indica qual
     ente GERE o estabelecimento (contratualizacao), nao a propriedade. Em
     Alta Floresta d'Oeste/RO, 67 estabelecimentos vem como "MUNICIPAL", mas
     so 32 sao publicos pela natureza juridica real (clinicas LTDA e
     consultorios de pessoa fisica inflam a leitura ingenua). Propriedade
     correta = primeiro digito de `descricao_natureza_juridica_estabelecimento`
     (tabela CONCLA: 1=publico, 2=privado lucrativo, 3=sem fins lucrativos,
     4=pessoa fisica, 5=internacional).
  3. `codigo_motivo_desabilitacao_estabelecimento` nao-nulo = estabelecimento
     DESABILITADO. Contar sem filtrar infla a oferta real com cadastros
     mortos — a amostra verificada tinha ~45% de registros desabilitados
     misturados aos ativos, sem nenhum campo de status obvio destacado.
  4. `limit` e aceito mas tetado em 20 pelo servidor (pedir 1000 devolve 20);
     `offset` e a unica forma de paginar.

Uso:
  .venv311/Scripts/python scripts/pipeline_cnes.py --all
  .venv311/Scripts/python scripts/pipeline_cnes.py --estados SP RJ --dry-run

FASE 2, NAO IMPLEMENTADA — leitos (grupo LT, exige FTP do DataSUS, a API nao
tem esse endpoint). Se for feita, a agregacao por municipio deve:
  - preferir LT (granular por tipo de leito) e usar os campos de leito da ST
    (qt_leitos_sus, qt_leitos_nao_sus) so como fallback quando LT faltar;
  - agrupar leitos por tipo (cirurgico, clinico, obstetrico, pediatrico,
    complementar, reabilitacao) e por vinculo SUS/nao-SUS de cada tipo;
  - o indicador de vitrine correto e leitos SUS por mil habitantes, nao
    estabelecimentos — capacidade de internacao de verdade e leito, nao
    contagem de unidade.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "CNES" / "estabelecimentos_ckpt"

BASE_URL = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos"
LIMITE_MAX = 20  # teto real do servidor, medido: limit=1000 devolve 20
UA = {"User-Agent": "saudeemdado-pipeline/1.0 (+https://saudeemdado.com)"}

UFS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

# Tipos de unidade com perfil de internacao (tabela de dominio CNES).
TIPOS_HOSPITALARES = {5, 7, 15, 20, 21, 61, 62, 67, 68, 69, 70, 71, 72, 73}

NATUREZA = {
    "1": "publico", "2": "privado_lucrativo", "3": "sem_fins_lucrativos",
    "4": "pessoa_fisica", "5": "internacional",
}


def to6(codigo) -> str:
    """Canoniza codigo de municipio para 6 digitos (padrao DataSUS)."""
    s = str(codigo).strip()
    if len(s) == 7:
        return s[:6]
    if len(s) == 5:
        return s.zfill(6)
    return s


def natureza(est: dict) -> str:
    cod = str(est.get("descricao_natureza_juridica_estabelecimento") or "").strip()
    return NATUREZA.get(cod[:1], "desconhecido") if cod else "desconhecido"


def eh_hospitalar(est: dict) -> bool:
    if est.get("estabelecimento_possui_atendimento_hospitalar") in (1, "1", True):
        return True
    return est.get("codigo_tipo_unidade") in TIPOS_HOSPITALARES


def eh_ativo(est: dict) -> bool:
    """Desabilitado = tem motivo de desabilitacao preenchido. Nao ha campo de status."""
    return not est.get("codigo_motivo_desabilitacao_estabelecimento")


def _get(params: dict, tentativas: int = 4, timeout: int = 40) -> list[dict]:
    for i in range(tentativas):
        try:
            r = requests.get(BASE_URL, params=params, headers=UA, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 + 2 * i)
                continue
            r.raise_for_status()
            return r.json().get("estabelecimentos", [])
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(1.5 ** i)
    return []


def baixar_uf(codigo_uf: str, pausa: float = 0.15) -> pd.DataFrame:
    """Pagina todos os estabelecimentos de uma UF. Checkpoint resumivel."""
    uf_sigla = UFS[codigo_uf]
    ck = CKPT / f"cnes_{uf_sigla}.parquet"
    if ck.exists():
        return pd.read_parquet(ck)

    linhas = []
    offset = 0
    while True:
        lote = _get({"codigo_uf": codigo_uf, "limit": LIMITE_MAX, "offset": offset})
        if not lote:
            break
        for e in lote:
            linhas.append({
                "cnes": str(e.get("codigo_cnes") or "").strip(),
                "municipio_cod": to6(e.get("codigo_municipio")),
                "natureza": natureza(e),
                "hospitalar": eh_hospitalar(e),
                "ativo": eh_ativo(e),
            })
        if len(lote) < LIMITE_MAX:
            break
        offset += LIMITE_MAX
        time.sleep(pausa)

    df = pd.DataFrame(linhas)
    CKPT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ck, compression="zstd", index=False)
    print(f"  [{uf_sigla}] {len(df):,} estabelecimentos "
          f"({df.ativo.sum():,} ativos, {(df.ativo & df.hospitalar).sum():,} hospitalares ativos)",
          flush=True)
    return df


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--estados", nargs="+", default=None,
                    help="Siglas de UF (ex: SP RJ). Default: todas.")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    if args.estados:
        alvo = {cod: sig for cod, sig in UFS.items() if sig in {e.upper() for e in args.estados}}
    else:
        alvo = UFS

    partes = [baixar_uf(cod) for cod in alvo]
    bruto = pd.concat(partes, ignore_index=True)
    ativo = bruto[bruto.ativo].copy()

    print(f"\n[bruto] {len(bruto):,} estabelecimentos ({len(ativo):,} ativos, "
          f"{len(bruto) - len(ativo):,} desabilitados)")

    agg = (ativo.groupby("municipio_cod", as_index=False)
           .agg(estabelecimentos_total=("cnes", "count"),
                estabelecimentos_hospitalares=("hospitalar", "sum")))
    nat = (ativo.pivot_table(index="municipio_cod", columns="natureza", values="cnes",
                              aggfunc="count", fill_value=0)
           .reset_index())
    for col in ["publico", "privado_lucrativo", "sem_fins_lucrativos", "pessoa_fisica", "internacional"]:
        if col not in nat.columns:
            nat[col] = 0
    agg = agg.merge(nat[["municipio_cod", "publico", "privado_lucrativo",
                          "sem_fins_lucrativos", "pessoa_fisica", "internacional"]],
                     on="municipio_cod", how="left")

    municipios = pd.read_parquet(REFS / "municipios.parquet")
    pop = pd.read_parquet(next(REFS.glob("populacao_*.parquet")))
    ano_pop = int(pop["ano"].max())
    pop = pop[pop.ano == ano_pop][["municipio_cod", "populacao"]]

    out = (municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]
           .merge(agg, on="municipio_cod", how="left")
           .merge(pop, on="municipio_cod", how="left"))
    for col in ["estabelecimentos_total", "estabelecimentos_hospitalares", "publico",
                "privado_lucrativo", "sem_fins_lucrativos", "pessoa_fisica", "internacional"]:
        out[col] = out[col].fillna(0).astype(int)

    out["estab_por_10k"] = (out.estabelecimentos_total / out.populacao * 10_000).round(2)
    out["estab_hosp_por_10k"] = (out.estabelecimentos_hospitalares / out.populacao * 10_000).round(2)
    out["pct_publico"] = (out.publico / out.estabelecimentos_total.replace(0, np.nan) * 100).round(1)
    out["ano_referencia"] = ano_pop
    out["populacao"] = out["populacao"].round().astype("Int64")

    print(f"\n[mart] municipios cobertos: {len(out):,}")
    print(f"  sem nenhum estabelecimento ativo: {(out.estabelecimentos_total == 0).sum():,}")
    print(f"  mediana estab_hosp_por_10k: {out.estab_hosp_por_10k.median():.2f}")

    MARTS.mkdir(exist_ok=True)
    out.to_parquet(MARTS / "mart_cnes_municipio.parquet", compression="zstd", index=False)
    print(f"[mart] mart_cnes_municipio.parquet salvo ({len(out):,} municipios)")

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
            r = requests.post(f"{url.rstrip('/')}/rest/v1/mart_cnes_municipio",
                               headers=h, data=body, timeout=300)
            if r.status_code in (200, 201):
                break
            if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"mart_cnes_municipio: HTTP {r.status_code} {r.text[:200]}")
            time.sleep(3 * (a + 1))
    print(f"[supabase] mart_cnes_municipio: {len(recs):,} OK")

    meta = [{"chave": "fonte_cnes",
             "valor": "API de dados abertos do Ministerio da Saude (apidadosabertos.saude.gov.br/cnes), "
                      "cadastro corrente, sem autenticacao. Estabelecimentos ativos "
                      "(codigo_motivo_desabilitacao_estabelecimento nulo). Natureza da propriedade via "
                      "primeiro digito de descricao_natureza_juridica_estabelecimento (CONCLA), nao via "
                      "descricao_esfera_administrativa (esfera de gestao, nao propriedade)."}]
    requests.post(f"{url.rstrip('/')}/rest/v1/meta_dataset", headers=h, data=json.dumps(meta), timeout=60)
    print("[done] CNES concluido.")


if __name__ == "__main__":
    main()
