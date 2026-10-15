#!/usr/bin/env python3
"""Fase 4-c — Extraccion del valor INDIVIDUAL de los microdatos CIS.

Entrada (SOLO LECTURA):
  data/raw/cis/<estudio>/...            ASCII DA#### + ES#### (universal)
  data/raw/cis/manifest.json
  pipeline/cis/catalog.json             metadatos (fecha, anio, eleccion, tipo)
  data/processed/cis/studies.json       variable de voto ya validada por estudio
  pipeline/cis/parse_microdata.py       parser ASCII (reutilizado)
  pipeline/cis/normalize.py             canonizador de partidos (reutilizado, import)

Salida (escritura SOLO en data/processed/microdatos/):
  individual.parquet                    un registro por individuo x estudio
  cobertura.json                        matriz estudio x era: variable presente/ausente
  extraction.json                       resumen (n estudios, n individuos, huecos)

Motivo del uso universal del ASCII DA/ES: el fichero ASCII existe en TODOS los
estudios descargados (con o sin .sav/.csv) y es exactamente lo que consume el
parser ya validado de Fase 1. El `.sav` (2018-2022) y el `.csv` (>=2023) son
serializaciones del MISMO contenido; se usan solo para comprobacion cruzada
(ver `--check-sav`). Asi se evita reimplementar el parseo por formato.

ejecutar:
  python3 pipeline/microdatos/extract_individual.py
  python3 pipeline/microdatos/extract_individual.py --check-sav 3141
"""
import argparse
import collections
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(BASE))
sys.path.insert(0, os.path.join(REPO, "pipeline", "cis"))
import parse_microdata as pm          # noqa: E402
import normalize as nz                # noqa: E402  (canonize, find_data, var_labels, candidates)

RAW = os.path.join(REPO, "data/raw/cis")
OUT = os.path.join(REPO, "data/processed/microdatos")
CATALOG = os.path.join(REPO, "pipeline/cis/catalog.json")
STUDIES = os.path.join(REPO, "data/processed/cis/studies.json")

TARGETS = ["provincia", "edad", "sexo", "estudios", "situacion_laboral", "tamuni",
           "ideologia", "interes_politica", "recuerdo_voto", "intencion_voto",
           "religiosidad", "peso"]

# ------------------------------- deteccion de variables (por etiquetas, no por nombre)
RE_NSNC = re.compile(r"n\.?\s?c\.?$|n\.?\s?s\.?$|no contesta|no sabe|no procede|n\.p\.?$", re.I)


def _labs(vlabels):
    return {v: (vlabels.get(v) or "").lower() for v in vlabels}


def _pick(order, low, pattern, exclude=None):
    """Primer var cuyo label case el regex `pattern` (y no el `exclude`)."""
    rx = re.compile(pattern)
    rx_ex = re.compile(exclude) if exclude else None
    for v in order:
        lab = low.get(v, "")
        if rx.search(lab) and not (rx_ex and rx_ex.search(lab)):
            return v
    return None


