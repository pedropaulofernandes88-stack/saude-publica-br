"""
Servidor MCP do Saúde em Dado — a saúde do Brasil consultável por IA (custo zero)
==================================================================================

Expõe o dataset público (DataSUS 2015–2024 + IBGE) como ferramentas MCP, para que
assistentes de IA (Claude Desktop, Claude Code etc.) consultem — com os mesmos
números citáveis do site saudeemdado.com — mortalidade (SIM), internações (SIH),
dengue (SINAN), internações evitáveis (ICSAP), fluxo de pacientes, visão hospitalar,
excesso de mortalidade e a CONFIABILIDADE do registro por município.

Custo zero: roda na máquina do cliente (Claude Desktop) e consulta a API pública;
não há servidor a hospedar nem chave de LLM do mantenedor — cada usuário traz o seu
próprio Claude.

Instalação (Python 3.10+):

    pip install mcp requests

Claude Desktop (claude_desktop_config.json):

    {
      "mcpServers": {
        "saudeemdado": {
          "command": "python",
          "args": ["/caminho/para/saude-publica-br/mcp_server/server.py"]
        }
      }
    }

A chave embutida no cliente é pública por design (somente leitura via RLS).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clients" / "python"))
import saudeemdado as sd  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP(
    "saudeemdado",
    instructions=(
        "Dados oficiais de saúde no Brasil (DataSUS 2015–2024 + IBGE). REGRAS DE USO "
        "(número de saúde não admite invenção):\n"
        "1. NUNCA estime números de cabeça — sempre chame uma ferramenta e use o valor "
        "retornado. Se não há ferramenta para a pergunta, diga que não sabe.\n"
        "2. SEMPRE cite a fonte (DataSUS/MS e IBGE) e o ano; o ano de 2024 é preliminar.\n"
        "3. Ao comparar municípios em mortalidade, use taxa_padronizada_100k (ajustada "
        "por idade) — a taxa bruta engana; ela vem com IC95% (ic95_inf/ic95_sup).\n"
        "4. CONFIABILIDADE: antes de afirmar causas de morte de um município, consulte "
        "qualidade_registro; se a classe for 'Ruim', avise que a causa é pouco confiável.\n"
        "5. Excesso de mortalidade usa baseline por TENDÊNCIA 2015–2019 (não média). "
        "Dengue: caso provável = notificação não descartada; 2024 foi epidemia recorde.\n"
        "6. NÃO faça inferência causal, extrapolação além do dado, nem recomendação "
        "clínica individual. Estes dados são agregados/ecológicos e retrospectivos.\n"
        "Metodologia: https://saudeemdado.com/metodologia/"
    ),
)


# ── Mortalidade ──────────────────────────────────────────────────────────────
@mcp.tool()
def serie_mensal_obitos(uf: str = "", capitulo_cid: str = "TOTAL") -> list[dict]:
    """Série mensal de óbitos 2015–2024. uf vazio = todas as UFs (some para o Brasil).
    capitulo_cid: I a XXII ou TOTAL (IX = circulatório, X = respiratório, II = neoplasias)."""
    return sd.serie_mensal(uf=uf or None, capitulo=capitulo_cid)


@mcp.tool()
def municipios_indicadores(
    uf: str, ano: int = 2023, capitulo_cid: str = "TOTAL", populacao_minima: int = 10000
) -> list[dict]:
    """Indicadores municipais: óbitos, taxa bruta/100k com IC95% e taxa padronizada por
    idade (taxa_padronizada_100k — use esta para comparar municípios)."""
    return sd.municipios(uf=uf, ano=ano, capitulo=capitulo_cid, pop_min=populacao_minima)


@mcp.tool()
def principais_causas(uf: str = "", ano: int = 2024, top: int = 20) -> list[dict]:
    """Principais causas básicas de óbito (CID-10, 3 caracteres) no Brasil (uf vazio) ou UF.
    Atenção: R99 = causa mal-definida (ausência de diagnóstico), não é doença."""
    return sd.causas(uf=uf or None, ano=ano, top=top)


@mcp.tool()
def descricao_cid10(codigos: list[str]) -> dict[str, str]:
    """Descrições oficiais de categorias CID-10 de 3 caracteres (ex.: I21, C34)."""
    todos = {r["causabas_3"]: r["descricao"] for r in sd.cid10()}
    return {c.upper(): todos.get(c.upper(), "código não encontrado") for c in codigos}


@mcp.tool()
def excesso_mortalidade(uf: str = "BR") -> list[dict]:
    """Excesso de mortalidade mensal (2020+) por UF ou BR (Brasil): observado, esperado
    (baseline por TENDÊNCIA linear 2015–2019, que capta o envelhecimento), excesso e %.
    Pico pandêmico Brasil 2020–2021 ≈ 643 mil; 2024 ≈ zero (preliminar)."""
    return sd.excesso(uf=uf)


# ── Confiabilidade do dado (camada anti-alucinação) ─────────────────────────
@mcp.tool()
def qualidade_registro(municipio_cod: str = "", uf: str = "") -> list[dict]:
    """CONFIABILIDADE do registro de óbitos (2022–2024): % de causas mal-definidas e
    classe (Bom <5% | Regular 5–10% | Ruim >10%). Consulte ANTES de afirmar causas de
    morte de um município. Informe municipio_cod (6 dígitos) OU uf."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,obitos_total,"
                  "obitos_mal_definidas,pct_mal_definidas,classificacao",
        "order": "pct_mal_definidas.desc",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_qualidade_registro_municipio", params)


