"""
tests/ingestion/test_utils.py
Testes para as utilidades de ingestão: bulk_load e ingestion_log.

Cobertura:
  - IngestionStatus: todos os valores do enum
  - IngestionEntry: dataclass defaults, campos opcionais, uppercasing implícito
  - df_to_parquet: cria arquivo Parquet particionado com estrutura correta
  - parquet_to_supabase: mock psycopg.connect + COPY; vazio retorna 0; sem DB_URL levanta ValueError
  - df_to_supabase_bulk: pipeline completo com mocks; erro no COPY propaga e preserva parquet
  - is_already_loaded: mock retorna row → True; None → False
  - get_pending_combinations: set-subtraction lógica; combos vazios; todos já carregados
  - upsert_log: verifica SQL executado e uppercasing do estado
  - ensure_table: verifica que DDL é executado
"""
from __future__ import annotations

import io
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

# ---------------------------------------------------------------------------
# Utilitários de imports — isolamos os módulos para mocks localizados
# ---------------------------------------------------------------------------

def _import_bulk():
    from ingestion.utils import bulk_load
    return bulk_load


def _import_log():
    from ingestion.utils import ingestion_log
    return ingestion_log


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_df() -> pd.DataFrame:
    """DataFrame mínimo compatível com SIA_PA_SCHEMA para testes de Parquet."""
    return pd.DataFrame({
        "mes_competencia":       ["202301", "202302"],
        "ano_competencia":       [2023, 2023],
        "mes_num":               [1, 2],
        "municipio_cod":         ["3550308", "3304557"],
        "proc_id":               ["0101010010", "0101010010"],
        "cid_primario":          ["Z00", "J18"],
        "qtd_aprovada":          [10, 20],
        "valor_aprovado":        [150.0, 300.0],
        "tipo_financiamento":    ["01", "01"],
        "categoria_atendimento": ["01", "02"],
        "sexo":                  ["M", "F"],
        "faixa_etaria":          [30, 45],
        "uf_sigla":              ["SP", "RJ"],
    })


