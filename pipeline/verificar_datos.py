#!/usr/bin/env python3
"""Guardia de datos de 29N — antes de comitear, no después.

Nació de un fallo real: el 8 de noviembre de 2026 el merge de la ingesta dejó
`<<<<<<< HEAD` dentro de `web/src/data/encuestas.json` y `exclusiones.json`.
`astro.config.mjs` hace `JSON.parse` de ese fichero al cargar la configuración,
así que el build de la web no arrancaba y el despliegue se cayó. El dato estaba
mal *y* nadie lo detectó hasta intentar publicar.

Este script comprueba tres cosas y sale con código 1 si alguna falla:

  1. Ningún fichero de dato contiene marcas de conflicto de git.
  2. Todo JSON de dato parsea; cada línea de los JSONL parsea.
  3. El número de encuestas publicadas no se reduce respecto a `origin/main`.

Uso:
    python3 pipeline/verificar_datos.py            # antes de comitear
    python3 pipeline/verificar_datos.py --base main # contra otra referencia

No necesita dependencias: solo la biblioteca estándar.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

def _raiz_repo() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             cwd=Path(__file__).resolve().parent,
                             capture_output=True, text=True, timeout=15)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return Path(__file__).resolve().parent.parent


RAIZ = _raiz_repo()

MARCAS = ("<<<<<<<", "=======", ">>>>>>>")
SUFIJOS_DATO = (".json", ".jsonl")
# Un "=======" suelto puede ser legítimo en un markdown o en un CSV; solo miramos
# marcas de conflicto en ficheros de dato estructurado.
DIRECTORIOS = [RAIZ / "web" / "src" / "data", RAIZ / "data" / "processed"]


def ficheros_dato() -> list[Path]:
    vistos: list[Path] = []
    for d in DIRECTORIOS:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix in SUFIJOS_DATO:
                vistos.append(p)
    return vistos


def revisar_marcas(ruta: Path) -> list[str]:
    fallos = []
    try:
        texto = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [f"{ruta.relative_to(RAIZ)}: no se pudo leer ({e})"]
    for i, linea in enumerate(texto.splitlines(), 1):
        if linea.startswith(MARCAS):
            fallos.append(f"{ruta.relative_to(RAIZ)}:{i}: marca de conflicto «{linea[:20]}»")
    return fallos


def revisar_parseo(ruta: Path) -> list[str]:
    rel = ruta.relative_to(RAIZ)
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as e:
        return [f"{rel}: no se pudo leer ({e})"]
    if ruta.suffix == ".json":
        try:
            json.loads(texto)
        except json.JSONDecodeError as e:
            return [f"{rel}:{e.lineno}:{e.colno}: JSON inválido ({e.msg})"]
        return []
    fallos = []
    for i, linea in enumerate(texto.splitlines(), 1):
        if not linea.strip():
            continue
        try:
            json.loads(linea)
        except json.JSONDecodeError as e:
            fallos.append(f"{rel}:{i}: JSONL inválido ({e.msg})")
            if len(fallos) >= 3:  # no inundar la salida
                break
    return fallos


def encuestas_en(ref: str) -> int | None:
    """Cuenta de encuestas publicadas en una referencia de git."""
    try:
        out = subprocess.run(
            ["git", "show", f"{ref}:web/src/data/encuestas.json"],
            cwd=RAIZ, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        d = json.loads(out.stdout)
    except json.JSONDecodeError:
        return None
    n = d.get("meta", {}).get("n")
    if isinstance(n, int):
        return n
    e = d.get("encuestas")
    return len(e) if isinstance(e, list) else None


def main() -> int:
    base = "main"
    if "--base" in sys.argv:
        i = sys.argv.index("--base")
        if i + 1 < len(sys.argv):
            base = sys.argv[i + 1]
    ref = f"origin/{base}"

    fallos: list[str] = []
    ficheros = ficheros_dato()
    if not ficheros:
        print(f"FALLO: no se encontró ningún fichero de dato bajo {RAIZ}. "
              "¿Se está ejecutando fuera del repo?")
        return 1

    for p in ficheros:
        fallos += revisar_marcas(p)
        fallos += revisar_parseo(p)

    # El total publicado no puede bajar: una ingesta que reduce el histórico
    # significa que se ha perdido algo por el camino.
    local = RAIZ / "web" / "src" / "data" / "encuestas.json"
    n_local = None
    if local.exists():
        try:
            d = json.loads(local.read_text(encoding="utf-8"))
            n_local = d.get("meta", {}).get("n") or len(d.get("encuestas") or [])
        except json.JSONDecodeError:
            n_local = None  # ya está reportado como fallo de parseo
    n_base = encuestas_en(ref)
    if n_local is not None and n_base is not None and n_local < n_base:
        fallos.append(
            f"web/src/data/encuestas.json: el total baja de {n_base} a {n_local} "
            f"(referencia {ref})"
        )

    print(f"Datos revisados: {len(ficheros)} ficheros · encuestas {n_local} "
          f"(referencia {ref}: {n_base})")

    if fallos:
        print(f"\nFALLAN {len(fallos)} comprobaciones:")
        for f in fallos:
            print(f"  - {f}")
        print("\nNo comitees ni publishes con esto así.")
        return 1

    print("OK: sin marcas de conflicto, todo parsea y el total no baja.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
