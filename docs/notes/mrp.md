# Fase 4-c (segundo uso) — MRP provincial (29N)

Fecha: 2026-10-15 · Alcance de escritura: `pipeline/mrp/`, `data/processed/mrp/`,
este documento. Todo lo demás es **solo lectura** (`data/processed/modelo/`,
`pipeline/modelo/`, `pipeline/microdatos/`, `data/raw/cis/`, `web/`). Sin commits
ni push.

Objetivo: construir un **MRP** (Multilevel Regression and Post-stratification) y
comprobar con un backtest honesto si mejora la predicción **provincial** del
**swing proporcional uniforme** que hoy produce `data/processed/modelo/seats.json`.

---

## 0. Resumen ejecutivo

| | MAE provincial global (52 prov. × universo, 5 elecciones) |
|---|---|
| **MRP especificado** (demografía + provincia) | **1,037 pp** |
| **MRP anclado** (variante exploratoria, + recuerdo de voto) | **0,864 pp** |
| **Swing uniforme** (mejor variante por elección) | **0,833 pp** |

- **Test A** (objetivo nacional = resultado real, aísla la geografía):
  swing **0,833** < MRP anclado 0,864 < MRP 1,037.
- **Test B** (objetivo nacional = encuestas, previsión sin fuga):
  MRP anclado **1,716** < swing **1,787** < MRP 1,788.

**Veredicto: el MRP no bate al swing uniforme.** El modelo *especificado* pierde
en las dos pruebas. La variante anclada, que recibe la misma información que el
swing (resultados de la elección anterior), queda en tablas: gana el Test B por
0,07 pp y pierde el Test A por 0,03 pp — dentro del ruido (n=5 elecciones).
**No se adopta y no se genera `seats_mrp.json`.** El swing sigue siendo el
método de producción; se documenta todo el proceso y se conserva la
post-estratificación reproducible del 29N (`poststrat.json`) para contraste.

Por qué pierde (dato, no opinión): el error del MRP se concentra en los
**partidos grandes** (PP, PSOE, VOX, SUMAR). El swing parte de la geografía real
de la elección anterior, que es un predictor fortísimo de la siguiente; la
demografía sola no reconstruye esa geografía. En partidos territoriales
concentrados (ERC, PNV, EH BILDU, CUP, CC, NA+) el MRP sí es competitivo
(MAE ≤ 0,35 pp).

---

## 1. Datos

### 1.1 Denominadores censales (INE tabla 66600)

`pipeline/mrp/fetch_censo_ine.py` descarga y reduce la tabla **66600** de INEbase
(«Población de 15 y más años por sexo, edad año a año, nivel de estudios detallado
y provincia», serie **2021-2024**):

- API JSON Tempus3 (`servicios.ine.es/wstempus/js/ES/DATOS_TABLA/66600`): **la
  tabla completa se rechaza por volumen**
  (`{"status":"No puede mostrarse por restricciones de volumen"}`), documentado en
  `censo_meta.json`.
- Fallback canónico: `www.ine.es/jaxiT3/files/t/csv_bdsc/66600.csv` (mismos datos
  en la misma desagregación; el fichero se sirve con *Content-Type*
  `ISO-8859-15` pero está en **UTF-8 con BOM** — verificado).
- Licencia: aviso legal INE (reutilización con atribución, sin coste).

Reducción a celdas `provincia × sexo × grupo de edad × grupo de estudios × periodo`:

- **Edad**: 7 grupos (`18-24, 25-34, 35-44, 45-54, 55-64, 65-74, 75+`). Se
  descartan los 15-17 años (la microdata CIS es 18+).
- **Estudios**: 10 categorías censales (CNED-2014) → 3 grupos:
  - `BAJO`: sin estudios + educación primaria;
  - `MEDIO`: 1ª etapa secundaria + 2ª etapa general + 2ª etapa profesional/postsecundaria;
  - `ALTO`: FP superior + grados/los licenciados + máster + doctorado.

Control: 8.736 celdas (52 × 2 × 7 × 3 × 4 periodos), población 18+ **2024 =
40.594.509** (coincide con el patrón publicado).

### 1.2 Microdatos CIS

`data/processed/microdatos/individual.parquet` (532.498 entrevistas, 55 estudios).
Se usa `intencion_voto` (y `recuerdo_voto` en la variante anclada), `peso`,
`provincia` (código INE 1-52), `edad`, `sexo`, `estudios`. Los estudios de ámbito
no estatal (Andalucía, Cataluña…) quedan **fuera**: usan otra base y
sobre-representan a los partidos territoriales.

### 1.3 Resultados reales

