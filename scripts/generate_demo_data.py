#!/usr/bin/env python3
"""
generate_demo_data.py — Gera dados sintéticos para desenvolvimento e testes.

Cria arquivos Parquet compatíveis com o schema do pipeline saude-publica-br,
sem necessidade de acesso ao DataSUS.

Uso:
    python scripts/generate_demo_data.py
    python scripts/generate_demo_data.py --estados SP RJ --anos 2023 2024 --registros 5000

Saída:
    data/demo/parquet/sia_pa/estado=SP/ano=2023/sia_pa_SP_2023.parquet
    data/demo/parquet/sim_do/...
    data/demo/parquet/sih_aih/...
    data/demo/parquet/sinan/...
    data/demo/parquet/cnes/...
"""
from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_demo_data")

# ---------------------------------------------------------------------------
# Constantes de domínio
# ---------------------------------------------------------------------------

ESTADOS = ["SP", "RJ", "MG", "BA", "RS", "PR", "PE", "CE", "GO", "SC"]
MUNICIPIOS = {
    "SP": ["355030", "350950", "354340", "354870", "353440"],  # São Paulo, Campinas, Ribeirão Preto, Santo André, Santos
    "RJ": ["330455", "330170", "330227", "330045", "330100"],  # Rio, Nova Iguaçu, Duque de Caxias, Belford Roxo, Campos
    "MG": ["310620", "311860", "313670", "314330", "317220"],  # BH, Betim, Contagem, Juiz de Fora, Uberlândia
    "BA": ["292740", "291340", "291080", "290570", "293290"],  # Salvador, Feira, Camaçari, Barreiras, Vitória da Conquista
    "RS": ["431490", "430510", "430300", "430260", "431220"],  # Porto Alegre, Caxias, Canoas, Cachoeirinha, Pelotas
    "PR": ["410690", "410840", "411820", "410430", "410520"],  # Curitiba, Cascavel, Londrina, Araucária, Campo Mourão
    "PE": ["261160", "260790", "260005", "260545", "261070"],  # Recife, Jaboatão, Caruaru, Gravatá, Olinda
    "CE": ["230440", "230670", "230940", "231270", "230390"],  # Fortaleza, Caucaia, Juazeiro, Sobral, Canindé
    "GO": ["520870", "520140", "521190", "520760", "521250"],  # Goiânia, Anápolis, Rio Verde, Luziânia, Senador Canedo
    "SC": ["420540", "420380", "421730", "421120", "420455"],  # Florianópolis, Blumenau, São José, Joinville, Criciúma
}

CID10_CAUSAS = {
    "J18": "Pneumonia",
    "I21": "Infarto agudo do miocárdio",
    "J44": "DPOC",
    "K92": "Hemorragia gastrointestinal",
    "N18": "Insuficiência renal crônica",
    "A90": "Dengue",
    "A15": "Tuberculose respiratória",
    "C34": "Neoplasia maligna de brônquios e pulmões",
    "I64": "AVC não especificado",
    "E11": "Diabetes mellitus tipo 2",
    "B54": "Malária não especificada",
    "J06": "Infecções agudas das vias respiratórias superiores",
}

PROCEDIMENTOS = {
    "0301010072": "Consulta médica em atenção básica",
    "0301010110": "Consulta médica em atenção especializada",
    "0204030030": "Hemograma completo",
    "0202010473": "Dosagem de glicose",
    "0101010010": "Ação educativa coletiva",
    "0303040070": "Hemodiálise",
    "0401010034": "Parto normal",
    "0405020055": "Colecistectomia",
    "0402050055": "Cateterismo cardíaco",
    "0301060096": "Consulta de urgência",
}

COMPLEXIDADES = {
    "AB": "Atenção Básica",
    "MC": "Média Complexidade",
    "AC": "Alta Complexidade",
}

ANOS = [2020, 2021, 2022, 2023, 2024]
COMPETENCIAS = [f"{m:02d}" for m in range(1, 13)]

SEED = 42
rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------------------
# Geradores de tabelas
# ---------------------------------------------------------------------------


