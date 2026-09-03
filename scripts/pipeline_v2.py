"""
pipeline_v2.py — Pipeline completo: SIM 2015–2024, padronização etária,
IC95% e excesso de mortalidade. Substitui o pipeline_custo_zero.py (v1).
==========================================================================

Fontes (todas oficiais e abertas):
  - SIM 2022+   : CSV nacional OpenDataSUS (DO{AA}OPEN.csv)
  - SIM 2015–21 : arquivos .dbc por UF/ano (FTP DataSUS, CID10/DORES),
                  convertidos com datasus-dbc (requer Python 3.10–3.12)
  - IBGE        : municípios (localidades), população total por ano (SIDRA
                  6579/4709), população por faixa etária (Censo 2022, t/9514)

Metodologia (documentada em saudeemdado.com/metodologia):
  - Óbitos fetais fora da base PELA FONTE: o filtro TIPOBITO<>1 existe e é
    correto, mas nunca removeu nada — 100% dos 14.378.827 registros das duas
    fontes têm TIPOBITO=2. O óbito fetal está em SIM/CID10/DOFET, que não é
    coletado. O filtro fica como defesa contra fonte futura que os misture
  - Taxa padronizada por idade: método direto, padrão = Brasil Censo 2022,
    9 faixas; óbitos com idade ignorada redistribuídos pro-rata no município/ano
  - IC95% da taxa bruta: método gamma (Poisson exato)
  - População por faixa nos anos ≠2022: estrutura do Censo 2022 escalada pelo
    total municipal do ano (aproximação documentada)
  - Excesso de mortalidade: esperado = tendência linear por mês civil ajustada a
    2015–2019 (mínimos quadrados, 5 pontos) e projetada para o ano-alvo, por UF
    e Brasil, a partir de 2020. Excesso = observado − esperado
  - Detalhe demográfico completo a partir de 2022; 2015–2021 em grão reduzido
    (totais e marginais) para caber no free tier

Uso:
  .venv311/Scripts/python scripts/pipeline_v2.py                # tudo
  .venv311/Scripts/python scripts/pipeline_v2.py --medir        # sem upload
  .venv311/Scripts/python scripts/pipeline_v2.py --anos 2015 2016
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from ftplib import FTP
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests

from _datasus_ftp import CHAVE_FONTE, baixar, fonte_do_checkpoint, tamanho
from _publicacao import escrever_parquet
from _sim_obitos import (  # noqa: E402
    ANOS_CSV,
    CID10_CAPITULOS,
    criar_obitos_t,
    criar_tabela_capitulos,
)
from _supabase_key import chave_escrita
from scipy.stats import gamma as gamma_dist

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "SIM"
RAW_DBC = RAW / "dbc"
REFS = ROOT / "data" / "refs"
MARTS_DIR = ROOT / "data" / "marts"


def versao_dataset() -> str:
    """Versão publicada em meta_dataset, lida do CHANGELOG.

    Estava fixa em "2.0.0" enquanto o banco já servia 3.1.0 e o CHANGELOG
    anunciava 3.2.0 — rodar o pipeline REGREDIRIA o campo em duas versões, e
    quem consome a API não teria como saber qual definição de AIH recebeu.
    O CHANGELOG é a fonte única; aqui só se lê a primeira entrada dele.
    """
    try:
        for linha in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines():
            m = re.match(r"^##\s*\[(\d+\.\d+\.\d+)\]", linha)
            if m:
                return m.group(1)
    except OSError:
        pass
    return "0.0.0"  # sem CHANGELOG legível: melhor um valor obviamente inválido


S3_SIM = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM"
FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SIM/CID10/DORES"

ANO_DETALHE = 2022                      # >= : grão demográfico completo
BASELINE = (2015, 2019)                 # excesso de mortalidade

UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
       "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]

FAIXAS = ["<1","1-4","5-14","15-29","30-44","45-59","60-74","75+"]

# SIDRA t/9514 (Censo 2022) — categorias da classificação 287 → faixa
SIDRA_FAIXA = {
    "<1":    [6557],
    "0-4":   [93070],                      # auxiliar p/ derivar 1-4
    "5-14":  [93084, 93085],
    "15-29": [93086, 93087, 93088],
    "30-44": [93089, 93090, 93091],
    "45-59": [93092, 93093, 93094],
    "60-74": [93095, 93096, 93097],
    "75+":   [93098, 49108, 49109, 60040, 60041, 6653],
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


# ───────────────────────────── Fontes SIM ──────────────────────────────────
def download_csv_open(anos: list[int]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for ano in anos:
        if ano not in ANOS_CSV:
            continue
        dest = RAW / f"DO{str(ano)[2:]}OPEN.csv"
        url = f"{S3_SIM}/DO{str(ano)[2:]}OPEN.csv"
        # O cache valia por "existe e tem mais de 1 MB", ou seja, para sempre. O
        # OpenDataSUS reescreve arquivo publicado; o HEAD custa uma requisicao e
        # diz se o que esta em disco ainda e o que a fonte serve.
        # FONTE INALCANCAVEL != FONTE INALTERADA.
        #
        # Em 2026-09-02 o bucket S3 inteiro do OpenDataSUS passou a responder 403
        # — SIM, SINASC e SIH — enquanto o FTP do DataSUS seguia servindo. Um
        # `raise_for_status()` aqui derrubava o pipeline mesmo com o CSV do ano
        # inteiro ja em disco e conferido.
        #
        # A regra passa a distinguir os dois casos, como manda o principio de
        # ausencia versus falha: sem arquivo local, fonte inalcancavel e FALHA e
        # aborta; com arquivo local, segue e DIZ que nao pode verificar. O que
        # nao se faz e o silencio — cache que se declara valido sem ter
        # comparado com nada foi o defeito original desta funcao.
        try:
            remoto = requests.head(url, timeout=60, allow_redirects=True)
            remoto.raise_for_status()
            bytes_remoto = int(remoto.headers.get("content-length") or 0)
        except requests.RequestException as exc:
            if not dest.exists():
                raise SystemExit(
                    f"{dest.name}: fonte inalcancavel ({exc}) e nao ha copia local. "
                    "Processar sem este ano publicaria recorte incompleto.") from exc
            print(f"[ATENCAO] {dest.name}: fonte inalcancavel ({type(exc).__name__}); "
                  f"usando a copia local de {dest.stat().st_size/1e6:.0f} MB SEM poder "
                  "conferir se a origem mudou.", flush=True)
            continue
        if dest.exists() and bytes_remoto and dest.stat().st_size == bytes_remoto:
            print(f"[cache] {dest.name} ({bytes_remoto/1e6:.0f} MB, tamanho confere)")
            continue
        if dest.exists():
            print(f"[fonte] {dest.name} mudou: {dest.stat().st_size:,} -> {bytes_remoto:,} bytes",
                  flush=True)
        print(f"[download] {url}")
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)


def _dbc_to_parquet(uf: str, ano: int) -> tuple[str, int, str | None]:
    """Baixa DO{UF}{ANO}.dbc via FTP e salva parquet mínimo. Thread-safe."""
    import datasus_dbc
    import dbfread
    import pyarrow as pa
    import pyarrow.parquet as pq
    import tempfile

    out = RAW_DBC / f"DO{uf}{ano}.parquet"
    nome = f"DO{uf}{ano}.dbc"
    cols = ["TIPOBITO", "DTOBITO", "IDADE", "SEXO", "CODMUNRES", "LOCOCOR", "CAUSABAS"]
    try:
        # O cache valia por "existe e tem mais de 1 KB" e nunca era revisitado.
        # Agora ele carrega, nos metadados Arrow, a VERSAO do .dbc que o
        # produziu; se o DataSUS reescrever o arquivo, o tamanho muda e o cache
        # deixa de servir sozinho. Mesmo carimbo do SIH e do SINAN.
        marca = f"{nome} bytes={tamanho(FTP_DIR, nome)}"
        if out.exists() and fonte_do_checkpoint(out) == marca:
            return (f"{uf}{ano}", -1, None)  # cache da versao atual

        tmp = Path(tempfile.gettempdir())
        dbc = tmp / nome
        dbf = tmp / f"DO{uf}{ano}.dbf"
        dbc.write_bytes(baixar(FTP_DIR, nome))
        datasus_dbc.decompress(str(dbc), str(dbf))

        rows = []
        for rec in dbfread.DBF(str(dbf), encoding="latin-1", char_decode_errors="replace"):
            rows.append(tuple(str(rec.get(c) or "") for c in cols))
        dbc.unlink(missing_ok=True)
        dbf.unlink(missing_ok=True)

        table = pa.table({c: [r[i] for r in rows] for i, c in enumerate(cols)})
        table = table.replace_schema_metadata({CHAVE_FONTE: marca})
        out.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, out, compression="zstd")
        return (f"{uf}{ano}", len(rows), None)
    except Exception as exc:  # noqa: BLE001
        return (f"{uf}{ano}", 0, f"{type(exc).__name__}: {exc}")


def download_dbc(anos: list[int], workers: int = 4) -> None:
    alvos = [(uf, a) for a in anos if a not in ANOS_CSV for uf in UFS]
    if not alvos:
        return
    RAW_DBC.mkdir(parents=True, exist_ok=True)
    # Existir nao basta: o parquet precisa DECLARAR de qual versao do .dbc veio.
    # `fonte_do_checkpoint` devolve None tanto para arquivo ausente quanto para
    # arquivo sem carimbo, entao um criterio so cobre os dois casos.
    pend = [(u, a) for u, a in alvos
            if fonte_do_checkpoint(RAW_DBC / f"DO{u}{a}.parquet") is None]
    print(f"[dbc] {len(alvos)} arquivos alvo, {len(pend)} a baixar (FTP DataSUS)")
    erros = []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_dbc_to_parquet, u, a): (u, a) for u, a in pend}
        for fut in as_completed(futs):
            key, n, err = fut.result()
            done += 1
            if err:
                erros.append((key, err))
                print(f"[dbc] {done}/{len(pend)} {key} ERRO {err[:80]}", flush=True)
            else:
                print(f"[dbc] {done}/{len(pend)} {key}: {n:,} registros", flush=True)
    # retry sequencial dos erros
    for key, _ in list(erros):
        uf, ano = key[:2], int(key[2:])
        k2, n2, e2 = _dbc_to_parquet(uf, ano)
        if not e2:
            erros = [e for e in erros if e[0] != key]
            print(f"[dbc] retry {key}: {n2:,} registros OK")
    if erros:
        raise RuntimeError(f"{len(erros)} arquivos DBC falharam: {[e[0] for e in erros]}")


# ───────────────────────────── Referências IBGE ─────────────────────────────
def fetch_municipios() -> pd.DataFrame:
    cache = REFS / "municipios.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
    rows = requests.get(url, timeout=60).json()
    df = pd.DataFrame({
        "municipio_cod7": [str(x["municipio-id"]) for x in rows],
        "municipio_nome": [x["municipio-nome"] for x in rows],
        "uf_sigla": [x["UF-sigla"] for x in rows],
        "uf_nome": [x["UF-nome"] for x in rows],
        "regiao": [x["regiao-nome"] for x in rows],
    })
    df["municipio_cod"] = df["municipio_cod7"].str[:6]
    df = df[["municipio_cod", "municipio_cod7", "municipio_nome", "uf_sigla", "uf_nome", "regiao"]]
    REFS.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df


def _sidra(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data[1:])


def fetch_populacao(anos: list[int]) -> pd.DataFrame:
    """População total municipal por ano: 6579 (estimativas) + 4709 (Censo 2022) + 2023 interpolado."""
    cache = REFS / f"populacao_{min(anos)}_{max(anos)}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)

    frames = []
    anos_est = sorted({a for a in anos if a not in (2022, 2023)})
    if anos_est:
        print(f"[ibge] estimativas {anos_est} (t/6579)...")
        p = ",".join(str(a) for a in anos_est)
        df = _sidra(f"https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/{p}")
        # coluna do ano: localizada dinamicamente (valores = anos pedidos)
        anos_str = {str(a) for a in anos_est}
        ano_col = next(c for c in df.columns if c.startswith("D") and c.endswith("C")
                       and df[c].astype(str).isin(anos_str).all())
        df = df.rename(columns={"D1C": "cod7", ano_col: "ano", "V": "pop"})
        df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
        df["pop"] = pd.to_numeric(df["pop"], errors="coerce")
        df = df.dropna(subset=["ano", "pop"])
        for a in anos_est:
            sub = df[df["ano"] == a]
            frames.append(pd.DataFrame({
                "municipio_cod": sub["cod7"].astype(str).str[:6],
                "ano": a, "populacao": sub["pop"].astype(int),
                "fonte": f"IBGE Estimativas {a}",
            }))

    if 2022 in anos or 2023 in anos:
        print("[ibge] Censo 2022 (t/4709)...")
        c = _sidra("https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022")
        c = c.rename(columns={"D1C": "cod7", "V": "pop"})
        c["pop"] = pd.to_numeric(c["pop"], errors="coerce")
        c = c.dropna(subset=["pop"])
        censo = pd.DataFrame({
            "municipio_cod": c["cod7"].astype(str).str[:6],
            "populacao": c["pop"].astype(int),
        })
        if 2022 in anos:
            d = censo.copy(); d["ano"] = 2022; d["fonte"] = "IBGE Censo 2022"
            frames.append(d[["municipio_cod", "ano", "populacao", "fonte"]])
        if 2023 in anos:
            est24 = next((f for f in frames if (f["ano"] == 2024).all()), None)
            if est24 is not None:
                m = censo.merge(est24[["municipio_cod", "populacao"]], on="municipio_cod",
                                suffixes=("_22", "_24"), how="inner")
                m["populacao"] = ((m["populacao_22"] + m["populacao_24"]) / 2).round().astype(int)
                m["ano"] = 2023
                m["fonte"] = "Interpolação Censo 2022 / Estimativas 2024"
                frames.append(m[["municipio_cod", "ano", "populacao", "fonte"]])

    out = pd.concat(frames, ignore_index=True)
    REFS.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache)
    return out


def fetch_pop_faixa() -> pd.DataFrame:
    """População por faixa etária e município — Censo 2022 (t/9514)."""
    cache = REFS / "pop_faixa_censo2022.parquet"
    if cache.exists():
        return pd.read_parquet(cache)

    todas = sorted({c for ids in SIDRA_FAIXA.values() for c in ids})
    print(f"[ibge] população por idade (t/9514, {len(todas)} grupos × 5570 municípios)...")
    # SIDRA limita ~100k valores por consulta: 5570 municípios × lote de 8 grupos
    partes = []
    for i in range(0, len(todas), 8):
        lote = ",".join(str(c) for c in todas[i:i+8])
        partes.append(_sidra(
            f"https://apisidra.ibge.gov.br/values/t/9514/n6/all/v/93/p/2022/c2/6794/c287/{lote}"
        ))
        print(f"[ibge]   lote {i//8 + 1}: {len(partes[-1]):,} linhas")
    df = pd.concat(partes, ignore_index=True)

    # localiza dinamicamente a coluna da classificação de idade (códigos conhecidos)
    ids_str = {str(c) for c in todas}
    cat_col = next(c for c in df.columns if c.startswith("D") and c.endswith("C")
                   and df[c].astype(str).isin(ids_str).any())
    df = df.rename(columns={"D1C": "cod7", cat_col: "cat", "V": "pop"})
    df["pop"] = pd.to_numeric(df["pop"], errors="coerce").fillna(0)
    df["cat"] = pd.to_numeric(df["cat"], errors="coerce")
    df["municipio_cod"] = df["cod7"].astype(str).str[:6]

    cat2grupo = {c: g for g, ids in SIDRA_FAIXA.items() for c in ids}
    df["grupo"] = df["cat"].map(cat2grupo)
    piv = df.groupby(["municipio_cod", "grupo"])["pop"].sum().unstack(fill_value=0)

    out_rows = []
    for cod, row in piv.iterrows():
        vals = {
            "<1": row.get("<1", 0),
            "1-4": max(row.get("0-4", 0) - row.get("<1", 0), 0),
            "5-14": row.get("5-14", 0),
            "15-29": row.get("15-29", 0),
            "30-44": row.get("30-44", 0),
            "45-59": row.get("45-59", 0),
            "60-74": row.get("60-74", 0),
            "75+": row.get("75+", 0),
        }
        for fx, p in vals.items():
            out_rows.append((cod, fx, int(p)))
    out = pd.DataFrame(out_rows, columns=["municipio_cod", "faixa_etaria", "populacao"])
    out["fonte"] = "IBGE Censo 2022 (SIDRA t/9514)"
    REFS.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache)
    return out


def fetch_cid10_categorias() -> pd.DataFrame | None:
    """Descrições CID-10 (3 chars) — tabela auxiliar do próprio FTP do SIM."""
    cache = REFS / "cid10_categorias.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    try:
        import io
        import dbfread, tempfile
        ftp = FTP(FTP_HOST, timeout=120)
        ftp.login()
        buf = io.BytesIO()
        ftp.retrbinary("RETR /dissemin/publicos/SIM/CID10/TABELAS/CID10.DBF", buf.write)
        ftp.quit()
        tmp = Path(tempfile.gettempdir()) / "CID10.DBF"
        tmp.write_bytes(buf.getvalue())
        rows = []
        for rec in dbfread.DBF(str(tmp), encoding="latin-1", char_decode_errors="replace"):
            vals = {k.upper(): str(v or "").strip() for k, v in rec.items()}
            cd = vals.get("CID10") or vals.get("CD_COD") or vals.get("CODIGO") or ""
            ds = vals.get("DESCR") or vals.get("DS_DESCR") or vals.get("DESCRICAO") or vals.get("NOME") or ""
            if len(cd) == 3 and ds:
                rows.append((cd, ds))
        df = pd.DataFrame(rows, columns=["causabas_3", "descricao"]).drop_duplicates("causabas_3")
        if df.empty:
            return None
        REFS.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache)
        return df
    except Exception as exc:  # noqa: BLE001
        print(f"[cid10] descrições indisponíveis ({exc}) — seguindo sem")
        return None


# ───────────────────────────── Transformação ────────────────────────────────
def build(con: duckdb.DuckDBPyConnection, anos: list[int]) -> None:
    criar_tabela_capitulos(con)

    print("[duckdb] derivando colunas (todas as fontes)...")
    # A derivacao mora em `_sim_obitos.py` para que
    # `pipeline_mortalidade_causa_municipio.py` use a MESMA definicao de
    # obito em vez de reescreve-la. Duas copias divergiriam em silencio.
    criar_obitos_t(con, anos)
    n = con.execute("SELECT count(*) FROM obitos_t").fetchone()[0]
    print(f"[duckdb] óbitos não fetais {min(anos)}–{max(anos)}: {n:,}")
    for ano, cnt in con.execute("SELECT ano, count(*) FROM obitos_t GROUP BY 1 ORDER BY 1").fetchall():
        print(f"[duckdb]   {ano}: {cnt:,}")

    # ── mart município ───────────────────────────────────────────────────────
    print("[duckdb] mart_mortalidade_municipio...")
    con.execute(f"""
        CREATE OR REPLACE TABLE mart_municipio AS
        WITH full_grain AS (
            SELECT o.municipio_cod, m.municipio_nome,
                   COALESCE(m.uf_sigla,'ND') uf_sigla, m.regiao, o.ano,
                   COALESCE(CASE WHEN GROUPING(o.capitulo_cid)=1 THEN 'TOTAL' ELSE o.capitulo_cid END,'TOTAL') capitulo_cid,
                   COALESCE(CASE WHEN GROUPING(o.sexo)=1 THEN 'TOTAL' ELSE o.sexo END,'TOTAL') sexo,
                   count(*)::INT obitos,
                   sum(CASE WHEN o.is_hospital THEN 1 ELSE 0 END)::INT obitos_hospital,
                   sum(CASE WHEN o.is_domicilio THEN 1 ELSE 0 END)::INT obitos_domicilio
            FROM obitos_t o LEFT JOIN dim_municipio m USING (municipio_cod)
            WHERE o.ano >= {ANO_DETALHE}
            GROUP BY GROUPING SETS (
                (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano, o.capitulo_cid, o.sexo),
                (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano, o.capitulo_cid),
                (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano, o.sexo),
                (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano))
        ),
        hist_grain AS (
            SELECT o.municipio_cod, m.municipio_nome,
                   COALESCE(m.uf_sigla,'ND') uf_sigla, m.regiao, o.ano,
                   COALESCE(CASE WHEN GROUPING(o.capitulo_cid)=1 THEN 'TOTAL' ELSE o.capitulo_cid END,'TOTAL') capitulo_cid,
                   'TOTAL' sexo,
                   count(*)::INT obitos,
                   sum(CASE WHEN o.is_hospital THEN 1 ELSE 0 END)::INT obitos_hospital,
                   sum(CASE WHEN o.is_domicilio THEN 1 ELSE 0 END)::INT obitos_domicilio
            FROM obitos_t o LEFT JOIN dim_municipio m USING (municipio_cod)
            WHERE o.ano < {ANO_DETALHE}
            GROUP BY GROUPING SETS (
                (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano, o.capitulo_cid),
                (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano))
        )
        SELECT * FROM full_grain UNION ALL SELECT * FROM hist_grain
    """)

    # taxa padronizada: óbitos por faixa (IGN redistribuído pro-rata) × pop faixa do ano
    print("[duckdb] taxa padronizada por idade...")
    con.execute("""
        CREATE OR REPLACE TABLE obitos_faixa AS
        WITH base AS (
            SELECT municipio_cod, ano, faixa_etaria, count(*)::DOUBLE d
            FROM obitos_t GROUP BY 1,2,3
        ),
        tot AS (
            SELECT municipio_cod, ano,
                   sum(CASE WHEN faixa_etaria <> 'IGN' THEN d END) d_known,
                   sum(CASE WHEN faixa_etaria  = 'IGN' THEN d END) d_ign
            FROM base GROUP BY 1,2
        )
        SELECT b.municipio_cod, b.ano, b.faixa_etaria,
               b.d * (1 + COALESCE(t.d_ign,0) / NULLIF(t.d_known,0)) AS d_adj
        FROM base b JOIN tot t USING (municipio_cod, ano)
        WHERE b.faixa_etaria <> 'IGN'
    """)
    con.execute("""
        CREATE OR REPLACE TABLE taxa_pad AS
        WITH pop_ano AS (  -- estrutura Censo 2022 escalada pelo total do ano
            SELECT pf.municipio_cod, p.ano, pf.faixa_etaria,
                   pf.populacao * (p.populacao::DOUBLE / NULLIF(c22.populacao,0)) AS pop_f
            FROM dim_pop_faixa pf
            JOIN dim_populacao p  ON p.municipio_cod = pf.municipio_cod
            JOIN (SELECT municipio_cod, populacao FROM dim_populacao WHERE ano = 2022) c22
              ON c22.municipio_cod = pf.municipio_cod
        ),
        w AS (SELECT faixa_etaria, populacao::DOUBLE / sum(populacao) OVER () AS w FROM dim_pop_padrao)
        SELECT o.municipio_cod, o.ano,
               round(sum(w.w * o.d_adj / NULLIF(pa.pop_f,0)) * 100000, 2) AS taxa_padronizada_100k
        FROM obitos_faixa o
        JOIN pop_ano pa USING (municipio_cod, ano, faixa_etaria)
        JOIN w ON w.faixa_etaria = o.faixa_etaria
        WHERE pa.pop_f > 0
        GROUP BY 1, 2
    """)

    con.execute("""
        CREATE OR REPLACE TABLE mart_municipio_final AS
        SELECT mm.*,
               CASE WHEN mm.sexo='TOTAL' THEN p.populacao END AS populacao,
               CASE WHEN mm.sexo='TOTAL' AND COALESCE(p.populacao,0) > 0
                    THEN round(mm.obitos * 100000.0 / p.populacao, 2) END AS taxa_obitos_100k,
               CASE WHEN mm.sexo='TOTAL' AND mm.capitulo_cid='TOTAL'
                    THEN tp.taxa_padronizada_100k END AS taxa_padronizada_100k
        FROM mart_municipio mm
        LEFT JOIN dim_populacao p ON p.municipio_cod = mm.municipio_cod AND p.ano = mm.ano
        LEFT JOIN taxa_pad tp     ON tp.municipio_cod = mm.municipio_cod AND tp.ano = mm.ano
    """)

    # ── mart UF × mês ────────────────────────────────────────────────────────
    print("[duckdb] mart_mortalidade_uf_mes...")
    con.execute(f"""
        CREATE OR REPLACE TABLE mart_uf_mes AS
        WITH full_grain AS (
            SELECT COALESCE(m.uf_sigla,'ND') uf_sigla, any_value(m.regiao) regiao,
                   o.ano, o.mes, o.mes_competencia,
                   COALESCE(CASE WHEN GROUPING(o.capitulo_cid)=1 THEN 'TOTAL' ELSE o.capitulo_cid END,'TOTAL') capitulo_cid,
                   COALESCE(CASE WHEN GROUPING(o.sexo)=1 THEN 'TOTAL' ELSE o.sexo END,'TOTAL') sexo,
                   COALESCE(CASE WHEN GROUPING(o.faixa_etaria)=1 THEN 'TOTAL' ELSE o.faixa_etaria END,'TOTAL') faixa_etaria,
                   count(*)::INT obitos
            FROM obitos_t o LEFT JOIN dim_municipio m USING (municipio_cod)
            WHERE o.ano >= {ANO_DETALHE}
            GROUP BY GROUPING SETS (
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid, o.sexo, o.faixa_etaria),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid, o.sexo),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid, o.faixa_etaria),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.sexo, o.faixa_etaria),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.sexo),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.faixa_etaria),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia))
        ),
        hist_grain AS (
            SELECT COALESCE(m.uf_sigla,'ND') uf_sigla, any_value(m.regiao) regiao,
                   o.ano, o.mes, o.mes_competencia,
                   COALESCE(CASE WHEN GROUPING(o.capitulo_cid)=1 THEN 'TOTAL' ELSE o.capitulo_cid END,'TOTAL') capitulo_cid,
                   COALESCE(CASE WHEN GROUPING(o.sexo)=1 THEN 'TOTAL' ELSE o.sexo END,'TOTAL') sexo,
                   COALESCE(CASE WHEN GROUPING(o.faixa_etaria)=1 THEN 'TOTAL' ELSE o.faixa_etaria END,'TOTAL') faixa_etaria,
                   count(*)::INT obitos
            FROM obitos_t o LEFT JOIN dim_municipio m USING (municipio_cod)
            WHERE o.ano < {ANO_DETALHE}
            GROUP BY GROUPING SETS (
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.sexo),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.faixa_etaria),
                (m.uf_sigla, o.ano, o.mes, o.mes_competencia))
        )
        SELECT * FROM full_grain UNION ALL SELECT * FROM hist_grain
    """)

    print("[duckdb] mart_mortalidade_causa...")
    con.execute("""
        CREATE OR REPLACE TABLE mart_causa AS
        SELECT o.ano, COALESCE(m.uf_sigla,'ND') uf_sigla, o.causabas_3,
               any_value(o.capitulo_cid) capitulo_cid, count(*)::INT obitos
        FROM obitos_t o LEFT JOIN dim_municipio m USING (municipio_cod)
        WHERE o.causabas_3 <> ''
        GROUP BY 1, 2, 3
    """)

    # ── excesso de mortalidade ──────────────────────────────────────────────
    print("[duckdb] mart_excesso_uf_mes...")
    con.execute(f"""
        CREATE OR REPLACE TABLE mart_excesso AS
        WITH serie AS (
            -- 'ND' = obito sem UF de residencia identificada. Excesso "da UF
            -- desconhecida" nao e uma serie interpretavel, e a tabela publicada
            -- nunca o teve; sem este filtro o pipeline criaria uma 28a serie
            -- espuria. Os obitos ND seguem contando no total do Brasil abaixo,
            -- que agrega tudo -- eles existiram, so nao se sabe onde.
            SELECT uf_sigla, ano, mes, mes_competencia, obitos
            FROM mart_uf_mes
            WHERE capitulo_cid='TOTAL' AND sexo='TOTAL' AND faixa_etaria='TOTAL'
              AND uf_sigla <> 'ND'
            UNION ALL
            SELECT 'BR', ano, mes, make_date(ano, mes, 1), sum(obitos)::INT
            FROM mart_uf_mes
            WHERE capitulo_cid='TOTAL' AND sexo='TOTAL' AND faixa_etaria='TOTAL'
            GROUP BY 2, 3
        ),
        -- Tendencia linear por MES CIVIL: regride os obitos daquele mes contra o
        -- ano em {BASELINE[0]}-{BASELINE[1]} (minimos quadrados, 5 pontos) e projeta para o
        -- ano-alvo. Captura crescimento populacional E envelhecimento, que elevam
        -- o esperado ano a ano.
        --
        -- O metodo ANTERIOR era media do baseline x razao populacional. Ele
        -- ignorava a tendencia secular e por isso superestimava o excesso nos
        -- anos recentes: o "excesso persistente" de 2022-2023 era em boa parte
        -- artefato disso. A troca foi anunciada no CHANGELOG 3.1.0 e esta descrita
        -- em site/app/metodologia (secao 6), nos artigos e no preprint -- mas
        -- nunca chegou a ESTE script, que continuou com a media. Quem rodasse o
        -- pipeline reverteria silenciosamente os numeros publicados.
        tend AS (
            SELECT s.uf_sigla, s.mes,
                   regr_intercept(s.obitos, s.ano) AS a,
                   regr_slope(s.obitos, s.ano)     AS b
            FROM serie s
            WHERE s.ano BETWEEN {BASELINE[0]} AND {BASELINE[1]}
            GROUP BY 1, 2
        )
        SELECT s.uf_sigla, s.ano, s.mes, s.mes_competencia,
               s.obitos,
               round(t.a + t.b * s.ano, 1)                                    AS esperado,
               round(s.obitos - (t.a + t.b * s.ano), 1)                       AS excesso,
               round((s.obitos / NULLIF(t.a + t.b * s.ano, 0) - 1) * 100, 2)  AS pct_excesso
        FROM serie s
        JOIN tend t ON t.uf_sigla = s.uf_sigla AND t.mes = s.mes
        WHERE s.ano >= 2020
    """)

    for t in ("mart_municipio_final", "mart_uf_mes", "mart_causa", "mart_excesso"):
        print(f"[duckdb]   {t}: {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:,} linhas")


def add_ic95(df: pd.DataFrame) -> pd.DataFrame:
    """IC95% (gamma/Poisson exato) da taxa bruta nas linhas sexo=TOTAL com população."""
    df["ic95_inf"] = np.nan
    df["ic95_sup"] = np.nan
    m = (df["sexo"] == "TOTAL") & df["populacao"].notna() & (df["populacao"] > 0)
    d = df.loc[m, "obitos"].to_numpy(dtype=float)
    p = df.loc[m, "populacao"].to_numpy(dtype=float)
    inf = np.where(d > 0, gamma_dist.ppf(0.025, np.maximum(d, 1e-9)) / p * 1e5, 0.0)
    sup = gamma_dist.ppf(0.975, d + 1) / p * 1e5
    df.loc[m, "ic95_inf"] = np.round(inf, 2)
    df.loc[m, "ic95_sup"] = np.round(sup, 2)
    return df


# ───────────────────────────── Upload ───────────────────────────────────────
class SupabaseLoader:
    def __init__(self, url: str, anon_key: str, batch_rows: int = 8_000):
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal,resolution=merge-duplicates",
        }
        self.batch = batch_rows

    def load_df(self, table: str, df: pd.DataFrame) -> None:
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
        records = df.astype(object).where(pd.notna(df), None).to_dict("records")
        nb = math.ceil(len(records) / self.batch)
        sent = 0
        for i in range(nb):
            body = json.dumps(records[i*self.batch:(i+1)*self.batch], default=_jd, allow_nan=False)
            for attempt in range(4):
                r = requests.post(f"{self.url}/rest/v1/{table}", headers=self.headers,
                                  data=body, timeout=300)
                if r.status_code in (200, 201):
                    break
                if attempt == 3 or r.status_code in (400, 401, 403, 404, 409):
                    raise RuntimeError(f"{table} lote {i+1}/{nb}: HTTP {r.status_code} {r.text[:200]}")
                time.sleep(3 * (attempt + 1))
            sent += min(self.batch, len(records) - i*self.batch)
            print(f"[supabase]   {table}: {sent:,}/{len(records):,}", end="\r", flush=True)
        print(f"[supabase]   {table}: {len(records):,} OK            ")


def _jd(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(str(type(o)))


# ───────────────────────────── Main ─────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="+", type=int, default=list(range(2015, 2025)))
    ap.add_argument("--medir", action="store_true")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    anos = sorted(args.anos)
    env = load_env()

    download_csv_open(anos)
    download_dbc(anos, args.workers)

    municipios = fetch_municipios()
    populacao = fetch_populacao(anos)
    pop_faixa = fetch_pop_faixa()
    pop_padrao = (pop_faixa.groupby("faixa_etaria", as_index=False)["populacao"].sum())
    pop_padrao["fonte"] = "Brasil, Censo 2022 (soma municipal)"
    cid_cat = fetch_cid10_categorias()
    print(f"[refs] municipios {len(municipios):,} | populacao {len(populacao):,} | "
          f"pop_faixa {len(pop_faixa):,} | cid10cat {0 if cid_cat is None else len(cid_cat):,}")

    con = duckdb.connect()
    con.register("mdf", municipios);  con.execute("CREATE TABLE dim_municipio AS SELECT * FROM mdf")
    con.register("pdf_", populacao);  con.execute("CREATE TABLE dim_populacao AS SELECT * FROM pdf_")
    con.register("pff", pop_faixa);   con.execute("CREATE TABLE dim_pop_faixa AS SELECT * FROM pff")
    con.register("ppd", pop_padrao);  con.execute("CREATE TABLE dim_pop_padrao AS SELECT * FROM ppd")

    build(con, anos)

    mart_mun = con.execute("SELECT * FROM mart_municipio_final").df()
    mart_mun = add_ic95(mart_mun)
    mart_ufm = con.execute("SELECT * FROM mart_uf_mes").df()
    mart_causa = con.execute("SELECT * FROM mart_causa").df()
    mart_exc = con.execute("SELECT * FROM mart_excesso").df()

    if args.medir:
        return

    # Vinha sendo apenas ENVIADA ao banco, nunca exportada: por isso o Parquet
    # dela so podia vir de reexportacao do Postgres. E derivada da constante
    # CID10_CAPITULOS, entao nao depende de nenhuma fonte externa.
    cap_df = pd.DataFrame([(c, n, f"{i}-{f}", d) for c, n, i, f, d in CID10_CAPITULOS],
                          columns=["capitulo", "capitulo_num", "faixa", "descricao"])

    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    exports = {
        "dim_cid10_capitulo": cap_df,
        "dim_municipio": municipios, "dim_populacao": populacao,
        "dim_pop_faixa": pop_faixa, "dim_pop_padrao": pop_padrao,
        "mart_mortalidade_municipio": mart_mun, "mart_mortalidade_uf_mes": mart_ufm,
        "mart_mortalidade_causa": mart_causa, "mart_excesso_uf_mes": mart_exc,
    }
    if cid_cat is not None:
        exports["dim_cid10_categoria"] = cid_cat
    for name, df in exports.items():
        out = escrever_parquet(df, MARTS_DIR / f"{name}.parquet", origem="pipeline",
                               produtor="scripts/pipeline_v2.py")
        print(f"[export] {out.name}: {out.stat().st_size/1e6:.1f} MB")

    if args.no_upload:
        return

    url, key = env.get("SUPABASE_URL"), chave_escrita(env)
    if not url or not key:
        sys.exit("Defina SUPABASE_URL e SUPABASE_ANON_KEY no .env")
    loader = SupabaseLoader(url, key)

    loader.load_df("dim_cid10_capitulo", cap_df)
    loader.load_df("dim_municipio", municipios)
    loader.load_df("dim_populacao", populacao)
    loader.load_df("dim_pop_faixa", pop_faixa)
    loader.load_df("dim_pop_padrao", pop_padrao)
    if cid_cat is not None:
        loader.load_df("dim_cid10_categoria", cid_cat)
    loader.load_df("mart_mortalidade_municipio", mart_mun)
    loader.load_df("mart_mortalidade_uf_mes", mart_ufm)
    loader.load_df("mart_mortalidade_causa", mart_causa)
    loader.load_df("mart_excesso_uf_mes", mart_exc)

    meta = pd.DataFrame([
        ("fonte_obitos", "SIM/DataSUS — microdados abertos (OpenDataSUS 2022+; FTP CID10/DORES 2015–2021)"),
        ("fonte_populacao", "IBGE — Censo 2022 (t/4709, t/9514) e Estimativas (t/6579); 2023 interpolado"),
        ("anos_cobertura", ", ".join(str(a) for a in anos)),
        ("ano_detalhe_completo", f"{ANO_DETALHE}+ (anos anteriores: totais e marginais)"),
        ("exclusoes", "Óbitos fetais ausentes de todos os marts. A exclusão vem da FONTE "
                       "(DOFET é arquivo separado e não é coletado); o filtro TIPOBITO<>1 "
                       "existe como defesa e não remove nenhum registro hoje."),
        ("padronizacao", "Taxa padronizada por idade: método direto, padrão Brasil Censo 2022, 9 faixas; idade ignorada redistribuída pro-rata"),
        ("ic95", "IC95% da taxa bruta: método gamma (Poisson exato)"),
        ("excesso_baseline", f"Esperado = tendência linear por mês civil ajustada a {BASELINE[0]}–{BASELINE[1]} "
                             "(capta crescimento e envelhecimento), projetada para o ano-alvo. "
                             "Excesso = observado − esperado."),
        ("nota_preliminar", "Dados do ano mais recente podem ser preliminares (sujeitos a revisão pelo MS)"),
        ("licenca", "Dados públicos — DATASUS/MS e IBGE; uso livre com citação das fontes"),
        ("gerado_em", datetime.now().isoformat(timespec="seconds")),
        ("pipeline", "scripts/pipeline_v2.py"),
        ("versao_dataset", versao_dataset()),
    ], columns=["chave", "valor"])
    loader.load_df("meta_dataset", meta)
    print("[done] pipeline v2 concluído.")


if __name__ == "__main__":
    main()
