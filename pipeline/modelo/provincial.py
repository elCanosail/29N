#!/usr/bin/env python3
"""Fase 4 (paso 5) — Desagregación provincial y simulación D'Hondt.

Modelo de swing **proporcional uniforme**: el ratio nacional de cada partido
(target / base_23J) se aplica a su cuota en cada provincia, preservando la
geografía del voto. Se descartó el swing **aditivo** (mismo ±pp en todas las
provincias) porque destruye a los partidos de apoyo concentrado: para bajar a
CC 0,3 pp en el agregado nacional habría que restarle ~16 pp en Canarias.
Fórmula:

    v_{p,k} ∝ base_{p,k} · r_k ,   r_k = target_k / base_nacional_k
    (normalizada a 100 dentro de cada provincia)

Coherencia verificable: como `Σ_k base_{p,k}·r_k` no suma 100 exacto por
provincia, tras normalizar se **calibra r** iterativamente (método de punto
fijo `r_k ← r_k · target_k / agg_k`) hasta que el agregado provincial ponderado
por votos coincide con el forecast estatal en ≤ 0,1 pp. Converge en ~5
iteraciones (ver `test_coherence.py`).

Simulación: 10.000 runs muestreando las cuotas nacionales (N(punto, σ_backtest),
recorte a ≥0 y renormalización), recalibrando y aplicando D'Hondt por provincia
(`pipeline/interior/dhondt.py`).

Salida: `data/processed/modelo/seats.json`.

Uso (tras `forecast.py`):
    /root/.venvs/29n/bin/python pipeline/modelo/provincial.py
"""

from __future__ import annotations

import json
import sys
from datetime import date

import numpy as np

import common as C

sys.path.insert(0, str(C.ROOT / "pipeline" / "interior"))
from dhondt import dhondt  # noqa: E402

BASE_ELECTION = "2023-07-23"
N_RUNS = 10000
SEED = 20261015
COHERENCE_TOL = 0.1
CALIB_TOL = 0.02
CALIB_MAX_ITER = 20


# --------------------------------------------------------------------------- #
def build_base(inter, parties):
    """Cuotas provinciales y nacionales base (universo modelado, suma=100)."""
    prov = inter.provincial_canonical(BASE_ELECTION)
    base_prov = {}
    for code, d in prov.items():
        sub = {p: float(d.get(p, 0.0)) for p in parties}
        tot = sum(sub.values())
        base_prov[code] = {p: 100.0 * v / tot for p, v in sub.items()} if tot else sub
    nat = inter.national_canonical(BASE_ELECTION)
    sub = {p: float(nat.get(p, 0.0)) for p in parties}
    tot = sum(sub.values())
    base_nat = {p: 100.0 * v / tot for p, v in sub.items()}
    return base_prov, base_nat


def ratios_from_target(base_nat, target, parties):
    r = {}
    for p in parties:
        r[p] = (target[p] / base_nat[p]) if base_nat[p] > 0.001 else 0.0
    return r


def provincial_from_ratios(base_prov, r, parties):
    """Aplica los ratios y normaliza a 100 dentro de cada provincia."""
    out = {}
    for code, bp in base_prov.items():
        v = {p: bp[p] * r[p] for p in parties}
        s = sum(v.values())
        out[code] = {p: (100.0 * v[p] / s if s > 0 else 0.0) for p in parties}
    return out


def weighted_agg(prov, w, parties):
    return {p: sum(w[c] * prov[c][p] for c in prov) for p in parties}


def calibrate(base_prov, base_nat, target, parties, w,
              tol=CALIB_TOL, max_iter=CALIB_MAX_ITER):
    """Ajusta los ratios hasta que el agregado provincial = target (≤ tol)."""
    r = ratios_from_target(base_nat, target, parties)
    prov = provincial_from_ratios(base_prov, r, parties)
    dev = float("inf")
    it = 0
    for it in range(1, max_iter + 1):
        agg = weighted_agg(prov, w, parties)
        dev = max(abs(agg[p] - target[p]) for p in parties)
        if dev <= tol:
            break
        for p in parties:
            if base_nat[p] > 0.001 and agg[p] > 1e-6:
                r[p] *= target[p] / agg[p]
        prov = provincial_from_ratios(base_prov, r, parties)
    return prov, r, it, dev


def allocate(prov_shares, valid_votes, escanos, parties):
    seats = {}
    for code, sh in prov_shares.items():
        vv = valid_votes[code]
        votes = {p: max(0.0, sh[p]) * vv / 100.0 for p in parties}
        seats[code] = dhondt(votes, escanos[code], C.DHONDT_THRESHOLD, vv)
    return seats


