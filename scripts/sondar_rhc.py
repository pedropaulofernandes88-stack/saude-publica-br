"""
sondar_rhc.py — o Registro Hospitalar de Câncer tem microdado público, e tem
armadilha
==============================================================================

    python scripts/sondar_rhc.py            # portão: confere o que a coleta assume
    python scripts/sondar_rhc.py --baixar 2019

POR QUE ESTA FONTE
------------------
Medido em 2026-09-21, ao fechar o achado do prazo da Lei dos 60 Dias: **toda a
literatura brasileira sobre tempo até o tratamento oncológico usa duas fontes
por PESSOA** — o PAINEL-Oncologia e o IntegradorRHC — e o projeto não tinha
nenhuma das duas por pessoa. A APAC do SIA/SUS conta autorização, e a ligação
por `AP_CNSPCN` resolve a contagem sem resolver o resto: ela não traz
escolaridade, raça/cor, estadiamento clínico confirmado por laudo, nem "primeiro
tratamento de QUALQUER modalidade", que é o que a Lei 12.732/2012 conta.

O RHC traz os quatro. É a fonte contra a qual a literatura se mede, e com ela a
comparação entre sistemas deixa de depender do recorte que cada autor publicou.

O QUE A SONDAGEM MEDIU (2019, base nacional, 2026-09-21)
--------------------------------------------------------
    518.186 registros | 383.940 analíticos | 46 campos | 21,4 MB zipado
    anos ofertados: 1985 a 2023, sem 1987

QUATRO ARMADILHAS, TODAS MEDIDAS E NENHUMA ÓBVIA
------------------------------------------------
1. **`ESTADIAM` = 88 ou 99 NÃO é estádio.** Os dois ficam fora do
   `r_estadiam.cnv`, que só conhece 0, 1..4 com sufixos, A/B/C/D. Somados como
   estádio produzem uma distribuição inventada. São **53,1% dos registros**
   (51,2% entre os analíticos) — na mesma ordem dos 51% de ausência que este
   projeto já mediu no Painel de Oncologia, e quatro vezes os 12,3% da APAC.
   Ausência tem rótulo próprio, sempre. Ver `_estadio` em
   `pipeline_siasus_oncologia.py`, onde devolver "0" para vazio custou uma
   coleta inteira.

2. **O ano do arquivo é o da PRIMEIRA CONSULTA, não o do diagnóstico.**
   `ANOPRIDI` diverge do ano do arquivo em **21,7%** dos registros de 2019 — e
   `9999` (sem informação) aparece 15.230 vezes. Somar "casos por ano" pelo
   nome do arquivo responde outra pergunta. É a mesma armadilha do SINAN, já
   documentada.

3. **Caso não analítico é outro universo.** `TPCASO = 2` são 134.246 dos
   518.186 (25,9%): pacientes que chegaram com diagnóstico E tratamento feitos
   fora. Misturá-los com os analíticos mede a rede, não o hospital — e é
   exatamente a exclusão que Jomar et al. 2023 fazem (3.978 casos).

4. **A data vem em `DD/MM/YYYY`.** Todo o resto do DataSUS neste projeto usa
   `YYYYMMDD`. Reaproveitar o leitor de datas do SIA aqui não quebra: devolve
   silenciosamente lixo ou `NaT`.

E uma quinta, que não é do dado: **o download é assíncrono**. Um POST pede a
geração e devolve `{'status':'1'}`; o arquivo só existe depois de o servidor
dizer `'2'`. Um coletor ingênuo grava a resposta de status como se fosse ZIP —
14 bytes de JSON com extensão `.zip`, e nenhum erro.

O QUE ESTA SONDAGEM NÃO DECIDE
------------------------------
Se a fonte entra como 16ª do projeto. Isso é decisão editorial e depende de
haver pergunta que só ela responde — hoje há uma, registrada em
`rascunhos/prazo-60-dias-artefato/`: a diferença de 30 pontos entre RHC, APAC
ligada e Painel para o mesmo indicador legal.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
import time
import zipfile
from pathlib import Path

import requests

BASE = "https://irhc.inca.gov.br/RHCNet"
#: A página só lista os anos quando recebe o escopo. `local=todosho` é a base
#: nacional de todos os estados — o valor sai do `envia()` da própria página.
PREPARA = f"{BASE}/selecionaDownloadTabWin.action?initial=1&local=todosho&unidFed="
DOWNLOAD = f"{BASE}/downloadTabWin!bases.action"
UA = "saude-publica-br/sondagem (+https://github.com/saude-publica-br)"

STATUS_GERANDO, STATUS_PRONTO = "1", "2"

#: Anos que a sondagem de 2026-09-21 encontrou. 1987 não existe, e não é falha.
ANOS_CONHECIDOS = tuple(a for a in range(1985, 2024) if a != 1987)

#: Códigos que `r_estadiam.cnv` conhece. Tudo FORA disto é ausência com rótulo
#: próprio — nunca um estádio.
ESTADIOS_VALIDOS = frozenset({
    "0", "00", "01", "02", "03", "04",
    "1", "1A", "1B", "1C", "2", "2A", "2B", "2C",
    "3", "3A", "3B", "3C", "4", "4A", "4B", "4C",
    "A", "A1", "A2", "B", "B1", "B2", "C", "C0", "C1", "C2", "D1", "D2",
})

#: Campos que qualquer uso desta fonte precisa. Se o INCA mudar o layout, o
#: portão avisa aqui em vez de o pipeline produzir coluna vazia.
CAMPOS_ESSENCIAIS = frozenset({
    "TPCASO",      # 1 analítico, 2 não analítico — universos diferentes
    "LOCTUDET",    # CID-O topografia detalhada
    "ESTADIAM",    # estadiamento clínico (ver ESTADIOS_VALIDOS)
    "DTDIAGNO",    # data do diagnóstico — DD/MM/YYYY
    "DATAINITRT",  # data do início do 1º tratamento — DD/MM/YYYY
    "PRITRATH",    # 1º tratamento no hospital, QUALQUER modalidade
    "DIAGANT",     # diagnóstico/tratamento anteriores (1,2,3,4,9)
    "ANOPRIDI",    # ano do 1º diagnóstico — NÃO é o ano do arquivo
    "INSTRUC",     # escolaridade — não existe na APAC
    "RACACOR",
    "UFUH",        # UF da unidade hospitalar
    "ESTADRES",    # UF de residência
})

DATA_BR = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


# ---------------------------------------------------------------------------
# Leitura do DBF — puro, e é o que o portão exercita
# ---------------------------------------------------------------------------

def campos_do_dbf(cabecalho: bytes) -> list[tuple[str, int, int]]:
    """(nome, deslocamento, largura) de cada campo, a partir do cabeçalho dBase.

    O deslocamento começa em 1 porque o primeiro byte de cada registro é a
    marca de exclusão. Errar isso desloca TODAS as colunas por um caractere, o
    que não levanta exceção nenhuma: produz dado plausível e errado.
    """
    campos, off = [], 1
    corpo = cabecalho[32:]
    for i in range(0, len(corpo) - 1, 32):
        b = corpo[i:i + 32]
        if len(b) < 32 or b[0] == 0x0D:
            break
        nome = b[:11].split(b"\x00")[0].decode("latin-1")
        campos.append((nome, off, b[16]))
        off += b[16]
    return campos


def metadados_do_dbf(cabecalho32: bytes) -> tuple[int, int, int]:
    """(registros, tamanho do cabeçalho, largura do registro)."""
    return (struct.unpack("<I", cabecalho32[4:8])[0],
            struct.unpack("<H", cabecalho32[8:10])[0],
            struct.unpack("<H", cabecalho32[10:12])[0])


def data_br(valor: str) -> str | None:
    """`DD/MM/YYYY` → `YYYY-MM-DD`, ou None quando não é data.

    Existe para que ninguém reaproveite o leitor `YYYYMMDD` do resto do projeto
    aqui. O RHC é a única fonte deste repositório que usa o formato brasileiro.
    """
    m = DATA_BR.match((valor or "").strip())
    if not m:
        return None
    dia, mes, ano = m.groups()
    if not (1 <= int(mes) <= 12 and 1 <= int(dia) <= 31 and 1900 <= int(ano) <= 2100):
        return None
    return f"{ano}-{mes}-{dia}"


def estadio(valor: str) -> str:
    """Estádio com rótulo próprio para ausência. 88 e 99 NÃO são estádios.

    Mesma regra de `_estadio` no pipeline da APAC, e pela mesma razão: lá,
    devolver "0" para o campo vazio publicou ausência como diagnóstico precoce
    e custou uma coleta de três horas.
    """
    v = (valor or "").strip().upper()
    return v if v in ESTADIOS_VALIDOS else "ignorado"


# ---------------------------------------------------------------------------
# Rede
# ---------------------------------------------------------------------------

def anos_ofertados(sessao: requests.Session | None = None) -> list[int]:
    """Anos que o site oferece hoje, lidos da própria página de download."""
    s = sessao or requests.Session()
    s.headers.setdefault("User-Agent", UA)
    html = s.get(PREPARA, timeout=60).text
    return sorted({int(a) for a in
                   re.findall(r'name="anosSelecionados"[^>]*value="(\d{4})"', html)})


def baixar_ano(ano: int, destino: Path,
               sessao: requests.Session | None = None) -> Path:
    """Baixa um ano da base nacional. Respeita o protocolo assíncrono do site.

    Um POST pede a geração e devolve status; só depois de `'2'` a MESMA url
    entrega os bytes. Gravar a resposta do POST produz um `.zip` de 14 bytes
    que é JSON, e nenhuma etapa reclama.
    """
    s = sessao or requests.Session()
    s.headers.setdefault("User-Agent", UA)
    s.get(PREPARA, timeout=60).raise_for_status()

    form = {
        "local": "todosho", "unidFed": "", "anoPrimeiraConsulta": "",
        "arquivoDef": "true", "arquivoAux": "true",
        "anosSelecionados": str(ano),
        "downloadToken": str(int(time.time() * 1000)),
        "wwajax": "1", "wwresult": "0",
    }
    cab = {"Referer": PREPARA}
    r = s.post(DOWNLOAD, data=form, headers=cab, timeout=120)
    for _ in range(60):
        if f'"status":"{STATUS_PRONTO}"' in r.text.replace("'", '"'):
            break
        if f'"status":"{STATUS_GERANDO}"' not in r.text.replace("'", '"'):
            raise RuntimeError(f"RHC {ano}: resposta inesperada {r.text[:120]!r}")
        time.sleep(3)
        r = s.get(f"{DOWNLOAD}?wwajax=1&wwresult=0", headers=cab, timeout=120)
    else:
        raise RuntimeError(f"RHC {ano}: o servidor nunca disse pronto")

    destino.parent.mkdir(parents=True, exist_ok=True)
    with s.get(DOWNLOAD, headers=cab, stream=True, timeout=900) as f:
        f.raise_for_status()
        with open(destino, "wb") as saida:
            for bloco in f.iter_content(1 << 20):
                saida.write(bloco)

    if not zipfile.is_zipfile(destino):
        cabeca = destino.read_bytes()[:120]
        raise RuntimeError(
            f"RHC {ano}: o download não é ZIP — {cabeca!r}. Quase sempre é a "
            "resposta de status gravada como arquivo: o protocolo é assíncrono.")
    return destino


# ---------------------------------------------------------------------------
# Portão
# ---------------------------------------------------------------------------

def portao(ano: int = 2019) -> int:
    """Confere, contra a rede, o que a coleta assume. 0 aprova, 1 reprova."""
    problemas: list[str] = []
    s = requests.Session()
    s.headers["User-Agent"] = UA

    ofertados = anos_ofertados(s)
    if not ofertados:
        problemas.append("a página não lista ano nenhum — o formulário mudou")
    else:
        sumiram = set(ANOS_CONHECIDOS) - set(ofertados)
        if sumiram:
            problemas.append(f"anos que existiam sumiram: {sorted(sumiram)}")
        print(f"[rhc] anos ofertados: {min(ofertados)}–{max(ofertados)} "
              f"({len(ofertados)} anos)")

    destino = Path(sys.argv[0]).resolve().parent.parent / "data" / "cache" / f"rhc_{ano}.zip"
    if not destino.exists():
        baixar_ano(ano, destino, s)
    z = zipfile.ZipFile(destino)
    dbf = next((n for n in z.namelist() if n.lower().endswith(".dbf")), None)
    if not dbf:
        problemas.append(f"nenhum .dbf no pacote de {ano}: {z.namelist()[:5]}")
    else:
        with z.open(dbf) as f:
            c32 = f.read(32)
            n, ini, larg = metadados_do_dbf(c32)
            campos = campos_do_dbf(c32 + f.read(ini - 32))
            nomes = {nm for nm, _, _ in campos}
            faltam = CAMPOS_ESSENCIAIS - nomes
            if faltam:
                problemas.append(f"campos essenciais ausentes em {ano}: {sorted(faltam)}")
            print(f"[rhc] {dbf}: {n:,} registros, {len(campos)} campos, "
                  f"{larg} bytes por registro")

            sel = {nm: (o, t) for nm, o, t in campos}
            amostra = [f.read(larg) for _ in range(min(n, 20_000))]

        def valores(campo: str) -> list[str]:
            o, t = sel[campo]
            return [r[o:o + t].decode("latin-1").strip() for r in amostra if len(r) == larg]

        if "DTDIAGNO" in sel:
            datas = valores("DTDIAGNO")
            ok = sum(1 for v in datas if data_br(v))
            print(f"[rhc] DTDIAGNO em DD/MM/YYYY: {100 * ok / max(len(datas), 1):.1f}%")
            if ok < 0.9 * len(datas):
                problemas.append(
                    "DTDIAGNO deixou de vir em DD/MM/YYYY — o leitor de datas "
                    "desta fonte é o único do projeto que espera formato BR")

        if "ESTADIAM" in sel:
            est = valores("ESTADIAM")
            ign = sum(1 for v in est if estadio(v) == "ignorado")
            pct = 100 * ign / max(len(est), 1)
            print(f"[rhc] ESTADIAM sem estádio válido (88/99/vazio): {pct:.1f}%")
            if pct == 0:
                problemas.append(
                    "NENHUM registro sem estadiamento — improvável, e é o sinal "
                    "de que 88/99 passaram a ser lidos como estádio")
            if pct > 80:
                problemas.append(f"{pct:.1f}% sem estadiamento: o campo mudou de código")

        if "TPCASO" in sel:
            tp = valores("TPCASO")
            nao = sum(1 for v in tp if v == "2")
            print(f"[rhc] não analíticos: {100 * nao / max(len(tp), 1):.1f}%")
            if nao == 0:
                problemas.append(
                    "nenhum caso não analítico na amostra — ou o pacote mudou, "
                    "ou TPCASO parou de distinguir os dois universos")

    for p in problemas:
        print(f"[rhc] REPROVA: {p}", file=sys.stderr)
    if problemas:
        return 1
    print("[rhc] portão aprovado")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baixar", type=int, metavar="ANO",
                    help="baixa um ano para data/cache/ e sai")
    ap.add_argument("--ano", type=int, default=2019,
                    help="ano usado pelo portão (padrão 2019)")
    a = ap.parse_args()
    if a.baixar:
        raiz = Path(__file__).resolve().parents[1]
        destino = baixar_ano(a.baixar, raiz / "data" / "cache" / f"rhc_{a.baixar}.zip")
        print(f"[rhc] {destino} ({destino.stat().st_size:,} bytes)")
        return 0
    return portao(a.ano)


if __name__ == "__main__":
    sys.exit(main())
