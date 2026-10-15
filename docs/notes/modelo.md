# Modelo de predicción del 29N (fase 4)

Fecha: 2026-10-15 · Alcance: `pipeline/modelo/`, `data/processed/modelo/`, este
informe. Sin commits ni push. Solo lectura sobre `pipeline/cis|encuestadores|interior|sesgo`
y sus datos. No se toca `web/`.

Objetivo: modelo de predicción completo del 29N (29-11-2026) — serie ponderada →
forecast estatal → backtest contra 5 elecciones → desagregación provincial por
swing → simulación D'Hondt (10.000 runs) → JSON para la web.

## Pipeline (orden de ejecución)

```bash
/root/.venvs/29n/bin/python pipeline/modelo/build_series.py   # serie mensual ponderada
/root/.venvs/29n/bin/python pipeline/modelo/backtest.py       # TimesFM vs baseline
/root/.venvs/29n/bin/python pipeline/modelo/forecast.py       # forecast estatal (lee backtest.json)
/root/.venvs/29n/bin/python pipeline/modelo/provincial.py     # swing + D'Hondt 10.000 runs
/root/.venvs/29n/bin/python pipeline/modelo/test_coherence.py # coherencia estatal-provincial
```

Ficheros: `common.py` (utilidades/canonicalización/serie), `build_series.py`,
`forecast.py`, `backtest.py`, `provincial.py`, `test_coherence.py`.

## 1. Serie mensual ponderada

Base de todo: **% sobre voto válido** (la base con que se reparten escaños).

- **CIS**: `data/processed/cis/polls.jsonl` publica voto directo **% sobre censo**;
  se reescala a válido dividiendo por `valid_base_censo/100` (Σ partidos
  reconocidos + en blanco), igual que `pipeline/sesgo/compute_house_effects.py`.
- **Privados**: `porcentaje` ya está sobre válido.
- **Pesos** por observación: `recencia × muestra × calidad`
  - recencia: media-vida **45 días** → `0.5^(Δdías/45)`;
  - muestra: `√(n/2000)`;
  - calidad: `1/(1+MAE)`. Privados: MAE 23J de `encuestadores/scoring.json`.
    CIS: MAE histórica del voto directo reescalado (**1,795 pp**), de
    `house_effects.json`.
- **Correcciones EB** (`house_effects.json`, `correccion = media_error·n/(n+5)`)
  restadas a cada observación según su casa y serie: CIS `micro_valid`,
  privados `privado`. Sin corrección para una casa/partido → 0.
- **Serie mensual** (rejilla 1977-06 → 2026-11, 594 puntos): valor en cada
  fin de mes = media ponderada de las observaciones con fecha ≤ fin de mes
  (ventana efectiva ~2 años por la exponencial); sin datos → arrastre del
  último valor (LOCF).

**Limpiezas documentadas** (todas en `series.json` → `meta`):

1. Estudios CIS que la fase 4-bis marcó `no_validada` (variable de voto mal
   normalizada): fuera → `1135, 1181, 1183, 1324, 1326, 1533, 2207, 3416, 7715, 7789`.
2. Encuestas de ámbito **no estatal** (CEO-Cataluña, `ambito="Cataluña"`) fuera:
   si no, ERC/JXCAT/CUP disparaban el forecast (ERC salía al 15 %).
3. Estudios privados con **publicación incompleta** (no dan los 4 grandes con
   suma ≥ 75 %): fuera → `40db-2023-07-08`, `40db-2025-09-28`, `40db-2026-10-08`
   (esta última sumaba 67,8 %: PP 20,5 / PSOE 23 / VOX 20,1 / SUMAR 4,2, cifras
   en otra base y discordantes con todas las demás de 2026), `imop-2023-05-29`,
   `imop-2023-07-11`.
4. **Familias**: el espacio de la izquierda estatal cambia de marca
   (IU → Podemos/Unidas Podemos → SUMAR); se modela como una sola familia
   (`SUMAR`) para evitar partidos fantasma que TimesFM extrapola con su último
   nivel caduco. La base provincial de 23J ya es SUMAR.
5. **NA+/UPN**: en 2023 Interior publica UPN como `u-p-n`, que la
   canonicalización mandaba a OTROS; se reasigna a NA+ (misma familia navarra)
   para que el partido tenga anclaje provincial.

Sanity check (serie vs resultado real de 23J, corte 23-07-2023):
PP 34,61 / 33,06 · PSOE 29,54 / 31,68 · VOX 12,10 / 12,38 · SUMAR 12,94 / 12,33.

## 2. Forecast estatal — **TimesFM vs baseline (veredicto honesto)**

