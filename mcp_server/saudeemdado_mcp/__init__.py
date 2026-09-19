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

import functools
import sys
from datetime import date
from pathlib import Path

try:  # instalado via pip/uvx: o cliente é uma dependência
    import saudeemdado as sd
except ImportError:  # rodando do repositório clonado sem instalar: usa o cliente local
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "clients" / "python"))
    import saudeemdado as sd

import requests
from mcp.server import MCPServer

__version__ = "0.11.0"

# A 2.0.0 do SDK renomeou FastMCP para MCPServer e removeu mcp.server.fastmcp.
# A API de decorators nao mudou: as 41 @mcp.tool() seguem iguais.
mcp = MCPServer(
    "saudeemdado",
    version=__version__,
    title="Saúde em Dado",
    description=(
        "Dados oficiais de saúde no Brasil — mortalidade (SIM), dengue (SINAN), "
        "internações SUS (SIH), leitos e serviços (CNES), nascimentos (SINASC), "
        "vacinação (PNI/RNDS), vigilância da água (SISAGUA) e financiamento "
        "(SIOPS), a partir dos microdados do DataSUS, do Ministério da Saúde e do IBGE."
    ),
    website_url="https://saudeemdado.com",
    instructions=(
        "Dados oficiais de saúde no Brasil (DataSUS 2015–2024 + IBGE). REGRAS DE USO "
        "(número de saúde não admite invenção):\n"
        "1. NUNCA estime números de cabeça — sempre chame uma ferramenta e use o valor "
        "retornado. Se não há ferramenta para a pergunta, diga que não sabe.\n"
        "2. SEMPRE cite a fonte. Toda ferramenta de dado devolve `procedencia` ao lado "
        "de `dados`: REPRODUZA o campo `como_citar` ao publicar, apresentar ou responder "
        "com estes números, e diga o ano — o mais recente é preliminar. Os marts "
        "derivados estão sob CC BY 4.0, em que a atribuição é CONDIÇÃO da licença.\n"
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
        "8. ICSAP NÃO É TERMÔMETRO DA ATENÇÃO PRIMÁRIA. A leitura convencional "
        "('%ICSAP alto = APS fraca') foi TESTADA nesta plataforma e REFUTADA na direção "
        "e no mecanismo: o %ICSAP responde fortemente à existência de LEITO local — a "
        "associação com leitos SUS/mil é POSITIVA, e municípios SEM leito têm proporção "
        "MENOR, não maior. NUNCA traduza %ICSAP alto como 'atenção primária frágil'; "
        "descreva-o como sinal que exige comparação com oferta hospitalar local, porte, "
        "cobertura privada e pares. Os valores medidos e a hipótese refutada por extenso "
        "estão em metodologia('icsap').\n"
        "9. ANTES de escrever a frase que acompanha um número, chame "
        "`metodologia(<indicador ou nome da ferramenta>)`. Ela devolve numerador, "
        "denominador, unidade, defasagem, o que o indicador NÃO mede, as ressalvas "
        "obrigatórias ao relatar e as leituras já testadas e refutadas aqui. É o que "
        "impede repetir uma explicação que a plataforma já descartou. Sem entrada no "
        "catálogo, diga que não há limite documentado — não improvise uma ressalva.\n"
        "Metodologia: https://saudeemdado.com/metodologia/"
    ),
)


# ── Procedência: a citação viaja COM o dado ──────────────────────────────────
#
# O servidor sempre teve a regra "SEMPRE cite a fonte" nas instruções. Instrução
# some quando a resposta é copiada — e as 19 ferramentas devolviam `list[dict]`
# cru, sem nada que dissesse de onde o número veio nem como creditar. Só a
# vigésima (`metadados_dataset`) trazia licença e DOI, e um assistente
# raramente a chama sozinho.
#
# Isso não é detalhe de etiqueta: os marts derivados estão sob **CC BY 4.0**, em
# que atribuição é CONDIÇÃO, não cortesia. Entregar dado sem dizer como citar é
# construir a superfície que produz o uso não creditado.
#
# Agora toda ferramenta de dado devolve `{"dados": ..., "procedencia": {...}}`,
# e a procedência sai de `meta_dataset` — a mesma fonte que a API e o site
# leem, não uma segunda cópia da frase.
_META_CACHE: dict[str, str] | None = None


def _meta() -> dict[str, str]:
    """`meta_dataset`, buscado uma vez por processo.

    Falha de rede não pode derrubar uma consulta de dado que já funcionou: sem
    metadados, a procedência sai reduzida ao que é constante do pacote, e a
    ferramenta continua respondendo.
    """
    global _META_CACHE
    if _META_CACHE is None:
        try:
            _META_CACHE = sd.metadados()
        except Exception:  # noqa: BLE001 — rede/HTTP; degradar é melhor que falhar
            _META_CACHE = {}
    return _META_CACHE


def _procedencia(chave_fonte: str) -> dict[str, str]:
    m = _meta()
    return {
        "fonte_primaria": m.get(chave_fonte, "DATASUS/Ministério da Saúde e IBGE"),
        "plataforma": f"Saúde em Dado (saudeemdado.com) — versão do dataset {m.get('versao_dataset', '?')}",
        "dado_gerado_em": m.get("gerado_em", "?"),
        "licenca": m.get("licenca", "Marts derivados sob CC BY 4.0 — atribuição obrigatória."),
        "como_citar": m.get(
            "como_citar",
            "Fernandes, P. P. Saúde em Dado. https://saudeemdado.com · "
            "DOI: 10.5281/zenodo.20706845",
        ),
        "ao_reportar": (
            "Inclua a citação acima ao publicar, apresentar ou responder com estes "
            "números. A atribuição é condição da licença, não cortesia."
        ),
    }


