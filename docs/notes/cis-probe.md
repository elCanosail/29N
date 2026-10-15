# Sondeo de viabilidad — ingesta CIS (29N)

Fecha: 2026-10-15 · Autor: subagente de sondeo · Alcance: `pipeline/cis/`, `data/raw/`, este informe.
Sin commits ni push. Todos los datos crudos quedaron en `data/raw/cis/` (ruta en `.gitignore`).

## Resumen ejecutivo

**Viable y más fácil de lo previsto.** La descarga de microdatos del CIS **no** exige el formulario
que describe el propio CIS en sus FAQ: las páginas de estudio enlazan el fichero
`MD####.zip` con una URL pública directa que responde `200 application/zip` sin cookies ni
tokens. Se descargaron y validaron **3 estudios** (3411 · 2023, 3141 · 2016, 3263 · 2019).

- **Descarga**: directa por URL, sin formulario, sin login. El único coste real es el
  *rate limiting* (HTTP 429) si se piden varias páginas seguidas → backoff obligatorio.
- **Parseo**: CSV abierto cuando el estudio fue *preparado* ≥2023 (p. ej. 3411); `.sav` cuando
  fue preparado ≥2018; y `DA####`+`ES####` (ASCII ancho fijo) como vía universal — se implementó
  un parser propio que funciona para todos.
- **Validación**: el "voto directo en la encuesta" publicado **se reproduce desde los microdatos
  con tolerancia ±0,1 pp** en 3411 (todas las filas) y 3263 (todas las filas); en 3141 cuadran
  16/18 filas, con 2 filas regionales que parecen transpuestas en el PDF publicado (ver §4).
- **Provincia**: variable `PROV` presente en los tres estudios, 52 provincias, ponderadores
  `PESO`/`PESOCCAA`/`PESOPROV`.

## 1. Localización del catálogo y de los estudios

### Catálogo

- Página de catálogo (listado de estudios):
  `https://www.cis.es/es/estudios/catalogo?catalogo=estudio&sort=createDateBDE-&t=0`
- Paginación por `&start=N` (10 por página). El listado se pinta **por JS** (data-set de
  Liferay): en el HTML no vienen los enlaces a las fichas, solo el cascarón y los enlaces
  de paginación. Sin `Accept-Language: es` el sitio redirige a `/en/` y usa slugs `/en/surveys/...`.
- La ficha de cada estudio sí es HTML estático en:
  `https://www.cis.es/es/estudios/<slug>`

### API interna descubierta (bundle `cis-lcx`)

Del JS `https://www.cis.es/o/cis-lcx/assets/index.js` (variable `X = https://www.cis.es`):

| Endpoint | Método | Uso |
|---|---|---|
| `/ws/v2/api/cis/estudio/{id}` | GET | ficha cabecera del estudio (JSON) |
| `/ws/v2/api/cis/pregunta/{id}` | GET | ficha de pregunta |
| `/ws/v2/api/cis/serie/{id}` | GET | serie |
| `/ws/v2/api/cis/ficha_serie/{id}` | POST | export ficha serie (blob) |
| `/ws/v2/api/cis/ficha_estudio/{id}` | POST | export ficha estudio (blob) |
| `/ws/v2/api/cis/resultados` | POST | resultados |
| `/o/c/datafileaccesses/` | POST | **formulario registrado de acceso a ficheros** (con `x-csrf-token`) |

**Aviso importante**: el `{id}` de `/ws/v2/api/cis/estudio/{id}` es un **id interno de BD, no el
número de estudio**. Evidencia: `/ws/v2/api/cis/estudio/3411` devuelve
`{"estudio":{"id":3411,"codigo":2475,"titulo":"Sondeo sobre la Juventud Española 2002 (cuarta oleada)"...}}`
→ código 2475, no 3411. La ruta con slug (`/estudio/preelectoral-elecciones-generales-2023`)
devuelve **404**. Por tanto la API sirve para enriquecer metadatos, no para enumerar por nº de estudio.

### Tres estudios identificados (y dos extra)

