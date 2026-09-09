"""
_sisagua.py — cliente da API do SISAGUA, com as guardas que a fonte exige
=========================================================================

Módulo de apoio de `pipeline_sisagua.py`. Fica separado porque as decisões aqui
nasceram de medição, não de leitura da documentação, e cada uma tem um custo se
for esquecida.

A DOCUMENTAÇÃO DA API ERRA EM DOIS PONTOS — MEDIDO EM 2026-09-06
-----------------------------------------------------------------
* `limit` está documentado como "menor ou igual a 100". Aceita **1000**, e
  acima disso trava em 1000 **em silêncio**, sem erro. Pedir 5000 e receber
  1000 sem aviso é como um coletor perde 80% de uma página achando que leu
  tudo.
* `offset` está documentado como "número da página". É deslocamento de
  **registro**: `offset=1` anda uma linha, não cem. Um coletor fiel à
  documentação leria 99% de linhas repetidas — e a contagem final bateria,
  que é exatamente o modo de falha que nenhuma guarda de contagem pega.

HTTP 502 É FREQUENTE, INTERMITENTE, E NÃO É FIM DE DADO
-------------------------------------------------------
Medido com 3 repetições por ponto:

    offset   500.000 -> [200, 200, 200]
    offset 1.000.000 -> [502, 502, 200]
    offset 1.500.000 -> [502, 502, 502]
    offset 3.000.000 -> [200, 200, 200]

Não é teto — 3.000.000 responde. E não acontece só em offset profundo: uma
consulta filtrada por UF e ano também devolveu 502. É instabilidade do proxy.

Daí as duas regras que este módulo existe para impor:

1. **502 se repete, nunca se interpreta.** Coletor que trate erro como fim de
   página trunca em silêncio; coletor que o trate como lista vazia publica
   recorte parcial com exit 0. Ver `coleta-ausencia-vs-falha` na memória do
   projeto e o caso do Maranhão 2023.
2. **Fatia que falhou ABORTA a coleta.** Não existe "pular a UF que deu erro e
   seguir": isso produz um mart que parece inteiro, com uma UF faltando, e
   nada acusa. Ausência de dado é `[]` depois de uma resposta 200 — e só isso.

POR QUE FATIAR POR UF × ANO
---------------------------
Duas razões, nesta ordem. A primeira é correção: fatias pequenas mantêm o
`offset` raso, e é no offset profundo que o 502 fica mais provável. A segunda é
retomada: 324 fatias (27 UFs × 12 anos) que podem ser refeitas uma a uma valem
mais que uma varredura de milhões de linhas que precisa recomeçar do zero.
"""
from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

BASE = "https://apidadosabertos.saude.gov.br/sisagua"

#: Teto real, medido. A documentação diz 100 e a API trava em 1000 sem avisar —
#: pedir mais devolveria 1000 e um coletor ingênuo acharia que a página acabou.
PAGINA = 1000

#: Tentativas por requisição. Eram oito, com espera até 30 s (~1,5 min por
#: requisição). Não bastou: em 2026-09-08 a coleta abortou na PRIMEIRA fatia
#: (AC/2020, offset 4000) com 502 nas oito. O proxy fica fora por minutos, não
#: por segundos. Doze tentativas com espera até 60 s dão ~6 min por requisição.
TENTATIVAS = 12
ESPERA_MAXIMA = 60

#: Onde ficam as fatias JÁ COLETADAS, para que retomar não recomece do zero.
#:
#: Só entra aqui fatia COMPLETA: `coletar_fatia` grava depois que a paginação
#: termina, e qualquer erro no meio levanta antes disso. O cache não afrouxa a
#: guarda — o mart continua exigindo TODAS as fatias, e continua não sendo
#: gravado se faltar uma. Ele só impede que um 502 na fatia 1 de 162 jogue fora
#: as outras 161 que já tinham vindo.
CACHE = Path(__file__).resolve().parents[1] / "data" / "raw" / "SISAGUA" / "fatias"


