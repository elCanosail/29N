#!/usr/bin/env python3
"""Parser del formato ASCII de microdatos del CIS (DAxxxx + sintaxis SPSS ESxxxx).

Los estudios antiguos (preparados antes de 2018) no traen .sav ni CSV: solo el
fichero ASCII de ancho fijo DA#### y la sintaxis SPSS ES#### con el DATA LIST.
Este módulo reconstruye las columnas y las etiquetas a partir de esa sintaxis.

Uso:
  python parse_microdata.py <ES_file> <DA_file> --var P7 [--weight PESO] [--crosstab PROV]
"""
import argparse
import collections
import re
import sys

SPEC_TOKEN = re.compile(r'([A-Za-z]\w*)\s+(\d+)(?:-(\d+))?(?:\((\d+)\))?')


def parse_es(path):
    """Devuelve (spec, value_labels) desde la sintaxis SPSS ESxxxx (latin-1)."""
    txt = open(path, encoding="latin-1").read()
    # --- DATA LIST spec ---
    m = re.search(r'DATA LIST[^\n]*\n(.*?)\.\s*\n', txt, re.S)
    spec = {}
    order = []
    if m:
        blob = m.group(1)
        for name, a, b, dec in SPEC_TOKEN.findall(blob):
            start = int(a); end = int(b) if b else start
            spec[name] = (start, end, int(dec) if dec else 0)
            order.append(name)
    # --- VALUE LABELS ---
    vl = parse_value_labels(txt)
    return spec, order, vl


def parse_value_labels(txt):
    """Parsea el bloque VALUE LABELS de la sintaxis SPSS.

    Formato real del CIS: cada variable empieza con '/NOMBRE' en su propia
    línea y las parejas 'código \'etiqueta\'' pueden seguir en las líneas
    posteriores, hasta la siguiente '/NOMBRE'.
    """
    m = re.search(r'VALUE LABELS(.*?)(?:\n\s*EXECUTE|\n\s*MISSING VALUES|\Z)',
                  txt, re.S)
    if not m:
        return {}
    vl = {}
    for chunk in re.split(r'(?m)^\s*/', m.group(1)):
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.split("\n")
        head = lines[0].split()
        if not head:
            continue
        var = head[0]
        rest = "\n".join([lines[0][len(var):]] + lines[1:])
        pairs = re.findall(r"(-?\w+)\s+'([^']*)'", rest)
        if pairs:
            vl[var] = {str(k): v for k, v in pairs}
    return vl


def read_records(da_path, spec, order):
    with open(da_path, encoding="latin-1") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            rec = {}
            for name in order:
                a, b, dec = spec[name]
                raw = line[a - 1:b].strip()
                if raw == "":
                    rec[name] = None
                elif dec:
                    # el CIS usa coma decimal en los campos con decimales (p.ej. PESO)
                    try:
                        rec[name] = float(raw.replace(',', '.'))
                    except ValueError:
                        rec[name] = None
                else:
                    try:
                        rec[name] = int(raw)
                    except ValueError:
                        rec[name] = raw
            yield rec


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("es")
    ap.add_argument("da")
    ap.add_argument("--var", required=True)
    ap.add_argument("--weight", default="PESO")
    ap.add_argument("--crosstab", default=None)
    ap.add_argument("--top", type=int, default=60)
    args = ap.parse_args()

    spec, order, vl = parse_es(args.es)
    if args.var not in spec:
        print(f"AVISO: '{args.var}' no está en el spec. Var. disponibles: "
              f"{', '.join(order[:20])} ...")
        sys.exit(2)

    tot = 0.0
    d = collections.Counter()
    ct = collections.defaultdict(collections.Counter)
    for rec in read_records(args.da, spec, order):
        w = rec.get(args.weight) or 0.0
        v = rec.get(args.var)
        tot += w
        d[v] += w
        if args.crosstab:
            ct[rec.get(args.crosstab)][v] += w

    labels = vl.get(args.var, {})
    print(f"# {args.var} ponderado por {args.weight}  (N={len(d)} cat., "
          f"suma_pesos={tot:.1f})")
    for k, v in sorted(d.items(), key=lambda x: -x[1])[:args.top]:
        lab = labels.get(str(k), "")
        print(f"  {str(k):>6}  {100*v/tot:6.2f}%  {lab}")

    if args.crosstab:
        print(f"\n# crosstab {args.crosstab} x {args.var} (pesos)")
        for c in sorted(ct, key=lambda x: (x is None, x)):
            s = sum(ct[c].values())
            print(f"  {args.crosstab}={c}: n_w={s:.1f}")


if __name__ == "__main__":
    main()
