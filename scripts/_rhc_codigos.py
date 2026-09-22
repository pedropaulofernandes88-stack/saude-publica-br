"""Códigos do RHC: os mapas, e por que eles são declarados e não deduzidos.

O INCA embarca os dicionários DENTRO do próprio zip anual (`r_racacor.cnv`,
`r_ginstruc.cnv`, `r_pritrathosp.cnv`, …). Isso é raro e é bom, mas ler `.cnv`
em tempo de coleta trocaria um problema por outro: o formato é posicional,
tem dialeto próprio, e um erro de leitura viraria rótulo errado em silêncio.

A escolha aqui é a mesma que o projeto já fez para a chave natural da view:
**declarar e verificar**, não declarar só. Os mapas estão escritos abaixo, e
`tests/test_rhc_codigos.py` abre o zip real, lê o `.cnv` e exige que bata. Se o
INCA mudar um código, o teste reprova — e reprova dizendo qual.

A ARMADILHA DO ÍNDICE
---------------------
O `.cnv` tem DUAS colunas numéricas: a ordem da linha e o código real. Elas
**não coincidem**:

    6  1
          1  Branca          1
          ...
          6  Sem Informacao  9      <-- linha 6, código 9

Ler pela ordem daria `6 → "Sem Informacao"` e perderia o 9. Em raça/cor isso
apagaria 46.780 registros de 2019 (9,0%) e inventaria uma categoria que não
existe. Os mapas abaixo são por CÓDIGO.

O CÓDIGO QUE NÃO ESTÁ NO DICIONÁRIO
-----------------------------------
`SEXO` e `INSTRUC` trazem `0` no dado de 2019 — dois registros cada, e `0` não
existe em nenhum dos dois `.cnv`. Não é erro de leitura: é código fora do
dicionário da própria fonte. Cai em `"ignorado"`, como qualquer outro
desconhecido, e a COBERTURA conta quantos caíram — ausência que não é contada
é ausência que vira zero.

"NENHUM" NÃO É "SEM INFORMAÇÃO"
------------------------------
Em `PRITRATH`, o código 1 é **"Nenhum"** — o paciente não recebeu tratamento no
hospital — e o 9 é "Sem informação". São 83.956 e poucos milhares em 2019, e
confundi-los apaga justamente quem o estudo de acesso precisa contar. Ficam em
rótulos distintos, e nenhum dos dois é nulo.
"""
from __future__ import annotations

IGNORADO = "ignorado"

SEXO = {"1": "masculino", "2": "feminino"}

RACA_COR = {
    "1": "branca",
    "2": "preta",
    "3": "amarela",
    "4": "parda",
    "5": "indigena",
    "9": IGNORADO,
}

ESCOLARIDADE = {
    "1": "nenhuma",
    "2": "fundamental_incompleto",
    "3": "fundamental_completo",
    "4": "medio",
    "5": "superior_incompleto",
    "6": "superior_completo",
    "9": IGNORADO,
}

ESTADO_FIM_TRATAMENTO = {
    "1": "sem_evidencia_da_doenca",
    "2": "remissao_parcial",
    "3": "doenca_estavel",
    "4": "doenca_em_progressao",
    "5": "fora_de_possibilidade_terapeutica",
    "6": "obito",
    "8": "nao_se_aplica",
    "9": IGNORADO,
}

RAZAO_NAO_TRATAMENTO = {
    "1": "recusa_do_tratamento",
    "2": "tratamento_realizado_fora",
    "3": "doenca_avancada_ou_sem_condicao_clinica",
    "4": "abandono_do_tratamento",
    "5": "complicacoes_do_tratamento",
    "6": "obito",
    "7": "outras",
    "8": "nao_se_aplica",
    "9": IGNORADO,
}

