"""
pipeline_convenios.py — convênios federais de SAÚDE por município e ano
========================================================================

    python scripts/pipeline_convenios.py --no-upload

A VARREDURA DA API É PASSO SEPARADO deste script, e de propósito: ela leva
dezenas de minutos com limitador, grava um JSON por UF em `data/raw/CONVENIOS/`
e é retomável. Este pipeline só LÊ esses checkpoints. Separar evita que um erro
de agregação custe outra varredura inteira de um órgão público.

Produz:
  * `mart_convenios_municipio`  — município × ano × tipo de convenente
  * `mart_convenios_cobertura`  — uma linha por UF, dizendo o que foi coletado

Abre o eixo **dinheiro federal × território**, que nenhuma das treze fontes
anteriores cobre: elas descrevem óbito, internação, notificação, leito, dose e
exame. Fonte: API do Portal da Transparência (CGU), função SIAFI 10 (Saúde).

LEIA `scripts/sondar_convenios.py` ANTES DE MEXER AQUI
------------------------------------------------------
O portão de prontidão registra as três armadilhas da API que este pipeline
contorna, e por que o grão é município e não estabelecimento. Resumo do que
mata um coletor ingênuo:

  * `funcao=10` sozinho é HTTP 400 — a API exige âncora (aqui: `uf`);
  * `codigoIBGE` de SEIS dígitos devolve **200 com lista vazia**, e de sete
    devolve o dado. Por isso a varredura é por UF, e o município vem de dentro
    do registro (`municipioConvenente.codigoIBGE`), já com sete dígitos;
  * a API escreve `descricaoSubfuncap`, com typo.

POR QUE O GRÃO É MUNICÍPIO, E NÃO ESTABELECIMENTO
--------------------------------------------------
A ideia original era ligar convênio a hospital por CNPJ. Medido antes de
codificar, o casamento é de 15,6% a 20,1% por CONTAGEM — e de **5,9% por VALOR
pactuado** (R$ 174 mi de R$ 2,95 bi). A distância entre os dois é a resposta: o
que casa com um estabelecimento são os convênios PEQUENOS.

A razão é estrutural. No Acre, 93,9% dos convenentes são **administração
pública** — prefeitura ou secretaria, cujo CNPJ não é o de estabelecimento
nenhum; e no CNES apenas 7,7% dos estabelecimentos públicos têm CNPJ
preenchido.

A quebra por `tipo_convenente` substitui o cruzamento com vantagem: responde
"este dinheiro foi para a rede pública ou para filantrópicas?" sem depender de
casamento nenhum, e sem inventar precisão que a fonte não sustenta.

O EIXO TEMPORAL É `dataInicioVigencia`
---------------------------------------
100% preenchido, e é quando o convênio passa a valer. `dataPublicacao` também
serve e anda junto; `dataConclusao` falta em 15%; e `dataReferencia` **não** é
confiável como data do convênio: é majoritariamente o dia do retrato
(2026-09-11), mas traz também 1900-01-01 como sentinela de nulo.

Convênio é plurianual: um assinado em 2019 com vigência até 2021 não é "dinheiro
de 2019" em execução. Por isso o mart traz `ano` (do início da vigência) E as
colunas de vigência, e a metodologia tem de dizer que somar `valor_pactuado` por
ano descreve QUANDO SE ASSINOU, não quando se gastou.

O MUNICÍPIO É O DA SEDE DE QUEM ASSINOU, NÃO O DESTINO DO DINHEIRO
-------------------------------------------------------------------
**Esta é a ressalva que decide se o mart informa ou engana**, e não é caso de
borda: ela domina o topo do ranking.

`municipioConvenente.codigoIBGE` é o endereço cadastral do convenente. Medido
sobre os 21.023 convênios:

  * **Brasília aparece com R$ 32,25 bi — 45% de todo o dinheiro do país.** Não
    é saúde do Distrito Federal: são 90 dos 91 convênios com **organizações
    internacionais** (R$ 31,71 bi), que têm escritório em Brasília e executam
    programas nacionais;
  * **Dourados-MS, 200 mil habitantes, aparece com R$ 4,46 bi.** São 37
    convênios da **Missão Evangélica Caiuá**, que opera saúde indígena em
    território de vários estados e tem sede lá.

Ou seja: um mapa de "investimento federal em saúde por município" construído
sobre este campo mostraria metade do dinheiro do Brasil caindo em Brasília, e
estaria errado de um jeito que parece plausível.

A leitura correta da coluna é **"valor comprometido com entidades sediadas
neste município"**. Quem quiser destino do gasto precisa de outra fonte — o
objeto do convênio traz o território, em texto livre, e isso é trabalho de
outra ordem.

PACTUADO ≠ LIBERADO
--------------------
`valor` é o pactuado; `valorLiberado` é o que saiu do caixa. Num registro real
do Acre: R$ 100.000 pactuados, R$ 48.050 liberados. As duas colunas viajam
juntas e `pct_executado` é derivada — publicar só uma delas seria publicar
intenção como se fosse execução.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _saida import Resultado  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "CONVENIOS"

#: Digitado aqui, e não lido de `_fontes.py`, pela mesma razão de ORDEM do
#: SISCAN: o registro exige que o id exista em `site/lib/fontes.ts`, e o site
#: exige que toda fonte declarada tenha tabela no manifesto. Enquanto o mart não
#: for publicado, declarar `convenios` quebraria a guarda do site.
#:
#: REMOVER daqui assim que `mart_convenios_municipio` for publicado: declarar
#: `convenios` em `_fontes.py` (api, https://api.portaldatransparencia.gov.br/
#: api-de-dados/convenios) e em `fontes.ts`, e trocar esta constante por
#: `fonte("convenios").local("api").caminho`.
API = "https://api.portaldatransparencia.gov.br/api-de-dados/convenios"

UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
       "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
       "SE", "SP", "TO"]

#: Os rótulos que a API usa em `convenente.tipo`, agrupados no que o mart
#: publica. O agrupamento é editorial e fica explícito: "Administração Pública"
#: sem qualificação aparece ao lado de "Municipal" e "Estadual ou do Distrito
#: Federal", e as três são poder público.
GRUPO_CONVENENTE = {
    "Administração Pública": "publico",
    "Administração Pública Municipal": "publico",
    "Administração Pública Estadual ou do Distrito Federal": "publico",
    "Administração Pública Federal": "publico",
    "Entidades Sem Fins Lucrativos": "sem_fins_lucrativos",
    "Entidades Empresariais Privadas": "empresarial",
    "Pessoas Físicas": "pessoa_fisica",
    # Grupo PRÓPRIO, e não jogado em "outro" nem somado ao público: são 91
    # convênios que concentram R$ 31,7 bi — 44% de todo o dinheiro federal de
    # saúde em convênios, R$ 349 milhões de média contra R$ 1,8 milhão dos
    # demais. Diluí-los em qualquer outro grupo apagaria o fato mais importante
    # desta fonte.
    "Organizações Internacionais": "organismo_internacional",
}


def _grupo(rotulo: str | None) -> str:
    """Grupo do convenente. Rótulo novo vira `outro`, e NÃO é silencioso:
    `guardas()` reprova se `outro` passar de 5% das linhas."""
    return GRUPO_CONVENENTE.get((rotulo or "").strip(), "outro")


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def ler_checkpoints() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Os JSON por UF → DataFrame de convênios, e a cobertura por UF.

    A cobertura existe pelo motivo de sempre: município sem convênio e município
    NÃO COLETADO viram a mesma ausência no mart. Sem esta tabela ao lado, ler
    "zero convênios" seria adivinhação.
    """
    linhas, cobertura = [], []
    for uf in UFS:
        arq = CKPT / f"convenios_saude_{uf}.json"
        if not arq.exists():
            cobertura.append({"uf_sigla": uf, "coletado": False, "convenios": 0})
            continue
        dados = json.loads(arq.read_text(encoding="utf-8"))
        cobertura.append({"uf_sigla": uf, "coletado": True, "convenios": len(dados)})
        for x in dados:
            conv = x.get("convenente") or {}
            mun = x.get("municipioConvenente") or {}
            cod7 = "".join(c for c in str(mun.get("codigoIBGE") or "") if c.isdigit())
            inicio = str(x.get("dataInicioVigencia") or "")
            linhas.append({
                "municipio_cod7": cod7,
                "ano": int(inicio[:4]) if inicio[:4].isdigit() else None,
                "grupo_convenente": _grupo(conv.get("tipo")),
                "tipo_convenente_bruto": (conv.get("tipo") or "").strip(),
                "valor_pactuado": _num(x.get("valor")),
                "valor_liberado": _num(x.get("valorLiberado")),
                "valor_contrapartida": _num(x.get("valorContrapartida")),
                "data_inicio_vigencia": inicio or None,
                "data_final_vigencia": x.get("dataFinalVigencia") or None,
            })
    return pd.DataFrame(linhas), pd.DataFrame(cobertura)


