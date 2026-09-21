"""
Fonte publicada e não observada não dá erro — só deixa de avisar.

O observador roda toda segunda e abre issue quando o DataSUS mexe num arquivo.
O que ele NÃO faz é reclamar do que não está na lista dele: o Painel Oncologia
e a sífilis entraram no site sem entrar na observação, e o SIM — a fonte de
maior peso do projeto — era vigiado por uma URL do S3 que devolve 403 em todos
os anos. Nos três casos a cobertura envelheceu sem nenhum sinal.

Estes testes fecham o laço entre `site/lib/fontes.ts` (o que prometemos) e
`scripts/observar_fontes.py` (o que vigiamos).

Executar: .venv311/Scripts/python -m pytest tests/test_observacao_de_fontes.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import observar_fontes as obs  # noqa: E402

FONTES_TS = RAIZ / "site" / "lib" / "fontes.ts"


def ids_publicados() -> set[str]:
    """Os ids declarados no array FONTES do site."""
    texto = FONTES_TS.read_text(encoding="utf-8")
    corpo = texto.split("FONTE_DA_TABELA")[0]
    return set(re.findall(r'^\s*id:\s*"([a-z_]+)"', corpo, re.M))


def bases_configuradas() -> set[str]:
    """Rótulos `base` que a configuração do observador realmente produz.

    Os não-FTP saem de `OBSERVADORES_EXTRAS`, no próprio observador, e não de
    um conjunto digitado aqui: com a lista no teste, registrar uma fonte como
    observada e esquecer de chamá-la passaria — que é o defeito que esta guarda
    existe para pegar.
    """
    return ({base for base, _, _, _ in obs.DIRETORIOS_FTP}
            | set(obs.OBSERVADORES_EXTRAS))


def test_o_site_declara_fontes_legiveis():
    """Se a leitura quebrar, os testes abaixo passariam vazios."""
    assert len(ids_publicados()) >= 10


def test_toda_fonte_publicada_esta_observada_ou_dispensada_com_motivo():
    faltando = ids_publicados() - set(obs.OBSERVADAS) - set(obs.NAO_OBSERVADAS)
    assert not faltando, (
        f"fonte publicada sem decisão de observação: {sorted(faltando)}. "
        "Ou entra em OBSERVADAS (com diretório/URL de verdade), ou entra em "
        "NAO_OBSERVADAS com o motivo. Silêncio não é decisão."
    )


def test_nenhuma_fonte_observada_deixou_de_existir_no_site():
    sobrando = (set(obs.OBSERVADAS) | set(obs.NAO_OBSERVADAS)) - ids_publicados()
    assert not sobrando, (
        f"a observação cita fonte que o site não publica mais: {sorted(sobrando)}"
    )


def test_fonte_nao_esta_nas_duas_listas():
    assert not set(obs.OBSERVADAS) & set(obs.NAO_OBSERVADAS)


def test_toda_dispensa_traz_motivo_escrito():
    mudas = [k for k, v in obs.NAO_OBSERVADAS.items() if not v.strip()]
    assert not mudas, f"dispensa sem motivo: {mudas}"


def test_base_declarada_existe_de_fato_na_configuracao():
    """Declarar não basta: o rótulo tem de sair de um diretório ou URL real.

    É a diferença entre uma guarda implementada e uma guarda anunciada — esta
    é a checagem que teria pego o SIM sendo "observado" só por uma constante.
    """
    reais = bases_configuradas()
    fantasmas = {f: b for f, b in obs.OBSERVADAS.items() if b not in reais}
    assert not fantasmas, (
        f"fonte declarada como observada cuja base não é produzida por nenhuma "
        f"entrada real: {fantasmas}"
    )


def test_o_sim_e_observado_pelo_ftp_e_nao_so_pelo_s3():
    """Depender de uma rota só é o que quebrou em 2026-09-06.

    O S3 servia DO22/DO23/DO24 em 200 até 31/08/2026 e passou a 403 na semana
    seguinte — com o PNI, no mesmo bucket, seguindo em 200. Enquanto o SIM
    tiver as duas rotas observadas, a queda de uma aparece como mudança em vez
    de aparecer como silêncio.
    """
    diretorios = [d for base, _h, d, _p in obs.DIRETORIOS_FTP if base == "SIM"]
    assert diretorios, "o SIM voltou a depender só do S3, que hoje devolve 403"
    assert any("SIM" in d for d in diretorios)


def test_a_sifilis_e_observada_no_prelim_porque_nao_ha_finais():
    """Não existe SIF* em DADOS/FINAIS: procurar lá seria vigiar o vazio."""
    padroes = [(d, p) for base, _h, d, p in obs.DIRETORIOS_FTP if "SIF" in p]
    assert padroes, "a sífilis saiu da observação"
    for diretorio, _ in padroes:
        assert diretorio.endswith("PRELIM"), f"sífilis vigiada em {diretorio}"


def test_o_cnes_vigia_a_competencia_que_o_projeto_ingere():
    """O pipeline lê só dezembro; vigiar os outros onze meses é ruído."""
    padroes = [p for base, _h, _d, p in obs.DIRETORIOS_FTP if base == "CNES"]
    assert padroes
    assert all("12" in p for p in padroes)


@pytest.mark.parametrize("padrao", [p for _, _, _, p in obs.DIRETORIOS_FTP])
def test_todo_padrao_de_arquivo_compila(padrao):
    re.compile(padrao)


# ── a guarda vista REPROVANDO ──────────────────────────────────────────────
#
# Os testes acima aprovam o estado atual, e um teste que só sabe aprovar é
# indistinguível de um teste quebrado. Estes reconstroem os três esquecimentos
# reais e exigem que a checagem os pegue.

def _faltando(publicados, observadas, dispensadas):
    return set(publicados) - set(observadas) - set(dispensadas)


def test_a_guarda_pega_fonte_nova_sem_decisao():
    """Foi assim que oncologia e sífilis entraram no site sem entrar aqui."""
    faltando = _faltando({"sim", "oncologia"}, {"sim": "SIM"}, {})
    assert faltando == {"oncologia"}


def test_a_guarda_pega_base_declarada_que_nao_existe():
    """O caso do SIM: id declarado como observado, sem diretório que o produza."""
    reais = {"SIH", "SINASC"}
    fantasmas = {f: b for f, b in {"sim": "SIM"}.items() if b not in reais}
    assert fantasmas == {"sim": "SIM"}


def test_a_guarda_pega_fonte_que_sumiu_do_site():
    sobrando = ({"sim", "extinta"}) - {"sim"}
    assert sobrando == {"extinta"}


def test_a_checagem_de_hoje_aprovaria_o_estado_de_ontem_se_fosse_fraca():
    """Controle: com oncologia e sífilis fora, a lista de faltantes não é vazia.

    Se este teste passar a devolver conjunto vazio, a checagem virou decorativa.
    """
    ontem = {k: v for k, v in obs.OBSERVADAS.items()
             if k not in ("oncologia", "sifilis")}
    assert _faltando(ids_publicados(), ontem, obs.NAO_OBSERVADAS) == {
        "oncologia", "sifilis"}


# ── os dois dialetos de LIST ───────────────────────────────────────────────
#
# O DataSUS responde MS-DOS e a ANS responde Unix. Aplicar o leitor do primeiro
# ao segundo NÃO levanta erro: lê a permissão como data (None) e o ANO como
# tamanho. O registro fica com bytes=2024, o que é pior que não observar,
# porque parece observação.

from datetime import date  # noqa: E402


def test_linha_ms_dos_do_datasus():
    linha = "08-11-26  11:05AM              1234567 RDPE2601.dbc"
    assert obs.parse_linha_ftp(linha) == ("RDPE2601.dbc", 1234567, "2026-08-11")


def test_linha_unix_com_ano_explicito():
    linha = "-rwxrwxr-x    1 1001     1001       402386 Sep 04  2024 pda-024-icb-AC-2026_07.zip"
    assert obs.parse_linha_ftp(linha) == (
        "pda-024-icb-AC-2026_07.zip", 402386, "2024-09-04")


def test_linha_unix_de_diretorio():
    """A competência da ANS é um DIRETÓRIO, e é ela que precisa ser vista."""
    linha = "drwxrwxr-x    2 1001     1001         4096 Jul 05  2024 202105"
    assert obs.parse_linha_ftp(linha) == ("202105", 4096, "2024-07-05")


def test_linha_unix_recente_infere_o_ano():
    """Arquivo com menos de seis meses traz hora no lugar do ano."""
    linha = "-rwxrwxr-x    1 1001     1001      3301853 Sep 04 15:02 pda.zip"
    assert obs.parse_linha_ftp(linha, hoje=date(2026, 9, 21)) == (
        "pda.zip", 3301853, "2026-09-04")


def test_linha_unix_recente_no_futuro_volta_um_ano():
    """Em janeiro, 'Dec 20' é do ano passado, não do que vem."""
    linha = "-rwxrwxr-x    1 1001     1001         100 Dec 20 15:02 x.zip"
    assert obs.parse_linha_ftp(linha, hoje=date(2026, 1, 5)) == (
        "x.zip", 100, "2025-12-20")


def test_o_leitor_antigo_leria_o_ano_como_tamanho():
    """Regressão explícita do defeito, para ninguém 'simplificar' de volta."""
    linha = "drwxrwxr-x    2 1001     1001         4096 Jul 05  2024 202105"
    partes = linha.split()
    antigo_bytes = int(partes[-2]) if partes[-2].isdigit() else None
    assert antigo_bytes == 2024, "o defeito era este: o ano virava tamanho"
    nome, tam, quando = obs.parse_linha_ftp(linha)
    assert (tam, quando) == (4096, "2024-07-05")


def test_linha_curta_ou_estranha_devolve_none():
    for linha in ("", "total 64", "?? ??", "abc def"):
        assert obs.parse_linha_ftp(linha) is None


def test_a_ans_esta_entre_as_bases_configuradas():
    assert "ANS" in bases_configuradas(), (
        "a ANS voltou a ficar sem observação; ela tem FTP próprio, com 64 "
        "competências listadas e ZIP por UF com tamanho e data")


def test_todo_observador_extra_existe_de_fato():
    """O mapa aponta para função que existe E que o main chama."""
    fonte_do_main = (RAIZ / "scripts" / "observar_fontes.py").read_text(encoding="utf-8")
    for base, funcao in obs.OBSERVADORES_EXTRAS.items():
        assert callable(getattr(obs, funcao, None)), f"{base}: {funcao} não existe"
        assert f"{funcao}()" in fonte_do_main, (
            f"{base}: {funcao} está no mapa e ninguém a chama — a base seria "
            f"declarada como observada sem nunca ser observada")


def test_o_rhc_e_observado():
    """Regressão: ele entrou no registro e quase ficou sem observador."""
    assert "RHC" in obs.OBSERVADORES_EXTRAS
    assert "RHC" in bases_configuradas()
