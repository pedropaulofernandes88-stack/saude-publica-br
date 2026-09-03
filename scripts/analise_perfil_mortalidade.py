"""
analise_perfil_mortalidade.py — perfil de causas por município: eixos e grupos
==============================================================================

Análise não supervisionada sobre `mart_mortalidade_causa_municipio`: cada
município é um ponto, as coordenadas são a composição de causas de morte, e a
pergunta é se municípios se separam por "padrão de mortes".

Responde a duas perguntas de um desenho de artigo:

  1. municípios agrupam por perfil de causa? em quantos grupos?
  2. dentro de cada grupo, quais CIDs se movem juntos ao longo do tempo?

O QUE ESTA ANÁLISE ACHOU, EM UMA FRASE
--------------------------------------
Há estrutura real — seis eixos acima do ruído multinomial —, os municípios NÃO
se separam em grupos discretos, e o eixo principal é, em quase um terço,
**precisão de codificação**, não epidemiologia.

Os três resultados são independentes e cada um muda o que se pode publicar.

1. QUATRO CONFUNDIDORES SAEM ANTES DE QUALQUER COISA
----------------------------------------------------
Composição de causa responde a coisas que não são o que se quer estudar:

    log população     municípios grandes têm perfil diferente por serem grandes
    % 60 anos ou mais estrutura etária domina qualquer perfil de mortalidade
    % mal definidas   qualidade do registro, que varia 23x entre municípios
    fração de B34     COVID-19, o maior choque do período

POR QUE A IDADE ENTRA COMO COVARIÁVEL, E NÃO POR PADRONIZAÇÃO DIRETA
---------------------------------------------------------------------
`mart_mortalidade_causa_municipio_faixa` traz o grão etário, o que permitiria
padronizar a composição de causas por idade em vez de residualizar sobre o
percentual de 60 anos ou mais. Foi medido, e a padronização direta **não
substitui a covariável**:

    desenho                                    razão vs nulo   |r| com %60+
    bruta + %60+ como covariável (o adotado)        5,23x          0,000
    bruta, sem controle nenhum                      9,33x          0,710
    padronizada por idade, sem covariável           7,69x          0,602
    padronizada por idade + covariável              5,16x          0,001

A padronização parece reter mais sinal (7,69 contra 5,23), e é ilusão: o PC1
padronizado ainda correlaciona **0,602** com a estrutura etária. O ganho é
confundimento NÃO removido, não epidemiologia preservada. Padronizar a
composição pela distribuição etária dos ÓBITOS remove o efeito de quem morre,
mas não o de municípios envelhecidos terem perfil distinto dentro de cada faixa
— e a composição intra-faixa de um município jovem, com poucos óbitos em 75+, é
ela própria ruidosa.

Manter as duas (última linha) controla a idade tão bem quanto a covariável
sozinha e deixa o achado de codificação um pouco mais forte (0,576 contra
0,536), ao custo de um componente acima do nulo (5 em vez de 6). A diferença é
pequena e o desenho publicado continua sendo o da primeira linha; a linha 4 é o
caminho natural se o grão etário for incorporado.

Cada proporção de CID é regredida nessas quatro e o que sobra é analisado. Medido:
com os quatro controles, o PC1 cai de 6,3% para 3,3% da variância — quase metade
do "padrão de mortalidade" municipal era idade, porte, registro e pandemia.

**A estrutura sobrevive**: seis componentes ainda superam 2x o nulo multinomial.

2. NÃO HÁ GRUPOS DISCRETOS — HÁ UM CONTÍNUO ESTRUTURADO
--------------------------------------------------------
Duas medidas discordam de um jeito que só tem uma leitura:

    ARI entre subamostras (k=3)   0,94   a partição se REPRODUZ
    silhueta (k=3)                0,17   os grupos NÃO se separam

Partição reprodutível com silhueta baixa é a assinatura de um gradiente
contínuo: o mesmo corte reaparece porque a direção é real, não porque existam
ilhas. E a fração de soma de quadrados não explicada cai sem cotovelo de k=2 a
k=20 — não existe número natural de grupos.

Por isso o produto principal são as COORDENADAS (`pc1`…`pc6`), e o rótulo
`grupo` é publicado como discretização declarada, não como descoberta. Vender
os três grupos como tipologia de município seria afirmar uma separação que a
silhueta nega.

3. O EIXO PRINCIPAL É, EM PARTE, COMO SE CODIFICA
--------------------------------------------------
O polo negativo do PC1 é I64, I10, E14, V29; o positivo é C18, C34, C25, C43.
Lidos como doença, seriam "cerebrovascular e metabólico" contra "câncer". Lidos
pelo texto da CID, os quatro do lado negativo terminam em **NE — não
especificado** — e os quatro do positivo são diagnósticos precisos.

Construindo um índice de inespecificidade (fração dos óbitos em CIDs cuja
descrição traz NE, NCOP ou SOE, EXCLUÍDO o B34, que é COVID):

    correlação PC1 x inespecificidade      -0,54   (r² = 0,29)
    correlação %mal definidas x índice     +0,37

O indicador clássico de qualidade — % de causas mal definidas — capta só um
terço disso. Ele mede o balde do R99; o índice mede a granularidade de tudo o
mais. **São coisas diferentes, e a segunda não estava sendo controlada.**

Consequência prática: uma clusterização de mortalidade municipal brasileira
publicada sem esse controle descreveria, em boa parte, cultura de codificação
médica — e seria lida como epidemiologia.

4. CORRELAÇÃO ENTRE CAUSAS: O CONTEMPORÂNEO VALE, A DEFASAGEM NÃO
------------------------------------------------------------------
Séries mensais 2015–2024 (120 pontos), sem tendência e sem efeito de mês civil.

O controle positivo passa: o par de |r| mais alto de toda a matriz é
**A90 x A91 = +0,97** — dengue e dengue hemorrágica, que TÊM de andar juntas.
Aparecem também C34xC50, J44xJ43, G30xI69, e as correlações NEGATIVAS de B34
com I21 e N39, que é a substituição de causa durante a pandemia.

Já a correlação CRUZADA com defasagem não se sustenta. O histograma do lag de
pico se concentra em zero e nas BORDAS da janela (2.209 pares em -6 e 2.204 em
+6, contra ~1.200 nos lags intermediários). Pico na borda é assinatura de busca
sobreajustada, não de precedência. E os pares "revelados" pela defasagem são
clinicamente implausíveis — câncer de cólon precedendo câncer de ânus em cinco
meses. **Publicado como achado negativo**: com 120 pontos mensais agregados não
há como sustentar indicador antecedente entre causas.

Uso:
  .venv311/Scripts/python scripts/analise_perfil_mortalidade.py
  .venv311/Scripts/python scripts/analise_perfil_mortalidade.py --no-upload
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _achados import esquecer, registrar  # noqa: E402
from _publicacao import carregar_env, conferir_chave_unica, escrever_parquet  # noqa: E402
from _sim_obitos import ANOS_CONSOLIDADOS  # noqa: E402
from _supabase_key import chave_escrita  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
PRODUTOR = "scripts/analise_perfil_mortalidade.py"

#: Municípios com menos óbitos que isto no período têm perfil dominado por ruído
#: multinomial: a mediana nacional é de 77 óbitos por ano, e com 287 CIDs o
#: perfil de um município pequeno é quase todo zero-ou-um.
CORTE_OBITOS = 500

#: Componentes retidos: os que superam 2x o nulo. Medido, são 6.
FATOR_ACIMA_DO_NULO = 2.0
MAX_COMPONENTES = 20

#: Candidatos a k. NÃO se fixa um: varre-se, e o perfil inteiro de ARI por k é
#: o resultado — mais informativo que qualquer k escolhido.
#:
#: Por que deixou de ser fixo: com 2024 recoletado do `.dbc` (105.669 óbitos que
#: o CSV não trazia), o ARI de k=3 caiu de 0,934 para 0,887 e a guarda reprovou.
#: Baixar o limiar seria trocar uma trava real por conforto. Medindo o perfil
#: inteiro, apareceu o que importa:
#:
#:     k=2  ARI 0,957   k=3  0,887   k=4  0,917
#:     k=5  ARI 0,782   k=6  0,890   k=8  0,842
#:
#: A estabilidade NÃO É MONOTÔNICA em k — 3 reprova e 4 passa. Se houvesse
#: grupos reais, o ARI teria pico no k verdadeiro; em vez disso ele oscila, e um
#: único ano a mais de dado reordena o ranking. É a evidência mais forte do
#: contínuo que a análise inteira descreve, e ela só apareceu porque a guarda
#: reprovou em vez de ser afrouxada.
K_CANDIDATOS = (2, 3, 4, 5, 6, 8)
ARI_MINIMO = 0.90

SEMENTE = 7
#: Repetições do reamostrador. Eram 10, e 10 não bastava: o mesmo k=3 saía com
#: ARI 0,887 na análise e 0,918 no gerador de tabelas — os dois lados do limiar
#: de 0,90, só por causa da sequência de sorteios. Decidir estabilidade com um
#: estimador cuja incerteza atravessa o próprio ponto de corte é decidir no
#: ruído. Com 50, o desvio cai e passa a ser REPORTADO junto da média.
N_SUBAMOSTRAS = 50

#: Sufixos que a tabela da CID-10 usa para diagnóstico impreciso.
#: NE = não especificado · NCOP = não classificado em outra parte · SOE = sem
#: outra especificação.
MARCAS_INESPECIFICO = r"\b(NE|NCOP|SOE)\b"

#: B34 casa com o padrão ("Doenc p/virus de localiz NE") e NÃO é imprecisão: é
#: COVID-19. Deixá-lo dentro do índice mediria pandemia como se fosse
#: codificação frouxa. Sem ele o achado cai de r=-0,565 para -0,536: sobrevive.
FORA_DO_INDICE = {"B34"}

LAGS = range(-6, 7)

#: Rótulo do recorte nacional na tabela de pares. -1 e não NULL porque a coluna
#: entra na chave primária, e NULL em chave não identifica linha.
GRUPO_NACIONAL = -1

#: Termos removidos da série antes da correlação: intercepto, tendência e onze
#: indicadores de mês. Entram no ajuste dos graus de liberdade.
TERMOS_REMOVIDOS = 13


def so_consolidado(df: pd.DataFrame, o_que: str) -> pd.DataFrame:
    """Descarta anos preliminares, em voz alta.

    A base passou a cobrir 2025, que o DataSUS ainda não fechou. Ano preliminar
    tem a cauda incompleta, e cauda incompleta impõe um choque comum a todas as
    causas: no CSV de 2024, ela inflou os pares de causa significativos de 7.030
    para 20.234. Deixá-lo entrar em silêncio faria a análise do artigo mudar sem
    ninguém pedir.

    Filtrar calado seria quase tão ruim — quem lesse o resultado não saberia que
    havia dado disponível e descartado. Por isso o descarte é impresso.
    """
    fora = sorted(set(df.ano.unique()) - set(ANOS_CONSOLIDADOS))
    if fora:
        print(f"[recorte] {o_que}: descartando {fora} — anos preliminares, "
              f"a análise usa {ANOS_CONSOLIDADOS[0]}–{ANOS_CONSOLIDADOS[-1]}", flush=True)
    return df[df.ano.isin(ANOS_CONSOLIDADOS)]


# ---------------------------------------------------------------------------
# Matriz e confundidores
# ---------------------------------------------------------------------------

def carregar() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    """Devolve (composição, confundidores, índice de inespecificidade, contagens)."""
    dim = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    informativos = set(dim[dim.informativo].causabas_3)
    inespecificos = set(
        dim[dim.descricao.fillna("").str.contains(MARCAS_INESPECIFICO, regex=True)]
        .causabas_3) - FORA_DO_INDICE

    anual = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                            columns=["municipio_cod", "ano", "causabas_3", "obitos"])
    anual = so_consolidado(anual, "composição de causas")
    contagens = (anual[anual.causabas_3.isin(informativos)]
                 .pivot_table(index="municipio_cod", columns="causabas_3",
                              values="obitos", aggfunc="sum", fill_value=0))
    contagens = contagens[contagens.sum(axis=1) >= CORTE_OBITOS]
    composicao = contagens.div(contagens.sum(axis=1), axis=0)

    presentes = [c for c in composicao.columns if c in inespecificos]
    inespecificidade = composicao[presentes].sum(axis=1)

    pop = (pd.read_parquet(MARTS / "dim_populacao.parquet")
           .query("ano == 2022").set_index("municipio_cod").populacao)
    faixa = pd.read_parquet(MARTS / "dim_pop_faixa.parquet")
    idoso = (faixa[faixa.faixa_etaria.isin(["60-74", "75+"])]
             .groupby("municipio_cod").populacao.sum()
             / faixa.groupby("municipio_cod").populacao.sum())
    mal = (pd.read_parquet(MARTS / "mart_qualidade_registro_municipio.parquet")
           .set_index("municipio_cod").pct_mal_definidas)

    conf = pd.DataFrame({
        "log_pop": np.log10(pop.reindex(composicao.index).astype(float)),
        "pct_idoso": idoso.reindex(composicao.index),
        "pct_mal_definidas": mal.reindex(composicao.index),
        "share_covid": composicao.get("B34", 0.0),
    }).dropna()

    idx = conf.index
    return composicao.loc[idx], conf, inespecificidade.loc[idx], contagens.loc[idx]


def residualizar(valores: np.ndarray, conf: pd.DataFrame) -> np.ndarray:
    """Remove dos dados a parte explicada linearmente pelos confundidores."""
    desenho = np.column_stack([np.ones(len(conf)), conf.values])
    return valores - desenho @ np.linalg.lstsq(desenho, valores, rcond=None)[0]


def componentes(valores: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Escores, fração de variância e cargas, padronizando cada coluna antes."""
    centrado = valores - valores.mean(axis=0)
    desvio = centrado.std(axis=0)
    z = centrado[:, desvio > 0] / desvio[desvio > 0]
    z = z - z.mean(axis=0)
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    return u * s, s**2 / (s**2).sum(), vt


