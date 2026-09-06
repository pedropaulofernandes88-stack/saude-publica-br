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

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

BASE = "https://apidadosabertos.saude.gov.br/sisagua"

#: Teto real, medido. A documentação diz 100 e a API trava em 1000 sem avisar —
#: pedir mais devolveria 1000 e um coletor ingênuo acharia que a página acabou.
PAGINA = 1000

#: Tentativas por requisição. Oito porque o 502 chega a repetir três vezes
#: seguidas no mesmo ponto; a espera cresce até 30 s.
TENTATIVAS = 8


class FalhaDeColeta(RuntimeError):
    """A fonte não respondeu. NÃO é ausência de dado — é ausência de resposta."""


@dataclass
class Fatia:
    """O resultado de uma fatia UF × ano, com a distinção que importa preservada."""
    uf: str
    ano: int
    registros: list[dict]
    paginas: int
    #: `True` quando a fonte respondeu 200 e devolveu zero linhas. É um FATO
    #: sobre o recorte — aquela UF não reportou naquele ano —, não um erro.
    vazia_de_fato: bool


@dataclass
class Relatorio:
    """O que a coleta viu, para a guarda decidir depois — e para o log dizer."""
    fatias: list[Fatia] = field(default_factory=list)

    @property
    def registros(self) -> int:
        return sum(len(f.registros) for f in self.fatias)

    @property
    def vazias(self) -> list[tuple[str, int]]:
        return [(f.uf, f.ano) for f in self.fatias if f.vazia_de_fato]


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
            time.sleep(min(2 ** i, 30))
    raise FalhaDeColeta(f"{TENTATIVAS} tentativas falharam em {url}: {ultimo}")


def coletar_fatia(endpoint: str, uf: str, ano: int, campo_ano: str = "ano_de_referencia",
                  quieto: bool = False) -> Fatia:
    """Todas as páginas de uma UF num ano.

    A paginação para quando uma página vem com menos de `PAGINA` linhas — e
    NÃO quando vem vazia, porque vazia já é menor que `PAGINA`. Parar por erro
    é impossível por construção: `_get` levanta.
    """
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
    return Fatia(uf=uf, ano=ano, registros=registros, paginas=paginas,
                 vazia_de_fato=not registros)


def coletar(endpoint: str, ufs: list[str], anos: list[int],
            campo_ano: str = "ano_de_referencia", quieto: bool = False) -> Relatorio:
    """Percorre UF × ano. Qualquer fatia que falhe interrompe TUDO.

    Deliberadamente sem `try/except` em volta da fatia: capturar aqui e seguir
    produziria um mart a que falta uma UF inteira, com aparência de completo.
    Quem quiser retomar refaz o recorte — as fatias são independentes.
    """
    rel = Relatorio()
    for ano in anos:
        for uf in ufs:
            f = coletar_fatia(endpoint, uf, ano, campo_ano=campo_ano, quieto=quieto)
            rel.fatias.append(f)
            if not quieto:
                marca = "vazia" if f.vazia_de_fato else f"{len(f.registros):,} linhas"
                print(f"   {uf} {ano}: {marca}", flush=True)
    return rel
