"""
gerar_tabelas.py — as tabelas do manuscrito, calculadas a partir dos marts
==========================================================================

Nenhum número do artigo é digitado. Cada tabela sai daqui, dos Parquet
publicados com SHA-256 no manifesto, e é regravada em CSV toda vez que este
script roda. Um número no texto que não exista em `artigo/tabelas/` é um número
sem procedência — e foi exatamente esse o defeito que `_achados.py` existe para
impedir no site.

As tabelas 2 e 4 refazem cálculos que só existiam dentro de
`analise_perfil_mortalidade.py` (variância contra o nulo por componente,
estabilidade por k). Refazê-los aqui é deliberado: quem revisar o artigo tem de
poder reproduzir a tabela sem executar o pipeline inteiro.

Uso:
  .venv311/Scripts/python artigo/gerar_tabelas.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
SAIDA = Path(__file__).resolve().parent / "tabelas"
sys.path.insert(0, str(ROOT / "scripts"))

from _sim_obitos import ANOS_CSV  # noqa: E402
from analise_perfil_mortalidade import (  # noqa: E402
    CORTE_OBITOS,
    SEMENTE,
    _nulo,
    carregar,
    componentes,
    medir_estabilidade,
    residualizar,
)

KS = [2, 3, 4, 5, 6, 8, 10, 12]


def _grava(df: pd.DataFrame, nome: str, titulo: str) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA / f"{nome}.csv", index=False, encoding="utf-8-sig")
    print(f"[tabela] {nome}: {len(df)} linhas — {titulo}", flush=True)


def _faixa(anos: list[int]) -> str:
    """Lista de anos em faixas: [2015..2021, 2024] -> "2015–2021 e 2024"."""
    if not anos:
        return "nenhum ano"
    blocos, ini, ant = [], anos[0], anos[0]
    for a in anos[1:] + [None]:
        if a is not None and a == ant + 1:
            ant = a
            continue
        blocos.append(str(ini) if ini == ant else f"{ini}–{ant}")
        if a is not None:
            ini = ant = a
    return " e ".join(blocos) if len(blocos) < 3 else ", ".join(blocos[:-1]) + f" e {blocos[-1]}"


#: Abreviaturas do dicionário CID-10 do DataSUS. O arquivo oficial abrevia para
#: caber em campo de tamanho fixo — "Outr transt do trato urinario" —, e essa
#: forma é ilegível numa tabela de artigo. A expansão é textual e conservadora:
#: só troca token inteiro, nunca parte de palavra, e o que não estiver aqui
#: passa como veio.
ABREVIATURAS = {
    "Outr": "Outros", "outr": "outros", "transt": "transtornos",
    "Doenc": "Doença", "doenc": "doenças", "infecc": "infecções",
    "Neopl": "Neoplasia", "malig": "maligna",
    # NE, NCOP e SOE ficam como estão. Expandi-las exigiria concordar com o
    # substantivo — "Pneumonia bacteriana não classificadOS em outra parte" foi
    # o que a expansão produziu —, e concordância depende do núcleo do sintagma,
    # que não se resolve por dicionário. São siglas padrão da CID-10 e o artigo
    # as define na §3.5; mantê-las é mais correto que expandi-las errado.
    "dev": "devida a", "p/": "por", "c/": "com", "s/": "sem",
    "Insuf": "Insuficiência", "respirat": "respiratórios", "cronicas": "crônicas",
    "cronica": "crônica", "coracao": "coração", "cerebr": "cerebral",
    "Acid": "Acidente", "vasc": "vascular", "traum": "traumatizado",
    "acid": "acidente", "transp": "transporte", "localiz": "localização",
    "subcutaneo": "subcutâneo", "Agressao": "Agressão", "hemorragica": "hemorrágica",
    "virus": "vírus", "urinario": "urinário", "essencial": "essencial",
    "bacter": "bacteriana", "septicemias": "septicemias", "quedas": "quedas",
    "nivel": "nível", "isquemica": "isquêmica", "cardiaca": "cardíaca",
    "hipertensiva": "hipertensiva", "Hipertensao": "Hipertensão",
    "microorg": "microorganismo", "obstrutivas": "obstrutivas",
    "pulmonares": "pulmonares", "Embolia": "Embolia", "disseccao": "dissecção",
    "Sequelas": "Sequelas", "cerebrovasculares": "cerebrovasculares",
    "comport": "comportamentais", "alcool": "álcool", "Demencia": "Demência",
    "nao-insulino-dependemte": "não insulino-dependente",
    "nao-insulino-dependente": "não insulino-dependente",
    "Infarto": "Infarto", "Enfisema": "Enfisema", "Pneumonia": "Pneumonia",
}


#: Palavras femininas que seguem "Outr" no dicionário do DataSUS. A abreviatura
#: não marca gênero, e expandi-la sempre como "Outros" produzia "Outros
#: septicemias" numa tabela do artigo. A lista sai da varredura das 27 palavras
#: que de fato aparecem depois de "Outr" entre as categorias informativas — é
#: fechada e verificável, não uma heurística de terminação que erraria em
#: "afeccoes" e acertaria em "anemias" por acaso.
FEMININAS_APOS_OUTR = {
    "afeccoes", "anemias", "arma", "arritmias", "doenc", "embolia",
    "estruturas", "form", "gastroenterites", "hemorragias", "infecc",
    "malformacoes", "neopl", "partes", "quedas", "septicemias",
}


def rotulo_cid(bruto: str | None, cid: str) -> str:
    """Descrição da CID legível para uma tabela de artigo.

    Devolve o `cid` quando não há descrição — nunca string vazia, que numa
    tabela vira célula muda.
    """
    if not bruto:
        return cid
    texto = bruto.split("   ")[-1].strip()
    # As barras vêm COLADAS na palavra seguinte ("p/virus", "dev/"), e sem
    # separá-las o tokenizador nunca vê a abreviatura. Foi assim que
    # "Doenc p/virus" virou "Doença p/virus" em vez de "Doença por vírus".
    for sigla, palavra in (("p/", "por "), ("c/", "com "), ("s/", "sem ")):
        texto = texto.replace(sigla, palavra)
    tokens = texto.split()
    fora = []
    for i, t in enumerate(tokens):
        if t in ("Outr", "outr"):
            seguinte = tokens[i + 1] if i + 1 < len(tokens) else ""
            fem = seguinte in FEMININAS_APOS_OUTR
            base = "utras" if fem else "utros"
            fora.append(("O" if t[0] == "O" else "o") + base)
            continue
        fora.append(ABREVIATURAS.get(t, t))
    return " ".join(fora)


def tabela_1_base() -> pd.DataFrame:
    man = pd.read_json(ROOT / "data" / "publicacoes" / "atual.json", typ="series")
    pub = pd.read_json(ROOT / "data" / "publicacoes" / f"{man['id']}.json")
    anual = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                            columns=["municipio_cod", "ano", "causabas_3", "obitos"])
    mensal = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio_mes.parquet",
                             columns=["obitos"])
    dim = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    por_mun_ano = anual.groupby(["municipio_cod", "ano"]).obitos.sum()
    linhas = [
        # A fonte sai de ANOS_CSV, não de string escrita à mão: foi assim que a
        # tabela seguiu anunciando "CSV 2022–2024" depois de 2024 migrar para o
        # .dbc. Número copiado envelhece; texto copiado também.
        ("Fonte", f"SIM/DataSUS (CSV OpenDataSUS {_faixa(sorted(ANOS_CSV))}; .dbc por UF {_faixa(sorted(set(range(2015, 2025)) - ANOS_CSV))})"),
        ("Período", f"{int(anual.ano.min())}–{int(anual.ano.max())}"),
        ("Óbitos não fetais", f"{int(anual.obitos.sum()):,}".replace(",", ".")),
        ("Municípios", f"{anual.municipio_cod.nunique():,}".replace(",", ".")),
        ("Categorias da CID-10 (3 caracteres)", f"{dim.shape[0]:,}".replace(",", ".")),
        ("Células município × CID × ano", f"{len(anual):,}".replace(",", ".")),
        ("Células município × CID × ano × mês", f"{len(mensal):,}".replace(",", ".")),
        ("Óbitos por município-ano (mediana)", f"{int(por_mun_ano.median())}"),
        ("Óbitos por município-ano (P25–P75)",
         f"{int(por_mun_ano.quantile(.25))}–{int(por_mun_ano.quantile(.75))}"),
        ("CIDs informativos (não mal definidos, ≥25% dos municípios)",
         f"{int(dim.informativo.sum())}"),
        ("Municípios analisados (≥500 óbitos no período)", None),
        ("Publicação", f"{man['id']} · {pub['resumo']['n_tabelas']} tabelas"),
    ]
    contagens = (anual[anual.causabas_3.isin(set(dim[dim.informativo].causabas_3))]
                 .groupby("municipio_cod").obitos.sum())
    linhas[10] = ("Municípios analisados (≥500 óbitos no período)",
                  f"{int((contagens >= CORTE_OBITOS).sum()):,}".replace(",", "."))
    return pd.DataFrame(linhas, columns=["Item", "Valor"])


def tabela_2_covid() -> pd.DataFrame:
    anual = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                            columns=["ano", "causabas_3", "obitos"])
    tot = anual.groupby("ano").obitos.sum()
    b34 = anual[anual.causabas_3 == "B34"].groupby("ano").obitos.sum()
    u07 = anual[anual.causabas_3.str.startswith("U0")].groupby("ano").obitos.sum()
    df = pd.DataFrame({
        "Ano": tot.index,
        "B34 (óbitos)": b34.reindex(tot.index).fillna(0).astype(int).values,
        "U07 (óbitos)": u07.reindex(tot.index).fillna(0).astype(int).values,
        "Total de óbitos": tot.values,
    })
    df["B34 (% do total)"] = (100 * df["B34 (óbitos)"] / df["Total de óbitos"]).round(2)
    return df


def tabela_3_variancia(comp, conf, contagens) -> pd.DataFrame:
    _, var_bruto, _ = componentes(comp.values)
    resid = residualizar(comp.values, conf)
    _, var_resid, _ = componentes(resid)
    _, var_nulo, _ = componentes(_nulo(contagens, conf, SEMENTE))
    k = 8
    return pd.DataFrame({
        "Componente": [f"PC{i + 1}" for i in range(k)],
        "Variância — bruto (%)": (100 * var_bruto[:k]).round(2),
        "Variância — residualizado (%)": (100 * var_resid[:k]).round(2),
        "Variância — nulo multinomial (%)": (100 * var_nulo[:k]).round(2),
        "Razão residualizado/nulo": (var_resid[:k] / var_nulo[:k]).round(2),
    })


def tabela_3b_grao(comp, conf, contagens) -> pd.DataFrame:
    """Categoria contra capítulo, no MESMO desenho residualizado.

    A comparação só é honesta se as duas passarem pelos mesmos quatro controles
    e pelo mesmo nulo. Feita de outro jeito — bruto contra residualizado — ela
    exagera a favor da categoria.
    """
    anual = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                            columns=["municipio_cod", "capitulo_cid", "obitos"])
    cap = anual.pivot_table(index="municipio_cod", columns="capitulo_cid",
                            values="obitos", aggfunc="sum", fill_value=0)
    cap = cap.loc[cap.index.intersection(comp.index)]
    conf_cap = conf.loc[cap.index]

    linhas = []
    for rotulo, matriz, conta, cfd in (
            ("Categoria (3 caracteres)", comp, contagens, conf),
            ("Capítulo", cap.div(cap.sum(axis=1), axis=0), cap, conf_cap)):
        _, obs, _ = componentes(residualizar(matriz.values, cfd))
        _, nulo, _ = componentes(_nulo(conta, cfd, SEMENTE))
        k = min(len(obs), len(nulo), 20)
        linhas.append({
            "Grão": rotulo,
            "Categorias": matriz.shape[1],
            "PC1 observado (%)": round(100 * float(obs[0]), 2),
            "PC1 nulo (%)": round(100 * float(nulo[0]), 2),
            "Razão PC1": round(float(obs[0] / nulo[0]), 2),
            "Componentes acima de 2x": int((obs[:k] > 2 * nulo[:k]).sum()),
        })
    return pd.DataFrame(linhas)


def tabela_4_cargas(comp, conf) -> pd.DataFrame:
    resid = residualizar(comp.values, conf)
    _, _, cargas = componentes(resid)
    desvio = (resid - resid.mean(axis=0)).std(axis=0)
    cols = comp.columns[desvio > 0]
    dim = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    descricao = dim.set_index("causabas_3").descricao.to_dict()
    inesp = set(dim[dim.descricao.fillna("").str.contains(r"\b(?:NE|NCOP|SOE)\b", regex=True)]
                .causabas_3) - {"B34"}

    linhas = []
    for i in range(3):
        serie = pd.Series(cargas[i], index=cols).sort_values()
        for polo, itens in (("negativo", serie.index[:6]), ("positivo", serie.index[-6:][::-1])):
            for cid in itens:
                linhas.append({
                    "Componente": f"PC{i + 1}", "Polo": polo, "CID": cid,
                    "Descrição": rotulo_cid(descricao.get(cid), cid),
                    "Carga": round(float(serie[cid]), 3),
                    "Inespecífico": "sim" if cid in inesp else "não",
                })
    return pd.DataFrame(linhas)


def tabela_5_agrupamento(comp, conf, contagens, k_comp: int) -> pd.DataFrame:
    from sklearn.cluster import KMeans

    escores = componentes(residualizar(comp.values, conf))[0][:, :k_comp]
    nulo = componentes(_nulo(contagens, conf, SEMENTE))[0][:, :k_comp]

    def fracao_sq(x, k):
        km = KMeans(k, n_init=10, random_state=0).fit(x)
        return float(km.inertia_ / ((x - x.mean(0)) ** 2).sum())

    linhas = []
    for k in KS:
        # IMPORTA de analise_perfil_mortalidade em vez de reimplementar. A cópia
        # que morava aqui usava a mesma semente mas outra SEQUÊNCIA de sorteios,
        # e por isso dava ARI 0,918 para k=3 onde a análise dava 0,887 — os dois
        # lados do limiar de decisão. Duas implementações da mesma estatística
        # não divergem só em teoria.
        ari, dp, sil = medir_estabilidade(escores, k)
        linhas.append({
            "k": k,
            "ARI entre subamostras": round(ari, 3),
            "Desvio do ARI": round(dp, 3),
            "Silhueta": round(sil, 3),
            "SQ não explicada — observado": round(fracao_sq(escores, k), 4),
            "SQ não explicada — nulo": round(fracao_sq(nulo, k), 4),
        })
    df = pd.DataFrame(linhas)
    df["Razão obs/nulo"] = (df["SQ não explicada — observado"]
                            / df["SQ não explicada — nulo"]).round(3)
    return df


def tabela_6_grupos() -> pd.DataFrame:
    perfil = pd.read_parquet(MARTS / "mart_perfil_mortalidade_municipio.parquet")
    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet").set_index("municipio_cod")
    qual = (pd.read_parquet(MARTS / "mart_qualidade_registro_municipio.parquet")
            .set_index("municipio_cod").pct_mal_definidas)
    faixa = pd.read_parquet(MARTS / "dim_pop_faixa.parquet")
    idoso = (faixa[faixa.faixa_etaria.isin(["60-74", "75+"])]
             .groupby("municipio_cod").populacao.sum()
             / faixa.groupby("municipio_cod").populacao.sum())
    pop = (pd.read_parquet(MARTS / "dim_populacao.parquet")
           .query("ano == 2022").set_index("municipio_cod").populacao)

    p = perfil.set_index("municipio_cod")
    p["ivs"] = ivs.ivs_score.reindex(p.index)
    p["mal_definidas"] = qual.reindex(p.index)
    p["idoso"] = (idoso.reindex(p.index) * 100)
    p["pop"] = pop.reindex(p.index)

    linhas = []
    regioes = sorted(p.regiao.unique())
    for g, sub in p.groupby("grupo"):
        linha = {
            "Grupo": int(g), "Municípios": len(sub),
            "População (mediana)": int(sub["pop"].median()),
            "% 60+ (mediana)": round(float(sub.idoso.median()), 1),
            "IVS (mediana)": round(float(sub.ivs.median()), 1),
            "% mal definidas (mediana)": round(float(sub.mal_definidas.median()), 2),
            "Índice de inespecificidade (mediana)":
                round(float(sub.indice_inespecificidade.median()), 3),
        }
        for r in regioes:
            linha[f"% {r}"] = round(100 * float((sub.regiao == r).mean()), 1)
        linhas.append(linha)
    return pd.DataFrame(linhas)


def tabela_7_correlacao() -> pd.DataFrame:
    pares = pd.read_parquet(MARTS / "mart_correlacao_causas.parquet")
    # A tabela passou a ter quatro recortes (nacional e os três grupos); sem
    # este filtro o "top 15" misturaria recortes e repetiria pares.
    pares = pares[pares.grupo == -1]
    dim = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    d = dim.set_index("causabas_3").descricao.to_dict()
    sig = pares[pares.significativo].copy()
    sig["abs_r"] = sig.r.abs()
    top = sig.nlargest(15, "abs_r").copy()
    top["Descrição A"] = top.cid_a.map(lambda c: rotulo_cid(d.get(c), c))
    top["Descrição B"] = top.cid_b.map(lambda c: rotulo_cid(d.get(c), c))
    return top[["cid_a", "cid_b", "Descrição A", "Descrição B", "r"]].rename(
        columns={"cid_a": "CID A", "cid_b": "CID B", "r": "Correlação"})


def tabela_8_anomalias() -> tuple[pd.DataFrame, pd.DataFrame]:
    an = pd.read_parquet(MARTS / "mart_anomalia_causa_municipio.parquet")
    dim = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    d = dim.set_index("causabas_3").descricao.to_dict()
    sig = an[an.excesso_proprio]

    resumo = (sig.groupby("causabas_3").size().sort_values(ascending=False)
              .head(12).rename("Municípios-ano").reset_index())
    resumo["Descrição"] = resumo.causabas_3.map(lambda c: rotulo_cid(d.get(c), c))
    resumo = resumo.rename(columns={"causabas_3": "CID"})[["CID", "Descrição", "Municípios-ano"]]

    por_ano = (an.groupby("ano")
               .agg(**{"Excesso vs. história própria": ("excesso_proprio", "sum"),
                       "Excesso descontada a tendência nacional": ("excesso_relativo", "sum")})
               .reset_index().rename(columns={"ano": "Ano"}))

    dengue = an[an.causabas_3.isin(["A90", "A91"]) & an.excesso_proprio].copy()
    dengue = dengue[["municipio_nome", "uf_sigla", "ano", "causabas_3", "obitos",
                     "esperado", "razao"]].sort_values("razao", ascending=False)
    dengue.columns = ["Município", "UF", "Ano", "CID", "Óbitos", "Esperado", "Razão"]
    return resumo, por_ano, dengue


def tabela_9_eixos_sociais() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Eixos do contexto social e o cruzamento com os de mortalidade."""
    import analise_contexto_social as acs

    perfil = (pd.read_parquet(MARTS / "mart_perfil_mortalidade_municipio.parquet")
              .set_index("municipio_cod"))
    x = acs.carregar_contexto()
    x = x.loc[x.index.intersection(perfil.index)].dropna()
    perfil = perfil.loc[x.index]
    escores, var, cargas = acs.eixos(x)

    resumo = []
    for i, c in enumerate(cargas.columns):
        ordenado = cargas[c].sort_values()
        resumo.append({
            "Eixo": c.upper(),
            "Variância (%)": round(100 * float(var[i]), 1),
            "Polo negativo": ", ".join(ordenado.index[:3]),
            "Polo positivo": ", ".join(ordenado.index[-3:][::-1]),
        })

    mort = perfil[[f"pc{i}" for i in range(1, 7)]].values.astype(float)
    cruz = pd.DataFrame(
        [[round(float(np.corrcoef(mort[:, i], escores[:, j])[0, 1]), 3)
          for j in range(escores.shape[1])] for i in range(mort.shape[1])],
        columns=[f"SPC{j + 1}" for j in range(escores.shape[1])])
    cruz.insert(0, "Eixo de mortalidade", [f"PC{i + 1}" for i in range(mort.shape[1])])
    return pd.DataFrame(resumo), cruz


