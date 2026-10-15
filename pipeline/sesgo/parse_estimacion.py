"""Parser de las tablas publicadas de "Estimación de voto" del CIS (29N, sesgo).

Extrae, del PDF de estimación de cada estudio electoral, dos columnas por
partido:
  - `directo`: "Voto directo en la encuesta (en % sobre censo)"
  - `estim`:   "Estimación de voto CIS (en % sobre voto válido)"

El formato de la tabla cambia entre estudios (con/sin margen de error, con/sin
escaños, y en 3269 una columna intermedia de voto directo sobre voto emitido).
Se resuelve contando los tokens numéricos de cada fila: se descartan los que
llevan '±' (margen) y los rangos de escaños ('120-128', '122 – 140'), y se
toma el primero como voto directo y el último como estimación.
"""
import re
import unicodedata

# Nombre en la tabla -> canónico del análisis (None = categoría no partidista)
NAME_MAP = {
    "PP": "PP", "PSOE": "PSOE", "VOX": "VOX", "SUMAR": "SUMAR",
    "MOVIMIENTO SUMAR": "SUMAR", "UNIDAS PODEMOS": "UNIDAS PODEMOS",
    "UNIDOS PODEMOS": "UNIDAS PODEMOS", "PODEMOS": "PODEMOS",
    "IU": "IU", "IU (UNIDAD POPULAR)": "IU", "IZQUIERDA UNIDA": "IU",
    "CIUDADANOS": "CIUDADANOS", "CS": "CIUDADANOS", "UPYD": "UPYD",
    "ERC": "ERC", "JXCAT": "JXCAT", "JUNTS": "JXCAT", "JUNTSXCAT": "JXCAT",
    "EAJ-PNV": "PNV", "EAJ-PN": "PNV", "PNV": "PNV",
    "EH BILDU": "EH BILDU", "EH-BILDU": "EH BILDU", "BILDU": "EH BILDU",
    "BNG": "BNG", "CUP": "CUP",
    "CCA-NC": "CC", "CCA": "CC", "CC": "CC", "CC-PNC": "CC", "CC/PNC": "CC",
    "NC": "NC", "NA+": "NA+", "NAVARRA SUMA": "NA+",
    "MÁS PAÍS": "MÁS PAÍS", "MÁS PAÍS /": "MÁS PAÍS",
    "GEROA BAI": "GEROA BAI", "PAR": "PAR", "PRC": "PRC", "CHA": "CHA",
    "COMPROMÍS": "COMPROMIS", "MÉS COMPROMÍS": "COMPROMIS",
}
NON_PARTY = {"EN BLANCO", "VOTO NULO", "ABSTENCIÓN", "ABSTENCION",
             "NO SABE", "NO CONTESTA", "OTROS PARTIDOS", "OTROS"}


def _norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def canon_name(raw):
    n = _norm(raw)
    # quitar sufijos de nota: "(1)", "(2)", "**", "*"
    n = re.sub(r"\s*\([0-9a-z]+\)\s*$", "", n).strip()
    n = n.rstrip("*").strip()
    if n in NON_PARTY:
        return None
    if n in NAME_MAP:
        return NAME_MAP[n]
    for k, v in NAME_MAP.items():
        if n.startswith(k):
            return v
    return None


_NUM = re.compile(r"^-?\d+,\d+$")
_RANGE = re.compile(r"^\d+\s*[-–]\s*\d+$")
_ROW = re.compile(r"^\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 .,()/–\-]+?)\s{2,}(.*\d,\d.*)$")


def parse_total_nacional(text):
    """Devuelve {canonico: {'directo': float, 'estim': float}} del primer
    cuadro nacional de estimación que aparezca en el texto."""
    out = {}
    lines = text.splitlines()
    # localizar la cabecera del primer cuadro nacional. La cabecera puede
    # ocupar varias líneas, así que basta con encontrar "voto directo".
    start = None
    for i, ln in enumerate(lines):
        if "voto directo" in ln.lower():
            start = i
            break
    if start is None:
        for i, ln in enumerate(lines):
            if "estimaci" in ln.lower() and "cis" in ln.lower():
                start = i
                break
    if start is None:
        return out
    for ln in lines[start:start + 60]:
        m = _ROW.match(ln)
        if not m:
            continue
        name, tail = m.group(1), m.group(2)
        canon = canon_name(name)
        if not canon:
            continue
        toks = re.findall(r"±\d+,\d+|^\d+\s*[-–]\s*\d+$|\d+\s*[-–]\s*\d+|\d+,\d+",
                          tail)
        nums = [t for t in toks if _NUM.match(t)]
        if len(nums) < 2:
            continue
        directo = float(nums[0].replace(",", "."))
        estim = float(nums[-1].replace(",", "."))
        out[canon] = {"directo": directo, "estim": estim}
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path
    for p in sorted(Path("data/raw/cis/estimacion").glob("est*.txt")):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        t = parse_total_nacional(txt)
        print(p.name, len(t), t)