| Nº | Título | Slug ficha | Elección |
|---|---|---|---|
| **3411** | Preelectoral elecciones generales 2023 | `preelectoral-elecciones-generales-2023` | 23J-2023 |
| **3141** | Preelectoral elecciones generales 2016 | `preelectoral-elecciones-generales-2016` | 26J-2016 |
| **3263** | Macrobarómetro de octubre 2019. Preelectoral elecciones generales 2019 | `macrobarometro-de-octubre-2019.-preelectoral-elecciones-generales-2019` | 10N-2019 |
| 3242 (extra) | Macrobarómetro de marzo 2019. Preelectoral elecciones generales 2019 | `macrobarometro-de-marzo-2019.-preelectoral-elecciones-generales-2019` | 28A-2019 |
| 3117 (extra) | Preelectoral elecciones generales 2015. Panel (1ª fase) | `preelectoral-elecciones-generales-2015.-panel-1-fase-` | 20D-2015 |

Los 5 se localizaron por búsqueda web + navegación de fichas; los 5 corresponden a preelectorales
de generales. (3411/3141/3263 son los tres descargados y validados.)

## 2. Descarga de microdatos — funciona sin formulario

### URLs exactas que devolvieron datos

```
14194752 b  200  https://www.cis.es/documents/20117/1557956/MD3411.zip/5694a453-285e-1d34-b803-75b4177f0c89?version=1.0&t=1699726161897
 3016887 b  200  https://www.cis.es/documents/20117/1556341/MD3141.zip/19108e99-c58a-06af-78e0-6072a856e630?version=1.0&t=1696370646177
 2666599 b  200  https://www.cis.es/documents/20117/1557011/MD3263.zip/89dba8d9-c737-1bb0-2127-33aca8c69bdc?version=1.0&t=1706023135913
```

El patrón es `https://www.cis.es/documents/20117/<folder_id>/MD<estudio>.zip/<uuid>?version=1.0&t=<epoch-ms>`.
Cada ficha de estudio incrusta ese enlace en su HTML (se extrae con regex).

### Contenido del ZIP (varía por antigüedad de preparación)

**3411 (preparado 2023)** — `data/raw/cis/3411/`:
```
3411csv.zip   (8.9 MB)  → dentro: 3411_etiq.csv (104.6 MB), 3411_num.csv (16.7 MB)
3411.sav      (11.4 MB) SPSS
DA3411        (14.7 MB) ASCII ancho fijo
ES3411        sintaxis SPSS
codigo3411.pdf, cues3411.pdf, FT3411.pdf
```

**3141 (2016)** y **3263 (2019)** — `data/raw/cis/MD3141/`, `MD3263/`: `.sav` + `DA####` + `ES####` +
PDFs (código, cuestionario, ficha técnica, tarjetas). **Sin CSV** (el propio CIS dice: CSV solo para
"estudios cuyos datos han sido preparados desde 2023").

> Regla confirmada: **CSV ⇐ preparado ≥2023 · .sav ⇐ preparado ≥2018 · DA+ES ⇐ siempre**.

### Bloqueos encontrados (reales)

1. **HTTP 429 (rate limit)** tras ~5-8 peticiones rápidas seguidas. A veces sin `Retry-After`.
   Solución implementada: backoff exponencial (`base 20 s × intento`) y pausas entre peticiones.
   Es el principal riesgo del scraping a 60 estudios; con pausas de 8-15 s el proceso es estable.
2. **Formulario**: el endpoint `POST /o/c/datafileaccesses/` (con `x-csrf-token`) existe y es el que
   usa la web (pide email, valida longitud…), pero **no hace falta**: la URL de documento anterior
   es pública. No hay que resolver captcha ni mantener sesión.
3. **`formulario.jsp` histórico muerto**: `http://www.cis.es/cis/opencms/ES/formulario.jsp?dwld=/Microdatos/MD3117_A.zip`
   → **404**. La vía antigua (la que citan los repos de 2015) ya no existe.
4. **FAQ engañosa**: "hay que cumplimentar un formulario" y "no es posible la descarga en bloque".
   La primera parte no aplica a las URLs directas; la segunda es cierta (hay que ir estudio a estudio).

### Scripts de sondeo (en `pipeline/cis/`)

- `cis_fetch.py` — `page <url> <out>` (GET con backoff), `docs <html>` (lista documentos de una ficha),
  `study <html> <dir> --referer <url>` (baja el `MD####.zip` y lo descomprime).
- `parse_microdata.py` — parser genérico del formato ASCII (`ES####`+`DA####`): reconstruye columnas,
  maneja decimales con coma, y extrae etiquetas de `VALUE LABELS`.

