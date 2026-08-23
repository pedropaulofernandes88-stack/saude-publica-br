"""
publicar.py — publica uma versão datada e imutável dos dados
=============================================================

Produz uma **publicação**: o conjunto de Parquet que representa o estado dos
dados numa data, mais o manifesto que o descreve. O manifesto é versionado no
git; os bytes vão para o Storage.

    .venv311/Scripts/python scripts/publicar.py --simular
    .venv311/Scripts/python scripts/publicar.py
    .venv311/Scripts/python scripts/publicar.py --tabelas mart_forecast_demanda_hospital
    .venv311/Scripts/python scripts/publicar.py --bootstrap

O QUE ELE FAZ
-------------
1. reúne o Parquet de cada tabela publicada, preferindo o que o pipeline gerou
   em `data/marts/`; com `--bootstrap`, reexporta do Postgres o que faltar;
2. confere cada Parquet contra a contagem do banco — arquivo que não bate com a
   tabela servida pela API não é publicado;
3. calcula SHA-256, linhas, colunas e faixa de competência;
4. compara com a publicação anterior e sobe ao Storage **só o que mudou**;
5. escreve `data/publicacoes/{id}.json` e atualiza `atual.json`.

O QUE ELE NÃO FAZ
-----------------
Não altera o Postgres. A publicação é de leitura sobre o banco; quem escreve nas
tabelas continua sendo cada pipeline. Isso é deliberado: enquanto o eixo estiver
migrando, publicar não pode ser capaz de corromper a única cópia que ainda é
canônica de facto.

CUSTO DE ARMAZENAMENTO
----------------------
Tabela que não muda entre duas publicações não duplica bytes: o manifesto novo
herda a entrada e aponta para a publicação em que aquele conteúdo entrou. Só o
que mudou ganha cópia em `hist/{id}/`.
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _publicacao import (  # noqa: E402
    MARTS,
    Manifesto,
    baixar_do_storage,
    carregar_env,
    carregar_manifesto,
    commit_atual,
    contar_no_postgres,
    descrever,
    enviar_ao_storage,
    exportar_do_postgres,
    novo_id_publicacao,
    origem_registrada,
    registrar_origem,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

#: As tabelas que compõem uma publicação.
#:
#: Lista explícita, e não "tudo que existe no banco": publicação é uma decisão
#: editorial, não um despejo. Tabela nova entra aqui conscientemente, com alguém
#: tendo verificado que ela deve mesmo ser distribuída como arquivo aberto.
#:
#: A ordem é a de tamanho decrescente, para que uma execução interrompida já
#: tenha resolvido o que custa mais.
TABELAS = [
    "mart_mortalidade_municipio",
    "mart_internacoes_municipio",
    "mart_dengue_semana",
    "mart_internacoes_agravo",
    "mart_los_hospital",
    "mart_cobertura_aps_municipio",
    "mart_mortalidade_uf_mes",
    "mart_fluxo_intermunicipal",
    "mart_demanda_mensal_hospital",
    "mart_mortalidade_causa",
    "mart_leitos_municipio",
    "mart_saude_suplementar_municipio",
    "mart_siops_municipio",
    "mart_hsmr_hospital",
    "mart_forecast_demanda_hospital",
    "mart_dengue_municipio_ano",
    "mart_icsap_municipio",
    # View, não tabela (V016/V025). Entrou aqui depois que a checagem de
    # cobertura do validar_camadas.py a flagrou: ela é servida pela API, é lida
    # pelo site e pela ferramenta MCP `icsap_distancia_dos_pares`, e não tinha
    # arquivo. Do ponto de vista de quem consome, view servida é dado publicado.
    "mart_icsap_pares",
    "mart_natalidade_municipio",
    "mart_qualidade_registro_municipio",
    "mart_internacoes_hospital",
    "mart_excesso_uf_mes",
    "mart_mortalidade_infantil_uf",
    "mart_cnes_municipio",
    "mart_leitos_icsap_municipio",
    "mart_vazio_assistencial_municipio",
    "mart_cobertura_icsap_municipio",
    "mart_equidade_aps_municipio",
    "dim_municipio",
    "dim_populacao",
    "dim_pop_faixa",
    "dim_pop_padrao",
    "dim_ivs",
    "dim_cluster_municipio",
    "dim_cid10_categoria",
    "dim_cid10_capitulo",
]


def semear_do_storage(alvos: list[str], env: dict, quieto: bool) -> int:
    """Traz para `data/marts/` o Parquet que JÁ está publicado no Storage.

    Sem isto, a primeira publicação reexportaria do Postgres as 21 tabelas que
    já têm arquivo — cerca de 3.400 requisições ao PostgREST para reproduzir
    bytes que podem ser baixados em 26 MB. E reexportar não é neutro: um Parquet
    novo gerado a partir das mesmas linhas pode ter SHA-256 diferente (ordem de
    linhas, metadados do escritor), o que marcaria como "mudou" uma tabela que
    não mudou, quebrando os checksums já publicados em /dados.

    A origem fica registrada como `storage-legado`: estes arquivos foram
    publicados à mão, antes de existir pipeline de publicação.
    """
    semeadas = 0
    for tabela in alvos:
        local = MARTS / f"{tabela}.parquet"
        if local.exists():
            continue
        try:
            dados = baixar_do_storage(f"{tabela}.parquet", env)
        except Exception:
            continue  # não existe no Storage; o bootstrap resolve
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(dados)
        registrar_origem(tabela, "storage-legado")
        semeadas += 1
        if not quieto:
            print(f"   ↓ {tabela}: semeado do Storage ({len(dados)/1e6:.1f} MB)", flush=True)
    return semeadas


def _obter_parquet(tabela: str, env: dict, bootstrap: bool,
                   quieto: bool) -> tuple[Path, str] | None:
    """Devolve (caminho, origem) do Parquet a publicar, ou None se indisponível.

    A preferência pelo arquivo local é o que faz o eixo migrar: quanto mais
    tabelas nascem em `data/marts/` pela mão do pipeline, menos o Postgres é a
    origem. A origem real vem do sidecar `.origem.json` — inferir "pipeline"
    para todo arquivo local afirmaria uma linhagem falsa.
    """
    local = MARTS / f"{tabela}.parquet"
    n_banco = contar_no_postgres(tabela, env)

    if local.exists():
        import pandas as pd
        n_local = len(pd.read_parquet(local))
        if n_local == n_banco:
            return local, origem_registrada(tabela) or "pipeline"
        if not quieto:
            print(f"   ! {tabela}: parquet local tem {n_local:,} linhas e o banco "
                  f"{n_banco:,} — desatualizado", flush=True)
        if not bootstrap:
            return None

    if not bootstrap:
        return None
    if not quieto:
        print(f"   ↓ {tabela}: exportando {n_banco:,} linhas do Postgres "
              f"({-(-n_banco // 1000)} requisições)", flush=True)
    exportar_do_postgres(tabela, env, local, quieto=quieto)
    registrar_origem(tabela, "postgres-bootstrap")
    return local, "postgres-bootstrap"


def main() -> None:
    ap = argparse.ArgumentParser(description="Publica uma versão datada dos dados.")
    ap.add_argument("--tabelas", nargs="+", default=None,
                    help="publica só estas (padrão: todas as de TABELAS)")
    ap.add_argument("--bootstrap", action="store_true",
                    help="reexporta do Postgres o que não estiver em data/marts/. "
                         "Marca a origem como postgres-bootstrap no manifesto.")
    ap.add_argument("--semear", action="store_true",
                    help="baixa para data/marts/ o Parquet que já está no Storage, "
                         "em vez de reexportá-lo do Postgres. Use junto com --bootstrap "
                         "na primeira publicação.")
    ap.add_argument("--simular", action="store_true",
                    help="calcula tudo e mostra o plano, sem subir nada nem gravar manifesto")
    ap.add_argument("--quieto", action="store_true")
    args = ap.parse_args()

    env = carregar_env()
    anterior = carregar_manifesto()
    id_pub = novo_id_publicacao()
    alvos = args.tabelas or TABELAS

    print(f"[publicar] publicação {id_pub}"
          f"{f' (anterior: {anterior.id})' if anterior else ' (primeira)'}", flush=True)
    print(f"[publicar] {len(alvos)} tabelas · bootstrap={'sim' if args.bootstrap else 'não'}"
          f" · {'SIMULAÇÃO' if args.simular else 'publicação real'}\n", flush=True)

    if args.semear:
        n = semear_do_storage(alvos, env, args.quieto)
        print(f"[publicar] {n} tabelas semeadas do Storage\n", flush=True)

    manifesto = Manifesto(
        id=id_pub,
        gerado_em=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        commit=commit_atual(),
        anterior=anterior.id if anterior else None,
    )

    mudaram: list[str] = []
    herdadas: list[str] = []
    ausentes: list[str] = []

    for tabela in alvos:
        obtido = _obter_parquet(tabela, env, args.bootstrap, args.quieto)
        if obtido is None:
            ausentes.append(tabela)
            # Herdar a entrada antiga manteria o manifesto "completo" mentindo:
            # ele afirmaria que o arquivo representa o estado atual da tabela.
            if anterior and tabela in anterior.tabelas:
                herdada = anterior.tabelas[tabela]
                manifesto.tabelas[tabela] = herdada
                herdadas.append(tabela)
            continue

        caminho, origem = obtido
        t = descrever(tabela, caminho, origem, id_pub)

        igual_ao_anterior = (
            anterior is not None
            and tabela in anterior.tabelas
            and anterior.tabelas[tabela].sha256 == t.sha256
        )
        if igual_ao_anterior:
            # Conteúdo idêntico: herda a publicação de origem e não duplica bytes.
            t.publicada_em = anterior.tabelas[tabela].publicada_em
            t.origem = anterior.tabelas[tabela].origem
            manifesto.tabelas[tabela] = t
            herdadas.append(tabela)
            if not args.quieto:
                print(f"   = {tabela}: inalterada desde {t.publicada_em}", flush=True)
            continue

        manifesto.tabelas[tabela] = t
        mudaram.append(tabela)
        if not args.quieto:
            print(f"   + {tabela}: {t.linhas:,} linhas · {t.bytes/1e6:.1f} MB · "
                  f"{t.sha256[:12]}… · origem={origem}", flush=True)

        if not args.simular:
            enviar_ao_storage(caminho, f"{tabela}.parquet", env)
            enviar_ao_storage(caminho, t.caminho_historico(), env)

    print(f"\n[publicar] mudaram: {len(mudaram)} · herdadas: {len(herdadas)} · "
          f"sem arquivo: {len(ausentes)}", flush=True)
    if ausentes:
        print(f"[publicar] sem Parquet disponível: {', '.join(ausentes)}", flush=True)
        print("           rode com --bootstrap para reexportá-las do Postgres", flush=True)

    resumo = manifesto.resumo()
    print(f"[publicar] manifesto: {resumo['n_tabelas']} tabelas · "
          f"{resumo['n_linhas']:,} linhas · {resumo['bytes']/1e6:.1f} MB", flush=True)
    print(f"[publicar] por origem: {resumo['por_origem']}", flush=True)

    if args.simular:
        print("\n[publicar] SIMULAÇÃO — nada foi enviado nem gravado.", flush=True)
        return

    destino = manifesto.salvar()
    manifesto_remoto = f"publicacoes/{id_pub}.json"
    enviar_ao_storage(destino, manifesto_remoto, env)
    enviar_ao_storage(destino, "publicacoes/atual.json", env)
    print(f"\n[ok] manifesto em {destino.relative_to(ROOT)} (versione-o no git)", flush=True)
    print(f"[ok] publicado em {manifesto_remoto} e publicacoes/atual.json", flush=True)


if __name__ == "__main__":
    main()
