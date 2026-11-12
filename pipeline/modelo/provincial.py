#!/usr/bin/env python3
"""Fase 4 (paso 5) — Desagregación provincial y simulación D'Hondt.

Modelo de swing **proporcional uniforme**: el ratio nacional de cada partido
(target / base_23J) se aplica a su cuota en cada provincia, preservando la
geografía del voto. Se descartó el swing **aditivo** (mismo ±pp en todas las
provincias) porque destruye a los partidos de apoyo concentrado: para bajar a
CC 0,3 pp en el agregado nacional habría que restarle ~16 pp en Canarias.
Fórmula:

    v_{p,k} ∝ base_{p,k} · r_k ,   r_k = target_k / base_nacional_k
    (normalizada a 100 dentro de cada provincia)

Coherencia verificable: como `Σ_k base_{p,k}·r_k` no suma 100 exacto por
provincia, tras normalizar se **calibra r** iterativamente (método de punto
fijo `r_k ← r_k · target_k / agg_k`) hasta que el agregado provincial ponderado
por votos coincide con el forecast estatal en ≤ 0,1 pp. Converge en ~5
iteraciones (ver `test_coherence.py`).

Simulación: 10.000 runs muestreando las cuotas nacionales (N(punto, σ_backtest),
recorte a ≥0 y renormalización), recalibrando y aplicando D'Hondt por provincia
(`pipeline/interior/dhondt.py`).

Salida: `data/processed/modelo/seats.json`.

Agregados nuevos (PR-2 de la issue #15), todos derivados de las mismas 10.000
corridas — el modelo no cambia:

- `bloques`: suma de escaños por bloque de investidura en cada corrida
  (pertenencia editorial en `bloques.yaml`, constante versionada y citable),
  con `p_ge176` = proporción de corridas que alcanzan la mayoría absoluta.
- `provincias[c].ultimo_escano`: duelo por el último escaño de D'Hondt en cada
  provincia (ganador, rival y diferencia relativa de cocientes).
- `deltas` + `cambios.json`: diff contra la corrida anterior publicada.

Uso (tras `forecast.py`):
    /root/.venvs/29n/bin/python pipeline/modelo/provincial.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import yaml

import common as C

sys.path.insert(0, str(C.ROOT / "pipeline" / "interior"))
from dhondt import reparto, ultimo_escano  # noqa: E402

BASE_ELECTION = "2023-07-23"
N_RUNS = 10000
SEED = 20261015
COHERENCE_TOL = 0.1
CALIB_TOL = 0.02
CALIB_MAX_ITER = 20

# Pertenencia editorial a bloques y mayoría absoluta (176 de 350).
BLOQUES_YAML = Path(__file__).with_name("bloques.yaml")
# Tope del log acumulado de cambios entre corridas.
MAX_CAMBIOS = 52


# --------------------------------------------------------------------------- #
def build_base(inter, parties):
    """Cuotas provinciales y nacionales base (universo modelado, suma=100)."""
    prov = inter.provincial_canonical(BASE_ELECTION)
    base_prov = {}
    for code, d in prov.items():
        sub = {p: float(d.get(p, 0.0)) for p in parties}
        tot = sum(sub.values())
        base_prov[code] = {p: 100.0 * v / tot for p, v in sub.items()} if tot else sub
    nat = inter.national_canonical(BASE_ELECTION)
    sub = {p: float(nat.get(p, 0.0)) for p in parties}
    tot = sum(sub.values())
    base_nat = {p: 100.0 * v / tot for p, v in sub.items()}
    return base_prov, base_nat


def ratios_from_target(base_nat, target, parties):
    r = {}
    for p in parties:
        r[p] = (target[p] / base_nat[p]) if base_nat[p] > 0.001 else 0.0
    return r


def provincial_from_ratios(base_prov, r, parties):
    """Aplica los ratios y normaliza a 100 dentro de cada provincia."""
    out = {}
    for code, bp in base_prov.items():
        v = {p: bp[p] * r[p] for p in parties}
        s = sum(v.values())
        out[code] = {p: (100.0 * v[p] / s if s > 0 else 0.0) for p in parties}
    return out


def weighted_agg(prov, w, parties):
    return {p: sum(w[c] * prov[c][p] for c in prov) for p in parties}


def calibrate(base_prov, base_nat, target, parties, w,
              tol=CALIB_TOL, max_iter=CALIB_MAX_ITER):
    """Ajusta los ratios hasta que el agregado provincial = target (≤ tol)."""
    r = ratios_from_target(base_nat, target, parties)
    prov = provincial_from_ratios(base_prov, r, parties)
    dev = float("inf")
    it = 0
    for it in range(1, max_iter + 1):
        agg = weighted_agg(prov, w, parties)
        dev = max(abs(agg[p] - target[p]) for p in parties)
        if dev <= tol:
            break
        for p in parties:
            if base_nat[p] > 0.001 and agg[p] > 1e-6:
                r[p] *= target[p] / agg[p]
        prov = provincial_from_ratios(base_prov, r, parties)
    return prov, r, it, dev


def allocate(prov_shares, valid_votes, escanos, parties, ultimo=None):
    """Reparte escaños provincia a provincia.

    Si se pasa `ultimo` (dict), se rellena con la ficha del último escaño de
    cada provincia: `{codigo: (ganador, rival, diferencia_relativa)}`. La
    escalera se construye una sola vez por provincia y se usa para las dos
    cosas, así que el reparto sigue siendo exactamente el de `dhondt`.
    """
    seats = {}
    for code, sh in prov_shares.items():
        vv = valid_votes[code]
        votes = {p: max(0.0, sh[p]) * vv / 100.0 for p in parties}
        reparto_c, ladder = reparto(votes, escanos[code], C.DHONDT_THRESHOLD, vv)
        seats[code] = reparto_c
        if ultimo is not None:
            ultimo[code] = ultimo_escano(ladder, escanos[code])
    return seats


# --------------------------------------------------------------------------- #
# Bloques, último escaño y deltas (PR-2 de la issue #15)
# --------------------------------------------------------------------------- #
def load_bloques(path=BLOQUES_YAML, parties=None):
    """Carga la pertenencia editorial a bloques desde `bloques.yaml`.

    Valida que los bloques sean disjuntos y que, junto con `fuera_de_bloque`,
    cubran exactamente el universo modelado: si un partido falta o se repite,
    el pipeline se para en vez de publicar una suma incompleta.
    """
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    bloques = {nombre: list(d["partidos"]) for nombre, d in cfg["bloques"].items()}
    mayoria = int(cfg["mayoria_absoluta"])
    fuera = list(cfg.get("fuera_de_bloque", []))

    miembros = [p for ps in bloques.values() for p in ps]
    if len(miembros) != len(set(miembros)):
        raise ValueError(f"bloques.yaml: partido repetido en dos bloques: {miembros}")
    if set(miembros) & set(fuera):
        raise ValueError("bloques.yaml: partido a la vez en bloque y fuera_de_bloque")
    if parties is not None and (set(miembros) | set(fuera)) != set(parties):
        faltan = sorted(set(parties) - (set(miembros) | set(fuera)))
        sobran = sorted((set(miembros) | set(fuera)) - set(parties))
        raise ValueError(
            f"bloques.yaml no cubre MODELED_PARTIES (faltan {faltan}, sobran {sobran})")
    return {"bloques": bloques, "mayoria": mayoria, "fuera": fuera}


def sumas_de_bloque_de_run(tot, idx_bloque):
    """Suma de escaños de cada bloque en una corrida.

    `tot` es el vector nacional de escaños por partido de esa corrida e
    `idx_bloque` la lista de índices de partido de cada bloque (en el orden del
    yaml). Devuelve una lista de enteros, un valor por bloque.
    """
    return [int(tot[idx].sum()) for idx in idx_bloque]


def agregar_bloques(bloque_runs, cfg, mayoria):
    """Agrega las sumas por bloque de todas las corridas.

    Returns
    -------
    (dict, float)
        Por bloque: `{partidos, p_ge176, media, ic95}`; y `p_ninguno`, la
        proporción de corridas en que ningún bloque alcanza la mayoría. Como
        los bloques son disjuntos, `p_izq + p_der + p_ninguno = 1` exacto (las
        tres se redondean a 4 decimales).
    """
    bloque_runs = np.asarray(bloque_runs)
    out = {}
    for j, (nombre, miembros) in enumerate(cfg["bloques"].items()):
        col = bloque_runs[:, j].astype(np.int32)
        out[nombre] = {
            "partidos": list(miembros),
            "p_ge176": round(float((col >= mayoria).mean()), 4),
            "media": round(float(col.mean()), 2),
            "ic95": [int(np.percentile(col, 2.5)), int(np.percentile(col, 97.5))],
        }
    p_ninguno = round(float((bloque_runs < mayoria).all(axis=1).mean()), 4)
    return out, p_ninguno


def agregar_ultimo_escano(ganadores, rivales, diffs, parties):
    """Agrega las series por corrida del último escaño a la ficha publicada.

    Parameters
    ----------
    ganadores, rivales : array de índices de partido (uno por corrida)
    diffs : array float de la diferencia relativa de cocientes de cada corrida
    parties : lista de partidos (índice = posición)

    Returns
    -------
    dict ``{partidos: [A, B], p_a, p_b, diff_medio}``

    A es el partido que gana el último escaño con más frecuencia y B su rival
    más frecuente en esas mismas corridas. `p_a`/`p_b` son frecuencias
    **relativas al duelo** (suman 1 por construcción): cómo se reparten entre A
    y B las corridas en que el escaño cae en uno de los dos. Si un tercer
    partido gana el escaño en alguna corrida, esa corrida no entra en el
    reparto p_a/p_b — el duelo describe a los dos que se lo disputan.
    """
    n_part = len(parties)
    ganadores = np.asarray(ganadores)
    rivales = np.asarray(rivales)
    diffs = np.asarray(diffs, dtype=float)

    victorias = np.bincount(ganadores, minlength=n_part)
    # Partido que gana más veces (empate → orden de `parties`).
    a = max(range(n_part), key=lambda i: (int(victorias[i]), -i))

    en_a = ganadores == a
    duelos = np.bincount(rivales[en_a], minlength=n_part) if en_a.any() else np.zeros(n_part)
    duelos[a] = 0
    b = max(range(n_part), key=lambda i: (int(duelos[i]), -i)) if duelos.any() else a

    denom = int(victorias[a]) + int(victorias[b])
    if denom <= 0:
        p_a = 1.0
    else:
        p_a = round(int(victorias[a]) / denom, 4)
    p_b = round(1.0 - p_a, 4)

    if a == b:
        diff_medio = 0.0
    else:
        sel = en_a & (rivales == b)
        if not sel.any():
            sel = en_a
        diff_medio = round(float(diffs[sel].mean()), 4)

    return {"partidos": [parties[a], parties[b]], "p_a": p_a, "p_b": p_b,
            "diff_medio": diff_medio}


def leer_corrida_previa(path):
    """seats.json de la corrida anterior, o None si no hay (no se inventa)."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        prev = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(prev, dict) or "nacional" not in prev:
        return None
    return prev


