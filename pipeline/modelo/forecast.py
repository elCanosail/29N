#!/usr/bin/env python3
"""Fase 4 (paso 2) — Forecast estatal del 29N.

Produce la predicción estatal por partido a **nov-2026** con:
  - **punto primario**: el método que gana el backtest (`backtest.json`); en la
    práctica el *baseline* (última media ponderada), que empata en la práctica
    con TimesFM (ver `docs/notes/modelo.md`). Regla de honestidad: se usa el
    que mejor mide, no el que mejor vende.
  - **intervalos**: empíricos, de la desviación de los errores de ese método en
    el backtest (por partido; el error agrupado si n<4), **recalibrados** a su
    cobertura nominal con el factor multiplicativo de `calibracion.py`
    (`banda(L) = punto ± k_L·z·σ`; el punto NO cambia). Se publican las bandas
    del 80 % (p10–p90) y del 95 % (p2,5–p97,5).
  - además se publica el forecast **TimesFM** (punto + cuantiles nativos) como
    contraste.

Salidas: `data/processed/modelo/forecast_state.json` (primario) y
`forecast_state.timesfm.json` (TimesFM crudo).

Uso (tras `backtest.py`):
    /root/.venvs/29n/bin/python pipeline/modelo/forecast.py
"""

from __future__ import annotations

import json
import statistics
from datetime import date, timedelta

import numpy as np

import common as C

CHECKPOINT = "google/timesfm-2.5-200m-pytorch"
QUANTILE_LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
QUANTILE_COLUMNS = list(range(1, 10))
POINT_COLUMN = 5

# Cuantiles del forecast publicado. Los nativos de TimesFM solo llegan a
# q0.1..q0.9; 0,025/0,975 añaden la banda del 95 % recalibrada y 0,5 es el punto.
PUBLISHED_LEVELS = [0.025, 0.1, 0.2, 0.5, 0.8, 0.9, 0.975]


# --------------------------------------------------------------------------- #
# Runner TimesFM (compartido con backtest.py)
# --------------------------------------------------------------------------- #
def load_model(per_core_batch_size, max_context, horizon, torch_compile=False):
    import timesfm

    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
        CHECKPOINT, torch_compile=torch_compile)
    max_horizon = max(128, int(np.ceil(horizon / 128.0)) * 128)
    cfg = timesfm.ForecastConfig(
        max_context=int(np.ceil(max_context / 32.0) * 32),
        max_horizon=max_horizon,
        normalize_inputs=True,
        use_continuous_quantile_head=True,
        force_flip_invariance=True,
        infer_is_positive=True,
        fix_quantile_crossing=True,
        per_core_batch_size=max(1, per_core_batch_size),
    )
    model.compile(cfg)
    return model


def forecast_batch(model, series_list, horizon):
    """(point, quantiles). point: (n, H); quantiles: (n, H, 10); cols 1..9 = q0.1..q0.9."""
    point, quantiles = model.forecast(
        horizon=horizon, inputs=[np.asarray(s, dtype=float) for s in series_list])
    return np.asarray(point), np.asarray(quantiles)


# --------------------------------------------------------------------------- #
def last_data_month(obs):
    return max(o["date"] for o in obs.obs).replace(day=1)


def month_end(d):
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


def z_value(level):
    """Cuantil normal estándar (aprox. Acklam), sin dependencia de scipy."""
    # implementación compacta de la inversa de la normal estándar
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p = float(level)
    if p <= 0 or p >= 1:
        return float("nan")
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = (-2 * np.log(p)) ** 0.5
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = (-2 * np.log(1 - p)) ** 0.5
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def party_error_sd(backtest, parties):
    """σ de los errores del método primario por partido (backtest)."""
    metodo = backtest["mae_global"]["metodo_primario"]
    key = {"timesfm": "err_timesfm", "baseline": "err_baseline",
           "ensemble": "err_ensemble"}[metodo]
    pooled = []
    per = {}
    for eid, e in backtest["por_eleccion"].items():
        for p, x in e["partidos"].items():
            if x["real"] >= 0.1:
                per.setdefault(p, []).append(x[key])
                pooled.append(x[key])
    pooled_sd = statistics.pstdev(pooled) if len(pooled) > 1 else 2.5
    sd = {}
    for p in parties:
        v = per.get(p, [])
        # desviación muestral del propio partido (n-1); es la mejor estimación
        # disponible del error de la predicción para ese partido. Un σ agrupado
        # (dominado por los partidos grandes) sobreestimaba a los pequeños.
        sd[p] = max(0.10, statistics.stdev(v)) if len(v) >= 2 else pooled_sd
    return metodo, sd, pooled_sd


