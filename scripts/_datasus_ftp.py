"""
_datasus_ftp.py — coleta do FTP do DataSUS que falha alto
=========================================================

Todos os pipelines do SIH/SINASC tinham o mesmo defeito: qualquer exceção ao
baixar um arquivo mensal virava `return None`, e o laço que montava o ano
seguia adiante. Um mês que **falhou** ficava indistinguível de um mês que
**não existe** — e o checkpoint era gravado como se o ano estivesse completo.
Como checkpoint não se refaz, a perda ficava congelada.

O estrago medido em 2026-08-23, comparando os checkpoints v1 (2026-07) com os
v2 (2026-08-11):

    fluxo/ICSAP  MA 2023  -41%   (5 meses perdidos)
    fluxo/ICSAP  AM 2024  -17%
    demanda      PB 2022  -18%   (meses 05 e 06 ausentes)
    demanda      PE 2022   -8%   (mês 11 ausente)
    demanda      GO 2023   -8%   (mês 02 ausente)
    agravo       RR 2022   -7%

Nenhuma dessas perdas disparou alarme: o pipeline terminou com código 0 e
imprimiu números plausíveis.

Este módulo separa as duas situações e não deixa a segunda passar:

    ArquivoAusente  o arquivo não está no diretório do FTP (mês futuro,
                    competência ainda não publicada) — pular é correto.
    FalhaDeColeta   o arquivo existe e a coleta falhou — abortar é correto.

E grava dentro do checkpoint **quais meses** o produziram, para que um
checkpoint incompleto seja detectado na próxima execução em vez de ser
reaproveitado para sempre.
"""
from __future__ import annotations

import contextlib
import io
import tempfile
import threading
import time
from collections.abc import Iterator
from ftplib import FTP
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

HOST_PADRAO = "ftp.datasus.gov.br"
FTP_DIR_SIH = "/dissemin/publicos/SIHSUS/200801_/Dados"
CHAVE_MESES = "saude_em_dado.meses"
CHAVE_FONTE = "saude_em_dado.fonte"

# Uma queda de DNS de poucos minutos nao pode derrubar uma execucao de horas:
# a coleta inteira aborta e o ano-UF em andamento se perde. Dez tentativas com
# espera crescente ate 60 s dao ~6,5 minutos de tolerancia por arquivo, o que
# cobre a oscilacao de rede sem mascarar falha de verdade -- arquivo que nao
# existe e detectado pela LISTAGEM, nunca pela retentativa.
TENTATIVAS = 10


def espera(tentativa: int) -> float:
    return min(60.0, 10.0 * (tentativa + 1))


_listagens: dict[tuple[str, str], set[str]] = {}
_trava = threading.Lock()


class ArquivoAusente(Exception):  # noqa: N818 — nomes em português, como o resto do projeto
    """O arquivo não existe no FTP. Pular é o comportamento correto."""


class FalhaDeColeta(Exception):  # noqa: N818 — idem
    """O arquivo existe (ou o FTP não respondeu) e a coleta falhou.

    Nunca deve ser confundida com ausência: seguir adiante publica um recorte
    silenciosamente incompleto.
    """


def listar(diretorio: str, host: str = HOST_PADRAO, tentativas: int = TENTATIVAS) -> set[str]:
    """Nomes de arquivo do diretório, em MAIÚSCULAS. Uma listagem por processo."""
    chave = (host, diretorio)
    with _trava:
        if chave in _listagens:
            return _listagens[chave]
    erro: Exception | None = None
    for tentativa in range(tentativas):
        try:
            ftp = FTP(host, timeout=180)
            ftp.login()
            try:
                nomes = {Path(n).name.upper() for n in ftp.nlst(diretorio)}
            finally:
                with contextlib.suppress(Exception):
                    ftp.quit()
            if not nomes:
                raise FalhaDeColeta(f"listagem vazia de {diretorio}")
            with _trava:
                _listagens[chave] = nomes
            return nomes
        except Exception as e:      # noqa: BLE001 — reempacotada abaixo
            erro = e
            time.sleep(espera(tentativa))
    raise FalhaDeColeta(f"não consegui listar {host}{diretorio}: {erro}")


def existe(diretorio: str, nome: str, host: str = HOST_PADRAO) -> bool:
    return nome.upper() in listar(diretorio, host)


def baixar(diretorio: str, nome: str, host: str = HOST_PADRAO,
           tentativas: int = TENTATIVAS) -> bytes:
    """Bytes do arquivo. `ArquivoAusente` se não existe, `FalhaDeColeta` se falhou."""
    if not existe(diretorio, nome, host):
        raise ArquivoAusente(f"{nome} não está em {diretorio}")
    erro: Exception | None = None
    for tentativa in range(tentativas):
        try:
            ftp = FTP(host, timeout=180)
            ftp.login()
            try:
                buf = io.BytesIO()
                ftp.retrbinary(f"RETR {diretorio}/{nome}", buf.write)
            finally:
                with contextlib.suppress(Exception):
                    ftp.quit()
            dados = buf.getvalue()
            if not dados:
                raise FalhaDeColeta(f"{nome} veio vazio")
            return dados
        except Exception as e:      # noqa: BLE001 — reempacotada abaixo
            erro = e
            time.sleep(espera(tentativa))
    raise FalhaDeColeta(f"{nome}: {tentativas} tentativas falharam ({erro})")


