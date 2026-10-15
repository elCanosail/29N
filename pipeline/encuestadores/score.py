#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scoring histórico de encuestadores privados (29N, Fase 3).

Calcula el error absoluto medio (MAE) de cada encuestador contra el resultado
real de las elecciones generales del 23J de 2023, usando:

  - data/processed/encuestadores/polls.jsonl   (una línea por encuesta×partido)
  - data/processed/interior/elections.json     (resultado oficial por candidatura)

Salida por consola + data/processed/encuestadores/scoring.json

Solo biblioteca estándar. Uso:
    python3 pipeline/encuestadores/score.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POLLS = os.path.join(REPO, "data", "processed", "encuestadores", "polls.jsonl")
ELECTIONS = os.path.join(REPO, "data", "processed", "interior", "elections.json")
OUT = os.path.join(REPO, "data", "processed", "encuestadores", "scoring.json")

ELECTION_ID = "2023-07-23"
PARTIES = ["PP", "PSOE", "VOX", "SUMAR"]

# Mapa candidatura oficial (partido_id de Interior) -> canónico del diccionario CIS.
# Agrupa las marcas territoriales de PSOE y SUMAR bajo su canónico estatal.
INTERIOR_TO_CANON = {
    "pp": "PP",
    "psoe": "PSOE", "psc": "PSOE", "psdeg": "PSOE", "pse": "PSOE",
    "psib-psoe": "PSOE", "psn-psoe": "PSOE",
    "vox": "VOX",
    "sumar": "SUMAR", "ecp": "SUMAR", "compromis": "SUMAR",
    "sumar-aragón": "SUMAR", "més-per-mallorca-més-per-menorca-sumar": "SUMAR",
}


def real_23j() -> dict:
    """Porcentaje oficial por partido canónico sobre votos válidos en 23J."""
    with open(ELECTIONS, encoding="utf-8") as fh:
        data = json.load(fh)
    elec = next(e for e in data["elecciones"] if e["id"] == ELECTION_ID)
    validos = elec["totales"]["votos_validos"]
    agg: dict[str, int] = defaultdict(int)
    for p in elec["partidos"]:
        canon = INTERIOR_TO_CANON.get(p["partido_id"])
        if canon:
            agg[canon] += p["votos"]
    return {c: round(100.0 * v / validos, 2) for c, v in agg.items()}


def load_polls() -> list:
    if not os.path.exists(POLLS):
        sys.exit(f"[score] falta {POLLS}")
    rows = []
    with open(POLLS, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def score() -> dict:
    real = real_23j()
    rows = load_polls()
    per_pollster: dict = defaultdict(list)
    per_pollster_party: dict = defaultdict(lambda: defaultdict(list))
    n_polls: dict = defaultdict(set)

    for r in rows:
        if "2023" not in str(r.get("eleccion", "")):
            continue
        partido = r.get("partido_canonico")
        if partido not in PARTIES or partido not in real:
            continue
        pct = r.get("porcentaje")
        if pct is None:
            continue
        err = abs(float(pct) - real[partido])
        src = r["fuente"]
        per_pollster[src].append(err)
        per_pollster_party[src][partido].append(err)
        n_polls[src].add(r["estudio_id"])

    resultado = []
    for src, errs in per_pollster.items():
        resultado.append({
            "encuestador": src,
            "n_encuestas_2023": len(n_polls[src]),
            "n_observaciones": len(errs),
            "mae": round(sum(errs) / len(errs), 2),
            "mae_por_partido": {
                p: round(sum(v) / len(v), 2)
                for p, v in per_pollster_party[src].items()
            },
        })
    resultado.sort(key=lambda x: x["mae"])
    return {
        "eleccion_referencia": ELECTION_ID,
        "resultado_real_pct": real,
        "partidos_comparados": PARTIES,
        "por_encuestador": resultado,
    }


def main() -> None:
    out = score()
    real = out["resultado_real_pct"]
    print("Resultado real 23J (votos válidos %): " + ", ".join(f"{p}={real[p]}" for p in PARTIES))
    print()
    hdr = f"{'Encuestador':<22}{'n':>3}{'obs':>5}{'MAE':>7}   " + " ".join(f"{p:>6}" for p in PARTIES)
    print(hdr)
    print("-" * len(hdr))
    for r in out["por_encuestador"]:
        pp = r["mae_por_partido"]
        cells = " ".join(f"{pp.get(p, float('nan')):>6.2f}" for p in PARTIES)
        print(f"{r['encuestador']:<22}{r['n_encuestas_2023']:>3}{r['n_observaciones']:>5}{r['mae']:>7.2f}   {cells}")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\n[score] escrito {os.path.relpath(OUT, REPO)}")


if __name__ == "__main__":
    main()
