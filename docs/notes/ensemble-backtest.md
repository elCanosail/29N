# Prototipo bayesiano dinámico + ensemble — backtest comparativo (29N)

Fecha: 2026-10-16 · Alcance: `pipeline/ensemble/`, `data/processed/ensemble/`,
este informe. **Sin commits ni push.** No se modifica `pipeline/modelo/backtest.py`
ni `forecast.json`, `seats.json`, `sync-data.py` ni `web/src/`.

Objetivo: implementar y evaluar un **miembro bayesiano dinámico** (estado
latente + filtro de Kalman) y un **ensemble 50/50** con el **modelo vivo**
(baseline), reutilizando el protocolo de backtest existente. El ensemble solo
pasaría a producción si **bate el MAE del modelo vivo** en el backtest.

Ejecución reproducible:

```bash
/root/.venvs/29n/bin/python pipeline/ensemble/backtest_ensemble.py
# -> data/processed/ensemble/backtest_ensemble.json
# semilla fija SEED=20261129; solo numpy (ya usado por el repo) + stdlib.
```

---

## 1. Cómo funciona el baseline (modelo vivo) y su backtest

**Baseline** (`pipeline/modelo/`): la serie mensual ponderada por partido es la
media de las observaciones con pesos `w = recencia × muestra × calidad`
(media-vida 45 d; `√(n/2000)`; `1/(1+MAE)`), con las correcciones
empirical-bayes de efecto de casa de `common.py` ya restadas. El **punto del
baseline es el último valor de la serie** ("última media ponderada"). Es el
método primario declarado en `forecast.py` porque TimesFM no lo mejora
(ver `docs/notes/modelo.md`).

**Protocolo de `backtest.py`** (reutilizado sin cambios):

- 5 elecciones: `2015-12-20, 2016-06-26, 2019-04-28, 2019-11-10, 2023-07-23`.
- Corte = día de la votación; **sin fuga**: solo observaciones anteriores.
- La serie es una **rejilla mensual truncada en el fin del mes anterior** al de
  la votación ⇒ las observaciones del **mes de la elección quedan fuera**.
- Métrica: **MAE sobre % de voto válido** (base completa, sin renormalizar),
  contabilizado solo donde el partido supera 0,1 % de voto real. n = 59
  observaciones partido×elección.

### Hallazgo de alineación (importante)

La primera implementación filtraba las observaciones hasta el **día** de la
votación. Eso introducía información que el baseline **no** usa (el mes
electoral) y, con ella, artefactos de datos del CIS (filas duplicadas del mismo
estudio, p. ej. tres valores de la familia SUMAR en 2019-04: 2,74/4,93/2,70).
Resultado intermedio (corregido): MAE bayesiano 1,589 pp. Al **alinear el corte
de información** con el del baseline (primer día del mes electoral), el
bayesiano baja a **1,270 pp** y el ensemble a **1,227 pp**. El corte alineado
es el correcto para comparar.

---

## 2. Miembro bayesiano dinámico

Estado latente `x_t` = intención de voto (% sobre válido) por partido, **random
walk** con volatilidad `σ = 0,15 pp/√día`:

```
x_t = x_{t-1} + w_t,     w_t ~ N(0, σ²·Δt·I_K)
y_i = x_{t_i}[p] + h_c + ε_i,   ε_i ~ N(0, τ_i²)
```

- `τ_i` del tamaño muestral con **inflación de diseño**: `τ = max(0,30 ;
  deff·100·√(p̂(1−p̂)/n))`, `deff = 1,7` (rango objetivo 1,5–2), suelo 0,30 pp.
- `h_c` = **efecto de casa residual** como estado constante, prior centrado en
  0 (`σ_h = 1,0 pp`). La **corrección EB de `common.py` se reutiliza** antes
  (los valores de `Observations` ya vienen corregidos), así que `h_c` recoge el
  sesgo de casa que queda — sin duplicar la lógica. El shrinkage hacia la media
  de casas es el del propio filtro (cociente de varianzas); tras filtrar se
  recentra `h` a media cero entre casas y se devuelve la media absorbida a `x`
  (invariante en `y = x + h`), garantizando la identificabilidad del nivel.
  En las 4 elecciones de casa única (solo CIS) el efecto queda en 0 (no es
  estimable con una sola casa); en 2023, con 5 casas, se estiman efectos
  pequeños (40dB +0,49 · CIS +0,01 · GAD3 −0,44 · Imop −0,01 · Sociometrica −0,33 pp).
- Sin MCMC, sin dependencias nuevas (numpy + stdlib).
- **Forecast** = `x_T` filtrado en el corte, propagado a la fecha electoral con
  la misma `σ` (la **varianza** suma `σ²·Δt`; el **punto** no cambia:
  random walk sin deriva).

