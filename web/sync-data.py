#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-data.py — copia y transforma los datos del pipeline a `web/src/data/`.

La web es 100 % estática y NO calcula nada (decisión en docs/plan.md): este
script es el único puente entre `data/processed/` (fuente de verdad, solo
lectura) y los JSON que Astro importa en tiempo de build.

Regenerar:

    /root/.venvs/29n/bin/python web/sync-data.py

o, si no existiera ese entorno:

    python3 web/sync-data.py

El script es idempotente y determinista (sin aleatoriedad, sin fechas del
sistema): dos ejecuciones seguidas producen byte a byte el mismo resultado
salvo que cambie la entrada. No toca `data/processed/`, `pipeline/` ni la web
más allá de escribir en `web/src/data/`.

Salidas (todas en `web/src/data/`):

    forecast.json      predicción estatal 29N (punto + cuantiles por partido)
    seats.json         escaños nacionales y por provincia (media + IC95)
    backtest.json      MAE por partido y por elección (veredicto sin maquillar)
    series.json        serie mensual ponderada 2015-01 → 2026-11 (13 partidos)
    elecciones.json    resultados nacionales oficiales de las 16 generales
    encuestas.json     catálogo de encuestas (CIS + privados) con su ficha
    exclusiones.json   log público de exclusiones (CIS + encuestadores)
    sesgo.json         efectos de casa y correcciones EB (fase 4-bis)

Cada fichero lleva su bloque `meta` con origen, fecha de generación del dato y
advertencias, para que la web pueda citarlas y enlazarlas sin inventar nada.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(RAIZ, "data", "processed")
SALIDA = os.path.join(RAIZ, "web", "src", "data")

P_MODELO = os.path.join(PROC, "modelo")
P_INTERIOR = os.path.join(PROC, "interior")
P_CIS = os.path.join(PROC, "cis")
P_ENC = os.path.join(PROC, "encuestadores")
P_SESGO = os.path.join(PROC, "sesgo")

