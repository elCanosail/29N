#!/usr/bin/env python3
"""Construye pipeline/cis/catalog.json a partir de los fragmentos cosechados del
catálogo del CIS (data/raw/cis/catalog/chunk_*.json).

Los fragmentos `chunk_t{1..4}.json` provienen de la paginación del catálogo
(`.../es/estudios/catalogo?catalogo=estudio&sort=createDateBDE-&t=0&delta=200&start=N`)
filtrando por los estudios electorales (generales, europeas, encuestas flash,
estudios de voto). El catálogo solo se puede enumerar por navegador (la página
se pinta por JS y el endpoint de búsqueda dispara un anti-bot para clientes sin
JS); ver docs/notes/cis-ingest.md.

Cada elemento del catálogo se clasifica (tipo/ámbito/elección) a partir del slug,
que es estable en cis.es.
"""
import json
import os
import re
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(BASE))

# --- clasificadores sobre el slug -----------------------------------------

CCAA = {
    "andalucia": "Andalucía", "aragon": "Aragón", "asturias": "Principado de Asturias",
    "principado-de-asturias": "Principado de Asturias", "baleares": "Islas Baleares",
    "islas-baleares": "Islas Baleares", "canarias": "Canarias", "cantabria": "Cantabria",
    "castilla-la-mancha": "Castilla-La Mancha", "castilla-y-leon": "Castilla y León",
    "cataluna": "Cataluña", "extremadura": "Extremadura", "galicia": "Galicia",
    "la-rioja": "La Rioja", "madrid": "Comunidad de Madrid",
    "comunidad-de-madrid": "Comunidad de Madrid", "provincia-de-madrid": "Comunidad de Madrid",
    "murcia": "Región de Murcia", "region-de-murcia": "Región de Murcia",
    "navarra": "Comunidad Foral de Navarra", "comunidad-foral-de-navarra": "Comunidad Foral de Navarra",
    "pais-vasco": "País Vasco", "valencia": "Comunidad Valenciana",
    "comunidad-valenciana": "Comunidad Valenciana", "ceuta": "Ceuta", "melilla": "Melilla",
}


def _norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def classify(slug):
    s = slug.lower()
    # ámbito/elección
    if "parlamento-europeo" in s or re.search(r"\beuropeo", s):
        eleccion = "europeas"
    elif "elecciones-generales" in s or re.search(r"elecciones-generales|generales-\d{4}", s):
        eleccion = "generales"
    elif "municipales" in s and "autonomicas" in s:
        eleccion = "municipales_autonomicas"
    elif "municipales" in s:
        eleccion = "municipales"
    elif "autonomicas" in s:
        eleccion = "autonomicas"
    else:
        eleccion = "otro"

    # tipo
    if s.startswith("preelectoral") or "preelectoral" in s:
        tipo = "preelectoral"
    elif "postelectoral" in s:
        tipo = "postelectoral"
    elif "campana" in s or "precampana" in s:
        tipo = "campana"
    elif "encuesta-flash" in s or "flash" in s:
        tipo = "flash"
    elif "metodologic" in s:
        tipo = "metodologico"
    elif "panel" in s:
        tipo = "panel"
    else:
        tipo = "otro"

    if "panel" in s:
        tipo = "panel" if tipo == "otro" else tipo + "_panel"

    # año
    m = re.search(r"(19|20)\d{2}", slug)
    anio = int(m.group(0)) if m else None

    # ámbito geográfico (submuestras autonómicas: "preelectoral-elecciones-generales-1989.-cataluna")
    ambito = "estatal"
    for key, name in CCAA.items():
        if s.endswith("-" + key + "-") or s.endswith("." + key) or s.endswith("-" + key) \
           or re.search(r"[.\-]" + re.escape(key) + r"(-|$)", s):
            # evitar falsos positivos: solo si va al final del slug
            if s.rstrip("-").endswith(key):
                ambito = name
                break

    return tipo, ambito, eleccion, anio


def main():
    frags = []
    cdir = os.path.join(REPO, "data/raw/cis/catalog")
    for i in range(1, 11):
        p = os.path.join(cdir, f"chunk_t{i}.json")
        if os.path.exists(p):
            frags.append(json.load(open(p)))
    items = {}
    for f in frags:
        for est, fecha, slug in f:
            items[est] = {"estudio": est, "fecha_trabajo": fecha, "slug": slug,
                          "url": "https://www.cis.es/es/estudios/" + slug}
    out = []
    for est, rec in items.items():
        tipo, ambito, eleccion, anio = classify(rec["slug"])
        rec.update({"tipo": tipo, "ambito": ambito, "eleccion": eleccion, "anio": anio})
        out.append(rec)
    # orden por fecha_trabajo ascendente
    def key(r):
        d = r["fecha_trabajo"].split("/")
        return (d[2], d[1], d[0]) if len(d) == 3 else ("9999", "99", "99")
    out.sort(key=key)
    dst = os.path.join(BASE, "catalog.json")
    json.dump(out, open(dst, "w"), ensure_ascii=False, indent=1)
    print(f"catalog.json: {len(out)} estudios -> {dst}")
    from collections import Counter
    print("  por elección:", dict(Counter(r["eleccion"] for r in out)))
    print("  por tipo:", dict(Counter(r["tipo"] for r in out)))


if __name__ == "__main__":
    main()
