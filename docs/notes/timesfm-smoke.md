# Smoke test TimesFM — 29N

**Fecha:** 2026-10-15
**Máquina:** Elcano (Linux 6.8.0-101-generic, x86_64, 8 cores, 15 GiB RAM, CPU only)
**Script:** `pipeline/timesfm_smoke.py`
**Veredicto:** ✅ **TimesFM 2.5 (200M) funciona en CPU, con intervalos, y sirve como base del motor de predicción de 29N.** La forma real de la carga (≈10 series mensuales de ~600 puntos, horizonte 12) se ejecuta en ~1,6 s y ~2,2 GiB de RAM.

---

## 1. Entorno e instalación

Venv **fuera del repo** (según lo pedido): `/root/.venvs/29n` (Python 3.12.3).

```bash
python3.12 -m venv /root/.venvs/29n
/root/.venvs/29n/bin/pip install "timesfm[torch]"
```

**Resultado: instalación correcta, sin errores** (`EXIT=0`). Backend PyTorch, no hizo falta el intento con JAX.

| Paquete | Versión |
|---|---|
| timesfm | **3.0.2** |
| torch | **2.14.1+cu130** |
| numpy | 2.5.4 |
| huggingface_hub | 2.2.0 |
| Modelo | `google/timesfm-2.5-200m-pytorch` (200M params) |

Tamaños y coste de disco:

- venv con torch: **5,4 GiB** (los wheels de CUDA `nvidia-*` suman la mayor parte).
- Caché Hugging Face con el checkpoint: **883 MiB**.
- Disco tras la operación: 41 GiB libres de 150 GiB.

> Nota de eficiencia: no hay GPU (`torch.cuda.is_available() == False`), pero pip instaló el torch **cu130** con todos los paquetes CUDA. Un torch CPU-only reduciría el venv de ~5,4 GiB a ~1 GiB. Funciona igual; es solo coste de disco en CI/deploy.

`timesfm.__version__` no está definido (devuelve `unknown`); la versión de distribución (`3.0.2`) se obtiene con `importlib.metadata`.

---

## 2. Contrato de la API (verificado sobre 3.0.2, no supuesto)

```python
import timesfm
model = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
model.compile(timesfm.ForecastConfig(max_context=..., max_horizon=..., ...))
point, quantiles = model.forecast(horizon=12, inputs=[serie1, serie2, ...])
```

Puntos que **no son obvios** y que se leyeron en el código fuente:

- `point` tiene shape `(n_series, horizon)`.
- `quantiles` tiene shape `(n_series, horizon, **10**)`. El **punto es la columna 5**; las columnas **1..9 son los cuantiles 0.1..0.9**; la **columna 0 NO es un cuantil** (canal auxiliar). Origen: `timesfm_2p5_torch.py` → `return full_forecast[..., 5], full_forecast`.
  - Un etiquetado ingenuo de columnas `0..8 = 0.1..0.9` produce "cruces de cuantiles" **falsos**. Corregido y verificado.
- Los 9 cuantiles son un **intervalo central del 80%** (q0.1–q0.9), **no del 90%**. Para el 90% habría que usar q0.05–q0.95, que la cabecera continua no expone directamente (solo 0.1..0.9).
- `compile()` con backend PyTorch es prácticamente gratis (0,0 s): solo fija configuración y enlaza el decode.
- Restricciones de `ForecastConfig`: `max_context` se redondea a múltiplo de 32 (patch 32); `max_horizon` a múltiplo de 128 (patch de salida 128) y, con cabecera de cuantiles continuos, debe ser ≤ 1024; además `max_context + max_horizon ≤ 16384`.
- **`per_core_batch_size` importa mucho**: `global_batch_size = per_core_batch_size × nº dispositivos`. Por defecto es **1**, lo que serializa el lote aunque le pases 10 series.

---

## 3. Evidencia fresca (comandos y salidas reales)

### Comando principal

```bash
cd /root/.openclaw/workspace/projects/29n
/root/.venvs/29n/bin/python pipeline/timesfm_smoke.py \
    --years 50 --horizon 12 --n-series 10 --per-core-batch-size 32 --seed 7 \
    --json /tmp/29n_smoke_batch32.json
```

Serie de prueba: 10 series mensuales de 50 años (**600 puntos** cada una), escala 0–100 tipo intención de voto, con tendencia + estacionalidad anual (periodo 12) + ruido. Horizonte = 12 (un ciclo). Verificación de contrato al final.

### Tiempos y memoria (batch 32)

| Métrica | Valor |
|---|---|
| RAM antes de cargar | 0,50 GiB |
| **Carga del checkpoint** | **1,78 s** (caché local; 6,67 s la 1ª vez incluyendo descarga de 883 MiB) |
| RAM tras cargar | 2,23 GiB |
| Compilación | 0,0 s |
| `global_batch_size` | 32 |
| Warm-up | 2,29 s |
| **Inferencia del lote (10 series × 12 meses)** | **1,636 s → 163,6 ms/serie** |
| **RAM pico (RSS)** | **2,23 GiB** |

### Verificación de sanidad del resultado

