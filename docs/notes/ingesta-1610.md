# Ingesta 16-10-2026 — encuestadores nuevos (CIS + IMOP) para el modelo 29N

Alcance: `pipeline/cis/` (dedup + ingesta), `docs/notes/`, `data/raw/cis/`
(gitignored). Sin commits ni push. **No se tocó** `pipeline/modelo/`,
`web/src/`, `forecast.json`, `seats.json` ni `sync-data.py`, y **no se
regeneró el forecast ni la serie ponderada**.

Punto de partida: informe del cron `29n-exploracion-diaria` (job
`a7e00063-92cc-4e46-95c6-4e8ee78f87aa`, run 16-10-2026 06:00 UTC) = «3 URLs
candidatas nuevas de encuestadores (IMOP)» + «194 estudios CIS nuevos
detectados en la primera página del catálogo».

---

## 0. Resumen ejecutivo

1. **CIS — falso positivo masivo del detector.** De los 200 estudios de la
   primera página del catálogo (los más **recientes por fecha de creación**),
   solo **11 ya estaban en el catálogo** (re-detecciones) y **189 no**; pero de
   esos 189, **168 no son estudios electorales** (barómetros, Índice de
   Confianza del Consumidor, encuestas temáticas) y **21 son electorales
   autonómicos/municipales** (Andalucía/CyL/Aragón/Extremadura 2025-26, Galicia/
   País Vasco/Cataluña 2024). **Cero estudios de elecciones generales o europeas
   nuevos.** Motivo: el cron compara *todos* los tipos de estudio del listado
   reciente contra un catálogo que solo contiene electorales.
2. **CIS — nada que ingerir al corpus del modelo.** No hay generales/europeas
   nuevos ⇒ `pipeline/cis/catalog.json` **se regenera sin cambios** (134
   estudios validados). Como prueba de que la ingesta *sería* viable, se
   descargaron 2 estudios autonómicos nuevos (3558, 3566) con el pipeline
   existente: ambos OK (ver §2).
3. **IMOP — las 3 URLs detectadas no sirven para el modelo**, pero la home
   esconde **una encuesta pre-electoral real y fresca** (9-oct-2026, IMOP para El
   Confidencial) que el cron **no** detectó. Ficha técnica extraída en §3.
   Es la única fuente nueva model-relevante del día.
4. **IMOP — integración propuesta (sin aplicar).** `Imop Insights` ya es casa
   canónica del corpus privado (3 encuestas 2023, MAE 2,32). La encuesta nueva
   entra como observación `serie=privado` sin tocar `pipeline/modelo/` (ver §5).

---

## 1. Dedup CIS — números reales

Método reproducible: cargar la primera página del catálogo
(`.../es/estudios/catalogo?catalogo=estudio&sort=createDateBDE-&t=0&delta=200&start=0`,
«Mostrando 200 de 2584 elementos») con navegador anti-detección (Camoufox),
extraer los 200 *slugs* de estudio y contrastarlos contra
`pipeline/cis/catalog.json` **por ID de estudio** (el slug no lleva el nº; el ID
se lee de la ficha del listado) y **por slug**.

| Métrica | Valor |
|---|---|
| Estudios en la 1ª página del listado | **200** (de 2 584 totales) |
| Ya en `catalog.json` por **ID** (re-detecciones) | **11** |
| No en `catalog.json` por ID | **189** |
| → de esos 189, **no electorales** (barómetro/ICC/temático) | **168** |
| → de esos 189, **electorales autonómicos/municipales** | **21** |
| → de esos 189, **generales / europeas** | **0** |
| `catalog.json` (total, estudios electorales) | **134** |
| Estudios del catálogo que **no** aparecen en la 1ª página (antiguos) | 123 |

Los **11 re-detectados** (coinciden por ID y por slug):
`3386, 3407, 3411, 3415, 3416, 3420, 3458, 3460, 3465, 3500, 3513`.

**Reconciliación con el «194» del cron.** El cron suma los slugs de *todos* los
`<a href*="/es/estudios/">` de la página, incluidas 3 anclas de navegación
(`informacion-general`, `faqs-preguntas-frecuentes`, `metodologias`), y resta los
del catálogo. Reproducido hoy: 200 estudios + 3 nav = 203; 203 − 11 coincidencias
= **192**. El informe decía **194** (Δ+2, contenidos dinámicos del listado entre
las 06:00 y la reproducción). Conclusión idéntica con cualquiera de las dos
cifras: **el grueso de las detecciones no son estudios electorales**.

**Los 21 electorales no catalogados** (candidatos reales, todos autonómicos/municipales):

