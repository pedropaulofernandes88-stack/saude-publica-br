"""
analise_contexto_social.py — o outro espaço de atributos, e o cruzamento
=========================================================================

O desenho original oferecia duas matérias-primas para a análise não
supervisionada: mortalidade **ou contexto social**. `analise_perfil_mortalidade.py`
faz a primeira. Este arquivo faz a segunda, e depois cruza as duas — que é onde
a pergunta fica interessante.

Quinze variáveis municipais de contexto social e de sistema de saúde,
padronizadas e decompostas em componentes principais:

    dim_ivs                      analfabetismo, domicílios sem água, IVS
    mart_cobertura_icsap         cobertura da atenção primária
    mart_leitos_icsap            leitos SUS por mil habitantes
    mart_siops_icsap             gasto próprio, transferência SUS, receita própria
    mart_saude_suplementar_icsap vínculos de plano por 100 habitantes
    mart_cnes                    estabelecimentos e hospitais por 10 mil hab.
    mart_natalidade              baixo peso, prematuridade, pré-natal 7+ consultas
    dim_populacao                log da população

O QUE O CRUZAMENTO RESPONDE
---------------------------
Se os eixos de mortalidade fossem apenas um reflexo do contexto social, a
análise de mortalidade não acrescentaria nada — bastaria olhar o IVS. Se fossem
independentes, o perfil de causas seria uma dimensão nova.

Medido: o maior |r| entre os seis eixos de mortalidade e os quatro sociais é
**0,46**, entre o PC1 de mortalidade e o eixo social de vulnerabilidade. Há
alinhamento substancial (r² = 0,21) e sobra bastante variação não explicada.
As duas leituras são parcialmente redundantes e parcialmente complementares.

O TESTE QUE ESTE ARQUIVO EXISTE PARA FAZER
-------------------------------------------
`analise_perfil_mortalidade.py` achou que o eixo principal do perfil de causas
é, em quase um terço, imprecisão de codificação. Ficou uma interpretação
alternativa em aberto e declarada: imprecisão diagnóstica pode não ser
artefato, e sim falta de recurso diagnóstico — sem tomografia não se distingue
acidente vascular isquêmico de hemorrágico, e o óbito vira I64.

Este é o teste direto dessa alternativa, e o resultado é específico:

    analfabetismo                   r = +0,56
    IVS                             r = +0,48
    estabelecimentos por 10 mil     r = -0,42
    vínculos de plano por 100 hab   r = -0,42
    gasto próprio em saúde          r = -0,39
    pré-natal com 7+ consultas      r = -0,30
    LEITOS SUS por mil              r = -0,09
    HOSPITAIS por 10 mil            r = -0,02
    log da população                r = +0,01

A imprecisão acompanha **vulnerabilidade social e densidade de atenção
ambulatorial**, e é praticamente indiferente a leito hospitalar e a porte do
município. Isso desfavorece a leitura de "falta de equipamento hospitalar" e
favorece a de gradiente socioeconômico com acesso ambulatorial — mas não separa
artefato de acesso real, e o cabeçalho de `analise_perfil_mortalidade.py`
continua declarando que a separação exige informação que a base não tem.

Uso:
  .venv311/Scripts/python scripts/analise_contexto_social.py
  .venv311/Scripts/python scripts/analise_contexto_social.py --no-upload
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
PRODUTOR = "scripts/analise_contexto_social.py"

#: Eixos sociais publicados. Os quatro primeiros somam 61,5% da variância; do
#: quinto em diante cada um fica abaixo de 7% e não tem leitura estável.
N_EIXOS = 4

#: De onde vem cada variável. Lista explícita, e não "tudo que houver", porque
#: a composição do espaço de atributos É a análise: incluir mais uma variável
#: de sistema de saúde deslocaria os eixos.
FONTES: list[tuple[str, list[str]]] = [
    ("dim_ivs", ["taxa_analfabetismo", "pct_sem_agua", "ivs_score"]),
    ("mart_cobertura_icsap_municipio", ["cobertura_pct"]),
    ("mart_leitos_icsap_municipio", ["leitos_sus_por_mil", "populacao"]),
    ("mart_siops_icsap_municipio", ["gasto_proprio_saude_hab", "transf_sus_hab",
                                    "pct_receita_propria_saude"]),
    ("mart_saude_suplementar_icsap_municipio", ["vinculos_plano_por_100_hab"]),
    ("mart_cnes_municipio", ["estabelecimentos_total", "estabelecimentos_hospitalares"]),
]

#: Variáveis com as quais o índice de inespecificidade é confrontado, na ordem
#: em que o resultado é lido. As duas últimas são as que mais informam por
#: serem NULAS — ver o cabeçalho.
INFRAESTRUTURA = ["taxa_analfabetismo", "ivs_score", "estab_por_10k",
                  "vinculos_plano_por_100_hab", "gasto_proprio_saude_hab",
                  "pct_prenatal_7mais", "cobertura_pct", "leitos_sus_por_mil",
                  "hosp_por_10k", "log_pop"]


def carregar_contexto() -> pd.DataFrame:
    partes = []
    for arquivo, colunas in FONTES:
        d = pd.read_parquet(MARTS / f"{arquivo}.parquet").set_index("municipio_cod")
        partes.append(d[colunas])
    x = pd.concat(partes, axis=1)

    nat = pd.read_parquet(MARTS / "mart_natalidade_municipio.parquet")
    nat = (nat[nat.ano == nat.ano.max()].set_index("municipio_cod")
           [["pct_baixo_peso", "pct_prematuro", "pct_prenatal_7mais"]])
    x = x.join(nat)

    # `astype(float)` depois do `to_numeric`: as colunas do SIOPS chegam como
    # object com NA do pandas, e o SVD recusa dtype object com uma mensagem que
    # não menciona a coluna culpada.
    x = x.apply(pd.to_numeric, errors="coerce")
    x["estab_por_10k"] = 1e4 * x.estabelecimentos_total / x.populacao
    x["hosp_por_10k"] = 1e4 * x.estabelecimentos_hospitalares / x.populacao
    x["log_pop"] = np.log10(x.populacao)
    return x.drop(columns=["estabelecimentos_total", "estabelecimentos_hospitalares",
                           "populacao"]).astype(float)


def eixos(x: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    z = ((x - x.mean()) / x.std()).values
    z = z - z.mean(axis=0)
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    var = s**2 / (s**2).sum()
    cargas = pd.DataFrame(vt[:N_EIXOS].T, index=x.columns,
                          columns=[f"spc{i + 1}" for i in range(N_EIXOS)])
    return (u * s)[:, :N_EIXOS], var, cargas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    perfil = (pd.read_parquet(MARTS / "mart_perfil_mortalidade_municipio.parquet")
              .set_index("municipio_cod"))
    x = carregar_contexto()
    x = x.loc[x.index.intersection(perfil.index)].dropna()
    perfil = perfil.loc[x.index]
    print(f"[base] {len(x):,} municípios × {x.shape[1]} variáveis de contexto", flush=True)

    escores, var, cargas = eixos(x)
    print(f"[eixos] variância {np.round(var[:6], 3)} | soma dos {N_EIXOS} primeiros "
          f"{var[:N_EIXOS].sum():.3f}", flush=True)
    for c in cargas.columns:
        ordenado = cargas[c].sort_values()
        print(f"[eixos]   {c}: (−) {', '.join(ordenado.index[:3])} "
              f"| (+) {', '.join(ordenado.index[-3:][::-1])}", flush=True)

    mort = perfil[[f"pc{i}" for i in range(1, 7)]].values.astype(float)
    cruz = pd.DataFrame(
        [[float(np.corrcoef(mort[:, i], escores[:, j])[0, 1]) for j in range(N_EIXOS)]
         for i in range(mort.shape[1])],
        index=[f"pc{i + 1}_mortalidade" for i in range(mort.shape[1])],
        columns=[f"spc{j + 1}" for j in range(N_EIXOS)])
    maior = float(np.abs(cruz.values).max())
    print(f"[cruzamento] maior |r| entre eixos de mortalidade e sociais: {maior:.3f}",
          flush=True)
    print(cruz.round(3).to_string(), flush=True)

    inesp = perfil.indice_inespecificidade.astype(float)
    print("[codificação] índice de inespecificidade contra o contexto:", flush=True)
    correl = {}
    for v in INFRAESTRUTURA:
        correl[v] = float(np.corrcoef(inesp, x[v])[0, 1])
        print(f"[codificação]   {v:<28} r = {correl[v]:+.3f}", flush=True)
    if abs(correl["log_pop"]) > 0.3:
        raise SystemExit(
            f"inespecificidade correlaciona {correl['log_pop']:+.3f} com o porte. O "
            "índice deveria ser praticamente ortogonal ao tamanho do município — "
            "porte já foi removido do perfil. Reveja antes de publicar.")

    saida = pd.DataFrame({"municipio_cod": x.index})
    for i in range(N_EIXOS):
        saida[f"spc{i + 1}"] = escores[:, i].round(4)
    for v in INFRAESTRUTURA:
        saida[v] = x[v].round(4).values
    conferir_chave_unica("mart_contexto_social_municipio", saida, ["municipio_cod"])
    escrever_parquet(saida, MARTS / "mart_contexto_social_municipio.parquet",
                     origem="pipeline", produtor=PRODUTOR)
    print(f"[parquet] mart_contexto_social_municipio: {len(saida):,} linhas", flush=True)

    fontes = ["mart_perfil_mortalidade_municipio"]
    registrar("contexto_maior_r_com_mortalidade", maior, fontes=fontes,
              descricao="maior correlação absoluta entre os seis eixos de perfil de causas e os "
                        "quatro eixos de contexto social — mede o quanto as duas leituras se "
                        "sobrepõem")
    registrar("inespecificidade_analfabetismo", correl["taxa_analfabetismo"], fontes=fontes,
              descricao="correlação do índice de inespecificidade de codificação com a taxa de "
                        "analfabetismo municipal")
    registrar("inespecificidade_leitos", correl["leitos_sus_por_mil"], fontes=fontes,
              descricao="correlação do índice de inespecificidade com leitos SUS por mil — quase "
                        "nula, o que desfavorece a leitura de falta de equipamento hospitalar")

    if args.no_upload:
        return
    env = carregar_env()
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    cab = {"apikey": key, "Authorization": f"Bearer {key}",
           "Content-Type": "application/json",
           "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = saida.astype(object).where(pd.notna(saida), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        r = requests.post(f"{url}/rest/v1/mart_contexto_social_municipio", headers=cab,
                          data=json.dumps(recs[i:i + 5000], allow_nan=False,
                                          default=lambda o: o.item() if hasattr(o, "item") else o),
                          timeout=300)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload: HTTP {r.status_code} {r.text[:200]}")
    print(f"[supabase]   mart_contexto_social_municipio: {len(recs):,} OK", flush=True)
    requests.post(f"{url}/rest/v1/meta_dataset", headers=cab, timeout=60,
                  data=json.dumps([{"chave": "gerado_em",
                                    "valor": datetime.now().isoformat(timespec="seconds")}]))
    print("[done] contexto social concluído.", flush=True)


if __name__ == "__main__":
    main()