Hiperparámetros: `σ = 0,15 pp/√día`, `deff = 1,7`, `τ_floor = 0,30 pp`,
`σ_h = 1,0 pp`, `P0 = 25 pp²` (varianza inicial difusa).

---

## 3. Ensemble 50/50

- **Punto** = media aritmética de los dos miembros: `m_e = 0,5·m_bayes + 0,5·m_base`.
- **Intervalos** = cuantiles de la **mezcla** de las dos predictivas
  `F_e(z) = 0,5·Φ((z−m_b)/s_b) + 0,5·Φ((z−m_base)/s_base)`, resueltos por
  bisección (determinista).
- **Aproximación del baseline**: en el backtest el baseline **solo da punto**.
  Sus intervalos se construyen con la **SD empírica de sus errores por partido**,
  con la definición exacta del modelo vivo (`forecast.party_error_sd`): desviación
  muestral del partido si n≥2, SD agrupada si n<2, suelo 0,10 pp. Es una
  aproximación **en muestra** (documentada); para un control honesto se reporta
  además `ensemble_loo`, con la SD del baseline estimada **fuera** de la elección
  evaluada.

---

## 4. Resultados — MAE (% voto válido, n = 59)

| Método | MAE global (pp) |
|---|---|
| **baseline (modelo vivo)** | **1,234** |
| bayesiano dinámico | 1,270 |
| **ensemble 50/50** | **1,227** |

Δ ensemble − baseline = **−0,007 pp** (el ensemble mejora por 0,007 pp).

**MAE por partido** (baseline / bayesiano / ensemble; n = elecciones con real ≥ 0,1 %):

| Partido | baseline | bayes | ensemble | n |
|---|---|---|---|---|
| SUMAR | 4,77 | 5,24 | 4,72 | 5 |
| PSOE | 3,49 | 3,36 | 3,43 | 5 |
| PP | 2,29 | 2,35 | 2,32 | 5 |
| VOX | 2,05 | 2,03 | 2,04 | 5 |
| ERC | 0,51 | 0,53 | 0,52 | 5 |
| PACMA | 0,44 | 0,43 | 0,43 | 5 |
| CUP | 0,32 | 0,31 | 0,31 | 2 |
| JXCAT | 0,26 | 0,27 | 0,27 | 5 |
| BNG | 0,18 | 0,19 | 0,19 | 4 |
| EH BILDU | 0,18 | 0,19 | 0,19 | 5 |
| CC | 0,16 | 0,16 | 0,16 | 5 |
| NA+ | 0,14 | 0,15 | 0,15 | 3 |
| PNV | 0,05 | 0,04 | 0,04 | 5 |

Los 5 grandes concentran el error (SUMAR: el descalabro de Podemos 2015-2019;
2023-07: PP bayes 34,95 vs real 33,06). El bayesiano gana a PSOE/VOX/PNV y
pierde en SUMAR/PP/JXCAT respecto al baseline; el ensemble queda entre los dos,
como era de esperar de una media.

### Significancia — bootstrap emparejado (B = 10.000, semilla fija)

Diferencia de MAE `baseline − ensemble` (positivo ⇒ ensemble mejor):

| Comparación | Δ media | SD | IC95 | P(mejora) |
|---|---|---|---|---|
| baseline − **ensemble** | **+0,006 pp** | 0,044 | **[−0,085 ; +0,093]** | 0,57 |
| baseline − bayes | −0,037 pp | 0,068 | [−0,191 ; +0,069] | 0,34 |

El IC95 de la mejora **incluye 0**: la ventaja del ensemble (0,007 pp) está muy
por debajo del ruido de muestreo. Con n = 59 y σ de errores ≈ 2,8 pp, es
**estadísticamente indistinguible** del baseline.

---

## 5. Cobertura de intervalos (95 % y 80 %)

| Método | 95 % | 80 % |
|---|---|---|
| baseline (definición del modelo vivo, en muestra) | 89,8 | 76,3 |
| baseline LOO (honesta) | 81,4 | 74,6 |
| bayesiano | 88,1 | 81,4 |
| ensemble (mezcla) | 94,9 | 91,5 |
| ensemble_loo (SD del baseline fuera de muestra) | 93,2 | 91,5 |

Cobertura por elección (ensemble / baseline):