def detect_vars(spec, order, vl, vlabels):
    low = _labs(vlabels)
    d = {}

    # provincia (codigo INE 1-52). Descartar variantes [ANULADA]/nacimiento/autonomia.
    for v in order:
        if v == "PROV" and "anulada" not in low.get(v, ""):
            d["provincia"] = v
            break
    else:
        d["provincia"] = _pick(order, low, r"^provincia", r"anulada|nacimiento|ccaa|comunidad")

    # edad (fallback por nombre para ES sin VARIABLE LABELS, p.ej. 2757/7708)
    d["edad"] = ("EDAD" if "EDAD" in spec else
                 "edad" if "edad" in spec else
                 _pick(order, low, r"^edad\b"))

    # sexo
    d["sexo"] = ("SEXO" if "SEXO" in spec else
                 "sexo" if "sexo" in spec else
                 _pick(order, low, r"^sexo"))

    # nivel de estudios: se prefiere la recodificada armonizada ESTUDIOS
    if "ESTUDIOS" in spec:
        d["estudios"] = "ESTUDIOS"
    elif "NIVELESTENTREV" in spec:
        d["estudios"] = "NIVELESTENTREV"
    else:
        d["estudios"] = _pick(order, low, r"nivel de estudios|^estudios\b|estudios alcanzados?|estudios complet")

    # situacion laboral
    d["situacion_laboral"] = ("SITLAB" if "SITLAB" in spec else
                              _pick(order, low, r"^situaci[oó]n laboral"))

    # tamano de municipio / habitat
    d["tamuni"] = ("TAMUNI" if "TAMUNI" in spec else
                   _pick(order, low, r"tama[nñ]o (de|del) (municipio|h[aá]bitat)"))

    # ideologia autoubicada 1-N (excluye padre/madre/atribuida/partido).
    # OJO: en latin-1 'ideologica' lleva '\xf3' y NO contiene la subcadena
    # 'ideolog'; la raiz segura es 'ideol'.
    # Regla reforzada: entre las candidatas se prefiere la que es REALMENTE una
    # escala izquierda-derecha (sus VALUE LABELS contienen 'izquierda' y
    # 'derecha'), porque hay variables con 'ideologia' en la etiqueta que no son
    # la autoubicacion (p. ej. 3458 PARTIDOSUE_2 'valores, ideologia, etc.' o
    # 3269 A11 'Autodefinicion...' = familias ideologicas, no 1-10).
    d["ideologia"] = None
    cands_ideo = [v for v in order if "ideol" in low.get(v, "") and
                  not re.search(r"padre|madre|atribuid|partido|personas", low.get(v, ""))]

    def _es_escala_lr(v):
        j = " ".join((vl.get(v) or {}).values()).lower()
        return "izquierda" in j and "derecha" in j

    lr = [v for v in cands_ideo if _es_escala_lr(v)]
    if lr:
        # si hay varias, la que se anuncie como escala/autoubicacion
        lr.sort(key=lambda v: ("autoubicaci" not in low[v] and "escala" not in low[v],
                               order.index(v)))
        d["ideologia"] = lr[0]
    else:
        # Escalas 1-10 con los codigos 1..10 SIN etiqueta (VALUE LABELS solo trae
        # N.S./N.C.): 1533/2207/2210 'Escala de autoubicacion ideologica (1-10)',
        # 2104 'Escala de ideologia'. Se aceptan solo si la etiqueta lo declara
        # como escala/autoubicacion de ideologia (excluye 3458 PARTIDOSUE_2
        # 'valores, ideologia, etc.' y 3269 A11 'Autodefinicion...').
        alt = [v for v in cands_ideo
               if "autoubicaci" in low[v] or ("escala" in low[v] and "ideol" in low[v])]
        if alt:
            alt.sort(key=lambda v: order.index(v))
            d["ideologia"] = alt[0]

    # interes por la politica (no por la campana ni noticias)
    d["interes_politica"] = _pick(order, low, r"inter[eé]s por la pol[ií]tica")

    # religiosidad (no frecuencia de asistencia)
    d["religiosidad"] = ("RELIGION" if "RELIGION" in spec else
                         _pick(order, low, r"religiosidad", r"frecuencia|asistencia"))

    # recuerdo de voto: recodificada armonizada, si existe
    rec = None
    if "RECUERDO" in spec and re.search(r"recuerdo", low.get("RECUERDO", "")):
        rec = "RECUERDO"
    if rec is None:
        for v in ("RECUVOTOG", "RECUVOTOGR"):
            if v in spec:
                rec = v
                break
    if rec is None:
        rec = _pick(order, low, r"recuerdo de voto.*generales", r"de los votantes|recodificada")
    d["recuerdo_voto"] = rec

    return d


