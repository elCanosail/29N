#!/usr/bin/env python3
"""cron_diario.py — exploración diaria de nuevas encuestas hasta el 29N (29N).

Qué hace (v1, detección y reporte — la ingesta con curación manual es posterior
y aplica la regla de la ficha técnica):

  1. Encuestadores privados: recorre las páginas de listing conocidas
     (electografica.com, imop.es) y detecta URLs de encuestas nuevas frente al
     corpus ya indexado (web/src/data/encuestas.json). Las candidatas se
     persisten en data/processed/cron/candidatas.json.
  2. CIS: carga la primera página del catálogo (ordenada por fecha de creación,
     los últimos estudios primero) con Chromium headless (playwright) — el
     listado se pinta por JS y dispara anti-bot sin navegador — y detecta
     estudios nuevos frente a pipeline/cis/catalog.json.
  3. Imprime un informe: el scheduler lo entrega al chat del proyecto.

Auto-límite: tras el 29N (2026-11-29) informa que la exploración terminó y
pide retirar la automatización.

v2 previsto (si se pide): ingesta automática de los estudios CIS nuevos con el
pipeline validado (fetch + normalize ±0,1 pp) y regeneración + deploy de la web.
"""
import datetime
import json
import os
import re
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
LIMITE = datetime.date(2026, 11, 29)
CATALOGO_URL = ("https://www.cis.es/es/estudios/catalogo?catalogo=estudio"
                "&sort=createDateBDE-&t=0&delta=200&start=0")
LISTINGS = ["https://www.electografica.com/", "https://www.imop.es/"]


def informe(msg):
    print(msg)


def urls_conocidas():
    conocidas = set()
    enc = os.path.join(REPO, "web", "src", "data", "encuestas.json")
    if os.path.exists(enc):
        datos = json.load(open(enc, encoding="utf-8"))
        for e in datos.get("encuestas", []):
            if e.get("url"):
                conocidas.add(e["url"].rstrip("/"))
    return conocidas


def explora_privados(conocidas):
    candidatas = []
    for url in LISTINGS:
        try:
            req = urllib.request.Request(url, headers=UA)
            html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as exc:
            informe(f"- ⚠ {url}: error de acceso ({exc})")
            continue
        for m in re.finditer(r'href="(https?://[^"]+)"', html):
            u = m.group(1).rstrip("/")
            bajo = u.lower()
            if any(p in bajo for p in ("encuesta", "sondeo", "barometro", "barómetro")) \
                    and u not in conocidas and u not in candidatas:
                candidatas.append(u)
    return candidatas


def persiste_candidatas(candidatas, hoy):
    if not candidatas:
        return
    out = os.path.join(REPO, "data", "processed", "cron", "candidatas.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    previas = []
    if os.path.exists(out):
        previas = json.load(open(out, encoding="utf-8"))
    conocidas_prev = {p.get("url") for p in previas}
    for u in candidatas:
        if u not in conocidas_prev:
            previas.append({"url": u, "detectada": hoy.isoformat()})
    json.dump(previas, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def explora_cis():
    from playwright.sync_api import sync_playwright
    slugs = set()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA["User-Agent"])
        page.goto(CATALOGO_URL, timeout=60000, wait_until="networkidle")
        hrefs = page.eval_on_selector_all(
            "a[href*='/es/estudios/']", "els => els.map(e => e.getAttribute('href'))")
        browser.close()
    for h in hrefs or []:
        m = re.search(r"/es/estudios/([^/?#]+)", h)
        if m:
            slugs.add(m.group(1).rstrip("/"))
    cat = os.path.join(REPO, "pipeline", "cis", "catalog.json")
    conocidos = set()
    if os.path.exists(cat):
        for e in json.load(open(cat, encoding="utf-8")):
            conocidos.add((e.get("slug") or "").rstrip("/"))
    return sorted(slugs - conocidos - {""})


def main():
    hoy = datetime.date.today()
    if hoy > LIMITE:
        informe(f"EXPLORACIÓN COMPLETADA: el 29N ({LIMITE}) ya ha pasado. "
                "Retirar esta automatización (automations remove).")
        return 0

    dias = (LIMITE - hoy).days
    informe(f"## Exploración diaria de encuestas — quedan {dias} días para el 29N")
    informe("")

    conocidas = urls_conocidas()

    candidatas = explora_privados(conocidas)
    if candidatas:
        informe(f"- 📰 {len(candidatas)} URLs candidatas nuevas de encuestadores "
                "(pendientes de curación con ficha técnica):")
        for u in candidatas[:10]:
            informe(f"  - {u}")
        persiste_candidatas(candidatas, hoy)
    else:
        informe("- 📰 Sin candidatas nuevas de encuestadores privados.")
    informe("")

    try:
        nuevos_cis = explora_cis()
    except Exception as exc:
        informe(f"- ⚠ CIS: comprobación con navegador fallida "
                f"({type(exc).__name__}: {exc})")
        nuevos_cis = None
    if nuevos_cis:
        informe(f"- 🏛️ {len(nuevos_cis)} estudios CIS nuevos detectados en la primera "
                "página del catálogo (pendientes de catalogar e ingesta):")
        for s in nuevos_cis[:10]:
            informe(f"  - {s}")
    elif nuevos_cis is not None:
        informe("- 🏛️ Sin estudios CIS nuevos en la primera página del catálogo.")
    informe("")
    informe("_Exploración v1 (detección). La ingesta con curación se hace con el "
            "pipeline validado — regla de la ficha técnica._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