def gerar_sia_pa(estado: str, ano: int, n: int) -> pd.DataFrame:
    """Produção ambulatorial sintética (SIA/PA)."""
    municipios = MUNICIPIOS.get(estado, ["000000"] * 5)
    procedimentos = list(PROCEDIMENTOS.keys())
    complexidades = list(COMPLEXIDADES.keys())
    competencias = COMPETENCIAS

    records = {
        "uf_sigla": estado,
        "municipio_codigo": rng.choice(municipios, n),
        "competencia_ano": ano,
        "competencia_mes": rng.choice(competencias, n),
        "procedimento_codigo": rng.choice(procedimentos, n),
        "complexidade": rng.choice(complexidades, n, p=[0.50, 0.35, 0.15]),
        "quantidade_aprovada": rng.integers(1, 500, n),
        "valor_aprovado": rng.uniform(5.0, 2500.0, n).round(2),
        "cns_pac": [f"{rng.integers(100000000000, 999999999999)}" for _ in range(n)],
        "dt_atendimento": pd.to_datetime(
            [f"{ano}-{rng.integers(1, 13):02d}-{rng.integers(1, 28):02d}" for _ in range(n)]
        ),
    }
    df = pd.DataFrame(records)
    df["valor_aprovado"] = df["valor_aprovado"].astype(float)
    return df


def gerar_sim_do(estado: str, ano: int, n: int) -> pd.DataFrame:
    """Declarações de óbito sintéticas (SIM/DO)."""
    municipios = MUNICIPIOS.get(estado, ["000000"] * 5)
    causas = list(CID10_CAUSAS.keys())

    records = {
        "uf_sigla": estado,
        "municipio_codigo_ocorrencia": rng.choice(municipios, n),
        "municipio_codigo_residencia": rng.choice(municipios, n),
        "ano_obito": ano,
        "mes_obito": rng.integers(1, 13, n),
        "causa_basica_cid10": rng.choice(causas, n),
        "idade": rng.integers(0, 100, n),
        "sexo": rng.choice(["M", "F", "I"], n, p=[0.50, 0.49, 0.01]),
        "raca_cor": rng.choice(["1", "2", "3", "4", "5"], n, p=[0.47, 0.08, 0.43, 0.01, 0.01]),
        "escolaridade": rng.choice(["1", "2", "3", "4", "5"], n),
        "local_ocorrencia": rng.choice(["1", "2", "3", "4"], n, p=[0.60, 0.20, 0.15, 0.05]),
    }
    return pd.DataFrame(records)


def gerar_sih_aih(estado: str, ano: int, n: int) -> pd.DataFrame:
    """Autorizações de internação hospitalar sintéticas (SIH/AIH)."""
    municipios = MUNICIPIOS.get(estado, ["000000"] * 5)
    causas = list(CID10_CAUSAS.keys())
    procedimentos = list(PROCEDIMENTOS.keys())

    permanencia = rng.integers(0, 60, n)
    obito = (rng.random(n) < 0.04).astype(int)  # ~4% de mortalidade intra-hospitalar

    records = {
        "uf_sigla": estado,
        "municipio_codigo": rng.choice(municipios, n),
        "ano_cmpt": ano,
        "mes_cmpt": rng.integers(1, 13, n),
        "procedimento_principal": rng.choice(procedimentos, n),
        "diagnostico_principal": rng.choice(causas, n),
        "idade": rng.integers(0, 100, n),
        "sexo": rng.choice(["1", "3"], n, p=[0.49, 0.51]),
        "permanencia_dias": permanencia,
        "val_tot": rng.uniform(200.0, 50000.0, n).round(2),
        "morte": obito,
        "complexidade": rng.choice(["01", "02", "03"], n, p=[0.30, 0.50, 0.20]),
        "regime": rng.choice(["01", "02"], n, p=[0.80, 0.20]),
    }
    df = pd.DataFrame(records)
    df["val_tot"] = df["val_tot"].astype(float)
    return df


def gerar_sinan(estado: str, ano: int, n: int) -> pd.DataFrame:
    """Agravos de notificação sintéticos (SINAN)."""
    municipios = MUNICIPIOS.get(estado, ["000000"] * 5)
    agravos = {
        "A90": "Dengue",
        "A15": "Tuberculose",
        "A37": "Coqueluche",
        "A22": "Carbúnculo",
        "B54": "Malária",
        "A36": "Difteria",
    }
    codigos = list(agravos.keys())
    # Sazonalidade artificial: dengue mais comum no verão (jan-mar)
    meses = rng.choice(range(1, 13), n, p=[0.15, 0.15, 0.12, 0.07, 0.06, 0.06, 0.06, 0.07, 0.07, 0.07, 0.06, 0.06])

    records = {
        "uf_sigla": estado,
        "municipio_codigo": rng.choice(municipios, n),
        "ano_notificacao": ano,
        "mes_notificacao": meses,
        "agravo_cid10": rng.choice(codigos, n, p=[0.55, 0.20, 0.05, 0.05, 0.10, 0.05]),
        "idade": rng.integers(0, 90, n),
        "sexo": rng.choice(["M", "F"], n, p=[0.50, 0.50]),
        "classificacao_final": rng.choice(["1", "2", "3", "8"], n, p=[0.70, 0.15, 0.10, 0.05]),
        "evolucao": rng.choice(["1", "2", "9"], n, p=[0.92, 0.04, 0.04]),
    }
    return pd.DataFrame(records)


