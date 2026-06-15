import requests

H = {"User-Agent": "Mozilla/5.0"}
# 1) dados.gov.br CKAN — procurar dataset do IVS / Atlas Vulnerabilidade Social
try:
    r = requests.get("https://dados.gov.br/api/3/action/package_search",
                     params={"q": "vulnerabilidade social atlas ipea", "rows": 10},
                     headers=H, timeout=60)
    d = r.json()
    print("dados.gov.br:", r.status_code, "results:", d.get("result", {}).get("count"))
    for p in d.get("result", {}).get("results", [])[:6]:
        print("  PKG:", p.get("name"))
        for res in p.get("resources", [])[:4]:
            print("      ", res.get("format"), res.get("url"))
except Exception as e:
    print("dados.gov.br ERR", str(e)[:120])

# 2) ipeadata OData v4 — filtro correto ($filter precisa de aspas simples)
try:
    u = "http://www.ipeadata.gov.br/api/odata4/Metadados('IVS')"
    r = requests.get(u, headers=H, timeout=60)
    print("ipeadata IVS direct:", r.status_code, r.text[:200])
except Exception as e:
    print("ipeadata ERR", str(e)[:120])