def calcular_deltas(prev, nacional, bloques, p_ninguno):
    """Diff contra la corrida anterior publicada.

    `nacional`: delta entero de `central_escenario` por partido.
    `bloques`: delta de `p_ge176` por bloque en puntos porcentuales (1 decimal).
    Sin corrida anterior → `{}` (ningún delta inventado).
    """
    if not prev:
        return {}
    deltas_nac = {}
    for p, d in nacional.items():
        antes = (prev.get("nacional") or {}).get(p)
        if antes is not None and antes.get("central_escenario") is not None:
            deltas_nac[p] = int(d["central_escenario"]) - int(antes["central_escenario"])
    prev_bloques = prev.get("bloques") or {}
    deltas_blo = {}
    for nombre, d in bloques.items():
        antes = prev_bloques.get(nombre) or {}
        if antes.get("p_ge176") is not None:
            deltas_blo[nombre] = round(100.0 * (d["p_ge176"] - antes["p_ge176"]), 1)
    if prev_bloques.get("p_ninguno") is not None:
        deltas_blo["p_ninguno"] = round(100.0 * (p_ninguno - prev_bloques["p_ninguno"]), 1)
    return {"contra": (prev.get("meta") or {}).get("generado"),
            "nacional": deltas_nac, "bloques": deltas_blo}