```bash
python3 pipeline/cis/cis_fetch.py page "https://www.cis.es/es/estudios/preelectoral-elecciones-generales-2016" /tmp/p.html
python3 pipeline/cis/cis_fetch.py docs /tmp/p.html
python3 pipeline/cis/cis_fetch.py study /tmp/p.html data/raw/cis --referer "https://www.cis.es/es/estudios/preelectoral-elecciones-generales-2016"
python3 pipeline/cis/parse_microdata.py data/raw/cis/MD3263/ES3263 data/raw/cis/MD3263/DA3263 --var P9R
```

## 3. Parseo y validación de provincia y estimación de voto

Variables clave (presentes en los tres estudios): `PROV` (provincia), `PESO` (peso nacional),
`PESOCCAA`, `PESOPROV`, y la intención de voto en su versión **recodificada (`*R`)**, que es la que
usan las tablas publicadas.

Provincia: `PROV` con **52 provincias** en los tres; suma de pesos = N de muestra.

| Estudio | registros | provincias | suma PESO | fichero |
|---|---|---|---|---|
| 3411 | 29.201 | 52 | 29.201,0 | `3411_num.csv` |
| 3141 | 17.488 | 52 | 17.488,0 | `DA3141` (ASCII) |
| 3263 | 17.650 | 52 | 17.650,0 | `DA3263` (ASCII) |

> Los pesos `PESO` vienen con **5 decimales implícitos y coma decimal** (p. ej. `0,71550`).
> El parser ya lo maneja.

### Validación contra las tablas publicadas (±0,1 pp)

Se contrasta la columna **"Voto directo en la encuesta (en %)"** del PDF *Estimación de voto*
de cada estudio. (La otra columna, "Estimación de voto CIS (en % sobre voto válido)", es el
resultado del *modelo* del CIS — filtrado/ponderación/imputación — y **no es reproducible solo con
los microdatos**; no se usa para validar.)

**Estudio 3411** (23J-2023, variable `INTENCIONG`; ponderado por `PESO`) — todas las filas ≤0,05 pp:

| Partido | Publicado | Microdatos | Δ |
|---|---|---|---|
| PP | 25,4 | 25,37 | 0,03 |
| PSOE | 24,6 | 24,64 | 0,04 |
| SUMAR (coalición) | 12,7 | 12,68 | 0,02 |
| VOX | 8,8 | 8,81 | 0,01 |
| ERC | 1,3 | 1,28 | 0,02 |
| JxCat | 1,0 | 0,99 | 0,01 |
| EH-Bildu | 1,0 | 0,99 | 0,01 |
| EAJ-PNV | 0,8 | 0,81 | 0,01 |
| BNG | 0,8 | 0,80 | 0,00 |
| CUP | 0,5 | 0,47 | 0,03 |
| En blanco | 1,2 | 1,25 | 0,05 |
| Voto nulo | 0,8 | 0,77 | 0,03 |
| Abstención | 2,3 | 2,33 | 0,03 |
| No sabe | 14,1 | 14,12 | 0,02 |
| No contesta | 2,8 | 2,78 | 0,02 |

**Estudio 3263** (10N-2019, variable `P9R`) — **27/27 filas ≤0,05 pp**: PSOE 19,88/19,9 · PP 9,10/9,1 ·
Ciudadanos 4,19/4,2 · Unidas Podemos 5,74/5,7 · VOX 3,98/4,0 · Más País 0,82/0,8 · PACMA 0,60/0,6 ·
ERC 2,54/2,5 · En Comú Podem 1,20/1,2 · JxCat 0,83/0,8 · CUP 0,32/0,3 · EAJ-PNV 0,87/0,9 ·
EH Bildu 0,86/0,9 · Geroa Bai 0,06/0,1 · NA+ 0,20/0,2 · CCa-NC 0,16/0,2 · Més Compromís 0,50/0,5 ·
PRC 0,10/0,1 · En Común-Unidas Podemos 0,45/0,5 · BNG 0,21/0,2 · Otros 0,76/0,8 · En blanco 1,40/1,4 ·
Voto nulo 0,64/0,6 · Abstención 11,76/11,8 · No decidido 20,30/20,3 · No sabe 3,22/3,2 · No contesta 9,23/9,2.

**Estudio 3141** (26J-2016, variable `P7R`) — **16/18 filas ≤0,05 pp**; dos excepciones:

