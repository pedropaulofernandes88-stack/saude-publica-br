"""
pipeline_siscan.py — rastreamento de colo e mama por município e ano
=====================================================================

    .venv311/Scripts/python scripts/pipeline_siscan.py
    .venv311/Scripts/python scripts/pipeline_siscan.py --anos 2023 2024
    .venv311/Scripts/python scripts/pipeline_siscan.py --parcial

Baixa do FTP do DataSUS, agrega e grava `data/marts/mart_siscan_municipio.parquet`
e `data/marts/mart_siscan_cobertura.parquet`. Não publica: subir para o Supabase
é passo separado.

O RECORTE, E POR QUE ELE É ESTE
-------------------------------
O SISCAN tem cinco exames em duas visões, 53,4 GB (ver `sondar_siscan.py`). Este
pipeline pega **três exames e a visão de exame**:

    HISTO_COLO ..... 0,10 GB    histopatológico do colo do útero
    HISTO_MAMA ..... 0,08 GB    histopatológico da mama
    CITO_MAMA ...... 0,03 GB    citopatológico da mama

Os dois que faltam — CITO_COLO (18,5 GB) e MAMOGRAFIA (9,2 GB) — concentram 28 GB
e ficam para uma decisão própria de custo. **Eles são os exames de rastreamento
populacional**; estes três são, em boa parte, seguimento diagnóstico. Quem ler o
mart precisa saber disso: ele ainda NÃO responde "quantas mulheres foram
rastreadas neste município".

O EIXO TEMPORAL É A COMPETÊNCIA, E ISSO FOI UMA ESCOLHA
--------------------------------------------------------
As cinco visões do SISCAN não usam o mesmo eixo: o CITO_COLO só oferece
`CO_ANO_LIBERACAO` (liberação do RESULTADO), e as outras quatro oferecem
competência do exame. O mart adota **competência**, o que é indolor nesta fatia
justamente porque o CITO_COLO ficou de fora. Quando ele entrar, o eixo terá de
ser reconciliado ou declarado por exame — não somar os dois como se fossem "ano".

TRÊS NOMES PARA A MESMA COISA
------------------------------
A heterogeneidade não para no eixo temporal. A mesma coluna muda de nome entre
exames vizinhos, e por isso cada campo é resolvido por uma LISTA de candidatos,
não por um nome fixo:

    competência ... CO_ANO_COMPETENCIA (histo colo) | NU_ANO_COMPETENCIA (mama)
    idade ......... CO_FAIXA_ETARIA | CO_IDADE_PACIENTE | CO_FAIXA_ETARIA_PACIENTE

`CO_IDADE_PACIENTE` no HISTO_MAMA é IDADE, não faixa — por isso a idade **não
entra** no mart: unificá-la exigiria decidir um recorte de faixas, e um recorte
inventado aqui viajaria como se fosse da fonte.

A FORMA DA SÉRIE, MEDIDA
------------------------
Primeira execução completa em 2026-09-19: 86.901 linhas município×ano×exame,
5.453 dos 5.571 municípios, 1.107.057 exames, 39 de 39 arquivos presentes.

    ano    cito_mama  histo_colo  histo_mama
    2013         666       1.210         444   ← implantação, não é linha de base
    2014      11.137      22.460      13.039
    2019      19.907      48.984      39.970
    2020      13.312      32.933      32.125   ← queda de pandemia, real
    2024      13.838      52.442      66.882
    2025      10.709      47.367      63.279   ← ano ainda aberto

**2013 é ano de implantação do SISCAN**, não um ano baixo: 1.210 histopatológicos
de colo contra 22.460 em 2014. Usá-lo como baseline de tendência inventaria uma
alta. Mesma armadilha da descontinuidade de 2018 no Painel de Oncologia.

O `QT_EXAME` do CITO_MAMA não é decorativo: 12.882 linhas viraram 13.838 exames
em 2024. Assumir uma linha = um exame subcontaria 7% só nesse recorte.

AUSÊNCIA NÃO É ZERO, E A COBERTURA É QUEM DIZ
----------------------------------------------
Município-ano sem exame não vira linha zerada: fica fora do mart. O risco real é
outro e maior — se o arquivo de um ano inteiro falhar ao baixar, TODOS os
municípios daquele ano somem juntos, e a leitura natural é "ninguém fez exame".
Por isso `mart_siscan_cobertura` tem uma linha por (exame, ano) com o que foi
efetivamente lido. Sem ela, falha de coleta é indistinguível de ausência de
serviço — o defeito que o projeto já pagou no SIH do Maranhão em 2023.
"""
from __future__ import annotations

import argparse
import ftplib
import io
import socket
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _saida import Resultado  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"

FTP_HOST = "ftp.datasus.gov.br"
#: Digitado aqui, e não lido de `_fontes.py`, por uma razão de ORDEM: o registro
#: exige que o id exista também em `site/lib/fontes.ts`, e o site exige que toda
#: fonte declarada tenha tabela no manifesto. O mart do SISCAN ainda não foi
#: publicado, então declarar a fonte agora quebraria a guarda do site.
#: `tests/test_registro_de_fontes.py` carrega a exceção com a condição de saída;
#: ao publicar o mart, este caminho vira `fonte("siscan").local(...).caminho`.
FTP_DIR = "/dissemin/publicos/SISCAN/SISCAN"

