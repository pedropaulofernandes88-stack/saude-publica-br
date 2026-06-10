"""
bulk_load.py
Utilitários de carregamento em massa: DataFrame → Parquet local → Supabase (COPY).
Estratégia: 10× mais rápido que INSERT row-by-row (validado no artigo PoC, R²=0.996).
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import psycopg
from loguru import logger


PARQUET_DIR = Path(os.getenv("PARQUET_DIR", "./data/parquet"))
DATABASE_URL = os.getenv("DATABASE_URL", "")


# ---------------------------------------------------------------------------
# Schemas Parquet por tabela
# ---------------------------------------------------------------------------

SIA_PA_SCHEMA = pa.schema([
    ("mes_competencia",       pa.string()),
    ("ano_competencia",       pa.int16()),
    ("mes_num",               pa.int8()),
    ("municipio_cod",         pa.string()),
    ("proc_id",               pa.string()),
    ("cid_primario",          pa.string()),
    ("qtd_aprovada",          pa.int32()),
    ("valor_aprovado",        pa.float64()),
    ("tipo_financiamento",    pa.string()),
    ("categoria_atendimento", pa.string()),
    ("sexo",                  pa.string()),
    ("faixa_etaria",          pa.int16()),
    ("uf_sigla",              pa.string()),  # coluna derivada do arquivo
])

SIM_DO_SCHEMA = pa.schema([
    # Identificação
    ("numerodo",        pa.string()),
    ("tipobito",        pa.string()),
    # Temporal
    ("dtobito",         pa.string()),    # DDMMAAAA
    ("ano_obito",       pa.int16()),
    ("mes_obito",       pa.int16()),
    # Causa básica
    ("causabas",        pa.string()),
    ("causabas_cap",    pa.string()),
    # Localização ocorrência
    ("municipio_ocor",  pa.string()),
    ("uf_ocor",         pa.string()),
    # Localização residência
    ("municipio_res",   pa.string()),
    ("uf_res",          pa.string()),
    # Características do falecido
    ("sexo",            pa.string()),
    ("idade_valor",     pa.int16()),
    ("idade_unidade",   pa.string()),    # A/M/D/H
    ("racacor",         pa.string()),
    ("escolaridade",    pa.string()),
    ("estadociv",       pa.string()),
    # Local e tipo de óbito
    ("lococor",         pa.string()),
    ("assistmed",       pa.string()),
    # Metadados
    ("uf_arquivo",      pa.string()),
])

SIH_AIH_SCHEMA = pa.schema([
    # Identificação
    ("n_aih",           pa.string()),
    ("ident",           pa.string()),
    # Temporal
    ("dt_inter",        pa.string()),    # AAAMMDD
    ("dt_saida",        pa.string()),    # AAAMMDD
    ("ano_cmpt",        pa.int16()),
    ("mes_cmpt",        pa.int16()),
    ("dias_perm",       pa.int16()),
    # Diagnóstico
    ("diag_princ",      pa.string()),
    ("diag_secun",      pa.string()),
    ("diag_cap",        pa.string()),
    # Procedimento
    ("proc_rea",        pa.string()),
    ("proc_sol",        pa.string()),
    # Localização ocorrência
    ("cnes",            pa.string()),
    ("municipio_ocor",  pa.string()),
    ("uf_ocor",         pa.string()),
    # Localização residência
    ("municipio_res",   pa.string()),
    ("uf_res",          pa.string()),
    # Características
    ("sexo",            pa.string()),
    ("idade",           pa.int16()),
    ("nasc",            pa.string()),
    ("raca_cor",        pa.string()),
    # Desfecho
    ("morte",           pa.int16()),
    ("cobranca",        pa.string()),
    # Valores (float64 para evitar overflow em grandes somas)
    ("val_tot",         pa.float64()),
    ("val_sh",          pa.float64()),
    ("val_sp",          pa.float64()),
    ("val_sadt",        pa.float64()),
    ("val_uci",         pa.float64()),
    # Gestão
    ("gestor_cod",      pa.string()),
    ("instru",          pa.string()),
    ("car_int",         pa.string()),
    # Metadados
    ("uf_arquivo",      pa.string()),
])

# SINAN — notificações de agravos (dengue / chikungunya / zika)
SINAN_SCHEMA = pa.schema([
    # Identificação
    ("nu_notific",      pa.string()),
    ("agravo",          pa.string()),   # DENG | CHIK | ZIKA
    ("dt_notific",      pa.string()),   # AAAAMMDD
    ("ano_notif",       pa.int16()),
    ("mes_notif",       pa.int16()),
    # Localização de notificação
    ("uf_notif",        pa.string()),
    ("municipio_notif", pa.string()),
    ("cnes_unidade",    pa.string()),
    # Localização de residência
    ("uf_res",          pa.string()),
    ("municipio_res",   pa.string()),
    # Dados do paciente
    ("dt_sin_pri",      pa.string()),   # data primeiros sintomas
    ("dt_nasc",         pa.string()),
    ("nu_idade_n",      pa.int16()),    # idade codificada DataSUS
    ("idade_anos",      pa.int16()),    # calculada no ingestor
    ("cs_sexo",         pa.string()),   # M | F | I
    ("cs_raca",         pa.int16()),
    ("cs_gestant",      pa.int16()),
    # Classificação e desfecho
    ("classi_fin",      pa.int16()),
    ("criterio",        pa.int16()),
    ("evolucao",        pa.int16()),
    ("dt_obito",        pa.string()),
    ("dt_encerra",      pa.string()),
    # Manifestações clínicas
    ("febre",           pa.int16()),
    ("mialgia",         pa.int16()),
    ("cefaleia",        pa.int16()),
    ("exantema",        pa.int16()),
    ("vomito",          pa.int16()),
    ("artralgia",       pa.int16()),
    ("artrite",         pa.int16()),
    # Exames laboratoriais
    ("sorotipo",        pa.int16()),
    ("resul_ns1",       pa.int16()),
    ("resul_prnt",      pa.int16()),
    ("resul_soro",      pa.int16()),
    ("resul_pcr",       pa.int16()),
    ("dt_soro",         pa.string()),
    ("dt_pcr",          pa.string()),
    # Metadados
    ("uf_arquivo",      pa.string()),
])

# CNES — estabelecimentos de saúde (grupo ST)
CNES_ESTAB_SCHEMA = pa.schema([
    # Identificação
    ("cnes",                pa.string()),
    ("ano_cmpt",            pa.int16()),
    ("mes_cmpt",            pa.int16()),
    ("uf",                  pa.string()),
    # Localização
    ("municipio_cod",       pa.string()),
    ("municipio_nome",      pa.string()),
    ("cep",                 pa.string()),
    ("tp_unid",             pa.string()),
    ("tp_unid_desc",        pa.string()),
    # Identificação do prestador
    ("cnpj_mantenedora",    pa.string()),
    ("pf_pj",               pa.string()),
    ("tp_prest",            pa.string()),
    # Esfera administrativa
    ("esfera_adm",          pa.string()),
    ("ret_obrig",           pa.string()),
    # Natureza jurídica
    ("nat_jur",             pa.string()),
    # Nível de atenção
    ("nivel_dep",           pa.string()),
    ("tp_gestao",           pa.string()),
    # Capacidades (int16 — nunca ultrapassa 32767 leitos por unidade)
    ("qt_leitos_sus",       pa.int16()),
    ("qt_leitos_nao_sus",   pa.int16()),
    ("qt_amb_sus",          pa.int16()),
    ("qt_amb_nao_sus",      pa.int16()),
    ("qt_cons_sus",         pa.int16()),
    # Serviços especializados (flags 0/1)
    ("serv_uti",            pa.int16()),
    ("serv_emer",           pa.int16()),
    ("serv_cirg",           pa.int16()),
    ("serv_obstet",         pa.int16()),
    ("serv_hemot",          pa.int16()),
    ("serv_diag",           pa.int16()),
    # Vínculo SUS
    ("vinc_sus",            pa.string()),   # S | N
    # Metadados
    ("uf_arquivo",          pa.string()),
])

# CNES — leitos por estabelecimento e tipo (grupo LT)
CNES_LEITOS_SCHEMA = pa.schema([
    # Identificação
    ("cnes",            pa.string()),
    ("ano_cmpt",        pa.int16()),
    ("mes_cmpt",        pa.int16()),
    ("uf",              pa.string()),
    # Localização
    ("municipio_cod",   pa.string()),
    # Tipo de leito
    ("tp_leito",        pa.string()),
    ("tp_leito_desc",   pa.string()),
    # Especialidade
    ("cod_espec",       pa.string()),
    ("cod_espec_desc",  pa.string()),
    # Quantidades
    ("qt_exist",        pa.int16()),
    ("qt_sus",          pa.int16()),
    ("qt_nao_sus",      pa.int16()),
    ("qt_contr",        pa.int16()),
    # Metadados
    ("uf_arquivo",      pa.string()),
])


# ---------------------------------------------------------------------------
# Parquet
# ---------------------------------------------------------------------------

def df_to_parquet(
    df: pd.DataFrame,
    uf: str,
    ano: int,
    mes: int,
    schema: Optional[pa.Schema] = None,
    base_dir: Optional[Path] = None,
    table_name: str = "sia_pa",
) -> Path:
    """
    Salva DataFrame como Parquet particionado por UF/ano/mês.
    
    Estrutura: data/parquet/sia_pa/uf=SP/ano=2023/mes=06/data.parquet
    Permite queries DuckDB por partição sem ler todo o dataset.
    """
    base = base_dir or (PARQUET_DIR / table_name)
    partition_path = base / f"uf={uf.upper()}" / f"ano={ano}" / f"mes={mes:02d}"
    partition_path.mkdir(parents=True, exist_ok=True)
    output_file = partition_path / "data.parquet"

    table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)

    pq.write_table(
        table,
        output_file,
        compression="snappy",       # Melhor equilíbrio velocidade/tamanho
        row_group_size=100_000,     # Otimizado para leitura colunar
    )

    size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"  Parquet salvo: {output_file} ({size_mb:.2f} MB, {len(df):,} linhas)")
    return output_file


# ---------------------------------------------------------------------------
# Supabase — COPY via psycopg3
# ---------------------------------------------------------------------------

def parquet_to_supabase(
    parquet_path: Path,
    table_name: str,
    columns: list[str],
    database_url: Optional[str] = None,
    batch_size: int = 100_000,
) -> int:
    """
    Carrega arquivo Parquet no Supabase usando COPY (bulk load).
    
    Muito mais eficiente que INSERT row-by-row para grandes volumes.
    A PoC validou 3.2M registros com esta estratégia (R²=0.996).
    
    Returns:
        int: número de registros carregados
    """
    db_url = database_url or DATABASE_URL
    if not db_url:
        raise ValueError("DATABASE_URL não configurado")

    df = pd.read_parquet(parquet_path, columns=columns)
    total = len(df)
    
    if total == 0:
        logger.warning(f"  Parquet vazio: {parquet_path}")
        return 0

    logger.info(f"  COPY → {table_name}: {total:,} registros de {parquet_path.name}")
    t0 = time.perf_counter()

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            col_str = ", ".join(columns)
            
            # Processa em batches para não estourar memória
            loaded = 0
            for i in range(0, total, batch_size):
                batch = df.iloc[i : i + batch_size]
                
                buffer = io.StringIO()
                batch.to_csv(buffer, index=False, header=False, sep="\t",
                             na_rep="\\N")  # \N = NULL no PostgreSQL COPY
                buffer.seek(0)
                
                with cur.copy(
                    f"COPY {table_name} ({col_str}) FROM STDIN "
                    f"WITH (FORMAT CSV, DELIMITER '\t', NULL '\\N')"
                ) as copy:
                    copy.write(buffer.read())
                
                loaded += len(batch)
                logger.debug(f"    Batch {i // batch_size + 1}: {loaded:,}/{total:,}")
            
            conn.commit()

    elapsed = time.perf_counter() - t0
    rate = total / elapsed if elapsed > 0 else 0
    logger.info(f"  ✓ {total:,} registros em {elapsed:.1f}s ({rate:,.0f} rec/s)")
    return total


def df_to_supabase_bulk(
    df: pd.DataFrame,
    uf: str,
    ano: int,
    mes: int,
    table_name: str,
    columns: list[str],
    schema: Optional[pa.Schema] = None,
    database_url: Optional[str] = None,
    keep_parquet: bool = True,
) -> tuple[Path, int]:
    """
    Pipeline completo: DataFrame → Parquet → Supabase.
    
    Returns:
        tuple[Path, int]: caminho do Parquet e qtd de registros carregados
    """
    # 1. Salva Parquet local (para DuckDB queries e backup)
    parquet_path = df_to_parquet(df, uf, ano, mes, schema, table_name=table_name)
    
    # 2. Carrega no Supabase via COPY
    try:
        loaded = parquet_to_supabase(parquet_path, table_name, columns, database_url)
    except Exception as e:
        logger.error(f"  Erro no COPY para Supabase: {e}")
        if not keep_parquet:
            parquet_path.unlink(missing_ok=True)
        raise

    return parquet_path, loaded