| ID | Fecha | Tipo / ámbito | Título |
|---|---|---|---|
| 3566 | 04/06/2026 | postelectoral · autonómicas 2026 | Andalucía |
| 3558 | 10/04/2026 | preelectoral · autonómicas 2026 | Andalucía |
| 3550 | 30/03/2026 | postelectoral · autonómicas 2026 | Castilla y León |
| 3548 | 18/02/2026 | postelectoral · autonómicas 2026 | Aragón |
| 3545 | 06/02/2026 | preelectoral · autonómicas 2026 | Castilla y León |
| 3541 | 15/01/2026 | postelectoral · autonómicas 2025 | Extremadura |
| 3543 | 12/01/2026 | preelectoral · autonómicas 2026 | Aragón |
| 3538 | 21/11/2025 | preelectoral · autonómicas 2025 | Extremadura |
| 3503 | 07/03/2025 | municipales/autonómicas | Tendencias y demandas municipales y autonómicas |
| 3464 | 11/06/2024 | autonómicas 2024 | Postelectoral Cataluña |
| 3459 | 17/05/2024 | autonómicas 2024 | Postelectoral País Vasco |
| 3456 | 24/04/2024 | autonómicas 2024 | Campaña Cataluña |
| 3453 | 11/04/2024 | autonómicas 2024 | Preelectoral Cataluña |
| 3451 | 04/04/2024 | autonómicas 2024 | Campaña País Vasco |
| 3448 | 18/03/2024 | autonómicas 2024 | Preelectoral País Vasco |
| 3446 | 06/03/2024 | autonómicas 2024 | Postelectoral Galicia |
| 3442 | 05/02/2024 | autonómicas 2024 | Campaña Galicia |
| 3440 | 29/01/2024 | autonómicas 2024 | Precampaña Galicia |
| 3437 | 08/01/2024 | autonómicas 2024 | Preelectoral Galicia |
| 3410 | 01/06/2023 | municipales/autonómicas 2023 | Barómetro junio 2023 postel. |
| 3402 | 10/04/2023 | municipales/autonómicas 2023 | Preelectoral municipales y autonómicas |

→ Ninguno es de ámbito estatal generales/europeas. **No amplían el corpus del
modelo 29N** (que se apoya en generales + europeas).

**Diagnóstico del detector (recomendación).** `cron_diario.py::explora_cis()`
compara el listado *completo* reciente (todos los tipos) contra un catálogo
*solo electoral* ⇒ ~85% de falsos positivos. Sugerencia: filtrar por slug
(`preelectoral|postelectoral|campana|flash|elecciones-(generales|al-parlamento-europeo)`)
antes de reportar, y excluir las 3 anclas de navegación.

---

## 2. Ingesta realizada (qué entró en el catálogo)

- **`pipeline/cis/catalog.json`: sin cambios (134 estudios).** Regenerado con
  `python3 pipeline/cis/build_catalog.py` desde los fragmentos validados
  (`data/raw/cis/catalog/chunk_t{1..4}.json`); salida idéntica byte a byte
  (`git diff` vacío). Reparto: generales 87, europeas 38, otro 8, municipales 1.
- **Nada nuevo que añadir al corpus del modelo**: 0 generales/europeas nuevos
  (§1). Los 21 electorales autonómicos quedan **listados como candidatos** sin
  incorporar (cambiarían el ámbito del corpus → decisión de alcance a revisar).
- **Prueba de viabilidad de ingesta** (no incorporada, solo descarga a
  `data/raw/`, gitignored): para 2 de los candidatos autonómicos nuevos,

  ```
  python3 pipeline/cis/fetch_microdata.py --catalog <tmp> --only 3558 3566 --pause 8
  → {"done": 2, "fail": 0, "skip": 0}
  ```

  - **3558** (preelectoral Andalucía 2026): `MD3558.zip` OK (2,69 MB), estimación
    `3558_Estimacion.pdf` descargada. ES parsea: `PESO` presente, 149 variables;
    incluye `INTENCIONANDA` (voto autonómico) **y `INTENCIONG` (intención de voto
    en *supuestas elecciones generales*)**.
  - **3566** (postelectoral Andalucía 2026): `MD3566.zip` OK (2,48 MB); ES
    parsea, `PESO` presente, 254 variables.
  - **Sin anti-bot** en el momento de la prueba (HTTP 200 en ficha y ZIP).
- **Conversión (`normalize.py`) NO ejecutada**: reescribiría
  `data/processed/cis/polls.jsonl` / `studies.json` / `validation.json` con
  estudios autonómicos, contaminando el corpus validado del modelo. No se fuerza
  (coherente con «la entrada se revisará antes»). La viabilidad de conversión se
  verificó de forma **no destructiva** (parseo del ES en memoria: §2).
- **Hallazgo útil:** estudios autonómicos como 3558 llevan variable de voto
  **general** (`INTENCIONG`) → un subconjunto autonómico *podría* aportar señal al
  modelo general, pero con ámbito territorial = CCAA (no nacional) ⇒ requiere
  tratamiento aparte, no merge directo.

