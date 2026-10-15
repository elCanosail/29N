#!/usr/bin/env python3
"""agrega.py — agregados estáticos del explorador de microdatos CIS (29N).

Entrada (solo lectura):  data/processed/microdatos/individual.parquet
Salida:                  web/src/data/microdatos/*.json

Cortes precalculados (siempre ponderados por `peso`):
  1. por_anio.json           — intención por partido canónico + ideología media + recuerdo, por año.
  2. por_provincia.json      — intención por partido por provincia (2015-2025).
  3. ideologia_partido.json  — ideología media y distribución 1-10 por partido votado.
  4. perfil_partido.json     — edad media, sexo y estudios por partido.
  5. serie_ideologia.json    — serie de ideología media por año (evolución del electorado).

Reproducibilidad: los bloques de DATOS no contienen fechas del sistema. La única
fecha viva es `meta.generacion`, aislada en el bloque `meta` de cada archivo; el
resto del contenido es determinista para un parquet dado.

Uso:  /root/.venvs/29n-micro/bin/python pipeline/microdatos/agrega.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# --- rutas -----------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[2]
PARQUET = RAIZ / "data/processed/microdatos/individual.parquet"
SALIDA = RAIZ / "web/src/data/microdatos"
SEATS = RAIZ / "web/src/data/seats.json"

# --- contrato de agregación ------------------------------------------------
# Cobertura mínima de la variable de intención en un estudio para entrar en los
# cortes de voto. 10 estudios (2004-2011 y europeas 1989) no traen la pregunta
# extraída (cobertura ~0 %); incluirlos fabricaría ceros falsos.
COBERTURA_MIN_INTENCION = 0.5
# Edad plausible: el CIS muestrea población adulta; se descartan 0 y <15 / >100.
EDAD_MIN, EDAD_MAX = 15, 100
# Ideología 1-10 agrupada por redondeo al entero más próximo (las escalas 1-7 se
# reescalan a 1-10 en origen: 2,5 / 5,5 / 8,5 → 2 / 6 / 9).
IDEOL_MIN, IDEOL_MAX = 1, 10

# partido canónico: familia política (DESIGN.md §2: AP→PP, UCD→PP, PODEMOS→Sumar)
CANON = {
    "PSOE": "PSOE", "PSC": "PSOE", "PSE-EE": "PSOE", "PSDEG": "PSOE",
    "PSIB-PSOE": "PSOE", "PSN-PSOE": "PSOE",
    "PP": "PP", "AP": "PP", "PP-AP": "PP", "CP": "PP", "UCD": "PP",
    "VOX": "VOX",
    "SUMAR": "SUMAR", "PODEMOS": "SUMAR", "UNIDAS PODEMOS": "SUMAR",
    "IU": "SUMAR", "MÁS PAÍS": "SUMAR", "COMPROMIS": "SUMAR", "ECP": "SUMAR",
    "CIUDADANOS": "CIUDADANOS",
    "ERC": "ERC",
    "JXCAT": "JXCAT", "JUNTS": "JXCAT", "CIU": "JXCAT",
    "PNV": "PNV", "GEROA BAI": "PNV",
    "EH BILDU": "EH BILDU",
    "BNG": "BNG",
    "CUP": "CUP",
    "CC": "CC",
    "NA+": "NA+", "UPN": "NA+",
    "PACMA": "PACMA",
    "CDS": "CDS",
    "OTRO": "OTROS", "OTROS": "OTROS", "PAR": "OTROS", "PRC": "OTROS",
    "UPYD": "OTROS", "CHA": "OTROS", "FORO": "OTROS", "PI": "OTROS",
}
# categorías de no-voto (se mantienen como categorías propias, no son partido)
NO_VOTO = ["ABSTENCION", "NS", "NC", "NO DECIDIDO", "EN BLANCO", "VOTO NULO"]
NO_DECLARADO = "NO DECLARADO"

PARTIDOS = ["PSOE", "PP", "VOX", "SUMAR", "CIUDADANOS", "ERC", "JXCAT", "PNV",
            "EH BILDU", "BNG", "CUP", "CC", "NA+", "PACMA", "CDS", "OTROS"]
CATEGORIAS = PARTIDOS + NO_VOTO + [NO_DECLARADO]

# estudios (niveles de estudios CIS → 5 niveles + residual)
NIVEL_ESTUDIOS = {
    "Sin estudios": "Sin estudios",
    "Menos de estudios primarios, sabe leer (menos de 6 años de escuela)": "Sin estudios",
    "Menos de estudios primarios, sabe leer (Menos de 6 años de escuela)": "Sin estudios",
    "Menos de estudios primarios, no sabe leer": "Sin estudios",
    "Primaria": "Primaria",
    "Estudios primarios completos, cultura general": "Primaria",
    "Estudios completos, cultura general": "Primaria",
    "Secundaria": "Secundaria",
    "Secundaria 1ª etapa": "Secundaria",
    "Secundaria 2ª etapa": "Secundaria",
    "Bachiller elemental": "Secundaria",
    "Bachiller superior": "Secundaria",
    "Grado medio": "Secundaria",
    "F.P.": "FP",
    "FP": "FP",
    "Formación Profesional": "FP",
    "Estudios de formación profesional": "FP",
    "Cualificación profesional": "FP",
    "Superiores": "Superiores",
    "Medios universitarios": "Superiores",
    "Universitarios o técnicos de grado superior": "Superiores",
    "Estudios de grado medio (peritajes, magisterio)": "Superiores",
    "Estudios de grado medio (peritajes, magisterio...)": "Superiores",
    "Estudios de grado medio": "Superiores",
    # residuales de codificación / no contesta
    "N.C.": "NC/Otros",
    "Blanco": "NC/Otros",
    "Otros": "NC/Otros",
    "Otros no reglados": "NC/Otros",
}
NIVELES = ["Sin estudios", "Primaria", "Secundaria", "FP", "Superiores", "NC/Otros"]


# --- utilidades ------------------------------------------------------------
def _canon_cat(v: object) -> str:
    """Categoría canónica: partido (familia), no-voto, NO DECLARADO o OTROS."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return NO_DECLARADO
    if v in NO_VOTO:
        return str(v)
    return CANON.get(str(v), "OTROS")


