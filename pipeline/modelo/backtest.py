#!/usr/bin/env python3
"""Fase 4 (paso 3) — Backtest del modelo estatal y comparativa con baseline.

Para 20D-2015, 26J-2016, 28A-2019, 10N-2019 y 23J-2023:
  1. se reconstruye la serie mensual ponderada usando **solo** observaciones
     anteriores a la votación (0 fuga de información);
  2. se predice el mes de la elección con TimesFM (zero-shot);
  3. se compara con un **baseline ingenuo**: la última media ponderada (valor
     final de la serie) con intervalos derivados de la distribución de errores
     históricos del propio baseline.

La métrica es el MAE por partido sobre **% de voto válido**, normalizando
predicción y realidad al mismo universo de partidos modelados. Nada de
maquillaje: si TimesFM no mejora al baseline, se declara.

Salida: `data/processed/modelo/backtest.json`.

Uso:
    /root/.venvs/29n/bin/python pipeline/modelo/backtest.py
"""

from __future__ import annotations

import json
from datetime import date

import numpy as np

import common as C
from forecast import forecast_batch, load_model, QUANTILE_COLUMNS, QUANTILE_LEVELS


def universe_normalize(d, parties):
    """Renormaliza a 100 dentro del universo de partidos modelados."""
    sub = {p: float(d.get(p, 0.0)) for p in parties}
    tot = sum(sub.values())
    if tot <= 0:
        return sub
    return {p: 100.0 * v / tot for p, v in sub.items()}


def build_inputs_for_cutoff(obs, parties, cutoff):
    grid = [g for g in C.month_grid()
            if (g.year, g.month) < (cutoff.year, cutoff.month)]
    series = {}
    for p in parties:
        _, vals = C.build_party_series(p, obs, cutoff=cutoff)
        series[p] = vals[: len(grid)]
    return grid, series


