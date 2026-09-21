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

from _fontes import HOST_FTP, S3_CKAN, diretorios_ftp
from sondar_rhc import anos_ofertados as anos_ofertados_rhc
from _fontes import nao_observadas as _nao_observadas
from _fontes import observadas as _observadas

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "data" / "observacoes"

#: Os caminhos NÃO são digitados aqui. Eles vêm de `_fontes.py`, que é a mesma
#: declaração que os pipelines leem — foi a divergência entre as duas cópias que
#: deixou `SIM/PRELIM/DORES` fora da vigilância enquanto o `pipeline_v2.py` lia
#: dele. Para incluir ou recortar um diretório, edite o registro.
FTP_HOST = HOST_FTP
S3_SIM = f"{S3_CKAN}/SIM"
S3_PNI = f"{S3_CKAN}/PNI/csv"

#: (base, diretório, padrão do nome do arquivo) — uma tripla por LOCAL.
DIRETORIOS_FTP = diretorios_ftp()

ANOS_SIM = range(2022, date.today().year + 1)

MESES_PNI = ["jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez"]
ANOS_PNI = range(2023, date.today().year + 1)

#: Fonte publicada (id em `site/lib/fontes.ts`) → rótulo `base` da observação.
#:
#: Derivado: uma fonte é observada quando declara ao menos um local observável.
#: Antes eram dois dicionários escritos à mão, e a cobertura envelheceu em
#: silêncio duas vezes — o Painel Oncologia e a sífilis entraram no site sem
#: entrar aqui, e o SIM era "observado" por uma URL que devolve 403 desde
#: sempre. Uma fonte não observada não dá erro: ela só deixa de avisar.
OBSERVADAS: dict[str, str] = _observadas()

#: Fonte publicada que NÃO é observada, com o motivo. Estar aqui é uma decisão;
#: não estar em lugar nenhum é esquecimento — e é isso que o teste separa.
NAO_OBSERVADAS: dict[str, str] = _nao_observadas()


def _data_ftp(pedaco: str) -> str | None:
    """'08-11-26 11:05AM' -> '2026-08-11'. O FTP do DataSUS usa MM-DD-YY."""
    m = re.match(r"(\d{2})-(\d{2})-(\d{2})", pedaco)
    if not m:
        return None
    mes, dia, ano = m.groups()
    return f"20{ano}-{mes}-{dia}"


MESES_UNIX = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def parse_linha_ftp(linha: str, hoje: date | None = None) -> tuple[str, int | None, str | None] | None:
    """Uma linha de `LIST` → (nome, bytes, data ISO), nos dois dialetos.

    O DataSUS responde no estilo MS-DOS (`08-11-26  11:05AM  1234  ARQ.dbc`) e
    a ANS no estilo Unix (`-rw-r--r-- 1 u g 1234 Jul 05 2024 arq.zip`). O
    observador só conhecia o primeiro, e aplicá-lo ao segundo não levanta erro:
    lê a permissão como data (devolve None) e o ANO como tamanho. O registro
    fica com `bytes=2024` e `modificado_em=None`, o que é pior que não observar,
    porque parece observação.

    No estilo Unix o ano só aparece quando o arquivo tem mais de seis meses; nos
    recentes vem a hora no lugar. Aí o ano é inferido — e se a data inferida
    cair no futuro, ela é do ano passado.
    """
    partes = linha.split()
    if len(partes) < 4:
        return None

    if re.match(r"^\d{2}-\d{2}-\d{2}$", partes[0]):          # MS-DOS
        nome = partes[-1]
        tam = int(partes[-2]) if partes[-2].isdigit() else None
        return nome, tam, _data_ftp(partes[0])

    if partes[0][0] in "-dl" and len(partes) >= 9:            # Unix
        mes, dia, ultimo = partes[5], partes[6], partes[7]
        nome = " ".join(partes[8:])
        tam = int(partes[4]) if partes[4].isdigit() else None
        m = MESES_UNIX.get(mes)
        if not m or not dia.isdigit():
            return nome, tam, None
        if ultimo.isdigit() and len(ultimo) == 4:
            ano = int(ultimo)
        else:
            hoje = hoje or date.today()
            ano = hoje.year
            if date(ano, m, int(dia)) > hoje:
                ano -= 1
        return nome, tam, f"{ano:04d}-{m:02d}-{int(dia):02d}"

    return None


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


