"""
SISCAN: ler em blocos tem de dar o mesmo que ler inteiro, e o eixo é coluna.

O CITO_COLO tem 18,5 GB e um único ano chega a 1,8 GB. A leitura que existia
carregava o CSV inteiro em memória, e não sobrevive a esse arquivo — então
passou a ser em blocos, para TODOS os exames. Duas coisas podem quebrar aí sem
fazer barulho:

1. **A fronteira do bloco.** Um município cujas linhas caem em dois blocos tem
   de somar, não virar duas linhas. O teste usa arquivo maior que o bloco de
   propósito, porque um teste que cabe num bloco não exercita nada.

2. **O eixo temporal.** O CITO_COLO só oferece `CO_ANO_LIBERACAO`, que é quando
   o RESULTADO saiu; os outros três trazem competência do exame. Somar os dois
   como "ano" mistura quando o exame foi feito com quando ele foi liberado — e
   a diferença entre as duas coisas é justamente a fila que se quer medir.

Executar: .venv311/Scripts/python -m pytest tests/test_siscan_blocos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from pipeline_siscan import (  # noqa: E402
    EIXO_POR_EXAME,
    EXAMES,
    ler_em_blocos,
    normalizar,
)


def _csv(tmp_path: Path, linhas: list[dict], nome: str = "x.csv") -> Path:
    caminho = tmp_path / nome
    pd.DataFrame(linhas).to_csv(caminho, sep=";", index=False, encoding="latin1")
    return caminho


def _linha_competencia(mun: str, ano: str, mes: str) -> dict:
    return {"CO_MUN_RESIDENCIA": mun, "CO_ANO_COMPETENCIA": ano,
            "CO_ANO_MES_COMPETENCIA": f"{ano}{mes}"}


def _linha_liberacao(mun: str, ano: str, mes: str) -> dict:
    return {"CO_MUN_RESIDENCIA": mun, "CO_ANO_LIBERACAO": ano,
            "CO_ANO_MES_LIBERACAO": f"{ano}{mes}"}


# ── a fronteira do bloco ───────────────────────────────────────────────────

def test_municipio_partido_entre_blocos_soma_em_vez_de_duplicar(tmp_path, monkeypatch):
    import pipeline_siscan
    monkeypatch.setattr(pipeline_siscan, "LINHAS_POR_BLOCO", 7)
    caminho = _csv(tmp_path, [_linha_competencia("355030", "2023", "05")] * 20)

    df, lidas = ler_em_blocos(caminho, "HISTO_COLO")
    assert lidas == 20
    assert len(df) == 1, "o mesmo município×ano×mês virou mais de uma linha"
    assert int(df.iloc[0]["exames"]) == 20


def test_ler_em_blocos_bate_com_ler_de_uma_vez(tmp_path, monkeypatch):
    import pipeline_siscan
    linhas = [_linha_competencia(m, a, f"{i % 12 + 1:02d}")
              for i, (m, a) in enumerate(
                  [("355030", "2023"), ("330455", "2023"), ("355030", "2024")] * 40)]
    caminho = _csv(tmp_path, linhas)

    monkeypatch.setattr(pipeline_siscan, "LINHAS_POR_BLOCO", 1_000_000)
    inteiro, n1 = ler_em_blocos(caminho, "HISTO_COLO")
    monkeypatch.setattr(pipeline_siscan, "LINHAS_POR_BLOCO", 11)
    picado, n2 = ler_em_blocos(caminho, "HISTO_COLO")

    assert n1 == n2 == len(linhas)
    chave = ["municipio_cod", "ano", "ano_mes"]
    pd.testing.assert_frame_equal(
        inteiro.sort_values(chave, ignore_index=True),
        picado.sort_values(chave, ignore_index=True))


def test_total_de_exames_nao_muda_com_o_tamanho_do_bloco(tmp_path, monkeypatch):
    import pipeline_siscan
    linhas = [_linha_competencia(f"3550{i % 7:02d}", "2023", "03") for i in range(53)]
    caminho = _csv(tmp_path, linhas)
    totais = []
    for tamanho in (3, 10, 1000):
        monkeypatch.setattr(pipeline_siscan, "LINHAS_POR_BLOCO", tamanho)
        df, _ = ler_em_blocos(caminho, "HISTO_COLO")
        totais.append(int(df["exames"].sum()))
    assert totais == [53, 53, 53]


# ── o eixo temporal ────────────────────────────────────────────────────────

def test_cito_colo_e_lido_pela_coluna_de_liberacao(tmp_path):
    """O exame do rastreamento não tem competência — só liberação do resultado."""
    caminho = _csv(tmp_path, [_linha_liberacao("292740", "2022", "07")] * 3)
    df, _ = ler_em_blocos(caminho, "CITO_COLO")
    assert int(df.iloc[0]["ano"]) == 2022
    assert df.iloc[0]["ano_mes"] == "202207"


def test_todo_exame_declara_o_seu_eixo():
    faltando = {r for r in EXAMES.values()} - set(EIXO_POR_EXAME)
    assert not faltando, f"exame sem eixo declarado: {faltando}"


def test_o_cito_colo_nao_e_competencia():
    """Se algum dia virar 'competencia' por descuido, o mart passa a somar
    liberação com competência como se fossem a mesma grandeza."""
    assert EIXO_POR_EXAME["cito_colo"] == "liberacao"
    assert {EIXO_POR_EXAME[e] for e in ("histo_colo", "histo_mama", "cito_mama")} == {
        "competencia"}


# ── o que a fonte muda sem avisar ──────────────────────────────────────────

def test_sem_coluna_de_data_reprova_em_vez_de_inventar():
    df = pd.DataFrame([{"CO_MUN_RESIDENCIA": "355030", "OUTRA": "1"}])
    with pytest.raises(SystemExit, match="nenhuma coluna"):
        normalizar(df, "CITO_COLO")


def test_sem_municipio_reprova():
    df = pd.DataFrame([{"CO_ANO_LIBERACAO": "2022", "CO_ANO_MES_LIBERACAO": "202201"}])
    with pytest.raises(SystemExit, match="layout mudou"):
        normalizar(df, "CITO_COLO")


def test_quantidade_da_fonte_vence_a_contagem_por_linha(tmp_path):
    """Onde existe QT_EXAME, contar 1 por linha subestimaria — e para menos."""
    linhas = [{"CO_MUN_RESIDENCIA": "355030", "CO_ANO_COMPETENCIA": "2023",
               "CO_ANO_MES_COMPETENCIA": "202301", "QT_EXAME": "4"}] * 2
    df, _ = ler_em_blocos(_csv(tmp_path, linhas), "CITO_MAMA")
    assert int(df.iloc[0]["exames"]) == 8


def test_linha_sem_ano_nao_entra_como_zero(tmp_path):
    linhas = [_linha_competencia("355030", "2023", "01"),
              {"CO_MUN_RESIDENCIA": "355030", "CO_ANO_COMPETENCIA": "",
               "CO_ANO_MES_COMPETENCIA": ""}]
    df, lidas = ler_em_blocos(_csv(tmp_path, linhas), "HISTO_COLO")
    assert lidas == 2
    assert int(df["exames"].sum()) == 1, "linha sem ano virou exame"
