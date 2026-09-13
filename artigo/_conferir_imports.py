"""
_conferir_imports.py — o pacote tem de conter o que os seus scripts importam
=============================================================================

Usado pelos `empacotar.py` dos artigos.

POR QUE ESTA GUARDA EXISTE
---------------------------
Uma auditoria externa tentou reexecutar o pacote do artigo de imunopreveníveis e
a análise **não começou**: ela abre com `from _achados import registrar`, e
`_achados.py` não estava no ZIP. O pacote parecia completo — tinha manuscrito,
tabelas, figuras e três arquivos em `codigo/` —, e o único jeito de descobrir a
falta era tentar rodar, que é exatamente o que ninguém faz antes de enviar.

É a mesma família do resto das guardas deste projeto: contagem não detecta
ausência, e "parece completo" é a forma mais cara de estar incompleto, porque o
erro só aparece na mão de quem recebeu.

O QUE ELA CONFERE, E O QUE NÃO
-------------------------------
Ela lê a árvore sintática de cada `.py` que vai para o pacote e coleta os
módulos **locais** importados — os que começam com sublinhado, que é a convenção
deste repositório para módulo interno. Se algum não estiver entre os arquivos
empacotados, aborta e diz qual.

Não resolve import transitivo além de um nível sem que o arquivo intermediário
esteja no pacote — mas isso é justamente o que ela força: se `_a` entra e
importa `_b`, `_b` também é conferido, porque `_a` passa a ser um dos arquivos
lidos. Também não confere dependência externa (`numpy`, `scipy`): isso é
trabalho de um arquivo de ambiente, e está declarado como pendência no LEIA-ME
de cada pacote.
"""
from __future__ import annotations

import ast
from pathlib import Path


def modulos_locais(codigo: str) -> set[str]:
    """Os módulos com sublinhado que este arquivo importa.

    `from _achados import registrar` e `import _sim_obitos` contam; `import sys`
    e `from pathlib import Path` não. A convenção do repositório é que módulo
    interno começa com sublinhado, e é ela que separa os dois casos.
    """
    achados: set[str] = set()
    for no in ast.walk(ast.parse(codigo)):
        if isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            achados.add(no.module.split(".")[0])
        elif isinstance(no, ast.Import):
            achados.update(a.name.split(".")[0] for a in no.names)
    # Um sublinhado, e nao dois: `__future__` e' da linguagem, nao deste
    # repositorio, e a primeira versao desta guarda o acusava como modulo local
    # faltando — reprovando todo pacote que existe. Guarda que reprova sempre
    # e' desligada na primeira vez, e ai nao guarda mais nada.
    return {m for m in achados
            if m.startswith("_") and not m.startswith("__")}


def conferir(itens: list[tuple[str, bytes, str]], pacote: str) -> None:
    """Aborta se um script empacotado importar módulo local que ficou de fora.

    `itens` é a lista que o empacotador já montou: (caminho no ZIP, bytes,
    descrição). A conferência acontece sobre ela, e não sobre o disco, porque o
    que importa é o que vai **dentro** do pacote.
    """
    nomes = {Path(destino).stem for destino, _, _ in itens
             if destino.endswith(".py")}
    faltando: dict[str, set[str]] = {}
    for destino, dados, _ in itens:
        if not destino.endswith(".py"):
            continue
        try:
            precisa = modulos_locais(dados.decode("utf-8"))
        except SyntaxError as e:
            raise SystemExit(
                f"{destino} não compila ({e}). Um pacote com script quebrado é "
                "pior que um sem script, porque parece reprodutível.") from e
        fora = precisa - nomes
        if fora:
            faltando[destino] = fora

    if faltando:
        linhas = "\n".join(f"  {d} importa {sorted(m)}"
                           for d, m in sorted(faltando.items()))
        raise SystemExit(
            f"{pacote}: há script importando módulo local que não vai no "
            f"pacote.\n{linhas}\n"
            "Quem receber o ZIP não consegue executar: a análise falha no "
            "import, antes de ler qualquer dado. Acrescente o arquivo a "
            "CONTEUDO, ou remova o script do pacote.")


def conferir_derivados(itens: list[tuple[str, bytes, str]], fonte: Path,
                       pacote: str) -> None:
    """Aborta se um derivado do manuscrito for mais antigo que o manuscrito.

    POR QUE ESTA GUARDA EXISTE
    ---------------------------
    O pacote do artigo de imunopreveníveis distribuía um `manuscrito.html` e um
    `manuscrito.pdf` gerados semanas antes da revisão. Eles traziam o título
    anterior e, pior, a frase "o cruzamento ecológico deu nulo pelo critério
    declarado" — uma conclusão que o autor havia **retirado** do DOCX por ser
    baseada em exposição mal medida. Quem abrisse o pacote pelo PDF leria a
    versão retratada, e nada no ZIP indicava qual das duas valia.

    O manuscrito em Markdown é a fonte; tudo o que deriva dele tem de ser mais
    novo que ele. A comparação é de data de modificação em disco, o que é
    grosseiro mas suficiente: o modo de falha real não é uma diferença de
    segundos, é um derivado de semanas atrás que ninguém regerou.
    """
    if not fonte.exists():
        raise SystemExit(f"{fonte} não existe; nada para comparar.")
    ref = fonte.stat().st_mtime
    velhos = {}
    for destino, _, _ in itens:
        if not destino.endswith((".html", ".pdf", ".docx")):
            continue
        local = fonte.parent / Path(destino).name
        if local.exists() and local.stat().st_mtime < ref - 1:
            velhos[destino] = local.name
    if velhos:
        raise SystemExit(
            f"{pacote}: derivados mais antigos que o manuscrito: "
            f"{sorted(velhos)}.\n"
            "Eles podem trazer título, conclusão ou números de uma versão "
            "anterior, e quem recebe o pacote não tem como saber qual vale. "
            "Rode `artigo/renderizar.py` e `artigo/gerar_docx.py` antes de "
            "empacotar.")
