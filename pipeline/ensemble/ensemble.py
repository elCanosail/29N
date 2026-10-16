#!/usr/bin/env python3
"""Ensemble 50/50 (bayesiano dinámico + baseline) para el 29N.

Combinación
-----------
Dos miembros:

- **bayesiano dinámico** (``kalman.BayesDynamic``): punto ``m_b`` y SD
  predictiva ``s_b`` (modelo, honesta).
- **baseline** = modelo vivo (`forecast.py`): última media ponderada. En el
  backtest solo da **punto**; sus intervalos se derivan de la **SD empírica de
  sus errores** por partido (misma definición que el modelo vivo:
  ``z(lv)·s``), con la SD agrupada si el partido tiene n<2. Es la aproximación
  documentada en el informe.

Punto del ensemble = media aritmética 50/50:
    m_e = 0,5·m_b + 0,5·m_base

Intervalos = cuantiles de la **mezcla** de las dos predictivas gaussianas:
    F_e(z) = 0,5·Φ((z-m_b)/s_b) + 0,5·Φ((z-m_base)/s_base)
Los cuantiles se obtienen por bisección sobre ``F_e`` (determinista,
reproducible; sin Monte Carlo salvo que se pida explícitamente).
"""

from __future__ import annotations

import math

_SQRT2 = math.sqrt(2.0)


def _ncdf(x: float, m: float, s: float) -> float:
    if s <= 0:
        return 1.0 if x >= m else 0.0
    return 0.5 * (1.0 + math.erf((x - m) / (s * _SQRT2)))


def mixture_cdf(x, m1, s1, m2, s2, w1=0.5):
    """CDF de la mezcla de dos gaussianas."""
    return w1 * _ncdf(x, m1, s1) + (1.0 - w1) * _ncdf(x, m2, s2)


def mixture_quantile(m1, s1, m2, s2, q, w1=0.5, tol=1e-9, max_iter=200):
    """Cuantil ``q`` de la mezcla 50/50 por bisección (determinista)."""
    lo = min(m1 - 10 * s1, m2 - 10 * s2)
    hi = max(m1 + 10 * s1, m2 + 10 * s2)
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if mixture_cdf(mid, m1, s1, m2, s2, w1) < q:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def ensemble_point(bayes_mean, base_point, w1=0.5):
    """Punto del ensemble (media de los dos miembros)."""
    return w1 * bayes_mean + (1.0 - w1) * base_point


def ensemble_quantiles(bayes_mean, bayes_sd, base_point, base_sd, levels,
                       w1=0.5):
    """Cuantiles centrales de la mezcla para una lista de niveles."""
    return {lv: mixture_quantile(bayes_mean, bayes_sd, base_point, base_sd, lv, w1)
            for lv in levels}
