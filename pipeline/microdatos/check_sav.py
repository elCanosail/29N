#!/usr/bin/env python3
"""Comprobacion cruzada ASCII (DA/ES) vs .sav (pyreadstat) para un estudio.

Evidencia de que el parseo ASCII universal reproduce el fichero SPSS del CIS.
Requiere el venv con pyreadstat:
  /root/.venvs/29n-micro/bin/python pipeline/microdatos/check_sav.py 3141
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(BASE))
sys.path.insert(0, os.path.join(REPO, "pipeline", "cis"))
import parse_microdata as pm          # noqa: E402
import normalize as nz                # noqa: E402


def find_sav(est):
    for root in (os.path.join(REPO, "data/raw/cis", est),
                 os.path.join(REPO, "data/raw/cis", f"MD{est}")):
        for dp, _d, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(".sav"):
                    return os.path.join(dp, f)
    return None


def main():
    est = sys.argv[1]
    import pyreadstat
    import pandas as pd

    sav = find_sav(est)
    df_sav, meta = pyreadstat.read_sav(sav)
    es, da = nz.find_data(est)
    spec, order, vl = pm.parse_es(es)
    ascii_rows = sum(1 for _ in pm.read_records(da, spec, order))

    cols = [c for c in ("PROV", "PESO", "SEXO", "EDAD", "ESCIDEOL", "RECUERDO")
            if c in df_sav.columns]

    def dist_ascii(var, weight="PESO"):
        d = {}
        for rec in pm.read_records(da, spec, order):
            k = rec.get(var)
            d[k] = d.get(k, 0.0) + (rec.get(weight) or 0.0)
        return d

    print(f"estudio {est}: sav={sav}")
    print(f"  n_sav={len(df_sav)}  n_ascii={ascii_rows}  columnas_sav={len(df_sav.columns)}")
    for c in cols:
        a = dist_ascii(c)
        s = df_sav.groupby(c)["PESO"].sum() if "PESO" in df_sav.columns else None
        print(f"  {c}: sav_cats={len(s) if s is not None else '-'} ascii_cats={len(a)}")
    # comparacion directa de una marginal ponderada
    if "SEXO" in df_sav.columns:
        sa = df_sav.groupby("SEXO")["PESO"].sum()
        aa = dist_ascii("SEXO")
        tot_a = sum(aa.values())
        print("  SEXO ponderado (%) sav  vs ascii:")
        for k in sorted(sa.index, key=lambda x: str(x)):
            print(f"    {k}: {100*sa[k]/sa.sum():.3f}  vs {100*aa.get(k,0)/tot_a:.3f}")


if __name__ == "__main__":
    main()
