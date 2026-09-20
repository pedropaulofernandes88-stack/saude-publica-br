"""
sondar_convenios.py — a fonte de convênios federais × CNES está pronta?
========================================================================

    python scripts/sondar_convenios.py
    python scripts/sondar_convenios.py --json

Sai com 0 quando a fonte serve e o cruzamento tem chave dos DOIS lados. Sai com
≠ 0 enquanto não, nomeando cada razão. É portão, não relatório: rodar primeiro,
antes de escrever uma linha de coletor.

POR QUE ESTA FONTE INTERESSA
-----------------------------
Todas as treze fontes publicadas hoje descrevem SAÚDE: óbito, internação,
notificação, leito, dose, exame. Nenhuma liga **dinheiro federal a
estabelecimento**. Convênios da União cruzados com o CNES abrem esse eixo, e é o
único item do backlog de fontes que não é aprofundamento de um eixo existente.

O QUE FOI MEDIDO EM 2026-09-20, ANTES DE QUALQUER CÓDIGO DE COLETA
-------------------------------------------------------------------

**1. O portal NÃO é rota. Está atrás de AWS WAF com CAPTCHA.**

`portaldatransparencia.gov.br/download-de-dados/convenios` responde 200 e a
página até abre, mas o ativo que monta os links de download
(`/static/js/portal/download-planilhas.js`) devolveu, para um cliente HTTP comum,
um desafio "Human Verification" da AWS WAF — **com HTTP 200**. O caminho por ano
(`/download-de-dados/convenios/2026`) devolve `AccessDenied` de S3.

Ou seja: raspar o portal é frágil por desenho e passaria a depender de resolver
CAPTCHA, o que este projeto não faz. A rota é a API oficial, e só ela.

**2. A API oficial serve, é documentada, e EXIGE CHAVE.**

`api.portaldatransparencia.gov.br/v3/api-docs` é público (167 KB de OpenAPI) e
declara seis endpoints de convênio. A consulta sem chave devolve **401**:

    {"Erro na API": "Chave de API não informada! Para obter a chave acesse
     http://www.portaldatransparencia.gov.br/api-de-dados/cadastrar-email"}

A chave sai de um cadastro de e-mail, é gratuita, e **tem de ser feita por uma
pessoa** — não por este projeto. Ela entra no `.env` como
`PORTAL_TRANSPARENCIA_API_KEY`, e é o que este portão espera encontrar.

**3. Os filtros tornam o recorte barato, e um deles é o que salva a fonte.**

`/api-de-dados/convenios` aceita `codigoIBGE` (município), `uf`, `funcao` e
`subfuncao` (classificação SIAFI — **função 10 é Saúde**), faixas de data de
vigência, publicação e última liberação, e faixas de valor. Só `pagina` é
obrigatório. Recortar saúde por município é uma consulta, não uma varredura do
país inteiro.

**4. A resposta traz as DUAS chaves de cruzamento, e isso não era garantido.**

`ConvenioDTO` tem 21 campos. Os que importam:

    convenente.cnpjFormatado ........ CNPJ de quem recebeu  → cruza com CNES
    convenente.cpfFormatado ......... quando é pessoa física
    convenente.razaoSocialReceita ... nome na Receita
    municipioConvenente.codigoIBGE .. município           → cruza com tudo
    orgao.{nome,codigoSIAFI,cnpj} ... quem concedeu
    valor ........................... valor TOTAL pactuado
    valorLiberado ................... valor efetivamente LIBERADO
    valorContrapartida .............. contrapartida local
    situacao, datas de vigência/publicação/última liberação/conclusão

**5. E do NOSSO lado a chave falha exatamente onde o dinheiro está.**

    ⚠️ ESTA SEÇÃO ESTÁ ERRADA. Ver "ESTES NÚMEROS ESTÃO ERRADOS" mais abaixo:
    o campo foi medido pela API do CNES, que o omite; no FTP ele existe em
    99,4%, e o casamento vai de 15,6% para 81,9%. Fica aqui inteira porque o
    erro é o ensinamento, não porque ainda valha.

Medido em 600 estabelecimentos de 10 municípios de portes diferentes, pela API
do CNES (campos `numero_cnpj` e `numero_cnpj_entidade`):

    natureza jurídica (1º dígito)   estab.   com CNPJ
    1 Administração pública ......... 26        7,7%   <-- o problema
    2 Entidade empresarial ......... 415       98,8%
    3 Sem fins lucrativos ........... 14       92,9%
    4 Pessoa física ................ 145        0,0%   (têm CPF, e não recebem
                                                        convênio como entidade)

O CNPJ da **mantenedora** (`numero_cnpj_entidade`), que seria o fallback óbvio,
vem preenchido em **5%** dos estabelecimentos — não resolve.

CONSEQUÊNCIA DE DESENHO, e é a razão de sondar antes de codar: um mart que
ligasse convênio a estabelecimento SÓ por CNPJ cobriria bem o setor privado e
filantrópico e **perderia sistematicamente o público**, que é para onde vai a
maior parte do convênio federal em saúde — porque quem assina é a prefeitura ou
a secretaria estadual, cujo CNPJ não é o do hospital.

Daí o grão duplo, e ele tem de estar no mart desde o primeiro dia:

  * **município × ano** (por `municipioConvenente.codigoIBGE`): cobertura
    nacional, sem depender de CNPJ nenhum;
  * **estabelecimento** (por CNPJ): preciso onde existe, e com uma coluna que
    diga POR QUE não existe quando não existe — nunca uma linha ausente sem
    explicação, que é [[coleta-ausencia-vs-falha]].

**6. A ressalva editorial que o número exige.**

`valor` é o pactuado; `valorLiberado` é o que saiu do caixa. Convênio assinado
não é dinheiro entregue, e um mapa de "investimento federal por município" feito
sobre `valor` descreve intenção, não execução. Os dois vão para o mart, e a
metodologia tem de dizer qual responde a qual pergunta.

MEDIDO COM A CHAVE, EM 2026-09-20 — E TRÊS ARMADILHAS QUE A ESPECIFICAÇÃO OMITE
-------------------------------------------------------------------------------

**a) `funcao` sozinho é recusado.** HTTP 400: "escolha um período de até 1 mês ou
um convenente ou um órgão/entidade ou uma localidade ou um número de convênio".
O OpenAPI marca todos os parâmetros como opcionais menos `pagina`. A regra só
aparece batendo na API, e define a forma da varredura: âncora obrigatória.

**b) `codigoIBGE` exige SETE dígitos e falha em SILÊNCIO com seis.** Ver o
comentário de `MUNICIPIOS_AMOSTRA`. É a armadilha mais perigosa desta fonte.

**c) A API escreve `descricaoSubfuncap`**, com typo, dentro de `subfuncao`. Quem
ler `descricaoSubfuncao` recebe `None` sem erro nenhum.

Página: **15 registros**, fixos. `dataReferencia` é a data do RETRATO (a mesma em
todas as linhas), não a data do convênio. Linhas repetidas por convenente NÃO são
duplicatas: são convênios distintos (ids e códigos distintos) da mesma entidade —
somar `valor` sobre linhas está correto.

A TAXA DE CASAMENTO, E A DECISÃO DE GRÃO QUE ELA IMPÕE
-------------------------------------------------------
Medido em 10 municípios de todas as regiões, 782 convênios de função 10, 139
entidades distintas, contra o CNPJ de todos os estabelecimentos do CNES daqueles
mesmos municípios:

    por entidade, CNPJ completo (14) ..... 22/139 = 15,8%
    por entidade, RAIZ (8 dígitos) ....... 28/139 = 20,1%
    por linha (convênio), CNPJ completo .. 122/782 = 15,6%
    POR VALOR PACTUADO ................... R$ 174,1 mi de R$ 2,95 bi = 5,9%
    POR VALOR LIBERADO ................... R$ 138,2 mi de R$ 2,51 bi = 5,5%

O critério declarado ANTES de olhar (`CASAMENTO_MINIMO_PCT`) era 20%. Por
contagem, as medidas ficam entre 15,6% e 20,1% — abaixo ou encostando. Por
VALOR, que é o denominador que importa para quem pergunta "para onde foi o
dinheiro", cai para **5,9%**.

╔══════════════════════════════════════════════════════════════════════════════╗
║ ESTES NÚMEROS ESTÃO ERRADOS, E A CORREÇÃO ESTÁ LOGO ABAIXO                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Ficam aqui porque o ERRO é o ensinamento: eles saíram da **API** do CNES, que
omite o campo que responde a pergunta. Conferido no FTP em 2026-09-20, sobre os
21.023 convênios nacionais e os 335.702 CNPJ distintos dos 27 arquivos `ST`:

    por CONVÊNIO ......................... 17.224/21.023 = **81,9%**
    por ENTIDADE ......................... 4.113/5.558  = **74,0%**
    por VALOR ............................ R$ 26,98 bi de R$ 72,25 bi = 37,3%
    por VALOR, sem organismos internac. .. R$ 26,98 bi de R$ 40,52 bi = **66,6%**

**O grão por estabelecimento SE SUSTENTA.** O corte declarado de 20% é superado
com folga em todo denominador.

POR QUE EU ERREI, E COMO NÃO REPETIR
-------------------------------------
Eu media `numero_cnpj_entidade` da API, que vem preenchido em 5%. O FTP traz o
mesmo conceito em `CNPJ_MAN` (CNPJ da MANTENEDORA), preenchido em **99,4%** dos
43.604 estabelecimentos públicos medidos. A estrutura é complementar e faz
sentido: estabelecimento privado, filantrópico ou de pessoa física carrega o
próprio documento em `CPF_CNPJ` (100%); estabelecimento público carrega o da
mantenedora — que é a prefeitura ou a secretaria, exatamente quem assina
convênio federal.

Ou seja: eu havia concluído que o dado brasileiro tem um limite estrutural que
impede ligar dinheiro a serviço. Era limitação da **API**, não do cadastro. A
lição: antes de declarar limite estrutural de uma fonte, conferir a mesma fonte
por outra ROTA. `coleta-ausencia-vs-falha` vale também para campo vazio.

Os 37,3% por valor são menores porque R$ 31,73 bi estão em 91 convênios com
organizações internacionais, que não são estabelecimento do CNES por definição —
e não deveriam casar.

ARMADILHA TÉCNICA DO FTP DO CNES, que provavelmente é a razão de este caminho
nunca ter sido usado: os arquivos `ST` **não abrem com `dbfread`**. O cabeçalho
declara 208 campos e não traz o terminador `0x0D` do padrão DBF — há `0x00` no
lugar, e o leitor varre além do cabeçalho até estourar com "unpack requires a
buffer of 32 bytes". O DBC descompacta normalmente; quem quebra é o leitor de
DBF. A saída é ler pelo tamanho declarado no cabeçalho em vez de procurar o
terminador, conferindo que a soma dos campos bate com o tamanho do registro.

Achado que veio junto e vale por si: a execução geral (liberado/pactuado) é de
**85,0%** na amostra. Bem acima do que um caso isolado de 48% sugeria — não
extrapolar execução a partir de exemplo.

Consequência de desenho: o mart nasce com grão **município × ano**, e o CNPJ
entra como ENRIQUECIMENTO opcional — coluna que liga ao CNES quando existe, com
outra coluna dizendo por que não ligou quando não existe. Nunca o contrário.

Duas hipóteses minhas foram testadas e REFUTADAS no caminho, e ficam registradas
para ninguém refazê-las:

  * *"o casamento falha porque convênio e estabelecimento estão sob filiais
    diferentes do mesmo CNPJ"* — a raiz de 8 dígitos acrescenta 6 entidades em
    139 (+4,3 pontos). Ajuda, mas não é o mecanismo dominante;
  * *"as linhas repetidas por entidade são duplicatas"* — não são. São convênios
    distintos.

O QUE SEGUE SEM MEDIÇÃO
------------------------
O volume nacional. Paginar 5.570 municípios a 15 registros por página custa caro
em requisições, e o limite publicado é 400/min (700 entre 00h e 06h; convênios
não está na lista de APIs restritas). Medir isso é a primeira coisa que o
coletor deve fazer, e com limitador próprio: a API do CNES derrubou a conexão
nesta sondagem quando foi consultada sem pausa.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Windows usa cp1252 quando a saída é redirecionada, e um único caractere fora
# da tabela (o ❌ do veredito) derruba o script DEPOIS de todo o trabalho feito.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

API = "https://api.portaldatransparencia.gov.br/api-de-dados/convenios"
DOCS = "https://api.portaldatransparencia.gov.br/v3/api-docs"
CADASTRO = "http://www.portaldatransparencia.gov.br/api-de-dados/cadastrar-email"
VARIAVEL = "PORTAL_TRANSPARENCIA_API_KEY"

#: Função SIAFI da Saúde. É o recorte inteiro desta fonte.
FUNCAO_SAUDE = "10"

#: Municípios da amostra, em código IBGE de **SETE** dígitos.
#:
#: Sete, e não os seis que o projeto usa em toda parte, porque a API SÓ aceita
#: sete — e o modo como ela recusa seis é a pior armadilha desta fonte. Medido
#: em 2026-09-20:
#:
#:     codigoIBGE=355030  -> HTTP 200, lista VAZIA
#:     codigoIBGE=3550308 -> HTTP 200, 15 registros
#:
#: Um coletor que usasse `municipio_cod` (o canônico daqui) publicaria um mart
#: em que NENHUM município tem convênio, com exit 0 e sem uma linha de erro. É
#: [[coleta-ausencia-vs-falha]] com o gatilho pronto.
#:
#: O sete dígitos já existe em `data/refs/municipios.parquet`, coluna
#: `municipio_cod7` — não é preciso calcular dígito verificador.
MUNICIPIOS_AMOSTRA = ["3524402", "3549904", "3131307", "2611606", "4115200",
                      "5002704", "2304400", "1501402", "3106200", "4314902"]

#: Abaixo disso, o grão por ESTABELECIMENTO não se sustenta e o mart deve sair
#: só por município. Não é regra universal: é o limiar que este projeto aceita
#: para publicar uma ligação como se fosse a regra, e está aqui para ser
#: discutido antes de olhar o resultado — ver [[criterio-antes-do-dado]].
CASAMENTO_MINIMO_PCT = 20.0


def carregar_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for linha in f.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, _, v = linha.partition("=")
                env[k.strip()] = v.strip()
    env.update(os.environ)
    return env


def _get(url: str, chave: str | None = None, timeout: int = 90) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    if chave:
        req.add_header("chave-api-dados", chave)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def documentacao_no_ar() -> tuple[bool, str]:
    """A especificação é pública e não precisa de chave. Se ela cair, a API mudou."""
    status, corpo = _get(DOCS)
    if status != 200:
        return False, f"OpenAPI respondeu {status}"
    try:
        doc = json.loads(corpo)
    except ValueError:
        return False, "OpenAPI não devolveu JSON (possível desafio de WAF)"
    caminhos = [p for p in doc.get("paths", {}) if "convenio" in p.lower()]
    if not caminhos:
        return False, "a especificação não declara mais endpoint de convênio"
    return True, f"{len(caminhos)} endpoints de convênio declarados"


def medir_com_chave(chave: str) -> dict:
    """O que só a resposta real responde. Roda quando a chave existe.

    Toda consulta leva ÂNCORA, e isso não é preferência: a API recusa filtro de
    função sozinho, com 400 e esta mensagem —

        "Para usar filtros em convênios, escolha um período de até 1 mês ou um
         convenente ou um órgão/entidade ou uma localidade (município ou
         estado-UF) ou um número de convênio."

    A especificação OpenAPI marca TODOS os parâmetros como opcionais menos
    `pagina`, então esta regra só aparece batendo na API. A âncora escolhida
    aqui é o município, que é o grão do projeto.
    """
    medida: dict = {}
    ancora = MUNICIPIOS_AMOSTRA[0]
    status, corpo = _get(
        f"{API}?pagina=1&codigoIBGE={ancora}&funcao={FUNCAO_SAUDE}", chave)
    medida["status_funcao_saude"] = status
    if status != 200:
        medida["erro"] = corpo[:300].decode("utf-8", "replace")
        return medida
    pagina = json.loads(corpo)
    medida["registros_por_pagina"] = len(pagina)
    medida["campos"] = sorted(pagina[0]) if pagina else []

    # Quantos convenios de saude existem por municipio da amostra, e com que
    # CNPJ. A taxa de casamento contra o CNES fecha a conta do grao.
    cnpjs: set[str] = set()
    por_municipio: dict[str, int] = {}
    for cod in MUNICIPIOS_AMOSTRA:
        st, cp = _get(f"{API}?pagina=1&funcao={FUNCAO_SAUDE}&codigoIBGE={cod}", chave)
        if st != 200:
            por_municipio[cod] = -1
            continue
        itens = json.loads(cp)
        por_municipio[cod] = len(itens)
        for it in itens:
            doc = ((it.get("convenente") or {}).get("cnpjFormatado") or "")
            so_digitos = "".join(c for c in doc if c.isdigit())
            if so_digitos:
                cnpjs.add(so_digitos)
    medida["convenios_por_municipio_amostra"] = por_municipio
    medida["cnpjs_distintos_na_amostra"] = len(cnpjs)
    return medida


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    env = carregar_env()
    chave = env.get(VARIAVEL, "").strip()

    ok_doc, nota_doc = documentacao_no_ar()
    relatorio: dict = {"openapi_ok": ok_doc, "openapi_nota": nota_doc,
                       "tem_chave": bool(chave)}
    impedimentos: list[str] = []

    if not ok_doc:
        impedimentos.append(
            f"a API oficial não está descrevendo convênios: {nota_doc}. É a única "
            "rota: o portal de download está atrás de AWS WAF com CAPTCHA, e "
            "resolver CAPTCHA não é caminho."
        )

    if not chave:
        impedimentos.append(
            f"falta a chave da API. Ela é gratuita e sai de um cadastro de e-mail "
            f"em {CADASTRO} — cadastro é ato de pessoa, não deste projeto. "
            f"Depois, gravar no .env como {VARIAVEL}=<chave>."
        )
    elif ok_doc:
        medida = medir_com_chave(chave)
        relatorio["medida"] = medida
        if medida.get("status_funcao_saude") != 200:
            impedimentos.append(
                f"a chave existe e a consulta de função {FUNCAO_SAUDE} (Saúde) "
                f"respondeu {medida.get('status_funcao_saude')}: "
                f"{medida.get('erro', '')[:160]}"
            )

    if args.json:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        print(f"[convenios] OpenAPI: {nota_doc}")
        print(f"[convenios] chave em {VARIAVEL}: {'sim' if chave else 'NÃO'}")
        for campo, valor in (relatorio.get("medida") or {}).items():
            print(f"[convenios] {campo}: {valor}")
        print()
        for i in impedimentos:
            print(f"❌ {i}\n")

    if impedimentos:
        print("Fonte NÃO apta para ingestão. Nada foi coletado.")
        return 1
    print("✅ Fonte apta: API respondendo e chave presente. "
          "O grão do mart continua sendo decisão — ver o cabeçalho deste arquivo "
          "sobre o CNPJ faltar em 92% dos estabelecimentos públicos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
