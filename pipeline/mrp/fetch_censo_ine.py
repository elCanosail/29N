#!/usr/bin/env python3
"""Fase 4-c (segundo uso) — Denominadores censales INE para la post-estratificación.

Descarga la tabla **66600** de INEbase («Población de 15 y más años por sexo,
edad (año a año), nivel de estudios (detalle) y provincia», serie 2021-2024) y
la reduce a las celdas que consume el MRP:

    provincia × sexo × grupo de edad × grupo de estudios × periodo -> población

Fuente y licencia
-----------------
- Tabla: https://www.ine.es/jaxiT3/Tabla.htm?t=66600 (INEbase, «Censo de Población»).
- API JSON Tempus3: `https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/66600`.
  El endpoint **rechaza la tabla completa** por volumen
  (`{"status":"No puede mostrarse por restricciones de volumen"}`); se intenta
  primero y se deja constancia en el meta. El fallback es el fichero canónico
  PC-Axis/CSV de INEbase (`csv_bdsc/66600.csv`), que contiene **los mismos datos**
  en la misma desagregación.
- Licencia: aviso legal INE (reutilización permitida con atribución, sin coste).

Limitación de backtest (documentada, no maquillada)
---------------------------------------------------
La serie con las TRES dimensiones (sexo × edad × estudios) por provincia arranca
en **2021**. El Censo 2011 existe pero sólo en el sistema interactivo
(`ine.es/censos2011_datos/`) sin CSV/API descargable por provincia y con otra
armonización de estudios. Por tanto el backtest 2015-2023 usa la estructura
demográfica **2021** (la más cercana disponible en la serie 66600). Sesgo
esperado: los niveles de estudios han subido entre 2011 y 2021, así que la
estructura 2021 sobrepondera ligeramente a los más formados al reproyectarla al
pasado. Se documenta como supuesto; ver `docs/notes/mrp.md` §2 y §4.

Uso:
    /root/.venvs/29n-mrp/bin/python pipeline/mrp/fetch_censo_ine.py

Salidas:
    data/raw/ine/66600.csv                (crudo, gitignored ~90 MB)
    data/processed/mrp/censo_cells.csv    (celdas agregadas)
    data/processed/mrp/censo_meta.json    (trazabilidad + totales de control)
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "ine"
OUT = ROOT / "data" / "processed" / "mrp"

TABLE_ID = "66600"
API_URL = f"https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{TABLE_ID}"
CSV_URL = f"https://www.ine.es/jaxiT3/files/t/csv_bdsc/{TABLE_ID}.csv"
UA = "29n-mrp/0.1 (investigacion; contacto: elcano@agentmail.to)"

PERIODOS = (2021, 2022, 2023, 2024)

# Grupos de edad del MRP (alineados con la microdata CIS, 18+)
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]

# Armonización de estudios: 10 categorías censales (CNED-2014) -> 3 grupos MRP.
# Mismo mapeo aplicado a las etiquetas CIS en mrp_core.py.
EDU_CENSO = {
    "Sin estudios": "BAJO",
    "Educación primaria": "BAJO",
    "Primera etapa de Educación Secundaria y similar": "MEDIO",
    "Segunda etapa de educación secundaria, con orientación general": "MEDIO",
    "Segunda etapa de educación secundaria con orientación profesional, Educación postsecundaria no superior": "MEDIO",
    "Enseñanzas de formación profesional, artes plásticas y diseño y deportivas de grado superior y equivalentes": "ALTO",
    "Grados universitarios de hasta 240 créditos ECTS, diplomados universitarios y equivalentes": "ALTO",
    "Grados universitarios de más de 240 créditos ECTS, licenciados y equivalentes": "ALTO",
    "Másteres, especialidades en Ciencias de la Salud por el sistema de residencia y similares": "ALTO",
    "Doctorado universitario": "ALTO",
}


def fetch(url: str, dest: Path, note: dict) -> bool:
    """GET respetuoso con UA identificable; guarda en dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001
        note["error"] = f"{type(exc).__name__}: {exc}"
        return False
    dest.write_bytes(data)
    note["bytes"] = len(data)
    note["url"] = url
    return True


def try_api(note: dict) -> None:
    """Intento documentado con Tempus3 (se espera rechazo por volumen)."""
    dest = RAW / f"{TABLE_ID}.api.json"
    if not fetch(f"{API_URL}?nult=1", dest, note):
        return
    head = dest.read_bytes()[:200].decode("utf-8", "replace")
    note["respuesta_head"] = head
    note["aceptado"] = "restricciones de volumen" not in head
    if not note["aceptado"]:
        dest.unlink(missing_ok=True)