def procedencia(chave_fonte: str):
    """Envelopa o retorno de uma ferramenta com a sua procedência.

    Fica ENTRE `@mcp.tool()` e a função, para o corpo de cada ferramenta seguir
    devolvendo só o dado. `functools.wraps` preserva nome, docstring e
    assinatura (o MCP deriva o schema dela); só a anotação de retorno é
    reescrita, senão a ferramenta anunciaria `list[dict]` e devolveria `dict`.
    """

    def decorador(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            saida = fn(*args, **kwargs)
            # Falha não leva citação, e não desce um nível.
            #
            # A primeira versão envelopava tudo, e `{"erro": ...}` virava
            # `{"dados": {"erro": ...}}` — quatro testes de caminho de erro
            # reprovaram, com razão. Anexar "como citar" a uma mensagem de erro
            # é dar procedência a dado que não existe, e enterra o `erro` um
            # nível abaixo de onde o modelo o procura. Erro passa direto.
            if isinstance(saida, dict) and "erro" in saida:
                return saida
            return {"dados": saida, "procedencia": _procedencia(chave_fonte)}

        wrapper.__annotations__ = {**getattr(fn, "__annotations__", {}), "return": dict}
        return wrapper

    return decorador


# ── Mortalidade ──────────────────────────────────────────────────────────────
@mcp.tool()
@procedencia("fonte_obitos")
def serie_mensal_obitos(uf: str = "", capitulo_cid: str = "TOTAL") -> list[dict]:
    """Série mensal de óbitos 2015–2024. uf vazio = todas as UFs (some para o Brasil).
    capitulo_cid: I a XXII ou TOTAL (IX = circulatório, X = respiratório, II = neoplasias)."""
    return sd.serie_mensal(uf=uf or None, capitulo=capitulo_cid)


@mcp.tool()
@procedencia("fonte_obitos")
def municipios_indicadores(
    uf: str, ano: int = 2023, capitulo_cid: str = "TOTAL", populacao_minima: int = 10000
) -> list[dict]:
    """Indicadores municipais: óbitos, taxa bruta/100k com IC95% e taxa padronizada por
    idade (taxa_padronizada_100k — use esta para comparar municípios)."""
    return sd.municipios(uf=uf, ano=ano, capitulo=capitulo_cid, pop_min=populacao_minima)


@mcp.tool()
@procedencia("fonte_mortalidade_causa_municipio")
def principais_causas(uf: str = "", ano: int = 2024, top: int = 20) -> list[dict]:
    """Principais causas básicas de óbito (CID-10, 3 caracteres) no Brasil (uf vazio) ou UF.
    Atenção: R99 = causa mal-definida (ausência de diagnóstico), não é doença."""
    return sd.causas(uf=uf or None, ano=ano, top=top)


@mcp.tool()
@procedencia("fonte_mortalidade_causa_municipio")
def descricao_cid10(codigos: list[str]) -> dict[str, str]:
    """Descrições oficiais de categorias CID-10 de 3 caracteres (ex.: I21, C34)."""
    todos = {r["causabas_3"]: r["descricao"] for r in sd.cid10()}
    return {c.upper(): todos.get(c.upper(), "código não encontrado") for c in codigos}


@mcp.tool()
@procedencia("fonte_obitos")
def excesso_mortalidade(uf: str = "BR") -> list[dict]:
    """Excesso de mortalidade mensal (2020+) por UF ou BR (Brasil): observado, esperado
    (baseline por TENDÊNCIA linear 2015–2019, que capta o envelhecimento), excesso e %.
    Pico pandêmico Brasil 2020–2021 ≈ 643 mil; 2024 ≈ zero (preliminar)."""
    return sd.excesso(uf=uf)


# ── Confiabilidade do dado (camada anti-alucinação) ─────────────────────────
@mcp.tool()
@procedencia("fonte_qualidade_registro")
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
@procedencia("fonte_sih")
def internacoes_municipios(uf: str = "", ano: int = 2024, capitulo_cid: str = "TOTAL") -> list[dict]:
    """Internações SUS (SIH/AIH) por município: volume, permanência média, mortalidade
    intra-hospitalar (%) e custo médio (R$). Cobre só a rede SUS.

    AIH != internacao != paciente: `internacoes` conta AIHs APROVADAS (producao), incluindo a AIH de continuacao emitida quando a internacao se prolonga. `permanencia_media` e `custo_medio` sao por EPISODIO, calculados sobre `aih_normal` (= internacoes - aih_continuacao). Nos capitulos V (transtornos mentais, 25% de continuacao) e VI (sistema nervoso, 10%) os dois numeros divergem muito; nos outros, quase nada."""
    return sd.internacoes(uf=uf or None, ano=ano, capitulo=capitulo_cid)


@mcp.tool()
@procedencia("fonte_fluxo_icsap")
def internacoes_evitaveis_icsap(uf: str = "") -> list[dict]:
    """ICSAP — internações por condições sensíveis à atenção primária, por município (2024):
    total, ICSAP, % e por 100k hab.

    NÃO LEIA %ICSAP COMO QUALIDADE DA ATENÇÃO BÁSICA. Medido nesta plataforma (§19 da
    metodologia, 5.570 municípios, 2024): a correlação com leitos SUS/mil é POSITIVA
    (ρ=+0,32), e municípios sem leito local têm %ICSAP MENOR (17,7%) que os com leito
    (21,4%) — ter leito local aumenta a internação sensível em +51% a +85% conforme o
    porte, sem mexer nas demais. O indicador mede, em parte relevante, a EXISTÊNCIA DE
    LEITO na cidade. Proporção alta é sinal que exige comparação com oferta hospitalar,
    porte, cobertura privada e pares — nunca conclusão sobre a APS. É indicador de
    sistema, não de 'má gestão' local."""
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
@procedencia("fonte_agravo_hospital")
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
@procedencia("fonte_agravo_hospital")
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
@procedencia("fonte_fluxo_icsap")
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
@procedencia("fonte_dengue")
def dengue_municipios(uf: str = "", ano: int = 2024) -> list[dict]:
    """Dengue (SINAN) por município/ano: casos prováveis, graves, óbitos, incidência/100k e
    letalidade. 2024 foi epidemia recorde (6,56 milhões de casos)."""
    return sd.dengue(uf=uf or None, ano=ano, nivel="ano")


@mcp.tool()
@procedencia("fonte_dengue")
def dengue_semanal(uf: str, ano: int = 2024) -> list[dict]:
    """Dengue (SINAN) por semana epidemiológica de uma UF/ano — curvas sazonais e picos."""
    return sd.dengue(uf=uf, ano=ano, nivel="semana")


# ── Água para consumo humano (SISAGUA) ──────────────────────────────────────
#
# Duas ferramentas, e a segunda não é acessório: a ausência de um município em
# `mart_sisagua_municipio` tem DOIS significados — ele não reportou análise, ou
# não conseguimos coletar. Sem a cobertura da coleta ao lado, as duas viram
# "zero análises", que é a leitura errada mais fácil desta fonte.
@mcp.tool()
@procedencia("fonte_sisagua")
def agua_vigilancia_municipio(
    uf: str = "", municipio_cod: str = "", ano: int = 2024, parametro: str = ""
) -> list[dict]:
    """Vigilância da qualidade da água (SISAGUA), controle mensal, 2014–2026: amostras
    analisadas, resultados de Escherichia coli e coliformes totais, meses com análise no
    ano e formas de abastecimento. Informe uf OU municipio_cod (6 dígitos).

    MEDE VOLUME E REGULARIDADE DE ANÁLISE, NÃO POTABILIDADE DA ÁGUA. Um município
    com muitas amostras não tem água melhor: tem mais vigilância registrada.

    AUSÊNCIA NÃO É ZERO. Município que não aparece ou não reportou análise alguma, ou
    não foi coletado — as duas produzem a mesma linha faltando. Chame
    agua_cobertura_da_coleta antes de dizer que um município "não analisa".

    parametro vazio = todos. Os do controle básico: 'Escherichia coli',
    'Coliformes totais', 'Cloro Residual Livre (mg/L)', 'Turbidez (uT)', 'Cor (uH)',
    'pH', 'Fluoreto (mg/L)', 'Dióxido de Cloro', 'Bactérias Heterotróficas (UFC/mL)'."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,parametro,"
                  "amostras_analisadas,escherichia_coli,coliformes_totais,"
                  "meses_com_analise,formas_de_abastecimento",
        "ano": f"eq.{ano}", "order": "municipio_cod,parametro",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    if parametro:
        params["parametro"] = f"eq.{parametro}"
    return sd._get("mart_sisagua_municipio", params)


@mcp.tool()
@procedencia("fonte_sisagua")
def agua_cobertura_da_coleta(uf: str = "", municipio_cod: str = "") -> list[dict]:
    """COBERTURA da coleta do SISAGUA: uma linha por município do país, para separar
    'não analisou' de 'não coletamos'. Consulte SEMPRE que for afirmar ausência de
    vigilância em agua_vigilancia_municipio.

    coletado=false: a coleta falhou para este município — a ausência é nossa, não dele.
    coletado=true com linhas_no_mart=0: coletamos e ele não reportou análise alguma.
    As duas produzem a mesma ausência no mart; só esta tabela as distingue."""
    params = {"select": "municipio_cod,uf_sigla,coletado,registros_brutos,linhas_no_mart",
              "order": "municipio_cod"}
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_sisagua_cobertura", params)


# ── Vacinação (PNI/RNDS) ─────────────────────────────────────────────────────
#
# Duas ferramentas porque são duas coisas, e confundi-las é o erro clássico desta
# fonte: DOSE é contagem e não precisa de denominador; COBERTURA precisa, e o
# denominador só serve por UF. A separação aqui é a regra 'dose não é cobertura'
# implementada como superfície, não como aviso.
@mcp.tool()
@procedencia("fonte_pni")
def vacinacao_doses(uf: str = "", competencia: str = "", imunobiologico: str = "") -> list[dict]:
    """Doses aplicadas do PNI por competência mensal, UF e imunobiológico. FONTE MAIS
    ATUAL do acervo histórico: cerca de um mês de defasagem (vai até 2026-08), enquanto
    as demais param no DataSUS consolidado de 2024.

    DOSE NÃO É COBERTURA e NÃO É PESSOA. É contagem de aplicações: a mesma criança
    aparece uma vez por dose do esquema. Para cobertura, use cobertura_vacinal_uf —
    e leia o limite dela antes.

    competencia no formato 'AAAA-MM'; vazio = toda a série. imunobiologico vazio =
    todos (78 na competência mais recente, incluindo várias apresentações de COVID-19:
    somar rótulos diferentes do mesmo produto duplica)."""
    params = {"select": "competencia,uf_sigla,imunobiologico,doses",
              "order": "competencia,uf_sigla,imunobiologico"}
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    if competencia:
        params["competencia"] = f"eq.{competencia}"
    if imunobiologico:
        params["imunobiologico"] = f"eq.{imunobiologico}"
    return sd._get("mart_vacinacao_uf_mes", params)


@mcp.tool()
@procedencia("fonte_pni")
def cobertura_vacinal_uf(uf: str = "", ano: int = 2024) -> list[dict]:
    """Cobertura vacinal em menores de 1 ano, POR UF e apenas 2023–2024, para cinco
    indicadores da atenção básica: Pentavalente, Poliomielite, Rotavirus, Pneumococica
    e Meningococica, todos 1ª dose. Denominador: nascidos vivos definitivos (SINASC).

    NÃO EXISTE COBERTURA MUNICIPAL AQUI, e não é omissão: foi testada e REPROVADA por
    viés sistemático de denominador. A mediana cai de 102,7% nos municípios com 50–100
    nascidos para 86,2% nos com 5.000+, e mais da metade dos pequenos passa de 100%.
    NÃO derive cobertura municipal dividindo vacinacao_doses por população — é
    exatamente o cálculo reprovado.

    BCG e hepatite B ao nascer estão EXCLUÍDAS mesmo por UF: aplicadas na maternidade,
    chegam a 127,8% (CE) e 121,0% (AL) em 2024, porque o denominador é por residência
    da mãe. Cobertura acima de 100% é guarda de erro de composição, não desempenho.

    Cada indicador declara qual tipo de dose conta; somar tipos diferentes conta a
    mesma criança duas vezes."""
    params = {"select": "uf_sigla,ano,indicador,doses,nascidos,cobertura_pct",
              "ano": f"eq.{ano}", "order": "uf_sigla,indicador"}
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_cobertura_vacinal_uf", params)


# ── Nascimentos (SINASC) ─────────────────────────────────────────────────────
@mcp.tool()
@procedencia("fonte_sinasc")
def natalidade_municipio(uf: str = "", municipio_cod: str = "", ano: int = 2024) -> list[dict]:
    """Nascidos vivos por município e ano (SINASC), 2021–2024: volume, % de baixo peso
    (<2500 g), % de prematuros (<37 semanas), % com 7 ou mais consultas de pré-natal e
    idade média da mãe. Informe uf OU municipio_cod (6 dígitos).

    Nascidos por RESIDÊNCIA DA MÃE, não por local do parto. Município com maternidade
    de referência não infla aqui — é o oposto do que acontece com internação.

    É o denominador oficial da mortalidade infantil e da cobertura vacinal desta
    plataforma; quando usar como denominador, confira se o ano tem SINASC definitivo."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,nascidos,"
                  "pct_baixo_peso,pct_prematuro,pct_prenatal_7mais,idade_media_mae",
        "ano": f"eq.{ano}", "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_natalidade_municipio", params)


