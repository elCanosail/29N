#!/usr/bin/env python3
"""Utilidades compartidas del modelo de predicción 29N (fase 4).

Carga de datos normalizados (CIS, encuestadores privados, Interior, sesgo),
canonicalización de partidos, observaciones corregidas por efectos de casa
(empirical-bayes) y construcción de la **serie mensual ponderada** por partido.

Bases de porcentaje
-------------------
Toda la serie se construye en **% sobre voto válido**, que es la base con la
que se reparten escaños (D'Hondt) y la que usan los datos de Interior.

- CIS `polls.jsonl` publica voto directo **% sobre censo**. Se reescala a
  válido dividiendo por la cuota declarada: `valid_base_censo/100`, donde
  `valid_base_censo` = Σ(partidos reconocidos) + voto en blanco (idéntico a
  como lo calcula `pipeline/sesgo/compute_house_effects.py`).
- Encuestadores privados: `porcentaje` ya está en % sobre válido.

Correcciones EB
---------------
`data/processed/sesgo/house_effects.json` → `correcciones_eb[casa][serie][partido]`
= `media_error × n/(n+K)`, K=5. Se **resta** a cada observación de esa casa y
serie (signo documentado en `docs/notes/sesgo.md`). Si no hay corrección para
esa casa/partido, la corrección es 0.

Pesos
-----
`w = recencia × muestra × calidad`
- recencia: media-vida 45 días → `0.5 ** (Δdías/45)`.
- muestra: `√(n / 2000)`.
- calidad: `1/(1+MAE)`. Privados, MAE 23J de `encuestadores/scoring.json`; CIS,
  MAE histórica del voto directo reescalado (`micro_valid`, calidad validada),
  calculada de `house_effects.json`.

Serie mensual
-------------
Para cada partido y cada fin de mes `m`, el valor es la media ponderada de las
observaciones con fecha ≤ `m` (ventana efectiva: la exponencial anula lo viejo;
se acota a 730 días por estabilidad numérica). Sin observaciones en la ventana
→ se arrastra la última ("LOCF"). Sin ninguna observación → 0.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"

# --- Parámetros del modelo --------------------------------------------------
HALFLIFE_DAYS = 45.0          # media-vida de la ponderación por recencia
SIZE_REF_N = 2000             # muestra de referencia para el peso de tamaño
MAX_LOOKBACK_DAYS = 730       # ventana máxima de observaciones por mes
GRID_START = (1977, 6)        # primer mes de la serie (tras la 1ª general)
GRID_END = (2026, 11)         # mes objetivo (elección 29N, 29-11-2026)
ELECTION_29N = date(2026, 11, 29)
DHONDT_THRESHOLD = 0.03

# Partidos modelados explícitamente (canónicos de `party_canon`). El resto cae
# en OTROS (residual).
MODELED_PARTIES = [
    "PP", "PSOE", "VOX", "SUMAR",
    "ERC", "JXCAT", "PNV", "EH BILDU", "BNG", "CUP", "CC", "NA+", "PACMA",
]

# Familias: el espacio de la izquierda estatal alternativa al PSOE ha cambiado
# de marca (IU → PODEMOS/UNIDAS PODEMOS → SUMAR). Se modela como una sola
# serie para evitar "partidos fantasma" (una marca sin datos recientes que
# TimesFM extrapola con su último nivel caduco). La base provincial de 2023 es
# SUMAR; las marcas antiguas se pliegan en esa misma familia.
FAMILY = {
    "IU": "SUMAR",
    "PODEMOS": "SUMAR",
    "UNIDAS PODEMOS": "SUMAR",
}

# Filtro de completitud de estudios privados: solo entran los que publican el
# desglose nacional de los 4 grandes partidos (PP/PSOE/VOX/SUMAR) y cuya suma
# es ≥ este umbral. Los sondeos con publicación parcial (solo 2 partidos) o con
# cifras en otra base no son comparables.
BIG4 = ("PP", "PSOE", "VOX", "SUMAR")
BIG4_MIN_SUM = 75.0

# Casas con serie propia
CIS = "CIS"

# Grupos de etiquetas CIS no partidistas (excluidas del denominador)
NON_PARTY = {"NS", "NC", "EN BLANCO", "VOTO NULO", "ABSTENCION",
             "NO DECIDIDO", "OTROS"}

BACKTEST_ELECTIONS = [
    "2015-12-20", "2016-06-26", "2019-04-28", "2019-11-10", "2023-07-23",
]


# --------------------------------------------------------------------------- #
# Carga básica
# --------------------------------------------------------------------------- #
def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_jsonl(path: Path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def parse_date(s):
    """Acepta 'dd/mm/yyyy', 'yyyy-mm-dd' y rangos 'a/b' (toma el fin)."""
    if not s:
        return None
    s = str(s).strip()
    if "/" in s and len(s) > 10:          # rango "2023-06-05/2023-06-08"
        s = s.split("/")[-1]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# Canonicalización de partidos
# --------------------------------------------------------------------------- #
import sys

sys.path.insert(0, str(ROOT / "pipeline" / "sesgo"))
from party_canon import canonical_of_cis, canonical_of_slug  # noqa: E402


def canonical_cis(label):
    return canonical_of_cis(label)


# Huecos de canonicalización detectados al construir el modelo (Interior):
# en 2023 UPN se publica con la sigla `u-p-n`, que `party_canon` no reconoce
# (manda a OTROS). UPN es la rama navarra del espacio NA+, así que se reasigna
# para que el partido tenga anclaje provincial en la base de 23J.
SLUG_FIXES = {"u-p-n": "NA+"}


def canon_slug(slug, eid=None):
    c = canonical_of_slug(slug, eid)
    if c == "OTROS" and slug in SLUG_FIXES:
        c = SLUG_FIXES[slug]
    return FAMILY.get(c, c)


# --------------------------------------------------------------------------- #
# Interior
# --------------------------------------------------------------------------- #
class Interior:
    def __init__(self):
        self.elections = load_json(DATA / "interior" / "elections.json")["elecciones"]
        self._by_id = {e["id"]: e for e in self.elections}
        self.rows = load_jsonl(DATA / "interior" / "results_provincial.jsonl")
        self._prov = {}
        for r in self.rows:
            self._prov.setdefault(r["eleccion"], []).append(r)

    def ids(self):
        return [e["id"] for e in self.elections]

    def election(self, eid):
        return self._by_id[eid]

    def valid_votes(self, eid):
        return {p["codigo"]: p["votos_validos"] for p in self._by_id[eid]["provincias"]}

    def seats(self, eid):
        return {p["codigo"]: p["escanos"] for p in self._by_id[eid]["provincias"]}

    def provinces(self, eid):
        return self._by_id[eid]["provincias"]

    def national_canonical(self, eid):
        """{canónico: votos} sobre voto válido nacional (con familias)."""
        tot = {}
        for r in self._prov.get(eid, []):
            c = canon_slug(r["partido_id"], eid)
            tot[c] = tot.get(c, 0) + r["votos"]
        valid = sum(self.valid_votes(eid).values())
        return {c: 100.0 * v / valid for c, v in tot.items()}

    def provincial_canonical(self, eid):
        """{prov_code: {canónico: % sobre voto válido provincial}}."""
        valid = self.valid_votes(eid)
        out = {}
        for r in self._prov.get(eid, []):
            p = r["provincia"]
            d = out.setdefault(p, {})
            c = canon_slug(r["partido_id"], eid)
            d[c] = d.get(c, 0) + r["votos"]
        for p, d in out.items():
            vv = valid.get(p) or sum(d.values())
            out[p] = {c: 100.0 * v / vv for c, v in d.items()}
        return out


# --------------------------------------------------------------------------- #
# Observaciones (CIS + privados), corregidas por EB
# --------------------------------------------------------------------------- #
class Observations:
    """Observaciones normalizadas a % sobre válido, con corrección EB aplicada."""

    def __init__(self):
        self.sesgo = load_json(DATA / "sesgo" / "house_effects.json")
        self.correcciones = self.sesgo["correcciones_eb"]
        self.cis_meta = self.sesgo.get("estudios_cis", {})
        self.scoring = load_json(DATA / "encuestadores" / "scoring.json")
        self.mae_cis = self._compute_mae_cis()
        self.mae_priv = self._compute_mae_priv()
        self.mae_priv_default = self._median_mae_priv()
        self.obs = self._build()
        self.by_party = {}
        for o in self.obs:
            self.by_party.setdefault(o["party"], []).append(o)

    # --- MAE históricas -----------------------------------------------------
    def _compute_mae_cis(self):
        errs = [s["err"] for s in self.sesgo["series"]
                if s["casa"] == CIS and s["serie"] == "micro_valid"
                and s["calidad"] == "validada"]
        return sum(abs(e) for e in errs) / len(errs) if errs else 1.8

    def _compute_mae_priv(self):
        out = {}
        for row in self.scoring["por_encuestador"]:
            out[row["encuestador"]] = row["mae"]
        return out

    def _median_mae_priv(self):
        vals = sorted(self.mae_priv.values())
        if not vals:
            return 2.0
        n = len(vals)
        return vals[n // 2] if n % 2 else 0.5 * (vals[n // 2 - 1] + vals[n // 2])

    def quality_weight(self, casa):
        if casa == CIS:
            mae = self.mae_cis
        else:
            mae = self.mae_priv.get(casa, self.mae_priv_default)
        return 1.0 / (1.0 + mae)

    # --- Correcciones EB ----------------------------------------------------
    def correction(self, casa, serie, party):
        d = self.correcciones.get(casa, {}).get(serie, {})
        return d.get(party, {}).get("correccion", 0.0)

    # --- Construcción -------------------------------------------------------
    def _build(self):
        obs = []
        obs.extend(self._build_cis())
        obs.extend(self._build_priv())
        obs.sort(key=lambda o: (o["date"], o["casa"]))
        return obs

    def _build_cis(self):
        rows = load_jsonl(DATA / "cis" / "polls.jsonl")
        by_study = {}
        for r in rows:
            by_study.setdefault(r["estudio_id"], []).append(r)
        out = []
        skipped = []
        for eid, rs in by_study.items():
            # Estudios que la fase 4-bis no pudo validar contra las tablas
            # publicadas (variable de voto mal normalizada) quedan fuera:
            meta = self.cis_meta.get(eid)
            if meta and meta.get("calidad") == "no_validada":
                skipped.append(eid)
                continue
            # Base válida declarada (partidos reconocidos + en blanco)
            base = sum(x["voto_pct"] for x in rs
                       if canonical_cis(x["partido"]) is not None
                       or x["partido"] == "EN BLANCO")
            # ignoramos estudios con cobertura ínfima (no reproducibles)
            if base < 30.0:
                continue
            d = parse_date(rs[0]["fecha_trabajo"])
            if d is None:
                continue
            n = rs[0]["n"]
            for x in rs:
                party = canonical_cis(x["partido"])
                if party is None:
                    continue
                party = FAMILY.get(party, party)
                val = 100.0 * x["voto_pct"] / base  # % sobre válido
                val -= self.correction(CIS, "micro_valid", party)
                out.append({
                    "date": d, "casa": CIS, "serie": "micro_valid",
                    "party": party, "value": max(0.0, val), "n": n,
                    "estudio": eid,
                })
        self._cis_skipped = sorted(skipped)
        return out

    def _build_priv(self):
        rows = load_jsonl(DATA / "encuestadores" / "polls.jsonl")
        out = []
        dropped = []
        dropped_incompleto = []
        by_study = {}
        for r in rows:
            if str(r.get("ambito", "nacional")).lower() not in ("nacional", "estatal"):
                continue
            by_study.setdefault(r["estudio_id"], []).append(r)
        for eid, rs in by_study.items():
            vals = {x["partido_canonico"]: float(x["porcentaje"]) for x in rs}
            if all(p in vals for p in BIG4) and sum(vals[p] for p in BIG4) >= BIG4_MIN_SUM:
                continue
            dropped_incompleto.append(eid)
        for r in rows:
            # Solo encuestas de ámbito estatal: las proyecciones autonómicas
            # (p. ej. CEO en Cataluña) usan otra base y no son comparables.
            if str(r.get("ambito", "nacional")).lower() not in ("nacional", "estatal"):
                dropped.append(r["estudio_id"])
                continue
            if r["estudio_id"] in dropped_incompleto:
                continue
            d = parse_date(r.get("fecha_trabajo")) or parse_date(r.get("fecha_publicacion"))
            if d is None:
                continue
            casa = r["fuente"]
            party = FAMILY.get(r["partido_canonico"], r["partido_canonico"])
            val = float(r["porcentaje"]) - self.correction(casa, "privado", party)
            out.append({
                "date": d, "casa": casa, "serie": "privado",
                "party": party, "value": max(0.0, val), "n": r.get("n") or 1000,
                "estudio": r["estudio_id"],
            })
        self._priv_dropped = sorted(set(dropped))
        self._priv_incompleto = sorted(set(dropped_incompleto))
        return out


# --------------------------------------------------------------------------- #
# Serie mensual ponderada
# --------------------------------------------------------------------------- #
def month_grid(start=GRID_START, end=GRID_END):
    """Lista de fechas 'fin de mes' (aprox.: último día del mes)."""
    y, m = start
    out = []
    while (y, m) <= end:
        if m == 12:
            last = date(y, 12, 31)
        else:
            last = date(y, m + 1, 1) - timedelta(days=1)
        out.append(last)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _weights(obs_list, ref_date):
    w = []
    for o in obs_list:
        d = (ref_date - o["date"]).days
        if d < 0:
            continue
        rec = 0.5 ** (d / HALFLIFE_DAYS)
        size = math.sqrt(max(o["n"] or 1, 1) / SIZE_REF_N)
        qual = o["qw"]
        w.append((o, rec * size * qual))
    return w


def build_party_series(party, obs, cutoff=None, ref_date=None):
    """Serie mensual ponderada de un partido.

    Parameters
    ----------
    party : str
    obs : Observations
    cutoff : date | None
        Solo se usan observaciones con fecha estrictamente < cutoff.
    ref_date : (y, m) | None
        Último mes de la rejilla (por defecto GRID_END).
    """
    o = []
    for x in obs.by_party.get(party, []):
        if cutoff is not None and x["date"] >= cutoff:
            continue
        o.append({**x, "qw": obs.quality_weight(x["casa"])})
    o.sort(key=lambda x: x["date"])

    grid = month_grid(end=ref_date or GRID_END)
    values = []
    last = 0.0
    for me in grid:
        recent = [x for x in o if (me - x["date"]).days <= MAX_LOOKBACK_DAYS
                  and x["date"] <= me]
        if recent:
            ws = _weights(recent, me)
            tot = sum(w for _, w in ws)
            if tot > 0:
                last = sum(x["value"] * w for x, w in ws) / tot
            values.append(last)
        else:
            values.append(last)
    return grid, values


def aggregate_series(obs, parties=None, cutoff=None, ref_date=None):
    """Series por partido (dict partido -> lista)."""
    parties = parties or MODELED_PARTIES
    return {p: build_party_series(p, obs, cutoff=cutoff, ref_date=ref_date)[1]
            for p in parties}


def normalize(d):
    """Renormaliza un dict de % para que sume 100. Devuelve (dict, factor)."""
    tot = sum(d.values())
    if tot <= 0:
        return d, 1.0
    return {k: 100.0 * v / tot for k, v in d.items()}, 100.0 / tot
