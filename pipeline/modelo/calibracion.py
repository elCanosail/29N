#!/usr/bin/env python3
"""Recalibración multiplicativa de los intervalos del modelo vivo (29N).

Contexto
--------
El backtest del ensemble (`docs/notes/ensemble-backtest.md`, §5) midió que las
bandas **nominales** del modelo vivo (que en la práctica es el *baseline*:
última media ponderada + intervalos `punto ± z·σ`, con `σ` = SD de sus errores
de backtest) **subcubren** fuera de muestra:

    nominal 80 % → cobertura real 74,6 %
    nominal 95 % → cobertura real 81,4 %

La causa es doble: (a) la SD estimada en muestra es optimista y (b) la
distribución de errores tiene colas más pesadas que la normal, así que el
multiplicador `z` puro queda corto.

Chema aprobó **recalibrar las bandas publicadas sin cambiar el punto ni el
método**. Este módulo estima, para cada banda nominal, un único factor de
escala multiplicativo `k` que ensancha (o estrecha) la semianchura de la banda
hasta que su cobertura fuera de muestra coincida con la nominal:

    banda(L) = punto ± k_L · z_{(1+L)/2} · σ
    punto   = SIN cambios (k solo toca la semianchura; en p50, z=0)

Estimador (honesto, con fuga cero)
----------------------------------
Para cada observación `i` (partido × elección con voto real ≥ 0,1 %):

1. Se estandariza su error absoluto por la SD del propio baseline estimada
   **sin la elección evaluada** (`SD leave-one-election-out`, LOO), que es la
   definición con la que el informe midió la cobertura honesta 74,6 / 81,4 %:
   `r_i = |err_i| / σ_LOO(i)`.
2. El factor de la banda L es `k_L = quantile_L({r_i}) / z_{(1+L)/2}`.

Con la semianchura calibrada, la cobertura empírica es, por construcción, ≈ L.
Como el factor se estima con los MISMOS datos con los que se mide, la
cobertura "después" es **optimista por construcción**; la honestidad se
cuantifica aparte con validación **leave-one-election-out del propio
estimador** (§`validacion_loo`): se recalcula `k` en 4 elecciones y se mide la
cobertura en la elección excluida. Con n = 59 observaciones pero solo 5
elecciones independientes, ese LOO es la referencia honesta y se reporta tal
cual, sin maquillar.

Advertencias
------------
- **5 elecciones**: el estimador descansa en 5 citas electorales. El boostrap
  de las 59 observaciones NO es independiente (errores correlacionados dentro
  de una elección). La incertidumbre real del factor es la del LOO, no la de
  un IC binomial sobre 59.
- **Factor agrupado**: un solo `k` para todos los partidos (una SD por partido
  con n≤5 no permite un factor por partido). Los partidos con colas pesadas
  (SUMAR) empujan el factor al alza para todos.
- **Solo ensancha, no re-forma**: sigue siendo una banda simétrica tipo normal.
  Corrige la anchura, no la asimetría.
- **σ del sampler D'Hondt intacta**: la recalibración NO toca
  `sd_error_backtest`, que `provincial.py` usa para simular escaños. Por eso el
  punto y los escaños quedan idénticos (ver `docs/notes/calibracion-intervalos.md`).

Salida: `data/processed/modelo/calibracion_intervalos.json`.

Uso:
    /root/.venvs/29n/bin/python pipeline/modelo/calibracion.py
"""

from __future__ import annotations

import json
import statistics
from datetime import date

import numpy as np

import common as C
from forecast import z_value

# Bandas nominales del encargo: 0,80 → p10–p90 (la publicada); 0,95 → p2,5–p97,5.
# 0,60 se estima SOLO como diagnóstico (la web publica p20/p80, pero recalibrar
# esa banda interior no está en el alcance aprobado): se marca `aplicado: false`
# y `factor_para` la ignora. Su cobertura honesta actual (≈66 %) sobre-cubre, así
# que dejarla intacta es conservador.
NIVELES = (0.60, 0.80, 0.95)
APLICADOS = (0.80, 0.95)

FACTORES_PATH = C.DATA / "modelo" / "calibracion_intervalos.json"

_ERR_KEY = {"timesfm": "err_timesfm", "baseline": "err_baseline",
            "ensemble": "err_ensemble"}