```
CONTRACT CHECK: point==col5 dif=0.00e+00, crossings=0 -> OK
```

- `point_forecast == quantiles[:, :, 5]` con diferencia máxima **0,0** (el punto es exactamente la mediana).
- **0 cruces** de cuantiles (columnas 1..9 monótonas) con `fix_quantile_crossing=True`.

### Salida de la serie 0 (últimos observados y forecast con intervalos)

```
últimos 4 observados : 39.80  41.46  43.50  42.52

mes   point(q0.5)   q0.1    q0.9
 1      43.41      42.26   44.46
 2      41.96      40.77   43.07
 3      40.65      39.54   41.71
 4      39.35      38.38   40.38
 5      38.11      37.14   39.16
 6      37.44      36.45   38.42
 7      37.14      36.20   38.18
 8      37.81      36.82   38.86
 9      39.45      38.46   40.49
10      41.71      40.72   42.76
11      43.30      42.33   44.33
12      44.10      43.05   45.23
```

El forecast **reproduce la forma estacional anual** (baja y vuelve a subir dentro del ciclo de 12 meses): la máquina de detección de ciclo funciona. El ancho medio del intervalo 80% por serie es **2,08–2,38 puntos** para un ruido sintético σ≈0,8 — coherente, aunque solo valida la *maquinaria*, no la precisión real.

### Comparativa de batching (mismo caso, `--per-core-batch-size 1`)

```bash
/root/.venvs/29n/bin/python pipeline/timesfm_smoke.py --per-core-batch-size 1 \
    --json /tmp/29n_smoke_batch1.json
```

| | batch=1 (default) | batch=32 |
|---|---|---|
| `global_batch_size` | 1 | 32 |
| Inferencia (10 series) | **9,127 s** | **1,636 s** |
| ms/serie | 912,7 | **163,6** |
| RAM pico | 2,23 GiB | 2,23 GiB |

**El batching da ~5,6× de aceleración** sin coste de memoria apreciable. En el pipeline de 29N hay que fijar `per_core_batch_size` explícitamente (≥ nº de series), no dejarlo por defecto.

---

## 4. ¿Sirve para series mensuales de intención de voto (~50 años, ~10 partidos)?

**Sí, y holgadamente en coste.** Concretando:

1. **Longitud:** 600 puntos/partido frente a un `context_limit` de **16.384**. Soobra contexto; se podría incluso usar ventana completa sin truncar. La estacionalidad anual la aprende sin features manuales.
2. **Volumen:** los 10 partidos en un solo lote tardan **~1,6 s** y ~2,2 GiB. Repetir esto para backtest (p. ej. 30 ciclos) son ~50 s en total. Es viable en el pipeline batch, no hace falta GPU ni servicio externo.
3. **Intervalos:** sí, expone cuantiles nativos (0.1..0.9) → **intervalo central 80%**, listo para la promesa del proyecto ("publica intervalos, no titulares"). Cobertura al 90% habría que construirla aparte (p. ej. remuestreo o supuesto gaussiano sobre el ancho 0.1–0.9); no viene de fábrica.
4. **Ventaja clave para 29N:** es *zero-shot*. No hay que entrenar con 50 años de historia electoral; el modelo ya viene preentrenado y aquí solo hace forecasting. Eso encaja con la fase 0.

**Límites y advertencias (honestas):**

- El smoke valida **maquinaria, no precisión**. Las series son sintéticas: el ruido es blanco y la estacionalidad limpia. Los datos reales de intención de voto tienen salto por eventos (debates, mociones, irrupción de partidos), huecos entre elecciones, y cambios de "régimen" (bipartidismo → multipartidismo). TimesFM no incorpora covariables electorales (eventos, encuestador, tamaño muestral) salvo vía `forecast_with_covariates`.
- El `point` devuelto es **la mediana (q0.5)**, correcto para series acotadas; la salida está forzada a no-negativa (`infer_is_positive=True`).
- `force_flip_invariance=True` (default) ejecuta el decode **dos veces** (normal y `-inputs`). Desactivarlo podría casi duplicar la velocidad, a cambio de perder la garantía de simetría. No se ha medido aquí; candidato a probar si el backtest lo pide.
- El venv pesa 5,4 GiB por los wheels CUDA inútiles en CPU: para CI/Vercel (aunque el modelo va en pipeline, no en la web) conviene un `requirements` con torch CPU-only.

**Siguientes pasos sugeridos (no ejecutados, fuera de este scope):** backtest contra los resultados reales de 23J/10N/28A (forma de medir cobertura empírica de los intervalos y error), y evaluación de `forecast_with_covariates` para meter las covariables del pitchfork scoring.

---

## Reproducir

```bash
python3.12 -m venv /root/.venvs/29n
/root/.venvs/29n/bin/pip install "timesfm[torch]"
cd /root/.openclaw/workspace/projects/29n
/root/.venvs/29n/bin/python pipeline/timesfm_smoke.py \
    --years 50 --horizon 12 --n-series 10 --per-core-batch-size 32 --json /tmp/smoke.json
```

Exit code `0` = contrato verificado (punto = mediana, sin cruces); `1` = fallo de contrato.
