# Fase 4-c — Microdatos CIS a nivel individual (29N)

Fecha: 2026-10-15 · Alcance de escritura: `pipeline/microdatos/`,
`data/processed/microdatos/`, este documento. Todo lo demás es **solo lectura**
(`data/raw/cis/` incluido). No se toca `data/processed/cis/` ni `pipeline/cis/`.

Objetivo: extraer el valor **individual** de los microdatos CIS descargados
(~110 estudios) a un dataset normalizado, validarlo contra los agregados ya
validados de Fase 1 y decidir la viabilidad del MRP.

## Resumen ejecutivo (cifras reales)

| Métrica | Valor |
|---|---|
| Estudios descargados con carpeta | 112 |
| Con microdato ASCII (DA/ES) | 106 |
| **Estudios extraídos a nivel individual** | **55** |
| **Individuos (registros)** | **532.498** |
| Estudios excluidos | 57 (51 sin ponderador, 6 sin ASCII) |
| **Validación vs `polls.jsonl` (±0,1 pp)** | **35/35 OK**, Δ máx **0,0322 pp** |
| Estudios de la validación exigida | 6/6 OK (1135, 1181, 3117, 3242, 3263, 3415) |
| Comprobación ASCII vs `.sav` (3141) | 17.488 = 17.488 filas, mismas categorías |

Artefactos: `data/processed/microdatos/individual.parquet` (zstd),
`cobertura.json`, `validation_micro.json`, `extraction.json`.
Código: `pipeline/microdatos/{extract_individual.py, validate_vs_polls.py, check_sav.py, requirements.txt}`.

## 1. Inventario de variables y cobertura por era

La detección es **por etiquetas** (`VARIABLE LABELS` del ES), no por nombre, para
resistir el cambio de nombre entre eras (P22→EDAD, P17→ESCIDEOL, P7R→INTENCIONGR…).
Trampa del `latin-1`: `ideológica` lleva `ó` como byte único, así que la raíz
segura es `ideol` (no `ideolog`). El inventario completo está en
`data/processed/microdatos/cobertura.json` (estudio × variable detectada).

Cobertura por decade (n / presente):

| Era | n | prov | edad | sexo | estudios | sit.lab | tamuni | ideol. | interés | recuerdo | intención | relig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1970s | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 0 | 2 | 3 | 3 |
| 1980s | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 16 | 12 | 18 | 18 | 14 |
| 1990s | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 0 | 4 | 4 | 0 |
| 2000s | 6 | 6 | 3 | 3 | 6 | 1 | 5 | 0 | 0 | 2 | 0 | 0 |
| 2010s | 10 | 10 | 9 | 9 | 10 | 8 | 10 | 8 | 7 | 10 | 8 | 6 |
| 2020s | 14 | 14 | 14 | 14 | 14 | 12 | 14 | 13 | 0 | 13 | 14 | 10 |
| **Total** | **55** | **55** | **51** | **51** | **55** | **46** | **53** | **44** | **19** | **49** | **47** | **33** |

Por elección: 39 generales, 8 europeas, 7 `otro`, 1 municipal. Para MRP deben
filtrarse los `tipo_estudio ∈ {otro}`.

### Huecos detectados (no maquillados)

- **Sin densidad de etiquetas** (0 extraídos): `1324`, `1326` (1982, ficheros
  derivados sin ideología) y `2555/2559/2750/2915` (2004-2011) cuyo **ES no trae
  bloque `VARIABLE LABELS`** y no tienen `.sav` ni `.csv` alternativos → solo se
  recupera `PROV`/`ESTUDIOS` por nombre. Sin demografía.
- `2757`, `7708` (2008): ES sin etiquetas pero con nombres explícitos
  `sexo`/`edad` → recuperados por nombre; el resto de variables no.
- **Sin ideología 1-10**: 1324, 1326, 2555, 2559, 2750, 2757, 7708, 2807, 2915,
  2920, 3299.
- **Sin intención de voto**: 2555, 2559, 2750, 2757, 7708, 2807, 2915, 2920.
- **Interés por la política** solo en 19/55 (la pregunta es tardía y no está en
  los preelectorales antiguos; es un hueco real de origen, no de detección).
- **Reescalado**: las escalas 1-7 (p. ej. 1135 P9) se reescalan linealmente a
  1-10 (`1 + (v-1)·9/6`); las 1-10 se dejan tal cual. `ideologia_escala` guarda
  la escala de origen. Escalas con códigos sin etiqueta (1533, 2104, 2207,
  2210) se resuelven por la etiqueta `(1-10)` o, en su defecto, por el máximo
  observado.
