# MRP provincial (29N) — estado real del prototipo y recomendación

Fecha: 2026-10-16 · Alcance de escritura de esta sesión: `pipeline/mrp/`,
`data/processed/mrp/`, este documento. Todo lo demás es **solo lectura**.
Sin commits ni push. Premisa del propietario: **SIN PRISA** — la calidad y la
honestidad del backtest importan más que la fecha; el método está congelado para
producción y esto es I+D para evaluar si entra (esta elección o la siguiente).

> Este documento sustituye al resumen ejecutivo de `docs/notes/mrp.md` (que se
> conserva como bitácora de la fase 4-c). Aquí se audita el prototipo, se añade
> lo que faltaba (modelo **multinivel** de verdad, sensibilidad al censo,
> comparación con el baseline de producción) y se dan los números reales.

---

## 0. Resumen ejecutivo (respuesta a la tarea)

- **El prototipo ya estaba casi completo y es reproducible.** El backtest
  2015-2023 corre en ~40 s y reproduce *bit a bit* los resultados publicados
  (verificado esta sesión). La conclusión previa se mantiene.
- **Lo que faltaba de verdad** (y se ha completado aquí):
  1. el «modelo multinivel» era en realidad **efectos fijos** (dummies de
     provincia) con una L2 única que además penalizaba la demografía — no era un
     modelo jerárquico;
  2. **no había cuantificación del bloqueo del censo antiguo** (§2 de `mrp.md`):
     se afirmaba la limitación, pero no se medía su efecto;
  3. **no había comparación explícita con el baseline de producción**
     (`seats.json`).
- **Veredicto tras completarlo: el MRP sigue sin batir al swing uniforme.**
  - Test A (geografía pura): MRP **1,037** / MRP jerárquico **1,030** /
    swing **0,833** pp.
  - Test B (previsión sin fuga): MRP **1,788** / MRP jerárquico **1,783** /
    swing **1,787** pp.
- **El bloqueo del censo antiguo NO decide el veredicto.** Post-estratificar
  2015-2019 con censo 2021, 2022, 2023 o 2024 mueve el MAE **0,002 pp de media**
  (rango 0,001-0,003), frente a brechas de 0,06-0,65 pp frente al swing.
- **Recomendación: NO listo para entrar al modelo provincial.** Lo que le falta
  no es demografía: la geografía del voto provincial es **persistente**, y lo que
  la predice es el voto provincial anterior. La vía con evidencia es modelar
  **elasticidades de swing por provincia** (microdatos de panel), no añadir
  estructura sociodemográfica.

---

## 1. Auditoría del estado real

### 1.1 Qué funciona (verificado ejecutando)

| Componente | Estado | Evidencia |
|---|---|---|
| `fetch_censo_ine.py` → `censo_cells.csv` + `censo_meta.json` | ✅ completo | 8.736 celdas (52×2×7×3×4 periodos), población 18+ 2024 = 40.594.509 |
| `mrp_core.py` (modelo + post-estratificación + swing + lectura de Interior) | ✅ completo | backtest reproducible en 40 s |
| `backtest_mrp.py` (5 elecciones, 2 tests) | ✅ completo | regen. idéntica salvo fecha/segundos |
| `poststrat_29n.py` → `poststrat.json` | ✅ completo | 4 estudios, 17.366 filas, censo 2024, 2.184 celdas |
| `test_coherence.py` (5 tests) | ✅ pasan | provincias suman 100; agregado = forecast (dev 0,0098 pp); 2.184 celdas; población censal; estructura vs `seats.json` |

### 1.2 Qué estaba a medias (y se ha completado)

1. **El «modelo multinivel» no era multinivel.** `mrp_core.fit_mrp` usa
   `LogisticRegression` con dummies de provincia y **una sola** `C` que penaliza
   por igual demografía y provincia. El encogimiento provincial es un subproducto
   de la L2, no un efecto aleatorio con varianza estimada. → Añadido
   `mrp_hier.py` (ver §3).
2. **El bloqueo del censo no estaba cuantificado.** → Añadido
   `sensitivity_censo.py` (ver §5).
3. **No había comparación con el baseline.** → Añadido
   `compare_baseline_29n.py` (ver §6).

### 1.3 Dependencias de datos que faltan (limitaciones reales)

- **Censo**: la tabla 66600 (provincia × sexo × edad × estudios) **arranca en
  2021**. El Censo 2011 no ofrece descarga CSV/API por provincia ni armonización
  de estudios compatible → el backtest 2015-2019 fuerza la estructura 2021 (o la
  más cercana). Ver §5: el efecto es despreciable.
