"""
_publicacao.py — o Parquet datado como fonte canônica, e o manifesto que o prova
================================================================================

Núcleo compartilhado por `publicar.py` (que publica) e `validar_camadas.py` (que
confere). Existir separado é o que impede o publicador e o validador de
divergirem — o mesmo motivo de `_series_forecast.py` existir.

POR QUE ESTE MÓDULO EXISTE
--------------------------
Até aqui a camada canônica de facto era o Postgres, e ela era a pior candidata
possível para o papel. Medido em 2026-08-22:

  * 740 MB, contra 26 MB dos mesmos dados em Parquet;
  * 57 migrações aplicadas, 47 delas com nome ad-hoc e sem arquivo no
    repositório — o banco não se reconstrói a partir do repo;
  * marts sobrescritos no lugar: o valor publicado em junho é irrecuperável;
  * e **nenhuma linha de código subia Parquet para o Storage**. A publicação de
    arquivo sempre foi manual, e por isso 14 das 35 tabelas servidas pela API
    nunca tiveram arquivo nenhum — enquanto a página /dados chamava o conjunto
    de "a base completa".

O eixo se inverte aqui: o **arquivo datado passa a ser a verdade**, e o Postgres
vira cache de consulta reconstruível a partir dele.

O QUE É UMA PUBLICAÇÃO
----------------------
Um conjunto imutável de Parquet mais um manifesto que o descreve. O manifesto é
versionado no git (`data/publicacoes/{id}.json`); os bytes ficam no Storage.
O git guarda a verdade *sobre* os arquivos sem guardar os arquivos.

Dois caminhos no Storage, de propósito:

    dados/{tabela}.parquet              o estado ATUAL, caminho estável
    dados/hist/{id}/{tabela}.parquet    a cópia imutável daquela publicação

O caminho estável preserva todos os links e checksums já publicados em /dados. O
caminho histórico só recebe cópia quando o conteúdo MUDA — tabela que não mudou
entre duas publicações não duplica bytes, e o manifesto aponta para a publicação
em que ela mudou pela última vez.

LINHAGEM
--------
Cada tabela registra `origem`:

    "pipeline"            o Parquet saiu do pipeline que gera o dado — o estado
                          desejado, em que o arquivo nasce canônico;
    "postgres-bootstrap"  o Parquet foi reexportado do Postgres porque era o
                          único lugar onde o dado existia.

O bootstrap é honesto e temporário: reexportar do banco é justamente devolver o
eixo a ele. O campo existe para que a dívida fique visível e mensurável, em vez
de silenciosa.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
PUBLICACOES = ROOT / "data" / "publicacoes"
BUCKET = "dados"

#: Limite rígido do PostgREST. Pedir mais devolve 1000 assim mesmo — medido.
PAGINA_REST = 1000

#: Compressão do Parquet canônico. zstd porque é o que os pipelines já usam;
#: trocar mudaria o SHA-256 de todo arquivo sem mudar um único dado.
COMPRESSAO = "zstd"


# ---------------------------------------------------------------------------
# Ambiente
# ---------------------------------------------------------------------------

#: URL e chave de LEITURA públicas do projeto.
#:
#: São os mesmos valores já embutidos em `scripts/validate_data.py`, em
#: `site/lib/api.ts` e no workflow de keep-alive — a chave `anon` é pública por
#: desenho do PostgREST, e o README a divulga. Ter o padrão aqui é o que permite
#: rodar a validação de leitura no CI sem nenhum segredo configurado; a chave de
#: ESCRITA nunca tem padrão e continua vindo só do ambiente.
URL_PUBLICA = "https://zekjhmxjamatlxpkykde.supabase.co"
ANON_PUBLICA = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpla2pobXhqYW1hdGx4cGt5a2RlIiwicm9sZSI6ImFub24i"
    "LCJpYXQiOjE3ODEwNzY4MzIsImV4cCI6MjA5NjY1MjgzMn0."
    "px8FcU0QK8w9v95kwGlGzASKpY3drsxAvFe0e6wUoCU"
)


def carregar_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for linha in f.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, _, v = linha.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})

    # Variável VAZIA conta como ausente. O GitHub Actions materializa
    # `${{ secrets.X }}` como string vazia quando o segredo não existe, e o
    # repositório não tem nenhum segredo configurado. Sem esta linha,
    # `setdefault` não dispara — a chave existe, só está vazia — e o script
    # tenta montar URL a partir de "", falhando com "Invalid URL: No schema
    # supplied". Foi exatamente assim que o primeiro job de CI quebrou.
    env = {k: v for k, v in env.items() if v}

    env.setdefault("SUPABASE_URL", URL_PUBLICA)
    env.setdefault("SUPABASE_ANON_KEY", ANON_PUBLICA)
    return env


def commit_atual() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "desconhecido"
    except Exception:
        return "desconhecido"


# ---------------------------------------------------------------------------
# Entrada do manifesto
# ---------------------------------------------------------------------------

@dataclass
class Tabela:
    """Uma tabela dentro de uma publicação.

    `publicada_em` é o id da publicação em que este conteúdo apareceu pela
    última vez. Quando uma tabela não muda, a publicação nova a herda: o
    manifesto continua completo, mas nenhum byte é duplicado no Storage.
    """

    nome: str
    linhas: int
    bytes: int
    sha256: str
    colunas: list[str]
    origem: str                      # "pipeline" | "postgres-bootstrap"
    publicada_em: str                # id da publicação onde este sha entrou
    competencia_min: str | None = None
    competencia_max: str | None = None

    def caminho_historico(self) -> str:
        return f"hist/{self.publicada_em}/{self.nome}.parquet"


@dataclass
class Manifesto:
    """O manifesto é o artefato canônico. Os Parquet são o seu corpo."""

    id: str
    gerado_em: str
    commit: str
    anterior: str | None
    tabelas: dict[str, Tabela] = field(default_factory=dict)

    # -- serialização --------------------------------------------------------

    def to_json(self) -> str:
        d = {
            "id": self.id,
            "gerado_em": self.gerado_em,
            "commit": self.commit,
            "anterior": self.anterior,
            "resumo": self.resumo(),
            "tabelas": {n: asdict(t) for n, t in sorted(self.tabelas.items())},
        }
        return json.dumps(d, ensure_ascii=False, indent=2) + "\n"

    @classmethod
    def from_json(cls, texto: str) -> Manifesto:
        d = json.loads(texto)
        m = cls(id=d["id"], gerado_em=d["gerado_em"], commit=d["commit"],
                anterior=d.get("anterior"))
        for nome, t in d["tabelas"].items():
            m.tabelas[nome] = Tabela(**t)
        return m

    def resumo(self) -> dict:
        return {
            "n_tabelas": len(self.tabelas),
            "n_linhas": sum(t.linhas for t in self.tabelas.values()),
            "bytes": sum(t.bytes for t in self.tabelas.values()),
            "por_origem": {
                origem: sum(1 for t in self.tabelas.values() if t.origem == origem)
                for origem in sorted({t.origem for t in self.tabelas.values()})
            },
            "novas_nesta_publicacao": sorted(
                t.nome for t in self.tabelas.values() if t.publicada_em == self.id
            ),
        }

    # -- persistência --------------------------------------------------------

    def salvar(self) -> Path:
        PUBLICACOES.mkdir(parents=True, exist_ok=True)
        destino = PUBLICACOES / f"{self.id}.json"
        destino.write_text(self.to_json(), encoding="utf-8")
        # `atual.json` é um ponteiro, não uma cópia: duplicar o manifesto criaria
        # duas verdades sobre qual é a publicação corrente.
        (PUBLICACOES / "atual.json").write_text(
            json.dumps({"id": self.id, "arquivo": f"{self.id}.json"},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        return destino


def carregar_manifesto(id_pub: str | None = None) -> Manifesto | None:
    """Carrega uma publicação pelo id, ou a corrente quando id é None."""
    if id_pub is None:
        ponteiro = PUBLICACOES / "atual.json"
        if not ponteiro.exists():
            return None
        id_pub = json.loads(ponteiro.read_text(encoding="utf-8"))["id"]
    arquivo = PUBLICACOES / f"{id_pub}.json"
    if not arquivo.exists():
        return None
    return Manifesto.from_json(arquivo.read_text(encoding="utf-8"))


def publicacoes_existentes() -> list[str]:
    if not PUBLICACOES.exists():
        return []
    return sorted(p.stem for p in PUBLICACOES.glob("*.json") if p.stem != "atual")


# ---------------------------------------------------------------------------
# Parquet
# ---------------------------------------------------------------------------

#: Sidecar que registra de onde veio cada Parquet em `data/marts/`.
#:
#: `data/marts/` é ignorado pelo git e recebe arquivo de três procedências
#: diferentes — pipeline, reexportação do Postgres e download do que já estava
#: publicado. Sem este registro, o publicador inferiria "pipeline" para qualquer
#: arquivo local, e o manifesto afirmaria uma linhagem que não é verdade. A
#: dívida de proveniência só é pagável se for medível.
ORIGENS = MARTS / ".origem.json"


#: Chave da proveniência gravada DENTRO do Parquet.
#:
#: O sidecar `.origem.json` é frágil: mora em `data/marts/`, que é ignorado pelo
#: git, e some quando alguém limpa o diretório ou publica de outra máquina. A
#: proveniência precisa viajar com os BYTES — quem recebe o arquivo tem de poder
#: dizer de onde ele veio sem depender de um arquivo ao lado.
CHAVE_ORIGEM = b"saude_em_dado.origem"
CHAVE_PRODUTOR = b"saude_em_dado.produtor"

#: Rótulo para arquivo sem proveniência declarada.
#:
#: NÃO é "pipeline". Assumir pipeline para qualquer arquivo local afirma uma
#: linhagem que ninguém verificou — e foi o que aconteceu:
#: `mart_demanda_mensal_hospital` foi BAIXADO do Postgres por
#: `_baixar_mart_completo.py` e entrou no manifesto rotulado `pipeline`.
ORIGEM_DESCONHECIDA = "desconhecida"
ORIGEM_VIEW = "view"


def views_do_esquema() -> set[str]:
    """Nomes das VIEWs do `schema.sql` versionado.

    View nao tem produtor de arquivo: ela e derivada no banco, e o Parquet dela
    so pode sair de uma exportacao. Rotula-la como `postgres-bootstrap` sugere
    divida a pagar; nao ha divida, ha uma natureza diferente. O nome sai do
    esquema versionado, nunca de lista escrita a mao.
    """
    arquivo = ROOT / "migrations" / "schema" / "schema.sql"
    if not arquivo.exists():
        return set()
    # o schema.sql gerado emite "create or replace view public.x with (...)"
    return set(re.findall(r"create (?:or replace )?view public\.(\w+)",
                          arquivo.read_text(encoding="utf-8"), re.I))


def escrever_parquet(df: pd.DataFrame, destino: Path, origem: str,
                     produtor: str | None = None) -> Path:
    """Grava um Parquet declarando quem o produziu, no próprio arquivo.

    Usado pelos pipelines no lugar de `df.to_parquet(...)`. O custo é uma
    dependência a mais (pyarrow, que já vem com o pandas do projeto) e alguns
    bytes de metadado; o ganho é que a linhagem deixa de depender de um sidecar
    que pode sumir.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    tabela_arrow = pa.Table.from_pandas(df, preserve_index=False)
    meta = dict(tabela_arrow.schema.metadata or {})
    meta[CHAVE_ORIGEM] = origem.encode()
    if produtor:
        meta[CHAVE_PRODUTOR] = produtor.encode()
    tabela_arrow = tabela_arrow.replace_schema_metadata(meta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(tabela_arrow, destino, compression=COMPRESSAO)
    return destino


def acumular_parquet(df_novo: pd.DataFrame, destino: Path, tabela: str,
                     origem: str, produtor: str | None = None) -> tuple[Path, int, int]:
    """Funde uma competência no Parquet existente, como o banco faz por upsert.

    POR QUE ISTO EXISTE
    -------------------
    Os pipelines do SIH processam **um ano por execução** (`--ano`, padrão 2024)
    e SOBRESCREVIAM o Parquet local. O Postgres, recebendo upsert com
    `merge-duplicates`, acumulava; o arquivo não. Resultado medido:

        mart_internacoes_agravo     52.861 no arquivo  ×  158.041 no banco
        mart_fluxo_intermunicipal   43.179             ×  156.663
        mart_icsap_municipio         5.570             ×   22.280

    Era esta a razão estrutural de 17 tabelas ficarem em `postgres-bootstrap`: o
    arquivo NÃO PODIA ser canônico, porque só continha a última fatia
    processada. Reexportar do banco era o único jeito de obter a série inteira —
    e reexportar do banco é justamente devolver o eixo a ele.

    Aqui o arquivo passa a acumular com a mesma semântica do upsert: linha com
    a mesma chave primária é substituída, o resto é preservado. A chave sai do
    `schema.sql` versionado, não de uma lista escrita à mão.

    Devolve (caminho, linhas_antes, linhas_depois).
    """
    pk = chaves_primarias().get(tabela)
    if not pk:
        raise RuntimeError(
            f"{tabela}: sem chave primária em schema.sql — acumular sem chave "
            "duplicaria linhas a cada execução")
    presentes = [c for c in pk if c in df_novo.columns]
    if len(presentes) != len(pk):
        raise RuntimeError(
            f"{tabela}: o DataFrame não traz a chave completa "
            f"({'+'.join(pk)}); faltam {set(pk) - set(presentes)}")

    antes = 0
    if destino.exists():
        anterior = pd.read_parquet(destino)
        antes = len(anterior)
        if all(c in anterior.columns for c in pk):
            chaves_novas = set(map(tuple, df_novo[pk].astype(str).itertuples(index=False)))
            manter = ~anterior[pk].astype(str).apply(tuple, axis=1).isin(chaves_novas)
            df_novo = pd.concat([anterior[manter], df_novo], ignore_index=True)

    conferir_chave_unica(tabela, df_novo, pk)
    escrever_parquet(df_novo, destino, origem, produtor)
    return destino, antes, len(df_novo)


def origem_do_parquet(caminho: Path) -> str | None:
    """Lê a proveniência gravada no arquivo, ou None se ele não declarar."""
    try:
        import pyarrow.parquet as pq

        meta = pq.read_schema(caminho).metadata or {}
        valor = meta.get(CHAVE_ORIGEM)
        return valor.decode() if valor else None
    except Exception:
        return None


def registrar_origem(tabela: str, origem: str) -> None:
    MARTS.mkdir(parents=True, exist_ok=True)
    d = json.loads(ORIGENS.read_text(encoding="utf-8")) if ORIGENS.exists() else {}
    d[tabela] = origem
    ORIGENS.write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")


def origem_registrada(tabela: str) -> str | None:
    if not ORIGENS.exists():
        return None
    return json.loads(ORIGENS.read_text(encoding="utf-8")).get(tabela)


def sha256_de(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _competencias(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Extrai a faixa temporal coberta, quando a tabela tem coluna de tempo.

    Serve à completude histórica: o manifesto precisa dizer não só quantas
    linhas, mas de QUE período — é o que permite detectar uma publicação que
    perdeu uma competência sem perder volume.
    """
    for col in ("ano_mes", "competencia", "ano_mes_previsto", "ano", "ano_epi"):
        if col in df.columns:
            s = df[col].dropna()
            if s.empty:
                return None, None
            return str(s.min()), str(s.max())
    return None, None


def descrever(nome: str, caminho: Path, origem: str, id_pub: str) -> Tabela:
    df = pd.read_parquet(caminho)
    cmin, cmax = _competencias(df)
    return Tabela(
        nome=nome,
        linhas=len(df),
        bytes=caminho.stat().st_size,
        sha256=sha256_de(caminho),
        colunas=sorted(map(str, df.columns)),
        origem=origem,
        publicada_em=id_pub,
        competencia_min=cmin,
        competencia_max=cmax,
    )


# ---------------------------------------------------------------------------
# Postgres → Parquet (bootstrap)
# ---------------------------------------------------------------------------

def chaves_primarias() -> dict[str, list[str]]:
    """Chave primária de cada tabela, lida do `schema.sql` versionado.

    Vem do artefato, e não de uma lista escrita aqui: se o esquema mudar, a
    ordenação da exportação acompanha sozinha.
    """
    arquivo = ROOT / "migrations" / "schema" / "schema.sql"
    if not arquivo.exists():
        return {}
    pks: dict[str, list[str]] = {}
    texto = arquivo.read_text(encoding="utf-8")
    for m in re.finditer(
        r"create table if not exists public\.(\w+)\s*\((.*?)\n\);", texto, re.S
    ):
        p = re.search(r"PRIMARY KEY \(([^)]+)\)", m.group(2))
        if p:
            pks[m.group(1)] = [c.strip().strip('"') for c in p.group(1).split(",")]
    return pks


def exportar_do_postgres(tabela: str, env: dict[str, str], destino: Path,
                         quieto: bool = False) -> Path:
    """Reexporta uma tabela inteira do Postgres para Parquet local.

    Caminho de BOOTSTRAP, não o estado desejado — ver o cabeçalho do módulo.
    Pagina de 1000 em 1000 porque é o teto do PostgREST (pedir mais devolve
    1000 assim mesmo).

    A ORDENAÇÃO EXPLÍCITA NÃO É COSMÉTICA. Paginar com LIMIT/OFFSET sem ORDER BY
    é indefinido: o Postgres não promete a mesma ordem entre duas consultas, e
    páginas consecutivas podem se sobrepor — repetindo linhas e perdendo outras.
    Foi o que aconteceu: `mart_internacoes_municipio` saiu com 334.769 linhas e
    apenas 212.893 chaves distintas, e o TOTAL bateu com o banco, porque as
    linhas repetidas ocuparam o lugar das que sumiram. Uma checagem que compara
    só a contagem não enxerga isso; só a violação de PK no rebuild enxergou.
    """
    url = env["SUPABASE_URL"].rstrip("/")
    chave = env["SUPABASE_ANON_KEY"]
    cabecalho = {"apikey": chave, "Authorization": f"Bearer {chave}"}

    pk = chaves_primarias().get(tabela)
    if not pk:
        raise RuntimeError(
            f"{tabela}: sem chave primária conhecida em schema.sql — exportar sem "
            "ordenação determinística produziria linhas duplicadas e ausentes")
    ordem = ",".join(f"{c}.asc" for c in pk)

    linhas: list[dict] = []
    offset = 0
    while True:
        r = requests.get(
            f"{url}/rest/v1/{tabela}",
            headers={**cabecalho, "Range-Unit": "items",
                     "Range": f"{offset}-{offset + PAGINA_REST - 1}"},
            params={"select": "*", "order": ordem}, timeout=120)
        r.raise_for_status()
        lote = r.json()
        linhas.extend(lote)
        if len(lote) < PAGINA_REST:
            break
        offset += PAGINA_REST
        if not quieto and offset % 50_000 == 0:
            print(f"      {tabela}: {offset:,} linhas...", flush=True)
    if not linhas:
        raise RuntimeError(f"{tabela}: consulta devolveu zero linhas")

    df = pd.DataFrame(linhas)
    conferir_chave_unica(tabela, df, pk)
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(destino, compression=COMPRESSAO, index=False)
    return destino


def colunas_obrigatorias() -> dict[str, list[str]]:
    """Colunas `not null` de cada tabela, lidas do `schema.sql` versionado."""
    arquivo = ROOT / "migrations" / "schema" / "schema.sql"
    if not arquivo.exists():
        return {}
    obrig: dict[str, list[str]] = {}
    texto = arquivo.read_text(encoding="utf-8")
    for m in re.finditer(
        r"create table if not exists public\.(\w+)\s*\((.*?)\n\);", texto, re.S
    ):
        cols = []
        for linha in m.group(2).splitlines():
            linha = linha.strip().rstrip(",")
            if not linha or linha.lower().startswith("constraint"):
                continue
            if " not null" in linha.lower():
                cols.append(linha.split()[0].strip('"'))
        if cols:
            obrig[m.group(1)] = cols
    return obrig


def conferir_nao_nulos(tabela: str, df: pd.DataFrame) -> None:
    """Recusa Parquet com NULL em coluna declarada `not null` no destino.

    Terceira guarda, e a que faltava. Contagem de linhas e unicidade de chave
    não bastam: `mart_saude_suplementar_municipio` passou nas duas e falhou ao
    ser recarregado, porque `razao_implausivel` — `not null default false` no
    esquema — saía com NULL em 4 municípios (`NA > 100` devolve NA quando a
    razão não pôde ser calculada).

    Um arquivo que não recarrega no esquema que ele diz representar não é uma
    cópia canônica; é uma cópia parecida.
    """
    obrigatorias = colunas_obrigatorias().get(tabela, [])
    problemas = {
        c: int(df[c].isna().sum())
        for c in obrigatorias
        if c in df.columns and df[c].isna().any()
    }
    if problemas:
        detalhe = ", ".join(f"{c}={n:,}" for c, n in sorted(problemas.items()))
        raise RuntimeError(
            f"{tabela}: NULL em coluna(s) declarada(s) `not null` no schema.sql "
            f"({detalhe}). O arquivo não recarregaria no banco e NÃO será publicado.")


def conferir_chave_unica(tabela: str, df: pd.DataFrame, pk: list[str]) -> None:
    """Recusa um DataFrame cuja chave primária tenha repetição.

    Guarda que faltava: a contagem de linhas batia com o banco enquanto o
    arquivo já estava corrompido. Duplicata na PK é impossível na tabela de
    origem — se aparece no arquivo, o arquivo está errado, ponto.
    """
    presentes = [c for c in pk if c in df.columns]
    if not presentes:
        return
    n, distintas = len(df), len(df[presentes].drop_duplicates())
    if n != distintas:
        raise RuntimeError(
            f"{tabela}: {n:,} linhas para apenas {distintas:,} chaves distintas "
            f"({n - distintas:,} duplicadas em {'+'.join(presentes)}). "
            "O arquivo está corrompido e NÃO será publicado.")


def contar_no_postgres(tabela: str, env: dict[str, str]) -> int:
    """Contagem exata via PostgREST, para conferir o Parquet contra o banco."""
    url = env["SUPABASE_URL"].rstrip("/")
    chave = env["SUPABASE_ANON_KEY"]
    r = requests.get(f"{url}/rest/v1/{tabela}",
                     headers={"apikey": chave, "Authorization": f"Bearer {chave}",
                              "Prefer": "count=exact", "Range-Unit": "items",
                              "Range": "0-0"},
                     params={"select": "*"}, timeout=120)
    r.raise_for_status()
    return int(r.headers.get("content-range", "0/0").split("/")[-1])


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _chave_escrita(env: dict[str, str]) -> str:
    chave = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not chave:
        raise SystemExit(
            "SUPABASE_SERVICE_ROLE_KEY ausente — publicar no Storage exige a chave de escrita"
        )
    return chave


def _cabecalho_escrita(chave: str) -> dict[str, str]:
    """Cabeçalhos de autenticação que funcionam com os DOIS formatos de chave.

    O Supabase migrou as chaves de API do JWT legado (`eyJ…`, três segmentos)
    para o formato opaco (`sb_secret_…`). O Storage rejeita o formato novo em
    `Authorization: Bearer` com "Invalid Compact JWS", porque tenta parseá-lo
    como JWS — mas aceita a mesma chave no cabeçalho `apikey`. O PostgREST
    aceita os dois.

    Medido nesta base: `Bearer sb_secret_…` devolve 400/AccessDenied; `apikey:
    sb_secret_…` devolve 200. Mandar `Bearer` só quando a chave é de fato um JWT
    mantém a compatibilidade com quem ainda usa a chave antiga, sem quebrar
    quem já migrou.
    """
    cab = {"apikey": chave}
    if chave.count(".") == 2:          # JWT legado
        cab["Authorization"] = f"Bearer {chave}"
    return cab


def enviar_ao_storage(caminho_local: Path, caminho_remoto: str,
                      env: dict[str, str], tentativas: int = 4) -> None:
    """Sobe um arquivo ao bucket público, sobrescrevendo se já existir."""
    url = env["SUPABASE_URL"].rstrip("/")
    chave = _chave_escrita(env)
    dados = caminho_local.read_bytes()
    alvo = f"{url}/storage/v1/object/{BUCKET}/{caminho_remoto}"
    for tentativa in range(tentativas):
        r = requests.post(alvo, data=dados, timeout=600, headers={
            **_cabecalho_escrita(chave),
            "Content-Type": "application/octet-stream",
            "x-upsert": "true",
        })
        if r.status_code in (200, 201):
            return
        if tentativa == tentativas - 1 or r.status_code in (401, 403):
            raise RuntimeError(
                f"upload de {caminho_remoto} falhou: HTTP {r.status_code} {r.text[:200]}")
        time.sleep(3 * (tentativa + 1))


def baixar_do_storage(caminho_remoto: str, env: dict[str, str]) -> bytes:
    url = env["SUPABASE_URL"].rstrip("/")
    r = requests.get(f"{url}/storage/v1/object/public/{BUCKET}/{caminho_remoto}",
                     timeout=600)
    r.raise_for_status()
    return r.content


def sha256_no_storage(caminho_remoto: str, env: dict[str, str]) -> str | None:
    """SHA-256 do arquivo publicado, ou None se ele não existir."""
    try:
        return hashlib.sha256(baixar_do_storage(caminho_remoto, env)).hexdigest()
    except requests.HTTPError:
        return None


def novo_id_publicacao() -> str:
    """Id da publicação: a data UTC, com sufixo se já houver uma no mesmo dia.

    Data e não timestamp porque o id aparece em caminho de URL e em nome de
    arquivo versionado — legibilidade importa mais que precisão de segundo.
    """
    hoje = datetime.now(UTC).strftime("%Y-%m-%d")
    existentes = publicacoes_existentes()
    if hoje not in existentes:
        return hoje
    n = 2
    while f"{hoje}.{n}" in existentes:
        n += 1
    return f"{hoje}.{n}"


def ler_parquet_de_bytes(dados: bytes) -> pd.DataFrame:
    return pd.read_parquet(io.BytesIO(dados))
