# Ingesta IMOP · El Confidencial (pre-electoral 29N, campo 5-7 oct 2026)

Tarea: ingesta de la encuesta pre-electoral de IMOP para El Confidencial al
modelo 29N. Repo `github.com/elCanosail/29N`.

**Fecha de trabajo:** 16-10-2026 · **Autor:** subagente (sesión `29N · ingesta
IMOP/Confidencial`) · **Sin commits, sin push, sin deploy.**

---

## 0. Resumen ejecutivo (hallazgo principal)

> **La encuesta YA estaba ingerida en el modelo desde el 15-10-2026** (commit
> `55c13ae`, «Fase 3 — curación inicial de encuestadores privados»), con
> `estudio_id = imop-2026-10-05`, casa `Imop Insights`, `n = 900`, campo
> `2026-10-05/2026-10-07`, publicación `2026-10-09`.

Por tanto, la premisa de la tarea («el cron no la detectó ⇒ hay que añadirla»)
es **solo cierta en la parte de detección**: el cron diario de exploración
**no** capturó la URL el 16-10 (ver `docs/notes/ingesta-1610.md` §3), pero el
dato **ya había entrado por la curación manual de la Fase 3** una semana antes.
La reeje cución de la cadena (`build_series → forecast → provincial →
sync-data`) es **byte a byte idempotente**: el punto **no se mueve** porque el
dato ya estaba dentro.

Para cuantificar el efecto de la encuesta (lo que sí cambió al integrarla el
15-10) se calcula un contrafactual (con vs. sin la observación IMOP): PP −0,21 pp,
SUMAR +0,15 pp, VOX +0,07 pp, PSOE −0,02 pp (§6).

**No se ha modificado ningún dato**: no hacía falta añadir la encuesta (ya
estaba) y las dos vías de "ampliación" detectadas (mayor precisión de PP/PSOE;
partidos pequeños) requieren una decisión de alcance del propietario (§7).

---

## 1. Fuentes

| # | Fuente | URL | Estado |
|---|---|---|---|
| A | **IMOP Insights** — ficha original (encuestador) | `https://www.imop.es/encuesta-pre-electoral-para-el-confidencial-2026/` | HTTP 200 con `curl` (sin anti-bot) |
| B | **El Confidencial** — artículo de publicación (comitente) | `https://www.elconfidencial.com/espana/2026-10-09/derecha-pp-gana-vox-dispara-sanchez-baja-sumar_4441291/` | HTTP 403 con `curl`; cuerpo tras muro (Camoufox carga la cabecera/ficha; los dígitos completos solo aparecen en el texto indexado) |
| C | Agregadores (contraste) | `sumomento.com/encuestas/imop-2026-10-07`, `electografica.com/2026/10/encuesta-imop-insights-261009.html`, `colmenadedatos.com/...`, `eleccionesespaña/imop` | Indexados |

El artículo de El Confidencial se localiza (tarea 1) y se cita; su cuerpo
detallado está **parcialmente tras el muro** para sesión anónima, pero el titular,
la entradilla y la **ficha técnica** se recuperan íntegros.

---

## 2. Datos verbatim

### 2.1 IMOP (fuente A) — estimación de voto

> **ESTIMACIÓN DE VOTO (Encuesta pre-electoral El Confidencial 09-10-26)**
>
> *Si las elecciones fuesen mañana:*
> - ✓ El PP se situaría como primera fuerza política, con **el 30% de los votos
>   válidos**, seguido del PSOE, con **un 26%**.
> - ✓ Vox consolidaría su tercera posición, alcanzando **el 19% de los
>   sufragios** y ampliando considerablemente la distancia respecto a Sumar,
>   con quien prácticamente empató en 2023.
> - ✓ Sumar retrocedería hasta **el 7,6%**.

Nota publicada en la misma página: «*el campo se cerró antes de tener
conocimiento de la muerte de Maricarmen*» (contexto; no afecta a la ficha).

### 2.2 IMOP (fuente A) — ficha técnica

| Campo | Valor verbatim |
|---|---|
| Publicación | `octubre 9, 2026` (`date`: `2026-10-09`) |
| Comisionado | «IMOP Insights para EL CONFIDENCIAL» |
| Universo | «Personas de 18 años y más censadas y con derecho a voto en las elecciones generales.» |
| Fechas de campo | «Del 5 al 7 de octubre de 2026.» |
| Diseño muestral | «Aleatorio estratificado proporcional por CCAA y tamaño de municipio. Control de cuotas por sexo-edad y nivel estudios.» |
| Tamaño muestral | «900 entrevistas.» |
| Técnica de entrevista | «Metodología híbrida: telefónica (CATI) y online (CAWI). Las entrevistas online se realizaron a través de EMOP, panel propio de IMOP.» |
| Margen de error | «±3,3 puntos porcentuales» (orientativo; IMOP advierte que la parte online no es probabilística y «no procede calcular el margen de error muestral en sentido estricto») |

