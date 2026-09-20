"""
pipeline_siasus_oncologia.py — APAC de quimioterapia e radioterapia (SIA/SUS)
==============================================================================

    python scripts/pipeline_siasus_oncologia.py --ano 2024 --workers 3
    python scripts/pipeline_siasus_oncologia.py --ano-inicio 2013 --ano-fim 2026

Produz:
  * `mart_oncologia_tratamento`  — município do PACIENTE × ano × modalidade ×
                                   CID-3 × estadiamento
  * `mart_oncologia_fluxo`       — município do paciente → município do
                                   estabelecimento, por ano e modalidade
  * `mart_oncologia_tratamento_cobertura` — UF × ano, o que foi coletado

RODE `scripts/sondar_siasus.py` ANTES. O portão registra o recorte e, sobretudo,
**o que esta fonte não mede** — o prazo da Lei dos 60 Dias NÃO sai de
`AQ_DTIDEN`/`AQ_DTINTR`, e a conta óbvia produz uma manchete falsa. Este
pipeline não publica prazo, e isso é decisão, não esquecimento.

O RECORTE: AQ + AR
-------------------
Quimioterapia e radioterapia. Ficam de fora PA e BI (398 GB e 100% dos 997
arquivos partidos do SIA) e AM (medicamentos de alto custo, eixo próprio).

DOIS MUNICÍPIOS, E ELES NÃO SÃO O MESMO
----------------------------------------
`AP_MUNPCN` é onde o paciente MORA; `AP_UFMUN` é onde o estabelecimento está.
Medido na sondagem: **54% das APACs de quimioterapia são de paciente tratado
fora do próprio município**. Confundir os dois transformaria deslocamento em
oferta local, e é por isso que o mart principal usa a RESIDÊNCIA (é medida de
população) e o fluxo existe em tabela separada.

A UNIDADE É A APAC, NÃO A PESSOA
---------------------------------
Uma APAC é uma autorização, tipicamente mensal. Paciente em quimioterapia
contínua gera várias por ano, e `AP_CNSPCN` — o único identificador de pessoa —
vem **criptografado**. Então: `apacs` conta autorizações, nunca pacientes, e o
nome da coluna diz isso. Qualquer leitura per capita sobre esta tabela está
errada, e a metodologia tem de repetir isso.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _datasus_ftp import ArquivoAusente, FalhaDeColeta, baixar, registros_dbc  # noqa: E402
from _saida import Resultado  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "SIASUS" / "onco_ckpt"

#: Digitado aqui, e não lido de `_fontes.py`, pela mesma razão de ORDEM do
#: SISCAN e dos convênios: fonte entra no registro quando publica. REMOVER ao
#: publicar o mart, declarando `siasus` em `_fontes.py` e em `fontes.ts`.
FTP_DIR = "/dissemin/publicos/SIASUS/200801_/Dados"

#: Modalidade por prefixo de arquivo. Os campos próprios de cada uma mudam de
#: nome (`AQ_ESTADI` vs `AR_ESTADI`), e é só isso que difere na leitura.
MODALIDADES = {"AQ": "quimioterapia", "AR": "radioterapia"}

UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
       "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
       "SE", "SP", "TO"]

#: Estadiamento que a fonte usa. Qualquer outro valor vira "ignorado" — e a
#: ausência NÃO é somada a nenhum estádio real: ela tem rótulo próprio, porque
#: 15,9% dos registros não a trazem e diluí-los mudaria toda proporção.
ESTADIOS = {"0", "1", "2", "3", "4"}


def _limpo(v) -> str:
    return str(v or "").strip().upper()


def _estadio(v) -> str:
    e = _limpo(v).lstrip("0") or "0"
    return e if e in ESTADIOS else "ignorado"


def _processar(uf: str, ano: int, mes: int, grupo: str):
    """Um arquivo mensal → dois dicionários agregados (tratamento, fluxo).

    Levanta `ArquivoAusente` quando a competência não foi publicada e
    `FalhaDeColeta` quando existe e falhou — a distinção é o que impede
    ausência de virar zero publicado.
    """
    nome = f"{grupo}{uf}{ano % 100:02d}{mes:02d}.dbc"
    dados = baixar(FTP_DIR, nome)
    trat: dict = defaultdict(lambda: [0, 0.0])
    fluxo: dict = defaultdict(lambda: [0, 0.0])
    modal = MODALIDADES[grupo]
    campo_est = f"{grupo}_ESTADI"
    for rec in registros_dbc(dados, nome, Counter()):
        mun_pcn = _limpo(rec.get("AP_MUNPCN"))[:6]
        mun_est = _limpo(rec.get("AP_UFMUN"))[:6]
        if len(mun_pcn) != 6:
            continue
        cid = _limpo(rec.get("AP_CIDPRI"))[:3]
        est = _estadio(rec.get(campo_est))
        try:
            valor = float(rec.get("AP_VL_AP") or 0)
        except (TypeError, ValueError):
            valor = 0.0
        t = trat[(mun_pcn, ano, modal, cid, est)]
        t[0] += 1
        t[1] += valor
        if len(mun_est) == 6:
            f = fluxo[(mun_pcn, mun_est, ano, modal)]
            f[0] += 1
            f[1] += valor
    return trat, fluxo


def coletar_ano(ano: int, workers: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trat: dict = defaultdict(lambda: [0, 0.0])
    fluxo: dict = defaultdict(lambda: [0, 0.0])
    cobertura: list[dict] = []

    tarefas = [(uf, mes, g) for uf in UFS for mes in range(1, 13) for g in MODALIDADES]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futuros = {ex.submit(_processar, uf, ano, mes, g): (uf, mes, g)
                   for uf, mes, g in tarefas}
        por_uf: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
        for fut in as_completed(futuros):
            uf, mes, g = futuros[fut]
            chave = (uf, g)
            try:
                t, f = fut.result()
            except ArquivoAusente:
                por_uf[chave][1] += 1          # competência não publicada
                continue
            except FalhaDeColeta:
                por_uf[chave][2] += 1          # existe e falhou — NÃO é ausência
                continue
            por_uf[chave][0] += 1
            for k, v in t.items():
                trat[k][0] += v[0]; trat[k][1] += v[1]
            for k, v in f.items():
                fluxo[k][0] += v[0]; fluxo[k][1] += v[1]

    for (uf, g), (ok, ausentes, falhas) in sorted(por_uf.items()):
        cobertura.append({"uf_sigla": uf, "ano": ano, "modalidade": MODALIDADES[g],
                          "meses_coletados": ok, "meses_ausentes": ausentes,
                          "meses_com_falha": falhas})

    df_t = pd.DataFrame(
        [{"municipio_cod": k[0], "ano": k[1], "modalidade": k[2], "cid3": k[3],
          "estadiamento": k[4], "apacs": v[0], "valor_aprovado": round(v[1], 2)}
         for k, v in trat.items()])
    df_f = pd.DataFrame(
        [{"municipio_cod_residencia": k[0], "municipio_cod_atendimento": k[1],
          "ano": k[2], "modalidade": k[3], "apacs": v[0],
          "valor_aprovado": round(v[1], 2)} for k, v in fluxo.items()])
    return df_t, df_f, pd.DataFrame(cobertura)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", type=int)
    ap.add_argument("--ano-inicio", type=int, default=2013)
    ap.add_argument("--ano-fim", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    anos = [args.ano] if args.ano else list(range(args.ano_inicio, args.ano_fim + 1))
    res = Resultado("scripts/pipeline_siasus_oncologia.py")
    CKPT.mkdir(parents=True, exist_ok=True)

    for ano in anos:
        alvo_t = CKPT / f"tratamento_{ano}.parquet"
        if alvo_t.exists():
            print(f"[onco] {ano}: checkpoint", flush=True)
            continue
        t, f, c = coletar_ano(ano, args.workers)
        if t.empty:
            print(f"[onco] {ano}: nada coletado", flush=True)
            continue
        t.to_parquet(alvo_t, compression="zstd", index=False)
        f.to_parquet(CKPT / f"fluxo_{ano}.parquet", compression="zstd", index=False)
        c.to_parquet(CKPT / f"cobertura_{ano}.parquet", compression="zstd", index=False)
        falhas = int(c["meses_com_falha"].sum())
        print(f"[onco] {ano}: {t['apacs'].sum():,} APACs | "
              f"R$ {t['valor_aprovado'].sum()/1e6:,.1f} mi | "
              f"{t['municipio_cod'].nunique():,} municípios"
              + (f" | {falhas} mês(es) COM FALHA" if falhas else ""), flush=True)

    print("[ok] checkpoints em", CKPT)
    return res.relatar()


if __name__ == "__main__":
    sys.exit(main())
