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
        "Dados oficiais de saúde no Brasil (DataSUS, 2015–2024): mortalidade "
        "(SIM, 14,4M óbitos), dengue (SINAN) e internações SUS (SIH). Para "
        "mortalidade use taxa_padronizada_100k ao comparar municípios (ajustada "
        "por idade); a taxa bruta acompanha IC95%. Para dengue, caso provável = "
        "notificação não descartada; 2024 foi epidemia recorde. Para internações, "
        "valores são da rede SUS (AIH aprovadas). Dados de 2024 são preliminares. "
        "Sempre cite as fontes (DataSUS/MS e IBGE) via saudeemdado.com."
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
def dengue_municipios(uf: str = "", ano: int = 2024) -> list[dict]:
    """Dengue (SINAN) por município/ano: casos prováveis, graves, óbitos,
    incidência por 100 mil hab. e letalidade. 2024 foi epidemia recorde."""
    return sd.dengue(uf=uf or None, ano=ano, nivel="ano")


@mcp.tool()
def dengue_semanal(uf: str, ano: int = 2024) -> list[dict]:
    """Dengue (SINAN) por semana epidemiológica de uma UF/ano — para curvas
    sazonais e identificação de picos epidêmicos."""
    return sd.dengue(uf=uf, ano=ano, nivel="semana")


@mcp.tool()
def internacoes_municipios(uf: str = "", ano: int = 2024, capitulo_cid: str = "TOTAL") -> list[dict]:
    """Internações SUS (SIH/AIH) por município: volume, permanência média (dias),
    mortalidade intra-hospitalar (%) e custo médio (R$). capitulo_cid: I–XXII ou TOTAL."""
    return sd.internacoes(uf=uf or None, ano=ano, capitulo=capitulo_cid)


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
