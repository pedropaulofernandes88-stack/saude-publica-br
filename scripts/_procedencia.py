"""
_procedencia.py — grava a procedência de um mart, e CONFERE que ela chegou
===========================================================================

    from _procedencia import gravar_procedencia

    gravar_procedencia(url, cabecalhos, [
        {"chave": "fonte_cnes", "valor": "API de dados abertos ..."},
    ])

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Doze pontos do projeto gravavam procedência assim:

    requests.post(f"{url}/rest/v1/meta_dataset", headers=h,
                  data=json.dumps(meta), timeout=60)

Sem `raise_for_status`, sem olhar `status_code`, sem atribuir o retorno a nada.
Conferir LEITURA virou reflexo neste repositório; conferir ESCRITA não tinha
virado. E um POST silencioso é indistinguível de sucesso.

O DEFEITO MEDIDO, E O MECANISMO
--------------------------------
Medido contra o banco em 2026-09-20: `fonte_cnes`, `fonte_leitos` e
`fonte_saude_suplementar` estavam no código e **não** em produção. Os pipelines
que as declaram terminavam com exit 0.

O mecanismo, reproduzido de propósito contra a tabela real:

    POST de chave nova ..................... 201
    POST com resolution=merge-duplicates ... 200
    POST de chave que JÁ EXISTE ............ 409  duplicate key value violates
                                                  unique constraint

Daí a forma do conserto. Só acrescentar `raise_for_status` deixaria o pipeline
QUEBRAR na segunda execução, porque regravar a mesma procedência é o caso
normal, não o excepcional. A escrita precisa ser as duas coisas ao mesmo tempo:

  * **idempotente**, com `resolution=merge-duplicates`, para que regravar seja
    barato e correto; e
  * **barulhenta**, conferindo o status, para que falhar seja visível.

Uma sem a outra troca um modo de falha por outro.

O QUE ESTA FUNÇÃO NÃO RESOLVE
------------------------------
Ela garante que o que foi ENVIADO chegou. Não garante que alguém envie: chave
que nenhum script declara continua invisível daqui. `fonte_agravo_hospital`
vive no banco sem origem em script nenhum, e só um confronto com o banco a
encontra — a guarda offline de `tests/test_metodologia_catalogo.py` cruza as
chaves que o MCP usa com as que os pipelines declaram, e pega o typo, não a
ausência. Ver a memória `escrita-sem-conferir-resposta`.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import requests

#: Endpoint único, para que mudar a tabela de metadados seja uma edição só.
TABELA = "meta_dataset"


def gravar_procedencia(url: str, cabecalhos: Mapping[str, str],
                       registros: Sequence[Mapping[str, Any]],
                       *, timeout: int = 60) -> int:
    """Grava os registros de procedência e devolve quantos foram gravados.

    Levanta `RuntimeError` se o PostgREST recusar. Regravar chave existente é
    caso normal e NÃO levanta: o `Prefer` embute `resolution=merge-duplicates`,
    que transforma a colisão de chave primária num update.
    """
    if not registros:
        return 0

    preferencia = cabecalhos.get("Prefer", "")
    if "resolution=" not in preferencia:
        partes = [p for p in (preferencia, "resolution=merge-duplicates") if p]
        preferencia = ",".join(partes)
    cab = {**cabecalhos, "Prefer": preferencia, "Content-Type": "application/json"}

    alvo = f"{url.rstrip('/')}/rest/v1/{TABELA}"
    r = requests.post(alvo, headers=cab, data=json.dumps(registros, ensure_ascii=False),
                      timeout=timeout)
    if r.status_code not in (200, 201, 204):
        chaves = ", ".join(str(reg.get("chave", "?")) for reg in registros)
        raise RuntimeError(
            f"procedência não gravada ({chaves}): HTTP {r.status_code} {r.text[:300]}"
        )
    return len(registros)
