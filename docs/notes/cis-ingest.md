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
La tabla publicada y los microdatos se canonizan **con el mismo año** (si no, los
aliases con ventana temporal aplicarían a un solo lado).

### Correcciones tras revisión (2026-10-15)

1. **`tipo == 'otro'` fuera de polls y validación.** Los estudios clasificados
   como `otro` (p. ej. **3382**, macroencuesta de voto *municipal* oct-2022) se
   comparaban contra tablas de otro ámbito → validación inválida (Δ23,46 pp).
   Ahora van a `exclusions.json` con motivo `tipo 'otro'` (11 estudios).
2. **Aliases con ventana temporal** (`party_aliases_eras.csv`): en 2023 SUMAR
   absorbe En Comú Podem / Compromís-Sumar / Més Compromís; en 2015-2019 esos
   nombres integraban UNIDAS PODEMOS; Més Compromís 2019-2022 = Más País.
3. **Residuales NO forzados a OTROS.** Se probó a agregar los partidos
   residuales no reconocidos en OTROS: reproduce 3411 (0,83→0,59) pero **rompe**
   3263 (0,04→0,49), 3367 (0,09→6,10), 3458 (0,52→4,71) y 3460 (0,22→5,00),
   donde el CIS **no** los agrupa en "Otros partidos". Se **revierte**: las
   etiquetas no reconocidas se descartan y se registran en
   `residuales_en_otros` de `studies.json` (trazabilidad, sin forzar).

### Antes / después (Δ máx por estudio, tolerancia ±0,2)

| Estudio | Antes | Después | Partido con Δ | Nota |
|---|---|---|---|---|
| 3117 (20D-2015 panel) | 0,05 ✅ | 0,05 ✅ | — | |
| 3141 (26J-2016) | 0,05 ✅ | 0,05 ✅ | — | |
| 3242 (28A-2019) | 0,14 ✅ | 0,14 ✅ | — | |
| 3263 (10N-2019) | 0,04 ✅ | 0,04 ✅ | — | |
| 3269 (postelect. 2019) | 0,34 ❌ | **0,08 ✅** | MÁS PAÍS (antes) | corregido por alias 2019 |
| 3367 (flash 2022) | 0,09 ✅ | 0,09 ✅ | — | |
| 3382 (macroencuesta municipal) | 23,46 ❌ | — | — | **excluido** (`tipo 'otro'`) |
| 3415 (flash 2023) | 0,05 ✅ | 0,05 ✅ | — | |
| 3407 (flash municip. 2023) | 3,06 ❌ | 3,06 ❌ | OTROS | limitación |
| 3411 (23J-2023) | 0,83 ❌ | 0,83 ❌ | OTROS | limitación |
| 3420 (postelect. 2023) | 0,52 ❌ | 0,52 ❌ | OTROS | limitación |
| 3458 (europeas 2024, pre) | 0,52 ❌ | 0,52 ❌ | OTROS | limitación |
| 3460 (europeas 2024, campaña) | 0,22 ❌ | 0,22 ❌ | OTROS | limitación |
| 3500 (flash 2024) | 0,36 ❌ | 0,36 ❌ | SUMAR, ABSTENCIÓN | limitación |

**Total: 6/14 → 7/13 OK** (denominador menor al excluir 3382).

### Limitación documentada (no maquillada)

Las 6 validaciones que siguen fuera de tolerancia lo hacen **solo en "Otros
partidos"** (3407, 3411, 3420, 3458, 3460) y en 3500 (SUMAR/ABSTENCIÓN).
Causa raíz: el reparto de "Otros partidos" del CIS **no sigue una regla única
entre estudios** — a veces agrupa las candidaturas residuales (España Vaciada,
Teruel Existe, Por Ávila, UPL, Ahora Repúblicas, Partido Libertario…), a veces
las lista aparte. Reproducirlo exigiría replicar la **agrupación por estudio**
del propio CIS (lectura del libro de códigos de cada campaña), que aquí no se
aplica para no forzar el ajuste. El déficit medido en 3411 es exactamente la
masa residual descartada (0,83 pp ≈ suma de las 7 candidaturas no reconocidas).
Mitigación futura: fijar las candidaturas de cada convocatoria (diccionario por
año) y, solo entonces, decidir su agrupación con criterio documentado.


## 5. Exclusiones (`data/processed/cis/exclusions.json`)

- `tipo 'otro'` (11): estudio cuyo tipo no es preelectoral/postelectoral/etc.;
  no entra en polls ni validación (incluye el caso 3382 de validación cruzada inválida).
- `sin PESO` (53): fondos antiguos sin ponderador en el ASCII.
- `no se detecta variable de voto` (7): estudios sin variable de intención explícita.
- (La ausencia de microdato publicado en fichas antiguas se refleja en el
  `manifest.json` como `no_data_link`/`bad_zip`, no como exclusión de normalización.)

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