def main() -> int:
    obs = C.Observations()
    inter = C.Interior()
    parties = C.MODELED_PARTIES

    model = load_model(per_core_batch_size=len(parties), max_context=594, horizon=1)

    results = {}
    pooled = {"ts": [], "base": [], "ens": []}
    per_party = {p: {"ts": [], "base": [], "ens": [], "n": 0} for p in parties}
    cobertura = {}

    for eid in C.BACKTEST_ELECTIONS:
        cutoff = date(*[int(x) for x in eid.split("-")])
        grid, series = build_inputs_for_cutoff(obs, parties, cutoff)
        hist_len = len(grid)

        point, quantiles = forecast_batch(model, [series[p] for p in parties], 1)
        ts = {p: float(point[i, 0]) for i, p in enumerate(parties)}
        ts_interval = {
            p: {str(lv): float(quantiles[i, 0, QUANTILE_COLUMNS[k]])
                for k, lv in enumerate(QUANTILE_LEVELS)}
            for i, p in enumerate(parties)}
        # baseline = último valor de la serie (media ponderada actual)
        base = {p: float(series[p][-1]) for p in parties}

        # Realidad sobre la misma base (% sobre voto válido nacional), SIN
        # renormalizar: así una parte no modelada (p. ej. Ciudadanos en
        # 2015-2019) no infla artificialmente los errores de los partidos
        # modelados. La cobertura del universo se documenta aparte.
        real_all = inter.national_canonical(eid)
        real = {p: float(real_all.get(p, 0.0)) for p in parties}
        cobertura[eid] = round(sum(real.values()), 2)
        # ensemble = media de TimesFM y baseline
        ens = {p: 0.5 * (ts[p] + base[p]) for p in parties}

        entry = {"partidos": {}, "historia_meses": hist_len,
                 "cobertura_universo_pct": cobertura[eid]}
        for p in parties:
            e_ts = ts[p] - real[p]
            e_bs = base[p] - real[p]
            e_en = ens[p] - real[p]
            entry["partidos"][p] = {
                "pred_timesfm": round(ts[p], 3),
                "pred_baseline": round(base[p], 3),
                "pred_ensemble": round(ens[p], 3),
                "real": round(real[p], 3),
                "err_timesfm": round(e_ts, 3),
                "err_baseline": round(e_bs, 3),
                "err_ensemble": round(e_en, 3),
                "ts_interval_80": {k: round(v, 3) for k, v in ts_interval[p].items()},
            }
            # MAE por partido solo donde el partido es relevante realmente
            if real[p] >= 0.1:
                per_party[p]["ts"].append(abs(e_ts))
                per_party[p]["base"].append(abs(e_bs))
                per_party[p]["ens"].append(abs(e_en))
                per_party[p]["n"] += 1
                pooled["ts"].append(abs(e_ts))
                pooled["base"].append(abs(e_bs))
                pooled["ens"].append(abs(e_en))
        results[eid] = entry

    mae_ts = float(np.mean(pooled["ts"]))
    mae_base = float(np.mean(pooled["base"]))
    mae_ens = float(np.mean(pooled["ens"]))
    best = min([("timesfm", mae_ts), ("baseline", mae_base), ("ensemble", mae_ens)],
               key=lambda x: x[1])
    verdict = (f"Mejor metodo en backtest: {best[0]} "
               f"(MAE {best[1]:.3f} pp). "
               + ("TimesFM NO mejora al baseline" if mae_ts >= mae_base
                  else "TimesFM mejora al baseline"))

    mae_partido = {}
    for p in parties:
        d = per_party[p]
        if d["n"] == 0:
            continue
        mae_partido[p] = {
            "mae_timesfm": round(float(np.mean(d["ts"])), 3),
            "mae_baseline": round(float(np.mean(d["base"])), 3),
            "mae_ensemble": round(float(np.mean(d["ens"])), 3),
            "n_elecciones": d["n"],
        }

    # Distribución de errores del baseline (para intervalos ingênuos)
    base_err = pooled["base"]
    out = {
        "generado": date.today().isoformat(),
        "elecciones": C.BACKTEST_ELECTIONS,
        "metrica": "MAE sobre % de voto válido (base completa, sin renormalizar)",
        "cobertura_universo_pct_por_eleccion": cobertura,
        "n_observaciones_mae": len(pooled["ts"]),
        "mae_global": {
            "timesfm": round(mae_ts, 3),
            "baseline": round(mae_base, 3),
            "ensemble": round(mae_ens, 3),
            "verdict": verdict,
            "mejora_timesfm_vs_baseline_pp": round(mae_base - mae_ts, 3),
            "mejora_ensemble_vs_baseline_pp": round(mae_base - mae_ens, 3),
            "metodo_primario": best[0],
        },
        "mae_por_partido": mae_partido,
        "baseline_error_distribution": {
            "media": round(float(np.mean(base_err)), 3),
            "sd": round(float(np.std(base_err)), 3),
            "p90_abs": round(float(np.percentile([abs(e) for e in base_err], 90)), 3),
            "n": len(base_err),
        },
        "por_eleccion": results,
        "notas": [
            "TimesFM es zero-shot: no se entrena por elección.",
            "El baseline es 'última media ponderada' (valor final de la serie).",
            "Predicción y realidad sobre la misma base: % de voto válido nacional.",
            "La cobertura del universo modelado cae en 2015-2019 (Ciudadanos y "
            "otros fuera del modelo); MAE por partido no se ve afectado por ello.",
            "MAE por partido contado solo en elecciones donde el partido supera 0,1 %.",
        ],
    }

    path = C.DATA / "modelo" / "backtest.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print(f"OK backtest.json — n={len(pooled['ts'])} observaciones partido×elección")
    print(f"  MAE TimesFM   = {mae_ts:.3f} pp")
    print(f"  MAE baseline  = {mae_base:.3f} pp")
    print(f"  MAE ensemble  = {mae_ens:.3f} pp")
    print(f"  VERDICT: {verdict}")
    print("  MAE por partido (TimesFM vs baseline vs ensemble):")
    for p, d in sorted(mae_partido.items(), key=lambda x: -x[1]["mae_baseline"]):
        print(f"    {p:8s} ts={d['mae_timesfm']:5.2f}  base={d['mae_baseline']:5.2f}  "
              f"ens={d['mae_ensemble']:5.2f}  n={d['n_elecciones']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
