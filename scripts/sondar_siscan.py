"""
sondar_siscan.py — o SISCAN está pronto para ser ingerido, e por qual chave?
============================================================================

    .venv311/Scripts/python scripts/sondar_siscan.py
    .venv311/Scripts/python scripts/sondar_siscan.py --json
    .venv311/Scripts/python scripts/sondar_siscan.py --ano 2023

Sai com código 0 apenas quando toda visão sondada tem município de residência e
um eixo temporal utilizável. Enquanto alguma reprovar, sai com ≠ 0 e diz qual —
é portão de prontidão, não relatório.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O SISCAN entra no roteiro como o elo que falta entre a mortalidade por neoplasia
e a hipótese de detecção: é rastreamento de colo e mama, por município de
residência, desde 2013. Antes de escrever coletor, três coisas precisavam ser
medidas, e nenhuma delas aparece para quem lê a documentação.

**1. O microdado existe no FTP.** Um projeto externo de oncologia bem construído
(rafa-trindade/onco-360-foundation) declara que o SISCAN "não disponibiliza
microdados individuais por FTP — apenas tabulações agregadas via TABNET", e por
isso monta requisições contra o TABNET a partir dos arquivos `.def`. Medido em
2026-09-19, `/dissemin/publicos/SISCAN/SISCAN` tem **130 CSVs e 53,4 GB**,
cobrindo 2013–2025. Raspar o TABNET aqui seria trabalho a mais por uma fonte
pior.

**2. As colunas NÃO são uniformes entre os exames.** Esta é a razão principal do
portão. Um coletor que leia os cinco arquivos com o mesmo `read_csv` e o mesmo
nome de coluna temporal produz recorte silenciosamente errado:

    CITO_COLO ....... CO_ANO_LIBERACAO / CO_ANO_MES_LIBERACAO  (liberação!)
    HISTO_COLO ...... CO_ANO_COMPETENCIA                        (prefixo CO_)
    HISTO_MAMA ...... NU_ANO_COMPETENCIA                        (prefixo NU_)
    CITO_MAMA ....... NU_ANO_COMPETENCIA
    MAMOGRAFIA ...... NU_ANO_COMPETENCIA

Liberação do resultado e competência do exame **não são a mesma data**, e o
citopatológico de colo — o exame de maior volume, 18,5 GB — é justamente o que
só oferece a primeira. Somar os cinco por "ano" sem checar isto mistura dois
eixos temporais. É a mesma família de [[sinan-ano-do-arquivo]]: o ano do arquivo
não quer dizer a mesma coisa em agravos vizinhos.

**3. A visão PACNT é outra coisa, não uma duplicata.** Cada exame vem em duas
visões, `X` e `X_PACNT`. Nenhuma das duas traz nome, CNS, CPF ou data de
nascimento — conferido coluna a coluna. O critério para ficar só com a visão de
exame é de escopo, não de risco: é a que responde "quantos exames neste
município", que é a pergunta do mart.

UM AVISO SOBRE ESTA PRÓPRIA SONDA
---------------------------------
A primeira versão da varredura de identificadores marcava
`TP_RECEPTOR_HORMONAL_ESTROG` como suspeito. Não é: o padrão `CEP` casava dentro
de "reCEPtor". Detector por substring em nome de coluna produz falso positivo com
a mesma facilidade com que produziria falso negativo, e um falso positivo que
ninguém confere vira fonte descartada por engano. A checagem abaixo casa por
palavra (separadores `_`), não por substring.
"""
from __future__ import annotations

import argparse
import ftplib
import json
import re
import socket
import sys
from collections import Counter

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SISCAN/SISCAN"

#: Visões de exame (sem PACNT) que o mart pretende usar.
VISOES = ("CITO_COLO", "HISTO_COLO", "CITO_MAMA", "HISTO_MAMA", "MAMOGRAFIA")

PADRAO = re.compile(r"^SISCAN_(.+?)_(\d{4})\.csv$", re.IGNORECASE)

#: Bytes lidos de cada CSV. Só o cabeçalho interessa; nenhum arquivo é baixado
#: inteiro (o menor tem 2 MB, o maior 1,8 GB).
LIMITE_BYTES = 200_000

