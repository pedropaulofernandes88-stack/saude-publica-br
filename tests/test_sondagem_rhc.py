"""O portão do RHC reprova pelas razões certas, e sabe aprovar.

As quatro armadilhas que a sondagem de 2026-09-21 mediu são todas SILENCIOSAS —
nenhuma levanta exceção, todas produzem número plausível e errado:

  * `ESTADIAM` 88/99 somado como estádio inventa uma distribuição (53,1% dos
    registros de 2019);
  * o ano do arquivo é o da primeira consulta, e diverge do ano do diagnóstico
    em 21,7%;
  * caso não analítico é outro universo, e são 25,9%;
  * a data vem em `DD/MM/YYYY`, contra o `YYYYMMDD` do resto do projeto.

Cada uma tem teste aqui, nos dois sentidos. O deslocamento dos campos do dBase
ganhou teste próprio porque errar o byte de exclusão desloca TODAS as colunas em
um caractere sem falhar em lugar nenhum.

Nada aqui toca a rede.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import sondar_rhc as sr  # noqa: E402


# ---------------------------------------------------------------------------
# Um dBase mínimo, construído aqui para não depender de rede nem de arquivo
# ---------------------------------------------------------------------------

def dbf_sintetico(campos: list[tuple[str, int]],
                  registros: list[list[str]]) -> bytes:
    """Monta um .dbf dBase III com campos de texto."""
    n_campos = len(campos)
    ini = 32 + 32 * n_campos + 1
    larg = 1 + sum(t for _, t in campos)
    cab = bytearray(32)
    cab[0] = 0x03
    cab[1:4] = bytes((125, 3, 8))
    cab[4:8] = struct.pack("<I", len(registros))
    cab[8:10] = struct.pack("<H", ini)
    cab[10:12] = struct.pack("<H", larg)
    for nome, tam in campos:
        d = bytearray(32)
        d[:len(nome)] = nome.encode("latin-1")
        d[11] = ord("C")
        d[16] = tam
        cab += d
    cab += b"\x0d"
    corpo = bytearray()
    for r in registros:
        corpo += b" "
        for (_, tam), v in zip(campos, r):
            corpo += v.encode("latin-1").ljust(tam)[:tam]
    return bytes(cab) + bytes(corpo)


CAMPOS = [("TPCASO", 20), ("ESTADIAM", 20), ("DTDIAGNO", 20)]


def test_campos_do_dbf_acerta_nome_largura_e_deslocamento():
    b = dbf_sintetico(CAMPOS, [["1", "2A", "05/03/2019"]])
    n, ini, larg = sr.metadados_do_dbf(b[:32])
    campos = sr.campos_do_dbf(b[:ini])
    assert [(nm, t) for nm, _, t in campos] == CAMPOS
    assert [o for _, o, _ in campos] == [1, 21, 41], (
        "o deslocamento tem que começar em 1: o primeiro byte do registro é a "
        "marca de exclusão do dBase, e ignorá-la desloca TODA coluna em um "
        "caractere sem erro nenhum"
    )
    assert (n, larg) == (1, 61)


def test_o_registro_lido_com_o_deslocamento_certo_bate():
    b = dbf_sintetico(CAMPOS, [["1", "2A", "05/03/2019"], ["2", "99", "01/01/2018"]])
    _, ini, larg = sr.metadados_do_dbf(b[:32])
    campos = sr.campos_do_dbf(b[:ini])
    reg = b[ini:ini + larg]
    lido = [reg[o:o + t].decode("latin-1").strip() for _, o, t in campos]
    assert lido == ["1", "2A", "05/03/2019"]


# ---------------------------------------------------------------------------
# Armadilha 1: 88 e 99 não são estádio
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bruto", ["88", "99", "", "  ", "II", "ZZ", "9"])
def test_estadio_rotula_ausencia_em_vez_de_inventar(bruto):
    assert sr.estadio(bruto) == "ignorado"


@pytest.mark.parametrize("bruto,esperado", [
    ("0", "0"), ("1", "1"), ("2A", "2A"), ("4C", "4C"),
    ("b1", "B1"), (" 3 ", "3"), ("01", "01"),
])
def test_estadio_preserva_o_que_o_dicionario_conhece(bruto, esperado):
    assert sr.estadio(bruto) == esperado


def test_nem_88_nem_99_entraram_na_lista_de_validos():
    """Regressão da armadilha: basta alguém 'completar' a lista para quebrar."""
    assert "88" not in sr.ESTADIOS_VALIDOS
    assert "99" not in sr.ESTADIOS_VALIDOS


# ---------------------------------------------------------------------------
# Armadilha 4: a data é brasileira, e só nesta fonte
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bruto,esperado", [
    ("05/03/2019", "2019-03-05"),
    ("31/12/1985", "1985-12-31"),
    (" 01/01/2023 ", "2023-01-01"),
])
def test_data_br_converte(bruto, esperado):
    assert sr.data_br(bruto) == esperado


@pytest.mark.parametrize("bruto", [
    "20190305",    # o formato do RESTO do projeto — não pode ser aceito aqui
    "2019-03-05",
    "05/13/2019",  # mês 13
    "32/01/2019",  # dia 32
    "05/03/19",
    "", "  ", None, "//",
])
def test_data_br_recusa_o_que_nao_e_data_brasileira(bruto):
    assert sr.data_br(bruto) is None


def test_data_br_nao_aceita_o_formato_do_datasus():
    """O erro que motivou a função: reaproveitar o leitor do SIA aqui.

    `20190305` é uma data perfeitamente válida no resto do projeto. Se esta
    função a aceitasse, o RHC leria silenciosamente datas erradas.
    """
    assert sr.data_br("20190305") is None
    assert sr.data_br("05/03/2019") == "2019-03-05"


# ---------------------------------------------------------------------------
# O que o portão promete: os campos essenciais e os anos conhecidos
# ---------------------------------------------------------------------------

def test_campos_essenciais_cobrem_as_duas_datas_e_o_universo():
    """Lista que envelhece calada vale menos que lista nenhuma."""
    for c in ("DTDIAGNO", "DATAINITRT", "TPCASO", "ESTADIAM", "ANOPRIDI"):
        assert c in sr.CAMPOS_ESSENCIAIS


def test_1987_nao_esta_entre_os_anos_conhecidos():
    """Ausência medida, não falha — e sem isto o portão reprovaria sozinho."""
    assert 1987 not in sr.ANOS_CONHECIDOS
    assert 1986 in sr.ANOS_CONHECIDOS and 1988 in sr.ANOS_CONHECIDOS
    assert len(sr.ANOS_CONHECIDOS) == 38


def test_a_deteccao_de_campo_faltando_e_por_conjunto():
    """O portão compara conjuntos; um campo removido tem que aparecer."""
    presentes = set(sr.CAMPOS_ESSENCIAIS) - {"ESTADIAM"}
    assert sr.CAMPOS_ESSENCIAIS - presentes == {"ESTADIAM"}


# ---------------------------------------------------------------------------
# Armadilha 5: o download assíncrono
# ---------------------------------------------------------------------------

class _RespostaFalsa:
    def __init__(self, texto: str) -> None:
        self.text = texto

    def raise_for_status(self) -> None:
        pass


class _SessaoFalsa:
    """Servidor que responde status para sempre — o modo de falha real."""

    def __init__(self, sequencia: list[str]) -> None:
        self.sequencia = sequencia
        self.headers: dict[str, str] = {}
        self.chamadas = 0

    def get(self, url, **kw):
        if "wwajax" not in str(url):
            return _RespostaFalsa("")
        self.chamadas += 1
        i = min(self.chamadas - 1, len(self.sequencia) - 1)
        return _RespostaFalsa(self.sequencia[i])

    def post(self, url, **kw):
        return _RespostaFalsa(self.sequencia[0])


def test_baixar_recusa_quando_o_servidor_so_diz_gerando(tmp_path, monkeypatch):
    """Sem isto, o coletor gravaria `{'status':'1'}` com extensão .zip."""
    monkeypatch.setattr(sr.time, "sleep", lambda _s: None)
    s = _SessaoFalsa(["{'status':'1'}"])
    with pytest.raises(RuntimeError, match="nunca disse pronto"):
        sr.baixar_ano(2019, tmp_path / "x.zip", s)
    assert not (tmp_path / "x.zip").exists()


def test_baixar_recusa_resposta_inesperada(tmp_path, monkeypatch):
    monkeypatch.setattr(sr.time, "sleep", lambda _s: None)
    s = _SessaoFalsa(["<html>Sessao expirada</html>"])
    with pytest.raises(RuntimeError, match="resposta inesperada"):
        sr.baixar_ano(2019, tmp_path / "x.zip", s)
