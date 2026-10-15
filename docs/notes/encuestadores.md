# Encuestadores privados (29N, Fase 3) — curación inicial 2023-2026

Fecha: 2026-10-15 · Alcance: `pipeline/encuestadores/`, `data/processed/encuestadores/`.
Sin commits ni push. No se tocaron `pipeline/party_aliases.csv`, `pipeline/cis/`,
`data/processed/cis/`, `data/raw/cis/`, `pipeline/interior/`, `web/` ni `DESIGN.md`.

**Regla de oro aplicada:** toda encuesta entra con URL de su ficha técnica publicada
(prensa o web del encuestador) y un extracto verbatim. Nada se ha rellenado de memoria;
si un dato no aparece literal en la fuente, se omite. Lo que no pasa validación va a
`exclusions.json`.

## Resumen

- **32 encuestas**, **132 filas encuesta×partido**, **9 encuestadores**, **8 exclusiones**.
- **15 encuestas son de las generales del 23J (2023)**; el resto, contexto post-23J y
  la próxima cita de 2026.
- Origen de la fuente: **15 prensa**, **5 web del encuestador**, **12 agregador**
  (Electográfica, pollingforecast, politpro, sumomento). El tipo va en el campo
  `fuente_tipo` de cada fila para que la web pueda degradar la confianza visualmente.
- Esquema alineado con el CIS (`docs/notes/cis-ingest.md`): una línea por encuesta×partido
  con `fuente, estudio_id, fecha_trabajo, fecha_publicacion, n, metodologia, ambito,
  eleccion, partido_canonico, porcentaje` + `fuente_url` y `fuente_tipo` (trazabilidad,
  criterio de aceptación nº1 del plan).

## Cobertura por encuestador

| Encuestador | Encuestas | De 23J (2023) | Post-23J / 2026 | Fuentes usadas |
|---|---:|---:|---:|---|
| GAD3 | 6 | 3 | 3 | ABC (prensa), gad3.com, Electográfica |
| 40dB | 5 | 2 | 3 | El País, Electográfica, PDF El País |
| NC Report | 5 | 2 | 3 | La Razón, Electográfica, politpro |
| Imop Insights | 4 | 3 | 1 | El Confidencial, imop.es |
| Sigma Dos | 4 | 2 | 2 | El Mundo, sigmados.com, Electográfica, pollingforecast |
| Sociometrica (SocioMétrica) | 4 | 2 | 2 | El Español, Electográfica, sumomento |
| Simple Lógica | 2 | 1 | 1 | elDiario.es |
| Demoscopia y Servicios | 1 | 0 | 1 | Libertad Digital |
| CEO (Centre d'Estudis d'Opinió) | 1 | 0 | 1 | El Plural (ámbito **Cataluña**) |

Por elección declarada en el fragmento: 15 «generales 2023», 11 «generales 2026», 6
contexto post-23J/próximas.

## Scoring 23J (error absoluto medio)

Resultado real de referencia (23J, % sobre votos válidos, agregado de Interior):
**PP 33,06 · PSOE 31,68 · VOX 12,38 · SUMAR 12,33**. Calculado por
`pipeline/encuestadores/score.py` sobre las 15 encuestas de 2023:

```
Encuestador             n  obs    MAE       PP   PSOE    VOX  SUMAR
-------------------------------------------------------------------
Simple Lógica           1    4   1.73     0.86   3.08   1.52   1.47
Sigma Dos               2    8   1.82     1.74   3.23   1.18   1.12
Sociometrica            2    8   2.03     0.70   4.83   1.97   0.62
NC Report               2    8   2.10     3.54   3.63   0.65   0.58
GAD3                    3   12   2.14     3.77   3.45   0.39   0.93
40dB                    2    6   2.28     1.16   3.43   1.22   3.27
Imop Insights           3    7   2.32     0.58   7.18   2.52   2.40
```

Lectura honesta: la muestra es diminuta (1-3 encuestas por encuestador, 4-12
observaciones) y **no es todavía un ranking fiable**; sirve para validar el pipeline
de scoring, no para concluir qué encuestador es mejor. El error tiende a concentrarse
en PSOE (los sondeos infravaloraron sistemáticamente al PSOE antes del 23J) y el
"peor" MAE de Imop viene de su infrarrepresentación del PSOE (24,5 %). Se publicará con
la advertencia de tamaño muestral.

## Huecos detectados

Encuestadores objetivo de la Fase 3 y qué ha pasado con cada uno:

- **GAD3, 40dB, Sigma Dos, NC Report:** cubiertos, pero solo con una **muestra** de sus
  series. Los *trackings* diarios de campaña (GAD3 para ABC/Vocento, Sigma Dos para El
  Mundo, NC Report y 40dB para La Razón/El País) tienen decenas de entregas; aquí entran
  algunas piezas representativas, no la serie completa.
- **Simple Lógica:** cubierta en 2023 y 2024; **sin encuestas de generales publicadas
  desde 09/2024** (elDiario.es pasa a Ateneo del Dato en 2026). Hueco real, no de búsqueda.