- **Microdatos 2015-2016**: el 20D-2015 sólo dispone de **2 estudios** estatales
  en la ventana de 3 años (17.403 filas) y el 26J-2016 de **3** (34.864). Es una
  limitación de **muestra**, no sólo censal.
- **29N (2026-11)**: la microdata CIS termina en **2025-04**, así que la
  post-estratificación usa sólo **4 estudios de 2024-2025** (17.366 filas). Las
  encuestas privadas hasta 2026-10 que alimentan el forecast estatal **no**
  entran aquí (no son microdato).
- **Entorno**: el intérprete de sistema es **Python 3.12.3** (no 3.11); el venv
  `29n-mrp` se creó con `--system-site-packages`. **No se han añadido
  dependencias pesadas**: `mrp_hier.py` usa sólo `numpy` + `scipy` (ya presentes);
  `statsmodels` figura en `requirements.txt` pero el código no lo usa.

---

## 2. Datos usados

- Censo: INE tabla 66600 (reducción propia a 52 × 2 sexos × 7 edades × 3 estudios
  × 4 periodos). `pipeline/mrp/fetch_censo_ine.py`.
- Microdatos: `data/processed/microdatos/individual.parquet` (532.498
  entrevistas, 55 estudios). Sólo estudios de ámbito **estatal** (los autonómicos
  usan otra base y sobre-representan a los territoriales).
- Resultados reales: `data/processed/interior/results_provincial.jsonl` +
  `elections.json` (canonicalización del proyecto, leída).
- Baseline de producción: `data/processed/modelo/seats.json` (sólo lectura).

---

## 3. Lo añadido: modelo multinivel propiamente dicho

`pipeline/mrp/mrp_hier.py`.

```
logit P(y_i = k) = α_k + β_{k, demografía_i} + u_{k, provincia_i}
u_{k,p} ~ N(0, τ²)                          (efecto ALEATORIO de provincia)
```

- **Demografía** (sexo × edad × estudios, interacción completa, 42 celdas):
  efectos fijos, **sin penalizar** (identifican la estructura sociodemográfica).
- **Provincia**: intercepto **aleatorio** por provincia, con varianza τ² **común**
  estimada por **evidencia (aproximación de Laplace)** sobre una rejilla. El
  encogimiento de cada provincia hacia la media nacional lo fija el dato (τ² y la
  precisión de la provincia), no una constante impuesta a ojo.
- Ajuste: máximo del posterior (log-verosimilitud multinomial ponderada +
  prior gaussiano) con L-BFGS-B y gradiente analítico **verificado contra
  diferencias finitas** (error relativo máx. < 1e-6 en test sintético; la
  verificación destapó y corrigió dos bugs: signo del gradiente y tratamiento de
  la clase de referencia en el softmax).
- **τ² estimado**: τ = 1,0 en 2015-2016 y 1,5 en 2019-2023. En 2023 se comprobó
  con rejilla ampliada (hasta τ = 10) que 1,5 es un **óptimo interior** real, no
  un borde.

**Lectura**: el dato prefiere **encogimiento débil** — las provincias difieren de
verdad más de lo que explica el ruido de muestreo. Por eso el modelo jerárquico
queda **al mismo nivel que los efectos fijos** (MAE 1,030 vs 1,037 en Test A), no
mejor. Es un resultado honesto: la sofisticación multinivel no aporta aquí.

---

## 4. Backtest provincial — números REALES

Protocolo: `backtest_mrp.py` (idéntico al de `mrp.md`, **no** se toca
`pipeline/modelo/backtest.py`, que es el protocolo de referencia estatal).
Universo = 13 partidos modelados + Ciudadanos (peso histórico 2015-2019).
MAE provincial en % sobre voto válido, 52 provincias.

### 4.1 MAE global medio (5 elecciones)

| Método | Test A (nacional = real) | Test B (nacional = encuestas) |
|---|---|---|
| **MRP efectos fijos** | 1,0368 | 1,7875 |
| **MRP jerárquico** (nuevo) | **1,0299** | **1,7825** |
| MRP crudo (sin calibrar) | 1,7740 | 1,7740 |
| MRP anclado (exploratorio) | 0,8641 | 1,7163 |
| **Swing uniforme (mejor)** | **0,8328** | **1,7869** |

### 4.2 MAE por elección — Test A (objetivo nacional real)

