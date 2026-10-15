#!/usr/bin/env python3
"""Descarga (reanudable) de los microdatos del CIS para los estudios del catálogo.

Estrategia verificada (docs/notes/cis-probe.md + docs/notes/cis-ingest.md):
  - La ficha de cada estudio es HTML estático en `https://www.cis.es/es/estudios/<slug>`
    e incluye un bloque JSON-LD (`application/ld+json`) con un array `distribution`
    donde cada documento trae su `contentUrl` directo:
        * "Fichero datos"  -> .../MD<estudio>.zip   (application/zip)
        * "Estimación de voto" -> .../<estudio>_Estimacion*.pdf
        * "Cuestionario", "Ficha técnica", ...
    No hace falta formulario ni sesión: la URL del ZIP es pública.
  - El sitio aplica anti-bot (HTTP 302 a /__cis_antibot) a peticiones repetidas
    sin JS. Por eso: backoff exponencial + pausa entre peticiones. Si una petición
    devuelve 302 a __cis_antibot, se nombre como bloqueo y se reintenta tras una
    pausa larga.

Uso:
  python fetch_microdata.py --catalog pipeline/cis/catalog.json            # todo
  python fetch_microdata.py --only 3411 3141 3263                          # selección
  python fetch_microdata.py --priority generales                           # prioriza generales
  python fetch_microdata.py --limit 5                                      # solo N

Estado: data/raw/cis/manifest.json (reanudable; no se re-descarga lo ya completado).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(BASE))
RAW = os.path.join(REPO, "data/raw/cis")
MANIFEST = os.path.join(RAW, "manifest.json")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

LDJSON = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)


def http_get(url, referer=None, timeout=120, retries=5, base_sleep=25):
    """GET con backoff exponencial; detecta el anti-bot (302 -> __cis_antibot)."""
    headers = {
        "User-Agent": UA,
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                final = r.geturl()
                if "__cis_antibot" in final:
                    raise urllib.error.HTTPError(url, 302, "antibot", r.headers, None)
                return r.read(), r.status, dict(r.headers)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504, 302):
                sleep = base_sleep * (2 ** attempt)
                ra = e.headers.get("Retry-After") if e.headers else None
                if ra and str(ra).isdigit():
                    sleep = max(sleep, int(ra))
                sys.stderr.write(f"  [{e.code}] {url[:80]}  espero {sleep}s "
                                 f"({attempt + 1}/{retries})\n")
                time.sleep(sleep)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            sleep = base_sleep * (2 ** attempt)
            sys.stderr.write(f"  [{type(e).__name__}] {url[:80]}  espero {sleep}s\n")
            time.sleep(sleep)
    raise RuntimeError(f"fallo tras {retries} intentos: {url} ({last})")


def _walk_distribution(node, docs):
    """Recorre recursivamente (incl. @graph) y recoge los bloques `distribution`."""
    if isinstance(node, dict):
        for d in (node.get("distribution") or []):
            if isinstance(d, dict):
                name = (d.get("name") or "").strip()
                url = d.get("contentUrl") or d.get("url")
                if name and url:
                    docs[name] = url
        for v in node.values():
            _walk_distribution(v, docs)
    elif isinstance(node, list):
        for v in node:
            _walk_distribution(v, docs)


def parse_documents(html):
    """Devuelve dict nombre->url de los documentos del JSON-LD de la ficha."""
    docs = {}
    for m in LDJSON.finditer(html):
        txt = m.group(1).strip()
        try:
            data = json.loads(txt)
        except json.JSONDecodeError:
            continue
        _walk_distribution(data, docs)
    return docs


def fetch_study(rec, pause=12):
    est = rec["estudio"]
    outdir = os.path.join(RAW, est)
    zips = []
    if os.path.isdir(outdir):
        zips = [f for f in os.listdir(outdir) if re.match(r"MD\d+.*\.zip$", f)]
    # ya descomprimido?
    if zips:
        for z in zips:
            sub = os.path.join(outdir, z[:-4])
            if os.path.isdir(sub) and any(f.startswith("DA") or f.endswith(".sav")
                                          or f.endswith("_num.csv") for f in os.listdir(sub)):
                return {"status": "done", "md_zip": zips[0], "reused": True}
    # 1) ficha
    html, status, _ = http_get(rec["url"])
    docs = parse_documents(html.decode("utf-8", "replace"))
    zurl = next((u for n, u in docs.items() if n.lower().startswith("fichero datos")), None)
    if not zurl:
        zurl = next((u for u, in [(u,) for u in docs.values()] if u.lower().endswith(".zip")), None)
    if not zurl:
        return {"status": "no_data_link", "docs": sorted(docs), "http": status}
    estpdf = next((u for n, u in docs.items() if "estimaci" in n.lower()), None)
    time.sleep(pause)
    # 2) zip
    os.makedirs(outdir, exist_ok=True)
    zname = zurl.split("?")[0].rstrip("/").split("/")[-1]
    if not zname.lower().endswith(".zip"):
        zname = f"MD{est}.zip"
    zpath = os.path.join(outdir, zname)
    data, st, _ = http_get(zurl, referer=rec["url"])
    with open(zpath, "wb") as f:
        f.write(data)
    # 3) descomprimir
    sub = os.path.join(outdir, zname[:-4])
    try:
        with zipfile.ZipFile(zpath) as z:
            z.extractall(sub)
        ok = True
    except zipfile.BadZipFile:
        ok = False
    # 4) estimación de voto (PDF) para validación
    if estpdf:
        try:
            time.sleep(pause)
            pdata, _, _ = http_get(estpdf, referer=rec["url"])
            os.makedirs(os.path.join(RAW, "estimacion"), exist_ok=True)
            with open(os.path.join(RAW, "estimacion", f"est{est}.pdf"), "wb") as f:
                f.write(pdata)
        except Exception as e:  # noqa
            sys.stderr.write(f"  estimación {est}: {e}\n")
    return {"status": "done" if ok else "bad_zip", "md_url": zurl, "est_pdf": estpdf,
            "bytes": len(data), "http": st}


def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST))
    return {}


def save_manifest(m):
    os.makedirs(RAW, exist_ok=True)
    json.dump(m, open(MANIFEST, "w"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=os.path.join(BASE, "catalog.json"))
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--priority", choices=["generales", "europeas", "all"], default="all")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pause", type=int, default=12)
    args = ap.parse_args()

    cat = json.load(open(args.catalog))
    order = {"generales": 0, "europeas": 1, "municipales_autonomicas": 2,
             "autonomicas": 3, "municipales": 4, "otro": 9}
    if args.priority != "all":
        cat = [r for r in cat if r["eleccion"] == args.priority] + \
              [r for r in cat if r["eleccion"] != args.priority]
    cat.sort(key=lambda r: (order.get(r["eleccion"], 9), r["fecha_trabajo"][-4:]))
    if args.only:
        want = set(args.only)
        cat = [r for r in cat if r["estudio"] in want]
    if args.limit:
        cat = cat[:args.limit]

    man = load_manifest()
    stats = {"done": 0, "fail": 0, "skip": 0}
    for i, rec in enumerate(cat, 1):
        est = rec["estudio"]
        prev = man.get(est, {})
        if prev.get("status") == "done":
            stats["skip"] += 1
            continue
        sys.stderr.write(f"[{i}/{len(cat)}] estudio {est}  {rec['slug'][:60]}\n")
        try:
            res = fetch_study(rec, pause=args.pause)
        except Exception as e:  # noqa
            res = {"status": "error", "error": str(e)}
        res.update({"slug": rec["slug"], "tipo": rec["tipo"], "eleccion": rec["eleccion"],
                    "fecha_trabajo": rec["fecha_trabajo"], "url": rec["url"],
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        man[est] = res
        save_manifest(man)
        if res["status"] == "done":
            stats["done"] += 1
        else:
            stats["fail"] += 1
        time.sleep(args.pause)
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
