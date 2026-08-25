"""
pipeline_siops.py — Gasto público municipal em saúde (SIOPS) → mart agregado
============================================================================

O projeto media desfecho (mortalidade, ICSAP, HSMR) e oferta física (leitos),
nunca o INSUMO FINANCEIRO. O SIOPS é a única base nacional com orçamento público
de saúde por município, e é o que permite perguntar se gastar mais está associado
a internar menos por condição evitável.

DE ONDE VEM. O SIOPS não está no FTP do DataSUS nem na API de dados abertos do
Ministério (85 rotas, nenhuma financeira). Também não está no SICONFI: o Anexo 12
do RREO — o demonstrativo de saúde — é transmitido pelo próprio SIOPS e não
aparece na API do Tesouro (conferido em 3 capitais × 3 anos). A via publica é o
TABNET da série histórica de indicadores:

  http://siops-asp.datasus.gov.br/cgi/tabcgi.exe?SIOPS/serhist/municipio/indic{UF}.def

um .def por UF, um arquivo indmun{AA}.dbf por ano. Os DBF não são servidos
diretamente (404), então a extração é por POST no formulário, em `formato=prn`,
que devolve `"{cod6} {nome}";{valor}` por linha. O TABNET é ISO-8859-1: enviar
os campos acentuados em UTF-8 devolve "Tabela de conversão não encontrada".

INDICADORES EXTRAÍDOS
  D.R.Próprios_em_Saúde/Hab        gasto com recursos próprios por habitante (R$)
  3.2_%R.Próprios_em_Saúde-EC_29   % da receita própria aplicada em ASPS — o piso
                                   constitucional de 15% (EC 29 / LC 141)
  D.Total_Saúde                    despesa total em saúde (R$)
  R.Transf.SUS/Hab                 transferências do SUS por habitante (R$)
  População                        população declarada — só para conferência

SUBFUNÇÕES NÃO ENTRAM. Os indicadores 2.20/2.21 (atenção básica, assistência
hospitalar) existem no .def mas vêm VAZIOS de 2016 em diante — conferido em AC:
22 de 23 municípios preenchidos em 2015, zero em 2020 e em 2024. O SIOPS parou de
popular o detalhamento por subfunção na série histórica. Seria a variável mais
interessante para cruzar com ICSAP, e não está disponível no período do projeto.

LIMITAÇÕES (declaradas, não resolvidas)
  - AUTODECLARAÇÃO. O ente preenche e homologa; não há verificação externa das
    transações. Erro de classificação contábil entra no dado como se fosse gasto.
  - FASE DA DESPESA. Empenhada, liquidada e paga são valores diferentes no mesmo
    período. A série histórica do TABNET usa a despesa empenhada; misturar fases
    entre fontes invalida comparação.
  - PER CAPITA EM MUNICÍPIO PEQUENO OSCILA MUITO. Uma obra num município de 3 mil
    habitantes desloca o indicador de um ano para o outro sem mudar nada
    estrutural. Comparar dentro de faixa de porte, como o resto do projeto faz.
  - CAPACIDADE FISCAL DIFERENTE. Ranquear municípios por gasto sem controlar
    receita própria e papel regional compara coisas distintas.
  - GASTO NÃO É ACESSO NEM QUALIDADE. O SIOPS não mede produção assistencial,
    acesso ou necessidade. Cruzar com SIH/SIA é ecológico e não estabelece causa.
  - RESTOS A PAGAR. Despesa inscrita, cancelada ou compensada em exercícios
    anteriores afeta retroativamente o cumprimento do mínimo.

Fundamentação: R. F. Saldanha, "Sistemas de Informação em Saúde no Brasil",
cap. SIOPS — https://rfsaldanha.github.io/sis/siops.html

Uso:
  .venv311/Scripts/python scripts/pipeline_siops.py --anos 2021 2022 2023 2024
"""
from __future__ import annotations

import argparse
import html as H
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

from _supabase_key import chave_escrita
from _varredura import varrer_orfaos
from _publicacao import escrever_parquet

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "SIOPS" / "ckpt"

BASE = "http://siops-asp.datasus.gov.br/cgi/tabcgi.exe?SIOPS/serhist/municipio/indic{uf}.def"
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "ES", "GO", "MA", "MG", "MS", "MT",
       "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