@mcp.tool()
@procedencia("fonte_sinasc")
def mortalidade_infantil_uf(uf: str = "", ano: int = 0) -> list[dict]:
    """Taxa de mortalidade infantil por UF e ano: óbitos de menores de 1 ano (SIM)
    dividido por nascidos vivos (SINASC), por mil. uf e ano vazios = série completa.

    Só por UF, e de propósito: a TMI municipal oscila demais em município pequeno,
    onde poucos óbitos mudam a taxa em dezenas de pontos. Não a derive dividindo
    óbitos por nascidos de um município.

    O numerador vem do SIM e o denominador do SINASC — dois sistemas com fechamentos
    diferentes. Ano sem SINASC definitivo não entra."""
    params = {"select": "uf_sigla,ano,nascidos,obitos_menor1,tmi_por_mil",
              "order": "uf_sigla,ano"}
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    if ano:
        params["ano"] = f"eq.{ano}"
    return sd._get("mart_mortalidade_infantil_uf", params)


# ── Atenção primária (e-Gestor AB) ───────────────────────────────────────────
@mcp.tool()
@procedencia("fonte_cobertura_aps")
def cobertura_aps_municipio(uf: str = "", municipio_cod: str = "", ano: int = 2026,
                            mes: int = 0) -> list[dict]:
    """Cobertura POTENCIAL da atenção primária por município e mês, 2021 em diante:
    equipes (ESF, EAP, eSFR, eCR, EAPP), capacidade instalada e cobertura_pct.
    Informe uf OU municipio_cod (6 dígitos); mes vazio = todos os meses do ano.

    É COBERTURA POTENCIAL, calculada da capacidade das equipes cadastradas — não é
    população efetivamente acompanhada. Passa de 100% em município pequeno, onde a
    capacidade por equipe supera a população local: é comportamento documentado do
    indicador oficial, não erro do dado.

    NÃO USE COMO MEDIDA DE DESEMPENHO DA APS. Medido nesta plataforma: a associação
    com %ICSAP é praticamente nula (Spearman +0,004 bruto, +0,018 controlando porte e
    vulnerabilidade), a cobertura satura acima de 100% em 86% dos municípios e o que
    ela correlaciona forte é PORTE (ρ −0,54 com população). Ver metodologia('cobertura_aps')."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,mes,mes_competencia,"
                  "populacao,qt_esf,qt_eap20,qt_eap30,qt_esfr,qt_ecr,qt_eapp20,qt_eapp30,"
                  "capacidade_equipe,cobertura_pct",
        "ano": f"eq.{ano}", "order": "municipio_cod,mes",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    if mes:
        params["mes"] = f"eq.{mes}"
    return sd._get("mart_cobertura_aps_municipio", params)


# ── Saúde suplementar (ANS) e rede cadastrada (CNES) ─────────────────────────
@mcp.tool()
@procedencia("fonte_saude_suplementar")
def saude_suplementar_municipio(uf: str = "", municipio_cod: str = "",
                                ano: int = 2024) -> list[dict]:
    """Vínculos de planos de saúde médico-hospitalares por município e ano (ANS):
    vínculos, vínculos por 100 habitantes e um sinalizador de razão implausível.
    Informe uf OU municipio_cod (6 dígitos).

    VÍNCULO NÃO É PESSOA. Uma pessoa com dois planos conta duas vezes, e o vínculo é
    registrado pelo município do CONTRATO, que pode não ser o de residência — por isso
    existem municípios acima de 100 vínculos por 100 habitantes. Use `razao_implausivel`
    para excluí-los de qualquer leitura de 'cobertura privada'.

    Serve como CONTEXTO de quanto da população local não depende só do SUS; não serve
    para estimar a população SUS-dependente por subtração."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,populacao,"
                  "vinculos_medico_hospitalar,vinculos_plano_por_100_hab,razao_implausivel",
        "ano": f"eq.{ano}", "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_saude_suplementar_municipio", params)


