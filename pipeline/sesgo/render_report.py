#!/usr/bin/env python3
"""Renderiza data/processed/sesgo/bias_report.md desde house_effects.json.

Informe legible de la fase 4-bis (efectos de casa y sesgo de incumbencia).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/processed/sesgo/house_effects.json"
DST = ROOT / "data/processed/sesgo/bias_report.md"

SERIE_LABEL = {
    "micro_censo": "CIS microdato (voto directo, % sobre censo)",
    "micro_valid": "CIS microdato normalizado (% sobre voto válido)",
    "est": "CIS modelo publicado (estimación, % sobre voto válido)",
    "privado": "Encuestador privado (% sobre voto válido)",
}


def fmt(x, nd=2):
    if x is None:
        return "—"
    return f"{x:+.{nd}f}"


def fmt_ci(ci, nd=2):
    if not ci:
        return "—"
    return f"[{ci[0]:+.{nd}f}, {ci[1]:+.{nd}f}]"


def table_errors(he, casa, serie):
    parties = he.get(casa, {}).get(serie)
    if not parties:
        return "_sin datos_\n"
    rows = sorted(parties.items(), key=lambda x: -abs(x[1]["media"]))
    out = ["| partido | n | media | sd | IC95 bootstrap |", "|---|---:|---:|---:|---|"]
    for p, st in rows:
        out.append(f"| {p} | {st['n']} | {fmt(st['media'])} | {st['sd']:.2f} | "
                   f"{fmt_ci(st.get('ic95_bootstrap'))} |")
    return "\n".join(out) + "\n"


def table_incumbency(inc):
    out = ["| casa | serie | grupo | n | media | IC95 bootstrap |",
           "|---|---|---|---:|---:|---|"]
    for casa, sers in inc.items():
        for serie, e in sers.items():
            for key, lab in (("in", "EN Gobierno"), ("out", "FUERA")):
                g = e[key]
                out.append(f"| {casa} | {serie} | {lab} | {g['n']} | "
                           f"{fmt(g['media'])} | {fmt_ci(g['ic95_bootstrap'])} |")
            out.append(f"| {casa} | {serie} | **IN − OUT** | — | "
                       f"{fmt(e.get('diferencia_in_menos_out'))} | "
                       f"{fmt_ci(e.get('diferencia_ic95_bootstrap'))} |")
    return "\n".join(out) + "\n"


def table_corrections(corr, casa, serie):
    parties = corr.get(casa, {}).get(serie)
    if not parties:
        return "_sin datos_\n"
    rows = sorted(parties.items(), key=lambda x: -abs(x[1]["correccion"]))
    out = ["| partido | n | media_error | corrección EB |", "|---|---:|---:|---:|"]
    for p, st in rows:
        out.append(f"| {p} | {st['n']} | {fmt(st['media_error'])} | "
                   f"{fmt(st['correccion'])} |")
    return "\n".join(out) + "\n"


def main():
    d = json.load(open(SRC))
    he = d["house_effects"]
    he_all = d["house_effects_serie_completa"]
    inc = d["incumbencia"]
    corr = d["correcciones_eb"]
    res = d["resumen"]
    est = d["estudios_cis"]

    L = []
    L.append("# Efectos de casa y sesgo de incumbencia — 29N (fase 4-bis)\n")
    L.append("Generado por `pipeline/sesgo/render_report.py` desde "
             "`data/processed/sesgo/house_effects.json`.\n")
    L.append(f"- Serie principal (casa × partido): **{d['conteo']['n_series_validada']} "
             f"observaciones validadas** de {d['n_series']} totales.\n")
    L.append("- Error firmado = `pct_encuesta − pct_real`, **misma base de porcentaje**: "
             "el microdato del CIS es *% sobre censo* y se compara con el resultado real "
             "sobre censo; el modelo publicado y los encuestadores privados son *% sobre "
             "voto válido* y se comparan con el resultado real sobre voto válido.\n")
    L.append("- Las **correcciones** se aplican restando: "
             "`pct_corregido = pct_encuesta − corrección`.\n")

    # 1. efecto del modelo CIS
    cc = res.get("CIS_comparacion_mismo_conjunto", {})
    L.append("\n## 0. ¿Vive el sesgo del CIS en el modelo o en las respuestas?\n")
    L.append(f"Sobre el mismo conjunto de elecciones ({', '.join(cc.get('elecciones', []))}):\n")
    L.append(f"- Voto directo de microdato reescalado a voto válido: "
             f"**MAE = {cc.get('mae_micro_valid'):.2f} pp** "
             f"(sesgo medio {fmt(cc.get('sesgo_medio_micro_valid'))} pp, n={cc.get('n_micro_valid')}).\n")
    L.append(f"- Estimación publicada del modelo CIS: **MAE = {cc.get('mae_est'):.2f} pp** "
             f"(sesgo medio {fmt(cc.get('sesgo_medio_est'))} pp, n={cc.get('n_est')}).\n")
    red = cc.get("mae_micro_valid") - cc.get("mae_est")
    L.append(f"\n**Lectura:** el modelo del CIS **reduce** el error absoluto medio en "
             f"**{red:.2f} pp** respecto a la respuesta directa. El sesgo direccional residual "
             "del CIS está, pues, **más en la respuesta directa** (infravaloración de PP y VOX "
             "y sobrevaloración de PSOE) que en el propio modelo, que corrige buena parte de él. "
             "No se observa una *sobrecorrección* sistemática hacia la izquierda mayor que la "
             "que ya traía el dato directo.\n")

    # 2. tabla principal de errores
    L.append("\n## 1. Error firmado medio por casa × partido\n")
    L.append("### CIS — serie microdato (voto directo, % sobre censo)\n")
    L.append(table_errors(he, "CIS", "micro_censo"))
    L.append("\n### CIS — serie microdato normalizada (% sobre voto válido)\n")
    L.append(table_errors(he, "CIS", "micro_valid"))
    L.append("\n### CIS — serie modelo publicado (estimación, % sobre voto válido)\n")
    L.append(table_errors(he, "CIS", "est"))
    for casa in ("GAD3", "Sigma Dos", "NC Report", "Sociometrica"):
        if casa in he:
            L.append(f"\n### {casa} — encuesta final 2023 (% sobre voto válido)\n")
            L.append(table_errors(he, casa, "privado"))

    # 3. incumbencia
    L.append("\n## 2. Sesgo de incumbencia\n")
    L.append("Grupo **EN Gobierno** = partidos del ejecutivo de turno que se presentan "
             "(ver `pipeline/sesgo/incumbency.json`, con fuentes). **FUERA** = el resto. "
             "Intervalos bootstrap (10 000 remuestreos, semilla 20261015).\n")
    L.append("\n> **Advertencia de potencia estadística:** con n=1–5 observaciones por grupo, "
             "los intervalos son anchísimos y **ningún sesgo de incumbencia se declara "
             "significativo** salvo que su IC95 excluya el 0. En los encuestadores privados "
             "solo hay **una elección (2023)**, de modo que su diferencia IN−OUT **no puede "
             "separarse del error específico de esa cita** y no debe leerse como sesgo estructural.\n")
    L.append("\n" + table_incumbency(inc))

    # 4. correcciones
    L.append("\n## 3. Correcciones (encogimiento empirical-bayes)\n")
    L.append(f"`correccion_i = media_error_i × n_i/(n_i + K)`, con **K = {d['definiciones']['k_encogimiento_eb']}** "
             "(documentado en `docs/notes/sesgo.md`). Restar la corrección a la encuesta.\n")
    L.append("\n### CIS — modelo publicado\n")
    L.append(table_corrections(corr, "CIS", "est"))
    L.append("\n### CIS — microdato normalizado\n")
    L.append(table_corrections(corr, "CIS", "micro_valid"))
    for casa in ("GAD3", "Sigma Dos", "NC Report", "Sociometrica"):
        if casa in corr:
            L.append(f"\n### {casa}\n")
            L.append(table_corrections(corr, casa, "privado"))

    # 5. huecos
    L.append("\n## 4. Huecos de datos y limitaciones\n")
    L.append("- **Estudios CIS sin tabla publicada** (variable de voto elegida por heurística): "
             "quedan fuera de la tabla principal y se listan en el anexo. Varios están claramente "
             "mal normalizados (p. ej. 1326: UCD 23,5 frente a 5,0 real; 1533: PP 40,3 frente a 18,0; "
             "1135 con 44 % de NS/NC).\n")
    L.append("- **Fin de campo del CIS**: solo se dispone de la fecha fin para los estudios con "
             "ficha técnica en `data/raw/cis`; para el resto se usa la fecha del catálogo "
             "(inicio de campo), marcada como `sin FT`.\n")
    L.append("- **Definición estricta (7 días)**: produce muy pocas observaciones "
             f"({len(d['observaciones_estricta_7d'])}; ver anexo). El CIS termina su campo "
             "habitualmente 2–5 semanas antes de la votación, así que la tabla principal usa la "
             "**última encuesta preelectoral** de cada casa como «final» (fallback documentado).\n")
    L.append("- **Encuestadores privados**: solo hay datos con resultado real para 2023; las "
             "encuestas de contexto 2024–2026 no tienen elección de referencia.\n")
    L.append("- **Descarga CIS en curso**: la ingesta de estudios sigue avanzando en segundo "
             "plano; n y cobertura pueden crecer.\n")

    # anexo
    L.append("\n## Anexo A — serie CIS no validada (referencia, no usar para correcciones)\n")
    L.append(table_errors(he_all, "CIS", "micro_censo"))
    L.append("\n## Anexo B — estudios CIS usados (calidad y cobertura)\n")
    L.append("| estudio | elección | fin de campo | fuente fecha | n | calidad | cobertura partidos (% censo) | NS+NC (% censo) |")
    L.append("|---|---|---|---|---:|---|---:|---:|")
    for sid, m in sorted(est.items(), key=lambda x: x[1]["eleccion"]):
        fe = m["fecha_end"] if m["fecha_end"] not in (None, "None") else "—"
        L.append(f"| {sid} | {m['eleccion']} | {fe} | {m['end_source']} | "
                 f"{m['n']} | {m['calidad']} | {m['cobertura_partidos_censo']} | {m['ns_nc_censo']} |")

    DST.write_text("\n".join(L), encoding="utf-8")
    print("escrito", DST)


if __name__ == "__main__":
    main()
