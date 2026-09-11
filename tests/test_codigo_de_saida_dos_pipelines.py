"""
O código de saída dos pipelines tem três valores, e todo pipeline usa os três.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
`scripts/_saida.py` separa "falhou" de "não veio dado novo". A separação só vale
se for universal: um pipeline fora da convenção sai com 0 sempre, e quem encadeia
não tem como saber que aquele 0 não significa a mesma coisa que o 0 do vizinho.

É o mesmo perigo que já apareceu duas vezes no projeto, e nas duas a ausência de
cobertura não deu erro — ela só deixou de avisar:

  * o observador de fontes vigiava 4 de 12 fontes publicadas, e o teste que
    consertou isso (`test_observacao_de_fontes.py`) é o modelo seguido aqui: uma
    fonte fora da convenção precisa ESTAR DECLARADA como fora, com motivo;
  * a guarda de chave única não rodava para 10 das 52 tabelas publicadas
    enquanto o comentário ao lado afirmava que valia para qualquer origem.

A varredura é por AST, não por texto. Procurar `sys.exit(main())` com grep
acharia a string dentro de uma docstring e daria o teste por passado — foi assim
que a varredura de guardas de 2026-09-02 deixou passar três pontos cegos.

O QUE CADA INVARIANTE IMPEDE
----------------------------
  1. `main() -> int`            — sem a anotação, `return` nu devolve None
  2. `sys.exit(main())`         — sem isso o código calculado é jogado fora
  3. nenhum `return` nu no main — `sys.exit(None)` é 0, ou seja, "dado novo"
  4. `Resultado` importado      — o pipeline tem de ter como medir o desfecho
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _saida import ERRO, NOME, SEM_NOVIDADE, SUCESSO, Resultado  # noqa: E402

pytestmark = pytest.mark.unit

#: Pipeline que NÃO segue a convenção, com o motivo. Estar aqui é uma decisão;
#: não estar em lugar nenhum é esquecimento — e é isso que o teste separa.
#: Vazio hoje: os 24 pipelines de `scripts/` seguem a convenção.
SEM_CONVENCAO: dict[str, str] = {}

BLOCO_MAIN = "__name__ == '__main__'"


def pipelines() -> list[Path]:
    return sorted(SCRIPTS.glob("pipeline_*.py"))


def _main_de(caminho: Path) -> tuple[ast.Module, ast.FunctionDef | None]:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    main = next((n for n in arvore.body
                 if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    return arvore, main


def _ids(caminhos: list[Path]) -> list[str]:
    return [c.name for c in caminhos]


# -- a convenção existe e é universal ---------------------------------------

def test_ha_pipelines_para_varrer():
    # Varredura que não encontra arquivo nenhum passa em silêncio e não prova
    # nada. Este teste é o que impede o resto do arquivo de ser decorativo.
    assert len(pipelines()) >= 20


@pytest.mark.parametrize("caminho", pipelines(), ids=_ids(pipelines()))
def test_pipeline_segue_a_convencao_de_saida(caminho: Path):
    if caminho.name in SEM_CONVENCAO:
        pytest.skip(f"fora da convenção por decisão: {SEM_CONVENCAO[caminho.name]}")

    arvore, main = _main_de(caminho)
    assert main is not None, f"{caminho.name}: sem def main()"

    # 1. assinatura anotada como int
    retorno = main.returns
    assert isinstance(retorno, ast.Name) and retorno.id == "int", (
        f"{caminho.name}: main() precisa ser anotada '-> int'; sem isso um "
        f"'return' nu devolve None e vira exit 0")

    # 2. importa Resultado de _saida
    importa = any(
        isinstance(n, ast.ImportFrom) and n.module == "_saida"
        and any(a.name == "Resultado" for a in n.names)
        for n in ast.walk(arvore))
    assert importa, f"{caminho.name}: não importa Resultado de _saida"

    # 3. nenhum 'return' nu dentro de main
    nus = [n.lineno for n in ast.walk(main)
           if isinstance(n, ast.Return) and n.value is None]
    assert not nus, (
        f"{caminho.name}: 'return' sem valor em {nus} — sai 0 e afirma dado novo")

    # 4. o bloco __main__ passa o código adiante
    blocos = [n for n in arvore.body
              if isinstance(n, ast.If) and ast.unparse(n.test) == BLOCO_MAIN]
    assert blocos, f"{caminho.name}: sem bloco __main__"
    corpo = ast.unparse(blocos[-1]).replace(" ", "")
    assert "sys.exit(main())" in corpo, (
        f"{caminho.name}: o bloco __main__ precisa ser sys.exit(main()); "
        f"chamar main() solto descarta o código calculado")


@pytest.mark.parametrize("caminho", pipelines(), ids=_ids(pipelines()))
def test_main_tem_algum_caminho_que_devolve_valor(caminho: Path):
    """Anotar '-> int' e nunca retornar nada também sai 0."""
    if caminho.name in SEM_CONVENCAO:
        pytest.skip(SEM_CONVENCAO[caminho.name])
    _, main = _main_de(caminho)
    com_valor = [n for n in ast.walk(main)
                 if isinstance(n, ast.Return) and n.value is not None]
    assert com_valor, f"{caminho.name}: main() anotada '-> int' mas não retorna nada"


def test_excecao_declarada_existe_de_fato():
    """Nome em SEM_CONVENCAO sem arquivo correspondente é lixo que esconde
    cobertura — o dicionário passaria a isentar um pipeline inexistente."""
    nomes = {p.name for p in pipelines()}
    sobrando = set(SEM_CONVENCAO) - nomes
    assert not sobrando, f"declarados fora da convenção mas inexistentes: {sobrando}"


# -- semântica dos códigos ---------------------------------------------------

def test_os_tres_codigos_sao_distintos():
    assert len({SUCESSO, ERRO, SEM_NOVIDADE}) == 3


def test_sem_novidade_nao_e_zero_nem_um():
    # Se um dia virar 0, "nada mudou" passa a se anunciar como dado novo. Se
    # virar 1, passa a derrubar quem chamou como se tivesse falhado.
    assert SEM_NOVIDADE not in (SUCESSO, ERRO)
    assert SUCESSO == 0
    assert ERRO == 1


def test_todo_codigo_tem_nome_legivel():
    assert set(NOME) == {SUCESSO, ERRO, SEM_NOVIDADE}


# -- Resultado: o desfecho medido --------------------------------------------

def test_resultado_vazio_e_sem_novidade():
    """'--medir' e '--no-upload' param antes de publicar. Sair 0 ali afirmaria
    dado novo que ninguém recebeu."""
    assert Resultado("teste").codigo == SEM_NOVIDADE


def test_uma_tabela_que_mudou_basta_para_sucesso():
    res = Resultado("teste")
    res.registrar("a", False)
    res.registrar("b", True)
    assert res.codigo == SUCESSO
    assert res.novidades == ["b"]


def test_todas_iguais_e_sem_novidade():
    res = Resultado("teste")
    res.registrar("a", False)
    res.registrar("b", False)
    assert res.codigo == SEM_NOVIDADE
    assert res.novidades == []


def test_registrar_duas_vezes_acumula_por_ou():
    """Uma competência nova entre dez repetidas ainda é novidade."""
    res = Resultado("teste")
    res.registrar("pni", False)
    res.registrar("pni", True)
    res.registrar("pni", False)
    assert res.codigo == SUCESSO


# -- a guarda precisa REPROVAR de verdade, com arquivo real -------------------

def _df():
    import pandas as pd
    return pd.DataFrame({"uf": ["MG", "SP"], "ano": [2024, 2024], "n": [10, 20]})


def test_gravar_o_mesmo_quadro_duas_vezes_da_sem_novidade(tmp_path):
    """O caminho que importa, exercitado ponta a ponta.

    Se o Parquet não fosse byte-estável, SEM_NOVIDADE nunca aconteceria e o
    módulo inteiro seria decoração — guarda declarada que nunca reprova. Este
    teste é o que prova que ela reprova.
    """
    destino = tmp_path / "mart_x.parquet"

    primeira = Resultado("teste")
    primeira.gravar(_df(), destino)
    assert primeira.codigo == SUCESSO, "primeira gravação é sempre novidade"

    segunda = Resultado("teste")
    segunda.gravar(_df(), destino)
    assert segunda.codigo == SEM_NOVIDADE


def test_gravar_quadro_diferente_da_sucesso(tmp_path):
    destino = tmp_path / "mart_x.parquet"
    Resultado("teste").gravar(_df(), destino)

    df2 = _df()
    df2.loc[0, "n"] = 11          # um único valor muda
    res = Resultado("teste")
    res.gravar(df2, destino)
    assert res.codigo == SUCESSO, "conteúdo diferente tem de ser detectado"


def test_mudanca_que_a_contagem_de_linhas_nao_veria(tmp_path):
    """Duplicata e ausência se cancelam na contagem de linhas. No sha256, não."""
    import pandas as pd

    destino = tmp_path / "mart_x.parquet"
    a = pd.DataFrame({"uf": ["MG", "SP", "BA"], "n": [1, 2, 3]})
    b = pd.DataFrame({"uf": ["MG", "MG", "BA"], "n": [1, 2, 3]})  # SP some, MG duplica
    assert len(a) == len(b), "o par só vale se a contagem for igual nos dois"

    Resultado("teste").gravar(a, destino)
    res = Resultado("teste")
    res.gravar(b, destino)
    assert res.codigo == SUCESSO


def test_acumular_a_mesma_fatia_duas_vezes_da_sem_novidade(tmp_path):
    """O caso do SIH, que processa um ano por execução e funde no Parquet.

    Refazer 2024 sobre um arquivo que já tem 2024 não muda byte nenhum — e é
    exatamente esse o caso que precisava deixar de sair 0. A chave primária vem
    do schema.sql versionado, como no pipeline de verdade.
    """
    import pandas as pd

    destino = tmp_path / "mart_icsap_municipio.parquet"
    fatia = pd.DataFrame({"municipio_cod": ["310620", "355030"], "ano": [2024, 2024],
                          "internacoes": [10, 20]})

    primeira = Resultado("teste")
    primeira.acumular(fatia, destino, "mart_icsap_municipio")
    assert primeira.codigo == SUCESSO

    segunda = Resultado("teste")
    _, antes, depois = segunda.acumular(fatia.copy(), destino, "mart_icsap_municipio")
    assert (antes, depois) == (2, 2), "a fatia repetida não pode duplicar linhas"
    assert segunda.codigo == SEM_NOVIDADE


def test_acumular_ano_novo_da_sucesso(tmp_path):
    import pandas as pd

    destino = tmp_path / "mart_icsap_municipio.parquet"
    Resultado("teste").acumular(
        pd.DataFrame({"municipio_cod": ["310620"], "ano": [2024], "internacoes": [10]}),
        destino, "mart_icsap_municipio")

    res = Resultado("teste")
    res.acumular(
        pd.DataFrame({"municipio_cod": ["310620"], "ano": [2025], "internacoes": [11]}),
        destino, "mart_icsap_municipio")
    assert res.codigo == SUCESSO


def test_relatar_devolve_o_mesmo_que_codigo(capsys):
    res = Resultado("teste")
    res.registrar("a", True)
    assert res.relatar() == SUCESSO
    assert "SUCESSO" in capsys.readouterr().out
