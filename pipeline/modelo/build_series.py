#!/usr/bin/env python3
"""Fase 4 (paso 1) — Serie mensual ponderada de intención de voto por partido.

Combina CIS (voto directo reescalado a válido) + encuestadores privados, con
pesos de recencia (media-vida 45 d), tamaño muestral (√n) y calidad del
encuestador (1/(1+MAE)), y correcciones empirical-bayes de efectos de casa.

Salida: `data/processed/modelo/series.json` (metadata + series mensuales) y
`data/processed/modelo/series.csv` (forma larga, para inspección).

Uso:
    /root/.venvs/29n/bin/python pipeline/modelo/build_series.py
"""

from __future__ import annotations

import json
from datetime import date

import common as C


def main() -> int:
    obs = C.Observations()
    inter = C.Interior()

    parties = C.MODELED_PARTIES
    series = {}
    for p in parties:
        grid, vals = C.build_party_series(p, obs)
        series[p] = {
            "months": [d.isoformat() for d in grid],
            "values": [round(v, 4) for v in vals],
            "n_obs": len(obs.by_party.get(p, [])),
            "last_obs": max((o["date"].isoformat() for o in obs.by_party.get(p, [])),
                            default=None),
        }

    # Diagnóstico: posición de la serie en la última cita (23J-2023)
    diag = {}
    real = inter.national_canonical("2023-07-23")
    for p in parties:
        _, v = C.build_party_series(p, obs, cutoff=date(2023, 7, 23))
        diag[p] = {"serie_2023_07": round(v[-1], 2),
                   "real_2023_07": round(real.get(p, 0.0), 2)}

    meta = {
        "generado": date.today().isoformat(),
        "base": "% sobre voto valido",
        "parametros": {
            "media_vida_dias": C.HALFLIFE_DAYS,
            "n_referencia_muestra": C.SIZE_REF_N,
            "ventana_max_dias": C.MAX_LOOKBACK_DAYS,
            "partidos_modelados": parties,
            "familias": C.FAMILY,
            "estudios_cis_excluidos_no_validados": getattr(obs, "_cis_skipped", []),
            "estudios_privados_excluidos_ambito": getattr(obs, "_priv_dropped", []),
            "estudios_privados_excluidos_incompletos": getattr(obs, "_priv_incompleto", []),
            "umbral_completitud_big4": C.BIG4_MIN_SUM,
        },
        "pesos": {
            "calidad_cis_mae": round(obs.mae_cis, 4),
            "calidad_privados_mae": obs.mae_priv,
            "calidad_privados_mae_default": round(obs.mae_priv_default, 4),
        },
        "correcciones_eb_aplicadas": {
            "CIS[micro_valid]": obs.correcciones.get("CIS", {}).get("micro_valid", {}),
            "privados[privado]": {
                casa: obs.correcciones[casa]["privado"]
                for casa in obs.correcciones if casa != "CIS"
            },
        },
        "diagnostico_2023": diag,
        "n_observaciones_total": len(obs.obs),
    }

    out = C.DATA / "modelo" / "series.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "series": series}, fh, ensure_ascii=False)

    # CSV largo
    csv_path = C.DATA / "modelo" / "series.csv"
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write("mes,partido,valor\n")
        for p in parties:
            for m, v in zip(series[p]["months"], series[p]["values"]):
                fh.write(f"{m},{p},{v}\n")

    print(f"OK series.json ({out}) — {len(parties)} partidos, "
          f"{len(series[parties[0]]['months'])} meses cada uno "
          f"({series[parties[0]]['months'][0]}..{series[parties[0]]['months'][-1]})")
    print("Diagnóstico 23J (serie vs real):")
    for p in parties:
        d = diag[p]
        if d["real_2023_07"] > 0:
            print(f"  {p:16s} serie={d['serie_2023_07']:6.2f}  real={d['real_2023_07']:6.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