### 2.3 IMOP (fuente A) — escaños (`<script id="chart-data">`, bloque JSON embebido)

```json
{
  "title": "Estimación Elecciones Generales 29 Noviembre para El Confidencial",
  "date": "2026-10-09",
  "estimateLabel": "Estimación actual",
  "referenceLabel": "Resultados 2023",
  "totalSeats": 350,
  "parties": [
    { "id": "sumar", "name": "SUMAR/F.A.", "estimate": 11,  "reference": 31 },
    { "id": "psoe",  "name": "PSOE",       "estimate": 110, "reference": 121 },
    { "id": "pp",    "name": "PP",         "estimate": 137, "reference": 137 },
    { "id": "vox",   "name": "VOX",        "estimate": 70,  "reference": 33 }
  ]
}
```

(Colores omitidos; el JSON los incluye.) El total representado en el gráfico es
328/350 (faltan ~22 escaños de partidos no dibujados: ERC, Junts, PNV, EH Bildu,
BNG, CC, UPN, AA…).

### 2.4 El Confidencial (fuente B) — verbatim del artículo

- Titular: «**La derecha suma 201 escaños: el PP gana, pero cae 7; Vox se dispara
  y Sánchez baja 11 y se come a Sumar**».
- Entradilla: «*El bloque de la derecha (51.3%) aventaja en 15 puntos
  porcentuales al de la izquierda (36.4%)…: el PSOE pierde 11 diputados (110), el
  Partido Popular gana con **130**, Vox sube 37 hasta **70** y Sumar se
  descalabra (**11**)*».
- «El Partido Popular será la primera fuerza con **130 escaños**, lo que supone
  una pérdida de 7 diputados frente a los 137 del 23J (-2,7%). El gran vencedor
  de la encuesta es Vox, que pasa de 33 escaños a 70 (+37) y **del 12,4% de las
  papeletas al 19%** (+6,6%).»
- «el PSOE cae 11 escaños, al pasar de **121 a 110** (-5,2%), pero sobre todo al
  batacazo de Sumar, que con la nueva denominación de **Frente Amplio** pasa de
  **31 escaños a 11**».
- «Podemos, que esta vez tiene previsto concurrir en solitario, consigue un
  único escaño y el **2,3%** de las papeletas.»
- Ficha técnica (idéntica a §2.2; añade): técnica «*hibrida, mediante la
  combinación de entrevista telefónica (CATI) y entrevista online (CAWI), con una
  distribución aproximada de **45%/55%**. En el canal telefónico, el **70%** de
  las entrevistas se realizó con individuos contactados a través de teléfono
  móvil*»; margen «*±3,3 puntos porcentuales*».

### 2.5 Contraste con agregadores (fuente C)

Los agregadores publican la tabla completa (voto % y escaños), coincidente con
El Confidencial:

| Partido | Voto % | Escaños |
|---|---|---|
| PP | **30,4** | 130 |
| PSOE | **26,5** | 110 |
| Vox | **19,0** | 70 |
| Sumar | 7,6 | 11 |
| Podemos | 2,3 | 1 |
| ERC | 2,2 | 8 |
| SALF | 1,9 | 0 |
| EH Bildu | 1,3 | 6 |
| Junts | 1,1 | 4 |
| BNG | 1,1 | 3 |
| AA | 1,0 | 1 |
| PNV | 0,9 | 4 |
| CC | 0,6 | 1 |
| UPN | 0,2 | 1 |

---

## 3. Mapeo al modelo de partidos

`pipeline/modelo/common.py` usa los **canónicos** de `party_canon` (diccionario
CIS) y la familia `FAMILY` (`PODEMOS`/`IU`/`UNIDAS PODEMOS` → `SUMAR`).

| Etiqueta IMOP/EC | Canónico del modelo | ¿Familia? | Encaja |
|---|---|---|---|
| PP | `PP` | — | ✅ partido modelado |
| PSOE | `PSOE` | — | ✅ |
| Vox / VOX | `VOX` | — | ✅ |
| Sumar / «SUMAR/F.A.» | `SUMAR` | ya es la marca-familia | ✅ (no se pliega) |

- Los **4 grandes encajan sin alias nuevos**. `pipeline/encuestadores/aliases.json`
  ya tiene la casa y los partidos; `Imop Insights` es casa canónica
  (MAE 23J = 2,32).
