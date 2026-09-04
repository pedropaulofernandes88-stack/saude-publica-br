"""
empacotar.py — o material suplementar do artigo, em um arquivo só
==================================================================

Junta num `.zip` tudo o que é preciso para conferir o artigo sem ter o
repositório: o manuscrito, as dezesseis tabelas, as saídas de análise em grão
mais fino e o código que produz as duas coisas.

POR QUE UM SCRIPT, E NÃO UM ZIP FEITO À MÃO
--------------------------------------------
O primeiro manuscrito do repositório tem um `tabelas-do-artigo.zip` montado uma
vez, sem script. Ele não tem como envelhecer bem: quando os CSVs mudam, o zip
não muda junto, e ninguém percebe porque um zip não reprova em teste. Aqui o
pacote é derivado — se apagar e rodar de novo, sai igual.

Duas propriedades deliberadas:

**Manifesto com SHA-256.** Cada arquivo entra com tamanho, linhas, colunas e
hash. É o mesmo idioma do resto do projeto (o Storage publica Parquet com
SHA-256 ao lado) e serve a quem recebe o pacote fora do git: dá para conferir
que o CSV que se está lendo é o que foi empacotado.

**Data fixa nas entradas.** O zip usa 1980-01-01 para todas as entradas, então
dois empacotamentos do mesmo conteúdo produzem bytes idênticos. Sem isso, o
arquivo mudaria a cada execução só pelo relógio, e um diff de repositório
mostraria alteração onde não houve.

Uso:
  .venv311/Scripts/python artigo-imunopreveniveis/empacotar.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import sys
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[0]
DESTINO = AQUI / "dados-do-artigo.zip"

#: Entradas fixas do zip, na ordem em que aparecem: (caminho no disco, caminho
#: dentro do zip, descrição para o manifesto). Ordem fixa também é o que torna
#: o pacote reprodutível byte a byte.
CONTEUDO: tuple[tuple[Path, str, str], ...] = (
    (AQUI / "manuscrito.md",   "manuscrito/manuscrito.md",   "O manuscrito, em Markdown — é a fonte"),
    (AQUI / "manuscrito.html", "manuscrito/manuscrito.html", "O manuscrito renderizado, autocontido"),
    (AQUI / "manuscrito.pdf",  "manuscrito/manuscrito.pdf",  "O manuscrito em PDF"),
    (ROOT / "scripts" / "analise_mortes_imunopreveniveis.py",
     "codigo/analise_mortes_imunopreveniveis.py",
     "As listas de CID-10, a derivação do óbito e as guardas"),
    (AQUI / "gerar_tabelas.py", "codigo/gerar_tabelas.py",
     "Formata as dezesseis tabelas do artigo a partir do microdado"),
    (ROOT / "scripts" / "_sim_obitos.py", "codigo/_sim_obitos.py",
     "A definição compartilhada de óbito no SIM, importada pelos dois anteriores"),
)

#: Descrição de cada tabela do artigo. Sem isto o pacote seria dezesseis nomes
#: de arquivo e nenhum sentido — quem recebe não tem o manuscrito aberto ao lado.
TABELAS = {
    "tabela_1_base.csv": "Tabela 1 — a base analisada e as guardas",
    "tabela_2_codigos_subgrupo_1_1.csv": "Tabela 2 — os códigos do subgrupo 1.1, por versão etária",
    "tabela_3_subgrupo_1_1_por_ano.csv": "Tabela 3 — óbitos do subgrupo 1.1 por ano",
    "tabela_4_panorama.csv": "Tabela 4 — panorama dos conjuntos comparados",
    "tabela_5_estrutura_etaria.csv": "Tabela 5 — estrutura etária dos óbitos por causas com vacina",
    "tabela_6_composicao_subgrupo_1_1.csv": "Tabela 6 — composição interna do subgrupo 1.1",
    "tabela_7_ampliado_por_causa.csv": "Tabela 7 — o conjunto ampliado, causa a causa",
    "tabela_8_eventos_serie_anual.csv": "Tabela 8 — febre amarela, sarampo e coqueluche, série anual",
    "tabela_9_febre_amarela_uf.csv": "Tabela 9 — febre amarela 2017–2018 por unidade da federação",
    "tabela_10_influenza_por_faixa.csv": "Tabela 10 — óbitos por influenza, por faixa etária",
    "tabela_11_covid_por_faixa.csv": "Tabela 11 — óbitos por COVID-19, por faixa etária",
    "tabela_12_teto_codificacao.csv": "Tabela 12 — presença de agente etiológico na causa básica",
    "tabela_13_razoes_de_especificidade.csv": "Tabela 13 — razões entre código inespecífico e específico",
    "tabela_14_influenza_doses_uf.csv": "Tabela 14 — o cruzamento ecológico, dado por unidade da federação",
    "tabela_15_correlacao_por_ano.csv": "Tabela 15 — correlação de Spearman por ano",
    "tabela_16_latencia_longa.csv": "Tabela 16 — causas de latência longa, fora de qualquer total",
}

#: As saídas da análise. Grão diferente do das tabelas do artigo: elas são o que
#: o script de análise imprime, sem recorte de página.
ANALISE = {
    "imunopreveniveis_lista_oficial_por_ano.csv": "Subgrupo 1.1 por ano, com o total de óbitos do ano",
    "imunopreveniveis_ampliado_por_causa_ano.csv": "Conjunto ampliado e latência longa, ano a ano, 2015–2025",
    "imunopreveniveis_estrutura_etaria.csv": "Óbitos por faixa etária e conjunto",
    "imunopreveniveis_teto_codificacao.csv": "Óbitos por código inespecífico e específico",
    "imunopreveniveis_febre_amarela.csv": "Febre amarela por ano e unidade da federação",
    "imunopreveniveis_sarampo.csv": "Sarampo por ano, com menores de 1 ano e unidades atingidas",
    "imunopreveniveis_coqueluche.csv": "Coqueluche por ano, com menores de 1 ano",
    "imunopreveniveis_influenza_por_idade.csv": "Influenza por ano e faixa etária",
    "imunopreveniveis_covid_pos_vacina.csv": "COVID-19 por ano e faixa etária, a partir de 2021",
    "imunopreveniveis_influenza_x_doses_uf.csv": "Cruzamento influenza × doses por unidade da federação",
}

LEIA_ME = """# Material suplementar

