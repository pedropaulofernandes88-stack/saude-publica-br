"""
Toda ferramenta de dado tem limites declarados no catálogo de metodologia.

Motivo de existir: o valor do servidor MCP não é devolver o número do DataSUS —
é devolver junto o que aquele número NÃO sustenta. Enquanto esse conhecimento
vivia só em docstring e no campo `instructions`, ele tinha duas falhas: a
docstring um cliente pode nunca ler, e `instructions` todo cliente carrega
inteiro em toda sessão, use ou não. A cada armadilha nova o texto fixo crescia.

`metodologia.json` é o catálogo canônico e `metodologia()` o serve sob demanda.
O risco que estes testes cobrem é o mesmo que `fontes.test.mts` cobre do outro
lado: incompletude não reprova sozinha. Uma ferramenta nova sem entrada aqui
nasceria muda — devolvendo número sem limite documentado, que é exatamente a
superfície que o servidor existe para não ter.

Nenhum acesso a rede: tudo lê arquivo do repositório, e nada importa o módulo
(importá-lo puxaria o SDK do MCP e o cliente HTTP).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RAIZ = Path(__file__).resolve().parents[1]
PACOTE = RAIZ / "mcp_server" / "saudeemdado_mcp"
MCP = PACOTE / "__init__.py"
CATALOGO = PACOTE / "metodologia.json"

# Ferramentas que servem o catálogo, o dicionário ou os metadados do dataset —
# não entregam indicador epidemiológico e por isso não precisam de entrada.
FERRAMENTAS_META = {"metadados_dataset", "metodologia", "descricao_cid10"}

CAMPOS_OBRIGATORIOS = (
    "nome", "definicao", "numerador", "denominador", "unidade",
    "cobertura", "defasagem", "nao_mede", "ao_relatar", "refutado", "ferramentas",
)


@pytest.fixture(scope="module")
def texto_mcp() -> str:
    return MCP.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def catalogo() -> dict:
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ferramentas_do_servidor(texto_mcp: str) -> list[str]:
    """Nomes das @mcp.tool() declaradas, lidos do arquivo.

    Regex e não importação: o módulo importa `mcp` e o cliente HTTP, e este
    teste precisa rodar sem nenhum dos dois instalados.
    """
    return re.findall(
        r"@mcp\.tool\(\)\s*(?:@procedencia\([^)]*\)\s*)?def\s+([a-z_0-9]+)\(", texto_mcp
    )


# ---------------------------------------------------------------------------
# O catálogo cobre o servidor, e o servidor confirma o catálogo
# ---------------------------------------------------------------------------

def test_toda_ferramenta_de_dado_tem_indicador(catalogo, ferramentas_do_servidor):
    cobertas = {f for v in catalogo["indicadores"].values() for f in v["ferramentas"]}
    orfas = sorted(set(ferramentas_do_servidor) - cobertas - FERRAMENTAS_META)
    assert orfas == [], (
        f"ferramenta sem entrada em metodologia.json: {orfas}. Ela devolveria número "
        "sem limite documentado — declare o indicador, ou inclua em FERRAMENTAS_META "
        "se de fato não entrega indicador."
    )


def test_toda_ferramenta_citada_no_catalogo_existe(catalogo, ferramentas_do_servidor):
    existentes = set(ferramentas_do_servidor)
    citadas = {f for v in catalogo["indicadores"].values() for f in v["ferramentas"]}
    fantasmas = sorted(citadas - existentes)
    assert fantasmas == [], (
        f"o catálogo aponta para ferramenta que não existe mais: {fantasmas}. "
        "metodologia() resolveria por esse nome e devolveria entrada de algo removido."
    )


def test_ferramenta_nao_pertence_a_dois_indicadores(catalogo):
    """A resolução por nome de ferramenta precisa ser determinística."""
    vistas: dict[str, str] = {}
    duplicadas = []
    for ind, v in catalogo["indicadores"].items():
        for f in v["ferramentas"]:
            if f in vistas:
                duplicadas.append(f"{f}: {vistas[f]} e {ind}")
            vistas[f] = ind
    assert duplicadas == [], (
        f"ferramenta em mais de um indicador: {duplicadas}. metodologia('<ferramenta>') "
        "devolveria a primeira entrada por ordem de dicionário, silenciosamente."
    )


# ---------------------------------------------------------------------------
# Forma das entradas
# ---------------------------------------------------------------------------

def test_entradas_tem_todos_os_campos_preenchidos(catalogo):
    faltando = []
    for ind, v in catalogo["indicadores"].items():
        for campo in CAMPOS_OBRIGATORIOS:
            if campo not in v:
                faltando.append(f"{ind}.{campo} ausente")
            elif campo not in ("refutado",) and not v[campo]:
                faltando.append(f"{ind}.{campo} vazio")
    assert faltando == [], (
        f"entrada incompleta no catálogo: {faltando}. Campo vazio é pior que ausente — "
        "aparenta ter sido preenchido. (`refutado` pode ser lista vazia: nem todo "
        "indicador teve hipótese testada e derrubada.)"
    )


def test_todo_indicador_declara_o_que_nao_mede(catalogo):
    """O campo que justifica o catálogo existir."""
    sem = sorted(i for i, v in catalogo["indicadores"].items() if len(v["nao_mede"]) < 1)
    assert sem == [], (
        f"indicador sem nenhum limite declarado: {sem}. Todo indicador de saúde tem "
        "pelo menos um uso indevido conhecido; não declarar nenhum é omissão, não elogio."
    )


def test_refutacao_traz_evidencia(catalogo):
    """`refutado` é reservado a hipótese testada — e teste tem origem citável."""
    problemas = []
    for ind, v in catalogo["indicadores"].items():
        for i, r in enumerate(v["refutado"]):
            for campo in ("leitura", "resultado", "evidencia", "consequencia"):
                if not r.get(campo):
                    problemas.append(f"{ind}.refutado[{i}].{campo}")
    assert problemas == [], (
        f"refutação sem {problemas}: uma hipótese só entra como REFUTADA com o que a "
        "derrubou e o que muda na prática. Sem isso é opinião com autoridade emprestada."
    )


# ---------------------------------------------------------------------------
# Pareamento com o servidor
# ---------------------------------------------------------------------------

def test_instructions_mandam_chamar_a_metodologia(texto_mcp: str):
    """As regras fixas encolheram porque apontam para a ferramenta.

    Se o ponteiro sumir, o conteúdo que saiu de `instructions` fica inalcançável
    para um cliente que só lê as regras do servidor.
    """
    i = texto_mcp.find("instructions=(")
    bloco = texto_mcp[i:i + 4000]
    assert "metodologia(" in bloco, (
        "as instructions não mandam mais chamar metodologia(); o catálogo vira "
        "conhecimento que existe e ninguém consulta"
    )


# ---------------------------------------------------------------------------
# A procedência que a ferramenta promete tem de existir em algum lugar
# ---------------------------------------------------------------------------
#: Chaves que o MCP usa e que nenhum script deste repositório declara. Duas
#: situações diferentes, as duas conhecidas e nenhuma silenciosa:
#:
#: fonte_sisagua — ainda NÃO existe em meta_dataset, então a ferramenta de água
#: cai no texto genérico de `_procedencia` ("DATASUS/Ministério da Saúde e
#: IBGE"), que não é falso mas é vago: o SISAGUA é do Ministério da Saúde e não
#: do DataSUS. pipeline_sisagua.py só grava Parquet e quem sobe o mart é
#: publicar.py; nenhum dos dois escreve meta_dataset, e decidir onde a chave
#: entra é desenho do pipeline, não do servidor.
#:
#: fonte_cobertura_aps — mesmo caso do SISAGUA: `pipeline_cobertura_aps.py`
#: constrói o mart e não publica chave nenhuma em meta_dataset, então a cobertura
#: da APS cita o genérico. O e-Gestor AB é do Ministério da Saúde e não do
#: DataSUS, então o genérico erra a atribuição por um nível.
#:
#: fonte_agravo_hospital — está VIVA no banco e em site/public/sdata/meta.json,
#: e mesmo assim nenhum script do repositório a declara. A citação funciona hoje
#: e não é reproduzível a partir do código: republicar do zero a perderia.
PROCEDENCIA_SEM_PIPELINE = {"fonte_sisagua", "fonte_cobertura_aps", "fonte_agravo_hospital"}


def test_chave_de_procedencia_e_declarada_por_algum_pipeline(texto_mcp: str):
    """Uma chave inventada no servidor não quebra nada — degrada em silêncio.

    `_procedencia` faz `m.get(chave, <texto generico>)`: errar o nome da chave
    devolve uma citação vaga em vez de erro, e a ferramenta continua respondendo.
    Este teste é a única coisa entre um typo e um numero publicado citando
    "DATASUS/Ministerio da Saude e IBGE" no lugar da fonte real.

    Offline de proposito: le o que os pipelines DECLARAM, nao o que o banco tem.
    Chave declarada e ausente em producao e outro defeito, e nenhum pipeline
    confere a resposta do POST que a grava.
    """
    usadas = set(re.findall(r'@procedencia\("([a-z_]+)"\)', texto_mcp))
    declaradas = set()
    for script in (RAIZ / "scripts").glob("*.py"):
        # Dois formatos convivem nos pipelines: `{"chave": "fonte_x", ...}` e a
        # tupla `("fonte_x", "...")`. Casar a string citada cobre os dois.
        declaradas |= set(
            re.findall(r'"(fonte_[a-z_]+)"', script.read_text(encoding="utf-8"))
        )
    orfas = sorted(usadas - declaradas - PROCEDENCIA_SEM_PIPELINE)
    assert orfas == [], (
        f"o MCP cita procedência que nenhum pipeline grava: {orfas}. Ou a chave está "
        "escrita errada, ou o pipeline da fonte precisa publicá-la em meta_dataset. "
        "Enquanto isso a ferramenta devolve a citação genérica sem reclamar."
    )


def test_catalogo_viaja_dentro_do_pacote():
    """O wheel do PyPI só leva o diretório do pacote.

    Se o catálogo migrar para data/ ou para o site, `uvx saudeemdado-mcp` passa a
    subir sem ele e metodologia() quebra só na máquina do usuário.
    """
    assert CATALOGO.parent == PACOTE, (
        "metodologia.json saiu de dentro de saudeemdado_mcp/ — ele não seria "
        "empacotado no wheel"
    )
    assert "metodologia.json" in MCP.read_text(encoding="utf-8"), (
        "o servidor não referencia mais metodologia.json"
    )
