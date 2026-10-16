#!/usr/bin/env python3
"""Fase 4-c (segundo uso) — Backtest provincial del MRP frente al swing uniforme.

Para cada una de las 5 elecciones (20D-2015, 26J-2016, 28A-2019, 10N-2019,
23J-2023):

1. Se entrena el MRP **solo con microdatos CIS anteriores a la votación**
   (ventana de 3 años; ver `docs/notes/mrp.md` §3) y se post-estratifica con la
   tabla censal 66600.
2. Se calcula el rival: **swing proporcional uniforme** desde la elección
   general anterior (misma mecánica que `data/processed/modelo/seats.json`).
3. Se comparan ambos contra los **resultados reales** de Interior, restringidos
   al universo modelado (13 partidos + Ciudadanos en el backtest).

Dos pruebas, para separar los dos errores que se mezclan en una previsión:

- **Test A — "geografía pura"**: ambos métodos se calibran al **resultado
  nacional real**. Si el MRP pierde aquí, pierde por reparto provincial, no por
  la estimación nacional de las encuestas.
- **Test B — "previsión sin fuga"**: ambos se calibran al **nacional directo de
  las mismas encuestas** que usa el MRP (ventana de entrenamiento). Es lo más
  parecido a un pronóstico real hecha la comparación como para como.

Salida: `data/processed/mrp/backtest_mrp.json`.

Uso:
    /root/.venvs/29n-mrp/bin/python pipeline/mrp/backtest_mrp.py
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

OUT = M.MRP / "backtest_mrp.json"

WINDOW_DAYS = 1095          # 3 años
C_REG = 1.0                 # regularización L2 del multinomial
SWING_FLOOR = 0.1           # pp de base mínima uniforme (partidos nuevos)

ELECTIONS = [
    {"id": "2015-12-20", "prev": "2011-11-20", "censo": 2021},
    {"id": "2016-06-26", "prev": "2015-12-20", "censo": 2021},
    {"id": "2019-04-28", "prev": "2016-06-26", "censo": 2021},
    {"id": "2019-11-10", "prev": "2019-04-28", "censo": 2021},
    {"id": "2023-07-23", "prev": "2019-11-10", "censo": 2023},
]


def mae(pred, real, universe, provs, big_parties=None):
    """MAE media sobre provincias × partidos; opcionalmente solo partidos grandes."""
    errs, per_party = [], {p: [] for p in universe}
    for c in provs:
        for p in universe:
            if big_parties is not None and p not in big_parties:
                continue
            e = abs(pred[c][p] - real[c][p])
            errs.append(e)
            per_party[p].append(e)
    out = {"mae": float(np.mean(errs)), "n": len(errs)}
    if big_parties is None:
        out["por_partido"] = {p: float(np.mean(v)) for p, v in per_party.items()}
    return out


def weighted_mae(pred, real, universe, provs, w):
    tot = sum(w[c] for c in provs)
    return float(sum(w[c] * abs(pred[c][p] - real[c][p])
                     for c in provs for p in universe) / (tot * len(universe)))


def main() -> int:
    t_start = time.time()
    M.MRP.mkdir(parents=True, exist_ok=True)
    df = M.load_microdata(M.BACKTEST_PARTIES)
    inter = M.Interior()
    universe = M.BACKTEST_PARTIES
    censo_all = pd.read_csv(M.MRP / "censo_cells.csv")

    report = {
        "generado": time.strftime("%Y-%m-%d"),
        "metrica": "MAE provincial en % sobre voto válido, normalizado al universo "
                   "(13 partidos modelados + Ciudadanos), 52 provincias",
        "universo": universe,
        "ventana_entrenamiento_dias": WINDOW_DAYS,
        "regularizacion_C": C_REG,
        "swing_floor_pp": SWING_FLOOR,
        "elecciones": {},
    }

    for el in ELECTIONS:
        eid, prev, cp = el["id"], el["prev"], el["censo"]
        t0 = time.time()
        print(f"\n=== {eid} (base {prev}, censo {cp}) ===")

        train, sel = M.training_set(df, eid, WINDOW_DAYS)
        u = M.usable(train)
        studies = sorted(sel["estudio_id"].astype(str).tolist())
        n_rows = len(u)

        model, classes = M.fit_mrp(u, universe, C=C_REG)
        censo = censo_all[censo_all["periodo"] == cp].drop(columns=["periodo"]).copy()
        proba = M.predict_cells(model, classes, censo)
        mrp_raw = M.poststratify(proba, model, universe)

        # Variante exploratoria anclada al voto de la elección anterior
        ua = M.usable_anchored(train)
        base_prov_prev = inter.provincial_shares(prev, universe)
        try:
            ma, classes_a, rec_cats = M.fit_mrp_anchored(ua, universe, C=C_REG)
            mrp_anch = M.predict_anchored(ma, classes_a, rec_cats, censo,
                                          base_prov_prev, universe)
            anch_rows = len(ua)
        except Exception as exc:  # noqa: BLE001
            print(f"  [aviso] anclado no ajustable: {exc}")
            mrp_anch, anch_rows = None, 0

        # Variante multinivel (jerárquica): provincia como efecto aleatorio con
        # varianza τ² estimada por evidencia (Laplace). Ver pipeline/mrp/mrp_hier.py.
        try:
            mh, logh = H.fit_mrp_hier(u, universe)
            P_h = H.predict_cells_hier(mh, censo)
            mrp_hier_raw = H.poststratify_hier(P_h, censo, mh.classes, universe)
            hier_info = {"tau": logh["tau_seleccionado"],
                         "tau2": logh["tau2_seleccionado"],
                         "criterio_laplace_max": round(logh["criterio_laplace_max"], 3),
                         "rejilla": logh["grid"],
                         "clases": logh["clases"]}
            print(f"  [jerárquico] τ seleccionado = {logh['tau_seleccionado']:.2f}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [aviso] jerárquico no ajustable: {exc}")
            mrp_hier_raw, hier_info = None, {"error": str(exc)}

        # --- Referencias reales -------------------------------------------------
        real = inter.provincial_shares(eid, universe)
        real_nat = inter.national_shares(eid, universe)
        provs = sorted(real)
        w = inter.weights(eid)
        base_prov = inter.provincial_shares(prev, universe)

        # Nacional directo de las encuestas de entrenamiento (sin fuga)
        wtot = {p: float(u.loc[u["clase"] == p, "peso"].sum()) for p in universe}
        s = sum(wtot.values())
        polls_nat = {p: 100.0 * v / s for p, v in wtot.items()}

        big = {p for p in universe if real_nat[p] >= 1.0}

        res = {
            "estudios_entrenamiento": studies,
            "filas_entrenamiento": n_rows,
            "filas_entrenamiento_anclado": anch_rows,
            "jerarquico": hier_info,
            "censo_periodo": cp,
            "cobertura_muestras_pp": round(float(sum(wtot.values()) /
                                                  u["peso"].sum() * 100), 3),
            "nacional_real": {p: round(real_nat[p], 3) for p in universe},
            "nacional_encuestas": {p: round(polls_nat[p], 3) for p in universe},
            "nacional_mrp_crudo": {
                p: round(float(sum(w[c] * mrp_raw[c][p] for c in provs)), 3)
                for p in universe},
            "tests": {},
        }

        targets = {
            "A_objetivo_nacional_real": real_nat,
            "B_objetivo_nacional_encuestas": polls_nat,
        }

        for tname, target in targets.items():
            mrp_cal, r_cal, it_cal, dev_cal = M.calibrate(mrp_raw, target, w, universe)
            sw, r_sw, it_sw, dev_sw = M.swing_uniforme(base_prov, target, w, universe,
                                                       floor=0.0)
            swf, r_swf, it_swf, dev_swf = M.swing_uniforme(base_prov, target, w,
                                                           universe,
                                                           floor=SWING_FLOOR)
            methods = {
                "mrp": mrp_cal,
                "mrp_crudo": mrp_raw,
                "swing": sw,
                "swing_fix": swf,
            }
            if mrp_anch is not None:
                anch_cal, _, _, _ = M.calibrate(mrp_anch, target, w, universe)
                methods["mrp_anclado"] = anch_cal
            if mrp_hier_raw is not None:
                hier_cal, _, _, _ = M.calibrate(mrp_hier_raw, target, w, universe)
                methods["mrp_jerarquico"] = hier_cal
            t = {}
            for mname, pred in methods.items():
                a = mae(pred, real, universe, provs)
                b = mae(pred, real, universe, provs, big_parties=big)
                t[mname] = {
                    "mae_global": round(a["mae"], 4),
                    "mae_partidos_ge1": round(b["mae"], 4),
                    "mae_ponderado_votos": round(weighted_mae(pred, real, universe, provs, w), 4),
                    "mae_por_partido": {p: round(v, 4) for p, v in a["por_partido"].items()},
                }
            t["_mejor_swing"] = min(t["swing"]["mae_global"], t["swing_fix"]["mae_global"])
            t["_veredicto_global"] = ("MRP gana" if t["mrp"]["mae_global"] < t["_mejor_swing"]
                                      else "swing gana")
            t["_veredicto_big"] = ("MRP gana" if t["mrp"]["mae_partidos_ge1"]
                                   < min(t["swing"]["mae_partidos_ge1"],
                                         t["swing_fix"]["mae_partidos_ge1"])
                                   else "swing gana")
            res["tests"][tname] = t
            print(f"  [{tname}] MAE global  MRP {t['mrp']['mae_global']:.3f} | "
                  f"MRP_jer {t.get('mrp_jerarquico',{}).get('mae_global', float('nan')):.3f} | "
                  f"MRP_anc {t.get('mrp_anclado',{}).get('mae_global', float('nan')):.3f} | "
                  f"swing {t['swing']['mae_global']:.3f} | swing_fix {t['swing_fix']['mae_global']:.3f}"
                  f"  -> {t['_veredicto_global']}")

        report["elecciones"][eid] = res
        print(f"  ({time.time()-t0:.1f}s, {n_rows} filas, {len(studies)} estudios)")

    # --- Agregados --------------------------------------------------------------
    agg = {}
    for tname in ("A_objetivo_nacional_real", "B_objetivo_nacional_encuestas"):
        for mname in ("mrp", "mrp_crudo", "mrp_jerarquico", "mrp_anclado", "swing", "swing_fix"):
            if any(mname not in report["elecciones"][e]["tests"][tname]
                   for e in report["elecciones"]):
                continue
            vals = [report["elecciones"][e]["tests"][tname][mname]["mae_global"]
                    for e in report["elecciones"]]
            vals_big = [report["elecciones"][e]["tests"][tname][mname]["mae_partidos_ge1"]
                        for e in report["elecciones"]]
            agg[f"{tname}|{mname}"] = {
                "mae_global_medio": round(float(np.mean(vals)), 4),
                "mae_global_por_eleccion": [round(v, 4) for v in vals],
                "mae_partidos_ge1_medio": round(float(np.mean(vals_big)), 4),
            }
        swing_best = [min(report["elecciones"][e]["tests"][tname]["swing"]["mae_global"],
                          report["elecciones"][e]["tests"][tname]["swing_fix"]["mae_global"])
                      for e in report["elecciones"]]
        agg[f"{tname}|swing_mejor"] = {
            "mae_global_medio": round(float(np.mean(swing_best)), 4),
            "mae_global_por_eleccion": [round(v, 4) for v in swing_best],
        }
    report["agregado"] = agg

    # Veredicto global
    a_mrp = agg["A_objetivo_nacional_real|mrp"]["mae_global_medio"]
    a_anc = agg["A_objetivo_nacional_real|mrp_anclado"]["mae_global_medio"]
    a_sw = agg["A_objetivo_nacional_real|swing_mejor"]["mae_global_medio"]
    b_mrp = agg["B_objetivo_nacional_encuestas|mrp"]["mae_global_medio"]
    b_anc = agg["B_objetivo_nacional_encuestas|mrp_anclado"]["mae_global_medio"]
    b_sw = agg["B_objetivo_nacional_encuestas|swing_mejor"]["mae_global_medio"]
    best_a, best_b = min(a_mrp, a_anc), min(b_mrp, b_anc)
    report["veredicto"] = {
        "test_A_mae_medio": {"mrp": a_mrp, "mrp_anclado": a_anc,
                             "swing_mejor": a_sw,
                             "delta_pp_mrp": round(a_mrp - a_sw, 4),
                             "delta_pp_mrp_anclado": round(a_anc - a_sw, 4)},
        "test_B_mae_medio": {"mrp": b_mrp, "mrp_anclado": b_anc,
                             "swing_mejor": b_sw,
                             "delta_pp_mrp": round(b_mrp - b_sw, 4),
                             "delta_pp_mrp_anclado": round(b_anc - b_sw, 4)},
        "ganador": "MRP" if (best_a < a_sw and best_b < b_sw) else "swing uniforme",
        "mrp_especificado_gana": bool(a_mrp < a_sw and b_mrp < b_sw),
        "mejor_variante_mrp_gana": bool(best_a < a_sw and best_b < b_sw),
    }
    report["segundos_totales"] = round(time.time() - t_start, 1)

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n" + "=" * 72)
    v = report["veredicto"]
    print(f"VEREDICTO: {v['ganador']}")
    print(f"  Test A (nacional real):      MRP {a_mrp:.3f} | MRP_anc {a_anc:.3f} | "
          f"swing {a_sw:.3f}")
    print(f"  Test B (nacional encuestas): MRP {b_mrp:.3f} | MRP_anc {b_anc:.3f} | "
          f"swing {b_sw:.3f}")
    print(f"  MRP especificado gana: {v['mrp_especificado_gana']} · "
          f"mejor variante MRP gana: {v['mejor_variante_mrp_gana']}")
    print(f"OK {OUT} ({report['segundos_totales']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