| Elección | MRP ef. fijos | MRP jerárquico | MRP anclado | swing (mejor) | gana |
|---|---|---|---|---|---|
| 20D-2015 | 1,099 | 1,101 | 1,021 | 1,685 | MRP |
| 26J-2016 | 0,932 | 0,934 | 0,746 | **0,280** | swing |
| 28A-2019 | 1,133 | 1,121 | 0,995 | **1,077** | swing |
| 10N-2019 | 1,080 | 1,066 | 0,874 | **0,475** | swing |
| 23J-2023 | 0,940 | 0,928 | 0,685 | **0,648** | swing |

El swing gana **4 de 5**. El único triunfo claro del MRP es 2015, donde la base
del swing (2011) es tan antigua que arrastra Podemos/Ciudadanos mal anclados.
2019-04 es prácticamente un empate (1,121 jerárquico vs 1,077 swing).

### 4.3 MAE por partido (Test A, media de 5 elecciones)

Sólo la variante jerárquica frente a la de efectos fijos (el patrón por partido
es idéntico al descrito en `mrp.md` §4.2: el MRP brilla en territoriales
concentrados —ERC, JXCAT, PNV, EH BILDU, BNG, CUP, CC, NA+— y falla en los
grandes —PP, PSOE— porque la demografía no reconstruye su geografía).

---

## 5. La respuesta honesta al bloqueo del censo antiguo

`pipeline/mrp/sensitivity_censo.py` → `data/processed/mrp/sensitivity_censo.json`.

Se post-estratifica el **mismo** modelo con los **cuatro** censos disponibles
(2021-2024) para cada elección:

| Elección | MAE censo 2021 | 2022 | 2023 | 2024 | rango | brecha al swing |
|---|---|---|---|---|---|---|
| 20D-2015 | 1,0986 | 1,0989 | 1,1003 | 1,1006 | 0,002 | −0,586 |
| 26J-2016 | 0,9325 | 0,9332 | 0,9348 | 0,9355 | 0,003 | +0,653 |
| 28A-2019 | 1,1328 | 1,1326 | 1,1335 | 1,1339 | 0,001 | +0,056 |
| 10N-2019 | 1,0796 | 1,0791 | 1,0799 | 1,0805 | 0,001 | +0,605 |
| 23J-2023 | 0,9413 | 0,9408 | 0,9404 | 0,9401 | 0,001 | +0,294 |

**Rango medio entre censos: 0,002 pp.** Es decir: **el supuesto censal de §2 no
es el que decide el veredicto** en ninguna elección. La limitación (usar la
estructura 2021 para 2015-2019) es real y se declara, pero su efecto medido es
~100 veces menor que la brecha a batir. El bloqueo queda, por tanto,
**cuantificado y descartado como causa** — no forzamos números: medimos el
forzamiento y mostramos que es inocuo.

> Lo que **no** se puede hacer honestamente: un backtest 2015-2019 con el censo
> 2011 real por edad × estudios, porque esa tabla no existe con descarga
> provincial. Se declara como limitación de fuente, no se simula.

---

## 6. Comparación con el baseline de producción (29N)

`pipeline/mrp/compare_baseline_29n.py` → `compare_baseline_29n.json`.
Se reparten escaños por **D'Hondt** (umbral legal 3 % provincial) sobre las
cuotas provinciales del MRP (crudas y calibradas al forecast) y se comparan con
`seats.json` (swing + 10.000 simulaciones).

- Suma de escaños: MRP calibrado **350** (coherente) · baseline 350.
- **MAE de escaños por provincia-partido**: MRP calibrado **0,141** · crudo 0,264.
- Nacional (MRP calibrado / baseline escenario central):

| | PP | PSOE | VOX | SUMAR | ERC | JXCAT | PNV | EH BILDU | BNG | NA+ |
|---|---|---|---|---|---|---|---|---|---|---|
| MRP calibrado | 138 | 112 | 72 | 9 | 4 | 5 | 4 | 5 | 1 | 0 |
| baseline (central) | 138 | 109 | 68 | 9 | 7 | 5 | 4 | 7 | 2 | 1 |

(El `central_escenario` de `seats.json`. Por medias: PP 136,5 · PSOE 106,4 ·
VOX 66,8 · SUMAR 15,0 · ERC 5,8 · EH BILDU 7,1 · BNG 1,6 · NA+ 1,1.)

