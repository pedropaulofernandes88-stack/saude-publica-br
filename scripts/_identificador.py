"""
_identificador.py — o identificador de pessoa é chave opaca, e nunca sai daqui
==============================================================================

POR QUE ESTE MÓDULO EXISTE
--------------------------
Em 2026-09-21 o projeto ligou 42.860.027 APACs de quimioterapia em 2.348.571
pessoas usando `AP_CNSPCN`, o Cartão Nacional de Saúde que vem em todo registro
do SIA/SUS. Isso abriu uma classe inteira de pergunta que o dado agregado não
responde — trajetória, primeira ocorrência, quem começa e não continua.

E abriu, junto, o único risco deste projeto cujo dano não se desfaz.

**O campo não é criptografado. É ofuscado.** Os valores têm 15 bytes, todos na
faixa `0x7B`–`0x84` — exatamente dez valores distintos, que é a assinatura de
dígito deslocado por constante. O CNS real é recuperável por subtração, e o
arquivo é público no FTP do DataSUS. Não existe barreira técnica; existe uma
decisão, e ela precisa estar escrita e vigiada, não lembrada.

A DOUTRINA, EM QUATRO REGRAS
----------------------------
1. **Usar sempre a forma como vem.** O valor ofuscado serve como chave opaca
   para qualquer junção. Recuperar o número real seria reidentificar pessoas
   sem necessidade analítica nenhuma.
2. **Nunca decodificar.** Não há caso de uso neste projeto que exija o CNS real.
   Se algum dia houver, ele começa por uma discussão ética, não por um commit.
3. **Nunca publicar** — nem ofuscado, nem derivado, nem em amostra — em mart,
   tabela servida, figura, anexo ou rascunho. O repositório guarda o método e os
   agregados, não a chave de pessoa.
4. **Nunca versionar o intermediário.** O arquivo por pessoa que a ligação
   produz vive em pasta temporária de sessão e morre lá.

POR QUE A GUARDA CONFERE FORMA, E NÃO NOME
------------------------------------------
Uma lista de nomes proibidos (`ap_cnspcn`, `cns`, ...) protege contra descuido e
contra nada mais: basta renomear a coluna para `chave`, `id_pac` ou `paciente`
e a guarda aprova. Este projeto já pagou por esse erro em outro lugar — a
projeção populacional de 2018 era suave, tinha a forma certa, e passou em toda
verificação de formato porque nenhuma delas conferia procedência.

Aqui é o contrário, e de propósito: **o detector principal olha os valores.**
Quinze caracteres, todos na faixa da ofuscação, é uma assinatura que nenhum dado
legítimo de saúde pública produz por acaso. Renomear a coluna não ajuda; só não
colocá-la no arquivo ajuda.

O detector do nome fica, mas como segunda linha — ele pega o caso em que a
coluna está vazia ou truncada e a forma já não denuncia.

ONDE ELA FECHA
--------------
`escrever_parquet` é o caminho por onde todo mart do projeto nasce. A guarda
mora ali, no ponto mais cedo possível: um arquivo com identificador nunca chega
a existir no disco. `publicar.py` a chama de novo antes de enviar ao Storage,
porque tabela em `postgres-bootstrap` não passa por `escrever_parquet`.
"""
from __future__ import annotations

import pandas as pd

#: Faixa de bytes do CNS ofuscado do DataSUS, medida em 2026-09-21 sobre o
#: SIA/SUS: 15 caracteres, todos entre `{` (0x7B) e 0x84. São dez valores
#: distintos porque a ofuscação desloca cada DÍGITO por uma constante.
FAIXA_OFUSCADA = frozenset(chr(c) for c in range(0x7B, 0x85))

#: Comprimento do CNS, ofuscado ou não.
COMPRIMENTO_CNS = 15

#: Primeiro dígito válido de um CNS real (definitivo 1/2, provisório 7/8/9).
#: Só é usado pelo detector do valor DECODIFICADO, que é a segunda linha.
INICIAIS_CNS = frozenset("12789")

