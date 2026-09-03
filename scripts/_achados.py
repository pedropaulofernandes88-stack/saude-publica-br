"""Registro legível por máquina dos coeficientes que o site publica.

POR QUE ISTO EXISTE
-------------------
Os achados do projeto viram prosa: "ρ = +0,32", "17,7% contra 21,4%". Prosa não
tem quem a contradiga, e por isso envelhece em silêncio — foi o que aconteceu
quando a Lista Brasileira de ICSAP foi corrigida em 2026-08-31 e os coeficientes
publicados passaram a descrever um dado que não existia mais.

`tests/test_numeros_do_site.py` já compara tabelas, testes e fontes contra uma
fonte de verdade. Coeficiente não tinha nenhuma: recalculá-lo dentro do teste
duplicaria a lógica da análise, e duas cópias divergem.

A saída aqui é essa fonte. Quem calcula continua sendo o script de análise — ele
apenas passa a gravar o que já imprimia. O teste compara site × este arquivo, e
confere se o arquivo é mais novo que os dados que o originaram.

O CARIMBO DE FRESCOR É O PONTO
------------------------------
Guardar o número não basta: o defeito real não foi número errado, foi análise
não refeita depois de o dado mudar. Por isso cada achado grava a mtime dos
Parquet que leu. Se um mart for regravado e a análise não rodar de novo, o teste
reprova — que é exatamente o caso que passou despercebido.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARQUIVO = ROOT / "data" / "marts" / "achados.json"


def registrar(chave: str, valor: float, *, fontes: list[str], descricao: str) -> None:
    """Grava um coeficiente publicado, com o frescor dos dados que o geraram.

    `fontes` são nomes de mart (sem extensão). A mtime de cada um viaja junto:
    é o que permite detectar análise velha sobre dado novo.
    """
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    dados: dict = {}
    if ARQUIVO.exists():
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))

    marts = {}
    for nome in fontes:
        caminho = ROOT / "data" / "marts" / f"{nome}.parquet"
        if caminho.exists():
            marts[nome] = caminho.stat().st_mtime

    dados[chave] = {
        "valor": round(float(valor), 3),
        "descricao": descricao,
        "calculado_em": datetime.now().isoformat(timespec="seconds"),
        "marts": marts,
    }
    ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=1, sort_keys=True),
                       encoding="utf-8")


def esquecer(*chaves: str) -> list[str]:
    """Remove achados que o código não produz mais.

    `registrar` só escreve; uma chave renomeada fica órfã no arquivo para
    sempre. A guarda de frescor a acusa (foi como `perfil_silhueta_k3`
    apareceu depois de virar `perfil_silhueta`), mas acusar não limpa — e um
    achado órfão só some quando alguém o apaga de propósito.
    """
    if not ARQUIVO.exists():
        return []
    dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    removidas = [c for c in chaves if c in dados]
    for c in removidas:
        del dados[c]
    if removidas:
        ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=1, sort_keys=True),
                           encoding="utf-8")
    return removidas


def carregar() -> dict:
    if not ARQUIVO.exists():
        return {}
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def desatualizados() -> list[str]:
    """Achados cujo mart foi regravado depois do cálculo.

    Devolve as chaves em que a análise ficou para trás do dado — o defeito que
    motivou este módulo.
    """
    atrasados = []
    for chave, reg in carregar().items():
        for nome, mtime_registrada in (reg.get("marts") or {}).items():
            caminho = ROOT / "data" / "marts" / f"{nome}.parquet"
            if caminho.exists() and caminho.stat().st_mtime > mtime_registrada + 1:
                atrasados.append(f"{chave} (mart {nome} é mais novo que o cálculo)")
                break
    return atrasados
