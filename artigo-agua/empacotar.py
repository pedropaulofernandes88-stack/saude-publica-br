"""
empacotar.py — o pacote que acompanha o manuscrito da água
===========================================================

    .venv311/Scripts/python artigo-agua/empacotar.py

Produz `artigo-agua/dados-hidricas.zip`: as dezesseis tabelas, as nove figuras,
o manuscrito e o código que produz as três coisas — o do desenho transversal e o
da reanálise em painel, que é a análise primária da versão atual.

POR QUE UM SCRIPT, E NÃO UM ZIP FEITO À MÃO
--------------------------------------------
Zip montado uma vez não envelhece bem: quando os CSVs mudam, ele não muda junto,
e ninguém percebe porque zip não reprova em teste. Aqui o pacote é derivado — se
apagar e rodar de novo, sai igual.

**Manifesto com SHA-256.** Cada arquivo entra com tamanho, linhas, colunas e
hash. É o idioma do resto do projeto, e serve a quem recebe o pacote fora do
git: dá para conferir que o CSV que se está lendo é o que foi empacotado.

**Datas fixas nas entradas.** O zip é reprodutível byte a byte: duas execuções
sobre os mesmos arquivos produzem o mesmo hash. Sem isso o carimbo de tempo
mudaria o SHA a cada execução, e o manifesto perderia a função.

ABORTA EM VEZ DE EMPACOTAR PELA METADE
---------------------------------------
Falta de tabela ou de figura interrompe. Pacote incompleto é pior que pacote
nenhum, porque parece completo para quem recebe.
"""
from __future__ import annotations

import csv
import hashlib
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "artigo"))
from _conferir_imports import conferir, conferir_derivados  # noqa: E402

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
#: O nome do zip carrega o assunto pela mesma razão do .docx: os dois
#: artigos são anexados no mesmo e-mail, e dois "dados-do-artigo.zip"
#: chegam como um deles e uma cópia numerada.
DESTINO = AQUI / "dados-hidricas.zip"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: As tabelas e as figuras, por NOME e não por contagem.
#:
#: A versão anterior conferia `len(...) == 11` e `len(...) == 5`. Contagem não
#: distingue os casos que importam: renomear uma tabela mantém a contagem, e um
#: PNG de uma versão anterior que ninguém apagou entra no pacote com a mesma
#: aparência de arquivo atual — e a contagem passa a reprovar o conjunto certo.
#: Declarar os nomes faz a guarda dizer QUAL arquivo falta, e acusar sobra.
TABELAS_ESPERADAS = {
    # o desenho transversal, agora reportado como descrição
    "tabela_1_base.csv", "tabela_2_serie_anual.csv",
    "tabela_3_alta_por_faixa.csv", "tabela_4_alta_por_codigo.csv",
    "tabela_5_teste_codificacao.csv", "tabela_6_exposicao.csv",
    "tabela_7_gradiente.csv", "tabela_8_criterios.csv",
    "tabela_9_rrr_por_idade.csv", "tabela_10_sem_vigilancia_por_uf.csv",
    "tabela_11_por_quartil_de_acesso.csv",
    # a reanálise em painel, que é a análise primária
    "tabela_p1_painel.csv", "tabela_p2_especificidade.csv",
    "tabela_p3_efeito_fixo.csv", "tabela_p4_tendencia.csv",
    "tabela_p5_robustez.csv",
    # a extensao microbiologica, condicional a reportar
    "tabela_e1_painel.csv", "tabela_e2_especificidade.csv",
    "tabela_e3_efeito_fixo.csv", "tabela_e4_intensidade.csv",
    "tabela_e5_robustez.csv",
}
FIGURAS_ESPERADAS = {
    "figura_01_serie_nacional.png", "figura_02_alta_por_faixa.png",
    "figura_03_gradiente.png", "figura_04_criterios.png",
    "figura_05_rrr_por_idade.png",
    "figura_p1_especificidade.png", "figura_p2_com_e_sem_efeito_fixo.png",
    "figura_p3_tendencia.png", "figura_p4_robustez.png",
    "figura_e1_ecoli.png",
}

#: O que entra além das tabelas e figuras, e como se chama no pacote.
CONTEUDO = [
    (AQUI / "manuscrito.md", "manuscrito.md", "O manuscrito, em Markdown"),
    (AQUI / "manuscrito-hidricas.docx", "manuscrito-hidricas.docx",
     "O manuscrito em Word, SEM identificação de autoria, com as figuras no corpo e as tabelas como material suplementar"),
    (ROOT / "scripts" / "analise_agua_mortalidade.py",
     "codigo/analise_agua_mortalidade.py",
     "A análise: critérios declarados no cabeçalho, e as onze tabelas"),
    (AQUI / "gerar_tabelas.py", "codigo/gerar_tabelas.py",
     "Reexecuta a análise e formata as tabelas do artigo"),
    (AQUI / "gerar_figuras.py", "codigo/gerar_figuras.py",
     "Desenha as cinco figuras do desenho transversal"),
    (ROOT / "scripts" / "analise_agua_painel.py",
     "codigo/analise_agua_painel.py",
     "A ANÁLISE PRIMÁRIA: painel de efeitos fixos de município, exposição defasada, quatro critérios declarados no cabeçalho"),
    (ROOT / "scripts" / "analise_agua_ecoli.py", "codigo/analise_agua_ecoli.py",
     "A EXTENSAO MICROBIOLOGICA: deteccao de E. coli como exposicao, condicional a reportar, com os quatro criterios no cabecalho"),
    (ROOT / "scripts" / "_poisson_fe.py", "codigo/_poisson_fe.py",
     "O estimador de Poisson condicional de efeitos fixos, com o autoteste de recuperação"),
    (AQUI / "gerar_tabelas_painel.py", "codigo/gerar_tabelas_painel.py",
     "Transporta as cinco tabelas do painel, conferindo as colunas que o texto cita"),
    (AQUI / "gerar_figuras_painel.py", "codigo/gerar_figuras_painel.py",
     "Desenha as quatro figuras do painel"),
    (ROOT / "data" / "refs" / "Obitos_Evitaveis_5_a_74_anos.pdf",
     "referencia/Obitos_Evitaveis_5_a_74_anos.pdf",
     "Nota técnica do TabNet/DataSUS com a Lista Brasileira (5 a 74 anos)"),
]

