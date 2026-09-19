"""
frescura_dos_marts.py — até quando vai cada mart publicado, e o que já venceu
=============================================================================

    .venv311/Scripts/python scripts/frescura_dos_marts.py
    .venv311/Scripts/python scripts/frescura_dos_marts.py --json

Sai com código 0 quando nenhum artefato com VALIDADE está vencido. Sai com ≠ 0
quando algum está, dizendo qual — é portão, não relatório.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O projeto observa a frescura das FONTES (`observar_fontes.py`): o FTP mudou, o
arquivo novo chegou. Ninguém observava a frescura do que foi PUBLICADO, e a
diferença ficou visível em 2026-09-19, ao expor o forecast no MCP:

    mart_forecast_demanda_hospital ... previa 2025-01 a 2025-03

Dezoito meses no passado. E cada linha saía com `status_validacao = "A"`,
validado — que é a combinação exata que faz um leitor apresentar previsão velha
como projeção atual. O rótulo de qualidade do ajuste e o rótulo de atualidade são
eixos diferentes, e só o primeiro estava publicado.

O QUE ESTE PORTÃO REPROVA, E O QUE ELE NÃO REPROVA
---------------------------------------------------
Reprova apenas **artefato com validade**: aquele cuja competência aponta para o
FUTURO por construção. Hoje isso é a projeção de demanda. Uma previsão cujo
horizonte passou não é uma previsão velha — deixou de ser previsão.

NÃO reprova mart em 2024. A varredura que motivou este arquivo mediu os 35 marts
e achou o resto saudável: os consolidados param em 2024 porque o DataSUS
consolida até 2024, e as fontes correntes estavam em 2026 (dengue e SISAGUA em
2026, PNI em 2026-08, cobertura da APS em 2026-05). Confundir defasagem de
consolidação com abandono produziria alarme diário, e alarme diário treina a
gente a ignorar a issue — o mesmo motivo pelo qual o padrão do SIH recorta o
período no observador de fontes.

Os marts sem coluna temporal (`mart_qualidade_registro_municipio`,
`mart_perfil_mortalidade_municipio`, `mart_contexto_social_municipio`,
`mart_icsap_pares`, `mart_sisagua_cobertura`) são retrato ou derivação de período
fechado, não série: eles aparecem no relatório como "sem eixo temporal" e não
entram no portão.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "clients" / "python"))

import saudeemdado as sd  # noqa: E402

SCHEMA = ROOT / "migrations" / "schema" / "schema.sql"

#: Nomes de coluna temporal, em ordem de preferência. O primeiro que existir na
#: tabela é o eixo — os marts não padronizam o nome, e tentar padronizá-los aqui
#: seria inventar um que a fonte não usa.
CANDIDATOS = ("ano_mes_previsto", "ano_mes", "competencia", "mes_competencia",
              "ano_epi", "ano_referencia", "ano")

#: Marts cuja competência aponta para o FUTURO por construção. Só estes o portão
#: reprova quando vencem. Crescer esta lista é decisão; crescê-la por engano faz
#: o portão reprovar consolidação normal.
COM_VALIDADE = {"mart_forecast_demanda_hospital"}


def colunas_do_schema() -> dict[str, list[str]]:
    texto = SCHEMA.read_text(encoding="utf-8")
    saida = {}
    for nome in sorted(set(re.findall(r"public\.(mart_[a-z0-9_]+)", texto))):
        m = re.search(r"create table if not exists public\.%s \((.*?)\n\);" % nome,
                      texto, re.S)
        if not m:
            continue
        saida[nome] = [linha.strip().split()[0] for linha in m.group(1).splitlines()
                       if linha.strip() and not linha.strip().startswith("constraint")]
    return saida


def _periodo_atual(coluna: str) -> str:
    """O 'agora' comparável, na granularidade da própria coluna."""
    hoje = date.today()
    if coluna in ("ano", "ano_epi", "ano_referencia"):
        return str(hoje.year)
    return hoje.strftime("%Y-%m")


def _normalizar(valor, coluna: str) -> str:
    """'2026-05-01' e '2026-05' comparam igual; ano vira string."""
    texto = str(valor)
    if coluna in ("ano", "ano_epi", "ano_referencia"):
        return texto[:4]
    return texto[:7]


def medir() -> list[dict]:
    resultado = []
    for mart, cols in colunas_do_schema().items():
        coluna = next((c for c in CANDIDATOS if c in cols), None)
        if coluna is None:
            resultado.append({"mart": mart, "coluna": None, "ultimo": None,
                              "com_validade": False, "vencido": False})
            continue
        try:
            linhas = sd._get(mart, {"select": coluna, "order": f"{coluna}.desc",
                                    "limit": "1"}, max_rows=1)
        except Exception as e:  # noqa: BLE001 — rede/HTTP; reportar, não derrubar
            resultado.append({"mart": mart, "coluna": coluna, "ultimo": None,
                              "erro": type(e).__name__, "com_validade": False,
                              "vencido": False})
            continue
        ultimo = _normalizar(linhas[0][coluna], coluna) if linhas else None
        com_validade = mart in COM_VALIDADE
        resultado.append({
            "mart": mart, "coluna": coluna, "ultimo": ultimo,
            "com_validade": com_validade,
            # Vazio também reprova quando o artefato tem validade: nenhuma linha
            # é indistinguível de "não há previsão", e é isso que se reporta.
            "vencido": com_validade and (ultimo is None or ultimo < _periodo_atual(coluna)),
        })
    return resultado


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--json", action="store_true", help="saída em JSON, para CI")
    args = ap.parse_args()

    medidas = medir()
    vencidos = [m for m in medidas if m["vencido"]]

    if args.json:
        print(json.dumps({"medido_em": date.today().isoformat(), "marts": medidas,
                          "vencidos": [m["mart"] for m in vencidos]},
                         ensure_ascii=False, indent=2))
    else:
        for m in sorted(medidas, key=lambda x: (x["ultimo"] or "", x["mart"])):
            if m["coluna"] is None:
                continue
            marca = "  ← VENCIDO" if m["vencido"] else (" (validade)" if m["com_validade"] else "")
            print(f"  {m['mart']:<42}{m['coluna']:<20}{m['ultimo'] or 'VAZIO'}{marca}")
        sem_eixo = [m["mart"] for m in medidas if m["coluna"] is None]
        if sem_eixo:
            print("\n  sem eixo temporal (retrato ou período fechado, fora do portão):")
            for nome in sem_eixo:
                print(f"    - {nome}")
        print()
        if vencidos:
            for m in vencidos:
                print(f"❌ {m['mart']}: última competência {m['ultimo']}, e o artefato "
                      f"tem VALIDADE — o horizonte já passou.\n"
                      f"   Enquanto não for retreinado, não há previsão vigente, e "
                      f"apresentá-la como projeção atual é erro.\n")
            print("Há artefato vencido publicado.")
        else:
            print("✅ Nenhum artefato com validade está vencido. Mart em 2024 é "
                  "defasagem de consolidação do DataSUS, não abandono.")

    return 1 if vencidos else 0


if __name__ == "__main__":
    sys.exit(main())