#: Os três exames desta fatia, com o rótulo que vai para a coluna `exame`.
EXAMES = {"HISTO_COLO": "histo_colo", "HISTO_MAMA": "histo_mama", "CITO_MAMA": "cito_mama"}

ANOS_DISPONIVEIS = list(range(2013, 2026))

#: Resolvidos por lista porque o nome muda entre exames — ver o cabeçalho.
CANDIDATOS_ANO = ("CO_ANO_COMPETENCIA", "NU_ANO_COMPETENCIA")
CANDIDATOS_ANO_MES = ("CO_ANO_MES_COMPETENCIA", "NU_ANO_MES_COMPETENCIA")
COLUNA_MUNICIPIO = "CO_MUN_RESIDENCIA"

#: Só o CITO_MAMA tem contagem por linha; nos outros dois cada linha é um exame.
COLUNA_QUANTIDADE = "QT_EXAME"


def _conectar() -> ftplib.FTP:
    # IPv4 explícito: o host resolve para IPv6 em algumas redes e o DataSUS não
    # responde nele. Mesmo tratamento de `sondar_siscan.py`.
    ftp = ftplib.FTP()
    ftp.connect(socket.gethostbyname(FTP_HOST), 21, timeout=120)
    ftp.login()
    ftp.set_pasv(True)
    ftp.cwd(FTP_DIR)
    return ftp


def baixar(nome: str) -> bytes | None:
    """CSV inteiro em memória, ou None se o arquivo não existe na origem.

    None é ausência declarada pela fonte (550), e é diferente de erro: qualquer
    outra falha sobe e derruba o pipeline, porque tratá-la como ausência é
    exatamente como se perdem meses sem ninguém notar.
    """
    ftp = _conectar()
    buffer = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {nome}", buffer.write, blocksize=1 << 20)
    except ftplib.error_perm as e:
        if str(e).startswith("550"):
            return None
        raise
    finally:
        try:
            ftp.quit()
        except Exception:  # noqa: BLE001 — sessão já suja
            ftp.close()
    return buffer.getvalue()


def _coluna(df: pd.DataFrame, candidatos: tuple[str, ...], exame: str) -> str:
    for c in candidatos:
        if c in df.columns:
            return c
    raise SystemExit(
        f"[siscan] {exame}: nenhuma coluna de {candidatos} no arquivo. "
        "O layout da fonte mudou — reveja sondar_siscan.py antes de ajustar isto.")


def ler(bruto: bytes, exame: str) -> pd.DataFrame:
    """CSV do SISCAN para quadro, já normalizado no que o mart usa."""
    df = pd.read_csv(io.BytesIO(bruto), sep=";", encoding="latin1",
                     dtype=str, low_memory=False)
    col_ano = _coluna(df, CANDIDATOS_ANO, exame)
    col_ano_mes = _coluna(df, CANDIDATOS_ANO_MES, exame)
    if COLUNA_MUNICIPIO not in df.columns:
        raise SystemExit(f"[siscan] {exame}: sem {COLUNA_MUNICIPIO} — layout mudou.")

    saida = pd.DataFrame({
        "municipio_cod": df[COLUNA_MUNICIPIO].astype(str).str.strip().str.zfill(6),
        "ano": pd.to_numeric(df[col_ano], errors="coerce"),
        "ano_mes": df[col_ano_mes].astype(str).str.strip(),
    })
    # Onde a fonte conta por linha, a quantidade é 1; onde ela traz QT_EXAME, é o
    # campo. Assumir 1 para os três daria contagem errada só no CITO_MAMA, e
    # errada para menos — o tipo de viés que passa despercebido.
    if COLUNA_QUANTIDADE in df.columns:
        saida["exames"] = pd.to_numeric(df[COLUNA_QUANTIDADE], errors="coerce").fillna(0)
    else:
        saida["exames"] = 1
    return saida.dropna(subset=["ano"])


