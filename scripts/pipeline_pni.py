"""
pipeline_pni.py — PNI/RNDS: doses aplicadas, coleta e agregação
================================================================

Baixa os arquivos mensais de doses aplicadas do Programa Nacional de
Imunizações — alimentados pela Rede Nacional de Dados em Saúde — e os reduz a
três agregados por competência. O CSV bruto (5 a 13 GB por mês) é lido em
streaming de dentro do zip e nunca toca o disco.

A RNDS em si não é fonte consumível: exige CNES, certificado ICP-Brasil e
credenciamento no DATASUS, e trafega registro individual identificado. O que é
aberto é o derivado — registro individual PSEUDONIMIZADO (`co_paciente` é hash
de 64 caracteres), publicado por mês no portal de dados abertos do SUS.

Fonte: ckan.saude.gov.br/PNI/csv/vacinacao_{mes}_{ano}_csv.zip

CHAVE DE AGREGAÇÃO — decidida por medição, não por intuição. Cardinalidade
observada em agosto/2026 (10,9 milhões de doses):

    município × imuno × dose × faixa                835.749 linhas
    + sexo                                        1.233.658
    + raça/cor                                    2.130.991
    + etnia indígena                              2.135.830  (+4.839 sobre raça)
    UF × imuno × dose × faixa × sexo × raça         168.229
    município paciente × município estabelecimento  208.604

Daí as três saídas: sexo entra no municipal (+48% de linhas por uma dimensão
de equidade que o site já usa em mortalidade); raça/cor não entra no municipal
(+73%) e vai para o recorte por UF, que responde o mesmo por 1/7 do custo;
etnia indígena não entra em lugar nenhum, porque soma 4.839 linhas sobre
raça/cor — é redundante com o código de raça 05.

A primeira versão agregou `tipo_dose` e `faixa_etaria` em arquivos SEPARADOS.
Cobertura precisa dos dois juntos: "1ª dose de pentavalente em menores de 1
ano" não existia em nenhum dos dois, e o cálculo deu 231,8%.

GOTCHA: o CSV a granel e a API do DEMAS usam nomes DIFERENTES para os mesmos
campos (`co_municipio_paciente` no CSV, `codigo_municipio_paciente` na API).
Código escrito olhando a API quebra aqui. E a API não substitui este caminho:
`offset=50.000.000` devolve 502.

Uso:
  .venv311/Scripts/python scripts/pipeline_pni.py --anos 2023 2024 2025 2026
"""
from __future__ import annotations

import argparse
import array
import csv
import io
import json
import sys
import time
import traceback
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _datasus_ftp import ArquivoAusente, FalhaDeColeta  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SAIDA = ROOT / "data" / "raw" / "PNI" / "agregados"

S3 = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/PNI/csv"
MESES = [("jan", "01"), ("fev", "02"), ("mar", "03"), ("abr", "04"),
         ("mai", "05"), ("jun", "06"), ("jul", "07"), ("ago", "08"),
         ("set", "09"), ("out", "10"), ("nov", "11"), ("dez", "12")]

csv.field_size_limit(10_000_000)

FAIXAS = [(0, "<1"), (4, "1-4"), (9, "5-9"), (14, "10-14"), (19, "15-19"),
          (29, "20-29"), (39, "30-39"), (49, "40-49"), (59, "50-59"),
          (69, "60-69"), (79, "70-79")]


