"""
pipeline_painel_oncologia.py — o prazo da Lei dos 60 dias, por município
=========================================================================

    .venv311/Scripts/python scripts/pipeline_painel_oncologia.py --anos 2024
    .venv311/Scripts/python scripts/pipeline_painel_oncologia.py --todos-os-anos

Produz dois marts a partir do Painel Oncologia do DataSUS (FTP,
`painel_oncologia/Dados/POBR<ano>.dbc`), numa passada só sobre cada arquivo:

* `mart_oncologia_municipio.parquet` — **município de residência × ano de
  diagnóstico**, com o indicador da Lei dos 60 dias;
* `mart_oncologia_estadiamento.parquet` — **município × ano × sítio (CID-10 de
  3 caracteres) × faixa etária × estadiamento bruto**.

PARA QUE SERVE O SEGUNDO MART
------------------------------
Ele é o denominador que o SIM não tem. Mortalidade sozinha não separa "menos
câncer" de "menos diagnóstico", e a saída usual — comparar com a incidência
estimada do INCA — é circular: a Estimativa do INCA **deriva** incidência da
mortalidade, pela razão I/M dos Registros de Câncer de Base Populacional. O
Painel é contagem administrativa de quem entrou na assistência oncológica do
SUS; erra por outros motivos, e não pelo mesmo.

A GRAVAÇÃO É SOBRESCRITA, NÃO UPSERT
-------------------------------------
`out` vira o arquivo inteiro. Foi assim que uma corrida de teste com
`--anos 2023` reduziu, com exit 0, um mart de 2013–2026 a um único ano. Daí
`guarda_nao_encolher`: perder ano exige `--permitir-encolher` escrito à mão.

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
  registrada no SUS; quem não chegou ao SUS não está aqui. A omissão NÃO é
  uniforme no território: onde há mais plano de saúde, mais diagnóstico
  acontece fora do SUS. Quem usar o Painel como denominador precisa dizer para
  que lado isso empurra o resultado.
* O estadiamento é majoritariamente ausente — 51,0% `'9'` e 5,0% vazio em
  POBR2023, com só 24,9% dos casos entre os estádios 0 e 4. Na escala de
  completude usada pela literatura brasileira de registros de câncer, isso é
  "muito ruim" (ausência ≥ 50%). Distribuição de estádio publicada sem a
  completude ao lado mede preenchimento, não doença.
* O Painel inclui `D00–D48` (`D48` é o segundo sítio mais frequente de 2023).
  Cruzar com mortalidade por neoplasia MALIGNA exige filtrar `C00–C97` nos dois
  lados; o mart não filtra sozinho.
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
from collections.abc import Callable
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _datasus_ftp import ArquivoAusente, FalhaDeColeta, baixar, registros_dbc  # noqa: E402
from _saida import Resultado  # noqa: E402

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

#: Faixas etárias do projeto, iguais às da mortalidade. Repetidas aqui — e não
#: importadas de `_sim_obitos` — porque aquele módulo devolve SQL para DuckDB e
#: este agrega em Python, registro a registro. Se as duas listas divergirem, a
#: razão óbito/caso passa a comparar faixas diferentes nas duas pontas, que é o
#: erro que nenhuma soma acusa.
FAIXAS = ((5, "0-4"), (15, "5-14"), (30, "15-29"), (45, "30-44"),
          (60, "45-59"), (75, "60-74"), (999, "75+"))

#: Idade acima da qual o valor deixa de ser idade. O Painel traz `IDADE` em anos
#: com três dígitos, e um campo de três dígitos aceita 999 sem reclamar.
IDADE_MAXIMA = 130

#: Rótulo da faixa quando `IDADE` não é legível. Existe como categoria, e não
#: como descarte, pela mesma razão de `sem_tratamento`: ausência que vira filtro
#: silencioso muda o denominador de quem vier depois.
FAIXA_IGNORADA = "ignorada"


def _faixa(valor: object) -> str:
    """Faixa etária do projeto a partir de `IDADE`, ou `FAIXA_IGNORADA`."""
    t = str(valor or "").strip().lstrip("+")
    if not t.isdigit():
        return FAIXA_IGNORADA
    idade = int(t)
    if idade > IDADE_MAXIMA:
        return FAIXA_IGNORADA
    return next(rotulo for teto, rotulo in FAIXAS if idade < teto)


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


class Estadiamento:
    """Casos por município × ano × sítio × faixa etária × estadiamento BRUTO.

    Acumulador, e não função, porque roda na MESMA passada de `agregar`: o .dbc
    de um ano leva minutos para descomprimir e percorrer, e ler o arquivo duas
    vezes para produzir dois marts do mesmo dado dobraria o custo sem trocar
    nada em retorno.

    O estadiamento entra **como veio**, sem tradução. Medido em POBR2023, o campo
    é 51,0% `'9'`, 19,0% `'5'` e 5,0% vazio — só 24,9% dos casos trazem um
    estádio de 0 a 4. Um mart que já chegasse com `estadio_avancado` embutido
    esconderia essa proporção dentro de um denominador, e quem consumisse leria
    "8% em estádio IV" como fato sobre a doença quando é fato sobre o
    preenchimento. A interpretação mora em quem analisa, e o mart carrega a
    ausência em categoria própria — mesma decisão de `sem_tratamento`.

    O sítio vem de `DIAG_DETH` (CID-10) truncado em três caracteres. Note que o
    Painel inclui `D00–D48` — `D48` é o segundo sítio mais frequente de 2023,
    com 68.440 casos. Quem cruzar este mart com mortalidade por neoplasia
    MALIGNA precisa filtrar `C00–C97` dos dois lados; o mart não filtra por
    conta própria, porque o recorte é decisão de quem pergunta.
    """

    def __init__(self) -> None:
        self.acc: dict[tuple[str, int, str, str, str], int] = {}
        self.lidos = 0
        self.descartados = 0

    def __call__(self, r: dict) -> None:
        self.lidos += 1
        cod = str(r.get("MUN_RESID") or "").strip()
        sitio = str(r.get("DIAG_DETH") or "").strip().upper()[:3]
        try:
            ano = int(str(r.get("ANO_DIAGN") or "").strip())
        except ValueError:
            self.descartados += 1
            return
        if len(cod) != 6 or not cod.isdigit() or len(sitio) != 3:
            self.descartados += 1
            return
        chave = (cod, ano, sitio, _faixa(r.get("IDADE")),
                 str(r.get("ESTADIAM") or "").strip())
        self.acc[chave] = self.acc.get(chave, 0) + 1

    def df(self, ano_arquivo: int) -> pd.DataFrame:
        linhas = [{"municipio_cod": c, "ano": a, "sitio": s, "faixa_etaria": f,
                   "estadiam": e, "casos": n}
                  for (c, a, s, f, e), n in self.acc.items()]
        df = pd.DataFrame(linhas)
        if df.empty:
            return df
        # Nenhum registro some sem ser contado: o que entrou é o que foi
        # agregado mais o que foi explicitamente descartado. Sem esta conta, um
        # `continue` a mais numa revisão futura encolheria o mart em silêncio.
        if int(df["casos"].sum()) + self.descartados != self.lidos:
            raise SystemExit(
                f"[oncologia] POBR{ano_arquivo}: estadiamento agregou "
                f"{int(df['casos'].sum()):,} + descartou {self.descartados:,}, "
                f"mas leu {self.lidos:,} registros.")
        fora = df[df["ano"] != ano_arquivo]
        if len(fora):
            raise SystemExit(
                f"[oncologia] POBR{ano_arquivo}: {len(fora)} linhas de estadiamento "
                f"com ANO_DIAGN diferente de {ano_arquivo}.")
        return (df.sort_values(["municipio_cod", "ano", "sitio", "faixa_etaria", "estadiam"])
                  .reset_index(drop=True))


def agregar(registros, ano_arquivo: int,
            tambem: Callable[[dict], None] | None = None) -> pd.DataFrame:
    """Município de residência × ano de diagnóstico.

    Residência, e não local de tratamento: o indicador é sobre o acesso da
    POPULAÇÃO daquele município. Quem mora em cidade pequena e é tratado na
    capital conta para a cidade pequena, que é onde a fila dele existe.

    `tambem` recebe cada registro ANTES de qualquer descarte desta agregação, e
    existe para que `Estadiamento` leia o mesmo arquivo na mesma passada. Os
    critérios de descarte dos dois são independentes de propósito: este exige
    município válido, aquele exige também um sítio de três caracteres.
    """
    acc: dict[tuple[str, int], dict] = {}
    for r in registros:
        if tambem is not None:
            tambem(r)
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


def guarda_nao_encolher(novo: pd.DataFrame, destino: Path, permitido: bool) -> None:
    """Recusa gravar por cima de um mart que cobre anos que esta corrida não cobre.

    A gravação aqui é SOBRESCRITA, não upsert: `out` vira o arquivo inteiro. Com
    isso `--anos 2023` reduzia silenciosamente um mart de 2013–2026 a um ano só,
    com exit 0 e a mesma aparência de sucesso. Aconteceu de verdade em
    2026-09-07, numa corrida de teste, e só não virou dado publicado porque
    havia cópia.

    O mart não tem chave primária em `schema.sql` (não é servido), então
    `acumular_parquet` não se aplica; a proteção possível é esta — reprovar o
    encolhimento em vez de confiar em quem digita o comando. Rebuild parcial
    legítimo existe, e por isso a saída é uma flag explícita, não um bloqueio.
    """
    if permitido or not destino.exists() or novo.empty:
        return
    try:
        anos_antes = set(pd.read_parquet(destino, columns=["ano"])["ano"].unique())
    except (OSError, ValueError, KeyError):
        return
    perdidos = sorted(int(a) for a in anos_antes - set(novo["ano"].unique()))
    if perdidos:
        raise SystemExit(
            f"[oncologia] {destino.name} cobre {len(anos_antes)} anos e esta corrida "
            f"cobre {novo['ano'].nunique()}; gravar perderia {perdidos}. Rode com "
            "--todos-os-anos, ou repita com --permitir-encolher se o recorte é intencional.")


def guardas_estadiamento(est: pd.DataFrame, prazo: pd.DataFrame) -> None:
    """Aborta antes de gravar o mart de estadiamento."""
    if est.empty:
        raise SystemExit("[oncologia] agregação de estadiamento vazia — não grava.")

    if (est["casos"] <= 0).any():
        raise SystemExit("[oncologia] estadiamento com contagem de casos não positiva.")

    if est["sitio"].str.len().ne(3).any():
        raise SystemExit("[oncologia] estadiamento com sítio fora do formato de 3 caracteres.")

    validas = {r for _, r in FAIXAS} | {FAIXA_IGNORADA}
    fora = sorted(set(est["faixa_etaria"]) - validas)
    if fora:
        raise SystemExit(f"[oncologia] faixas etárias desconhecidas no estadiamento: {fora}.")

    # Os dois marts saem da mesma passada e descartam por critérios diferentes:
    # o de prazo exige município válido, o de estadiamento exige também sítio.
    # O de estadiamento só pode ter MENOS casos, nunca mais. Se tiver mais,
    # alguém contou o mesmo registro duas vezes.
    if int(est["casos"].sum()) > int(prazo["casos"].sum()):
        raise SystemExit(
            f"[oncologia] estadiamento tem {int(est['casos'].sum()):,} casos contra "
            f"{int(prazo['casos'].sum()):,} do mart de prazo — não pode ter mais.")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Mart do Painel Oncologia (Lei dos 60 dias).")
    ap.add_argument("--anos", nargs="+", type=int)
    ap.add_argument("--todos-os-anos", action="store_true")
    ap.add_argument("--permitir-encolher", action="store_true",
                    help="grava mesmo que o mart resultante perca anos já existentes")
    args = ap.parse_args()
    res = Resultado("scripts/pipeline_painel_oncologia.py")

    anos = ANOS if args.todos_os_anos else (args.anos or [])
    if not anos:
        ap.error("informe --anos ou --todos-os-anos")

    partes: list[pd.DataFrame] = []
    partes_est: list[pd.DataFrame] = []
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

        est = Estadiamento()
        df = agregar(registros_dbc(dados, f"POBR{ano}"), ano, tambem=est)
        df_est = est.df(ano)
        partes.append(df)
        partes_est.append(df_est)
        com_estadio = df_est[df_est["estadiam"].isin(list("01234"))]["casos"].sum()
        print(f"   {nome}: {df['casos'].sum():,} casos · "
              f"{df['municipio_cod'].nunique():,} municípios · "
              f"{df['sem_tratamento'].sum() / df['casos'].sum() * 100:.1f}% sem tratamento · "
              f"{com_estadio / df_est['casos'].sum() * 100:.1f}% com estádio 0–4",
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

    out_est = pd.concat(partes_est, ignore_index=True)
    guardas_estadiamento(out_est, out)
    com_estadio = out_est[out_est["estadiam"].isin(list("01234"))]["casos"].sum()
    print(f"\n[estadiamento] {len(out_est):,} linhas município×ano×sítio×faixa×estádio")
    print(f"[estadiamento] com estádio 0–4: {com_estadio:,} de "
          f"{out_est['casos'].sum():,} casos ({com_estadio / out_est['casos'].sum() * 100:.1f}%)")
    print("[nota] o estádio NÃO informado é maioria. Qualquer distribuição de "
          "estádio precisa publicar a completude ao lado, ou estará medindo "
          "preenchimento e chamando de doença.")

    MARTS.mkdir(parents=True, exist_ok=True)
    guarda_nao_encolher(out, MARTS / "mart_oncologia_municipio.parquet", args.permitir_encolher)
    guarda_nao_encolher(out_est, MARTS / "mart_oncologia_estadiamento.parquet",
                        args.permitir_encolher)
    res.gravar(out, MARTS / "mart_oncologia_municipio.parquet")
    print(f"[ok] mart_oncologia_municipio.parquet em {MARTS}")
    res.gravar(out_est, MARTS / "mart_oncologia_estadiamento.parquet")
    print(f"[ok] mart_oncologia_estadiamento.parquet em {MARTS}")
    return res.relatar()


if __name__ == "__main__":
    sys.exit(main())