def agregar(bruto: pd.DataFrame) -> pd.DataFrame:
    """município × ano × grupo de convenente."""
    mref = pd.read_parquet(REFS / "municipios.parquet")[
        ["municipio_cod", "municipio_cod7", "municipio_nome", "uf_sigla", "regiao"]]
    d = bruto.dropna(subset=["ano"]).copy()
    d["ano"] = d["ano"].astype(int)

    g = (d.groupby(["municipio_cod7", "ano", "grupo_convenente"], as_index=False)
           .agg(convenios=("valor_pactuado", "size"),
                valor_pactuado=("valor_pactuado", "sum"),
                valor_liberado=("valor_liberado", "sum"),
                valor_contrapartida=("valor_contrapartida", "sum")))
    g = g.merge(mref, on="municipio_cod7", how="left")

    # pct_executado só onde há pactuado: dividir por zero inventaria 0% ou inf,
    # e as duas leituras são falsas para um convênio de valor zero.
    g["pct_executado"] = (
        (100 * g["valor_liberado"] / g["valor_pactuado"]).round(2)
        .where(g["valor_pactuado"] > 0)
    )
    return g[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano",
              "grupo_convenente", "convenios", "valor_pactuado", "valor_liberado",
              "valor_contrapartida", "pct_executado", "municipio_cod7"]]


