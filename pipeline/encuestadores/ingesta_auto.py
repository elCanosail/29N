#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ingesta automática de encuestas publicadas (29N), con la regla del proyecto.

Regla (decisión de Chema, 18-10-2026, docs/plan.md Fase 3):
  - Las encuestas claras y relevantes (intención de voto de generales con ficha
    técnica verificable) se ingieren sin supervisión.
  - Las dudosas escalan a Chema con el motivo concreto.
  - Las no electorales se descartan con una línea.

Qué hace este script:
  1. Descubre las encuestas de generales del feed de electografica (Blogger).
  2. Extrae ficha técnica y desglose de voto (pipeline/encuestadores/electografica.py).
  3. Valida: n, fechas de campo, suma de voto, partidos mínimos y URL de ficha.
  4. Contrasta las cifras principales contra la fuente original (artículo o web
     del encuestador). Si no cuadra, no se ingiere: escala.
  5. Escribe un fragmento `_staging/auto-<fecha>-<slug>.json` con las encuestas
     aceptadas y las exclusiones, para que build_dataset.py las normalice.

No inventa nada: si un dato falta, la encuesta no entra.

Uso:
    python3 pipeline/encuestadores/ingesta_auto.py --desde 2026-10-24          # solo informe
    python3 pipeline/encuestadores/ingesta_auto.py --desde 2026-10-24 --write  # escribe staging
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from electografica import feed  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAGING = os.path.join(REPO, "data", "processed", "encuestadores", "_staging")
SOURCES = os.path.join(REPO, "data", "processed", "encuestadores", "sources.json")
ESCALADAS = os.path.join(REPO, "data", "processed", "cron", "escaladas.json")
UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")}

# Las diez formaciones que usa el modelo. Todo lo demás se documenta y se deja
# fuera: meter marcas nuevas (SALF, Aliança, UPN, Podemos en solitario) rompería
# la comparabilidad de la serie, que es el criterio aplicado a IMOP el 24-10.
MAPEO = {
    "PP": "PP", "PSOE": "PSOE", "VOX": "VOX",
    # El espacio Sumar se publica con etiquetas distintas por casa: FA sola,
    # «FA-FV-UPC» ya agregada, o FA + Compromís + UPC en filas separadas. Las
    # tres formas son el mismo partido y se SUMAN (no se duplican): verificado
    # contra Colmena de Datos, Sigma Dos 26-10 da FA 8,2 = 7,4 + 0,8.
    "FA": "SUMAR", "FA-FV-UPC": "SUMAR", "FRENTE AMPLIO": "SUMAR",
    "COMPROMÍS-FV": "SUMAR", "UPC": "SUMAR",
    "ERC": "ERC", "JUNTS": "JXCAT", "EH BILDU": "EH BILDU",
    "EAJ-PNV": "PNV", "CCa-1ºCAN": "CC", "CCa-1ªCAN": "CC", "CC": "CC",
}
# Etiquetas que se publican pero no entran, con su razón (se documenta por encuesta).
FUERA = {
    "PODEMOS": "Podemos concurre en solitario en 2026: plegarlo a SUMAR alteraría la serie",
    "SALF": "SALF mapea a OTROS (residual no modelado)",
    "UPN": "UPN va dentro del PP en varias casas; su fila suelta no es comparable",
    "ALIANÇA.CAT": "Aliança Catalana no tiene serie histórica en el modelo",
    "D21": "partido sin serie histórica en el modelo",
    "IE": "partido sin serie histórica en el modelo",
    "EV": "partido sin serie histórica en el modelo",
}

MIN_N, MAX_N = 200, 20000
SUMA_MIN, SUMA_MAX = 85.0, 102.0
PARTIDOS_MIN = 5
CAMPO_MAX_DIAS = 45