---

## 3. IMOP — fichas técnicas

Las **3 URLs** de `data/processed/cron/candidatas.json` (detectadas 15-10):

| URL | Qué es | Publicado | ¿Model-relevante? |
|---|---|---|---|
| `/encuesta-telefonica` | Página de **servicio** (metodología CATI, «+30 años de encuestas telefónicas») | 2022-05-12 | No |
| `/encuestas-online` | Página de **servicio** (panel propio EMOP, CAWI) | 2022-05-12 | No |
| `/encuesta-de-imop-insights-para-vanitatis-sobre-el-estado-de-la-corona` | Encuesta **Vanitatis (El Confidencial)** sobre la *imagen de la Corona*, 8º aniversario de Felipe VI | 2022-06-23 | No (no electoral, 4 años) |

**Ninguna accesible con anti-bot** (curl HTTP 200 directo, sin challenge).

**Hallazgo (la encuesta que importa).** La home de IMOP publica hoy una cuarta
candidata que el cron **no** capturó el 16-10:

- **URL:** `https://www.imop.es/encuesta-pre-electoral-para-el-confidencial-2026/`
- **Título:** Encuesta pre-electoral para El Confidencial 2026 · publicada **09-10-2026**
- **Cliente/comisionado:** IMOP Insights para **El Confidencial**
- **Universo:** personas de 18+ años censadas con derecho a voto en elecciones generales
- **Fechas de campo:** **5 al 7 de octubre de 2026**
- **Diseño muestral:** aleatorio estratificado proporcional por CCAA y tamaño de municipio; control de cuotas por sexo-edad y nivel de estudios
- **Tamaño:** **900 entrevistas**
- **Técnica:** híbrida **CATI (telefónica) + CAWI (online)**; la parte online vía **EMOP**, panel propio de IMOP
- **Margen de error:** no procede estricto (parte online no probabilística); **±3,3 pp orientativo**
- **Estimación de voto (base voto válido):** **PP 30%**, **PSOE 26%**, **Vox 19%**, **Sumar 7,6%**
- Nota publicada: «el campo se cerró antes de tener conocimiento de la muerte de Maricarmen» (María del Carmen, contextual — no afecta a la ficha)

*(Otras entradas electorales de IMOP, antiguas y regionales: `encuesta-electoral-andalucia`
29-04-2022 y `electoralcastillayleon` 24-01-2022, ambas para el Observatorio
electoral de El Confidencial.)*

**Por qué el cron falló aquí.** El informe imprimía solo 10 slugs; el detector
casa `href` absolutos de la home. La candidata `pre-electoral-2026` apareció en
la home **después** de la pasada de las 06:00 (o vía enlace relativo/asíncrono),
y quedó fuera. **Acción sugerida:** que el cron (a) capture también `href`
relativos y (b) re-liste IMOP por `/noticias/` además de la home.

---

## 4. IMOP — propuesta de mapeo alias → familia del modelo

IMOP **ya está** en el corpus privado: `pipeline/encuestadores/aliases.json` la
canoniza como **`Imop Insights`** (alias: `Imop`, `IMOP Insights para El
Confidencial`); `data/processed/encuestadores/scoring.json` le da **MAE 23J =
2,32** (n=3 encuestas, 7 obs).

**No hace falta ningún alias nuevo.** La encuesta publica las 4 grandes con sus
nombres estándar, ya cubiertos en `party_aliases.csv` y `aliases.json`:

| Etiqueta IMOP | Canónico | Grupo | ¿Familia `FAMILY`? |
|---|---|---|---|
| PP | `PP` | derecha | — (partido modelado) |
| PSOE | `PSOE` | centroizquierda | — |
| Vox / VOX | `VOX` | derecha | — |
| Sumar | `SUMAR` | izquierda | — (ya es la marca-familia; no se pliega) |

**Serie IMOP en el modelo:** `casa = "Imop Insights"`, `serie = "privado"`,
`ambito = "nacional"`, `eleccion = "generales 2026"`. Con solo las 4 grandes,
suma 82,6 ≥ `BIG4_MIN_SUM=75` ⇒ **pasa el filtro de completitud** de
`common.py::_build_priv`. Corrección EB por casa `Imop Insights` (ya existe si
está en `house_effects.json`; si no, corrección 0). Peso:
recencia (media-vida 45 d) × √(n/2000) × 1/(1+MAE 2,32).

---

## 5. Plan de integración IMOP (preparado, **sin aplicar**)

**No se aplica nada al modelo**: la entrada se revisa antes (instrucción de la
tarea). Bosquejo listo para ejecutar tras el visto bueno.

