#!/usr/bin/env python3
"""Test de coherencia estatal–provincial del modelo 29N.

Sin dependencias de test (assert nativo, como `pipeline/interior/test_dhondt.py`).
Falla si:
  1. la suma de las **medias de escaños** difiere de 350 en más de 0,1;
  2. en alguna provincia la suma de medias de escaños difiere de sus escaños;
  3. el **agregado provincial ponderado por votos** de las cuotas de partido
     difiere del forecast estatal en más de 0,1 pp para algún partido.

Ejecutar:
    /root/.venvs/29n/bin/python pipeline/modelo/test_coherence.py
    (o `pytest pipeline/modelo/test_coherence.py`, sin fixtures)
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common as C          # noqa: E402
import provincial as P      # noqa: E402

TOL = 0.1


def _load():
    seats = json.loads((C.DATA / "modelo" / "seats.json").read_text(encoding="utf-8"))
    fc = json.loads((C.DATA / "modelo" / "forecast_state.json").read_text(encoding="utf-8"))
    return seats, fc


def check_suma_escanos_nacional():
    seats, _ = _load()
    total = sum(v["media"] for v in seats["nacional"].values())
    assert abs(total - 350) <= TOL, f"suma de medias = {total:.3f}, se esperaba 350±{TOL}"
    return total


def check_escanos_por_provincia():
    seats, _ = _load()
    peor = 0.0
    for code, p in seats["provincias"].items():
        total = sum(x["media"] for x in p["partidos"].values())
        peor = max(peor, abs(total - p["escanos"]))
        assert abs(total - p["escanos"]) <= TOL, (
            f"provincia {code} ({p['nombre']}): suma medias = {total:.3f}, "
            f"escaños = {p['escanos']}")
    return peor


def check_coherencia_votos():
    _, fc = _load()
    parties = C.MODELED_PARTIES
    target = {p: fc["partidos"][p]["punto"] for p in parties}

    inter = C.Interior()
    base_prov, base_nat = P.build_base(inter, parties)
    vv = inter.valid_votes(P.BASE_ELECTION)
    w = {c: vv[c] / sum(vv.values()) for c in vv}

    prov, _, _, dev = P.calibrate(base_prov, base_nat, target, parties, w)
    agg = P.weighted_agg(prov, w, parties)
    peor = 0.0
    for p in parties:
        d = abs(agg[p] - target[p])
        peor = max(peor, d)
        assert d <= TOL, f"{p}: agregado provincial {agg[p]:.4f} vs estatal {target[p]:.4f}"
    assert dev <= TOL
    return peor


def run():
    print("Test de coherencia estatal–provincial (29N)")
    t = check_suma_escanos_nacional()
    print(f"  OK suma de medias de escaños = {t:.3f} (350 ± {TOL})")
    d = check_escanos_por_provincia()
    print(f"  OK escaños por provincia (desviación máxima {d:.4f})")
    v = check_coherencia_votos()
    print(f"  OK coherencia de votos (desviación máxima {v:.4f} pp ≤ {TOL})")
    print("TODO OK")


# Wrappers para que `pytest` también los recoja (sin fixtures)
def test_suma_escanos_nacional():
    check_suma_escanos_nacional()


def test_escanos_por_provincia():
    check_escanos_por_provincia()


def test_coherencia_votos():
    check_coherencia_votos()


if __name__ == "__main__":
    run()