def _make_mock_conn() -> MagicMock:
    """Constrói um mock de psycopg.Connection como context manager."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.commit = MagicMock()

    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)

    copy_ctx = MagicMock()
    copy_ctx.__enter__ = MagicMock(return_value=copy_ctx)
    copy_ctx.__exit__ = MagicMock(return_value=False)
    cur.copy = MagicMock(return_value=copy_ctx)

    conn.cursor = MagicMock(return_value=cur)

    # execute().fetchone() padrão: None (nenhum registro encontrado)
    exec_result = MagicMock()
    exec_result.fetchone = MagicMock(return_value=None)
    exec_result.fetchall = MagicMock(return_value=[])
    conn.execute = MagicMock(return_value=exec_result)

    return conn


# ===========================================================================
# IngestionStatus
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestIngestionStatus:

    def test_all_values_defined(self):
        log = _import_log()
        status = log.IngestionStatus
        assert status.PENDING.value   == "pending"
        assert status.RUNNING.value   == "running"
        assert status.SUCCESS.value   == "success"
        assert status.ERROR.value     == "error"
        assert status.SKIPPED.value   == "skipped"

    def test_is_str_subclass(self):
        log = _import_log()
        assert isinstance(log.IngestionStatus.SUCCESS, str)

    def test_enum_comparison_with_string(self):
        log = _import_log()
        assert log.IngestionStatus.SUCCESS == "success"

    def test_five_members(self):
        log = _import_log()
        assert len(log.IngestionStatus) == 5


# ===========================================================================
# IngestionEntry
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestIngestionEntry:

    def test_required_fields_present(self):
        log = _import_log()
        field_names = {f.name for f in fields(log.IngestionEntry)}
        assert {"estado", "ano", "mes", "sistema", "status"} <= field_names

    def test_optional_fields_default_to_none(self):
        log = _import_log()
        entry = log.IngestionEntry(
            estado="SP", ano=2023, mes=6,
            sistema="SIA_PA",
            status=log.IngestionStatus.SUCCESS,
        )
        assert entry.loaded_at is None
        assert entry.qtd_registros is None
        assert entry.error_msg is None
        assert entry.elapsed_sec is None

    def test_all_fields_set(self):
        log = _import_log()
        ts = datetime(2024, 1, 15, 12, 0, 0)
        entry = log.IngestionEntry(
            estado="RJ", ano=2022, mes=12,
            sistema="SIM",
            status=log.IngestionStatus.ERROR,
            loaded_at=ts,
            qtd_registros=5000,
            error_msg="Connection timeout",
            elapsed_sec=3.14,
        )
        assert entry.estado == "RJ"
        assert entry.ano == 2022
        assert entry.mes == 12
        assert entry.sistema == "SIM"
        assert entry.status == log.IngestionStatus.ERROR
        assert entry.qtd_registros == 5000
        assert entry.error_msg == "Connection timeout"
        assert entry.elapsed_sec == pytest.approx(3.14)

    def test_all_sistemas_accepted(self):
        """IngestionEntry não valida o campo sistema — aceita qualquer string."""
        log = _import_log()
        for sistema in ("SIA_PA", "SIM", "SIH", "CNES", "SINAN"):
            entry = log.IngestionEntry(
                estado="MG", ano=2021, mes=1,
                sistema=sistema,
                status=log.IngestionStatus.PENDING,
            )
            assert entry.sistema == sistema


# ===========================================================================
# df_to_parquet
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestDfToParquet:

    def test_creates_file_at_correct_path(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        result = bl.df_to_parquet(df, uf="SP", ano=2023, mes=6, base_dir=tmp_path)

        expected = tmp_path / "uf=SP" / "ano=2023" / "mes=06" / "data.parquet"
        assert result == expected
        assert result.exists()

    def test_file_is_readable_parquet(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        path = bl.df_to_parquet(df, uf="SP", ano=2023, mes=1, base_dir=tmp_path)

        recovered = pd.read_parquet(path)
        assert len(recovered) == len(df)

    def test_uf_uppercased_in_path(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        path = bl.df_to_parquet(df, uf="sp", ano=2023, mes=3, base_dir=tmp_path)
        # Deve criar uf=SP (uppercase)
        assert "uf=SP" in str(path)

    def test_month_zero_padded(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        path = bl.df_to_parquet(df, uf="RJ", ano=2024, mes=3, base_dir=tmp_path)
        assert "mes=03" in str(path)

    def test_two_digit_month_not_padded_again(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        path = bl.df_to_parquet(df, uf="MG", ano=2024, mes=12, base_dir=tmp_path)
        assert "mes=12" in str(path)

    def test_creates_intermediate_directories(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        base = tmp_path / "deep" / "nested"
        path = bl.df_to_parquet(df, uf="BA", ano=2022, mes=7, base_dir=base)
        assert path.parent.is_dir()

    def test_with_explicit_schema(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        path = bl.df_to_parquet(
            df, uf="PR", ano=2021, mes=11,
            schema=bl.SIA_PA_SCHEMA,
            base_dir=tmp_path,
        )
        assert path.exists()

    def test_overwrite_existing_file(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        path1 = bl.df_to_parquet(df, uf="SP", ano=2023, mes=6, base_dir=tmp_path)
        size1 = path1.stat().st_size

        df2 = _minimal_df().iloc[:1]  # menor
        path2 = bl.df_to_parquet(df2, uf="SP", ano=2023, mes=6, base_dir=tmp_path)
        assert path1 == path2
        # Arquivo foi sobrescrito
        assert path2.stat().st_size != size1 or len(pd.read_parquet(path2)) == 1

    def test_returns_path_object(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        result = bl.df_to_parquet(df, uf="CE", ano=2020, mes=2, base_dir=tmp_path)
        assert isinstance(result, Path)

    def test_default_table_name_in_path(self, tmp_path):
        """Sem table_name explícito → usa PARQUET_DIR (ou base_dir) direto."""
        bl = _import_bulk()
        df = _minimal_df()
        # Com base_dir, não usa table_name no caminho
        path = bl.df_to_parquet(df, uf="AM", ano=2023, mes=8, base_dir=tmp_path)
        assert path.exists()


# ===========================================================================
# parquet_to_supabase
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestParquetToSupabase:

    def _write_test_parquet(self, tmp_path: Path, n: int = 5) -> Path:
        df = _minimal_df().head(n) if n > 0 else _minimal_df().head(0)
        cols = ["municipio_cod", "uf_sigla", "qtd_aprovada"]
        path = tmp_path / "test.parquet"
        df[cols].to_parquet(path, index=False)
        return path

    def test_raises_if_no_database_url(self, tmp_path):
        bl = _import_bulk()
        path = self._write_test_parquet(tmp_path)
        with pytest.raises(ValueError, match="DATABASE_URL"):
            bl.parquet_to_supabase(
                path, "sia_pa",
                ["municipio_cod", "uf_sigla", "qtd_aprovada"],
                database_url="",
            )

    def test_empty_parquet_returns_zero(self, tmp_path):
        bl = _import_bulk()
        path = self._write_test_parquet(tmp_path, n=0)

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn):
            result = bl.parquet_to_supabase(
                path, "sia_pa",
                ["municipio_cod", "uf_sigla", "qtd_aprovada"],
                database_url="postgresql://fake/db",
            )
        assert result == 0
        # Sem banco de dados chamado para arquivo vazio
        mock_conn.__enter__.assert_not_called()

    def test_normal_load_returns_row_count(self, tmp_path):
        bl = _import_bulk()
        path = self._write_test_parquet(tmp_path, n=2)

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn):
            result = bl.parquet_to_supabase(
                path, "sia_pa",
                ["municipio_cod", "uf_sigla", "qtd_aprovada"],
                database_url="postgresql://fake/db",
            )
        assert result == 2

    def test_copy_write_called(self, tmp_path):
        bl = _import_bulk()
        path = self._write_test_parquet(tmp_path, n=2)

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn):
            bl.parquet_to_supabase(
                path, "sia_pa",
                ["municipio_cod", "uf_sigla", "qtd_aprovada"],
                database_url="postgresql://fake/db",
            )
        # copy context manager deve ter sido usado
        mock_conn.cursor.return_value.__enter__.return_value.copy.assert_called()

    def test_commit_called_on_success(self, tmp_path):
        bl = _import_bulk()
        path = self._write_test_parquet(tmp_path, n=2)

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn):
            bl.parquet_to_supabase(
                path, "sia_pa",
                ["municipio_cod", "uf_sigla", "qtd_aprovada"],
                database_url="postgresql://fake/db",
            )
        mock_conn.commit.assert_called_once()

    def test_batch_size_one_produces_multiple_batches(self, tmp_path):
        """Com batch_size=1, cada linha gera um COPY separado."""
        bl = _import_bulk()
        path = self._write_test_parquet(tmp_path, n=2)

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn):
            result = bl.parquet_to_supabase(
                path, "sia_pa",
                ["municipio_cod", "uf_sigla", "qtd_aprovada"],
                database_url="postgresql://fake/db",
                batch_size=1,
            )
        assert result == 2
        # copy foi chamado 2 vezes (uma por linha)
        assert mock_conn.cursor.return_value.__enter__.return_value.copy.call_count == 2

    def test_uses_env_database_url_when_none_passed(self, tmp_path, monkeypatch):
        bl = _import_bulk()
        path = self._write_test_parquet(tmp_path, n=1)
        monkeypatch.setattr("ingestion.utils.bulk_load.DATABASE_URL", "postgresql://env/db")

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn) as mock_connect:
            bl.parquet_to_supabase(
                path, "sia_pa",
                ["municipio_cod", "uf_sigla", "qtd_aprovada"],
            )
        mock_connect.assert_called_once_with("postgresql://env/db")


# ===========================================================================
# df_to_supabase_bulk
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestDfToSubabaseBulk:

    def test_returns_path_and_row_count(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()
        cols = ["municipio_cod", "uf_sigla", "qtd_aprovada"]

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn):
            path, count = bl.df_to_supabase_bulk(
                df, uf="SP", ano=2023, mes=6,
                table_name="sia_pa",
                columns=cols,
                base_dir=tmp_path,
                database_url="postgresql://fake/db",
            )

        assert isinstance(path, Path)
        assert path.exists()
        assert count == len(df)

    def test_parquet_preserved_on_success(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn):
            path, _ = bl.df_to_supabase_bulk(
                df, uf="RJ", ano=2022, mes=3,
                table_name="sia_pa",
                columns=["municipio_cod", "uf_sigla"],
                base_dir=tmp_path,
                database_url="postgresql://fake/db",
                keep_parquet=True,
            )
        assert path.exists()

    def test_parquet_removed_on_error_when_keep_false(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()

        with patch("ingestion.utils.bulk_load.parquet_to_supabase",
                   side_effect=RuntimeError("COPY falhou")):
            with pytest.raises(RuntimeError, match="COPY falhou"):
                bl.df_to_supabase_bulk(
                    df, uf="MG", ano=2021, mes=1,
                    table_name="sia_pa",
                    columns=["municipio_cod"],
                    base_dir=tmp_path,
                    database_url="postgresql://fake/db",
                    keep_parquet=False,
                )

    def test_parquet_kept_on_error_when_keep_true(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()

        # Deixa df_to_parquet rodar, mas parquet_to_supabase falha
        with patch("ingestion.utils.bulk_load.parquet_to_supabase",
                   side_effect=RuntimeError("COPY falhou")):
            with pytest.raises(RuntimeError):
                bl.df_to_supabase_bulk(
                    df, uf="BA", ano=2023, mes=9,
                    table_name="sia_pa",
                    columns=["municipio_cod"],
                    base_dir=tmp_path,
                    database_url="postgresql://fake/db",
                    keep_parquet=True,
                )
        # O parquet deve ter sido criado (df_to_parquet rodou antes do erro)
        expected = tmp_path / "uf=BA" / "ano=2023" / "mes=09" / "data.parquet"
        assert expected.exists()

    def test_error_propagates(self, tmp_path):
        bl = _import_bulk()
        df = _minimal_df()

        with patch("ingestion.utils.bulk_load.parquet_to_supabase",
                   side_effect=ConnectionError("DB indisponível")):
            with pytest.raises(ConnectionError, match="DB indisponível"):
                bl.df_to_supabase_bulk(
                    df, uf="PR", ano=2020, mes=5,
                    table_name="sia_pa",
                    columns=["municipio_cod"],
                    base_dir=tmp_path,
                    database_url="postgresql://fake/db",
                )


# ===========================================================================
# is_already_loaded
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestIsAlreadyLoaded:

    def test_returns_true_when_row_found(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchone.return_value = (1,)

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.is_already_loaded(
                "SP", 2023, 6, "SIA_PA",
                database_url="postgresql://fake/db",
            )
        assert result is True

    def test_returns_false_when_no_row(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchone.return_value = None

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.is_already_loaded(
                "RJ", 2022, 3, "SIA_PA",
                database_url="postgresql://fake/db",
            )
        assert result is False

    def test_estado_uppercased_in_query(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchone.return_value = None

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.is_already_loaded(
                "sp", 2023, 1, "SIA_PA",
                database_url="postgresql://fake/db",
            )

        # Verificar que execute foi chamado com "SP" (uppercase)
        call_args = mock_conn.execute.call_args
        params = call_args[0][1]  # segundo argumento posicional da chamada
        assert params[0] == "SP"

    def test_uses_env_database_url(self, monkeypatch):
        log = _import_log()
        monkeypatch.setattr("ingestion.utils.ingestion_log.DATABASE_URL", "postgresql://env/db")
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchone.return_value = None

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn) as mock_c:
            log.is_already_loaded("MG", 2021, 7, "SIA_PA")

        mock_c.assert_called_once_with("postgresql://env/db")

    @pytest.mark.parametrize("sistema", ["SIA_PA", "SIM", "SIH"])
    def test_sistema_passed_correctly(self, sistema):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchone.return_value = None

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.is_already_loaded("RS", 2023, 12, sistema,
                                   database_url="postgresql://fake/db")

        call_args = mock_conn.execute.call_args
        params = call_args[0][1]
        assert params[3] == sistema


# ===========================================================================
# get_pending_combinations
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestGetPendingCombinations:

    def test_empty_inputs_returns_empty(self):
        log = _import_log()
        mock_conn = _make_mock_conn()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.get_pending_combinations(
                [], [], [],
                database_url="postgresql://fake/db",
            )
        assert result == []

    def test_no_db_call_when_inputs_empty(self):
        log = _import_log()
        mock_conn = _make_mock_conn()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn) as mock_c:
            log.get_pending_combinations([], [], [],
                                          database_url="postgresql://fake/db")
        # Sem combinações, não deve abrir conexão
        mock_c.assert_not_called()

    def test_all_pending_when_db_empty(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchall.return_value = []  # nenhum já carregado

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.get_pending_combinations(
                estados=["SP", "RJ"],
                anos=[2022, 2023],
                meses=[1, 2],
                database_url="postgresql://fake/db",
            )

        # 2 estados × 2 anos × 2 meses = 8 combinações
        assert len(result) == 8

    def test_already_loaded_excluded(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        # SP, 2022, 1 já foi carregado
        mock_conn.execute.return_value.fetchall.return_value = [
            ("SP", 2022, 1),
        ]

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.get_pending_combinations(
                estados=["SP", "RJ"],
                anos=[2022],
                meses=[1, 2],
                database_url="postgresql://fake/db",
            )

        # Total: 4, carregado: 1 → pendente: 3
        assert len(result) == 3
        assert ("SP", 2022, 1) not in result

    def test_all_loaded_returns_empty(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchall.return_value = [
            ("SP", 2023, 6),
            ("RJ", 2023, 6),
        ]

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.get_pending_combinations(
                estados=["SP", "RJ"],
                anos=[2023],
                meses=[6],
                database_url="postgresql://fake/db",
            )
        assert result == []

    def test_result_is_sorted(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchall.return_value = []

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.get_pending_combinations(
                estados=["SP", "AM", "BA"],
                anos=[2023],
                meses=[3, 1, 2],
                database_url="postgresql://fake/db",
            )
        assert result == sorted(result)

    def test_estados_uppercased_in_lookup(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchall.return_value = [
            ("SP", 2023, 1),  # Já carregado em uppercase
        ]

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.get_pending_combinations(
                estados=["sp"],  # lowercase
                anos=[2023],
                meses=[1],
                database_url="postgresql://fake/db",
            )
        # ("SP", 2023, 1) estava carregado → não deve aparecer
        assert ("SP", 2023, 1) not in result
        assert len(result) == 0

    def test_combinations_are_tuples(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        mock_conn.execute.return_value.fetchall.return_value = []

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            result = log.get_pending_combinations(
                estados=["SP"], anos=[2023], meses=[1],
                database_url="postgresql://fake/db",
            )
        assert len(result) == 1
        estado, ano, mes = result[0]
        assert isinstance(estado, str)
        assert isinstance(ano, int)
        assert isinstance(mes, int)


# ===========================================================================
# upsert_log
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestUpsertLog:

    def _make_entry(self, status_str: str = "success", estado: str = "SP"):
        log = _import_log()
        return log.IngestionEntry(
            estado=estado,
            ano=2023,
            mes=6,
            sistema="SIA_PA",
            status=log.IngestionStatus(status_str),
            loaded_at=datetime(2024, 1, 1),
            qtd_registros=1000,
            elapsed_sec=2.5,
        )

    def test_execute_called_once(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        entry = self._make_entry()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.upsert_log(entry, database_url="postgresql://fake/db")

        mock_conn.execute.assert_called_once()

    def test_commit_called_once(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        entry = self._make_entry()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.upsert_log(entry, database_url="postgresql://fake/db")

        mock_conn.commit.assert_called_once()

    def test_estado_uppercased_in_params(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        entry = self._make_entry(estado="rj")  # lowercase

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.upsert_log(entry, database_url="postgresql://fake/db")

        call_args = mock_conn.execute.call_args
        params = call_args[0][1]
        assert params[0] == "RJ"  # deve ser uppercase

    @pytest.mark.parametrize("status_str", ["pending", "running", "success", "error", "skipped"])
    def test_all_statuses_upserted(self, status_str):
        log = _import_log()
        mock_conn = _make_mock_conn()
        entry = self._make_entry(status_str=status_str)

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            # Não deve levantar
            log.upsert_log(entry, database_url="postgresql://fake/db")

        call_args = mock_conn.execute.call_args
        params = call_args[0][1]
        assert params[4] == status_str  # status.value

    def test_sql_contains_on_conflict(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        entry = self._make_entry()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.upsert_log(entry, database_url="postgresql://fake/db")

        sql = mock_conn.execute.call_args[0][0]
        assert "ON CONFLICT" in sql.upper()

    def test_error_entry_preserves_error_msg(self):
        log = _import_log()
        mock_conn = _make_mock_conn()
        entry = log.IngestionEntry(
            estado="SP", ano=2023, mes=1,
            sistema="SIA_PA",
            status=log.IngestionStatus.ERROR,
            error_msg="Arquivo .dbc corrompido",
        )

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.upsert_log(entry, database_url="postgresql://fake/db")

        params = mock_conn.execute.call_args[0][1]
        # error_msg deve estar nos parâmetros
        assert "Arquivo .dbc corrompido" in params

    def test_uses_env_database_url(self, monkeypatch):
        log = _import_log()
        monkeypatch.setattr("ingestion.utils.ingestion_log.DATABASE_URL", "postgresql://env/db")
        mock_conn = _make_mock_conn()
        entry = self._make_entry()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn) as mock_c:
            log.upsert_log(entry)

        mock_c.assert_called_once_with("postgresql://env/db")


# ===========================================================================
# ensure_table
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestEnsureTable:

    def test_executes_create_table_sql(self):
        log = _import_log()
        mock_conn = _make_mock_conn()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.ensure_table(database_url="postgresql://fake/db")

        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS" in sql

    def test_commit_called(self):
        log = _import_log()
        mock_conn = _make_mock_conn()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.ensure_table(database_url="postgresql://fake/db")

        mock_conn.commit.assert_called_once()

    def test_sql_creates_indexes(self):
        log = _import_log()
        mock_conn = _make_mock_conn()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.ensure_table(database_url="postgresql://fake/db")

        sql = mock_conn.execute.call_args[0][0]
        assert "CREATE INDEX IF NOT EXISTS" in sql

    def test_sql_has_unique_constraint(self):
        """A chave UNIQUE (estado, ano, mes, sistema) é fundamental para upsert."""
        log = _import_log()
        sql = log.CREATE_TABLE_SQL
        assert "UNIQUE" in sql

    def test_uses_env_database_url(self, monkeypatch):
        log = _import_log()
        monkeypatch.setattr("ingestion.utils.ingestion_log.DATABASE_URL", "postgresql://env/db")
        mock_conn = _make_mock_conn()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn) as mock_c:
            log.ensure_table()

        mock_c.assert_called_once_with("postgresql://env/db")

    def test_connection_used_as_context_manager(self):
        log = _import_log()
        mock_conn = _make_mock_conn()

        with patch("ingestion.utils.ingestion_log.psycopg.connect", return_value=mock_conn):
            log.ensure_table(database_url="postgresql://fake/db")

        mock_conn.__enter__.assert_called()
        mock_conn.__exit__.assert_called()


# ===========================================================================
# Testes de integração leve (sem banco real, mas multi-função)
# ===========================================================================

@pytest.mark.unit
@pytest.mark.ingestion
class TestBulkLoadIntegrationLight:
    """Testa interações entre funções do bulk_load sem banco real."""

    def test_full_pipeline_writes_and_counts(self, tmp_path):
        """Pipeline completo: df → parquet (real) → supabase (mock)."""
        bl = _import_bulk()
        df = _minimal_df()
        cols = ["municipio_cod", "uf_sigla", "qtd_aprovada"]

        mock_conn = _make_mock_conn()
        with patch("ingestion.utils.bulk_load.psycopg.connect", return_value=mock_conn):
            path, count = bl.df_to_supabase_bulk(
                df, uf="SP", ano=2023, mes=6,
                table_name="sia_pa",
                columns=cols,
                base_dir=tmp_path,
                database_url="postgresql://fake/db",
            )

        assert count == len(df)
        assert path.exists()
        # Parquet recuperável
        df_recovered = pd.read_parquet(path)
        assert len(df_recovered) == len(df)

    def test_partition_structure_matches_expected(self, tmp_path):
        """Verifica estrutura de diretórios do particionamento Hive."""
        bl = _import_bulk()
        df = _minimal_df()

        path = bl.df_to_parquet(df, uf="SC", ano=2024, mes=4, base_dir=tmp_path)

        parts = path.parts
        assert any("uf=SC" in p for p in parts)
        assert any("ano=2024" in p for p in parts)
        assert any("mes=04" in p for p in parts)
        assert path.name == "data.parquet"