# --------------------------------------------------------------------------- #
def main() -> int:
    obs = C.Observations()
    inter = C.Interior()
    parties = C.MODELED_PARTIES

    fc = json.loads((C.DATA / "modelo" / "forecast_state.json").read_text(encoding="utf-8"))
    target = {p: fc["partidos"][p]["punto"] for p in parties}
    sigma = {p: fc["partidos"][p]["sd_error_backtest"] for p in parties}

    base_prov, base_nat = build_base(inter, parties)
    valid_votes = inter.valid_votes(BASE_ELECTION)
    escanos = inter.seats(BASE_ELECTION)
    names = {p["codigo"]: p["nombre"] for p in inter.provinces(BASE_ELECTION)}
    total_vv = sum(valid_votes.values())
    w = {c: valid_votes[c] / total_vv for c in valid_votes}

    # --- Escenario central --------------------------------------------------
    prov_shares, ratios, calib_iters, calib_dev = calibrate(
        base_prov, base_nat, target, parties, w)
    central_seats = allocate(prov_shares, valid_votes, escanos, parties)

    coherence_votes = {p: weighted_agg(prov_shares, w, parties)[p] - target[p]
                       for p in parties}
    max_dev_votes = max(abs(v) for v in coherence_votes.values())

    # --- Simulación ---------------------------------------------------------
    rng = np.random.default_rng(SEED)
    n_p = len(parties)
    mu = np.array([target[p] for p in parties])
    sd = np.array([sigma[p] for p in parties])
    seats_runs = {c: np.zeros((N_RUNS, n_p), dtype=np.int16) for c in base_prov}

    for r_ in range(N_RUNS):
        draw = np.clip(rng.normal(mu, sd), 0.0, None)
        s = draw.sum()
        draw = draw * (100.0 / s) if s > 0 else draw
        tgt = {p: float(draw[i]) for i, p in enumerate(parties)}
        ps, _, _, _ = calibrate(base_prov, base_nat, tgt, parties, w,
                                tol=0.08, max_iter=12)
        alloc = allocate(ps, valid_votes, escanos, parties)
        for c in alloc:
            seats_runs[c][r_, :] = [alloc[c][p] for p in parties]

    # --- Agregados ----------------------------------------------------------
    prov_out = {}
    national_runs = np.zeros((N_RUNS, n_p), dtype=np.int32)
    for c, arr in seats_runs.items():
        national_runs += arr
        d = {}
        for i, p in enumerate(parties):
            col = arr[:, i]
            d[p] = {
                "media": round(float(col.mean()), 2),
                "ic95": [int(np.percentile(col, 2.5)), int(np.percentile(col, 97.5))],
                "prob_ge1": round(float((col >= 1).mean()), 3),
            }
        prov_out[c] = {"nombre": names.get(int(c), str(c)),
                       "escanos": escanos[c], "partidos": d}

    national = {}
    for i, p in enumerate(parties):
        col = national_runs[:, i]
        national[p] = {
            "media": round(float(col.mean()), 2),
            "ic95": [int(np.percentile(col, 2.5)), int(np.percentile(col, 97.5))],
            "p_ge1": round(float((col >= 1).mean()), 3),
            "central_escenario": sum(central_seats[c][p] for c in central_seats),
        }

    sum_media = sum(v["media"] for v in national.values())

    meta = {
        "generado": date.today().isoformat(),
        "objetivo": "29N 2026-11-29",
        "base_provincial": BASE_ELECTION,
        "metodo": "swing proporcional uniforme desde 23J + calibración + D'Hondt",
        "n_runs": N_RUNS,
        "seed": SEED,
        "ratios_swing_calibrados": {p: round(ratios[p], 4) for p in parties},
        "calibracion": {"iteraciones": calib_iters, "desviacion_max_pp": round(calib_dev, 4)},
        "coherencia": {
            "suma_medias_escanos": round(sum_media, 3),
            "total_escanos": 350,
            "desviacion_escanos": round(sum_media - 350, 3),
            "tolerancia": COHERENCE_TOL,
            "ok_escanos": abs(sum_media - 350) <= COHERENCE_TOL,
            "max_desviacion_votos_pp": round(max_dev_votes, 4),
            "ok_votos": max_dev_votes <= COHERENCE_TOL,
        },
        "advertencia": (
            "Swing proporcional uniforme: no modela terremotos locales ni "
            "elasticidades provinciales distintas. Intervalos provinciales de "
            "partidos pequeños muy anchos (diseño honesto)."
        ),
    }

    out = {"meta": meta, "nacional": national, "provincias": prov_out}
    with open(C.DATA / "modelo" / "seats.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print(f"OK seats.json — {N_RUNS} runs, {len(prov_out)} provincias, "
          f"calibración {calib_iters} it (dev {calib_dev:.4f} pp)")
    print("  Escaños (media, IC95):")
    for p in sorted(national, key=lambda x: -national[x]["media"]):
        n = national[p]
        print(f"    {p:8s} {n['media']:6.1f}  IC95=[{n['ic95'][0]:3d},{n['ic95'][1]:3d}]  "
              f"(central={n['central_escenario']})")
    print(f"  Coherencia escaños: suma={sum_media:.2f} "
          f"(ok={meta['coherencia']['ok_escanos']})")
    print(f"  Coherencia votos:   max dev={max_dev_votes:.4f} pp "
          f"(ok={meta['coherencia']['ok_votos']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
