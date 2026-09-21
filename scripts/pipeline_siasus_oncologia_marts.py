"""
pipeline_siasus_oncologia_marts.py — os checkpoints do SIA/APAC viram mart
==========================================================================

    python scripts/pipeline_siasus_oncologia_marts.py

Produz:
  * `mart_apac_oncologia_tratamento` — município de RESIDÊNCIA × ano × modalidade ×
                                  CID-3 × estadiamento
  * `mart_apac_oncologia_fluxo`      — município de residência → município de
                                  atendimento, por ano e modalidade
  * `mart_apac_oncologia_cobertura`  — UF × ano × modalidade: o que foi coletado

POR QUE ESTE SCRIPT É SEPARADO DA COLETA
-----------------------------------------
`pipeline_siasus_oncologia.py` leva TRÊS HORAS para varrer 14 anos × 27 UFs ×
12 meses × 2 modalidades no FTP. Se a agregação morasse lá, cada erro de
agregação custaria outra varredura do FTP de um órgão público. Mesma razão pela
qual a varredura dos convênios não mora em `pipeline_convenios.py`: aqui só se
LÊ checkpoint.

E não é hipótese. A primeira coleta inteira foi descartada porque `_estadio("")`
devolvia `"0"` — ausência de estadiamento publicada como carcinoma in situ. O
conserto era de três linhas e mesmo assim custou a coleta toda.

O CARIMBO DE ANO PARCIAL
-------------------------
`meses_cobertos` vai como COLUNA, seguindo V046 (SIH) e o mart da sífilis: quem
lê UMA linha — pelo Parquet, pela API ou pelo CSV — vê a ressalva junto do
número que ela qualifica, sem depender de rodapé que ninguém lê. 2026 tem SETE
meses publicados; plotar seus 3,1 mi de APACs ao lado dos 5,1 mi de 2025 desenha
uma queda de 40% que não existe.

O grão do carimbo é NACIONAL por ano × modalidade, e não por UF como no SIH.
A razão é o próprio dado: 55% das APACs são de paciente tratado fora do seu
município, e o arquivo do FTP é organizado pela UF do ESTABELECIMENTO enquanto
o mart é pela UF de RESIDÊNCIA. Carimbar a linha com a cobertura da UF onde o
paciente MORA descreveria um arquivo que não produziu aquele registro — um
residente de Tocantins tratado em Goiás veio do arquivo de GO.

O número sai do máximo de `meses_coletados` entre as UFs daquele ano e
modalidade. Isso iguala a contagem de meses publicados no FTP a menos que UFs
diferentes publiquem conjuntos DISJUNTOS de meses, o que não ocorre: um mês
publicado aparece em dezenas de UFs ao mesmo tempo. A guarda
`_carimbo_so_cai_na_ponta` recusa ano fechado com menos de 12.

INTERMITÊNCIA DE UF NÃO É ANO PARCIAL
--------------------------------------
26 pares UF × ano × modalidade têm menos de 12 meses fora de 2026 — AP com UM
mês de radioterapia em 2025, AC com um em 2018. Nenhum é falha de coleta (o
total de `meses_com_falha` é ZERO nos 14 anos): é serviço que não existia ou
não faturou. AP não teve radioterapia nenhuma de 2013 a 2021. Isso é achado,
não defeito, e mora inteiro em `mart_apac_oncologia_cobertura` — diluí-lo no carimbo
nacional apagaria a estreia do serviço no Amapá.

OS CÓDIGOS QUE NÃO SÃO MUNICÍPIO DO IBGE
-----------------------------------------
37 códigos, 73.479 APACs (0,14%), em três famílias: `UF+0000` (município
ignorado dentro da UF), Regiões Administrativas do DF (o DataSUS codifica
Ceilândia à parte; o IBGE só tem 530010) e municípios extintos. Ficam no mart —
são tratamentos que aconteceram — mas NÃO passam por município do IBGE.

A `uf_sigla` é derivada dos dois primeiros dígitos do código, e não do join com
a dimensão, justamente para que esses 73 mil não sumam da leitura por UF: a UF
se sabe em todos eles. Sem isso o DF perderia 32.009 APACs das suas Regiões
Administrativas — 7% do próprio DF — numa agregação estadual.

O que NÃO se sabe é o município, e aí `municipio_nome` fica NULO. Nulo é "não
sei qual"; escolher um seria inventar.

O PREFIXO `mart_apac_` NÃO É ENFEITE
------------------------------------
Já existem `mart_oncologia_municipio` e `mart_oncologia_estadiamento`, do
PAINEL DE ONCOLOGIA — outra fonte, cobrindo os mesmos anos (2013-2026), o mesmo
grão municipal e o mesmo assunto. Os universos não são comparáveis:

    Painel   conta CASOS de pessoas diagnosticadas, inclui D00-D48, e tem
             51% de estadiamento AUSENTE.
    APAC/SIA conta AUTORIZAÇÕES de tratamento, e tem 12,3% ausente.

Quem lesse `mart_oncologia_estadiamento` ao lado de `mart_oncologia_tratamento`
pelo prefixo comum concluiria que o registro de estadiamento melhorou quatro
vezes. Não melhorou: são coisas diferentes contadas de formas diferentes. O
nome carrega a fonte porque documentação não alcança quem lista o diretório.

O CID-3 `000` É AUSÊNCIA, E NÃO COLIDE
---------------------------------------
3.530 APACs (0,007%) vêm sem `AP_CIDPRI`. Diferente do estadiamento, aqui a
ausência não tem como se disfarçar de valor real: não existe CID-10 começando
por dígito, então `000` é inequívoco. Fica documentado mesmo assim, porque a
lição do estádio 0 é que ninguém confere o que parece óbvio.

Os CID fora de C/D são 0,03% e são REAIS, não lixo: L91 (cicatriz
hipertrófica), Z51 (sessão de radioterapia), N62, Q28 — radioterapia de
condição benigna é indicação legítima.
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _saida import Resultado  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "SIASUS" / "onco_ckpt"

ANOS_ESPERADOS = list(range(2013, 2027))

#: Chaves naturais. Conferidas antes de gravar: duplicata aqui é dado somado
#: duas vezes, e contagem de linhas não a detecta — ela se cancela com ausência.
PK = {
    "tratamento": ["municipio_cod", "ano", "modalidade", "cid3", "estadiamento"],
    "fluxo": ["municipio_res", "municipio_mov", "ano", "modalidade"],
    "cobertura": ["uf_sigla", "ano", "modalidade"],
}


def _ler(padrao: str) -> pd.DataFrame:
    arquivos = sorted(glob.glob(str(CKPT / padrao)))
    if not arquivos:
        raise SystemExit(
            f"nenhum checkpoint {padrao} em {CKPT}. A coleta é passo separado: "
            f"python scripts/pipeline_siasus_oncologia.py --ano-inicio 2013 --ano-fim 2026"
        )
    return pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)


def _dimensao() -> tuple[pd.DataFrame, dict[str, str]]:
    """A dimensão de municípios, e o mapa código-de-UF → sigla tirado dela."""
    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")
    dim["municipio_cod"] = dim["municipio_cod"].astype(str)
    uf_por_prefixo = (dim.assign(pre=dim["municipio_cod"].str[:2])
                         .drop_duplicates("pre")
                         .set_index("pre")["uf_sigla"].to_dict())
    return dim, uf_por_prefixo


def _meses_cobertos(cob: pd.DataFrame) -> pd.DataFrame:
    """Meses publicados no país, por ano × modalidade. Ver o cabeçalho."""
    m = (cob.groupby(["ano", "modalidade"])["meses_coletados"].max()
            .rename("meses_cobertos").reset_index())
    m["meses_cobertos"] = m["meses_cobertos"].astype("Int64")
    return m


def _carimbo_so_cai_na_ponta(m: pd.DataFrame) -> None:
    """Ano parcial NO MEIO da série é buraco; na ponta, é o calendário.

    Regra copiada do mart da sífilis. O último ano é sempre retrato em
    andamento e reprovar isso seria reprovar a atualidade. Um ano ANTERIOR com
    menos de doze meses é coleta incompleta se passando por ano fechado — o
    defeito que nenhuma contagem de linhas pega.
    """
    ultimo = int(m["ano"].max())
    furados = m[(m["meses_cobertos"] < 12) & (m["ano"] != ultimo)]
    if len(furados):
        raise SystemExit(
            "[onco] ano fechado com menos de 12 meses publicados: "
            f"{furados[['ano', 'modalidade', 'meses_cobertos']].to_dict('records')} "
            "— o checkpoint não cobre o ano que o nome promete."
        )


def _sem_duplicata(df: pd.DataFrame, chave: list[str], rotulo: str) -> None:
    n = int(df.duplicated(subset=chave).sum())
    if n:
        raise SystemExit(
            f"[onco] {rotulo}: {n:,} linhas duplicadas na chave {chave}. "
            "Duplicata é dado somado duas vezes, e a contagem de linhas não a "
            "denuncia — ela se cancela com ausência."
        )


def _ausencia_de_estadiamento_tem_rotulo(trat: pd.DataFrame) -> None:
    """A guarda que existe por um defeito meu, e a única que olha ANO A ANO.

    `_estadio("")` devolvia `"0"`, e estádio 0 é carcinoma in situ — ausência
    virava diagnóstico precoce. O que denunciou não foi teste: foi comparar a
    distribuição do ano coletado com os 84% de preenchimento que a sondagem
    tinha medido. Um ano com 100% de estadiamento é impossível nesta fonte.

    Ano a ano de propósito: 2014 sobreviveu ao conserto porque foi pulado por
    checkpoint, e um agregado nacional o teria escondido atrás dos outros 13.
    """
    for ano, sub in trat.groupby("ano"):
        ign = sub.loc[sub["estadiamento"] == "ignorado", "apacs"].sum()
        pct = 100 * ign / sub["apacs"].sum()
        if pct == 0:
            raise SystemExit(
                f"[onco] {ano}: NENHUMA APAC com estadiamento 'ignorado'. Esta "
                "fonte tem ~12% de ausência em todos os anos; zero significa que "
                "a ausência foi somada a algum estádio real. Recolete o ano."
            )
        if pct > 40:
            raise SystemExit(
                f"[onco] {ano}: {pct:.1f}% sem estadiamento. A sondagem mediu ~16% "
                "de ausência; o triplo disso é leitura do campo errado."
            )


def montar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trat, fluxo, cob = _ler("tratamento_*.parquet"), _ler("fluxo_*.parquet"), _ler("cobertura_*.parquet")

    faltam = sorted(set(ANOS_ESPERADOS) - set(trat["ano"].unique()))
    if faltam:
        raise SystemExit(f"[onco] anos sem checkpoint: {faltam}. Colete antes de agregar.")

    falhas = int(cob["meses_com_falha"].sum())
    if falhas:
        ruins = cob[cob["meses_com_falha"] > 0][["uf_sigla", "ano", "modalidade", "meses_com_falha"]]
        raise SystemExit(
            f"[onco] {falhas} mês(es) COM FALHA — arquivo que existe no FTP e não "
            f"foi lido. Publicar assim é recorte incompleto com código 0:\n{ruins.to_string(index=False)}"
        )

    _ausencia_de_estadiamento_tem_rotulo(trat)
    meses = _meses_cobertos(cob)
    _carimbo_so_cai_na_ponta(meses)

    dim, uf_por_prefixo = _dimensao()
    nomes = dim.set_index("municipio_cod")["municipio_nome"]

    # -- tratamento ---------------------------------------------------------
    t = trat.copy()
    t["uf_sigla"] = t["municipio_cod"].str[:2].map(uf_por_prefixo)
    t["municipio_nome"] = t["municipio_cod"].map(nomes)
    t = t.merge(meses, on=["ano", "modalidade"], how="left")
    t = t[["municipio_cod", "municipio_nome", "uf_sigla", "ano", "modalidade",
           "cid3", "estadiamento", "apacs", "valor_aprovado", "meses_cobertos"]]
    t = t.sort_values(PK["tratamento"], ignore_index=True)

    # -- fluxo --------------------------------------------------------------
    f = fluxo.rename(columns={"municipio_cod_residencia": "municipio_res",
                              "municipio_cod_atendimento": "municipio_mov"}).copy()
    f["municipio_res_nome"] = f["municipio_res"].map(nomes)
    f["municipio_mov_nome"] = f["municipio_mov"].map(nomes)
    f["uf_res"] = f["municipio_res"].str[:2].map(uf_por_prefixo)
    f["uf_mov"] = f["municipio_mov"].str[:2].map(uf_por_prefixo)
    f = f.merge(meses, on=["ano", "modalidade"], how="left")
    f = f[["ano", "modalidade", "municipio_res", "municipio_res_nome", "uf_res",
           "municipio_mov", "municipio_mov_nome", "uf_mov",
           "apacs", "valor_aprovado", "meses_cobertos"]]
    f = f.sort_values(PK["fluxo"], ignore_index=True)

    c = cob.sort_values(PK["cobertura"], ignore_index=True)

    for df, rotulo in ((t, "tratamento"), (f, "fluxo"), (c, "cobertura")):
        _sem_duplicata(df, PK[rotulo], rotulo)

    # A soma tem de sobreviver à agregação: join que não casa some com linha.
    for antes, depois, rotulo in ((trat["apacs"].sum(), t["apacs"].sum(), "tratamento"),
                                  (fluxo["apacs"].sum(), f["apacs"].sum(), "fluxo")):
        if int(antes) != int(depois):
            raise SystemExit(
                f"[onco] {rotulo}: {int(antes):,} APACs no checkpoint e "
                f"{int(depois):,} no mart. O join perdeu linha."
            )
    return t, f, c


def relatar(t: pd.DataFrame, f: pd.DataFrame, c: pd.DataFrame) -> None:
    dim, _ = _dimensao()
    reais = set(dim["municipio_cod"])
    dentro = t[t["municipio_cod"].isin(reais)]
    fora = t[~t["municipio_cod"].isin(reais)]

    print(f"[onco] {len(t):,} linhas | {t['apacs'].sum():,} APACs | "
          f"R$ {t['valor_aprovado'].sum() / 1e9:,.1f} bi | "
          f"{t['ano'].min()}–{t['ano'].max()}")
    print(f"[onco] {dentro['municipio_cod'].nunique():,} municípios do IBGE "
          f"(de {len(reais):,} no país)")
    if len(fora):
        print(f"[onco] {fora['municipio_cod'].nunique()} códigos FORA da dimensão "
              f"({fora['apacs'].sum():,} APACs, {fora['apacs'].sum() / t['apacs'].sum():.3%}): "
              "município ignorado (UF+0000), Regiões Administrativas do DF e "
              "municípios extintos. Ficam no mart; não são municípios do IBGE.")

    parcial = t[t["meses_cobertos"] < 12]["ano"].unique()
    if len(parcial):
        for ano in sorted(parcial):
            m = int(t[t["ano"] == ano]["meses_cobertos"].max())
            print(f"[onco] ANO PARCIAL {ano}: {m} de 12 meses publicados — o total "
                  "deste ano NÃO é comparável com o de um ano fechado.")

    ign = t[t["estadiamento"] == "ignorado"]["apacs"].sum()
    print(f"[onco] sem estadiamento: {ign:,} APACs ({100 * ign / t['apacs'].sum():.1f}%) "
          "— com rótulo próprio, nunca somadas ao estádio 0.")

    fora_mun = f[f["municipio_res"] != f["municipio_mov"]]["apacs"].sum()
    print(f"[onco] fluxo: {len(f):,} linhas | "
          f"{100 * fora_mun / f['apacs'].sum():.1f}% das APACs fora do município de residência")
    print(f"[onco] cobertura: {len(c):,} linhas | "
          f"{int(c['meses_com_falha'].sum())} mês(es) com falha")


def main() -> int:
    argparse.ArgumentParser(
        description="Agrega os checkpoints do SIA/APAC oncológico em marts."
    ).parse_args()
    res = Resultado("scripts/pipeline_siasus_oncologia_marts.py")

    t, f, c = montar()
    relatar(t, f, c)

    MARTS.mkdir(parents=True, exist_ok=True)
    res.gravar(t, MARTS / "mart_apac_oncologia_tratamento.parquet")
    res.gravar(f, MARTS / "mart_apac_oncologia_fluxo.parquet")
    res.gravar(c, MARTS / "mart_apac_oncologia_cobertura.parquet")
    print(f"[ok] marts em {MARTS}")
    return res.relatar()


if __name__ == "__main__":
    sys.exit(main())