@mcp.tool()
@procedencia("fonte_cnes")
def rede_cadastrada_municipio(uf: str = "", municipio_cod: str = "") -> list[dict]:
    """Rede de estabelecimentos cadastrados no CNES por município: total, hospitalares,
    composição por natureza (público, privado com e sem fins lucrativos, pessoa física,
    internacional), estabelecimentos por 10 mil habitantes e % público.
    Informe uf OU municipio_cod (6 dígitos).

    CADASTRO NÃO É OPERAÇÃO. Estabelecimento cadastrado não comprova serviço em
    funcionamento, com equipe ou com horário. É retrato do cadastro corrente, não série
    histórica: `ano_referencia` diz de quando é.

    Estabelecimento não é leito, e contagem de estabelecimentos não mede capacidade —
    uma UBS e um hospital contam 1 cada."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,estabelecimentos_total,"
                  "estabelecimentos_hospitalares,publico,privado_lucrativo,"
                  "sem_fins_lucrativos,pessoa_fisica,internacional,populacao,"
                  "estab_por_10k,estab_hosp_por_10k,pct_publico,ano_referencia",
        "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_cnes_municipio", params)


# ── Financiamento (SIOPS) ────────────────────────────────────────────────────
@mcp.tool()
@procedencia("fonte_siops")
def gasto_saude_municipio(uf: str = "", municipio_cod: str = "", ano: int = 2024) -> list[dict]:
    """Gasto público municipal em saúde (SIOPS), 2021–2024: gasto próprio por habitante,
    despesa total, transferências SUS por habitante, % da receita própria aplicada em
    saúde e se ficou abaixo do mínimo constitucional (EC 29). Informe uf OU
    municipio_cod (6 dígitos).

    É despesa EMPENHADA e AUTODECLARADA pelo ente — não é despesa paga nem auditada.

    GASTO NÃO MEDE ACESSO NEM QUALIDADE. Gastar mais por habitante não implica melhor
    serviço, e o teste desta plataforma contra o %ICSAP é um dos achados nulos do
    projeto. Não construa ranking de 'melhor gestão' com este campo.

    populacao_siops é a declarada pelo ente no sistema e pode divergir da projeção do
    IBGE usada nos demais indicadores; não a misture com outros denominadores."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,populacao_siops,"
                  "gasto_proprio_saude_hab,despesa_total_saude,transf_sus_hab,"
                  "pct_receita_propria_saude,abaixo_do_minimo_ec29",
        "ano": f"eq.{ano}", "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_siops_municipio", params)