- **Ambigüedad resuelta**: se descartan como ideología variables que solo
  contienen la palabra (3458 `PARTIDOSUE_2` «valores, ideología, etc.», 3269
  `A11` «Autodefinición…» = familias, no 1-10). Se exige escala izquierda–derecha
  o etiqueta de escala/autoubicación.

## 2. Extracción normalizada

`individual.parquet` — una fila por individuo × estudio. Columnas canónicas:

`estudio_id, fecha_trabajo, anio, eleccion, provincia (código INE 1-52), peso,
edad, sexo, estudios, ideologia_1a10, interes_politica, recuerdo_voto,
intencion_voto` + extras de auditoría (`tipo_estudio, ambito, peso_var,
ideologia_var, ideologia_escala, intencion_var, intencion_src, recuerdo_var,
intencion_voto_raw, recuerdo_voto_raw`).

Decisiones:
- **ASCII universal.** El fichero `DA####`+`ES####` existe en los 106 estudios
  (con/sin `.sav`/`.csv`) y es lo que ya consume el parser validado de Fase 1.
  Se evita reimplementar el parseo por formato. `.sav`/`.csv` se reservan para
  comprobación cruzada.
- **Ponderación.** `PESO` nacional preferente; si falta, variantes
  (`PESOCCAA, PESOPROV, PESOA, PESO2, PESO1`). 51 estudios no tienen ningún
  ponderador → excluidos (documentado en `extraction.json`; coincide con las 53
  «sin PESO» de Fase 1).
- **Voto canónico.** `recuerdo_voto`/`intencion_voto` pasan por
  `normalize.canonize` (diccionario + aliases por era) y, si no hay partido, por
  categorías de no-voto (`ABSTENCION/BLANCO/NULO/NS/NC/NO_DECIDIDO/OTRO`). La
  etiqueta cruda se conserva en las columnas `*_raw`.
- **Variable de intención.** Se reutiliza la ya validada por estudio
  (`studies.json`, 35 estudios) y, en el resto, la heurística `candidates`
  (20 estudios, marcados `intencion_src=heuristica`).
- **Entorno.** `/root/.venvs/29n-micro` (creado con `--system-site-packages`;
  pandas/numpy/pyarrow del sistema) + `pyreadstat 1.3.6` desde
  `pipeline/microdatos/requirements.txt`.

### Comprobación ASCII ↔ `.sav`

`/root/.venvs/29n-micro/bin/python pipeline/microdatos/check_sav.py 3141`:
`n_sav=17.488 = n_ascii=17.488`; categorías idénticas en `PROV` (52) y
`RECUERDO` (17). El ASCII reproduce el SPSS.

## 3. Validación (prueba de corrección)

`pipeline/microdatos/validate_vs_polls.py` reagrega el dataset individual por
partido canónico y lo compara con `data/processed/cis/polls.jsonl` (ya validado
contra las tablas publicadas del CIS).

- **35/35 estudios** dentro de ±0,1 pp.
- **Δ máx global = 0,0322 pp** (3513/2025, partido NS); siguiente 0,0187 (7789).
- Estudios exigidos (6): **1135, 1181, 3117, 3242, 3263, 3415 → todos OK**.

Que la extracción individual reproduzca los agregados ya validados confirma que
la lectura de registros, los pesos y la canonización por era son correctos.
(Las diferencias ≤0,03 pp en 3513/7789 provienen de redondeo de `voto_pct` a 3
decimales en `polls.jsonl` y de filas con peso 0 excluidas aquí.)

## 4. Censo INE — viabilidad de post-estratificación provincial (investigación)

Sin descarga masiva; solo se ha verificado qué series existen, desde cuándo,
formato y licencia.

