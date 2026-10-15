#!/usr/bin/env python3
"""Reparto de escaños por D'Hondt (Ley Orgánica 5/1985, art. 163 LOREG).

Circunscripción = provincia. Umbral legal por defecto del 3 % de los votos
válidos de la circunscripción (candidaturas + en blanco), que es el que aplica
a las elecciones al Congreso de los Diputados.

Función pura, sin dependencias. Se usa tanto para normalizar como para la
validación obligatoria (reproducir los escaños oficiales a partir de los votos
provinciales).
"""

from __future__ import annotations


def dhondt(votes, seats, threshold_frac=0.03, valid_votes=None):
    """Reparte `seats` escaños entre `votes` por el método D'Hondt.

    Parameters
    ----------
    votes : dict[str, int|float]
        Votos por candidatura en la circunscripción.
    seats : int
        Escaños a repartir en la circunscripción.
    threshold_frac : float
        Umbral mínimo de votos para entrar en el reparto, como fracción de
        `valid_votes` (0.03 = 3 %). 0 desactiva el umbral.
    valid_votes : int|float|None
        Total de votos válidos de la circunscripción para el umbral. Si es None
        se usa la suma de los votos de las propias candidaturas (sin blancos).

    Returns
    -------
    dict[str, int]
        Escaños por candidatura (misma clave que `votes`; incluye ceros).

    Notas
    -----
    - Empates de cociente se rompen de forma determinista por nombre de
      candidatura (orden lexicográfico). La LOREG los resuelve por sorteo; en
      la práctica no afecta a los escaños (los empates exactos en el corte son
      rarísimos y, si ocurren, se documentan en la validación).
    """
    result = {c: 0 for c in votes}
    if seats <= 0:
        return result

    total = sum(v for v in votes.values() if v > 0)
    if valid_votes is None:
        valid_votes = total
    cut = threshold_frac * valid_votes

    eligible = {c: v for c, v in votes.items() if v > 0 and v >= cut}
    if not eligible:
        return result

    quotients = []
    for cand, v in eligible.items():
        for k in range(1, seats + 1):
            quotients.append((v / k, cand))
    quotients.sort(key=lambda q: (-q[0], q[1]))

    for _, cand in quotients[:seats]:
        result[cand] += 1
    return result