# ── Vazio assistencial: leitos x local do óbito ─────────────────────────────
@mcp.tool()
@procedencia("fonte_obitos")
def vazio_assistencial(uf: str = "", municipio_cod: str = "") -> list[dict]:
    """Cruzamento de leitos (CNES) com mortalidade (SIM) por município, 2023: leitos
    totais e SUS, leitos SUS por mil, se o município não tem leito, óbitos em hospital
    e em domicílio, taxa bruta e PADRONIZADA por idade, porte e vulnerabilidade.
    Informe uf OU municipio_cod (6 dígitos).

    O QUE ESTE CRUZAMENTO JÁ RESPONDEU: viver em município sem leito local NÃO eleva a
    mortalidade padronizada — muda o LOCAL do óbito, com mais mortes em domicílio. O
    efeito bruto que parecia existir era confundido por porte populacional. Portanto
    NÃO apresente ausência de leito local como causa de mais mortes; apresente como
    deslocamento do local de morte e dependência de outro município (ver
    fluxo_pacientes).

    Use taxa_padronizada_100k para comparar municípios; a bruta reflete a estrutura
    etária. pct_obito_domicilio é o campo em que a diferença aparece."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,populacao,"
                  "porte_quartil,leitos_total,leitos_sus,leitos_sus_por_mil,sem_leito,"
                  "obitos,obitos_hospital,obitos_domicilio,pct_obito_domicilio,"
                  "pct_obito_hospital,taxa_obitos_100k,taxa_padronizada_100k,ivs_score",
        "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_vazio_assistencial_municipio", params)


# ── Hospital: mortalidade ajustada, permanência e demanda ───────────────────
@mcp.tool()
@procedencia("fonte_sih")
def hsmr_hospital(uf: str = "", cnes: str = "", ano: int = 2024, top: int = 50) -> list[dict]:
    """HSMR — razão de mortalidade hospitalar padronizada por estabelecimento (CNES):
    óbitos observados vs. esperados, ajustada por faixa etária × capítulo CID-10
    (padronização indireta), com IC95%, significância e o estrato usado.
    Informe uf OU cnes.

    É a mortalidade hospitalar COM ajuste de risco, ao contrário de `hospitais`, que
    devolve a bruta. Mesmo assim NÃO É MEDIDA DE QUALIDADE: HSMR alto indica que vale
    investigar, não que o hospital é pior. O ajuste cobre idade e capítulo, não
    gravidade dentro do capítulo, case-mix fino nem área de captação.

    `estavel=false` quando os óbitos esperados são menos de 5 — a razão fica instável e
    é publicada assim mesmo, marcada, em vez de omitida. Não ranqueie por HSMR sem
    filtrar por `estavel` e sem olhar o IC95%."""
    params = {
        "select": "cnes,municipio_cod,municipio_nome,uf_sigla,ano,internacoes,"
                  "obitos_observados,obitos_esperados,hsmr,estavel,hsmr_ic95_inf,"
                  "hsmr_ic95_sup,significancia,tem_uti,leitos_total,leitos_uti,estrato",
        "ano": f"eq.{ano}", "order": "hsmr.desc", "limit": str(top),
    }
    if cnes:
        params["cnes"] = f"eq.{cnes}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_hsmr_hospital", params)


@mcp.tool()
@procedencia("fonte_sih")
def permanencia_por_diagnostico(uf: str = "", cnes: str = "", cid3: str = "",
                                ano: int = 2024, top: int = 100) -> list[dict]:
    """Tempo de permanência por diagnóstico (CID-10 de 3 caracteres) e estabelecimento:
    mediana do hospital, mediana nacional e o desvio em dias. Informe uf OU cnes;
    cid3 vazio = todos. desvio_dias > 0 = interna por mais tempo que a mediana nacional.

    As medianas são APROXIMADAS por histograma de faixas de dias, não calculadas sobre
    a distribuição contínua — trate a diferença como ordem de grandeza.

    Permanência maior não é ineficiência: pode ser perfil de gravidade, falta de
    retaguarda para alta ou espera por vaga em outro serviço. E permanência menor não
    é eficiência — pode ser alta precoce ou óbito."""
    params = {
        "select": "cnes,municipio_cod,municipio_nome,uf_sigla,ano,cid3,capitulo_cid,"
                  "internacoes,mediana_hospital_dias,mediana_nacional_dias,desvio_dias",
        "ano": f"eq.{ano}", "order": "internacoes.desc", "limit": str(top),
    }
    if cnes:
        params["cnes"] = f"eq.{cnes}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    if cid3:
        params["cid3"] = f"eq.{cid3.upper()}"
    return sd._get("mart_los_hospital", params)


@mcp.tool()
@procedencia("fonte_sih")
def demanda_mensal_hospital(cnes: str = "", uf: str = "", top: int = 500) -> list[dict]:
    """Série mensal de internações por estabelecimento (CNES): volume, óbitos e valor
    aprovado por competência. Informe cnes OU uf. É a base histórica sobre a qual a
    projeção é feita — para a projeção em si, use forecast_demanda_hospital.

    Conta AIHs aprovadas, com a mesma ressalva de sempre: não são pacientes nem
    episódios. Queda numa competência pode ser fechamento de serviço, mudança de
    credenciamento ou atraso de digitação, não queda de demanda."""
    params = {"select": "cnes,municipio_cod,municipio_nome,uf_sigla,ano_mes,internacoes,"
                        "obitos,valor_total",
              "order": "ano_mes", "limit": str(top)}
    if cnes:
        params["cnes"] = f"eq.{cnes}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_demanda_mensal_hospital", params)


@mcp.tool()
@procedencia("fonte_sih")
def forecast_demanda_hospital(cnes: str = "", uf: str = "", top: int = 200) -> list[dict]:
    """Projeção de internações mensais por hospital, com faixa de incerteza, horizonte,
    erro medido no estrato (sMAPE do backtest) e o commit do código que a gerou.
    Informe cnes OU uf.

    LEIA A FAIXA, NUNCA O PONTO. O IC95% tem largura mediana de 74% da previsão nos
    hospitais grandes e 217% nos de 6 a 20 internações por mês.

    USOS QUE A MODEL CARD DESACONSELHA, e que você não deve produzir:
    dimensionar leitos, escalas ou orçamento; comparar hospitais (não há ajuste de
    case-mix, porte ou captação); ler queda prevista como piora assistencial (a
    projeção segue a tendência, que mistura demanda, oferta, credenciamento e
    registro); qualquer horizonte além de 3 meses, que não foi validado.

    `status_validacao` A é validado (sMAPE ≤30%), B é experimental (30–50%, ou
    histórico curto) e sai com aviso. Hospitais abaixo de 5 internações/mês não são
    publicados.

    Cada linha vem com `previsao_vencida`: true quando a competência prevista já
    passou. Previsão vencida não é previsão — é histórico não corrigido, e não deve
    ser apresentada como projeção. O campo é calculado aqui, e não deixado para o
    leitor comparar datas."""
    params = {
        "select": "cnes,municipio_cod,municipio_nome,uf_sigla,ano_mes_previsto,"
                  "internacoes_previstas,ic_inferior,ic_superior,n_meses_historico,"
                  "confianca,horizonte_meses,faixa_volume,status_validacao,motivo_status,"
                  "smape_backtest_pct,modelo,ultima_competencia,treinado_em,commit_codigo",
        "order": "ano_mes_previsto", "limit": str(top),
    }
    if cnes:
        params["cnes"] = f"eq.{cnes}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    linhas = sd._get("mart_forecast_demanda_hospital", params)
    # Medido em 2026-09-19: o mart publicado previa 2025-01 a 2025-03, ou seja,
    # dezoito meses no passado. A docstring já mandava conferir; mandar conferir é
    # o controle mais fácil de ignorar que existe. O campo faz o dado dizer.
    mes_atual = date.today().strftime("%Y-%m")
    for linha in linhas:
        previsto = str(linha.get("ano_mes_previsto") or "")
        linha["previsao_vencida"] = bool(previsto) and previsto < mes_atual
    return linhas


# ── Os cruzamentos que testaram explicações do %ICSAP ───────────────────────
#
# Três marts que existem porque uma hipótese foi testada, não porque um painel
# precisava de mais uma aba. Expor cada um junto do resultado é o que impede que
# alguém refaça o cruzamento e anuncie como achado o que já deu nulo.
@mcp.tool()
@procedencia("fonte_fluxo_icsap")
def oferta_local_e_icsap(uf: str = "", municipio_cod: str = "") -> list[dict]:
    """Cruzamento de leitos (CNES) com ICSAP (SIH) por município, 2024: leitos totais e
    SUS, leitos por mil, se o município não tem leito local, internações totais e
    sensíveis, %ICSAP e vulnerabilidade. Informe uf OU municipio_cod (6 dígitos).

    É o cruzamento que MEDIU a dependência do %ICSAP com a oferta local — chame
    metodologia('icsap') para o resultado por extenso antes de interpretar qualquer
    linha daqui.

    ATENÇÃO à assimetria das chaves: ICSAP é por município de RESIDÊNCIA do paciente e
    leitos são por município do ESTABELECIMENTO. `sem_leito` significa sem oferta
    LOCAL, não sem acesso — o residente pode se internar no município vizinho, o que
    fluxo_pacientes mostra."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,populacao,"
                  "leitos_total,leitos_sus,leitos_sus_por_mil,sem_leito,internacoes_total,"
                  "internacoes_por_mil,internacoes_icsap,pct_icsap,icsap_100k,ivs_score",
        "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_leitos_icsap_municipio", params)