| Elección | baseline 95/80 | bayes 95/80 | ensemble 95/80 |
|---|---|---|---|
| 2015-12-20 | 80,0 / 70,0 | 90,0 / 80,0 | 90,0 / 90,0 |
| 2016-06-26 | 90,9 / 81,8 | 81,8 / 72,7 | 90,9 / 90,9 |
| 2019-04-28 | 91,7 / 66,7 | 91,7 / 83,3 | 100,0 / 91,7 |
| 2019-11-10 | 84,6 / 69,2 | 84,6 / 76,9 | 92,3 / 84,6 |
| 2023-07-23 | 100,0 / 92,3 | 92,3 / 92,3 | 100,0 / 100,0 |

Lectura: las bandas del baseline **en muestra** (89,8 % / 76,3 %) están algo
por debajo de lo nominal y, fuera de muestra (LOO), claramente por debajo
(81,4 % / 74,6 %) — sus intervalos son optimistas. El bayesiano es algo mejor en
el 80 %. El ensemble, al mezclar una banda ancha con una honesta, sobrecubre
(94,9 % / 91,5 %), pero incluso con la versión honesta `ensemble_loo` mantiene
93,2 % / 91,5 %: sus intervalos son algo conservadores, no mal calibrados.

---

## 6. Sensibilidad al hiperparámetro σ (robustez)

| σ (pp/√día) | MAE bayes | MAE ensemble | ¿ensemble bate al baseline? |
|---|---|---|---|
| 0,05 | 1,297 | 1,249 | **No** |
| 0,10 | 1,208 | 1,221 | Sí |
| **0,15 (primario)** | 1,270 | **1,227** | Sí |
| 0,25 | 1,339 | 1,235 | No |
| 0,40 | 1,377 | 1,251 | No |

El veredicto **depende de σ**: el ensemble solo bate al baseline en una banda
estrecha (σ ≈ 0,10–0,15) y pierde fuera de ella. Puesto que σ se eligió *a
priori* (0,15, documentado) y no se tocó tras ver resultados, el veredicto
primario se mantiene; pero la falta de robustez confirma que la ventaja no es
real.

---

## 7. Veredicto explícito

> **¿Bate el ensemble al modelo vivo?** Sobre la configuración fijada *a priori*
> (σ = 0,15), **sí en el punto por 0,007 pp** (MAE 1,227 vs 1,234), pero el
> bootstrap emparejado da IC95 **[−0,085 ; +0,093]** — **incluye el 0** — y el
> resultado **cambia de signo** al mover σ. Es un **empate estadístico**, no una
> mejora.

**Recomendación: NO promover el ensemble a producción con esta evidencia.**
No hay ganancia medible y añade un modelo y una σ más que mantener. Se
recomienda conservar el **baseline** como punto primario. El ensemble y el
bayesiano quedan como contraste reproducible; el bayesiano aporta, eso sí,
**intervalos intrínsecos mejor calibrados** en el 80 % que los del baseline, y
la mezcla es ligeramente conservadora (cobertura ≈ 93–95 % frente al ~81 % LOO
del baseline) — pero eso no basta para justificar el cambio.

---

## 8. Datos, límites y advertencias (sin maquillaje)

- **Datos suficientes**: el backtest completo se ejecuta con los datos
  disponibles (421 observaciones; 42–219 por elección). Antes de 2019 solo hay
  **CIS** (una sola casa), así que el efecto de casa no es estimable en esas 4
  citas; el modelo lo fija a 0 (correcto con una sola casa).
- **Artefacto de datos CIS**: hay **filas duplicadas** por estudio y partido
  (la familia SUMAR pliega IU/PODEMOS/Unidas Podemos). El baseline las promedia
  con peso; el Kalman las trata como medidas independientes (ligeramente
  sobreconfiado). El corte de información alineado neutraliza las que caían en
  el mes electoral.
- **Baseline con solo punto**: sus intervalos en el backtest son en muestra;
  se documenta y se contrasta con LOO.
- **σ y deff**: elegidos a priori; la sensibilidad a σ se reporta explícitamente.
- **Métrica**: 1 mes vista (misma estructura que el 29N). Base completa sin
  renormalizar; cobertura del universo modelado 83,2 / 85,4 / 81,6 / 88,5 / 98,0 %
  (en 2015-2019 Ciudadanos queda fuera del modelo, irrelevante para 29N).
- **Sin dependencias nuevas**: solo `numpy` y stdlib.

## 9. Salidas

- `pipeline/ensemble/kalman.py` — miembro bayesiano dinámico (Kalman).
- `pipeline/ensemble/ensemble.py` — mezcla 50/50 y cuantiles por bisección.
- `pipeline/ensemble/backtest_ensemble.py` — runner comparativo (protocolo de
  `backtest.py` copiado por aislamiento; el original intacto).
- `data/processed/ensemble/backtest_ensemble.json` — resultados completos
  (MAE por partido y por elección, bootstrap, cobertura, sensibilidades,
  efectos de casa, intervalos por caso).
