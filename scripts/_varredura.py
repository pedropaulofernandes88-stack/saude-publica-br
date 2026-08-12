"""
_varredura.py — remove do Supabase as linhas que sairam do calculo.

O PROBLEMA. Os pipelines publicam com POST + `resolution=merge-duplicates`, ou
seja, upsert. Upsert atualiza o que existe e insere o que e novo -- mas nunca
remove o que DEIXOU de existir. Uma linha que sai do recorte (o par hospital x
CID que caiu abaixo do minimo de internacoes, o municipio que zerou, o agravo
que sumiu) fica publicada para sempre, com os valores da ultima vez em que foi
calculada.

Isso e silencioso: a linha orfa parece valida. Em 12/08/2026 foram encontradas
1.830 delas (1.829 em mart_los_hospital, 1 em mart_internacoes_agravo) so
porque uma anulacao temporaria de colunas as deixou visiveis -- sem esse
acidente, seguiriam la.

A ESTRATEGIA. Nao e apagar o escopo antes de inserir: se o upload falhar no
meio, o periodo fica faltando na API publica. Aqui a ordem e a inversa e mais
segura -- primeiro o upsert (feito pelo chamador), depois a varredura:

  1. baixa apenas as COLUNAS-CHAVE das linhas do escopo (barato: 3 colunas
     curtas, mesmo em centenas de milhares de linhas);
  2. compara com as chaves do DataFrame recem-publicado;
  3. apaga so a diferenca, que na pratica e punhado.

Em nenhum momento a tabela fica sem os dados bons.

Uso:
    from _varredura import varrer_orfaos
    varrer_orfaos(url, key, "mart_los_hospital", los,
                  chaves=["cnes", "cid3", "ano"], escopo={"ano": f"eq.{ano}"})
"""
from __future__ import annotations

import sys
from typing import Iterable

import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PAGINA = 1000
LOTE_DELETE = 200


def _chaves_publicadas(url: str, key: str, tabela: str, chaves: list[str],
                       escopo: dict[str, str] | None) -> pd.DataFrame:
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    params = {"select": ",".join(chaves), **(escopo or {})}
    linhas: list[dict] = []
    offset = 0
    while True:
        r = requests.get(f"{url}/rest/v1/{tabela}", timeout=120,
                         headers={**h, "Range-Unit": "items",
                                  "Range": f"{offset}-{offset + PAGINA - 1}"},
                         params=params)
        r.raise_for_status()
        bloco = r.json()
        linhas.extend(bloco)
        if len(bloco) < PAGINA:
            break
        offset += PAGINA
    return pd.DataFrame(linhas, columns=chaves)


def _filtro_or(chaves: list[str], registros: Iterable[dict]) -> str:
    """Monta o `or=(and(...),and(...))` do PostgREST para apagar N chaves compostas."""
    partes = []
    for r in registros:
        cond = ",".join(f"{c}.eq.{r[c]}" for c in chaves)
        partes.append(f"and({cond})")
    return "(" + ",".join(partes) + ")"


#: Acima disso a varredura recusa apagar. Um conjunto de chaves errado faz TODAS
#: as linhas parecerem orfas -- a trava troca "tabela limpa em silencio" por
#: "pipeline para e reclama". Orfas de verdade sao punhado: as 1.829 do
#: mart_los_hospital eram 0,7% da tabela.
LIMITE_ORFAS = 0.20


def calcular_orfas(publicadas: pd.DataFrame, novas: pd.DataFrame,
                   chaves: list[str]) -> pd.DataFrame:
    """Chaves presentes em `publicadas` e ausentes em `novas`. Funcao pura."""
    if publicadas.empty:
        return publicadas
    pub = publicadas[chaves].astype(str)
    nov = novas[chaves].astype(str).drop_duplicates()
    juncao = pub.merge(nov, on=chaves, how="left", indicator=True)
    return juncao[juncao["_merge"] == "left_only"][chaves].reset_index(drop=True)


def varrer_orfaos(url: str, key: str, tabela: str, df: pd.DataFrame,
                  chaves: list[str], escopo: dict[str, str] | None = None) -> int:
    """Apaga do `tabela` as linhas do `escopo` cujas chaves nao estao em `df`.

    Chamar DEPOIS do upsert. Devolve quantas linhas foram removidas.
    """
    url = url.rstrip("/")
    faltando = [c for c in chaves if c not in df.columns]
    if faltando:
        raise ValueError(f"{tabela}: colunas-chave ausentes no DataFrame: {faltando}")

    publicadas = _chaves_publicadas(url, key, tabela, chaves, escopo)
    if publicadas.empty:
        return 0

    orfas = calcular_orfas(publicadas, df, chaves)
    if orfas.empty:
        print(f"[varredura] {tabela}: nenhuma linha orfa", flush=True)
        return 0

    fracao = len(orfas) / len(publicadas)
    if fracao > LIMITE_ORFAS:
        raise RuntimeError(
            f"{tabela}: varredura abortada — {len(orfas):,} de {len(publicadas):,} linhas "
            f"({fracao:.1%}) apareceram como orfas, acima do limite de {LIMITE_ORFAS:.0%}. "
            f"Quase sempre isso significa conjunto de chaves errado ({chaves}) e nao dado "
            f"que sumiu. Nada foi apagado."
        )

    h = {"apikey": key, "Authorization": f"Bearer {key}", "Prefer": "return=minimal"}
    registros = orfas.to_dict("records")
    for i in range(0, len(registros), LOTE_DELETE):
        lote = registros[i:i + LOTE_DELETE]
        r = requests.delete(f"{url}/rest/v1/{tabela}", headers=h, timeout=120,
                            params={"or": _filtro_or(chaves, lote)})
        if r.status_code not in (200, 204):
            raise RuntimeError(f"{tabela}: DELETE HTTP {r.status_code} {r.text[:200]}")
    print(f"[varredura] {tabela}: {len(registros):,} linhas orfas removidas", flush=True)
    return len(registros)


__all__ = ["varrer_orfaos"]