#: Quantas repeticoes cada endpoint custou nesta execucao. Contador de processo,
#: nao metrica persistida: serve para o relatorio final dizer se a lentidao veio
#: da fonte ou de outro lugar.
REPETICOES: Counter = Counter()


class FalhaDeColeta(RuntimeError):
    """A fonte não respondeu. NÃO é ausência de dado — é ausência de resposta."""


@dataclass
class Fatia:
    """O resultado de uma fatia, com a distinção que importa preservada.

    `municipio` preenchido = fatia por código IBGE, que é a estratégia que
    FUNCIONA. Ver `coletar_por_municipio`.
    """
    uf: str
    ano: int
    registros: list[dict]
    paginas: int
    #: `True` quando a fonte respondeu 200 e devolveu zero linhas. É um FATO
    #: sobre o recorte — aquele município não reportou —, não um erro.
    vazia_de_fato: bool
    #: Código IBGE, quando a fatia é por município (a estratégia que funciona).
    municipio: str | None = None
    #: Quantos registros a fatia tem, quando `registros` não os carrega.
    #: A coleta por município grava página a página em disco e devolve só a
    #: contagem — segurar 577 mil dicionários para contá-los seria o defeito
    #: que essa gravação existe para remover.
    n_registros: int | None = None

    def __len__(self) -> int:
        return self.n_registros if self.n_registros is not None else len(self.registros)


@dataclass
class Relatorio:
    """O que a coleta viu, para a guarda decidir depois — e para o log dizer."""
    fatias: list[Fatia] = field(default_factory=list)

    @property
    def registros(self) -> int:
        return sum(len(f) for f in self.fatias)

    @property
    def vazias(self) -> list[tuple[str, int]]:
        return [(f.municipio or f.uf, f.ano) for f in self.fatias if f.vazia_de_fato]


def _get(endpoint: str, params: dict[str, object]) -> list[dict]:
    """Uma requisição, com repetição. Esgotadas as tentativas, LEVANTA.

    Nunca devolve `[]` para disfarçar erro: `[]` aqui significa exclusivamente
    que a API respondeu 200 com lista vazia.
    """
    q = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE}/{endpoint}?{q}"
    ultimo: Exception | None = None
    for i in range(TENTATIVAS):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                corpo = json.load(r)
            if "parametros" not in corpo:
                # Contrato mudou. Silenciar isso com `.get(..., [])` faria a
                # coleta inteira sair vazia sem uma linha de erro.
                raise FalhaDeColeta(
                    f"resposta sem a chave 'parametros' (chaves: {list(corpo)}) em {url}")
            return corpo["parametros"]
        except urllib.error.HTTPError as e:
            # 4xx é pergunta malformada e não melhora com repetição; 5xx é o
            # proxy instável e melhora.
            if 400 <= e.code < 500:
                raise FalhaDeColeta(f"HTTP {e.code} em {url}") from e
            ultimo = e
        except FalhaDeColeta:
            raise
        except Exception as e:  # noqa: BLE001 — a causa vai na exceção final
            ultimo = e
        if i < TENTATIVAS - 1:
            espera = min(2 ** i, ESPERA_MAXIMA)
            # Repetição SILENCIOSA torna "está lento" indistinguível de "está
            # travado". Em 2026-09-08 um município pareceu levar três horas para
            # coletar 202 mil linhas, e passei uma investigação inteira medindo
            # a API, o tamanho do município e o crescimento do arquivo para
            # descobrir onde estava o custo. A causa era prosaica — a máquina
            # ficou desligada nesse intervalo —, mas o ponto se sustenta: eu não
            # tinha como distinguir isso de doze tentativas por página, porque o
            # log não registrava nenhuma. Uma linha aqui elimina a dúvida.
            REPETICOES[endpoint] += 1
            print(f"      [retry {i + 1}/{TENTATIVAS}] {type(ultimo).__name__} em "
                  f"offset={params.get('offset')}; esperando {espera}s", flush=True)
            time.sleep(espera)
    raise FalhaDeColeta(f"{TENTATIVAS} tentativas falharam em {url}: {ultimo}")


