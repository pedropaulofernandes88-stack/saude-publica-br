"""
pipeline_custo_zero.py — Pipeline de publicação a custo zero
=============================================================

Processa microdados REAIS e ABERTOS do SIM (Sistema de Informações sobre
Mortalidade, DataSUS/MS) publicados no OpenDataSUS como CSV nacional, agrega
em marts compactos e carrega no Supabase (free tier) via API REST (PostgREST).

Fontes:
  - SIM/DataSUS  : https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM/DO{AA}OPEN.csv
  - IBGE         : API de localidades (municípios) + SIDRA (população:
                   Censo 2022 t/4709 e Estimativas 2024 t/6579)

Marts gerados (todos agregados — microdados NÃO sobem para o banco):
  - mart_mortalidade_municipio : município × ano × capítulo CID-10 × sexo
  - mart_mortalidade_uf_mes    : UF × mês × capítulo × sexo × faixa etária
  - mart_mortalidade_causa     : UF × ano × causa básica (CID-10 3 chars)

Observações metodológicas:
  - Óbitos fetais (TIPOBITO=1) são EXCLUÍDOS (convenção de mortalidade geral).
  - Faixa etária derivada do campo IDADE do SIM (unidade 4=anos, 5=100+,
    0–3 = menores de 1 ano, 9/ausente = ignorado).
  - LOCOCOR: 1=hospital, 3=domicílio (dicionário oficial SIM).
  - Taxas por 100 mil hab. apenas em linhas sexo=TOTAL (população não é
    desagregada por sexo aqui).
  - População: 2022=Censo, 2024=Estimativas IBGE, 2023=interpolação linear.

Uso:
  python scripts/pipeline_custo_zero.py --anos 2022 2023 2024
  python scripts/pipeline_custo_zero.py --medir            # só mede cardinalidades
  python scripts/pipeline_custo_zero.py --no-upload        # gera CSVs locais apenas

Variáveis de ambiente (ou .env na raiz):
  SUPABASE_URL, SUPABASE_ANON_KEY
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "SIM"
MARTS_DIR = ROOT / "data" / "marts"

S3_SIM = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM"

# Capítulos CID-10 (faixa de categorias de 3 caracteres)
CID10_CAPITULOS = [
    ("I",     1, "A00", "B99", "Algumas doenças infecciosas e parasitárias"),
    ("II",    2, "C00", "D48", "Neoplasias (tumores)"),
    ("III",   3, "D50", "D89", "Doenças do sangue e dos órgãos hematopoéticos e transtornos imunitários"),
    ("IV",    4, "E00", "E90", "Doenças endócrinas, nutricionais e metabólicas"),
    ("V",     5, "F00", "F99", "Transtornos mentais e comportamentais"),
    ("VI",    6, "G00", "G99", "Doenças do sistema nervoso"),
    ("VII",   7, "H00", "H59", "Doenças do olho e anexos"),
    ("VIII",  8, "H60", "H95", "Doenças do ouvido e da apófise mastóide"),
    ("IX",    9, "I00", "I99", "Doenças do aparelho circulatório"),
    ("X",    10, "J00", "J99", "Doenças do aparelho respiratório"),
    ("XI",   11, "K00", "K93", "Doenças do aparelho digestivo"),
    ("XII",  12, "L00", "L99", "Doenças da pele e do tecido subcutâneo"),
    ("XIII", 13, "M00", "M99", "Doenças do sistema osteomuscular e do tecido conjuntivo"),
    ("XIV",  14, "N00", "N99", "Doenças do aparelho geniturinário"),
    ("XV",   15, "O00", "O99", "Gravidez, parto e puerpério"),
    ("XVI",  16, "P00", "P96", "Algumas afecções originadas no período perinatal"),
    ("XVII", 17, "Q00", "Q99", "Malformações congênitas, deformidades e anomalias cromossômicas"),
    ("XVIII",18, "R00", "R99", "Sintomas, sinais e achados anormais não classificados em outra parte"),
    ("XIX",  19, "S00", "T98", "Lesões, envenenamento e algumas outras consequências de causas externas"),
    ("XX",   20, "V01", "Y98", "Causas externas de morbidade e de mortalidade"),
    ("XXI",  21, "Z00", "Z99", "Fatores que influenciam o estado de saúde e o contato com os serviços de saúde"),
    ("XXII", 22, "U00", "U99", "Códigos para propósitos especiais (inclui COVID-19: U07)"),
]


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
def load_env() -> dict[str, str]:
    """Lê .env simples da raiz (KEY=VALUE) sem dependências externas."""
    env: dict[str, str] = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})
    return env


# ---------------------------------------------------------------------------
# Download SIM (OpenDataSUS)
# ---------------------------------------------------------------------------
def download_sim(anos: list[int]) -> list[Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for ano in anos:
        yy = str(ano)[2:]
        dest = RAW_DIR / f"DO{yy}OPEN.csv"
        if dest.exists() and dest.stat().st_size > 1_000_000:
            print(f"[cache] {dest.name} ({dest.stat().st_size/1e6:.0f} MB)")
        else:
            url = f"{S3_SIM}/DO{yy}OPEN.csv"
            print(f"[download] {url}")
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            print(f"[ok] {dest.name} ({dest.stat().st_size/1e6:.0f} MB)")
        paths.append(dest)
    return paths


# ---------------------------------------------------------------------------
# Referências IBGE
# ---------------------------------------------------------------------------
def fetch_municipios() -> pd.DataFrame:
    """Municípios IBGE com UF e região (API de localidades)."""
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(
        {
            "municipio_cod7": [str(x["municipio-id"]) for x in rows],
            "municipio_nome": [x["municipio-nome"] for x in rows],
            "uf_sigla": [x["UF-sigla"] for x in rows],
            "uf_nome": [x["UF-nome"] for x in rows],
            "regiao": [x["regiao-nome"] for x in rows],
        }
    )
    df["municipio_cod"] = df["municipio_cod7"].str[:6]
    return df[["municipio_cod", "municipio_cod7", "municipio_nome", "uf_sigla", "uf_nome", "regiao"]]


def _sidra(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data[1:])  # primeira linha = cabeçalho
    df = df[["D1C", "V"]].rename(columns={"D1C": "municipio_cod7", "V": "populacao"})
    df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce")
    df = df.dropna(subset=["populacao"])
    df["municipio_cod"] = df["municipio_cod7"].astype(str).str[:6]
    df["populacao"] = df["populacao"].astype(int)
    return df[["municipio_cod", "populacao"]]


def fetch_populacao(anos: list[int]) -> pd.DataFrame:
    """População municipal: Censo 2022 + Estimativas 2024; 2023 interpolado."""
    print("[ibge] população — Censo 2022 (SIDRA t/4709)...")
    pop22 = _sidra("https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022")
    print(f"[ibge]   {len(pop22):,} municípios (Censo 2022)")

    pop24 = None
    try:
        print("[ibge] população — Estimativas 2024 (SIDRA t/6579)...")
        pop24 = _sidra("https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2024")
        print(f"[ibge]   {len(pop24):,} municípios (Estimativas 2024)")
    except Exception as exc:
        print(f"[ibge]   estimativas 2024 indisponíveis ({exc}); usando Censo 2022")

    frames = []
    for ano in anos:
        if ano <= 2022 or pop24 is None:
            df = pop22.copy()
            df["fonte"] = "IBGE Censo 2022"
        elif ano >= 2024:
            df = pop24.copy()
            df["fonte"] = "IBGE Estimativas 2024"
        else:  # 2023: interpolação linear entre Censo 2022 e Estimativas 2024
            m = pop22.merge(pop24, on="municipio_cod", suffixes=("_22", "_24"), how="inner")
            m["populacao"] = ((m["populacao_22"] + m["populacao_24"]) / 2).round().astype(int)
            df = m[["municipio_cod", "populacao"]].copy()
            df["fonte"] = "Interpolação Censo 2022 / Estimativas 2024"
        df["ano"] = ano
        frames.append(df)
    return pd.concat(frames, ignore_index=True)[["municipio_cod", "ano", "populacao", "fonte"]]


# ---------------------------------------------------------------------------
# Transformação DuckDB
# ---------------------------------------------------------------------------
def build_marts(con: duckdb.DuckDBPyConnection, anos: list[int]) -> None:
    files = [str(RAW_DIR / f"DO{str(a)[2:]}OPEN.csv") for a in anos]
    file_list = ", ".join(f"'{f}'" for f in files)

    # Tabela de capítulos para classificação por faixa de código
    con.execute("CREATE OR REPLACE TABLE cid10_cap (capitulo TEXT, capitulo_num SMALLINT, ini TEXT, fim TEXT, descricao TEXT)")
    con.executemany("INSERT INTO cid10_cap VALUES (?, ?, ?, ?, ?)", CID10_CAPITULOS)

    print("[duckdb] lendo microdados SIM (CSV ; ) e derivando colunas...")
    con.execute(f"""
        CREATE OR REPLACE VIEW obitos AS
        WITH raw AS (
            SELECT
                TIPOBITO, DTOBITO, IDADE, SEXO, CODMUNRES, LOCOCOR, CAUSABAS
            FROM read_csv([{file_list}], delim=';', header=true, quote='"',
                          all_varchar=true, union_by_name=true)
        ),
        t AS (
            SELECT
                lpad(DTOBITO, 8, '0')                          AS dt,
                COALESCE(NULLIF(trim(CODMUNRES), ''), '000000') AS municipio_cod,
                upper(COALESCE(trim(CAUSABAS), ''))             AS causabas,
                trim(COALESCE(SEXO, ''))                        AS sexo_raw,
                trim(COALESCE(LOCOCOR, ''))                     AS lococor,
                trim(COALESCE(IDADE, ''))                       AS idade_raw
            FROM raw
            WHERE COALESCE(TIPOBITO, '2') <> '1'   -- exclui óbitos fetais
        ),
        d AS (
            SELECT
                TRY_CAST(substr(dt, 5, 4) AS SMALLINT)  AS ano,
                TRY_CAST(substr(dt, 3, 2) AS SMALLINT)  AS mes,
                municipio_cod,
                substr(causabas, 1, 3)                  AS causabas_3,
                CASE sexo_raw WHEN '1' THEN 'M' WHEN '2' THEN 'F'
                              WHEN 'M' THEN 'M' WHEN 'F' THEN 'F'
                              ELSE 'I' END              AS sexo,
                lococor,
                -- idade em anos a partir do campo IDADE do SIM
                CASE
                    WHEN idade_raw = '' OR idade_raw IS NULL THEN NULL
                    WHEN substr(lpad(idade_raw, 3, '0'), 1, 1) = '4'
                        THEN TRY_CAST(substr(lpad(idade_raw, 3, '0'), 2, 2) AS INT)
                    WHEN substr(lpad(idade_raw, 3, '0'), 1, 1) = '5'
                        THEN 100 + COALESCE(TRY_CAST(substr(lpad(idade_raw, 3, '0'), 2, 2) AS INT), 0)
                    WHEN substr(lpad(idade_raw, 3, '0'), 1, 1) IN ('0','1','2','3') THEN 0
                    ELSE NULL
                END                                     AS idade_anos
            FROM t
        )
        SELECT
            d.ano, d.mes,
            make_date(d.ano, d.mes, 1)                  AS mes_competencia,
            d.municipio_cod,
            d.causabas_3,
            COALESCE(c.capitulo, 'N/D')                 AS capitulo_cid,
            d.sexo,
            CASE
                WHEN d.idade_anos IS NULL THEN 'IGN'
                WHEN d.idade_anos < 1   THEN '<1'
                WHEN d.idade_anos <= 4  THEN '1-4'
                WHEN d.idade_anos <= 14 THEN '5-14'
                WHEN d.idade_anos <= 29 THEN '15-29'
                WHEN d.idade_anos <= 44 THEN '30-44'
                WHEN d.idade_anos <= 59 THEN '45-59'
                WHEN d.idade_anos <= 74 THEN '60-74'
                ELSE '75+'
            END                                         AS faixa_etaria,
            (d.lococor = '1')                           AS is_hospital,
            (d.lococor = '3')                           AS is_domicilio
        FROM d
        LEFT JOIN cid10_cap c
          ON d.causabas_3 >= c.ini AND d.causabas_3 <= c.fim
        WHERE d.ano IN ({', '.join(str(a) for a in anos)})
          AND d.mes BETWEEN 1 AND 12
    """)

    print("[duckdb] materializando base de óbitos...")
    con.execute("CREATE OR REPLACE TABLE obitos_t AS SELECT * FROM obitos")
    total = con.execute("SELECT count(*) FROM obitos_t").fetchone()[0]
    print(f"[duckdb] óbitos (não fetais) processados: {total:,}")

    # dim_municipio em DuckDB para enriquecer marts
    print("[duckdb] mart_mortalidade_municipio...")
    con.execute("""
        CREATE OR REPLACE TABLE mart_municipio AS
        SELECT
            o.municipio_cod,
            m.municipio_nome,
            COALESCE(m.uf_sigla, 'ND')                              AS uf_sigla,
            m.regiao,
            o.ano,
            COALESCE(CASE WHEN GROUPING(o.capitulo_cid) = 1 THEN 'TOTAL' ELSE o.capitulo_cid END, 'TOTAL') AS capitulo_cid,
            COALESCE(CASE WHEN GROUPING(o.sexo) = 1 THEN 'TOTAL' ELSE o.sexo END, 'TOTAL')                 AS sexo,
            count(*)::INT                                           AS obitos,
            sum(CASE WHEN o.is_hospital THEN 1 ELSE 0 END)::INT     AS obitos_hospital,
            sum(CASE WHEN o.is_domicilio THEN 1 ELSE 0 END)::INT    AS obitos_domicilio
        FROM obitos_t o
        LEFT JOIN dim_municipio m USING (municipio_cod)
        GROUP BY GROUPING SETS (
            (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano, o.capitulo_cid, o.sexo),
            (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano, o.capitulo_cid),
            (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano, o.sexo),
            (o.municipio_cod, m.municipio_nome, m.uf_sigla, m.regiao, o.ano)
        )
    """)

    # População + taxa apenas nas linhas sexo=TOTAL
    con.execute("""
        CREATE OR REPLACE TABLE mart_municipio_final AS
        SELECT
            mm.*,
            CASE WHEN mm.sexo = 'TOTAL' THEN p.populacao END                       AS populacao,
            CASE WHEN mm.sexo = 'TOTAL' AND COALESCE(p.populacao, 0) > 0
                 THEN round(mm.obitos * 100000.0 / p.populacao, 2) END             AS taxa_obitos_100k
        FROM mart_municipio mm
        LEFT JOIN dim_populacao p
          ON p.municipio_cod = mm.municipio_cod AND p.ano = mm.ano
    """)

    print("[duckdb] mart_mortalidade_uf_mes...")
    con.execute("""
        CREATE OR REPLACE TABLE mart_uf_mes AS
        SELECT
            COALESCE(m.uf_sigla, 'ND')                                              AS uf_sigla,
            any_value(m.regiao)                                                     AS regiao,
            o.ano, o.mes, o.mes_competencia,
            COALESCE(CASE WHEN GROUPING(o.capitulo_cid) = 1 THEN 'TOTAL' ELSE o.capitulo_cid END, 'TOTAL') AS capitulo_cid,
            COALESCE(CASE WHEN GROUPING(o.sexo) = 1 THEN 'TOTAL' ELSE o.sexo END, 'TOTAL')                 AS sexo,
            COALESCE(CASE WHEN GROUPING(o.faixa_etaria) = 1 THEN 'TOTAL' ELSE o.faixa_etaria END, 'TOTAL') AS faixa_etaria,
            count(*)::INT                                                           AS obitos
        FROM obitos_t o
        LEFT JOIN dim_municipio m USING (municipio_cod)
        GROUP BY GROUPING SETS (
            (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid, o.sexo, o.faixa_etaria),
            (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid, o.sexo),
            (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid, o.faixa_etaria),
            (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.sexo, o.faixa_etaria),
            (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.capitulo_cid),
            (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.sexo),
            (m.uf_sigla, o.ano, o.mes, o.mes_competencia, o.faixa_etaria),
            (m.uf_sigla, o.ano, o.mes, o.mes_competencia)
        )
    """)

    print("[duckdb] mart_mortalidade_causa...")
    con.execute("""
        CREATE OR REPLACE TABLE mart_causa AS
        SELECT
            o.ano,
            COALESCE(m.uf_sigla, 'ND')   AS uf_sigla,
            o.causabas_3,
            any_value(o.capitulo_cid)    AS capitulo_cid,
            count(*)::INT                AS obitos
        FROM obitos_t o
        LEFT JOIN dim_municipio m USING (municipio_cod)
        WHERE o.causabas_3 <> ''
        GROUP BY o.ano, m.uf_sigla, o.causabas_3
    """)

    for t in ("mart_municipio_final", "mart_uf_mes", "mart_causa"):
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"[duckdb]   {t}: {n:,} linhas")


# ---------------------------------------------------------------------------
# Upload Supabase (PostgREST)
# ---------------------------------------------------------------------------
class SupabaseLoader:
    def __init__(self, url: str, anon_key: str, batch_rows: int = 20_000):
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
            # merge-duplicates = upsert pela PK (re-runs idempotentes)
            "Prefer": "return=minimal,resolution=merge-duplicates",
        }
        self.batch_rows = batch_rows

    def load_df(self, table: str, df: pd.DataFrame) -> None:
        # NaN/NaT → None; datas → ISO
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
        # astype(object) antes do where: em colunas float, None viraria NaN
        records = df.astype(object).where(pd.notna(df), other=None).to_dict(orient="records")
        # Converte tipos numpy → python nativos
        n_batches = math.ceil(len(records) / self.batch_rows)
        sent = 0
        for i in range(n_batches):
            batch = records[i * self.batch_rows : (i + 1) * self.batch_rows]
            body = json.dumps(batch, default=_json_default, allow_nan=False)
            for attempt in range(4):
                resp = requests.post(
                    f"{self.url}/rest/v1/{table}", headers=self.headers,
                    data=body, timeout=300,
                )
                if resp.status_code in (200, 201):
                    break
                if attempt == 3 or resp.status_code in (400, 401, 403, 404, 409):
                    raise RuntimeError(f"upload {table} lote {i+1}/{n_batches}: HTTP {resp.status_code} — {resp.text[:300]}")
                time.sleep(3 * (attempt + 1))
            sent += len(batch)
            print(f"[supabase]   {table}: {sent:,}/{len(records):,}", end="\r")
        print(f"[supabase]   {table}: {len(records):,} linhas OK          ")


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(f"não serializável: {type(o)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description="Pipeline custo zero — SIM/DataSUS → Supabase")
    p.add_argument("--anos", nargs="+", type=int, default=[2022, 2023, 2024])
    p.add_argument("--medir", action="store_true", help="só mede cardinalidades, sem upload")
    p.add_argument("--no-upload", action="store_true", help="gera marts locais sem subir")
    args = p.parse_args()

    env = load_env()
    anos = sorted(args.anos)

    download_sim(anos)

    print("[ibge] municípios...")
    municipios = fetch_municipios()
    print(f"[ibge]   {len(municipios):,} municípios")
    populacao = fetch_populacao(anos)

    con = duckdb.connect()  # in-memory
    con.register("municipios_df", municipios)
    con.execute("CREATE OR REPLACE TABLE dim_municipio AS SELECT * FROM municipios_df")
    con.register("populacao_df", populacao)
    con.execute("CREATE OR REPLACE TABLE dim_populacao AS SELECT * FROM populacao_df")

    build_marts(con, anos)

    if args.medir:
        return

    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    exports = {
        "dim_municipio": "SELECT * FROM dim_municipio",
        "dim_populacao": "SELECT * FROM dim_populacao",
        "mart_mortalidade_municipio": "SELECT * FROM mart_municipio_final",
        "mart_mortalidade_uf_mes": "SELECT * FROM mart_uf_mes",
        "mart_mortalidade_causa": "SELECT * FROM mart_causa",
    }
    for name, sql in exports.items():
        out = MARTS_DIR / f"{name}.parquet"
        con.execute(f"COPY ({sql}) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        print(f"[export] {out.name}: {out.stat().st_size/1e6:.1f} MB")

    if args.no_upload:
        return

    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_ANON_KEY")
    if not url or not key:
        sys.exit("Defina SUPABASE_URL e SUPABASE_ANON_KEY no .env")

    loader = SupabaseLoader(url, key)

    print("[supabase] dim_cid10_capitulo...")
    cid_df = pd.DataFrame(
        [(c, n, f"{i}-{f}", d) for c, n, i, f, d in CID10_CAPITULOS],
        columns=["capitulo", "capitulo_num", "faixa", "descricao"],
    )
    loader.load_df("dim_cid10_capitulo", cid_df)
    loader.load_df("dim_municipio", municipios)
    loader.load_df("dim_populacao", populacao)
    loader.load_df("mart_mortalidade_municipio", con.execute("SELECT * FROM mart_municipio_final").df())
    loader.load_df("mart_mortalidade_uf_mes", con.execute("SELECT * FROM mart_uf_mes").df())
    loader.load_df("mart_mortalidade_causa", con.execute("SELECT * FROM mart_causa").df())

    meta = pd.DataFrame(
        [
            ("fonte_obitos", "SIM — Sistema de Informações sobre Mortalidade (DataSUS/Ministério da Saúde), microdados abertos OpenDataSUS"),
            ("fonte_populacao", "IBGE — Censo 2022 (SIDRA t/4709) e Estimativas 2024 (SIDRA t/6579); 2023 por interpolação linear"),
            ("anos_cobertura", ", ".join(str(a) for a in anos)),
            ("exclusoes", "Óbitos fetais (TIPOBITO=1) excluídos de todos os marts"),
            ("nota_preliminar", "Dados do ano mais recente podem ser preliminares (sujeitos a revisão pelo MS)"),
            ("licenca", "Dados públicos — DATASUS/MS e IBGE; uso livre com citação das fontes"),
            ("gerado_em", datetime.now().isoformat(timespec="seconds")),
            ("pipeline", "scripts/pipeline_custo_zero.py — github: saude-publica-br"),
        ],
        columns=["chave", "valor"],
    )
    loader.load_df("meta_dataset", meta)
    print("[done] pipeline concluído.")


if __name__ == "__main__":
    main()