LEIA_ME = """# Mortes evitáveis por doença infecciosa intestinal no Brasil, 2015–2024

Pacote de dados, figuras e código do manuscrito.

## O que tem aqui

    manuscrito.md            o texto
    tabelas/                 as dezesseis tabelas, em CSV: onze do desenho
                             transversal (tabela_N) e cinco do painel (tabela_pN)
    figuras/                 as nove figuras, em PNG a 300 dpi
    codigo/                  as duas análises, o estimador e os quatro geradores
    referencia/              a nota técnica oficial da Lista Brasileira
    MANIFESTO.csv            inventário com SHA-256 de cada arquivo

## Como reproduzir

    python codigo/analise_agua_painel.py          # a análise PRIMÁRIA (~30 min)
    python codigo/gerar_tabelas_painel.py         # transporta as tabelas do painel
    python codigo/gerar_figuras_painel.py         # desenha as figuras do painel
    python codigo/analise_agua_mortalidade.py     # o desenho transversal
    python codigo/gerar_tabelas.py                # formata para o artigo
    python codigo/gerar_figuras.py                # redesenha as figuras

As análises reexecutam a partir dos marts publicados do projeto. Os critérios de
refutação estão escritos no cabeçalho de cada script, antes de qualquer
resultado. No transversal, o quarto está rotulado como **post-hoc** porque foi
concebido depois de observar os dados.

## O que este desenho NÃO autoriza

É ecológico. A unidade é o município, e nada aqui autoriza afirmar que a pessoa
que morreu consumiu água não vigiada. E ausência de registro de vigilância não é
água contaminada: é ausência da prova.

Além disso, a leitura causal está **refutada pelos próprios dados**: o painel de
efeitos fixos não reproduz a associação que o desenho transversal mede. As onze
tabelas do transversal ficam no pacote como descrição, e não como evidência de
efeito. O que elas documentam está na §4 do manuscrito.
"""


def _perfil(dados: bytes, nome: str) -> tuple[str, str, str]:
    """Linhas, colunas e SHA-256. Linhas e colunas só fazem sentido em CSV."""
    sha = hashlib.sha256(dados).hexdigest()
    if not nome.endswith(".csv"):
        return "", "", sha
    texto = dados.decode("utf-8", errors="replace").strip().split("\n")
    return str(len(texto) - 1), str(len(texto[0].split(","))) if texto else "", sha


def main() -> None:
    itens: list[tuple[str, bytes, str]] = []

    for origem, destino, descricao in CONTEUDO:
        if not origem.exists():
            raise SystemExit(
                f"{origem} não existe. Pacote com arquivo faltando é pior que "
                "pacote nenhum, porque parece completo.")
        itens.append((destino, origem.read_bytes(), descricao))

    for pasta, esperado, gerador, descricao in (
            ("tabelas", TABELAS_ESPERADAS,
             "gerar_tabelas.py e gerar_tabelas_painel.py",
             "Tabela do manuscrito"),
            ("figuras", FIGURAS_ESPERADAS,
             "gerar_figuras.py e gerar_figuras_painel.py",
             "Figura do manuscrito (PNG, 300 dpi)")):
        achados = {p.name for p in (AQUI / pasta).glob("*")}
        faltam = sorted(esperado - achados)
        sobram = sorted(achados - esperado)
        if faltam or sobram:
            raise SystemExit(
                f"o conteúdo de {pasta}/ não é o que o manuscrito cita.\n"
                + (f"  faltam: {faltam}\n" if faltam else "")
                + (f"  sobram: {sobram}\n" if sobram else "")
                + f"Rode `{gerador}`. Sobra importa tanto quanto falta: "
                "arquivo de uma versão anterior entra no pacote com a mesma "
                "aparência de arquivo atual.")
        for nome in sorted(esperado):
            itens.append((f"{pasta}/{nome}",
                          (AQUI / pasta / nome).read_bytes(), descricao))

    # O pacote tem de conter o que os seus proprios scripts importam.
    conferir(itens, DESTINO.name)
    conferir_derivados(itens, AQUI / "manuscrito.md", DESTINO.name)

    manifesto = io.StringIO()
    w = csv.writer(manifesto, lineterminator="\n")
    w.writerow(["arquivo", "descricao", "bytes", "linhas", "colunas", "sha256"])
    for destino, dados, descricao in itens:
        linhas, colunas, sha = _perfil(dados, destino)
        w.writerow([destino, descricao, len(dados), linhas, colunas, sha])

    itens.insert(0, ("LEIA-ME.md", LEIA_ME.encode("utf-8"), "Este arquivo"))
    itens.insert(1, ("MANIFESTO.csv", manifesto.getvalue().encode("utf-8"),
                     "Inventário com SHA-256 de cada arquivo"))

    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for destino, dados, _ in itens:
            info = zipfile.ZipInfo(destino, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, dados)

    tamanho = DESTINO.stat().st_size
    print(f"[zip] {DESTINO.name} — {len(itens)} arquivos, {tamanho // 1024} kB")
    print(f"[sha] {hashlib.sha256(DESTINO.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
