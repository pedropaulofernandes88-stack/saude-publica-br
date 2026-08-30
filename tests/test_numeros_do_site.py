"""Os números que o site AFIRMA precisam bater com os que ele TEM.

Esta guarda nasceu de três casos no mesmo dia. O site anunciava 547 testes
tendo 556; `docs/ARQUITETURA_DADOS.md` descrevia 4,2 milhões de linhas em 36
tabelas quando eram 4,37 milhões em 37; o deck e os PDFs diziam nove fontes
depois de a décima entrar. Nenhum deles quebrou nada — número em prosa não tem
quem o contradiga, e por isso envelhece em silêncio.

O padrão é sempre o mesmo: alguém mede, copia o resultado para um texto, e a
medida segue andando sem o texto. A correção pontual não resolve a classe; a
guarda resolve.

O que se pode derivar de uma fonte de verdade é derivado aqui:

  tabelas  <- manifesto de publicação (data/publicacoes/atual.json)
  testes   <- coleta real do pytest
  fontes   <- não há lista canônica legível por máquina, então a checagem é de
              CONSISTÊNCIA INTERNA: as três declarações no site têm de
              concordar entre si e com a lista de siglas de /sobre

A checagem de fontes é mais fraca de propósito. Inventar um
`data/refs/fontes.json` só para ter o que conferir criaria mais um número
escrito à mão para envelhecer — trocaria o problema de lugar em vez de
resolvê-lo. Consistência entre três lugares já teria pego o defeito real: um
revisor encontrou o site dizendo cinco fontes enquanto o PDF dizia oito.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
HOME = RAIZ / "site" / "app" / "page.tsx"
SOBRE = RAIZ / "site" / "app" / "sobre" / "page.tsx"
PUBLICACOES = RAIZ / "data" / "publicacoes"

# Só os números que este projeto de fato escreve por extenso.
POR_EXTENSO = {
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
}


def _texto(caminho: Path) -> str:
    if not caminho.exists():
        pytest.skip(f"{caminho.relative_to(RAIZ)} não existe nesta árvore")
    return caminho.read_text(encoding="utf-8")


def _manifesto_atual() -> dict:
    atual = PUBLICACOES / "atual.json"
    if not atual.exists():
        pytest.skip("sem publicação local para conferir")
    ponteiro = json.loads(atual.read_text(encoding="utf-8"))
    return json.loads((PUBLICACOES / ponteiro["arquivo"]).read_text(encoding="utf-8"))


def _declarado_na_home() -> tuple[int, int]:
    """(tabelas, fontes) do cartão 'N tabelas · M fontes'."""
    m = re.search(r"(\d+)\s+tabelas\s*·\s*(\d+)\s+fontes", _texto(HOME))
    assert m, "a home não declara mais 'N tabelas · M fontes' — a guarda precisa saber onde olhar"
    return int(m.group(1)), int(m.group(2))


def test_tabelas_declaradas_batem_com_o_manifesto():
    tabelas, _ = _declarado_na_home()
    real = len(_manifesto_atual()["tabelas"])
    assert tabelas == real, (
        f"a home anuncia {tabelas} tabelas e o manifesto publicado tem {real}. "
        f"Corrigir o cartão em site/app/page.tsx."
    )


def test_fontes_sao_consistentes_entre_as_declaracoes_do_site():
    _, fontes_home = _declarado_na_home()
    sobre = _texto(SOBRE)

    m = re.search(r'\["(\d+)\s+fontes",\s*"([^"]+)"\]', sobre)
    assert m, "/sobre não declara mais '[N fontes, lista]' — a guarda precisa saber onde olhar"
    fontes_sobre, lista = int(m.group(1)), m.group(2)
    siglas = [s.strip() for s in lista.split("·") if s.strip()]

    palavra = re.search(r"(\w+) fontes integradas em (\d+) tabelas", sobre)
    assert palavra, "a linha de comparação de /sobre mudou de forma"
    fontes_prosa = POR_EXTENSO.get(palavra.group(1).lower())
    assert fontes_prosa, f"número por extenso desconhecido: {palavra.group(1)!r}"
    tabelas_prosa = int(palavra.group(2))

    assert fontes_home == fontes_sobre == len(siglas) == fontes_prosa, (
        f"contagem de fontes divergente — home={fontes_home}, /sobre cartão={fontes_sobre}, "
        f"siglas listadas={len(siglas)} ({', '.join(siglas)}), prosa={fontes_prosa}"
    )
    tabelas_home, _ = _declarado_na_home()
    assert tabelas_prosa == tabelas_home, (
        f"a prosa de /sobre diz {tabelas_prosa} tabelas e a home diz {tabelas_home}"
    )


def _coletar_testes() -> int:
    """Conta os testes que o pytest coleta, num processo separado.

    Processo separado, e não `pytest.main` aqui dentro, porque coletar de
    dentro de uma sessão em andamento mexe em estado global do pytest.
    """
    codigo = (
        "import io,contextlib,pytest\n"
        "class C:\n"
        "    def __init__(self): self.n=0\n"
        "    def pytest_collection_modifyitems(self, items): self.n=len(items)\n"
        "c=C()\n"
        "b=io.StringIO()\n"
        "with contextlib.redirect_stdout(b), contextlib.redirect_stderr(b):\n"
        "    pytest.main(['tests/','--collect-only','-q','-p','no:cacheprovider'], plugins=[c])\n"
        "print(c.n)\n"
    )
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ,
                       capture_output=True, text=True, timeout=600)
    saida = (r.stdout or "").strip().splitlines()
    if not saida or not saida[-1].isdigit():
        pytest.skip(f"não foi possível coletar: {(r.stderr or r.stdout)[-200:]}")
    return int(saida[-1])


def test_testes_declarados_batem_com_a_coleta():
    m = re.search(r'\["(\d+)\s+testes"', _texto(HOME))
    assert m, "a home não declara mais 'N testes' — a guarda precisa saber onde olhar"
    declarado = int(m.group(1))
    real = _coletar_testes()
    assert declarado == real, (
        f"a home anuncia {declarado} testes e a suíte tem {real}. "
        f"Corrigir o cartão em site/app/page.tsx. "
        f"Falhar aqui ao adicionar um teste é o comportamento pretendido: "
        f"é o que impede o número de envelhecer."
    )

