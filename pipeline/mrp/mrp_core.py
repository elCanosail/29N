#!/usr/bin/env python3
"""Fase 4-c (segundo uso) — MRP (Multilevel Regression and Post-stratification)
pragmático para la predicción provincial del 29N.

Qué hace
--------
1. **Regresión** multinomial de la intención de voto individual sobre
   `edad × sexo × estudios` (interacción completa) + **efecto provincial**
   (dummies por provincia con regularización L2 ⇒ encogimiento hacia la media
   nacional, el papel que en un MRP canónico juega el efecto aleatorio).
2. **Post-estratificación**: las probabilidades por celda se agregan con los
   denominadores censales (INE tabla 66600) por provincia × sexo × edad × estudios.

Es deliberadamente *pragmático*: un modelo multinomial con logits lineales y una
post-estratificación por celdas censales. Nada de MCMC: con 52 provincias y
~1.000-2.000 entrevistas por estudio, un modelo jerárquico completo no aporta
sobre esta estructura y hace el backtest irreproducible en minutos.

Alternativa simple incluida
---------------------------
`cell_means_poststrat()` implementa la versión sin modelo (medias de celda
ponderadas con encogimiento hacia la media demográfica nacional). Sirve para
justificar, con el backtest, si la regresión multinomial compensa.

Solo lectura sobre `data/processed/microdatos|interior|modelo`.
"""

from __future__ import annotations

import json
import math
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"
MRP = DATA / "mrp"

sys.path.insert(0, str(ROOT / "pipeline" / "sesgo"))
from party_canon import canonical_of_slug  # noqa: E402

# --- Universo de partidos (idéntico al del modelo estatal) -------------------
MODELED_PARTIES = [
    "PP", "PSOE", "VOX", "SUMAR",
    "ERC", "JXCAT", "PNV", "EH BILDU", "BNG", "CUP", "CC", "NA+", "PACMA",
]
# En el backtest 2015-2019 Ciudadanos pesa hasta un 14 %: incluirlo evita que
# la renormalización al universo modelado distorsione la comparación.
BACKTEST_PARTIES = MODELED_PARTIES + ["CIUDADANOS"]

# `interior/dhondt` umbral legal Congreso
DHONDT_THRESHOLD = 0.03

# --- Celdas demográficas -----------------------------------------------------
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"]
EDU_GROUPS = ["BAJO", "MEDIO", "ALTO"]
SEXOS = ["hombre", "mujer"]
DEMO_CATS = [f"{s}|{a}|{e}" for s in SEXOS for a in AGE_GROUPS for e in EDU_GROUPS]
PROV_CATS = [str(i) for i in range(1, 53)]
FEATURES = [f"demo:{d}" for d in DEMO_CATS] + [f"prov:{p}" for p in PROV_CATS]
FEATURE_INDEX = {f: i for i, f in enumerate(FEATURES)}

# --- Canonicalización de la intención/recuerdo de voto -----------------------
FAMILY = {"IU": "SUMAR", "PODEMOS": "SUMAR", "UNIDAS PODEMOS": "SUMAR"}
NON_PARTY = {
    "ABSTENCION": "ABSTENCION",
    "NS": "NO_DECIDIDO", "NC": "NO_DECIDIDO", "NO DECIDIDO": "NO_DECIDIDO",
    "EN BLANCO": "BLANCO", "VOTO NULO": "NULO",
    "OTRO": "OTROS", "OTROS": "OTROS",
}
RESIDUAL_ORDER = ["ABSTENCION", "NO_DECIDIDO", "BLANCO", "NULO", "OTROS"]

