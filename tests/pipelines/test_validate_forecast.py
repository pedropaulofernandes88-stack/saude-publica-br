"""Testes da régua de publicação do forecast (`scripts/validate_forecast.py`).

POR QUE ESTES TESTES EXISTEM
----------------------------
O cabeçalho do script sempre disse que "um modelo que não passa a régua não
deveria ser publicado". Era uma frase: até 2026-09-02 o script media, escrevia o
relatório e saía com código 0 qualquer que fosse o resultado. Ninguém o
executava — nem o CI, nem esta suíte —, e a última validação era treze horas
mais velha que o forecast que estava no ar.

Três defeitos somados, e cada um sozinho já bastaria: critério declarado e não
aplicado, verificação fora de toda automação, e veredito mais velho que o
artefato julgado.

O que se testa aqui é a parte automatizável — que `conferir_regua` REPROVE. Rodar
o backtest completo custa minutos e lê um mart de 19 MB, então não entra na
suíte; o que entra é a decisão que ele toma no fim, alimentada por linhas
sintéticas. É a mesma divisão de `test_mortalidade_causa_municipio.py`: a guarda
é testada nos dois sentidos, porque guarda que só foi vista aprovando não é
guarda.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


def _carregar():
    """Importa o script sem rodar o backtest.

    O módulo precisa entrar em `sys.modules` ANTES de `exec_module`: ele define
    um `@dataclass`, e `dataclasses` resolve as anotações consultando
    `sys.modules[cls.__module__]`. Sem o registro, a importação quebra com
    `'NoneType' object has no attribute '__dict__'` — descoberto quebrando.
    """
    sys.path.insert(0, str(RAIZ / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "validate_forecast", RAIZ / "scripts" / "validate_forecast.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["validate_forecast"] = mod
    spec.loader.exec_module(mod)
    return mod


vf = _carregar()


def _linha(horizonte: int, mase: float, cobertura: float = 95.0,
           modelo: str | None = None) -> dict:
    return {"modelo": modelo or vf.MODELO_ATUAL,
            "horizonte_meses": horizonte,
            "mase": mase,
            "cobertura_ic95_pct": cobertura}


# --------------------------------------------------------------------------
# 1. a régua reprova — que é o caso que ela existe para cobrir
# --------------------------------------------------------------------------
def test_modelo_que_nao_supera_o_baseline_derruba_a_execucao():
    """MASE >= 1 significa que o ingênuo sazonal é tão bom quanto o modelo."""
    with pytest.raises(SystemExit, match="REPROVADO"):
        vf.conferir_regua([_linha(1, 1.02)], (1,))


def test_mase_exatamente_um_reprova_porque_o_criterio_e_estrito():
    """A régua é MASE < 1, não <= 1: empatar com o baseline não é superá-lo."""
    with pytest.raises(SystemExit, match="REPROVADO"):
        vf.conferir_regua([_linha(1, 1.0)], (1,))


def test_mase_nao_finito_reprova_em_vez_de_escapar():
    """NaN passaria calado por qualquer comparação `>=` escrita sem cuidado.

    `float('nan') >= 1.0` é False — sem o teste de finitude, uma série
    degenerada seria lida como modelo aprovado.
    """
    with pytest.raises(SystemExit, match="REPROVADO"):
        vf.conferir_regua([_linha(1, float("nan"))], (1,))


def test_reprovar_em_um_horizonte_basta():
    """Passar em 1 e 2 meses não compra o horizonte de 3.

    Uma métrica agregada esconderia isso, que é exatamente a deterioração de
    horizonte longo que o relatório separa de propósito.
    """
    with pytest.raises(SystemExit, match="3m"):
        vf.conferir_regua([_linha(1, 0.80), _linha(2, 0.90), _linha(3, 1.10)],
                          (1, 2, 3))


def test_modelo_publicado_ausente_dos_resultados_reprova():
    """Se o modelo no ar não foi avaliado, a validação não julgou nada."""
    with pytest.raises(SystemExit, match="não aparece nos resultados"):
        vf.conferir_regua([_linha(1, 0.5, modelo="outro_modelo")], (1,))


# --------------------------------------------------------------------------
# 2. a régua aprova quando deve, e não inventa reprovação
# --------------------------------------------------------------------------
def test_modelo_que_supera_o_baseline_passa(monkeypatch):
    registrados: list[tuple[str, float]] = []
    monkeypatch.setattr(vf, "registrar",
                        lambda c, v, **kw: registrados.append((c, v)))
    vf.conferir_regua([_linha(1, 0.81, 89.0), _linha(2, 0.87, 86.8),
                       _linha(3, 0.92, 85.0)], (1, 2, 3))
    chaves = {c for c, _ in registrados}
    assert chaves == {f"forecast_{m}_h{h}"
                      for h in (1, 2, 3)
                      for m in ("mase", "cobertura_ic95")}


def test_subcobertura_do_intervalo_nao_reprova(monkeypatch):
    """O IC95% entrega 85–89%, e isso NÃO derruba a execução de propósito.

    A régua declarada do projeto é o MASE. Apertar o intervalo muda o que a
    plataforma promete ao leitor — é decisão científica, não automatizável.
    A subcobertura é impressa em destaque e vai para `achados.json`; quem
    decide é uma pessoa.
    """
    monkeypatch.setattr(vf, "registrar", lambda *a, **k: None)
    vf.conferir_regua([_linha(1, 0.81, 50.0)], (1,))   # cobertura péssima, MASE bom


# --------------------------------------------------------------------------
# 3. as métricas ficam sob a guarda de frescor
# --------------------------------------------------------------------------
def test_registra_citando_o_mart_do_forecast(monkeypatch):
    """É este detalhe que conserta o defeito original.

    `_achados.desatualizados()` compara a mtime de cada mart citado com o
    instante do cálculo. Citar `mart_forecast_demanda_hospital` é o que faz
    "forecast regerado sem revalidar" virar teste vermelho — antes disso, a
    validação podia ficar treze horas atrás do artefato sem que nada acusasse.
    """
    fontes_vistas: list[list[str]] = []
    monkeypatch.setattr(vf, "registrar",
                        lambda c, v, *, fontes, descricao: fontes_vistas.append(fontes))
    vf.conferir_regua([_linha(1, 0.81)], (1,))
    assert fontes_vistas, "nenhuma métrica foi registrada"
    for fontes in fontes_vistas:
        assert "mart_forecast_demanda_hospital" in fontes
