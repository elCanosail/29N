"""Canonicalización de partidos para el análisis de efectos de casa (29N, fase 4-bis).

Objetivo: unificar en una misma familia canónica
  (a) las etiquetas del diccionario CIS (`pipeline/party_aliases.csv`), y
  (b) los `partido_id` del Ministerio del Interior (`data/processed/interior/`),
con las ramas territoriales agregadas a su matriz nacional (PSC/PSE/PSdG -> PSOE,
AP/AP-PDP/Coalición Popular -> PP, etc.), porque el CIS publica ya agregado.

El universo de partidos es el que se puede seguir a lo largo de la serie CIS.
Todo lo no mapeado cae en OTROS.
"""

# --- Familias con ramas territoriales -------------------------------------
# Interior lista las candidaturas provinciales por su sigla local; el CIS las
# agrega en la matriz nacional. Estas listas replican esa agregación.

PSOE_SLUGS = {
    "psoe", "psc", "pse", "psdeg", "psg", "psib", "pspv", "psoe-a", "psoe-de-a",
    "psoe-h", "psoe-nca", "ps-g-psoe", "psg-psoe", "psdg-psoe", "pse-ee-pso",
    "pse-ee-psoe", "psc-psc-psoe", "psn-psoe", "psib-psoe", "p-s-o-e", "pspc",
    "pspa", "psoe-progr", "psoe-progresistas",
}
PP_SLUGS = {
    "pp", "p-p", "ap", "ap-pdp", "ap-pdp-par", "ap-pdp-pdl", "ap-pdp-pl",
    "ap-pdp-pl-c", "ap-pdp-uv", "ap-pl-upn", "upn-ap-pdp", "upn-pp", "pp-par",
    "pp-foro", "pp-upm", "pp-c-de-g", "pp-eu", "ppcr", "pprov",
}
IU_SLUGS = {
    "iu", "iuc", "iulv", "eupv", "pce", "psuc", "ic", "icv", "eu", "iu-eu",
    "iun-neb", "iuc-cxi", "iuc-iph-lv", "iu-b-a-los-verdes", "iu-b-upec", "iu-ba",
    "iu-cha-upec", "iu-cl", "iu-cm", "iu-cyl", "iu-eb", "iu-icam", "iu-icu",
    "iu-ix", "iu-lv", "iu-pdsc", "iu-siex", "iu-upec", "iu-upec-ias",
    "iu-v-siex", "iu-verdes-s", "iucl", "iuclm-lv", "iucm-lv", "iucyl",
    "iulv-ca-up", "iulv-ca-upe", "iuv-rm", "icv-euia", "icv-gorordo", "ic-ev",
    "ic-v", "pce-epk", "pce-m-l", "pce-pcg", "pce-pv", "pca-pce", "pcc-pce",
    "eupv-ev", "eupv-ir", "eupv-lv", "eupv-upec", "eu-eue", "eu-ev", "eu-ex",
    "eu-pv", "eu-ug", "eu-v", "eu-eg",
}
UP_SLUGS = {
    "up", "podemos", "ecp", "emarea", "en-comú", "podemos-aha", "podemos-aho",
    "podemos-com", "podemos-en", "podemos-eu", "podemos-eui", "podemos-euib",
    "podemos-eupv", "podemos-iu", "podemos-iu-alto-aragón-en-común",
    "podemos-iu-batzarre", "podemos-iu-equo", "podemos-iu-equo-batzarre",
    "podemos-iu-equo-berdeak", "podemos-iu-equo-clias", "podemos-iu-equo-izca",
    "podemos-iu-equo-segoviemos", "podemos-iu-lv-ca", "podemos-iu-lv-ca-equo",
    "podemos-ix", "podemos-ix-equo", "ecp-guanyem-el-canvi",
    "podemos-ahal-dugu-iu-equo", "podemos-en-marea-anova-eu", "up-iulv-ca",
    "up-upec", "upb-iu-upe", "upec-iu", "upec-iu-izc", "iu-b-upec",
    "unidad-popu", "unidadpopular-partido", "adl-iu",
}
# SUMAR 2023 (coalición) — Interior la lista por su sigla nacional
SUMAR_SLUGS = {"sumar", "sumar-aragón", "més-per-mallorca-més-per-menorca-sumar"}

# Partidos con sigla estable propia
SIMPLE = {
    "vox": "VOX",
    "cs": "CIUDADANOS", "c-s": "CIUDADANOS", "c-d-s": "CIUDADANOS",
    "erc": "ERC", "erc-catsí": "ERC", "erc-sobiranistes": "ERC",
    "erc-ri-cat": "ERC", "esquerra": "ERC", "esquerra-pv": "ERC",
    "ciu": "JXCAT", "cdc": "JXCAT", "junts": "JXCAT", "jxc": "JXCAT",
    "jxg": "JXCAT", "dcar": "JXCAT", "dl": "JXCAT", "pdecat-e-ciu": "JXCAT",
    "pnv": "PNV", "pnv-nv": "PNV",
    "hb": "EH BILDU", "eb": "EH BILDU", "eb-az": "EH BILDU", "eb-b": "EH BILDU",
    "eb-iu": "EH BILDU", "ehbildu": "EH BILDU", "amaiur": "EH BILDU",
    "anv": "EH BILDU",
    "bng": "BNG", "b-n-g": "BNG", "bng-nós": "BNG", "bnpg": "BNG",
    "cup": "CUP", "cup-pr": "CUP",
    "cc": "CC", "cc-ap": "CC", "cc-ucd": "CC", "cca-pnc": "CC",
    "cc-nc-pnc": "CC", "cc-pnc-pil": "CC", "cca-pnc-nc": "CC",
    "cc-nc": "CC", "ccnc": "CC",
    "na": "NA+", "upn": "NA+", "na-bai": "NA+",
    "nc-bc": "NC", "nc-cca-pnc": "NC", "nc-ccn": "NC", "nca": "NC",
    "cds": "CDS", "cdas-cds": "CDS", "cds-uc": "CDS", "cdas": "CDS",
    "ucd": "UCD",
    "upyd": "UPYD",
    "compromis": "COMPROMIS", "compromís-2": "COMPROMIS",
    "compromís-q": "COMPROMIS", "més": "COMPROMIS",
    "maspais": "MÁS PAÍS", "m-país": "MÁS PAÍS", "más-país-equo": "MÁS PAÍS",
    "más-país-andalucía": "MÁS PAÍS",
    "más-país-candidatura-ecologista": "MÁS PAÍS",
    "geroabai": "GEROA BAI",
    "par": "PAR",
    "prc": "PRC",
    "pacma": "PACMA",
    "cha": "CHA", "cha-iu": "CHA",
    "ea": "EA",
}

