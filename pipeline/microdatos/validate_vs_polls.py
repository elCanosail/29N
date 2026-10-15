#!/usr/bin/env python3
"""Fase 4-c — Validacion de la extraccion individual contra polls.jsonl.

Prueba de correccion: los agregados ponderados calculados a partir del dataset
individual (data/processed/microdatos/individual.parquet) deben reproducir los
agregados ya validados de data/processed/cis/polls.jsonl (tolerancia +-0,1 pp).

No se lee `variable_voto` de studies.json para re-agregar a mano: se usa la
columna `intencion_voto` del dataset individual tal cual, calculada con el
mismo canonizador (normalize.canonize). La comparacion es por partido canonico.

Salida: data/processed/microdatos/validation_micro.json
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(BASE))
OUT = os.path.join(REPO, "data/processed/microdatos")
POLLS = os.path.join(REPO, "data/processed/cis/polls.jsonl")
TOL = 0.1
# 5 estudios exigidos, cubriendo eras distintas (>=2015 y fondos antiguos)
REQUIRED = ["1135", "1181", "3117", "3242", "3263", "3415"]


def main():
    import pandas as pd
    df = pd.read_parquet(os.path.join(OUT, "individual.parquet"),
                         columns=["estudio_id", "anio", "peso", "intencion_voto"])
    polls = [json.loads(l) for l in open(POLLS, encoding="utf-8")]

    pub = {}
    for r in polls:
        pub.setdefault(r["estudio_id"], {})[r["partido"]] = r["voto_pct"]

    results = []
    for est, table in sorted(pub.items(), key=lambda kv: kv[0]):
        sub = df[df["estudio_id"] == est]
        if sub.empty:
            results.append({"estudio": est, "estado": "SIN_DATOS_INDIVIDUALES"})
            continue
        tot = float(sub["peso"].sum())
        agg = sub.groupby("intencion_voto")["peso"].sum()
        mine = {k: 100.0 * float(v) / tot for k, v in agg.items() if k is not None}
        deltas = []
        for party, pct in table.items():
            d = abs(mine.get(party, 0.0) - pct)
            deltas.append({"partido": party, "polls": pct,
                           "individual": round(mine.get(party, 0.0), 3),
                           "delta": round(d, 4)})
        deltas.sort(key=lambda x: -x["delta"])
        worst = deltas[0] if deltas else {"partido": None, "delta": None}
        results.append({
            "estudio": est, "anio": int(sub["anio"].iloc[0]),
            "n_individuos": int(len(sub)), "suma_pesos": round(tot, 2),
            "partidos_comparados": len(deltas),
            "max_delta_pp": round(worst["delta"], 4) if worst["delta"] is not None else None,
            "peor_partido": worst["partido"],
            "ok": (worst["delta"] is not None and worst["delta"] <= TOL),
            "deltas": deltas,
        })

    ok = [r for r in results if r.get("ok")]
    req = [r for r in results if r["estudio"] in REQUIRED]
    summary = {
        "tolerancia_pp": TOL,
        "estudios_comparados": len([r for r in results if r.get("max_delta_pp") is not None]),
        "estudios_ok": len(ok),
        "requeridos": REQUIRED,
        "requeridos_ok": [r["estudio"] for r in req if r.get("ok")],
        "requeridos_fallidos": [r["estudio"] for r in req if not r.get("ok")],
        "max_delta_global_pp": max((r["max_delta_pp"] for r in results
                                    if r.get("max_delta_pp") is not None), default=None),
        "detalle": results,
    }
    t = os.path.join(OUT, "validation_micro.json.tmp")
    with open(t, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    os.replace(t, os.path.join(OUT, "validation_micro.json"))

    for r in results:
        if r.get("max_delta_pp") is None:
            print(f"  {r['estudio']}: {r.get('estado')}")
        else:
            print(f"  {r['estudio']} ({r['anio']}) n={r['n_individuos']:>6} "
                  f"partidos={r['partidos_comparados']:>2} maxΔ={r['max_delta_pp']:.4f} pp "
                  f"[{r['peor_partido']}] {'OK' if r['ok'] else 'FALLA'}")
    print(json.dumps({k: v for k, v in summary.items() if k != "detalle"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
