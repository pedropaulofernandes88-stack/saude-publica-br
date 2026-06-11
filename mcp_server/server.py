"""
Servidor MCP do Saúde em Dado — pesquise a mortalidade brasileira via IA
=========================================================================

Expõe o dataset público (SIM/DataSUS 2015–2024, 14,4M óbitos) como ferramentas
MCP, permitindo que assistentes de IA (Claude Desktop, Claude Code etc.)
consultem séries, rankings municipais, causas CID-10 e excesso de mortalidade
diretamente — com os mesmos números citáveis do site saudeemdado.com.

Instalação e uso (requer Python 3.10+):

    pip install mcp requests

Configuração no Claude Desktop (claude_desktop_config.json):

    {
      "mcpServers": {
        "saudeemdado": {
          "command": "python",
          "args": ["/caminho/para/saude-publica-br/mcp_server/server.py"]
        }
      }
    }

A chave embutida é pública por design (somente leitura via RLS).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Reutiliza o cliente oficial
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clients" / "python"))
import saudeemdado as sd  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP(
    "saudeemdado",
    instructions=(
        "Dados oficiais de mortalidade no Brasil (SIM/DataSUS, 2015–2024; "
        "14,4M óbitos não fetais). Use taxa_padronizada_100k para comparar "
        "municípios (ajustada por idade); a taxa bruta acompanha IC95%. "
        "Dados de 2024 são preliminares. Detalhe por sexo/faixa etária só a "
        "partir de 2022. Sempre cite: SIM/DataSUS (MS) e IBGE, via saudeemdado.com."
    ),
)


@mcp.tool()
def serie_mensal_obitos(uf: str = "", capitulo_cid: str = "TOTAL") -> list[dict]:
    """Série mensal de óbitos 2015–2024. uf vazio = todas as UFs (some para
    obter o Brasil). capitulo_cid: I a XXII ou TOTAL (ex.: IX = circulatório,
    X = respiratório, XX = causas externas, II = neoplasias)."""
    return sd.serie_mensal(uf=uf or None, capitulo=capitulo_cid)


@mcp.tool()
def municipios_indicadores(
    uf: str, ano: int = 2023, capitulo_cid: str = "TOTAL", populacao_minima: int = 10000
) -> list[dict]:
    """Indicadores municipais de um estado/ano: óbitos, população, taxa bruta
    por 100 mil hab. com IC95% (ic95_inf/ic95_sup) e taxa padronizada por idade
    (taxa_padronizada_100k — use esta para comparar municípios)."""
    return sd.municipios(uf=uf, ano=ano, capitulo=capitulo_cid, pop_min=populacao_minima)


@mcp.tool()
def principais_causas(uf: str = "", ano: int = 2023, top: int = 20) -> list[dict]:
    """Principais causas básicas de óbito (CID-10, 3 caracteres) de um ano,
    no Brasil (uf vazio) ou em uma UF. Use descricao_cid10 para os nomes."""
    return sd.causas(uf=uf or None, ano=ano, top=top)


@mcp.tool()
def descricao_cid10(codigos: list[str]) -> dict[str, str]:
    """Descrições oficiais de categorias CID-10 de 3 caracteres (ex.: I21, C34)."""
    todos = {r["causabas_3"]: r["descricao"] for r in sd.cid10()}
    return {c.upper(): todos.get(c.upper(), "código não encontrado") for c in codigos}


@mcp.tool()
def excesso_mortalidade(uf: str = "BR") -> list[dict]:
    """Excesso de mortalidade mensal (2020+) vs baseline 2015–2019 ajustado por
    população: observado, esperado, excesso e % — por UF ou BR (Brasil)."""
    return sd.excesso(uf=uf)


@mcp.tool()
def metadados_dataset() -> dict[str, str]:
    """Fontes, metodologia resumida, exclusões, licença e versão do dataset."""
    return sd.metadados()


if __name__ == "__main__":
    mcp.run()