def tabela_10_inespecificidade_contexto() -> pd.DataFrame:
    """O teste da interpretação alternativa: artefato ou falta de recurso?"""
    ctx = (pd.read_parquet(MARTS / "mart_contexto_social_municipio.parquet")
           .set_index("municipio_cod"))
    perfil = (pd.read_parquet(MARTS / "mart_perfil_mortalidade_municipio.parquet")
              .set_index("municipio_cod"))
    inesp = perfil.indice_inespecificidade.reindex(ctx.index).astype(float)
    rotulos = {
        "taxa_analfabetismo": "Taxa de analfabetismo",
        "ivs_score": "Índice de vulnerabilidade social",
        "estab_por_10k": "Estabelecimentos de saúde por 10 mil hab.",
        "vinculos_plano_por_100_hab": "Vínculos de plano por 100 hab.",
        "gasto_proprio_saude_hab": "Gasto próprio em saúde por hab.",
        "pct_prenatal_7mais": "Pré-natal com 7+ consultas (%)",
        "cobertura_pct": "Cobertura da atenção primária (%)",
        "leitos_sus_por_mil": "Leitos SUS por mil hab.",
        "hosp_por_10k": "Hospitais por 10 mil hab.",
        "log_pop": "log₁₀ da população",
    }
    linhas = [{"Variável": rot,
               "r com o índice de inespecificidade":
                   round(float(np.corrcoef(inesp, ctx[v].astype(float))[0, 1]), 3)}
              for v, rot in rotulos.items()]
    return pd.DataFrame(linhas).sort_values("r com o índice de inespecificidade",
                                            ascending=False).reset_index(drop=True)


