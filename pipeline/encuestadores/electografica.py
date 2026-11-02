#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lector de encuestas publicadas en electografica.com (Blogger).

electografica publica cada encuesta como una entrada con:
  - la tabla de estimación de voto (partido, %, escaños),
  - un bloque «Ficha técnica» (encuestadora, cliente, fechas, método, muestra,
    margen de error),
  - enlaces a la fuente original (encuestador o prensa).

Este módulo no decide nada: extrae y devuelve lo que hay, con las marcas de lo
que falta. La validación y la decisión de ingestar viven en `cron_ingesta.py`.

Uso para inspeccionar:
    python3 pipeline/encuestadores/electografica.py            # últimas del feed
    python3 pipeline/encuestadores/electografica.py --desde 2026-10-24
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import re
import sys
import unicodedata
import urllib.request

FEED = ("https://www.electografica.com/feeds/posts/default"
        "?alt=json&max-results=150")
UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")}

# «ESPAÑA · Elecciones generales · Encuesta Sigma Dos 01/11/2026»
TITULO_ES = re.compile(r"^ESPAÑA\s*·\s*Elecciones generales\s*·\s*Encuesta\s+(.+?)\s+(\d{2}/\d{2}/\d{4})", re.I)

# Emoji + siglas + % + escaños: «🟦 PP 32,4% (137)»
VOTO = re.compile(r"([A-ZÁÉÍÓÚÜÑ][A-Za-zÀ-ÿ0-9\.\-]{0,12}(?:\s[A-ZÁÉÍÓÚÜÑ][A-Za-zÀ-ÿ0-9\.\-]{0,12}){0,2})\s(\d{1,2}(?:,\d)?)\s*%(?:\s*\((\d{1,3})\))?")


def _txt(fragmento: str) -> str:
    t = re.sub(r"<script.*?</script>", " ", fragmento, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t)


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _fecha_iso(ddmmyyyy: str) -> str | None:
    try:
        return datetime.datetime.strptime(ddmmyyyy.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _trabajo(crudo: str) -> tuple[str | None, str | None]:
    """«22-28/10/2026» → ('2026-10-22/2026-10-28', None) o (None, motivo)."""
    crudo = crudo.strip().replace("–", "-").replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})/(\d{1,2})/(\d{4})", crudo)
    if m:
        d1, d2, mes, anio = m.groups()
        try:
            ini = datetime.date(int(anio), int(mes), int(d1))
            fin = datetime.date(int(anio), int(mes), int(d2))
        except ValueError:
            return None, f"fechas de campo imposibles: {crudo}"
        if fin < ini:
            return None, f"fin de campo anterior al inicio: {crudo}"
        return f"{ini.isoformat()}/{fin.isoformat()}", None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", crudo)
    if m:
        d, mes, anio = m.groups()
        try:
            d_iso = datetime.date(int(anio), int(mes), int(d))
        except ValueError:
            return None, f"fecha de campo imposible: {crudo}"
        return f"{d_iso.isoformat()}/{d_iso.isoformat()}", None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})-(\d{1,2})/(\d{1,2})/(\d{4})", crudo)
    if m:  # «01/09-25/10/2026» (tracking: 1 sept → 25 oct)
        d1, mes1, d2, mes2, anio = m.groups()
        try:
            ini = datetime.date(int(anio), int(mes1), int(d1))
            fin = datetime.date(int(anio), int(mes2), int(d2))
        except ValueError:
            return None, f"fechas de campo imposibles: {crudo}"
        if fin < ini:
            return None, f"fin de campo anterior al inicio: {crudo}"
        return f"{ini.isoformat()}/{fin.isoformat()}", None
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})/(\d{1,2})-(\d{1,2})/(\d{4})", crudo)
    if m:  # «30-31/10-01/11/2026» (cruce de mes)
        d1, mes1, d2, mes2, anio = m.groups()
        try:
            ini = datetime.date(int(anio), int(mes1), int(d1))
            fin = datetime.date(int(anio), int(mes2), int(d2))
        except ValueError:
            return None, f"fechas de campo imposibles: {crudo}"
        if fin < ini:
            return None, f"fin de campo anterior al inicio: {crudo}"
        return f"{ini.isoformat()}/{fin.isoformat()}", None
    return None, f"formato de fechas de campo no reconocido: {crudo}"


