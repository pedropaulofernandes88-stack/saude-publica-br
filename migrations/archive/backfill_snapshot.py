"""
backfill_snapshot.py — reconstrói o histórico de extrações a partir do git.

A tabela snapshot_publicacao (V026) mede quanto um número preliminar ainda se
move entre uma leitura da fonte e a seguinte. Ela só tem valor com série, e
série leva tempo — a menos que já exista uma escondida em algum lugar.

A hipótese era essa: site/public/sdata/*.json é gerado no build e está
VERSIONADO, então `git log` sobre esses arquivos seria uma série temporal de
extrações acumulada sem querer.

RESULTADO DA HIPÓTESE — ELA NÃO SE SUSTENTOU (medido em 2026-08-18)
    serie_total.json tem 2 commits, ambos em 2026-06-11. dengue_uf_semana.json
    tem 2 commits com conteúdo idêntico. Sobra UMA extração por série: zero
    revisões observáveis.

    A confirmação veio dos boletins semanais, que são datados e independentes:
    as cinco edições de 2026-07-23 a 2026-08-17 repetem os MESMOS números —
    6.564.924 casos de dengue em 2024 e 102.412 óbitos em novembro/2024, sem
    variar um dígito em 25 dias.

    Isso não mostra que o DataSUS é estável. Mostra que este projeto não
    reingere: os marts estão congelados desde junho, e uma fonte que nunca é
    relida nunca revela revisão. (Os alertas do InfoDengue, esses sim, mudam
    toda semana — a parte viva do boletim é o nowcasting, não o SIM/SINAN.)

O QUE ESTE SCRIPT FAZ, ENTÃO
    Registra o t₀ da série: o valor que cada competência tinha na primeira
    publicação conhecida, com origem `git:<sha>`. É âncora, não medição — a
    data é a do build, não a da leitura da fonte. A medição começa quando o
    pipeline passar a gravar `origem='pipeline'` a cada execução, e só terá o
    que observar se houver reingestão periódica.

DEDUPLICAÇÃO
    Commits consecutivos com conteúdo idêntico são colapsados no primeiro. Um
    rebuild que não mudou nenhum número não é um evento de publicação, e contá-lo
    inflaria a série com revisões de 0,00% que só diriam "o site foi para o ar
    de novo".

GRANULARIDADE
    UF × competência, mais o agregado BR. Município fica de fora de propósito:
    ali a variação de poucos óbitos domina o percentual sem dizer nada sobre a
    estabilidade da fonte (ver o cabeçalho da V026).

Uso:
    .venv311/Scripts/python scripts/backfill_snapshot.py
    .venv311/Scripts/python scripts/backfill_snapshot.py --resumo
    .venv311/Scripts/python scripts/_subir_mart.py snapshot_publicacao
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"

# (caminho versionado, base, metrica, campo do valor, como montar a competencia)
FONTES = [
    ("site/public/sdata/serie_total.json", "SIM", "obitos", "obitos", "mensal"),
    ("site/public/sdata/dengue_uf_semana.json", "SINAN", "casos_provaveis",
     "casos_provaveis", "semanal"),
]


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                       encoding="utf-8", errors="replace")
    return r.stdout


def revisoes(caminho: str) -> list[tuple[str, str]]:
    """[(sha, data)] do mais antigo para o mais novo."""
    saida = git("log", "--follow", "--format=%H %ad", "--date=short", "--", caminho)
    linhas = [ln.split() for ln in saida.splitlines() if ln.strip()]
    return [(sha, data) for sha, data in reversed(linhas)]


def competencia_de(row: dict, modo: str) -> str | None:
    if modo == "mensal":
        mes = str(row.get("mes_competencia") or "")
        return mes[:7] if len(mes) >= 7 else None
    ano, semana = row.get("ano_epi"), row.get("semana_epi")
    if ano is None or semana is None:
        return None
    return f"{int(ano)}-W{int(semana):02d}"


def agregar(blob: str, metrica_campo: str, modo: str) -> dict[tuple[str, str], float]:
    """{(competencia, uf): valor}, incluindo o agregado BR."""
    try:
        dados = json.loads(blob)
    except json.JSONDecodeError:
        return {}
    if not isinstance(dados, list):
        return {}

    fora: dict[tuple[str, str], float] = defaultdict(float)
    for row in dados:
        if not isinstance(row, dict):
            continue
        comp = competencia_de(row, modo)
        uf = row.get("uf_sigla")
        valor = row.get(metrica_campo)
        if comp is None or not uf or valor is None:
            continue
        # 'BR' na fonte seria dupla contagem: o agregado e recalculado abaixo.
        if uf == "BR":
            continue
        fora[(comp, uf)] += float(valor)
        fora[(comp, "BR")] += float(valor)
    return dict(fora)


def coletar() -> pd.DataFrame:
    linhas: list[dict] = []
    for caminho, base, metrica, campo, modo in FONTES:
        revs = revisoes(caminho)
        if not revs:
            print(f"[aviso] sem historico para {caminho}", flush=True)
            continue

        anterior_hash: str | None = None
        aproveitados = 0
        for sha, data in revs:
            blob = git("show", f"{sha}:{caminho}")
            if not blob.strip():
                continue
            h = hashlib.sha256(blob.encode("utf-8", "replace")).hexdigest()
            if h == anterior_hash:
                continue  # rebuild sem mudanca de numero: nao e evento de publicacao
            anterior_hash = h

            agregado = agregar(blob, campo, modo)
            if not agregado:
                continue
            aproveitados += 1
            for (comp, uf), valor in agregado.items():
                linhas.append({
                    "base": base, "metrica": metrica, "competencia": comp,
                    "uf_sigla": uf, "valor": valor, "extraido_em": data,
                    "origem": f"git:{sha[:10]} {caminho}",
                })
        print(f"[{base}] {caminho}: {len(revs)} commits -> "
              f"{aproveitados} extracoes distintas", flush=True)

    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    # Mesma data com dois commits: fica o ultimo, que e o estado publicado do dia.
    return (df.sort_values(["base", "metrica", "competencia", "uf_sigla", "extraido_em"])
              .drop_duplicates(["base", "metrica", "competencia", "uf_sigla", "extraido_em"],
                               keep="last")
              .reset_index(drop=True))


def resumo(df: pd.DataFrame) -> None:
    """O que a serie ja permite dizer — e o que ainda nao permite."""
    chave = ["base", "metrica", "competencia", "uf_sigla"]
    n = df.groupby(chave, observed=True).size()
    print(f"\nextracoes por serie: min={n.min()} mediana={int(n.median())} max={n.max()}")
    if n.max() < 2:
        print("Uma extracao por serie: nenhuma revisao observavel ainda.")
        return

    d = df.sort_values("extraido_em").groupby(chave, observed=True)["valor"]
    variacao = ((d.last() / d.first() - 1) * 100).replace([float("inf"), -float("inf")], pd.NA).dropna()
    mexeram = variacao[variacao.abs() > 0.001]
    print(f"series com 2+ extracoes: {len(variacao)}")
    print(f"series que MUDARAM de valor: {len(mexeram)} "
          f"({len(mexeram) / len(variacao) * 100:.1f}%)")
    if len(mexeram):
        print(f"variacao: mediana {mexeram.median():+.3f}% | "
              f"min {mexeram.min():+.3f}% | max {mexeram.max():+.3f}%")
        print("\nmaiores revisoes:")
        for (b, m, c, uf), v in mexeram.abs().nlargest(8).items():
            print(f"  {b:<6} {c:<8} {uf:<3} {variacao.loc[(b, m, c, uf)]:+8.3f}%")
    else:
        print("Nenhuma serie mudou de valor. Com o historico curto disponivel isso\n"
              "NAO significa que a fonte e estavel: pode ser que o pipeline nao\n"
              "tenha reingerido no periodo. So a gravacao por execucao separa os casos.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--resumo", action="store_true",
                    help="so analisa e imprime, sem gravar o parquet")
    args = ap.parse_args()

    df = coletar()
    if df.empty:
        sys.exit("nada coletado — o historico de site/public/sdata/ esta vazio?")

    print(f"\n{len(df):,} linhas | {df['extraido_em'].nunique()} datas de extracao "
          f"| {df['competencia'].nunique()} competencias")
    resumo(df)

    if args.resumo:
        return
    MARTS.mkdir(parents=True, exist_ok=True)
    destino = MARTS / "snapshot_publicacao.parquet"
    df.to_parquet(destino, index=False)
    print(f"\ngravado: {destino}")
    print("publicar com: python scripts/_subir_mart.py snapshot_publicacao")


if __name__ == "__main__":
    main()
