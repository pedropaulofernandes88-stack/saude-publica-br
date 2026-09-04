"""As tabelas do manuscrito continuam sendo as que os CSVs dizem.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O manuscrito trazia doze tabelas em Markdown copiadas à mão de
`artigo/tabelas/*.csv`. Enquanto o dado não mudava, a cópia parecia inofensiva.

Em 2026-09-02, 2024 foi recoletado do `.dbc` do DataSUS — 105.669 óbitos que o
CSV do OpenDataSUS não trazia, com 63% de dezembro ausente. **As doze tabelas
passaram a divergir de uma vez, e nenhuma avisou.** Um artigo cujas tabelas
descrevem um dado que não existe mais é pior que um artigo sem tabelas.

`artigo/sincronizar_tabelas.py` passou a regerá-las do CSV, e este teste
transforma a sincronia em regressão: quem regerar os CSVs sem sincronizar o
manuscrito vê vermelho aqui, não numa revisão por pares.

O teste é rápido e não toca rede nem banco: compara texto com CSV.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MANUSCRITO = RAIZ / "artigo" / "manuscrito.md"
SINCRONIZADOR = RAIZ / "artigo" / "sincronizar_tabelas.py"

#: Os manuscritos do repositório. O sincronizador é um só, com `--dir`; a lista
#: existe para que um manuscrito novo entre na regressão ao ser criado, e não no
#: dia em que alguém lembrar.
MANUSCRITOS = ["artigo", "artigo-neoplasias", "artigo-imunopreveniveis"]

pytestmark = pytest.mark.unit


def _ocorrencias(texto: str, alvo: str) -> list[int]:
    fora, i = [], texto.find(alvo)
    while i != -1:
        fora.append(i)
        i = texto.find(alvo, i + 1)
    return fora


@pytest.mark.parametrize("pasta", MANUSCRITOS)
def test_tabelas_do_manuscrito_batem_com_os_csvs(pasta: str) -> None:
    if not (RAIZ / pasta / "manuscrito.md").exists():
        pytest.skip(f"{pasta}/manuscrito.md ausente")
    r = subprocess.run(
        [sys.executable, str(SINCRONIZADOR), "--conferir", "--dir", str(RAIZ / pasta)],
        cwd=RAIZ, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (
        f"alguma tabela de {pasta}/manuscrito.md divergiu do CSV que a gera.\n"
        + (r.stdout or "") + (r.stderr or "")
    )


@pytest.mark.skipif(not MANUSCRITO.exists(), reason="manuscrito ausente")
def test_o_total_de_obitos_e_o_mesmo_no_texto_e_na_tabela() -> None:
    """O número mais citado do artigo aparece na prosa E na Tabela 1.

    Sincronizar a tabela não sincroniza o parágrafo: o total de óbitos é escrito
    à mão em três lugares do texto corrido. Foi um deles que ficou em
    14.378.827 depois da recoleta.
    """
    texto = MANUSCRITO.read_text(encoding="utf-8")
    csv = (RAIZ / "artigo" / "tabelas" / "tabela_1_base.csv").read_text(encoding="utf-8")
    linha = next(x for x in csv.splitlines() if x.startswith("Óbitos não fetais"))
    total = linha.split(",")[1].strip()
    assert total in texto, f"a Tabela 1 diz {total} óbitos e a prosa não repete esse número"
    assert "14.378.827" not in texto, (
        "o total da coleta anterior (14.378.827) ainda aparece no texto. "
        "Ele não tem uso legítimo: era o total com 2024 incompleto."
    )

    # 1.426.346 — o 2024 do CSV — PODE aparecer, e aparece de propósito na §2.2,
    # que explica por que a fonte mudou. O que não pode é aparecer como se fosse
    # o dado corrente. A regra é de contexto: toda ocorrência tem de estar perto
    # da palavra que a qualifica.
    for pos in _ocorrencias(texto, "1.426.346"):
        janela = texto[max(0, pos - 400):pos + 400]
        assert "CSV" in janela, (
            "1.426.346 (o 2024 incompleto do CSV) aparece sem o contexto que o "
            f"qualifica, perto de: …{texto[max(0, pos - 120):pos + 120]}…"
        )


#: Números da prosa que legitimamente NÃO estão em nenhuma tabela, POR
#: MANUSCRITO, com o motivo ao lado. As listas são curtas de propósito: cada
#: item é uma exceção que alguém precisou justificar, e uma lista que cresce sem
#: justificativa devolve a garantia que o teste dá.
#:
#: São por pasta, e não um conjunto só, porque exceção legítima num artigo é
#: buraco no outro: `0,30` é o limiar declarado do artigo de imunopreveníveis e
#: não teria razão nenhuma para ser dispensado no de neoplasias.
DECIMAIS_SEM_TABELA = {
    "artigo-neoplasias": {
        # Valor ERRADO, citado na §2.2 como exemplo da armadilha de padronizar
        # somando só os estratos com óbito. Não pode estar em tabela — é o número
        # que o método corrigiu.
        "29,4",
        # Diferença entre as duas rotas de coleta do SIM para 2024, medida em
        # `scripts/_sim_obitos.py` e citada na §2.1 para justificar a escolha da
        # fonte. Não vem de nenhuma tabela deste artigo, e por acaso coincide com
        # uma célula da Tabela 15 — o que o faria passar pelo motivo errado. Está
        # declarado aqui para que a procedência seja a real.
        "6,9",
    },
    "artigo-imunopreveniveis": {
        # Limiar de nulidade declarado ANTES de olhar o resultado (§2.6):
        # |rho| < 0,30. É parâmetro de decisão, não medida — não sai de tabela
        # nenhuma, e cravá-lo numa seria fingir que foi observado.
        "0,30",
    },
}

#: Os manuscritos submetidos à regra "nenhum número da prosa é digitado".
#:
#: `artigo/` está de fora, e a razão é MEDIDA, não preguiça: pela mesma varredura
#: ele tem 64 números órfãos em 101 citados, herdados de quando era escrito antes
#: de a regra existir. Incluí-lo aqui reprovaria o CI até que 64 valores ganhassem
#: tabela — trabalho legítimo e grande, que não se faz de carona num teste. Até
#: lá ele segue coberto pela regressão de tabelas acima, que é o que sempre teve.
#:
#: Para quem for fazer esse trabalho: mover a pasta para cá é o último passo, não
#: o primeiro, e o teste diz exatamente quais são os 64.
COM_PROCEDENCIA = ["artigo-neoplasias", "artigo-imunopreveniveis"]


@pytest.mark.parametrize("pasta", COM_PROCEDENCIA)
def test_todo_numero_da_prosa_existe_em_alguma_tabela(pasta: str) -> None:
    """Nenhum valor do texto corrido é digitado sem procedência.

    O README dos manuscritos afirma a regra desde sempre e nada a verificava:
    sincronizar a tabela não sincroniza o parágrafo. Foi assim que, no primeiro
    manuscrito, o total de óbitos ficou desatualizado em um dos três lugares em
    que aparece — a tabela estava certa e a frase, não.

    O teste olha as duas formas de número que carregam achado: decimal com
    vírgula (toda taxa, toda razão, todo percentual) e inteiro com separador de
    milhar (toda contagem). Ano, número de seção e ordinal não casam com nenhuma
    das duas e ficam de fora sem precisar de exceção.

    O CASAMENTO É POR NÚMERO, NÃO POR SUBSTRING
    -------------------------------------------
    A primeira versão procurava o número no texto das tabelas com `in`, e por
    isso aprovava `6,9` porque existia um `16,9` em outra tabela. Três valores
    passaram assim — entre eles um `1,4%` que, medido, era `2%`. Uma guarda que
    casa substring aprova justamente o número errado que se parece com um certo.
    Aqui cada célula é decomposta nos números que contém, e a comparação é de
    igualdade.

    A REGRA É DO REPOSITÓRIO, NÃO DE UM ARTIGO
    -------------------------------------------
    O teste nasceu preso a `artigo-neoplasias`. Ele é parametrizado por
    `COM_PROCEDENCIA` pelo mesmo motivo que a lista `MANUSCRITOS` existe: um
    manuscrito novo precisa entrar na regressão no dia em que é criado, e não no
    dia em que alguém lembrar. As exceções passaram a ser por pasta junto, senão
    a dispensa escrita para um artigo abriria buraco em todos.

    O QUE ELE AINDA NÃO PEGA, MEDIDO
    --------------------------------
    A verificação é de PRESENÇA, não de correspondência. Testado por mutação em
    2026-09-04: trocar `4,48` (Tabela 2) por `4,39` reprova, porque `4,39` não
    existe em tabela alguma; trocar por `4,47` **passa**, porque esse valor
    existe — na Tabela 14, sobre outra coisa. Ligar cada citação à sua tabela
    exigiria marcação no texto, e o custo não se paga: o modo de falha real é o
    número que envelhece quando o dado muda, e esse o teste pega.
    """
    manuscrito = RAIZ / pasta / "manuscrito.md"
    if not manuscrito.exists():
        pytest.skip(f"{pasta}/manuscrito.md ausente")
    linhas = manuscrito.read_text(encoding="utf-8").splitlines()
    prosa = [x for x in linhas if not x.startswith("|")]

    numeros_em_tabela: set[str] = set()
    for linha in linhas:
        if linha.startswith("|"):
            for celula in linha.strip().strip("|").split("|"):
                numeros_em_tabela |= set(
                    re.findall(r"\d+(?:\.\d{3})*(?:,\d+)?", celula))

    citados = set()
    for linha in prosa:
        # O DOI é um número com ponto que não é uma contagem: `10.1136/bmjonc`
        # casa com o padrão de separador de milhar e entrava como "10.113".
        # Sai antes da varredura, e não como exceção na lista — a lista é para
        # valores do estudo, não para ruído de sintaxe.
        limpa = re.sub(r"\b10\.\d{4,9}/\S+", " ", linha)
        citados |= set(re.findall(r"\d+(?:\.\d{3})*,\d+", limpa))
        citados |= set(re.findall(r"\d{1,3}(?:\.\d{3})+", limpa))

    dispensados = DECIMAIS_SEM_TABELA.get(pasta, set())
    orfas = sorted((citados - dispensados) - numeros_em_tabela)
    assert not orfas, (
        f"em {pasta}, estes números aparecem na prosa e em nenhuma tabela "
        "do manuscrito: "
        f"{', '.join(orfas)}.\nOu o valor mudou e a frase não acompanhou, ou ele "
        "nunca teve procedência. Se for exceção legítima, acrescente a "
        f"DECIMAIS_SEM_TABELA[{pasta!r}] com o motivo."
    )
