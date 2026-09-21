"""
analise_cauda_de_reporte.py — quanto do horizonte de previsão nasce vencido
===========================================================================

    python scripts/analise_cauda_de_reporte.py

A PERGUNTA
----------
Uma previsão sobre dado administrativo precisa de uma âncora: a competência
mais recente considerada COMPLETA. Mas a competência só fica completa com o
tempo, e enquanto isso o relógio anda. A previsão ancorada no último mês
completo cobre, em boa parte, meses que **já aconteceram** quando ela é
publicada.

Este script mede a cauda de reporte de duas fontes com caudas deliberadamente
diferentes e formaliza a tensão que elas revelam.

A TENSÃO, EM QUATRO LINHAS
--------------------------
Seja `τ(a)` a completude de uma competência com `a` períodos de idade, e `θ` o
critério de completude exigido pela âncora. Defina

    A(θ) = menor idade `a` tal que τ(a) ≥ θ        (a defasagem imposta por θ)

No instante `T` a âncora é a competência `T − A(θ)`. Uma previsão de horizonte
`H` cobre `[T − A(θ) + 1, T − A(θ) + H]`, e destes os primeiros `min(H, A(θ))`
períodos **já estão no passado**. Logo a fração útil do horizonte é

    U(θ, H) = max(0, H − A(θ)) / H

`τ` é não decrescente em `a`, portanto `A` é **não decrescente em θ** e `U` é
**não crescente em θ**. Isto é uma propriedade da definição, não do dado:

    quanto mais exigente o critério de completude, menos horizonte útil sobra —
    e U(θ, H) = 0 sempre que H ≤ A(θ).

Não há escolha de θ que escape: afrouxá-lo devolve horizonte às custas de
ancorar em competência incompleta, que é o defeito que θ existia para evitar.
A única saída real é fora do eixo — nowcasting, ou seja, modelar τ e corrigir a
competência incompleta em vez de descartá-la.

O TETO QUE A MEDIÇÃO ACRESCENTOU
--------------------------------
τ oscila mesmo em competências já assentadas, onde por definição não há
incompletude. Chame de **piso de ruído** o τ do 5º percentil entre elas.
Critério acima do piso não é mensurável: "incompleto" e "oscilou" ficam
indistinguíveis, e reportar A(θ) ali é inventar precisão.

Medido em 2026-09-21:

    SIH/SUS       piso 98,6%   A(0,90)=1  A(0,95)=2   θ=0,99 NÃO é mensurável
    InfoDengue    piso 67,7%   nenhum critério usual se sustenta

O 99% que qualquer pipeline sério escreveria no código está **acima** do que o
SIH permite verificar. E com θ = 0,95, U(θ,1) = 0 e U(θ,3) = 33%: a previsão de
um mês é inteiramente retrospectiva, e a de três meses entrega um mês.

O QUE ESTE SCRIPT NÃO RESOLVE
-----------------------------
`τ` é medida de um ÚNICO retrato, comparando competências de idades diferentes.
Isso confunde idade com identidade: uma unidade que fechou de verdade aparece
como incompletude. O controle usado aqui é a forma da curva — a contagem volta a
um platô estável nas competências mais velhas, e nenhum processo real derruba
15% dos hospitais de um mês para o outro. Um controle de fato exigiria retratos
datados da MESMA competência ao longo do tempo, que o projeto só passou a
guardar em 2026-08 (`data/observacoes/`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
MARTS = RAIZ / "data" / "marts"

#: Critérios de completude examinados. 0,99 é o que qualquer pipeline sério
#: escolheria; 0,80 é o mais frouxo que ainda se defende em público.
CRITERIOS = (0.80, 0.90, 0.95, 0.99)

#: Horizontes examinados, na unidade de cada fonte.
HORIZONTES = (1, 3, 6, 12)

#: Quantos períodos do fim da série entram na medição da cauda. O resto define
#: o platô.
JANELA_CAUDA = 12


def _completude(serie: pd.Series, periodos_por_ano: int) -> tuple[pd.DataFrame, float]:
    """τ(a) a partir de uma série ordenada de contagem de unidades reportando.

    POR QUE NÃO É SÓ "DIVIDIR PELO PLATÔ"
    -------------------------------------
    A primeira versão deste script comparava a cauda com a mediana dos períodos
    anteriores. Funcionava no SIH e **mentia no InfoDengue**: as semanas 23–34
    são a baixa estação da dengue, e a queda de municípios com caso que eu
    estava medindo como incompletude era o verão tendo acabado. Dava A(0,99) =
    "nunca" para uma fonte cuja cauda real é de uma semana.

    A medida aqui é a razão ano a ano — `unidades(c) / unidades(c − 1 ano)` —
    normalizada pela mediana dessa razão nos períodos já assentados. Isso
    neutraliza sazonalidade E tendência de uma vez: uma competência completa tem
    razão igual à das suas vizinhas assentadas, cresça a série ou não.
    """
    if len(serie) <= periodos_por_ano + JANELA_CAUDA:
        raise ValueError("série curta demais para razão ano a ano mais cauda")
    razao = (serie / serie.shift(periodos_por_ano)).dropna()
    if len(razao) <= JANELA_CAUDA:
        raise ValueError("série curta demais para separar cauda de assentado")

    velhos = razao.iloc[:-JANELA_CAUDA]
    assentado = float(velhos.median())
    cauda = razao.iloc[-JANELA_CAUDA:]

    # Piso de ruído: o quanto τ já oscila em competências ASSENTADAS, onde por
    # definição não há incompletude. Nenhum critério θ acima deste piso é
    # mensurável — a diferença entre "incompleto" e "oscilou" some no ruído, e
    # reportar A(θ) ali é inventar precisão. É o que separa uma fonte
    # administrativa estável de uma série epidêmica.
    piso = float((velhos / assentado).quantile(0.05))

    tau = pd.DataFrame({
        "periodo": cauda.index,
        "idade": list(range(len(cauda) - 1, -1, -1)),   # 0 = a mais recente
        "unidades": serie.reindex(cauda.index).to_numpy(),
        "razao_aa": cauda.to_numpy(),
        "tau": cauda.to_numpy() / assentado,
    }).sort_values("idade").reset_index(drop=True)
    tau.attrs["piso_de_ruido"] = piso
    return tau, assentado


def defasagem(tau: pd.DataFrame, criterio: float) -> int | None:
    """A(θ): menor idade a partir da qual τ ≥ θ e NÃO volta a cair.

    O "não volta a cair" importa: τ oscila em torno de 1 nas competências já
    assentadas, e pegar o primeiro cruzamento isolado devolveria defasagem
    otimista por acidente de ruído.
    """
    ok = tau.tau >= criterio
    for i in range(len(tau)):
        if ok.iloc[i:].all():
            return int(tau.idade.iloc[i])
    return None


def fracao_util(a: int | None, h: int) -> float:
    """U(θ, H). `None` (critério nunca atingido) devolve 0 por definição."""
    if a is None:
        return 0.0
    return max(0, h - a) / h


def _tabela(nome: str, unidade: str, serie: pd.Series,
            periodos_por_ano: int) -> pd.DataFrame:
    tau, assentado = _completude(serie, periodos_por_ano)
    print(f"\n=== {nome} — {unidade} ===")
    print(f"razão ano a ano dos períodos assentados (mediana): {assentado:.3f}")
    print(tau.assign(tau=lambda d: (100 * d.tau).round(1),
                     razao_aa=lambda d: d.razao_aa.round(3))
          .rename(columns={"tau": "tau_%"}).to_string(index=False))

    piso = tau.attrs["piso_de_ruido"]
    print(f"\npiso de ruído (τ do 5º percentil já assentado): {100 * piso:.1f}%")
    print("\n  θ      A(θ)   " + "".join(f"U(θ,{h:>2})  " for h in HORIZONTES))
    for c in CRITERIOS:
        if c > piso:
            print(f"  {c:.2f}  indistinguível do ruído desta fonte")
            continue
        a = defasagem(tau, c)
        celulas = "".join(f"{100 * fracao_util(a, h):>6.0f}%  " for h in HORIZONTES)
        rotulo = "nunca" if a is None else f"{a:>5}"
        print(f"  {c:.2f}  {rotulo}   {celulas}")

    # A monotonicidade é da definição, mas vale ver o dado obedecendo.
    defs = [defasagem(tau, c) for c in CRITERIOS if c <= piso]
    finitos = [d for d in defs if d is not None]
    if finitos != sorted(finitos):
        raise SystemExit(
            f"[cauda] {nome}: A(θ) não é monótona em θ ({defs}). Isso é "
            "impossível pela definição — ou `defasagem` está errada, ou τ não "
            "é o que se pensa que é.")
    return tau


def main() -> int:
    # --- SIH: cauda longa, e a contagem de unidades é o que a denuncia ------
    sih = pd.read_parquet(MARTS / "mart_demanda_mensal_hospital.parquet")
    hosp = sih.groupby("ano_mes")["cnes"].nunique().sort_index()
    tau_h = _tabela("SIH/SUS (internações)",
                    "hospitais que reportaram, por competência", hosp, 12)

    # O volume NÃO denuncia: é a razão de a guarda precisar contar unidades.
    vol = sih.groupby("ano_mes")["internacoes"].sum().sort_index()
    tau_v, _ = _completude(vol, 12)
    print("\n  a mesma cauda, medida por VOLUME em vez de unidades:")
    comp = pd.DataFrame({
        "idade": tau_h.idade,
        "tau_unidades_%": (100 * tau_h.tau).round(1),
        "tau_volume_%": (100 * tau_v.tau).round(1),
    })
    print(comp.to_string(index=False))
    print("  Contagem de linhas não detecta o que a contagem de unidades "
          "detecta — o volume fica em torno de 100% enquanto 15% dos hospitais "
          "faltam, porque quem falta é pequeno.")

    # --- InfoDengue: cauda curta de propósito -------------------------------
    den = pd.read_parquet(MARTS / "mart_dengue_uf_semana.parquet")
    den = den[den.ano_epi >= 2023].copy()
    den["periodo"] = (den.ano_epi.astype(str) + "-S"
                      + den.semana_epi.astype(int).astype(str).str.zfill(2))
    mun = den.groupby("periodo")["municipios_com_casos"].sum().sort_index()
    _tabela("InfoDengue (arboviroses)", "municípios com caso, por semana epi",
            mun, 52)

    print("\n--- o que as duas juntas dizem ---")
    print("1. A tensão não é peculiaridade do SIH. A forma aparece nas duas: a")
    print("   competência mais recente está visivelmente incompleta (τ = 84,1%")
    print("   no SIH, 79,7% no InfoDengue) e sobe com a idade.")
    print("2. O que muda entre fontes não é a existência da cauda, é A(θ) — e")
    print("   com ele a fração útil. No SIH, θ = 0,95 já zera o horizonte de um")
    print("   mês e deixa um terço do de três.")
    print("3. E há um teto que o achado original não tinha: **θ não pode passar")
    print("   do piso de ruído da própria fonte.** No SIH esse piso é 98,6%, ou")
    print("   seja, o critério de 99% que qualquer pipeline sério escolheria")
    print("   NÃO É MENSURÁVEL — a diferença entre 'incompleto' e 'oscilou'")
    print("   some. No InfoDengue o piso é 67,7% e nenhum critério usual se")
    print("   sustenta, porque a amplitude entre anos epidêmicos engole tudo.")
    print("4. Logo o estimador de τ por retrato único exige base ano a ano")
    print("   estável. Onde ela não existe, a cauda é visível e não é")
    print("   quantificável — o que é um limite do método, não da fonte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
