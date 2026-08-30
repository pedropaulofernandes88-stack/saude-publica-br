"""
pipeline_sinasc.py — SINASC (nascidos vivos) → natalidade + mortalidade infantil
=================================================================================

Processa as Declarações de Nascido Vivo (SINASC/DataSUS) por município e ano,
em streaming com checkpoint por UF-ano (resiliente), e deriva:
  - mart_natalidade_municipio: nascidos vivos, % baixo peso (<2500g),
    % prematuro (<37 sem), % >=7 consultas pré-natal, idade média da mãe
  - mart_mortalidade_infantil_uf: óbitos <1 ano (SIM) / nascidos vivos (SINASC),
    por UF e ano — Taxa de Mortalidade Infantil (por mil nascidos vivos)

Fonte: /dissemin/publicos/SINASC/NOV/DNRES/DN{UF}{AAAA}.dbc
Óbitos <1 ano: mart_mortalidade_uf_mes (faixa '<1'), já na base.

Crédito: a integração de natalidade/mortalidade infantil e o cruzamento social
seguem a linha do LabSUS (Lucas Amaral Dourado, UFT). Métodos de domínio público.

Uso:
  .venv311/Scripts/python scripts/pipeline_sinasc.py --anos 2021 2022 2023 --workers 6
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

from _datasus_ftp import ArquivoAusente, FalhaDeColeta, baixar, gravar_checkpoint, listar
from _publicacao import escrever_parquet
from _supabase_key import chave_escrita

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS_DIR = ROOT / "data" / "marts"
CKPT = ROOT / "data" / "raw" / "SINASC" / "ckpt"

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SINASC/NOV/DNRES"

# Os DEFINITIVOS por UF param em 2022 no FTP; o PRELIM só tem 2025 e 2026.
# 2023 e 2024 existem, mas apenas como CSV nacional no portal de dados abertos
# — mesmo desenho que o SIM já usa (ver pipeline_v2.py). Adivinhar o nome do
# arquivo deu 403 em quatro tentativas; o caminho certo é ler o recurso na
# página do conjunto, e não presumir o padrão.
S3_SINASC = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv"

# UF pelo prefixo do código IBGE. Não depende do arquivo de referência: um
# município ausente de refs ainda cai na UF certa, em vez de sumir do ano.
UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
       "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]

URL = "https://zekjhmxjamatlxpkykde.supabase.co"


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


def anos_definitivos_no_ftp() -> set[int]:
    """Anos com arquivo DEFINITIVO por UF no FTP, lidos da listagem.

    Constante escrita a mao envelhece em silencio: no dia em que o DATASUS
    publicar o definitivo de 2023, o pipeline tem de migrar sozinho do CSV para
    o FTP, sem ninguem lembrar de editar um numero.
    """
    padrao = re.compile(r"DN[A-Z]{2}(\d{4})\.dbc$", re.IGNORECASE)
    return {int(m.group(1)) for n in listar(FTP_DIR) if (m := padrao.match(n))}


def _agregar_registro(agg: dict, mun: str, peso: str, sem: str, gest: str,
                      cons: str, consc: str, idm: str) -> None:
    """Uma DN -> contadores do municipio. Mesma regra para DBC e para CSV.

    Existe para que as duas fontes nao divirjam em definicao: se o criterio de
    baixo peso mudar aqui, muda para os dois caminhos ao mesmo tempo.
    """
    c = agg[mun]
    c[0] += 1
    if peso.isdigit() and 0 < int(peso) < 2500:
        c[1] += 1
    if sem.isdigit() and 0 < int(sem) < 37:
        c[2] += 1
    elif gest in ("1", "2", "3"):        # 1..5 (<22..>=42); 1-3 = <37 sem
        c[2] += 1
    if cons.isdigit() and int(cons) >= 7:
        c[3] += 1
    elif consc == "4":                   # 4 = 7+ consultas
        c[3] += 1
    if idm.isdigit() and 10 <= int(idm) <= 60:
        c[4] += int(idm)
        c[5] += 1


def preparar_ano_csv(ano: int) -> None:
    """Baixa o CSV nacional do ano e escreve os MESMOS checkpoints por UF-ano.

    Assim o resto do pipeline nao sabe de onde o ano veio: `build` continua
    lendo checkpoint por UF, e a conferencia cruzada continua valendo.
    """
    CKPT.mkdir(parents=True, exist_ok=True)
    faltando = [uf for uf in UFS if not (CKPT / f"sinasc_{uf}_{ano}.parquet").exists()]
    if not faltando:
        print(f"[sinasc] {ano}: checkpoints de todas as UFs ja existem", flush=True)
        return

    import csv as _csv
    import zipfile

    _csv.field_size_limit(10_000_000)
    url = f"{S3_SINASC}/SINASC_{ano}_csv.zip"
    cab = requests.head(url, allow_redirects=True, timeout=60)
    if cab.status_code == 404:
        raise ArquivoAusente(f"SINASC_{ano}_csv.zip nao existe na origem")
    cab.raise_for_status()
    esperado = int(cab.headers["Content-Length"])

    destino = Path(tempfile.gettempdir()) / f"SINASC_{ano}_csv.zip"
    # Retomada por Range: conexao caida nao pode custar o que ja foi baixado.
    for tentativa in range(1, 5):
        ja = destino.stat().st_size if destino.exists() else 0
        if ja == esperado:
            break
        if ja > esperado:
            destino.unlink()
            ja = 0
        try:
            cabecalho = {"Range": f"bytes={ja}-"} if ja else {}
            with requests.get(url, stream=True, timeout=600, headers=cabecalho) as r:
                r.raise_for_status()
                # 200 a um pedido com Range = servidor ignorou a retomada.
                modo = "ab" if (ja and r.status_code == 206) else "wb"
                with open(destino, modo) as fh:
                    for bloco in r.iter_content(chunk_size=1 << 20):
                        fh.write(bloco)
        except (requests.RequestException, OSError) as e:
            print(f"[sinasc] {ano}: download interrompido ({type(e).__name__}), "
                  f"tentativa {tentativa}", flush=True)
    if destino.stat().st_size != esperado:
        tamanho = destino.stat().st_size
        destino.unlink(missing_ok=True)
        raise FalhaDeColeta(f"SINASC {ano}: baixou {tamanho} de {esperado} bytes")
    print(f"[sinasc] {ano}: CSV nacional {esperado / 1e6:.0f} MB", flush=True)

    agg: dict = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    linhas = 0
    with zipfile.ZipFile(destino) as z:
        nome = z.namelist()[0]
        with z.open(nome) as bruto:
            leitor = _csv.DictReader(
                io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")
            for rec in leitor:
                linhas += 1
                mun = (rec.get("CODMUNRES") or "").strip()[:6]
                if len(mun) < 6:
                    continue
                _agregar_registro(
                    agg, mun,
                    (rec.get("PESO") or "").strip(),
                    (rec.get("SEMAGESTAC") or "").strip(),
                    (rec.get("GESTACAO") or "").strip(),
                    (rec.get("CONSPRENAT") or "").strip(),
                    (rec.get("CONSULTAS") or "").strip(),
                    (rec.get("IDADEMAE") or "").strip())
    destino.unlink(missing_ok=True)

    df = pd.DataFrame(
        [(m, ano, c[0], c[1], c[2], c[3], c[4], c[5]) for m, c in agg.items()],
        columns=["municipio_cod", "ano", "nascidos", "baixo_peso", "prematuro",
                 "prenatal_7mais", "idade_mae_soma", "idade_mae_n"])
    df["uf"] = df.municipio_cod.str[:2].map(UF_POR_CODIGO)
    sem_uf = int(df[df.uf.isna()].nascidos.sum())
    if sem_uf:
        print(f"[sinasc] {ano}: {sem_uf:,} nascidos com codigo de UF desconhecido",
              flush=True)

    fonte = f"SINASC_{ano}.csv bytes={esperado}"
    for uf in UFS:
        parte = df[df.uf == uf].drop(columns="uf")
        if parte.empty:
            # UF sem nenhum nascido no arquivo nacional e defeito do arquivo,
            # nao ausencia legitima -- nao gravar checkpoint vazio por cima.
            raise FalhaDeColeta(f"SINASC {ano}: {uf} sem registro no CSV nacional")
        gravar_checkpoint(parte, CKPT / f"sinasc_{uf}_{ano}.parquet", fonte=fonte)
    print(f"[sinasc] {ano}: {linhas:,} DN lidas -> {int(df.nascidos.sum()):,} nascidos "
          f"em {len(UFS)} checkpoints (fonte CSV)", flush=True)


def _process_uf_ano(uf: str, ano: int, via_csv: bool = False) -> pd.DataFrame:
    """Um DN{UF}{ANO}.dbc → df agregado por município. Checkpoint resumível."""
    CKPT.mkdir(parents=True, exist_ok=True)
    ckpt = CKPT / f"sinasc_{uf}_{ano}.parquet"
    if ckpt.exists():
        return pd.read_parquet(ckpt)
    if via_csv:
        # O CSV nacional ja deveria ter escrito este checkpoint. Faltar aqui e
        # falha, nao ausencia: devolver vazio sumiria com a UF do ano.
        raise FalhaDeColeta(f"SINASC {ano}: checkpoint de {uf} nao veio do CSV")

    import subprocess
    import dbfread

    nome = f"DN{uf}{ano}"
    # Ausência e falha eram o mesmo `DataFrame()` vazio: uma UF que falhasse
    # no download sumia do ano sem alarme. Ver `_datasus_ftp`.
    try:
        dados = baixar(FTP_DIR, f"{nome}.dbc")
    except ArquivoAusente:
        return pd.DataFrame()      # ano inexistente p/ a UF

    tmp = Path(tempfile.gettempdir())
    dbc = tmp / f"{nome}.dbc"
    dbf = tmp / f"{nome}.dbf"
    dbc.write_bytes(dados)
    dbf.unlink(missing_ok=True)
    ok = False
    for _ in range(3):
        r = subprocess.run([sys.executable, "-c",
            f"import datasus_dbc; datasus_dbc.decompress(r'{dbc}', r'{dbf}')"],
            capture_output=True, text=True)
        if r.returncode == 0 and dbf.exists() and dbf.stat().st_size > 5000:
            ok = True
            break
        dbf.unlink(missing_ok=True)
    if not ok:
        dbc.unlink(missing_ok=True)
        raise FalhaDeColeta(f"{nome}: 3 tentativas de descompactar falharam")

    agg: dict = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    # [nascidos, baixo_peso, prematuro, prenatal7, idade_mae_soma, idade_mae_n]
    try:
        for rec in dbfread.DBF(str(dbf), encoding="latin-1", char_decode_errors="replace", load=False):
            mun = (str(rec.get("CODMUNRES") or "")).strip()[:6]
            if len(mun) < 6:
                continue
            c = agg[mun]
            c[0] += 1
            peso = str(rec.get("PESO") or "").strip()
            if peso.isdigit() and 0 < int(peso) < 2500:
                c[1] += 1
            sem = str(rec.get("SEMAGESTAC") or "").strip()
            if sem.isdigit() and 0 < int(sem) < 37:
                c[2] += 1
            else:
                gest = str(rec.get("GESTACAO") or "").strip()  # 1..5 (<22..>=42); 1-3 = <37 sem
                if gest in ("1", "2", "3"):
                    c[2] += 1
            cons = str(rec.get("CONSPRENAT") or "").strip()
            if cons.isdigit() and int(cons) >= 7:
                c[3] += 1
            else:
                consc = str(rec.get("CONSULTAS") or "").strip()  # 4 = 7+ consultas
                if consc == "4":
                    c[3] += 1
            idm = str(rec.get("IDADEMAE") or "").strip()
            if idm.isdigit() and 10 <= int(idm) <= 60:
                c[4] += int(idm); c[5] += 1
    finally:
        dbc.unlink(missing_ok=True)
        dbf.unlink(missing_ok=True)

    df = pd.DataFrame(
        [(m, ano, c[0], c[1], c[2], c[3], c[4], c[5]) for m, c in agg.items()],
        columns=["municipio_cod", "ano", "nascidos", "baixo_peso", "prematuro",
                 "prenatal_7mais", "idade_mae_soma", "idade_mae_n"])
    df.to_parquet(ckpt, compression="zstd", index=False)
    print(f"[sinasc] {uf} {ano}: {int(df['nascidos'].sum()):,} nascidos → checkpoint", flush=True)
    return df


def build(anos: list[int], workers: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    partes = []
    no_ftp = anos_definitivos_no_ftp()
    print(f"[sinasc] definitivos no FTP: {min(no_ftp)}-{max(no_ftp)}", flush=True)
    for a in anos:
        via_csv = a not in no_ftp
        if via_csv:
            print(f"[sinasc] {a}: sem definitivo no FTP, usando o CSV nacional", flush=True)
            preparar_ano_csv(a)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_process_uf_ano, uf, a, via_csv): uf for uf in UFS}
            for fut in as_completed(futs):
                d = fut.result()
                if not d.empty:
                    partes.append(d)
        print(f"[sinasc] ano {a} concluído", flush=True)
    base = pd.concat(partes, ignore_index=True)
    base = base.groupby(["municipio_cod", "ano"], as_index=False).sum()

    municipios = pd.read_parquet(REFS / "municipios.parquet")
    nat = base.merge(municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]],
                     on="municipio_cod", how="left")
    nat["uf_sigla"] = nat["uf_sigla"].fillna("ND")
    nat["pct_baixo_peso"] = (nat["baixo_peso"] / nat["nascidos"] * 100).round(2)
    nat["pct_prematuro"] = (nat["prematuro"] / nat["nascidos"] * 100).round(2)
    nat["pct_prenatal_7mais"] = (nat["prenatal_7mais"] / nat["nascidos"] * 100).round(2)
    nat["idade_media_mae"] = (nat["idade_mae_soma"] / nat["idade_mae_n"]).round(1)
    nat = nat[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano", "nascidos",
               "pct_baixo_peso", "pct_prematuro", "pct_prenatal_7mais", "idade_media_mae"]]

    # Taxa de mortalidade infantil por UF: óbitos <1 ano (SIM) / nascidos vivos (SINASC) * 1000
    nv_uf = base.merge(municipios[["municipio_cod", "uf_sigla"]], on="municipio_cod", how="left") \
                .groupby(["uf_sigla", "ano"], as_index=False)["nascidos"].sum()
    env = load_env()
    H = {"apikey": env["SUPABASE_ANON_KEY"]}
    obi = requests.get(f"{URL}/rest/v1/mart_mortalidade_uf_mes", params={
        "select": "uf_sigla,ano,obitos:obitos.sum()",
        "faixa_etaria": "eq.<1", "sexo": "eq.TOTAL", "capitulo_cid": "eq.TOTAL",
        "ano": f"in.({','.join(str(a) for a in anos)})",
    }, headers=H, timeout=120).json()
    obidf = pd.DataFrame(obi).rename(columns={"obitos": "obitos_menor1"})
    obidf["ano"] = obidf["ano"].astype(int)
    tmi = nv_uf.merge(obidf, on=["uf_sigla", "ano"], how="left")
    tmi["tmi_por_mil"] = (tmi["obitos_menor1"] / tmi["nascidos"] * 1000).round(2)
    tmi = tmi[["uf_sigla", "ano", "nascidos", "obitos_menor1", "tmi_por_mil"]]

    nat = nat.sort_values(["municipio_cod", "ano"]).reset_index(drop=True)
    print(f"[sinasc] natalidade: {len(nat):,} linhas | TMI: {len(tmi):,} linhas")
    print(f"[sinasc] nascidos {min(anos)}–{max(anos)}: {int(base['nascidos'].sum()):,}")
    return nat, tmi


class Loader:
    def __init__(self, url, key, batch=8000):
        self.url = url.rstrip("/"); self.batch = batch
        self.h = {"apikey": key, "Authorization": f"Bearer {key}",
                  "Content-Type": "application/json",
                  "Prefer": "return=minimal,resolution=merge-duplicates"}

    def load(self, table, df):
        recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
        nb = math.ceil(len(recs) / self.batch)
        for i in range(nb):
            body = json.dumps(recs[i*self.batch:(i+1)*self.batch], default=_jd, allow_nan=False)
            for a in range(4):
                r = requests.post(f"{self.url}/rest/v1/{table}", headers=self.h, data=body, timeout=300)
                if r.status_code in (200, 201):
                    break
                if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                    raise RuntimeError(f"{table} lote {i+1}/{nb}: HTTP {r.status_code} {r.text[:200]}")
                time.sleep(3 * (a + 1))
        print(f"[supabase]   {table}: {len(recs):,} OK")


def _jd(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(str(type(o)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="+", type=int, default=[2021, 2022, 2023])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    anos = sorted(args.anos)
    env = load_env()

    nat, tmi = build(anos, args.workers)
    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    for df_, nome_ in ((nat, "mart_natalidade_municipio"), (tmi, "mart_mortalidade_infantil_uf")):
        escrever_parquet(df_, MARTS_DIR / f"{nome_}.parquet", origem="pipeline",
                         produtor="scripts/pipeline_sinasc.py")
    if args.no_upload:
        return

    ld = Loader(env["SUPABASE_URL"], chave_escrita(env))
    ld.load("mart_natalidade_municipio", nat)
    ld.load("mart_mortalidade_infantil_uf", tmi)
    meta = pd.DataFrame([
        ("fonte_sinasc", "SINASC/DataSUS — DN (nascidos vivos): FTP NOV/DNRES por UF até o último ano definitivo; CSV nacional do portal de dados abertos nos anos ainda sem definitivo"),
        ("sinasc_cobertura", f"{min(anos)}–{max(anos)}"),
        ("sinasc_definicoes", "Nascidos por residência (CODMUNRES); baixo peso<2500g; prematuro<37sem; pré-natal 7+ consultas; TMI=óbitos<1ano(SIM)/nascidos*1000"),
        ("gerado_em", datetime.now().isoformat(timespec="seconds")),
    ], columns=["chave", "valor"])
    ld.load("meta_dataset", meta)
    print("[done] pipeline SINASC concluído.")


if __name__ == "__main__":
    main()
