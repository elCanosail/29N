# Recalibración de los intervalos del modelo vivo (29N)

Fecha: 2026-10-16 · Alcance: `pipeline/modelo/calibracion.py`,
`pipeline/modelo/forecast.py` (integración en la generación), `web/sync-data.py`
(publica la banda del 95 %), los JSON regenerados y este informe.
**Sin commits ni push.** No se modifica `pipeline/modelo/backtest.py` ni ningún
fichero de `web/src/` salvo los **dos JSON de datos** (`forecast.json`,
`seats.json`).

## 0. Qué se ha hecho y qué NO

- **Sí**: ensanchar las bandas **publicadas** con un **factor multiplicativo `k`**
  estimado del propio backtest, sin tocar el **punto** ni el **método**.
  - 80 % (p10–p90): `k = 1,2806`
  - 95 % (p2,5–p97,5): `k = 1,8977`
- **No**: nada más. El punto (`punto`, = media ponderada), el σ del modelo
  (`sd_error_backtest`) y la simulación D'Hondt quedan **idénticos**.
- **Fuera de alcance (documentado)**: la banda interior del 60 % (p20–p80) y
  los `ic95` de escaños. Ver §6.

## 1. Motivación (el diagnóstico medido)

El backtest del ensemble (`docs/notes/ensemble-backtest.md`, §5) midió que las
bandas **nominales** del modelo vivo (`baseline` + `punto ± z·σ`) **subcubren**
fuera de muestra:

| Nominal | Cobertura real (LOO) |
|---|---|
| 80 % (p10–p90) | **74,6 %** |
| 95 % (p2,5–p97,5) | **81,4 %** |

El motivo es doble: (a) σ se estima en muestra (optimista) y (b) los errores
tienen **colas más pesadas** que la normal, así que el multiplicador `z` puro se
queda corto. La recalibración multiplicativa es la corrección mínima que arregla
la **anchura** sin tocar el punto ni la forma del método.

## 2. Estimador (honesto, con fuga cero)

`pipeline/modelo/calibracion.py`. Para cada observación `i` (partido × elección,
real ≥ 0,1 %) del **mismo protocolo** de `backtest.py`:

1. Se estandariza su error absoluto por la σ del baseline estimada **sin la
   elección evaluada** (`σ_LOO`, leave-one-election-out) — la misma definición
   con la que el informe del ensemble midió la cobertura honesta:
   `r_i = |err_i| / σ_LOO(i)`.
2. Factor de la banda `L`: **`k_L = quantile_L({r_i}) / z_{(1+L)/2}`**
   (interpolación lineal, numpy). La semianchura publicada pasa de `z·σ` a
   `k_L·z·σ`; como en p50 `z=0`, el **punto no cambia**.

n = 59 observaciones, pero solo **5 elecciones independientes**. El estimador es
**agrupado** (un `k` para los 13 partidos): una σ por partido con n ≤ 5 no
permite un factor por partido.

## 3. Factores y cobertura antes/después (números REALES)

Cobertura **fuera de muestra** (estandarizada con `σ_LOO`):

| Banda | `k` | z | Antes | Después | Nominal |
|---|---|---|---|---|---|
| 80 % (p10–p90) | **1,2806** | 1,2816 | 74,6 % | **79,7 %** | 80 % |
| 95 % (p2,5–p97,5) | **1,8977** | 1,9600 | 81,4 % | **94,9 %** | 95 % |

Los "antes" reproducen **exactamente** los del informe del ensemble (74,6 / 81,4):
el protocolo es el mismo. Los "después" quedan en 79,7 % (47/59) y 94,9 % (56/59)
— la diferencia con 80/95 es la discretización del cuantil empírico.

**Honestidad del "después"**: la cobertura "después" es optimista *por
construcción* (se estima y se mide con los mismos datos). La referencia honesta
es la **validación LOO del propio estimador** (§4).

Cobertura por elección con el `k` agrupado (honesta, `σ_LOO`):

| Elección | n | 80 % antes → después | 95 % antes → después |
|---|---|---|---|
| 2015-12-20 | 10 | 70,0 → 70,0 | 70,0 → 90,0 |
| 2016-06-26 | 11 | 90,9 → 90,9 | 90,9 → 100,0 |
| 2019-04-28 | 12 | 58,3 → 75,0 | 75,0 → 100,0 |
| 2019-11-10 | 13 | 69,2 → 76,9 | 76,9 → 92,3 |
| 2023-07-23 | 13 | 84,6 → 84,6 | 92,3 → 92,3 |
| **Total** | **59** | **74,6 → 79,7** | **81,4 → 94,9** |

No todas las elecciones llegan a ≈80 % (con 10–13 puntos por cita, ±1 acierto ya
mueve ~8 pp): el factor agrupado **mejora el conjunto**, no clava cada elección.

## 4. Validación leave-one-election-out del estimador (honestidad)

Se recalcula `k` con **4 elecciones** y se mide la cobertura en la **elección
excluida**. Es la referencia honesta (no la de §3).

| Banda | Cobertura LOO | `k` por fold (mín–máx) |
|---|---|---|
| 80 % | **79,7 %** | 1,028 – 1,536 |
| 95 % | **94,9 %** | 1,787 – 1,980 |