# NB: o DF não tem .def municipal — é ente estadual/distrital, tabulado à parte.

#: indicador do TABNET -> coluna do mart
INDICADORES = {
    "D.R.Próprios_em_Saúde/Hab":      "gasto_proprio_saude_hab",
    "3.2_%R.Próprios_em_Saúde-EC_29": "pct_receita_propria_saude",
    "D.Total_Saúde":                   "despesa_total_saude",
    "R.Transf.SUS/Hab":                "transf_sus_hab",
    "População":                       "populacao_siops",
}

LINHA_PRN = re.compile(r'^"(\d{6})\s+(.*?)";([-\d.,]*)\s*$')


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})
    return env


def _numero(txt: str) -> float | None:
    """'1.012,63' -> 1012.63 ; '-' e '' -> None (o TABNET usa '-' para ausente)."""
    txt = (txt or "").strip()
    if not txt or txt in {"-", "..."}:
        return None
    try:
        return float(txt.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def parse_prn(texto: str) -> dict[str, float | None]:
    """Extrai {municipio_cod6: valor} do corpo `formato=prn` do TABNET.

    O corpo vem como linhas `"350010 Adamantina";1012,63`, com entidades HTML nos
    acentos e uma linha "Total" no fim que NÃO é município.
    """
    out: dict[str, float | None] = {}
    for linha in H.unescape(texto).splitlines():
        m = LINHA_PRN.match(linha.strip())
        if not m:
            continue
        cod, _nome, valor = m.groups()
        out[cod] = _numero(valor)
    return out


def _consultar(uf: str, ano: int, indicador: str, tentativas: int = 3) -> dict[str, float | None]:
    """Um POST no TABNET: uma UF, um ano, um indicador."""
    url = BASE.format(uf=uf)
    campos = [
        ("Linha", "Municípios"),
        ("Coluna", "--Não-Ativa--"),
        ("Incremento", indicador),
        ("Arquivos", f"indmun{ano % 100:02d}.dbf"),
        ("SMunicípio", "TODAS_AS_CATEGORIAS__"),
        ("zeradas", "exibirlz"),
        ("formato", "prn"),
        ("mostre", "Mostra"),
    ]
    corpo = "&".join(
        f"{quote(k, encoding='latin-1')}={quote(v, encoding='latin-1')}" for k, v in campos
    ).encode("latin-1")
    for t in range(tentativas):
        try:
            r = requests.post(url, data=corpo, timeout=240, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": url, "User-Agent": "saude-em-dado/1.0 (+https://saudeemdado.com)"})
            r.encoding = "latin-1"
            if "convers" in r.text and "encontrada" in r.text:
                raise RuntimeError("TABNET recusou os parâmetros (tabela de conversão)")
            return parse_prn(r.text)
        except Exception as exc:
            if t == tentativas - 1:
                print(f"  [{uf} {ano}] {indicador}: FALHOU — {exc}", flush=True)
                return {}
            time.sleep(4 * (t + 1))
    return {}


def _processar_uf_ano(uf: str, ano: int) -> pd.DataFrame:
    CKPT.mkdir(parents=True, exist_ok=True)
    ck = CKPT / f"siops_{uf}_{ano}.parquet"
    if ck.exists():
        return pd.read_parquet(ck)

    colunas: dict[str, dict[str, float | None]] = {}
    for indicador, coluna in INDICADORES.items():
        colunas[coluna] = _consultar(uf, ano, indicador)
        time.sleep(1.0)  # o TABNET é um CGI antigo; não convém martelar

    municipios = sorted({c for d in colunas.values() for c in d})
    if not municipios:
        print(f"[siops] {uf} {ano}: sem dados", flush=True)
        return pd.DataFrame()

    df = pd.DataFrame({"municipio_cod": municipios, "ano": ano})
    for coluna, mapa in colunas.items():
        df[coluna] = df["municipio_cod"].map(mapa)
    df.to_parquet(ck, compression="zstd", index=False)
    n_ok = int(df["gasto_proprio_saude_hab"].notna().sum())
    print(f"[siops] {uf} {ano}: {len(df):,} municípios ({n_ok:,} com gasto próprio) → checkpoint",
          flush=True)
    return df


def build(anos: list[int]) -> pd.DataFrame:
    partes = [_processar_uf_ano(uf, ano) for ano in anos for uf in UFS]
    partes = [p for p in partes if not p.empty]
    df = pd.concat(partes, ignore_index=True)

    # O TABNET fecha cada UF com uma pseudo-linha de total (código terminado em
    # 0000, população 0). Não é município: o join com a referência do IBGE a
    # elimina, e é por isso que o merge aqui é `inner` e não `left`.
    municipios = pd.read_parquet(REFS / "municipios.parquet")
    antes = len(df)
    df = df.merge(municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]],
                  on="municipio_cod", how="inner")
    if antes != len(df):
        print(f"[siops] {antes - len(df)} linhas descartadas por não serem município "
              f"(totais de UF do TABNET)", flush=True)

    # Sinaliza quem não alcançou o piso constitucional de 15% da receita própria
    # em ASPS (EC 29 / LC 141). NULL quando o ente não declarou — ausência de
    # declaração não é descumprimento, e afirmar isso seria acusação sem base.
    df["abaixo_do_minimo_ec29"] = df["pct_receita_propria_saude"].lt(15.0).where(
        df["pct_receita_propria_saude"].notna())

    df = df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano",
             "populacao_siops", "gasto_proprio_saude_hab", "despesa_total_saude",
             "transf_sus_hab", "pct_receita_propria_saude", "abaixo_do_minimo_ec29"]]
    return df.sort_values(["municipio_cod", "ano"]).reset_index(drop=True)


