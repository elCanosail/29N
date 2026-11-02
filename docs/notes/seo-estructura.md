# Estructura de la información y posicionamiento (tramos 1 y 2)

Fecha: 2026-11-02 · Autor: Elcano · Decisión de Chema: «Orquesta esta noche los tramos 1 y 2».

## Por qué

El sitio tenía **10 URLs indexables** y los activos con más valor —78 fichas de
encuesta, 52 provincias, 16 elecciones, 14 encuestadores— dentro de tres páginas
enormes. Sin páginas de entidad no hay long tail que rastrear: se puede competir
por «encuestas elecciones generales» (imposible de ganar contra los agregadores)
o por «encuesta Sigma Dos 26 de octubre» (ganable, y el dato ya estaba).

Criterio aplicado: **una página por entidad, con dato real detrás y fuente
citada**. Nada de páginas vacías por provincia ni de copiar el titular de otro.

## Familias de URL (189 páginas construidas)

| Familia | Nº | Contenido | lastmod |
|---|---|---|---|
| `/encuestas/[id]/` | 78 | Ficha técnica, estimaciones, extracto y fuente original | Última fecha de campo o publicación de esa encuesta |
| `/encuestadores/[slug]/` | 14 | Histórico de la casa + MAE y sesgo medio medidos | Última encuesta de la casa |
| `/prediccion/[provincia]/` | 52 | Escaños por partido, IC 95 % y P(≥1 escaño) | Fecha de generación de `seats.json` |
| `/elecciones/[id]/` | 16 | Resultado oficial candidatura por candidatura | Fecha de la elección |
| `/partidos/[slug]/` | 13 | Serie del partido, escaños y nº de encuestas | Generación de `seats.json` |
| `/series/`, `/glosario/`, `/exclusiones/`, `/encuestadores/`, `/elecciones/`, `/partidos/` | 6 | Índices y páginas de referencia | Según dato |
| Portada, predicción, resultados, simulador, microdatos, metodología, blog, 404 | 10 | Ya existentes | Sin cambio |

## Datos estructurados (JSON-LD)

- `Organization` + `WebSite` en la portada (con `SearchAction`).
- `BreadcrumbList` en todas las páginas con migas (lo emite `Breadcrumbs.astro`).
- `Report` en cada ficha de encuesta, con `temporalCoverage`, `isBasedOn` (URL de
  la fuente) y `variableMeasured` por partido.
- `Dataset` en predicción provincial, elecciones, encuestadores, partidos, series.
- `FAQPage` en la portada de predicción (5 preguntas) y en el glosario.
- `Article` en los posts del blog.

Regla: **solo se marca lo que se ve**. Si el número no está en la página, no va
en el JSON-LD.

## Detalles técnicos que importan

- `canonical` autorreferente y `og:url` en `Base.astro` (antes no había ninguno).
- `og:image` por defecto en `/og/portada.png`, generada con los datos reales del
  día. Las tarjetas por entidad quedan para el tramo 3.
- `lastmod` real por familia en `astro.config.mjs`; 180 de 189 URLs lo llevan. Las
  9 restantes son páginas de contenido estático, y ahí no se inventa fecha.
- `inferir títulos`: el sufijo «· 29N» no se duplica si el título ya lo contiene.
- Las cifras solo entran al `<title>` de una encuesta si la primera fuerza supera
  el 15 % y es una marca reconocible; si no, el título dice «ficha técnica».
- `nacional` y `estatal` se unificaron en `sync-data.py`: partían los filtros y
  las páginas de entidad en dos vocabularios para lo mismo.

## Tramo 3 (pendiente)

1. Tarjetas OG por encuesta y por provincia (requiere `satori`/`@vercel/og` o
   rasterizado en build; hoy hay una sola imagen).
2. Comparador de dos encuestas y descarga CSV/JSON con cita.
3. `/api/` documentada con nombres estables.
4. Post-mortem del 30N: publicar el error real. Es el activo que ningún agregador
   tiene y el que genera enlaces.
5. 1-2 piezas de blog por semana.

## Cómo se comprueba

```bash
cd web && npm run build
# 189 páginas, 0 enlaces internos rotos, 0 páginas sin canonical
python3 - <<'PY'
import re, glob, os
root='dist'
pages=[f for f in glob.glob(f'{root}/**/index.html', recursive=True)]
sin=[p for p in pages if 'rel="canonical"' not in open(p).read()]
print(len(pages), 'páginas ·', len(sin), 'sin canonical')
PY
```