# --------------------------------------------------------------------------- #
# Datos del backtest
# --------------------------------------------------------------------------- #
def errores_primario(backtest):
    """Observaciones (partido × elección, real ≥ 0,1 %) del método primario.

    Cada fila lleva el error absoluto y, además, la SD del baseline estimada
    (a) sin la elección evaluada (`sd_loo`, honesta) y (b) sobre todo el
    backtest (`sd_pub`, la que publica el modelo vivo).
    """
    metodo = backtest["mae_global"]["metodo_primario"]
    key = _ERR_KEY[metodo]
    rows = []
    for eid, e in backtest["por_eleccion"].items():
        for p, x in e["partidos"].items():
            if float(x["real"]) < 0.1:
                continue
            rows.append({"eid": eid, "party": p,
                         "err": float(x[key]),
                         "pred": float(x["pred_baseline"]),
                         "real": float(x["real"])})
    # SD publicada (definición del modelo vivo, `forecast.party_error_sd`)
    pooled = [r["err"] for r in rows]
    pooled_sd = statistics.pstdev(pooled) if len(pooled) > 1 else 2.5
    for r in rows:
        v = [q["err"] for q in rows if q["party"] == r["party"]]
        r["sd_pub"] = max(0.10, statistics.stdev(v)) if len(v) >= 2 else pooled_sd
        # SD LOO: excluye la elección evaluada (idéntica a `_loo_sd` del
        # runner del ensemble, que produjo las coberturas 74,6 / 81,4 %).
        v = [q["err"] for q in rows if q["party"] == r["party"] and q["eid"] != r["eid"]]
        if len(v) >= 2:
            r["sd_loo"] = max(0.10, statistics.stdev(v))
        else:
            allv = [q["err"] for q in rows if q["eid"] != r["eid"]]
            r["sd_loo"] = statistics.pstdev(allv) if len(allv) > 1 else 2.5
        r["r_loo"] = abs(r["err"]) / r["sd_loo"]
        r["r_pub"] = abs(r["err"]) / r["sd_pub"]
    return metodo, rows


# --------------------------------------------------------------------------- #
# Estimación del factor
# --------------------------------------------------------------------------- #
def _factor(niveles_res, nivel):
    """k = quantile_L(r) / z_{(1+L)/2} (interpolación lineal, numpy)."""
    z = z_value((1.0 + nivel) / 2.0)
    return float(np.quantile(niveles_res, nivel) / z), z


def estimar(rows):
    """Factores por nivel y cobertura antes/después (honesta y publicada)."""
    r_loo = np.asarray([r["r_loo"] for r in rows], dtype=float)
    r_pub = np.asarray([r["r_pub"] for r in rows], dtype=float)
    abs_err = np.asarray([abs(r["err"]) for r in rows], dtype=float)
    sd_loo = np.asarray([r["sd_loo"] for r in rows], dtype=float)
    sd_pub = np.asarray([r["sd_pub"] for r in rows], dtype=float)

    out = {}
    for nivel in NIVELES:
        k, z = _factor(r_loo, nivel)
        half_loo = k * z * sd_loo
        half_pub = k * z * sd_pub
        out[f"{nivel:.2f}"] = {
            "nivel_nominal_pct": round(100.0 * nivel, 1),
            "aplicado": nivel in APLICADOS,
            "z": round(z, 4),
            "k": round(k, 4),
            "cobertura_antes_honesta_pct": round(100.0 * float((r_loo <= z).mean()), 1),
            "cobertura_despues_honesta_pct": round(100.0 * float((r_loo <= k * z).mean()), 1),
            "cobertura_antes_publicada_pct": round(100.0 * float((abs_err <= z * sd_pub).mean()), 1),
            "cobertura_despues_publicada_pct": round(
                100.0 * float((abs_err <= k * z * sd_pub).mean()), 1),
            "semianchura_media_antes_pp": round(float(np.mean(z * sd_pub)), 3),
            "semianchura_media_despues_pp": round(float(np.mean(k * z * sd_pub)), 3),
        }
    return out


def validacion_loo(rows, elecciones):
    """Recalcula k en 4 elecciones y mide la cobertura en la 5.ª (honesto)."""
    out = {}
    for nivel in NIVELES:
        detalle = {}
        aciertos = total = 0
        for eid_eval in elecciones:
            train = [r["r_loo"] for r in rows if r["eid"] != eid_eval]
            test = [r for r in rows if r["eid"] == eid_eval]
            k, z = _factor(train, nivel)
            a = sum(1 for r in test if r["r_loo"] <= k * z)
            detalle[eid_eval] = {
                "k_estimado": round(k, 4),
                "n": len(test),
                "aciertos": a,
                "cobertura_pct": round(100.0 * a / len(test), 1) if test else None,
            }
            aciertos += a
            total += len(test)
        out[f"{nivel:.2f}"] = {
            "nivel_nominal_pct": round(100.0 * nivel, 1),
            "cobertura_loo_pct": round(100.0 * aciertos / total, 1) if total else None,
            "k_por_fold": [round(v["k_estimado"], 4) for v in detalle.values()],
            "k_rango": [round(min(v["k_estimado"] for v in detalle.values()), 4),
                        round(max(v["k_estimado"] for v in detalle.values()), 4)],
            "detalle": detalle,
        }
    return out


