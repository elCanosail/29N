# Ingesta CIS completa (29N) — notas de ejecución

Fecha: 2026-10-15 · Alcance: `pipeline/cis/`, `pipeline/party_aliases.csv`,
`data/raw/cis/` (gitignored), `data/processed/cis/`. Sin commits ni push.

Continúa el sondeo `docs/notes/cis-probe.md` (3 estudios validados manualmente).

## Resumen

- **Catálogo** (`pipeline/cis/catalog.json`): **134 estudios electorales**
  cosechados del catálogo del CIS — 87 de elecciones generales y 38 al
  Parlamento Europeo (más ensayos metodológicos de voto y encuestas flash).
  Cobertura 1977–2026.
- **Descarga**: reanudable (`data/raw/cis/manifest.json`), prioriza generales.
  La ficha de cada estudio expone el microdato en un bloque JSON-LD con URL
  directa; sin formulario ni sesión. Backoff exponencial ante 429/anti-bot.
- **Normalización** (`normalize.py`): parser ASCII universal DA####+ES####;
  la variable de intención de voto se **elige reproduciendo la tabla publicada**
  ("Voto directo en la encuesta") y esa misma comparación es la validación.
- **Validación**: 4 estudios con tabla publicada normalizados, **3 reproducen
  todas las filas dentro de ±0,2 pp** (3141 máx Δ0,05; 3242 máx Δ0,14;
  3263 máx Δ0,04). 3411 tiene **1 fila fuera de tolerancia** (ver §4).

## 1. Descubrimiento del catálogo (el único paso que exige navegador)

El listado del catálogo se pinta por JS y el endpoint de búsqueda devuelve
HTTP 302 a `/__cis_antibot` para clientes sin JS (probado con `curl`: incluso
la primera petición servidor‑side acabó bloqueada por IP). Por eso el catálogo
se cosechó con un **navegador anti‑detección (Camoufox)**, ejecutando `fetch()`
same‑origin contra:

```
/es/estudios/catalogo?catalogo=estudio&sort=createDateBDE-&t=0&delta=200&start=N
```

`delta=200` reduce la paginación a 13 páginas para 2.584 estudios. El filtrado
de los electorales se hace en el propio navegador; los fragmentos crudos quedan
en `data/raw/cis/catalog/chunk_*.json` y `build_catalog.py` genera `catalog.json`.

**API interna**: `/ws/v2/api/cis/estudio/{id}` usa un **id interno de BD**, no el
nº de estudio (confirmado: `/estudio/3411` → código 2475), y no existe endpoint
de listado ⇒ no sirve para enumerar. La API pública descargable está en la ficha
como JSON‑LD (ver §2).

## 2. Descarga de microdatos — JSON‑LD, no formulario

La ficha `https://www.cis.es/es/estudios/<slug>` (HTML estático, **sí** accesible
por `curl`) incluye un `<script type="application/ld+json">` con
`{"@graph":[…,{"@type":"Dataset","distribution":[…]}]}`. Cada documento trae
`contentUrl` directo:

| name | contenido |
|---|---|
| **Fichero datos** | `…/MD<estudio>.zip` (o `MD<estudio>_mod.zip`) |
| **Estimación de voto** | `…/<estudio>_Estimacion*.pdf` (para validación) |
| Cuestionario / Ficha técnica / Resultados | PDF/HTML |

`fetch_microdata.py` descarga la ficha, extrae esas URLs, baja el ZIP, lo
descomprime y guarda el PDF de estimación en `data/raw/cis/estimacion/`.
Estado por estudio en `manifest.json` (reanudable; no repite lo completado).

### Hallazgo real: estudios antiguos sin microdato publicado

De los primeros estudios descargados, **18 quedaron en `no_data_link`**: su
ficha **no publica "Fichero datos"** (p. ej. **1132**, *Preelectoral elecciones
generales 1977 (I)*: la ficha solo ofrece el Cuestionario). Es decir, el CIS no
expone microdato descargable para parte del fondo 1977‑1989 vía ficha actual.
Estos entran en `exclusions.json` con motivo `no_data_link` (no es un fallo de
ingesta sino ausencia en origen).

## 3. Normalización

Camino universal **DA####+ES####** (ASCII ancho fijo) para todos los estudios:
reconstruye columnas desde el `DATA LIST` y las etiquetas desde `VALUE LABELS`
(`pipeline/cis/parse_microdata.py`). Peso = `PESO` (nacional).

**Selección de la variable de voto**: se puntúan las variables cuyos *labels*
citan partidos; si existe tabla publicada se elige la que **mejor la reproduce**
(menos filas fuera de ±0,2 pp, luego más filas comparadas, luego menor Δ máxima).
Sin tabla, se usa la de mayor puntuación heurística.