def normaliza_pesos(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza `peso` dentro de cada estudio (suma = n del estudio).

    Los estudios no comparten escala de peso (algunos traen pesos ~1e6). Para
    poder agrupar varios estudios por año o provincia, cada estudio debe aportar
    en proporción a su tamaño muestral, no a su escala de ponderación.
    """
    df = df.copy()
    tot = df.groupby("estudio_id")["peso"].transform("sum")
    n = df.groupby("estudio_id")["peso"].transform("size")
    df["wn"] = df["peso"] / tot * n
    return df


def leer_parquet() -> pd.DataFrame:
    df = pd.read_parquet(PARQUET).copy()
    # canoniza el voto; NaN → NO DECLARADO, no-voto se mantiene como categoría propia
    df["cat_intencion"] = df["intencion_voto"].map(_canon_cat)
    df["cat_recuerdo"] = df["recuerdo_voto"].map(_canon_cat)
    df["nivel_estudios"] = df["estudios"].map(NIVEL_ESTUDIOS)
    df["sexo_norm"] = df["sexo"].where(df["sexo"].isin(["Hombre", "Mujer"]), None)
    # cobertura de la variable de intención por estudio
    cov = df.assign(x=df["intencion_voto"].notna()).groupby("estudio_id")["x"].mean()
    df["_cov_intencion"] = df["estudio_id"].map(cov)
    return df


def pct_ponderado(serie_pesos: pd.Series, base: float) -> float:
    return round(float(serie_pesos.sum() / base * 100), 4) if base > 0 else None


def media_ponderada(valores: pd.Series, pesos: pd.Series) -> float | None:
    mask = valores.notna() & pesos.notna()
    if not mask.any() or pesos[mask].sum() == 0:
        return None
    return round(float((valores[mask] * pesos[mask]).sum() / pesos[mask].sum()), 3)


def cuantil_ponderado(valores: pd.Series, pesos: pd.Series, q: float) -> float | None:
    mask = valores.notna() & pesos.notna()
    if not mask.any():
        return None
    v = valores[mask].to_numpy()
    w = pesos[mask].to_numpy()
    orden = v.argsort()
    v, w = v[orden], w[orden]
    acum = w.cumsum() / w.sum()
    idx = int((acum >= q).argmax())
    return round(float(v[idx]), 2)


def dist_ideologia(sub: pd.DataFrame) -> list[float] | None:
    """Distribución ponderada de ideología 1-10 (redondeo al entero)."""
    s = sub.dropna(subset=["ideologia_1a10"])
    if s.empty or s["wn"].sum() == 0:
        return None
    bins = s["ideologia_1a10"].round().clip(IDEOL_MIN, IDEOL_MAX).astype(int)
    agg = s.groupby(bins)["wn"].sum()
    base = agg.sum()
    return [round(float(agg.get(b, 0.0) / base * 100), 3) for b in range(IDEOL_MIN, IDEOL_MAX + 1)]


def meta_bloque(extra: dict, df: pd.DataFrame) -> dict:
    """Bloque meta común. Única fecha viva del archivo; separada de los datos."""
    return {
        "generacion": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fuente": "data/processed/microdatos/individual.parquet",
        "dataset": "Microdatos CIS a nivel individual (fase 4-c), estudios 1977-2025",
        "n_entrevistas": int(len(df)),
        "n_estudios": int(df["estudio_id"].nunique()),
        "cobertura_temporal": "1977-2025",
        "ponderacion": (
            "Todos los agregados ponderan por `peso` (ponderador nacional preferente). "
            "Los pesos se normalizan por estudio (suma = n del estudio) antes de agrupar, "
            "para no mezclar escalas de ponderación distintas."
        ),
        "base": (
            "CIS = % sobre censo: el denominador es el total de entrevistas del grupo "
            "(incluye abstención, NS, NC y no declarado). NO es % sobre voto válido; por eso "
            "los partidos suman bastante menos de 100 %."
        ),
        "advertencias": [
            "CIS = % sobre censo (todas las entrevistas), no sobre voto válido.",
            "Intención de voto calculada solo con estudios de cobertura de la pregunta "
            f"≥ {int(COBERTURA_MIN_INTENCION * 100)} %; quedan fuera 10 estudios 2004-2011 "
            "sin la pregunta extraída (así no se fabrican ceros falsos).",
            "Ideología autoubicada 1-10 (1 = izquierda, 10 = derecha). Las escalas 1-7 "
            "se reescalan a 1-10 en origen; la distribución se agrupa por redondeo al entero.",
            "Muestras provinciales pequeñas en provincias poco pobladas: cada celda publica su n.",
            "Solo agregados: ningún microdato reidentificable se publica.",
        ],
        **extra,
    }


# --- cortes ----------------------------------------------------------------
def corte_por_anio(df: pd.DataFrame) -> dict:
    elig = df[df["_cov_intencion"] >= COBERTURA_MIN_INTENCION]
    anios = []
    for anio, g in elig.groupby("anio"):
        base = g["wn"].sum()
        intencion = {
            c: pct_ponderado(g.loc[g["cat_intencion"] == c, "wn"], base) for c in CATEGORIAS
        }
        # ideología y recuerdo: sobre TODO el dataset del año, no solo los estudios elegibles
        ga = df[df["anio"] == anio]
        ideol = ga.dropna(subset=["ideologia_1a10"])
        rec_base = ga["wn"].sum()
        rec = ga.dropna(subset=["recuerdo_voto"])
        anios.append({
            "anio": int(anio),
            "eleccion": sorted(ga["eleccion"].dropna().unique().tolist()),
            "n_entrevistas": int(len(ga)),
            "n_intencion": int(len(g)),
            "n_estudios": int(g["estudio_id"].nunique()),
            "intencion": intencion,
            "ideologia_media": media_ponderada(ga["ideologia_1a10"], ga["wn"]),
            "n_ideologia": int(len(ideol)),
            "pct_con_recuerdo": pct_ponderado(rec["wn"], rec_base) if len(rec) else None,
        })
    anios.sort(key=lambda a: a["anio"])
    return {
        "meta": meta_bloque({
            "corte": "intención de voto e ideología por año",
            "unidad": "% sobre censo (CIS)",
            "nota": (
                "Los años 2004-2011 no traen intención extraída: aparecen sin partidos. "
                "La ideología media excluye a quien no se autoubica."
            ),
        }, df),
        "categorias": CATEGORIAS,
        "partidos": PARTIDOS,
        "no_voto": NO_VOTO,
        "anios": anios,
    }


def corte_por_provincia(df: pd.DataFrame) -> dict:
    ventana = df[(df["anio"] >= 2015) & (df["anio"] <= 2025) & (df["_cov_intencion"] >= COBERTURA_MIN_INTENCION)]
    nombres = mapa_provincias()
    filas = []
    for prov, g in ventana.groupby("provincia"):
        base = g["wn"].sum()
        intencion = {c: pct_ponderado(g.loc[g["cat_intencion"] == c, "wn"], base) for c in CATEGORIAS}
        filas.append({
            "codigo": int(prov),
            "provincia": nombres.get(int(prov), f"Provincia {int(prov)}"),
            "n_entrevistas": int(len(g)),
            "n_estudios": int(g["estudio_id"].nunique()),
            "intencion": intencion,
        })
    filas.sort(key=lambda f: f["codigo"])
    base_nac = ventana["wn"].sum()
    nacional = {c: pct_ponderado(ventana.loc[ventana["cat_intencion"] == c, "wn"], base_nac) for c in CATEGORIAS}
    return {
        "meta": meta_bloque({
            "corte": "intención de voto por provincia",
            "periodo": "2015-2025",
            "unidad": "% sobre censo (CIS), agregado 2015-2025",
            "nota": (
                "Provincias con muestra CIS agregada de 2015-2025, ponderada por estudio. "
                "n bajo en provincias pequeñas: el margen es amplio y se publica tal cual."
            ),
        }, df),
        "partidos": PARTIDOS,
        "no_voto": NO_VOTO,
        "categorias": CATEGORIAS,
        "nacional": {"n_entrevistas": int(len(ventana)), "intencion": nacional},
        "provincias": filas,
    }


def corte_ideologia_partido(df: pd.DataFrame) -> dict:
    con_ideol = df.dropna(subset=["ideologia_1a10"])
    filas = []
    for p in PARTIDOS:
        sub = con_ideol[con_ideol["cat_intencion"] == p]
        if sub.empty:
            continue
        dist = dist_ideologia(sub)
        filas.append({
            "partido": p,
            "n": int(len(sub)),
            "ideologia_media": media_ponderada(sub["ideologia_1a10"], sub["wn"]),
            "p25": cuantil_ponderado(sub["ideologia_1a10"], sub["wn"], 0.25),
            "p75": cuantil_ponderado(sub["ideologia_1a10"], sub["wn"], 0.75),
            "distribucion": dist,
        })
    total = {
        "partido": "Total",
        "n": int(len(con_ideol)),
        "ideologia_media": media_ponderada(con_ideol["ideologia_1a10"], con_ideol["wn"]),
        "p25": cuantil_ponderado(con_ideol["ideologia_1a10"], con_ideol["wn"], 0.25),
        "p75": cuantil_ponderado(con_ideol["ideologia_1a10"], con_ideol["wn"], 0.75),
        "distribucion": dist_ideologia(con_ideol),
    }
    filas.sort(key=lambda f: (f["ideologia_media"] is None, f["ideologia_media"] or 0))
    return {
        "meta": meta_bloque({
            "corte": "ideología autoubicada por partido votado (intención)",
            "unidad": "media 1-10 y distribución % sobre electorado del partido",
            "nota": "Sobre quienes declaran intención de voto y se autoubican en la escala 1-10.",
        }, df),
        "escala": {"min": IDEOL_MIN, "max": IDEOL_MAX, "etiquetas": ["1 izquierda", "10 derecha"]},
        "total": total,
        "partidos": filas,
    }


def corte_perfil_partido(df: pd.DataFrame) -> dict:
    filas = []
    for p in PARTIDOS:
        sub = df[df["cat_intencion"] == p]
        if sub.empty:
            continue
        # edad
        ge = sub[(sub["edad"] >= EDAD_MIN) & (sub["edad"] <= EDAD_MAX)]
        # sexo
        niveles = {}
        for nivel in NIVELES:
            ss = sub[sub["nivel_estudios"] == nivel]
            niveles[nivel] = pct_ponderado(ss["wn"], sub["wn"].sum()) if len(ss) else None
        filas.append({
            "partido": p,
            "n": int(len(sub)),
            "edad_media": media_ponderada(ge["edad"], ge["wn"]),
            "n_edad": int(len(ge)),
            "sexo": {
                "Hombre": pct_ponderado(sub.loc[sub["sexo_norm"] == "Hombre", "wn"], sub["wn"].sum()),
                "Mujer": pct_ponderado(sub.loc[sub["sexo_norm"] == "Mujer", "wn"], sub["wn"].sum()),
                "NC": round(float(sub.loc[sub["sexo_norm"].isna(), "wn"].sum() / sub["wn"].sum() * 100), 4),
            },
            "estudios": niveles,
        })
    total = df
    total_sexo = {
        "Hombre": pct_ponderado(total.loc[total["sexo_norm"] == "Hombre", "wn"], total["wn"].sum()),
        "Mujer": pct_ponderado(total.loc[total["sexo_norm"] == "Mujer", "wn"], total["wn"].sum()),
        "NC": round(float(total.loc[total["sexo_norm"].isna(), "wn"].sum() / total["wn"].sum() * 100), 4),
    }
    total_ge = total[(total["edad"] >= EDAD_MIN) & (total["edad"] <= EDAD_MAX)]
    filas.sort(key=lambda f: (f["edad_media"] is None, f["edad_media"] or 0))
    return {
        "meta": meta_bloque({
            "corte": "perfil sociodemográfico por partido votado (intención)",
            "unidad": "edad media (años) y % sobre el electorado de cada partido",
            "nota": (
                "Edad restringida a 15-100 años (se descartan 0 / fuera de rango). "
                "Estudios armonizados a 6 niveles; NC/Otros agrupa no-consta y no-reglados."
            ),
        }, df),
        "niveles_estudios": NIVELES,
        "total": {
            "n": int(len(total)),
            "edad_media": media_ponderada(total_ge["edad"], total_ge["wn"]),
            "sexo": total_sexo,
            "estudios": {
                n: pct_ponderado(total.loc[total["nivel_estudios"] == n, "wn"], total["wn"].sum())
                for n in NIVELES
            },
        },
        "partidos": filas,
    }


def corte_serie_ideologia(df: pd.DataFrame) -> dict:
    con = df.dropna(subset=["ideologia_1a10"])
    serie = []
    for anio, g in con.groupby("anio"):
        serie.append({
            "anio": int(anio),
            "media": media_ponderada(g["ideologia_1a10"], g["wn"]),
            "p25": cuantil_ponderado(g["ideologia_1a10"], g["wn"], 0.25),
            "p75": cuantil_ponderado(g["ideologia_1a10"], g["wn"], 0.75),
            "n": int(len(g)),
            "n_estudios": int(g["estudio_id"].nunique()),
        })
    serie.sort(key=lambda a: a["anio"])
    return {
        "meta": meta_bloque({
            "corte": "ideología media autoubicada por año",
            "unidad": "media 1-10 (1 izquierda, 10 derecha)",
            "nota": (
                "Evolución del electorado que se autoubica. Los huecos (2004-2011) son "
                "estudios sin la variable extraída, no un valor 0."
            ),
        }, df),
        "escala": {"min": IDEOL_MIN, "max": IDEOL_MAX},
        "serie": serie,
    }


def mapa_provincias() -> dict[int, str]:
    with open(SEATS, encoding="utf-8") as f:
        seats = json.load(f)
    return {int(p["codigo"]): p["nombre"] for p in seats.get("provincias", [])}


def main() -> None:
    df = leer_parquet()
    df = normaliza_pesos(df)
    SALIDA.mkdir(parents=True, exist_ok=True)

    salidas = {
        "por_anio.json": corte_por_anio(df),
        "por_provincia.json": corte_por_provincia(df),
        "ideologia_partido.json": corte_ideologia_partido(df),
        "perfil_partido.json": corte_perfil_partido(df),
        "serie_ideologia.json": corte_serie_ideologia(df),
    }
    for nombre, contenido in salidas.items():
        with open(SALIDA / nombre, "w", encoding="utf-8") as f:
            json.dump(contenido, f, ensure_ascii=False, indent=1)
        print(f"escrito {SALIDA / nombre}")


if __name__ == "__main__":
    main()
