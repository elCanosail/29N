#!/usr/bin/env python3
"""Efectos de casa y sesgo de incumbencia de los encuestadores (29N, fase 4-bis).

Calcula, con las encuestas "finales" de cada casa:

  1. Error firmado medio por casa x partido (n, media, desviación) sobre todas
     las elecciones con encuesta final disponible.
  2. Sesgo de incumbencia: error medio en los partidos EN el Gobierno de turno
     frente a los que están FUERA, con intervalos bootstrap (semilla fija) y
     advertencia explícita de potencia estadística.
  3. Corrección con encogimiento empirical-bayes:
         correccion_i = media_error_i * n_i / (n_i + K),  K = 5.

Tres series separadas, para localizar el sesgo:
  (a) CIS microdato  — voto directo de `polls.jsonl` (% sobre censo).
  (a') CIS microdato normalizado — el mismo voto directo reescalado a % sobre
       voto válido (partidos + blanco), comparable con (b).
  (b) CIS estimación — columna "Estimación de voto CIS" publicada (% sobre voto
       válido) de `data/raw/cis/estimacion/`.
  (c) Encuestadores privados — `polls.jsonl` de encuestadores (% sobre voto
       válido publicado por la casa).

Definiciones de "encuesta final" (ver docs/notes/sesgo.md):
  - ESTRICTA (enunciado): fin de trabajo de campo dentro de los 7 días naturales
    previos al día de la votación.
  - OPERATIVA (fallback documentado): última encuesta preelectoral de la casa
    cuyo trabajo de campo terminó antes del día de la votación. Necesaria porque
    el campo del CIS termina habitualmente 2-5 semanas antes del día de la
    votación y la definición estricta dejaría la serie CIS sin observaciones.

Solo escribe ficheros en pipeline/sesgo/ y data/processed/sesgo/. No commit.
"""
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "sesgo"))

from party_canon import canonical_of_slug, canonical_of_cis  # noqa: E402
from parse_estimacion import parse_total_nacional  # noqa: E402

K_SHRINK = 5          # constante de encogimiento empirical-bayes (documentada)
STRICT_DAYS = 7       # ventana estricta del enunciado
RNG_SEED = 20261015

# CIS estudio -> elección (solo generales al Congreso; el resto se excluye)
CIS_STUDY_ELECTION = {
    "1135": "1977-06-15",
    "1181": "1979-03-01", "1183": "1979-03-01",
    "1324": "1982-10-28", "1326": "1982-10-28",
    "1533": "1986-06-22",
    "7789": "1989-10-29",
    "2207": "1996-03-03",
    "3117": "2015-12-20", "7715": "2015-12-20",
    "3141": "2016-06-26",
    "3242": "2019-04-28",
    "3263": "2019-11-10",
    "3411": "2023-07-23", "3415": "2023-07-23", "3416": "2023-07-23",
}
# Estudios con tabla publicada de estimación de voto -> elección
CIS_EST_ELECTION = {
    "3117": "2015-12-20",
    "3141": "2016-06-26",
    "3242": "2019-04-28",
    "3263": "2019-11-10",
    "3411": "2023-07-23",
    "3415": "2023-07-23",
    "3269": "2019-11-10",   # postelectoral (marca: no es preelectoral)
    "3420": "2023-07-23",   # postelectoral
}
CIS_EST_POSTELECTORAL = {"3269", "3420"}

# Estudios cuyo microdato ha sido VALIDADO contra la tabla publicada "Voto
# directo en la encuesta" (nota cis-ingest.md §4 y parse_estimacion.py).
# Los estudios antiguos sin tabla publicada usan heurística de selección de la
# variable de voto y pueden estar mal normalizados (p.ej. 1326/1533); quedan
# fuera de la tabla principal y se reportan aparte.
CIS_VALIDADA = {"3117", "3141", "3242", "3263", "3411", "3415"}

POLLSTER_ELECTION = {"generales 2023": "2023-07-23"}


# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------
def parse_date(s):
    if not s:
        return None
    s = s.strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if m:
        d, mo, y = map(int, m.groups())
        return date(y, mo, d)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        return date(y, mo, d)
    return None


