#!/usr/bin/env python3
"""Fase 4-c (segundo uso) — Post-estratificación MRP del 29N.

Ajusta el MRP con **solo** microdatos CIS anteriores al 29-11-2026 y lo
post-estratifica con el censo INE 2024 (tabla 66600). Escribe
`data/processed/mrp/poststrat.json` con:

- las celdas censales usadas como denominador,
- las cuotas provinciales post-estratificadas (crudas y calibradas al forecast
  estatal de `data/processed/modelo/forecast_state.json`),
- el agregado nacional y los diagnósticos de calibración.

**El MRP no se adopta como método de producción** (pierde el backtest provincial
frente al swing uniforme; ver `docs/notes/mrp.md`). Este artefacto es la
post-estratificación reproducible del candidato, para contraste.

Uso:
    /root/.venvs/29n-mrp/bin/python pipeline/mrp/poststrat_29n.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mrp_core as M  # noqa: E402
import mrp_hier as H  # noqa: E402

CUT = "2026-11-29"
WINDOW_DAYS = 1095
C_REG = 1.0
CENSO_PERIOD = 2024
BASE_ELECTION = "2023-07-23"
OUT = M.MRP / "poststrat.json"


def main() -> int:
    t0 = time.time()
    M.MRP.mkdir(parents=True, exist_ok=True)
    forecast = json.loads((M.DATA / "modelo" / "forecast_state.json")
                          .read_text(encoding="utf-8"))
    target = {p: float(forecast["partidos"][p]["punto"]) for p in M.MODELED_PARTIES}

    df = M.load_microdata(M.MODELED_PARTIES)
    train, sel = M.training_set(df, CUT, WINDOW_DAYS)
    u = M.usable(train)
    studies = sorted(sel["estudio_id"].astype(str).tolist())

    model, classes = M.fit_mrp(u, M.MODELED_PARTIES, C=C_REG)
    censo_all = pd.read_csv(M.MRP / "censo_cells.csv")
    censo = censo_all[censo_all["periodo"] == CENSO_PERIOD].drop(columns=["periodo"]).copy()
    proba = M.predict_cells(model, classes, censo)
    raw = M.poststratify(proba, model, M.MODELED_PARTIES)

    inter = M.Interior()
    w = inter.weights(BASE_ELECTION)
    names = inter.province_names(BASE_ELECTION)
    escanos = inter.seats(BASE_ELECTION)

    nat_raw = {p: round(float(sum(w[c] * raw[c][p] for c in raw)), 3)
               for p in M.MODELED_PARTIES}
    cal, ratios, cal_iters, cal_dev = M.calibrate(raw, target, w,
                                                  M.MODELED_PARTIES)
    nat_cal = {p: round(float(sum(w[c] * cal[c][p] for c in cal)), 3)
               for p in M.MODELED_PARTIES}

    # --- Variante multinivel (jerárquica) del 29N, para contraste ------------
    mh, logh = H.fit_mrp_hier(u, M.MODELED_PARTIES)
    Ph = H.predict_cells_hier(mh, censo)
    raw_h = H.poststratify_hier(Ph, censo, mh.classes, M.MODELED_PARTIES)
    cal_h, ratios_h, it_h, dev_h = M.calibrate(raw_h, target, w, M.MODELED_PARTIES)
    nat_raw_h = {p: round(float(sum(w[c] * raw_h[c][p] for c in raw_h)), 3)
                 for p in M.MODELED_PARTIES}
    nat_cal_h = {p: round(float(sum(w[c] * cal_h[c][p] for c in cal_h)), 3)
                 for p in M.MODELED_PARTIES}
    provincias_h = {
        str(c): {"nombre": names.get(c, str(c)), "escanos": escanos.get(c),
                 "partidos": {p: {"crudo": round(raw_h[c][p], 3),
                                   "calibrado": round(cal_h[c][p], 3)}
                              for p in M.MODELED_PARTIES}}
        for c in sorted(raw_h)}

    # Celdas de post-estratificación (provincia × sexo × edad × estudios)
    cols = ["provincia", "sexo", "edad_grupo", "edu_grupo", "poblacion"] + M.MODELED_PARTIES
    den = proba[[f"p_{c}" for c in model.classes_ if c in M.MODELED_PARTIES]].sum(axis=1)
    filas = []
    censo_r = censo.reset_index(drop=True)
    for i in range(len(proba)):
        d = float(den.iloc[i])
        sh = []
        for k in M.MODELED_PARTIES:
            col = proba.get(f"p_{k}")
            sh.append(round(float(col.iloc[i]) / d * 100, 2)
                      if (col is not None and d > 0) else 0.0)
        filas.append([int(censo_r.loc[i, "provincia"]), censo_r.loc[i, "sexo"],
                      censo_r.loc[i, "edad_grupo"], censo_r.loc[i, "edu_grupo"],
                      int(censo_r.loc[i, "poblacion"])] + sh)

    provincias = {}
    for c in sorted(raw):
        provincias[str(c)] = {
            "nombre": names.get(c, str(c)),
            "escanos": escanos.get(c),
            "partidos": {
                p: {"crudo": round(raw[c][p], 3), "calibrado": round(cal[c][p], 3)}
                for p in M.MODELED_PARTIES},
        }

    out = {
        "meta": {
            "generado": time.strftime("%Y-%m-%d"),
            "objetivo": "29N 2026-11-29",
            "metodo": "MRP pragmático: logits multinomiales (demo × provincia) + "
                      "post-estratificación censal INE 66600",
            "adoptado": False,
            "motivo_no_adopcion": "El backtest provincial (2015-2023) da mejor MAE al "
                                  "swing uniforme; ver docs/notes/mrp.md §4",
            "corte_entrenamiento": CUT,
            "ventana_dias": WINDOW_DAYS,
            "estudios_entrenamiento": studies,
            "filas_entrenamiento": int(len(u)),
            "regularizacion_C": C_REG,
            "censo_tabla": "66600",
            "censo_periodo": CENSO_PERIOD,
            "universo": M.MODELED_PARTIES,
            "pesos_agregacion": "votos válidos provinciales de 23J (misma base que seats.json)",
        },
        "nacional": {
            "crudo": nat_raw,
            "calibrado": nat_cal,
            "forecast_objetivo": {p: round(target[p], 3) for p in M.MODELED_PARTIES},
        },
        "calibracion": {
            "iteraciones": cal_iters,
            "desviacion_max_pp": round(cal_dev, 4),
            "ratios": {p: round(ratios[p], 4) for p in M.MODELED_PARTIES},
        },
        "variante_jerarquica": {
            "metodo": "multinivel: demografía (fija) + provincia (efecto aleatorio, "
                      "τ² por evidencia Laplace)",
            "tau_seleccionado": logh["tau_seleccionado"],
            "tau2_seleccionado": logh["tau2_seleccionado"],
            "nacional": {"crudo": nat_raw_h, "calibrado": nat_cal_h,
                         "forecast_objetivo": {p: round(target[p], 3)
                                               for p in M.MODELED_PARTIES}},
            "calibracion": {"iteraciones": it_h, "desviacion_max_pp": round(dev_h, 4)},
            "provincias": provincias_h,
            "nota": "No adoptada: en el backtest provincial queda al mismo nivel "
                    "que la variante de efectos fijos y por detrás del swing; "
                    "ver docs/notes/mrp-estado.md.",
        },
        "provincias": provincias,
        "celdas_poststrat": {"columnas": cols, "filas": filas},
        "segundos": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK {OUT}")
    print(f"  {len(studies)} estudios · {len(u)} filas · censo {CENSO_PERIOD} · "
          f"{len(filas)} celdas")
    print("  Nacional (crudo -> calibrado / objetivo):")
    for p in sorted(M.MODELED_PARTIES, key=lambda x: -nat_cal[x]):
        print(f"    {p:10s} {nat_raw[p]:6.1f} -> {nat_cal[p]:6.1f}  (obj {target[p]:5.1f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