#: Marca da última linha de uma fatia em JSONL. Sua ausência denuncia arquivo
#: truncado mesmo que o gzip abra — é a checagem que o rename sozinho não faz.
MARCA_FIM = "__fatia_completa__"

#: Terminador de linha do JSONL. Constante porque o arquivo é aberto em modo
#: texto: escrever "\n" aqui viraria CRLF no Windows e o mesmo cache teria bytes
#: diferentes conforme o sistema que o gravou.
LINHA = "\n"


def _caminho_cache(endpoint: str, uf: str, ano: int) -> Path:
    """Formato ANTIGO: um JSON com a lista inteira. Ainda lido, não mais escrito."""
    return CACHE / endpoint.replace("/", "_") / f"{uf}_{ano}.json.gz"


def _caminho_jsonl(endpoint: str, chave: str, ano: int) -> Path:
    """Formato ATUAL: JSON Lines gzipado, uma linha por registro.

    A coleta por município grava PÁGINA A PÁGINA. O formato antigo obrigava a
    segurar a fatia inteira em memória para serializá-la de uma vez: um
    município da Bahia trouxe 577.191 linhas em 578 páginas, e o processo
    chegou a 574 MB montando um só município. São Paulo ainda viria.
    """
    return CACHE / endpoint.replace("/", "_") / f"{chave}_{ano}.jsonl.gz"


def _fim_valido(alvo: Path) -> dict | None:
    """Metadados da última linha, ou None se a fatia não terminou de gravar."""
    try:
        with gzip.open(alvo, "rt", encoding="utf-8", newline="") as fh:
            ultima = None
            for linha in fh:
                ultima = linha
    except (OSError, ValueError, EOFError):
        return None
    if not ultima:
        return None
    try:
        d = json.loads(ultima)
    except ValueError:
        return None
    return d.get(MARCA_FIM)


def registros_do_cache(endpoint: str, chave: str, ano: int = 0):
    """Itera os registros da fatia SEM carregar tudo na memória.

    É o que torna a agregação viável: o cache nacional passa de 40 milhões de
    linhas, e ler fatia a fatia, linha a linha, mantém o pico no tamanho de uma
    página. Levanta se a fatia não estiver completa — ler pela metade seria
    exatamente o recorte parcial com cara de inteiro.
    """
    alvo = _caminho_jsonl(endpoint, chave, ano)
    if alvo.exists():
        if _fim_valido(alvo) is None:
            raise FalhaDeColeta(f"fatia {chave} sem marca de fim — não terminou de gravar")
        with gzip.open(alvo, "rt", encoding="utf-8", newline="") as fh:
            for linha in fh:
                d = json.loads(linha)
                if MARCA_FIM in d:
                    return
                yield d
        return
    antigo = _caminho_cache(endpoint, chave, ano)
    if not antigo.exists():
        raise FalhaDeColeta(f"fatia {chave} não está em cache")
    with gzip.open(antigo, "rt", encoding="utf-8", newline="") as fh:
        yield from json.load(fh)["registros"]


