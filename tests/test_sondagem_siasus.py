"""O portão do SIA/SUS reprova pelas razões certas, e sabe aprovar.

A razão de existir mais importante está na regressão dos ARQUIVOS PARTIDOS: o
recorte AQ+AR foi escolhido porque hoje não há nenhum ali, e as duas convenções
do DataSUS são armadilhas OPOSTAS — uma some com a competência, a outra conta em
dobro, e num total nacional elas se cancelam. Se um dia o DataSUS partir um
arquivo de quimioterapia, o coletor passaria a errar em silêncio. Este portão é
o que avisa.

Nada aqui toca a rede.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import sondar_siasus as ss  # noqa: E402


def _linha(nome: str, tamanho: int = 1_000_000) -> str:
    """Uma linha no formato do IIS, que é o que o DataSUS serve."""
    return f"02-10-26  02:44PM        {tamanho:>12} {nome}"


def _diretorio(**por_grupo: int) -> list[str]:
    """Um LIST sintético: quantos arquivos por grupo."""
    linhas = []
    for grupo, n in por_grupo.items():
        for i in range(n):
            uf = ["AC", "SP", "MG"][i % 3]
            # <GRUPO><UF><AA><MM> — o ano tem DOIS dígitos no SIA, e errar isso
            # aqui fazia todo arquivo sintético cair fora da gramática.
            linhas.append(_linha(f"{grupo}{uf}{i % 26:02d}{i % 12 + 1:02d}.dbc"))
    return linhas


SAUDAVEL = {"AQ": ss.MINIMO_ARQUIVOS + 10, "AR": ss.MINIMO_ARQUIVOS + 10,
            "PA": 100, "BI": 100}


def _rodar(linhas, monkeypatch, capsys):
    monkeypatch.setattr(ss, "listar", lambda: linhas)
    monkeypatch.setattr(sys, "argv", ["sondar_siasus.py"])
    codigo = ss.main()
    return codigo, capsys.readouterr().out


def test_APROVA_quando_os_grupos_alvo_estao_sadios(monkeypatch, capsys):
    codigo, saida = _rodar(_diretorio(**SAUDAVEL), monkeypatch, capsys)
    assert codigo == 0, "portão que nunca aprova é indistinguível de portão quebrado"
    assert "Fonte apta" in saida
    # E mesmo aprovando, não deixa a refutação passar em silêncio.
    assert "60 Dias" in saida


def test_reprova_se_um_grupo_alvo_sumir_do_FTP(monkeypatch, capsys):
    sem_ar = {k: v for k, v in SAUDAVEL.items() if k != "AR"}
    codigo, saida = _rodar(_diretorio(**sem_ar), monkeypatch, capsys)
    assert codigo == 1
    assert "AR" in saida and "sumiu" in saida


def test_reprova_se_o_volume_despencar(monkeypatch, capsys):
    poucos = {**SAUDAVEL, "AQ": 10}
    codigo, saida = _rodar(_diretorio(**poucos), monkeypatch, capsys)
    assert codigo == 1
    assert "recorte parcial" in saida, (
        "a mensagem tem de dizer o DANO, não só o número"
    )


@pytest.mark.parametrize("sufixo", ["a", "_1"])
def test_reprova_se_aparecer_arquivo_PARTIDO_no_recorte(sufixo, monkeypatch, capsys):
    """As duas convenções do DataSUS, e o portão tem de pegar as duas.

    `PASP2412a` — o arquivo base NÃO existe: quem procurar o base some com a
    competência inteira. `BIMG2305_1` — o base EXISTE e é a soma: quem pegar
    tudo do prefixo conta duas vezes.
    """
    linhas = _diretorio(**SAUDAVEL) + [_linha(f"AQSP2412{sufixo}.dbc")]
    codigo, saida = _rodar(linhas, monkeypatch, capsys)
    assert codigo == 1
    assert "PARTIDO" in saida
    assert "opostas" in saida, "a mensagem tem de explicar por que isso é grave"


def test_partido_FORA_do_recorte_nao_reprova(monkeypatch, capsys):
    """PA e BI têm 997 partidos hoje e o coletor não os toca — não é problema."""
    linhas = _diretorio(**SAUDAVEL) + [_linha("PASP2412a.dbc"), _linha("BIMG2305_1.dbc")]
    codigo, _ = _rodar(linhas, monkeypatch, capsys)
    assert codigo == 0


def test_o_parser_e_do_IIS_e_nao_do_ls_do_unix():
    """Parser de `ls` devolve ZERO arquivos sem erro — o diretório parece vazio."""
    iis = _linha("AQAC2401.dbc")
    grupos, fora, _ = ss.compor([iis])
    assert grupos["AQ"][0] == 1 and fora == 0

    unix = "-rw-r--r-- 1 ftp ftp 1000000 Oct  2 14:44 AQAC2401.dbc"
    grupos2, fora2, _ = ss.compor([unix])
    assert grupos2 == {} and fora2 == 1, (
        "linha que não casa tem de ser CONTADA como resíduo, nunca ignorada"
    )


def test_a_refutacao_do_prazo_esta_escrita_no_arquivo():
    """O número óbvio desta fonte é falso, e quem abrir o arquivo tem de topar
    com isso antes de escrever a conta."""
    texto = (RAIZ / "scripts" / "sondar_siasus.py").read_text(encoding="utf-8")
    assert "AQ_DTIDEN" in texto and "AQ_DTINTR" in texto
    assert "prevalência" in texto, "tem de dizer O QUE o intervalo realmente mede"
    assert "AP_CNSPCN" in texto, "e por que a medida certa exige ligação longitudinal"