- **TimesFM**: `google/timesfm-2.5-200m-pytorch`, backend PyTorch/CPU, zero-shot,
  1 serie por partido (13), `per_core_batch_size=13` (si no, serializa ×5,6),
  historia 594 pts, horizonte 1 mes (nov-2026; último dato 2026-10).
- **Baseline ingenuo**: última media ponderada (valor final de la serie).
- **Ensemble**: media de ambos.

### Backtest (sin fuga de datos: se entrena con observaciones anteriores a la votación)

5 elecciones: 20D-2015, 26J-2016, 28A-2019, 10N-2019, 23J-2023. Métrica: MAE
sobre **% de voto válido** (base completa, sin renormalizar; ver advertencia).

| Método | MAE (n=59) |
|---|---|
| baseline | **1,234 pp** |
| ensemble | 1,236 pp |
| TimesFM | 1,272 pp |

**Veredicto: TimesFM NO mejora al baseline.** El baseline gana por 0,038 pp —
empate estadístico con n=59 (σ de errores = 2,56 pp). Interpretación: la serie
es un promedio de encuestas ya casi óptimo a 1 mes vista; la extrapolación de
TimesFM añade ruido y no información. **Se usa el baseline como punto primario**
(regla del proyecto: la honestidad manda sobre el branding). TimesFM se publica
como contraste (`forecast_state.timesfm.json`).

MAE por partido (TimesFM / baseline / ensemble), n = elecciones contadas
(real ≥ 0,1 %):

| Partido | TimesFM | Baseline | Ensemble | n |
|---|---|---|---|---|
| PSOE | 4,04 | 3,49 | 3,73 | 5 |
| SUMAR | 4,19 | 4,77 | 4,34 | 5 |
| VOX | 2,82 | 2,05 | 2,43 | 5 |
| PP | 2,01 | 2,29 | 2,15 | 5 |
| ERC | 0,47 | 0,51 | 0,49 | 5 |
| PACMA | 0,42 | 0,44 | 0,43 | 5 |
| CUP | 0,35 | 0,32 | 0,34 | 2 |
| JXCAT | 0,28 | 0,26 | 0,26 | 5 |
| NA+ | 0,20 | 0,14 | 0,17 | 3 |
| BNG | 0,19 | 0,18 | 0,19 | 4 |
| EH BILDU | 0,18 | 0,18 | 0,18 | 5 |
| CC | 0,17 | 0,16 | 0,17 | 5 |
| PNV | 0,04 | 0,05 | 0,04 | 5 |

Detalle de `backtest.json`: incluye por elección `pred_timesfm`, `pred_baseline`,
`pred_ensemble`, `real`, errores e intervalo 80 % de TimesFM.

**Dónde está el error**: los 5 grandes concentran el MAE. 2015 es el peor caso
(SUMAR/UP real 24,4 % frente a ~8 % que daban las encuestas CIS de 2015: el
sesgo documentado del CIS con Podemos ese año). En 2016 y 2023 el baseline baja
de 1 pp porque hay encuestas privadas equidistantes. La **cobertura del universo
modelado** fue 83,2 / 85,4 / 81,6 / 88,5 / 98,0 % — en 2015-2019 Ciudadanos
(hasta ~14 %) queda fuera del modelo (irrelevante para 29N, donde Cs ≈ 0), lo
que no afecta al MAE por partido porque predicción y realidad van sobre la misma
base completa.

## 3. Predicción estatal 29N (método primario = baseline)

Punto + intervalo 80 % empírico (σ = desviación de los errores del baseline en
el backtest, por partido; no es una probabilidad calibrada de resultado).

| Partido | Punto | IC80 | (TimesFM) |
|---|---|---|---|
| PP | 35,4 | 31,9 – 38,9 | 35,2 |
| PSOE | 29,2 | 23,5 – 34,8 | 29,2 |
| VOX | 20,6 | 16,6 – 24,6 | 20,6 |
| SUMAR | 7,1 | 0,0 – 16,2 | 7,2 |
| ERC | 1,7 | 0,9 – 2,6 | 1,7 |
| EH BILDU | 1,6 | 1,3 – 1,9 | 1,6 |
| JXCAT | 1,5 | 1,3 – 1,8 | 1,5 |
| PNV | 1,0 | 0,9 – 1,2 | 1,0 |
| BNG | 0,8 | 0,4 – 1,1 | 0,8 |
| PACMA | 0,4 | 0,0 – 1,1 | 0,4 |
| CUP | 0,3 | 0,0 – 0,8 | 0,3 |
| NA+ | 0,3 | 0,0 – 0,6 | 0,3 |
| CC | 0,2 | 0,0 – 0,3 | 0,2 |