def ler_cache(endpoint: str, uf: str, ano: int) -> Fatia | None:
    """A fatia já coletada, ou None. Cache ilegível é tratado como ausente.

    Lê os DOIS formatos: as 3.316 fatias gravadas antes de 2026-09-08 estão no
    JSON de lista, e reescrevê-las custaria uma recoleta inteira sem ganho.
    """
    novo = _caminho_jsonl(endpoint, uf, ano)
    if novo.exists():
        meta = _fim_valido(novo)
        if meta is None:
            return None
        return Fatia(uf=meta.get("uf", uf), ano=ano, registros=[],
                     paginas=meta["paginas"], vazia_de_fato=meta["vazia_de_fato"],
                     municipio=meta.get("municipio"), n_registros=meta["n_registros"])

    alvo = _caminho_cache(endpoint, uf, ano)
    if not alvo.exists():
        return None
    try:
        with gzip.open(alvo, "rt", encoding="utf-8", newline="") as fh:
            d = json.load(fh)
    except (OSError, ValueError, EOFError):
        # Arquivo truncado por interrupção: refazer é barato e correto.
        return None
    return Fatia(uf=uf, ano=ano, registros=d["registros"], paginas=d["paginas"],
                 vazia_de_fato=d["vazia_de_fato"], n_registros=len(d["registros"]))


def gravar_cache(endpoint: str, f: Fatia) -> None:
    # `municipio` ANTES de `uf`: gravar por UF fazia os 22 municípios do Acre
    # sobrescreverem o mesmo AC_0.json.gz. Cinquenta municípios coletados viraram
    # três arquivos, e a próxima execução leria o último como se fosse a fatia
    # de todos eles. Cache com chave errada é pior que cache nenhum: ele mente
    # com aparência de acerto.
    alvo = _caminho_cache(endpoint, f.municipio or f.uf, f.ano)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    # Grava em temporário e renomeia: interrupção no meio deixaria um .json.gz
    # pela metade que a próxima execução leria como fatia completa.
    tmp = alvo.with_suffix(".parcial")
    with gzip.open(tmp, "wt", encoding="utf-8", newline="") as fh:
        json.dump({"uf": f.uf, "ano": f.ano, "paginas": f.paginas,
                   "vazia_de_fato": f.vazia_de_fato, "registros": f.registros},
                  fh, ensure_ascii=False)
    tmp.replace(alvo)


def coletar_fatia(endpoint: str, uf: str, ano: int, campo_ano: str = "ano_de_referencia",
                  quieto: bool = False, usar_cache: bool = True) -> Fatia:
    """Todas as páginas de uma UF num ano.

    A paginação para quando uma página vem com menos de `PAGINA` linhas — e
    NÃO quando vem vazia, porque vazia já é menor que `PAGINA`. Parar por erro
    é impossível por construção: `_get` levanta.

    Fatia completa vai para o cache em disco. A gravação acontece DEPOIS do
    laço: fatia interrompida no meio levanta e nunca chega a ser gravada, então
    o cache nunca guarda recorte parcial.
    """
    if usar_cache:
        em_disco = ler_cache(endpoint, uf, ano)
        if em_disco is not None:
            if not quieto:
                marca = "vazia" if em_disco.vazia_de_fato else f"{len(em_disco.registros):,} linhas"
                print(f"   {uf} {ano}: {marca} (cache)", flush=True)
            return em_disco

    registros: list[dict] = []
    offset = 0
    paginas = 0
    while True:
        lote = _get(endpoint, {"uf": uf, campo_ano: ano,
                               "limit": PAGINA, "offset": offset})
        registros.extend(lote)
        paginas += 1
        if len(lote) < PAGINA:
            break
        offset += PAGINA
        if not quieto and paginas % 20 == 0:
            print(f"      {uf} {ano}: {len(registros):,} linhas…", flush=True)
    f = Fatia(uf=uf, ano=ano, registros=registros, paginas=paginas,
              vazia_de_fato=not registros)
    if usar_cache:
        gravar_cache(endpoint, f)
    return f