# ------------------------------------------------ canonizacion de etiquetas de voto
CAT_RULES = [
    (re.compile(r"no vot|absten", re.I), "ABSTENCION"),
    (re.compile(r"no pudo votar|no pudieron votar", re.I), "ABSTENCION"),
    (re.compile(r"en blanco|voto blanco|blanco", re.I), "BLANCO"),
    (re.compile(r"nul[oa]", re.I), "NULO"),
    (re.compile(r"no sabe|n\.?\s?s\.?$", re.I), "NS"),
    (re.compile(r"no contesta|n\.?\s?c\.?$", re.I), "NC"),
    (re.compile(r"no decid|no lo tiene decid|duda|ya ver|depende", re.I), "NO_DECIDIDO"),
]


def canon_vote(label, anio):
    """Partido canonico si el diccionario lo reconoce; si no, categoria de no-voto;
    si no, 'OTRO' (residual, trazable)."""
    if label is None:
        return None
    c = nz.canonize(label, anio)
    if c:
        return c
    for rx, tok in CAT_RULES:
        if rx.search(label):
            return tok
    return "OTRO"


# ------------------------------------------------------------- extraccion por estudio
def extract_study(est, meta, var_voto_hint):
    es, da = nz.find_data(est)
    if not es:
        return None, {"estudio": est, "motivo": "sin ASCII DA/ES"}
    spec, order, vl = pm.parse_es(es)
    vlabels = nz.var_labels(es)
    d = detect_vars(spec, order, vl, vlabels)

    # variable de intencion de voto: la validada si la hay, si no la heuristica
    if var_voto_hint and var_voto_hint in spec:
        d["intencion_voto"] = var_voto_hint
        voto_src = "validada(studies.json)"
    else:
        cands = nz.candidates(vl, vlabels)
        d["intencion_voto"] = cands[0] if cands else None
        voto_src = "heuristica(candidates)"

    # peso: PESO nacional preferente, luego variantes
    peso_var = None
    for v in ("PESO", "PESOCCAA", "PESOPROV", "PESOA", "PESO2", "PESO1", "peso"):
        if v in spec:
            peso_var = v
            break
    if peso_var is None:
        cand = [v for v in order if "peso" in v.lower()]
        peso_var = cand[0] if cand else None
    d["peso"] = peso_var
    if peso_var is None:
        return None, {"estudio": est, "motivo": "sin variable de ponderacion"}

    anio = meta.get("anio")
    labs_ideo = vl.get(d["ideologia"] or "", {})
    ideo_scale = 10
    ideo_scale_fuente = "default"
    if d["ideologia"]:
        m = re.search(r"\(\s*1\s*-\s*(\d+)\s*\)", low_ideo_lab := vlabels.get(d["ideologia"], ""))
        if m:
            ideo_scale = int(m.group(1))
            ideo_scale_fuente = "etiqueta"
        elif labs_ideo:
            codes = [int(k) for k in labs_ideo if re.fullmatch(r"\d+", k)]
            codes = [c for c in codes if 1 <= c <= 11]
            if codes:
                ideo_scale = max(codes)
                ideo_scale_fuente = "value_labels"

    # edad: detectar uso de tramos (etiquetas) vs anos
    edad_var = d["edad"]
    edad_labs = vl.get(edad_var or "", {})
    edad_tramos = False
    if edad_labs:
        real = [k for k, v in edad_labs.items() if not RE_NSNC.search(v)]
        if len(real) > 3:
            edad_tramos = True

    rows = []
    for rec in pm.read_records(da, spec, order):
        w = rec.get(peso_var)
        if w is None or w <= 0:
            continue
        prov = rec.get(d["provincia"]) if d["provincia"] else None
        if isinstance(prov, str):
            prov = int(re.sub(r"\D", "", prov) or 0)
        edad = rec.get(edad_var) if edad_var else None
        if edad_tramos and isinstance(edad, (int, float)):
            lab = edad_labs.get(str(int(edad)), "")
            rng = re.findall(r"\d+", lab)
            if len(rng) >= 2:
                edad = (int(rng[0]) + int(rng[1])) / 2.0
            elif len(rng) == 1:
                edad = float(rng[0])
            else:
                edad = None
        sexo_lab = None
        if d["sexo"]:
            s = rec.get(d["sexo"])
            sexo_lab = vl.get(d["sexo"], {}).get(str(s))
        est_lab = None
        if d["estudios"]:
            e = rec.get(d["estudios"])
            est_lab = vl.get(d["estudios"], {}).get(str(e))
        s_lab = None
        if d["situacion_laboral"]:
            s = rec.get(d["situacion_laboral"])
            s_lab = vl.get(d["situacion_laboral"], {}).get(str(s))

        ideo = None
        if d["ideologia"]:
            iv = rec.get(d["ideologia"])
            if isinstance(iv, (int, float)) and 1 <= iv <= ideo_scale:
                ideo = float(iv)
                if ideo_scale != 10:  # reescalar 1-7 -> 1-10 (documentado)
                    ideo = 1 + (ideo - 1) * 9.0 / (ideo_scale - 1)

        raw_voto = None
        if d["intencion_voto"]:
            raw_voto = vl.get(d["intencion_voto"], {}).get(str(rec.get(d["intencion_voto"])))
        raw_rec = None
        if d["recuerdo_voto"]:
            raw_rec = vl.get(d["recuerdo_voto"], {}).get(str(rec.get(d["recuerdo_voto"])))

        rows.append({
            "estudio_id": est,
            "fecha_trabajo": meta.get("fecha_trabajo"),
            "anio": anio,
            "eleccion": meta.get("eleccion"),
            "provincia": prov if isinstance(prov, int) and 1 <= prov <= 52 else None,
            "peso": float(w),
            "edad": float(edad) if isinstance(edad, (int, float)) else None,
            "sexo": sexo_lab,
            "estudios": est_lab,
            "ideologia_1a10": ideo,
            "interes_politica": (vl.get(d["interes_politica"], {}).get(str(rec.get(d["interes_politica"])))
                                 if d["interes_politica"] else None),
            "recuerdo_voto": canon_vote(raw_rec, anio),
            "intencion_voto": canon_vote(raw_voto, anio),
            "religiosidad": (vl.get(d["religiosidad"], {}).get(str(rec.get(d["religiosidad"])))
                             if d["religiosidad"] else None),
            # --- extra (auditoria) ---
            "tipo_estudio": meta.get("tipo"),
            "ambito": meta.get("ambito"),
            "peso_var": peso_var,
            "ideologia_var": d["ideologia"],
            "ideologia_escala": ideo_scale if d["ideologia"] else None,
            "intencion_var": d["intencion_voto"],
            "intencion_src": voto_src,
            "recuerdo_var": d["recuerdo_voto"],
            "intencion_voto_raw": raw_voto,
            "recuerdo_voto_raw": raw_rec,
        })

    # Escala de ideologia no declarada en etiqueta ni en VALUE LABELS (p.ej.
    # 2104 'Escala de ideología'): se infiere del maximo observado y se reescala
    # a 1-10 si difiere (documentado en la nota de metodo).
    if d["ideologia"] and ideo_scale_fuente == "default":
        obs = [r["ideologia_1a10"] for r in rows if r["ideologia_1a10"]]
        if obs:
            mx = int(max(obs))
            if 1 < mx <= 11 and mx != 10:
                ideo_scale, ideo_scale_fuente = mx, "observado"
                for r in rows:
                    if r["ideologia_1a10"]:
                        r["ideologia_1a10"] = 1 + (r["ideologia_1a10"] - 1) * 9.0 / (mx - 1)

    cov = {"estudio": est, "anio": anio, "tipo": meta.get("tipo"),
           "eleccion": meta.get("eleccion"), "n_individuos": len(rows),
           "suma_pesos": round(sum(r["peso"] for r in rows), 2),
           "variables": {k: d.get(k) for k in TARGETS},
           "intencion_src": voto_src, "edad_tramos": edad_tramos,
           "ideologia_escala": ideo_scale if d["ideologia"] else None}
    return rows, cov