- **Demoscopia y Servicios (Más1):** **sin sondeos de generales verificables en 2023 ni
  2026**; solo el macroencuesta de 09/2025 (Libertad Digital). La marca «Más1 / Más1
  investigación social demoscópica» **no se ha podido verificar en fuentes primarias**
  como denominación de la casa. Hueco.
- **Hand Research:** **no existe** encuestador con esa denominación publicando intención
  de voto para generales (las búsquedas devuelven resultados no relacionados). Excluido.
- **Cercle d'Estudis:** no hay encuestadora con esa denominación exacta; el homólogo real
  es el **Centre d'Estudis d'Opinió (CEO)** de la Generalitat, de **ámbito Cataluña**, no
  estatal. Se documenta su 2ª ola de 2026 con ámbito «Cataluña» (no suma a la serie estatal).
- **Imop Insights:** 3 entregas de 2023 con nota publicada (una sin desglose completo:
  solo PP y SUMAR en 29/05; solo PP en 11/07). El resto del *tracking* diario de El
  Confidencial no se pudo cotejar con ficha propia → excluido.

Huecos de cobertura temporal (fuera de los encuestadores objetivo):

- **No hay serie 2019 ni anteriores** de encuestadores privados. El scoring contra 23J es
  el único posible hoy; para una serie robusta harían falta 10N-2019 y 28A-2019.
- **12 de 32 encuestas** llegan vía agregador (Electográfica, pollingforecast, politpro,
  sumomento) en lugar de la nota del medio o del encuestador. El dato y la ficha
  (periodo, método, muestra) son verificables en el agregador, pero falta enlazar la
  fuente primaria.
- **Datos parciales:** varias encuestas no publican el % de todos los partidos (solo
  escaños); se ha optado por omitir en vez de estimar.
- **`40dB 2026-10-08`** es un «barómetro flash» de **intención directa de voto** (sin
  cocina demoscópica): no es comparable con estimación de voto y así queda etiquetado.

## Calidad de fuentes

- Las fichas de **prensa y de los propios encuestadores** traen universo, cuotas, técnica,
  tamaño y fechas de campo: son las de mejor calidad y las preferidas (20/32).
- Las de **agregador** reproducen la ficha técnica (periodo, método, muestra, margen)
  pero conviene sustituirlas por la fuente primaria cuando exista.
- Dos entradas tienen campos incompletos por ausencia en origen: `fecha_publicacion` nulo
  (Sigma Dos 01-10-2026, NC Report 03-09-2026) y `fecha_trabajo` nulo (Sigma Dos 12-10-2026).

## Recomendación para la serie completa

1. **Completar los *trackings* 23J** de GAD3, Sigma Dos, NC Report, 40dB, Simple Lógica e
   Imop entrega a entrega (con su ficha), y **añadir 2019** (10N y 28A) para un scoring
   con ≥5 encuestas por encuestador.
2. **Sustituir URLs de agregador por la fuente primaria** (nota del medio o PDF del
   encuestador) para las 12 filas afectadas; el agregador queda como contrastación.
3. **Investigar los huecos reales**: por qué Demoscopia no publica generales y si Simple
   Lógica cesó; documentar «Hand Research» y «Cercle d'Estudis» como nombres erróneos del
   inventario de objetivos (equivalente real: CEO).
4. **Ampliar la normalización de partidos** con ventana temporal para las coaliciones
   dependientes de la era (mismo problema que el CIS documenta en su §4): «En Comú Podem»
   o «Més Compromís» son UNIDAS PODEMOS en 2016-2019 y SUMAR en 2023. Hoy el diccionario
   de encuestadores no distingue por año.
5. **Publicar el scoring con su n** y no como ranking; añadir intervalos/bootstrap cuando
   haya muestra suficiente.

## Artefactos y reproducción

- `data/processed/encuestadores/polls.jsonl` — 132 filas (encuesta×partido).
- `data/processed/encuestadores/sources.json` — 32 entradas con URL + extracto verbatim.
- `data/processed/encuestadores/exclusions.json` — 8 entradas con motivo.
- `data/processed/encuestadores/scoring.json` — MAE por encuestador contra 23J.
- `data/processed/encuestadores/_staging/*.json` — fragmentos crudos por encuestador.
- `pipeline/encuestadores/build_dataset.py` — normaliza fragmentos → salidas.
- `pipeline/encuestadores/score.py` — scoring contra el resultado real de Interior.
- `pipeline/encuestadores/aliases.json` — aliases de encuestadores y partidos.
- `pipeline/encuestadores/requirements.txt` — sin dependencias de terceros.

```bash
python3 pipeline/encuestadores/build_dataset.py   # fragmentos → polls/sources/exclusions
python3 pipeline/encuestadores/score.py            # MAE contra 23J
```

Cada fase cierra con prueba documentada; la prueba de esta fase son los conteos del
`build_dataset.py` (32 / 132 / 8) y la tabla de `score.py` sobre el resultado oficial de
`data/processed/interior/elections.json`.
