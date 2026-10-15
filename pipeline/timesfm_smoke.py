#!/usr/bin/env python3
"""Smoke test de TimesFM (Google Research) para el motor de predicción de 29N.

Objetivo
--------
Verificar de punta a punta que TimesFM carga en esta máquina (backend PyTorch,
CPU), que produce un forecast con intervalos (cuantiles) sobre series
sintéticas estacionales, y medir tiempos y memoria reales. Además, reproducir
la forma real de la carga de 29N: **~10 series paralelas (una por partido)**,
mensuales y largas (~50 años = 600 puntos), con horizonte del próximo ciclo
(12 meses).

Qué mide
--------
- Versiones (Python, numpy, torch, timesfm) y dispositivo (CPU/GPU).
- Tiempos: carga del checkpoint, compilación, warm-up y lote de inferencia.
- RAM pico (RSS) del proceso.
- Sanidad del resultado: `point_forecast == quantiles[:, 5]` (el punto es la
  mediana) y monotonía de los 9 cuantiles publicados (columnas 1..9).

Contrato de la API (verificado sobre timesfm 3.0.2)
---------------------------------------------------
`model.forecast(horizon, inputs)` devuelve `(point, quantiles)`:
- `point`: shape `(n_series, horizon)`.
- `quantiles`: shape `(n_series, horizon, 10)`. **La columna 5 es el punto
  (mediana q0.5)**; las columnas **1..9 son los cuantiles 0.1..0.9**; la
  columna 0 es un canal auxiliar que NO es un cuantil. Ver
  `timesfm_2p5_torch.py`: `return full_forecast[..., 5], full_forecast`.

Uso
---
    /root/.venvs/29n/bin/python pipeline/timesfm_smoke.py
    /root/.venvs/29n/bin/python pipeline/timesfm_smoke.py --years 50 --horizon 12 \
        --n-series 10 --per-core-batch-size 32 --seed 7
    /root/.venvs/29n/bin/python pipeline/timesfm_smoke.py --per-core-batch-size 1  # comparar sin batching

Notas
-----
- No descarga datos de 29N: es un smoke aislado y reproducible.
- El checkpoint se descarga de Hugging Face la primera vez y queda en caché
  (~/.cache/huggingface). Ejecuciones siguientes no re-descargan.
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import sys
import time
from importlib import metadata
from pathlib import Path

import numpy as np

CHECKPOINT = "google/timesfm-2.5-200m-pytorch"
QUANTILE_LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
# Columnas del array de cuantiles: 1..9 corresponden a QUANTILE_LEVELS.
QUANTILE_COLUMNS = list(range(1, 10))
POINT_COLUMN = 5


# --------------------------------------------------------------------------- #
# Utilidades de medición
# --------------------------------------------------------------------------- #
def _peak_rss_gib() -> float:
    """RAM pico (RSS high-water mark) del proceso en GiB."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 2)


def _versions() -> dict:
    import torch

    def pkg(name: str) -> str:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            return "unknown"

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "timesfm_pkg": pkg("timesfm"),
        "timesfm_attr": getattr(__import__("timesfm"), "__version__", "unknown"),
        "torch_cuda_available": torch.cuda.is_available(),
        "torch_device": "cuda:0" if torch.cuda.is_available() else "cpu",
    }


def make_party_series(n_series: int, n_points: int, seed: int, period: int = 12) -> list[np.ndarray]:
    """Simula ~10 series mensuales tipo 'intención de voto' por partido (0-100).

    Cada serie: nivel base distinto + tendencia propia + estacionalidad anual
    (periodo 12, con fase distinta) + ruido. No pretende ser realista
    electoralmente, solo reproducir la forma (longitud, escala, ciclo).
    """
    rng = np.random.default_rng(seed)
    out = []
    t = np.arange(n_points, dtype=float)
    for k in range(n_series):
        level = float(rng.uniform(3.0, 40.0))          # partidos grandes y pequeños
        trend = float(rng.uniform(-0.03, 0.03))        # deriva lenta
        amp1 = float(rng.uniform(0.5, 4.0))
        amp2 = float(rng.uniform(0.2, 1.5))
        phase = float(rng.uniform(0, 2 * np.pi))
        seasonal = amp1 * np.sin(2 * np.pi * t / period + phase) + amp2 * np.cos(4 * np.pi * t / period + phase)
        noise = rng.normal(0.0, 0.8, size=n_points)
        out.append(np.clip(level + trend * t + seasonal + noise, 0.0, 100.0))
    return out