# --- Educación: etiquetas CIS -> 3 grupos (mismo mapa que las censales) ------
# Normalizadas a minúsculas sin espacios redundantes.
EDU_CIS = {
    "sin estudios": "BAJO",
    "primaria": "BAJO",
    "menos de estudios primarios, sabe leer (menos de 6 años de escuela)": "BAJO",
    "menos de estudios primarios, no sabe leer": "BAJO",
    "estudios primarios completos, cultura general": "BAJO",
    "estudios completos, cultura general": "BAJO",
    "f.p.": "MEDIO",
    "fp": "MEDIO",
    "formación profesional": "MEDIO",
    "estudios de formación profesional": "MEDIO",
    "secundaria": "MEDIO",
    "secundaria 1ª etapa": "MEDIO",
    "secundaria 2ª etapa": "MEDIO",
    "bachiller elemental": "MEDIO",
    "bachiller superior": "MEDIO",
    "grado medio": "MEDIO",
    "cualificación profesional": "MEDIO",
    "otros": "MEDIO",
    "otros no reglados": "MEDIO",
    "superiores": "ALTO",
    "medios universitarios": "ALTO",
    "universitarios o técnicos de grado superior": "ALTO",
    "estudios de grado medio (peritajes, magisterio)": "ALTO",
    "estudios de grado medio": "ALTO",
}
# 'Blanco', 'N.C.' y vacíos => sin dato


def age_group_of(a):
    if a is None or (isinstance(a, float) and math.isnan(a)):
        return None
    a = float(a)
    if a < 18 or a > 110:
        return None
    if a < 25:
        return "18-24"
    if a < 35:
        return "25-34"
    if a < 45:
        return "35-44"
    if a < 55:
        return "45-54"
    if a < 65:
        return "55-64"
    if a < 75:
        return "65-74"
    return "75+"


def edu_group_of(e):
    if e is None or (isinstance(e, float) and math.isnan(e)):
        return None
    key = " ".join(str(e).strip().lower().split())
    return EDU_CIS.get(key)