**Óbitos por doenças imunopreveníveis no Brasil, 2015–2024: um instrumento
oficial que descreve o calendário vacinal de 2010**

Pedro Paulo Fernandes · Saúde em Dado — saudeemdado.com

---

## O que há neste pacote

| pasta | conteúdo |
|---|---|
| `manuscrito/` | o artigo em Markdown, HTML e PDF |
| `tabelas/` | as dezesseis tabelas do artigo, em CSV |
| `analise/` | as saídas do script de análise, em grão mais fino |
| `codigo/` | os três arquivos Python que produzem tudo o que está aqui |
| `MANIFESTO.csv` | tamanho, linhas, colunas e SHA-256 de cada arquivo |

Todos os CSV estão em UTF-8, com vírgula como separador de campo e ponto como
separador decimal — o formato de máquina. As tabelas **do manuscrito** aparecem
lá com a formatação de leitura brasileira (ponto no milhar, vírgula no decimal);
os CSV daqui são a fonte, não a página.

## Como reproduzir

O pacote é derivado de microdados públicos, e os três scripts de `codigo/` são
o caminho inteiro. Eles esperam os arquivos do SIM em `data/raw/SIM` — os
`.dbc` por unidade da federação do FTP do DataSUS para 2015–2021, 2024 e 2025,
e os CSV nacionais do OpenDataSUS para 2022 e 2023.

```
python scripts/analise_mortes_imunopreveniveis.py
python artigo-imunopreveniveis/gerar_tabelas.py
```

O segundo não depende do primeiro: ele reagrega o microdado por conta própria,
importando as listas de CID-10 e a derivação do óbito do primeiro. É deliberado
— ler um CSV já gravado faria o artigo descrever, sem avisar, um dado que
poderia ter mudado.

## O que os números são, e o que não são

As contagens deste artigo são de **óbitos cuja causa básica é uma doença com
vacina disponível**. Não são mortes evitáveis: faltam a eficácia vacinal, que
nunca é total, e a situação vacinal de quem morreu, que o SIM não registra.
Todo total é um teto, e a §4.4 do manuscrito lista as demais limitações.

## Fontes

Todas de domínio público:

- Sistema de Informações sobre Mortalidade (SIM) — DataSUS e OpenDataSUS
- Programa Nacional de Imunizações (PNI/RNDS) — OpenDataSUS
- Estimativas populacionais e Censo 2022 — IBGE
- Lista Brasileira de Causas de Mortes Evitáveis — notas técnicas do
  TabNet/DataSUS: `Obitos_Evitaveis_0_a_4_anos.pdf` e
  `Obitos_Evitaveis_5_a_74_anos.pdf`

Nenhum dado individual é publicado — apenas agregados.

## Licença

Código sob licença MIT, como o restante do repositório. Tabelas e texto podem
ser reutilizados com citação. Ao usar, cite também as fontes primárias acima.
"""


def _perfil(dados: bytes, nome: str) -> tuple[str, str, str]:
    """Linhas e colunas de um CSV; vazio para o que não é CSV."""
    sha = hashlib.sha256(dados).hexdigest()
    if not nome.endswith(".csv"):
        return "", "", sha
    linhas = list(csv.reader(io.StringIO(dados.decode("utf-8"))))
    corpo = [x for x in linhas if x]
    return str(max(0, len(corpo) - 1)), str(len(corpo[0]) if corpo else 0), sha


def main() -> None:
    itens: list[tuple[str, bytes, str]] = []

    for origem, destino, descricao in CONTEUDO:
        if not origem.exists():
            raise SystemExit(
                f"{origem} não existe. Rode `gerar_tabelas.py` e "
                "`artigo/renderizar.py artigo-imunopreveniveis` antes de empacotar — "
                "pacote com arquivo faltando é pior que pacote nenhum, porque parece completo.")
        itens.append((destino, origem.read_bytes(), descricao))

    for pasta, mapa, prefixo in ((AQUI / "tabelas", TABELAS, "tabelas"),
                                 (ROOT / "data" / "analises", ANALISE, "analise")):
        presentes = {p.name for p in pasta.glob("*.csv")}
        faltando = sorted(set(mapa) - presentes)
        if faltando:
            raise SystemExit(f"faltam em {pasta}: {', '.join(faltando)}")
        for nome, descricao in mapa.items():
            itens.append((f"{prefixo}/{nome}", (pasta / nome).read_bytes(), descricao))

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

    print(f"[zip] {DESTINO.name} — {len(itens)} arquivos, "
          f"{DESTINO.stat().st_size / 1024:.0f} kB", flush=True)
    print(f"[sha] {hashlib.sha256(DESTINO.read_bytes()).hexdigest()}", flush=True)


if __name__ == "__main__":
    main()