### 5.1 Extractor (nuevo fichero, p. ej. `pipeline/encuestadores/extract_imop.py`)
El post de IMOP es HTML estático (curl directo, sin anti-bot). El extractor debe:
1. Descargar `https://www.imop.es/<slug>/`.
2. Extraer la **ficha técnica** (campos «Universo», «Fechas de campo», «Diseño
   muestral», «Tamaño muestral», «Técnica de entrevista», «Margen de error») y la
   **estimación** (bullets «PP … 30% de los votos válidos», «PSOE … 26%»,
   «Vox … 19%», «Sumar … 7,6%»).
3. Emitir una **entrada de staging** en `data/processed/encuestadores/_staging/`
   con el esquema ya usado por el pipeline (`majors.json`):

   ```json
   {"encuestas": [{
     "fuente": "Imop Insights",
     "estudio_id": "imop-2026-10-09-elconfidencial-pre29n",
     "fecha_trabajo": "2026-10-05/2026-10-07",
     "fecha_publicacion": "2026-10-09",
     "n": 900,
     "metodologia": "CATI + CAWI (panel EMOP propio)",
     "ambito": "nacional",
     "eleccion": "generales 2026",
     "url": "https://www.imop.es/encuesta-pre-electoral-para-el-confidencial-2026/",
     "fuente_tipo": "prensa",
     "extracto": "IMOP/El Confidencial (ficha técnica): 900 entrevistas, campo 5-7 oct 2026, CATI+CAWI. Voto válido: PP 30%, PSOE 26%, Vox 19%, Sumar 7,6%.",
     "votos": {"PP": 30.0, "PSOE": 26.0, "VOX": 19.0, "SUMAR": 7.6}
   }]}
   ```

### 5.2 Punto exacto donde entra en la serie ponderada
`pipeline/encuestadores/build_dataset.py` lee los `_staging/*.json` y escribe
`data/processed/encuestadores/{polls.jsonl, sources.json}` (ya existe la ruta
genérica → **sin cambios de código**):

```
[staging imop] → build_dataset.py → encuestadores/polls.jsonl
   → modelo/common.py::Observations._build_priv   (casa "Imop Insights", serie "privado")
   → modelo/common.py::build_party_series         (peso recencia×muestra×calidad + corr. EB)
   → modelo/build_series.py → data/processed/modelo/series.json  (mes 2026-10)
   → forecast (NO ejecutado)
```

Es decir, la observación entra como **una más de la casa `Imop Insights`** en la
serie mensual ponderada, en el bucket **2026-10**; nada en `pipeline/modelo/`
necesita cambio (el esquema de `polls.jsonl` es el mismo que ya consume).

### 5.3 Pasos de ejecución (cuando se apruebe)
1. Añadir `extract_imop.py` (nuevo) y su entrada de staging.
2. `python3 pipeline/encuestadores/build_dataset.py` (regenera polls+sources).
3. Revisar diff de `polls.jsonl` (debe sumar solo la observación IMOP nueva).
4. `python3 pipeline/modelo/build_series.py` + re-forecast (fase ya existente;
   **fuera del alcance de esta tarea**).

### 5.4 Caveats
- IMOP publica solo los 4 grandes en el resumen ⇒ la observación no aporta ERC/
  JxCat/PNV/EH Bildu/BNG/CUP/CC/NA+ (el modelo los deja sin observación en ese
  mes; correcto).
- La técnica es híbrida con panel no probabilístico; IMOP mismo advierte del
  margen. Mantener el peso de calidad por MAE histórico (2,32) sin inflarlo.
- Tras cada ingesta conviene re-correr `sesgo/compute_house_effects.py` para que
  la corrección EB de `Imop Insights` incluya el nuevo punto (paso del pipeline
  de sesgo, no del modelo).

---

## 6. Limitaciones / notas de honestidad

- El «194» del cron es hoy **192** reproducibles (contenido dinámico del listado).
- No se pudo confirmar si la candidata `pre-electoral-2026` estaba en la home a
  las 06:00 (posible publicación/actualización posterior); se reporta como
  hallazgo, no como fallo certero del cron.
- La conversión CIS de los nuevos autonómicos **no se ejecutó** para no
  sobrescribir el corpus validado (decisión deliberada, no fallo).
- Los cambios en `pipeline/modelo/`, `web/src/`, `forecast.json`, `seats.json` y
  `sync-data.py` que aparecen en `git status` **son de otro trabajo en curso y no
  se han tocado**.

## 7. Artefactos

- `docs/notes/ingesta-1610.md` — este documento.
- `pipeline/cis/catalog.json` — regenerado, **idéntico** (134 estudios).
- `data/raw/cis/{3558,3566}/` — descargas de prueba (gitignored), manifest
  actualizado.
- Listado primero del catálogo CIS (200 estudios, JSON parseado) — volcado en
  `/tmp/cis_listing.json` (efímero; reproducible con Camoufox sobre el endpoint
  `catalogo?...&delta=200&start=0`).