def _nulo(contagens: pd.DataFrame, conf: pd.DataFrame, semente: int) -> np.ndarray:
    """Composição simulada: cada município sorteia os SEUS óbitos do padrão nacional."""
    p_nacional = (contagens.sum(axis=0) / contagens.sum(axis=0).sum()).values
    rng = np.random.default_rng(semente)
    sim = np.vstack([rng.multinomial(n, p_nacional)
                     for n in contagens.sum(axis=1).values]).astype(float)
    return residualizar(sim / sim.sum(axis=1, keepdims=True), conf)


# ---------------------------------------------------------------------------
# 1. eixos e agrupamento
# ---------------------------------------------------------------------------

def escolher_componentes(resid: np.ndarray, contagens: pd.DataFrame,
                         conf: pd.DataFrame) -> tuple[int, np.ndarray, np.ndarray]:
    _, var_obs, cargas = componentes(resid)
    _, var_nulo, _ = componentes(_nulo(contagens, conf, SEMENTE))
    k = int((var_obs[:MAX_COMPONENTES]
             > FATOR_ACIMA_DO_NULO * var_nulo[:MAX_COMPONENTES]).sum())
    print(f"[eixos] componentes acima de {FATOR_ACIMA_DO_NULO}x o nulo: {k}", flush=True)
    print(f"[eixos] variância observada {np.round(var_obs[:8], 3)}", flush=True)
    print(f"[eixos] variância nula      {np.round(var_nulo[:8], 3)}", flush=True)
    if k < 1:
        raise SystemExit("nenhum componente supera o nulo — não há o que agrupar")
    return k, var_obs, cargas


