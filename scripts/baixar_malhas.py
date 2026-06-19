"""Baixa as malhas municipais (qualidade mínima) das 27 UFs do IBGE e salva em
site/public/sdata/malhas/{UF}.json — para o mapa não depender do IBGE em runtime."""
import json
from pathlib import Path
import requests

UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
       "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]
OUT = Path(__file__).resolve().parents[1] / "site" / "public" / "sdata" / "malhas"
OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}
total = 0
for uf in UFS:
    dest = OUT / f"{uf}.json"
    u = (f"https://servicodados.ibge.gov.br/api/v4/malhas/estados/{uf}"
         "?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima")
    for tent in range(4):
        try:
            r = requests.get(u, headers=H, timeout=120)
            r.raise_for_status()
            gj = r.json()
            n = len(gj.get("features", []))
            dest.write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
            kb = dest.stat().st_size // 1024
            total += dest.stat().st_size
            print(f"{uf}: {n} municípios, {kb} KB", flush=True)
            break
        except Exception as e:
            print(f"{uf} tent {tent+1} erro: {str(e)[:80]}", flush=True)
print(f"TOTAL: {total/1e6:.1f} MB em {OUT}")