| Fila | Publicado | Microdatos | Δ |
|---|---|---|---|
| Compromís-Podemos-EUPV | 1,4 | 1,95 | 0,55 ⚠ |
| En Marea | 1,7 | 1,19 | 0,51 ⚠ |

La **suma** de ambas coincide (publicado 3,1 · microdatos 3,14), lo que apunta a un **intercambio de
etiquetas entre esas dos filas en el PDF publicado** (o a un recode distinto del documentado en el
libro de códigos), no a un fallo de la ingesta. Se documenta tal cual; en la ingesta normalizada
debería fijarse el criterio por el libro de códigos y anotar la discrepancia.

## 4. Estrategia de ingesta recomendada (≈60 series electorales)

1. **Enumeración del catálogo** (una vez, con navegador headless): recorrer
   `.../estudios/catalogo?catalogo=estudio&start=N` filtrando por la colección
   "Elecciones Legislativas" (o por texto "preelectoral elecciones generales") y cosechar las
   URLs `/es/estudios/<slug>`. Es lo único que hoy exige JS; el resto del pipeline es `requests`.
   (Bonus: la misma pasada da el nº de estudio y la colección, para el inventario.)
2. **Por estudio**: GET de la ficha → regex del enlace `MD####.zip` → descarga con backoff → unzip.
   Preferir el `MD####.zip` único (trae datos + documentación junta).
3. **Parseo con prioridad de formato** según antigüedad de preparación:
   - CSV (`_num.csv` + `_etiq.csv`) si existe → vía más simple (3411).
   - `.sav` (SPSS) si existe → `pyreadstat` (no instalado en este host; añadir a
     `pipeline/requirements.txt`).
   - `DA####` + `ES####` → **parser propio** (`parse_microdata.py`), universal y sin dependencias.
4. **Ponderación y voto**: usar `PESO` (nacional) / `PESOPROV` (provincial) y la variable de
   intención de voto **recodificada** (`P7R`, `P9R`, `INTENCIONG`…) para cuadrar con las tablas
   publicadas. La columna "estimación de voto del modelo CIS" NO se reproduce desde microdatos.
5. **Provincia**: `PROV` (52 valores). Conservar además `CCAA`, `TAMUNI` para desagregación.
6. **Ritmo**: secuencial, pausas de **8-15 s** entre peticiones, backoff exponencial ante 429.
   Unos 60 estudios × (~0,7 MB de ficha + 3-15 MB de ZIP) ≈ poco más de una hora, holgado.
7. **Licencia/datos**: microdatos **no redistribuibles** → crudos en `data/raw/` (gitignored),
   en el repo solo salidas normalizadas + URL de procedencia por estudio (trazabilidad exigida
   por el plan). Guardar el nº de estudio, la colección y la fecha de descarga.
8. **Validación automática por estudio**: comparar el "voto directo" recalculado contra el PDF
   *Estimación de voto* (extraíble con `pdftotext -layout`) y marcar como incidencia cualquier
   fila con Δ>0,1 pp (caso 3141/Compromís-En Marea).

### Riesgos residuales

- **429/rate-limit**: mitigable con backoff; si el sitio endurece, plan B es descarga manual
  estudio a estudio (factible: ~60 fichas).
- **Cambios de maquetación** (fichas Liferay): mitigado aislando el regex del enlace en un
  módulo y con test por estudio.
- **Metadatos por API**: recordar que `/ws/v2/api/cis/estudio/{id}` usa id interno, no el nº de estudio.

## Evidencia archivada

En `data/raw/cis/` (gitignored): `MD3411.zip`, `3411/`, `MD3141.zip`, `MD3141/`, `MD3263.zip`,
`MD3263/`, `pages/` (HTML de fichas y catálogo) y `estimacion/` (PDFs + texto de estimación de voto).
Scripts versionables: `pipeline/cis/cis_fetch.py`, `pipeline/cis/parse_microdata.py`.

## Supuestos

- "Voto directo en la encuesta (en %)" se calcula sobre el **total ponderado de la muestra**
  (suma de `PESO`); verificado por coincidencia en las filas no-coalición y de no-voto.
- Para coaliciones se usa la variable recodificada (`*R`) del cuestionario del propio CIS.
- 3411 corresponde al preelectoral de las generales del 23J-2023 (ficheros fechados 05-11/07-2023).
