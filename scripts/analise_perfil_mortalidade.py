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
from _achados import registrar  # noqa: E402
from _publicacao import carregar_env, conferir_chave_unica, escrever_parquet  # noqa: E402
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

#: k da discretização publicada. Não é "o número de grupos" — ver a seção 2 do
#: cabeçalho. É o maior k com ARI acima de 0,9 entre subamostras.
K_GRUPOS = 3
ARI_MINIMO = 0.90

SEMENTE = 7
N_SUBAMOSTRAS = 10

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
                            columns=["municipio_cod", "causabas_3", "obitos"])
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


def medir_estabilidade(escores: np.ndarray, k: int) -> tuple[float, float]:
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
    return float(np.mean(aris)), sil


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

    ari, sil = medir_estabilidade(escores, K_GRUPOS)
    print(f"[grupos] k={K_GRUPOS}: ARI entre subamostras {ari:.3f} | silhueta {sil:.3f}",
          flush=True)
    if ari < ARI_MINIMO:
        raise SystemExit(
            f"partição instável (ARI {ari:.3f} < {ARI_MINIMO}). Publicar rótulo de "
            "grupo que não se reproduz seria inventar tipologia.")
    veredito = ("contínuo estruturado — partição reprodutível, grupos não separados"
                if sil < 0.25 else "grupos separados")
    print(f"[grupos] leitura: {veredito}", flush=True)

    from sklearn.cluster import KMeans
    grupos = KMeans(K_GRUPOS, n_init=10, random_state=0).fit_predict(escores)

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
    registrar("perfil_ari_k3", ari, fontes=fontes,
              descricao=f"índice Rand ajustado entre partições de subamostras de 80% (k={K_GRUPOS})")
    registrar("perfil_silhueta_k3", sil, fontes=fontes,
              descricao=f"silhueta média da partição k={K_GRUPOS}; baixa com ARI alto indica "
                        "contínuo estruturado, não grupos discretos")
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
    recs = pares.astype(object).where(pd.notna(pares), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        r = requests.post(f"{url}/rest/v1/mart_correlacao_causas", headers=cab,
                          data=json.dumps(recs[i:i + 5000], allow_nan=False,
                                          default=lambda o: o.item() if hasattr(o, "item") else o),
                          timeout=300)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload: HTTP {r.status_code} {r.text[:200]}")
    print(f"[supabase]   mart_correlacao_causas: {len(recs):,} OK", flush=True)
    requests.post(f"{url}/rest/v1/meta_dataset", headers=cab, timeout=60,
                  data=json.dumps([{"chave": "gerado_em",
                                    "valor": datetime.now().isoformat(timespec="seconds")}]))
    print("[done] perfil de mortalidade concluído.", flush=True)


if __name__ == "__main__":
    main()
