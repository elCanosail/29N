#!/usr/bin/env python3
"""Normaliza los estudios CIS descargados a un esquema común + valida.

Entrada : data/raw/cis/<estudio>/... (microdatos) + data/raw/cis/manifest.json
          data/raw/cis/estimacion/est<estudio>.pdf|.txt (tabla publicada)
Salida (escritura atómica temp+rename):
  data/processed/cis/polls.jsonl        una línea por estudio × partido
  data/processed/cis/studies.json       catálogo normalizado con trazabilidad
  data/processed/cis/validation.json    validación vs. tablas publicadas (≤2015+)
  data/processed/cis/exclusions.json    estudios no normalizables y motivo

Reglas:
  * Parseo ASCII universal DA#### + ES####.
  * Selección de la variable de voto: si hay tabla publicada se elige la que
    MEJOR la reproduce (menos filas fuera de tolerancia, luego más filas
    comparadas, luego menor Δ máxima); si no, la de mayor puntuación heurística.
  * Los estudios con tipo == 'otro' NO entran en polls ni en validación: van a
    exclusions.json (su tabla publicada es de otro ámbito → comparación inválida).
  * Diccionario de partidos con aliases generales (party_aliases.csv) y aliases
    con ventana temporal por año (party_aliases_eras.csv).
  * Los partidos residuales no reconocidos se agregan en OTROS (así lo hace la
    propia tabla del CIS con "Otros partidos"); los códigos no-partido
    (N.P., No procede, consultar tarjeta, …) se descartan.
NO se maquilla ni se fuerza: lo que no cuadre queda como discrepancia/limitación.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_microdata as pm  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(BASE))
RAW = os.path.join(REPO, "data/raw/cis")
OUT = os.path.join(REPO, "data/processed/cis")

STRONG = ["PP", "PSOE", "PSC", "VOX", "PODEMOS", "IU", "CIUDADANOS", "ERC", "PNV",
          "BILDU", "BNG", "CUP", "SUMAR", "COMPROM", "MARE", "GEROA", "PRC", "PACMA",
          "UPYD", "CDS", "UCD", "AP", "PCE", "AMAIUR", "JUNTS", "PDECAT"]
MARKERS = ["blanco", "nulo", "absten", "no votar", "no votar\u00e1", "ns", "n.s.",
           "nc", "n.c.", "no decidido", "no lo tiene decidido", "no sabe", "no contesta"]
PREF_VARS = {"P9R", "P7R", "P10R", "P32R", "P24R", "INTENCIONG", "VOTOR"}

# etiquetas que NO son partido -> no se agregan a OTROS
NONPARTY = re.compile(
    r"(n\.?\s?p\.?$|no procede|no recuerda|no quiere contestar|no va a votar|"
    r"no votar[ií]a|no votar[aá]|no sabe|no contesta|no ten[ií]a edad|"
    r"no identificables|ninguno|ninguna|consultar tarjeta|a quien le dijesen)",
    re.I)


def alias_to_regex(alias):
    a = alias.upper()
    if re.fullmatch(r"[A-Z0-9+&' ]+", a) and a.isascii() and " " not in a:
        return re.compile(r"(?<![A-Z0-9])" + re.escape(a) + r"(?![A-Z0-9])")
    return re.compile(re.escape(a))


def _read_aliases(path):
    if not os.path.exists(path):
        return []
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    rows.sort(key=lambda r: int(re.sub(r"\D", "", r["priority"]) or 0))
    return rows


def load_aliases():
    gen = [(r["canonical"], alias_to_regex(r["alias"]))
           for r in _read_aliases(os.path.join(REPO, "pipeline/party_aliases.csv"))]
    eras = []
    for r in _read_aliases(os.path.join(BASE, "party_aliases_eras.csv")):
        d = int(r["desde"]) if (r.get("desde") or "").strip() else None
        h = int(r["hasta"]) if (r.get("hasta") or "").strip() else None
        eras.append((r["canonical"], alias_to_regex(r["alias"]), d, h))
    return gen, eras


ALIAS_GEN, ALIAS_ERA = load_aliases()


def canonize(label, anio=None):
    """Mapea una etiqueta a partido canónico; los aliases con ventana temporal
    solo aplican si el año del estudio cae dentro de [desde, hasta]."""
    u = label.upper().strip()
    if anio is not None:
        for canon, rx, d, h in ALIAS_ERA:
            if (d is None or anio >= d) and (h is None or anio <= h) and rx.search(u):
                return canon
    for canon, rx in ALIAS_GEN:
        if rx.search(u):
            return canon
    return None


def is_party_residual(label):
    """Etiqueta no reconocida: ¿es un partido residual (→ OTROS) o un código
    no-partido (se descarta)?"""
    u = label.strip()
    if not u:
        return False
    if re.fullmatch(r"[\d\s\.,-]+", u):   # códigos numéricos / tarjeta
        return False
    if NONPARTY.search(u):
        return False
    return True


# ------------------------------------------------------------------ parseo

def var_labels(es_path):
    txt = open(es_path, encoding="latin-1").read()
    vl = {}
    for m in re.finditer(r"/([A-Za-z]\w*)\s+'([^']*)'", txt):
        vl.setdefault(m.group(1), m.group(2))
    return vl


def candidates(vl, vlabels):
    out = []
    for v, labs in vl.items():
        if not labs:
            continue
        joined = " ; ".join(labs.values())
        nu = joined.upper()
        nstrong = sum(1 for s in STRONG if re.search(r"(?<![A-Z])" + s + r"(?![A-Z])", nu))
        if nstrong < 3:
            continue
        marc = sum(1 for m in MARKERS if m in joined.lower())
        combos = sum(1 for x in labs.values() if "/" in x)
        score = nstrong * 2 + marc * 3 - combos * 3
        if v.endswith("R"):
            score += 8
        if v in PREF_VARS:
            score += 4
        low = (vlabels.get(v, "") + " " + v).lower()
        if "voto" in low or "intenci" in low:
            score += 4
        if "duda" in low or "entre los que" in low or "bcomb" in low or re.search(r"b0[12]", low):
            score -= 12
        out.append((score, v))
    out.sort(reverse=True)
    return [v for _s, v in out]


def find_data(est):
    for root in (os.path.join(RAW, est), os.path.join(RAW, f"MD{est}")):
        if not os.path.isdir(root):
            continue
        for dirpath, _d, files in os.walk(root):
            es = [f for f in files if re.fullmatch(r"ES\d+", f)]
            da = [f for f in files if re.fullmatch(r"DA\d+", f)]
            if es and da:
                return os.path.join(dirpath, es[0]), os.path.join(dirpath, da[0])
    return None, None


def weighted_distribution(da, spec, order, var, weight="PESO"):
    tot = 0.0
    counts = defaultdict(float)
    n = 0
    for rec in pm.read_records(da, spec, order):
        w = rec.get(weight)
        if w is None:
            continue
        tot += w
        counts[rec.get(var)] += w
        n += 1
    return counts, tot, n


def distribution_by_canon(counts, tot, labs, anio=None):
    """Agrega por partido canónico.

    Las etiquetas no reconocidas por el diccionario NO se fuerzan a OTROS: se
    registran en `residual` y se descartan del reparto (evidencia: forzarlas a
    OTROS reproduce 3411 pero rompe 3263/3367/3458, donde el CIS NO las agrupa
    en "Otros partidos"). Queda como limitación documentada.
    """
    d = defaultdict(float)
    residual = []
    for code, w in counts.items():
        lab = labs.get(str(code))
        if lab is None:
            continue
        c = canonize(lab, anio)
        if c is None:
            residual.append(lab)
            continue
        d[c] += 100.0 * w / tot
    return {k: v for k, v in d.items()}, sorted(set(residual))


# -------------------------------------------------------------- validación

ROW = re.compile(r"^\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ(][^\n]*?)\s{2,}(\d+,\d+)(?:\s|$)", re.M)


def published_table(est, anio=None):
    txt = os.path.join(RAW, "estimacion", f"est{est}.txt")
    pdf = os.path.join(RAW, "estimacion", f"est{est}.pdf")
    if not os.path.exists(txt) and os.path.exists(pdf):
        try:
            subprocess.run(["pdftotext", "-layout", pdf, txt], check=True, timeout=60)
        except Exception:
            return None
    if not os.path.exists(txt):
        return None
    data = open(txt, encoding="utf-8", errors="replace").read()
    start = data.find("Voto directo")
    if start > 0:
        data = data[start:]
    cut = data.find("ESTIMACIÓN DE ESCAÑOS")
    if cut > 0:
        data = data[:cut]
    table = defaultdict(float)
    for m in ROW.finditer(data):
        label = m.group(1).strip().rstrip("-").strip()
        pct = float(m.group(2).replace(",", "."))
        if len(label) > 45:
            continue
        # misma canonización (con el año del estudio) que los microdatos:
        # si no, los aliases con ventana temporal aplicarían a un solo lado.
        canon = canonize(label, anio)
        if canon:
            table[canon] += pct
    return dict(table) or None


def score_against_var(dist, table, tolerance=0.2):
    common = [k for k in table if k in dist]
    if not common:
        return (-1, 0, -999.0)
    diffs = [abs(dist[k] - table[k]) for k in common]
    bad = sum(1 for d in diffs if d > tolerance)
    return (-bad, len(common), -max(diffs))


# ------------------------------------------------------------ escritura atómica

def atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_lines(path, lines):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln)
            f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=os.path.join(BASE, "catalog.json"))
    ap.add_argument("--tolerance", type=float, default=0.2)
    args = ap.parse_args()

    cat = {r["estudio"]: r for r in json.load(open(args.catalog))}
    mpath = os.path.join(RAW, "manifest.json")
    man = json.load(open(mpath)) if os.path.exists(mpath) else {}
    os.makedirs(OUT, exist_ok=True)

    studies, exclusions, polls, validation = [], [], [], []
    for est, rec in sorted(cat.items(), key=lambda kv: kv[1]["fecha_trabajo"][-4:]):
        es, da = find_data(est)
        if not es:
            continue  # no descargado
        if rec["tipo"] == "otro":
            exclusions.append({"estudio": est, "slug": rec["slug"],
                               "eleccion": rec["eleccion"], "tipo": rec["tipo"],
                               "motivo": "tipo 'otro': fuera de ámbito preelectoral/"
                                         "postelectoral; no entra en polls ni validación"})
            continue
        spec, order, vl = pm.parse_es(es)
        if "PESO" not in spec:
            exclusions.append({"estudio": est, "slug": rec["slug"], "motivo": "sin PESO"})
            continue
        anio = rec.get("anio")
        vlabels = var_labels(es)
        cands = candidates(vl, vlabels)
        if not cands:
            exclusions.append({"estudio": est, "slug": rec["slug"],
                               "motivo": "no se detecta variable de voto"})
            continue
        table = published_table(est, anio)
        chosen, chosen_var = None, None
        if table:
            best = None
            for v in cands[:6]:
                counts, tot, n = weighted_distribution(da, spec, order, v)
                if tot <= 0:
                    continue
                dist, _ = distribution_by_canon(counts, tot, vl.get(v, {}), anio)
                sc = score_against_var(dist, table, args.tolerance)
                if best is None or sc > best[0]:
                    best = (sc, (counts, tot, n, dist), v)
            if best is None:
                counts, tot, n = weighted_distribution(da, spec, order, cands[0])
                dist, _ = distribution_by_canon(counts, tot, vl.get(cands[0], {}), anio)
                chosen, chosen_var = (counts, tot, n, dist), cands[0]
            else:
                _sc, chosen, chosen_var = best
        else:
            counts, tot, n = weighted_distribution(da, spec, order, cands[0])
            dist, _ = distribution_by_canon(counts, tot, vl.get(cands[0], {}), anio)
            chosen, chosen_var = (counts, tot, n, dist), cands[0]

        counts, tot, n, _ = chosen
        dist, residual = distribution_by_canon(counts, tot, vl.get(chosen_var, {}), anio)

        for canon, pct in sorted(dist.items()):
            polls.append({"estudio_id": est, "fecha_trabajo": rec["fecha_trabajo"],
                          "tipo": rec["tipo"], "ambito": rec["ambito"],
                          "eleccion": rec["eleccion"], "anio": anio,
                          "partido": canon, "voto_pct": round(pct, 3),
                          "variable": chosen_var, "n": n,
                          "suma_pesos": round(tot, 2), "fuente_url": rec["url"]})
        studies.append({"estudio": est, "fecha_trabajo": rec["fecha_trabajo"],
                        "slug": rec["slug"], "url": rec["url"], "tipo": rec["tipo"],
                        "ambito": rec["ambito"], "eleccion": rec["eleccion"],
                        "anio": anio, "n": n, "suma_pesos": round(tot, 2),
                        "variable_voto": chosen_var, "n_partidos": len(dist),
                        "residuales_en_otros": residual[:25],
                        "candidatas": cands[:5]})
        if table:
            diffs = [{"partido": k, "publicado": table[k], "microdatos": round(dist[k], 2),
                      "delta": round(abs(dist[k] - table[k]), 2)}
                     for k in table if k in dist]
            bad = [d for d in diffs if d["delta"] > args.tolerance]
            missing = [k for k in table if k not in dist]
            validation.append({"estudio": est, "variable": chosen_var,
                               "filas_comparadas": len(diffs),
                               "max_delta": max((d["delta"] for d in diffs), default=None),
                               "discrepancias": bad, "publicado_no_reproducido": missing,
                               "ok": not bad})
        print(f"OK {est} var={chosen_var} n={n} partidos={len(dist)}"
              + (f" valid={'OK' if validation and validation[-1]['estudio']==est and validation[-1]['ok'] else 'REVISAR'}"
                 if table else ""), file=sys.stderr)

    atomic_write_lines(os.path.join(OUT, "polls.jsonl"),
                       [json.dumps(p, ensure_ascii=False) for p in polls])
    atomic_write_json(os.path.join(OUT, "studies.json"), studies)
    atomic_write_json(os.path.join(OUT, "validation.json"), validation)
    atomic_write_json(os.path.join(OUT, "exclusions.json"), exclusions)
    ok = sum(1 for v in validation if v["ok"])
    print(json.dumps({"estudios": len(studies), "filas": len(polls),
                      "validados_ok": ok, "validados_total": len(validation),
                      "exclusiones": len(exclusions)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