def canon_class(v, universe):
    """Etiqueta de intención/recuerdo -> clase del modelo (o None si no hay dato)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip()
    if not s:
        return None
    c = FAMILY.get(s, s)
    if c in universe:
        return c
    return NON_PARTY.get(s.upper(), "OTROS")


# --------------------------------------------------------------------------- #
# Microdatos
# --------------------------------------------------------------------------- #
def load_microdata(universe) -> pd.DataFrame:
    """individual.parquet -> filas utilizables con columnas del modelo."""
    cols = ["estudio_id", "fecha_trabajo", "anio", "eleccion", "tipo_estudio",
            "ambito", "provincia", "peso", "edad", "sexo", "estudios",
            "intencion_voto", "recuerdo_voto"]
    df = pd.read_parquet(DATA / "microdatos" / "individual.parquet", columns=cols)
    df["fecha"] = pd.to_datetime(df["fecha_trabajo"], format="%d/%m/%Y",
                                 errors="coerce")
    df["edad_grupo"] = df["edad"].map(age_group_of)
    df["edu_grupo"] = df["estudios"].map(edu_group_of)
    df["sexo_n"] = df["sexo"].map({"Hombre": "hombre", "Mujer": "mujer"})
    df["clase"] = df["intencion_voto"].map(lambda v: canon_class(v, universe))
    df["clase_rec"] = df["recuerdo_voto"].map(lambda v: canon_class(v, universe))
    df["prov"] = pd.to_numeric(df["provincia"], errors="coerce")
    df["peso"] = pd.to_numeric(df["peso"], errors="coerce").fillna(0.0)
    df["demo"] = (df["sexo_n"].astype("string") + "|" + df["edad_grupo"].astype("string")
                  + "|" + df["edu_grupo"].astype("string"))
    return df


def usable(df: pd.DataFrame) -> pd.DataFrame:
    m = (df["clase"].notna() & df["demo"].notna() & df["prov"].notna()
         & df["peso"] > 0)
    out = df.loc[m, ["estudio_id", "fecha", "prov", "peso", "demo", "clase"]].copy()
    out["prov"] = out["prov"].astype(int).astype(str)
    return out


def usable_anchored(df: pd.DataFrame) -> pd.DataFrame:
    """Como `usable` pero exigiendo también recuerdo de voto (codificador anclado)."""
    m = (df["clase"].notna() & df["clase_rec"].notna() & df["demo"].notna()
         & df["prov"].notna() & df["peso"] > 0)
    out = df.loc[m, ["estudio_id", "fecha", "prov", "peso", "demo", "clase",
                     "clase_rec"]].copy()
    out["prov"] = out["prov"].astype(int).astype(str)
    return out


def study_table(df: pd.DataFrame) -> pd.DataFrame:
    g = (df.groupby("estudio_id")
           .agg(fecha=("fecha", "first"), anio=("anio", "first"),
                eleccion=("eleccion", "first"), tipo=("tipo_estudio", "first"),
                ambito=("ambito", "first"), n=("estudio_id", "size"),
                n_usable=("clase", lambda s: s.notna().sum()))
           .reset_index())
    return g.sort_values("fecha")


def training_set(df: pd.DataFrame, cut, window_days: int,
                 amb_ok=("estatal",)) -> pd.DataFrame:
    """Filas de estudios con fecha estrictamente anterior al corte y dentro de la
    ventana de recencia. Solo estudios de ámbito estatal (los autonómicos usan
    otra base y sobre-representan partidos territoriales)."""
    lo = pd.Timestamp(cut) - pd.Timedelta(days=window_days)
    stu = study_table(df)
    sel = stu[(stu["fecha"].notna()) & (stu["fecha"] < pd.Timestamp(cut))
              & (stu["fecha"] >= lo) & (stu["tipo"].isin(["preelectoral", "flash",
                                                          "campana", "otro",
                                                          "preelectoral_panel",
                                                          "municipales"]))
              & (stu["ambito"].isin(amb_ok))]
    ids = set(sel["estudio_id"].astype(str))
    out = df[df["estudio_id"].astype(str).isin(ids)]
    return out, sel


# --------------------------------------------------------------------------- #
# Diseño y modelo
# --------------------------------------------------------------------------- #
def design_matrix(demo: pd.Series, prov: pd.Series) -> sparse.csr_matrix:
    return _matrix([(a, b, None) for a, b in zip(demo.to_numpy(), prov.to_numpy())],
                   None, None)


REC_CATS_DEFAULT = list(MODELED_PARTIES) + ["CIUDADANOS"] + RESIDUAL_ORDER


def _matrix(rows_vals, extra_cols, extra_cats):
    n = len(rows_vals)
    n_extra = len(extra_cats) if extra_cats else 0
    width = len(FEATURES) + n_extra
    rows, cols = [], []
    for i, (a, b, c) in enumerate(rows_vals):
        j = FEATURE_INDEX.get(f"demo:{a}")
        if j is not None:
            rows.append(i); cols.append(j)
        j = FEATURE_INDEX.get(f"prov:{b}")
        if j is not None:
            rows.append(i); cols.append(j)
        if c is not None and extra_cats:
            try:
                j = len(FEATURES) + extra_cats.index(c)
            except ValueError:
                j = None
            if j is not None:
                rows.append(i); cols.append(j)
    data = np.ones(len(rows), dtype=np.float64)
    return sparse.csr_matrix((data, (rows, cols)), shape=(n, width))


def design_matrix_anchor(demo, prov, rec, rec_cats) -> sparse.csr_matrix:
    """Diseño del modelo anclado: demografía + provincia + recuerdo de voto."""
    return _matrix(list(zip(demo.to_numpy(), prov.to_numpy(), rec.to_numpy())),
                   None, list(rec_cats))


def fit_mrp(train: pd.DataFrame, universe, C: float = 1.0, max_iter: int = 3000):
    classes = list(universe) + [c for c in RESIDUAL_ORDER
                                if c in set(train["clase"].unique())]
    present = set(train["clase"].unique())
    classes = [c for c in classes if c in present]
    # y como etiquetas de texto: `model.classes_` (ordenado) indexa las columnas
    # de `predict_proba`, así que basta con usarlo como fuente de verdad.
    y = train["clase"].to_numpy()
    X = design_matrix(train["demo"], train["prov"])
    w = train["peso"].to_numpy(dtype=np.float64)
    model = LogisticRegression(solver="lbfgs", C=C, max_iter=max_iter, tol=1e-4)
    model.fit(X, y, sample_weight=w)
    return model, list(model.classes_)


def predict_cells(model, classes, censo: pd.DataFrame) -> pd.DataFrame:
    """Probabilidad por clase y celda censal (provincia × sexo × edad × estudios)."""
    demo = (censo["sexo"] + "|" + censo["edad_grupo"] + "|" + censo["edu_grupo"])
    X = design_matrix(demo.reset_index(drop=True),
                      censo["provincia"].astype(str).reset_index(drop=True))
    P = model.predict_proba(X)
    out = pd.DataFrame(P, columns=[f"p_{c}" for c in model.classes_])
    out["provincia"] = censo["provincia"].to_numpy()
    out["poblacion"] = censo["poblacion"].to_numpy()
    return out


def fit_mrp_anchored(train: pd.DataFrame, universe, C: float = 1.0,
                     max_iter: int = 3000):
    """Variante exploratoria: intención ~ demografía + provincia + **recuerdo de
    voto** (la misma información de la elección anterior que usa el swing).

    La post-estratificación necesita entonces P(recuerdo | provincia), que se
    toma de los resultados reales de la elección anterior (
    `Interior.provincial_shares`). Ver `predict_anchored`.
    """
    rec_cats = [c for c in REC_CATS_DEFAULT if c in set(train["clase_rec"].unique())]
    y = train["clase"].to_numpy()
    X = design_matrix_anchor(train["demo"], train["prov"], train["clase_rec"], rec_cats)
    w = train["peso"].to_numpy(dtype=np.float64)
    model = LogisticRegression(solver="lbfgs", C=C, max_iter=max_iter, tol=1e-4)
    model.fit(X, y, sample_weight=w)
    return model, list(model.classes_), rec_cats


def predict_anchored(model, classes, rec_cats, censo: pd.DataFrame, prev_shares,
                     universe):
    """Post-estratificación del modelo anclado.

    Celda = provincia × demografía × recuerdo, con peso
    `N_censo(prov, demo) · π(rec | prov)` (independencia demo-rec dentro de la
    provincia, supuesto explícito). `π(rec|prov)` sale de la elección anterior.
    """
    provs = sorted(censo["provincia"].unique())
    parts = []
    for prov in provs:
        c = censo[censo["provincia"] == prov]
        pi = prev_shares.get(int(prov)) or prev_shares.get(prov) or {}
        tot = sum(pi.get(r, 0.0) for r in rec_cats)
        if tot <= 0:
            pi_norm = {r: 1.0 / len(rec_cats) for r in rec_cats}
        else:
            pi_norm = {r: pi.get(r, 0.0) / tot for r in rec_cats}
        demo = (c["sexo"] + "|" + c["edad_grupo"] + "|" + c["edu_grupo"]).to_numpy()
        pob = c["poblacion"].to_numpy(dtype=float)
        for r in rec_cats:
            parts.append(pd.DataFrame({
                "provincia": int(prov),
                "demo": demo,
                "rec": r,
                "w": pob * pi_norm[r],
            }))
    grid = pd.concat(parts, ignore_index=True)
    grid = grid[grid["w"] > 0]
    X = design_matrix_anchor(grid["demo"], grid["provincia"].astype(str),
                             grid["rec"], rec_cats)
    P = model.predict_proba(X)
    probs = pd.DataFrame(P, columns=model.classes_)
    probs["provincia"] = grid["provincia"].to_numpy()
    probs["w"] = grid["w"].to_numpy()
    uni = [c for c in model.classes_ if c in set(universe)]
    probs["_den"] = probs[uni].sum(axis=1) * probs["w"]
    den = probs.groupby("provincia")["_den"].sum()
    out = {int(p): {} for p in den.index}
    for p in universe:
        if p not in probs.columns:
            for prov in out:
                out[prov][p] = 0.0
            continue
        num = (probs[p] * probs["w"]).groupby(probs["provincia"]).sum()
        sh = (100.0 * num / den.replace(0, np.nan)).fillna(0.0)
        for prov, val in sh.items():
            out[int(prov)][p] = float(val)
    return out


def poststratify(proba: pd.DataFrame, model, universe, parties=None):
    """Agrega probabilidades por celda con los pesos censales.

    Devuelve `{prov: {partido: %}}` normalizado al universo (suma = 100 por
    provincia), condicionando a votar a alguno de los partidos del universo.
    """
    parties = parties or list(universe)
    # Un partido puede no aparecer en las clases ajustadas (VOX no tenía muestra
    # en 2015): su columna no existe y su cuota post-estratificada es 0.
    denom_cols = [f"p_{c}" for c in model.classes_ if c in set(universe)]
    prov_arr = proba["provincia"].to_numpy()
    den = pd.Series((proba[denom_cols].sum(axis=1) * proba["poblacion"]).to_numpy())
    den_prov = den.groupby(prov_arr).sum()
    out = {int(p): {} for p in sorted(proba["provincia"].unique())}
    for p in parties:
        col = proba.get(f"p_{p}")
        if col is None:
            for prov in out:
                out[prov][p] = 0.0
            continue
        num = pd.Series((col * proba["poblacion"]).to_numpy())
        num_prov = num.groupby(prov_arr).sum()
        sh = (100.0 * num_prov / den_prov.replace(0, np.nan)).fillna(0.0)
        for prov, val in sh.items():
            out[int(prov)][p] = float(val)
    return out


def cell_means_poststrat(train: pd.DataFrame, censo: pd.DataFrame, universe,
                         K: float = 50.0):
    """Alternativa simple: medias de celda ponderadas con encogimiento.

    share(celda) = λ·share_observada + (1-λ)·share_nacional_demográfica,
    λ = n_eff/(n_eff+K) con n_eff = Σpesos/mean(peso). Después se post-estratifica
    con los denominadores censales.
    """
    parties = list(universe)
    df = train.copy()
    df["w"] = df["peso"]
    # celda provincia × demo
    cell = (df.groupby(["prov", "demo", "clase"])["w"].sum().unstack(fill_value=0.0)
              .reindex(columns=parties, fill_value=0.0))
    cell["_n"] = df.groupby(["prov", "demo"])["w"].sum()
    # prior: media demográfica nacional
    nat = (df.groupby(["demo", "clase"])["w"].sum().unstack(fill_value=0.0)
             .reindex(columns=parties, fill_value=0.0))
    nat = nat.div(nat.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    mean_w = df["w"].mean() or 1.0
    out = {}
    for prov in sorted(censo["provincia"].unique()):
        c = censo[censo["provincia"] == prov]
        num = np.zeros(len(parties))
        den = 0.0
        for _, row in c.iterrows():
            demo = f"{row['sexo']}|{row['edad_grupo']}|{row['edu_grupo']}"
            key = (str(prov), demo)
            if key in cell.index:
                obs = cell.loc[key, parties].to_numpy(dtype=float)
                n_eff = float(cell.loc[key, "_n"]) / mean_w
            else:
                obs = np.zeros(len(parties))
                n_eff = 0.0
            prior = nat.loc[demo].to_numpy(dtype=float) if demo in nat.index \
                else np.zeros(len(parties))
            lam = n_eff / (n_eff + K)
            p = lam * obs + (1.0 - lam) * prior
            s = p.sum()
            if s > 0:
                p = p / s
            num += p * float(row["poblacion"])
        tot = num.sum()
        out[int(prov)] = {parties[i]: 100.0 * num[i] / tot if tot > 0 else 0.0
                          for i in range(len(parties))}
    return out


# --------------------------------------------------------------------------- #
# Interior (datos reales provinciales) — lectura propia, sin tocar pipeline/modelo
# --------------------------------------------------------------------------- #
SLUG_FIXES = {"u-p-n": "NA+"}


def canon_slug(slug, eid=None):
    c = canonical_of_slug(slug, eid)
    if c == "OTROS" and slug in SLUG_FIXES:
        c = SLUG_FIXES[slug]
    return FAMILY.get(c, c)


class Interior:
    def __init__(self):
        self.elections = json.loads(
            (DATA / "interior" / "elections.json").read_text(encoding="utf-8"))["elecciones"]
        self._by = {e["id"]: e for e in self.elections}
        self._prov = {}
        with open(DATA / "interior" / "results_provincial.jsonl", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                self._prov.setdefault(r["eleccion"], []).append(r)

    def valid_votes(self, eid):
        return {p["codigo"]: p["votos_validos"] for p in self._by[eid]["provincias"]}

    def seats(self, eid):
        return {p["codigo"]: p["escanos"] for p in self._by[eid]["provincias"]}

    def province_names(self, eid):
        return {p["codigo"]: p["nombre"] for p in self._by[eid]["provincias"]}

    def _totals(self, eid):
        tot = {}
        for r in self._prov.get(eid, []):
            c = canon_slug(r["partido_id"], eid)
            tot[c] = tot.get(c, 0.0) + r["votos"]
        return tot

    def national_shares(self, eid, universe):
        tot = self._totals(eid)
        sub = {p: tot.get(p, 0.0) for p in universe}
        s = sum(sub.values())
        return {p: 100.0 * v / s for p, v in sub.items()} if s else {p: 0.0 for p in universe}

    def provincial_shares(self, eid, universe):
        raw = {}
        for r in self._prov.get(eid, []):
            p = r["provincia"]
            c = canon_slug(r["partido_id"], eid)
            d = raw.setdefault(p, {})
            d[c] = d.get(c, 0.0) + r["votos"]
        out = {}
        for p, d in raw.items():
            sub = {k: d.get(k, 0.0) for k in universe}
            s = sum(sub.values())
            out[p] = {k: (100.0 * v / s if s else 0.0) for k, v in sub.items()}
        return out

    def weights(self, eid):
        vv = self.valid_votes(eid)
        tot = sum(vv.values())
        return {p: v / tot for p, v in vv.items()}


# --------------------------------------------------------------------------- #
# Calibración y swing uniforme
# --------------------------------------------------------------------------- #
def calibrate(prov, target, w, parties, tol=0.02, max_iter=40):
    """Punto fijo: escala las cuotas provinciales para que el agregado ponderado
    por votos coincida con `target` (≤ tol pp). Misma mecánica que el modelo
    estatal (se reimplementa aquí para no depender de `pipeline/modelo/`)."""
    base_nat = {p: sum(w[c] * prov[c][p] for c in prov) for p in parties}

    def ratios():
        r = {}
        for p in parties:
            if base_nat[p] > 1e-6 and target[p] > 0:
                r[p] = target[p] / base_nat[p]
            else:
                r[p] = 0.0
        return r

    def apply(r):
        out = {}
        for c, d in prov.items():
            v = {p: d[p] * r[p] for p in parties}
            s = sum(v.values())
            out[c] = {p: (100.0 * v[p] / s if s > 0 else 0.0) for p in parties}
        return out

    r = ratios()
    cur = apply(r)
    dev = float("inf")
    it = 0
    for it in range(1, max_iter + 1):
        agg = {p: sum(w[c] * cur[c][p] for c in cur) for p in parties}
        dev = max(abs(agg[p] - target[p]) for p in parties)
        if dev <= tol:
            break
        for p in parties:
            if base_nat[p] > 1e-6 and agg[p] > 1e-9:
                r[p] *= target[p] / agg[p]
        cur = apply(r)
    return cur, r, it, dev


def swing_uniforme(base_prov, target, w, parties, floor=0.0):
    """Swing proporcional uniforme desde una base provincial.

    `floor > 0` añade a cada partido/provincia una base mínima uniforme (pp):
    es el arreglo para partidos que no existían en la base (VOX en 2016, CS en
    2011). Sin él, `ratio = target/base = ∞ -> 0` y el partido se queda a cero
    en todas partes, un artefacto del backtest que no sufre el producto real
    (cuya base 23J contiene a todos los partidos modelados).
    """
    if floor > 0:
        base_prov = {c: {p: v + floor for p, v in d.items()}
                     for c, d in base_prov.items()}
    return calibrate(base_prov, target, w, parties)