@mcp.tool()
@procedencia("fonte_fluxo_icsap")
def cobertura_aps_e_icsap(uf: str = "", municipio_cod: str = "", ano: int = 2024) -> list[dict]:
    """Cruzamento da cobertura potencial da APS com o %ICSAP por município, 2024, com
    cobertura efetiva, equipes, internações sensíveis e vulnerabilidade.
    Informe uf OU municipio_cod (6 dígitos).

    ESTE CRUZAMENTO JÁ FOI FEITO E DEU NULO: Spearman +0,004 bruto e +0,018
    controlando porte e vulnerabilidade. A cobertura potencial satura acima de 100% em
    86% dos municípios e o que ela correlaciona forte é PORTE (ρ −0,54 com população).

    Use estes dados para mostrar a ausência de associação, não para reencontrá-la.
    Ver metodologia('cobertura_aps')."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,populacao,"
                  "cobertura_pct,cobertura_efetiva,qt_esf,internacoes_total,"
                  "internacoes_icsap,pct_icsap,icsap_100k,ivs_score",
        "ano": f"eq.{ano}", "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_cobertura_icsap_municipio", params)


@mcp.tool()
@procedencia("fonte_fluxo_icsap")
def equidade_aps_no_porte(uf: str = "", municipio_cod: str = "", ano: int = 2024) -> list[dict]:
    """Teste de robustez do cruzamento anterior, comparando cada município SÓ com os do
    mesmo quartil de porte: densidade de ESF por 10 mil habitantes (e não a cobertura %,
    que satura) contra %ICSAP (e não ICSAP/100k, que embute acesso hospitalar geral).
    Informe uf OU municipio_cod (6 dígitos).

    RESULTADO TAMBÉM NULO: ρ entre −0,02 e +0,18 dentro do porte. As colunas
    `pct_esf_no_porte` e `pct_icsap_no_porte` são percentis DENTRO do quartil, não
    nacionais — não os compare entre quartis diferentes.

    A existência deste mart é o ponto: a hipótese sobreviveu a uma troca de medida e a
    um controle mais duro, e continuou nula."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,populacao,"
                  "porte_quartil,esf_por_10k,pct_esf_no_porte,pct_icsap,icsap_100k,"
                  "pct_icsap_no_porte,ivs_score,ivs_quartil,atencao",
        "ano": f"eq.{ano}", "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_equidade_aps_municipio", params)


# ── Perfil e anomalia de causas de morte ────────────────────────────────────
@mcp.tool()
@procedencia("fonte_mortalidade_causa_municipio")
def anomalia_de_causa_municipio(municipio_cod: str = "", ano: int = 2024,
                                top: int = 50) -> list[dict]:
    """Células município × causa (CID-10 de 3 caracteres) × ano com excesso sobre a
    história do PRÓPRIO município em 2015–2019, por binomial negativa com controle de
    FDR a 1%. Cobre 2020–2024. Informe municipio_cod (6 dígitos).

    A comparação é do município consigo mesmo, não com outros — é detecção de mudança,
    não de nível. `esperado_relativo` e `p_relativo` trazem a versão que também desconta
    a variação nacional do ano.

    Os controles positivos do método são COVID em 2020–2021 e dengue apenas em 2024:
    se uma execução deixar de encontrá-los, o detector está quebrado.

    Excesso detectado NÃO é surto nem causa identificada. Pode ser mudança de
    codificação, de cobertura do registro ou de composição etária — consulte
    qualidade_registro antes de afirmar qualquer coisa sobre a causa."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,ano,causabas_3,obitos,esperado,"
                  "esperado_relativo,razao,p_proprio,p_relativo,excesso_proprio,"
                  "excesso_relativo",
        "ano": f"eq.{ano}", "order": "excesso_proprio.desc", "limit": str(top),
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    return sd._get("mart_anomalia_causa_municipio", params)


@mcp.tool()
@procedencia("fonte_mortalidade_causa_municipio")
def perfil_de_causas_municipio(uf: str = "", municipio_cod: str = "") -> list[dict]:
    """Coordenadas do perfil de causas de morte do município (2015–2024), DEPOIS de
    remover porte, estrutura etária, qualidade do registro e COVID: grupo, índice de
    inespecificidade e seis componentes. Informe uf OU municipio_cod (6 dígitos).

    São COMPONENTES, não indicadores: pc1 a pc6 não têm unidade e o sinal não tem
    direção boa ou ruim. Só seis ficaram acima do nulo multinomial — os demais eram
    indistinguíveis de ruído e não foram publicados.

    `grupo` é rótulo de agrupamento, não diagnóstico do município, e não autoriza
    comparação de qualidade entre grupos. `indice_inespecificidade` mede quanto do
    perfil é causa mal definida: alto significa registro fraco, não doença."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,obitos_periodo,grupo,"
                  "indice_inespecificidade,pc1,pc2,pc3,pc4,pc5,pc6",
        "order": "municipio_cod",
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    elif uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return sd._get("mart_perfil_mortalidade_municipio", params)


