"""
sondar_siasus.py — SIA/SUS (APAC oncológica) está pronto, e o que ele NÃO mede
==============================================================================

    python scripts/sondar_siasus.py
    python scripts/sondar_siasus.py --json

Sai 0 quando a fonte serve. Sai ≠ 0 enquanto não, nomeando cada razão. Portão,
não relatório: rodar antes de escrever coletor.

O QUE O SIA/SUS ACRESCENTA
---------------------------
Traz **gasto EXECUTADO ligado a estabelecimento e a paciente**, que é exatamente
o que os convênios federais não conseguiram dar: lá, 5,9% do valor casava com um
estabelecimento do CNES, porque quem assina convênio é prefeitura. Aqui o CNES
executante (`AP_CODUNI`) vem em 100% dos registros, junto com o valor aprovado
da APAC e o município de residência do paciente.

O RECORTE, E POR QUE ELE RESOLVE DUAS COISAS DE UMA VEZ
--------------------------------------------------------
Medido no FTP em 2026-09-20 — 54.478 arquivos, e a composição decide sozinha:

    grupo                    arquivos      GB   partidos
    PA  produção ambulatorial   6.454  212,22        740
    BI  boletim individualizado 6.191  186,44        257
    AM  APAC medicamentos       5.957   18,62          0
    AQ  APAC quimioterapia      5.979    5,06          0
    AR  APAC radioterapia       5.465    0,36          0
    demais (PS, AD, ATD, AN…)  18.412    8,08          0

**PA e BI concentram 98,7% do volume E 100% dos 997 arquivos partidos** — a pior
armadilha do FTP do DataSUS, com duas convenções opostas que se cancelariam num
total nacional (ver a memória `ftp-datasus-mapa`). Recortar para APAC elimina o
volume e a armadilha na mesma decisão, sem que isso seja sorte: os arquivos
partidos existem porque PA e BI são grandes demais para um arquivo só.

`AQ` + `AR` são **5,42 GB em 11.444 arquivos**, comparável ao SISCAN. `AM`
(18,6 GB) fica para depois, e tem eixo próprio (medicamento de alto custo).

O QUE VEM EM CADA REGISTRO (74 campos)
---------------------------------------
Comuns a toda APAC:

    AP_CODUNI .. CNES executante        AP_MUNPCN .. município do PACIENTE
    AP_CIDPRI .. CID-10 principal       AP_UFMUN ... município do ESTABELECIMENTO
    AP_VL_AP ... valor aprovado (R$)    AP_CMP ..... competência
    AP_TPAPAC .. 1=inicial 2=continuação AP_NUIDADE/AP_SEXO

Próprios da quimioterapia (`AQ_`) e da radioterapia (`AR_`): estadiamento, grau
histológico, data do diagnóstico, início do tratamento, finalidade, e — só na
quimio — os dez campos de medicamento do esquema.

Preenchimento medido em 104.190 APACs de quimioterapia (AC, PE e SP, 2024-01):

    AQ_DTIDEN, AQ_DTINTR, AP_CIDPRI, AP_CODUNI, AP_MUNPCN .... 100,0%
    AQ_GRAHIS (grau histológico) .............................. 89,5%
    AP_VL_AP (valor aprovado) ................................. 90,9%
    AQ_ESTADI (estadiamento) .................................. 84,1%

O estadiamento em 84,1% é **muito melhor que os 49% do Painel de Oncologia**
(ver `painel-oncologia-denominador`), e essa diferença é uma razão forte para a
fonte existir ao lado do Painel em vez de substituí-la.

╔══════════════════════════════════════════════════════════════════════════════╗
║ A REFUTAÇÃO — ESTA FONTE **NÃO** MEDE O PRAZO DA LEI DOS 60 DIAS             ║
╚══════════════════════════════════════════════════════════════════════════════╝

É o achado mais importante desta sondagem, e ele existe porque a conta ÓBVIA
produz um número que parece manchete e é falso.

`AQ_DTIDEN` (diagnóstico) e `AQ_DTINTR` (início do tratamento) estão 100%
preenchidos e parecem entregar de graça o intervalo da Lei 12.732/2012. Medido
em Pernambuco, 2024-01:

    todas as APACs ........................... mediana 323d | 79,0% acima de 60d
    só AP_TPAPAC=1 (inicial) ................. mediana 288d | 78,0%
    + AQ_CONTTR='N' (sem continuidade) ....... mediana 239d | 76,3%
    + AQ_TRANTE='N' (sem tratamento anterior)  mediana 196d | 72,4%

**Nenhum filtro resgata o número.** Uma mediana de 196 dias para "começar o
tratamento depois do diagnóstico" não descreve o sistema: descreve outra coisa.
E a amostra sem filtro trazia `max = 1.526.633 dias` — 4.182 anos —, aritmética
que só é possível sobre data corrompida (há diagnósticos carimbados em 1919).

A explicação que sobra: **APAC "inicial" é inicial de um PLANO de tratamento, não
do paciente.** Quem recidiva, troca de linha terapêutica ou muda de
estabelecimento gera nova APAC inicial carregando a data de diagnóstico
ORIGINAL. O intervalo medido é "tempo desde o diagnóstico entre quem está em
tratamento", que é medida de prevalência — e não tem nada a ver com fila.

Publicar 79% como "pacientes que esperam mais de 60 dias" seria erro grave e de
alta repercussão. Para medir o prazo de verdade é preciso a PRIMEIRA APAC da
vida do paciente, o que exige ligação longitudinal por `AP_CNSPCN` — que vem
100% preenchido, é estável dentro do arquivo (17.108 distintos em 17.867
linhas), e é **criptografado**: os bytes são opacos. Ligação por ele é projeto
próprio, não subproduto deste coletor.

Até que isso exista, o mart NÃO publica prazo. Ver [[criterio-antes-do-dado]].

O QUE A FONTE MEDE BEM, E QUE NINGUÉM MAIS MEDE
-------------------------------------------------
**Fluxo de paciente para tratamento oncológico.** `AP_MUNPCN` (residência) e
`AP_UFMUN` (estabelecimento) são campos distintos, e medido na amostra:
**54,0% das APACs de quimioterapia são de paciente tratado fora do próprio
município**. É o análogo oncológico de `mart_fluxo_intermunicipal`, que o
projeto já tem para internação.

Mais: valor aprovado por estabelecimento e por CID, estadiamento na entrada do
tratamento, e o esquema de medicamentos.

CUSTO
-----
11.444 arquivos, 5,42 GB, 2008–2026, por UF e competência. É ingestão de
microdado com checkpoint por UF-ano, da ordem do que o SISCAN custou.
"""
from __future__ import annotations