| Fuente | Contenido | Cobertura | Geografía | Formato |
|---|---|---|---|---|
| **INEbase tabla 66600** | Población 15+ por **sexo × edad (año a año 15-90+) × nivel de estudios (detalle, 11 cat.)** | **2021-2024** | CCAA y **provincia** | HTML, PC-Axis, XLSX, CSV, **API JSON** |
| INEbase tabla 66789 | Población 15+ por sexo × nivel de estudios (agrupado, 5 cat.) | 2021-2024 | provincia, **municipio y sección censal** | ídem |
| INEbase tabla 67573 | Igual que 66600, ámbito CCAA, serie Censo de Población | 2021-2023 | CCAA | CSV `csv_bdsc/67573.csv`, API |
| Padrón continuo tabla 03002 | Población por provincia × edad **quinquenal** × sexo × nacionalidad | **1998-2022** | provincia | PC-Axis, CSV, API |
| Censo 2021 (INE) | Población por sexo, nacionalidad y nivel de estudios (agregado) | 2021 | CCAA y provincia | CSV/PC-Axis |

- **Licencia**: aviso legal INE (`https://www.ine.es/aviso_legal`) — reutilización
  permitida con atribución, sin coste. Publicadores: INE en datos.gob.es.
- **API**: INEbase JSON (Tempus3) y descarga directa CSV
  (`https://www.ine.es/jaxiT3/files/t/csv_bdsc/<tabla>.csv`); documentación
  OpenAPI/Swagger en `ine.es/OpenAPI`.

### Veredicto MRP

**Viable, con matices.**

1. La post-estratificación por **provincia × sexo × edad × estudios** está servida
   por la tabla **66600** para **2021-2024** (coherente con el horizonte 29N). No
   hace falta microdato censal: la propia tabla da el denominador por celda.
2. **Limitación de backtest**: el censo con esas tres dimensiones arranca en
   **2021**. Para validar el MRP contra 2015-2019 habría que usar el **Censo
   2011** (existe tabla análoga por provincia, distinta armonización de estudios)
   o aceptar que el backtest se hace con estructura demográfica actual
   reproyectada — a documentar como supuesto. El Padrón 03002 (1998-2022) sirve
   para edad×sexo provincial pero **no** trae nivel de estudios.
3. **Armonización de estudios**: las 11 categorías censales (CNED-2014) no
   coinciden 1:1 con las escalas CIS (que además cambian por era). Requiere un
   mapeo explícito CIS-era → 5-6 niveles MRP → categorías INE; es el trabajo
   pendiente real, no la disponibilidad del dato.
4. **Covariables MRP**: edad, sexo y estudios sí se post-estratifican; **provincia**
   entra como efecto de área. La **ideología** no está en el censo → solo puede
   entrar como término individual (no post-estratificado). Con 44/55 estudios con
   ideología 1-10 y buena demografía, el diseño es factible.
5. **n bajo**: provincias pequeñas con muestras CIS de ~1.000-2.000 casos y n
   provincial de 20-80 → el MRP ayuda precisamente ahí (encogimiento multinivel),
   pero los intervalos seguirán anchos. Publicar tal cual.

## 5. Explorador sociodemográfico de la web

Qué puede dar de sí, con este dataset:
- **Cruces individuales ponderados** por decenio/elección y provincia:
  voto / intención / recuerdo × edad, sexo, estudios, situación laboral, hábitat,
  interés y religiosidad.
- **Serie de ideología 1-10** (44 estudios, 1977-2025) y su relación con el voto.
- **Segmentación provincial** con muestra CIS (n por celda mostrado siempre; sin
  microdato reidentificable, conforme a CONTRIBUTING).
- **Pirámide/sociodemografía comparada** CIS (muestra) vs censo INE (población)
  para explicar visualmente el sesgo de muestra y el sentido del MRP.

Límites: `interes_politica` (19/55) y `religiosidad` (33/55) son esporádicos;
el explorador debe mostrar la cobertura por estudio para no sugerir falsos
huecos de categoría.

## 6. Reproducir

```bash
# entorno con pyreadstat (opcional, solo para check_sav)
python3 -m venv --system-site-packages /root/.venvs/29n-micro
/root/.venvs/29n-micro/bin/pip install -r pipeline/microdatos/requirements.txt

python3 pipeline/microdatos/extract_individual.py      # individual.parquet + cobertura.json
python3 pipeline/microdatos/validate_vs_polls.py       # validation_micro.json
/root/.venvs/29n-micro/bin/python pipeline/microdatos/check_sav.py 3141
```

## Siguiente paso

1. Mapeo CIS-era → categorías INE (66600) para las celdas de post-estratificación.
2. Descargar tabla 66600 (CSV/API) a `data/raw/ine/` (fuera de este scope) y
  construir el `censo_prov.csv` de denominadores.
3. Prototipo MRP con 3117/3141/3242 (con backtest) antes de generalizar.