# ── Internações (SIH) ────────────────────────────────────────────────────────
@mcp.tool()
def internacoes_municipios(uf: str = "", ano: int = 2024, capitulo_cid: str = "TOTAL") -> list[dict]:
    """Internações SUS (SIH/AIH) por município: volume, permanência média, mortalidade
    intra-hospitalar (%) e custo médio (R$). Cobre só a rede SUS."""
    return sd.internacoes(uf=uf or None, ano=ano, capitulo=capitulo_cid)


@mcp.tool()
def internacoes_evitaveis_icsap(uf: str = "") -> list[dict]:
    """ICSAP — internações por condições sensíveis à atenção primária, por município (2024):
    total, ICSAP, % e por 100k hab. Proporção alta sinaliza fragilidade da atenção básica;
    é indicador de sistema, não de 'má gestão' local."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,internacoes_total,"
                  "internacoes_icsap,pct_icsap,icsap_100k,populacao",
        "ano": "eq.2024", "order": "municipio_cod",
    }
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_icsap_municipio", params)


@mcp.tool()
def internacoes_por_agravo(uf: str = "", agravo: str = "") -> list[dict]:
    """Internações por agravo traçador (CID-3), por município (2024): diabetes, avc, iam,
    icc, asma, dpoc, pneumonia, depressao, esquizofrenia, alcool_drogas, tce. agravo vazio =
    todos. Traz permanência, mortalidade e custo por agravo."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,agravo,agravo_label,grupo,"
                  "internacoes,obitos,permanencia_media,mortalidade_pct,custo_medio,internacoes_100k",
        "order": "municipio_cod",
    }
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    if agravo:
        params["agravo"] = f"eq.{agravo.lower()}"
    return sd._get("mart_internacoes_agravo", params)


@mcp.tool()
def hospitais(uf: str = "", ordenar_por: str = "internacoes", top: int = 50) -> list[dict]:
    """Visão por estabelecimento (CNES), 2024: volume, permanência, mortalidade, custo e
    capítulo predominante. ordenar_por: internacoes | mortalidade_pct | permanencia_media |
    custo_medio. Mortalidade é BRUTA (sem ajuste de risco/case-mix) — não comparar como
    qualidade. Sem nome do estabelecimento (só CNES)."""
    params = {
        "select": "cnes,municipio_nome,uf_sigla,capitulo_principal,internacoes,"
                  "permanencia_media,mortalidade_pct,custo_medio",
        "ano": "eq.2024", "internacoes": "gte.50",
        "order": f"{ordenar_por}.desc", "limit": str(top),
    }
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_internacoes_hospital", params)


