#!/usr/bin/env python3
"""Sensibilidad del backtest MRP al **año de censo** (bloqueo conocido, §2 mr.md).

Motivación
----------
La tabla censal 66600 (provincia × sexo × edad × estudios) arranca en **2021**.
El Censo 2011 no tiene descarga CSV/API por provincia ni armonización de
estudios compatible, así que el backtest 2015-2019 se post-estratifica forzando
la estructura de 2021. Este script cuantifica **cuánto** mueve ese supuesto:

para cada elección, post-estratifica el mismo modelo con los **cuatro** periodos
censales disponibles (2021-2024) y mide el MAE provincial resultante.

Lectura honesta:
- Si el rango (max-min) del MAE entre censos es pequeño frente a la brecha
  MRP-swing ⇒ el supuesto censal **no** cambia el veredicto, y el backtest es
  sólido pese a la limitación.
- Si es grande ⇒ el backtest de esas elecciones es **inconcluso**: se declara, no
  se fuerza.

Salida: `data/processed/mrp/sensitivity_censo.json`.

Uso:
    /root/.venvs/29n-mrp/bin/python pipeline/mrp/sensitivity_censo.py
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

OUT = M.MRP / "sensitivity_censo.json"
C_REG = 1.0
WINDOW_DAYS = 1095
CENSOS = [2021, 2022, 2023, 2024]

ELECTIONS = [
    {"id": "2015-12-20", "prev": "2011-11-20"},
    {"id": "2016-06-26", "prev": "2015-12-20"},
    {"id": "2019-04-28", "prev": "2016-06-26"},
    {"id": "2019-11-10", "prev": "2019-04-28"},
    {"id": "2023-07-23", "prev": "2019-11-10"},
]


def mae(pred, real, universe, provs):
    return float(np.mean([abs(pred[c][p] - real[c][p])
                          for c in provs for p in universe]))


def main() -> int:
    t0 = time.time()
    df = M.load_microdata(M.BACKTEST_PARTIES)
    inter = M.Interior()
    universe = M.BACKTEST_PARTIES
    censo_all = pd.read_csv(M.MRP / "censo_cells.csv")

    rep = {
        "generado": time.strftime("%Y-%m-%d"),
        "objetivo": "Cuantificar el supuesto de censo (§2): el backtest 2015-2019 "
                    "usa la estructura 2021 porque la serie 66600 arranca ahí.",
        "nota_censo_2011": "El Censo 2011 (INE) no ofrece descarga CSV/API por "
                           "provincia × edad × estudios; no es replicable aquí.",
        "censos_probados": CENSOS,
        "elecciones": {},
    }

    for el in ELECTIONS:
        eid, prev = el["id"], el["prev"]
        train, sel = M.training_set(df, eid, WINDOW_DAYS)
        u = M.usable(train)
        model, classes = M.fit_mrp(u, universe, C=C_REG)
        real = inter.provincial_shares(eid, universe)
        real_nat = inter.national_shares(eid, universe)
        provs = sorted(real)
        w = inter.weights(eid)

        # swing (independiente del censo) para medir la brecha a batir
        base_prov = inter.provincial_shares(prev, universe)
        sw, _, _, _ = M.swing_uniforme(base_prov, real_nat, w, universe, floor=0.0)
        swf, _, _, _ = M.swing_uniforme(base_prov, real_nat, w, universe, floor=0.1)
        swing_best = min(mae(sw, real, universe, provs),
                         mae(swf, real, universe, provs))

        por_censo = {}
        for cp in CENSOS:
            censo = censo_all[censo_all["periodo"] == cp].drop(
                columns=["periodo"]).copy()
            proba = M.predict_cells(model, classes, censo)
            raw = M.poststratify(proba, model, universe)
            cal, _, _, _ = M.calibrate(raw, real_nat, w, universe)
            por_censo[str(cp)] = round(mae(cal, real, universe, provs), 4)

        vals = list(por_censo.values())
        rango = max(vals) - min(vals)
        ref = por_censo[str(2021)]      # el que usa el backtest principal
        gap = ref - swing_best          # brecha MRP(2021) - swing
        rep["elecciones"][eid] = {
            "mae_por_censo": por_censo,
            "censo_backtest_principal": 2021 if eid != "2023-07-23" else 2023,
            "rango_mae_entre_censos": round(rango, 4),
            "swing_mejor": round(swing_best, 4),
            "gap_mrp_vs_swing_en_2021": round(gap, 4),
            "conclusion": ("robusto: el supuesto censal mueve el MAE menos que la "
                           "brecha a batir" if rango < abs(gap)
                           else "sensible al censo: el veredicto de esta elección "
                                "no se apoya solo en el reparto demográfico"),
        }
        print(f"{eid}: MAE por censo {por_censo} | rango {rango:.3f} | "
              f"swing {swing_best:.3f} | gap {gap:+.3f}")

    # resumen
    rangos = [v["rango_mae_entre_censos"] for v in rep["elecciones"].values()]
    rep["resumen"] = {
        "rango_mae_medio_entre_censos_pp": round(float(np.mean(rangos)), 4),
        "rango_mae_max_entre_censos_pp": round(float(np.max(rangos)), 4),
        "interpretacion": "Si el rango máximo entre censos (2021-2024) es mucho "
                          "menor que la brecha MRP-swing (~0,2 pp en la media), el "
                          "supuesto de censo de §2 no es el que decide el veredicto.",
    }
    rep["segundos"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nOK {OUT} ({rep['segundos']}s)")
    print(f"  rango medio entre censos: "
          f"{rep['resumen']['rango_mae_medio_entre_censos_pp']:.3f} pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