`data/processed/interior/results_provincial.jsonl` + `elections.json`, con la
canonicalización del proyecto (`pipeline/sesgo/party_canon.py`, leída — no
modificada). El módulo `mrp_core.Interior` reimplementa la lectura para **no
depender de `pipeline/modelo/`**.

---

## 2. Supuesto censal del backtest (documentado y con limitación)

La serie 66600 con las **tres** dimensiones (sexo × edad × estudios) por provincia
**arranca en 2021**. El Censo 2011 existe, pero sólo en el sistema interactivo del
INE (`ine.es/censos2011_datos/`), sin CSV/API descargable por provincia y con otra
armonización de estudios.

**Supuesto**: el backtest 2015-2023 se post-estratifica con la estructura
demográfica de **2021** (la más cercana disponible en la serie), y el 29N con la
de **2024**.

**Limitación que introduce**: entre 2011 y 2021 (y más entre 2011 y 2024) el nivel
educativo de la población subió mucho. Reproytectar la estructura 2021 al pasado
sobrepondera a los más formados. El efecto va sobre todo por la celda
edad × estudios, que es la que cambia. Alternativa descartada: el Padrón continuo
(tabla 03002 / ECP) da provincia × edad × sexo para cualquier año 1998-2022, pero
**no** nivel de estudios, que es justamente la dimensión con más deriva temporal.

Sensibilidad disponible: cambiar `censo` en `ELECTIONS` de `backtest_mrp.py` (p. ej.
2023 para 23J, ya aplicado) y recalcular.

---

## 3. Modelo

`pipeline/mrp/mrp_core.py`.

### 3.1 Modelo especificado (MRP pragmático)

- **Regresión multinomial** (`sklearn.linear_model.LogisticRegression`,
  `solver="lbfgs"`, `C=1,0`, L2) de la clase de intención de voto sobre:
  - **demografía**: interacción completa `sexo × grupo de edad × grupo de estudios`
    (42 categorías, one-hot);
  - **efecto provincial**: 52 dummies (one-hot). Es el papel que en un MRP
    canónico juega el efecto **aleatorio** de área: la penalización L2 **encoge**
    las provincias con poca muestra hacia la media nacional. Se eligió fijo+L2
    sobre aleatorio-MCMC por reproducibilidad (segundos, no horas) y porque con
    ~1.000-2.000 entrevistas por estudio no hay señal suficiente para calibrar una
    distribución jerárquica completa.
- **Clases**: los 13 partidos modelados (+ `CIUDADANOS` en el backtest, por peso
  histórico) y el residual no-partidista (`ABSTENCION`, `NO_DECIDIDO`, `BLANCO`,
  `NULO`, `OTROS`). Pesos de encuesta = `peso` individual.
- **Post-estratificación**: para cada provincia,
  `cuota_k = Σ_celdas N_celda · P(k | demografía, provincia) / Σ_celdas N_celda · P(vota a partido del universo)`,
  con `N_celda` del censo. Normalizado al universo modelado (suma = 100 por
  provincia).

### 3.2 Variante simple (para justificar o descartar la sofisticación)

`cell_means_poststrat()`: medias de celda ponderadas con encogimiento hacia la
media demográfica nacional (`λ = n_eff/(n_eff+50)`), post-estratificadas igual.
Es la «logística + pesos de celda» del enunciado, sin regresión.

### 3.3 Variante anclada (exploratoria)

`fit_mrp_anchored()`: añade **recuerdo de voto** (`recuerdo_voto`) como covariable,
de modo que el MRP reciba la misma información que el swing (la elección
anterior). La post-estratificación necesita `P(recuerdo | provincia)`, que se toma
de los **resultados reales de la elección anterior** (`Interior`), combinada con
el censo bajo el supuesto explícito de independencia demo × recuerdo dentro de la
provincia. Es el techo razonable del MRP: si ni así bate al swing, el veredicto es
sólido.

---

## 4. Backtest provincial

`pipeline/mrp/backtest_mrp.py`. Para cada elección se entrena el MRP **solo con
microdatos anteriores a la votación** (ventana de 3 años, estudios estatales) y se
compara contra la **elección general anterior** («swing») y los **resultados
reales**.

### 4.1 Metodología de comparación

- **Universo**: los 13 partidos modelados + Ciudadanos (el backtest abarca 2015,
  año en que Cs valía un 14 %; excluirlo distorsionaría la renormalización).
  ⚠️ La predicción, el swing y la realidad se miden **en la misma base**, así que
  el veredicto no depende de esa elección de universo.
- **Swing uniforme** (idéntico al del producto): `v_{p,k} ∝ base_{p,k} · r_k`,
  `r_k = objetivo_k / base_nacional_k`, renormalizado por provincia. Base = elección
  general anterior; calibrado por punto fijo al objetivo nacional (misma mecánica
  que `pipeline/modelo/provincial.py`, reimplementada localmente para no tocar
  `pipeline/modelo/`).
