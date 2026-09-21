"""
pipeline_rhc.py — Registro Hospitalar de Câncer: a 16ª fonte, e a primeira por
PESSOA
==============================================================================

    python scripts/pipeline_rhc.py                 # 2013–2023
    python scripts/pipeline_rhc.py --anos 2019 2020

POR QUE ESTA FONTE ENTRA
------------------------
Todas as fontes oncológicas do projeto contam evento: a APAC conta
AUTORIZAÇÃO, o Painel conta caso mas deriva do próprio SIA. O RHC conta
**pessoa, com confirmação histopatológica**, e traz três coisas que nenhuma das
outras traz: escolaridade, raça/cor declarada no registro hospitalar, e o
**primeiro tratamento de qualquer modalidade** — que é o que a Lei 12.732/2012
efetivamente conta, e que a APAC de quimioterapia não consegue observar.

A sondagem que decidiu isto está em `scripts/sondar_rhc.py`, com as quatro
armadilhas medidas. Este pipeline as respeita, e o portão de lá é o que avisa
se alguma mudar.

O QUE ESTE PIPELINE PUBLICA
---------------------------
`mart_rhc_caso`     município de RESIDÊNCIA × ano da primeira consulta × CID-3
                    × estadiamento × tipo de caso → casos e prazo
`mart_rhc_cobertura` ano × UF → o que entrou, o que faltou, e por quê

AS ARMADILHAS, E COMO CADA UMA É TRATADA AQUI
---------------------------------------------
1. **`ESTADIAM` 88/99 não é estádio.** Vira `"ignorado"`, com rótulo próprio,
   nunca somado a estádio 0. São ~53% dos registros, e publicá-los como estádio
   inventaria uma distribuição. Mesma regra de `_estadio` na APAC, e pela mesma
   razão: lá o erro custou uma coleta inteira.
2. **O ano do arquivo é o da PRIMEIRA CONSULTA**, não o do diagnóstico. A
   coluna se chama `ano_primeira_consulta` por isso. `ANOPRIDI` diverge dela em
   21,7% dos registros de 2019, e a cobertura publica essa divergência.
3. **Caso analítico e não analítico são universos diferentes.** `tipo_caso` é
   coluna de chave, não filtro escondido: quem quiser o universo da literatura
   filtra `analitico`, e quem somar os dois sabe o que está somando.
4. **A data é `DD/MM/YYYY`.** O leitor está em `sondar_rhc.data_br`, e recusa
   `YYYYMMDD` de propósito — é o formato do resto do projeto, e aceitá-lo aqui
   produziria data errada em silêncio.

O PRAZO É PUBLICADO AQUI, E NÃO NA APAC
---------------------------------------
`mart_apac_oncologia_*` não publica prazo, por decisão registrada: a subtração
entre `AQ_DTIDEN` e `AQ_DTINTR` conta autorização e produz manchete falsa
(2026-09-21: 256 dias contra 68 quando se conta pessoa). No RHC a unidade JÁ é
a pessoa e a data de diagnóstico é o laudo, então o prazo é o que a fonte
realmente mede.

Ainda assim ele sai em CONTAGEM, não em mediana: mediana não se agrega, e uma
coluna `mediana_dias` num mart municipal seria somada por quem lesse rápido. As
colunas são `casos_com_prazo`, `casos_ate_60d` e `casos_acima_60d`, e qualquer
proporção se calcula sobre elas.

Excluído do prazo, seguindo Jomar et al. 2023: intervalo negativo ou acima de
365 dias. Eles chamam de outlier e excluem 384 de 18.098; aqui a contagem do
que saiu fica na cobertura, e não em rodapé.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from _saida import Resultado  # noqa: E402
from sondar_rhc import (  # noqa: E402
    baixar_ano,
    campos_do_dbf,
    data_br,
    estadio,
    metadados_do_dbf,
)

CACHE = RAIZ / "data" / "cache"
MARTS = RAIZ / "data" / "marts"

#: 2013 é o primeiro ano inteiro sob a Lei 12.732/2012; 2023 é o último que o
#: INCA publica. Anos anteriores existem (desde 1985) e ficam fora por recorte,
#: não por indisponibilidade.
ANOS = tuple(range(2013, 2024))

#: Teto do intervalo, em dias, seguindo Jomar et al. 2023. Acima disso o
#: registro entra em `casos_sem_prazo` — não some.
TETO_PRAZO = 365
PRAZO_LEGAL = 60

TIPO_CASO = {"1": "analitico", "2": "nao_analitico"}

CAMPOS = ("TPCASO", "LOCTUDET", "ESTADIAM", "DTDIAGNO", "DATAINITRT",
          "PROCEDEN", "ESTADRES", "UFUH", "CNES", "ANOPRIDI")


def _registros(caminho: Path):
    """Itera o .dbf de dentro do .zip, devolvendo só os campos que interessam.

    Lê em blocos: o arquivo de 2019 tem 477 MB descompactados e 518 mil
    registros de 921 bytes. Carregar inteiro custaria mais memória que o
    pipeline da APAC, que processa quarenta vezes mais linhas.
    """
    z = zipfile.ZipFile(caminho)
    nome = next(n for n in z.namelist() if n.lower().endswith(".dbf"))
    with z.open(nome) as f:
        c32 = f.read(32)
        n, ini, larg = metadados_do_dbf(c32)
        campos = campos_do_dbf(c32 + f.read(ini - 32))
        sel = [(nm, o, t) for nm, o, t in campos if nm in CAMPOS]
        faltam = set(CAMPOS) - {nm for nm, _, _ in sel}
        if faltam:
            raise SystemExit(
                f"[rhc] {caminho.name}: campos ausentes {sorted(faltam)}. O "
                f"layout do INCA mudou; conferir com sondar_rhc.py antes de "
                f"publicar qualquer número.")
        lidos = 0
        while lidos < n:
            bloco = f.read(larg * min(20_000, n - lidos))
            if not bloco:
                break
            for i in range(0, len(bloco) - larg + 1, larg):
                r = bloco[i:i + larg]
                yield {nm: r[o:o + t].decode("latin-1").strip()
                       for nm, o, t in sel}
                lidos += 1


def _prazo(rec: dict) -> tuple[bool, int | None]:
    """(entrou no prazo, dias). `entrou=False` quando a data não serve.

    Ausência de data e intervalo impossível são a MESMA coluna na cobertura, e
    nenhuma das duas vira zero dia.
    """
    di, dt = data_br(rec["DTDIAGNO"]), data_br(rec["DATAINITRT"])
    if not di or not dt:
        return False, None
    dias = (pd.Timestamp(dt) - pd.Timestamp(di)).days
    if dias < 0 or dias > TETO_PRAZO:
        return False, dias
    return True, dias


def processar_ano(ano: int) -> tuple[dict, dict]:
    caminho = CACHE / f"rhc_{ano}.zip"
    if not caminho.exists():
        print(f"[rhc] {ano}: baixando", flush=True)
        baixar_ano(ano, caminho)

    casos: dict = defaultdict(lambda: [0, 0, 0, 0])   # casos, com_prazo, ate60, acima60
    cob: dict = defaultdict(lambda: defaultdict(int))
    hospitais: dict = defaultdict(set)
    municipios: dict = defaultdict(set)

    for rec in _registros(caminho):
        uf = rec["UFUH"] or "??"
        mun = rec["PROCEDEN"][:6]
        tipo = TIPO_CASO.get(rec["TPCASO"], "ignorado")
        est = estadio(rec["ESTADIAM"])
        cid = rec["LOCTUDET"][:3].upper()
        ok, _dias = _prazo(rec)

        c = cob[uf]
        c["casos"] += 1
        c[tipo] += 1
        if est == "ignorado":
            c["sem_estadiamento"] += 1
        if not ok:
            c["sem_prazo"] += 1
        if rec["ANOPRIDI"] and rec["ANOPRIDI"] != str(ano):
            c["ano_diagnostico_difere"] += 1
        if rec["CNES"]:
            hospitais[uf].add(rec["CNES"])
        if len(mun) == 6:
            municipios[uf].add(mun)

        if len(mun) != 6 or not cid:
            continue
        k = (mun, ano, cid, est, tipo)
        v = casos[k]
        v[0] += 1
        if ok:
            _, dias = _prazo(rec)
            v[1] += 1
            if dias <= PRAZO_LEGAL:
                v[2] += 1
            else:
                v[3] += 1

    for uf in cob:
        cob[uf]["hospitais"] = len(hospitais[uf])
        cob[uf]["municipios"] = len(municipios[uf])
    return casos, cob


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anos", type=int, nargs="*", default=list(ANOS))
    a = ap.parse_args()

    linhas_caso, linhas_cob = [], []
    for ano in a.anos:
        casos, cob = processar_ano(ano)
        for (mun, an, cid, est, tipo), v in casos.items():
            linhas_caso.append((mun, an, cid, est, tipo, *v))
        for uf, c in cob.items():
            linhas_cob.append((ano, uf, c["casos"], c["analitico"],
                               c["nao_analitico"], c["sem_estadiamento"],
                               c["sem_prazo"], c["ano_diagnostico_difere"],
                               c["hospitais"], c["municipios"]))
        total = sum(c["casos"] for c in cob.values())
        print(f"[rhc] {ano}: {total:,} casos, {len(casos):,} combinações",
              flush=True)

    caso = pd.DataFrame(linhas_caso, columns=[
        "municipio_cod", "ano_primeira_consulta", "cid3", "estadiamento",
        "tipo_caso", "casos", "casos_com_prazo", "casos_ate_60d",
        "casos_acima_60d"])
    cobertura = pd.DataFrame(linhas_cob, columns=[
        "ano_primeira_consulta", "uf_sigla", "casos", "analiticos",
        "nao_analiticos", "sem_estadiamento", "sem_prazo",
        "ano_diagnostico_difere", "hospitais", "municipios"])

    _guardas(caso, cobertura)

    MARTS.mkdir(parents=True, exist_ok=True)
    res = Resultado("scripts/pipeline_rhc.py")
    res.gravar(caso, MARTS / "mart_rhc_caso.parquet")
    res.gravar(cobertura, MARTS / "mart_rhc_cobertura.parquet")
    print(f"[rhc] caso: {len(caso):,} linhas | "
          f"cobertura: {len(cobertura):,} linhas", flush=True)
    return res.relatar()


def _guardas(caso: pd.DataFrame, cob: pd.DataFrame) -> None:
    """As três que a sondagem disse serem necessárias, conferidas ano a ano."""
    if caso.empty or cob.empty:
        raise SystemExit("[rhc] mart vazio")

    for ano, sub in cob.groupby("ano_primeira_consulta"):
        pct = 100 * sub.sem_estadiamento.sum() / sub.casos.sum()
        if pct == 0:
            raise SystemExit(
                f"[rhc] {ano}: NENHUM caso sem estadiamento. Medido na "
                f"sondagem: ~53%. Zero significa que 88/99 voltaram a ser "
                f"lidos como estádio.")
        if pct > 90:
            raise SystemExit(f"[rhc] {ano}: {pct:.1f}% sem estadiamento — o "
                             f"campo mudou de código.")
        if sub.nao_analiticos.sum() == 0:
            raise SystemExit(
                f"[rhc] {ano}: nenhum caso não analítico. TPCASO parou de "
                f"distinguir os dois universos, e somá-los vira outro estudo.")

    soma = caso.casos_ate_60d + caso.casos_acima_60d
    if not (soma == caso.casos_com_prazo).all():
        raise SystemExit("[rhc] casos_ate_60d + casos_acima_60d não fecha com "
                         "casos_com_prazo: a classificação perdeu registro.")
    if (caso.casos_com_prazo > caso.casos).any():
        raise SystemExit("[rhc] mais casos com prazo do que casos.")
    if "0" in set(caso.estadiamento) and "ignorado" not in set(caso.estadiamento):
        raise SystemExit("[rhc] há estádio 0 e nenhum 'ignorado' — é a "
                         "assinatura de ausência publicada como diagnóstico "
                         "precoce, o erro que a APAC já pagou.")


if __name__ == "__main__":
    sys.exit(main())
