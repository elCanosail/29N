#!/usr/bin/env python3
"""Descarga de resultados electorales oficiales del Ministerio del Interior (29N).

FUENTE PRIMARIA (accesible desde este host)
-------------------------------------------
Portal de datos abiertos del Ministerio del Interior:
    https://descargas.interior.gob.es/datasets/resultados_electorales/

    Elecciones-Congreso.xlsx                  -> escrutinio por provincia y candidatura
                                                 (votos y escaños), todas las generales
                                                 desde 1977 (Congreso).
    Elecciones-Congreso-cargos-electos.xlsx   -> cargos electos (definitivo) por provincia.
    Elecciones-Senado.xlsx                    -> (opcional) Senado.

FUENTE SOLICITADA — infoelectoral.interior.gob.es — BLOQUEADA desde este host
-----------------------------------------------------------------------------
El portal `infoelectoral.interior.gob.es` (y el legacy `www.infoelectoral.mir.es`)
resuelven a 212.128.101.22 / .21 y **no aceptan conexiones TCP** desde este host
(timeout en 80 y 443; también desde proxies públicos y desde el extractor web del
Gateway). `www.interior.gob.es` sí responde pero con HTTP 403 (WAF). El Área de
Descargas de infoelectoral (que ofrece los ZIP `.DAT` de ancho fijo por elección)
queda por tanto inalcanzable. Los datos abiertos de `descargas.interior.gob.es`
son el **mismo escrutinio oficial** publicado por el propio Ministerio y sí son
accesibles; se usan como fuente primaria. Ver docs/notes/interior-ingest.md.

Uso
---
    python3 interior_fetch.py                 # descarga los ficheros a data/raw/interior/
    python3 interior_fetch.py --force         # re-descarga aunque existan
    python3 interior_fetch.py --host dest     # directorio destino (por defecto data/raw/interior)
    python3 interior_fetch.py --try-infoelectoral   # intenta infoelectoral y registra el fallo

Reanudable: si el fichero existe parcialmente, pide el resto con Range.
Educado: pausa entre peticiones y backoff exponencial ante 429/5xx.
No hace commit ni push.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import ssl
import urllib.request
import urllib.error

BASE = "https://descargas.interior.gob.es/datasets/resultados_electorales"

RECURSOS = [
    "Elecciones-Congreso.xlsx",
    "Elecciones-Congreso-cargos-electos.xlsx",
    "Elecciones-Senado.xlsx",
]

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _ssl_contexts():
    """Devuelve contextos SSL por preferencia: verificado y, si falla la cadena,
    uno sin verificar (el certificado de descargas.interior.gob.es se sirve con
    la cadena incompleta; son datos públicos y no se envían credenciales)."""
    ctxs = []
    try:
        import certifi
        ctxs.append(("certifi", ssl.create_default_context(cafile=certifi.where())))
    except Exception:
        pass
    ctxs.append(("default", ssl.create_default_context()))
    ctxs.append(("unverified", ssl._create_unverified_context()))
    return ctxs


def _is_cert_error(exc):
    if isinstance(exc, ssl.SSLError):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, ssl.SSLError):
        return True
    return "CERTIFICATE_VERIFY_FAILED" in str(exc)


def head(url, timeout=30):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    last = None
    for name, ctx in _ssl_contexts():
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return dict(r.headers), r.status, name
        except urllib.error.HTTPError as e:
            return dict(e.headers or {}), e.code, name
        except (ssl.SSLError, urllib.error.URLError) as e:
            last = e
            continue
    raise SystemExit(f"Fallo HEAD: {url} ({last})")


def download(url, dest, force=False, pause=2.0, retries=5):
    """Descarga con reanudación (Range) y backoff. Devuelve la ruta final."""
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    hdr, status, ctxname = head(url)
    remote_len = int(hdr.get("Content-Length", 0) or 0)
    etag = hdr.get("ETag")

    existing = os.path.getsize(dest) if os.path.exists(dest) else 0
    if existing and not force and remote_len and existing == remote_len:
        print(f"  = ya completo ({existing} bytes): {os.path.basename(dest)}")
        return dest
    if existing and force:
        os.remove(dest)
        existing = 0

    mode = "ab" if existing else "wb"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if existing and remote_len:
        req.add_header("Range", f"bytes={existing}-")

    last = None
    for attempt in range(retries):
        for cname, ctx in _ssl_contexts():
            try:
                with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
                    with open(dest, mode) as f:
                        while True:
                            chunk = r.read(1 << 16)
                            if not chunk:
                                break
                            f.write(chunk)
                size = os.path.getsize(dest)
                print(f"  OK {os.path.basename(dest)} ({size} bytes, TLS={cname})")
                time.sleep(pause)
                return dest
            except ssl.SSLError as e:
                last = e
                continue
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 500, 502, 503, 504):
                    wait = 10 * (attempt + 1)
                    ra = e.headers.get("Retry-After") if e.headers else None
                    if ra and str(ra).isdigit():
                        wait = max(wait, int(ra))
                    sys.stderr.write(f"  HTTP {e.code}; espero {wait}s "
                                     f"(intento {attempt+1}/{retries})\n")
                    time.sleep(wait)
                    break
                raise
            except (ssl.SSLError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = e
                if _is_cert_error(e):
                    continue  # prueba el siguiente contexto TLS
                sys.stderr.write(f"  {type(e).__name__} ({e}); reintento\n")
                time.sleep(10 * (attempt + 1))
                break
    raise SystemExit(f"Fallo tras {retries} intentos: {url} ({last})")


def try_infoelectoral():
    """Registra el estado del portal solicitado (informativo, no fatal)."""
    for url in ("https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/",
                "https://www.infoelectoral.mir.es/min/areaDescarga.html?method=inicio"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                print(f"  infoelectoral ACCESIBLE: {url} ({r.status})")
        except Exception as e:
            print(f"  infoelectoral INACCESIBLE: {url} -> {type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default="data/raw/interior",
                    help="directorio destino (por defecto data/raw/interior)")
    ap.add_argument("--force", action="store_true", help="re-descargar aunque existan")
    ap.add_argument("--pause", type=float, default=2.0, help="pausa entre peticiones (s)")
    ap.add_argument("--try-infoelectoral", action="store_true",
                    help="intenta el portal infoelectoral y registra el resultado")
    args = ap.parse_args()

    if args.try_infoelectoral:
        print("== Estado del portal infoelectoral ==")
        try_infoelectoral()

    print(f"== Descarga datos abiertos Interior -> {args.dest} ==")
    ok = []
    for name in RECURSOS:
        url = f"{BASE}/{name}"
        dest = os.path.join(args.dest, name)
        try:
            download(url, dest, force=args.force, pause=args.pause)
            ok.append(name)
        except SystemExit as e:
            sys.stderr.write(f"  SKIP {name}: {e}\n")
    print(f"Descargados {len(ok)}/{len(RECURSOS)}: {', '.join(ok)}")


if __name__ == "__main__":
    main()