def parse_entrada(entry: dict) -> dict:
    """Devuelve un dict con lo extraído y una lista de `faltan`."""
    titulo = entry["title"]["$t"].strip()
    publicado = entry["published"]["$t"][:10]
    url_post = next((l["href"] for l in entry["link"] if l["rel"] == "alternate"), "")
    crudo = entry.get("content", {}).get("$t", "")

    enlaces = [u for u in re.findall(r"href=[\"'](https?://[^\"']+)[\"']", crudo)
               if "electografica.com" not in u]
    texto = _txt(crudo)

    casa = cliente = metodo = margen = None
    n = None
    fecha_trabajo = None
    faltan: list[str] = []

    m = re.search(r"Encuestadora\s+(.+?)\s+Cliente\s+(.+?)\s+Fecha", texto)
    if m:
        casa, cliente = m.group(1).strip(), m.group(2).strip()
    else:
        faltan.append("sin bloque de ficha técnica (encuestadora/cliente)")

    m = re.search(r"Fecha (?:realización|realizacion|campo)\s+([\d\-/]{6,20})", texto)
    if m:
        fecha_trabajo, err = _trabajo(m.group(1))
        if err:
            faltan.append(err)
    else:
        faltan.append("sin fechas de trabajo de campo")

    m = re.search(r"Método\s+(.+?)\s+(?:Muestra|Ámbito|Margen)", texto)
    if m:
        metodo = m.group(1).strip()
    m = re.search(r"Muestra\s+([\d\.\s]{2,9})\s*(?:entrevistas|encuestas|casos|personas)", texto, re.I)
    if m:
        try:
            n = int(re.sub(r"[^\d]", "", m.group(1)))
        except ValueError:
            n = None
    if not n:
        faltan.append("sin tamaño muestral")

    m = re.search(r"Margen de error\s*±?\s*([\d,\.]+)\s*%", texto)
    if m:
        margen = m.group(1)

    # Votos: panel «Estimación de voto» (p1t-a). Cada partido es un bloque con
    # alt="SIGLAS" y dos data-w (voto actual, voto anterior). El resumen del pie
    # solo trae los grandes, así que se lee el panel completo.
    votos_html: dict[str, float] = {}
    esc_html: dict[str, int] = {}
    m = re.search(r'id="p1t-a".*?(?=id="p1t-b"|id="p1t-c"|fin-fichas)', crudo, re.S)
    panel = m.group(0) if m else ""
    for trozo in panel.split('<img')[1:]:
        a = re.search(r'alt="([^"]{1,14})"', trozo)
        w = re.search(r'data-w="([\d.]+)"', trozo)
        if not a or not w:
            continue
        nombre = html.unescape(a.group(1)).strip()
        # «Participación» es un dato del panel, no un partido: si entra, la suma
        # de voto se dispara (158 % en Hamalgama) y la validación lo rechazaría.
        if nombre.lower().startswith(("participaci", "abstenci")) or \
                nombre.lower() in {"españa", "espana", ""} or nombre in votos_html:
            continue
        try:
            votos_html[nombre] = float(w.group(1))
        except ValueError:
            continue
    if len(votos_html) >= 3:
        return {
            "titulo": titulo,
            "publicado": publicado,
            "url_post": url_post,
            "casa": casa,
            "cliente": cliente,
            "fecha_trabajo": fecha_trabajo,
            "metodologia": metodo,
            "margen_error": margen,
            "n": n,
            "votos": votos_html,
            "escaños": esc_html,
            "suma_votos": round(sum(votos_html.values()), 2),
            "enlaces": enlaces,
            "faltan": faltan,
            "texto": texto,
        }

    # Respaldo: resumen del pie (solo los grandes).
    votos: dict[str, float] = {}
    escaños: dict[str, int] = {}
    cola = texto.split("Gráfico: electog", 1)
    bloque = cola[1] if len(cola) > 1 else texto
    for siglas, pct, esc in VOTO.findall(bloque):
        siglas = siglas.strip()
        if siglas.lower() in {"fuente", "grafico", "gráfico", "españa", "info"}:
            continue
        if siglas in votos:
            continue
        votos[siglas] = float(pct.replace(",", "."))
        if esc:
            escaños[siglas] = int(esc)
        if len(votos) >= 20:
            break
    if len(votos) < 3:
        faltan.append(f"desglose de voto insuficiente ({len(votos)} partidos)")

    return {
        "titulo": titulo,
        "publicado": publicado,
        "url_post": url_post,
        "casa": casa,
        "cliente": cliente,
        "fecha_trabajo": fecha_trabajo,
        "metodologia": metodo,
        "margen_error": margen,
        "n": n,
        "votos": votos,
        "escaños": escaños,
        "suma_votos": round(sum(votos.values()), 2),
        "enlaces": enlaces,
        "faltan": faltan,
        "texto": texto,
    }


def feed(desde: str | None = None, solo_espana: bool = True) -> list[dict]:
    req = urllib.request.Request(FEED, headers=UA)
    datos = json.loads(urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace"))
    salida = []
    for e in datos["feed"].get("entry", []):
        titulo = e["title"]["$t"].strip()
        if solo_espana and not TITULO_ES.match(titulo):
            continue
        if desde and e["published"]["$t"][:10] < desde:
            continue
        salida.append(parse_entrada(e))
    return salida


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", help="fecha ISO mínima de publicación")
    ap.add_argument("--json", action="store_true", help="salida JSON completa")
    args = ap.parse_args()

    filas = feed(args.desde)
    if args.json:
        for f in filas:
            f.pop("texto", None)
        print(json.dumps(filas, ensure_ascii=False, indent=1))
        return 0

    print(f"{len(filas)} encuestas de generales en el feed"
          + (f" desde {args.desde}" if args.desde else "") + "\n")
    for f in filas:
        ok = "OK " if not f["faltan"] else "!! "
        print(f"{ok}{f['publicado']} · {f['titulo'][:58]}")
        print(f"    casa={f['casa']} · n={f['n']} · campo={f['fecha_trabajo']} · suma={f['suma_votos']}")
        if f["faltan"]:
            print(f"    faltan: {'; '.join(f['faltan'])}")
        if f["votos"]:
            print(f"    {', '.join(f'{k} {v}' for k, v in f['votos'].items())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