# ------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="solo N estudios (prueba)")
    ap.add_argument("--check-sav", default=None, help="estudio .sav para comprobar contra ASCII")
    args = ap.parse_args()

    cat = {r["estudio"]: r for r in json.load(open(CATALOG))}
    hints = {}
    if os.path.exists(STUDIES):
        for r in json.load(open(STUDIES)):
            hints[r["estudio"]] = r.get("variable_voto")
    man = json.load(open(os.path.join(RAW, "manifest.json"))) if os.path.exists(os.path.join(RAW, "manifest.json")) else {}

    dirs = [d for d in os.listdir(RAW)
            if os.path.isdir(os.path.join(RAW, d)) and d not in ("pages", "estimacion", "catalog")]
    ests = sorted({re.search(r"\d+", d).group(0) for d in dirs if re.search(r"\d+", d)},
                  key=lambda e: (cat.get(e, {}).get("anio") or 0, e))
    if args.limit:
        ests = ests[:args.limit]

    all_rows, cov, exclusions = [], [], []
    for est in ests:
        meta = dict(cat.get(est, {}))
        if not meta.get("anio") and meta.get("fecha_trabajo"):
            m = re.search(r"(19|20)\d{2}", meta["fecha_trabajo"])
            meta["anio"] = int(m.group(0)) if m else None
        rows, info = extract_study(est, meta, hints.get(est))
        if rows is None:
            exclusions.append({**info, "slug": man.get(est, {}).get("slug")})
            continue
        all_rows.extend(rows)
        cov.append(info)
        print(f"  {est} n={info['n_individuos']:>6} votovar={info['variables'].get('intencion_voto')}"
              f" prov={'ok' if info['variables'].get('provincia') else '--'}"
              f" ideo={info['variables'].get('ideologia') or '--'}", file=sys.stderr)

    # --- escritura
    os.makedirs(OUT, exist_ok=True)
    import pandas as pd
    df = pd.DataFrame(all_rows)
    df = df.sort_values(["estudio_id", "anio"]).reset_index(drop=True)
    tmp = os.path.join(OUT, "individual.parquet.tmp")
    df.to_parquet(tmp, index=False, compression="zstd")
    os.replace(tmp, os.path.join(OUT, "individual.parquet"))

    def aw(path, obj):
        t = path + ".tmp"
        with open(t, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(t, path)

    aw(os.path.join(OUT, "cobertura.json"), cov)
    summary = {
        "estudios_extraidos": len(cov),
        "estudios_excluidos": len(exclusions),
        "individuos": int(len(df)),
        "columnas": list(df.columns),
        "archivo": "data/processed/microdatos/individual.parquet",
        "exclusiones": exclusions,
        "cobertura_objetivo": {t: sum(1 for c in cov if c["variables"].get(t)) for t in TARGETS},
        "por_decada": dict(collections.Counter(f"{(c['anio'] or 0)//10*10}s" for c in cov)),
    }
    aw(os.path.join(OUT, "extraction.json"), summary)

    if args.check_sav:
        _check_sav(args.check_sav, df)

    print(json.dumps({k: v for k, v in summary.items() if k not in ("columnas", "exclusiones")},
                     ensure_ascii=False))


def _check_sav(est, df):
    """Comprobacion cruzada ASCII vs .sav con pyreadstat (venv 29n-micro)."""
    import subprocess
    es, da = nz.find_data(est)
    sav = None
    for root in (os.path.join(RAW, est), os.path.join(RAW, f"MD{est}")):
        for dp, _d, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(".sav"):
                    sav = os.path.join(dp, f)
    if not sav:
        print(f"[check-sav] {est}: sin .sav", file=sys.stderr)
        return
    code = ("import pyreadstat,sys\n"
            "d,meta=pyreadstat.read_sav(sys.argv[1])\n"
            "print(len(d), list(d.columns)[:8])\n")
    r = subprocess.run(["/root/.venvs/29n-micro/bin/python", "-c", code, sav],
                       capture_output=True, text=True)
    n_ascii = int((df["estudio_id"] == est).sum())
    print(f"[check-sav] {est}: ascii_n={n_ascii} sav_n={r.stdout.strip()}", file=sys.stderr)


if __name__ == "__main__":
    main()
