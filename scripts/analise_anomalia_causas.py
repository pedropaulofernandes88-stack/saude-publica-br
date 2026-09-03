"""
analise_anomalia_causas.py — onde uma causa saiu do padrão do próprio município
===============================================================================

Terceira análise do desenho: para cada município e cada CID, comparar o
observado em 2020–2024 com o que a própria história do município (2015–2019)
faria esperar, e sinalizar os excessos.

POR QUE NÃO É z-SCORE
---------------------
O pedido original falava em z-score por CID por município. Z-score gaussiano é
o instrumento errado aqui, por dois motivos que se somam:

  * **contagem pequena.** A mediana é 77 óbitos por município-ano, e a maioria
    das células município×CID×ano é 0, 1 ou 2. A distribuição normal não
    aproxima isso; um z de 3 numa célula de esperado 0,4 não significa nada.
  * **superdispersão.** Mesmo onde a contagem cresce, a variância excede a
    média. Assumir Poisson puro produziria alarme em massa.

Aqui o teste é **binomial negativa**, com a dispersão φ estimada por CID a
partir da variação ANO A ANO dentro do mesmo município no período base.

A ESTIMATIVA DE DISPERSÃO ERROU UMA VEZ, E O ERRO IMPORTA
----------------------------------------------------------
A primeira versão estimava φ comparando cada município com a média NACIONAL.
Isso mistura duas coisas diferentes: a variação temporal (ruído, que é o que se
quer no denominador) e a variação entre municípios (que é o SINAL — municípios
realmente diferem). O resultado foi φ inflado, mediana perto de 20, e a análise
inteira ficou surda: 132 excessos em 947 mil testes.

Estimando φ pela variação ano a ano DENTRO do município, a mediana cai para 1,23
e o P95 para 3,38 — e a detecção passa a 2.167 excessos. O sinal estava sendo
absorvido pelo próprio denominador.

O ZERO NA LINHA DE BASE É INFORMAÇÃO, NÃO LACUNA
-------------------------------------------------
Segundo defeito real, e mais grave. A versão inicial usava a proporção do
próprio município como esperado e descartava células com esperado abaixo de 1.
Município sem NENHUM óbito de dengue em 2015–2019 tinha esperado zero, era
descartado — ou seja, **exatamente onde a causa surgiu era onde ela não podia
ser detectada.** Uma detecção de mudança de padrão cega para o aparecimento de
uma causa nova não serve para nada.

A correção é encolhimento bayesiano: a proporção esperada mistura a do próprio
município com a nacional, com peso equivalente a `PSEUDO_EXPOSICAO` óbitos.
Município sem histórico da causa passa a ter esperado pequeno mas positivo, e um
surto fica visível.

DOIS ESCORES, PORQUE SÃO DUAS PERGUNTAS
----------------------------------------
    excesso_proprio    observado contra a história do PRÓPRIO município.
                       É o pedido literal. Responde "mudou aqui?".
    excesso_relativo   o mesmo, DESCONTADA a variação nacional do CID no ano.
                       Responde "mudou aqui mais do que no Brasil?".

A diferença não é acadêmica. Sem descontar a tendência nacional, o que mais
aparece é **deriva de codificação**: N39, E11, G30, I10 encabeçam a lista, e o
número de sinais cresce monotonicamente de 203 (2020) para 644 (2024) — padrão
de mudança de prática de registro, não de epidemia. Para vigilância serve o
segundo escore; para descrever o que mudou no município, o primeiro.

CONTROLE POSITIVO
-----------------
Dengue (A90/A91) aparece **apenas em 2024**, o ano da maior epidemia registrada
(6,6 milhões de casos prováveis contra 1,6 milhão em 2023). B34 — COVID —
domina 2020–2021. Uma detecção que não achasse esses dois estaria quebrada, e é
isso que `conferir_controles()` verifica antes de publicar.

Uso:
  .venv311/Scripts/python scripts/analise_anomalia_causas.py
  .venv311/Scripts/python scripts/analise_anomalia_causas.py --no-upload
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
from scipy.stats import nbinom

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _achados import registrar  # noqa: E402
from _publicacao import carregar_env, conferir_chave_unica, escrever_parquet  # noqa: E402
from _sim_obitos import ANOS_CONSOLIDADOS, CIDS_DENGUE  # noqa: E402
from _supabase_key import chave_escrita  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
PRODUTOR = "scripts/analise_anomalia_causas.py"

#: Base = anos pré-pandemia. 2020 em diante é o que se testa.
ANOS_BASE = list(range(2015, 2020))

#: Peso do prior nacional no encolhimento, em óbitos de exposição. Um município
#: com 5.000 óbitos na base fica com ~70% da própria proporção e ~30% da
#: nacional; um com 500, ao contrário. É o que dá esperado positivo a quem nunca
#: registrou aquela causa — ver a nota de cabeçalho.
PSEUDO_EXPOSICAO = 2000.0

#: Abaixo disto o teste não tem poder e só adiciona ruído ao FDR.
ESPERADO_MINIMO = 0.5

#: Taxa de descoberta falsa. 1% e não 5% porque são ~950 mil testes.
FDR = 0.01


def _bh(p: np.ndarray, q: float = FDR) -> np.ndarray:
    ordem = np.argsort(p)
    limite = p[ordem] <= q * (np.arange(1, len(p) + 1) / len(p))
    if not limite.any():
        return np.array([], dtype=int)
    return ordem[:int(np.max(np.where(limite)[0]) + 1)]


def _p_binomial_negativa(obs: np.ndarray, esperado: np.ndarray,
                         phi: np.ndarray) -> np.ndarray:
    """P(X >= obs) sob binomial negativa com média `esperado` e variância φ·média.

    φ = 1 degenera em Poisson; `r` vai ao infinito e a nbinom converge para ela.
    """
    # `np.where` avalia OS DOIS ramos antes de escolher, então φ=1 exato geraria
    # divisão por zero mesmo com a condição correta. O clip no denominador é o
    # que evita o aviso sem mudar nenhum resultado.
    r = np.where(phi > 1.0001, esperado / np.clip(phi - 1, 1e-9, None), 1e9)
    return nbinom.sf(obs - 1, r, r / (r + esperado))


def construir() -> tuple[pd.DataFrame, dict]:
    dim = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    cids = sorted(set(dim[dim.informativo].causabas_3))
    anual = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                            columns=["municipio_cod", "ano", "causabas_3", "obitos"])
    fora = sorted(set(anual.ano.unique()) - set(ANOS_CONSOLIDADOS))
    if fora:
        # Ver `so_consolidado` em analise_perfil_mortalidade.py. Aqui o risco é
        # ainda mais direto: um ano com a cauda faltando aparece como QUEDA
        # significativa em quase toda categoria, e o escore de anomalia viraria
        # um detector de atraso de registro.
        print(f"[recorte] descartando {fora} — anos preliminares", flush=True)
    anual = anual[anual.ano.isin(ANOS_CONSOLIDADOS)]
    anual = anual[anual.causabas_3.isin(set(cids))]
    total = anual.groupby(["municipio_cod", "ano"]).obitos.sum().rename("total")
    anual = anual.join(total, on=["municipio_cod", "ano"])

    base = anual[anual.ano.isin(ANOS_BASE)]
    total_mun_ano = base.groupby(["municipio_cod", "ano"]).total.first()
    total_base = total_mun_ano.groupby("municipio_cod").sum()
    obitos_base = base.groupby(["municipio_cod", "causabas_3"]).obitos.sum()
    share_nacional = base.groupby("causabas_3").obitos.sum() / total_mun_ano.sum()

    # A grade COMPLETA município × CID: a ausência de uma causa na base é
    # informação, e é justamente onde o surgimento precisa ser detectável.
    grade = pd.MultiIndex.from_product([total_base.index, cids],
                                       names=["municipio_cod", "causabas_3"])
    prior = obitos_base.reindex(grade, fill_value=0).rename("obitos_base").to_frame()
    prior["total_base"] = total_base.reindex(prior.index.get_level_values(0)).values
    prior["share_nacional"] = (share_nacional.reindex(prior.index.get_level_values(1))
                               .fillna(0).values)
    prior["share"] = ((prior.obitos_base + PSEUDO_EXPOSICAO * prior.share_nacional)
                      / (prior.total_base + PSEUDO_EXPOSICAO))

    # Dispersão TEMPORAL: quanto uma célula varia de um ano para o outro dentro
    # do próprio município, no período base. Ver a nota de cabeçalho.
    checagem = (base.set_index(["municipio_cod", "causabas_3"])
                .join(prior[["share"]], how="inner").reset_index())
    checagem["esperado"] = checagem.share * checagem.total
    checagem = checagem[checagem.esperado >= ESPERADO_MINIMO]
    phi = (checagem.assign(q=(checagem.obitos - checagem.esperado) ** 2 / checagem.esperado)
           .groupby("causabas_3").q.mean().clip(lower=1.0))

    alvo = (anual[anual.ano >= max(ANOS_BASE) + 1]
            .set_index(["municipio_cod", "causabas_3"])
            .join(prior[["share"]], how="inner").reset_index())
    alvo["esperado"] = alvo.share * alvo.total
    alvo = alvo[alvo.esperado >= ESPERADO_MINIMO].copy()
    alvo["phi"] = alvo.causabas_3.map(phi).fillna(1.0)

    # Escore 1: contra a própria história.
    alvo["p_proprio"] = _p_binomial_negativa(alvo.obitos.values, alvo.esperado.values,
                                             alvo.phi.values)
    # Escore 2: descontando o que o CID fez no Brasil naquele ano.
    nac_ano = (anual.groupby(["ano", "causabas_3"]).obitos.sum()
               / anual.groupby("ano").obitos.sum().reindex(
                   anual.groupby(["ano", "causabas_3"]).obitos.sum()
                   .index.get_level_values(0)).values)
    nac_base = share_nacional
    fator = (nac_ano / nac_base.reindex(nac_ano.index.get_level_values(1)).values).rename("fator")
    alvo = alvo.join(fator, on=["ano", "causabas_3"])
    alvo["fator"] = alvo.fator.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.1, 10)
    alvo["esperado_relativo"] = alvo.esperado * alvo.fator
    alvo["p_relativo"] = _p_binomial_negativa(alvo.obitos.values,
                                              alvo.esperado_relativo.values, alvo.phi.values)

    alvo["excesso_proprio"] = False
    alvo.iloc[_bh(alvo.p_proprio.values),
              alvo.columns.get_loc("excesso_proprio")] = True
    alvo["excesso_relativo"] = False
    alvo.iloc[_bh(alvo.p_relativo.values),
              alvo.columns.get_loc("excesso_relativo")] = True

    resumo = {
        "testes": len(alvo),
        "phi_mediana": float(phi.median()),
        "phi_p95": float(phi.quantile(0.95)),
        "excesso_proprio": int(alvo.excesso_proprio.sum()),
        "excesso_relativo": int(alvo.excesso_relativo.sum()),
    }
    return alvo, resumo


def conferir_controles(alvo: pd.DataFrame) -> None:
    """Dois controles positivos que uma detecção correta TEM de achar.

    Aborta se falharem: uma detecção que não vê a pandemia nem a maior epidemia
    de dengue já registrada está quebrada, e publicar seus alertas seria pior
    que não publicar nada.
    """
    sig = alvo[alvo.excesso_proprio]

    dengue = sig[sig.causabas_3.isin(CIDS_DENGUE)]
    if dengue.empty:
        raise SystemExit(
            f"controle positivo falhou: dengue ({'/'.join(CIDS_DENGUE)}) não aparece "
            "entre os excessos. "
            "2024 teve 6,6 milhões de casos prováveis — a detecção está cega.")
    anos = sorted(dengue.ano.unique())
    if anos != [2024]:
        print(f"[atenção] dengue sinalizada em {anos}, esperado só 2024", flush=True)
    print(f"[controle] dengue: {len(dengue)} município-ano, anos {anos}", flush=True)

    covid = sig[(sig.causabas_3 == "B34") & (sig.ano.isin([2020, 2021]))]
    if covid.empty:
        raise SystemExit(
            "controle positivo falhou: B34 (COVID-19) não aparece em 2020–2021.")
    print(f"[controle] COVID em 2020–2021: {len(covid)} município-ano", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    alvo, resumo = construir()
    print(f"[base] {resumo['testes']:,} testes município×CID×ano (2020–2024)", flush=True)
    print(f"[dispersão] φ mediana {resumo['phi_mediana']:.2f} | P95 {resumo['phi_p95']:.2f}",
          flush=True)
    print(f"[fdr {FDR:.0%}] excesso vs própria história: {resumo['excesso_proprio']:,}",
          flush=True)
    print(f"[fdr {FDR:.0%}] excesso descontada a tendência nacional: "
          f"{resumo['excesso_relativo']:,}", flush=True)
    conferir_controles(alvo)

    sig = alvo[alvo.excesso_proprio]
    print("[deriva] CIDs mais frequentes entre os excessos vs própria história:", flush=True)
    for cid, n in sig.causabas_3.value_counts().head(5).items():
        print(f"[deriva]   {cid}: {n}", flush=True)
    por_ano = sig.ano.value_counts().sort_index()
    print(f"[deriva] por ano: {por_ano.to_dict()} — crescimento monótono indica "
          "mudança de prática de registro, não epidemia", flush=True)

    mun = pd.read_parquet(MARTS / "dim_municipio.parquet").set_index("municipio_cod")
    saida = alvo[["municipio_cod", "ano", "causabas_3", "obitos"]].copy()
    # Códigos como 330000 são "município ignorado" de uma UF: óbito real cuja
    # residência não foi identificada. Rotular é melhor que descartar — some
    # da tabela e o total deixa de fechar com o mart de origem.
    saida["municipio_nome"] = (mun.municipio_nome.reindex(saida.municipio_cod)
                               .fillna("Não identificado").values)
    saida["uf_sigla"] = mun.uf_sigla.reindex(saida.municipio_cod).fillna("ND").values
    saida["esperado"] = alvo.esperado.round(3).values
    saida["esperado_relativo"] = alvo.esperado_relativo.round(3).values
    saida["razao"] = (alvo.obitos / alvo.esperado.clip(lower=0.01)).round(2).values
    saida["p_proprio"] = alvo.p_proprio.values
    saida["p_relativo"] = alvo.p_relativo.values
    saida["excesso_proprio"] = alvo.excesso_proprio.values
    saida["excesso_relativo"] = alvo.excesso_relativo.values
    # Só as células sinalizadas entram: publicar 947 mil linhas de não-achado
    # inflaria o arquivo sem acrescentar informação que o script não refaça.
    saida = (saida[saida.excesso_proprio | saida.excesso_relativo]
             .sort_values(["ano", "p_proprio"]).reset_index(drop=True))
    conferir_chave_unica("mart_anomalia_causa_municipio", saida,
                         ["municipio_cod", "ano", "causabas_3"])

    escrever_parquet(saida, MARTS / "mart_anomalia_causa_municipio.parquet",
                     origem="pipeline", produtor=PRODUTOR)
    print(f"[parquet] mart_anomalia_causa_municipio: {len(saida):,} linhas", flush=True)

    fontes = ["mart_mortalidade_causa_municipio"]
    registrar("anomalia_excessos_proprios", resumo["excesso_proprio"], fontes=fontes,
              descricao=f"células município×CID×ano com excesso sobre a própria história "
                        f"2015–2019 (binomial negativa, FDR {FDR:.0%})")
    registrar("anomalia_excessos_relativos", resumo["excesso_relativo"], fontes=fontes,
              descricao="o mesmo, descontada a variação nacional do CID no ano — "
                        "o escore útil para vigilância")
    registrar("anomalia_phi_mediana", resumo["phi_mediana"], fontes=fontes,
              descricao="dispersão temporal mediana por CID, estimada ano a ano dentro do "
                        "município; φ=1 seria Poisson puro")

    if args.no_upload:
        return
    env = carregar_env()
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    cab = {"apikey": key, "Authorization": f"Bearer {key}",
           "Content-Type": "application/json",
           "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = saida.astype(object).where(pd.notna(saida), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        r = requests.post(f"{url}/rest/v1/mart_anomalia_causa_municipio", headers=cab,
                          data=json.dumps(recs[i:i + 5000], allow_nan=False,
                                          default=lambda o: o.item() if hasattr(o, "item") else o),
                          timeout=300)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload: HTTP {r.status_code} {r.text[:200]}")
    print(f"[supabase]   mart_anomalia_causa_municipio: {len(recs):,} OK", flush=True)
    requests.post(f"{url}/rest/v1/meta_dataset", headers=cab, timeout=60,
                  data=json.dumps([{"chave": "gerado_em",
                                    "valor": datetime.now().isoformat(timespec="seconds")}]))
    print("[done] anomalias de causa concluídas.", flush=True)


if __name__ == "__main__":
    main()