# `PRITRATH` é código de SEQUÊNCIA: cada dígito é uma modalidade, e a ordem em
# que aparecem é a ordem em que foram dadas. O INCA agrupa as permutações — 23
# e 32 são ambos "Cirurgia + Radioterapia" — e o `.cnv` lista explicitamente
# quais permutações caem em qual rótulo.
#
# A lista NÃO é simétrica, e isso é do INCA, não meu: "RXT + RXT + QT" recebe
# só o 334, enquanto 343 e 433 não constam em lugar nenhum e caem em
# desconhecido. Reproduzo como está — corrigir a fonte aqui seria inventar
# dado, e o teste compara contra o `.cnv` justamente para essa assimetria não
# ser "consertada" por engano numa revisão futura.
PRIMEIRO_TRATAMENTO = {
    "1": "nenhum",
    "2": "cirurgia",
    "3": "radioterapia",
    "4": "quimioterapia",
    "5": "hormonioterapia",
    "6": "transplante_de_medula",
    "22": "cirurgia+cirurgia",
    "23": "cirurgia+radioterapia", "32": "cirurgia+radioterapia",
    "24": "cirurgia+quimioterapia", "42": "cirurgia+quimioterapia",
    "25": "cirurgia+hormonioterapia", "52": "cirurgia+hormonioterapia",
    "33": "radioterapia+radioterapia",
    "34": "radioterapia+quimioterapia", "43": "radioterapia+quimioterapia",
    "44": "quimioterapia+quimioterapia",
    "46": "quimioterapia+transplante", "64": "quimioterapia+transplante",
    "55": "hormonioterapia+hormonioterapia",
    "222": "cirurgia+cirurgia+cirurgia",
    "333": "radioterapia+radioterapia+radioterapia",
    "334": "radioterapia+radioterapia+quimioterapia",
    "444": "quimioterapia+quimioterapia+quimioterapia",
    "555": "hormonioterapia+hormonioterapia+hormonioterapia",
    "0": "outros_procedimentos", "-9": "outros_procedimentos",
    "8": "outros_procedimentos",
    "9": IGNORADO,
}
for _c in ("234", "243", "324", "342", "432", "423"):
    PRIMEIRO_TRATAMENTO[_c] = "cirurgia+radioterapia+quimioterapia"
for _c in ("245", "254", "425", "452", "542", "524"):
    PRIMEIRO_TRATAMENTO[_c] = "cirurgia+quimioterapia+hormonioterapia"
for _c in ("253", "235", "523", "532", "352", "325"):
    PRIMEIRO_TRATAMENTO[_c] = "cirurgia+hormonioterapia+radioterapia"
for _c in ("2345", "2354", "2435", "2453", "2534", "2543",
           "3245", "3254", "3425", "3452", "3524", "3542",
           "4235", "4253", "4325", "4352", "4523", "4532",
           "5234", "5243", "5324", "5342", "5423", "5432"):
    PRIMEIRO_TRATAMENTO[_c] = "cirurgia+quimioterapia+hormonioterapia+radioterapia"
del _c

#: A máscara de data vazia do RHC. `.strip()` a deixa NÃO vazia, então um
#: `if valor:` a trata como preenchida — foi assim que `DATAOBITO` mediu 99,6%
#: de preenchimento quando o real é 15,9%. Mesma família do `********` que já
#: quebrou o leitor da sífilis neste projeto.
MASCARA_DATA_VAZIA = frozenset({"/  /", "//", ""})


def decodificar(mapa: dict[str, str], valor: str) -> str:
    """Rótulo do código, ou `"ignorado"` — nunca `None`, nunca o código cru.

    Devolver o código cru "quando não conhece" é o que faz aparecer um
    `estadiamento = '88'` numa figura. Desconhecido tem nome, e é o mesmo nome
    do declarado-desconhecido de propósito: quem precisa separar os dois olha a
    cobertura, que conta os dois em colunas diferentes.
    """
    return mapa.get(valor.strip(), IGNORADO)


def faixa_etaria(valor: str) -> str:
    """Faixa de 5 anos, no corte do `r_fxeta5.cnv` do próprio INCA.

    `999` é "sem informação" no dicionário. Qualquer coisa que não seja inteiro
    também cai em ignorada — inclusive vazio, que não é o mesmo que zero anos.
    """
    try:
        i = int(valor)
    except (ValueError, TypeError):
        return "ignorada"
    if i < 0 or i >= 999:
        return "ignorada"
    if i >= 85:
        return "85+"
    base = (i // 5) * 5
    return f"{base:02d}-{base + 4:02d}"


def tem_data(valor: str) -> bool:
    """A data existe de verdade, e não é a máscara vazia nem `99/99/9999`."""
    v = valor.strip()
    return bool(v) and v not in MASCARA_DATA_VAZIA and not v.startswith("99")