def main() -> int:
    obs = C.Observations()
    parties = C.MODELED_PARTIES

    bt_path = C.DATA / "modelo" / "backtest.json"
    if not bt_path.exists():
        raise SystemExit("Falta backtest.json — ejecuta antes pipeline/modelo/backtest.py")
    backtest = json.loads(bt_path.read_text(encoding="utf-8"))
    metodo, sd_party, pooled_sd = party_error_sd(backtest, parties)

    # Recalibración de intervalos (multiplicativa, sin tocar el punto). Import
    # local para evitar el ciclo de importación (calibracion usa z_value de aquí).
    import calibracion
    factores = calibracion.cargar_factores()
    if factores is None:
        print("AVISO: sin calibracion_intervalos.json — bandas sin recalibrar")
        print("       ejecuta antes: python pipeline/modelo/calibracion.py")

    # Series hasta el último mes con dato; objetivo nov-2026.
    grid = C.month_grid()
    last = last_data_month(obs)
    cut_idx = grid.index(month_end(last))       # mes con el último dato
    horizon = len(grid) - 1 - cut_idx           # meses hasta 2026-11
    hist_series = {}
    for p in parties:
        _, vals = C.build_party_series(p, obs)
        hist_series[p] = vals[: cut_idx + 1]

    model = load_model(per_core_batch_size=len(parties),
                       max_context=len(hist_series[parties[0]]), horizon=horizon)
    point, quantiles = forecast_batch(model, [hist_series[p] for p in parties], horizon)
    idx = horizon - 1  # mes objetivo = nov-2026

    ts_point = {p: float(point[i, idx]) for i, p in enumerate(parties)}
    ts_q = {p: {str(lv): float(quantiles[i, idx, QUANTILE_COLUMNS[k]])
                for k, lv in enumerate(QUANTILE_LEVELS)} for i, p in enumerate(parties)}
    # baseline = último valor de la serie (media ponderada actual)
    base_point = {p: float(hist_series[p][-1]) for p in parties}

    # Normalización al universo modelado (suma = 100)
    def norm(d):
        tot = sum(d.values())
        return {k: 100.0 * v / tot for k, v in d.items()} if tot else d

    n_ts = norm(ts_point)
    n_base = norm(base_point)

    prim = n_base if metodo == "baseline" else (
        n_ts if metodo == "timesfm" else {p: 0.5 * (n_ts[p] + n_base[p]) for p in parties})

    inter = C.Interior()
    real23 = inter.national_canonical("2023-07-23")
    universo = sum(real23.get(p, 0.0) for p in parties)

    out_partidos = {}
    for p in parties:
        s = sd_party[p]
        # Cuantiles publicados = punto ± k_L·z·σ (k=1 en niveles no recalibrados).
        # El punto (q0,5, z=0) queda EXACTAMENTE igual: la calibración solo toca
        # la semianchura.
        q = {str(lv): round(calibracion.calibrar_cuantil(prim[p], s, lv, factores), 3)
             for lv in PUBLISHED_LEVELS}
        out_partidos[p] = {
            "punto": round(prim[p], 3),
            "cuantiles": q,
            "sd_error_backtest": round(s, 3),
            "punto_timesfm": round(n_ts[p], 3),
            "punto_baseline": round(n_base[p], 3),
            "cuantiles_timesfm": {k: round(v, 3) for k, v in ts_q[p].items()},
        }

    meta = {
        "generado": date.today().isoformat(),
        "objetivo": "29N — elecciones generales 2026-11-29",
        "mes_predicho": "2026-11",
        "ultimo_mes_con_dato": last.isoformat(),
        "horizonte_meses": horizon,
        "historia_meses": cut_idx + 1,
        "metodo_primario": metodo,
        "motivo_metodo": backtest["mae_global"]["verdict"],
        "backtest_mae": {
            "timesfm": backtest["mae_global"]["timesfm"],
            "baseline": backtest["mae_global"]["baseline"],
            "ensemble": backtest["mae_global"]["ensemble"],
            "n": backtest["n_observaciones_mae"],
        },
        "intervalos": {
            "tipo": "empiricos (errores del backtest del metodo primario), recalibrados",
            "nivel": "bandas 80% (p10-p90) y 95% (p2,5-p97,5) centrales",
            "sd_agrupada_pp": round(pooled_sd, 3),
        },
        "calibracion_intervalos": {
            "aplicada": factores is not None,
            "metodo": "banda(L) = punto ± k_L·z·σ; k_L de calibracion_intervalos.json",
            "factores": {f"{k:.2f}": round(v, 4) for k, v in (factores or {}).items()},
            "niveles_aplicados": ["0.80", "0.95"],
            "fuente": "data/processed/modelo/calibracion_intervalos.json",
            "nota": (
                "El punto no cambia: k solo escala la semianchura. Los escaños "
                "D'Hondt (sigma intacta en sd_error_backtest) quedan idénticos."
            ),
        },
        "timesfm": {"checkpoint": CHECKPOINT, "backend": "torch (CPU)",
                    "n_series": len(parties), "per_core_batch_size": len(parties)},
        "normalizacion": {
            "procedimiento": "renormalizado al universo modelado (suma = 100)",
            "cobertura_universo_23J_pct": round(universo, 3),
            "suma_puntos_baseline_cruda": round(sum(base_point.values()), 3),
            "suma_puntos_timesfm_cruda": round(sum(ts_point.values()), 3),
        },
        "advertencia": (
            "Punto = baseline (ultima media ponderada), que empata en el backtest "
            "con TimesFM; TimesFM NO mejora al baseline (ver docs/notes/modelo.md). "
            "Intervalos empiricos recalibrados a su cobertura nominal con un factor "
            "agrupado (ver docs/notes/calibracion-intervalos.md); siguen siendo "
            "bandas simetricas, no una probabilidad de resultado."
        ),
    }

    with open(C.DATA / "modelo" / "forecast_state.json", "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "partidos": out_partidos}, fh, ensure_ascii=False, indent=1)
    with open(C.DATA / "modelo" / "forecast_state.timesfm.json", "w", encoding="utf-8") as fh:
        json.dump({"meta": meta,
                   "punto": {p: round(n_ts[p], 3) for p in parties},
                   "cuantiles": {p: {k: round(v, 3) for k, v in ts_q[p].items()}
                                 for p in parties}},
                  fh, ensure_ascii=False, indent=1)

    print(f"OK forecast_state.json — horizonte {horizon} mes(es), "
          f"historia {len(grid)} pts, metodo={metodo}")
    for p in parties:
        d = out_partidos[p]
        print(f"  {p:8s} punto={d['punto']:6.2f}  "
              f"IC80=[{d['cuantiles']['0.1']:6.2f}, {d['cuantiles']['0.9']:6.2f}]  "
              f"| ts={d['punto_timesfm']:6.2f} base={d['punto_baseline']:6.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