_PSOE_PREFIX = ("psoe", "psc")
_PP_PREFIX = ("pp", "ap-", "p-p")
_IU_PREFIX = ("iu", "iuc", "iulv", "eupv", "pce", "icv", "ic-", "eu-", "euia",
              "eupv", "esquerra-uni")
_UP_PREFIX = ("podemos", "ecp", "en-com", "en-comú", "emarea", "unidas",
              "unidos", "uple", "upe")


# Coaliciones dependientes de la era: la misma sigla de Interior significa
# cosas distintas según el año (nota cis-ingest.md §4). Estas excepciones se
# fijan por (elección, slug) y se validan contra los resultados oficiales.
ERA_OVERRIDES = {
    ("2023-07-23", "ecp"): "SUMAR",
    ("2023-07-23", "compromis"): "SUMAR",
    ("2023-07-23", "més-per-mallorca-més-per-menorca-sumar"): "SUMAR",
    ("2023-07-23", "sumar-aragón"): "SUMAR",
    ("2019-04-28", "compromís-2"): "UNIDAS PODEMOS",
    ("2019-11-10", "compromis"): "COMPROMIS",
    ("2019-11-10", "compromís-2"): "COMPROMIS",
    ("2015-12-20", "compromis"): "UNIDAS PODEMOS",
    ("2016-06-26", "compromis"): "UNIDAS PODEMOS",
}


def canonical_of_slug(slug, eleccion_id=None):
    """partido_id de Interior -> canónico del análisis (o 'OTROS').

    `eleccion_id` permite resolver las coaliciones dependientes de la era.
    """
    if not slug:
        return "OTROS"
    s = slug.strip().lower()
    if eleccion_id and (eleccion_id, s) in ERA_OVERRIDES:
        return ERA_OVERRIDES[(eleccion_id, s)]
    if s in SIMPLE:
        return SIMPLE[s]
    if s in PSOE_SLUGS:
        return "PSOE"
    if s in PP_SLUGS:
        return "PP"
    if s in IU_SLUGS:
        return "IU"
    if s in UP_SLUGS:
        return "UNIDAS PODEMOS"
    if s in SUMAR_SLUGS:
        return "SUMAR"
    # prefijos (ramas territoriales que no enumeramos)
    if s.startswith(_PSOE_PREFIX):
        return "PSOE"
    if s.startswith(_UP_PREFIX):
        return "UNIDAS PODEMOS"
    if s.startswith(_PP_PREFIX) or s.startswith("ap"):
        return "PP"
    if s.startswith("iu") or s.startswith("eupv") or s.startswith("pce"):
        return "IU"
    return "OTROS"


# --- Etiquetas CIS -> canónico ---------------------------------------------
# Réplica del diccionario `pipeline/party_aliases.csv` (columna canonical),
# con las coaliciones dependientes de la era resueltas A MANO por elección
# donde el diccionario estático las cruza (nota cis-ingest.md §4).

CIS_DIRECT = {
    "PP": "PP", "PSOE": "PSOE", "VOX": "VOX", "SUMAR": "SUMAR",
    "PODEMOS": "PODEMOS", "IU": "IU", "UNIDAS PODEMOS": "UNIDAS PODEMOS",
    "CIUDADANOS": "CIUDADANOS", "CDS": "CDS", "UCD": "UCD", "ERC": "ERC",
    "JXCAT": "JXCAT", "PNV": "PNV", "EH BILDU": "EH BILDU", "BNG": "BNG",
    "CUP": "CUP", "CC": "CC", "NC": "NC", "NA+": "NA+",
    "COMPROMIS": "COMPROMIS", "MÁS PAÍS": "MÁS PAÍS", "UPYD": "UPYD",
    "PACMA": "PACMA", "PRC": "PRC", "GEROA BAI": "GEROA BAI", "PAR": "PAR",
    "CHA": "CHA",
}


def canonical_of_cis(label, anio=None):
    """Etiqueta canónica de polls.jsonl (CIS) -> canónico del análisis.

    Devuelve None para categorías no partidistas (NS, NC, EN BLANCO,
    VOTO NULO, ABSTENCION, NO DECIDIDO, OTROS).
    """
    if not label:
        return None
    c = label.strip().upper()
    if c in ("NS", "NC", "EN BLANCO", "VOTO NULO", "ABSTENCION",
             "NO DECIDIDO", "OTROS"):
        return None
    return CIS_DIRECT.get(c, c)