def actualizar_cambios(path, generado, deltas):
    """Appende (o sustituye) la entrada de esta corrida en el log acumulado.

    Idempotente por `generado`: dos corridas del mismo día dejan una sola
    entrada, la última. Tope de 52 entradas (se descartan las más antiguas).
    """
    path = Path(path)
    log = []
    if path.exists():
        try:
            cargado = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(cargado, list):
                log = cargado
        except (OSError, json.JSONDecodeError):
            log = []
    entrada = {
        "generado": generado,
        "deltas_nacional": deltas.get("nacional", {}),
        "deltas_bloques": deltas.get("bloques", {}),
    }
    log = [e for e in log if e.get("generado") != generado]
    log.append(entrada)
    log = log[-MAX_CAMBIOS:]
    path.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    return log


# --------------------------------------------------------------------------- #
def main() -> int:
    obs = C.Observations()
    inter = C.Interior()
    parties = C.MODELED_PARTIES

    fc = json.loads((C.DATA / "modelo" / "forecast_state.json").read_text(encoding="utf-8"))
    target = {p: fc["partidos"][p]["punto"] for p in parties}
    sigma = {p: fc["partidos"][p]["sd_error_backtest"] for p in parties}

    base_prov, base_nat = build_base(inter, parties)
    valid_votes = inter.valid_votes(BASE_ELECTION)
    escanos = inter.seats(BASE_ELECTION)
    names = {p["codigo"]: p["nombre"] for p in inter.provinces(BASE_ELECTION)}
    total_vv = sum(valid_votes.values())
    w = {c: valid_votes[c] / total_vv for c in valid_votes}

    # --- Bloques (pertenencia editorial versionada) -------------------------
    cfg_bloques = load_bloques(parties=parties)
    nombres_bloques = list(cfg_bloques["bloques"])
    mayoria = cfg_bloques["mayoria"]
    pidx = {p: i for i, p in enumerate(parties)}
    idx_bloque = [np.array([pidx[p] for p in ps], dtype=np.intp)
                  for ps in cfg_bloques["bloques"].values()]

    # --- Escenario central --------------------------------------------------
    prov_shares, ratios, calib_iters, calib_dev = calibrate(
        base_prov, base_nat, target, parties, w)
    central_seats = allocate(prov_shares, valid_votes, escanos, parties)

    coherence_votes = {p: weighted_agg(prov_shares, w, parties)[p] - target[p]
                       for p in parties}
    max_dev_votes = max(abs(v) for v in coherence_votes.values())

    # --- Simulación ---------------------------------------------------------
    rng = np.random.default_rng(SEED)
    n_p = len(parties)
    mu = np.array([target[p] for p in parties])
    sd = np.array([sigma[p] for p in parties])
    seats_runs = {c: np.zeros((N_RUNS, n_p), dtype=np.int16) for c in base_prov}
    national_runs = np.zeros((N_RUNS, n_p), dtype=np.int32)
    bloque_runs = np.zeros((N_RUNS, len(nombres_bloques)), dtype=np.int16)
    # Último escaño por provincia y corrida (índice de partido + diferencia).
    ult_win = {c: np.zeros(N_RUNS, dtype=np.int16) for c in base_prov}
    ult_riv = {c: np.zeros(N_RUNS, dtype=np.int16) for c in base_prov}
    ult_diff = {c: np.zeros(N_RUNS, dtype=np.float32) for c in base_prov}

    for r_ in range(N_RUNS):
        draw = np.clip(rng.normal(mu, sd), 0.0, None)
        s = draw.sum()
        draw = draw * (100.0 / s) if s > 0 else draw
        tgt = {p: float(draw[i]) for i, p in enumerate(parties)}
        ps, _, _, _ = calibrate(base_prov, base_nat, tgt, parties, w,
                                tol=0.08, max_iter=12)
        ult = {}
        alloc = allocate(ps, valid_votes, escanos, parties, ultimo=ult)
        tot = np.zeros(n_p, dtype=np.int32)
        for c in alloc:
            fila = [alloc[c][p] for p in parties]
            seats_runs[c][r_, :] = fila
            tot += fila
            a, b, d = ult[c]
            ult_win[c][r_] = pidx[a]
            ult_riv[c][r_] = pidx[b]
            ult_diff[c][r_] = d
        national_runs[r_, :] = tot
        for j, suma in enumerate(sumas_de_bloque_de_run(tot, idx_bloque)):
            bloque_runs[r_, j] = suma

    # --- Agregados ----------------------------------------------------------
    prov_out = {}
    for c, arr in seats_runs.items():
        d = {}
        for i, p in enumerate(parties):
            col = arr[:, i]
            d[p] = {
                "media": round(float(col.mean()), 2),
                "ic95": [int(np.percentile(col, 2.5)), int(np.percentile(col, 97.5))],
                "prob_ge1": round(float((col >= 1).mean()), 3),
            }
        prov_out[c] = {
            "nombre": names.get(int(c), str(c)),
            "escanos": escanos[c],
            "partidos": d,
            "ultimo_escano": agregar_ultimo_escano(
                ult_win[c], ult_riv[c], ult_diff[c], parties),
        }

    national = {}
    for i, p in enumerate(parties):
        col = national_runs[:, i]
        national[p] = {
            "media": round(float(col.mean()), 2),
            "ic95": [int(np.percentile(col, 2.5)), int(np.percentile(col, 97.5))],
            "p_ge1": round(float((col >= 1).mean()), 3),
            "central_escenario": sum(central_seats[c][p] for c in central_seats),
        }

    bloques, p_ninguno = agregar_bloques(bloque_runs, cfg_bloques, mayoria)

    # --- Deltas contra la corrida anterior publicada ------------------------
    seats_path = C.DATA / "modelo" / "seats.json"
    cambios_path = C.DATA / "modelo" / "cambios.json"
    prev = leer_corrida_previa(seats_path)
    deltas = calcular_deltas(prev, national, bloques, p_ninguno)
    bloques["p_ninguno"] = p_ninguno
    bloques["deltas_vs_prev"] = (deltas.get("bloques") or {})

    sum_media = sum(v["media"] for v in national.values())

    meta = {
        "generado": date.today().isoformat(),
        "objetivo": "29N 2026-11-29",
        "base_provincial": BASE_ELECTION,
        "metodo": "swing proporcional uniforme desde 23J + calibración + D'Hondt",
        "n_runs": N_RUNS,
        "seed": SEED,
        "ratios_swing_calibrados": {p: round(ratios[p], 4) for p in parties},
        "calibracion": {"iteraciones": calib_iters, "desviacion_max_pp": round(calib_dev, 4)},
        "coherencia": {
            "suma_medias_escanos": round(sum_media, 3),
            "total_escanos": 350,
            "desviacion_escanos": round(sum_media - 350, 3),
            "tolerancia": COHERENCE_TOL,
            "ok_escanos": abs(sum_media - 350) <= COHERENCE_TOL,
            "max_desviacion_votos_pp": round(max_dev_votes, 4),
            "ok_votos": max_dev_votes <= COHERENCE_TOL,
        },
        "advertencia": (
            "Swing proporcional uniforme: no modela terremotos locales ni "
            "elasticidades provinciales distintas. Intervalos provinciales de "
            "partidos pequeños muy anchos (diseño honesto)."
        ),
    }

    out = {"meta": meta, "bloques": bloques, "nacional": national,
           "provincias": prov_out, "deltas": deltas}
    with open(seats_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    actualizar_cambios(cambios_path, meta["generado"], deltas)

    print(f"OK seats.json — {N_RUNS} runs, {len(prov_out)} provincias, "
          f"calibración {calib_iters} it (dev {calib_dev:.4f} pp)")
    print("  Escaños (media, IC95):")
    for p in sorted(national, key=lambda x: -national[x]["media"]):
        n = national[p]
        print(f"    {p:8s} {n['media']:6.1f}  IC95=[{n['ic95'][0]:3d},{n['ic95'][1]:3d}]  "
              f"(central={n['central_escenario']})")
    print(f"  Coherencia escaños: suma={sum_media:.2f} "
          f"(ok={meta['coherencia']['ok_escanos']})")
    print(f"  Coherencia votos:   max dev={max_dev_votes:.4f} pp "
          f"(ok={meta['coherencia']['ok_votos']})")
    print("  Bloques (P(≥176), media, IC95):")
    for b in nombres_bloques:
        x = bloques[b]
        print(f"    {b:10s} p_ge176={x['p_ge176']:.4f}  media={x['media']:6.1f}  "
              f"IC95=[{x['ic95'][0]:3d},{x['ic95'][1]:3d}]  "
              f"({', '.join(x['partidos'])})")
    print(f"    ninguno    p_ge176={p_ninguno:.4f}")
    if deltas:
        print(f"  Deltas vs corrida {deltas.get('contra')}: "
              f"bloques={deltas.get('bloques')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