def medir_estabilidade(escores: np.ndarray, k: int) -> tuple[float, float, float]:
    """ARI entre partições de duas subamostras, e silhueta da partição completa.

    As duas juntas é que informam. ARI alto sozinho não prova grupo: um
    gradiente contínuo produz o MESMO corte toda vez, e o ARI não distingue
    "corte reprodutível" de "grupo real". Quem distingue é a silhueta.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score

    rng = np.random.default_rng(SEMENTE)
    n = len(escores)
    aris = []
    for _ in range(N_SUBAMOSTRAS):
        i1 = rng.choice(n, int(0.8 * n), replace=False)
        i2 = rng.choice(n, int(0.8 * n), replace=False)
        r1 = dict(zip(i1, KMeans(k, n_init=10, random_state=0).fit_predict(escores[i1]),
                      strict=True))
        r2 = dict(zip(i2, KMeans(k, n_init=10, random_state=0).fit_predict(escores[i2]),
                      strict=True))
        comum = np.intersect1d(i1, i2)
        aris.append(adjusted_rand_score([r1[c] for c in comum], [r2[c] for c in comum]))
    rotulos = KMeans(k, n_init=10, random_state=0).fit_predict(escores)
    sil = float(silhouette_score(escores, rotulos, sample_size=2000, random_state=0))
    return float(np.mean(aris)), float(np.std(aris)), sil


# ---------------------------------------------------------------------------
# 2. correlação entre causas ao longo do tempo
# ---------------------------------------------------------------------------

def _sem_tendencia_nem_mes(serie: pd.DataFrame) -> np.ndarray:
    """Tira tendência linear e efeito de mês civil de cada coluna.

    Sem isso a correlação mede inverno, não causa: na série bruta 23,3% dos
    pares passam de |r| 0,5; depois disto, 10,8%.
    """
    meses = np.array([m for (_, m) in serie.index])
    desenho = np.column_stack(
        [np.ones(len(serie)), np.arange(len(serie))]
        + [(meses == k).astype(float) for k in range(2, 13)])
    y = serie.values.astype(float)
    return y - desenho @ np.linalg.lstsq(desenho, y, rcond=None)[0]


def _bh(p: np.ndarray, q: float = 0.01) -> np.ndarray:
    """Benjamini-Hochberg: índices que sobrevivem ao controle de FDR."""
    ordem = np.argsort(p)
    limite = p[ordem] <= q * (np.arange(1, len(p) + 1) / len(p))
    if not limite.any():
        return np.array([], dtype=int)
    return ordem[:int(np.max(np.where(limite)[0]) + 1)]


def diferenca_entre_grupos(pares: pd.DataFrame, grupos: list[int]) -> dict:
    """Pares cuja correlação difere entre dois grupos, por teste z de Fisher.

    Compara as correlações do MESMO par em dois recortes independentes de
    municípios. Como as duas séries têm o mesmo comprimento, o erro padrão da
    diferença de z é sqrt(2/(n-3)).

    É o que transforma "quais CIDs se correlacionam em cada grupo" em pergunta
    respondível: a lista por grupo, sozinha, é longa demais para interpretar —
    o que informa é onde os grupos DISCORDAM.
    """
    from math import erfc

    n = 120 - TERMOS_REMOVIDOS - 1
    chave = ["cid_a", "cid_b"]
    saida: dict[tuple[int, int], int] = {}
    for i, a in enumerate(grupos):
        for b in grupos[i + 1:]:
            ja = pares[pares.grupo == a].set_index(chave).r
            jb = pares[pares.grupo == b].set_index(chave).r
            comuns = ja.index.intersection(jb.index)
            d = (np.arctanh(np.clip(ja.loc[comuns].values, -0.999, 0.999))
                 - np.arctanh(np.clip(jb.loc[comuns].values, -0.999, 0.999)))
            z = d / np.sqrt(2 / (n - 3))
            p = np.array([erfc(abs(v) / np.sqrt(2)) for v in z])
            saida[(a, b)] = len(_bh(p))
    return saida


def correlacao_entre_causas(cids: list[str],
                            municipios: set[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Correlação contemporânea (com FDR) e o diagnóstico da versão defasada.

    `municipios` restringe a série a um subconjunto — é o que responde à pergunta
    "em cada grupo de municípios, quais CIDs estão correlacionados?". Sem ele, a
    série é nacional.
    """
    from math import erfc

    colunas = ["ano", "mes", "causabas_3", "obitos"]
    if municipios is not None:
        colunas.insert(0, "municipio_cod")
    mensal = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio_mes.parquet",
                             columns=colunas)
    mensal = so_consolidado(mensal, "séries mensais")
    if municipios is not None:
        mensal = mensal[mensal.municipio_cod.isin(municipios)]
    serie = (mensal[mensal.causabas_3.isin(set(cids))]
             .groupby(["ano", "mes", "causabas_3"]).obitos.sum()
             .unstack(fill_value=0).sort_index())
    serie = serie.loc[:, serie.std() > 0]
    cids = [c for c in cids if c in serie.columns]
    resid = _sem_tendencia_nem_mes(serie[cids])
    z = (resid - resid.mean(axis=0)) / resid.std(axis=0)
    n = len(z)
    corr = (z.T @ z) / n
    iu = np.triu_indices(len(cids), 1)
    r = corr[iu]

    gl = n - TERMOS_REMOVIDOS - 1     # intercepto + tendência + 11 meses
    est = np.arctanh(np.clip(r, -0.999, 0.999)) * np.sqrt(gl - 3)
    p = np.array([erfc(abs(v) / np.sqrt(2)) for v in est])
    sig = _bh(p)

    pares = pd.DataFrame({
        "cid_a": [cids[i] for i in iu[0]], "cid_b": [cids[j] for j in iu[1]],
        "r": r, "p": p,
    })
    pares["significativo"] = False
    pares.loc[sig, "significativo"] = True

    # Diagnóstico da defasagem: onde cai o pico de |r| na janela de lags.
    picos = []
    for i, j in zip(iu[0], iu[1], strict=True):
        rs = []
        for lag in LAGS:
            a, b = ((z[lag:, i], z[:n - lag, j]) if lag >= 0
                    else (z[:n + lag, i], z[-lag:, j]))
            rs.append(float(np.corrcoef(a, b)[0, 1]))
        picos.append(list(LAGS)[int(np.argmax(np.abs(rs)))])
    hist = pd.Series(picos).value_counts().sort_index()
    bordas = int(hist.get(min(LAGS), 0) + hist.get(max(LAGS), 0))
    meio = float(hist.reindex([lag for lag in LAGS if lag not in (0, min(LAGS), max(LAGS))],
                              fill_value=0).mean())
    return pares, {"lag_hist": hist.to_dict(), "bordas": bordas, "meio_medio": meio}


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    composicao, conf, inespecificidade, contagens = carregar()
    print(f"[base] {composicao.shape[0]:,} municípios × {composicao.shape[1]} CIDs "
          f"(>={CORTE_OBITOS} óbitos em 2015–2024)", flush=True)

    resid = residualizar(composicao.values, conf)
    k, var_obs, cargas = escolher_componentes(resid, contagens, conf)
    escores, _, cargas = componentes(resid)
    escores = escores[:, :k]

    perfil = {kk: medir_estabilidade(escores, kk) for kk in K_CANDIDATOS}
    for kk, (ari, dp, sil) in perfil.items():
        marca = "estável" if ari >= ARI_MINIMO else "instável"
        ambiguo = abs(ari - ARI_MINIMO) < dp
        print(f"[grupos] k={kk}: ARI {ari:.3f} ± {dp:.3f} | silhueta {sil:.3f}  {marca}"
              + ("  (o desvio cruza o limiar — decisão no ruído)" if ambiguo else ""),
              flush=True)

    estaveis = {kk: v for kk, v in perfil.items() if v[0] >= ARI_MINIMO}
    if not estaveis:
        raise SystemExit(
            f"nenhum k entre {K_CANDIDATOS} tem ARI >= {ARI_MINIMO}. Publicar rótulo "
            "de grupo que não se reproduz seria inventar tipologia.")
    k_grupos = max(estaveis, key=lambda kk: estaveis[kk][0])
    ari, dp_ari, sil = estaveis[k_grupos]

    # A não monotonia é o achado, não um detalhe da varredura.
    ordem = [kk for kk in K_CANDIDATOS]
    monotonico = all(perfil[a][0] >= perfil[b][0] for a, b in zip(ordem, ordem[1:], strict=False))
    print(f"[grupos] k publicado: {k_grupos} (ARI {ari:.3f}, o mais estável)", flush=True)
    print(f"[grupos] ARI é monotônico em k? {'sim' if monotonico else 'NÃO — oscila, e é '           'isso que distingue contínuo de grupos reais'}", flush=True)
    veredito = ("contínuo estruturado — partição reprodutível, grupos não separados"
                if sil < 0.25 else "grupos separados")
    print(f"[grupos] leitura: {veredito}", flush=True)

    from sklearn.cluster import KMeans
    grupos = KMeans(k_grupos, n_init=10, random_state=0).fit_predict(escores)

    r_inesp = float(np.corrcoef(escores[:, 0], inespecificidade.values)[0, 1])
    r_mal = float(np.corrcoef(conf.pct_mal_definidas.values, inespecificidade.values)[0, 1])
    print(f"[codificação] PC1 × inespecificidade r={r_inesp:+.3f} (r²={r_inesp**2:.3f}) | "
          f"%mal definidas × inespecificidade r={r_mal:+.3f}", flush=True)

    pares, diag = correlacao_entre_causas(list(composicao.columns))
    pares["grupo"] = GRUPO_NACIONAL
    n_sig = int(pares.significativo.sum())
    print(f"[correlação] {len(pares):,} pares | {n_sig:,} significativos com FDR 1%",
          flush=True)
    topo = pares[pares.significativo].reindex(
        pares[pares.significativo].r.abs().sort_values(ascending=False).index).head(3)
    for _, x in topo.iterrows():
        print(f"[correlação]   r={x.r:+.2f}  {x.cid_a} × {x.cid_b}", flush=True)
    print(f"[defasagem] pico nas bordas da janela: {diag['bordas']} pares, contra "
          f"{diag['meio_medio']:.0f} por lag intermediário — busca sobreajustada",
          flush=True)

    # A pergunta original era "EM CADA GRUPO de municípios, quais CIDs estão
    # correlacionados?". A resposta nacional não a responde — e a diferença
    # entre os grupos acaba sendo o resultado mais informativo.
    por_grupo = [pares]
    for g in sorted(set(grupos)):
        do_grupo = set(composicao.index[grupos == g])
        p_g, _ = correlacao_entre_causas(list(composicao.columns), municipios=do_grupo)
        p_g["grupo"] = int(g)
        por_grupo.append(p_g)
        print(f"[correlação] grupo {g} ({len(do_grupo):,} municípios): "
              f"{int(p_g.significativo.sum()):,} pares significativos", flush=True)
    pares = pd.concat(por_grupo, ignore_index=True)

    diferencas = diferenca_entre_grupos(pares, sorted(set(int(g) for g in grupos)))
    for (a, b), n_dif in diferencas.items():
        print(f"[correlação] grupo {a} × {b}: {n_dif:,} pares com correlação diferente",
              flush=True)

    mun = pd.read_parquet(MARTS / "dim_municipio.parquet").set_index("municipio_cod")
    saida = pd.DataFrame({
        "municipio_cod": composicao.index,
        "municipio_nome": (mun.municipio_nome.reindex(composicao.index)
                           .fillna("Não identificado").values),
        "uf_sigla": mun.uf_sigla.reindex(composicao.index).fillna("ND").values,
        "regiao": mun.regiao.reindex(composicao.index).fillna("ND").values,
        "obitos_periodo": contagens.sum(axis=1).values.astype(int),
        "grupo": grupos.astype(int),
        "indice_inespecificidade": inespecificidade.values.round(4),
    })
    for i in range(k):
        saida[f"pc{i + 1}"] = escores[:, i].round(4)
    conferir_chave_unica("mart_perfil_mortalidade_municipio", saida, ["municipio_cod"])

    escrever_parquet(saida, MARTS / "mart_perfil_mortalidade_municipio.parquet",
                     origem="pipeline", produtor=PRODUTOR)
    print(f"[parquet] mart_perfil_mortalidade_municipio: {len(saida):,} linhas", flush=True)

    # A matriz de pares é a resposta à segunda pergunta do desenho e vale como
    # tabela publicada: 41 mil pares com r, p e a marca de FDR permitem refazer
    # qualquer recorte sem reprocessar os 7,7 milhões de células mensais.
    pares = pares.sort_values("p").reset_index(drop=True)
    pares["r"] = pares.r.round(4)
    conferir_chave_unica("mart_correlacao_causas", pares, ["grupo", "cid_a", "cid_b"])
    escrever_parquet(pares, MARTS / "mart_correlacao_causas.parquet",
                     origem="pipeline", produtor=PRODUTOR)
    print(f"[parquet] mart_correlacao_causas: {len(pares):,} pares", flush=True)

    fontes = ["mart_mortalidade_causa_municipio", "mart_mortalidade_causa_municipio_mes"]
    registrar("perfil_componentes_acima_do_nulo", k, fontes=fontes,
              descricao="componentes da composição de causas que superam 2x o nulo multinomial, "
                        "após remover porte, estrutura etária, qualidade do registro e COVID")
    # Chaves de quando o k era fixo em 3. Renomear um achado deixa órfão, e
    # órfão sobrevive porque `registrar` só escreve.
    esquecer("perfil_ari_k3_fixo", "perfil_silhueta_k3")
    registrar("perfil_k_publicado", k_grupos, fontes=fontes,
              descricao="k da discretização publicada: o mais estável entre os candidatos, "
                        "não um número de grupos descoberto")
    registrar("perfil_ari_desvio", dp_ari, fontes=fontes,
              descricao="desvio do ARI entre repetições do reamostrador; se ele cruza o "
                        "limiar de estabilidade, a escolha de k está sendo feita no ruído")
    registrar("perfil_ari", ari, fontes=fontes,
              descricao=f"índice Rand ajustado entre subamostras de 80% no k publicado ({k_grupos})")
    registrar("perfil_silhueta", sil, fontes=fontes,
              descricao=f"silhueta média no k publicado ({k_grupos}); baixa com ARI alto indica "
                        "contínuo estruturado, não grupos discretos")
    for kk, (a, _dp, _sl) in perfil.items():
        registrar(f"perfil_ari_k{kk}", a, fontes=fontes,
                  descricao=f"índice Rand ajustado para k={kk}; o perfil inteiro é o resultado, "
                            "e sua não monotonia é a evidência do contínuo")
    registrar("perfil_pc1_inespecificidade", r_inesp, fontes=fontes,
              descricao="correlação do PC1 com a fração de óbitos em CID inespecífico "
                        "(NE/NCOP/SOE, sem B34), já controlados os quatro confundidores")
    registrar("perfil_mal_definidas_inespecificidade", r_mal, fontes=fontes,
              descricao="correlação entre o indicador clássico de causas mal definidas e o "
                        "índice de inespecificidade — mede o quanto o clássico NÃO cobre")

    if args.no_upload:
        return
    env = carregar_env()
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    cab = {"apikey": key, "Authorization": f"Bearer {key}",
           "Content-Type": "application/json",
           "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = saida.astype(object).where(pd.notna(saida), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        r = requests.post(f"{url}/rest/v1/mart_perfil_mortalidade_municipio", headers=cab,
                          data=json.dumps(recs[i:i + 5000], allow_nan=False,
                                          default=lambda o: o.item() if hasattr(o, "item") else o),
                          timeout=300)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload: HTTP {r.status_code} {r.text[:200]}")
    print(f"[supabase]   mart_perfil_mortalidade_municipio: {len(recs):,} OK", flush=True)
    # `mart_correlacao_causas` NÃO sobe: está em NAO_SERVIDAS (_publicacao.py).
    # A tabela foi retirada do Postgres deliberadamente — 21 MB e zero buscas no
    # índice desde que existia, e o único consumidor (artigo/gerar_tabelas.py) lê
    # o Parquet. Este bloco de upload ficou para trás naquela remoção e passou a
    # falhar com PGRST205 ("could not find the table").
    #
    # Em 2026-09-03 eu li esse 404 como tabela faltando e a RECRIEI, desfazendo
    # a decisão que está documentada dez linhas acima da lista. Erro instrutivo:
    # um 404 pode significar "falta criar" ou "não deve existir", e as duas
    # coisas são indistinguíveis olhando só a mensagem. Quem decide é a lista.
    requests.post(f"{url}/rest/v1/meta_dataset", headers=cab, timeout=60,
                  data=json.dumps([{"chave": "gerado_em",
                                    "valor": datetime.now().isoformat(timespec="seconds")}]))
    print("[done] perfil de mortalidade concluído.", flush=True)


if __name__ == "__main__":
    main()
