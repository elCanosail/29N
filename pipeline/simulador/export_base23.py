#!/usr/bin/env python3
"""Fase 5 — Exportación de la base provincial 23J para el simulador «¿qué pasaría si…?».

Lee `data/processed/interior/results_provincial.jsonl` (solo lectura) y escribe
`web/src/data/base23.json`: la base provincial de la última elección (23J-2023),
por provincia, con

  - los escaños en juego en la circunscripción,
  - los votos válidos reales (peso de la provincia en la calibración del swing),
  - el reparto de voto por partido **sobre voto válido y renormalizado al
    universo modelado de 13 partidos** (la misma base con la que el modelo de
    `pipeline/modelo/` reparte los escaños).

Estructura compacta pensada para el cliente (D'Hondt en JavaScript):

    {
      "meta": { ... },
      "partidos": ["PP", "PSOE", ...],          # 13, orden del universo modelado
      "provincias": [
        {"codigo": 1, "nombre": "Araba/Álava", "escanos": 4, "validos": 169107,
         "pct": {"PP": 12.34, "PSOE": 25.10, ...}}   # suma 100 por provincia
      ]
    }

Canonicalización — coherencia con el modelo (regla del proyecto: la base del
simulador debe ser la MISMA con la que se calcula `seats.json`, o el escenario
central del simulador no coincidiría con el del modelo):

  - `pipeline/interior/partidos_aliases.json` es el diccionario canónico del
    pipeline de Interior (siglas/alias -> id canónico). El modelo de predicción
    lo replica en `pipeline/sesgo/party_canon.py` (con las coaliciones
    dependientes de la era resueltas por elección).
  - `pipeline/modelo/common.py` (importado aquí en modo lectura) aplica además
    las familias del universo modelado: plegado IU/Podemos/Unidas Podemos ->
    SUMAR y la corrección UPN (`u-p-n`) -> NA+. Usamos `common.canon_slug()`
    para que la base sea idéntica a la que usa `provincial.py`.
  - `partidos.json` se lee para documentar en `meta` el nombre/sigla oficiales
    de cada candidatura fusionada.

Verificación (se imprime al ejecutar): con la base exportada, el forecast
estatal puntual y la misma calibración de punto fijo que `provincial.py`, el
reparto D'Hondt resultante debe reproducir el escenario central de
`seats.json` (suma 350 escaños).

Uso:
    /root/.venvs/29n/bin/python pipeline/simulador/export_base23.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"
SALIDA = ROOT / "web" / "src" / "data" / "base23.json"

# Import en modo lectura del modelo: canonicalización + D'Hondt + datos Interior.
sys.path.insert(0, str(ROOT / "pipeline" / "modelo"))
import common as C  # noqa: E402

sys.path.insert(0, str(ROOT / "pipeline" / "interior"))
from dhondt import dhondt  # noqa: E402

BASE_ELECTION = "2023-07-23"
# Orden del universo modelado (mismo que PARTIDOS de sync-data.py y forecast.json).
PARTIDOS = [
    "PP", "PSOE", "VOX", "SUMAR", "EH BILDU", "ERC", "JXCAT",
    "PNV", "BNG", "NA+", "CUP", "CC", "PACMA",
]
# Tolerancias copiadas de pipeline/modelo/provincial.py (misma calibración).
CALIB_TOL = 0.02
CALIB_MAX_ITER = 20


def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_base(inter: "C.Interior"):
    """Cuotas provinciales renormalizadas al universo modelado (suma 100)."""
    prov = inter.provincial_canonical(BASE_ELECTION)
    out = {}
    for code, d in prov.items():
        sub = {p: float(d.get(p, 0.0)) for p in PARTIDOS}
        tot = sum(sub.values())
        out[code] = {p: 100.0 * v / tot for p, v in sub.items()} if tot else sub
    return out


def base_national(base_prov, valid_votes):
    """Cuota nacional del universo modelado, ponderada por votos válidos."""
    total = sum(valid_votes.values())
    return {
        p: sum(base_prov[c][p] * valid_votes[c] / total for c in base_prov)
        for p in PARTIDOS
    }


# --- Réplica exacta de la calibración de provincial.py (punto fijo) --------
def ratios_from_target(base_nat, target):
    return {p: (target[p] / base_nat[p]) if base_nat[p] > 0.001 else 0.0
            for p in PARTIDOS}


def provincial_from_ratios(base_prov, r):
    out = {}
    for code, bp in base_prov.items():
        v = {p: bp[p] * r[p] for p in PARTIDOS}
        s = sum(v.values())
        out[code] = {p: (100.0 * v[p] / s if s > 0 else 0.0) for p in PARTIDOS}
    return out


def weighted_agg(prov, w):
    return {p: sum(w[c] * prov[c][p] for c in prov) for p in PARTIDOS}


def calibrate(base_prov, base_nat, target, w,
              tol=CALIB_TOL, max_iter=CALIB_MAX_ITER):
    r = ratios_from_target(base_nat, target)
    prov = provincial_from_ratios(base_prov, r)
    dev, it = float("inf"), 0
    for it in range(1, max_iter + 1):
        agg = weighted_agg(prov, w)
        dev = max(abs(agg[p] - target[p]) for p in PARTIDOS)
        if dev <= tol:
            break
        for p in PARTIDOS:
            if base_nat[p] > 0.001 and agg[p] > 1e-6:
                r[p] *= target[p] / agg[p]
        prov = provincial_from_ratios(base_prov, r)
    return prov, r, it, dev


def allocate(prov_shares, valid_votes, escanos):
    seats = {}
    for code, sh in prov_shares.items():
        vv = valid_votes[code]
        votes = {p: max(0.0, sh[p]) * vv / 100.0 for p in PARTIDOS}
        seats[code] = dhondt(votes, escanos[code], C.DHONDT_THRESHOLD, vv)
    return seats


def main() -> int:
    inter = C.Interior()
    base_prov = build_base(inter)
    valid_votes = inter.valid_votes(BASE_ELECTION)
    escanos = inter.seats(BASE_ELECTION)
    nombres = {p["codigo"]: p["nombre"] for p in inter.provinces(BASE_ELECTION)}

    # Documentación: nombres/siglas oficiales de las candidaturas fusionadas.
    partidos_meta = load_json(DATA / "interior" / "partidos.json")["partidos"]
    aliases = load_json(ROOT / "pipeline" / "interior" / "partidos_aliases.json")["partidos"]

    # --- Verificación contra seats.json (escenario central) -----------------
    forecast = load_json(DATA / "modelo" / "forecast_state.json")
    target = {p: forecast["partidos"][p]["punto"] for p in PARTIDOS}
    total_vv = sum(valid_votes.values())
    w = {c: valid_votes[c] / total_vv for c in valid_votes}
    base_nat = base_national(base_prov, valid_votes)
    prov_shares, ratios, iters, dev = calibrate(base_prov, base_nat, target, w)
    central = allocate(prov_shares, valid_votes, escanos)

    seats_ref = load_json(DATA / "modelo" / "seats.json")
    # seats.json guarda `nacional` como {partido: {...}} (ver provincial.py).
    ref = {p: v["central_escenario"] for p, v in seats_ref["nacional"].items()}
    central_total = {p: sum(central[c][p] for c in central) for p in PARTIDOS}
    diffs = {p: central_total[p] - ref.get(p, 0) for p in PARTIDOS}

    # --- Escritura ----------------------------------------------------------
    provincias = []
    for code in sorted(valid_votes):
        pct = {p: round(float(base_prov[code][p]), 2) for p in PARTIDOS}
        provincias.append({
            "codigo": int(code),
            "nombre": nombres.get(code, str(code)),
            "escanos": int(escanos[code]),
            "validos": int(valid_votes[code]),
            "pct": pct,
        })

    salida = {
        "meta": {
            "eleccion": BASE_ELECTION,
            "fecha": BASE_ELECTION,
            "fuente": "Ministerio del Interior — resultados provinciales del Congreso",
            "base": "% sobre votos válidos provinciales, renormalizado al universo modelado",
            "universo_modelado": PARTIDOS,
            "universo_cobertura_23J_pct": 97.955,
            "canonicalizacion": (
                "partidos_aliases.json (diccionario canónico de Interior) + familias "
                "del modelo (IU/Podemos/UP -> SUMAR; UPN 'u-p-n' -> NA+) via "
                "pipeline/modelo/common.py"
            ),
            "n_provincias": len(provincias),
            "total_escanos": sum(escanos.values()),
            "nota": (
                "Base provincial del reparto 29N: cada provincia suma 100 en el universo "
                "modelado (13 partidos, ~98 % del voto válido de 23J). El residual no "
                "entra en D'Hondt: los minoritarios no se reparten escaños, como en el "
                "modelo provincial."
            ),
            "siglas": {p: (aliases.get(p.lower(), {}).get("nombre")
                           or partidos_meta.get(p.lower(), {}).get("nombre") or p)
                       for p in PARTIDOS},
        },
        "partidos": PARTIDOS,
        # Punto exacto del modelo (3 decimales), tal cual `forecast_state.json`.
        # El `forecast.json` de la web lo publica redondeado a 2 decimales; ese
        # redondeo basta para mover UN escaño en la frontera PSOE/PNV (29,15 vs
        # 29,146 en 23J-2026). Para que el simulador, partiendo del punto, sea
        # EXACTAMENTE el escenario central de `seats.json`, el valor inicial de
        # los controles usa esta referencia precisa.
        "punto_modelo": {p: round(float(target[p]), 3) for p in PARTIDOS},
        "provincias": provincias,
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    size = SALIDA.stat().st_size
    print(f"OK {SALIDA.relative_to(ROOT)} — {len(provincias)} provincias, "
          f"{size} bytes")
    print(f"  Calibración (verificación): {iters} iteraciones, desv {dev:.4f} pp")
    print("  Comprobación escenario central (simulador vs seats.json):")
    print(f"    suma de escaños = {sum(central_total.values())}")
    ok = True
    for p in sorted(PARTIDOS, key=lambda x: -central_total[x]):
        flag = "" if diffs[p] == 0 else f"  <-- dif {diffs[p]:+d}"
        if diffs[p] != 0:
            ok = False
        print(f"    {p:9s} {central_total[p]:3d}  (modelo {ref.get(p, 0):3d}){flag}")
    print(f"  Escenario central reproducido exactamente: {'SÍ' if ok else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
