"""
pipeline_rhc.py — Registro Hospitalar de Câncer: a 16ª fonte, e a primeira por
PESSOA
==============================================================================

    python scripts/pipeline_rhc.py                 # 2013–2023
    python scripts/pipeline_rhc.py --anos 2019 2020

POR QUE ESTA FONTE ENTRA
------------------------
Todas as fontes oncológicas do projeto contam evento: a APAC conta
AUTORIZAÇÃO, o Painel conta caso mas deriva do próprio SIA. O RHC conta
**pessoa, com confirmação histopatológica**, e traz três coisas que nenhuma das
outras traz: escolaridade, raça/cor declarada no registro hospitalar, e o
**primeiro tratamento de qualquer modalidade** — que é o que a Lei 12.732/2012
efetivamente conta, e que a APAC de quimioterapia não consegue observar.

A sondagem que decidiu isto está em `scripts/sondar_rhc.py`, com as quatro
armadilhas medidas. Este pipeline as respeita, e o portão de lá é o que avisa
se alguma mudar.

O QUE ESTE PIPELINE PUBLICA
---------------------------
`mart_rhc_caso`      município de RESIDÊNCIA × ano da primeira consulta × CID-3
                     × estadiamento × tipo de caso → casos e prazo
`mart_rhc_perfil`    UF do HOSPITAL × ano × CID-3 × sexo × faixa etária ×
                     raça/cor × escolaridade × estadiamento × tipo → casos e
                     prazo. É o único lugar do projeto onde iniquidade no
                     acesso oncológico é mensurável.
`mart_rhc_tratamento` UF do HOSPITAL × ano × CID-3 × estadiamento × primeiro
                     tratamento × razão de não tratar × estado ao fim
`mart_rhc_cobertura` ano × UF do HOSPITAL → o que entrou, o que faltou, e por quê

DUAS GEOGRAFIAS, E ELAS NÃO SÃO A MESMA
----------------------------------------
`mart_rhc_caso` é por município de **residência** (`PROCEDEN`). Os outros três
são por UF do **hospital** (`UFUH`). Não é descuido: a pergunta "onde mora quem
adoece" e a pergunta "onde está a estrutura que trata" são diferentes, e o RHC
é justamente a fonte em que elas divergem muito — cerca de metade dos pacientes
oncológicos se trata fora do próprio município, número que este projeto já
mediu no SIH e na APAC.

Cruzar os dois como se fossem a mesma geografia produz número sem significado.
Está dito também no comentário de coluna de `mart_rhc_cobertura.uf_sigla`, que
é onde quem consulta o banco vai olhar.

AS ARMADILHAS, E COMO CADA UMA É TRATADA AQUI
---------------------------------------------
1. **`ESTADIAM` 88/99 não é estádio.** Vira `"ignorado"`, com rótulo próprio,
   nunca somado a estádio 0. São ~53% dos registros, e publicá-los como estádio
   inventaria uma distribuição. Mesma regra de `_estadio` na APAC, e pela mesma
   razão: lá o erro custou uma coleta inteira.
2. **O ano do arquivo é o da PRIMEIRA CONSULTA**, não o do diagnóstico. A
   coluna se chama `ano_primeira_consulta` por isso. `ANOPRIDI` diverge dela em
   21,7% dos registros de 2019, e a cobertura publica essa divergência.
3. **Caso analítico e não analítico são universos diferentes.** `tipo_caso` é
   coluna de chave, não filtro escondido: quem quiser o universo da literatura
   filtra `analitico`, e quem somar os dois sabe o que está somando.
4. **A data é `DD/MM/YYYY`.** O leitor está em `sondar_rhc.data_br`, e recusa
   `YYYYMMDD` de propósito — é o formato do resto do projeto, e aceitá-lo aqui
   produziria data errada em silêncio.

O PRAZO É PUBLICADO AQUI, E NÃO NA APAC
---------------------------------------
`mart_apac_oncologia_*` não publica prazo, por decisão registrada: a subtração
entre `AQ_DTIDEN` e `AQ_DTINTR` conta autorização e produz manchete falsa
(2026-09-21: 256 dias contra 68 quando se conta pessoa). No RHC a unidade JÁ é
a pessoa e a data de diagnóstico é o laudo, então o prazo é o que a fonte
realmente mede.

Ainda assim ele sai em CONTAGEM, não em mediana: mediana não se agrega, e uma
coluna `mediana_dias` num mart municipal seria somada por quem lesse rápido. As
colunas são `casos_com_prazo`, `casos_ate_60d` e `casos_acima_60d`, e qualquer
proporção se calcula sobre elas.

Excluído do prazo, seguindo Jomar et al. 2023: intervalo negativo ou acima de
365 dias. Eles chamam de outlier e excluem 384 de 18.098; aqui a contagem do
que saiu fica na cobertura, e não em rodapé.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from hashlib import blake2b
from collections import defaultdict
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from _rhc_codigos import (  # noqa: E402
    ESCOLARIDADE,
    ESTADO_FIM_TRATAMENTO,
    PRIMEIRO_TRATAMENTO,
    RACA_COR,
    RAZAO_NAO_TRATAMENTO,
    SEXO,
    decodificar,
    faixa_etaria,
    tem_data,
)
from _saida import Resultado  # noqa: E402
from sondar_rhc import (  # noqa: E402
    baixar_ano,
    campos_do_dbf,
    data_br,
    estadio,
    metadados_do_dbf,
)

CACHE = RAIZ / "data" / "cache"
MARTS = RAIZ / "data" / "marts"

#: 2013 é o primeiro ano inteiro sob a Lei 12.732/2012; 2023 é o último que o
#: INCA publica. Anos anteriores existem (desde 1985) e ficam fora por recorte,
#: não por indisponibilidade.
ANOS = tuple(range(2013, 2024))

#: Teto do intervalo, em dias, seguindo Jomar et al. 2023. Acima disso o
#: registro entra em `casos_sem_prazo` — não some.
TETO_PRAZO = 365
PRAZO_LEGAL = 60

TIPO_CASO = {"1": "analitico", "2": "nao_analitico"}

#: O arquivo do INCA tem 46 campos. A primeira versão deste pipeline lia 10, e
#: os 36 que ficaram de fora incluíam justamente o que distingue o RHC das
#: outras duas fontes oncológicas: sexo e idade (sem os quais não se reproduz
#: recorte nenhum da literatura), raça/cor e escolaridade (que nenhuma das
#: outras 15 fontes do projeto tem), e `PRITRATH`, o primeiro tratamento de
#: QUALQUER modalidade — que é o que a Lei 12.732/2012 conta e o que a APAC de
#: quimioterapia não consegue observar.
#:
#: `DATAOBITO` entra para ser CONTADO, não para virar sobrevida. Ver a ressalva
#: em `_guardas` e o comentário de coluna de `casos_com_data_obito`.
CAMPOS = ("TPCASO", "LOCTUDET", "ESTADIAM", "DTDIAGNO", "DATAINITRT",
          "PROCEDEN", "ESTADRES", "UFUH", "CNES", "ANOPRIDI",
          "SEXO", "IDADE", "RACACOR", "INSTRUC",
          "PRITRATH", "RZNTR", "ESTDFIMT", "DATAOBITO")


#: O EXPORTADOR DO INCA GRAVA CADA PÁGINA DUAS VEZES
#: ------------------------------------------------
#: Medido em 2026-09-21, nos 11 anos: o arquivo declara `n` registros no
#: cabeçalho, ocupa exatamente `n` slots, e **cada registro aparece duas
#: vezes** — a cópia mora `PAGINA` posições adiante.
#:
#:     ano     n declarado    distintos    razão
#:     2013        406.766      202.270    2,011
#:     2019        518.186      258.322    2,006
#:     2023        142.038       70.737    2,008
#:
#: A razão passa de 2,000 porque existem pacientes genuinamente idênticos nos
#: campos publicados — e é por isso que a correção **divide a multiplicidade
#: por dois** em vez de "remover duplicata": deduplicar por valor apagaria os
#: gêmeos verdadeiros e produziria subcontagem.
#:
#: O padrão é de paginação: páginas de 50.000 escritas em dobro, e a última
#: página parcial também. É o mesmo modo de falha que este projeto já
#: documentou na própria exportação do Postgres — `LIMIT/OFFSET` sem `ORDER
#: BY` duplica e perde linha. Aqui ele veio de fora, e custou publicar toda a
#: 16ª fonte com o dobro de casos (2022: 461.166 publicados, 230.583 reais).
PAGINA = 50_000


def _posicao(i: int, n: int) -> tuple[bool, int]:
    """(é original?, posição dentro da página) para o registro `i` de `n`.

    Páginas de `PAGINA` alternam original/cópia. A última página é parcial e
    também vem em dobro, então o corte dela é a metade do que sobrou — não
    `PAGINA`. Sem esse caso especial, 2023 perderia 21.019 casos reais.

    A posição é o que permite conferir a cópia contra o original certo: a
    cópia do registro `p` da página está em `p + tamanho_da_pagina`.
    """
    inicio_da_cauda = (n // (2 * PAGINA)) * (2 * PAGINA)
    if i < inicio_da_cauda:
        tamanho, desloc = PAGINA, i % (2 * PAGINA)
    else:
        tamanho = (n - inicio_da_cauda) // 2
        desloc = i - inicio_da_cauda
    return (desloc < tamanho), (desloc if desloc < tamanho else desloc - tamanho)


def _registros(caminho: Path):
    """Itera o .dbf de dentro do .zip, devolvendo só os campos que interessam.

    Lê em blocos: o arquivo de 2019 tem 477 MB descompactados e 518 mil
    registros de 921 bytes. Carregar inteiro custaria mais memória que o
    pipeline da APAC, que processa quarenta vezes mais linhas.

    **Descarta a segunda cópia de cada página** — ver `PAGINA` acima — e
    CONFERE, registro a registro e não por amostra, que o descartado é mesmo
    byte por byte igual ao guardado. Custa 8 bytes de hash por registro da
    página corrente (400 KB) e é o que separa "corrigi uma duplicação medida"
    de "dividi por dois e torci".
    """
    z = zipfile.ZipFile(caminho)
    nome = next(n for n in z.namelist() if n.lower().endswith(".dbf"))
    with z.open(nome) as f:
        c32 = f.read(32)
        n, ini, larg = metadados_do_dbf(c32)
        campos = campos_do_dbf(c32 + f.read(ini - 32))
        sel = [(nm, o, t) for nm, o, t in campos if nm in CAMPOS]
        faltam = set(CAMPOS) - {nm for nm, _, _ in sel}
        if faltam:
            raise SystemExit(
                f"[rhc] {caminho.name}: campos ausentes {sorted(faltam)}. O "
                f"layout do INCA mudou; conferir com sondar_rhc.py antes de "
                f"publicar qualquer número.")
        lidos = mantidos = 0
        guardados: list[bytes] = []   # hashes da página original corrente
        while lidos < n:
            bloco = f.read(larg * min(20_000, n - lidos))
            if not bloco:
                break
            for i in range(0, len(bloco) - larg + 1, larg):
                r = bloco[i:i + larg]
                original, pos = _posicao(lidos, n)
                if original:
                    if pos == 0:
                        guardados = []          # começou página nova
                    guardados.append(blake2b(r, digest_size=8).digest())
                    mantidos += 1
                    yield {nm: r[o:o + t].decode("latin-1").strip()
                           for nm, o, t in sel}
                elif blake2b(r, digest_size=8).digest() != guardados[pos]:
                    # A cópia tem que bater byte por byte com o original na
                    # MESMA posição da página. Se não bater, a geometria mudou
                    # e dividir por dois passaria a descartar dado de verdade.
                    raise SystemExit(
                        f"[rhc] {caminho.name}: o registro {lidos} não é cópia "
                        f"do original na posição {pos} da página. A duplicação "
                        f"por página de {PAGINA} deixou de valer — reconferir "
                        f"com sondar_rhc.py ANTES de publicar qualquer número, "
                        f"porque a correção pela metade depende dela.")
                lidos += 1
        if mantidos * 2 != n:
            raise SystemExit(
                f"[rhc] {caminho.name}: mantidos {mantidos:,} de {n:,}; "
                f"esperado exatamente a metade.")


def _prazo(rec: dict) -> tuple[bool, int | None]:
    """(entrou no prazo, dias). `entrou=False` quando a data não serve.

    Ausência de data e intervalo impossível são a MESMA coluna na cobertura, e
    nenhuma das duas vira zero dia.
    """
    di, dt = data_br(rec["DTDIAGNO"]), data_br(rec["DATAINITRT"])
    if not di or not dt:
        return False, None
    dias = (pd.Timestamp(dt) - pd.Timestamp(di)).days
    if dias < 0 or dias > TETO_PRAZO:
        return False, dias
    return True, dias


def _acumular(alvo: list, ok: bool, dias: int | None) -> None:
    """Soma um caso na célula, e o prazo dele se a fonte souber dizer qual é.

    `ok=False` cobre ausência de data E intervalo impossível, e nenhum dos dois
    vira zero dia: o caso conta em `casos` e não conta em `casos_com_prazo`.
    A diferença entre as duas colunas é o que `sem_prazo` publica na cobertura.
    """
    alvo[0] += 1
    if ok:
        alvo[1] += 1
        if dias <= PRAZO_LEGAL:
            alvo[2] += 1
        else:
            alvo[3] += 1


def processar_ano(ano: int) -> tuple[dict, dict, dict, dict]:
    """Uma passada pelo arquivo, três agregações.

    O arquivo de 2019 tem 477 MB e 518 mil registros; ler três vezes para
    montar três marts custaria três vezes o I/O sem nenhum ganho. As quatro
    estruturas saem juntas e o custo é a memória dos dicionários, que é
    pequena perto do arquivo.
    """
    caminho = CACHE / f"rhc_{ano}.zip"
    if not caminho.exists():
        print(f"[rhc] {ano}: baixando", flush=True)
        baixar_ano(ano, caminho)

    casos: dict = defaultdict(lambda: [0, 0, 0, 0])   # casos, com_prazo, ate60, acima60
    perfil: dict = defaultdict(lambda: [0, 0, 0, 0])
    trat: dict = defaultdict(lambda: [0, 0])          # casos, com_data_obito
    cob: dict = defaultdict(lambda: defaultdict(int))
    hospitais: dict = defaultdict(set)
    municipios: dict = defaultdict(set)

    for rec in _registros(caminho):
        uf = rec["UFUH"] or "??"
        mun = rec["PROCEDEN"][:6]
        tipo = TIPO_CASO.get(rec["TPCASO"], "ignorado")
        est = estadio(rec["ESTADIAM"])
        cid = rec["LOCTUDET"][:3].upper()
        ok, dias = _prazo(rec)

        sexo = decodificar(SEXO, rec["SEXO"])
        faixa = faixa_etaria(rec["IDADE"])
        raca = decodificar(RACA_COR, rec["RACACOR"])
        escol = decodificar(ESCOLARIDADE, rec["INSTRUC"])
        tratamento = decodificar(PRIMEIRO_TRATAMENTO, rec["PRITRATH"])
        razao = decodificar(RAZAO_NAO_TRATAMENTO, rec["RZNTR"])
        fim = decodificar(ESTADO_FIM_TRATAMENTO, rec["ESTDFIMT"])
        obito = tem_data(rec["DATAOBITO"])

        c = cob[uf]
        c["casos"] += 1
        c[tipo] += 1
        if est == "ignorado":
            c["sem_estadiamento"] += 1
        if not ok:
            c["sem_prazo"] += 1
        if rec["ANOPRIDI"] and rec["ANOPRIDI"] != str(ano):
            c["ano_diagnostico_difere"] += 1
        # As ausências dos campos novos são CONTADAS, uma a uma. Ausência que
        # não é contada é ausência que vira zero na conta de quem lê.
        if sexo == "ignorado":
            c["sexo_ignorado"] += 1
        if faixa == "ignorada":
            c["idade_ignorada"] += 1
        if raca == "ignorado":
            c["raca_ignorada"] += 1
        if escol == "ignorado":
            c["escolaridade_ignorada"] += 1
        if tratamento == "ignorado":
            c["primeiro_tratamento_ignorado"] += 1
        if obito:
            c["com_data_obito"] += 1
        if rec["CNES"]:
            hospitais[uf].add(rec["CNES"])
        if len(mun) == 6:
            municipios[uf].add(mun)

        if not cid:
            continue

        if len(mun) == 6:
            _acumular(casos[(mun, ano, cid, est, tipo)], ok, dias)
        _acumular(perfil[(uf, ano, cid, sexo, faixa, raca, escol, est, tipo)],
                  ok, dias)

        t = trat[(uf, ano, cid, est, tratamento, razao, fim)]
        t[0] += 1
        t[1] += int(obito)

    for uf in cob:
        cob[uf]["hospitais"] = len(hospitais[uf])
        cob[uf]["municipios"] = len(municipios[uf])
    return casos, perfil, trat, cob


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anos", type=int, nargs="*", default=list(ANOS))
    a = ap.parse_args()

    linhas_caso, linhas_perfil, linhas_trat, linhas_cob = [], [], [], []
    for ano in a.anos:
        casos, perfil, trat, cob = processar_ano(ano)
        for k, v in casos.items():
            linhas_caso.append((*k, *v))
        for k, v in perfil.items():
            linhas_perfil.append((*k, *v))
        for k, v in trat.items():
            linhas_trat.append((*k, *v))
        for uf, c in cob.items():
            linhas_cob.append((ano, uf, c["casos"], c["analitico"],
                               c["nao_analitico"], c["sem_estadiamento"],
                               c["sem_prazo"], c["ano_diagnostico_difere"],
                               c["sexo_ignorado"], c["idade_ignorada"],
                               c["raca_ignorada"], c["escolaridade_ignorada"],
                               c["primeiro_tratamento_ignorado"],
                               c["com_data_obito"],
                               c["hospitais"], c["municipios"]))
        total = sum(c["casos"] for c in cob.values())
        print(f"[rhc] {ano}: {total:,} casos | caso {len(casos):,} · "
              f"perfil {len(perfil):,} · tratamento {len(trat):,}", flush=True)

    caso = pd.DataFrame(linhas_caso, columns=[
        "municipio_cod", "ano_primeira_consulta", "cid3", "estadiamento",
        "tipo_caso", "casos", "casos_com_prazo", "casos_ate_60d",
        "casos_acima_60d"])
    perfil = pd.DataFrame(linhas_perfil, columns=[
        "uf_sigla", "ano_primeira_consulta", "cid3", "sexo", "faixa_etaria",
        "raca_cor", "escolaridade", "estadiamento", "tipo_caso",
        "casos", "casos_com_prazo", "casos_ate_60d", "casos_acima_60d"])
    tratamento = pd.DataFrame(linhas_trat, columns=[
        "uf_sigla", "ano_primeira_consulta", "cid3", "estadiamento",
        "primeiro_tratamento", "razao_nao_tratamento",
        "estado_fim_tratamento", "casos", "casos_com_data_obito"])
    cobertura = pd.DataFrame(linhas_cob, columns=[
        "ano_primeira_consulta", "uf_sigla", "casos", "analiticos",
        "nao_analiticos", "sem_estadiamento", "sem_prazo",
        "ano_diagnostico_difere", "sexo_ignorado", "idade_ignorada",
        "raca_ignorada", "escolaridade_ignorada",
        "primeiro_tratamento_ignorado", "com_data_obito",
        "hospitais", "municipios"])

    incompletos = anos_incompletos(cobertura)
    for df in (caso, perfil, tratamento, cobertura):
        df["ano_incompleto"] = df.ano_primeira_consulta.isin(incompletos)
    if incompletos:
        print(f"[rhc] anos marcados como incompletos: {sorted(incompletos)}",
              flush=True)

    _guardas(caso, cobertura)
    _guardas_perfil(caso, perfil, tratamento, cobertura)

    MARTS.mkdir(parents=True, exist_ok=True)
    res = Resultado("scripts/pipeline_rhc.py")
    res.gravar(caso, MARTS / "mart_rhc_caso.parquet")
    res.gravar(perfil, MARTS / "mart_rhc_perfil.parquet")
    res.gravar(tratamento, MARTS / "mart_rhc_tratamento.parquet")
    res.gravar(cobertura, MARTS / "mart_rhc_cobertura.parquet")
    print(f"[rhc] caso {len(caso):,} · perfil {len(perfil):,} · "
          f"tratamento {len(tratamento):,} · cobertura {len(cobertura):,}",
          flush=True)
    return res.relatar()


#: Abaixo desta fração do platô de hospitais reportando, o ano é declarado
#: incompleto. 0,90 porque a variação entre anos assentados é de 213 a 235
#: hospitais (±5%), medida em 2026-09-21.
LIMIAR_COMPLETUDE = 0.90


def anos_incompletos(cob: pd.DataFrame) -> set[int]:
    """Anos cuja contagem de hospitais está abaixo do platô.

    POR QUE ISTO EXISTE
    -------------------
    2023 traz 71.019 casos contra 230.583 em 2022. Lido como série, isso é um
    colapso de 69% na detecção de câncer no Brasil. Não é: são **15 UFs e 69
    hospitais** contra 25 e 189, porque o RHC se enche ao longo de anos —
    hospital envia quando fecha o registro, não no fim do ano.

    O projeto já pagou por não carimbar isto: uma competência com 63% de
    dezembro faltando passou em toda guarda de forma e virou série publicada.
    A regra desde então é carimbar na LINHA, não em rodapé, como
    `meses_cobertos` faz no SIH e no mart da sífilis.

    O platô é a mediana dos anos anteriores ao último terço da série — a mesma
    ideia de `analise_cauda_de_reporte.py`, e pela mesma razão: comparar com a
    média da série inteira deixaria a própria cauda rebaixar o platô.
    """
    por_ano = cob.groupby("ano_primeira_consulta").hospitais.sum().sort_index()
    if len(por_ano) < 4:
        return set()
    corte = max(2, len(por_ano) // 3)
    plato = float(por_ano.iloc[:-corte].median())
    return {int(a) for a, v in por_ano.items() if v < LIMIAR_COMPLETUDE * plato}


#: Acima desta fração, "ignorado" deixou de ser ausência e virou o campo
#: inteiro — assinatura de layout deslocado, que é o modo de falha do dBase de
#: largura fixa: um campo a mais no cabeçalho e TODOS os offsets seguintes
#: andam, produzindo valor plausível e errado.
TETO_IGNORADO = 0.95

#: `DATAOBITO` vem com a máscara `"/  /"` em 83% dos registros. Se a contagem
#: de óbito se aproximar do total, o leitor voltou a contar máscara como data —
#: foi exatamente assim que ela mediu 99,6% antes de `tem_data` existir.
TETO_DATA_OBITO = 0.60


def _guardas_perfil(caso: pd.DataFrame, perfil: pd.DataFrame,
                    trat: pd.DataFrame, cob: pd.DataFrame) -> None:
    """As guardas dos campos que entraram em 2026-09-21, na segunda passada.

    Todas existem por um defeito concreto medido, e não por simetria: as três
    primeiras pegam layout deslocado, a quarta pega a máscara de data vazia, e
    a quinta pega o erro que apagaria o denominador de um estudo de acesso.
    """
    if perfil.empty or trat.empty:
        raise SystemExit("[rhc] mart de perfil ou de tratamento vazio")

    # 1. As três agregações saem da MESMA passada, então têm que fechar entre
    #    si. `caso` é municipal e descarta município inválido, logo é o menor;
    #    `perfil` e `tratamento` filtram só CID ausente, logo são iguais.
    n_perfil, n_trat, n_caso = (int(perfil.casos.sum()), int(trat.casos.sum()),
                                int(caso.casos.sum()))
    if n_perfil != n_trat:
        raise SystemExit(
            f"[rhc] perfil ({n_perfil:,}) e tratamento ({n_trat:,}) não fecham. "
            f"Saem da mesma passada e do mesmo filtro — divergir significa que "
            f"uma das duas perdeu registro.")
    if n_caso > n_perfil:
        raise SystemExit(
            f"[rhc] o mart municipal ({n_caso:,}) tem MAIS casos que o de "
            f"perfil ({n_perfil:,}), e ele é o que descarta município inválido.")

    # 2. A classificação do prazo fecha no perfil como fecha no caso.
    if not ((perfil.casos_ate_60d + perfil.casos_acima_60d)
            == perfil.casos_com_prazo).all():
        raise SystemExit("[rhc] perfil: casos_ate_60d + casos_acima_60d não "
                         "fecha com casos_com_prazo.")
    if (perfil.casos_com_prazo > perfil.casos).any():
        raise SystemExit("[rhc] perfil: mais casos com prazo do que casos.")

    # 3. Campo 100% ignorado é layout deslocado, não ausência.
    for ano, sub in cob.groupby("ano_primeira_consulta"):
        total = sub.casos.sum()
        for coluna in ("sexo_ignorado", "idade_ignorada", "raca_ignorada",
                       "escolaridade_ignorada",
                       "primeiro_tratamento_ignorado"):
            frac = sub[coluna].sum() / total
            if frac > TETO_IGNORADO:
                raise SystemExit(
                    f"[rhc] {ano}: {coluna} em {100 * frac:.1f}% dos casos. "
                    f"Acima de {100 * TETO_IGNORADO:.0f}% não é ausência, é o "
                    f"layout do dBase deslocado — conferir com sondar_rhc.py.")
        # Raça/cor e escolaridade TÊM ausência: 9,0% e 24,7% em 2019. Zero é a
        # assinatura de o código 9 ter voltado a ser lido como categoria.
        for coluna in ("raca_ignorada", "escolaridade_ignorada"):
            if sub[coluna].sum() == 0:
                raise SystemExit(
                    f"[rhc] {ano}: NENHUM caso com {coluna}. O código 9 ('sem "
                    f"informação') voltou a ser lido como categoria válida.")

    # 4. A máscara de data vazia, que já mediu 99,6% de preenchimento.
    frac_obito = cob.com_data_obito.sum() / cob.casos.sum()
    if frac_obito > TETO_DATA_OBITO:
        raise SystemExit(
            f"[rhc] data de óbito em {100 * frac_obito:.1f}% dos casos. "
            f"Medido: 15,9%. Acima de {100 * TETO_DATA_OBITO:.0f}% significa "
            f"que a máscara '/  /' voltou a contar como data preenchida.")
    if frac_obito == 0:
        raise SystemExit("[rhc] NENHUMA data de óbito. `tem_data` passou a "
                         "recusar data válida.")

    # 5. "Nenhum tratamento" é resposta, "sem informação" é ausência, e
    #    confundi-los apaga justamente quem um estudo de acesso precisa contar.
    rotulos = set(trat.primeiro_tratamento)
    if "nenhum" not in rotulos:
        raise SystemExit(
            "[rhc] nenhum caso com primeiro_tratamento = 'nenhum'. São 83.956 "
            "em 2019, e sumirem significa que o código 1 virou ausência.")
    if "ignorado" not in rotulos:
        raise SystemExit("[rhc] nenhum 'ignorado' em primeiro_tratamento — "
                         "ausência declarada não pode desaparecer.")


def _guardas(caso: pd.DataFrame, cob: pd.DataFrame) -> None:
    """As três que a sondagem disse serem necessárias, conferidas ano a ano."""
    if caso.empty or cob.empty:
        raise SystemExit("[rhc] mart vazio")

    for ano, sub in cob.groupby("ano_primeira_consulta"):
        pct = 100 * sub.sem_estadiamento.sum() / sub.casos.sum()
        if pct == 0:
            raise SystemExit(
                f"[rhc] {ano}: NENHUM caso sem estadiamento. Medido na "
                f"sondagem: ~53%. Zero significa que 88/99 voltaram a ser "
                f"lidos como estádio.")
        if pct > 90:
            raise SystemExit(f"[rhc] {ano}: {pct:.1f}% sem estadiamento — o "
                             f"campo mudou de código.")
        if sub.nao_analiticos.sum() == 0:
            raise SystemExit(
                f"[rhc] {ano}: nenhum caso não analítico. TPCASO parou de "
                f"distinguir os dois universos, e somá-los vira outro estudo.")

    soma = caso.casos_ate_60d + caso.casos_acima_60d
    if not (soma == caso.casos_com_prazo).all():
        raise SystemExit("[rhc] casos_ate_60d + casos_acima_60d não fecha com "
                         "casos_com_prazo: a classificação perdeu registro.")
    if (caso.casos_com_prazo > caso.casos).any():
        raise SystemExit("[rhc] mais casos com prazo do que casos.")
    if "0" in set(caso.estadiamento) and "ignorado" not in set(caso.estadiamento):
        raise SystemExit("[rhc] há estádio 0 e nenhum 'ignorado' — é a "
                         "assinatura de ausência publicada como diagnóstico "
                         "precoce, o erro que a APAC já pagou.")

    # O carimbo de ano incompleto só vale se ele cair no ANO CERTO. Um ano com
    # menos hospitais que o platô e sem carimbo é exatamente a série que se
    # lê como colapso da detecção de câncer.
    esperados = anos_incompletos(cob)
    marcados = set(cob.loc[cob.ano_incompleto, "ano_primeira_consulta"])
    if marcados != esperados:
        raise SystemExit(
            f"[rhc] carimbo de ano incompleto fora do lugar: marcados "
            f"{sorted(marcados)}, esperados {sorted(esperados)}.")
    ultimo = int(cob.ano_primeira_consulta.max())
    if ultimo not in esperados:
        print(f"[rhc] atenção: {ultimo} NÃO foi marcado como incompleto. O RHC "
              f"se enche ao longo de anos — conferir se ele fechou mesmo.")
    for ano, sub in caso.groupby("ano_primeira_consulta"):
        if sub.ano_incompleto.nunique() != 1:
            raise SystemExit(f"[rhc] {ano}: carimbo divergente dentro do ano.")


if __name__ == "__main__":
    sys.exit(main())
