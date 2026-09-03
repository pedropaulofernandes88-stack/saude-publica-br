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


# ── coeficientes ─────────────────────────────────────────────────────────────
# Um coeficiente publicado tem duas formas de envelhecer, e a segunda é a que
# passou despercebida: (a) alguém edita o texto e erra, ou (b) o DADO muda e a
# análise não é refeita. A correção da Lista Brasileira de ICSAP em 2026-08-31
# foi o caso (b) — os coeficientes descreviam um dado que deixara de existir.
#
# O valor de verdade vem de `data/marts/achados.json`, gravado pelos próprios
# scripts de análise (ver scripts/_achados.py). Recalcular aqui duplicaria a
# lógica da análise, e duas cópias divergem.
COEFICIENTES = {
    # chave em achados.json -> (arquivo do site, regex, casas decimais)
    "aps_x_icsap_bruta": (SOBRE, r"ρ = ([+-]\d,\d+); [+-]\d,\d+ controlando", 3),
    "aps_x_icsap_parcial": (SOBRE, r"ρ = [+-]\d,\d+; ([+-]\d,\d+) controlando", 3),
}


def _achados() -> dict:
    caminho = RAIZ / "data" / "marts" / "achados.json"
    if not caminho.exists():
        pytest.skip("sem achados.json — rode os scripts de análise")
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.mark.parametrize("chave", sorted(COEFICIENTES))
def test_coeficiente_publicado_bate_com_a_analise(chave):
    reg = _achados().get(chave)
    if reg is None:
        pytest.skip(f"{chave} ainda não foi registrado por nenhuma análise")
    caminho, padrao, casas = COEFICIENTES[chave]
    m = re.search(padrao, _texto(caminho))
    assert m, f"não achei {chave} em {caminho.name} com o padrão {padrao!r}"
    declarado = float(m.group(1).replace(",", "."))
    real = round(reg["valor"], casas)
    assert abs(declarado - real) < 10 ** -casas / 2, (
        f"{chave}: o site declara {declarado:+.3f} e a análise calculou {real:+.3f}. "
        f"Recalculado em {reg['calculado_em']}."
    )


def test_nenhuma_analise_ficou_atras_do_dado():
    """O defeito que motivou tudo isto: mart regravado, análise não refeita.

    Não confere valor — confere FRESCOR. Um coeficiente pode estar copiado
    corretamente e ainda assim descrever dado que não existe mais.
    """
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _achados import desatualizados  # noqa: PLC0415

    atrasados = desatualizados()
    assert not atrasados, (
        "análise mais velha que o mart que ela leu — rodar de novo os scripts "
        f"analise_*.py: {'; '.join(atrasados)}"
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



# --------------------------------------------------------------------------
# Rótulo de estado não pode depender de ano escrito à mão
#
# Mesmo defeito da classe acima, num disfarce: em vez de um número copiado, uma
# CONDIÇÃO copiada. `a === 2024 ? " (preliminar)"` estava certo quando foi
# escrito e passou a mentir em 2026-09-03, quando 2024 consolidou e 2025 entrou.
# O site ficou anunciando exatamente o inverso da verdade — 2024 marcado como
# preliminar, 2025 sem marca — e ninguém viu, porque a linha não quebrou nada.
#
# Fato histórico cravado é legítimo: "2024 (epidemia recorde)" continua verdade
# para sempre. O que não pode é ESTADO — preliminar, provisório, parcial —,
# porque estado muda e o literal não acompanha.
# --------------------------------------------------------------------------
ESTADOS_QUE_MUDAM = ("preliminar", "provisório", "provisorio", "parcial",
                     "incompleto", "atual", "corrente")

def test_nenhum_rotulo_de_estado_preso_a_ano_literal():
    ofensas = []
    for tsx in sorted((RAIZ / "site" / "app").rglob("*.tsx")):
        for n, linha in enumerate(_texto(tsx).splitlines(), 1):
            if not re.search(r"===\s*20\d\d\s*\?", linha):
                continue
            if any(e in linha.lower() for e in ESTADOS_QUE_MUDAM):
                ofensas.append(f"{tsx.relative_to(RAIZ)}:{n}: {linha.strip()[:110]}")
    assert not ofensas, (
        "rótulo de estado comparado a ano literal — use ehPreliminar() (mortalidade) "
        "ou derive do próprio vetor de anos (Math.max(...ANOS_X)):\n  "
        + "\n  ".join(ofensas))