def log(msg: str) -> None:
    print(f"[pni {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def faixa_etaria(idade: str) -> str:
    try:
        i = int(idade)
    except (ValueError, TypeError):
        return "sem idade"
    if i < 0 or i > 120:
        return "idade invalida"
    for limite, rotulo in FAIXAS:
        if i <= limite:
            return rotulo
    return "80+"


def baixar(url: str, destino: Path, esperado: int, ref: str, tentativas: int = 5) -> None:
    """Baixa com retomada por Range.

    Conexão caída não pode custar os gigabytes já transferidos: numa das
    execuções o download morreu em 2,29 de 2,71 GB e o mês inteiro se perdeu.

    A guarda é o tamanho: só vale o arquivo cujo tamanho final bate com o que a
    origem declarou. Arquivo curto é FALHA, não ausência — devolver o que veio
    publicaria um mês incompleto sem alarme.
    """
    for tentativa in range(1, tentativas + 1):
        ja = destino.stat().st_size if destino.exists() else 0
        if ja == esperado:
            return
        if ja > esperado:          # sobra de outra versão do arquivo
            destino.unlink()
            ja = 0
        try:
            cab = {"Range": "bytes=%d-" % ja} if ja else {}
            if ja:
                log("%s: retomando em %.2f/%.2f GB (tentativa %d)"
                    % (ref, ja / 1e9, esperado / 1e9, tentativa))
            with requests.get(url, stream=True, timeout=600, headers=cab) as r:
                r.raise_for_status()
                # 200 a um pedido com Range = o servidor ignorou a retomada e
                # vai mandar tudo de novo; então o arquivo recomeça do zero.
                modo = "ab" if (ja and r.status_code == 206) else "wb"
                with open(destino, modo) as fh:
                    for bloco in r.iter_content(chunk_size=1 << 20):
                        fh.write(bloco)
        except (requests.RequestException, OSError) as e:
            log(f"{ref}: download interrompido ({type(e).__name__})")
    raise FalhaDeColeta("%s: %d tentativas e o arquivo segue diferente da origem"
                        % (ref, tentativas))


def processar_mes(ano: int, sigla: str, mm: str) -> dict | None:
    """Um mês → três Parquets agregados + metadados. Devolve None se ausente."""
    ref = "%d-%s" % (ano, mm)
    url = "%s/vacinacao_%s_%d_csv.zip" % (S3, sigla, ano)
    destino_meta = SAIDA / (f"meta_{ref}.json")
    zipf = SAIDA / (f"tmp_{ref}.zip")
    SAIDA.mkdir(parents=True, exist_ok=True)

    cab = requests.head(url, allow_redirects=True, timeout=60)
    if cab.status_code == 404:
        # Mês ainda não publicado é ausência esperada, não defeito.
        log(f"{ref}: ausente na origem (404)")
        raise ArquivoAusente(ref)
    if cab.status_code != 200:
        raise FalhaDeColeta("%s: HEAD devolveu %d" % (ref, cab.status_code))
    esperado = int(cab.headers["Content-Length"])

    # O S3 reescreve arquivos já publicados (mai/2025 foi regravado em
    # 28/08/2026). Cache só vale se o tamanho bater com a origem.
    if destino_meta.exists():
        antigo = json.loads(destino_meta.read_text(encoding="utf-8"))
        if antigo.get("bytes_origem") == esperado:
            log("%s: checkpoint válido (%d linhas), pulando" % (ref, antigo["linhas"]))
            return antigo
        anterior = antigo.get("bytes_origem")
        log(f"{ref}: origem mudou de {anterior} para {esperado} bytes, reprocessando")

    t0 = time.time()
    baixar(url, zipf, esperado, ref)
    minutos_download = (time.time() - t0) / 60

    municipal: Counter = Counter()
    equidade: Counter = Counter()
    fluxo: Counter = Counter()
    por_competencia: Counter = Counter()
    nulos: Counter = Counter()
    documentos = array.array("q")
    linhas = 0

    t0 = time.time()
    with zipfile.ZipFile(zipf) as z:
        nome = z.namelist()[0]
        gb_csv = z.getinfo(nome).file_size / 1e9
        with z.open(nome) as bruto:
            leitor = csv.DictReader(
                io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")
            for reg in leitor:
                linhas += 1
                por_competencia[(reg.get("dt_vacina") or "")[:7]] += 1
                municipio = reg.get("co_municipio_paciente") or ""
                imuno = reg.get("sg_imunobiologico") or ""
                dose = reg.get("ds_tipo_dose") or ""
                faixa = faixa_etaria(reg.get("nu_idade_paciente") or "")
                sexo = reg.get("tp_sexo_paciente") or ""
                if not municipio:
                    nulos["municipio"] += 1
                if not imuno:
                    nulos["imunobiologico"] += 1
                documentos.append(hash(reg.get("co_documento") or ""))
                municipal[(municipio, imuno, dose, faixa, sexo)] += 1
                equidade[(reg.get("sg_uf_paciente") or "", imuno, dose, faixa, sexo,
                          reg.get("co_raca_cor_paciente") or "")] += 1
                fluxo[(municipio, reg.get("co_municipio_estabelecimento") or "")] += 1
                if linhas % 4_000_000 == 0:
                    log("  %s %dM linhas (%.0fk/s)"
                        % (ref, linhas / 1e6, linhas / (time.time() - t0) / 1000))
    minutos_parse = (time.time() - t0) / 60

    def gravar(contador: Counter, colunas: list[str], nome_arquivo: str) -> int:
        df = pd.DataFrame([(*k, v) for k, v in contador.items()],
                          columns=[*colunas, "doses"])
        df.insert(0, "competencia", ref)
        # Contagem de linhas não detecta corrupção, mas a soma detecta perda:
        # se o agregado não fecha com as linhas lidas, algo se perdeu no meio.
        if int(df.doses.sum()) != linhas:
            raise FalhaDeColeta(f"{ref}/{nome_arquivo}: agregado não fecha com as linhas lidas")
        df.to_parquet(SAIDA / (f"{nome_arquivo}_{ref}.parquet"), index=False)
        return len(df)

    n_municipal = gravar(
        municipal, ["municipio_cod", "imunobiologico", "tipo_dose", "faixa_etaria", "sexo"],
        "municipal")
    n_equidade = gravar(
        equidade,
        ["uf_sigla", "imunobiologico", "tipo_dose", "faixa_etaria", "sexo", "raca_cor"],
        "equidade")
    n_fluxo = gravar(fluxo, ["municipio_pac", "municipio_estab"], "fluxo")

    # Hash de co_documento por mês: guarda de duplicata ENTRE competências, que
    # só existe com a série na mão. Reescrita de arquivo publicado é onde
    # duplicata entre meses nasce.
    np.save(SAIDA / (f"docs_{ref}.npy"), np.frombuffer(documentos, dtype=np.int64))

    meta = {
        "competencia": ref,
        "bytes_origem": esperado,
        "gb_csv": round(gb_csv, 2),
        "last_modified": cab.headers.get("Last-Modified"),
        "linhas": linhas,
        "docs_distintos": int(len(np.unique(np.frombuffer(documentos, dtype=np.int64)))),
        "fora_da_competencia": linhas - por_competencia.get(ref, 0),
        "nulos": dict(nulos),
        "linhas_municipal": n_municipal,
        "linhas_equidade": n_equidade,
        "linhas_fluxo": n_fluxo,
        "minutos": round(minutos_download + minutos_parse, 1),
    }
    destino_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    zipf.unlink()      # pico de disco = um mês, não a soma dos meses
    log("%s: %d linhas | municipal %d, equidade %d, fluxo %d | %.1f min"
        % (ref, linhas, n_municipal, n_equidade, n_fluxo, meta["minutos"]))
    return meta


def conferir_ano(ano: int, metas: list[dict]) -> None:
    """Guardas que só existem com a série do ano completa."""
    fora = sum(m["fora_da_competencia"] for m in metas)
    dentro = sum(m["linhas"] - m["docs_distintos"] for m in metas)
    if fora:
        raise FalhaDeColeta("%d: %d registros fora da própria competência" % (ano, fora))
    if dentro:
        raise FalhaDeColeta("%d: %d documentos duplicados dentro de um mês" % (ano, dentro))

    por_mes = {p.stem.replace("docs_", ""): np.load(p)
               for p in sorted(SAIDA.glob("docs_%d-*.npy" % ano))}
    chaves = sorted(por_mes)
    for i, a in enumerate(chaves):
        for b in chaves[i + 1:]:
            n = int(np.intersect1d(por_mes[a], por_mes[b]).size)
            if n:
                raise FalhaDeColeta("%s e %s compartilham %d documentos" % (a, b, n))
    log("%d: %d meses, %d doses, sem duplicata dentro nem entre competências"
        % (ano, len(metas), sum(m["linhas"] for m in metas)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anos", type=int, nargs="+", required=True)
    args = ap.parse_args()

    falhou = []
    for ano in args.anos:
        log("=" * 50)
        log("ano %d" % ano)
        metas = []
        try:
            for sigla, mm in MESES:
                try:
                    m = processar_mes(ano, sigla, mm)
                except ArquivoAusente:
                    continue        # mês não publicado; o ano segue
                if m:
                    metas.append(m)
            if metas:
                conferir_ano(ano, metas)
        except Exception:
            # Um ano que falha não leva os outros junto, mas o processo termina
            # com código != 0 para o CI não achar que passou.
            log("ano %d FALHOU" % ano)
            traceback.print_exc()
            falhou.append(ano)

    if falhou:
        raise SystemExit(f"anos com falha: {falhou}")
    log("concluído")


if __name__ == "__main__":
    main()
