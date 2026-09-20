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

O QUE ESTE PORTÃO AINDA NÃO SABE
---------------------------------
Sem chave, não dá para medir o que só a resposta real responde, e que decide o
custo do coletor:

  * quantos convênios de função 10 existem, e em que período;
  * quantos registros vêm por página (a API do CNES, por exemplo, ignora `limit`
    e devolve 20 — ver a sondagem do SRAG para o mesmo tipo de armadilha);
  * a TAXA REAL DE CASAMENTO entre `convenente.cnpjFormatado` e o CNPJ do CNES,
    que é o número que decide se o grão por estabelecimento vale a pena.

Estas três medições estão implementadas abaixo e rodam assim que a chave existir.
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

#: Municípios de portes e regiões diferentes, para a amostra do casamento de
#: CNPJ não medir só capital. Os mesmos usados na medição do lado do CNES.
MUNICIPIOS_AMOSTRA = ["355030", "330455", "292740", "150140", "431490",
                      "520870", "172100", "230440", "261160", "410690"]

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
    """O que só a resposta real responde. Roda quando a chave existe."""
    medida: dict = {}
    status, corpo = _get(f"{API}?pagina=1&funcao={FUNCAO_SAUDE}", chave)
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
