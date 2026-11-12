#!/usr/bin/env python3
"""Reparto de escaños por D'Hondt (Ley Orgánica 5/1985, art. 163 LOREG).

Circunscripción = provincia. Umbral legal por defecto del 3 % de los votos
válidos de la circunscripción (candidaturas + en blanco), que es el que aplica
a las elecciones al Congreso de los Diputados.

Función pura, sin dependencias. Se usa tanto para normalizar como para la
validación obligatoria (reproducir los escaños oficiales a partir de los votos
provinciales).

`dhondt()` es el reparto; `escalera_cocientes()` expone la tabla de cocientes
que lo produce (misma ordenación, misma aritmética) y `ultimo_escano()` lee de
ella el escaño N y su rival más próximo. Las tres comparten el mismo helper,
así que el reparto no puede divergir de la escalera publicada.
"""

from __future__ import annotations


def _elegibles(votes, threshold_frac, valid_votes):
    """Candidaturas que superan el umbral (y tienen votos)."""
    total = sum(v for v in votes.values() if v > 0)
    if valid_votes is None:
        valid_votes = total
    cut = threshold_frac * valid_votes
    return {c: v for c, v in votes.items() if v > 0 and v >= cut}


def escalera_cocientes(votes, seats, threshold_frac=0.03, valid_votes=None):
    """Escalera de cocientes elegibles, ordenada como la usa `dhondt`.

    Returns
    -------
    list[tuple[float, str]]
        Pares ``(cociente, candidatura)`` ordenados por ``(-cociente, nombre)``.
        El escaño *k* (1-based) lo gana ``escalera[k - 1]``. Longitud =
        candidaturas elegibles × ``seats`` (vacía si ``seats <= 0``).

    Notas
    -----
    - Empates de cociente se rompen de forma determinista por nombre de
      candidatura (orden lexicográfico), igual que en `dhondt`.
    """
    if seats <= 0:
        return []
    eligible = _elegibles(votes, threshold_frac, valid_votes)
    quotients = []
    for cand, v in eligible.items():
        for k in range(1, seats + 1):
            quotients.append((v / k, cand))
    quotients.sort(key=lambda q: (-q[0], q[1]))
    return quotients


def reparto(votes, seats, threshold_frac=0.03, valid_votes=None):
    """Reparto y escalera en una sola pasada: ``(escaños, escalera)``."""
    result = {c: 0 for c in votes}
    ladder = escalera_cocientes(votes, seats, threshold_frac, valid_votes)
    for _, cand in ladder[:seats]:
        result[cand] += 1
    return result, ladder


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
    return reparto(votes, seats, threshold_frac, valid_votes)[0]


def ultimo_escano(escalera, seats):
    """Ganador del último escaño y rival con el mejor cociente no adjudicado.

    El escaño N (el último que reparte D'Hondt) lo gana ``escalera[seats - 1]``.
    Su rival es el **cociente no adjudicado más alto de otro partido**: si el
    siguiente cociente de la tabla pertenece al propio ganador (escaños
    consecutivos del mismo partido), no hay duelo real por ese escaño y se
    busca el mejor cociente de un partido distinto. El desempate es el mismo
    de `dhondt`: cociente mayor → nombre por orden alfabético.

    Returns
    -------
    tuple[str, str, float] | None
        ``(ganador, rival, diferencia_relativa)`` con
        ``diferencia_relativa = (q_ganador - q_rival) / q_ganador`` en [0, 1].
        ``rival == ganador`` y diferencia 0 cuando no hay otro partido con
        cocientes (circunscripción de un solo partido elegible).
        ``None`` si no hay escaños que repartir.
    """
    if seats <= 0 or len(escalera) < seats:
        return None
    q_a, ganador = escalera[seats - 1]
    rival = ganador
    q_b = None
    for q, cand in escalera[seats:]:
        if cand != ganador:
            rival, q_b = cand, q
            break
    if q_b is None or q_a <= 0:
        return ganador, rival, 0.0
    return ganador, rival, (q_a - q_b) / q_a