def coletar_fatia_municipio(endpoint: str, codigo: str, uf: str,
                            quieto: bool = False, usar_cache: bool = True) -> Fatia:
    """Todas as páginas de UM município, por `codigo_ibge`.

    POR QUE POR MUNICÍPIO, E NÃO POR UF × ANO
    ------------------------------------------
    Porque `uf` NÃO TEM ÍNDICE nesta API, e `codigo_ibge` tem. O docstring do
    `preflight` já registrava a medição desde 2026-09-06, e ninguém a aplicou
    ao coletor: ele continuou fatiando por `uf`, a forma medida como quebrada.
    Remedido em 2026-09-08, mesmo endpoint, `limit=1000`:

        sem filtro,            offset 0 ...... 200,  4,6 s
        uf=AC,                 offset 0 ...... 502, 60,2 s
        uf=AC + ano=2020,      offset 0 ...... 502, 60,2 s
        codigo_ibge=355030,    offset 0 ...... 200,  5,6 s
        codigo_ibge=355030,    offset 1000 ... 200, 15,7 s
        codigo_ibge=120040,    offset 0 ...... 200,  1,5 s

    Não foi instabilidade passageira do proxy: as duas coletas que abortaram
    (2026-09-08, madrugada) morreram na PRIMEIRA fatia, e o preflight passava
    logo antes — porque o preflight testa `codigo_ibge` e a coleta usava `uf`.
    Portão e coleta exercitavam caminhos diferentes, e o portão dizia "OK" sobre
    algo que a coleta não fazia.

    Fatiar por município ainda mantém o `offset` raso, que é a outra razão de o
    502 aparecer: o custo do offset cresce com a profundidade.
    """
    if usar_cache:
        em_disco = ler_cache(endpoint, codigo, 0)
        if em_disco is not None:
            return em_disco

    # PÁGINA A PÁGINA, direto para o disco. Nenhum ponto do laço segura mais que
    # uma página: a fatia maior já vista tem 577.191 linhas em 578 páginas, e
    # montá-la em memória levou o processo a 574 MB por UM município — com São
    # Paulo ainda por vir. O `acumular=False` protegia ENTRE municípios e não
    # dentro de um; a memória estava resolvida no nível errado.
    alvo = _caminho_jsonl(endpoint, codigo, 0)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    # `.parcial` + rename: fatia interrompida no meio nunca ganha o nome final,
    # então a próxima execução a vê como ausente e a refaz — que é o correto.
    tmp = alvo.with_suffix(".parcial")
    offset = paginas = total = 0
    try:
        with gzip.open(tmp, "wt", encoding="utf-8", newline="") as fh:
            while True:
                lote = _get(endpoint, {"codigo_ibge": codigo,
                                       "limit": PAGINA, "offset": offset})
                for r in lote:
                    fh.write(json.dumps(r, ensure_ascii=False) + LINHA)
                paginas += 1
                total += len(lote)
                if len(lote) < PAGINA:
                    break
                offset += PAGINA
            fh.write(json.dumps({MARCA_FIM: {
                "uf": uf, "municipio": codigo, "paginas": paginas,
                "n_registros": total, "vazia_de_fato": not total,
            }}, ensure_ascii=False) + LINHA)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(alvo)
    return Fatia(uf=uf, ano=0, registros=[], paginas=paginas,
                 vazia_de_fato=not total, municipio=codigo, n_registros=total)


