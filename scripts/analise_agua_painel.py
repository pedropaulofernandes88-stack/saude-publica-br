"""
analise_agua_painel.py — o desenho de painel, depois da revisão por pares
==========================================================================

    .venv311/Scripts/python scripts/analise_agua_painel.py

Grava `data/analises/agua-painel/tab*.csv`.

POR QUE ESTA ANÁLISE EXISTE, E O QUE ELA SUBSTITUI
---------------------------------------------------
A primeira versão deste trabalho (`analise_agua_mortalidade.py`) comparava
municípios entre si num corte de dez anos: sem vigilância contra vigilância
regular, com um controle negativo e razão de razões de 2,08. A revisão por pares
apontou três problemas, e os três procedem:

1. **o ajuste era fraco.** Quartis de domicílios sem ligação à rede não
   controlam esgoto, renda, urbanização, porte, região, cobertura de atenção
   primária, estrutura etária nem qualidade geral do registro;
2. **um controle negativo não basta.** Se toda causa infecciosa se comportar
   igual, a leitura é fragilidade geral do sistema, não caminho hídrico;
3. **o baseline de 2019 era conveniente.** A série é plana de 2015 a 2019, cai
   na pandemia e recupera depois. "A queda parou e inverteu" afirmava um
   declínio anterior que o dado não mostra.

Esta análise responde aos três.

O EFEITO FIXO DE MUNICÍPIO, E O PREÇO QUE ELE COBRA
----------------------------------------------------
O estimador é Poisson condicional de efeitos fixos (`_poisson_fe.py`), que
absorve **todo** confundidor invariante no tempo — medido ou não. É a única
forma de controle que não depende de eu ter pensado na variável certa, e ela
torna desnecessária a lista de covariáveis que a revisão pediu: renda,
urbanização, porte e esgoto não variam o suficiente em dez anos para
sobreviverem ao efeito fixo.

O preço é que a exposição precisa **variar dentro do município**. A exposição da
primeira versão — mediana de meses no decênio — é constante por município e
seria apagada inteira. Aqui a exposição é a **vigilância do ano anterior**, que
muda ao longo do painel; é a defasagem que a revisão sugeriu, e ela não é
refinamento: é o que torna o painel possível.

Efeitos de ANO entram como indicadoras, de modo que choques nacionais — a
pandemia inclusive — não são atribuídos à exposição.

OS CRITÉRIOS, DECLARADOS ANTES DE QUALQUER RESULTADO
-----------------------------------------------------
  CRITÉRIO 1 — ESPECIFICIDADE ENTRE CAUSAS (é o que refuta)
    A razão de taxas (IRR) da ausência de vigilância é estimada para CINCO
    grupos de causa. Para a interpretação hídrica valer, são necessárias duas
    coisas: o IRR de A00–A09 acima de 1 com IC95% que exclua 1, **e** maior que
    o de todos os outros grupos.
    **Se os IRR forem semelhantes entre as causas infecciosas, a leitura é
    fragilidade geral do sistema de saúde, e é assim que vai reportada.**
    Esta é a diferença central em relação à primeira versão, que tinha um
    controle só e não podia distinguir as duas coisas.

  CRITÉRIO 2 — SOBREVIVER AO EFEITO FIXO
    O IRR com efeitos fixos de município é comparado ao mesmo IRR sem eles. Se
    ele colapsar para perto de 1 sob efeito fixo, a associação do corte
    transversal era confundimento entre municípios, e o achado da primeira
    versão cai.

  CRITÉRIO 3 — A ALTA EXCEDE A TENDÊNCIA PRÉ-PANDEMIA?
    Ajuste log-linear sobre 2015–2019, projeção para 2022–2024, comparação com o
    observado. **Se 2024 não exceder a projeção, "a alta" é recuperação** e o
    artigo passa a descrever retomada, não excesso.

  CRITÉRIO 4 — ROBUSTEZ
    O resultado tem de sobreviver a: exclusão do Distrito Federal (uma unidade
    de 3 milhões de habitantes que o SISAGUA organiza por região administrativa
    e o SIM por um código, e cuja classificação é insegura por isso); exclusão
    de municípios com menos de 5.000 habitantes; e não depender de uma região.

O QUE ESTE DESENHO CONTINUA NÃO PODENDO DIZER
----------------------------------------------
É ECOLÓGICO. Efeito fixo de município controla confundimento entre municípios,
não falácia ecológica: nada aqui autoriza dizer que quem morreu consumiu água
não vigiada. E ausência de registro não é água contaminada — é ausência da
prova, e pode ser fragilidade administrativa do município em reportar.

O efeito fixo também NÃO controla confundimento que varia no tempo dentro do
município: um município que passa a não reportar no mesmo ano em que perde
capacidade de vigilância em saúde em geral confunde os dois, e o desenho não
separa. O Critério 1 é a única defesa contra isso, e é por isso que ele é o que
refuta.

Depende de: data/marts/{mart_mortalidade_causa_municipio, mart_sisagua_municipio,
dim_populacao, dim_municipio}.parquet e scripts/_poisson_fe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _poisson_fe import ajustar_matriz  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
REFS = ROOT / "data" / "refs"
SAIDA = ROOT / "data" / "analises" / "agua-painel"

#: Desfecho de 2016 a 2024; a exposicao e' o ano anterior, e 2015 fornece o
#: primeiro t-1. 2025 fica fora por ser preliminar.
ANOS_DESFECHO = list(range(2016, 2025))
ANOS_SISAGUA = list(range(2015, 2025))
REPS = 400
SEMENTE = 20260912
POP_MINIMA = 5_000

#: Os cinco grupos de causa. A ordem e' a do argumento: a hipotese primeiro, os
#: controles depois, do mais parecido ao menos parecido.
GRUPOS = {
    "A00-A09 intestinais (hipotese)": r"^A0[0-9]$",
    "J00-J22 respiratorias (subgrupo 1.2)": r"^J(0[0-6]|1[0-9]|2[0-2])$",
    "outras infecciosas do subgrupo 1.2": (
        r"^(A1[568]|B90|B1[5789]|B2[0-4]|A5[0-9]|A6[34]|N7[0-6]|I0[0-9]|L0[2-8])$"),
    "I20-I25 isquemicas do coracao": r"^I2[0-5]$",
    "V01-Y98 causas externas": r"^[VWXY]",
}


def montar_painel() -> pd.DataFrame:
    """Uma linha por municipio x ano, com a exposicao do ano ANTERIOR."""
    mort = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                           columns=["municipio_cod", "ano", "causabas_3", "obitos"])
    mort = mort[mort.ano.isin(ANOS_DESFECHO)]

    base = (mort.groupby(["municipio_cod", "ano"], as_index=False)
            .obitos.sum().rename(columns={"obitos": "obitos_total"}))
    for nome, padrao in GRUPOS.items():
        col = (mort[mort.causabas_3.str.match(padrao)]
               .groupby(["municipio_cod", "ano"], as_index=False)
               .obitos.sum().rename(columns={"obitos": nome}))
        base = base.merge(col, on=["municipio_cod", "ano"], how="left")
    for nome in GRUPOS:
        base[nome] = base[nome].fillna(0)

    pop = pd.read_parquet(MARTS / "dim_populacao.parquet")[
        ["municipio_cod", "ano", "populacao"]]
    base = base.merge(pop, on=["municipio_cod", "ano"], how="inner")

    # exposicao: meses com analise no ano t-1. Municipio-ano sem linha no mart
    # do SISAGUA e' ZERO mes, nao ausente — e' o que "nao reportou" significa.
    sis = pd.read_parquet(MARTS / "mart_sisagua_municipio.parquet",
                          columns=["municipio_cod", "ano", "meses_com_analise"])
    sis = (sis[sis.ano.isin(ANOS_SISAGUA)]
           .groupby(["municipio_cod", "ano"], as_index=False)
           .meses_com_analise.median())
    sis["ano"] = sis.ano + 1                       # vira exposicao do ano seguinte
    base = base.merge(sis.rename(columns={"meses_com_analise": "meses_t1"}),
                      on=["municipio_cod", "ano"], how="left")
    base["meses_t1"] = base.meses_t1.fillna(0.0)
    base["sem_vigilancia_t1"] = (base.meses_t1 == 0).astype(float)

    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")[
        ["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]
    base = base.merge(dim, on="municipio_cod", how="inner")

    antes = len(base)
    base = base[base.populacao > 0].copy()
    print(f"[painel] {antes:,} linhas municipio-ano -> {len(base):,} com populacao",
          flush=True)
    print(f"[painel] {base.municipio_cod.nunique():,} municipios x "
          f"{base.ano.nunique()} anos", flush=True)
    print(f"[painel] municipio-ano sem vigilancia no ano anterior: "
          f"{int(base.sem_vigilancia_t1.sum()):,} "
          f"({100 * base.sem_vigilancia_t1.mean():.1f}%)", flush=True)
    return base


def empilhar(d: pd.DataFrame, exposicao: str = "sem_vigilancia_t1") -> dict:
    """Converte o painel em MATRIZES (municipio x ano), uma vez.

    O painel e' balanceado — 9 anos para cada um dos 5.570 municipios, conferido
    — e isso permite que cada municipio seja uma LINHA. A partir daqui uma
    replica de bootstrap e' `Y[amostra]`: indexacao de linhas, sem remontar
    pedaco algum. Na versao anterior, que reamostrava DataFrames, a primeira das
    cinco causas nao terminou em vinte minutos.
    """
    d = d.sort_values(["municipio_cod", "ano"])
    munis = d.municipio_cod.unique()
    anos = np.array(sorted(d.ano.unique()))
    M, T = len(munis), len(anos)
    if len(d) != M * T:
        raise SystemExit(
            f"painel desbalanceado: {len(d):,} linhas para {M:,} municipios x "
            f"{T} anos. `empilhar` supoe balanceamento, e supor errado aqui "
            "embaralharia municipio com ano sem que nada acuse.")

    # desenho: exposicao + indicadoras de ano (a primeira fica de fora)
    # `exposicao` e' parametro porque a analise irma do E. coli
    # (`analise_agua_ecoli.py`) reusa esta funcao com outra coluna. O nome
    # padrao preserva o comportamento de quem ja chamava sem argumento.
    colunas = [d[exposicao].to_numpy().reshape(M, T)]
    for a in anos[1:]:
        colunas.append((d.ano.to_numpy() == a).astype(float).reshape(M, T))
    X = np.stack(colunas, axis=2)

    return {
        "munis": munis, "anos": anos, "M": M, "T": T, "X": X,
        "OFF": d.populacao.to_numpy(dtype=float).reshape(M, T),
        "Y": {nome: d[nome].to_numpy(dtype=float).reshape(M, T) for nome in GRUPOS},
        "uf": d.groupby("municipio_cod", sort=True).uf_sigla.first().to_numpy(),
        "regiao": d.groupby("municipio_cod", sort=True).regiao.first().to_numpy(),
        "pop_media": d.groupby("municipio_cod", sort=True).populacao.mean().to_numpy(),
        "tabela": d,
    }


def _filtrar(P: dict, selecao: np.ndarray) -> dict:
    """Um sub-painel. `selecao` e' mascara booleana OU vetor de indices.

    As duas formas entram aqui: o recorte ("sem o DF") e' booleano, e a replica
    de bootstrap e' vetor de indices com repeticao. Por isso M sai da FORMA do
    resultado, e nao de `selecao.sum()` — somar um vetor de indices devolveria
    a soma dos codigos de linha, um M enorme, e o bootstrap reamostraria numero
    errado de municipios sem nada acusar.
    """
    Q = dict(P)
    for k in ("munis", "uf", "regiao", "pop_media"):
        Q[k] = P[k][selecao]
    Q["X"], Q["OFF"] = P["X"][selecao], P["OFF"][selecao]
    Q["Y"] = {n: v[selecao] for n, v in P["Y"].items()}
    Q["M"] = int(Q["OFF"].shape[0])
    Q["tabela"] = None            # a de cima ficaria desalinhada; falhe alto
    return Q


def sem_anos(P: dict, fora: set[int]) -> dict:
    """Sub-painel sem os anos indicados, com as indicadoras de ano REFEITAS.

    POR QUE ISTO EXISTE
    --------------------
    O offset do painel e' a populacao municipal de `dim_populacao`, e essa serie
    troca de base em 2022: estimativas ate 2021, Censo em 2022, interpolacao em
    2023. A parte da troca que e' comum ao pais e' absorvida pelas indicadoras de
    ano; a parte que e' propria de cada municipio — e o Censo reviu municipios em
    direcoes diferentes — vira erro de medida no offset, e o efeito fixo nao a
    remove.

    Nao existe serie municipal harmonizada para reconstruir o denominador. O que
    da' para fazer e' medir o quanto o resultado depende dos anos afetados, e e'
    o que este recorte faz. Se o IRR nao se mover ao remove-los, a emenda do
    Censo nao explica o achado.

    Refazer as indicadoras e' obrigatorio: reaproveitar as do painel cheio
    deixaria colunas todas-zero para os anos removidos, e a matriz de desenho
    ficaria singular sem que nada acusasse.
    """
    fica = np.array([a not in fora for a in P["anos"]])
    if fica.sum() < 3:
        raise SystemExit(
            f"sobraram {int(fica.sum())} anos depois de remover {sorted(fora)}. "
            "Um painel de menos de tres anos nao sustenta efeito fixo com "
            "indicadora de ano.")
    anos = P["anos"][fica]
    M, T = P["M"], len(anos)

    colunas = [P["X"][:, fica, 0]]
    for a in anos[1:]:
        colunas.append(np.tile((anos == a).astype(float), (M, 1)))
    Q = dict(P)
    Q["anos"], Q["T"] = anos, T
    Q["X"] = np.stack(colunas, axis=2)
    Q["OFF"] = P["OFF"][:, fica]
    Q["Y"] = {n: v[:, fica] for n, v in P["Y"].items()}
    Q["tabela"] = None
    return Q


def irr(P: dict, causa: str, com_fe: bool = True) -> float:
    """Razao de taxas da ausencia de vigilancia, para uma causa."""
    Y, X, OFF = P["Y"][causa], P["X"], P["OFF"]
    if not com_fe:
        # um unico "municipio": equivale a Poisson comum com offset, o que
        # deixa o confundimento ENTRE municipios entrar. E' a comparacao do
        # criterio 2, nao uma alternativa defensavel.
        M, T, K = X.shape
        Y = Y.reshape(1, M * T)
        X = X.reshape(1, M * T, K)
        OFF = OFF.reshape(1, M * T)
    beta = ajustar_matriz(Y, X, OFF)
    return float(np.exp(beta[0])) if np.isfinite(beta[0]) else np.nan


def ic_municipio(P: dict, fn, reps: int = REPS) -> tuple[float, float, float]:
    """IC95% reamostrando MUNICIPIOS inteiros — linhas da matriz.

    O municipio sorteado duas vezes entra como duas linhas, que e' o que o
    bootstrap de cluster exige: os dois blocos sao independentes na reamostra,
    e na forma matricial isso sai de graca, sem identificador novo.
    """
    rng = np.random.default_rng(SEMENTE)
    vals = []
    for _ in range(reps):
        amostra = rng.integers(0, P["M"], size=P["M"])
        v = fn(_filtrar(P, amostra))
        if np.isfinite(v):
            vals.append(v)
    a = np.array(vals)
    return fn(P), float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))


# ── as tabelas ─────────────────────────────────────────────────────────────
def tab01_painel(P: dict) -> pd.DataFrame:
    d = P["tabela"]
    linhas = [("Municipios no painel", P["M"]),
              ("Anos de desfecho", P["T"]),
              ("Linhas municipio-ano", P["M"] * P["T"]),
              ("Pessoas-ano", int(P["OFF"].sum())),
              ("Municipio-ano sem vigilancia no ano anterior",
               int(P["X"][:, :, 0].sum()))]
    for nome in GRUPOS:
        linhas.append((f"Obitos: {nome}", int(P["Y"][nome].sum())))
    # A REPARTICAO EM TRES E' O DIAGNOSTICO DO DESENHO
    # -------------------------------------------------
    # O efeito fixo de municipio absorve todo confundidor constante no tempo, e
    # o preco e' que ele tambem absorve os municipios cuja exposicao nunca muda:
    # quem sempre vigiou e quem nunca vigiou nao contribuem para a estimativa.
    # Ela vem inteira dos que MUDARAM. Reportar os tres numeros e' o que permite
    # ao leitor julgar se um IRR proximo de 1 e' nulo informativo ou apenas
    # ausencia de variacao — e essa distincao nao se le no intervalo sozinho.
    sem_por_municipio = P["X"][:, :, 0].sum(axis=1)
    linhas.append(("Municipios com vigilancia em TODOS os anos",
                   int((sem_por_municipio == 0).sum())))
    linhas.append(("Municipios sem vigilancia em TODOS os anos",
                   int((sem_por_municipio == P["T"]).sum())))
    linhas.append(("Municipios que MUDARAM de estado no periodo",
                   int(((sem_por_municipio > 0)
                        & (sem_por_municipio < P["T"])).sum())))
    linhas.append(("Municipio-ano sem vigilancia no ano anterior (%)",
                   round(100 * float(P["X"][:, :, 0].mean()), 1)))
    # O CONJUNTO QUE DE FATO IDENTIFICA O EFEITO
    # -------------------------------------------
    # Municipio que muda de exposicao mas nao tem obito algum pela causa nao
    # contribui: a multinomial condicional dele e' degenerada e ele sai da
    # verossimilhanca. Reportar so os que mudam superestima a informacao
    # disponivel — uma auditoria externa apontou, e a recontagem confirmou.
    muda = ((sem_por_municipio > 0) & (sem_por_municipio < P["T"]))
    for nome in GRUPOS:
        tem = P["Y"][nome].sum(axis=1) > 0
        linhas.append((f"Municipios com algum obito: {nome}", int(tem.sum())))
        linhas.append((f"Municipios que mudam E tem obito: {nome}",
                       int((muda & tem).sum())))
    del d
    # dtype=object: a linha do percentual e' float e as outras sao contagens.
    # Sem isto o pandas promove a coluna inteira e o CSV sai com
    # "1880954497.0" onde ha 1.880.954.497 pessoas-ano.
    return pd.DataFrame({"Recorte": [k for k, _ in linhas],
                         "Valor": pd.Series([v for _, v in linhas],
                                            dtype=object)})


def tab02_especificidade(P: dict) -> pd.DataFrame:
    """CRITERIO 1. Cinco causas, o mesmo estimador, o mesmo painel."""
    linhas = []
    for nome in GRUPOS:
        v, lo, hi = ic_municipio(P, lambda p, n=nome: irr(p, n))
        linhas.append({"Grupo de causa": nome, "IRR": round(v, 3),
                       "IC95% inferior": round(lo, 3),
                       "IC95% superior": round(hi, 3),
                       "Exclui 1": "sim" if lo > 1 else "nao"})
        print(f"   {nome:<38} IRR {v:.3f} [{lo:.3f}, {hi:.3f}]", flush=True)
    return pd.DataFrame(linhas)


def tab03_efeito_fixo(P: dict) -> pd.DataFrame:
    """CRITERIO 2. O mesmo IRR com e sem efeito fixo de municipio.

    A RAZAO DE RAZOES ENTRA AQUI CALCULADA, E NAO NO TEXTO
    -------------------------------------------------------
    O desenho transversal deste artigo mediu a hipotese como razao de razoes
    contra o controle respiratorio. Para que as duas medidas sejam comparaveis,
    a RRR tem de ser calculada tambem no painel — e calculada AQUI, pela
    analise, nao no paragrafo. Nenhum numero da prosa deste projeto e' digitado:
    dividir 1,074 por 0,773 de cabeca e escrever o resultado seria exatamente o
    tipo de conta que ninguem confere depois.
    """
    controle = "J00-J22 respiratorias (subgrupo 1.2)"
    irrs = {nome: (irr(P, nome, False), irr(P, nome, True)) for nome in GRUPOS}
    base_sem, base_com = irrs[controle]

    linhas = []
    for nome, (sem, com) in irrs.items():
        linhas.append({"Grupo de causa": nome,
                       "IRR sem efeito fixo": round(sem, 3),
                       "IRR com efeito fixo": round(com, 3),
                       "Removido pelo efeito fixo": round(sem - com, 3),
                       "RRR contra o controle, sem efeito fixo":
                           round(sem / base_sem, 3),
                       "RRR contra o controle, com efeito fixo":
                           round(com / base_com, 3)})
        print(f"   {nome:<38} sem FE {sem:.3f} -> com FE {com:.3f}"
              f"   RRR {sem / base_sem:.3f} -> {com / base_com:.3f}", flush=True)
    return pd.DataFrame(linhas)


def tab04_tendencia(_: dict) -> pd.DataFrame:
    """CRITERIO 3. A tendencia 2015-2019 projetada, contra o observado.

    DOIS DENOMINADORES, E POR QUE NAO UM
    -------------------------------------
    A versao anterior media a mortalidade intestinal como PROPORCAO dos obitos
    do ano. Essa medida cancela sub-registro, mas tem um defeito que a pandemia
    expoe inteiro: em 2020 e 2021 a COVID-19 inflou o denominador, e a queda de
    27% e 40% que aparece ali nao e' queda de morte por diarreia — e' aumento
    de morte por outra coisa. Ler o excesso de 2024 contra uma serie que tem
    esse artefato no meio convida a atribuir ao desfecho o que e' do divisor.

    Por isso as duas series entram na tabela: por 10 mil obitos do ano e por
    milhao de habitantes. A primeira e' robusta a sub-registro e fragil a
    pandemia; a segunda, o contrario. Se as duas apontarem na mesma direcao em
    2024, a conclusao nao depende de qual denominador o leitor prefere — e se
    discordarem, a tabela mostra a discordancia em vez de a esconder.
    """
    m = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                        columns=["ano", "causabas_3", "obitos"])
    hid = (m[m.causabas_3.str.match(GRUPOS["A00-A09 intestinais (hipotese)"])]
           .groupby("ano").obitos.sum())
    tot = m.groupby("ano").obitos.sum()

    # O DENOMINADOR NACIONAL: QUAL SERIE, E COMO SABER QUE E' ELA
    # -------------------------------------------------------------
    # `dim_populacao` nao e' uma serie: a coluna `fonte` mostra estimativas
    # anuais ate 2021, o CENSO em 2022, interpolacao em 2023 e estimativas de
    # novo em 2024. A emenda produz queda de 4,80% de 2021 para 2022, que nao e'
    # demografia. Medir excesso contra tendencia sobre ela atribui ao desfecho o
    # que e' do divisor.
    #
    # A primeira tentativa de conserto trocou por `pop_idade_uf_ano.parquet` — e
    # ERROU: esse arquivo e' a projecao de 2018, PRE-Censo. O proprio
    # `pipeline_projecao_ibge.py` documenta isso em tabela, e `analise_neoplasias`
    # o rotula "Projecao rev. 2018 (anterior)". A serie oficial pos-Censo, que os
    # outros artigos usam, e' `pop_proj2024_uf_ano_idade.parquet`.
    #
    # POR QUE O ERRO PASSOU, E O QUE A GUARDA PRECISA CONFERIR
    # ---------------------------------------------------------
    # A guarda anterior verificava CONTINUIDADE — variacao anual abaixo de 2% —
    # e a projecao de 2018 e' perfeitamente continua, porque nunca foi tocada
    # pelo Censo. Suavidade foi lida como correcao. Continuidade nao distingue
    # duas series suaves de revisoes diferentes; so a PROCEDENCIA distingue, e e'
    # ela que passa a ser conferida, contra totais ancora publicados do IBGE.
    arq = REFS / "pop_proj2024_uf_ano_idade.parquet"
    if not arq.exists():
        raise SystemExit(
            f"{arq} nao existe. Rode `scripts/pipeline_projecao_ibge.py`. Nao "
            "substitua por `pop_idade_uf_ano.parquet`: aquele e' a projecao de "
            "2018, anterior ao Censo, e usa-lo aqui reporta excesso calculado "
            "sobre uma populacao que o pais nao tem.")
    proj = pd.read_parquet(arq, columns=["ano", "sexo", "populacao"])
    pop = proj[proj.sexo == "T"].groupby("ano").populacao.sum()
    anos = [a for a in range(2015, 2025) if a in pop.index]
    if len(anos) != 10:
        raise SystemExit(
            f"a projecao cobre {anos} de 2015 a 2024. A serie por habitante "
            "precisa dos dez anos; sem eles a projecao compara periodos "
            "diferentes sem nada acusar.")

    #: Totais nacionais publicados da Revisao 2024. Servem de impressao digital:
    #: a projecao de 2018 da' 214.828.540 em 2022, e o Censo bruto da'
    #: 203.080.756 — nenhum dos dois passa por aqui.
    ANCORAS = {2022: 210_862_983, 2024: 212_583_750}
    fora = {a: int(pop.loc[a]) for a, esperado in ANCORAS.items()
            if abs(int(pop.loc[a]) - esperado) > 1000}
    if fora:
        raise SystemExit(
            f"a serie populacional nao e' a Revisao 2024 do IBGE: {fora} contra "
            f"o esperado {ANCORAS}. Conferir a PROCEDENCIA, e nao so a forma da "
            "curva: a projecao de 2018 tambem e' suave, e foi aceita por uma "
            "guarda que so olhava continuidade.")

    variacao = pop.loc[anos].pct_change().dropna()
    saltos = {int(a): round(100 * v, 2) for a, v in variacao.items() if abs(v) > 0.02}
    if saltos:
        raise SystemExit(
            f"a serie populacional tem salto nao demografico em {saltos} (% ao "
            "ano). Populacao nacional nao muda mais de 2% em um ano: isto e' "
            "troca de base entre Censo e projecao.")

    por_obito = (1e4 * hid / tot).loc[2015:2024]
    por_hab = (1e6 * hid.loc[2015:2024] / pop.loc[anos])

    def _projetar(serie: pd.Series) -> np.ndarray:
        """Tendencia log-linear ajustada SO em 2015-2019, projetada ate 2024."""
        pre = serie.loc[2015:2019]
        coef = np.polyfit(pre.index.to_numpy(dtype=float),
                          np.log(pre.to_numpy()), 1)
        return np.exp(np.polyval(coef, np.arange(2015.0, 2025.0)))

    proj_obito, proj_hab = _projetar(por_obito), _projetar(por_hab)

    linhas = []
    for k, a in enumerate(range(2015, 2025)):
        o1, p1 = float(por_obito.loc[a]), float(proj_obito[k])
        o2, p2 = float(por_hab.loc[a]), float(proj_hab[k])
        linhas.append({
            "Ano": a,
            "Obitos por A00-A09": int(hid.loc[a]),
            "Observado por 10 mil obitos": round(o1, 2),
            "Projetado por 10 mil obitos": round(p1, 2),
            "Excesso relativo % (obitos)": round(100 * (o1 / p1 - 1), 1),
            "Observado por milhao de habitantes": round(o2, 2),
            "Projetado por milhao de habitantes": round(p2, 2),
            "Excesso relativo % (habitantes)": round(100 * (o2 / p2 - 1), 1),
            "Base do ajuste": "sim" if a <= 2019 else "nao"})
        print(f"   {a}: /obito {o1:5.2f} vs {p1:5.2f} "
              f"({100 * (o1 / p1 - 1):+6.1f}%)   "
              f"/hab {o2:5.2f} vs {p2:5.2f} "
              f"({100 * (o2 / p2 - 1):+6.1f}%)", flush=True)
    return pd.DataFrame(linhas)


def tab05_robustez(P: dict) -> pd.DataFrame:
    """CRITERIO 4. Exclusoes e regioes, sempre sobre a causa da hipotese."""
    causa = "A00-A09 intestinais (hipotese)"
    tudo = np.ones(P["M"], dtype=bool)
    recortes = [("Painel completo", tudo),
                ("Sem o Distrito Federal", P["uf"] != "DF"),
                ("Sem municipios com menos de 5.000 hab.",
                 P["pop_media"] >= POP_MINIMA),
                ("Sem o DF e sem municipios pequenos",
                 (P["uf"] != "DF") & (P["pop_media"] >= POP_MINIMA))]
    for reg in sorted({r for r in P["regiao"] if isinstance(r, str)}):
        recortes.append((f"Somente {reg}", P["regiao"] == reg))

    linhas = []
    for nome, mascara in recortes:
        if mascara.sum() < 30:
            continue
        sub = _filtrar(P, mascara)
        v, lo, hi = ic_municipio(sub, lambda p: irr(p, causa), reps=REPS)
        linhas.append({"Recorte": nome, "Municipios": int(mascara.sum()),
                       "IRR": round(v, 3), "IC95% inferior": round(lo, 3),
                       "IC95% superior": round(hi, 3)})
        print(f"   {nome:<40} IRR {v:.3f} [{lo:.3f}, {hi:.3f}]", flush=True)

    # O recorte por ANO, e nao por municipio: 2022 e' o ano do Censo e 2023 o da
    # interpolacao em `dim_populacao`, que e' o offset do modelo. Ver `sem_anos`.
    sub = sem_anos(P, {2022, 2023})
    v, lo, hi = ic_municipio(sub, lambda p: irr(p, causa), reps=REPS)
    linhas.append({"Recorte": "Sem 2022 e 2023 (troca de base populacional)",
                   "Municipios": int(P["M"]), "IRR": round(v, 3),
                   "IC95% inferior": round(lo, 3), "IC95% superior": round(hi, 3)})
    print(f"   {'Sem 2022 e 2023 (troca de base)':<40} IRR {v:.3f} "
          f"[{lo:.3f}, {hi:.3f}]", flush=True)
    return pd.DataFrame(linhas)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    SAIDA.mkdir(parents=True, exist_ok=True)
    P = empilhar(montar_painel())

    print("\n[criterio 1] especificidade entre cinco causas", flush=True)
    t02 = tab02_especificidade(P)
    print("\n[criterio 2] com e sem efeito fixo", flush=True)
    t03 = tab03_efeito_fixo(P)
    print("\n[criterio 3] tendencia pre-pandemia", flush=True)
    t04 = tab04_tendencia(P)
    print("\n[criterio 4] robustez", flush=True)
    t05 = tab05_robustez(P)

    for nome, t in (("tab01_painel", tab01_painel(P)),
                    ("tab02_especificidade", t02),
                    ("tab03_efeito_fixo", t03),
                    ("tab04_tendencia", t04),
                    ("tab05_robustez", t05)):
        t.to_csv(SAIDA / f"{nome}.csv", index=False, encoding="utf-8")
        print(f"   {nome}: {len(t)} linhas", flush=True)

    hip, outros = t02.iloc[0], t02.iloc[1:]
    print("\n[VEREDITO]")
    print(f"   IRR da hipotese ............ {hip['IRR']} "
          f"[{hip['IC95% inferior']}, {hip['IC95% superior']}]")
    print(f"   maior IRR entre controles .. {outros['IRR'].max()} "
          f"({outros.loc[outros['IRR'].idxmax(), 'Grupo de causa']})")
    if hip["IC95% inferior"] > 1 and hip["IRR"] > outros["IRR"].max():
        print("   criterio 1 APROVADO: o excesso e' especifico da causa hidrica.")
    else:
        print("   criterio 1 REPROVADO: a leitura e' fragilidade geral do")
        print("   sistema de saude, nao caminho hidrico. Vai reportado assim.")
    print(f"\n[ok] 5 tabelas em {SAIDA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
