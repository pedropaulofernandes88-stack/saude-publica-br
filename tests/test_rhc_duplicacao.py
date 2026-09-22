"""O exportador do INCA grava cada página duas vezes, e isso dobrou uma fonte.

O RHC entrou como 16ª fonte em 2026-09-21 e foi publicado com **todos os casos
em dobro** — 2022 saiu com 461.166 quando o real é 230.583. O arquivo declara
`n` no cabeçalho, ocupa exatamente `n` slots, e cada registro aparece duas
vezes: a cópia mora 50.000 posições adiante.

Nada de forma pegava isso. A geometria do dBase fechava byte a byte
(`1505 + 518186 × 921` = tamanho do arquivo), os campos decodificavam, as datas
eram válidas, a cobertura somava, e todas as guardas do pipeline passavam —
porque dobrar tudo preserva toda proporção. O que denunciou foi **paridade**:
119 categorias de idade e 224 de CNES, e nenhuma contagem ímpar.

Estes testes existem para que a terceira versão do pipeline não desfaça a
correção sem perceber. Dois deles valem mais que os outros:

* `test_recusa_quando_a_copia_nao_bate` — a conferência é registro a registro,
  não por amostra. Dividir por dois sem conferir seria trocar um erro por
  outro, e este projeto já tem `guarda-nunca-vista-reprovando` demais;
* `test_a_paridade_denuncia_e_a_geometria_nao` — a assinatura que achou o
  defeito, presa como teste, porque foi ela e não a forma que funcionou.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipeline_rhc as pr  # noqa: E402
from test_sondagem_rhc import dbf_sintetico  # noqa: E402

CAMPOS_MIN = [("TPCASO", 4), ("LOCTUDET", 4), ("ESTADIAM", 4),
              ("DTDIAGNO", 12), ("DATAINITRT", 12), ("PROCEDEN", 8),
              ("ESTADRES", 4), ("UFUH", 4), ("CNES", 8), ("ANOPRIDI", 6),
              ("SEXO", 4), ("IDADE", 4), ("RACACOR", 4), ("INSTRUC", 4),
              ("PRITRATH", 6), ("RZNTR", 4), ("ESTDFIMT", 4),
              ("DATAOBITO", 12)]


def registro(i: int) -> list[str]:
    """Um registro distinguível pelo índice, para a cópia ser verificável."""
    return ["1", "C50", "2A", "01/03/2019", "15/03/2019", f"3550{i:02d}",
            "SP", "SP", f"{2000000 + i}", "2019", "2", "050", "1", "2",
            "2", "8", "1", "/  /"]


def paginado(originais: list[list[str]], pagina: int) -> list[list[str]]:
    """Reproduz o defeito: páginas de `pagina` registros, cada uma em dobro."""
    fora: list[list[str]] = []
    for ini in range(0, len(originais), pagina):
        bloco = originais[ini:ini + pagina]
        fora.extend(bloco)
        fora.extend(bloco)
    return fora


def escrever(tmp_path: Path, registros: list[list[str]]) -> Path:
    import zipfile
    dbf = dbf_sintetico(CAMPOS_MIN, registros)
    z = tmp_path / "rhc.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("rhc19.dbf", dbf)
    return z


# ---------------------------------------------------------------------------
# 1. `_posicao`: a aritmética das páginas, inclusive a cauda parcial
# ---------------------------------------------------------------------------

def test_metade_exata_em_arquivo_de_paginas_inteiras():
    n = 200_000
    mantidos = [i for i in range(n) if pr._posicao(i, n)[0]]
    assert len(mantidos) == n // 2
    assert mantidos[:3] == [0, 1, 2]
    assert 50_000 not in mantidos          # é a cópia
    assert 100_000 in mantidos             # nova página original


def test_a_cauda_parcial_tambem_vem_em_dobro():
    """2023: n=142.038 é uma página inteira + 21.019 reais na cauda.

    Se a cauda fosse cortada em 50.000 como as outras, 21.019 casos reais
    virariam cópia e sumiriam — mais de um quarto do ano.
    """
    n = 142_038
    mantidos = [i for i in range(n) if pr._posicao(i, n)[0]]
    assert len(mantidos) == 71_019
    assert 100_000 in mantidos and 121_019 not in mantidos


@pytest.mark.parametrize("n", [2, 4, 100_000, 100_002, 142_038, 406_766,
                               518_186, 461_166])
def test_sempre_exatamente_a_metade(n):
    assert sum(pr._posicao(i, n)[0] for i in range(n)) == n // 2


@pytest.mark.parametrize("n", [200_000, 142_038, 518_186])
def test_cada_copia_aponta_para_a_posicao_do_seu_original(n):
    """A posição é o que permite conferir a cópia contra o original CERTO."""
    vistos: dict[int, int] = {}
    for i in range(n):
        original, pos = pr._posicao(i, n)
        if original:
            if pos == 0:
                vistos = {}          # página nova: o original anterior morreu
            vistos[pos] = i
        else:
            assert pos in vistos, f"cópia em {i} sem original na posição {pos}"


# ---------------------------------------------------------------------------
# 2. `_registros`: vista corrigindo, e vista recusando
# ---------------------------------------------------------------------------

def test_le_metade_dos_registros_e_devolve_os_originais(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "PAGINA", 10)
    originais = [registro(i) for i in range(30)]
    z = escrever(tmp_path, paginado(originais, 10))
    lidos = list(pr._registros(z))
    assert len(lidos) == 30
    assert [r["PROCEDEN"] for r in lidos] == [f"3550{i:02d}" for i in range(30)]


def test_sem_duplicacao_o_leitor_recusa_em_vez_de_dividir(tmp_path, monkeypatch):
    """Se o INCA consertar o defeito, o pipeline PARA — não corta pela metade.

    É a escolha deliberada: dividir por dois um arquivo já correto perderia
    metade dos casos em silêncio, que é pior que falhar alto.
    """
    monkeypatch.setattr(pr, "PAGINA", 10)
    z = escrever(tmp_path, [registro(i) for i in range(20)])
    with pytest.raises(SystemExit, match="não é cópia"):
        list(pr._registros(z))


def test_recusa_quando_a_copia_nao_bate(tmp_path, monkeypatch):
    """A conferência é registro a registro. Um único byte diferente reprova."""
    monkeypatch.setattr(pr, "PAGINA", 10)
    originais = [registro(i) for i in range(20)]
    corpo = paginado(originais, 10)
    corpo[13] = list(corpo[13])
    corpo[13][11] = "070"                  # muda a IDADE só na cópia
    z = escrever(tmp_path, corpo)
    with pytest.raises(SystemExit, match="não é cópia"):
        list(pr._registros(z))


def test_a_cauda_parcial_sai_inteira(tmp_path, monkeypatch):
    """25 originais: duas páginas de 10 e uma cauda de 5, todas em dobro."""
    monkeypatch.setattr(pr, "PAGINA", 10)
    originais = [registro(i) for i in range(25)]
    z = escrever(tmp_path, paginado(originais, 10))
    lidos = list(pr._registros(z))
    assert len(lidos) == 25
    assert lidos[-1]["PROCEDEN"] == "355024"


# ---------------------------------------------------------------------------
# 3. A assinatura que achou o defeito
# ---------------------------------------------------------------------------

def test_a_paridade_denuncia_e_a_geometria_nao(tmp_path, monkeypatch):
    """Toda contagem par em toda categoria: foi isto, e não a forma.

    A geometria do dBase fechava byte a byte com a duplicação presente. Só a
    paridade — 119 categorias de idade, 224 de CNES, zero ímpares — apontava.
    """
    monkeypatch.setattr(pr, "PAGINA", 10)
    originais = [registro(i) for i in range(20)]
    # 3 dos 20 com idade distinta, para as contagens serem informativas
    for i in (0, 5, 11):
        originais[i][11] = "061"
    z = escrever(tmp_path, paginado(originais, 10))

    import collections
    cru = collections.Counter()
    with __import__("zipfile").ZipFile(z) as zf:
        import sondar_rhc as sr
        b = zf.read("rhc19.dbf")
        n, ini, larg = sr.metadados_do_dbf(b[:32])
        campos = {nm: (o, t) for nm, o, t in sr.campos_do_dbf(b[:ini])}
        o, t = campos["IDADE"]
        for i in range(n):
            r = b[ini + i * larg: ini + (i + 1) * larg]
            cru[r[o:o + t].decode("latin-1").strip()] += 1
    assert all(v % 2 == 0 for v in cru.values()), (
        "o arquivo cru tem que ter TODA contagem par — é a assinatura")

    corrigido = collections.Counter(r["IDADE"] for r in pr._registros(z))
    assert any(v % 2 for v in corrigido.values()), (
        "depois da correção a paridade tem que sumir; se continuar toda par, "
        "a duplicação não foi desfeita")
    assert sum(corrigido.values()) == 20
