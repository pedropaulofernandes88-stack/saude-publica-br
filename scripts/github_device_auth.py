"""Fluxo de autorização por código de dispositivo do GitHub (OAuth device flow).

Usa o client_id público do GitHub CLI. Imprime o código para o usuário aprovar
em https://github.com/login/device e aguarda; ao final grava o token em
%TEMP%/gh_token.txt para o `gh auth login --with-token`.
"""
import sys
import time
import tempfile
from pathlib import Path

import requests

CLIENT_ID = "178c6fc778ccc68e1d6a"  # GitHub CLI (público)

r = requests.post(
    "https://github.com/login/device/code",
    data={"client_id": CLIENT_ID, "scope": "repo workflow"},
    headers={"Accept": "application/json"},
    timeout=30,
)
r.raise_for_status()
d = r.json()
print(f"CODIGO: {d['user_code']}", flush=True)
print(f"URL: {d['verification_uri']}", flush=True)

interval = d.get("interval", 5)
deadline = time.time() + d.get("expires_in", 900)
while time.time() < deadline:
    time.sleep(interval)
    t = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": CLIENT_ID,
            "device_code": d["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        },
        headers={"Accept": "application/json"},
        timeout=30,
    ).json()
    if "access_token" in t:
        out = Path(tempfile.gettempdir()) / "gh_token.txt"
        out.write_text(t["access_token"], encoding="ascii")
        print(f"AUTORIZADO — token salvo em {out}", flush=True)
        sys.exit(0)
    if t.get("error") in ("authorization_pending", "slow_down"):
        if t.get("error") == "slow_down":
            interval += 5
        continue
    sys.exit(f"ERRO: {t}")
sys.exit("EXPIRADO: o código não foi autorizado a tempo")
