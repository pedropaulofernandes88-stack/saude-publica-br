"""
observar_fontes.py — quando o DataSUS mexe no arquivo, sem baixar o arquivo.

O projeto media desfecho e nunca mediu a PRÓPRIA FONTE. Um arquivo publicado
pode ser reescrito anos depois, e não há aviso: quem citou o número de ontem não
tem como saber que ele mudou.

A primeira tentativa (hoje em migrations/archive/backfill_snapshot.py) quis
reconstruir isso do histórico
do site e falhou — o site não reingere, então nunca observou revisão. A saída é
observar a fonte diretamente. E não precisa baixar nada:

    * S3 (SIM)  → HEAD devolve Content-Length, Last-Modified e ETag
    * FTP       → LIST devolve nome, tamanho e data de todo o diretório
                  em UMA viagem

Custo de uma rodada completa: alguns segundos e alguns KB. Dá para rodar toda
semana sem pensar em cota.

POR QUE ISSO IMPORTA — medido em 2026-08-18, na primeira execução:
    DENGBR07.dbc, DENGBR08.dbc e DENGBR09.dbc (dengue de 2007, 2008 e 2009)
    foram modificados em 12/08/2026. Dado de dezenove anos atrás, reescrito seis
    dias atrás. DENGBR10 em 04/08 e DENGBR11/12 em 29/07.
    O CSV nacional do SIM, no mesmo dia, estava intacto desde abril de 2025.
    Revisão retroativa existe, é frequente, e não acontece onde se esperaria.

COMO NÃO LER ESTES NÚMEROS
    * mudança de arquivo NÃO é mudança de indicador. O arquivo pode ser
      reescrito com conteúdo equivalente. Só a reingestão diz o que mudou de
      fato — esta ferramenta diz QUANDO vale a pena reingerir;
    * `modificado_em` vem do servidor. O FTP do DataSUS entrega data local sem
      fuso declarado, com granularidade de minuto; o S3 entrega UTC exato. Não
      compare os dois no fio do relógio;
    * tamanho igual não garante conteúdo igual, e tamanho diferente não diz de
      quanto foi a revisão. É gatilho, não medida;
    * ausência (HTTP 403, arquivo fora da listagem) é informação e fica
      registrada como `disponivel: false`. SIM 2025 e 2026 não existem — isso
      não é erro da coleta.

Uso:
    .venv311/Scripts/python scripts/observar_fontes.py
    .venv311/Scripts/python scripts/observar_fontes.py --comparar
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from ftplib import FTP
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "data" / "observacoes"

S3_SIM = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM"
FTP_HOST = "ftp.datasus.gov.br"

# Diretórios do FTP e o recorte de cada um. O SIH tem ~5.400 arquivos (27 UF ×
# ~200 competências desde 2008): o filtro mantém a observação no periodo que o
# projeto publica, senão o arquivo diario vira ruido.
DIRETORIOS_FTP = [
    ("SINAN", "/dissemin/publicos/SINAN/DADOS/FINAIS", r"^DENGBR\d{2}\.dbc$"),
    ("SINAN", "/dissemin/publicos/SINAN/DADOS/PRELIM", r"^DENGBR\d{2}\.dbc$"),
    # Sífilis: SÓ existe em PRELIM (não há SIF* em FINAIS, nem para 2007), e é
    # a fonte mais defasada que o projeto publica — os arquivos de 2025 foram
    # reescritos em 30/06/2026 e ainda param em junho de 2025. Justamente por
    # isso precisa ser observada: o dia em que sair um SIFxBR26 é o dia de
    # reingerir, e ninguém teria como saber sem isto.
    ("SINAN", "/dissemin/publicos/SINAN/DADOS/PRELIM", r"^SIF[ACG]BR\d{2}\.dbc$"),
    # SIM pelo FTP, que é de onde o projeto REALMENTE lê. A observação por S3
    # (abaixo) devolve 403 em todos os anos desde que existe: estava vigiando
    # uma porta fechada e chamando isso de cobertura. O 403 continua registrado
    # — se um dia virar 200, é mudança —, mas quem responde "o SIM mexeu?" é
    # esta linha. Era o maior ponto cego do projeto: a fonte de mais peso,
    # observada por uma rota morta.
    ("SIM", "/dissemin/publicos/SIM/CID10/DORES", r"^DO[A-Z]{2}20(1[89]|2\d)\.dbc$"),
    ("SIH", "/dissemin/publicos/SIHSUS/200801_/Dados", r"^RD[A-Z]{2}(2[2-9])\d{2}\.dbc$"),
    ("SINASC", "/dissemin/publicos/SINASC/NOV/DNRES", r"^DN[A-Z]{2}20(1[89]|2\d)\.dbc$"),
    ("ONCOLOGIA", "/dissemin/publicos/painel_oncologia/Dados", r"^POBR\d{4}\.dbc$"),
    # CNES grupo LT: o pipeline ingere só a competência de DEZEMBRO de cada ano
    # (LT{UF}{AA}12). Observar as outras onze competências seria vigiar arquivo
    # que o projeto não usa — ruído que treina a gente a ignorar a issue.
    ("CNES", "/dissemin/publicos/CNES/200508_/Dados/LT", r"^LT[A-Z]{2}(1[5-9]|2\d)12\.dbc$"),
]

ANOS_SIM = range(2022, date.today().year + 1)

# PNI/RNDS não vive no FTP: são zips mensais no mesmo bucket do SIM.
S3_PNI = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/PNI/csv"
MESES_PNI = ["jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez"]
ANOS_PNI = range(2023, date.today().year + 1)

#: Fonte publicada (id em `site/lib/fontes.ts`) → rótulo `base` da observação.
#:
#: Esta tabela existe porque a cobertura envelheceu em silêncio duas vezes: o
#: Painel Oncologia e a sífilis entraram no site sem entrar aqui, e o SIM era
#: "observado" por uma URL que devolve 403 desde sempre. Uma fonte não observada
#: não dá erro — ela só deixa de avisar, que é o mesmo que não existir.
OBSERVADAS: dict[str, str] = {
    "sim": "SIM", "sih": "SIH", "sinan": "SINAN", "sifilis": "SINAN",
    "sinasc": "SINASC", "pni": "PNI", "oncologia": "ONCOLOGIA", "cnes": "CNES",
}

#: Fonte publicada que NÃO é observada, com o motivo. Estar aqui é uma decisão;
#: não estar em lugar nenhum é esquecimento — e é isso que o teste separa.
NAO_OBSERVADAS: dict[str, str] = {
    "aps": "e-Gestor/SISAB serve painel, não arquivo com tamanho e data estáveis",
    "siops": "SIOPS publica por consulta interativa, sem diretório versionado",
    "ans": "ANS tem calendário próprio de divulgação, fora do DataSUS",
    "ibge": "população censitária/projeções não são revisadas de surpresa",
    "derivado": "não é coleta: sai dos marts acima e muda quando eles mudam",
}


def _data_ftp(pedaco: str) -> str | None:
    """'08-11-26 11:05AM' -> '2026-08-11'. O FTP do DataSUS usa MM-DD-YY."""
    m = re.match(r"(\d{2})-(\d{2})-(\d{2})", pedaco)
    if not m:
        return None
    mes, dia, ano = m.groups()
    return f"20{ano}-{mes}-{dia}"


def _head_s3(base: str, nome: str, url: str, ano_ref: int) -> dict | None:
    """Um HEAD no bucket do ckan → registro de observação, ou None se a rede caiu.

    Ausência (404) NÃO é None: vira `disponivel: false` e fica registrada. Mês
    que ainda não saiu é informação — é o registro dele que permite ver, na
    semana seguinte, que ele saiu.
    """
    try:
        r = requests.head(url, allow_redirects=True, timeout=30)
    except requests.RequestException as e:
        print(f"  ! {nome}: {type(e).__name__}", flush=True)
        return None
    ok = r.status_code == 200
    iso = None
    if (mod := r.headers.get("Last-Modified")):
        try:
            iso = datetime.strptime(mod, "%a, %d %b %Y %H:%M:%S %Z") \
                    .replace(tzinfo=timezone.utc).date().isoformat()
        except ValueError:
            iso = None
    return {
        "base": base, "arquivo": nome, "fonte": "s3", "ano_ref": ano_ref,
        "disponivel": ok, "http": r.status_code,
        "bytes": int(r.headers["Content-Length"]) if ok and "Content-Length" in r.headers else None,
        "modificado_em": iso,
        "etag": (r.headers.get("ETag") or "").strip('"') or None,
    }


def observar_sim() -> list[dict]:
    fora = []
    for ano in ANOS_SIM:
        nome = f"DO{str(ano)[2:]}OPEN.csv"
        if (r := _head_s3("SIM", nome, f"{S3_SIM}/{nome}", ano)):
            fora.append(r)
    return fora


def observar_pni() -> list[dict]:
    """Os zips mensais do PNI/RNDS. O S3 reescreve mês já publicado.

    Medido pelo próprio pipeline: maio/2025 foi regravado em 28/08/2026. Sem
    observar, o mart de imunização fica com o retrato antigo para sempre.
    """
    fora = []
    for ano in ANOS_PNI:
        for mes in MESES_PNI:
            nome = f"vacinacao_{mes}_{ano}_csv.zip"
            if (r := _head_s3("PNI", nome, f"{S3_PNI}/{nome}", ano)):
                fora.append(r)
    return fora


def observar_ftp() -> list[dict]:
    fora: list[dict] = []
    ftp = FTP(FTP_HOST, timeout=120)
    ftp.login()
    try:
        for base, diretorio, padrao in DIRETORIOS_FTP:
            reg = re.compile(padrao, re.I)
            linhas: list[str] = []
            try:
                ftp.cwd(diretorio)
                ftp.dir(linhas.append)
            except Exception as e:  # noqa: BLE001 — diretorio some, renomeia, some de novo
                print(f"  ! {diretorio}: {type(e).__name__}: {e}", flush=True)
                continue

            achados = 0
            for linha in linhas:
                partes = linha.split()
                if len(partes) < 4:
                    continue
                nome = partes[-1]
                if not reg.match(nome):
                    continue
                achados += 1
                fora.append({
                    "base": base, "arquivo": nome, "fonte": f"ftp:{diretorio}",
                    "ano_ref": None, "disponivel": True, "http": None,
                    "bytes": int(partes[-2]) if partes[-2].isdigit() else None,
                    "modificado_em": _data_ftp(partes[0]),
                    "etag": None,
                })
            print(f"  {base} {diretorio.split('/')[-1]}: {achados} arquivos", flush=True)
    finally:
        try:
            ftp.quit()
        except Exception:  # noqa: BLE001 — servidor derruba a conexao sozinho as vezes
            ftp.close()
    return fora


def anterior() -> tuple[Path | None, list[dict]]:
    arquivos = sorted(DESTINO.glob("*.json"))
    if not arquivos:
        return None, []
    p = arquivos[-1]
    return p, json.loads(p.read_text(encoding="utf-8")).get("arquivos", [])


def comparar(antes: list[dict], agora: list[dict]) -> list[dict]:
    """Mudou tamanho, data ou disponibilidade? Arquivo novo tambem conta."""
    idx = {(r["base"], r["arquivo"], r["fonte"]): r for r in antes}
    mudancas = []
    for r in agora:
        a = idx.get((r["base"], r["arquivo"], r["fonte"]))
        if a is None:
            mudancas.append({**r, "mudanca": "novo"})
            continue
        campos = [c for c in ("bytes", "modificado_em", "etag", "disponivel")
                  if a.get(c) != r.get(c)]
        if campos:
            mudancas.append({**r, "mudanca": "+".join(campos),
                             "antes": {c: a.get(c) for c in campos}})
    vistos = {(r["base"], r["arquivo"], r["fonte"]) for r in agora}
    for a in antes:
        if (a["base"], a["arquivo"], a["fonte"]) not in vistos:
            mudancas.append({**a, "mudanca": "sumiu"})
    return mudancas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--comparar", action="store_true",
                    help="so compara com a ultima observacao, sem gravar")
    args = ap.parse_args()

    hoje = date.today().isoformat()
    print(f"observando as fontes em {hoje}\n\nSIM (S3, HEAD):", flush=True)
    arquivos = observar_sim()
    for r in arquivos:
        estado = f"{r['bytes'] / 1024 / 1024:.0f} MB, modificado {r['modificado_em']}" \
                 if r["disponivel"] else f"indisponivel (HTTP {r['http']})"
        print(f"  {r['arquivo']:<16} {estado}", flush=True)

    print("\nPNI (S3, HEAD):", flush=True)
    pni = observar_pni()
    publicados = [r for r in pni if r["disponivel"]]
    print(f"  {len(publicados)} de {len(pni)} meses publicados; "
          f"mais recente: {max((r['arquivo'] for r in publicados), default='—')}", flush=True)
    arquivos += pni

    print("\nFTP (LIST):", flush=True)
    arquivos += observar_ftp()

    p_ant, antes = anterior()
    mudancas = comparar(antes, arquivos) if antes else []

    print(f"\n{len(arquivos)} arquivos observados")
    if p_ant:
        print(f"comparando com {p_ant.name}: {len(mudancas)} mudancas")
        for m in sorted(mudancas, key=lambda r: (r["base"], r["arquivo"]))[:25]:
            print(f"  [{m['mudanca']:<22}] {m['base']:<7} {m['arquivo']:<16} "
                  f"modificado {m.get('modificado_em')}")
    else:
        print("primeira observacao — nao ha com o que comparar (linha de base)")

    if args.comparar:
        return

    DESTINO.mkdir(parents=True, exist_ok=True)
    saida = DESTINO / f"{hoje}.json"
    saida.write_text(_serializar(hoje, arquivos, mudancas, p_ant), encoding="utf-8")
    print(f"\ngravado: {saida.relative_to(ROOT)}")


def _serializar(hoje: str, arquivos: list[dict], mudancas: list[dict],
                p_ant: Path | None) -> str:
    """JSON válido com UM REGISTRO POR LINHA.

    `json.dumps(indent=...)` quebraria cada campo em sua própria linha e o diff
    semanal — que é o produto desta ferramenta — viraria centenas de linhas de
    ruído. Com um registro por linha, `git diff` mostra exatamente os arquivos
    que o DataSUS mexeu, e nada mais.
    """
    def linhas(registros: list[dict]) -> str:
        if not registros:
            return "[]"
        corpo = ",\n  ".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                             for r in registros)
        return "[\n  " + corpo + "\n ]"

    cabecalho = {
        "observado_em": hoje,
        "n_arquivos": len(arquivos),
        "n_mudancas": len(mudancas) if p_ant else None,
        "comparado_com": p_ant.name if p_ant else None,
    }
    partes = [f' {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}'
              for k, v in cabecalho.items()]
    partes.append(f' "mudancas": {linhas(sorted(mudancas, key=_ordem))}')
    partes.append(f' "arquivos": {linhas(sorted(arquivos, key=_ordem))}')
    return "{\n" + ",\n".join(partes) + "\n}\n"


def _ordem(r: dict) -> tuple:
    return (r.get("base") or "", r.get("fonte") or "", r.get("arquivo") or "")


if __name__ == "__main__":
    main()
