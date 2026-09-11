"""
_saida.py — o código de saída de um pipeline tem três valores, não dois.

POR QUE ISTO EXISTE
-------------------
Até aqui todo pipeline do projeto terminava em 0 ou estourava. Isso responde
"deu erro?" e deixa a segunda pergunta sem resposta: *veio dado novo?*

As duas não são a mesma pergunta, e confundi-las já custou caro. Em 2026-08-11
os pipelines do SIH gravaram checkpoints incompletos porque `except Exception:
return None` tratava "mês falhou" como "mês não existe": MA 2023 perdeu 5 dos 12
meses e o processo terminou com código 0. A correção de lá separou as
*exceções* (`ArquivoAusente` vs. `FalhaDeColeta`, em `_datasus_ftp.py`); esta
aqui separa o *desfecho*, que é o que chega a quem chamou.

    SUCESSO       (0) -- rodou certo E o que foi gravado mudou
    ERRO          (1) -- falhou de verdade
    SEM_NOVIDADE  (2) -- rodou certo, e nada mudou desde a última vez

ERRO não precisa ser produzido à mão: exceção não capturada e `SystemExit("msg")`
já saem com 1. O que faltava era o 2.

O QUE CONTA COMO NOVIDADE
-------------------------
O conteúdo do mart mudou. `Resultado.gravar()` tira o sha256 do arquivo de
destino ANTES de escrever e compara com o de depois — Parquet escrito pelo
`escrever_parquet` é byte-estável para o mesmo DataFrame (verificado: duas
gravações do mesmo quadro, com um segundo de intervalo, dão o mesmo sha256).

Isto é deliberadamente mais forte que a checagem por tamanho de arquivo que a
mesma ideia costuma receber: tamanho igual não implica conteúdo igual, e já
sabemos que contagem de linhas não detecta corrupção — duplicata e ausência se
cancelam na contagem e não se cancelam no hash.

E é deliberadamente mais fraco que "a FONTE mudou": responder isso exige um
manifesto dos arquivos de origem consumidos, que o projeto ainda não tem. O
desfecho aqui é sobre o artefato produzido, não sobre o insumo lido. Um
reprocessamento que chega ao mesmo mart é, para quem consome, SEM_NOVIDADE — e
é essa a pergunta que o 2 responde.

ATENÇÃO A QUEM CHAMA
--------------------
2 é diferente de zero. `set -e`, `&&` e o `run:` do GitHub Actions leem qualquer
código != 0 como falha. Quem encadeia pipeline precisa tratar o 2
explicitamente:

    python scripts/pipeline_sinan.py; c=$?
    [ $c -eq 1 ] && exit 1        # só o 1 é falha

Uso:
    from _saida import SEM_NOVIDADE, SUCESSO, Resultado

    def main() -> int:
        res = Resultado("scripts/pipeline_x.py")
        ...
        res.gravar(df, MARTS / "mart_x.parquet")
        return res.relatar()

    if __name__ == "__main__":
        sys.exit(main())
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - só para o type checker
    import pandas as pd

#: rodou certo E há dado novo.
SUCESSO = 0
#: falhou de verdade. Sai sozinho por exceção não capturada; está aqui para ser
#: nomeável por quem chama.
ERRO = 1
#: rodou certo, mas nada mudou desde a última vez.
SEM_NOVIDADE = 2

NOME = {
    SUCESSO: "SUCESSO (dado novo)",
    ERRO: "ERRO",
    SEM_NOVIDADE: "SEM NOVIDADE (nada mudou)",
}


class Resultado:
    """Acumula o que o pipeline gravou e devolve o código de saída.

    Vazio vale SEM_NOVIDADE: um pipeline que não produziu nada não tem
    novidade a anunciar. É o mesmo critério que `--medir` e `--no-upload`
    precisam — eles param antes de publicar, e sair com 0 ali afirmaria dado
    novo que ninguém recebeu.
    """

    def __init__(self, produtor: str) -> None:
        self.produtor = produtor
        self._mudou: dict[str, bool] = {}

    # -- registro ------------------------------------------------------------

    def registrar(self, nome: str, mudou: bool) -> None:
        """Declara o desfecho de um artefato que este módulo não escreveu.

        Para pipeline que grava fora do `escrever_parquet` (agregado de
        competência do PNI, `COPY ... TO` do DuckDB) e sabe por conta própria se
        produziu algo novo. Registrar duas vezes o mesmo nome acumula por OU:
        uma competência nova entre dez repetidas ainda é novidade.
        """
        self._mudou[nome] = self._mudou.get(nome, False) or mudou

    def gravar(self, df: pd.DataFrame, destino: Path, origem: str = "pipeline",
               produtor: str | None = None) -> Path:
        """`escrever_parquet` + a pergunta "mudou?" respondida pelo sha256."""
        from _publicacao import escrever_parquet, sha256_de

        antes = sha256_de(destino) if destino.exists() else None
        caminho = escrever_parquet(df, destino, origem, produtor or self.produtor)
        self.registrar(destino.stem, sha256_de(caminho) != antes)
        return caminho

    def acumular(self, df: pd.DataFrame, destino: Path, tabela: str,
                 origem: str = "pipeline", produtor: str | None = None
                 ) -> tuple[Path, int, int]:
        """`acumular_parquet` com a mesma medição.

        O SIH processa um ano por execução e funde no Parquet existente. Fundir
        uma fatia já presente não muda byte nenhum — e é exatamente esse o caso
        que precisa sair com 2 em vez de 0.
        """
        from _publicacao import acumular_parquet, sha256_de

        antes_sha = sha256_de(destino) if destino.exists() else None
        caminho, antes, depois = acumular_parquet(df, destino, tabela, origem,
                                                  produtor or self.produtor)
        self.registrar(tabela, sha256_de(caminho) != antes_sha)
        return caminho, antes, depois

    # -- desfecho ------------------------------------------------------------

    @property
    def novidades(self) -> list[str]:
        return sorted(n for n, mudou in self._mudou.items() if mudou)

    @property
    def codigo(self) -> int:
        if not self._mudou:
            return SEM_NOVIDADE
        return SUCESSO if any(self._mudou.values()) else SEM_NOVIDADE

    def relatar(self) -> int:
        """Imprime o desfecho e devolve o código. Chame no `return` do main()."""
        codigo = self.codigo
        if not self._mudou:
            print(f"[saida] {self.produtor}: nada foi gravado -> {NOME[codigo]}")
            return codigo
        novas = self.novidades
        if novas:
            print(f"[saida] {self.produtor}: {len(novas)} de {len(self._mudou)} "
                  f"tabela(s) mudaram -> {NOME[codigo]}")
            for n in novas:
                print(f"[saida]   + {n}")
        else:
            print(f"[saida] {self.produtor}: {len(self._mudou)} tabela(s) "
                  f"reescritas idênticas -> {NOME[codigo]}")
        return codigo
