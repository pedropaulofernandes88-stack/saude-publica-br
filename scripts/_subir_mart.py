"""
_subir_mart.py — Publica um parquet local na tabela correspondente do Supabase.

Contraparte de _baixar_mart_completo.py. Os scripts de análise
(analise_cobertura_icsap.py, analise_leitos_icsap.py, analise_equidade_aps.py…)
gravam só o parquet local — não têm rotina de upload própria, porque nasceram
como análise pontual. Quando o insumo é reprocessado, o parquet local fica
correto e a tabela publicada fica velha. Este script fecha essa lacuna sem
espalhar mais um bloco de upload por script.

Upsert com merge-duplicates (mesma convenção dos pipelines): linhas com a mesma
PK são atualizadas, linhas novas são inseridas. NÃO apaga o que existe e não
está no parquet — se a intenção for substituir a tabela inteira, use --truncar.

Uso:
  .venv311/Scripts/python scripts/_subir_mart.py mart_cobertura_icsap_municipio
  .venv311/Scripts/python scripts/_subir_mart.py mart_leitos_icsap_municipio --truncar
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests
from _supabase_key import chave_escrita

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
#: Linhas por requisição. 8.000 serve para a maioria das marts, mas NÃO é
#: seguro para tabela grande: o upsert precisa consultar a PK linha a linha, e
#: em `mart_mortalidade_municipio` (1,3 milhão de linhas) um lote desse tamanho
#: estourou o `statement_timeout` do Postgres — HTTP 500 com código 57014 depois
#: de quase dois minutos por lote. `--lote` existe para esse caso.
LOTE = 8_000


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _jd(o):
    """Serializa o que o json não conhece.

    Data/hora vem ANTES do `.item()`: `pd.Timestamp` tem `.item()`, e ele
    devolve um objeto que o json também não serializa, então o `default`
    reentrava para sempre e o erro saía como "Circular reference detected" —
    mensagem que não aponta para data nenhuma. Foi assim que
    `mart_excesso_uf_mes` e `mart_mortalidade_uf_mes` falharam ao subir.
    """
    if isinstance(o, datetime | date):
        return o.isoformat()
    if hasattr(o, "isoformat"):          # pd.Timestamp, np.datetime64 via pandas
        return o.isoformat()
    return o.item() if hasattr(o, "item") else o


def subir(table: str, df: pd.DataFrame, truncar: bool = False,
          lote: int = LOTE, ja_no_banco: int = 0) -> None:
    env = load_env()
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}",
         "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}

    if truncar:
        r = requests.delete(f"{url}/rest/v1/{table}", headers=h,
                            params={"municipio_cod": "not.is.null"}, timeout=120)
        if r.status_code not in (200, 204):
            raise RuntimeError(f"{table}: DELETE HTTP {r.status_code} {r.text[:200]}")
        print(f"[subir] {table}: tabela esvaziada antes da carga", flush=True)

    recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
    lotes = math.ceil(len(recs) / lote)
    for i in range(lotes):
        body = json.dumps(recs[i * lote:(i + 1) * lote], default=_jd, allow_nan=False)
        for tentativa in range(4):
            r = requests.post(f"{url}/rest/v1/{table}", headers=h, data=body, timeout=300)
            if r.status_code in (200, 201):
                break
            if tentativa == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"{table}: HTTP {r.status_code} {r.text[:300]}")
            time.sleep(3 * (tentativa + 1))
        print(f"[subir] {table}: lote {i + 1}/{lotes}", flush=True)

    # Confere LENDO DE VOLTA, não contando o que se tentou enviar.
    #
    # A linha anterior imprimia `len(recs)` — o tamanho do que saiu daqui — e
    # isso não é evidência de nada sobre o outro lado. Em 2026-09-03 uma carga
    # de `mart_mortalidade_municipio` foi interrompida no meio: 17.601 das
    # 201.760 linhas de 2025 entraram, e a única razão de o defeito ter
    # aparecido foi alguém ter conferido o banco à mão depois. Sem esta leitura,
    # a tabela ficava 184 mil linhas curta com "linhas publicadas" no log.
    #
    # Vale também para o caso sem interrupção: upsert que resolva conflito
    # descartando linha não devolve erro, devolve 200.
    r = requests.get(f"{url}/rest/v1/{table}", timeout=120,
                     headers={**h, "Prefer": "count=exact", "Range": "0-0"},
                     params={"select": df.columns[0]})
    if r.status_code not in (200, 206):
        raise RuntimeError(f"{table}: conferência HTTP {r.status_code} {r.text[:200]}")
    no_banco = int(r.headers["Content-Range"].split("/")[-1])
    # `ja_no_banco` é o que a tabela tinha ANTES desta carga e que este recorte
    # não cobre — sem ele, subir só um ano acusaria falsamente carga incompleta.
    esperado = len(recs) + ja_no_banco
    if no_banco < esperado:
        raise RuntimeError(
            f"{table}: carga INCOMPLETA — {no_banco:,} linhas no banco contra "
            f"{esperado:,} esperadas ({esperado - no_banco:,} faltando). "
            "A tabela ficou parcial; rode de novo antes de publicar.")
    extra = ("" if no_banco == esperado
             else f" (o banco tem {no_banco:,}: há linhas que este recorte não cobre)")
    print(f"[subir] {table}: {len(recs):,} linhas publicadas, conferidas no banco{extra}",
          flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tabela")
    ap.add_argument("--truncar", action="store_true",
                    help="apaga a tabela antes de carregar (para marts sem PK estável)")
    ap.add_argument("--lote", type=int, default=LOTE,
                    help=f"linhas por requisição (padrão {LOTE}); reduza em tabela "
                         "grande, onde o upsert estoura o statement_timeout")
    ap.add_argument("--anos", type=str, default=None,
                    help="sobe só estes anos, separados por vírgula (ex.: 2025). "
                         "Reenviar linha idêntica não é inofensivo: é o upsert mais "
                         "caro que existe, e foi o que fez a carga de 1,3 milhão de "
                         "linhas levar horas para acrescentar 200 mil")
    args = ap.parse_args()

    caminho = MARTS / f"{args.tabela}.parquet"
    if not caminho.exists():
        raise SystemExit(f"parquet não encontrado: {caminho}")
    df = pd.read_parquet(caminho)
    ja_no_banco = 0
    if args.anos:
        if "ano" not in df.columns:
            raise SystemExit(f"{args.tabela} não tem coluna `ano` — --anos não se aplica")
        anos = {int(a) for a in args.anos.split(",")}
        fora = sorted(set(df.ano.unique()) - anos)
        ja_no_banco = int(df.ano.isin(fora).sum())
        df = df[df.ano.isin(anos)]
        if df.empty:
            raise SystemExit(f"nenhuma linha de {sorted(anos)} em {caminho.name}")
        print(f"[subir] {args.tabela}: recorte {sorted(anos)} — {len(df):,} linhas; "
              f"as outras {ja_no_banco:,} ficam como estão", flush=True)
    print(f"[subir] {args.tabela}: {len(df):,} linhas em {caminho.name}", flush=True)
    subir(args.tabela, df, truncar=args.truncar, lote=args.lote,
          ja_no_banco=ja_no_banco)


if __name__ == "__main__":
    main()