def tabela_11_correlacao_por_grupo() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Quantos pares se correlacionam em cada grupo, e onde os grupos discordam."""
    corr = pd.read_parquet(MARTS / "mart_correlacao_causas.parquet")
    perfil = pd.read_parquet(MARTS / "mart_perfil_mortalidade_municipio.parquet")
    dim = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    descricao = dim.set_index("causabas_3").descricao.to_dict()

    resumo = []
    for g in sorted(corr.grupo.unique()):
        sub = corr[corr.grupo == g]
        linha = {"Recorte": "Nacional" if g < 0 else f"Grupo {g}",
                 "Pares significativos (FDR 1%)": int(sub.significativo.sum()),
                 "Total de pares": len(sub)}
        if g >= 0:
            do_grupo = perfil[perfil.grupo == g]
            linha["Municípios"] = len(do_grupo)
            linha["Índice de inespecificidade (mediana)"] = round(
                float(do_grupo.indice_inespecificidade.median()), 3)
        resumo.append(linha)

    # os pares em que o grupo mais preciso mais discorda do menos preciso
    mediana = perfil.groupby("grupo").indice_inespecificidade.median()
    a, b = int(mediana.idxmin()), int(mediana.idxmax())
    ja = corr[corr.grupo == a].set_index(["cid_a", "cid_b"]).r
    jb = corr[corr.grupo == b].set_index(["cid_a", "cid_b"]).r
    comuns = ja.index.intersection(jb.index)
    dif = (jb.loc[comuns] - ja.loc[comuns]).abs().nlargest(12)
    linhas = []
    for cid_a, cid_b in dif.index:
        linhas.append({
            "CID A": cid_a, "CID B": cid_b,
            "Descrição A": rotulo_cid(descricao.get(cid_a), cid_a),
            "Descrição B": rotulo_cid(descricao.get(cid_b), cid_b),
            f"r no grupo {a} (mais preciso)": round(float(ja.loc[(cid_a, cid_b)]), 2),
            f"r no grupo {b} (menos preciso)": round(float(jb.loc[(cid_a, cid_b)]), 2),
        })
    return pd.DataFrame(resumo), pd.DataFrame(linhas)


def main() -> None:
    comp, conf, inespecificidade, contagens = carregar()
    print(f"[base] {comp.shape[0]:,} municípios × {comp.shape[1]} CIDs", flush=True)

    _grava(tabela_1_base(), "tabela_1_base", "descrição da base")
    _grava(tabela_2_covid(), "tabela_2_covid_b34", "B34 e U07 por ano")
    t3 = tabela_3_variancia(comp, conf, contagens)
    _grava(t3, "tabela_3_variancia", "variância observada, residualizada e nula")
    k_comp = int((t3["Razão residualizado/nulo"] > 2).sum())
    _grava(tabela_3b_grao(comp, conf, contagens), "tabela_3b_grao",
           "categoria contra capítulo no mesmo desenho")
    _grava(tabela_4_cargas(comp, conf), "tabela_4_cargas", "cargas de PC1–PC3")
    _grava(tabela_5_agrupamento(comp, conf, contagens, k_comp), "tabela_5_agrupamento",
           "estabilidade e separação por k")
    _grava(tabela_6_grupos(), "tabela_6_grupos", "caracterização dos grupos")
    _grava(tabela_7_correlacao(), "tabela_7_correlacao", "pares de causa mais correlacionados")
    resumo, por_ano, dengue = tabela_8_anomalias()
    _grava(resumo, "tabela_8a_anomalias_por_cid", "CIDs mais sinalizados")
    _grava(por_ano, "tabela_8b_anomalias_por_ano", "sinais por ano e por escore")
    _grava(dengue, "tabela_8c_dengue_2024", "controle positivo: dengue")

    eixos_soc, cruzamento = tabela_9_eixos_sociais()
    _grava(eixos_soc, "tabela_9a_eixos_sociais", "eixos do contexto social")
    _grava(cruzamento, "tabela_9b_cruzamento", "mortalidade × contexto social")
    _grava(tabela_10_inespecificidade_contexto(), "tabela_10_inespecificidade_contexto",
           "o teste da interpretação alternativa")
    por_grupo, discordancia = tabela_11_correlacao_por_grupo()
    _grava(por_grupo, "tabela_11a_correlacao_por_grupo", "pares correlacionados por grupo")
    _grava(discordancia, "tabela_11b_discordancia", "onde os grupos mais discordam")

    r = np.corrcoef(componentes(residualizar(comp.values, conf))[0][:, 0],
                    inespecificidade.values)[0, 1]
    print(f"[conferência] PC1 × inespecificidade r={r:+.3f} — bate com o artigo", flush=True)


if __name__ == "__main__":
    main()