def _varrer_host(host: str, alvos: list[tuple[str, str, str]]) -> list[dict]:
    """Uma conexão, todos os diretórios daquele host."""
    fora: list[dict] = []
    ftp = FTP(host, timeout=120)
    ftp.login()
    try:
        for base, diretorio, padrao in alvos:
            reg = re.compile(padrao, re.I)
            linhas: list[str] = []
            try:
                ftp.cwd(diretorio)
                ftp.dir(linhas.append)
            except Exception as e:  # noqa: BLE001 — diretorio some, renomeia, some de novo
                print(f"  ! {host}{diretorio}: {type(e).__name__}: {e}", flush=True)
                continue

            achados = 0
            for linha in linhas:
                lido = parse_linha_ftp(linha)
                if not lido:
                    continue
                nome, tam, quando = lido
                if not reg.match(nome):
                    continue
                achados += 1
                fora.append({
                    "base": base, "arquivo": nome, "fonte": f"ftp:{diretorio}",
                    "ano_ref": None, "disponivel": True, "http": None,
                    "bytes": tam,
                    "modificado_em": quando,
                    "etag": None,
                })
            print(f"  {base} {diretorio.split('/')[-1]}: {achados} arquivos", flush=True)
    finally:
        try:
            ftp.quit()
        except Exception:  # noqa: BLE001 — servidor derruba a conexao sozinho as vezes
            ftp.close()
    return fora


def observar_ftp() -> list[dict]:
    """Varre os diretórios FTP do registro, agrupados por HOST.

    Até 2026-09-21 esta função abria uma conexão com `FTP_HOST` e percorria
    todos os diretórios nela. Isso não era uma simplificação: era o que impedia
    vigiar qualquer fonte fora do DataSUS, e a ANS ficou seis meses sem
    observação com uma dispensa escrita que descrevia o calendário dela em vez
    de explicar o impedimento. Uma fonte não observada não dá erro — ela só
    deixa de avisar.
    """
    por_host: dict[str, list[tuple[str, str, str]]] = {}
    for base, host, diretorio, padrao in DIRETORIOS_FTP:
        por_host.setdefault(host, []).append((base, diretorio, padrao))

    fora: list[dict] = []
    for host, alvos in sorted(por_host.items()):
        print(f"  [{host}] {len(alvos)} diretório(s)", flush=True)
        try:
            fora.extend(_varrer_host(host, alvos))
        except Exception as e:  # noqa: BLE001 — host fora do ar nao pode derrubar os outros
            print(f"  ! {host} inteiro: {type(e).__name__}: {e}", flush=True)
    return fora


def observar_rhc() -> list[dict]:
    """Os anos que o IntegradorRHC oferece hoje, lidos da página de download.

    Terceiro tipo de leitor, depois de FTP e S3, e ele existe por coerência: a
    regra que este projeto acabou de escrever é que dispensa precisa dizer o
    IMPEDIMENTO, e "o observador só sabe ler FTP" é impedimento do observador,
    não da fonte. O RHC publica uma lista de anos em HTML; lista é listagem, e
    ano novo aparecendo é exatamente o sinal que interessa.

    Não há tamanho nem data: o site não os expõe na listagem. `bytes=None` é
    honesto — o comparador então só detecta entrada nova ou entrada que sumiu,
    que é tudo o que esta fonte permite saber sem baixar 21 MB por ano.
    """
    try:
        anos = anos_ofertados_rhc()
    except Exception as e:  # noqa: BLE001 — fonte fora do ar nao derruba a rodada
        print(f"  ! RHC: {type(e).__name__}: {e}", flush=True)
        return []
    print(f"  RHC: {len(anos)} anos ofertados "
          f"({min(anos, default='—')}–{max(anos, default='—')})", flush=True)
    return [{
        "base": "RHC", "arquivo": str(a), "fonte": "http:irhc.inca.gov.br",
        "ano_ref": a, "disponivel": True, "http": 200,
        "bytes": None, "modificado_em": None, "etag": None,
    } for a in anos]


#: Observadores que NÃO saem do registro de diretórios FTP, por base.
#:
#: Existe como mapa, e não como lista escrita à mão em três lugares, porque a
#: guarda `test_base_declarada_existe_de_fato_na_configuracao` precisa saber
#: quais bases este arquivo realmente produz. Antes ela lia um conjunto
#: `{"SIM", "PNI"}` digitado no teste — o que significa que registrar uma fonte
#: nova como observada e esquecer de chamá-la passaria despercebido, que é
#: exatamente o defeito que a guarda existe para pegar. Foi o que aconteceu com
#: o RHC dois minutos depois de ele ser registrado, e a guarda pegou.
OBSERVADORES_EXTRAS: dict[str, str] = {
    "SIM": "observar_sim",
    "PNI": "observar_pni",
    "RHC": "observar_rhc",
}


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

    print("\nRHC (INCA, listagem HTML):", flush=True)
    arquivos += observar_rhc()

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