import argparse
import ftplib
import json
import re
import socket
import sys
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "ftp.datasus.gov.br"
DIRETORIO = "/dissemin/publicos/SIASUS/200801_/Dados"

#: Os grupos que este projeto ingere. Quimioterapia e radioterapia: o eixo
#: oncológico, que conversa com o Painel de Oncologia já publicado.
GRUPOS_ALVO = ("AQ", "AR")

#: Grupos que ficam FORA por decisão, não por esquecimento. PA e BI somam 398 GB
#: e todos os arquivos partidos do SIA; AM tem eixo próprio e 18,6 GB.
GRUPOS_FORA = {
    "PA": "produção ambulatorial — 212 GB e 740 arquivos partidos",
    "BI": "boletim individualizado — 186 GB e 257 arquivos partidos",
    "AM": "APAC de medicamentos — 18,6 GB, eixo próprio (alto custo)",
}

#: Mínimo de arquivos esperado por grupo alvo. 27 UFs × 12 meses × 18 anos dá
#: ~5.800; abaixo de 4.000 alguma coisa mudou no FTP e o coletor ingeriria um
#: recorte parcial achando que é o todo.
MINIMO_ARQUIVOS = 4_000

#: O formato do `LIST` do IIS, que o DataSUS usa. Parser de `ls` do Unix devolve
#: ZERO arquivos sem erro aqui — o diretório parece vazio. Ver `ftp-datasus-mapa`.
RX_LIST = re.compile(r"(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}[AP]M)\s+(\d+)\s+(\S+)\s*$")

#: <GRUPO><UF><AA><MM>[sufixo].dbc — o sufixo marca arquivo PARTIDO.
RX_NOME = re.compile(r"^([A-Z]{2,3})([A-Z]{2})(\d{2})(\d{2})([a-z]|_\d)?\.dbc$", re.I)


