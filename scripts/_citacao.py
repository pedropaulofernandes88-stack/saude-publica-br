"""
_citacao.py — a forma de citar, derivada do CITATION.cff
=========================================================

POR QUE ISTO EXISTE
-------------------
A citação sugerida do projeto estava escrita à mão em `site/app/dados/page.tsx`,
e os mesmos dados estruturados estavam em `CITATION.cff` — duas cópias, e a
segunda é a que o GitHub e os gerenciadores de referência leem. Duas cópias da
mesma frase divergem em silêncio, e nesta em particular a divergência é cara:
o DOI ou o nome do autor errados numa citação copiada por terceiro não voltam.

Pior: a citação não estava em lugar nenhum que viajasse COM O DADO. Quem usa a
API ou o MCP recebia números sem nada que dissesse de onde vieram nem como
creditar — e a licença dos marts derivados é CC BY 4.0, em que atribuição é
condição, não favor. Uso sem citação não é má-fé do usuário quando nada no
caminho do dado diz como citar.

O CFF é a fonte. Daqui a frase vai para `meta_dataset`, e de lá para a API, o
MCP e o cliente Python — uma escrita, três consumidores.

POR QUE UM LEITOR PRÓPRIO E NÃO PyYAML
---------------------------------------
São cinco campos de um arquivo que o próprio projeto escreve, e `pyyaml` não
está declarado em `requirements-test.txt` — a dependência entraria só para ler
`title:` e `doi:`. O leitor abaixo é estrito de propósito: campo ausente levanta,
em vez de produzir uma citação incompleta que ninguém notaria.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFF = ROOT / "CITATION.cff"


def _campo(texto: str, nome: str) -> str:
    """O valor de uma chave de primeiro nível do CFF, sem aspas."""
    m = re.search(rf'^{nome}:\s*"?([^"\n]+)"?\s*$', texto, re.M)
    if not m:
        raise ValueError(f"CITATION.cff sem o campo obrigatório `{nome}`")
    return m.group(1).strip()


def _primeiro_autor(texto: str) -> str:
    """`Fernandes, P. P.` — sobrenome e iniciais, como a citação usa."""
    fam = re.search(r"^\s*-\s*family-names:\s*(.+)$", texto, re.M)
    giv = re.search(r"^\s*given-names:\s*(.+)$", texto, re.M)
    if not fam or not giv:
        raise ValueError("CITATION.cff sem family-names/given-names do primeiro autor")
    sobrenome = fam.group(1).strip()
    iniciais = " ".join(f"{p[0]}." for p in giv.group(1).strip().split() if p)
    return f"{sobrenome}, {iniciais}"


def dados_da_citacao() -> dict[str, str]:
    """Os campos crus do CFF que a citação usa."""
    texto = CFF.read_text(encoding="utf-8")
    return {
        "autor": _primeiro_autor(texto),
        "titulo": _campo(texto, "title"),
        "doi": _campo(texto, "doi"),
        "url": _campo(texto, "url"),
    }


def como_citar() -> str:
    """A frase única, em uma linha, que acompanha o dado onde ele for.

    Uma linha porque ela viaja dentro de JSON, de resposta de ferramenta e de
    CSV — quebra de linha vira `\\n` visível em metade desses lugares.
    """
    d = dados_da_citacao()
    return (
        f"{d['autor']} {d['titulo']}. {d['url']} · DOI: {d['doi']}. "
        "Fontes primárias: DATASUS/Ministério da Saúde e IBGE. "
        "Marts derivados sob CC BY 4.0 — o uso exige atribuição."
    )


#: A licença, dita por extenso. A versão anterior em `meta_dataset` dizia
#: "uso livre com citação das fontes", que omite duas coisas que importam:
#: a licença TEM nome (CC BY 4.0) e a atribuição é CONDIÇÃO, não cortesia.
LICENCA = (
    "Dados originais em domínio público (DATASUS/MS e IBGE). Agregações e marts "
    "derivados sob CC BY 4.0: uso livre, inclusive comercial, COM ATRIBUIÇÃO "
    "obrigatória. Código sob MIT."
)


def linhas_meta() -> list[tuple[str, str]]:
    """As chaves de citação para `meta_dataset`, prontas para gravar."""
    d = dados_da_citacao()
    return [
        ("como_citar", como_citar()),
        ("doi", d["doi"]),
        ("licenca", LICENCA),
    ]


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for chave, valor in linhas_meta():
        print(f"{chave}\n  {valor}\n")