def _jd(o):
    return o.item() if hasattr(o, "item") else o


def publicar(df: pd.DataFrame, env: dict[str, str], anos: list[int]) -> None:
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
    lotes = math.ceil(len(recs) / 8000)
    for i in range(lotes):
        corpo = json.dumps(recs[i * 8000:(i + 1) * 8000], default=_jd, allow_nan=False)
        for t in range(4):
            r = requests.post(f"{url}/rest/v1/mart_siops_municipio", headers=h,
                              data=corpo, timeout=300)
            if r.status_code in (200, 201):
                break
            if t == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"mart_siops_municipio: HTTP {r.status_code} {r.text[:200]}")
            time.sleep(3 * (t + 1))
        print(f"[supabase] mart_siops_municipio: lote {i + 1}/{lotes}", flush=True)
    varrer_orfaos(url, key, "mart_siops_municipio", df,
                  chaves=["municipio_cod", "ano"],
                  escopo={"ano": f"in.({','.join(str(a) for a in anos)})"})

    meta = [{"chave": "fonte_siops",
             "valor": f"SIOPS/Ministério da Saúde, série histórica de indicadores municipais "
                      f"(TABNET siops-asp.datasus.gov.br), anos {anos}. Despesa EMPENHADA. "
                      f"Dado AUTODECLARADO pelo ente e homologado pelo gestor — não há "
                      f"verificação externa. Gasto não mede acesso nem qualidade."}]
    requests.post(f"{url}/rest/v1/meta_dataset", headers=h, data=json.dumps(meta), timeout=60)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", type=int, nargs="+", default=[2021, 2022, 2023, 2024])
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    df = build(args.anos)
    MARTS.mkdir(exist_ok=True)
    escrever_parquet(df, MARTS / "mart_siops_municipio.parquet", origem="pipeline",
                     produtor="scripts/pipeline_siops.py")

    print(f"\n[siops] mart_siops_municipio: {len(df):,} linhas "
          f"({df.municipio_cod.nunique():,} municípios × {df.ano.nunique()} anos)")
    for ano in sorted(df.ano.unique()):
        s = df[df.ano == ano]
        med = s["gasto_proprio_saude_hab"].median()
        abaixo = int(s["abaixo_do_minimo_ec29"].fillna(False).sum())
        decl = int(s["pct_receita_propria_saude"].notna().sum())
        print(f"  {ano}: gasto próprio mediano R$ {med:,.0f}/hab | "
              f"{decl:,} declararam | {abaixo:,} abaixo dos 15% da EC 29")

    if args.no_upload:
        return
    publicar(df, load_env(), args.anos)
    print("[done] SIOPS concluído.")


if __name__ == "__main__":
    main()
