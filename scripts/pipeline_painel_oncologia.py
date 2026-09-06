"""
pipeline_painel_oncologia.py — o prazo da Lei dos 60 dias, por município
=========================================================================

    .venv311/Scripts/python scripts/pipeline_painel_oncologia.py --anos 2024
    .venv311/Scripts/python scripts/pipeline_painel_oncologia.py --todos-os-anos

Produz `data/marts/mart_oncologia_municipio.parquet` no grão
**município de residência × ano de diagnóstico**, a partir do Painel Oncologia
do DataSUS (FTP, `painel_oncologia/Dados/POBR<ano>.dbc`).

O INDICADOR, E DE ONDE VEM O LIMIAR
------------------------------------
A Lei 12.732/2012 dá ao paciente com neoplasia maligna o direito de iniciar o
tratamento em até **60 dias** do diagnóstico. O limiar não é escolha nossa: é
o texto da lei, e é o que o próprio Painel existe para acompanhar.

99999 NÃO É UM TEMPO — É AUSÊNCIA DE TRATAMENTO
------------------------------------------------
A armadilha central desta fonte, e a razão de este cabeçalho ser longo.
`TEMPO_TRAT` traz `99999` para quem não tem tratamento registrado. Medido em
POBR2024, a correspondência é perfeita:

    TEMPO_TRAT = 99999  ⟺  TRATAMENTO = 5  ⟺  DT_TRAT vazio   (343.351 casos)

Somados os 15.899 com `TEMPO_TRAT` em branco, são **359.250 de 643.439 casos
(55,8%) sem tratamento registrado** em 2024.

Quem tratar 99999 como duração publica duas mentiras de uma vez: uma mediana de
99.999 dias, e um "% em até 60 dias" calculado sobre um denominador que inclui
centenas de milhares de pessoas que nunca iniciaram tratamento. Foi o que a
primeira leitura deste arquivo produziu — **24,2%**, contra os **53,4%** que
saem do denominador correto. O erro empurra o indicador para baixo e parece
notícia ruim plausível, que é o tipo de erro que ninguém confere.

Daí o desenho: `sem_tratamento` é **coluna própria**, não uma exclusão
silenciosa. Ele é o indicador de acesso mais duro desta base — e some se virar
apenas um filtro no denominador de outra coisa.

`pct_sem_tratamento` NÃO É COMPARÁVEL ENTRE ANOS
--------------------------------------------------
A série completa expõe duas descontinuidades, e nenhuma delas é fenômeno de
saúde. Medidas em 2026-09-06:

    2013  3,5%      2018 27,2%      2023 51,0%
    2014  5,4%      2019 46,6%      2024 55,8%
    2015  6,2%      2020 46,2%      2025 60,7%
    2016  6,0%      2021 48,1%      2026 79,7%
    2017  5,9%      2022 50,1%

1. **Censura à direita.** O arquivo é um retrato: quem foi diagnosticado em
   dezembro pode ser tratado depois do corte, e aparece como "sem tratamento".
   Quanto mais recente o ano, mais forte o efeito — os 79,7% de 2026 são
   sobretudo pacientes cujo tratamento ainda não aconteceu, não pacientes
   abandonados. Comparar 2026 com 2015 mede o calendário, não o acesso.

2. **Descontinuidade em 2018.** Os casos saltam de 196 mil (2017) para 352 mil
   (2018) e 565 mil (2019), e a proporção sem tratamento sobe junto. É mudança
   de escopo do próprio Painel, e nenhuma série que atravesse 2018 sem dizer
   isso está medindo a mesma coisa nas duas pontas.

Por isso o mart traz os NÚMEROS ABSOLUTOS ao lado dos percentuais: `casos`,
`sem_tratamento` e `com_tratamento`. Percentual sozinho esconde as duas coisas.

O QUE ESTE MART NÃO É
---------------------
* Não é incidência de câncer. O Painel cobre a assistência oncológica
  registrada no SUS; quem não chegou ao SUS não está aqui.
* `sem_tratamento` não é "não tratou": é "sem tratamento REGISTRADO no
  período do arquivo". Tratamento iniciado no ano seguinte cai no arquivo
  seguinte, e o Painel é reprocessado.
* Tempo negativo existe (5.036 casos em 2024, 0,8%) — tratamento antes do
  diagnóstico é impossível e indica data trocada na origem. Vai em coluna
  própria em vez de ser descartado em silêncio ou somado como zero.

Depende de: `scripts/_datasus_ftp.py`, `scripts/_publicacao.py`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _datasus_ftp import ArquivoAusente, FalhaDeColeta, baixar, registros_dbc  # noqa: E402
from _publicacao import escrever_parquet  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
DIR_FTP = "/dissemin/publicos/painel_oncologia/Dados"

#: Anos com arquivo no FTP, medidos em 2026-09-06 (POBR2013..POBR2026).
ANOS = list(range(2013, 2027))

#: O prazo da Lei 12.732/2012. Constante nomeada porque é norma, não parâmetro:
#: mudar este número é mudar de lei, não de configuração.
PRAZO_LEGAL_DIAS = 60

#: `TRATAMENTO = 5` é "sem tratamento registrado". Vem acompanhado de
#: `TEMPO_TRAT = 99999` e `DT_TRAT` vazio — as três coisas são a mesma.
COD_SEM_TRATAMENTO = "5"

#: Sentinela de ausência no campo de duração. NUNCA entra num cálculo de tempo.
SENTINELA_TEMPO = 99999


def _tempo(valor: object) -> int | None:
    """Dias entre diagnóstico e tratamento, ou `None`.

    `None` para vazio, não numérico e para a sentinela. Devolver 99999 aqui
    seria o suficiente para envenenar qualquer média, mediana ou percentual
    calculado adiante — e nada acusaria, porque 99999 é um número válido.
    """
    if valor is None:
        return None
    t = str(valor).strip().lstrip("+")
    if not t:
        return None
    try:
        v = int(t)
    except ValueError:
        return None
    return None if v == SENTINELA_TEMPO else v


def agregar(registros, ano_arquivo: int) -> pd.DataFrame:
    """Município de residência × ano de diagnóstico.

    Residência, e não local de tratamento: o indicador é sobre o acesso da
    POPULAÇÃO daquele município. Quem mora em cidade pequena e é tratado na
    capital conta para a cidade pequena, que é onde a fila dele existe.
    """
    acc: dict[tuple[str, int], dict] = {}
    for r in registros:
        cod = str(r.get("MUN_RESID") or "").strip()
        if len(cod) != 6 or not cod.isdigit():
            continue
        try:
            ano = int(str(r.get("ANO_DIAGN") or "").strip())
        except ValueError:
            continue

        d = acc.setdefault((cod, ano), {
            "municipio_cod": cod, "ano": ano,
            "casos": 0, "sem_tratamento": 0, "com_tratamento": 0,
            "ate_60_dias": 0, "acima_60_dias": 0, "tempo_negativo": 0,
            "_dias": [],
        })
        d["casos"] += 1

        sem = str(r.get("TRATAMENTO") or "").strip() == COD_SEM_TRATAMENTO
        dias = _tempo(r.get("TEMPO_TRAT"))
        if sem or dias is None:
            # A sentinela e o código de "sem tratamento" andam juntos; se um dia
            # se separarem, `guardas` reprova em vez de a contagem silenciar.
            d["sem_tratamento"] += 1
            continue

        d["com_tratamento"] += 1
        if dias < 0:
            d["tempo_negativo"] += 1
            continue
        d["_dias"].append(dias)
        if dias <= PRAZO_LEGAL_DIAS:
            d["ate_60_dias"] += 1
        else:
            d["acima_60_dias"] += 1

    linhas = []
    for d in acc.values():
        dias = sorted(d.pop("_dias"))
        # Mediana só entre os que TÊM tempo válido e não negativo — o mesmo
        # conjunto que alimenta o percentual, para os dois falarem do mesmo
        # grupo de pessoas.
        d["mediana_dias"] = float(dias[len(dias) // 2]) if dias else None
        base = d["ate_60_dias"] + d["acima_60_dias"]
        d["pct_ate_60_dias"] = round(d["ate_60_dias"] / base * 100, 1) if base else None
        d["pct_sem_tratamento"] = round(d["sem_tratamento"] / d["casos"] * 100, 1) if d["casos"] else None
        linhas.append(d)

    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    fora = df[df["ano"] != ano_arquivo]
    if len(fora):
        # O arquivo é anual e o ano vem de dentro do registro. Se divergirem, a
        # agregação estaria misturando anos sem que ninguém pedisse.
        raise SystemExit(
            f"[oncologia] POBR{ano_arquivo}: {len(fora)} linhas com ANO_DIAGN "
            f"diferente de {ano_arquivo} (ex.: {sorted(fora['ano'].unique())[:5]}).")
    return df.sort_values(["municipio_cod", "ano"]).reset_index(drop=True)


def guardas(df: pd.DataFrame) -> None:
    """Aborta antes de gravar. Cada uma vigia um jeito de o mart mentir."""
    if df.empty:
        raise SystemExit("[oncologia] agregação vazia — não grava.")

    soma = df["sem_tratamento"] + df["com_tratamento"]
    if not soma.equals(df["casos"]):
        n = int((soma != df["casos"]).sum())
        raise SystemExit(f"[oncologia] {n} linhas em que com+sem tratamento ≠ casos.")

    parcelas = df["ate_60_dias"] + df["acima_60_dias"] + df["tempo_negativo"]
    if not parcelas.equals(df["com_tratamento"]):
        n = int((parcelas != df["com_tratamento"]).sum())
        raise SystemExit(f"[oncologia] {n} linhas em que as faixas de prazo ≠ com_tratamento.")

    # A sentinela nunca pode ter virado duração. O teste é EXATO — procura o
    # valor 99999 — e não um proxy de plausibilidade.
    #
    # A primeira versão desta guarda reprovava mediana acima de 10 anos, e deu
    # falso positivo em 12 município-anos: são esperas REAIS, com as duas datas
    # conferindo (diagnóstico 21/05/2013, tratamento 21/07/2023 = 3.713 dias).
    # Guarda que testa proxy reprova dado verdadeiro e ensina a ser ignorada —
    # falso positivo custa o mesmo que falso negativo.
    mau = df[df["mediana_dias"] == SENTINELA_TEMPO]
    if len(mau):
        raise SystemExit(
            f"[oncologia] {len(mau)} linhas com mediana exatamente {SENTINELA_TEMPO} — "
            "a sentinela entrou no cálculo de tempo.")

    for col in ("pct_ate_60_dias", "pct_sem_tratamento"):
        mau = df[df[col].notna() & ((df[col] < 0) | (df[col] > 100))]
        if len(mau):
            raise SystemExit(f"[oncologia] {len(mau)} linhas com {col} fora de 0–100.")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Mart do Painel Oncologia (Lei dos 60 dias).")
    ap.add_argument("--anos", nargs="+", type=int)
    ap.add_argument("--todos-os-anos", action="store_true")
    args = ap.parse_args()

    anos = ANOS if args.todos_os_anos else (args.anos or [])
    if not anos:
        ap.error("informe --anos ou --todos-os-anos")

    partes: list[pd.DataFrame] = []
    ausentes: list[int] = []
    for ano in sorted(anos):
        nome = f"POBR{ano}.dbc"
        try:
            dados = baixar(DIR_FTP, nome)
        except ArquivoAusente:
            # Ano ainda não publicado é FATO, não falha: registra e segue.
            ausentes.append(ano)
            print(f"   {nome}: ausente no FTP (ano não publicado)", flush=True)
            continue
        except FalhaDeColeta as e:
            # Já existe e não veio: abortar. Seguir produziria um mart a que
            # falta um ano inteiro, com aparência de completo.
            raise SystemExit(f"[oncologia] {nome} existe e a coleta falhou: {e}") from e

        df = agregar(registros_dbc(dados, f"POBR{ano}"), ano)
        partes.append(df)
        print(f"   {nome}: {df['casos'].sum():,} casos · "
              f"{df['municipio_cod'].nunique():,} municípios · "
              f"{df['sem_tratamento'].sum() / df['casos'].sum() * 100:.1f}% sem tratamento",
              flush=True)

    if not partes:
        raise SystemExit("[oncologia] nenhum ano coletado — nada a gravar.")

    out = pd.concat(partes, ignore_index=True)
    guardas(out)

    base = out["ate_60_dias"].sum() + out["acima_60_dias"].sum()
    print(f"\n[oncologia] {len(out):,} linhas município×ano | {out['casos'].sum():,} casos")
    print(f"[oncologia] sem tratamento registrado: "
          f"{out['sem_tratamento'].sum() / out['casos'].sum() * 100:.1f}%")
    print(f"[oncologia] dos que iniciaram tratamento, em até {PRAZO_LEGAL_DIAS} dias: "
          f"{out['ate_60_dias'].sum() / base * 100:.1f}%")
    print(f"[oncologia] tempo negativo (impossível): {out['tempo_negativo'].sum():,}")
    if ausentes:
        print(f"[oncologia] anos ausentes no FTP: {ausentes}")
    print("[nota] pct_sem_tratamento NÃO é comparável entre anos: o ano recente é "
          "censurado (tratamento ainda não ocorreu) e há descontinuidade de escopo "
          "do Painel em 2018. Use os absolutos ao lado.")

    MARTS.mkdir(parents=True, exist_ok=True)
    escrever_parquet(out, MARTS / "mart_oncologia_municipio.parquet",
                     origem="pipeline", produtor="scripts/pipeline_painel_oncologia.py")
    print(f"[ok] mart_oncologia_municipio.parquet em {MARTS}")


if __name__ == "__main__":
    main()
