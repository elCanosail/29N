#!/usr/bin/env python3
"""Backtest comparativo 29N: baseline (modelo vivo) vs bayesiano vs ensemble.

Reutiliza el **protocolo exacto** de ``pipeline/modelo/backtest.py`` (que NO se
modifica): mismas 5 elecciones (``C.BACKTEST_ELECTIONS``), mismos días de corte
(el día de la votación), misma métrica (MAE sobre % de voto válido, base
completa sin renormalizar, contabilizada solo donde el partido supera 0,1 %).
Las funciones ``build_inputs_for_cutoff`` y ``universe_normalize`` se copian
bajo ``pipeline/ensemble/`` por aislamiento; el original permanece intacto.

Alineación de información
-------------------------
El baseline construye una serie **mensual** truncada en el fin del mes anterior
al de la votación: las observaciones del mes de la elección quedan fuera. Para
comparar en igualdad de condiciones, el miembro bayesiano usa el **mismo corte
de información** (``data_cutoff`` = primer día del mes de la elección) y solo
propaga la varianza hasta el día electoral (el punto de un random walk sin
deriva no cambia al propagar).

Métodos
-------
- **baseline**: última media ponderada de la serie (modelo vivo, `forecast.py`).
  En el backtest solo da punto; sus intervalos se derivan de la SD empírica de
  sus errores por partido (definición del modelo vivo, ``z·sd``).
- **bayesiano**: filtro de Kalman (``kalman.BayesDynamic``).
- **ensemble**: media 50/50 de los puntos; intervalos = cuantiles de la mezcla.

Semilla fija (``SEED``): filtro determinista; el bootstrap emparejado usa
``numpy.random.default_rng(SEED)``.

Salida: ``data/processed/ensemble/backtest_ensemble.json``.

Uso:
    /root/.venvs/29n/bin/python pipeline/ensemble/backtest_ensemble.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                    # pipeline/ensemble
sys.path.insert(0, str(HERE.parent / "modelo"))  # pipeline/modelo

import common as C                            # noqa: E402
from forecast import z_value                  # noqa: E402
import kalman                                 # noqa: E402
import ensemble                               # noqa: E402

SEED = 20261129

# Hiperparámetros del miembro bayesiano (documentados en el informe)
SIGMA_DAILY = kalman.DEFAULT_SIGMA_DAILY   # 0.15 pp/√día
DEFF = kalman.DEFAULT_DEFF                 # 1.7
TAU_FLOOR = kalman.DEFAULT_TAU_FLOOR       # 0.30 pp
SIGMA_H = kalman.DEFAULT_SIGMA_H           # 1.00 pp

LEVELS = [0.025, 0.10, 0.90, 0.975]        # 95% = (0.025,0.975); 80% = (0.10,0.90)
B_BOOT = 10000


# --------------------------------------------------------------------------- #
# Protocolo copiado de pipeline/modelo/backtest.py (aislado, sin modificar)
# --------------------------------------------------------------------------- #
def universe_normalize(d, parties):
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


def _sd_live_model(errors_by_party, parties):
    """SD de los errores por partido tal como la define el modelo vivo
    (``forecast.party_error_sd``): desviación muestral del partido si n≥2,
    SD agrupada si n<2, suelo 0,10 pp."""
    pooled = [e for v in errors_by_party.values() for e in v]
    pooled_sd = statistics.pstdev(pooled) if len(pooled) > 1 else 2.5
    sd = {}
    for p in parties:
        v = errors_by_party.get(p, [])
        sd[p] = max(0.10, statistics.stdev(v)) if len(v) >= 2 else pooled_sd
    return sd, pooled_sd


def paired_bootstrap(errs_base, errs_bayes, errs_ens, B=B_BOOT, seed=SEED):
    """Bootstrap emparejado de la diferencia de MAE (baseline − método).

    Positivo ⇒ el método batiría al baseline. Reproducible (semilla fija).
    """
    ab = np.abs(np.asarray(errs_base, dtype=float))
    ay = np.abs(np.asarray(errs_bayes, dtype=float))
    ae = np.abs(np.asarray(errs_ens, dtype=float))
    n = len(ab)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(B, n))
    d_ens = ab[idx].mean(axis=1) - ae[idx].mean(axis=1)
    d_bay = ab[idx].mean(axis=1) - ay[idx].mean(axis=1)

    def summ(d):
        return {
            "media_pp": round(float(d.mean()), 4),
            "sd_pp": round(float(d.std(ddof=1)), 4),
            "p2_5_pp": round(float(np.percentile(d, 2.5)), 4),
            "p97_5_pp": round(float(np.percentile(d, 97.5)), 4),
            "prop_mejora": round(float((d > 0).mean()), 3),
        }

    return {
        "n": n, "B": B, "seed": seed,
        "baseline_menos_ensemble": summ(d_ens),
        "baseline_menos_bayes": summ(d_bay),
    }


# --------------------------------------------------------------------------- #
def run(sigma_daily=SIGMA_DAILY, deff=DEFF, tau_floor=TAU_FLOOR, sigma_h=SIGMA_H):
    obs = C.Observations()
    inter = C.Interior()
    parties = C.MODELED_PARTIES
    kalman_obs = kalman.observations_from_common(obs, parties)
    bd = kalman.BayesDynamic(parties, sigma_daily=sigma_daily, deff=deff,
                             tau_floor=tau_floor, sigma_h=sigma_h)

    # --- Paso 1: puntos + errores -------------------------------------------
    per_election = {}
    base_err = {p: [] for p in parties}
    bayes_err = {p: [] for p in parties}
    pooled_base, pooled_bayes, pooled_ens = [], [], []
    cobertura = {}

    for eid in C.BACKTEST_ELECTIONS:
        cutoff = date(*[int(x) for x in eid.split("-")])
        grid, series = build_inputs_for_cutoff(obs, parties, cutoff)
        base = {p: float(series[p][-1]) for p in parties}
        # Corte de información alineado con el baseline + propagación a la
        # fecha electoral (la varianza crece; el punto no).
        data_cutoff = date(cutoff.year, cutoff.month, 1)
        kb = bd.predict(kalman_obs, data_cutoff, propagate_to=cutoff)
        bys, bysd = kb["mean"], kb["sd"]
        real_all = inter.national_canonical(eid)
        real = {p: float(real_all.get(p, 0.0)) for p in parties}
        cobertura[eid] = round(sum(real.values()), 2)

        entry = {"historia_meses": len(grid),
                 "n_obs_bayes": kb["n_obs"],
                 "ultima_obs": kb["last_obs"].isoformat() if kb["last_obs"] else None,
                 "dias_a_eleccion": kb["days_to_election"],
                 "house_effects": {k: round(v, 3) for k, v in kb["house_effects"].items()},
                 "cobertura_universo_pct": cobertura[eid],
                 "partidos": {}}
        for p in parties:
            ens = ensemble.ensemble_point(bys[p], base[p])
            entry["partidos"][p] = {
                "pred_baseline": round(base[p], 3),
                "pred_bayes": round(bys[p], 3),
                "pred_ensemble": round(ens, 3),
                "sd_bayes_modelo": round(bysd[p], 3),
                "real": round(real[p], 3),
                "err_baseline": round(base[p] - real[p], 3),
                "err_bayes": round(bys[p] - real[p], 3),
                "err_ensemble": round(ens - real[p], 3),
            }
            if real[p] >= 0.1:
                base_err[p].append(base[p] - real[p])
                bayes_err[p].append(bys[p] - real[p])
                pooled_base.append(base[p] - real[p])
                pooled_bayes.append(bys[p] - real[p])
                pooled_ens.append(ens - real[p])
        per_election[eid] = entry

    # --- Paso 2: intervalos y cobertura ------------------------------------
    sd_base, pooled_sd_base = _sd_live_model(base_err, parties)
    sd_bayes, pooled_sd_bayes = _sd_live_model(bayes_err, parties)

    def _loo_sd(p, exclude_eid):
        """SD del baseline para el partido p excluyendo la elección evaluada."""
        v = []
        for eid in C.BACKTEST_ELECTIONS:
            if eid == exclude_eid:
                continue
            x = per_election[eid]["partidos"][p]
            if x["real"] >= 0.1:
                v.append(x["err_baseline"])
        if len(v) >= 2:
            return max(0.10, statistics.stdev(v))
        allv = []
        for eid in C.BACKTEST_ELECTIONS:
            if eid == exclude_eid:
                continue
            for q in parties:
                y = per_election[eid]["partidos"][q]
                if y["real"] >= 0.1:
                    allv.append(y["err_baseline"])
        return statistics.pstdev(allv) if len(allv) > 1 else 2.5

    methods = ("baseline", "bayes", "ensemble", "ensemble_loo")
    cov = {m: {"95": [0, 0], "80": [0, 0]} for m in methods}
    cov_base_loo = {"95": [0, 0], "80": [0, 0]}
    coverage_detail = {}

    for eid in C.BACKTEST_ELECTIONS:
        entry = per_election[eid]
        cov_e = {m: {"95": [0, 0], "80": [0, 0]} for m in methods}
        for p in parties:
            x = entry["partidos"][p]
            if x["real"] < 0.1:
                continue
            base_p, by_p = x["pred_baseline"], x["pred_bayes"]
            bq = {lv: base_p + z_value(lv) * sd_base[p] for lv in LEVELS}
            yq = {lv: by_p + z_value(lv) * x["sd_bayes_modelo"] for lv in LEVELS}
            eq = ensemble.ensemble_quantiles(by_p, x["sd_bayes_modelo"],
                                             base_p, sd_base[p], LEVELS)
            sl = _loo_sd(p, eid)
            eq_loo = ensemble.ensemble_quantiles(by_p, x["sd_bayes_modelo"],
                                                 base_p, sl, LEVELS)
            lq = {lv: base_p + z_value(lv) * sl for lv in LEVELS}
            x["base_q"] = {str(k): round(v, 3) for k, v in bq.items()}
            x["bayes_q"] = {str(k): round(v, 3) for k, v in yq.items()}
            x["ens_q"] = {str(k): round(v, 3) for k, v in eq.items()}
            x["ens_q_loo_base"] = {str(k): round(v, 3) for k, v in eq_loo.items()}
            real = x["real"]
            for m, q in (("baseline", bq), ("bayes", yq), ("ensemble", eq),
                         ("ensemble_loo", eq_loo)):
                for lvl, (lo, hi) in (("95", (0.025, 0.975)), ("80", (0.10, 0.90))):
                    cov[m][lvl][1] += 1
                    cov_e[m][lvl][1] += 1
                    if q[lo] <= real <= q[hi]:
                        cov[m][lvl][0] += 1
                        cov_e[m][lvl][0] += 1
            for lvl, (lo, hi) in (("95", (0.025, 0.975)), ("80", (0.10, 0.90))):
                cov_base_loo[lvl][1] += 1
                if lq[lo] <= real <= lq[hi]:
                    cov_base_loo[lvl][0] += 1
        coverage_detail[eid] = {
            m: {lvl: round(100.0 * cov_e[m][lvl][0] / cov_e[m][lvl][1], 1)
                if cov_e[m][lvl][1] else None for lvl in ("95", "80")}
            for m in methods}

    # --- Métricas agregadas -------------------------------------------------
    mae = {
        "baseline": float(np.mean(np.abs(pooled_base))),
        "bayes": float(np.mean(np.abs(pooled_bayes))),
        "ensemble": float(np.mean(np.abs(pooled_ens))),
    }
    mae_party = {}
    for p in parties:
        n_b = len(base_err[p])
        if n_b == 0:
            continue
        errs_ens = [ensemble.ensemble_point(
            per_election[eid]["partidos"][p]["pred_bayes"],
            per_election[eid]["partidos"][p]["pred_baseline"]) -
            per_election[eid]["partidos"][p]["real"]
            for eid in C.BACKTEST_ELECTIONS
            if per_election[eid]["partidos"][p]["real"] >= 0.1]
        mae_party[p] = {
            "mae_baseline": round(float(np.mean(np.abs(base_err[p]))), 3),
            "mae_bayes": round(float(np.mean(np.abs(bayes_err[p]))), 3),
            "mae_ensemble": round(float(np.mean(np.abs(errs_ens))), 3),
            "n": n_b,
        }

    cov_pct = {m: {lvl: round(100.0 * cov[m][lvl][0] / cov[m][lvl][1], 1)
                   if cov[m][lvl][1] else None for lvl in ("95", "80")}
               for m in methods}
    cov_loo_pct = {lvl: round(100.0 * cov_base_loo[lvl][0] / cov_base_loo[lvl][1], 1)
                   if cov_base_loo[lvl][1] else None for lvl in ("95", "80")}

    boot = paired_bootstrap(pooled_base, pooled_bayes, pooled_ens)

    return {
        "mae": {k: round(v, 3) for k, v in mae.items()},
        "mae_party": mae_party,
        "cobertura_pct": cov_pct,
        "cobertura_pct_baseline_loo": cov_loo_pct,
        "cobertura_por_eleccion": coverage_detail,
        "bootstrap": boot,
        "n_obs_mae": len(pooled_base),
        "per_election": per_election,
        "cobertura_universo_pct": cobertura,
        "sd_base_party": {p: round(sd_base[p], 3) for p in parties},
        "sd_base_pooled": round(pooled_sd_base, 3),
        "sd_bayes_party": {p: round(sd_bayes[p], 3) for p in parties},
        "sd_bayes_pooled": round(pooled_sd_bayes, 3),
    }


def main() -> int:
    res = run()

    # Sensibilidad a sigma_daily (no cambia el punto apenas; calibra incertidumbre)
    sens = []
    for s in (0.05, 0.10, 0.15, 0.25, 0.40):
        r = run(sigma_daily=s)
        sens.append({
            "sigma_daily": s,
            "mae_baseline": r["mae"]["baseline"],
            "mae_bayes": r["mae"]["bayes"],
            "mae_ensemble": r["mae"]["ensemble"],
            "ensemble_bate": r["mae"]["ensemble"] < r["mae"]["baseline"],
            "cov_bayes_95": r["cobertura_pct"]["bayes"]["95"],
            "cov_bayes_80": r["cobertura_pct"]["bayes"]["80"],
            "cov_ens_95": r["cobertura_pct"]["ensemble"]["95"],
            "cov_ens_80": r["cobertura_pct"]["ensemble"]["80"],
        })

    mae = res["mae"]
    bate = mae["ensemble"] < mae["baseline"]
    boot = res["bootstrap"]["baseline_menos_ensemble"]
    n_boot = res["bootstrap"]["n"]
    verdict = (f"El ensemble {'bate' if bate else 'NO bate'} al modelo vivo en el "
               f"punto: MAE {mae['ensemble']:.3f} vs {mae['baseline']:.3f} pp "
               f"(Δ {mae['baseline'] - mae['ensemble']:+.3f} pp). "
               f"Bootstrap emparejado (n={n_boot}): Δ media {boot['media_pp']:+.3f} pp, "
               f"IC95 [{boot['p2_5_pp']:+.3f}, {boot['p97_5_pp']:+.3f}] — "
               f"{'mejora robusta' if boot['p2_5_pp'] > 0 else 'NO concluyente (el IC incluye 0)'}. "
               f"Bayesiano: {mae['bayes']:.3f} pp.")

    out = {
        "generado": date.today().isoformat(),
        "seed": SEED,
        "elecciones": C.BACKTEST_ELECTIONS,
        "metrica": "MAE sobre % de voto válido (base completa, sin renormalizar)",
        "hiperparametros_bayes": {
            "sigma_daily_pp_sqrt_dia": SIGMA_DAILY,
            "design_inflation_deff": DEFF,
            "tau_floor_pp": TAU_FLOOR,
            "sigma_house_prior_pp": SIGMA_H,
            "p0_varianza_inicial_pp2": kalman.DEFAULT_P0,
        },
        "protocolo": "reutiliza el de pipeline/modelo/backtest.py (sin modificarlo); "
                     "corte de información alineado (primer día del mes electoral)",
        "mae_global": {
            "baseline": mae["baseline"],
            "bayes": mae["bayes"],
            "ensemble": mae["ensemble"],
            "verdict": verdict,
            "mejora_ensemble_vs_baseline_pp": round(mae["baseline"] - mae["ensemble"], 3),
            "ensemble_bate_baseline": bate,
        },
        "bootstrap_diferencia_mae": res["bootstrap"],
        "mae_por_partido": res["mae_party"],
        "cobertura_intervalos_pct": res["cobertura_pct"],
        "cobertura_baseline_loo_pct": res["cobertura_pct_baseline_loo"],
        "cobertura_por_eleccion": res["cobertura_por_eleccion"],
        "cobertura_universo_pct_por_eleccion": res["cobertura_universo_pct"],
        "sd_errores_baseline_por_partido": res["sd_base_party"],
        "sd_errores_baseline_agrupada": res["sd_base_pooled"],
        "sd_errores_bayes_por_partido": res["sd_bayes_party"],
        "sd_errores_bayes_agrupada": res["sd_bayes_pooled"],
        "n_observaciones_mae": res["n_obs_mae"],
        "sensibilidad_sigma_daily": sens,
        "por_eleccion": res["per_election"],
        "notas": [
            "Baseline = 'última media ponderada' (valor final de la serie).",
            "El baseline solo da punto en el backtest; sus intervalos usan la SD "
            "empírica de sus errores por partido (definición del modelo vivo, "
            "forecast.party_error_sd) — aproximación documentada.",
            "ensemble_loo = ensemble con la SD del baseline estimada fuera de la "
            "elección evaluada (cobertura honesta, sin autoconfirmación).",
            "El bayesiano usa su SD predictiva intrínseca (modelo).",
            "El intervalo del ensemble es la mezcla 50/50 (cuantiles por bisección).",
            "MAE contado solo donde el partido supera 0,1 % de voto real.",
            "Predicción y realidad sobre la misma base: % de voto válido nacional.",
        ],
    }

    path = C.DATA / "ensemble" / "backtest_ensemble.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK backtest_ensemble.json — n={res['n_obs_mae']} observaciones partido×elección")
    print(f"  MAE baseline  = {mae['baseline']:.3f} pp")
    print(f"  MAE bayesiano = {mae['bayes']:.3f} pp")
    print(f"  MAE ensemble  = {mae['ensemble']:.3f} pp")
    print(f"  VERDICT: {verdict}")
    print(f"  Bootstrap baseline-ensemble: media {boot['media_pp']:+.3f} pp, "
          f"IC95 [{boot['p2_5_pp']:+.3f}, {boot['p97_5_pp']:+.3f}], "
          f"prop_mejora={boot['prop_mejora']}")
    print("  Cobertura intervalos (95% / 80%):")
    for m in ("baseline", "bayes", "ensemble", "ensemble_loo"):
        print(f"    {m:14s} 95%={res['cobertura_pct'][m]['95']}  "
              f"80%={res['cobertura_pct'][m]['80']}")
    print(f"    baseline(LOO)  95%={res['cobertura_pct_baseline_loo']['95']}  "
          f"80%={res['cobertura_pct_baseline_loo']['80']}")
    print("  Sensibilidad sigma_daily:")
    for s in sens:
        print(f"    sigma={s['sigma_daily']:.2f}  mae_base={s['mae_baseline']:.3f}  "
              f"mae_bayes={s['mae_bayes']:.3f}  mae_ens={s['mae_ensemble']:.3f}  "
              f"bate={s['ensemble_bate']}")
    print("  MAE por partido (baseline / bayes / ensemble):")
    for p, d in sorted(res["mae_party"].items(), key=lambda x: -x[1]["mae_baseline"]):
        print(f"    {p:8s} base={d['mae_baseline']:5.2f}  bayes={d['mae_bayes']:5.2f}  "
              f"ens={d['mae_ensemble']:5.2f}  n={d['n']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