- Solo se publican los 4 grandes en el resumen de IMOP ⇒ la observación **no
  aporta** datos a ERC/JXCAT/PNV/EH BILDU/BNG/CUP/CC/NA+/PACMA (correcto: el
  modelo los deja sin observación ese mes). *(Los partidos pequeños solo
  aparecen en El Confidencial / agregadores: §2.5 y §7.)*
- **Podemos no encaja en 2026**: según El Confidencial concurre «en solitario»
  (2,3%); la familia `FAMILY` lo plegaría a `SUMAR`, lo cual sería incorrecto en
  este escenario. → documentado, no aplicado (§7).

---

## 4. Dónde está en el pipeline (y por qué ya estaba)

Flujo real (confirmado leyendo el código):

```
data/processed/encuestadores/_staging/menores.json   ← YA contiene imop-2026-10-05
     │  build_dataset.py
     ▼
data/processed/encuestadores/polls.jsonl             ← 4 filas imop-2026-10-05 (YA, commit 55c13ae)
     │  common.py::Observations._build_priv  (casa "Imop Insights", serie "privado",
     │     pasa BIG4_MIN_SUM: 30,0+26,0+19,0+7,6 = 82,6 ≥ 75)
     ▼
common.py::build_party_series  (peso = recencia×√(n/2000)×1/(1+MAE); corrección EB)
     ▼
pipeline/modelo/build_series.py → data/processed/modelo/series.json  (bucket 2026-10)
     ▼
pipeline/modelo/forecast.py  → forecast_state.json  (punto = baseline = última media ponderada)
     ▼
pipeline/modelo/provincial.py → seats.json  (swing + D'Hondt, 10 000 sims)
     ▼
web/sync-data.py → web/src/data/{forecast,seats,…}.json
```

Evidencia de que la observación IMOP entra al modelo:
- En `series.json.meta.parametros.estudios_privados_excluidos_incompletos`
  aparecen `imop-2023-05-29` y `imop-2023-07-11` **pero no** `imop-2026-10-05`
  ⇒ la nueva **pasó** el filtro de completitud.
- `series.json` de PP/PSOE/VOX/SUMAR: `last_obs = 2026-10-12`, `n_obs` 49/49/42/69
  (incluye la observación del 5-7 oct).
- Contrafactual §6: quitar la observación **sí** cambia el punto ⇒ estaba dentro.

---

## 5. Cadena ejecutada y verificación (evidencia fresca)

Ejecutada el 16-10-2026 con `/root/.venvs/29n/bin/python`:

```
build_series.py   → OK series.json — 13 partidos, 594 meses (1977-06-30..2026-11-30)
forecast.py       → OK forecast_state.json — horizonte 1 mes, metodo=baseline
provincial.py     → OK seats.json — 10000 runs, 52 provincias, calibración 4 it (dev 0.0085 pp)
                    Coherencia escaños: suma=350.00 (ok=True) · votos: max dev=0.0085 pp (ok=True)
sync-data.py      → 9 JSON escritos en web/src/data/ (forecast, seats, backtest, series,
                    elecciones, reparto23, encuestas, exclusiones, sesgo)
```

**Idempotencia (prueba de que no faltaba nada).** SHA-256 antes vs. después de
la cadena:

| Fichero | Antes | Después | ¿Cambia? |
|---|---|---|---|
| `data/processed/modelo/forecast_state.json` | `ef081d96…` | `ef081d96…` | **no** |
| `data/processed/modelo/forecast_state.timesfm.json` | `5403bcc5…` | `5403bcc5…` | **no** |
| `data/processed/modelo/seats.json` | `9819c350…` | `9819c350…` | **no** |
| `web/src/data/forecast.json` | `b01b16f3…` | `b01b16f3…` | **no** |
| `web/src/data/seats.json` | `9b20aa2c…` | `9b20aa2c…` | **no** |

`series.csv` (solo valores) también byte-idéntico; de `series.json` solo cambió
el campo `meta.generado` (15-10 → 16-10). **Los valores no se mueven.**

### Dónde NO se tocó
`pipeline/mrp/` (otro agente), `pipeline/modelo/backtest.py`, `web/src/` fuera de
los JSON de datos. No hay commits ni push.

---

## 6. Punto antes / después

Punto estatal publicado (baseline = última media ponderada, renormalizada a
universo modelado; `%` sobre voto válido):