#: Chave geográfica do mart. Sem ela a fonte não serve ao recorte municipal.
COLUNA_MUNICIPIO = "CO_MUN_RESIDENCIA"

#: Eixos temporais aceitos, em ordem de preferência. A competência é o eixo do
#: exame; a liberação é o do resultado, e só existe no CITO_COLO.
EIXOS_TEMPORAIS = ("NU_ANO_COMPETENCIA", "CO_ANO_COMPETENCIA", "CO_ANO_LIBERACAO")

#: Identificação direta. Casado por PALAVRA, não por substring — ver o aviso no
#: cabeçalho deste arquivo.
PALAVRAS_IDENTIFICADORAS = {
    "NOME", "CNS", "CPF", "NASC", "DTNASC", "MAE", "ENDERECO", "LOGRADOURO",
    "CEP", "TELEFONE", "EMAIL", "PRONTUARIO",
}


class _Basta(Exception):
    """Interrompe o RETR quando já temos cabeçalho suficiente."""


def _conectar() -> ftplib.FTP:
    # O host resolve para IPv6 em algumas redes e o DataSUS não responde nele;
    # resolver para IPv4 explicitamente é o mesmo tratamento de base_ftp.
    ip = socket.gethostbyname(FTP_HOST)
    ftp = ftplib.FTP()
    ftp.connect(ip, 21, timeout=60)
    ftp.login()
    ftp.set_pasv(True)
    ftp.cwd(FTP_DIR)
    return ftp


def listar() -> list[tuple[str, str, int, int]]:
    """(visao, ano, bytes, ) de cada arquivo do diretório, mais os fora do padrão."""
    ftp = _conectar()
    linhas: list[str] = []
    ftp.retrlines("LIST", linhas.append)
    _fechar(ftp)
    saida = []
    for linha in linhas:
        partes = linha.split()
        nome, tamanho = partes[-1], int(partes[-2])
        m = PADRAO.match(nome)
        if m:
            saida.append((m.group(1).upper(), int(m.group(2)), tamanho, nome))
        else:
            saida.append(("FORA_DO_PADRAO", 0, tamanho, nome))
    return saida


def _fechar(ftp: ftplib.FTP) -> None:
    try:
        ftp.quit()
    except Exception:  # noqa: BLE001 — conexão já suja depois de abortar um RETR
        ftp.close()


def cabecalho(nome: str) -> list[str]:
    """Colunas do CSV, lendo só o começo do arquivo.

    Uma conexão por arquivo: abortar o RETR deixa a sessão inutilizável, e
    reaproveitá-la devolve zero bytes no arquivo seguinte — sem erro, o que faria
    a sonda concluir 'sem colunas' para um arquivo que está inteiro lá.
    """
    ftp = _conectar()
    buffer = bytearray()

    def recebeu(bloco: bytes) -> None:
        buffer.extend(bloco)
        if len(buffer) > LIMITE_BYTES:
            raise _Basta

    try:
        ftp.retrbinary(f"RETR {nome}", recebeu, blocksize=65536)
    except _Basta:
        pass
    except ftplib.error_perm:
        # 550 para arquivo inexistente. Precisa virar "cabeçalho vazio" e seguir
        # até o veredito: a primeira versão subia o traceback, e o portão saía
        # com 1 por acidente, sem dizer qual visão faltou.
        return []
    finally:
        _fechar(ftp)

    texto = bytes(buffer).decode("latin1", errors="replace").splitlines()
    if not texto:
        return []
    return [c.strip().strip('"') for c in texto[0].split(";")]


def identificadores(colunas: list[str]) -> list[str]:
    achados = []
    for coluna in colunas:
        if set(coluna.upper().split("_")) & PALAVRAS_IDENTIFICADORAS:
            achados.append(coluna)
    return achados


