"""
saudeemdado-mcp — a saúde do Brasil (DataSUS + IBGE) consultável por IA
=======================================================================

Servidor MCP que expõe o dataset público do Saúde em Dado como ferramentas para
assistentes de IA (Claude Desktop, Claude Code etc.), com os mesmos números
citáveis do site saudeemdado.com e regras anti-alucinação (todo número vem de uma
ferramenta, com a fonte citada).

Instalação:
    uvx saudeemdado-mcp            # ou: pip install saudeemdado-mcp
Config Claude Desktop:
    { "mcpServers": { "saudeemdado": { "command": "uvx", "args": ["saudeemdado-mcp"] } } }
"""
from __future__ import annotations

import sys
from pathlib import Path

try:  # instalado via pip/uvx: o cliente é uma dependência
    import saudeemdado as sd
except ImportError:  # rodando do repositório clonado sem instalar: usa o cliente local
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "clients" / "python"))
    import saudeemdado as sd

import requests
from mcp.server import MCPServer

__version__ = "0.4.0"

# A 2.0.0 do SDK renomeou FastMCP para MCPServer e removeu mcp.server.fastmcp.
# A API de decorators nao mudou: as 19 @mcp.tool() seguem iguais.
mcp = MCPServer(
    "saudeemdado",
    version=__version__,
    title="Saúde em Dado",
    description=(
        "Dados oficiais de saúde no Brasil — mortalidade (SIM), dengue (SINAN), "
        "internações SUS (SIH), leitos e serviços (CNES), nascimentos (SINASC) e "
        "financiamento (SIOPS), a partir dos microdados do DataSUS e do IBGE."
    ),
    website_url="https://saudeemdado.com",
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
        "6. INTERNAÇÕES: `internacoes` conta AIHs APROVADAS, não pacientes e nem episódios. "
        "Uma internação longa emite várias AIHs (continuação), e a AIH pública não tem "
        "identificador de paciente. NUNCA escreva 'pacientes' para esse número — escreva "
        "'internações registradas' ou 'AIHs aprovadas'. Médias por episódio "
        "(permanencia_media, custo_medio) já vêm calculadas sobre `aih_normal`; não as "
        "recalcule dividindo por `internacoes`. Nos capítulos V (transtornos mentais) e VI "
        "(sistema nervoso) a diferença é grande — 25% e 10% das AIHs são de continuação.\n"
        "7. NÃO faça inferência causal, extrapolação além do dado, nem recomendação "
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
    intra-hospitalar (%) e custo médio (R$). Cobre só a rede SUS.

    AIH != internacao != paciente: `internacoes` conta AIHs APROVADAS (producao), incluindo a AIH de continuacao emitida quando a internacao se prolonga. `permanencia_media` e `custo_medio` sao por EPISODIO, calculados sobre `aih_normal` (= internacoes - aih_continuacao). Nos capitulos V (transtornos mentais, 25% de continuacao) e VI (sistema nervoso, 10%) os dois numeros divergem muito; nos outros, quase nada."""
    return sd.internacoes(uf=uf or None, ano=ano, capitulo=capitulo_cid)


@mcp.tool()
def internacoes_evitaveis_icsap(uf: str = "") -> list[dict]:
    """ICSAP — internações por condições sensíveis à atenção primária, por município (2024):
    total, ICSAP, % e por 100k hab. Proporção alta sinaliza fragilidade da atenção básica;
    é indicador de sistema, não de 'má gestão' local."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,internacoes_total,"
                  "internacoes_icsap,aih_continuacao,aih_continuacao_icsap,"
                  "pct_icsap,icsap_100k,populacao",
        "ano": "eq.2024", "order": "municipio_cod",
    }
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_icsap_municipio", params)


