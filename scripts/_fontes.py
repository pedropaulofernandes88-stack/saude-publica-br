"""
_fontes.py — onde cada fonte mora, declarado uma vez.

POR QUE ISTO EXISTE
-------------------
O caminho de uma fonte estava digitado em toda parte. Medido em 2026-09-11:

    /dissemin/publicos/SIHSUS/200801_/Dados ....... 8 arquivos
    /dissemin/publicos/SINAN/DADOS/FINAIS ......... 6
    /dissemin/publicos/SINAN/DADOS/PRELIM ......... 4
    /dissemin/publicos/CNES/200508_/Dados/LT ...... 4

Cópia não é só feiúra — ela DIVERGE, e divergiu. O `observar_fontes.py` vigiava
o SIM em `SIM/CID10/DORES` e mais nada, enquanto o `pipeline_v2.py` lê de
`CID10/DORES` **e** de `SIM/PRELIM/DORES`. O diretório preliminar é onde moram
os anos mais recentes e mais voláteis — exatamente o que mais precisa de
vigilância — e era o único que ninguém observava. Nada acusou: fonte não
observada não dá erro, ela só deixa de avisar.

O registro fecha isso por construção. O pipeline e o observador passam a ler a
MESMA declaração, então não existe mais o estado em que um conhece um caminho
que o outro não conhece.

O QUE ELE CARREGA, E O QUE NÃO
-------------------------------
Carrega o que é **operacional e duplicado**: id, rótulo de observação, e os
lugares onde a fonte mora, com o padrão de nome de arquivo de cada um.

NÃO carrega o que é **editorial**: nome de exibição, o que a fonte traz e a
ressalva que o leitor precisa ler continuam em `site/lib/fontes.ts`, que é onde
o site os renderiza. Duas listas, um `id` em comum, e um teste que exige que os
ids batam — ver `tests/test_registro_de_fontes.py`.

Também não carrega tabela → fonte: isso já vive em `FONTE_DA_TABELA` no site,
já é guardado contra tabela publicada sem classificação, e trazer para cá seria
criar a segunda definição em vez de eliminar a primeira.

COMO USAR
---------
    from _fontes import fonte

    FTP_DIR        = fonte("sim").local("consolidado").caminho
    FTP_DIR_PRELIM = fonte("sim").local("preliminar").caminho

O nome local da constante fica: quem lê o pipeline continua vendo `FTP_DIR`.
O que muda é de onde vem o valor.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: O FTP do DataSUS. Repetido em `_datasus_ftp.HOST_PADRAO` de propósito: aquele
#: módulo é o cliente e precisa de um padrão próprio para funcionar sozinho.
#: O teste do registro exige que os dois concordem.
HOST_FTP = "ftp.datasus.gov.br"

#: O bucket aberto do Ministério. SIM, SINASC e PNI publicam CSV/ZIP aqui.
S3_CKAN = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br"


@dataclass(frozen=True)
class Local:
    """Um lugar onde a fonte mora, e o que reconhecer lá.

    `padrao` é o regex do NOME DO ARQUIVO, usado pelo observador para filtrar a
    listagem do diretório. Vazio significa "não dá para listar por nome" — o
    caso das APIs, que respondem a consulta e não entregam diretório.
    """

    nome: str                    # como o pipeline se refere a este lugar
    tipo: str                    # "ftp" | "s3" | "api"
    caminho: str                 # diretório FTP, prefixo de URL, ou endpoint
    padrao: str = ""             # regex do nome do arquivo
    observar: bool = True        # entra na rodada do observador?
    nota: str = ""               # por que este lugar existe, ou por que não vigiar
    #: Só para `tipo="ftp"`. Nem toda fonte do projeto é do DataSUS: a ANS tem
    #: FTP próprio, e o observador nunca soube disso porque o caminho dela
    #: morava só dentro do pipeline.
    host: str = HOST_FTP


@dataclass(frozen=True)
class Fonte:
    """Uma fonte publicada. O `id` é o mesmo de `site/lib/fontes.ts`."""

    id: str
    base: str = ""               # rótulo nas observações (SIM, SIH, SINAN…)
    locais: tuple[Local, ...] = field(default_factory=tuple)
    #: Motivo de não ser observável. Preenchido <=> `locais` sem nada a observar.
    dispensa: str = ""

    def local(self, nome: str) -> Local:
        for lo in self.locais:
            if lo.nome == nome:
                return lo
        disponiveis = ", ".join(lo.nome for lo in self.locais) or "nenhum"
        raise KeyError(f"fonte {self.id!r} não declara o local {nome!r} "
                       f"(tem: {disponiveis})")

    @property
    def observavel(self) -> bool:
        return any(lo.observar for lo in self.locais)


FONTES: tuple[Fonte, ...] = (
    Fonte(
        id="sim", base="SIM",
        locais=(
            Local("consolidado", "ftp", "/dissemin/publicos/SIM/CID10/DORES",
                  r"^DO[A-Z]{2}20(1[89]|2\d)\.dbc$"),
            # O ano preliminar vive em outro diretório e MIGRA para CID10/DORES
            # quando fecha — 2024 fez essa passagem em 2025-12-23. É o diretório
            # mais volátil do projeto e era o único do SIM fora da observação.
            Local("preliminar", "ftp", "/dissemin/publicos/SIM/PRELIM/DORES",
                  r"^DO[A-Z]{2}20(2\d)\.dbc$"),
            # O CSV nacional aberto. Observado por HEAD (Content-Length,
            # Last-Modified, ETag), não por listagem: o S3 não lista.
            Local("csv_aberto", "s3", f"{S3_CKAN}/SIM", nota="HEAD por ano, em observar_sim()"),
            # A tabela de categorias da CID-10, não os óbitos. Fica aqui para que
            # o caminho não volte a ser digitado dentro do pipeline; não é
            # observada porque não é série — é dicionário, e revisão dele não
            # muda número publicado sem passar por reingestão.
            Local("tabela_cid10", "ftp", "/dissemin/publicos/SIM/CID10/TABELAS",
                  observar=False, nota="CID10.DBF, dicionário de categorias"),
        ),
    ),
    Fonte(
        id="sih", base="SIH",
        locais=(
            # ~5.400 arquivos (27 UF x ~200 competências desde 2008): o padrão
            # recorta o período que o projeto publica, senão a observação diária
            # vira ruído que treina a gente a ignorar a issue.
            Local("dados", "ftp", "/dissemin/publicos/SIHSUS/200801_/Dados",
                  r"^RD[A-Z]{2}(2[2-9])\d{2}\.dbc$"),
        ),
    ),
    Fonte(
        id="sinan", base="SINAN",
        locais=(
            Local("finais", "ftp", "/dissemin/publicos/SINAN/DADOS/FINAIS",
                  r"^DENGBR\d{2}\.dbc$"),
            Local("preliminar", "ftp", "/dissemin/publicos/SINAN/DADOS/PRELIM",
                  r"^DENGBR\d{2}\.dbc$"),
        ),
    ),
    Fonte(
        id="sifilis", base="SINAN",
        locais=(
            # Só existe em PRELIM: não há SIF* em DADOS/FINAIS, nem para 2007.
            # Procurar em FINAIS seria vigiar o vazio.
            Local("preliminar", "ftp", "/dissemin/publicos/SINAN/DADOS/PRELIM",
                  r"^SIF[ACG]BR\d{2}\.dbc$"),
        ),
    ),
    Fonte(
        id="sinasc", base="SINASC",
        locais=(
            Local("dnres", "ftp", "/dissemin/publicos/SINASC/NOV/DNRES",
                  r"^DN[A-Z]{2}20(1[89]|2\d)\.dbc$"),
            Local("csv_aberto", "s3", f"{S3_CKAN}/SINASC/csv", observar=False,
                  nota="rota alternativa do pipeline; a observação vai pelo FTP"),
        ),
    ),
    Fonte(
        id="pni", base="PNI",
        locais=(
            # Zips mensais, e o S3 REESCREVE mês já publicado: maio/2025 foi
            # regravado em 28/08/2026. Sem observar, o mart fica com o retrato
            # antigo para sempre.
            Local("zip_mensal", "s3", f"{S3_CKAN}/PNI/csv",
                  nota="HEAD por ano/mês, em observar_pni()"),
        ),
    ),
    Fonte(
        id="oncologia", base="ONCOLOGIA",
        locais=(
            Local("dados", "ftp", "/dissemin/publicos/painel_oncologia/Dados",
                  r"^POBR\d{4}\.dbc$"),
        ),
    ),
    Fonte(
        id="cnes", base="CNES",
        locais=(
            # O pipeline de leitos ingere só a competência de DEZEMBRO de cada
            # ano (LT{UF}{AA}12). Observar as outras onze seria vigiar arquivo
            # que o projeto não usa.
            Local("leitos", "ftp", "/dissemin/publicos/CNES/200508_/Dados/LT",
                  r"^LT[A-Z]{2}(1[5-9]|2\d)12\.dbc$"),
            Local("estabelecimentos", "api",
                  "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos",
                  observar=False,
                  nota="API por consulta: não há arquivo com tamanho e data"),
        ),
    ),
    Fonte(
        id="sisagua", base="SISAGUA",
        locais=(
            # A raiz da API. O endpoint folha (`controle-mensal-parametros-basicos`)
            # fica no pipeline, que é quem escolhe qual consultar.
            Local("api", "api", "https://apidadosabertos.saude.gov.br/sisagua",
                  observar=False,
                  nota="responde por codigo_ibge; uf não tem índice e estoura em 502"),
        ),
        dispensa="API de dados abertos responde por consulta (codigo_ibge), não por "
                 "arquivo com tamanho e data — não há o que comparar entre rodadas",
    ),
    Fonte(
        id="aps",
        dispensa="e-Gestor/SISAB serve painel, não arquivo com tamanho e data estáveis",
        locais=(
            Local("cobertura", "api", "https://relatorioaps-prd.saude.gov.br/cobertura/aps",
                  observar=False,
                  nota="JSON por consulta; o e-Gestor serve painel, não arquivo "
                       "com tamanho e data estáveis"),
        ),
    ),
    Fonte(
        id="siops",
        dispensa="SIOPS publica por consulta interativa, sem diretório versionado",
    ),
    Fonte(
        id="ans",
        locais=(
            Local("beneficiarios", "ftp",
                  "FTP/PDA/informacoes_consolidadas_de_beneficiarios-024",
                  observar=False, host="ftp.dadosabertos.ans.gov.br",
                  nota="FTP da ANS, não do DataSUS"),
        ),
        dispensa="ANS tem calendário próprio de divulgação, fora do DataSUS",
    ),
    Fonte(
        id="ibge",
        dispensa="população censitária/projeções não são revisadas de surpresa",
    ),
    Fonte(
        id="derivado",
        dispensa="não é coleta: sai dos marts acima e muda quando eles mudam",
    ),
)

_POR_ID = {f.id: f for f in FONTES}


def fonte(id_: str) -> Fonte:
    """A fonte pelo id, ou KeyError com a lista do que existe."""
    try:
        return _POR_ID[id_]
    except KeyError:
        raise KeyError(f"fonte {id_!r} não existe no registro "
                       f"(tem: {', '.join(sorted(_POR_ID))})") from None


def diretorios_ftp() -> list[tuple[str, str, str]]:
    """As triplas (base, diretório, padrão) que o observador percorre.

    Uma por LOCAL, não por fonte: sífilis e dengue dividem o mesmo diretório com
    padrões diferentes, e o SIM tem consolidado e preliminar.
    """
    return [(f.base, lo.caminho, lo.padrao)
            for f in FONTES for lo in f.locais
            if lo.tipo == "ftp" and lo.observar and lo.padrao]


def observadas() -> dict[str, str]:
    """Fonte publicada → rótulo `base` da observação."""
    return {f.id: f.base for f in FONTES if f.observavel}


def nao_observadas() -> dict[str, str]:
    """Fonte publicada que NÃO é observada, com o motivo."""
    return {f.id: f.dispensa for f in FONTES if not f.observavel}