def avaliar(ano: int) -> dict:
    arquivos = listar()
    visoes_vistas = Counter(v for v, _, _, _ in arquivos)
    gb = {}
    for visao, _, tamanho, _ in arquivos:
        gb[visao] = gb.get(visao, 0) + tamanho / 1e9

    medidas = {"total_arquivos": len(arquivos),
               "fora_do_padrao": visoes_vistas.get("FORA_DO_PADRAO", 0),
               "gb_por_visao": {k: round(v, 2) for k, v in sorted(gb.items())},
               "visoes": {}}

    for visao in VISOES:
        nome = f"SISCAN_{visao}_{ano}.csv"
        colunas = cabecalho(nome)
        eixo = next((e for e in EIXOS_TEMPORAIS if e in colunas), None)
        medidas["visoes"][visao] = {
            "colunas": len(colunas),
            "tem_municipio_residencia": COLUNA_MUNICIPIO in colunas,
            "eixo_temporal": eixo,
            "eixo_e_competencia": bool(eixo and "COMPETENCIA" in eixo),
            "identificadores_diretos": identificadores(colunas),
        }
    return medidas


def veredito(medidas: dict) -> list[str]:
    falhas = []
    if medidas["fora_do_padrao"]:
        falhas.append(
            f"{medidas['fora_do_padrao']} arquivo(s) fora do padrão "
            "SISCAN_<VISAO>_<AAAA>.csv — o nome mudou e o coletor perderia arquivo "
            "sem reclamar")
    for visao, m in medidas["visoes"].items():
        if not m["colunas"]:
            falhas.append(f"{visao}: cabeçalho vazio — arquivo ausente ou RETR falhou")
            continue
        if not m["tem_municipio_residencia"]:
            falhas.append(f"{visao}: sem {COLUNA_MUNICIPIO} — não serve ao recorte municipal")
        if not m["eixo_temporal"]:
            falhas.append(
                f"{visao}: nenhum eixo temporal conhecido {EIXOS_TEMPORAIS} — "
                "o coletor não teria por onde recortar o ano")
        if m["identificadores_diretos"]:
            falhas.append(
                f"{visao}: coluna de identificação direta {m['identificadores_diretos']} — "
                "confira à mão antes de ingerir")
    return falhas


def main() -> None:
    # O console do Windows abre em cp1252 e estoura em "❌"/"✅", com o traceback
    # saindo DEPOIS do veredito meio impresso — mesmo tratamento de sondar_srag.py.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--ano", type=int, default=2024, help="ano sondado (padrão: 2024)")
    ap.add_argument("--json", action="store_true", help="saída em JSON, para CI")
    args = ap.parse_args()

    medidas = avaliar(args.ano)
    falhas = veredito(medidas)

    if args.json:
        print(json.dumps({**medidas, "ano": args.ano, "apta": not falhas,
                          "falhas": falhas}, ensure_ascii=False, indent=2))
    else:
        print(f"[siscan] {medidas['total_arquivos']} arquivos em {FTP_DIR}")
        print("[siscan] custo por visão (todos os anos):")
        for visao, tamanho in medidas["gb_por_visao"].items():
            marca = " ←" if visao in VISOES else ""
            print(f"           {visao:<22} {tamanho:>6.2f} GB{marca}")
        print(f"[siscan] cabeçalhos de {args.ano}:")
        for visao, m in medidas["visoes"].items():
            eixo = m["eixo_temporal"] or "NENHUM"
            tipo = "competência" if m["eixo_e_competencia"] else "LIBERAÇÃO"
            print(f"           {visao:<12} {m['colunas']:>3} col · município: "
                  f"{'sim' if m['tem_municipio_residencia'] else 'NÃO'} · "
                  f"{eixo} ({tipo})")
        print()
        if falhas:
            for f in falhas:
                print(f"❌ {f}\n")
            print("Fonte NÃO apta para ingestão. Nada foi coletado.")
        else:
            print("✅ Fonte apta. ATENÇÃO ao montar o mart: o eixo temporal NÃO é o "
                  "mesmo nas cinco visões — o CITO_COLO só tem liberação do resultado, "
                  "e as demais têm competência do exame. Não some as cinco por 'ano' "
                  "sem decidir, e documentar, qual eixo o mart adota.")

    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