El `k` del 80 % **oscila entre 1,03 y 1,54** según qué elección se deje fuera, y
la cobertura por fold va de 69,2 % a 92,3 %. Es decir: el valor puntual `k=1,28`
tiene una **incertidumbre real grande** (con 5 citas no se puede afinar más), y
la cobertura LOO agregada (79,7 / 94,9) coincide con la nominal pero **no**
garantiza que cada elección futura la alcance. Se reporta sin maquillar.

## 5. Verificación: punto y escaños idénticos

- **Punto**: `punto`, `punto_baseline`, `punto_timesfm` y `sd_error_backtest`
  **idénticos** uno a uno antes/después en `forecast_state.json` (comprobado
  programáticamente).
- **Escaños**: `provincial.py` (10.000 runs, semilla fija) solo consume `punto`
  y `sd_error_backtest`, ambos intactos ⇒ recomputado y **`data/processed/modelo/seats.json`
  es idéntico byte a byte** salvo la fecha `generado`:

  ```
  3c3
  <   "generado": "2026-10-15",
  ---
  >   "generado": "2026-10-16",
  ```

  Es el **único** diff. Las medias de escaños, `ic95`, `p_ge1` y
  `central_escenario` (p. ej. PP 136,5 · IC95 [111,164] · central 138) no cambian.
  Igual en `web/src/data/seats.json` (mismo diff de una línea).

**Bandas publicadas** (`web/src/data/forecast.json`), antes → después:

| Partido | punto | p10 | p90 | p025 (nuevo) | p975 (nuevo) |
|---|---|---|---|---|---|
| PP | 35,41 | 31,93 → **30,95** | 38,88 → **39,86** | — → **25,32** | — → **45,49** |
| PSOE | 29,15 | 23,53 → **21,95** | 34,77 → **36,34** | — → **12,84** | — → **45,46** |
| VOX | 20,59 | 16,63 → **15,51** | 24,56 → **25,68** | — → **9,08** | — → **32,11** |
| SUMAR | 7,10 | 0,00 → **0,00** | 16,22 → **18,77** | — → **0,00** | — → **33,56** |

`punto`, `p20`, `p50` y `p80` **no cambian**. Se añade la banda del 95 %
(`p025`/`p975`) al JSON; la web la ignora (compatible hacia atrás: build OK).

## 6. Advertencias honestas (sin maquillaje)

1. **Factor agrupado**: un solo `k` para los 13 partidos. Los de cola pesada
   (SUMAR) tiran del factor hacia arriba para todos.
2. **5 elecciones**: el estimador descansa en 5 citas; los 59 puntos **no son
   independientes** (errores correlacionados dentro de cada elección). El IC del
   factor es el del LOO (§4), no un IC binomial sobre 59.
3. **"Después" optimista por construcción**: mismo conjunto para estimar y medir;
   la cifra honesta es la LOO (§4).
4. **Solo anchura**: sigue siendo una banda **simétrica** tipo normal; corrige la
   anchura, no la asimetría ni un posible sesgo del punto.
5. **σ del sampler intacta**: no se toca `sd_error_backtest` (lo consume
   `provincial.py`), por eso los **escaños quedan idénticos**. Consecuencia: los
   **`ic95` de escaños NO se recalibran** y probablemente también subcubran;
   hacerlo cambiaría `seats.json` y queda fuera del encargo (recomendación
   aparte).
6. **Banda del 60 % (p20–p80) no recalibrada por alcance**: medida, sobre-cubre
   (66,1 % honesto con nominal 60 %), así que dejarla intacta es conservador.
   El factor estimado (`k=0,849`; `aplicado:false` en el JSON) está en el
   artefacto como diagnóstico.
7. **Aplicación sobre σ en muestra**: `k` se estimó contra `σ_LOO` y se aplica
   sobre la `σ` en muestra que publica el modelo (`sd_error_backtest`). Medida
   *en muestra*, la banda **publicada** pasa de 76,3 → 84,7 % (80 %) y de
   89,8 → 100,0 % (95 %): si acaso, **conservadora**. La cifra fuera de muestra
   que hay que citar sigue siendo la LOO (79,7 / 94,9).

## 7. Reproducción

```bash
cd projects/29n
/root/.venvs/29n/bin/python pipeline/modelo/calibracion.py   # factores + validación
/root/.venvs/29n/bin/python pipeline/modelo/forecast.py      # forecast_state.json (calibrado)
/root/.venvs/29n/bin/python pipeline/modelo/provincial.py    # seats.json (idéntico salvo fecha)
/root/.venvs/29n/bin/python web/sync-data.py                 # web/src/data/*.json
cd web && npm run build                                      # verifica la web
```

`sync-data.py` es idempotente (dos runs → byte a byte igual). Sin aleatoriedad:
la calibración es determinista.

## 8. Salidas

- `pipeline/modelo/calibracion.py` — estimador + validación LOO + API
  (`cargar_factores`, `calibrar_cuantil`) que usa la generación.
- `pipeline/modelo/forecast.py` — aplica `k` al publicar cuantiles y añade la
  banda del 95 %; el punto y `sd_error_backtest` no cambian.
- `data/processed/modelo/calibracion_intervalos.json` — factores, cobertura
  antes/después, validación LOO por fold, advertencias.
- `data/processed/modelo/forecast_state.json` — cuantiles recalibrados.
- `web/src/data/forecast.json` — p10/p90 recalibrados + p025/p975 nuevos.
- `web/src/data/seats.json` — regenerado (idéntico salvo fecha `generado`).