def range_end(s):
    """'2023-06-05/2023-06-08' -> 2023-06-08 ; fecha única -> esa fecha."""
    if not s:
        return None
    if "/" in s:
        return parse_date(s.split("/")[-1])
    return parse_date(s)


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def bootstrap_ci(xs, iters=10000, seed=RNG_SEED, lo=2.5, hi=97.5):
    if not xs:
        return None
    if len(xs) == 1:
        return [round(xs[0], 3), round(xs[0], 3)]
    rng = random.Random(seed)
    n = len(xs)
    means = []
    for _ in range(iters):
        means.append(sum(xs[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return [round(means[int(lo / 100 * iters)], 3),
            round(means[int(hi / 100 * iters)], 3)]


# --------------------------------------------------------------------------
# 1. resultados reales
# --------------------------------------------------------------------------
def load_real():
    d = json.load(open(ROOT / "data/processed/interior/elections.json"))
    inc = json.load(open(ROOT / "pipeline/sesgo/incumbency.json"))["elecciones"]
    real = {}
    for e in d["elecciones"]:
        if e["tipo"] != "congreso":
            continue
        eid = e["id"]
        tot = e.get("totales") or {}
        censo = tot.get("censo")
        validos = tot.get("votos_validos")
        agg = defaultdict(int)
        for p in e["partidos"]:
            agg[canonical_of_slug(p["partido_id"], eid)] += p["votos"]
        over_censo = {k: 100.0 * v / censo for k, v in agg.items()} if censo else {}
        over_valid = {k: 100.0 * v / validos for k, v in agg.items()} if validos else {}
        real[eid] = {
            "fecha": e["fecha"], "censo": censo, "votos_validos": validos,
            "votos_candidaturas": sum(agg.values()),
            "over_censo": over_censo, "over_valid": over_valid,
            "gobierno": inc.get(eid, {}),
        }
    return real


# --------------------------------------------------------------------------
# 2. series de encuestas
# --------------------------------------------------------------------------
def load_cis_micro():
    """estudio -> {fecha_end, eleccion, n, tipo, directo_censo{}, valid_censo{}}"""
    ends = json.load(open(ROOT / "pipeline/sesgo/cis_fieldwork_ends.json"))
    rows = defaultdict(lambda: {"directo_censo": {}, "n": None, "fecha_start": None,
                                "tipo": None, "nonparty": {}})
    for line in open(ROOT / "data/processed/cis/polls.jsonl"):
        o = json.loads(line)
        sid = o["estudio_id"]
        if sid not in CIS_STUDY_ELECTION:
            continue
        rows[sid]["n"] = o.get("n")
        rows[sid]["fecha_start"] = parse_date(o["fecha_trabajo"])
        canon = canonical_of_cis(o["partido"], o.get("anio"))
        if canon:
            rows[sid]["directo_censo"][canon] = o["voto_pct"]
        else:
            rows[sid]["nonparty"][o["partido"]] = o["voto_pct"]
    out = {}
    for sid, r in rows.items():
        eid = CIS_STUDY_ELECTION[sid]
        end = parse_date(ends.get(sid)) if ends.get(sid) else None
        # base de voto válido declarada = partidos + EN BLANCO
        valid_base = sum(r["directo_censo"].values()) + r["nonparty"].get("EN BLANCO", 0.0)
        direct_valid = {k: 100.0 * v / valid_base for k, v in r["directo_censo"].items()} \
            if valid_base > 0 else {}
        out[sid] = {
            "estudio": sid, "eleccion": eid, "fecha_start": r["fecha_start"],
            "fecha_end": end, "end_source": "FT (ficha técnica)" if end else "sin FT",
            "n": r["n"], "directo_censo": r["directo_censo"],
            "directo_valid": direct_valid, "nonparty": r["nonparty"],
            "valid_base_censo": round(valid_base, 3),
            "calidad": "validada" if sid in CIS_VALIDADA else "no_validada",
            "cobertura_partidos_censo": round(sum(r["directo_censo"].values()), 3),
            "ns_nc_censo": round(sum(r["nonparty"].get(k, 0.0)
                                    for k in ("NS", "NC", "NO DECIDIDO")), 3),
        }
    return out


def load_cis_est():
    out = {}
    for p in sorted((ROOT / "data/raw/cis/estimacion").glob("est*.txt")):
        sid = re.match(r"est(\w+)\.txt", p.name).group(1)
        if sid not in CIS_EST_ELECTION:
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        t = parse_total_nacional(txt)
        if not t:
            continue
        out[sid] = {
            "estudio": sid, "eleccion": CIS_EST_ELECTION[sid],
            "postelectoral": sid in CIS_EST_POSTELECTORAL,
            "directo_censo": {k: v["directo"] for k, v in t.items()},
            "estim_valid": {k: v["estim"] for k, v in t.items()},
        }
    return out


def load_pollsters():
    rows = defaultdict(lambda: {"por": {}, "fuente": None, "fecha_end": None,
                                "n": None, "eleccion": None, "fecha_raw": None})
    for line in open(ROOT / "data/processed/encuestadores/polls.jsonl"):
        o = json.loads(line)
        sid = o["estudio_id"]
        r = rows[sid]
        r["fuente"] = o["fuente"]
        r["fecha_raw"] = o.get("fecha_trabajo")
        r["fecha_end"] = range_end(o.get("fecha_trabajo"))
        r["n"] = o.get("n")
        r["eleccion"] = POLLSTER_ELECTION.get(o.get("eleccion"))
        r["por"][o["partido_canonico"]] = o["porcentaje"]
    return dict(rows)


# --------------------------------------------------------------------------
# 3. selección de encuesta final
# --------------------------------------------------------------------------
def pick_final(cands, election_date, strict):
    """cands: lista de (fecha_end, payload). Devuelve la elegida o None.

    strict=True  -> fin de campo dentro de los 7 días previos a la votación.
    strict=False -> la más próxima a la votación con campo terminado antes.
    """
    if election_date is None:
        return None
    ready = [c for c in cands if c[0] and c[0] < election_date]
    if not ready:
        return None
    if strict:
        cut = election_date - timedelta(days=STRICT_DAYS)
        ready = [c for c in ready if c[0] >= cut]
        if not ready:
            return None
    ready.sort(key=lambda c: c[0])
    return ready[-1]


def build_series(real, cis_micro, cis_est, pollsters):
    series = []   # cada item: dict con casa, serie, eleccion, partido, err, base

    # --- CIS microdato ---
    by_elec = defaultdict(list)
    for sid, m in cis_micro.items():
        by_elec[m["eleccion"]].append((m["fecha_end"], m))
    for eid, cands in by_elec.items():
        chosen = pick_final(cands, parse_date(eid), strict=False)
        if not chosen:
            continue
        m = chosen[1]
        real_c = real[eid]["over_censo"]
        real_v = real[eid]["over_valid"]
        for party, pct in m["directo_censo"].items():
            if party in real_c:
                series.append(dict(casa="CIS", serie="micro_censo", eleccion=eid,
                                   estudio=m["estudio"], partido=party,
                                   encuesta=pct, real=real_c[party],
                                   err=round(pct - real_c[party], 3), base="censo",
                                   calidad=m["calidad"]))
        for party, pct in m["directo_valid"].items():
            if party in real_v:
                series.append(dict(casa="CIS", serie="micro_valid", eleccion=eid,
                                   estudio=m["estudio"], partido=party,
                                   encuesta=round(pct, 3), real=real_v[party],
                                   err=round(pct - real_v[party], 3), base="válido",
                                   calidad=m["calidad"]))

    # --- CIS estimación ---
    by_elec = defaultdict(list)
    for sid, m in cis_est.items():
        if m["postelectoral"]:
            continue
        by_elec[m["eleccion"]].append((None, m))  # sin fecha: la más reciente por estudio
    for eid, cands in by_elec.items():
        # si hay varias, preferir el estudio preelectoral de campo más tardío
        micro_end = {}
        for sid, m in cis_micro.items():
            micro_end[sid] = m["fecha_end"]
        cands.sort(key=lambda c: (micro_end.get(c[1]["estudio"]) or date(1900, 1, 1)))
        m = cands[-1][1]
        real_v = real[eid]["over_valid"]
        for party, pct in m["estim_valid"].items():
            if party in real_v:
                series.append(dict(casa="CIS", serie="est", eleccion=eid,
                                   estudio=m["estudio"], partido=party,
                                   encuesta=pct, real=real_v[party],
                                   err=round(pct - real_v[party], 3), base="válido",
                                   calidad="validada"))

    # --- Encuestadores privados ---
    for sid, r in pollsters.items():
        if not r["eleccion"]:
            continue
        eid = r["eleccion"]
        cut = parse_date(eid) - timedelta(days=STRICT_DAYS)
        if not r["fecha_end"] or r["fecha_end"] < cut:
            continue  # solo la ventana final estricta para privados
        real_v = real[eid]["over_valid"]
        for party, pct in r["por"].items():
            if party in real_v:
                series.append(dict(casa=r["fuente"], serie="privado", eleccion=eid,
                                   estudio=sid, partido=party, encuesta=pct,
                                   real=real_v[party],
                                   err=round(pct - real_v[party], 3), base="válido",
                                   calidad="validada"))
    return series


# --------------------------------------------------------------------------
# 4. análisis
# --------------------------------------------------------------------------
def house_effects_table(series):
    """casa x serie -> partido -> (n, media, sd)."""
    g = defaultdict(lambda: defaultdict(list))
    for s in series:
        g[(s["casa"], s["serie"])][s["partido"]].append(s["err"])
    out = {}
    for (casa, serie), parties in g.items():
        out.setdefault(casa, {})[serie] = {
            p: {"n": len(v), "media": round(mean(v), 3), "sd": round(sd(v), 3),
                "ic95_bootstrap": bootstrap_ci(v),
                "errores": [round(x, 3) for x in v]}
            for p, v in sorted(parties.items())
        }
    return out


def incumbency_analysis(series, real):
    """Por casa y serie: media de error dentro/fuera del Gobierno + bootstrap."""
    g = defaultdict(lambda: {"in": [], "out": []})
    for s in series:
        gov = real[s["eleccion"]]["gobierno"].get("partidos_gobierno", [])
        key = "in" if s["partido"] in gov else "out"
        g[(s["casa"], s["serie"])][key].append(s["err"])
    out = {}
    for (casa, serie), d in g.items():
        entry = {}
        for key in ("in", "out"):
            xs = d[key]
            entry[key] = {
                "n": len(xs),
                "media": round(mean(xs), 3) if xs else None,
                "sd": round(sd(xs), 3) if xs else None,
                "ic95_bootstrap": bootstrap_ci(xs) if xs else None,
                "errores": [round(x, 3) for x in xs],
            }
        if entry["in"]["media"] is not None and entry["out"]["media"] is not None:
            entry["diferencia_in_menos_out"] = round(entry["in"]["media"] - entry["out"]["media"], 3)
            # bootstrap de la diferencia (remuestreo independiente de cada grupo)
            if d["in"] and d["out"]:
                rng = random.Random(RNG_SEED + 1)
                ni, no = len(d["in"]), len(d["out"])
                diffs = []
                for _ in range(10000):
                    mi = sum(d["in"][rng.randrange(ni)] for _ in range(ni)) / ni
                    mo = sum(d["out"][rng.randrange(no)] for _ in range(no)) / no
                    diffs.append(mi - mo)
                diffs.sort()
                entry["diferencia_ic95_bootstrap"] = [round(diffs[250], 3), round(diffs[9750], 3)]
        out.setdefault(casa, {})[serie] = entry
    return out


def eb_corrections(series):
    """correccion_i = media_error_i * n/(n+K) por casa x serie x partido."""
    g = defaultdict(list)
    for s in series:
        g[(s["casa"], s["serie"], s["partido"])].append(s["err"])
    out = defaultdict(lambda: defaultdict(dict))
    for (casa, serie, party), xs in g.items():
        n = len(xs)
        m = mean(xs)
        out[casa][serie][party] = {
            "n": n, "media_error": round(m, 3),
            "correccion": round(m * n / (n + K_SHRINK), 3),
        }
    return {c: {s: dict(p) for s, p in v.items()} for c, v in out.items()}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    real = load_real()
    cis_micro = load_cis_micro()
    cis_est = load_cis_est()
    pollsters = load_pollsters()
    series = build_series(real, cis_micro, cis_est, pollsters)
    series_val = [s for s in series if s.get("calidad") == "validada"]

    he = house_effects_table(series_val)
    he_all = house_effects_table(series)
    inc = incumbency_analysis(series_val, real)
    corr = eb_corrections(series_val)

    # subconjunto estricto (7 días) para documentar
    strict_subset = []
    for s in series:
        m = cis_micro.get(s.get("estudio")) if s["serie"].startswith("micro") else None
        if m and m["fecha_end"]:
            cut = parse_date(s["eleccion"]) - timedelta(days=STRICT_DAYS)
            if m["fecha_end"] >= cut:
                strict_subset.append(s)

    # --- resumen: error absoluto medio por serie y efecto del modelo CIS ---
    def _mae(xs):
        return round(mean([abs(x) for x in xs]), 3) if xs else None
    resumen = {}
    gk = defaultdict(list)
    for s in series_val:
        gk[(s["casa"], s["serie"])].append(s["err"])
    for (casa, serie), xs in gk.items():
        resumen.setdefault(casa, {})[serie] = {
            "n": len(xs), "mae": _mae(xs), "sesgo_medio": round(mean(xs), 3),
        }
    # comparación micro(válido) vs modelo, mismas elecciones
    elec_est = {m["eleccion"] for m in cis_est.values() if not m["postelectoral"]}
    mv = [s["err"] for s in series_val
          if s["serie"] == "micro_valid" and s["eleccion"] in elec_est]
    et = [s["err"] for s in series_val
          if s["serie"] == "est" and s["eleccion"] in elec_est]
    resumen["CIS_comparacion_mismo_conjunto"] = {
        "elecciones": sorted(elec_est),
        "n_micro_valid": len(mv), "n_est": len(et),
        "mae_micro_valid": _mae(mv), "mae_est": _mae(et),
        "sesgo_medio_micro_valid": round(mean(mv), 3),
        "sesgo_medio_est": round(mean(et), 3),
    }

    out = {
        "generado": "2026-10-15",
        "definiciones": {
            "encuesta_final_estricta": f"fin de campo dentro de los {STRICT_DAYS} días naturales previos a la votación",
            "encuesta_final_operativa": "última encuesta preelectoral de la casa con campo terminado antes de la votación (fallback documentado)",
            "error_firmado": "pct_encuesta - pct_real (misma base de porcentaje)",
            "k_encogimiento_eb": K_SHRINK,
        },
        "n_series": len(series),
        "series": series,
        "house_effects": he,
        "house_effects_serie_completa": he_all,
        "incumbencia": inc,
        "correcciones_eb": corr,
        "resumen": resumen,
        "observaciones_estricta_7d": strict_subset,
        "estudios_cis": {
            sid: {k: v for k, v in m.items() if k in (
                "estudio", "eleccion", "fecha_end", "end_source", "n",
                "calidad", "cobertura_partidos_censo", "ns_nc_censo",
                "valid_base_censo")}
            for sid, m in cis_micro.items()
        },
        "conteo": {
            "n_series": len(series),
            "n_series_validada": len(series_val),
            "por_casa_serie": {f"{casa}|{serie}": sum(p["n"] for p in parties.values())
                               for casa, sers in he.items()
                               for serie, parties in sers.items()},
            "elecciones_cis_micro": sorted({m["eleccion"] for m in cis_micro.values()}),
            "elecciones_cis_est": sorted({m["eleccion"] for m in cis_est.values()}),
        },
    }
    dest = ROOT / "data/processed/sesgo/house_effects.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(dest, "w"), ensure_ascii=False, indent=1, default=str)
    print("escrito", dest)
    print("n_series", len(series))
    print("casas/series:", list(out["conteo"]["por_casa_serie"]))
    return out


if __name__ == "__main__":
    main()
