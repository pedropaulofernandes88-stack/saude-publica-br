"""
gerar_tabelas.py — as quinze tabelas do artigo sobre mortalidade por câncer
===========================================================================

Nenhum número do manuscrito é digitado. Cada tabela sai daqui, e daqui sai de
`scripts/analise_neoplasias.py`, que é o único lugar onde as taxas são
calculadas. É a mesma disciplina de `artigo/gerar_tabelas.py` e pela mesma
razão: prosa não tem quem a contradiga, e por isso envelhece em silêncio.

POR QUE ESTE SCRIPT RECALCULA EM VEZ DE LER O QUE ESTÁ EM DISCO
---------------------------------------------------------------
Ele **executa a análise** antes de formatar (a menos que se passe
`--sem-recalcular`). A alternativa — ler os CSVs que já estão em
`data/analises/neoplasias/` — parece equivalente e não é: bastaria alguém
recoletar o SIM e esquecer de rodar a análise para o artigo passar a descrever
um dado que não existe mais, sem que nada avisasse. Foi exatamente o que
aconteceu no primeiro manuscrito quando 2024 foi recoletado do `.dbc`: doze
tabelas divergiram de uma vez, em silêncio (ver `tests/test_manuscrito.py`).

Recalcular custa cerca de 40 segundos e remove a classe inteira de defeito.
`--sem-recalcular` existe para iterar formatação, não para gerar entrega.

O QUE ESTE SCRIPT FAZ, ENTÃO
-----------------------------
Traduz: nomes de coluna em português, rótulos legíveis no lugar de códigos,
recorte de linhas quando a tabela inteira não caberia na página. Nenhuma conta
nova — se aparecer uma divisão aqui, ela está no lugar errado.

Uso:
  .venv311/Scripts/python artigo-neoplasias/gerar_tabelas.py
  .venv311/Scripts/python artigo-neoplasias/gerar_tabelas.py --sem-recalcular
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
FONTE = ROOT / "data" / "analises" / "neoplasias"
SAIDA = Path(__file__).resolve().parent / "tabelas"
sys.path.insert(0, str(ROOT / "scripts"))

#: Rótulo legível para as faixas etárias, que no dado são chaves de ordenação.
FAIXA = {"0-4": "0 a 4", "5-14": "5 a 14", "15-29": "15 a 29", "30-44": "30 a 44",
         "45-59": "45 a 59", "60-74": "60 a 74", "75+": "75 ou mais"}

#: Nome do sítio para a página, escrito à mão. A descrição que vem do DataSUS é
#: abreviada e SEM ACENTO — "Neopl malig do estomago", "Neopl malig do colo do
#: utero" —, e numa tabela de neoplasias o prefixo ainda repete o assunto da
#: tabela. Tirar o prefixo por expressão regular resolve metade e deixa a outra:
#: "utero" e "esofago" continuariam sem acento numa página em português.
#:
#: Por isso é um mapa explícito e não uma regra. O custo é ter de acrescentar uma
#: linha quando um sítio novo entrar em alguma tabela; o `_sitio` levanta nesse
#: caso, em vez de imprimir a abreviação do DataSUS na página sem avisar.
SITIOS = {
    "C15": "Esôfago", "C16": "Estômago", "C18": "Cólon", "C20": "Reto",
    "C22": "Fígado e vias biliares intra-hepáticas",
    "C24": "Outras partes das vias biliares", "C25": "Pâncreas",
    "C26": "Outros órgãos digestivos e mal definidos", "C32": "Laringe",
    "C34": "Brônquios e pulmões", "C41": "Ossos e cartilagens articulares",
    "C44": "Outras neoplasias malignas da pele", "C50": "Mama",
    "C53": "Colo do útero", "C56": "Ovário", "C61": "Próstata", "C64": "Rim",
    "C67": "Bexiga", "C71": "Encéfalo",
    "C72": "Medula espinhal e outros do sistema nervoso central",
    "C74": "Glândula suprarrenal",
    "C76": "Outras localizações e mal definidas",
    "C80": "Sem especificação de localização",
    "C85": "Linfoma não-Hodgkin", "C90": "Mieloma múltiplo",
    "C91": "Leucemia linfoide", "C92": "Leucemia mieloide",
}

#: Nenhuma tabela é truncada: a maior tem 27 linhas (as unidades da federação) e
#: cabe na página. A constante existe para o dia em que alguma precise ser
#: recortada — com o critério escrito ao lado, em vez de um `head(10)` solto no
#: meio do código, que é como um recorte vira achado sem que ninguém perceba.
SEM_RECORTE = "todas as linhas cabem na página; nenhuma tabela é truncada"


def _ler(nome: str) -> pd.DataFrame:
    caminho = FONTE / f"{nome}.csv"
    if not caminho.exists():
        raise SystemExit(
            f"{caminho.relative_to(ROOT).as_posix()} não existe. Rode "
            "`python scripts/analise_neoplasias.py` — ou este script sem "
            "`--sem-recalcular`, que o faz por você.")
    return pd.read_csv(caminho)


def _grava(df: pd.DataFrame, nome: str, titulo: str) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA / f"{nome}.csv", index=False, encoding="utf-8-sig")
    print(f"[tabela] {nome}: {len(df)} linhas — {titulo}", flush=True)


def _sitio(cid: str) -> str:
    """Nome do sítio na página, a partir da categoria da CID-10.

    Levanta em código desconhecido de propósito: cair no rótulo do DataSUS
    imprimiria "Neopl malig do estomago" numa página em português, e ninguém
    revisa o que não quebrou.
    """
    if cid not in SITIOS:
        raise SystemExit(f"CID {cid} entrou em alguma tabela e não tem nome em "
                         "SITIOS (artigo-neoplasias/gerar_tabelas.py). "
                         "Acrescente a linha antes de gerar o artigo.")
    return SITIOS[cid]


def _pt(valor: float, casas: int = 1) -> str:
    """Número no padrão do texto em português, para dentro de célula composta."""
    return f"{valor:,.{casas}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def tabela_1_base() -> pd.DataFrame:
    return _ler("tab00_base")


def tabela_2_serie() -> pd.DataFrame:
    """Série nacional com as duas colunas de qualidade do registro ao lado.

    As colunas de registro não são contexto: o degrau de 2020 na taxa
    padronizada seria trivialmente explicado por piora de codificação, e é a
    série de causa mal definida — que CAI no período — que descarta essa
    hipótese. Argumento que depende de número traz o número na mesma tabela.
    """
    d = _ler("tab01_serie_nacional")
    return pd.DataFrame({
        "Ano": d.ano,
        "Óbitos": d.obitos.astype(int),
        "População": d.populacao.astype(int),
        "Taxa bruta": d.taxa_bruta_100k,
        "Taxa padronizada": d.taxa_padronizada_100k,
        "% causa mal definida": d.pct_causa_mal_definida,
        "% C80 entre os cânceres": d.pct_c80_entre_neoplasias,
    })


def tabela_3_faixa() -> pd.DataFrame:
    """Taxa específica nos dois extremos da série, com a variação entre eles.

    Mostrar os dez anos por faixa seriam setenta linhas para um achado que se lê
    em duas colunas. A série completa por faixa fica no CSV da análise.
    """
    d = _ler("tab02_taxa_por_faixa_ano")
    a, b = d.ano.min(), d.ano.max()
    ini = d[d.ano == a].set_index("faixa_etaria")
    fim = d[d.ano == b].set_index("faixa_etaria")
    fx = [f for f in FAIXA if f in ini.index]
    return pd.DataFrame({
        "Faixa etária": [FAIXA[f] for f in fx],
        f"Óbitos {b}": [int(fim.obitos[f]) for f in fx],
        f"Taxa {a}": [ini.taxa_100k[f] for f in fx],
        f"Taxa {b}": [fim.taxa_100k[f] for f in fx],
        "Variação (%)": [round(100 * (fim.taxa_100k[f] / ini.taxa_100k[f] - 1), 1)
                         for f in fx],
    })


def tabela_4_decomposicao() -> pd.DataFrame:
    d = _ler("tab03_decomposicao")
    return pd.DataFrame({
        "Componente": d.componente.str.capitalize(),
        "Óbitos": d.obitos.astype(int),
        "% da variação": d.pct_da_variacao,
    })


def tabela_5_contrafactual() -> pd.DataFrame:
    d = _ler("tab04_contrafactual_2019")
    total = pd.DataFrame([{
        "Ano": "2020–2024",
        "Observado": int(d.obitos_observados.sum()),
        "Esperado (risco de 2019)": int(d.obitos_esperados_taxa_2019.sum()),
        "Diferença": int(d.diferenca.sum()),
        "%": round(100 * d.diferenca.sum() / d.obitos_esperados_taxa_2019.sum(), 1),
    }])
    anos = pd.DataFrame({
        "Ano": d.ano.astype(str),
        "Observado": d.obitos_observados.astype(int),
        "Esperado (risco de 2019)": d.obitos_esperados_taxa_2019.astype(int),
        "Diferença": d.diferenca.astype(int),
        "%": d.pct,
    })
    return pd.concat([anos, total], ignore_index=True)


def tabela_6_sitios_faixa() -> pd.DataFrame:
    """Os três sítios mais letais de cada faixa, um por coluna.

    A forma longa (uma linha por sítio) tem 21 linhas e obriga o leitor a
    reconstruir o ranking mentalmente. A forma larga põe o gradiente etário na
    vertical, que é onde ele se lê.
    """
    d = _ler("tab05_sitios_por_faixa")
    d = d[d.posicao <= 3]
    linhas = []
    for f in FAIXA:
        c = d[d.faixa_etaria == f].sort_values("posicao")
        if c.empty:
            continue
        linha = {"Faixa etária": FAIXA[f]}
        for _, r in c.iterrows():
            linha[f"{int(r.posicao)}º sítio"] = (
                f"{r.causabas_3} {_sitio(r.causabas_3)} "
                f"({_pt(r.obitos, 0)}; {_pt(r.pct_da_faixa)}%)")
        linhas.append(linha)
    return pd.DataFrame(linhas)


def tabela_7_sitios_sexo() -> pd.DataFrame:
    d = _ler("tab06_sitios_por_sexo")
    f = d[d.sexo == "F"].sort_values("posicao").reset_index(drop=True)
    m = d[d.sexo == "M"].sort_values("posicao").reset_index(drop=True)
    return pd.DataFrame({
        "Posição": f.posicao.astype(int),
        "Mulheres": [f"{r.causabas_3} {_sitio(r.causabas_3)}" for r in f.itertuples()],
        "Óbitos (F)": f.obitos.astype(int),
        "% (F)": f.pct_do_sexo,
        "Homens": [f"{r.causabas_3} {_sitio(r.causabas_3)}" for r in m.itertuples()],
        "Óbitos (M)": m.obitos.astype(int),
        "% (M)": m.pct_do_sexo,
    })


def tabela_8_uf() -> pd.DataFrame:
    d = _ler("tab07_uf")
    return pd.DataFrame({
        "UF": d.uf_sigla,
        "Óbitos": d.obitos.astype(int),
        "Taxa bruta": d.taxa_bruta_100k,
        "Taxa padronizada": d.taxa_padronizada_100k,
        "Colo do útero (padr.)": d.taxa_padr_colo_utero_100k,
    })


def tabela_9_vulnerabilidade() -> pd.DataFrame:
    d = _ler("tab08_vulnerabilidade")
    rotulo = {"Q1": "Q1 (menos vulnerável)", "Q2": "Q2", "Q3": "Q3",
              "Q4": "Q4 (mais vulnerável)"}
    return pd.DataFrame({
        "Quartil": d.quartil_ivs.map(rotulo),
        "Óbitos por câncer": d.obitos_neoplasia.astype(int),
        "Taxa padronizada": d.taxa_padronizada_100k,
        "Taxa corrigida": d.taxa_padr_corrigida_100k,
        "% causa mal definida": d.pct_causa_mal_definida,
        "% dos óbitos por câncer": d.pct_obitos_por_neoplasia,
    })


def tabela_10_sitio_vulnerabilidade() -> pd.DataFrame:
    d = _ler("tab09_sitio_por_vulnerabilidade")
    return pd.DataFrame({
        "CID": d.causabas_3,
        "Sítio": d.causabas_3.map(_sitio),
        "Óbitos": d.obitos.astype(int),
        "Taxa Q1": d.taxa_Q1_menos_vulneravel,
        "Taxa Q4": d.taxa_Q4_mais_vulneravel,
        "Razão Q4/Q1": d.razao_Q4_Q1,
    })


def tabela_11_raca() -> pd.DataFrame:
    d = _ler("tab10_raca")
    return pd.DataFrame({
        "Cor ou raça": d.raca,
        "Óbitos": d.obitos.astype(int),
        "Taxa bruta": d.taxa_bruta_100k,
        "Taxa padronizada": d.taxa_padronizada_100k,
        "IC95%": [f"{_pt(a, 1)}–{_pt(b, 1)}" for a, b in zip(d.ic95_inf, d.ic95_sup,
                                                             strict=True)],
    })


def tabela_12_sitio_raca() -> pd.DataFrame:
    """Sítio × cor/raça na forma longa, com contagem e intervalo.

    A primeira versão era um cruzamento largo — cinco colunas de taxa e uma de
    razão —, e escondia o que decide se há achado: **quantas mortes** sustentam
    cada célula. O câncer de cólon entre pessoas indígenas vinha de 28 óbitos e
    aparecia com a mesma tipografia dos 18.904 de brancas.

    A forma longa cabe em 25 linhas e traz as três coisas juntas: taxa,
    contagem e intervalo de Fay–Feuer. Perde a leitura do gradiente na
    horizontal, que a prosa faz.
    """
    d = _ler("tab11_sitio_por_raca")
    return pd.DataFrame({
        "Sítio": d.sitio,
        "Cor ou raça": d.raca,
        "Óbitos": d.obitos.astype(int),
        "Taxa padronizada": d.taxa_padronizada_100k,
        "IC95%": [f"{_pt(a, 2)}–{_pt(b, 2)}" for a, b in zip(d.ic95_inf, d.ic95_sup,
                                                             strict=True)],
    })


def tabela_13_escolaridade() -> pd.DataFrame:
    d = _ler("tab12_escolaridade_30_69")
    return pd.DataFrame({
        "Escolaridade": d.escolaridade.str.replace(r"^\d ", "", regex=True),
        "Óbitos (todas as causas)": d.obitos_totais.astype(int),
        "% por câncer": d.pct_obitos_por_neoplasia,
        "% causa mal definida": d.pct_causa_mal_definida,
        "% em hospital": d.pct_neo_morre_em_hospital,
        "% em domicílio": d.pct_neo_morre_em_domicilio,
    })


def tabela_14_raca_acesso() -> pd.DataFrame:
    d = _ler("tab13_raca_acesso_30_69")
    return pd.DataFrame({
        "Cor ou raça": d.raca,
        "Óbitos por câncer": d.obitos_neoplasia.astype(int),
        "% por câncer": d.pct_obitos_por_neoplasia,
        "% em hospital": d.pct_morre_em_hospital,
        "% em domicílio": d.pct_morre_em_domicilio,
        "% causa mal definida": d.pct_causa_mal_definida,
        "% C80 entre os cânceres": d.pct_c80_entre_neoplasias,
    })


def tabela_15_local_obito() -> pd.DataFrame:
    d = _ler("tab14_local_obito_por_faixa")
    return pd.DataFrame({
        "Faixa etária": d.faixa_etaria.map(FAIXA),
        "Óbitos por câncer": d.obitos_neoplasia.astype(int),
        "% em hospital": d.pct_hospital,
        "% em domicílio": d.pct_domicilio,
        "% em outros locais": d.pct_outros,
    })


TABELAS = [
    ("tabela_1_base", "enquadramento do estudo", tabela_1_base),
    ("tabela_2_serie_nacional", "série nacional 2015–2024", tabela_2_serie),
    ("tabela_3_taxa_por_faixa", "taxa específica por faixa etária", tabela_3_faixa),
    ("tabela_4_decomposicao", "decomposição do aumento", tabela_4_decomposicao),
    ("tabela_5_contrafactual", "observado contra o risco de 2019", tabela_5_contrafactual),
    ("tabela_6_sitios_por_faixa", "sítios mais letais por faixa", tabela_6_sitios_faixa),
    ("tabela_7_sitios_por_sexo", "sítios mais letais por sexo", tabela_7_sitios_sexo),
    ("tabela_8_uf", "taxa padronizada por UF", tabela_8_uf),
    ("tabela_9_vulnerabilidade", "quartil de vulnerabilidade municipal",
     tabela_9_vulnerabilidade),
    ("tabela_10_sitio_por_vulnerabilidade", "razão Q4/Q1 por sítio",
     tabela_10_sitio_vulnerabilidade),
    ("tabela_11_raca", "taxa padronizada por cor/raça", tabela_11_raca),
    ("tabela_12_sitio_por_raca", "sítio por cor/raça", tabela_12_sitio_raca),
    ("tabela_13_escolaridade", "escolaridade, 30 a 69 anos", tabela_13_escolaridade),
    ("tabela_14_raca_acesso", "cor/raça, acesso e registro, 30 a 69 anos",
     tabela_14_raca_acesso),
    ("tabela_15_local_obito", "local do óbito por faixa etária", tabela_15_local_obito),
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Gera as tabelas do manuscrito.")
    ap.add_argument("--sem-recalcular", action="store_true",
                    help="usa os CSVs já em data/analises/neoplasias/ — para "
                         "iterar formatação, nunca para gerar entrega")
    if not ap.parse_args().sem_recalcular:
        import analise_neoplasias
        print("[analise] recalculando de scripts/analise_neoplasias.py…", flush=True)
        analise_neoplasias.main()
        print()

    for nome, titulo, fn in TABELAS:
        _grava(fn(), nome, titulo)
    _empacotar()
    print(f"\n[done] {len(TABELAS)} tabelas em "
          f"{SAIDA.relative_to(ROOT).as_posix()} — {SEM_RECORTE}")


def _empacotar() -> None:
    """Reescreve o zip que acompanha o artigo, a partir dos CSVs recém-gravados.

    Mesma razão de `artigo/gerar_tabelas.py` ter um: pacote montado à mão
    envelhece sozinho, e quem recebe o anexo fica com dado diferente do
    manuscrito da mesma mensagem, sem nada indicando isso. Sai daqui, e não de
    um script separado, porque a única garantia de que o pacote corresponde às
    tabelas é ele ser feito no mesmo passo que as gera.
    """
    import zipfile
    csvs = sorted(SAIDA.glob("*.csv"))
    alvo = SAIDA.parent / "tabelas-do-artigo.zip"
    with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
        for c in csvs:
            z.write(c, c.name)
    print(f"[pacote] {alvo.name}: {len(csvs)} CSVs, {alvo.stat().st_size:,} bytes",
          flush=True)


if __name__ == "__main__":
    main()