# --------------------------------------------------------------------------- #
# API para la generación (forecast.py)
# --------------------------------------------------------------------------- #
def cargar_factores(path=FACTORES_PATH):
    """{nivel_float: k} de los niveles APLICADOS; None si no hay fichero.

    Los niveles marcados `aplicado: false` (diagnóstico 60 %) se excluyen para
    que la generación no los use.
    """
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    return {float(k): float(v["k"]) for k, v in d["factores"].items()
            if v.get("aplicado")}


def nivel_central(cuantil):
    """Nivel central de la banda a la que pertenece un cuantil dado.

    0,10/0,90 → 0,80 ; 0,20/0,80 → 0,60 ; 0,025/0,975 → 0,95 ; 0,50 → 0.
    """
    return 2.0 * max(cuantil, 1.0 - cuantil) - 1.0


def factor_para(factores, nivel):
    """k del nivel; si no está tabulado, 1.0 (p. ej. 0 en p50)."""
    if factores is None:
        return 1.0
    return factores.get(round(nivel, 4), 1.0)


def calibrar_cuantil(point, sd, cuantil, factores):
    """Cuantil calibrado: punto ± k·z·σ (solo cambia la semianchura)."""
    z = z_value(cuantil)
    k = factor_para(factores, nivel_central(cuantil))
    return max(0.0, point + k * z * sd)


# --------------------------------------------------------------------------- #
def main() -> int:
    bt_path = C.DATA / "modelo" / "backtest.json"
    if not bt_path.exists():
        raise SystemExit("Falta backtest.json — ejecuta antes pipeline/modelo/backtest.py")
    backtest = json.loads(bt_path.read_text(encoding="utf-8"))
    metodo, rows = errores_primario(backtest)
    elecciones = list(backtest["por_eleccion"].keys())

    factores = estimar(rows)
    loo = validacion_loo(rows, elecciones)

    avisos = [
        "Solo se aplican los niveles aprobados 0,80 (p10–p90) y 0,95 (p2,5–p97,5). "
        "El nivel 0,60 se estima como diagnóstico y NO se aplica.",
        "El factor es agrupado (un k para los 13 partidos): una SD por partido "
        "con n≤5 no permite estimar un factor por partido. Los partidos de "
        "cola pesada (SUMAR) empujan k al alza para todos.",
        "El estimador se apoya en 5 elecciones (59 observaciones partido×elección, "
        "correlacionadas dentro de cada cita). El IC del factor es el del LOO, "
        "no el de un IC binomial sobre 59 puntos independientes.",
        "La cobertura 'después' honesta ≈ nominal es optimista por construcción "
        "(mismo conjunto para estimar y medir). La columna LOO es la honesta.",
        "La recalibración solo ensancha bandas simétricas: corrige anchura, no "
        "asimetría ni sesgo del punto.",
        "No se modifica σ (`sd_error_backtest`) ni el punto: los escaños D'Hondt "
        "quedan idénticos (provincial.py consume solo punto + σ).",
    ]

    out = {
        "generado": date.today().isoformat(),
        "metodo_primario": metodo,
        "protocolo": "backtest.py (5 elecciones; errores del baseline, real ≥ 0,1 %)",
        "estimador": "k_L = quantile_L(|err|/σ_LOO) / z_{(1+L)/2}; agrupado; σ LOO",
        "n_observaciones": len(rows),
        "n_elecciones": len(elecciones),
        "factores": factores,
        "validacion_loo_del_estimador": loo,
        "advertencias": avisos,
    }
    FACTORES_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK calibracion_intervalos.json — n={len(rows)} obs / "
          f"{len(elecciones)} elecciones, método={metodo}")
    print("  Banda   k       cobertura antes→después (honesta LOO)")
    for nivel in NIVELES:
        d = factores[f"{nivel:.2f}"]
        print(f"   {int(100*nivel):>3d}%  {d['k']:6.3f}   "
              f"{d['cobertura_antes_honesta_pct']:5.1f}% → "
              f"{d['cobertura_despues_honesta_pct']:5.1f}%   "
              f"| LOO del estimador: {loo[f'{nivel:.2f}']['cobertura_loo_pct']}% "
              f"(k∈[{loo[f'{nivel:.2f}']['k_rango'][0]}, {loo[f'{nivel:.2f}']['k_rango'][1]}])")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
