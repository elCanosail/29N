#!/usr/bin/env python3
"""Sondeo de ingesta CIS (29N).

Utilidades para:
  - descargar una página del catálogo/estudio del CIS con backoff ante 429,
  - extraer los enlaces de documentos (PDFs y fichero de datos MD####.zip),
  - descargar y descomprimir el fichero de datos de un estudio.

Uso:
  python cis_fetch.py page   <url> <salida.html>
  python cis_fetch.py docs   <salida.html>            # lista documentos
  python cis_fetch.py study  <url> <dir_destino>      # baja MD####.zip y lo descomprime

No hace commit ni push. Solo escribe en la ruta que se indique.
"""
import argparse
import os
import re
import sys
import time
import urllib.request
import urllib.error
import zipfile

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

DOC_RE = re.compile(r'https://www\.cis\.es/documents/[^"\'\\<>\s]+')
MD_RE = re.compile(r'(MD\d{3,5}\.zip)')


def get(url, referer=None, timeout=90, retries=6, base_sleep=20):
    """GET con reintentos y backoff exponencial ante 429/5xx."""
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
                return r.read(), r.status, dict(r.headers)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                sleep = base_sleep * (attempt + 1)
                retry_after = e.headers.get("Retry-After") if e.headers else None
                if retry_after and retry_after.isdigit():
                    sleep = max(sleep, int(retry_after))
                sys.stderr.write(f"  HTTP {e.code} en {url}; espero {sleep}s "
                                 f"(intento {attempt+1}/{retries})\n")
                time.sleep(sleep)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            sleep = base_sleep * (attempt + 1)
            sys.stderr.write(f"  {type(e).__name__} en {url}; espero {sleep}s\n")
            time.sleep(sleep)
    raise SystemExit(f"Fallo tras {retries} intentos: {url} ({last})")


def cmd_page(args):
    data, status, _ = get(args.url)
    with open(args.out, "wb") as f:
        f.write(data)
    print(f"OK HTTP {status} -> {args.out} ({len(data)} bytes)")


def extract_docs(html):
    urls = sorted(set(DOC_RE.findall(html)))
    return urls


def cmd_docs(args):
    with open(args.html, encoding="utf-8", errors="replace") as f:
        html = f.read()
    urls = extract_docs(html)
    for u in urls:
        kind = "MD-ZIP" if MD_RE.search(u) else ("pdf" if ".pdf" in u.lower() else "otro")
        print(f"[{kind}] {u}")
    if not urls:
        print("(sin enlaces /documents/ — la página puede cargarse por JS)")
    md = [u for u in urls if MD_RE.search(u)]
    print(f"\ntotal={len(urls)}  ficheros_datos={len(md)}")
    return md


def cmd_study(args):
    with open(args.html, encoding="utf-8", errors="replace") as f:
        html = f.read()
    urls = extract_docs(html)
    md = [u for u in urls if MD_RE.search(u)]
    # dedupe por nombre (la página repite el enlace con y sin UUID/versión)
    seen = {}
    for u in md:
        seen.setdefault(MD_RE.search(u).group(1), u)
    md = list(seen.values())
    if not md:
        raise SystemExit("No encontré enlace MD####.zip en la página.")
    os.makedirs(args.dest, exist_ok=True)
    for u in md:
        name = MD_RE.search(u).group(1)
        path = os.path.join(args.dest, name)
        data, status, hdr = get(u, referer=args.referer)
        with open(path, "wb") as f:
            f.write(data)
        print(f"OK HTTP {status} {name} ({len(data)} bytes) -> {path}")
        try:
            with zipfile.ZipFile(path) as z:
                z.extractall(os.path.join(args.dest, name[:-4]))
            print(f"  descomprimido en {os.path.join(args.dest, name[:-4])}")
        except zipfile.BadZipFile:
            print("  ¡no es un zip válido!")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)

    sp = sub.add_parser("page", help="descarga una URL a fichero")
    sp.add_argument("url")
    sp.add_argument("out")
    sp.set_defaults(func=cmd_page)

    sd = sub.add_parser("docs", help="lista documentos de un html guardado")
    sd.add_argument("html")
    sd.set_defaults(func=cmd_docs)

    ss = sub.add_parser("study", help="baja y descomprime MD####.zip de un html guardado")
    ss.add_argument("html")
    ss.add_argument("dest")
    ss.add_argument("--referer", default=None)
    ss.set_defaults(func=cmd_study)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