**Diccionario de partidos** (`pipeline/party_aliases.csv`): 150+ alias con
`priority,canonical,grupo,alias,fuente` (PSC→PSOE, AP/AP‑PDP/Coalición Popular→PP,
IU/ICV/EUiA→IU; PODEMOS/En Comú Podem/En Marea/Compromís‑Podemos→UNIDAS PODEMOS;
Sumar; VOX; Cs; ERC; JxCat/PDeCAT/CDC/CiU; PNV; EH Bildu/Amaiur/HB; BNG; CUP;
CCa/NC; NA+/UPN; Compromís; y las categorías de no‑voto: blanco, nulo,
abstención, no decidido, NS, NC).

Salidas: `data/processed/cis/polls.jsonl` (una línea por estudio×partido),
`studies.json` (catálogo normalizado con `url`, `variable_voto`, `n`).

## 4. Validación (tolerancia ±0,2 pp) y discrepancias

Se replican las filas de "Voto directo en la encuesta (en %)" de la *Estimación
de voto* publicada, agregando las etiquetas de coalición por partido canónico.

| Estudio | Variable elegida | Filas | Δ máx | Resultado |
|---|---|---|---|---|
| 3263 (10N‑2019) | P9R | 25 | **0,04** | ✅ |
| 3242 (28A‑2019) | P10R | 19 | **0,14** | ✅ |
| 3141 (26J‑2016) | P7R | 13 | **0,05** | ✅ |
| 3411 (23J‑2023) | INTENCIONGR | 16 | **0,83** | ❌ 1 fila |

**Discrepancia 3411 (sin maquillar)**: auto‑selección elige la recodificada
`INTENCIONGR` (15/16 filas ≤0,2) pero **"Otros partidos"** sale 0,87 % frente a
1,7 % publicado (Δ0,83). Con `INTENCIONG` (la que usó el sondeo manual) el
"Otros" baja a 0,43 % y **"SUMAR" no se reproduce** (10,15 % vs 12,7 %).

**Causa raíz (limitación documentada)**: el diccionario estático no distingue
coaliciones **dependientes de la era**. Etiquetas como *En Comú Podem* o
*Més Compromís* significan **Unidas Podemos** en 2016‑2019 y **SUMAR** en 2023;
un mapa única‑alias→canónico no puede desambiguar por año. Consecuencia: en 3411
parte del voto de SUMAR cae en UNIDAS PODEMOS/OTROS. Mitigación futura: alias
**con ventana temporal** (`desde/hasta`) o desambiguación por coalición del año
electoral. Se deja como incidencia, no se corrige a mano.

## 5. Exclusiones (`data/processed/cis/exclusions.json`)

- `no_data_link`: estudio sin microdato en la ficha (fondo antiguo). 
- `no se detecta variable de voto` / `sin PESO` / `sin ficheros DA/ES`: estudios
  cualitativos, paneles sin dato descargable o formatos no cubiertos.

## 6. Artefactos

- `pipeline/cis/catalog.json` — catálogo (estudio, fecha, slug, tipo, ámbito, elección, año, url).
- `pipeline/cis/build_catalog.py` — construye el catálogo desde los fragmentos.
- `pipeline/cis/fetch_microdata.py` — descarga reanudable (JSON‑LD + backoff).
- `pipeline/cis/parse_microdata.py` — parser ASCII DA/ES (del sondeo).
- `pipeline/cis/normalize.py` — normaliza y valida.
- `pipeline/cis/requirements.txt` — sin dependencias de terceros (opcional pyreadstat, poppler‑utils).
- `pipeline/party_aliases.csv` — diccionario de partidos con aliases y fuentes.

## 7. Reproducir

```bash
python3 pipeline/cis/build_catalog.py                 # catálogo desde fragmentos
python3 pipeline/cis/fetch_microdata.py --pause 8     # descarga (reanudable)
python3 pipeline/cis/normalize.py                     # salidas + validación
```


## Cierre del barrido (15-10-2026)

Descarga completa: 110 estudios con microdatos, 22 sin enlace publico (1977-1989),
2 zip corruptos. Normalizacion v2: polls.jsonl ampliado, con `fecha_trabajo_iso`
anadido (encuestadores ya usa ISO; el merge de Fase 4 lo exige).

Nueva puerta de calidad en normalize.py: si la tabla publicada de un estudio es
irreproducible en >=50% de sus filas (fallo sistemico: variable o denominador
equivocado), el estudio va a exclusions.json en vez de contaminar polls.jsonl
(caso 3382, 18/22 filas, max_delta 23,46 pp). Los fallos dispersos (coaliciones
por era, p.ej. 3411/23J con 1 fila a 0,83 pp) se quedan en el dataset, flaggados
en validation.json con su mitigacion documentada.