def preflight(endpoint: str) -> None:
    """Recusa iniciar se a fonte não conseguir entregar a SEGUNDA página.

    POR QUE ISTO É A GUARDA MAIS IMPORTANTE DO MÓDULO
    --------------------------------------------------
    Uma primeira página cheia — 1000 linhas — é indistinguível de uma coleta
    completa. Se a página 2 falhar, um coletor sem esta checagem entrega um
    mart que parece íntegro e no qual faltam justamente os MAIORES municípios,
    porque são exatamente eles que passam de 1000 linhas. O erro seria
    silencioso, sistemático e enviesado para as capitais.

    MORA AQUI, E NÃO NO PIPELINE, POR UM DEFEITO CONCRETO
    ------------------------------------------------------
    Enquanto vivia em `pipeline_sisagua.py`, este portão testava `codigo_ibge`
    e a coleta logo abaixo fatiava por `uf` — duas consultas diferentes. Ele
    aprovava, e a coleta morria na primeira fatia (2026-09-08, duas vezes). Um
    portão só vale sobre o caminho que ele de fato exercita, então ele passou a
    ser chamado de dentro de `coletar_por_municipio`, que hoje usa exatamente
    a consulta por `codigo_ibge` que o portão mede.
    """
    print("[sisagua] preflight: a fonte entrega a segunda página?", flush=True)
    # São Paulo capital tem mais de 1000 linhas — é o caso em que a segunda
    # página é obrigatória, e por isso o teste certo.
    alvo = {"codigo_ibge": "355030", "limit": PAGINA}
    try:
        p1 = _get(endpoint, {**alvo, "offset": 0})
    except FalhaDeColeta as e:
        raise FalhaDeColeta(f"preflight: nem a PRIMEIRA página respondeu — {e}") from e

    if len(p1) < PAGINA:
        print(f"[sisagua] preflight: município de teste cabe numa página ({len(p1)} linhas); "
              "não dá para testar a segunda por aqui — seguindo.", flush=True)
        return

    try:
        _get(endpoint, {**alvo, "offset": PAGINA})
    except FalhaDeColeta as e:
        raise FalhaDeColeta(
            "preflight REPROVOU: a primeira página veio cheia e a SEGUNDA não "
            f"respondeu — {e}. Coletar assim truncaria em silêncio exatamente os "
            "maiores municípios, e um mart truncado desse jeito é indistinguível "
            "de um completo.") from e
    print("[sisagua] preflight: OK, a segunda página respondeu.", flush=True)


def coletar_por_municipio(endpoint: str, municipios: list[tuple[str, str]],
                          quieto: bool = False, acumular: bool = True) -> Relatorio:
    """Percorre municípios (código, UF). Qualquer fatia que falhe interrompe TUDO.

    Mesma regra de sempre — fatia que falha não pode virar mart incompleto —,
    mas agora com cache por fatia: retomar não recomeça do zero.

    `acumular=False` mantém os CONTADORES de cada fatia e descarta os registros
    da memória depois de gravá-los em disco. É o modo de aquecer o cache: a
    coleta nacional passa de 18 milhões de linhas, e segurar tudo em dicionário
    Python custaria alguns GB de RAM sem necessidade — a agregação lê de volta,
    fatia a fatia, quando for a hora.
    """
    preflight(endpoint)
    rel = Relatorio()
    total = len(municipios)
    for i, (codigo, uf) in enumerate(municipios, 1):
        f = coletar_fatia_municipio(endpoint, codigo, uf, quieto=quieto)
        lidos = len(f)
        rel.fatias.append(f)
        if not quieto and (i % 50 == 0 or i == total):
            marca = f"{rel.registros:,} linhas" if acumular else f"último: {lidos:,} linhas"
            print(f"   {i}/{total} municípios · {marca}", flush=True)
    return rel


def municipios_em_cache(endpoint: str) -> set[str]:
    """Códigos já coletados por inteiro, nos DOIS formatos.

    Enxergar só o formato antigo faria a retomada recoletar tudo que já viera
    no novo — e como o nome final só existe depois do rename, "está no disco"
    e "está completo" continuam sendo a mesma coisa. O `.parcial` não casa com
    nenhum dos dois padrões, então fatia interrompida segue contando como
    ausente, que é o correto.
    """
    dir_ = CACHE / endpoint.replace("/", "_")
    if not dir_.exists():
        return set()
    return ({p.name.split("_")[0] for p in dir_.glob("*_0.json.gz")}
            | {p.name.split("_")[0] for p in dir_.glob("*_0.jsonl.gz")})


#: A varredura por UF x ano foi REMOVIDA, não esquecida. A API não indexa `uf`,
#: e as medições em `coletar_fatia_municipio` mostram 502 em toda tentativa com
#: esse filtro. Manter a função convidaria a chamá-la; a coleta que funciona é
#: `coletar_por_municipio`.