# Partidos del universo modelado (13). Orden canónico por tamaño esperado.
PARTIDOS = [
    "PP", "PSOE", "VOX", "SUMAR", "EH BILDU", "ERC", "JXCAT",
    "PNV", "BNG", "NA+", "CUP", "CC", "PACMA",
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def leer_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def leer_jsonl(path: str) -> list[dict]:
    filas = []
    with open(path, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if linea:
                filas.append(json.loads(linea))
    return filas


def escribir(nombre: str, datos: Any) -> int:
    """Escribe un JSON compacto y legible (indent=1) y devuelve sus bytes."""
    ruta = os.path.join(SALIDA, nombre)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")
    return os.path.getsize(ruta)


def red(v: Any, dec: int = 2) -> Any:
    """Redondea recursivamente números a `dec` decimales (None-safe)."""
    if isinstance(v, float):
        return round(v, dec)
    if isinstance(v, dict):
        return {k: red(x, dec) for k, x in v.items()}
    if isinstance(v, list):
        return [red(x, dec) for x in v]
    return v


def iso_desde_ddmmyyyy(txt: str | None) -> str | None:
    """'01/06/1977' → '1977-06-01'. Devuelve None si no encaja."""
    if not txt:
        return None
    partes = txt.split("/")
    if len(partes) == 3 and len(partes[2]) == 4:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return txt


def anio_de_fecha(txt: str | None) -> int | None:
    """Extrae el año de 'YYYY-MM-DD...', 'DD/MM/YYYY' o 'YYYY-MM-DD/YYYY-MM-DD'."""
    if not txt:
        return None
    if "/" in txt and txt.count("/") == 2 and txt[:4].isdigit() is False:
        # DD/MM/YYYY
        return int(txt[-4:]) if txt[-4:].isdigit() else None
    trozo = txt.split("/")[0]
    return int(trozo[:4]) if trozo[:4].isdigit() else None


# ---------------------------------------------------------------------------
# 1. Predicción estatal
# ---------------------------------------------------------------------------

def gen_forecast() -> int:
    src = leer_json(os.path.join(P_MODELO, "forecast_state.json"))
    meta = src["meta"]
    partidos = []
    for nombre, d in src["partidos"].items():
        q = d.get("cuantiles", {})
        partidos.append({
            "partido": nombre,
            "punto": round(d["punto"], 2),
            "p10": round(q.get("0.1", d["punto"]), 2),
            "p20": round(q.get("0.2", d["punto"]), 2),
            "p50": round(q.get("0.5", d["punto"]), 2),
            "p80": round(q.get("0.8", d["punto"]), 2),
            "p90": round(q.get("0.9", d["punto"]), 2),
            "sd_error_backtest": round(d.get("sd_error_backtest", 0.0), 2),
            "punto_timesfm": round(d.get("punto_timesfm", d["punto"]), 2),
        })
    partidos.sort(key=lambda x: -x["punto"])
    datos = {
        "meta": {
            "generado": meta.get("generado"),
            "objetivo": meta.get("objetivo"),
            "mes_predicho": meta.get("mes_predicho"),
            "ultimo_mes_con_dato": meta.get("ultimo_mes_con_dato"),
            "metodo_primario": meta.get("metodo_primario"),
            "motivo_metodo": meta.get("motivo_metodo"),
            "backtest_mae": meta.get("backtest_mae"),
            "intervalos": meta.get("intervalos"),
            "normalizacion": meta.get("normalizacion"),
            "timesfm": meta.get("timesfm"),
            "advertencia": meta.get("advertencia"),
        },
        "partidos": partidos,
    }
    return escribir("forecast.json", datos)


# ---------------------------------------------------------------------------
# 2. Escaños (nacional + provincias)
# ---------------------------------------------------------------------------

def gen_seats() -> int:
    src = leer_json(os.path.join(P_MODELO, "seats.json"))

    nacional = []
    for nombre, d in src["nacional"].items():
        nacional.append({
            "partido": nombre,
            "media": round(d["media"], 2),
            "ic95": list(d["ic95"]),
            "p_ge1": round(d.get("prob_ge1", d.get("p_ge1", 0.0)), 3),
            "central_escenario": d.get("central_escenario"),
        })
    nacional.sort(key=lambda x: -x["media"])

    provincias = []
    for codigo, p in src["provincias"].items():
        filas = []
        for nombre, d in p["partidos"].items():
            prob = d.get("prob_ge1", d.get("p_ge1", 0.0))
            if d.get("media", 0) <= 0 and prob <= 0:
                continue
            filas.append({
                "partido": nombre,
                "media": round(d["media"], 2),
                "ic95": list(d["ic95"]),
                "p_ge1": round(prob, 3),
            })
        filas.sort(key=lambda x: -x["media"])
        ganador = filas[0]["partido"] if filas else "OTROS"
        provincias.append({
            "codigo": int(codigo),
            "nombre": p["nombre"],
            "escanos": p["escanos"],
            "ganador": ganador,
            "partidos": filas,
        })
    provincias.sort(key=lambda x: x["codigo"])

    datos = {
        "meta": src["meta"],
        "nacional": nacional,
        "provincias": provincias,
    }
    return escribir("seats.json", datos)


# ---------------------------------------------------------------------------
# 3. Backtest
# ---------------------------------------------------------------------------

def gen_backtest() -> int:
    src = leer_json(os.path.join(P_MODELO, "backtest.json"))
    por_eleccion = {}
    for fecha, bloque in src["por_eleccion"].items():
        filas = {}
        for partido, d in bloque["partidos"].items():
            ts = d.get("ts_interval_80", {})
            filas[partido] = {
                "pred_timesfm": round(d["pred_timesfm"], 2),
                "pred_baseline": round(d["pred_baseline"], 2),
                "pred_ensemble": round(d["pred_ensemble"], 2),
                "real": round(d["real"], 2),
                "err_timesfm": round(d["err_timesfm"], 2),
                "err_baseline": round(d["err_baseline"], 2),
                "err_ensemble": round(d["err_ensemble"], 2),
                "ts_p10": round(ts.get("0.1", d["pred_timesfm"]), 2),
                "ts_p50": round(ts.get("0.5", d["pred_timesfm"]), 2),
                "ts_p90": round(ts.get("0.9", d["pred_timesfm"]), 2),
            }
        por_eleccion[fecha] = {
            "partidos": filas,
            "historia_meses": bloque.get("historia_meses"),
            "cobertura_universo_pct": bloque.get("cobertura_universo_pct"),
        }
    datos = {
        "generado": src["generado"],
        "elecciones": src["elecciones"],
        "metrica": src["metrica"],
        "cobertura_universo_pct_por_eleccion": src["cobertura_universo_pct_por_eleccion"],
        "n_observaciones_mae": src["n_observaciones_mae"],
        "mae_global": src["mae_global"],
        "mae_por_partido": src["mae_por_partido"],
        "baseline_error_distribution": src["baseline_error_distribution"],
        "por_eleccion": por_eleccion,
    }
    return escribir("backtest.json", red(datos))


# ---------------------------------------------------------------------------
# 4. Serie mensual (ventana reciente)
# ---------------------------------------------------------------------------

def gen_series(desde: str = "2015-01") -> int:
    """Serie mensual en formato columnar compacto desde `desde` (inclusive)."""
    meses_set: set[str] = set()
    valores: dict[str, dict[str, float]] = {p: {} for p in PARTIDOS}
    with open(os.path.join(P_MODELO, "series.csv"), encoding="utf-8") as fh:
        cabecera = fh.readline()
        for linea in fh:
            mes, partido, valor = linea.rstrip("\n").split(",")
            if mes[:7] < desde:
                continue
            if partido not in valores:
                continue
            meses_set.add(mes[:7])
            valores[partido][mes[:7]] = round(float(valor), 2)
    meses = sorted(meses_set)
    series = {p: [valores[p].get(m, 0.0) for m in meses] for p in PARTIDOS}
    datos = {
        "meta": {
            "origen": "data/processed/modelo/series.csv",
            "ventana": [meses[0], meses[-1]] if meses else [],
            "unidad": "% sobre voto válido (media ponderada de encuestas)",
            "nota": "Promedio ponderado de encuestas; NO es un resultado oficial ni una predicción.",
        },
        "meses": meses,
        "series": series,
    }
    return escribir("series.json", datos)


# ---------------------------------------------------------------------------
# 5. Resultados oficiales (16 generales)
# ---------------------------------------------------------------------------

def gen_elecciones() -> int:
    src = leer_json(os.path.join(P_INTERIOR, "elections.json"))
    partidos_meta = leer_json(os.path.join(P_INTERIOR, "partidos.json"))["partidos"]

    elecciones = []
    for el in src["elecciones"]:
        validos = sum(p.get("votos_validos", 0) for p in el["provincias"])
        cands = []
        for c in el["partidos"]:
            pid = c["partido_id"]
            info = partidos_meta.get(pid, {})
            siglas = (info.get("siglas") or [None])[0]
            cands.append({
                "partido_id": pid,
                "nombre": info.get("nombre", pid.upper()),
                "sigla": siglas or pid.upper(),
                "votos": c["votos"],
                "escanos": c["escanos"],
                "pct": round(100.0 * c["votos"] / validos, 2) if validos else 0.0,
            })
        cands.sort(key=lambda x: -x["votos"])
        elecciones.append({
            "id": el["id"],
            "fecha": el["fecha"],
            "camara": el["camara"],
            "escanos_totales": el["escanos_totales"],
            "votos_validos": validos,
            "candidaturas": cands,
        })

    datos = {
        "meta": {
            "generado": src.get("generado"),
            "fuente": src.get("fuente", {}).get("ministerio"),
            "nota": "Candidaturas tal y como las publica el Ministerio del Interior; sin agrupar por familia.",
        },
        "elecciones": elecciones,
    }
    return escribir("elecciones.json", datos)


# ---------------------------------------------------------------------------
# 6. Catálogo de encuestas (CIS + privados)
# ---------------------------------------------------------------------------

# Partidos que la tabla muestra en columnas propias; el resto va en el JSON.
DESTACADOS = ["PP", "PSOE", "VOX", "SUMAR", "ERC", "EH BILDU", "JXCAT", "PNV", "BNG"]


def _normaliza_siglas_cis(partido: str) -> str:
    """CIS usa nombres largos; se conservan. Solo se unifica el blanco/nulo."""
    return partido


def gen_encuestas() -> int:
    encuestas: list[dict] = []

    # --- CIS (voto directo, % sobre censo) ---
    estudios = {e["estudio"]: e for e in leer_json(os.path.join(P_CIS, "studies.json"))}
    agrupado_cis: dict[str, dict] = {}
    for fila in leer_jsonl(os.path.join(P_CIS, "polls.jsonl")):
        eid = fila["estudio_id"]
        reg = agrupado_cis.setdefault(eid, {
            "id": f"CIS-{eid}",
            "casa": "CIS",
            "tipo": fila.get("tipo"),
            "ambito": fila.get("ambito"),
            "eleccion": fila.get("eleccion"),
            "anio": fila.get("anio"),
            "fecha_trabajo": iso_desde_ddmmyyyy(fila.get("fecha_trabajo")),
            "fecha_publicacion": None,
            "n": fila.get("n"),
            "url": fila.get("fuente_url"),
            "metodologia": None,
            "base": "censo",
            "partidos": {},
        })
        if not reg["n"] and fila.get("n"):
            reg["n"] = fila["n"]
        reg["partidos"][_normaliza_siglas_cis(fila["partido"])] = round(fila["voto_pct"], 2)
        est = estudios.get(eid)
        if est and est.get("url"):
            reg["url"] = est["url"]
        if est and est.get("fecha_trabajo") and not reg["fecha_trabajo"]:
            reg["fecha_trabajo"] = iso_desde_ddmmyyyy(est["fecha_trabajo"])
        if est and reg["anio"] is None:
            reg["anio"] = est.get("anio")
    encuestas.extend(agrupado_cis.values())

    # --- Encuestadores privados (% sobre voto válido) ---
    agrupado_enc: dict[str, dict] = {}
    for fila in leer_jsonl(os.path.join(P_ENC, "polls.jsonl")):
        eid = fila["estudio_id"]
        reg = agrupado_enc.setdefault(eid, {
            "id": eid,
            "casa": fila.get("fuente"),
            "tipo": fila.get("fuente_tipo"),
            "ambito": fila.get("ambito"),
            "eleccion": fila.get("eleccion"),
            "anio": anio_de_fecha(fila.get("fecha_publicacion") or fila.get("fecha_trabajo")),
            "fecha_trabajo": fila.get("fecha_trabajo"),
            "fecha_publicacion": fila.get("fecha_publicacion"),
            "n": fila.get("n"),
            "url": fila.get("fuente_url"),
            "metodologia": fila.get("metodologia"),
            "base": "valido",
            "partidos": {},
        })
        if fila.get("partido_canonico"):
            reg["partidos"][fila["partido_canonico"]] = round(fila["porcentaje"], 2)
    encuestas.extend(agrupado_enc.values())

    # Orden: más reciente primero (por fecha de publicación o de campo).
    def clave_orden(e: dict) -> str:
        return str(e.get("fecha_publicacion") or e.get("fecha_trabajo") or "")
    encuestas.sort(key=clave_orden, reverse=True)

    casas = sorted({e["casa"] for e in encuestas if e.get("casa")})
    anios = sorted({e["anio"] for e in encuestas if e.get("anio")})
    elecciones_dim = sorted({str(e["eleccion"]) for e in encuestas if e.get("eleccion")})

    datos = {
        "meta": {
            "n": len(encuestas),
            "n_cis": len(agrupado_cis),
            "n_privados": len(agrupado_enc),
            "nota_base": (
                "CIS = voto directo sobre censo (microdato); privados = estimación "
                "sobre voto válido. No son directamente comparables sin normalizar."
            ),
            "destacados": DESTACADOS,
        },
        "dimensiones": {"casas": casas, "anios": anios, "elecciones": elecciones_dim},
        "encuestas": encuestas,
    }
    return escribir("encuestas.json", datos)


# ---------------------------------------------------------------------------
# 7. Log de exclusiones
# ---------------------------------------------------------------------------

def gen_exclusiones() -> int:
    entradas: list[dict] = []

    for e in leer_json(os.path.join(P_CIS, "exclusions.json")):
        entradas.append({
            "origen": "CIS",
            "id": f"CIS-{e.get('estudio')}" if e.get("estudio") else None,
            "casa": "CIS",
            "slug": e.get("slug"),
            "tipo": e.get("tipo"),
            "eleccion": e.get("eleccion"),
            "motivo": e.get("motivo"),
            "url": None,
        })

    for e in leer_json(os.path.join(P_ENC, "exclusions.json")):
        entradas.append({
            "origen": "encuestadores",
            "id": e.get("estudio_id"),
            "casa": e.get("fuente"),
            "slug": e.get("archivo"),
            "tipo": None,
            "eleccion": None,
            "motivo": e.get("motivo"),
            "url": e.get("url"),
        })

    datos = {
        "meta": {
            "n": len(entradas),
            "n_cis": sum(1 for e in entradas if e["origen"] == "CIS"),
            "n_privados": sum(1 for e in entradas if e["origen"] == "encuestadores"),
            "nota": "Una encuesta que no pasa validación no desaparece: se documenta con su motivo.",
        },
        "exclusiones": entradas,
    }
    return escribir("exclusiones.json", datos)


# ---------------------------------------------------------------------------
# 8. Efectos de casa y correcciones (sesgo)
# ---------------------------------------------------------------------------

def gen_sesgo() -> int:
    src = leer_json(os.path.join(P_SESGO, "house_effects.json"))
    correcciones = src.get("correcciones_eb", {})

    # Se publica solo lo que el informe sostiene: resumen por casa×serie,
    # la comparación CIS (mismo conjunto) y las correcciones EB del CIS
    # micro_valid + micro_censo (las que aplica la serie mensual).
    ceb = {}
    for casa, series in correcciones.items():
        if casa != "CIS":
            continue
        ceb[casa] = series

    datos = {
        "meta": {
            "generado": src.get("generado"),
            "definiciones": src.get("definiciones"),
            "conteo": src.get("conteo"),
            "nota": (
                "Error firmado = pct_encuesta − pct_real (misma base). Corrección "
                "empírica de Bayes (encogimiento k=5): pct_corregido = pct_encuesta − corrección."
            ),
        },
        "resumen": src.get("resumen"),
        "correcciones_eb_cis": ceb,
        "incumbencia": src.get("incumbencia", {}).get("CIS"),
    }
    return escribir("sesgo.json", red(datos, 3))


# ---------------------------------------------------------------------------

def main() -> int:
    os.makedirs(SALIDA, exist_ok=True)
    tareas = [
        ("forecast.json", gen_forecast),
        ("seats.json", gen_seats),
        ("backtest.json", gen_backtest),
        ("series.json", gen_series),
        ("elecciones.json", gen_elecciones),
        ("encuestas.json", gen_encuestas),
        ("exclusiones.json", gen_exclusiones),
        ("sesgo.json", gen_sesgo),
    ]
    print(f"sync-data → {os.path.relpath(SALIDA, RAIZ)}")
    for nombre, fn in tareas:
        try:
            n = fn()
            print(f"  ✓ {nombre:<18} {n/1024:7.1f} KB")
        except FileNotFoundError as err:
            print(f"  ✗ {nombre:<18} falta la entrada: {err}", file=sys.stderr)
            return 1
    print("listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