@mcp.tool()
def fluxo_pacientes(municipio_res_cod: str) -> list[dict]:
    """Para onde os moradores de um município viajam para se internar (SIH 2024, fluxos ≥ 5).
    Revela dependência de polos regionais e evasão da rede local. Informe o código de 6
    dígitos do município de residência."""
    params = {
        "select": "municipio_mov,municipio_mov_nome,uf_mov,internacoes",
        "municipio_res": f"eq.{municipio_res_cod}", "ano": "eq.2024",
        "order": "internacoes.desc",
    }
    return sd._get("mart_fluxo_intermunicipal", params)


# ── Dengue (SINAN) ───────────────────────────────────────────────────────────
@mcp.tool()
def dengue_municipios(uf: str = "", ano: int = 2024) -> list[dict]:
    """Dengue (SINAN) por município/ano: casos prováveis, graves, óbitos, incidência/100k e
    letalidade. 2024 foi epidemia recorde (6,56 milhões de casos)."""
    return sd.dengue(uf=uf or None, ano=ano, nivel="ano")


@mcp.tool()
def dengue_semanal(uf: str, ano: int = 2024) -> list[dict]:
    """Dengue (SINAN) por semana epidemiológica de uma UF/ano — curvas sazonais e picos."""
    return sd.dengue(uf=uf, ano=ano, nivel="semana")


# ── Copiloto: anomalias ──────────────────────────────────────────────────────
@mcp.tool()
def detectar_anomalias(municipio_cod: str) -> dict:
    """COPILOTO: dado um município (6 dígitos), retorna um resumo priorizado de sinais —
    confiabilidade do registro, ICSAP vs. média nacional (~21%), e letalidade de dengue —
    para um briefing de gestor. Cada sinal traz o valor e a fonte; interprete com as regras
    de uso (sem causalidade; sinalizar baixa confiabilidade)."""
    achados = []
    q = sd._get("mart_qualidade_registro_municipio",
                {"select": "municipio_nome,uf_sigla,pct_mal_definidas,classificacao",
                 "municipio_cod": f"eq.{municipio_cod}"})
    nome = q[0]["municipio_nome"] if q else municipio_cod
    if q and q[0]["classificacao"] == "Ruim":
        achados.append({"sinal": "qualidade_registro", "gravidade": "alta",
                        "detalhe": f"registro RUIM ({q[0]['pct_mal_definidas']}% mal-definidas) — "
                                   "causas de morte pouco confiáveis", "fonte": "SIM 2022–2024"})
    ic = sd._get("mart_icsap_municipio",
                 {"select": "pct_icsap,internacoes_total,internacoes_icsap",
                  "municipio_cod": f"eq.{municipio_cod}", "ano": "eq.2024"})
    if ic and ic[0].get("pct_icsap") is not None:
        p = float(ic[0]["pct_icsap"])
        if p > 30 and (ic[0]["internacoes_total"] or 0) >= 200:
            achados.append({"sinal": "icsap", "gravidade": "média" if p < 40 else "alta",
                            "detalhe": f"{p:.1f}% de internações evitáveis (média nacional ~21%) — "
                                       "possível fragilidade da atenção primária", "fonte": "SIH 2024"})
    dg = sd._get("mart_dengue_municipio_ano",
                 {"select": "casos_provaveis,obitos,letalidade_pct,incidencia_100k",
                  "municipio_cod": f"eq.{municipio_cod}", "ano_epi": "eq.2024"})
    if dg and (dg[0].get("obitos") or 0) > 0:
        achados.append({"sinal": "dengue", "gravidade": "média",
                        "detalhe": f"{dg[0]['casos_provaveis']} casos e {dg[0]['obitos']} óbitos por dengue "
                                   f"(letalidade {dg[0].get('letalidade_pct')}%)", "fonte": "SINAN 2024"})
    return {"municipio": nome, "codigo": municipio_cod,
            "n_sinais": len(achados), "sinais": achados or [{"sinal": "nenhum",
            "detalhe": "sem anomalias nos limiares avaliados"}]}


@mcp.tool()
def metadados_dataset() -> dict[str, str]:
    """Fontes, metodologia resumida, exclusões, licença, DOI e versão do dataset."""
    return sd.metadados()


if __name__ == "__main__":
    mcp.run()