- **`swing_fix`**: corrige el artefacto de los **partidos nuevos**. Si un partido
  no existía en la base (VOX en 2016, Cs en 2011), `r = objetivo/0` y el swing lo
  deja a cero; se añade una base mínima uniforme de 0,1 pp. Sin este arreglo el
  swing es injustamente malo en 2015 y 2019-04 (el producto real no lo sufre
  porque su base 23J contiene a todos los partidos). **El competidor es el mejor
  de `swing` y `swing_fix` en cada elección.**
- **Dos pruebas**:
  - **Test A** — ambos métodos calibrados al **resultado nacional real**: mide
    sólo el reparto provincial (geografía pura).
  - **Test B** — ambos calibrados al **nacional directo de las mismas encuestas**
    de entrenamiento: previsión sin fuga, comparación como para como.

### 4.2 Resultados

MAE global (%) por elección. Test A / Test B. `anc` = MRP anclado.

| Elección | MRP | **MRP anc** | swing (mejor) | MRP | **MRP anc** | swing (mejor) |
|---|---|---|---|---|---|---|
| 20D-2015 | 1,099 | **1,021** | 1,685 | 1,340 | **1,396** | 2,049 |
| 26J-2016 | 0,932 | 0,746 | **0,280** | 1,365 | 1,369 | **1,346** |
| 28A-2019 | 1,133 | 0,995 | **1,077** | 2,331 | 2,141 | **2,188** |
| 10N-2019 | 1,080 | 0,874 | **0,475** | 2,264 | 2,176 | **2,028** |
| 23J-2023 | 0,940 | 0,685 | **0,648** | 1,637 | 1,499 | **1,324** |
| **Media** | **1,037** | **0,864** | **0,833** | **1,788** | **1,716** | **1,787** |

El swing gana **4 de 5** elecciones en ambas pruebas. El único triunfo claro del
MRP es **2015**, donde la base (2011) es tan antigua que el swing arrastra
Podemos/Ciudadanos mal anclados. Es un caso real, pero explica por qué el MRP no
destaca en el resto: en 2016-2023 la base del swing es reciente y buena.

MAE por partido (media de las 5 elecciones), Test A:

| Partido | MRP | MRP anc | swing | swing_fix |
|---|---|---|---|---|
| PP | 3,72 | **2,59** | 2,94 | 2,27 |
| PSOE | 3,37 | 2,54 | 2,84 | **2,46** |
| VOX | 1,35 | **1,25** | 1,62 | 1,31 |
| SUMAR | 2,41 | **2,24** | 3,23 | 2,77 |
| CIUDADANOS | 1,32 | 1,52 | 3,27 | **1,24** |
| ERC | 0,33 | 0,20 | **0,22** | 0,29 |
| JXCAT | 0,26 | 0,20 | **0,15** | 0,18 |
| PNV | **0,26** | 0,25 | 0,30 | 0,37 |
| EH BILDU | 0,25 | 0,26 | **0,21** | 0,27 |
| BNG | 0,14 | 0,12 | **0,08** | 0,21 |
| CUP | **0,06** | **0,04** | 0,12 | 0,29 |
| CC | 0,32 | 0,22 | **0,11** | 0,20 |
| NA+ | 0,16 | 0,14 | **0,12** | 0,26 |
| PACMA | 0,55 | 0,54 | **0,17** | 0,13 |

Lectura: el MRP **no** es competitivo con los grandes (PP/PSOE), pierde también
con PACMA y CC, y sí es bueno con los territoriales concentrados. El anclaje
mejora mucho a los grandes (PP 3,72→2,59) pero **no basta**.

`backtest_mrp.json` incluye, por elección: estudios y filas de entrenamiento,
nacional real / de encuestas / MRP crudo, MAE global, ponderado por votos, MAE de
partidos ≥ 1 % y MAE por partido de los 4 métodos × 2 pruebas.

### 4.3 Caveats del backtest

- **Fecha de trabajo gruesa**: en la microdata la fecha de trabajo viene con
  día 01 (`polls.jsonl`), así que el corte «estrictamente antes de la votación»
  es aproximado. El caso delicado es el estudio **3245** (europeas, 01-04-2019)
  en el backtest de 28A-2019: su campo pudo solaparse con el 28A. Quitarlo sólo
  puede **empeorar** al MRP, que ya pierde esa elección (2,331 vs 2,196 en Test B);
  el veredicto es robusto a ello.
- La ventana de 3 años mantiene fijo el nº de estudios por elección (2-8), con
  17k-85k filas de entrenamiento.