#: Nomes que denunciam a intenção mesmo quando a coluna está vazia. Segunda
#: linha: renomear a coluna derrota esta lista e não derrota o detector de
#: forma, que é o principal.
NOMES_PROIBIDOS = frozenset({
    "ap_cnspcn", "cnspcn", "cns", "cns_paciente", "cns_pac", "num_cns",
    "numero_cns", "cartao_sus", "cartaosus", "ns_pac",
})

#: Fração da coluna que precisa casar com a assinatura para o aborto. Não é 1,0
#: porque valor ausente e registro truncado existem; não é baixa porque uma
#: coluna legítima não encosta nisto.
LIMIAR = 0.5

#: Amostra por coluna. Varrer 40 milhões de linhas para responder "esta coluna é
#: identificador?" custa mais que o dano que evita, e a assinatura é densa: se
#: metade da coluna casa, ela casa nas primeiras milhares de linhas também.
AMOSTRA = 20_000


class IdentificadorVazado(RuntimeError):
    """Um identificador de pessoa alcançou um artefato que sai do projeto."""


def _fracao_ofuscada(valores: pd.Series) -> float:
    """Fração dos valores que têm a assinatura do CNS ofuscado."""
    def casa(v) -> bool:
        return (isinstance(v, str) and len(v) == COMPRIMENTO_CNS
                and set(v) <= FAIXA_OFUSCADA)
    return float(valores.map(casa).mean()) if len(valores) else 0.0


def _fracao_decodificada(valores: pd.Series) -> float:
    """Fração dos valores que parecem CNS em claro — 15 dígitos, início válido.

    Segunda linha, e conservadora de propósito: existe dado público de 15
    dígitos que não é CNS. O que torna este detector aceitável é a exigência do
    dígito inicial, que corta a maior parte dos códigos sequenciais.
    """
    def casa(v) -> bool:
        return (isinstance(v, str) and len(v) == COMPRIMENTO_CNS
                and v.isdigit() and v[0] in INICIAIS_CNS)
    return float(valores.map(casa).mean()) if len(valores) else 0.0


def conferir_sem_identificador(df: pd.DataFrame, contexto: str) -> None:
    """Recusa um DataFrame que carregue identificador de pessoa.

    Chamada de `escrever_parquet`, ou seja: de todo mart que o projeto produz.
    Levanta `IdentificadorVazado`, que ninguém captura — o objetivo é abortar a
    publicação, não registrar um aviso.
    """
    culpados: list[str] = []

    for coluna in df.columns:
        nome = str(coluna).strip().lower()
        serie = df[coluna]

        if nome in NOMES_PROIBIDOS:
            culpados.append(f"{coluna!r} (nome reservado a identificador)")
            continue

        # Só coluna de texto pode carregar a assinatura; numérica não guarda
        # 0x7B–0x84, e converter tudo para str para conferir custaria caro.
        if serie.dtype != object:
            continue

        amostra = serie.dropna().head(AMOSTRA)
        if not len(amostra):
            continue

        if (f := _fracao_ofuscada(amostra)) >= LIMIAR:
            culpados.append(
                f"{coluna!r} ({100 * f:.0f}% dos valores com a assinatura do "
                f"CNS ofuscado: {COMPRIMENTO_CNS} caracteres em 0x7B–0x84)")
        elif (f := _fracao_decodificada(amostra)) >= LIMIAR:
            culpados.append(
                f"{coluna!r} ({100 * f:.0f}% dos valores com a forma de CNS em "
                f"claro: {COMPRIMENTO_CNS} dígitos começando em 1/2/7/8/9) — "
                "e CNS em claro é pior que ofuscado, não melhor")

    if culpados:
        raise IdentificadorVazado(
            f"{contexto}: identificador de pessoa no artefato — "
            + "; ".join(culpados)
            + ". O identificador é chave opaca de junção e NÃO sai do projeto: "
              "nem em mart, nem em tabela servida, nem em figura. Agregue por "
              "pessoa e publique o agregado, não a chave. Ver _identificador.py."
        )
