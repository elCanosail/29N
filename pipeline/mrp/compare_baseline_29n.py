#!/usr/bin/env python3
"""Comparación 29N: post-estratificación MRP vs baseline provincial (seats.json).

Convierte las cuotas provinciales del MRP (`data/processed/mrp/poststrat.json`,
crudas y calibradas) en **escaños por D'Hondt** (umbral legal 3 % provincial) y
las compara, provincia a provincia y partido a partido, con el baseline de
producción `data/processed/modelo/seats.json` (swing uniforme + simulación).

Solo lectura sobre `data/processed/modelo/`. Escribe únicamente
`data/processed/mrp/compare_baseline_29n.json`.

Uso:
    /root/.venvs/29n-mrp/bin/python pipeline/mrp/compare_baseline_29n.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mrp_core as M  # noqa: E402

OUT = M.MRP / "compare_baseline_29n.json"
UMBRAL = 3.0   # % provincial para el Congreso


def dhondt(shares: dict, escanos: int, umbral: float = UMBRAL):
    """Reparto D'Hondt. `shares`: partido -> % (voto válido). Devuelve partido->escaños."""
    seats = {p: 0 for p in shares}
    elig = {p: v for p, v in shares.items() if v >= umbral}
    if not elig or escanos <= 0:
        return seats
    for _ in range(escanos):
        best_p, best_q = None, -1.0
        for p, v in elig.items():
            q = v / (seats[p] + 1)
            if q > best_q:
                best_q, best_p = q, p
        seats[best_p] += 1
    return seats


def main() -> int:
    post = json.loads((M.MRP / "poststrat.json").read_text(encoding="utf-8"))
    seats = json.loads((M.DATA / "modelo" / "seats.json").read_text(encoding="utf-8"))
    parties = post["meta"]["universo"]

    prov_out = {}
    tot_mrp_cal = {p: 0 for p in parties}
    tot_mrp_raw = {p: 0 for p in parties}
    tot_base_media = {p: 0.0 for p in parties}
    tot_base_central = {p: 0 for p in parties}
    diffs_cal, diffs_raw = [], []

    for c, info in post["provincias"].items():
        esc = info["escanos"]
        cal = {p: info["partidos"][p]["calibrado"] for p in parties}
        raw = {p: info["partidos"][p]["crudo"] for p in parties}
        s_cal = dhondt(cal, esc)
        s_raw = dhondt(raw, esc)
        base = seats["provincias"].get(c, {}).get("partidos", {})
        base_media = {p: float(base.get(p, {}).get("media", 0.0)) for p in parties}
        base_central = {p: int(base.get(p, {}).get("central_escenario", round(base_media[p])))
                        for p in parties}
        for p in parties:
            tot_mrp_cal[p] += s_cal[p]
            tot_mrp_raw[p] += s_raw[p]
            tot_base_media[p] += base_media[p]
            tot_base_central[p] += base_central[p]
            diffs_cal.append(abs(s_cal[p] - base_media[p]))
            diffs_raw.append(abs(s_raw[p] - base_media[p]))
        prov_out[c] = {
            "nombre": info["nombre"], "escanos": esc,
            "mrp_calibrado": s_cal, "mrp_crudo": s_raw,
            "baseline_media": {p: round(base_media[p], 2) for p in parties},
            "baseline_central": base_central,
        }

    suma_cal = sum(tot_mrp_cal.values())
    suma_base = round(sum(tot_base_media.values()))
    out = {
        "generado": post["meta"]["generado"],
        "objetivo": "29N 2026-11-29",
        "metodo_mrp": "D'Hondt sobre cuotas provinciales post-estratificadas (umbral 3 %)",
        "baseline": "data/processed/modelo/seats.json (swing uniforme + 10.000 sims)",
        "umbral_dhondt_pct": UMBRAL,
        "total_escanos": 350,
        "nacional_mrp_calibrado": tot_mrp_cal,
        "nacional_mrp_crudo": tot_mrp_raw,
        "nacional_baseline_media": {p: round(tot_base_media[p], 2) for p in parties},
        "nacional_baseline_central": tot_base_central,
        "suma_escanos_mrp_calibrado": suma_cal,
        "suma_escanos_baseline": suma_base,
        "mae_escanos_por_provincia_partido": {
            "mrp_calibrado_vs_baseline_media": round(float(np.mean(diffs_cal)), 3),
            "mrp_crudo_vs_baseline_media": round(float(np.mean(diffs_raw)), 3),
        },
        "provincias": prov_out,
        "nota": "Las cuotas del MRP están normalizadas al universo modelado (13 "
                "partidos), lo que sobreestima ligeramente a los partidos pequeños "
                "frente al baseline; el umbral del 3 % amortigua el efecto.",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK {OUT}")
    print(f"  suma escaños MRP calibrado = {suma_cal} | baseline = {suma_base}")
    print(f"  MAE escaños/prov-partido vs baseline: cal {out['mae_escanos_por_provincia_partido']['mrp_calibrado_vs_baseline_media']}, "
          f"crudo {out['mae_escanos_por_provincia_partido']['mrp_crudo_vs_baseline_media']}")
    print("  Nacional (MRP cal / baseline central):")
    orden = sorted(parties, key=lambda p: -tot_mrp_cal[p])
    for p in orden:
        print(f"    {p:10s} MRP {tot_mrp_cal[p]:3d} | base {tot_base_central[p]:3d} "
              f"(media {tot_base_media[p]:6.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
