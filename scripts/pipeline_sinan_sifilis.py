"""
pipeline_sinan_sifilis.py — sífilis congênita como falha de pré-natal
======================================================================

    .venv311/Scripts/python scripts/pipeline_sinan_sifilis.py --anos 2023 2024
    .venv311/Scripts/python scripts/pipeline_sinan_sifilis.py --todos-os-anos

Produz `data/marts/mart_sifilis_municipio.parquet` no grão **município de
residência × ano de notificação**, a partir do SINAN (FTP, `SINAN/DADOS/PRELIM`),
juntando os três agravos que a fonte publica separados:

    SIFA  sífilis adquirida     2010–2025   (27 campos)
    SIFG  sífilis em gestante   2007–2025   (32 campos)
    SIFC  sífilis congênita     2007–2025   (64 campos)

TODA A SÍFILIS É PRELIMINAR — NÃO EXISTE VERSÃO FINAL
------------------------------------------------------
`SINAN/DADOS/FINAIS` tem 45 agravos e **nenhum** deles é sífilis: os 54 arquivos
SIFA/SIFG/SIFC estão só em `PRELIM`, inclusive os de 2007. Não é atraso de um
ano recente — são dezenove anos que nunca foram promovidos. Todo número deste
mart é preliminar por natureza da fonte, e o DataSUS reescreve esses arquivos
sem avisar.

O INDICADOR: SÍFILIS CONGÊNITA É EVENTO SENTINELA
---------------------------------------------------
Sífilis congênita é integralmente evitável. Gestante diagnosticada e tratada a
tempo com penicilina benzatina não transmite. Cada caso congênito é, portanto,
uma falha do sistema — e a fonte diz **onde** a falha aconteceu, porque a ficha
do SIFC registra o que houve com a mãe:

    ANT_PRE_NA   fez pré-natal?            1 sim · 2 não · 9 ignorado
    ANTSIFIL_N   quando foi diagnosticada  1 no pré-natal · 2 no parto · 3 após · 4 não
    TRA_ESQUEM   tratamento da mãe         1 adequado · 2 inadequado · 3 não realizado
    ANT_TRATAD   parceiro tratado          1 sim · 2 não · 9 ignorado
    EVOLUCAO     desfecho                  1 vivo · 2 óbito por sífilis congênita
                                           3 óbito outras causas · 4 aborto · 5 natimorto

Os códigos NÃO foram inferidos da distribuição: saem do dicionário oficial
`SIFICN_DIC_DADOS.pdf`, em `SINAN/DOCS/Docs_TAB_SINAN.zip`. A distinção que dá
sentido ao mart é a que separa **falha de acesso** (mãe sem pré-natal) de
**falha dentro do cuidado** (mãe com pré-natal, e a criança nasce infectada).

DUAS ARMADILHAS DE CÓDIGO, MEDIDAS EM 2023
-------------------------------------------
1. **`CLASSI_FIN` do SIFG está vazio nos 87.344 registros.** Copiar o filtro do
   `pipeline_sinan.py` da dengue (`CLASSI_FIN != '5'`) passaria despercebido,
   mas qualquer filtro por confirmação (`== '1'`) zeraria a sífilis gestacional
   inteira. Este pipeline não filtra por `CLASSI_FIN` em lugar nenhum.

2. **`CLASSI_FIN` do SIFA vem com espaço à esquerda em 6.147 registros** (`' 1'`
   ao lado de `'1'`, 2,5% do arquivo). Todo código lido aqui passa por `_cod()`,
   que faz `strip()` antes de comparar. Comparar sem `strip` misclassificaria
   silenciosamente.

CRITÉRIOS DE ABANDONO, DECLARADOS ANTES DE OLHAR A SÉRIE
----------------------------------------------------------
Escritos antes de rodar 2007–2025. Se algum disparar, a coluna correspondente
não é publicada — e "deu tudo certo" é resultado, não trabalho perdido.

  A. Se `congenita_por_100_gestante` passar de 100 em qualquer ano nacional,
     a razão está medindo notificação e não transmissão vertical: os dois
     arquivos não são comparáveis, e a coluna cai. → guarda `_criterio_a`.

  B. Se a proporção de casos congênitos cuja mãe FEZ pré-natal ficar abaixo de
     50% na série, a leitura "falha dentro do cuidado" está errada e o mart
     descreve falta de acesso. Ressalva honesta: 2023 foi medido antes de o
     critério ser escrito (82,7%); os outros 18 anos, não. → guarda `_criterio_b`.

  C. Se menos de 95% dos `ID_MN_RESI` casarem com `dim_municipio`, o grão
     geográfico não se sustenta. → guarda `_criterio_c`.

2025 É MEIO ANO, E ISSO NÃO VAI MELHORAR TÃO CEDO
---------------------------------------------------
`SIFCBR25` tem 12.630 casos contra 24.631 em 2024. Não é queda de 49%: o arquivo
acaba em **junho de 2025** (julho traz 306 registros, agosto 22 — resíduo de
digitação), enquanto 2024 tem doze meses parelhos de ~2.000.

E a defasagem é estrutural, não um atraso passageiro. Medido no FTP em
2026-09-06: os três arquivos de 2025 foram **reescritos em 30/06/2026** e ainda
assim param em junho de 2025; não existe `SIFxBR26`. No mesmo diretório,
`DENGBR26.dbc` foi atualizado em 01/09/2026 e já cobre 2026. Ou seja, o DataSUS
mantém a dengue quase corrente e a sífilis com cerca de um ano de atraso.

Daí a coluna `meses_cobertos`: o ano parcial vai carimbado na própria linha, não
numa nota de rodapé que o consumidor do Parquet nunca lê. A guarda
`_cobertura_de_meses` deixa o ÚLTIMO ano ser parcial — isso é a fronteira do
dado — e aborta se um ano anterior vier com menos de doze meses, que aí é
coleta incompleta se passando por ano fechado.

O QUE NÃO É COMPARÁVEL
-----------------------
`taxa_congenita_por_mil_nv` existe só onde há denominador: `mart_natalidade_
municipio` cobre **2021–2024**. Nos demais anos a coluna é NULA, não zero.
E `casos_adquirida` é NULO em 2007–2009, porque o SIFA começa em 2010 — ausência
de arquivo não é ausência de doença.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _datasus_ftp import ArquivoAusente, FalhaDeColeta, baixar, registros_dbc  # noqa: E402
from _publicacao import escrever_parquet  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
DIR_FTP = "/dissemin/publicos/SINAN/DADOS/PRELIM"

# Prefixo do arquivo e primeiro ano publicado, por agravo. O SIFA começa três
# anos depois dos outros dois: a notificação de sífilis adquirida só se tornou
# compulsória em 2010.
AGRAVOS: dict[str, tuple[str, int]] = {
    "adquirida": ("SIFA", 2010),
    "gestante": ("SIFG", 2007),
    "congenita": ("SIFC", 2007),
}
ANO_INICIAL = 2007
ANO_FINAL = 2025

# Fração de registros com ano(DT_NOTIFIC) fora do ano do arquivo que ainda
# aceitamos. Medido em 2023: exatamente 0 nos três agravos.
TOLERANCIA_ANO = 0.01

COLUNAS_CONGENITA = [
    "congenita_mae_com_prenatal", "congenita_mae_sem_prenatal",
    "congenita_prenatal_ignorado", "congenita_diag_no_prenatal",
    "congenita_trat_materno_adequado", "congenita_trat_materno_inadequado",
    "congenita_trat_materno_nao_realizado", "congenita_parceiro_tratado",
    "congenita_obito", "congenita_aborto", "congenita_natimorto",
]
CONTAGENS = ["casos_adquirida", "casos_gestante", "casos_congenita", *COLUNAS_CONGENITA]


def _cod(valor) -> str:
    """Código de campo categórico, sem o espaço que o SINAN às vezes deixa.

    `' 1'` aparece 6.147 vezes em SIFABR23 ao lado de `'1'`. Sem `strip()` os
    dois seriam categorias diferentes.
    """
    return "" if valor is None else str(valor).strip()


def _municipio(valor) -> str | None:
    """Código IBGE de 6 dígitos, ou None se o registro não tem residência."""
    m = _cod(valor)
    return m[:6] if len(m) >= 6 and m[:6].isdigit() else None


def agregar(registros, agravo: str, ano_arquivo: int) -> tuple[pd.DataFrame, Counter]:
    """Conta um arquivo anual de um agravo no grão município × ano.

    Devolve também o relatório do que foi descartado: registro sem município de
    residência é perda real e precisa aparecer, não sumir dentro de um `continue`.
    """
    if agravo not in AGRAVOS:
        raise SystemExit(f"[sifilis] agravo desconhecido: {agravo}")

    linhas: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    rel: Counter = Counter()
    for r in registros:
        rel["lidos"] += 1
        dn = r.get("DT_NOTIFIC")
        if dn is not None and dn.year != ano_arquivo:
            rel["ano_divergente"] += 1
        if dn is not None:
            # O mês da notificação é o que denuncia ano PARCIAL. SIFCBR25 tem
            # 12.630 casos contra 24.631 em 2024, e isso não é queda de 49%:
            # o arquivo acaba em junho. Sem esta contagem, o retrato de meio
            # ano entra na série com cara de ano inteiro.
            rel[f"mes:{dn.month:02d}"] += 1
        mun = _municipio(r.get("ID_MN_RESI"))
        if mun is None:
            rel["sem_municipio"] += 1
            continue
        c = linhas[mun]
        c[f"casos_{agravo}"] += 1
        if agravo != "congenita":
            continue

        pre = _cod(r.get("ANT_PRE_NA"))
        if pre == "1":
            c["congenita_mae_com_prenatal"] += 1
        elif pre == "2":
            c["congenita_mae_sem_prenatal"] += 1
        else:
            c["congenita_prenatal_ignorado"] += 1

        if _cod(r.get("ANTSIFIL_N")) == "1":
            c["congenita_diag_no_prenatal"] += 1

        trat = _cod(r.get("TRA_ESQUEM"))
        if trat == "1":
            c["congenita_trat_materno_adequado"] += 1
        elif trat == "2":
            c["congenita_trat_materno_inadequado"] += 1
        elif trat == "3":
            c["congenita_trat_materno_nao_realizado"] += 1

        if _cod(r.get("ANT_TRATAD")) == "1":
            c["congenita_parceiro_tratado"] += 1

        evo = _cod(r.get("EVOLUCAO"))
        if evo == "2":
            c["congenita_obito"] += 1
        elif evo == "4":
            c["congenita_aborto"] += 1
        elif evo == "5":
            c["congenita_natimorto"] += 1

    if rel["lidos"] and rel["ano_divergente"] / rel["lidos"] > TOLERANCIA_ANO:
        # O arquivo é anual por ano de notificação. Se muitos registros dizem
        # outro ano, o arquivo não é o que o nome promete, e atribuir tudo ao
        # ano do nome estaria inventando uma série.
        raise SystemExit(
            f"[sifilis] {agravo} {ano_arquivo}: {rel['ano_divergente']:,} de "
            f"{rel['lidos']:,} registros com DT_NOTIFIC fora do ano do arquivo.")

    # Esquema estável: uma coluna que nenhum registro incrementou tem de sair
    # ZERO, e não sumir. Sem isto, um arquivo em que ninguém morreu não teria
    # coluna de óbito, e o `concat` a inventaria como NA — ausência falsa.
    colunas = [f"casos_{agravo}"] + (COLUNAS_CONGENITA if agravo == "congenita" else [])
    df = pd.DataFrame(
        [{"municipio_cod": m, "ano": ano_arquivo, **v} for m, v in linhas.items()],
        columns=["municipio_cod", "ano", *colunas])
    for col in colunas:
        df[col] = df[col].fillna(0).astype("int64")
    return df, rel


def combinar(partes: list[pd.DataFrame], coletados: dict[str, set[int]]) -> pd.DataFrame:
    """Junta os agravos e distingue zero verdadeiro de arquivo inexistente.

    Um município sem sífilis congênita num ano em que o SIFC foi coletado tem
    zero casos — é fato. O mesmo município em 2008 não tem zero sífilis
    ADQUIRIDA: o SIFA só começa em 2010, e ali a coluna precisa ser nula.
    """
    if not partes:
        raise SystemExit("[sifilis] nenhum arquivo agregado — nada a combinar.")

    df = pd.concat(partes, ignore_index=True)
    for col in CONTAGENS:
        if col not in df.columns:
            df[col] = 0
    df[CONTAGENS] = df[CONTAGENS].fillna(0)
    df = df.groupby(["municipio_cod", "ano"], as_index=False)[CONTAGENS].sum()

    for col in CONTAGENS:
        df[col] = df[col].astype("Int64")
    for agravo, anos in coletados.items():
        colunas = ["casos_congenita", *COLUNAS_CONGENITA] if agravo == "congenita" \
            else [f"casos_{agravo}"]
        fora = ~df["ano"].isin(anos)
        for col in colunas:
            df.loc[fora, col] = pd.NA
    return df.sort_values(["municipio_cod", "ano"]).reset_index(drop=True)


def meses_do_relatorio(rel: Counter) -> set[int]:
    """Meses do ano em que o arquivo tem ao menos uma notificação."""
    return {int(k.split(":")[1]) for k, v in rel.items() if k.startswith("mes:") and v}


def anotar_cobertura(df: pd.DataFrame, meses_por_ano: dict[int, set[int]]) -> pd.DataFrame:
    """Carimba quantos meses o arquivo daquele ano realmente cobre.

    Vai como COLUNA, não como nota de rodapé: quem lê o Parquet direto — que é
    o consumidor que este projeto promete servir — precisa ver o ano parcial no
    mesmo lugar em que vê a contagem que ele encolhe.
    """
    df = df.copy()
    df["meses_cobertos"] = df["ano"].map(
        {a: len(m) for a, m in meses_por_ano.items()}).astype("Int64")
    return df


def derivar(df: pd.DataFrame, natalidade: pd.DataFrame | None) -> pd.DataFrame:
    """Acrescenta o denominador de nascidos vivos e as duas taxas."""
    df = df.copy()
    if natalidade is not None and not natalidade.empty:
        nv = natalidade[["municipio_cod", "ano", "nascidos"]].copy()
        nv["municipio_cod"] = nv["municipio_cod"].astype(str)
        nv["nascidos"] = nv["nascidos"].astype("Int64")
        df = df.merge(nv, on=["municipio_cod", "ano"], how="left")
    else:
        df["nascidos"] = pd.Series([pd.NA] * len(df), dtype="Int64")

    nasc = pd.to_numeric(df["nascidos"], errors="coerce")
    cong = pd.to_numeric(df["casos_congenita"], errors="coerce")
    gest = pd.to_numeric(df["casos_gestante"], errors="coerce")

    df["taxa_congenita_por_mil_nv"] = (cong / nasc * 1000).round(2).where(nasc > 0)
    df["congenita_por_100_gestante"] = (cong / gest * 100).round(1).where(gest > 0)
    return df


# ── guardas ────────────────────────────────────────────────────────────────

def _criterio_a(df: pd.DataFrame) -> None:
    """Critério A: razão congênita/gestante acima de 100 num ano nacional."""
    por_ano = df.groupby("ano")[["casos_congenita", "casos_gestante"]].sum(min_count=1)
    cong = pd.to_numeric(por_ano["casos_congenita"], errors="coerce")
    gest = pd.to_numeric(por_ano["casos_gestante"], errors="coerce")
    # Denominador zero não é razão infinita, é razão INDEFINIDA. O ano em que o
    # SIFG não foi coletado já chega como NA; aqui sobra o ano coletado e vazio.
    razao = (cong / gest * 100).where(gest > 0)
    mau = razao[razao > 100]
    if len(mau):
        raise SystemExit(
            f"[sifilis] CRITERIO A: {len(mau)} anos com mais casos congênitos que "
            f"gestacionais ({dict(mau.round(1))}) — a razão mede notificação, não "
            "transmissão vertical. A coluna não deve ser publicada.")


def _criterio_b(df: pd.DataFrame) -> None:
    """Critério B: menos de metade das mães com pré-natal registrado."""
    com = pd.to_numeric(df["congenita_mae_com_prenatal"], errors="coerce").sum()
    sem = pd.to_numeric(df["congenita_mae_sem_prenatal"], errors="coerce").sum()
    if com + sem == 0:
        raise SystemExit("[sifilis] CRITERIO B: nenhum caso congênito com pré-natal informado.")
    pct = com / (com + sem) * 100
    if pct < 50:
        raise SystemExit(
            f"[sifilis] CRITERIO B: só {pct:.1f}% das mães fizeram pré-natal — o mart "
            "descreve falta de acesso, não falha dentro do cuidado. Releia o enquadramento.")


def _cobertura_de_meses(df: pd.DataFrame) -> None:
    """Ano parcial NO MEIO da série é buraco; na ponta, é o calendário.

    O último ano publicado é sempre um retrato em andamento — SIFCBR25 acaba em
    junho — e reprovar isso seria reprovar a atualidade. Mas um ano ANTERIOR com
    menos de doze meses é coleta incompleta se passando por ano fechado, que é
    o defeito que nenhuma contagem de linhas pega.
    """
    if "meses_cobertos" not in df.columns:
        return
    ultimo = int(df["ano"].max())
    cobertura = df.groupby("ano")["meses_cobertos"].max()
    furados = cobertura[(cobertura < 12) & (cobertura.index != ultimo)]
    if len(furados):
        raise SystemExit(
            f"[sifilis] anos fechados com menos de 12 meses de notificação: "
            f"{dict(furados)} — o arquivo não cobre o ano que o nome promete.")


def _criterio_c(df: pd.DataFrame, municipios: set[str] | None) -> None:
    """Critério C: os códigos de município precisam existir na dimensão."""
    if not municipios:
        return
    codigos = set(df["municipio_cod"])
    casa = len(codigos & municipios) / len(codigos) * 100
    if casa < 95:
        raise SystemExit(
            f"[sifilis] CRITERIO C: só {casa:.1f}% dos códigos de município casam com "
            "dim_municipio — o grão geográfico não se sustenta.")


def guardas(df: pd.DataFrame, municipios: set[str] | None = None) -> None:
    """Aborta antes de gravar. Cada uma vigia um jeito de o mart mentir."""
    if df.empty:
        raise SystemExit("[sifilis] agregação vazia — não grava.")

    cong = pd.to_numeric(df["casos_congenita"], errors="coerce")

    # As três categorias de pré-natal são exaustivas por construção (o `else`
    # cai em ignorado), então a soma tem de fechar com o total de congênitos.
    soma = sum(pd.to_numeric(df[c], errors="coerce") for c in
               ("congenita_mae_com_prenatal", "congenita_mae_sem_prenatal",
                "congenita_prenatal_ignorado"))
    ruim = df[(soma != cong) & cong.notna()]
    if len(ruim):
        raise SystemExit(
            f"[sifilis] {len(ruim)} linhas em que as categorias de pré-natal ≠ casos_congenita.")

    # Nenhum subconjunto de congênitos pode ser maior que o total. Pega troca de
    # coluna e dupla contagem de uma vez.
    for col in COLUNAS_CONGENITA:
        v = pd.to_numeric(df[col], errors="coerce")
        ruim = df[(v > cong) & v.notna() & cong.notna()]
        if len(ruim):
            raise SystemExit(f"[sifilis] {len(ruim)} linhas com {col} > casos_congenita.")

    for col in CONTAGENS:
        v = pd.to_numeric(df[col], errors="coerce")
        if (v < 0).any():
            raise SystemExit(f"[sifilis] {col} tem contagem negativa.")

    for col in ("taxa_congenita_por_mil_nv", "congenita_por_100_gestante"):
        if col in df.columns:
            v = df[col]
            if (v.notna() & (v < 0)).any():
                raise SystemExit(f"[sifilis] {col} tem valor negativo.")

    ruim = df[~df["municipio_cod"].str.fullmatch(r"\d{6}")]
    if len(ruim):
        raise SystemExit(f"[sifilis] {len(ruim)} linhas com municipio_cod fora de 6 dígitos.")

    _cobertura_de_meses(df)
    _criterio_a(df)
    _criterio_b(df)
    _criterio_c(df, municipios)


# ── execução ───────────────────────────────────────────────────────────────

def _dim_municipios() -> set[str] | None:
    alvo = MARTS / "dim_municipio.parquet"
    if not alvo.exists():
        return None
    return set(pd.read_parquet(alvo)["municipio_cod"].astype(str))


def _natalidade() -> pd.DataFrame | None:
    alvo = MARTS / "mart_natalidade_municipio.parquet"
    if not alvo.exists():
        return None
    return pd.read_parquet(alvo)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Mart de sífilis do SINAN (SIFA/SIFG/SIFC).")
    ap.add_argument("--anos", nargs="+", type=int)
    ap.add_argument("--todos-os-anos", action="store_true")
    args = ap.parse_args()

    if args.todos_os_anos:
        anos = list(range(ANO_INICIAL, ANO_FINAL + 1))
    elif args.anos:
        anos = sorted(args.anos)
    else:
        ap.error("informe --anos ou --todos-os-anos")

    partes: list[pd.DataFrame] = []
    coletados: dict[str, set[int]] = {a: set() for a in AGRAVOS}
    meses_por_ano: dict[int, set[int]] = {}
    ausentes: list[str] = []
    mascaradas = 0

    for agravo, (prefixo, inicio) in AGRAVOS.items():
        for ano in anos:
            if ano < inicio:
                continue
            nome = f"{prefixo}BR{ano % 100:02d}.dbc"
            try:
                dados = baixar(DIR_FTP, nome)
            except ArquivoAusente:
                ausentes.append(nome)
                print(f"   {nome}: ausente no FTP", flush=True)
                continue
            except FalhaDeColeta as e:
                raise SystemExit(f"[sifilis] {nome} existe e a coleta falhou: {e}") from e

            contador: Counter = Counter()
            df, rel = agregar(registros_dbc(dados, nome, contador), agravo, ano)
            if contador["impossivel"]:
                # Máscara é ausência; dígito que não forma data é corrupção.
                raise SystemExit(
                    f"[sifilis] {nome}: {contador['impossivel']} datas impossíveis "
                    f"({[k for k in contador if k.startswith('impossivel:')]}).")
            mascaradas += contador["mascarada"]
            coletados[agravo].add(ano)
            # Interseção, não união: o ano só está coberto até onde o agravo
            # MAIS ATRASADO chegou. União mascararia o agravo que parou antes.
            meses = meses_do_relatorio(rel)
            meses_por_ano[ano] = meses if ano not in meses_por_ano \
                else meses_por_ano[ano] & meses
            partes.append(df)
            print(f"   {nome}: {rel['lidos']:,} registros · "
                  f"{df['municipio_cod'].nunique():,} municípios · "
                  f"{rel['sem_municipio']:,} sem residência", flush=True)

    out = derivar(anotar_cobertura(combinar(partes, coletados), meses_por_ano),
                  _natalidade())
    guardas(out, _dim_municipios())

    cong = pd.to_numeric(out["casos_congenita"], errors="coerce")
    gest = pd.to_numeric(out["casos_gestante"], errors="coerce")
    adq = pd.to_numeric(out["casos_adquirida"], errors="coerce")
    com = pd.to_numeric(out["congenita_mae_com_prenatal"], errors="coerce").sum()
    sem = pd.to_numeric(out["congenita_mae_sem_prenatal"], errors="coerce").sum()
    adeq = pd.to_numeric(out["congenita_trat_materno_adequado"], errors="coerce").sum()

    print(f"\n[sifilis] {len(out):,} linhas município×ano")
    print(f"[sifilis] adquirida {adq.sum():,.0f} · gestante {gest.sum():,.0f} · "
          f"congênita {cong.sum():,.0f}")
    print(f"[sifilis] congênita com mãe que FEZ pré-natal: {com / (com + sem) * 100:.1f}%")
    print(f"[sifilis] tratamento materno adequado: {adeq / cong.sum() * 100:.1f}% "
          "dos casos congênitos")
    print(f"[sifilis] óbitos por sífilis congênita: "
          f"{pd.to_numeric(out['congenita_obito'], errors='coerce').sum():,.0f} · "
          f"abortos {pd.to_numeric(out['congenita_aborto'], errors='coerce').sum():,.0f} · "
          f"natimortos {pd.to_numeric(out['congenita_natimorto'], errors='coerce').sum():,.0f}")
    print(f"[sifilis] datas mascaradas pela fonte (ausência, não erro): {mascaradas:,}")
    parcial = {a: len(m) for a, m in sorted(meses_por_ano.items()) if len(m) < 12}
    if parcial:
        print(f"[sifilis] anos com menos de 12 meses no arquivo: {parcial} — "
              "a contagem deles NÃO é comparável com a dos anos fechados.")
    if ausentes:
        print(f"[sifilis] arquivos ausentes no FTP: {ausentes}")
    print("[nota] toda a sífilis do SINAN é PRELIMINAR: não há SIFA/SIFG/SIFC em "
          "DADOS/FINAIS, nem para 2007. taxa_congenita_por_mil_nv só existe em "
          "2021–2024, onde há denominador de nascidos vivos.")

    MARTS.mkdir(parents=True, exist_ok=True)
    escrever_parquet(out, MARTS / "mart_sifilis_municipio.parquet",
                     origem="pipeline", produtor="scripts/pipeline_sinan_sifilis.py")
    print(f"[ok] mart_sifilis_municipio.parquet em {MARTS}")


if __name__ == "__main__":
    main()