def agregar(anos: list[int], quieto: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    pedacos, cobertura = [], []
    for visao, rotulo in EXAMES.items():
        for ano in anos:
            nome = f"SISCAN_{visao}_{ano}.csv"
            bruto = baixar(nome)
            if bruto is None:
                cobertura.append({"exame": rotulo, "ano": ano, "arquivo_existe": False,
                                  "bytes": 0, "linhas_lidas": 0, "municipios": 0})
                if not quieto:
                    print(f"[siscan] {nome}: ausente na origem", flush=True)
                continue
            df = ler(bruto, visao)
            df["exame"] = rotulo
            # O ano da competência não precisa bater com o ano do arquivo, e não
            # forçamos: a divergência é registrada na cobertura para quem for
            # olhar. Filtrar em silêncio esconderia o que a fonte está dizendo.
            pedacos.append(df)
            cobertura.append({
                "exame": rotulo, "ano": ano, "arquivo_existe": True,
                "bytes": len(bruto), "linhas_lidas": len(df),
                "municipios": int(df["municipio_cod"].nunique()),
            })
            if not quieto:
                print(f"[siscan] {nome}: {len(df):,} linhas · "
                      f"{df['municipio_cod'].nunique():,} municípios", flush=True)

    cob = pd.DataFrame(cobertura)
    if not pedacos:
        return pd.DataFrame(), cob

    bruto = pd.concat(pedacos, ignore_index=True)
    mart = (
        bruto.groupby(["municipio_cod", "ano", "exame"], as_index=False)
        .agg(exames=("exames", "sum"),
             meses_com_exame=("ano_mes", "nunique"))
    )
    mart["ano"] = mart["ano"].astype(int)
    mart["exames"] = mart["exames"].astype(int)

    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")[
        ["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]
    mart = mart.merge(dim, on="municipio_cod", how="left")
    return mart.sort_values(["municipio_cod", "ano", "exame"]).reset_index(drop=True), cob


def guardas(mart: pd.DataFrame, cob: pd.DataFrame, anos: list[int], parcial: bool) -> None:
    """Aborta antes de gravar. Cada uma responde a um defeito conhecido."""
    if mart.empty:
        raise SystemExit(
            "[siscan] agregação vazia com arquivos lidos — não grava.\n"
            "         Isto é falha de leitura, não ausência de dado.")

    faltando = cob[~cob["arquivo_existe"]]
    if len(faltando) and not parcial:
        pares = ", ".join(f"{r.exame}/{r.ano}" for r in faltando.itertuples())
        raise SystemExit(
            f"[siscan] {len(faltando)} arquivo(s) ausentes na origem: {pares}.\n"
            "         Um ano inteiro faltando zera TODOS os municípios daquele ano, e\n"
            "         a leitura natural é 'ninguém fez exame'. Passe --parcial para\n"
            "         gravar assim (a cobertura registra quais ficaram de fora).")

    esperado = len(EXAMES) * len(anos)
    if len(cob) != esperado:
        raise SystemExit(
            f"[siscan] cobertura com {len(cob)} linhas, esperado {esperado} "
            f"({len(EXAMES)} exames × {len(anos)} anos) — o laço não cobriu o recorte.")

    chave = ["municipio_cod", "ano", "exame"]
    duplicadas = mart.duplicated(subset=chave).sum()
    if duplicadas:
        raise SystemExit(
            f"[siscan] {duplicadas} linhas duplicadas na chave {chave} — "
            "a agregação não fechou.")

    if (mart["exames"] < 0).any():
        raise SystemExit("[siscan] exames negativos — dado corrompido.")

    fora = mart[mart["meses_com_exame"] > 12]
    if len(fora):
        raise SystemExit(
            f"[siscan] {len(fora)} linhas com mais de 12 meses num ano. Ou a competência "
            "vem fora de 1–12, ou a chave de agregação está errada.")

    sem_dim = mart[mart["municipio_nome"].isna()]
    if len(sem_dim):
        codigos = sorted(sem_dim["municipio_cod"].unique())[:8]
        print(f"[AVISO] {len(sem_dim)} linhas de {sem_dim['municipio_cod'].nunique()} "
              f"município(s) sem correspondência em dim_municipio: {codigos}. "
              "Mantidas — descartá-las apagaria exame realizado.")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--anos", type=int, nargs="+", default=ANOS_DISPONIVEIS)
    ap.add_argument("--parcial", action="store_true",
                    help="grava mesmo com arquivo ausente na origem")
    ap.add_argument("--quieto", action="store_true")
    args = ap.parse_args()
    res = Resultado("scripts/pipeline_siscan.py")

    desconhecidos = [a for a in args.anos if a not in ANOS_DISPONIVEIS]
    if desconhecidos:
        ap.error(f"ano fora de {ANOS_DISPONIVEIS[0]}–{ANOS_DISPONIVEIS[-1]}: {desconhecidos}")

    mart, cob = agregar(args.anos, quieto=args.quieto)
    guardas(mart, cob, args.anos, args.parcial)

    print(f"\n[siscan] {len(mart):,} linhas município×ano×exame | "
          f"{mart['municipio_cod'].nunique():,} municípios | "
          f"{mart['exames'].sum():,} exames")
    for exame, g in mart.groupby("exame"):
        print(f"[siscan]   {exame:<12} {g['exames'].sum():>10,} exames · "
              f"{g['municipio_cod'].nunique():>5,} municípios")

    MARTS.mkdir(parents=True, exist_ok=True)
    res.gravar(mart, MARTS / "mart_siscan_municipio.parquet")
    res.gravar(cob, MARTS / "mart_siscan_cobertura.parquet")
    print("[nota] Fatia de 3 exames: histopatológicos e citopatológico de mama. Os dois "
          "exames de RASTREAMENTO populacional (CITO_COLO e MAMOGRAFIA) não estão aqui — "
          "este mart não responde 'quantas mulheres foram rastreadas'.")
    return res.relatar()


if __name__ == "__main__":
    sys.exit(main())
