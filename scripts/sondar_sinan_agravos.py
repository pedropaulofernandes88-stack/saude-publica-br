"""
sondar_sinan_agravos.py — o que os 45 agravos do SINAN têm EM COMUM
====================================================================

    .venv311/Scripts/python scripts/sondar_sinan_agravos.py
    .venv311/Scripts/python scripts/sondar_sinan_agravos.py --agravos DENG TUBE

Grava `data/refs/sondagem_sinan.json` e imprime o resumo.

POR QUE SONDAR ANTES DE INGERIR
--------------------------------
O SINAN publica 45 agravos em `DADOS/FINAIS`, e **cada um tem ficha própria**.
Um mart "todos os agravos" só existe se houver campo comum de verdade — e supor
qual é sai caro. Medido na ingestão da sífilis, em 2026-09-06:

  * `CLASSI_FIN` do SIFG está VAZIO nos 87.344 registros de 2023. Qualquer
    filtro por confirmação zeraria o agravo inteiro, em silêncio;
  * `CLASSI_FIN` do SIFA traz `' 1'` ao lado de `'1'` em 2,5% dos registros;
  * `EVOLUCAO` NÃO quer dizer a mesma coisa entre agravos: na sífilis congênita
    o código 2 é "óbito por sífilis congênita" e o 5 é "natimorto"; na dengue o
    2 é óbito pelo agravo. Somar os dois como "óbitos" inventaria uma série.

Então esta sondagem **não interpreta nada**. Ela responde três perguntas de
fato, por agravo:

  1. quais campos existem no arquivo;
  2. quantos registros têm município de residência utilizável;
  3. que VALORES aparecem nos campos categóricos que alguém teria vontade de
     usar como se fossem universais.

O que ela habilita é o único mart honesto sem dicionário por agravo:
**notificações por agravo × município de residência × ano**. Contagem de
notificação é comparável entre agravos; desfecho clínico não é.

CUSTO
-----
Um arquivo por agravo (o mais recente), não os 741. São ~45 downloads.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _datasus_ftp import ArquivoAusente, FalhaDeColeta, baixar, listar, registros_dbc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAIDA = ROOT / "data" / "refs" / "sondagem_sinan.json"
DIR_FINAIS = "/dissemin/publicos/SINAN/DADOS/FINAIS"

#: Já ingeridos por pipeline próprio, com dicionário conferido. Ficam de fora
#: para a sondagem falar só do que ainda não se conhece.
JA_INGERIDOS = {"DENG"}

#: Campos que um mart genérico precisaria. Presença é medida, não suposta.
CAMPOS_CHAVE = [
    "ID_AGRAVO", "DT_NOTIFIC", "NU_ANO", "SEM_PRI", "DT_SIN_PRI",
    "ID_MUNICIP", "ID_MN_RESI", "SG_UF", "CS_SEXO", "NU_IDADE_N",
    "CS_RACA", "CS_ESCOL_N", "CLASSI_FIN", "EVOLUCAO", "CRITERIO",
]

#: Categóricos cuja semântica muda entre agravos — a sondagem mostra os valores
#: brutos justamente para que ninguém os unifique sem ler a ficha de cada um.
CATEGORICOS = ["CLASSI_FIN", "EVOLUCAO", "CS_SEXO", "CRITERIO"]

#: Quantos registros ler por arquivo. Presença de campo sai do cabeçalho; a
#: distribuição de valores só precisa de amostra.
AMOSTRA = 60_000


def agravos_disponiveis() -> dict[str, list[int]]:
    """Prefixo -> anos publicados em FINAIS, pela LISTAGEM do diretório."""
    fora: dict[str, list[int]] = {}
    for nome in sorted(listar(DIR_FINAIS)):
        m = re.match(r"^([A-Z]+)BR(\d{2})\.DBC$", nome)
        if not m:
            continue
        prefixo, aa = m.group(1), int(m.group(2))
        # Ano de dois dígitos: 99 é 1999, não 2099. O SINAN começa nos anos 90.
        ano = 1900 + aa if aa >= 90 else 2000 + aa
        fora.setdefault(prefixo, []).append(ano)
    return {k: sorted(v) for k, v in sorted(fora.items())}


def _municipio(valor) -> str | None:
    m = "" if valor is None else str(valor).strip()
    return m[:6] if len(m) >= 6 and m[:6].isdigit() else None


def sondar(prefixo: str, ano: int) -> dict:
    """Lê um arquivo e devolve o que ele TEM, sem interpretar o que significa."""
    nome = f"{prefixo}BR{ano % 100:02d}.dbc"
    contador: Counter = Counter()
    campos: list[str] = []
    valores = {c: Counter() for c in CATEGORICOS}
    lidos = com_residencia = com_notificacao = 0

    it = registros_dbc(baixar(DIR_FINAIS, nome), nome, contador)
    for r in it:
        if not campos:
            campos = list(r.keys())
        lidos += 1
        if _municipio(r.get("ID_MN_RESI")) is not None:
            com_residencia += 1
        if _municipio(r.get("ID_MUNICIP")) is not None:
            com_notificacao += 1
        for c in CATEGORICOS:
            if c in r:
                valores[c][("" if r[c] is None else str(r[c]))[:6]] += 1
        if lidos >= AMOSTRA:
            break
    it.close()

    return {
        "agravo": prefixo,
        "ano_sondado": ano,
        "arquivo": nome,
        "campos": campos,
        "n_campos": len(campos),
        "registros_lidos": lidos,
        "amostra_truncada": lidos >= AMOSTRA,
        "pct_com_municipio_residencia": round(com_residencia / lidos * 100, 1) if lidos else None,
        "pct_com_municipio_notificacao": round(com_notificacao / lidos * 100, 1) if lidos else None,
        "campos_chave_presentes": [c for c in CAMPOS_CHAVE if c in campos],
        "campos_chave_ausentes": [c for c in CAMPOS_CHAVE if c not in campos],
        "valores": {c: dict(valores[c].most_common(12)) for c in CATEGORICOS if c in campos},
        "datas_mascaradas": contador["mascarada"],
        "datas_impossiveis": contador["impossivel"],
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Sondagem dos agravos do SINAN.")
    ap.add_argument("--agravos", nargs="+", help="prefixos a sondar (padrão: todos)")
    args = ap.parse_args()

    catalogo = agravos_disponiveis()
    alvos = args.agravos or [a for a in catalogo if a not in JA_INGERIDOS]
    print(f"[sinan] {len(catalogo)} agravos em FINAIS; sondando {len(alvos)}\n", flush=True)

    achados: list[dict] = []
    falhas: list[dict] = []
    for i, prefixo in enumerate(alvos, 1):
        anos = catalogo.get(prefixo)
        if not anos:
            falhas.append({"agravo": prefixo, "motivo": "não está em FINAIS"})
            print(f"[{i:2d}/{len(alvos)}] {prefixo}: não está em FINAIS", flush=True)
            continue
        # Recua de ano enquanto o arquivo vier VAZIO. Arquivo vazio é fato
        # epidemiológico — COLE 2022 e TETN 2021 têm zero notificações —, mas
        # não informa NADA sobre o esquema. Era assim que dois agravos normais
        # apareciam com "0 campos", indistinguíveis de arquivo quebrado.
        d: dict | None = None
        try:
            for ano in reversed(anos[-6:]):
                d = sondar(prefixo, ano)
                if d["registros_lidos"] > 0:
                    break
        except ArquivoAusente as e:
            falhas.append({"agravo": prefixo, "motivo": f"ausente: {e}"})
            print(f"[{i:2d}/{len(alvos)}] {prefixo}: ausente", flush=True)
            continue
        except FalhaDeColeta as e:
            # Falha NÃO é ausência: fica registrada como falha, e a sondagem
            # segue — o produto aqui é o inventário, não um recorte publicável.
            falhas.append({"agravo": prefixo, "motivo": f"falha de coleta: {str(e)[:160]}"})
            print(f"[{i:2d}/{len(alvos)}] {prefixo}: FALHA — {str(e)[:80]}", flush=True)
            continue
        if d is None:
            falhas.append({"agravo": prefixo, "motivo": "nenhum ano legível"})
            continue
        achados.append(d)
        print(f"[{i:2d}/{len(alvos)}] {prefixo} {ano}: {d['n_campos']:3d} campos · "
              f"{d['registros_lidos']:,} lidos · "
              f"{d['pct_com_municipio_residencia']}% com residência", flush=True)

    # ── resumo: o que é comum de verdade ───────────────────────────────────
    if achados:
        comuns = set(achados[0]["campos"])
        for d in achados[1:]:
            comuns &= set(d["campos"])
        print(f"\n[sinan] campos presentes em TODOS os {len(achados)} agravos sondados: "
              f"{sorted(comuns)}")
        for c in CAMPOS_CHAVE:
            tem = [d["agravo"] for d in achados if c in d["campos"]]
            if len(tem) != len(achados):
                print(f"[sinan] {c}: presente em {len(tem)}/{len(achados)} — "
                      f"falta em {sorted(set(d['agravo'] for d in achados) - set(tem))}")
        sem_resid = [(d["agravo"], d["pct_com_municipio_residencia"]) for d in achados
                     if (d["pct_com_municipio_residencia"] or 0) < 95]
        if sem_resid:
            print(f"[sinan] abaixo de 95% com município de residência: {sem_resid}")

    if falhas:
        print(f"\n[sinan] {len(falhas)} sem sondagem: {falhas}")

    # MESCLA, não sobrescreve. Rodar com `--agravos` para reconferir dois deles
    # apagava os outros 42 do arquivo — foi o que aconteceu em 2026-09-08, e o
    # resultado da varredura completa só não se perdeu porque estava no log.
    # Sondagem parcial não pode apagar o que já se sabia.
    anterior: dict = {"sondados": [], "falhas": []}
    if SAIDA.exists():
        try:
            anterior = json.loads(SAIDA.read_text(encoding="utf-8"))
        except ValueError:
            pass

    def _mesclar(velhos: list[dict], novos: list[dict]) -> list[dict]:
        por_agravo = {x["agravo"]: x for x in velhos}
        por_agravo.update({x["agravo"]: x for x in novos})
        return [por_agravo[k] for k in sorted(por_agravo)]

    achados = _mesclar(anterior.get("sondados", []), achados)
    sondados_ok = {a["agravo"] for a in achados}
    # Agravo que passou a ser sondado sai da lista de falhas.
    falhas = [f for f in _mesclar(anterior.get("falhas", []), falhas)
              if f["agravo"] not in sondados_ok]

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(
        {"catalogo": catalogo, "sondados": achados, "falhas": falhas},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n[ok] {SAIDA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