def registros_dbc(dados: bytes, nome: str) -> Iterator[dict]:
    """Descompacta um .dbc do DataSUS e itera os registros do .dbf resultante."""
    import datasus_dbc
    import dbfread

    tmp = Path(tempfile.gettempdir())
    dbc = tmp / f"{nome}.dbc"
    dbf = tmp / f"{nome}.dbf"
    dbc.write_bytes(dados)
    try:
        datasus_dbc.decompress(str(dbc), str(dbf))
        yield from dbfread.DBF(str(dbf), encoding="latin-1",
                               char_decode_errors="replace", load=False)
    except Exception as e:          # noqa: BLE001 — reempacotada
        raise FalhaDeColeta(f"{nome}: falha ao ler o DBC ({e})") from e
    finally:
        dbc.unlink(missing_ok=True)
        dbf.unlink(missing_ok=True)


def tamanho(diretorio: str, nome: str, host: str = HOST_PADRAO,
            tentativas: int = TENTATIVAS) -> int:
    """Bytes do arquivo no FTP, sem baixa-lo.

    E o detector de revisao mais barato que existe para arquivo anual gigante
    como o DENGBR: o DataSUS reescreve o arquivo preliminar, e o tamanho muda.
    Nao pega reescrita que preserve o tamanho -- para isso so o conteudo.
    """
    if not existe(diretorio, nome, host):
        raise ArquivoAusente(f"{nome} nao esta em {diretorio}")
    erro: Exception | None = None
    for tentativa in range(tentativas):
        try:
            ftp = FTP(host, timeout=180)
            ftp.login()
            try:
                return int(ftp.size(f"{diretorio}/{nome}") or 0)
            finally:
                with contextlib.suppress(Exception):
                    ftp.quit()
        except Exception as e:      # noqa: BLE001 — reempacotada abaixo
            erro = e
            time.sleep(espera(tentativa))
    raise FalhaDeColeta(f"nao consegui medir {nome}: {erro}")


def meses_publicados(diretorio: str, prefixo: str, ano: int,
                     host: str = HOST_PADRAO, extensao: str = "dbc") -> list[int]:
    """Meses do ano que o FTP publica para `{prefixo}{aa}{mm}.{extensao}`."""
    nomes = listar(diretorio, host)
    return [m for m in range(1, 13)
            if f"{prefixo}{ano % 100:02d}{m:02d}.{extensao}".upper() in nomes]


# -- checkpoint que sabe se está completo -----------------------------------

def gravar_checkpoint(df: pd.DataFrame, caminho: Path, meses: list[int] | None = None,
                      fonte: str | None = None) -> None:
    """Grava o checkpoint carimbando de onde ele veio.

    `meses` para as bases mensais (SIH); `fonte` para as anuais (SINAN), onde
    a unidade nao e o mes e sim a VERSAO do arquivo — o DataSUS reescreve o
    preliminar, e um checkpoint mudo seria reaproveitado para sempre.
    """
    tabela = pa.Table.from_pandas(df, preserve_index=False)
    md = dict(tabela.schema.metadata or {})
    if meses is not None:
        md[CHAVE_MESES.encode()] = ",".join(str(m) for m in sorted(meses)).encode()
    if fonte is not None:
        md[CHAVE_FONTE.encode()] = fonte.encode()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(tabela.replace_schema_metadata(md), caminho, compression="zstd")


def meses_do_checkpoint(caminho: Path) -> set[int] | None:
    """Meses carimbados no checkpoint, ou None se ele é anterior ao carimbo."""
    if not caminho.exists():
        return None
    md = pq.ParquetFile(caminho).schema_arrow.metadata or {}
    bruto = md.get(CHAVE_MESES.encode())
    if not bruto:
        return None
    return {int(x) for x in bruto.decode().split(",") if x}


def fonte_do_checkpoint(caminho: Path) -> str | None:
    """A fonte carimbada no checkpoint, ou None se ele e anterior ao carimbo."""
    if not caminho.exists():
        return None
    md = pq.ParquetFile(caminho).schema_arrow.metadata or {}
    bruto = md.get(CHAVE_FONTE.encode())
    return bruto.decode() if bruto else None


def checkpoint_utilizavel(caminho: Path, esperados: list[int]) -> bool:
    """Só reaproveita checkpoint que cobre todos os meses hoje publicados.

    Checkpoint sem carimbo (gravado antes desta guarda) é tratado como
    utilizável apenas se o chamador aceitar — quem quer certeza apaga.
    """
    meses = meses_do_checkpoint(caminho)
    if meses is None:
        return caminho.exists()
    return set(esperados).issubset(meses)