@mcp.tool()
@procedencia("fonte_ivs")
def contexto_social_municipio(municipio_cod: str = "", top: int = 200) -> list[dict]:
    """Eixos de contexto social e de sistema de saúde do município: quatro componentes
    (spc1 a spc4) resumindo 15 variáveis — vulnerabilidade, APS, leitos, gasto SIOPS,
    suplementar, CNES, natalidade e porte — mais as variáveis originais.
    Informe municipio_cod (6 dígitos).

    Os quatro eixos somam 61,5% da variância: quase 40% do que distingue os municípios
    NÃO está aqui. Componente não é índice e não tem unidade; não ranqueie por spc1.

    Redundância medida com o perfil de causas: o maior |r| entre os dois conjuntos é
    0,46, ou seja, as duas leituras são parcialmente a mesma coisa. Não as apresente
    como evidências independentes."""
    params = {
        "select": "municipio_cod,spc1,spc2,spc3,spc4,taxa_analfabetismo,ivs_score,"
                  "estab_por_10k,vinculos_plano_por_100_hab,gasto_proprio_saude_hab,"
                  "pct_prenatal_7mais,cobertura_pct,leitos_sus_por_mil,hosp_por_10k,log_pop",
        "order": "municipio_cod", "limit": str(top),
    }
    if municipio_cod:
        params["municipio_cod"] = f"eq.{municipio_cod}"
    return sd._get("mart_contexto_social_municipio", params)


# ── Copiloto: anomalias ──────────────────────────────────────────────────────
@mcp.tool()
@procedencia("fonte_obitos")
def detectar_anomalias(municipio_cod: str) -> dict:
    """COPILOTO: dado um município (6 dígitos), retorna um resumo priorizado de sinais —
    confiabilidade do registro, ICSAP vs. média nacional (~21%), e letalidade de dengue —
    para um briefing de gestor. Cada sinal traz o valor e a fonte; interprete com as regras
    de uso (sem causalidade; sinalizar baixa confiabilidade).

    O sinal `icsap` NÃO afirma nada sobre a atenção primária: ele vem acompanhado da oferta
    de leitos do próprio município justamente porque a associação medida entre leito local
    e %ICSAP é positiva e forte (§19). Relate os dois juntos ou não relate nenhum."""
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
            # A oferta local entra JUNTO com o sinal, nunca depois: o %ICSAP responde
            # fortemente a ter leito na cidade (§19), e o número sozinho induz a leitura
            # errada -- que era exatamente o que este campo dizia antes.
            lt = sd._get("mart_leitos_municipio",
                         {"select": "leitos_sus,leitos_sus_por_mil",
                          "municipio_cod": f"eq.{municipio_cod}", "ano": "eq.2024"})
            n_leitos = int(lt[0]["leitos_sus"] or 0) if lt and lt[0].get("leitos_sus") is not None else None
            if n_leitos is None:
                oferta = ("Oferta local de leitos indisponível para este município — "
                          "obtenha-a antes de interpretar o número.")
            elif n_leitos > 0:
                oferta = (f"Este município TEM {n_leitos} leitos SUS "
                          f"({lt[0].get('leitos_sus_por_mil')}/mil hab), e ter leito local está "
                          "associado a %ICSAP mais alto (+51% a +85% de internação sensível "
                          "conforme o porte, §19) — parte deste número pode ser oferta, não APS.")
            else:
                oferta = ("Este município NÃO tem leito SUS local, então a oferta hospitalar "
                          "local NÃO explica o número (municípios sem leito têm %ICSAP mediano "
                          "MENOR, 17,7% vs. 21,4%, §19). É um caso fora do padrão: investigue "
                          "o fluxo de internação dos residentes antes de qualquer leitura.")
            achados.append({"sinal": "icsap", "gravidade": "média" if p < 40 else "alta",
                            "detalhe": f"{p:.1f}% de internações evitáveis (média nacional ~21%). "
                                       f"NÃO conclua fragilidade da atenção primária. {oferta} "
                                       "Compare com pares de mesmo porte e oferta antes de interpretar.",
                            "leitos_sus": n_leitos,
                            "fonte": "SIH 2024 + CNES 2024 (mart_leitos_municipio)"})
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
@procedencia("fonte_clusters")
def comparar_com_pares(municipio_cod: str) -> dict:
    """ANÁLISE: compara um município (6 dígitos) com seus PARES — municípios do mesmo
    estrato de saúde (tercis fixos de mortalidade × vulnerabilidade × internações, 2023).
    Retorna, para cada métrica, o valor do município, a mediana dos pares e o percentil
    do município no grupo (0–100; alto = pior em mortalidade/vulnerabilidade).
    Comparação legítima: pares têm perfil estrutural semelhante, não só a mesma UF.
    Cobre ~1.700 municípios maiores; nos demais, retorna aviso."""
    alvo = sd._get("dim_cluster_municipio",
                   {"select": "municipio_cod,municipio_nome,uf_sigla,regiao,cluster,estrato_cod,perfil,"
                              "taxa_padronizada_100k,ivs_score,internacoes_100k",
                    "municipio_cod": f"eq.{municipio_cod}"})
    if not alvo:
        return {"erro": "município fora da base de estratos (cobre ~1.700 municípios "
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
        "arquetipo": m["perfil"], "estrato_cod": m.get("estrato_cod"), "n_pares": len(pares),
        "metricas": {
            "taxa_padronizada_100k": _stats("taxa_padronizada_100k"),
            "ivs_score": _stats("ivs_score"),
            "internacoes_100k": _stats("internacoes_100k"),
        },
        "pares_mais_proximos": [
            {"municipio": p["municipio_nome"], "uf": p["uf_sigla"],
             "taxa_padronizada_100k": p["taxa_padronizada_100k"]} for p in proximos
        ],
        "fonte": ("SIM/SIH/DataSUS + IBGE Censo 2022; estratos determinísticos por tercis fixos, "
                  "2023 (dim_cluster_municipio). O k-means anterior foi reprovado em teste de "
                  "estabilidade e substituído em 2026-08-29."),
    }


