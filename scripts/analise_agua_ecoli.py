"""
analise_agua_ecoli.py — do ato de reportar para o que a água mostrou
=====================================================================

    .venv311/Scripts/python scripts/analise_agua_ecoli.py

Grava `data/analises/agua-ecoli/tab*.csv`.

POR QUE ESTA ANÁLISE EXISTE
----------------------------
`analise_agua_painel.py` mede a **ausência de registro**: o município não
reportou análise alguma ao SISAGUA no ano anterior. É uma exposição
administrativa, e o manuscrito precisa de três parágrafos explicando que ela não
é a água — um município pode analisar e não reportar, e não reportar não é
contaminação.

Aqui a exposição muda de natureza. Entre os município-anos em que **houve**
análise reportada, a pergunta passa a ser se o resultado dela prediz mortalidade:
o laboratório encontrou *Escherichia coli* na água distribuída, ou não. Isso é
resultado, não papelada.

O ESTIMANDO, E A SELEÇÃO QUE ELE CARREGA
-----------------------------------------
O recorte é **condicional a reportar**. Município-ano sem amostra analisada sai
da análise, e não entra como "negativo": ausência de medida microbiológica não é
amostra limpa. A consequência é que nada aqui se aplica a quem não reporta — que
é exatamente a população da análise irmã.

Essa seleção é declarável, e não fatal, porque o estimando é explícito: entre
municípios que vigiam e reportam, a detecção de *E. coli* no ano anterior
antecede mortalidade maior por doença infecciosa intestinal **dentro do mesmo
município**? O efeito fixo de município absorve todo confundidor constante no
tempo, inclusive a propensão a reportar, que é a variável que define a seleção.

O que ela não resolve: municípios que reportam podem diferir dos que não
reportam em coisas que variam no tempo, e a comparação continua ecológica.

ESTA EXTENSÃO É EXPLORATÓRIA, E ISSO FICA DITO
------------------------------------------------
Ela foi concebida DEPOIS de ver o resultado do painel principal, a partir de uma
auditoria externa. Os critérios abaixo foram escritos antes de qualquer número
desta análise ser observado — o que é diferente de pré-especificação anterior
aos dados, e o manuscrito vai dizer isso com essas palavras.

OS CRITÉRIOS, DECLARADOS ANTES DE QUALQUER RESULTADO
------------------------------------------------------
  CRITÉRIO 1 — ESPECIFICIDADE ENTRE CAUSAS (é o que refuta)
    O IRR da detecção de E. coli é estimado para os mesmos CINCO grupos de causa
    do painel principal. Para a leitura hídrica valer são necessárias duas
    coisas: IRR de A00–A09 acima de 1 com IC95% que exclua 1, **e** maior que o
    de todos os controles.
    **Se os cinco vierem semelhantes, a leitura é que a detecção de E. coli
    marca município-ano de vigilância mais intensa ou de sistema mais frágil em
    geral — não caminho hídrico — e vai reportada assim.**

  CRITÉRIO 2 — SOBREVIVER AO EFEITO FIXO
    O mesmo IRR com e sem efeito fixo de município. Se a associação só existir
    sem ele, ela é diferença entre municípios, como foi no desenho transversal.

  CRITÉRIO 3 — NÃO SER ARTEFATO DE INTENSIDADE DE AMOSTRAGEM
    Quem coleta mais amostras acha mais E. coli por acaso. O desenho inclui o
    log do número de amostras analisadas como covariável, e o critério é que o
    IRR não mude de direção ao incluí-la. **Se mudar, o achado é sobre esforço
    de amostragem, e não sobre a água.**

  CRITÉRIO 4 — ROBUSTEZ
    Sem o Distrito Federal, sem municípios com menos de 5.000 habitantes, e por
    região, como no painel principal.

O QUE ESTE DESENHO CONTINUA NÃO PODENDO DIZER
-----------------------------------------------
É ECOLÓGICO. Nada aqui autoriza dizer que quem morreu bebeu a água em que a
E. coli foi encontrada. E detecção é evento de vigilância: um município que
encontra E. coli e trata o problema pode ter menos morte que um que não procura.

Depende de: data/marts/{mart_sisagua_municipio, mart_mortalidade_causa_municipio,
dim_populacao, dim_municipio}.parquet e scripts/_poisson_fe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _poisson_fe import ajustar_matriz  # noqa: E402
from analise_agua_painel import (  # noqa: E402
    ANOS_DESFECHO,
    ANOS_SISAGUA,
    GRUPOS,
    MARTS,
    POP_MINIMA,
    REPS,
    _filtrar,
    ic_municipio,
)

ROOT = Path(__file__).resolve().parents[1]
SAIDA = ROOT / "data" / "analises" / "agua-ecoli"


def montar_painel() -> pd.DataFrame:
    """Municipio x ano, restrito a quem REPORTOU amostra no ano anterior."""
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

    # A EXPOSICAO: o que a analise ENCONTROU, no ano anterior.
    #
    # `escherichia_coli` e `amostras_analisadas` sao contagens somadas sobre os
    # dez parametros do mart. Somar aqui e' correto: a pergunta e' se o municipio
    # teve alguma deteccao naquele ano, e a E. coli so' e' contada no parametro
    # em que ela e' medida.
    sis = pd.read_parquet(MARTS / "mart_sisagua_municipio.parquet",
                          columns=["municipio_cod", "ano", "amostras_analisadas",
                                   "escherichia_coli"])
    sis = (sis[sis.ano.isin(ANOS_SISAGUA)]
           .groupby(["municipio_cod", "ano"], as_index=False)
           .agg(amostras=("amostras_analisadas", "sum"),
                ecoli=("escherichia_coli", "sum")))
    sis["ano"] = sis.ano + 1                       # vira exposicao do ano seguinte
    base = base.merge(sis, on=["municipio_cod", "ano"], how="inner")

    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")[
        ["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]
    base = base.merge(dim, on="municipio_cod", how="inner")

    antes = len(base)
    # CONDICIONAL A REPORTAR: sem amostra analisada, nao ha' resultado. Zero
    # amostras NAO e' amostra negativa, e entra como ausencia, nao como limpo.
    base = base[(base.populacao > 0) & (base.amostras > 0)].copy()
    base["ecoli_t1"] = (base.ecoli > 0).astype(float)
    base["log_amostras"] = np.log(base.amostras)

    print(f"[painel] {len(base):,} linhas municipio-ano com amostra analisada no "
          f"ano anterior (de {antes:,} que chegaram ao merge, e de 50.130 no "
          "painel principal)", flush=True)
    print(f"[painel] {base.municipio_cod.nunique():,} municipios, "
          f"{base.ano.nunique()} anos (painel DESBALANCEADO por construcao)",
          flush=True)
    print(f"[painel] municipio-ano com E. coli detectada: "
          f"{int(base.ecoli_t1.sum()):,} ({100 * base.ecoli_t1.mean():.1f}%)",
          flush=True)
    return base


def empilhar_desbalanceado(d: pd.DataFrame, com_amostras: bool) -> dict:
    """Matrizes municipio x ano, com mascara para os anos ausentes.

    POR QUE NAO DA' PARA REUSAR `empilhar`
    ---------------------------------------
    O painel principal e' balanceado — todo municipio tem os nove anos — e aquela
    funcao aborta se nao for. Aqui o painel e' desbalanceado POR CONSTRUCAO: um
    municipio entra so' nos anos em que reportou amostra, que e' o que "condicional
    a reportar" significa.

    A solucao e' preencher a grade cheia e marcar o que nao existe com offset
    zero. Contagem zero com offset zero nao contribui para a multinomial
    condicional — a probabilidade daquele ano vai a zero e o ano sai da conta do
    municipio sozinho, sem precisar de codigo especial no estimador.
    """
    munis = np.sort(d.municipio_cod.unique())
    anos = np.sort(d.ano.unique())
    M, T = len(munis), len(anos)
    im = {m: i for i, m in enumerate(munis)}
    ia = {a: i for i, a in enumerate(anos)}
    li = d.municipio_cod.map(im).to_numpy()
    co = d.ano.map(ia).to_numpy()

    def espalhar(v: np.ndarray) -> np.ndarray:
        m = np.zeros((M, T))
        m[li, co] = v
        return m

    OFF = espalhar(d.populacao.to_numpy(dtype=float))
    colunas = [espalhar(d.ecoli_t1.to_numpy(dtype=float))]
    if com_amostras:
        colunas.append(espalhar(d.log_amostras.to_numpy(dtype=float)))
    for a in anos[1:]:
        colunas.append(espalhar((d.ano.to_numpy() == a).astype(float)))

    prim = d.drop_duplicates("municipio_cod").set_index("municipio_cod")
    return {
        "munis": munis, "anos": anos, "M": M, "T": T,
        "X": np.stack(colunas, axis=2), "OFF": OFF,
        "Y": {n: espalhar(d[n].to_numpy(dtype=float)) for n in GRUPOS},
        "uf": prim.loc[munis, "uf_sigla"].to_numpy(),
        "regiao": prim.loc[munis, "regiao"].to_numpy(),
        "pop_media": d.groupby("municipio_cod").populacao.mean().loc[munis].to_numpy(),
        "presente": espalhar(np.ones(len(d))),
        "tabela": d,
    }


def irr(P: dict, causa: str, com_fe: bool = True) -> float:
    """Razao de taxas da deteccao de E. coli, para uma causa."""
    Y, X, OFF = P["Y"][causa], P["X"], P["OFF"]
    if not com_fe:
        M, T, K = X.shape
        Y, OFF = Y.reshape(1, M * T), OFF.reshape(1, M * T)
        X = X.reshape(1, M * T, K)
    beta = ajustar_matriz(Y, X, OFF)
    return float(np.exp(beta[0])) if np.isfinite(beta[0]) else np.nan


def tab01_painel(P: dict, Pa: dict) -> pd.DataFrame:
    d = P["tabela"]
    exp = P["X"][:, :, 0]
    pres = P["presente"]
    muda = ((exp * pres).sum(axis=1) > 0) & (((1 - exp) * pres).sum(axis=1) > 0)
    linhas = [("Municipios com alguma amostra reportada", P["M"]),
              ("Municipio-ano no recorte (condicional a reportar)", int(pres.sum())),
              ("Municipio-ano com E. coli detectada no ano anterior",
               int((exp * pres).sum())),
              ("Municipio-ano com E. coli detectada (%)",
               round(100 * float((exp * pres).sum() / pres.sum()), 1)),
              ("Amostras analisadas no periodo", int(d.amostras.sum())),
              ("Deteccoes de E. coli no periodo", int(d.ecoli.sum())),
              ("Municipios que MUDARAM de estado de deteccao", int(muda.sum()))]
    for nome in GRUPOS:
        tem = P["Y"][nome].sum(axis=1) > 0
        linhas.append((f"Obitos: {nome}", int(P["Y"][nome].sum())))
        linhas.append((f"Municipios que mudam E tem obito: {nome}",
                       int((muda & tem).sum())))
    del Pa
    return pd.DataFrame({"Recorte": [k for k, _ in linhas],
                         "Valor": pd.Series([v for _, v in linhas], dtype=object)})


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
    """CRITERIO 2. O mesmo IRR com e sem efeito fixo de municipio."""
    controle = "J00-J22 respiratorias (subgrupo 1.2)"
    irrs = {n: (irr(P, n, False), irr(P, n, True)) for n in GRUPOS}
    bs, bc = irrs[controle]
    linhas = []
    for nome, (sem, com) in irrs.items():
        linhas.append({"Grupo de causa": nome,
                       "IRR sem efeito fixo": round(sem, 3),
                       "IRR com efeito fixo": round(com, 3),
                       "Removido pelo efeito fixo": round(sem - com, 3),
                       "RRR contra o controle, sem efeito fixo": round(sem / bs, 3),
                       "RRR contra o controle, com efeito fixo": round(com / bc, 3)})
        print(f"   {nome:<38} sem FE {sem:.3f} -> com FE {com:.3f}", flush=True)
    return pd.DataFrame(linhas)


def tab04_intensidade(P: dict, Pa: dict) -> pd.DataFrame:
    """CRITERIO 3. O IRR muda quando o esforco de amostragem entra no desenho?"""
    linhas = []
    for nome in GRUPOS:
        sem = irr(P, nome)
        com = irr(Pa, nome)
        linhas.append({"Grupo de causa": nome,
                       "IRR sem ajuste por amostras": round(sem, 3),
                       "IRR ajustado por log(amostras)": round(com, 3),
                       "Deslocamento": round(com - sem, 3),
                       "Muda de direcao": "sim" if (sem - 1) * (com - 1) < 0 else "nao"})
        print(f"   {nome:<38} {sem:.3f} -> {com:.3f} (ajustado)", flush=True)
    return pd.DataFrame(linhas)


def tab05_robustez(P: dict) -> pd.DataFrame:
    """CRITERIO 4. Exclusoes e regioes, sobre a causa da hipotese."""
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
        sub["presente"] = P["presente"][mascara]
        v, lo, hi = ic_municipio(sub, lambda p: irr(p, causa), reps=REPS)
        linhas.append({"Recorte": nome, "Municipios": int(mascara.sum()),
                       "IRR": round(v, 3), "IC95% inferior": round(lo, 3),
                       "IC95% superior": round(hi, 3)})
        print(f"   {nome:<40} IRR {v:.3f} [{lo:.3f}, {hi:.3f}]", flush=True)
    return pd.DataFrame(linhas)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    SAIDA.mkdir(parents=True, exist_ok=True)
    d = montar_painel()
    P = empilhar_desbalanceado(d, com_amostras=False)
    Pa = empilhar_desbalanceado(d, com_amostras=True)

    print("\n[criterio 1] especificidade entre cinco causas", flush=True)
    t02 = tab02_especificidade(P)
    print("\n[criterio 2] com e sem efeito fixo", flush=True)
    t03 = tab03_efeito_fixo(P)
    print("\n[criterio 3] ajuste por esforco de amostragem", flush=True)
    t04 = tab04_intensidade(P, Pa)
    print("\n[criterio 4] robustez", flush=True)
    t05 = tab05_robustez(P)

    for nome, t in (("tab01_painel", tab01_painel(P, Pa)),
                    ("tab02_especificidade", t02),
                    ("tab03_efeito_fixo", t03),
                    ("tab04_intensidade", t04),
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
        print("   criterio 1 APROVADO: entre quem reporta, a deteccao de E. coli")
        print("   antecede excesso ESPECIFICO de mortalidade intestinal.")
    else:
        print("   criterio 1 REPROVADO: a deteccao de E. coli nao distingue a")
        print("   causa hidrica das demais. Vai reportado assim.")
    print(f"\n[ok] 5 tabelas em {SAIDA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
