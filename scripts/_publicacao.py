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
    if "SUPABASE_URL" not in env:
        raise SystemExit("SUPABASE_URL ausente (.env ou ambiente)")
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

def exportar_do_postgres(tabela: str, env: dict[str, str], destino: Path,
                         quieto: bool = False) -> Path:
    """Reexporta uma tabela inteira do Postgres para Parquet local.

    Caminho de BOOTSTRAP, não o estado desejado — ver o cabeçalho do módulo.
    Pagina de 1000 em 1000 porque é o teto do PostgREST (pedir mais devolve
    1000 assim mesmo).
    """
    url = env["SUPABASE_URL"].rstrip("/")
    chave = env["SUPABASE_ANON_KEY"]
    cabecalho = {"apikey": chave, "Authorization": f"Bearer {chave}"}
    linhas: list[dict] = []
    offset = 0
    while True:
        r = requests.get(
            f"{url}/rest/v1/{tabela}",
            headers={**cabecalho, "Range-Unit": "items",
                     "Range": f"{offset}-{offset + PAGINA_REST - 1}"},
            params={"select": "*"}, timeout=120)
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
    destino.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(linhas).to_parquet(destino, compression=COMPRESSAO, index=False)
    return destino


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