def _texto(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        crudo = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception:
        return None
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", crudo, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t))


def _pct_variantes(v: float) -> list[str]:
    s = f"{v:.1f}".replace(".", ",")
    return [s, s.replace(",", "."), s.rstrip("0").rstrip(",")]


def fuentes_ordenadas(c: dict) -> list[tuple[str, str]]:
    """Enlaces a probar, del más específico al más general.

    Primero la web del encuestador, después el artículo de prensa y, si no hay
    nada mejor, la propia entrada de electografica (que es donde están las
    cifras, aunque sea agregador).
    """
    casa_host = (c.get("casa") or "").lower().split()[0]
    especificos = [u for u in c["enlaces"]
                   if u.split("//")[-1].partition("/")[2].strip("/?")]
    fuera = ("electografica", "wikipedia", "twitter", "facebook", "youtube")
    orden: list[tuple[str, str]] = []
    for u in especificos:
        host = u.split("//")[-1].split("/")[0].lower()
        if casa_host and casa_host[:6] in host:
            orden.append((u, "encuestador"))
    for u in especificos:
        host = u.split("//")[-1].split("/")[0].lower()
        if not any(x in host for x in fuera) and (u, "prensa") not in orden:
            orden.append((u, "prensa"))
    orden.append((c["url_post"], "agregador"))
    return orden


def valida(c: dict) -> tuple[bool, str]:
    """(aceptada, motivo del rechazo). No toca la red."""
    if not c.get("casa"):
        return False, "sin encuestadora identificada"
    if not c.get("n"):
        return False, "sin tamaño muestral publicado"
    if not (MIN_N <= c["n"] <= MAX_N):
        return False, f"muestra fuera de rango: {c['n']}"
    if not c.get("fecha_trabajo"):
        faltan = "; ".join(c.get("faltan") or []) or "sin fechas de campo"
        return False, faltan
    fin = datetime.date.fromisoformat(c["fecha_trabajo"].split("/")[1])
    hoy = datetime.date.today()
    if fin > hoy:
        return False, f"el campo termina en el futuro ({fin})"
    if (hoy - fin).days > CAMPO_MAX_DIAS:
        return False, f"campo cerrado hace {(hoy - fin).days} días (> {CAMPO_MAX_DIAS})"
    publi = len(c.get("votos") or {})
    if publi < PARTIDOS_MIN:
        return False, f"solo publica {publi} partidos"
    s = c["suma_votos"]
    if not (SUMA_MIN <= s <= SUMA_MAX):
        return False, f"la suma de voto publicado no cuadra ({s} %)"

    canonicos = {MAPEO[k] for k in c["votos"] if k in MAPEO}
    faltan = {"PP", "PSOE", "VOX", "SUMAR"} - canonicos
    if faltan:
        return False, f"falta el desglose de {', '.join(sorted(faltan))}"
    if not c.get("metodologia"):
        return False, "sin método de recogida"
    return True, ""


def contrasta(c: dict, url: str) -> tuple[bool, str]:
    """Las cifras grandes deben aparecer en la fuente original."""
    if url == c["url_post"]:
        return True, ""  # la fuente ES electografica: sus cifras son la fuente
    t = _texto(url)
    if t is None:
        return False, f"la ficha no responde ({url[:60]})"
    grandes = sorted(c["votos"].items(), key=lambda kv: -kv[1])[:3]
    encontrados = 0
    for siglas, v in grandes:
        variantes = _pct_variantes(v)
        # Con o sin «%», y con las siglas delante cuando el artículo las pone:
        # «el PP obtendría el 32,4%» o simplemente «32,4».
        if any(x in t for x in variantes) or any(
                re.search(rf"{re.escape(siglas)}\D{{0,40}}{re.escape(p)}\s*%", t, re.I)
                for p in variantes):
            encontrados += 1
    if encontrados == 0:
        return False, "la fuente no reproduce ninguna de las tres cifras principales"
    return True, f"{encontrados}/3 cifras principales confirmadas"


def votos_canonicos(c: dict) -> tuple[dict, list[str]]:
    votos, fuera = {}, []
    for etiqueta, pct in c["votos"].items():
        if etiqueta in MAPEO:
            canon = MAPEO[etiqueta]
            votos[canon] = round(votos.get(canon, 0.0) + pct, 1)
        elif etiqueta in FUERA:
            fuera.append(f"{etiqueta} ({pct}%): {FUERA[etiqueta]}")
    return votos, fuera


def ya_ingerida(c: dict, existentes: list[dict]) -> bool:
    """Duplicado si misma casa y mismo fin de campo (o mismo id)."""
    for e in existentes:
        if (e.get("fuente") or "").upper() == (c["casa"] or "").upper() and \
                (e.get("fecha_trabajo") or "").split("/")[-1] == \
                (c.get("fecha_trabajo") or "").split("/")[-1]:
            return True
    return False


def slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().replace("á", "a").replace("é", "e")
               .replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n"))
    return s.strip("-")[:24]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default=None, help="fecha ISO mínima de publicación")
    ap.add_argument("--write", action="store_true", help="escribe el fragmento de staging")
    ap.add_argument("--dia", default=None, help="agrupa el fragmento por esta fecha (ISO)")
    args = ap.parse_args()

    if args.desde is None:
        ultimo = ""
        if os.path.exists(SOURCES):
            with open(SOURCES, encoding="utf-8") as fh:
                pubs = [s.get("fecha_publicacion") or "" for s in json.load(fh)]
            ultimo = max(pubs) if pubs else ""
        # Margen de 3 días: una encuesta puede publicarse con retraso en el
        # agregador. Los duplicados los corta `ya_ingerida`, no la fecha.
        if ultimo:
            args.desde = (datetime.date.fromisoformat(ultimo)
                          - datetime.timedelta(days=3)).isoformat()
        else:
            args.desde = "2026-01-01"

    candidatas = feed(args.desde)
    existentes = json.load(open(SOURCES, encoding="utf-8")) if os.path.exists(SOURCES) else []

    aceptadas, descartadas, escaladas = [], [], []
    for c in candidatas:
        if ya_ingerida(c, existentes) or any(
                (a["fuente"] or "").upper() == (c["casa"] or "").upper() and
                a["fecha_trabajo"] == c.get("fecha_trabajo") for a in aceptadas):
            continue
        ok, motivo = valida(c)
        if not ok:
            (escaladas if "solo publica" in motivo or "no cuadra" in motivo
             or "falta el desglose" in motivo else descartadas).append(
                {"fuente": c["casa"], "publicado": c["publicado"], "url": c["url_post"],
                 "motivo": motivo})
            continue
        url = tipo = nota = ""
        fallos = []
        for cand, cand_tipo in fuentes_ordenadas(c):
            ok_c, nota_c = contrasta(c, cand)
            if ok_c:
                url, tipo, nota = cand, cand_tipo, nota_c
                break
            fallos.append(nota_c)
        if not url:
            escaladas.append({"fuente": c["casa"], "publicado": c["publicado"],
                              "url": fuentes_ordenadas(c)[0][0],
                              "motivo": fallos[0] if fallos else "sin fuente verificable"})
            continue
        votos, fuera = votos_canonicos(c)
        fin = c["fecha_trabajo"].split("/")[1]
        aceptadas.append({
            "fuente": c["casa"],
            "estudio_id": f"{slug(c['casa'])}-{fin}",
            "fecha_trabajo": c["fecha_trabajo"],
            "fecha_publicacion": c["publicado"],
            "n": c["n"],
            "metodologia": c["metodologia"],
            "ambito": "nacional",
            "eleccion": "generales 2026",
            "url": url,
            "extracto": (f"[{c['casa']}, publicado {c['publicado']}; ficha: {url}] "
                         f"{c['titulo']}. Campo {c['fecha_trabajo']}, n={c['n']}, "
                         f"método {c['metodologia']}. Voto estimado publicado: "
                         + ", ".join(f"{k} {v}%" for k, v in c["votos"].items() if v > 0)
                         + f". Suma de lo publicado {c['suma_votos']} %. "
                         f"Lectura desde electografica.com ({c['url_post']}); "
                         f"contraste: {nota or 'la ficha es el propio agregador'}."),
            "votos": votos,
            "fuente_votos_adicionales": (
                "Etiquetas publicadas y no ingestadas: " + "; ".join(fuera) + "."
                if fuera else ""),
            "fuente_tipo_hint": tipo,
        })

    print(f"## Ingesta automática de encuestas — desde {args.desde}")
    print(f"candidatas: {len(candidatas)} · aceptadas: {len(aceptadas)} · "
          f"escaladas: {len(escaladas)} · descartadas: {len(descartadas)}\n")
    for a in aceptadas:
        print(f"  ✅ {a['fecha_publicacion']} {a['fuente']} · {a['estudio_id']} · "
              f"n={a['n']} · {len(a['votos'])} partidos · campo {a['fecha_trabajo']}")
        print(f"      {a['url'][:100]}")
    for e in escaladas:
        print(f"  ⚠️  {e['publicado']} {e['fuente']} → {e['motivo']}")
        print(f"      {e['url'][:100]}")
    for d in descartadas:
        print(f"  ·  {d['publicado']} {d['fuente']} descartada: {d['motivo']}")

    if escaladas:
        os.makedirs(os.path.dirname(ESCALADAS), exist_ok=True)
        previas = json.load(open(ESCALADAS, encoding="utf-8")) if os.path.exists(ESCALADAS) else []
        vistas = {(p.get("url"), p.get("motivo")) for p in previas}
        for e in escaladas:
            if (e["url"], e["motivo"]) not in vistas:
                previas.append({**e, "detectada": datetime.date.today().isoformat()})
        json.dump(previas, open(ESCALADAS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if args.write and aceptadas:
        dia = args.dia or datetime.date.today().isoformat()
        os.makedirs(STAGING, exist_ok=True)
        ruta = os.path.join(STAGING, f"auto-{dia}.json")
        frag = {"encuestas": aceptadas, "exclusiones": []}
        if fuera:
            frag["exclusiones"].append({
                "fuente": aceptadas[0]["fuente"],
                "motivo": "Etiquetas publicadas fuera del modelo (se listan en "
                          "fuente_votos_adicionales de cada encuesta): "
                          + "; ".join(fuera) + ".",
            })
        for d in descartadas:
            frag["exclusiones"].append({"fuente": d["fuente"],
                                        "motivo": f"{d['publicado']}: {d['motivo']} ({d['url']})"})
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(frag, fh, ensure_ascii=False, indent=1)
        print(f"\nfragmento escrito: {os.path.relpath(ruta, REPO)} "
              f"({len(aceptadas)} encuestas, {len(frag['exclusiones'])} exclusiones)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