- Se incluyen todos los estudios estatales de la ventana, **incluidos** `7715` y
  `3416`, que el modelo estatal excluye de su serie por motivos de validación
  agregada (no de microdato). `7715` es una ola panel gemela de `3117`
  (sobre-pondera 2015, sin sesgo de nivel).
- MRP y swing comparten el **mismo objetivo nacional** en cada prueba; la
  diferencia medida es puramente de reparto provincial.

---

## 5. Post-estratificación del 29N y coherencia

`pipeline/mrp/poststrat_29n.py` → `data/processed/mrp/poststrat.json`.

- Corte 29-11-2026, ventana 3 años ⇒ 4 estudios de 2024-2025, 17.366 filas.
  (La microdata termina en 2025-04; el forecast estatal usa además encuestas
  privadas hasta 2026-10, que **no** entran aquí.)
- Censo 2024. Post-estratificación por provincia × sexo × edad × estudios
  (2.184 celdas).
- Nacional **crudo** del MRP frente al **objetivo** del forecast estatal
  (`data/processed/modelo/forecast_state.json`, solo lectura) y calibrado:

| | PP | PSOE | VOX | SUMAR | resto |
|---|---|---|---|---|---|
| MRP crudo | 28,9 | 38,8 | 11,6 | 13,4 | … |
| Calibrado al objetivo | 35,4 | 29,1 | 20,6 | 7,1 | … |
| Objetivo (forecast) | 35,4 | 29,1 | 20,6 | 7,1 | … |

  Es decir: el MRP crudo reproduce el sesgo clásico de los microdatos CIS
  (PSOE/izquierda altos, PP/VOX bajos). La calibración lo lleva al forecast, y a
  partir de ahí lo único que aporta es el **reparto provincial** — que es
  exactamente lo que el backtest dice que hace peor que el swing.

- `test_coherence.py` (5 tests, pasan, ejecutable directo y con pytest):
  1. cada provincia suma 100 % (crudo y calibrado);
  2. agregado provincial ponderado por votos = forecast estatal
     (**desviación máx 0,0098 pp** ≤ 0,1);
  3. 2.184 celdas censales (52 × 2 × 7 × 3);
  4. población censal 2024 = 40.594.509 y periodos {2021..2024};
  5. estructura del JSON comparable lado a lado con `seats.json`.

---

## 6. Veredicto

- **¿El MRP bate al swing uniforme?** **No.** El modelo especificado pierde en las
  dos pruebas (Δ +0,204 pp en Test A, +0,001 pp en Test B). La variante anclada
  empata (gana Test B por 0,07 pp, pierde Test A por 0,03 pp).
- **¿Se usa?** **No.** Se mantiene el swing uniforme como método de producción.
  **No se genera `seats_mrp.json`.** Regla del proyecto: la honestidad manda sobre
  el *branding*; igual que con TimesFM (fase 4), un candidato que no mejora se
  documenta y se descarta.
- **¿Sirve de algo?** Sí, tres cosas:
  1. mide el **techo real** del reparto demográfico provincial (~1,0 pp de MAE
     frente a ~0,83 del swing) y la cota de lo que aportaría mejorar el swing;
  2. `poststrat.json` da el sesgo demográfico de la muestra CIS vs censo, útil
     para la web (explicar por qué se post-estratifica);
  3. acota la discusión: la geografía del voto provincial es un fenómeno
     **persistente**, no demográfico; lo que predice bien el voto provincial es el
     voto provincial anterior.

---

## 7. Reproducir

```bash
python3 -m venv --system-site-packages /root/.venvs/29n-mrp
/root/.venvs/29n-mrp/bin/pip install -r pipeline/mrp/requirements.txt

/root/.venvs/29n-mrp/bin/python pipeline/mrp/fetch_censo_ine.py   # censo_cells.csv + censo_meta.json
/root/.venvs/29n-mrp/bin/python pipeline/mrp/backtest_mrp.py      # backtest_mrp.json  (~40 s)
/root/.venvs/29n-mrp/bin/python pipeline/mrp/poststrat_29n.py     # poststrat.json
/root/.venvs/29n-mrp/bin/python pipeline/mrp/test_coherence.py    # 5 tests
```

---

## 8. Siguiente paso

1. Si se quiere un gráfico lado a lado en la web, publicar el MRP **como
   contraste** (como `forecast_state.timesfm.json`), nunca como método primario —
   requeriría autorización explícita porque contradice el veredicto.
2. Si algún día interesa mejorar la predicción provincial, la vía con evidencia es
   **anclar al voto anterior** (swing con elasticidades por provincia estimadas de
   microdatos del panel), no añadir demografía.
3. Recalcular este backtest con el Censo 2011 si se consigue la tabla provincial
   por edad × estudios (mejoraría la validez del supuesto de §2 en 2015-2019).
