#!/usr/bin/env python3
"""Modelo multinivel (jerárquico) de intención de voto para el MRP provincial.

`mrp_core.fit_mrp` usa *efectos fijos* por provincia (dummies) con una
regularización L2 única para **todos** los coeficientes (demografía incluida).
Eso no es un modelo multinivel: es una regresión con provincia como factor fijo
y un encogimiento uniforme, que además penaliza la demografía (lo que no debe).

Este módulo implementa el modelo multinivel propiamente dicho:

    logit P(y_i = k) = α_k + β_{k, demo_i} + u_{k, provincia_i}
    u_{k,p} ~ N(0, τ_k²)                      (efecto aleatorio de provincia)

- **demografía** (sexo × edad × estudios, interacción completa, 42 celdas):
  efectos fijos sin penalizar (identifican la estructura sociodemográfica).
- **provincia**: intercepto **aleatorio** por provincia y partido, con varianza
  τ_k² **estimada de los datos** por *empirical Bayes* (estimador de momento
  iterado). El encogimiento de cada provincia hacia la media nacional es
  u_post = u_hat, pero la **cantidad** de encogimiento la fija τ_k² y la
  precisión de la provincia, no una constante impuesta a ojo (a diferencia del
  `C=1.0` de la variante de efectos fijos).

Ajuste: maximización de la log-verosimilitud multinomial ponderada **penalizada**
(posterior mode bajo el prior gaussiano) con L-BFGS-B (scipy). Nada de MCMC:
con 52 provincias y ~1.000-2.000 entrevistas por estudio, el posterior mode y el
momento EB de τ_k² son reproducibles en segundos y suficientes para el backtest.

Uso interno desde `backtest_mrp.py` (`fit_mrp_hier` / `predict_hier`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

from mrp_core import AGE_GROUPS, EDU_GROUPS, SEXOS  # noqa: F401  (documentación)

DEMO_INDEX = {f"{s}|{a}|{e}": i
              for i, (s, a, e) in enumerate(
                  (s, a, e) for s in SEXOS for a in AGE_GROUPS for e in EDU_GROUPS)}
PROV_INDEX = {str(i + 1): i for i in range(52)}


@dataclass
class HierModel:
    classes: list            # orden de clases (la última es la de referencia)
    demo_index: dict
    prov_index: dict
    A: np.ndarray            # (K,)
    B: np.ndarray            # (K, n_demo)
    U: np.ndarray            # (K, n_prov)
    tau2: np.ndarray         # (K,) varianza del prior por clase (0 en la ref.)
    n_demo: int
    n_prov: int
    log: dict = field(default_factory=dict)

    # -- probabilidades ---------------------------------------------------
    def _eta(self, demo_idx, prov_idx):
        eta = self.A[:, None] + self.B[:, demo_idx] + self.U[:, prov_idx]
        return eta

    def predict_proba(self, demo_idx, prov_idx):
        eta = self._eta(demo_idx, prov_idx)
        m = eta.max(axis=0, keepdims=True)
        e = np.exp(eta - m)
        return e / e.sum(axis=0, keepdims=True)

    # -- tamaño efectivo por provincia (diagnóstico de encogimiento) ------
    def shrink_diag(self):
        return {"tau_por_clase": {c: float(np.sqrt(self.tau2[i]))
                                  for i, c in enumerate(self.classes)}}


def _encode(train, universe, classes):
    """Índices de demo y provincia + vector de etiquetas y pesos."""
    demo_idx = train["demo"].map(DEMO_INDEX).to_numpy()
    prov_idx = train["prov"].map(PROV_INDEX).to_numpy()
    cls_idx = train["clase"].map({c: i for i, c in enumerate(classes)}).to_numpy()
    w = train["peso"].to_numpy(dtype=np.float64)
    ok = ~(np.isnan(demo_idx) | np.isnan(prov_idx) | np.isnan(cls_idx))
    return (demo_idx[ok].astype(np.int64), prov_idx[ok].astype(np.int64),
            cls_idx[ok].astype(np.int64), w[ok])


def _split(params, K, n_demo, n_prov):
    kk = K - 1
    a = params[0:kk]
    b = params[kk:kk + kk * n_demo].reshape(kk, n_demo)
    u = params[kk + kk * n_demo:].reshape(kk, n_prov)
    return a, b, u


def _neg_logpost(params, K, n_demo, n_prov, demo_idx, prov_idx, cls_idx, w,
                 tau2, lam_b, n):
    """-log posterior (softmax ponderado + prior N(0,tau2) en U, ridge en B).

    La clase K-1 es la referencia y va fija a 0 (identificación).
    """
    kk = K - 1
    a, b, u = _split(params, K, n_demo, n_prov)

    eta = a[:, None] + b[:, demo_idx] + u[:, prov_idx]        # (kk, n)
    m = np.maximum(eta.max(axis=0), 0.0)     # incluye la clase de referencia (logit 0)
    e = np.exp(eta - m)
    Z = np.exp(-m) + e.sum(axis=0)           # ref: exp(0 - m)
    logZ = m + np.log(Z)
    # log p de la clase observada
    obs_eta = np.where(cls_idx < kk, eta[np.minimum(cls_idx, kk - 1), np.arange(n)], 0.0)
    ll = float(np.sum(w * (obs_eta - logZ)))

    pen_u = float(np.sum(u * u / tau2[:, None]))
    pen_b = float(lam_b * np.sum(b * b))
    loss = -(ll - 0.5 * pen_u - 0.5 * pen_b)

    # gradiente (∂loss/∂parámetro), con loss = -ll + ½·pen_u + ½·pen_b
    p = e / Z                                                # (kk, n) = P(k<ref)
    g_eta = w[None, :] * (p - (cls_idx[None, :] == np.arange(kk)[:, None]))
    g_a = g_eta.sum(axis=1)
    # Acumulación por grupo con bincount (sin escribir a través de vistas).
    g_b = np.zeros((kk, n_demo))
    g_u = np.zeros((kk, n_prov))
    for k in range(kk):
        g_b[k] = np.bincount(demo_idx, weights=g_eta[k], minlength=n_demo)
        g_u[k] = np.bincount(prov_idx, weights=g_eta[k], minlength=n_prov)
    g_u += u / tau2[:, None]
    g_b += lam_b * b
    g = np.concatenate([g_a, g_b.ravel(), g_u.ravel()])
    return loss, g


def _laplace_criterion(params, K, n_demo, n_prov, demo_idx, prov_idx, cls_idx, w,
                       tau2, n_prov_bins=52):
    """Evidencia EB (aprox. Laplace) para un τ² dado.

    log m(y; τ²) ≈ ll_verdadera − ½·Σu²/τ² − ½·log|A|,  A = τ²⁻¹·I + H_u,
    con H_u aproximada por su diagonal de Fisher (info_{k,p}). Se maximiza sobre
    la rejilla de τ² (empirical Bayes). El prior sobre la demografía (lam_b) es
    despreciable y no entra en el criterio.
    """
    kk = K - 1
    a, b, u = _split(params, K, n_demo, n_prov)
    eta = a[:, None] + b[:, demo_idx] + u[:, prov_idx]
    m = np.maximum(eta.max(axis=0), 0.0)     # incluye la clase de referencia (logit 0)
    e = np.exp(eta - m)
    Z = np.exp(-m) + e.sum(axis=0)
    logZ = m + np.log(Z)
    obs_eta = np.where(cls_idx < kk,
                       eta[np.minimum(cls_idx, kk - 1), np.arange(len(cls_idx))], 0.0)
    ll = float(np.sum(w * (obs_eta - logZ)))
    pen = float(np.sum(u * u / tau2[:, None]))
    p = e / Z
    logdetA = 0.0
    for k in range(kk):
        info = np.bincount(prov_idx, weights=w * p[k] * (1.0 - p[k]),
                           minlength=n_prov_bins)[:n_prov_bins]
        logdetA += float(np.sum(np.log(1.0 / tau2[k] + info)))
    # término de complejidad del prior: −½·d·log(τ²), d = dim(u)
    dim_u = kk * n_prov
    return ll - 0.5 * pen - 0.5 * logdetA - 0.5 * dim_u * float(np.log(tau2[0]))


def fit_mrp_hier(train, universe, lam_b: float = 1e-4,
                 tau_grid=(0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5),
                 tol: float = 1e-6, max_iter: int = 600):
    """Ajusta el MRP multinivel con **una** varianza de provincia común (τ²)
    seleccionada por evidencia (Laplace). Devuelve (HierModel, log)."""
    present = set(train["clase"].unique())
    classes = [c for c in universe if c in present]
    classes = classes + [c for c in train["clase"].unique() if c not in classes]
    K = len(classes)
    n_demo, n_prov = len(DEMO_INDEX), len(PROV_INDEX)
    demo_idx, prov_idx, cls_idx, w = _encode(train, universe, classes)
    n = len(demo_idx)
    kk = K - 1

    log = {"clases": classes, "n": n, "grid": []}
    params0 = np.zeros(kk * (1 + n_demo + n_prov), dtype=np.float64)
    best = None
    for tau in tau_grid:
        tau2 = np.full(kk, float(tau) ** 2, dtype=np.float64)
        res = minimize(_neg_logpost, params0,
                       args=(K, n_demo, n_prov, demo_idx, prov_idx, cls_idx, w,
                             tau2, lam_b, n),
                       method="L-BFGS-B", jac=True,
                       options={"maxiter": max_iter, "ftol": tol, "gtol": 1e-8})
        crit = _laplace_criterion(res.x, K, n_demo, n_prov, demo_idx, prov_idx,
                                  cls_idx, w, tau2)
        log["grid"].append({"tau": float(tau), "tau2": float(tau) ** 2,
                            "criterio_laplace": round(float(crit), 3),
                            "loss_penalizada": round(float(res.fun), 3),
                            "converged": bool(res.success)})
        if best is None or crit > best["crit"]:
            best = {"crit": crit, "tau": float(tau), "params": res.x.copy(),
                    "tau2": tau2}

    params = best["params"]
    tau2 = best["tau2"]
    log["tau_seleccionado"] = best["tau"]
    log["tau2_seleccionado"] = float(best["tau"] ** 2)
    log["criterio_laplace_max"] = float(best["crit"])

    A = np.concatenate([params[0:kk], [0.0]])
    B = np.vstack([params[kk:kk + kk * n_demo].reshape(kk, n_demo),
                   np.zeros((1, n_demo))])
    U = np.vstack([params[kk + kk * n_demo:].reshape(kk, n_prov),
                   np.zeros((1, n_prov))])
    model = HierModel(classes=classes, demo_index=DEMO_INDEX, prov_index=PROV_INDEX,
                      A=A, B=B, U=U, tau2=np.concatenate([tau2, [0.0]]),
                      n_demo=n_demo, n_prov=n_prov, log=log)
    log["tau_final"] = {classes[i]: float(np.sqrt(max(tau2[i], 0.0)))
                        for i in range(kk)}
    log["tau_final"][classes[-1]] = 0.0   # clase de referencia, sin efecto
    return model, log


def predict_cells_hier(model: HierModel, censo) -> np.ndarray:
    """Probabilidad por clase y celda censal (provincia × sexo × edad × estudios).

    Devuelve una matriz (n_celdas, K). Las probabilidades se normalizan a 1
    sobre **todas** las clases (incluida la residual no partidista); la
    normalización al universo de partidos la hace la post-estratificación.
    """
    demo = (censo["sexo"] + "|" + censo["edad_grupo"] + "|" + censo["edu_grupo"])
    d_idx = demo.map(DEMO_INDEX).to_numpy()
    p_idx = censo["provincia"].astype(str).map(PROV_INDEX).to_numpy()
    if np.isnan(d_idx).any() or np.isnan(p_idx).any():
        bad = int(np.isnan(d_idx).sum() + np.isnan(p_idx).sum())
        raise ValueError(f"{bad} celdas censales sin categoría en el modelo")
    P = model.predict_proba(d_idx.astype(np.int64), p_idx.astype(np.int64))
    return P.T   # (n_celdas, K)


def poststratify_hier(P, censo, classes, universe):
    """Post-estratificación provincial del modelo jerárquico.

    Igual que `mrp_core.poststratify`: cuota_k = Σ_celdas N_celda·P(k|celda) /
    Σ_celdas N_celda·P(universo|celda), normalizado a 100 por provincia.
    """
    pob = censo["poblacion"].to_numpy(dtype=float)
    prov = censo["provincia"].to_numpy()
    idx = {c: i for i, c in enumerate(classes)}
    uni_cols = [idx[p] for p in universe if p in idx]
    den = P[:, uni_cols].sum(axis=1) * pob
    out = {int(p): {} for p in np.unique(prov)}
    den_prov = np.bincount(prov, weights=den, minlength=53)
    for p in universe:
        if p not in idx:
            for k in out:
                out[k][p] = 0.0
            continue
        num = np.bincount(prov, weights=P[:, idx[p]] * pob, minlength=53)
        d = den_prov.copy()
        d[d == 0] = np.nan
        sh = 100.0 * num / d
        for k in out:
            out[k][p] = float(sh[k]) if not np.isnan(sh[k]) else 0.0
    return out
