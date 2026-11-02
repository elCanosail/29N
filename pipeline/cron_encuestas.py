#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cron_encuestas.py — revisión e ingesta automática diaria hasta el 29N.

Cadena completa, sin intervención:

  1. `encuestadores/ingesta_auto.py`  descubre, valida y escribe staging.
  2. `encuestadores/build_dataset.py` normaliza (partidos canónicos, fuentes).
  3. `modelo/build_series.py`         serie ponderada.
  4. `modelo/forecast.py`             forecast estatal (baseline + TimesFM).
  5. `modelo/provincial.py`           desglose provincial + D'Hondt.
  6. `web/sync-data.py`               JSON de la web.

Códigos de salida (los usa el cron para decidir qué contar):
  0  nada nuevo: silencio
  10 hay encuestas nuevas ingeridas y la web regenerada
  1  fallo (se relanza el aviso con el error)

LOREG: desde el 24-11-2026 no se publican encuestas nuevas (art. 69.7 LOREG,
cinco días antes). El script sigue detectando, pero no reescribe la web: deja
las candidatas en cola para después del 29N.

Uso:
    python3 pipeline/cron_encuestas.py            # producción (escribe y regenera)
    python3 pipeline/cron_encuestas.py --seco     # solo detección e informe
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(REPO, ".venv", "bin", "python")
if not os.path.exists(PY):
    PY = sys.executable
STAGING = os.path.join(REPO, "data", "processed", "encuestadores", "_staging")
LIMITE = datetime.date(2026, 11, 29)
APAGON = datetime.date(2026, 11, 24)  # cinco días antes: no se publican nuevas

CADENA = [
    ("encuestadores/build_dataset.py", "normalización"),
    ("modelo/build_series.py", "serie ponderada"),
    ("modelo/forecast.py", "forecast estatal"),
    ("modelo/provincial.py", "provincial + D'Hondt"),
    ("web/sync-data.py", "JSON de la web"),
]


def corre(script: str, etiqueta: str) -> tuple[bool, str]:
    ruta = os.path.join(REPO, script)
    r = subprocess.run([PY, ruta], cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        cola = (r.stderr or r.stdout).strip().splitlines()[-6:]
        return False, f"{etiqueta}: " + " | ".join(cola)
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seco", action="store_true", help="no escribe ni regenera")
    ap.add_argument("--desde", default=None, help="fecha ISO mínima (por defecto, la última publicada)")
    args = ap.parse_args()

    hoy = datetime.date.today()
    if hoy > LIMITE:
        print(f"## 29N cerrado\nEl 29N ({LIMITE}) ya pasó. Retirar la automatización "
              "`29n-encuestas-diario` del cron.")
        return 0

    apagon = hoy >= APAGON
    print(f"## Encuestas 29N — {(LIMITE - hoy).days} días para el 29N"
          + (" · APAGÓN LOREG activo: no se publica nada nuevo" if apagon else ""))

    antes = set(os.listdir(STAGING)) if os.path.isdir(STAGING) else set()
    cmd = [PY, os.path.join(REPO, "pipeline", "encuestadores", "ingesta_auto.py")]
    if args.desde:
        cmd += ["--desde", args.desde]
    if not (args.seco or apagon):
        cmd.append("--write")
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        print(f"\nERROR en la detección: {r.stderr.strip()[-300:]}")
        return 1

    nuevos = sorted(set(os.listdir(STAGING)) - antes)
    if apagon:
        print("\nLas candidatas quedan en cola: se publicarán después del 29N.")
        return 0
    if args.seco or not nuevos:
        if not nuevos:
            print("\nSin encuestas nuevas: no se toca ningún dato.")
        return 0

    print(f"\nFragmento nuevo: {', '.join(nuevos)} — regenerando la cadena")
    for script, etiqueta in CADENA:
        ok, error = corre(script, etiqueta)
        if not ok:
            print(f"  ✗ {error}")
            return 1
        print(f"  ✓ {etiqueta}")

    with open(os.path.join(REPO, "data", "processed", "encuestadores", "sources.json"),
              encoding="utf-8") as fh:
        total = len(json.load(fh))
    print(f"\nTotal de encuestas de encuestadores privados: {total}")
    print("Siguiente paso del cron: revisar el diff y publicar (commit + push → Vercel).")
    return 10


if __name__ == "__main__":
    sys.exit(main())
