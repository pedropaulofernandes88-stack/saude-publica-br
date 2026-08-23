"""
pipeline_sih.py — SIH/AIH (internações SUS) → mart agregado (streaming)
=======================================================================

Arquivos RD{UF}{AAMM}.dbc são mensais por UF (~17 MB cada). Para cobrir N anos
são 27×12×N arquivos. Estratégia: baixar → descomprimir → agregar em streaming
→ descartar o bruto, mantendo apenas contadores por (município, ano, capítulo CID).
Disco e memória permanecem baixos; o custo é tempo/banda.

Fonte: SIH/DataSUS, /dissemin/publicos/SIHSUS/200801_/Dados/RD{UF}{AAMM}.dbc

Mart:
  mart_internacoes_municipio — município × ano × capítulo CID-10 (e TOTAL):
    internações, óbitos (MORTE=1), dias de permanência, valor aprovado (R$),
    permanência média, mortalidade intra-hospitalar, custo médio, internações/100k.

Convenções:
  - Município = residência do paciente (MUNIC_RES).
  - Capítulo CID-10 pelo diagnóstico principal (DIAG_PRINC).
  - Valores = VAL_TOT (valor total aprovado da AIH).

TIPO DE AIH (IDENT) — volume total vs. média por episódio
----------------------------------------------------------
O RD mistura AIH normal (IDENT=1) com AIH de CONTINUAÇÃO (IDENT=5), emitida
quando uma internação se prolonga além do período da AIH anterior. Uma mesma
internação longa gera, portanto, várias linhas. Contar linhas como "internações"
é a aproximação operacional correta para PRODUÇÃO aprovada, mas distorce
qualquer MÉDIA POR EPISÓDIO.

Medido em amostra de 808.470 AIHs (SP, MG, BA, PA, RS; 2024): IDENT=5 é 1,26%
das linhas mas 6,57% dos dias de permanência, e concentra-se em dois capítulos:

  cap. VI (sistema nervoso)   internações -19,9%, permanência 10,98 -> 6,21 dias
  cap. V  (transtornos ment.) internações -23,7%, permanência 14,43 -> 11,72
  outros 17 capítulos         |Δ| <= 0,8% e <= 2,1%

Regra adotada: manter o volume total (todas as AIHs aprovadas) E publicar os
contadores restritos à AIH normal, para que a média por episódio seja calculável
sem perder a produção. Colunas `aih_continuacao`, `dias_permanencia_normal` e
`valor_normal`; `permanencia_media` e `custo_medio` passam a usar a base normal.

Fundamentação: R. F. Saldanha, "Sistemas de Informação em Saúde no Brasil",
cap. SIH — "estadias prolongadas podem exigir regras de continuidade para evitar
fracionamento artificial". https://rfsaldanha.github.io/sis/sih.html

Uso:
  .venv311/Scripts/python scripts/pipeline_sih.py --anos 2023 2024 --workers 8
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from ftplib import FTP
from pathlib import Path

import pandas as pd
import requests

from _metricas_aih import (MEDIDAS, aplica_metricas_por_episodio,
                           capitulo as _capitulo)

from _varredura import varrer_orfaos
from _supabase_key import chave_escrita

# A linhagem viaja com os BYTES: `escrever_parquet` grava no proprio
# Parquet quem o produziu. Sem isso, um arquivo que veio do Postgres e um
# que veio do pipeline sao indistinguiveis, e o manifesto afirma o que
# ninguem verificou.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _publicacao import acumular_parquet  # noqa: E402

# Windows: quando a saida e redirecionada para arquivo, o Python usa cp1252 e um
# unico caractere fora da tabela (ex.: a seta dos logs) derruba o pipeline inteiro
# no meio do processamento. Forca UTF-8 na saida.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS_DIR = ROOT / "data" / "marts"

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SIHSUS/200801_/Dados"

UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
       "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]


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


def _process_file(uf: str, ano: int, mes: int) -> dict | None:
    """Baixa e agrega um RD mensal.

    Retorna dict[(mun6, cap)] = [n, obitos, dias, valor, n_cont, dias_norm, valor_norm],
    onde `n_cont` conta AIH de continuação (IDENT=5) e os campos `_norm` somam apenas
    AIH normal — ver a nota sobre IDENT no cabeçalho do módulo.
    None em erro/ausência (meses futuros)."""
    import datasus_dbc
    import dbfread

    yymm = f"{ano % 100:02d}{mes:02d}"
    nome = f"RD{uf}{yymm}"
    try:
        ftp = FTP(FTP_HOST, timeout=180)
        ftp.login()
        try:
            ftp.size(f"{FTP_DIR}/{nome}.dbc")
        except Exception:
            ftp.quit()
            return None  # mês inexistente
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {FTP_DIR}/{nome}.dbc", buf.write)
        ftp.quit()
    except Exception:
        return None

    tmp = Path(tempfile.gettempdir())
    dbc = tmp / f"{nome}.dbc"
    dbf = tmp / f"{nome}.dbf"
    dbc.write_bytes(buf.getvalue())
    try:
        datasus_dbc.decompress(str(dbc), str(dbf))
        agg: dict = defaultdict(lambda: [0, 0, 0, 0.0, 0, 0, 0.0])
        for rec in dbfread.DBF(str(dbf), encoding="latin-1", char_decode_errors="replace", load=False):
            mun = (str(rec.get("MUNIC_RES") or "")).strip()[:6]
            if len(mun) < 6:
                continue
            cid = (str(rec.get("DIAG_PRINC") or "")).strip().upper()[:3]
            cap = _capitulo(cid) if cid else "N/D"
            try:
                dias = int(rec.get("DIAS_PERM") or 0)
            except (ValueError, TypeError):
                dias = 0
            try:
                val = float(rec.get("VAL_TOT") or 0)
            except (ValueError, TypeError):
                val = 0.0
            morte = 1 if str(rec.get("MORTE") or "0").strip() in ("1",) else 0
            cont = 1 if str(rec.get("IDENT") or "").strip() == "5" else 0
            c = agg[(mun, cap)]
            c[0] += 1; c[1] += morte; c[2] += dias; c[3] += val
            c[4] += cont
            if not cont:
                c[5] += dias; c[6] += val
        return dict(agg)
    finally:
        dbc.unlink(missing_ok=True)
        dbf.unlink(missing_ok=True)


CKPT = ROOT / "data" / "raw" / "SIH" / "ckpt"


def _process_uf_ano(uf: str, ano: int, workers: int) -> pd.DataFrame:
    """Processa os 12 meses de uma UF/ano (paralelo) → df agregado. Checkpoint resumível."""
    CKPT.mkdir(parents=True, exist_ok=True)
    # sufixo _v2: os checkpoints anteriores nao tinham os contadores por IDENT e
    # seriam reaproveitados em silencio, produzindo um mart sem as colunas novas.
    ckpt = CKPT / f"sih_{uf}_{ano}_v2.parquet"
    if ckpt.exists():
        return pd.read_parquet(ckpt)

    agg: dict = defaultdict(lambda: [0, 0, 0, 0.0, 0, 0, 0.0])  # (mun, cap) -> [...]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_process_file, uf, ano, m): m for m in range(1, 13)}
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                for (mun, cap), c in res.items():
                    t = agg[(mun, cap)]
                    for i in range(7):
                        t[i] += c[i]
    df = pd.DataFrame(
        [(mun, ano, cap, c[0], c[1], c[2], round(c[3], 2), c[4], c[5], round(c[6], 2))
         for (mun, cap), c in agg.items()],
        columns=["municipio_cod", "ano", "capitulo_cid", "internacoes", "obitos",
                 "dias_permanencia", "valor_total", "aih_continuacao",
                 "dias_permanencia_normal", "valor_normal"])
    df.to_parquet(ckpt, compression="zstd", index=False)
    print(f"[sih] {uf} {ano}: {int(df['internacoes'].sum()):,} internações "
          f"({int(df['aih_continuacao'].sum()):,} de continuação) → checkpoint", flush=True)
    return df


def build(anos: list[int], workers: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    partes = []
    for a in anos:
        for uf in UFS:
            partes.append(_process_uf_ano(uf, a, workers))
    det = pd.concat(partes, ignore_index=True)
    det = (det.groupby(["municipio_cod", "ano", "capitulo_cid"], as_index=False)
           [MEDIDAS].sum())

    # linha TOTAL (todos os capítulos) por município/ano
    tot = (det.groupby(["municipio_cod", "ano"], as_index=False)[MEDIDAS].sum())
    tot["capitulo_cid"] = "TOTAL"
    mart = pd.concat([det, tot], ignore_index=True)

    # enriquecimento
    municipios = pd.read_parquet(REFS / "municipios.parquet")
    pop = pd.read_parquet(next(REFS.glob("populacao_*.parquet")))[["municipio_cod", "ano", "populacao"]]
    mart = mart.merge(municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]],
                      on="municipio_cod", how="left")
    mart["uf_sigla"] = mart["uf_sigla"].fillna("ND")
    mart = mart.merge(pop, on=["municipio_cod", "ano"], how="left")

    # Médias POR EPISÓDIO usam a base de AIH normal: incluir a AIH de continuação
    # fraciona uma internação longa em varias linhas e infla a média (cap. VI:
    # 10,98 vs. 6,21 dias). O volume (`internacoes`) segue sendo toda a produção
    # aprovada. Ver a nota sobre IDENT no cabeçalho do módulo.
    aplica_metricas_por_episodio(mart, casas_permanencia=2)
    mart["internacoes_100k"] = None
    m_tot = mart["capitulo_cid"] == "TOTAL"
    mart.loc[m_tot, "internacoes_100k"] = (
        mart.loc[m_tot, "internacoes"] / mart.loc[m_tot, "populacao"] * 100_000
    ).round(1)
    mart["populacao"] = mart["populacao"].where(m_tot).astype("Int64")  # nullable int

    mart = mart.sort_values(["municipio_cod", "ano", "capitulo_cid"]).reset_index(drop=True)
    print(f"[sih] mart_internacoes: {len(mart):,} linhas")
    n_tot, n_cont = int(det["internacoes"].sum()), int(det["aih_continuacao"].sum())
    d_tot, d_norm = int(det["dias_permanencia"].sum()), int(det["dias_permanencia_normal"].sum())
    pct_dias = (1 - d_norm / d_tot) * 100 if d_tot else 0.0
    print(f"[sih] internações {min(anos)}–{max(anos)}: {n_tot:,} | "
          f"valor total R$ {det['valor_total'].sum()/1e9:.1f} bi")
    print(f"[sih] AIH de continuação (IDENT=5): {n_cont:,} "
          f"({n_cont/n_tot*100:.2f}% das linhas, {pct_dias:.2f}% dos dias)")
    return mart, municipios


class SupabaseLoader:
    def __init__(self, url: str, key: str, batch: int = 8_000):
        self.url = url.rstrip("/")
        self.h = {"apikey": key, "Authorization": f"Bearer {key}",
                  "Content-Type": "application/json",
                  "Prefer": "return=minimal,resolution=merge-duplicates"}
        self.batch = batch

    def load_df(self, table: str, df: pd.DataFrame) -> None:
        df = df.copy()
        recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
        nb = math.ceil(len(recs) / self.batch)
        for i in range(nb):
            body = json.dumps(recs[i*self.batch:(i+1)*self.batch], default=_jd, allow_nan=False)
            for a in range(4):
                r = requests.post(f"{self.url}/rest/v1/{table}", headers=self.h, data=body, timeout=300)
                if r.status_code in (200, 201):
                    break
                if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                    raise RuntimeError(f"{table} lote {i+1}/{nb}: HTTP {r.status_code} {r.text[:200]}")
                time.sleep(3 * (a + 1))
            print(f"[supabase]   {table}: {min((i+1)*self.batch, len(recs)):,}/{len(recs):,}", end="\r", flush=True)
        print(f"[supabase]   {table}: {len(recs):,} OK            ")


def _jd(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(str(type(o)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="+", type=int, default=[2022, 2023, 2024])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    anos = sorted(args.anos)
    env = load_env()

    mart, _ = build(anos, args.workers)

    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    _, _antes, _depois = acumular_parquet(
        mart, MARTS_DIR / "mart_internacoes_municipio.parquet", "mart_internacoes_municipio",
        origem="pipeline", produtor="scripts/pipeline_sih.py")
    print(f"[acumulado] mart_internacoes_municipio: {_antes:,} -> {_depois:,} linhas", flush=True)

    if args.no_upload:
        return

    url, key = env.get("SUPABASE_URL"), chave_escrita(env)
    if not url or not key:
        sys.exit("Defina SUPABASE_URL e SUPABASE_ANON_KEY no .env")
    loader = SupabaseLoader(url, key)
    loader.load_df("mart_internacoes_municipio", mart)
    # Upsert nao remove o que saiu do calculo; a varredura fecha essa lacuna.
    varrer_orfaos(url, key, "mart_internacoes_municipio", mart,
                  chaves=["municipio_cod", "ano", "capitulo_cid"],
                  escopo={"ano": f"in.({','.join(str(a) for a in anos)})"})

    meta = pd.DataFrame([
        ("fonte_sih", "SIH/DataSUS — AIH (RD), FTP SIHSUS/200801_"),
        ("sih_cobertura", f"{min(anos)}–{max(anos)}"),
        ("sih_definicoes", "Internações por residência (MUNIC_RES) e capítulo CID-10 do diagnóstico principal; valor=VAL_TOT aprovado; mortalidade intra-hospitalar=MORTE/internações. `internacoes` conta AIHs aprovadas (produção), incluindo AIH de continuação (IDENT=5); `permanencia_media` e `custo_medio` são calculados sobre a AIH normal (`aih_normal`), porque a continuação fraciona uma internação longa em várias linhas — efeito relevante só nos capítulos V e VI."),
        ("gerado_em", datetime.now().isoformat(timespec="seconds")),
    ], columns=["chave", "valor"])
    loader.load_df("meta_dataset", meta)
    print("[done] pipeline SIH concluído.")


if __name__ == "__main__":
    main()