def guardas(mart: pd.DataFrame, bruto: pd.DataFrame, cob: pd.DataFrame) -> None:
    """Reprova o que passaria calado."""
    nao_coletadas = cob.loc[~cob["coletado"], "uf_sigla"].tolist()
    if nao_coletadas:
        raise SystemExit(
            f"UFs sem checkpoint: {nao_coletadas}. Publicar assim faria o mart "
            f"dizer que esses estados não têm convênio de saúde. Feche a "
            f"varredura antes — a cobertura parcial fica em mart_convenios_"
            f"cobertura, mas o mart principal não sai pela metade."
        )

    orfaos = mart["municipio_cod"].isna().sum()
    if orfaos:
        pct = 100 * orfaos / len(mart)
        if pct > 2.0:
            raise SystemExit(
                f"{orfaos} linhas ({pct:.1f}%) sem município na dimensão IBGE. "
                f"Acima de 2% isto não é ruído de código antigo — é chave errada."
            )
        print(f"[convenios] {orfaos} linhas sem município na dimensão ({pct:.2f}%)")

    # Por CONTAGEM **e** por VALOR, e a segunda não é zelo: na primeira
    # execução desta guarda, "Organizações Internacionais" eram 0,43% dos
    # convênios — passando folgado num corte de 5% — e **44% do dinheiro**,
    # R$ 31,7 bi num balde chamado `outro`. Contagem e valor respondem coisas
    # diferentes nesta fonte, e a guarda que olha só uma delas é cega para a
    # outra. Mesma lição do casamento por CNPJ, medido no mesmo dia.
    fora = bruto["grupo_convenente"] == "outro"
    desconhecidos = bruto.loc[fora, "tipo_convenente_bruto"].value_counts()
    pct_conta = fora.mean() * 100
    total_valor = bruto["valor_pactuado"].sum()
    pct_valor = (100 * bruto.loc[fora, "valor_pactuado"].sum() / total_valor
                 if total_valor else 0.0)
    if pct_conta > 5.0 or pct_valor > 5.0:
        raise SystemExit(
            f"rótulo de convenente fora de GRUPO_CONVENENTE: {pct_conta:.2f}% dos "
            f"convênios e {pct_valor:.2f}% do valor. Classificar em silêncio é pior "
            f"que parar. Rótulos: {dict(desconhecidos.head(8))}"
        )
    if len(desconhecidos):
        print(f"[convenios] rótulos fora do mapa: {pct_conta:.2f}% dos convênios, "
              f"{pct_valor:.2f}% do valor — {dict(desconhecidos.head(5))}")

    if (mart["valor_liberado"] > mart["valor_pactuado"] * 1.01).any():
        n = int((mart["valor_liberado"] > mart["valor_pactuado"] * 1.01).sum())
        print(f"[convenios] ATENÇÃO: {n} linhas com liberado > pactuado. "
              f"Ocorre em aditivo não refletido em `valor`; não é erro de soma.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    res = Resultado("scripts/pipeline_convenios.py")

    bruto, cob = ler_checkpoints()
    if bruto.empty:
        raise SystemExit(
            f"nenhum checkpoint em {CKPT}. A varredura da API é passo separado — "
            f"veja o cabeçalho e `scripts/sondar_convenios.py`."
        )
    mart = agregar(bruto)
    guardas(mart, bruto, cob)

    print(f"[convenios] {len(bruto):,} convênios de saúde | "
          f"{mart['municipio_cod'].nunique():,} municípios | "
          f"{mart['ano'].min()}–{mart['ano'].max()}")
    print(f"[convenios] pactuado R$ {mart['valor_pactuado'].sum()/1e9:,.2f} bi | "
          f"liberado R$ {mart['valor_liberado'].sum()/1e9:,.2f} bi "
          f"({100*mart['valor_liberado'].sum()/mart['valor_pactuado'].sum():.1f}%)")
    for grupo, sub in mart.groupby("grupo_convenente"):
        print(f"[convenios]   {grupo:<22} {sub['convenios'].sum():>7,} convênios | "
              f"R$ {sub['valor_pactuado'].sum()/1e9:>6,.2f} bi pactuados")

    MARTS.mkdir(parents=True, exist_ok=True)
    res.gravar(mart.drop(columns=["municipio_cod7"]),
               MARTS / "mart_convenios_municipio.parquet")
    res.gravar(cob, MARTS / "mart_convenios_cobertura.parquet")
    print(f"[ok] marts em {MARTS}")
    return res.relatar()


if __name__ == "__main__":
    sys.exit(main())