def gerar_cnes(estado: str, ano: int) -> pd.DataFrame:
    """Cadastro de estabelecimentos de saúde sintético (CNES)."""
    municipios = MUNICIPIOS.get(estado, ["000000"] * 5)
    tipos = {
        "01": "Hospital Geral",
        "02": "Hospital Especializado",
        "20": "Pronto Socorro Geral",
        "36": "UBS",
        "70": "Centro de Saúde/Unidade Básica",
    }
    n_estab = len(municipios) * 10

    records = {
        "uf_sigla": estado,
        "municipio_codigo": rng.choice(municipios, n_estab),
        "cnes_codigo": [f"{rng.integers(1000000, 9999999)}" for _ in range(n_estab)],
        "tipo_unidade": rng.choice(list(tipos.keys()), n_estab),
        "ano_competencia": ano,
        "mes_competencia": 12,
        "leitos_sus": rng.integers(0, 500, n_estab),
        "leitos_uti_sus": rng.integers(0, 50, n_estab),
        "leitos_neonatal_sus": rng.integers(0, 20, n_estab),
        "esf_equipes": rng.integers(0, 10, n_estab),
    }
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Escrita em Parquet
# ---------------------------------------------------------------------------


def salvar_parquet(df: pd.DataFrame, caminho: Path, nome: str) -> None:
    caminho.mkdir(parents=True, exist_ok=True)
    arquivo = caminho / f"{nome}.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, arquivo, compression="snappy")
    logger.info("  ✅ %s (%d registros, %s)", arquivo.name, len(df), _tamanho(arquivo))


def _tamanho(caminho: Path) -> str:
    kb = caminho.stat().st_size / 1024
    return f"{kb:.1f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dados sintéticos de demonstração")
    parser.add_argument("--estados", nargs="+", default=["SP", "RJ", "MG"], help="Siglas de estados (padrão: SP RJ MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2023, 2024], help="Anos a gerar (padrão: 2023 2024)")
    parser.add_argument("--registros", type=int, default=2000, help="Registros por estado/ano (padrão: 2000)")
    parser.add_argument("--saida", type=Path, default=Path("data/demo/parquet"), help="Pasta de saída")
    args = parser.parse_args()

    estados = [e.upper() for e in args.estados]
    anos = args.anos
    n = args.registros
    saida = args.saida

    logger.info("=" * 60)
    logger.info("saude-publica-br — Gerador de Dados de Demo")
    logger.info("Estados: %s | Anos: %s | Registros/combo: %d", estados, anos, n)
    logger.info("Saída: %s", saida.resolve())
    logger.info("=" * 60)

    total = 0
    for estado in estados:
        for ano in anos:
            logger.info("\n📂 %s / %d", estado, ano)

            # SIA/PA
            df = gerar_sia_pa(estado, ano, n)
            salvar_parquet(df, saida / "sia_pa" / f"estado={estado}" / f"ano={ano}", f"sia_pa_{estado}_{ano}")
            total += len(df)

            # SIM/DO
            df = gerar_sim_do(estado, ano, n // 10)  # óbitos são ~10% da produção
            salvar_parquet(df, saida / "sim_do" / f"estado={estado}" / f"ano={ano}", f"sim_do_{estado}_{ano}")
            total += len(df)

            # SIH/AIH
            df = gerar_sih_aih(estado, ano, n // 5)
            salvar_parquet(df, saida / "sih_aih" / f"estado={estado}" / f"ano={ano}", f"sih_aih_{estado}_{ano}")
            total += len(df)

            # SINAN
            df = gerar_sinan(estado, ano, n // 8)
            salvar_parquet(df, saida / "sinan" / f"estado={estado}" / f"ano={ano}", f"sinan_{estado}_{ano}")
            total += len(df)

        # CNES (anual mais recente)
        df = gerar_cnes(estado, max(anos))
        salvar_parquet(df, saida / "cnes" / f"estado={estado}", f"cnes_{estado}_{max(anos)}")
        total += len(df)

    logger.info("\n" + "=" * 60)
    logger.info("✅ Concluído! %d registros gerados em %s", total, saida.resolve())
    logger.info("")
    logger.info("Próximos passos:")
    logger.info("  1. bash scripts/load_demo_data.sh   — carrega no banco local")
    logger.info("  2. docker compose up -d              — sobe a stack")
    logger.info("  3. curl http://localhost/api/health  — verifica a API")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