Renormalizado al universo modelado (suma = 100; cobertura 98,0 % de 23J). El
intervalo de SUMAR es enorme (±7,1 pp) porque su error histórico incluye el
descalabro de Podemos en 2015-2019: es honesto, no un defecto.

## 4. Desagregación provincial

Base: **23J-2023** (última cita completa), cuotas provinciales de Interior
(`results_provincial.jsonl`) renormalizadas al universo modelado.

**Swing proporcional uniforme**: `v_{p,k} ∝ base_{p,k} · r_k`, con
`r_k = target_k / base_nacional_k`, normalizado a 100 por provincia. Se descartó
el swing **aditivo** (mismo ±pp en todas las provincias): destruye a los
partidos de apoyo concentrado (para bajar a CC 0,5 pp en el agregado nacional
habría que restarle ~16 pp en Canarias). Los ratios calibrados van de
CC 0,28 (se hunde) a VOX 1,66 (se dispara) — coherente con la predicción.

**Calibración (normalización documentada)**: `Σ_k base_{p,k}·r_k ≠ 100` por
provincia, así que tras normalizar se ajustan los ratios con punto fijo
`r_k ← r_k·target_k/agg_k` hasta que el **agregado provincial ponderado por
votos** coincide con el forecast estatal en **≤ 0,1 pp**. Converge en 4
iteraciones (desviación 0,0085 pp).

## 5. Simulación D'Hondt (10.000 runs)

Por run: se muestrea la cuota nacional de cada partido de `N(punto, σ_backtest)`,
recorte a ≥0 y renormalización; swing calibrado; **D'Hondt por provincia**
(reutiliza `pipeline/interior/dhondt.py`, umbral 3 %, votos válidos reales de 23J).

Escaños (media e IC95 de la simulación):

| Partido | Media | IC95 | Escenario central |
|---|---|---|---|
| PP | 136,5 | 111 – 164 | 138 |
| PSOE | 106,4 | 72 – 137 | 109 |
| VOX | 66,8 | 42 – 93 | 68 |
| SUMAR | 15,0 | 0 – 50 | 9 |
| EH BILDU | 7,1 | 5 – 10 | 7 |
| ERC | 5,8 | 0 – 12 | 7 |
| JXCAT | 5,0 | 3 – 8 | 5 |
| PNV | 4,1 | 3 – 6 | 4 |
| BNG | 1,6 | 0 – 5 | 2 |
| NA+ | 1,1 | 0 – 3 | 1 |
| CUP | 0,6 | 0 – 3 | 0 |
| CC | 0,2 | 0 – 1 | 0 |
| PACMA | 0,0 | 0 – 0 | 0 |

`seats.json` detalla las 52 provincias × partido (media, IC95, `prob_ge1`).

## 6. Coherencia verificable

`test_coherence.py` (3 tests, pasan; ejecutable standalone y con pytest):

1. suma de medias de escaños = **350 ± 0,1** → 350,00;
2. en cada provincia, suma de medias = escaños de la provincia (dev. máx 0,01);
3. agregado provincial ponderado por votos = forecast estatal ≤ 0,1 pp por
   partido → **desviación máxima 0,0085 pp**.

## Advertencias y límites (sin maquillaje)

- **TimesFM no aporta** aquí: empate con el baseline (Δ 0,04 pp). Se publica
  igualmente como contraste reproducible.
- Los intervalos son **empíricos** (errores del backtest), no calibrados como
  probabilidad; el σ por partido se estima con n=2–5 elecciones → ruidoso.
- El backtest mide a **1 mes vista** (corte en el último mes completo antes de
  la votación), la misma estructura que el 29N (último dato 2026-10, objetivo
  2026-11). Las encuestas del propio mes de la elección quedan fuera por
  simetría entre métodos.
- **Swing proporcional uniforme**: no captura terremotos locales ni
  elasticidades provinciales distintas. Los intervalos provinciales de partidos
  pequeños (CUP, CC, PACMA) son anchos a propósito.
- Universo modelado = 13 partidos que cubren 98,0 % del voto válido de 23J;
  el residual no se reparte escaños (como en la realidad con los minoritarios).
- **CIS**: la serie histórica tiene huecos (1989-1996, 1996-2015) por descargas
  en curso; no afecta al forecast de 2026, que vive de los datos 2023-2026.

## Salidas

- `data/processed/modelo/series.json` (+ `series.csv`) — series mensuales y meta.
- `data/processed/modelo/forecast_state.json` (+ `.timesfm.json`) — predicción
  estatal (punto + cuantiles) y TimesFM crudo.
- `data/processed/modelo/backtest.json` — MAE por partido y por elección.
- `data/processed/modelo/seats.json` — escaños por provincia × partido.