def age_group(edad_label: str) -> str | None:
    """'18 años' -> '18-24'; '90 y más años' -> '75+'; 'Total' -> None."""
    s = edad_label.strip()
    if s.endswith("y más años"):
        n = int(s.split()[0])
        if n >= 75:
            return "75+"
        return None
    if s.endswith("años"):
        try:
            n = int(s.split()[0])
        except ValueError:
            return None
        if n < 18:
            return None
        if n < 25:
            return "18-24"
        if n < 35:
            return "25-34"
        if n < 45:
            return "35-44"
        if n < 55:
            return "45-54"
        if n < 65:
            return "55-64"
        if n < 75:
            return "65-74"
        return "75+"
    return None


def parse(raw_csv: Path) -> list[dict]:
    """Reduce el CSV crudo a celdas provincia × sexo × edad × estudios × periodo.

    El censo trae la edad año a año (15-90+) y 10 categorías de estudios; aquí
    se agrega a los 7 grupos de edad y 3 de estudios del MRP.
    """
    acc: dict[tuple, int] = {}
    # El fichero se sirve como ISO-8859-15 en la cabecera HTTP pero está
    # realmente en UTF-8 con BOM (verificado: 'Educación' llega como UTF-8).
    with open(raw_csv, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh, delimiter=";")
        head = next(reader)
        assert head[2] == "Provincias" and head[7] == "Total", head
        for row in reader:
            prov_raw = row[2].strip()
            if not prov_raw:
                continue                      # fila nacional o de CCAA
            try:
                prov = int(prov_raw[:2])
            except ValueError:
                continue
            sexo = row[4].strip()
            if sexo not in ("Hombres", "Mujeres"):
                continue                      # descarta 'Total'
            ag = age_group(row[5])
            if ag is None:
                continue                      # 'Total' y 15-17 años
            edu = EDU_CENSO.get(row[3].strip())
            if edu is None:
                continue                      # 'Total' y categorías fuera de mapa
            val = row[7].strip().replace(".", "")
            if not val or val in ("..", ""):
                continue
            key = (prov, "hombre" if sexo == "Hombres" else "mujer",
                   ag, edu, int(row[6]))
            acc[key] = acc.get(key, 0) + int(val)
    return [
        {"provincia": k[0], "sexo": k[1], "edad_grupo": k[2],
         "edu_grupo": k[3], "periodo": k[4], "poblacion": v}
        for k, v in sorted(acc.items())
    ]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    meta: dict = {"tabla": TABLE_ID, "fuente": "INEbase", "api": {}, "csv_fallback": {}}

    print(f"· Tempus3 API {API_URL}")
    try_api(meta["api"])
    time.sleep(1.0)

    raw_csv = RAW / f"{TABLE_ID}.csv"
    if not raw_csv.exists() or raw_csv.stat().st_size < 1_000_000:
        print(f"· Descargando CSV canónico {CSV_URL}")
        if not fetch(CSV_URL, raw_csv, meta["csv_fallback"]):
            print("ERROR: no se pudo descargar el CSV de INEbase", file=sys.stderr)
            return 1
    else:
        meta["csv_fallback"] = {"cache": str(raw_csv), "bytes": raw_csv.stat().st_size}
    print(f"  crudo: {raw_csv} ({raw_csv.stat().st_size/1e6:.1f} MB)")

    cells = parse(raw_csv)
    out_csv = OUT / "censo_cells.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cells[0].keys()))
        w.writeheader()
        w.writerows(cells)

    # --- Controles ----------------------------------------------------------
    import collections
    tot_prov: dict[int, int] = collections.Counter()
    per_periodo: dict[int, int] = collections.Counter()
    for c in cells:
        tot_prov[c["provincia"]] += c["poblacion"]
        per_periodo[c["periodo"]] += c["poblacion"]

    nac_2024 = per_periodo.get(2024, 0)
    meta.update({
        "celdas": len(cells),
        "periodos": sorted(per_periodo),
        "poblacion_total_por_periodo": {str(k): v for k, v in sorted(per_periodo.items())},
        "poblacion_total_2024": nac_2024,
        "provincias": len(tot_prov),
        "grupos_edad": AGE_GROUPS,
        "grupos_educacion": EDU_CENSO,
        "mapeo_educacion": {"BAJO": [k for k, v in EDU_CENSO.items() if v == "BAJO"],
                            "MEDIO": [k for k, v in EDU_CENSO.items() if v == "MEDIO"],
                            "ALTO": [k for k, v in EDU_CENSO.items() if v == "ALTO"]},
        "supuesto_backtest": (
            "La serie 66600 con sexo x edad x estudios por provincia arranca en 2021. "
            "El Censo 2011 no tiene descarga CSV/API por provincia. El backtest 2015-2023 "
            "usa la estructura 2021 como aproximacion (la mas cercana disponible)."
        ),
        "nota_api": meta["api"].get("respuesta_head", ""),
    })
    (OUT / "censo_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK {out_csv} — {len(cells):,} celdas, {len(tot_prov)} provincias")
    print(f"   población 18+ 2024 (post-estratificada): {nac_2024:,}")
    print(f"   API Tempus3 aceptó la tabla completa: {meta['api'].get('aceptado')} "
          f"(usado CSV canónico: {bool(meta['csv_fallback'].get('bytes'))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
