"""
pipeline_pni_marts.py — PNI/RNDS: agregados → marts publicáveis
================================================================

Consome os agregados por competência gravados por `pipeline_pni.py` e produz
as três tabelas publicadas:

  mart_vacinacao_municipio    ano × município × imunobiológico × doses
  mart_vacinacao_uf_mes       competência × UF × imunobiológico × doses
  mart_cobertura_vacinal_uf   ano × UF × indicador × cobertura

CONTAGEM, NÃO TAXA, no recorte municipal. Cobertura vacinal municipal foi
testada e reprovada: correlação de 0,591 entre 2023 e 2024, e cobertura mediana
caindo de 102,7% nos municípios com 50–100 nascidos para 86,2% nos com 5 mil+.
Ruído não tem direção; isso é viés sistemático de denominador. A hipótese de
descasamento geográfico foi testada com o agregado de fluxo e REFUTADA
(correlação +0,002). Ver docs/vacinacao-pni-metodologia.md.

Contagem de doses não depende de denominador e por isso não herda nada disso.

Uso:
  .venv311/Scripts/python scripts/pipeline_pni_marts.py [--no-upload]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _publicacao import escrever_parquet  # noqa: E402
from _supabase_key import chave_escrita  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
AGREGADOS = ROOT / "data" / "raw" / "PNI" / "agregados"
MARTS = ROOT / "data" / "marts"
PRODUTOR = "scripts/pipeline_pni_marts.py"

# ── Vocabulário ──────────────────────────────────────────────────────────────
# O campo de imunobiológico traz 115 rótulos e nem todos são vacina. Diluente e
# soro entram no arquivo bruto e inflariam uma contagem de "doses aplicadas".
#
# O padrão de soro roda SEM ignorecase de propósito: com ignorecase, "Sarampo"
# — que é vacina — casa com `SA[A-Z]*` e some da contagem. Foi um erro real.
PADRAO_SORO = re.compile(r"^(SA[A-Z]{0,4}|IGHA[A-Z]{0,3}|SBOTUL[A-Z]*)$")
PADRAO_DILUENTE = re.compile(r"^DIL", re.IGNORECASE)
DILUENTE_EXATO = {"NaCl 0,9%"}
# Rótulos que não classificamos com segurança. Ficam de fora e são LISTADOS na
# saída: 0,004% das doses não justifica adivinhar, e sumir em silêncio é pior
# do que aparecer no relatório.
INDEFINIDOS = {"FTp", "Fta", "Tétano"}


def classificar(rotulo: str) -> str:
    if rotulo in DILUENTE_EXATO or PADRAO_DILUENTE.match(rotulo):
        return "diluente"
    if PADRAO_SORO.match(rotulo):
        return "soro/imunoglobulina"
    if rotulo in INDEFINIDOS:
        return "indefinido"
    return "vacina"


# ── Cobertura ────────────────────────────────────────────────────────────────
# Cada indicador declara QUAL tipo de dose conta. Somar tipos diferentes conta a
# mesma criança duas vezes: um conjunto genérico ("1ª Dose", "Única", "Dose")
# produziu 110,6% de cobertura de BCG.
#
# BCG e hepatite B ao nascer ficam de FORA: são aplicadas na maternidade e o
# denominador por residência da mãe não serve. Por UF chegam a 127,8% (CE) e
# 121,0% (AL) em 2024, enquanto as cinco de atenção básica ficam contidas.
INDICADORES: dict[str, tuple[list[str], list[str]]] = {
    "Pentavalente 1a dose": (["Penta", "Penta acelular", "Hexa acelular"], ["1ª Dose"]),
    "Poliomielite 1a dose": (["VIP"], ["1ª Dose"]),
    "Rotavirus 1a dose": (["ROTA", "ROTA5"], ["1ª Dose"]),
    "Pneumococica 1a dose": (["VPC10", "VPC13", "VPC15", "VPC20"], ["1ª Dose"]),
    "Meningococica 1a dose": (["MenC", "MenACWY"], ["1ª Dose"]),
}


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for linha in f.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, _, v = linha.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})
    return env


def carregar_agregados() -> pd.DataFrame:
    arquivos = sorted(AGREGADOS.glob("municipal_*.parquet"))
    if not arquivos:
        raise SystemExit(f"sem agregados em {AGREGADOS} — rode pipeline_pni.py antes")
    df = pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)
    df["ano"] = df.competencia.str[:4].astype(int)
    return df


class Loader:
    def __init__(self, url: str, key: str, batch: int = 8000):
        self.url = url.rstrip("/")
        self.batch = batch
        self.h = {"apikey": key, "Authorization": f"Bearer {key}",
                  "Content-Type": "application/json",
                  "Prefer": "return=minimal,resolution=merge-duplicates"}

    def load(self, tabela: str, df: pd.DataFrame) -> None:
        recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
        for i in range(0, len(recs), self.batch):
            corpo = json.dumps(recs[i:i + self.batch], allow_nan=False,
                               default=lambda o: o.item() if hasattr(o, "item") else o)
            r = requests.post(f"{self.url}/rest/v1/{tabela}",
                              headers=self.h, data=corpo, timeout=300)
            if r.status_code not in (200, 201):
                raise RuntimeError("%s: HTTP %d %s" % (tabela, r.status_code, r.text[:200]))
        print("[supabase]   %s: %d OK" % (tabela, len(recs)), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    bruto = carregar_agregados()
    total_bruto = int(bruto.doses.sum())

    por_classe: dict[str, list[str]] = {}
    for rotulo in sorted(bruto.imunobiologico.unique()):
        por_classe.setdefault(classificar(rotulo), []).append(rotulo)
    print("[pni] %d rótulos de imunobiológico" % sum(len(v) for v in por_classe.values()))
    for classe in ("diluente", "soro/imunoglobulina", "indefinido"):
        itens = por_classe.get(classe, [])
        if not itens:
            continue
        doses = int(bruto[bruto.imunobiologico.isin(itens)].doses.sum())
        print("[pni]   %-20s %2d rótulos, %9d doses (%.3f%%): %s"
              % (classe, len(itens), doses, 100 * doses / total_bruto, ", ".join(itens)))

    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")
    d = bruto[bruto.imunobiologico.map(lambda r: classificar(r) == "vacina")
              & bruto.municipio_cod.isin(set(dim.municipio_cod))].copy()
    print("[pni] doses %d → %d (%.3f%% fora da contagem de vacinação)"
          % (total_bruto, int(d.doses.sum()), 100 * (1 - d.doses.sum() / total_bruto)))

    # 1. municipal, anual
    mun = (d.groupby(["ano", "municipio_cod", "imunobiologico"], as_index=False).doses.sum()
           .merge(dim[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]],
                  on="municipio_cod", how="left"))
    mun = mun[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano",
               "imunobiologico", "doses"]].sort_values(
        ["municipio_cod", "ano", "imunobiologico"]).reset_index(drop=True)

    # 2. UF, mensal — é onde mora a atualidade
    com_uf = d.merge(dim[["municipio_cod", "uf_sigla"]], on="municipio_cod", how="left")
    ufmes = (com_uf.groupby(["competencia", "uf_sigla", "imunobiologico"], as_index=False)
             .doses.sum().sort_values(["competencia", "uf_sigla", "imunobiologico"])
             .reset_index(drop=True))

    # 3. cobertura por UF, só nos anos com nascidos vivos DEFINITIVOS
    nat = pd.read_parquet(MARTS / "mart_natalidade_municipio.parquet")
    nv = nat.groupby(["uf_sigla", "ano"], as_index=False).nascidos.sum()
    nv = nv[nv.uf_sigla != "ND"]
    anos_ok = sorted(set(nat.ano) & set(d.ano))
    print(f"[pni] anos com denominador definitivo: {anos_ok}")

    partes = []
    for nome, (vacinas, doses_validas) in INDICADORES.items():
        s = (com_uf[(com_uf.faixa_etaria == "<1") & com_uf.imunobiologico.isin(vacinas)
                    & com_uf.tipo_dose.isin(doses_validas) & com_uf.ano.isin(anos_ok)]
             .groupby(["uf_sigla", "ano"], as_index=False).doses.sum())
        s["indicador"] = nome
        partes.append(s)
    cob = pd.concat(partes, ignore_index=True).merge(nv, on=["uf_sigla", "ano"], how="inner")
    cob["cobertura_pct"] = (100 * cob.doses / cob.nascidos).round(1)
    cob = cob[["uf_sigla", "ano", "indicador", "doses", "nascidos", "cobertura_pct"]] \
        .sort_values(["ano", "indicador", "uf_sigla"]).reset_index(drop=True)

    # Guarda: cobertura acima de 100% denuncia erro de composição do indicador
    # ou de denominador. Não aborta — os cinco indicadores publicados têm
    # máximo de 104,2% —, mas tem de aparecer.
    acima = cob[cob.cobertura_pct > 100]
    print("[pni] cobertura acima de 100%%: %d de %d linhas (%.1f%%), máximo %.1f%%"
          % (len(acima), len(cob), 100 * len(acima) / len(cob), cob.cobertura_pct.max()))
    if cob.cobertura_pct.max() > 115:
        raise SystemExit("cobertura acima de 115% — composição do indicador suspeita")

    MARTS.mkdir(parents=True, exist_ok=True)
    saidas = [("mart_vacinacao_municipio", mun), ("mart_vacinacao_uf_mes", ufmes),
              ("mart_cobertura_vacinal_uf", cob)]
    for nome, df in saidas:
        escrever_parquet(df, MARTS / (f"{nome}.parquet"), origem="pipeline",
                         produtor=PRODUTOR)
        print("[pni] %-28s %8d linhas" % (nome, len(df)))
    print(f"[pni] última competência: {ufmes.competencia.max()}")

    if args.no_upload:
        return

    env = load_env()
    ld = Loader(env["SUPABASE_URL"], chave_escrita(env))
    for nome, df in saidas:
        ld.load(nome, df)
    meta = pd.DataFrame([
        ("fonte_pni", "PNI/Ministério da Saúde — doses aplicadas alimentadas pela RNDS, "
                      "arquivo mensal do portal de dados abertos do SUS"),
        ("pni_cobertura_temporal", "%d–%d; última competência %s"
         % (d.ano.min(), d.ano.max(), ufmes.competencia.max())),
        ("pni_limitacao", "Cobertura vacinal é publicada apenas por UF e apenas para cinco "
                          "indicadores da atenção básica. Cobertura municipal foi testada e "
                          "reprovada (viés sistemático de denominador); BCG e hepatite B ao "
                          "nascer não têm denominador adequado nem por UF."),
        ("gerado_em", datetime.now().isoformat(timespec="seconds")),
    ], columns=["chave", "valor"])
    ld.load("meta_dataset", meta)
    print("[done] marts do PNI concluídos.", flush=True)


if __name__ == "__main__":
    main()