# ── Tradução: do indicador para a decisão ────────────────────────────────────
@mcp.tool()
@procedencia("fonte_fluxo_icsap")
def icsap_distancia_dos_pares(municipio_cod: str = "", uf: str = "", top: int = 20) -> list[dict]:
    """TRADUÇÃO: converte o indicador ICSAP na pergunta do gestor — "quanto meu
    município está acima de municípios COMPARÁVEIS em internações evitáveis, e o que
    isso representa?". Informe municipio_cod (6 dígitos) OU uf (ranking dos maiores).
    Retorna: pct_icsap do município, mediana dos pares, diferença em pontos
    percentuais, e a tradução — internacoes_acima_pares, leitos_equivalentes_ano
    (leitos que ficariam ocupados o ano inteiro) e custo_associado_reais.
    Pares = municípios do mesmo estrato de saúde; sem estrato, mesma faixa
    populacional e região. Comparar com a média nacional seria injusto.

    AO RELATAR, estas ressalvas são obrigatórias — sem elas o número engana:
    1. NÃO é economia disponível. Chegar à mediana exige INVESTIR em atenção
       primária, não cortar; o valor mede o tamanho do problema, não caixa a resgatar.
    2. Nem toda ICSAP é evitável — a Lista Brasileira reúne condições SENSÍVEIS à
       atenção primária; boa cobertura reduz, não zera. Por isso a referência é a
       mediana dos pares, nunca zero.
    3. Associação ECOLÓGICA (municipal): não é risco individual nem prova de causa.
    4. O %ICSAP responde à OFERTA HOSPITALAR LOCAL, e o efeito é grande — medido, não
       suposto (§19). Esta ressalva já foi o oposto disto ("onde falta leito, a eletiva
       some e a fatia de ICSAP sobe"); a hipótese foi testada contra os leitos do CNES e
       REFUTADA na direção e no mecanismo. O que vale: municípios SEM leito local têm
       %ICSAP MENOR (17,7% vs. 21,4%), e a presença de leito aumenta a internação por
       ICSAP em +51% a +85% conforme o porte, sem alterar as demais — é o numerador que
       cresce. Quem abre um hospital pequeno vê o %ICSAP SUBIR sem ter piorado a APS.
       Nunca conclua "atenção primária frágil" a partir deste número; cruze com oferta
       hospitalar, porte e cobertura privada antes de qualquer leitura.
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
@procedencia("fonte_dengue")
def canal_endemico_dengue(uf: str, ano: int = 2024) -> dict:
    """ANÁLISE: canal endêmico de dengue de uma UF (diagrama de controle). Compara os
    casos semanais do ano observado com a faixa esperada (quartis P25–P75 das mesmas
    semanas nos anos anteriores, 2015+, excluindo o ano observado). Retorna a banda
    semana a semana, quantas semanas ficaram acima do P75 (sinal de surto) e o status.
    Semanas acima ≥13 (um trimestre) = surto prolongado."""
    # Tabela agregada por UF (V044). O canal endemico sempre foi por UF: antes
    # esta chamada somava linhas municipais no servidor a cada invocacao.
    linhas = sd._get("mart_dengue_uf_semana",
                     {"select": "ano_epi,semana_epi,casos:casos_provaveis",
                      "uf_sigla": f"eq.{uf.upper()}",
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
@procedencia("fonte_dengue")
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


# ── Metodologia: o que o número NÃO sustenta ────────────────────────────────
#
# O conhecimento que separa esta plataforma de um dump do DataSUS é saber onde
# cada indicador engana. Ele morava em três lugares que ninguém consulta sob
# demanda: a prosa da página de metodologia, as docstrings (que um cliente pode
# nunca ler) e o campo `instructions`, que todo cliente carrega inteiro em toda
# sessão — use ou não. A cada armadilha nova, `instructions` crescia e competia
# com o contexto do usuário.
#
# `metodologia.json` é o catálogo canônico; esta ferramenta o serve. As
# `instructions` ficam com a regra operativa, e a evidência vem por chamada.
_CATALOGO: dict | None = None


def _catalogo() -> dict:
    global _CATALOGO
    if _CATALOGO is None:
        import json

        _CATALOGO = json.loads(
            (Path(__file__).with_name("metodologia.json")).read_text(encoding="utf-8")
        )
    return _CATALOGO


@mcp.tool()
def metodologia(indicador: str = "") -> dict:
    """DEFINIÇÃO E LIMITES de um indicador: numerador, denominador, unidade, defasagem,
    o que ele NÃO mede, as ressalvas obrigatórias ao relatar e as leituras que já foram
    TESTADAS E REFUTADAS nesta plataforma.

    Chame ANTES de interpretar um número, e sempre que for escrever a frase que
    acompanha o valor — é o que impede repetir uma explicação que a plataforma já
    descartou. Aceita o id do indicador (ex.: 'icsap') OU o nome de uma ferramenta
    (ex.: 'internacoes_evitaveis_icsap'). Sem argumento, devolve o índice."""
    catalogo = _catalogo()
    indicadores: dict[str, dict] = catalogo["indicadores"]
    chave = indicador.strip().lower()
    if not chave:
        return {
            "versao": catalogo["versao"],
            "indicadores": [
                {"id": k, "nome": v["nome"], "ferramentas": v["ferramentas"]}
                for k, v in indicadores.items()
            ],
            "como_usar": "Chame metodologia('<id>') ou metodologia('<nome_da_ferramenta>').",
        }
    if chave in indicadores:
        return {"id": chave, **indicadores[chave]}
    # Resolver pelo nome da ferramenta: o modelo acabou de chamar uma e sabe o
    # nome dela, não o id do indicador.
    for k, v in indicadores.items():
        if chave in [f.lower() for f in v["ferramentas"]]:
            return {"id": k, **v}
    return {
        "erro": f"indicador '{indicador}' não está no catálogo",
        "disponiveis": sorted(indicadores),
        "nota": "Sem entrada aqui, não há limite documentado para citar — diga isso "
                "em vez de improvisar uma ressalva.",
    }


def main() -> None:
    """Ponto de entrada do console script `saudeemdado-mcp`."""
    mcp.run()


if __name__ == "__main__":
    main()
