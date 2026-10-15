#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normaliza los fragmentos de encuestadores privados (29N, Fase 3).

Entrada:  data/processed/encuestadores/_staging/*.json  (fragmentos por encuestador)
Salida:   data/processed/encuestadores/polls.jsonl      (una línea por encuesta×partido)
          data/processed/encuestadores/sources.json     (una entrada por encuesta con URL + extracto)
          data/processed/encuestadores/exclusions.json  (lo que no pasa validación)

Regla de oro: toda encuesta necesita URL de ficha técnica. Sin URL → exclusión.
No inventa datos: solo normaliza lo que traen los fragmentos.

Solo biblioteca estándar. Uso:
    python3 pipeline/encuestadores/build_dataset.py
"""
from __future__ import annotations

import glob
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAGING = os.path.join(REPO, "data", "processed", "encuestadores", "_staging")
OUTDIR = os.path.join(REPO, "data", "processed", "encuestadores")
ALIASES = os.path.join(REPO, "pipeline", "encuestadores", "aliases.json")

PRESS = {"elpais.com", "elmundo.es", "abc.es", "larazon.es", "elconfidencial.com",
         "elespanol.com", "elplural.com", "eldiario.es", "rtve.es", "publico.es",
         "libertaddigital.com", "epimg.net", "vozpopuli.com", "infobae.com"}
POLLSTER = {"gad3.com", "sigmados.com", "imop.es", "40db.es", "ncreport.es",
            "simplelógica.es", "simplelogica.es", "demoscopia.es"}


def load_aliases() -> tuple:
    with open(ALIASES, encoding="utf-8") as fh:
        data = json.load(fh)
    alias2canon = {}
    for canon, variants in data["partido"].items():
        alias2canon[canon] = canon
        for v in variants:
            alias2canon[v.upper()] = canon
    fuente2canon = {}
    for canon, variants in data.get("fuente", {}).items():
        fuente2canon[canon.upper()] = canon
        for v in variants:
            fuente2canon[v.upper()] = canon
    return alias2canon, fuente2canon


def canon_of(name: str, alias2canon: dict) -> str | None:
    if not name:
        return None
    return alias2canon.get(name.strip().upper())


def fuente_tipo(url: str) -> str:
    if not url:
        return "desconocida"
    host = url.split("//", 1)[-1].split("/", 1)[0].lower()
    if host.startswith("www."):
        host = host[4:]

    def matches(group):
        return any(host == d or host.endswith("." + d) for d in group)

    if matches(POLLSTER):
        return "encuestador"
    if matches(PRESS):
        return "prensa"
    return "agregador"


def main() -> None:
    alias2canon, fuente2canon = load_aliases()
    polls, sources, exclusions = [], [], []
    seen_estudios = set()

    files = sorted(glob.glob(os.path.join(STAGING, "*.json")))
    if not files:
        raise SystemExit(f"[build] no hay fragmentos en {STAGING}")

    for path in files:
        with open(path, encoding="utf-8") as fh:
            frag = json.load(fh)
        for exc in frag.get("exclusiones", []):
            exclusions.append({"archivo": os.path.basename(path), **exc})
        for e in frag.get("encuestas", []):
            url = e.get("url")
            eid = e.get("estudio_id")
            if not url:
                exclusions.append({"archivo": os.path.basename(path),
                                   "fuente": e.get("fuente"), "estudio_id": eid,
                                   "motivo": "sin URL de ficha técnica publicada"})
                continue
            # Duplicados por estudio: nos quedamos con la primera aparición.
            if eid in seen_estudios:
                exclusions.append({"archivo": os.path.basename(path), "fuente": e.get("fuente"),
                                   "estudio_id": eid, "motivo": "estudio_id duplicado (ya incluido)"})
                continue
            seen_estudios.add(eid)

            votos = e.get("votos") or {}
            rows = 0
            for raw_party, pct in votos.items():
                canon = canon_of(raw_party, alias2canon)
                if canon is None:
                    exclusions.append({"archivo": os.path.basename(path), "fuente": e.get("fuente"),
                                       "estudio_id": eid,
                                       "motivo": f"etiqueta de partido sin mapear: {raw_party}"})
                    continue
                polls.append({
                    "fuente": fuente2canon.get((e.get("fuente") or "").upper(), e.get("fuente")),
                    "estudio_id": eid,
                    "fecha_trabajo": e.get("fecha_trabajo"),
                    "fecha_publicacion": e.get("fecha_publicacion"),
                    "n": e.get("n"),
                    "metodologia": e.get("metodologia"),
                    "ambito": e.get("ambito"),
                    "eleccion": e.get("eleccion"),
                    "partido_canonico": canon,
                    "porcentaje": pct,
                    "fuente_url": url,
                    "fuente_tipo": fuente_tipo(url),
                    **({"nota": e["nota"]} if e.get("nota") else {}),
                })
                rows += 1
            if rows == 0:
                exclusions.append({"archivo": os.path.basename(path), "fuente": e.get("fuente"),
                                   "estudio_id": eid,
                                   "motivo": "sin desglose de voto por partido utilizable"})
                continue
            sources.append({
                "fuente": fuente2canon.get((e.get("fuente") or "").upper(), e.get("fuente")),
                "estudio_id": eid,
                "fecha_trabajo": e.get("fecha_trabajo"),
                "fecha_publicacion": e.get("fecha_publicacion"),
                "n": e.get("n"),
                "metodologia": e.get("metodologia"),
                "ambito": e.get("ambito"),
                "eleccion": e.get("eleccion"),
                "fuente_tipo": fuente_tipo(url),
                "url": url,
                "extracto": e.get("extracto"),
                "partidos_publicados": list(votos.keys()),
            })

    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "polls.jsonl"), "w", encoding="utf-8") as fh:
        for row in polls:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(os.path.join(OUTDIR, "sources.json"), "w", encoding="utf-8") as fh:
        json.dump(sources, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(OUTDIR, "exclusions.json"), "w", encoding="utf-8") as fh:
        json.dump(exclusions, fh, ensure_ascii=False, indent=1)

    print(f"[build] fragmentos: {len(files)}")
    print(f"[build] encuestas: {len(sources)}   filas poll×partido: {len(polls)}   exclusiones: {len(exclusions)}")
    from collections import Counter
    print("[build] por encuestador:")
    for k, v in sorted(Counter(s["fuente"] for s in sources).items(), key=lambda x: (-x[1], x[0])):
        print(f"    {k}: {v}")
    print("[build] por tipo de fuente:", dict(Counter(s["fuente_tipo"] for s in sources)))
    print("[build] por elección:", dict(Counter(s["eleccion"] for s in sources)))


if __name__ == "__main__":
    main()