def listar() -> list[str]:
    ftp = ftplib.FTP()
    ftp.connect(socket.gethostbyname(HOST), 21, timeout=180)
    ftp.login()
    ftp.set_pasv(True)
    ftp.cwd(DIRETORIO)
    linhas: list[str] = []
    ftp.retrlines("LIST", linhas.append)
    ftp.quit()
    return linhas


def compor(linhas: list[str]) -> tuple[dict, int, dict]:
    grupos: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    partidos: dict[str, int] = defaultdict(int)
    fora_da_gramatica = 0
    for linha in linhas:
        m = RX_LIST.match(linha)
        if not m:
            fora_da_gramatica += 1
            continue
        tamanho, nome = int(m.group(3)), m.group(4)
        n = RX_NOME.match(nome)
        if not n:
            fora_da_gramatica += 1
            continue
        g = n.group(1).upper()
        grupos[g][0] += 1
        grupos[g][1] += tamanho
        if n.group(5):
            partidos[g] += 1
    return dict(grupos), fora_da_gramatica, dict(partidos)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    impedimentos: list[str] = []
    try:
        linhas = listar()
    except Exception as e:  # noqa: BLE001
        print(f"❌ o FTP não respondeu: {type(e).__name__}: {e}")
        print("Fonte NÃO apta para ingestão. Nada foi coletado.")
        return 1

    grupos, fora, partidos = compor(linhas)
    relatorio = {
        "arquivos_no_diretorio": len(linhas),
        "grupos": {g: {"arquivos": v[0], "gb": round(v[1] / 1e9, 2),
                       "partidos": partidos.get(g, 0)}
                   for g, v in grupos.items()},
        "fora_da_gramatica": fora,
    }

    for g in GRUPOS_ALVO:
        if g not in grupos:
            impedimentos.append(
                f"o grupo {g} sumiu do FTP. Era {g} que o recorte deste projeto "
                f"ingere; sem ele não há o que coletar."
            )
            continue
        n = grupos[g][0]
        if n < MINIMO_ARQUIVOS:
            impedimentos.append(
                f"o grupo {g} tem {n:,} arquivos, abaixo do mínimo de "
                f"{MINIMO_ARQUIVOS:,}. Ingerir assim publicaria um recorte parcial "
                f"como se fosse a série inteira."
            )
        if partidos.get(g):
            impedimentos.append(
                f"o grupo {g} passou a ter {partidos[g]} arquivo(s) PARTIDO(s), e "
                f"não tinha nenhum quando o recorte foi decidido. As duas "
                f"convenções do DataSUS são opostas — uma some com a competência, "
                f"a outra conta em dobro — e o coletor não as trata."
            )

    if args.json:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        print(f"[siasus] {len(linhas):,} arquivos em {DIRETORIO}")
        print(f"\n{'grupo':<8}{'arquivos':>10}{'GB':>9}{'partidos':>10}   ")
        for g, v in sorted(grupos.items(), key=lambda kv: -kv[1][1]):
            marca = "  <- ALVO" if g in GRUPOS_ALVO else (
                f"  ({GRUPOS_FORA[g]})" if g in GRUPOS_FORA else "")
            print(f"{g:<8}{v[0]:>10,}{v[1]/1e9:>9.2f}{partidos.get(g, 0):>10}{marca}")
        if fora:
            print(f"\n[siasus] {fora} linha(s) fora da gramática de nome")
        print()
        for i in impedimentos:
            print(f"❌ {i}\n")

    if impedimentos:
        print("Fonte NÃO apta para ingestão. Nada foi coletado.")
        return 1
    alvo = sum(grupos[g][0] for g in GRUPOS_ALVO)
    gb = sum(grupos[g][1] for g in GRUPOS_ALVO) / 1e9
    print(f"✅ Fonte apta: {alvo:,} arquivos e {gb:.2f} GB nos grupos "
          f"{'+'.join(GRUPOS_ALVO)}, nenhum partido.")
    print("   LEMBRE do que ela NÃO mede: o prazo da Lei dos 60 Dias não sai de "
          "AQ_DTIDEN/AQ_DTINTR — ver o cabeçalho deste arquivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