Como ambos están calibrados **al mismo objetivo nacional** (el forecast estatal),
la diferencia es **puramente provincial**: el MRP concentra algo más en PSOE/VOX
y menos en los territoriales pequeños. La discrepancia es pequeña (~0,14 escaños
por provincia-partido), es decir, **el reparto demográfico cambia poco el mapa de
escaños** — lo que refuerza que el problema no es la demografía.

---

## 7. Recomendación

**El MRP no está listo para considerar su entrada al modelo provincial.** No por
falta de acabado —el prototipo está completo, verificado y documentado— sino por
**evidencia**: no bate al swing uniforme en ninguna prueba, y las dos palancas
que se han probado para mejorarlo no mueven la aguja:

1. **Darle la estructura demográfica fina** (censo por sexo × edad × estudios):
   ya está; es justamente la que no reconstruye la geografía del voto grande.
2. **Hacerlo multinivel de verdad** (efecto aleatorio de provincia, τ² estimado):
   hecho; queda al mismo nivel que los efectos fijos.
3. **Anclarlo al voto anterior** (`mrp_anclado`, recibe la elección previa): es lo
   único que lo pone a la par del swing — pero entonces el mérito es del ancla,
   que es *exactamente lo que ya hace el swing*.

**Qué le falta para ser candidato de verdad** (en orden de evidencia):

1. **Elasticidades de swing por provincia** estimadas de microdatos de panel
   (quién cambia de voto y dónde), para modelar desviaciones provinciales del
   swing y no sólo el reparto demográfico. Es la única palanca con respaldo en
   los datos.
2. **Más microdato estatal reciente** para el 29N (la microdata CIS de voto
   termina en 2025-04) y, si se puede, **microdato de panel**.
3. **Censo 2011 provincial por edad × estudios** — hoy inexistente en formato
   descargable; mejoraría la validez formal del backtest antiguo, aunque §5
   muestra que su efecto es despreciable.

**Qué conservar del trabajo**:
- `poststrat.json` (con la variante jerárquica incluida) da el **sesgo
  demográfico** de la muestra CIS frente al censo — útil para explicar en la web
  por qué se post-estratifica, sin usarlo como método primario.
- `backtest_mrp.json` y `sensitivity_censo.json` acotan **el techo real** del
  reparto demográfico provincial (~1,0 pp de MAE) frente al del swing (~0,83 pp).
- Regla del proyecto: un candidato que no mejora se documenta y se descarta, sin
  `seats_mrp.json` ni artefactos que compitan con la producción.

---

## 8. Reproducir

```bash
/root/.venvs/29n-mrp/bin/python pipeline/mrp/fetch_censo_ine.py     # censo_cells.csv + censo_meta.json
/root/.venvs/29n-mrp/bin/python pipeline/mrp/backtest_mrp.py        # backtest_mrp.json  (~40 s sin jerárquico; ~6,5 min con jerárquico)
/root/.venvs/29n-mrp/bin/python pipeline/mrp/sensitivity_censo.py   # sensitivity_censo.json  (~35 s)
/root/.venvs/29n-mrp/bin/python pipeline/mrp/poststrat_29n.py       # poststrat.json (incluye variante jerárquica)
/root/.venvs/29n-mrp/bin/python pipeline/mrp/compare_baseline_29n.py # compare_baseline_29n.json
/root/.venvs/29n-mrp/bin/python pipeline/mrp/test_coherence.py      # 5 tests
```

El MRP jerárquico no usa MCMC: cada ajuste es un L-BFGS-B determinista, así que
el backtest completo es reproducible en minutos.

---

## 9. Siguiente paso

1. **No** integrar el MRP en el modelo provincial. Mantener el swing uniforme.
2. Si se quiere mejorar la predicción provincial, abrir una línea de **I+D de
   elasticidades de swing por provincia** (microdatos de panel), no de más
   estructura demográfica.
3. Publicar, si interesa, el contraste demográfico en la web **como contraste**
   (igual que `forecast_state.timesfm.json`), nunca como método primario.

---

## 10. Nota de alcance (árbol de trabajo compartido)

Durante esta sesión, el árbol de git contiene cambios **ajenos** que no he hecho
ni tocado (mtimes 06:57-07:00, anteriores a mis escrituras de 07:07-07:16):
`pipeline/modelo/forecast.py`, `pipeline/modelo/calibracion.py`,
`data/processed/modelo/{seats,forecast_state}.json`, `web/src/data/*.json`,
`web/sync-data.py`, `docs/notes/{calibracion-intervalos,ingesta-1610}.md`. Se
preservan tal cual. Mis escrituras se limitan a `pipeline/mrp/`,
`data/processed/mrp/` y este documento.
