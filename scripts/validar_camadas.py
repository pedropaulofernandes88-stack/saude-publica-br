"""
validar_camadas.py — confere que as quatro camadas contam a mesma história
==========================================================================

O projeto distribui os mesmos dados por quatro caminhos:

    manifesto (git)  →  Parquet (Storage)  →  Postgres (API)  →  sdata (site)

Cada um deles já tinha alguma verificação interna. Nenhum tinha verificação
ENTRE eles — e foi exatamente aí que o defeito morou: 14 das 35 tabelas servidas
pela API nunca tiveram Parquet publicado, enquanto a página /dados chamava o
conjunto de "a base completa". Nada checava, porque nada olhava duas camadas ao
mesmo tempo.

    .venv311/Scripts/python scripts/validar_camadas.py
    .venv311/Scripts/python scripts/validar_camadas.py --rapido
    .venv311/Scripts/python scripts/validar_camadas.py --publicacao 2026-08-23

Sai com código ≠ 0 se qualquer camada divergir. Feito para rodar no CI.

O QUE É CONFERIDO
-----------------
1. manifesto → Storage   cada tabela tem arquivo, e o SHA-256 bate
2. manifesto → Postgres  a contagem de linhas bate com a tabela servida
3. histórico             toda publicação referenciada ainda tem sua cópia imutável
4. manifesto → sdata     os agregados congelados no site batem com o publicado
5. cobertura             a API não serve tabela que a publicação desconhece

O item 5 é o que teria pego o defeito original.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _publicacao import (  # noqa: E402
    BUCKET,
    baixar_do_storage,
    carregar_env,
    carregar_manifesto,
    contar_no_postgres,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SDATA = ROOT / "site" / "public" / "sdata"

FALHAS: list[str] = []


def check(nome: str, ok: bool, detalhe: str = "") -> bool:
    print(f"[{'OK ' if ok else 'FALHOU'}] {nome} {detalhe}", flush=True)
    if not ok:
        FALHAS.append(nome)
    return ok


# ---------------------------------------------------------------------------

def tabelas_servidas(env: dict) -> set[str]:
    """O que a API pública realmente expõe, segundo o próprio PostgREST.

    Ler do OpenAPI em vez de uma lista escrita à mão é o que torna a checagem de
    cobertura honesta: uma tabela nova aparece aqui sozinha, e a publicação
    passa a ter de explicá-la.

    Exige a chave de ESCRITA: o PostgREST responde ao endpoint raiz com
    "Only the `service_role` API key can..." para qualquer outra. É introspecção
    de operador, não consulta de cliente — roda na máquina de publicação e no
    CI, nunca no navegador.
    """
    url = env["SUPABASE_URL"].rstrip("/")
    chave = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not chave:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY ausente — a checagem de cobertura lê o "
            "OpenAPI do PostgREST, que só responde à chave de serviço")
    r = requests.get(f"{url}/rest/v1/",
                     headers={"apikey": chave, "Accept": "application/openapi+json"},
                     timeout=60)
    r.raise_for_status()
    caminhos = r.json().get("paths", {})
    return {p.lstrip("/") for p in caminhos
            if p.startswith("/") and p != "/" and "{" not in p
            and (p.lstrip("/").startswith(("mart_", "dim_")))}


def conferir_storage(man, env: dict, rapido: bool) -> None:
    print("\n── manifesto → Storage ──────────────────────────────────────")
    for nome, t in sorted(man.tabelas.items()):
        try:
            dados = baixar_do_storage(f"{nome}.parquet", env)
        except Exception as exc:
            check(f"{nome}: arquivo atual existe", False, str(exc)[:80])
            continue
        if rapido:
            check(f"{nome}: arquivo atual existe", True, f"{len(dados)/1e6:.1f} MB")
            continue
        sha = hashlib.sha256(dados).hexdigest()
        check(f"{nome}: SHA-256 do arquivo publicado", sha == t.sha256,
              "" if sha == t.sha256 else f"manifesto={t.sha256[:12]}… storage={sha[:12]}…")


def conferir_postgres(man, env: dict) -> None:
    print("\n── manifesto → Postgres ─────────────────────────────────────")
    for nome, t in sorted(man.tabelas.items()):
        if not t.servida:
            # Ausência aqui é o estado DESEJADO, e por isso vira checagem
            # positiva: se a tabela reaparecer na API, alguém a recarregou sem
            # atualizar o contrato, e o orçamento do banco estoura em silêncio.
            try:
                n = contar_no_postgres(nome, env)
            except Exception:
                check(f"{nome}: publicada sem ser servida (esperado)", True, "ausente da API")
                continue
            check(f"{nome}: publicada sem ser servida (esperado)", False,
                  f"reapareceu na API com {n:,} linhas")
            continue
        try:
            n = contar_no_postgres(nome, env)
        except Exception as exc:
            check(f"{nome}: tabela consultável", False, str(exc)[:80])
            continue
        check(f"{nome}: linhas manifesto == banco", n == t.linhas,
              f"manifesto={t.linhas:,} banco={n:,}")


def conferir_historico(man, env: dict) -> None:
    """Toda publicação citada como origem ainda precisa ter sua cópia imutável.

    É o que dá sentido a "publicações historicamente completas": se o arquivo de
    uma publicação antiga sumir, o manifesto que aponta para ela vira promessa
    vazia.
    """
    print("\n── histórico imutável ───────────────────────────────────────")
    url = env["SUPABASE_URL"].rstrip("/")
    for nome, t in sorted(man.tabelas.items()):
        alvo = f"{url}/storage/v1/object/public/{BUCKET}/{t.caminho_historico()}"
        try:
            r = requests.head(alvo, timeout=60)
            existe = r.status_code == 200
        except Exception:
            existe = False
        check(f"{nome}: cópia de {t.publicada_em} preservada", existe,
              t.caminho_historico())


def conferir_cobertura(man, env: dict) -> None:
    """A API não pode servir tabela que a publicação desconhece.

    É este item que teria pego o defeito original — 14 tabelas servidas sem
    nenhum arquivo publicado, por dois meses, sem ninguém notar.
    """
    print("\n── cobertura: API × publicação ──────────────────────────────")
    if not env.get("SUPABASE_SERVICE_ROLE_KEY"):
        # Degradar é melhor que falhar OU que passar em silêncio. As outras
        # quatro checagens rodam só com a chave pública; esta é a única que
        # precisa da chave de serviço, e um job vermelho por falta de segredo
        # ensinaria a ignorar o job.
        print("[PULOU] cobertura API × publicação — exige SUPABASE_SERVICE_ROLE_KEY "
              "(o endpoint raiz do PostgREST só responde à chave de serviço)", flush=True)
        return
    try:
        servidas = tabelas_servidas(env)
    except Exception as exc:
        check("OpenAPI do PostgREST legível", False, str(exc)[:90])
        return
    publicadas = set(man.tabelas)
    sem_arquivo = sorted(servidas - publicadas)
    check("toda tabela servida pela API está na publicação",
          not sem_arquivo,
          f"{len(sem_arquivo)} sem arquivo: {', '.join(sem_arquivo[:6])}"
          + ("…" if len(sem_arquivo) > 6 else ""))
    # As marcadas `servida: false` estão fora da API de propósito (V034) e não
    # são fantasmas: fantasma é a tabela que o manifesto promete servir e a API
    # não tem. A checagem oposta — que elas continuem ausentes — é feita em
    # `conferir_postgres`.
    publicadas = {n for n, t in man.tabelas.items() if t.servida}
    fantasmas = sorted(publicadas - servidas)
    check("toda tabela publicada e servida existe na API", not fantasmas,
          f"{len(fantasmas)} fantasmas: {', '.join(fantasmas[:6])}")


def conferir_sdata(man, env: dict) -> None:
    """Os agregados congelados no site têm de bater com o dado publicado.

    `sdata` é gerado do banco no build e versionado no git. Entre um build e
    outro ele envelhece em silêncio: nada avisa que a série congelada deixou de
    corresponder ao que a API devolve.
    """
    print("\n── manifesto → sdata (site) ─────────────────────────────────")
    arquivo = SDATA / "serie_total.json"
    if not arquivo.exists():
        check("serie_total.json presente", False, str(arquivo))
        return
    serie = pd.DataFrame(json.loads(arquivo.read_text(encoding="utf-8")))
    check("serie_total.json legível", not serie.empty, f"{len(serie):,} linhas")

    if "mart_mortalidade_uf_mes" not in man.tabelas:
        return
    try:
        dados = baixar_do_storage("mart_mortalidade_uf_mes.parquet", env)
    except Exception as exc:
        check("mart_mortalidade_uf_mes baixável", False, str(exc)[:80])
        return
    df = pd.read_parquet(io.BytesIO(dados))
    tot = df[(df.capitulo_cid == "TOTAL") & (df.sexo == "TOTAL")
             & (df.faixa_etaria == "TOTAL")] if "capitulo_cid" in df.columns else df

    # `serie_total.json` traz as 27 UFs MAIS uma linha agregada `BR`. Somar tudo
    # conta cada óbito duas vezes — a primeira versão desta checagem fazia isso e
    # acusava 100% de desvio num dado que estava perfeito. O agregado sai fora.
    if "uf_sigla" in serie.columns:
        serie = serie[serie.uf_sigla != "BR"]

    for ano in (2022, 2023):
        do_site = int(serie[serie.ano == ano].obitos.sum()) if "ano" in serie.columns else 0
        do_arquivo = int(tot[tot.ano == ano].obitos.sum()) if "ano" in tot.columns else 0
        if do_arquivo == 0:
            continue
        # Identidade, não ordem de grandeza: as duas camadas saem do mesmo mart,
        # então qualquer diferença significa que uma delas ficou para trás.
        desvio = abs(do_site - do_arquivo) / do_arquivo
        check(f"sdata × Parquet, óbitos {ano}", do_site == do_arquivo,
              f"site={do_site:,} parquet={do_arquivo:,}"
              + (f" desvio={desvio:.2%}" if do_site != do_arquivo else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="Valida a coerência entre as camadas.")
    ap.add_argument("--publicacao", default=None, help="id (padrão: a corrente)")
    ap.add_argument("--rapido", action="store_true",
                    help="pula o download completo para conferir SHA-256")
    ap.add_argument("--pular", nargs="*", default=[],
                    choices=["storage", "postgres", "historico", "cobertura", "sdata"])
    args = ap.parse_args()

    env = carregar_env()
    man = carregar_manifesto(args.publicacao)
    if man is None:
        raise SystemExit(
            "nenhuma publicação encontrada em data/publicacoes/ — rode scripts/publicar.py"
        )

    print(f"publicação {man.id} · gerada em {man.gerado_em} · commit {man.commit}")
    r = man.resumo()
    print(f"{r['n_tabelas']} tabelas · {r['n_linhas']:,} linhas · {r['bytes']/1e6:.1f} MB")
    print(f"origens: {r['por_origem']}")

    if "storage" not in args.pular:
        conferir_storage(man, env, args.rapido)
    if "postgres" not in args.pular:
        conferir_postgres(man, env)
    if "historico" not in args.pular:
        conferir_historico(man, env)
    if "cobertura" not in args.pular:
        conferir_cobertura(man, env)
    if "sdata" not in args.pular:
        conferir_sdata(man, env)

    print()
    if FALHAS:
        print(f"❌ {len(FALHAS)} divergência(s): {FALHAS[:8]}"
              + (" …" if len(FALHAS) > 8 else ""))
        sys.exit(1)
    print("✅ todas as camadas coerentes")


if __name__ == "__main__":
    main()