# --------------------------------------------------------------------------- #
# Núcleo del smoke
# --------------------------------------------------------------------------- #
def run_smoke(
    years: int,
    horizon: int,
    n_series: int,
    per_core_batch_size: int,
    seed: int,
    torch_compile: bool,
) -> dict:
    import timesfm

    n_points = years * 12
    series = make_party_series(n_series, n_points, seed=seed)
    report: dict = {
        "config": {
            "years": years,
            "n_points_per_series": n_points,
            "horizon": horizon,
            "n_series": n_series,
            "per_core_batch_size": per_core_batch_size,
            "seed": seed,
            "torch_compile": torch_compile,
            "checkpoint": CHECKPOINT,
            "quantile_column_map": {
                "point": POINT_COLUMN,
                "levels": dict(zip(QUANTILE_COLUMNS, QUANTILE_LEVELS)),
            },
        }
    }
    report["versions"] = _versions()
    report["rss_before_load_gib"] = round(_peak_rss_gib(), 3)

    # --- Carga del checkpoint ------------------------------------------------
    t0 = time.perf_counter()
    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(CHECKPOINT, torch_compile=torch_compile)
    report["load_seconds"] = round(time.perf_counter() - t0, 2)
    report["rss_after_load_gib"] = round(_peak_rss_gib(), 3)

    # --- Compilación ---------------------------------------------------------
    # max_context debe ser múltiplo de 32 y max_horizon múltiplo de 128;
    # con cabecera de cuantiles continuos, max_horizon <= 1024.
    cfg = timesfm.ForecastConfig(
        max_context=n_points,
        max_horizon=max(horizon, 128),
        normalize_inputs=True,
        use_continuous_quantile_head=True,
        force_flip_invariance=True,
        infer_is_positive=True,
        fix_quantile_crossing=True,
        per_core_batch_size=per_core_batch_size,
    )
    t0 = time.perf_counter()
    model.compile(cfg)
    report["compile_seconds"] = round(time.perf_counter() - t0, 2)
    report["global_batch_size"] = int(model.global_batch_size)

    # --- Inferencia ----------------------------------------------------------
    t0 = time.perf_counter()
    _ = model.forecast(horizon=horizon, inputs=[s.copy() for s in series])  # warm-up
    report["warmup_seconds"] = round(time.perf_counter() - t0, 4)

    t0 = time.perf_counter()
    point, quantiles = model.forecast(horizon=horizon, inputs=[s.copy() for s in series])
    report["batch_inference_seconds"] = round(time.perf_counter() - t0, 4)
    report["ms_per_series"] = round(1000.0 * report["batch_inference_seconds"] / n_series, 2)
    report["rss_peak_gib"] = round(_peak_rss_gib(), 3)

    point = np.asarray(point)
    quantiles = np.asarray(quantiles)
    report["point_shape"] = list(point.shape)
    report["quantiles_shape"] = list(quantiles.shape)

    # --- Verificación de contrato -------------------------------------------
    # 1) el punto es la columna 5 (mediana)
    report["point_equals_quantile_col5_max_abs_diff"] = float(
        np.max(np.abs(point - quantiles[:, :horizon, POINT_COLUMN]))
    )
    # 2) los 9 cuantiles (columnas 1..9) no se cruzan
    q = quantiles[:, :horizon, QUANTILE_COLUMNS]
    crossings = int((np.diff(q, axis=2) < -1e-6).sum())
    report["quantile_crossing_violations"] = crossings
    report["interval_note"] = "q0.1..q0.9 => intervalo central 80% (no 90%)"

    # --- Series de salida ----------------------------------------------------
    report["series_last_observed"] = [[round(float(v), 2) for v in s[-4:]] for s in series]
    report["series_point_forecast"] = [[round(float(v), 2) for v in point[i]] for i in range(n_series)]
    # Tabla completa de cuantiles para la primera serie (partido grande y pequeño no importa aquí)
    report["quantiles_series0"] = {
        str(lv): [round(float(v), 2) for v in q[0, :, i]]
        for i, lv in enumerate(QUANTILE_LEVELS)
    }
    # Anchos del intervalo central 80% (q0.9 - q0.1) por serie
    widths = q[:, :, -1] - q[:, :, 0]
    report["interval_width_80_mean_per_series"] = [round(float(w.mean()), 2) for w in widths]

    report["ok"] = True
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="TimesFM smoke test (29N)")
    ap.add_argument("--years", type=int, default=50, help="años de serie mensual (default 50)")
    ap.add_argument("--horizon", type=int, default=12, help="horizonte en meses (default 12 = 1 ciclo)")
    ap.add_argument("--n-series", type=int, default=10, help="nº de series en el lote (default 10 = partidos)")
    ap.add_argument("--per-core-batch-size", type=int, default=32)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--torch-compile", action="store_true",
                    help="activa torch.compile (arranque más lento; off por defecto)")
    ap.add_argument("--json", type=Path, default=None, help="guarda el informe en JSON")
    args = ap.parse_args()

    report = run_smoke(
        args.years, args.horizon, args.n_series,
        args.per_core_batch_size, args.seed, args.torch_compile,
    )

    print("=" * 72)
    print("TimesFM smoke test — 29N")
    print("=" * 72)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("=" * 72)

    ok = (
        report["point_equals_quantile_col5_max_abs_diff"] < 1e-6
        and report["quantile_crossing_violations"] == 0
    )
    print(f"CONTRACT CHECK: point==col5 dif={report['point_equals_quantile_col5_max_abs_diff']:.2e}, "
          f"crossings={report['quantile_crossing_violations']} -> {'OK' if ok else 'FAIL'}")

    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"Informe guardado en {args.json}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
