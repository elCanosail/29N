#!/usr/bin/env python3
"""Miembro bayesiano dinámico (filtro de Kalman) para el 29N.

Modelo
------
Estado latente ``x_t`` = intención de voto (en % sobre voto válido) por
partido, que evoluciona como **random walk** con volatilidad ``sigma_daily``
(pp/√día):

    x_t = x_{t-1} + w_t,        w_t ~ N(0, sigma_daily² · Δt · I_K)

Observación = cada encuesta. La observación del partido ``p`` en la casa ``c``
en la fecha ``t_i``:

    y_i = x_{t_i}[p] + h_c + eps_i,   eps_i ~ N(0, tau_i²)

- ``tau_i`` se deriva del tamaño muestral con inflación de diseño:
  ``tau_i = deff · 100·√(p̂(1-p̂)/n_i)`` con ``p̂ = value_i/100``, ``deff``
  en 1,5–2 (por defecto 1,7), y un suelo ``tau_floor`` para evitar confianza
  degenerada en partidos pequeños.
- ``h_c`` = efecto de casa residual (la corrección EB de ``common.py`` ya se
  aplica **antes** sobre ``value``; ``h_c`` recoge el sesgo específico de casa
  que queda). Se estima como estado constante con prior **centrado en 0** y
  varianza ``sigma_h²``; el filtro de Kalman hace el *shrinkage* hacia la media
  de casas de forma natural (encogimiento por cociente de varianzas).
  Tras filtrar se recentra ``h`` a media cero entre casas y se devuelve la
  media absorbida a ``x`` (invariante en ``y = x + h``), lo que garantiza la
  identificabilidad del nivel y sustituye explícitamente la media de casas.

Forecast
--------
``x_T`` propagado desde la última observación hasta la fecha de corte (día de
la elección) **con la misma volatilidad** ``sigma_daily`` (la varianza suma
``sigma_daily²·Δt_e``). La predictiva es ``x_T ~ N(m_T, P_T + sigma_daily²·Δt_e)``.

Sin MCMC, sin dependencias nuevas: solo ``numpy`` (ya usado por el repo) y
stdlib. Semillas irrelevantes (el filtro es determinista).
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np

# --- Hiperparámetros por defecto (documentados en el informe) --------------
DEFAULT_SIGMA_DAILY = 0.15   # pp/√día (volatilidad del random walk de x_t)
DEFAULT_DEFF = 1.7           # inflación de diseño (rango objetivo 1,5–2)
DEFAULT_TAU_FLOOR = 0.30     # pp, suelo del ruido de observación
DEFAULT_SIGMA_H = 1.00       # pp, prior SD del efecto de casa residual
DEFAULT_P0 = 25.0            # pp², varianza inicial difusa de x (SD 5 pp)
DEFAULT_EXTRA_SD = 0.00      # pp, término extra de realización electoral (off)


def obs_tau(value, n, deff=DEFAULT_DEFF, floor=DEFAULT_TAU_FLOOR):
    """Ruido de observación (pp) derivado del tamaño muestral.

    ``tau = max(floor, deff · 100·√(p̂(1-p̂)/n))`` con ``p̂ = value/100``.
    """
    p = min(max(float(value) / 100.0, 0.005), 0.995)
    n = max(int(n or 1), 1)
    se = 100.0 * math.sqrt(p * (1.0 - p) / n)
    return max(float(floor), float(deff) * se)


class BayesDynamic:
    """Filtro de Kalman para el miembro bayesiano dinámico.

    Parameters
    ----------
    parties : list[str]
        Partidos modelados (orden canónico).
    sigma_daily : float
        Volatilidad diaria del random walk (pp/√día).
    deff : float
        Inflación de diseño del ruido de observación.
    tau_floor : float
        Suelo (pp) del ruido de observación.
    sigma_h : float
        SD del prior del efecto de casa residual (pp).
    p0 : float
        Varianza inicial difusa de ``x`` (pp²).
    extra_sd : float
        Término aditivo de realización electoral (pp) sumado en el forecast.
        Por defecto 0 (modelo fiel al enunciado).
    """

    def __init__(self, parties, sigma_daily=DEFAULT_SIGMA_DAILY, deff=DEFAULT_DEFF,
                 tau_floor=DEFAULT_TAU_FLOOR, sigma_h=DEFAULT_SIGMA_H,
                 p0=DEFAULT_P0, extra_sd=DEFAULT_EXTRA_SD):
        self.parties = list(parties)
        self.sigma_daily = float(sigma_daily)
        self.deff = float(deff)
        self.tau_floor = float(tau_floor)
        self.sigma_h = float(sigma_h)
        self.p0 = float(p0)
        self.extra_sd = float(extra_sd)

    # ------------------------------------------------------------------ #
    def predict(self, observations, data_cutoff, propagate_to=None):
        """Filtra y proyecta hasta la fecha de la elección.

        Parameters
        ----------
        observations : list[dict]
            Cada dict con ``date`` (date), ``casa`` (str), ``party`` (str),
            ``value`` (float, % sobre válido, ya corregida por EB en
            ``common.Observations``) y ``n`` (int). Solo se usan las
            observaciones con ``date < data_cutoff``.
        data_cutoff : date
            Corte de información (exclusivo). Para reproducir el protocolo
            del baseline, es el **primer día del mes de la elección**: la
            rejilla mensual del baseline se trunca en el fin de mes anterior,
            de modo que las observaciones del mes de la votación quedan fuera.
        propagate_to : date | None
            Fecha a la que se propaga ``x_T`` (por defecto ``data_cutoff``).
            El punto no cambia (random walk sin deriva); solo crece la
            varianza.

        Returns
        -------
        dict con:
          - ``mean``: {partido: punto}
          - ``sd``:   {partido: SD predictiva en la fecha de corte}
          - ``house_effects``: {casa: h_c}
          - ``n_obs``: nº de observaciones usadas
          - ``last_obs``: fecha de la última observación usada
          - ``days_to_election``: días desde la última obs al corte
        """
        if propagate_to is None:
            propagate_to = data_cutoff
        cutoff = propagate_to
        parties = self.parties
        K = len(parties)
        pidx = {p: i for i, p in enumerate(parties)}
        obs = [o for o in observations
               if o["party"] in pidx and o["date"] < data_cutoff]
        obs.sort(key=lambda o: (o["date"], o["casa"]))

        if not obs:
            return {
                "mean": {p: 0.0 for p in parties},
                "sd": {p: math.sqrt(self.p0 + (self.extra_sd ** 2)) for p in parties},
                "house_effects": {},
                "n_obs": 0, "last_obs": None, "days_to_election": None,
            }

        houses = sorted({o["casa"] for o in obs})
        H = len(houses)
        hidx = {h: K + j for j, h in enumerate(houses)}
        n = K + H

        mu = np.zeros(n)
        P = np.zeros((n, n))
        for i in range(K):
            P[i, i] = self.p0
        for j in range(H):
            P[K + j, K + j] = self.sigma_h ** 2

        # Init de x con la primera observación de cada partido (evita transitorio)
        first = {}
        for o in obs:
            first.setdefault(o["party"], o["value"])
        for p, v in first.items():
            mu[pidx[p]] = v

        prev_date = None
        counts = {}
        for o in obs:
            if prev_date is not None:
                dt = (o["date"] - prev_date).days
                if dt > 0:
                    P[:K, :K] += (self.sigma_daily ** 2 * dt) * np.eye(K)
            prev_date = o["date"]

            a = pidx[o["party"]]
            b = hidx[o["casa"]]
            tau2 = obs_tau(o["value"], o["n"], self.deff, self.tau_floor) ** 2

            pred = mu[a] + mu[b]
            Ph = P[:, a] + P[:, b]          # = P @ h_obs
            S = Ph[a] + Ph[b] + tau2
            Kg = Ph / S
            mu = mu + Kg * (o["value"] - pred)
            P = P - np.outer(Kg, Ph)
            P = 0.5 * (P + P.T)              # mantener simetría numérica
            counts[o["casa"]] = counts.get(o["casa"], 0) + 1

        # Recentrado de efectos de casa (shrinkage hacia la media de casas):
        # h_j <- h_j - h̄ ;  x_p <- x_p + h̄   (invariante en y = x + h)
        hvals = np.array([mu[K + j] for j in range(H)])
        wts = np.array([counts.get(h, 1) for h in houses], dtype=float)
        hmean = float((hvals * wts).sum() / wts.sum()) if wts.sum() > 0 else 0.0
        for j in range(H):
            mu[K + j] -= hmean
        for i in range(K):
            mu[i] += hmean

        days_to_election = (cutoff - prev_date).days
        var_extra = (self.sigma_daily ** 2) * max(days_to_election, 0)
        mean = {p: float(mu[pidx[p]]) for p in parties}
        sd = {p: math.sqrt(max(P[pidx[p], pidx[p]] + var_extra
                               + self.extra_sd ** 2, 0.0)) for p in parties}
        return {
            "mean": mean,
            "sd": sd,
            "house_effects": {h: float(mu[hidx[h]]) for h in houses},
            "n_obs": len(obs),
            "last_obs": prev_date,
            "days_to_election": days_to_election,
        }


# --------------------------------------------------------------------------- #
# Adaptador sobre las observaciones de common.py
# --------------------------------------------------------------------------- #
def observations_from_common(common_obs, parties):
    """Extrae la lista de observaciones relevantes de ``common.Observations``.

    Reutiliza los valores **ya corregidos por EB** de ``common.py`` (la
    corrección se aplica al construir ``Observations``), de modo que el efecto
    de casa que estima el Kalman es el residual, sin duplicar la lógica.
    """
    pset = set(parties)
    return [{"date": o["date"], "casa": o["casa"], "party": o["party"],
             "value": float(o["value"]), "n": int(o["n"] or 1)}
            for o in common_obs.obs if o["party"] in pset]