| Partido | **PUBLICADO** (con IMOP, ya integrado) | **sin IMOP** (contrafactual) | Δ por incluir IMOP |
|---|---:|---:|---:|
| PP | **35,406 %** | 35,619 % | **−0,212 pp** |
| PSOE | **29,146 %** | 29,161 % | −0,015 pp |
| VOX | **20,595 %** | 20,528 % | +0,067 pp |
| SUMAR | **7,104 %** | 6,952 % | **+0,152 pp** |
| ERC | 1,724 | 1,722 | +0,002 |
| JXCAT | 1,511 | 1,509 | +0,002 |
| PNV | 1,039 | 1,038 | +0,001 |
| EH BILDU | 1,591 | 1,589 | +0,002 |
| BNG | 0,770 | 0,769 | +0,001 |
| CUP | 0,272 | 0,272 | ~0 |
| CC | 0,163 | 0,163 | ~0 |
| NA+ | 0,267 | 0,267 | ~0 |
| PACMA | 0,412 | 0,412 | ~0 |

- Columna «PUBLICADO» = `web/src/data/forecast.json` (coincide al dígito con el
  contrafactual «con IMOP»).
- **Antes/después de *esta* reeje cución:** sin cambio (idempotente, §5). El
  «después» es el publicado; el «antes» es el hipotético sin la encuesta.
- El punto movido por la encuesta al integrarse (15-10) fue el de la columna Δ.

**Escaños** (D'Hondt, media de 10 000 sims sobre el punto anterior):

| Partido | Media | IC95 | Central |
|---|---:|---|---:|
| PP | 136,5 | [111,164] | 138 |
| PSOE | 106,4 | [72,137] | 109 |
| VOX | 66,8 | [42,93] | 68 |
| SUMAR | 14,9 | [0,50] | 9 |
| EH BILDU | 7,1 | [5,10] | 7 |
| … | | | |

Coherencia: suma de medias = 350,000; desviación votos ≤ 0,0085 pp.

---

## 7. Discrepancias detectadas (no aplicadas) y recomendaciones

1. **Precisión de PP/PSOE.** IMOP redondea en su texto («30%», «26%»); El
   Confidencial y los agregadores publican **30,4%** y **26,5%**. El corpus
   guarda 30,0/26,0 (fuente IMOP). Sensibilidad calculada con 30,4/26,5:
   PP 35,406→35,415 (+0,009 pp), PSOE 29,146→29,173 (+0,027 pp). **Marginal**;
   no aplicado (fuente primaria = IMOP).
2. **Anomalía de escaños en el gráfico de IMOP.** Su `chart-data` da **PP = 137**
   escaños (= exactamente el resultado de 2023, y su propio «reference»), mientras
   El Confidencial publica **PP = 130**. Parece un error de la tabla editable de
   IMOP (PSOE 110, VOX 70 y SUMAR 11 sí coinciden con EC). **Los escaños no
   entran al modelo** (se recalcula con D'Hondt), así que no afecta; solo se deja
   constancia.
3. **Partidos pequeños ausentes.** IMOP solo publica los 4 grandes. El resto
   (ERC 2,2, Junts 1,1, PNV 0,9, EH Bildu 1,3, BNG 1,1, CC 0,6, UPN 0,2, Podemos
   2,3) viene de EC/agregadores. **Añadirlos movería partidos pequeños de forma
   material** (p. ej. ERC 1,72→2,41; CC 0,16→0,66; BNG 0,77→1,20 en el escenario
   de prueba). Requiere decisión de alcance: son fuentes secundarias y **Podemos
   no debe plegarse a SUMAR** en 2026. **No aplicado.**
4. **Gap de detección del cron (la causa real del encargo).** El cron
   `29n-exploracion-diaria` no capturó esta URL. Recomendaciones (ya sugeridas en
   `docs/notes/ingesta-1610.md` §3): capturar también `href` relativos y releer
   IMOP por `/noticias/` además de la home.

---

## 8. Limitaciones / honestidad

- El artículo de El Confidencial está parcialmente tras muro para sesión anónima
  (`curl` 403; Camoufox ve cabecera y ficha). Los dígitos completos del artículo
  se citan desde su texto indexado; se marcan como fuente B.
- La encuesta no publica margen estricto (panel no probabilístico); IMOP lo
  advierte. El modelo ya pondera por MAE histórico de la casa (2,32) sin
  inflarlo.
- El contrafactual usa el mismo resto del corpus congelado; es una comparación
  determinista (sin aleatoriedad) del efecto de la observación en la serie.
- `data/processed/modelo/series.json` queda modificado en el árbol de trabajo
  por la reeje cución (solo cambia `meta.generado`). No se ha commiteado.

## 9. Artefactos

- `docs/notes/ingesta-imop-confidencial.md` — este documento.
- `/tmp/imop.html`, `/tmp/cf.py`, `/tmp/sens.py` — efímeros (reproducibles).
- Ficheros regenerados (idénticos byte a byte): ver §5.