@mcp.tool()
def internacoes_por_agravo(uf: str = "", agravo: str = "") -> list[dict]:
    """Internações por agravo traçador (CID-3), por município (2024): diabetes, avc, iam,
    icc, asma, dpoc, pneumonia, depressao, esquizofrenia, alcool_drogas, tce. agravo vazio =
    todos. Traz permanência, mortalidade e custo por agravo.

    ATENÇÃO nos agravos de saúde mental (depressao, esquizofrenia, alcool_drogas): são do
    capítulo V, onde 25% das AIHs são de CONTINUAÇÃO de uma internação longa. `internacoes`
    conta AIHs aprovadas; `permanencia_media` e `custo_medio` usam `aih_normal`. Não
    apresente `internacoes` como número de pacientes nem como número de episódios."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,agravo,agravo_label,grupo,"
                  "internacoes,obitos,aih_continuacao,aih_normal,permanencia_media,"
                  "mortalidade_pct,custo_medio,internacoes_100k",
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
                  "aih_continuacao,aih_normal,permanencia_media,mortalidade_pct,custo_medio",
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


# ── Análise: comparação com pares ────────────────────────────────────────────
@mcp.tool()
def comparar_com_pares(municipio_cod: str) -> dict:
    """ANÁLISE: compara um município (6 dígitos) com seus PARES — municípios do mesmo
    arquétipo de saúde (k-means: mortalidade × vulnerabilidade × internações, 2023).
    Retorna, para cada métrica, o valor do município, a mediana dos pares e o percentil
    do município no grupo (0–100; alto = pior em mortalidade/vulnerabilidade).
    Comparação legítima: pares têm perfil estrutural semelhante, não só a mesma UF.
    Cobre ~1.700 municípios maiores; nos demais, retorna aviso."""
    alvo = sd._get("dim_cluster_municipio",
                   {"select": "municipio_cod,municipio_nome,uf_sigla,regiao,cluster,perfil,"
                              "taxa_padronizada_100k,ivs_score,internacoes_100k",
                    "municipio_cod": f"eq.{municipio_cod}"})
    if not alvo:
        return {"erro": "município fora da base de arquétipos (cobre ~1.700 municípios "
                        "maiores). Use municipios_indicadores para os indicadores diretos."}
    m = alvo[0]
    pares = sd._get("dim_cluster_municipio",
                    {"select": "municipio_cod,municipio_nome,uf_sigla,"
                               "taxa_padronizada_100k,ivs_score,internacoes_100k",
                     "cluster": f"eq.{m['cluster']}"})

    def _stats(campo: str) -> dict:
        vals = sorted(p[campo] for p in pares if p[campo] is not None)
        v = m[campo]
        if v is None or not vals:
            return {"valor": v, "mediana_pares": None, "percentil": None}
        mediana = vals[len(vals) // 2]
        pct = round(100 * sum(1 for x in vals if x <= v) / len(vals))
        return {"valor": v, "mediana_pares": mediana, "percentil": pct}

    proximos = sorted(
        (p for p in pares if p["municipio_cod"] != municipio_cod
         and p["taxa_padronizada_100k"] is not None and m["taxa_padronizada_100k"] is not None),
        key=lambda p: abs(p["taxa_padronizada_100k"] - m["taxa_padronizada_100k"]),
    )[:5]
    return {
        "municipio": m["municipio_nome"], "uf": m["uf_sigla"], "codigo": municipio_cod,
        "arquetipo": m["perfil"], "n_pares": len(pares),
        "metricas": {
            "taxa_padronizada_100k": _stats("taxa_padronizada_100k"),
            "ivs_score": _stats("ivs_score"),
            "internacoes_100k": _stats("internacoes_100k"),
        },
        "pares_mais_proximos": [
            {"municipio": p["municipio_nome"], "uf": p["uf_sigla"],
             "taxa_padronizada_100k": p["taxa_padronizada_100k"]} for p in proximos
        ],
        "fonte": "SIM/SIH/DataSUS + IBGE Censo 2022; clusters k-means 2023 (dim_cluster_municipio)",
    }


# ── Tradução: do indicador para a decisão ────────────────────────────────────
@mcp.tool()
def icsap_distancia_dos_pares(municipio_cod: str = "", uf: str = "", top: int = 20) -> list[dict]:
    """TRADUÇÃO: converte o indicador ICSAP na pergunta do gestor — "quanto meu
    município está acima de municípios COMPARÁVEIS em internações evitáveis, e o que
    isso representa?". Informe municipio_cod (6 dígitos) OU uf (ranking dos maiores).
    Retorna: pct_icsap do município, mediana dos pares, diferença em pontos
    percentuais, e a tradução — internacoes_acima_pares, leitos_equivalentes_ano
    (leitos que ficariam ocupados o ano inteiro) e custo_associado_reais.
    Pares = municípios do mesmo arquétipo k-means; sem arquétipo, mesma faixa
    populacional e região. Comparar com a média nacional seria injusto.

    AO RELATAR, estas ressalvas são obrigatórias — sem elas o número engana:
    1. NÃO é economia disponível. Chegar à mediana exige INVESTIR em atenção
       primária, não cortar; o valor mede o tamanho do problema, não caixa a resgatar.
    2. Nem toda ICSAP é evitável — a Lista Brasileira reúne condições SENSÍVEIS à
       atenção primária; boa cobertura reduz, não zera. Por isso a referência é a
       mediana dos pares, nunca zero.
    3. Associação ECOLÓGICA (municipal): não é risco individual nem prova de causa.
    4. Proporção alta pode indicar ACESSO restrito, não atenção primária ruim: onde
       falta leito, internação eletiva some e a fatia de ICSAP sobe. Sugira cruzar
       com oferta hospitalar antes de concluir.
    5. O custo em reais é TETO: deriva de 6 agravos traçadores que pendem para o
       lado caro da lista (AVC e ICC), sem as condições baratas (gastroenterite,
       infecção urinária, anemia)."""
    campos = ("municipio_cod,municipio_nome,uf_sigla,ano,populacao,internacoes_total,"
              "internacoes_icsap,pct_icsap,arquetipo,criterio_pares,n_pares,"
              "mediana_pares_pct,p25_pares_pct,diferenca_pp,internacoes_acima_pares,"
              "internacoes_acima_p25,custo_associado_reais,leitos_dia_associados,"
              "leitos_equivalentes_ano,custo_medio_icsap_ref,amostra_pequena")
    params = {"select": campos}
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    else:
        if uf:
            params["uf_sigla"] = f"eq.{uf.upper()}"
        params["order"] = "internacoes_acima_pares.desc"
        params["limit"] = str(top)
    return sd._get("mart_icsap_pares", params)


# ── Análise: canal endêmico ──────────────────────────────────────────────────
@mcp.tool()
def canal_endemico_dengue(uf: str, ano: int = 2024) -> dict:
    """ANÁLISE: canal endêmico de dengue de uma UF (diagrama de controle). Compara os
    casos semanais do ano observado com a faixa esperada (quartis P25–P75 das mesmas
    semanas nos anos anteriores, 2015+, excluindo o ano observado). Retorna a banda
    semana a semana, quantas semanas ficaram acima do P75 (sinal de surto) e o status.
    Semanas acima ≥13 (um trimestre) = surto prolongado."""
    linhas = sd._get("mart_dengue_semana",
                     {"select": "ano_epi,semana_epi,casos:casos_provaveis.sum()",
                      "uf_sigla": f"eq.{uf.upper()}", "semana_epi": "gte.1",
                      "order": "ano_epi,semana_epi"})
    if not linhas:
        return {"erro": f"sem dados de dengue para a UF {uf.upper()}"}
    por_semana: dict[int, dict[int, int]] = {}
    for r in linhas:
        w = r["semana_epi"]
        if 1 <= w <= 52:
            por_semana.setdefault(w, {})[r["ano_epi"]] = r["casos"]
    anos_base = sorted({r["ano_epi"] for r in linhas if r["ano_epi"] != ano})

    def _q(vals: list[int], p: float) -> int:
        if not vals:
            return 0
        s = sorted(vals)
        i = (len(s) - 1) * p
        lo, hi = int(i), min(int(i) + 1, len(s) - 1)
        return round(s[lo] + (s[hi] - s[lo]) * (i - lo))

    canal, acima = [], 0
    for w in range(1, 53):
        base = [v for a, v in por_semana.get(w, {}).items() if a != ano]
        obs = por_semana.get(w, {}).get(ano, 0)
        p75 = _q(base, 0.75)
        if obs > p75:
            acima += 1
        canal.append({"semana": w, "p25": _q(base, 0.25), "mediana": _q(base, 0.5),
                      "p75": p75, "observado": obs})
    status = ("surto prolongado (≥1 trimestre acima da faixa)" if acima >= 13
              else "acima da faixa em algumas semanas" if acima > 0
              else "dentro da faixa esperada")
    return {"uf": uf.upper(), "ano_observado": ano,
            "baseline": f"{anos_base[0]}–{anos_base[-1]} (exclui o ano observado)",
            "semanas_acima_p75": acima, "status": status, "canal": canal,
            "fonte": "SINAN/DataSUS (casos prováveis por semana de primeiros sintomas)"}


# ── Boletim epidemiológico semanal ───────────────────────────────────────────
@mcp.tool()
def boletim_semanal(edicao: str = "") -> dict:
    """SITUAÇÃO ATUAL + boletim semanal. Use esta ferramenta para perguntas sobre o
    que está acontecendo AGORA ("como está a dengue esta semana?", "tem alerta no meu
    estado?") — é a única fonte de dado corrente aqui; todas as outras ferramentas são
    históricas (DataSUS consolidado até 2024).
    Campo `vigilancia_atual`: nowcasting semanal do InfoDengue (Fiocruz/FGV) para as 27
    capitais — nível de alerta (1 verde, 2 amarelo, 3 laranja, 4 vermelho), Rt (>1 =
    transmissão crescendo), casos notificados vs. ESTIMADOS (o estimado corrige o atraso
    de digitação; nunca cite só o notificado da semana corrente, ele subestima).
    Cobre dengue e chikungunya. Traz também as seções históricas: canal endêmico Brasil,
    excesso de mortalidade e KPIs de internações.
    Sem argumento retorna a edição mais recente; edicao no formato '2026-se30' retorna
    uma específica. Ao citar a vigilância, credite InfoDengue (Fiocruz/FGV), não o DataSUS."""
    base = "https://saudeemdado.com/sdata/boletins"
    idx = requests.get(f"{base}/index.json", timeout=30)
    idx.raise_for_status()
    edicoes = idx.json()
    alvo = edicao or (edicoes[0]["edicao"] if edicoes else "")
    if not alvo:
        return {"erro": "nenhuma edição publicada ainda"}
    r = requests.get(f"{base}/{alvo}.json", timeout=30)
    if r.status_code == 404:
        return {"erro": f"edição '{alvo}' não encontrada",
                "disponiveis": [e["edicao"] for e in edicoes]}
    r.raise_for_status()
    b = r.json()
    b["permalink"] = f"https://saudeemdado.com/boletim-semanal/?e={alvo}"
    b["edicoes_disponiveis"] = [e["edicao"] for e in edicoes]
    return b


@mcp.tool()
def metadados_dataset() -> dict[str, str]:
    """Fontes, metodologia resumida, exclusões, licença, DOI e versão do dataset."""
    return sd.metadados()


def main() -> None:
    """Ponto de entrada do console script `saudeemdado-mcp`."""
    mcp.run()


if __name__ == "__main__":
    main()
