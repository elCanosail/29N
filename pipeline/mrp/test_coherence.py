#!/usr/bin/env python3
"""Fase 4-c (segundo uso) — Coherencia de la post-estratificación MRP.

Comprueba que:
1. cada provincia suma 100 % (crudo y calibrado);
2. el agregado provincial ponderado por votos = forecast estatal (≤ 0,1 pp);
3. los denominadores censales son completos (52 provincias × 42 celdas);
4. la población censal coincide con el total publicado por INE para 18+.

Ejecutable directo y con pytest:
    /root/.venvs/29n-mrp/bin/python pipeline/mrp/test_coherence.py
    /root/.venvs/29n-mrp/bin/pytest pipeline/mrp/test_coherence.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mrp_core as M  # noqa: E402

TOL_PP = 0.1


def _load():
    return json.loads((M.MRP / "poststrat.json").read_text(encoding="utf-8"))


def test_provincias_suman_100():
    d = _load()
    peor, quien = 0.0, None
    for prov, info in d["provincias"].items():
        for key in ("crudo", "calibrado"):
            s = sum(info["partidos"][p][key] for p in d["meta"]["universo"])
            if abs(s - 100.0) > peor:
                peor, quien = abs(s - 100.0), (prov, key)
    assert peor < 0.05, f"provincia {quien} desvía {peor:.4f} pp"


def test_agregado_provincial_igual_forecast():
    d = _load()
    inter = M.Interior()
    w = inter.weights("2023-07-23")
    parties = d["meta"]["universo"]
    agg = {p: sum(w[int(c)] * d["provincias"][c]["partidos"][p]["calibrado"]
                  for c in d["provincias"]) for p in parties}
    obj = d["nacional"]["forecast_objetivo"]
    dev = max(abs(agg[p] - obj[p]) for p in parties)
    assert dev <= TOL_PP, f"desviación agregado {dev:.4f} pp > {TOL_PP}"
    return dev


def test_celdas_censales_completas():
    d = _load()
    filas = d["celdas_poststrat"]["filas"]
    provs = {f[0] for f in filas}
    assert len(provs) == 52, f"{len(provs)} provincias, se esperaban 52"
    assert len(filas) == 52 * 2 * 7 * 3, f"{len(filas)} celdas, se esperaban 2184"


def test_poblacion_censal():
    meta = json.loads((M.MRP / "censo_meta.json").read_text(encoding="utf-8"))
    assert meta["provincias"] == 52
    assert meta["poblacion_total_2024"] == 40_594_509, meta["poblacion_total_2024"]
    assert set(meta["periodos"]) == {2021, 2022, 2023, 2024}


def test_estructura_igual_seats():
    """El JSON del MRP debe poder compararse lado a lado con seats.json."""
    d = _load()
    seats = json.loads((M.DATA / "modelo" / "seats.json").read_text(encoding="utf-8"))
    assert set(d["provincias"]) == set(seats["provincias"]), "provincias distintas"
    assert set(d["meta"]["universo"]) == set(seats["nacional"]), "universo distinto"


def main() -> int:
    tests = [test_provincias_suman_100, test_agregado_provincial_igual_forecast,
             test_celdas_censales_completas, test_poblacion_censal,
             test_estructura_igual_seats]
    ok = True
    for t in tests:
        try:
            extra = t()
            msg = f"  (dev máx {extra:.4f} pp)" if isinstance(extra, float) else ""
            print(f"PASS {t.__name__}{msg}")
        except AssertionError as exc:
            ok = False
            print(f"FAIL {t.__name__}: {exc}")
    print("OK" if ok else "FALLO")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
