# Simulador 29N — «¿qué pasaría si…?» con diseño honesto

Fecha: 2026-10-15 · Feature 3 del plan `docs/plans/features-diferenciales.md`.
Alcance: `pipeline/simulador/`, `web/src/data/base23.json`,
`web/src/pages/simulador/`, este informe. Sin commits ni push. Solo lectura sobre
`data/processed/interior/` y `data/processed/modelo/` (y `pipeline/modelo/` +
`pipeline/interior/dhondt.py`, importados en modo lectura). No se toca
`Header.astro`, `DESIGN.md`, `sync-data.py`, `pipeline/modelo/`, `pipeline/mrp/`
ni `data/processed/` (escritura). **La integración en la navegación la hace el
padre tras revisión.**

## Qué es

Un explorador donde el visitante mueve el voto de los 13 partidos del modelo
**dentro del intervalo que el propio modelo declara** (p10–p90 del backtest) y ve
cómo cambian los escaños. No es una predicción nueva: es el error del modelo
convertido en espacio de juego, con una nota permanente visible.

Principio de diseño: *los controles son la incertidumbre*. No hay un segundo
intervalo decorativo: la banda p10–p90 es literalmente el rango donde el slider
puede moverse.

## Ficheros

| Fichero | Qué hace |
|---|---|
| `pipeline/simulador/export_base23.py` | Exporta la base provincial 23J a `web/src/data/base23.json`. Verifica que el reparto reproduce `seats.json`. |
| `web/src/data/base23.json` | 52 provincias: escaños, votos válidos y % de voto por partido (universo modelado, suma 100 por provincia) + `punto_modelo`. |
| `web/src/pages/simulador/index.astro` | Página «Simulador 29N». Motor D'Hondt + swing + calibración en JS vanilla, datos embebidos. |

## 1. Base provincial (`base23.json`)

Se lee `data/processed/interior/results_provincial.jsonl` (solo lectura) y se
agrega la elección `2023-07-23`. Canonicalización **idéntica a la del modelo**, o
el escenario central del simulador no coincidiría con el del modelo:

- `pipeline/interior/partidos_aliases.json` es el diccionario canónico de
  Interior; el modelo lo replica en `pipeline/sesgo/party_canon.py`.
- `pipeline/modelo/common.py` (importado en modo lectura) aplica además las
  familias: IU/Podemos/Unidas Podemos → SUMAR y la corrección UPN (`u-p-n`) →
  NA+.
- `partidos.json` se usa para documentar nombres/siglas en `meta`.

Cada provincia se renormaliza al universo modelado de 13 partidos (suma 100),
igual que `build_base()` de `provincial.py`. El residual (~2 % del voto válido de
23J) no se reparte escaños, como en el modelo provincial.

## 2. Motor del simulador (JS vanilla, en el navegador)

1. **Sliders** (13): cada control va de `p10` a `p90` de `forecast.json`. El
   valor inicial es `punto_modelo` (ver §3). El total se **renormaliza
   proporcionalmente** a 100; la suma cruda se muestra siempre en pantalla
   («Suma de los controles: 125,7 % → renormalizado a 100 %»).
2. **Swing proporcional uniforme**: `v_{p,k} ∝ base_{p,k} · r_k`,
   `r_k = target_k / base_nacional_k`, normalizado a 100 por provincia. Se
   descarta el swing aditivo (destruye a los partidos de apoyo concentrado).
3. **Calibración de punto fijo** `r_k ← r_k · target_k / agg_k` hasta que el
   agregado provincial ponderado por votos coincide con los controles
   (tol 0,02 pp, máx 20 iteraciones). Es la misma calibración de
   `pipeline/modelo/provincial.py`.
4. **D'Hondt por provincia**: 52 circunscripciones, 350 escaños, umbral legal del
   3 % de los votos válidos. Misma lógica que `pipeline/interior/dhondt.py`
   (cocientes `v/k`, desempate determinista por nombre).
5. **Resultado**: barra apilada del reparto (colores de partido del contrato),
   tabla con escaños, **Δ frente al escenario central del modelo** y % de voto, y
   una nota permanente: *«Exploratorio: escenarios dentro del error del modelo
   (p10–p90 del backtest). No es una predicción nueva.»*

Sin JavaScript, la página ya muestra el escenario central renderizado en el
build (Astro), con la misma nota. El cálculo del visitante no sale del navegador.

## 3. El escaño de la frontera (decisión documentada)

`forecast.json` publica el punto redondeado a 2 decimales; `forecast_state.json`
lo guarda a 3. Ese redondeo basta para mover **un escaño** en la frontera
PSOE/PNV: con el punto exacto (PSOE 29,146) el reparto da PSOE 109 / PNV 4, y
con el redondeo (PSOE 29,15) da PSOE 108 / PNV 5 —ambos con 350 escaños—.

Para que el simulador, **partiendo de su estado inicial, sea exactamente el
escenario central de `seats.json`** (y no una versión desviada por redondeo), el
punto preciso viaja en `base23.json` (`punto_modelo`, 3 decimales) y los sliders
parten de ahí. Los límites del slider siguen siendo `p10`/`p90` de
`forecast.json` como pide el plan. Los controles usan `step=0.001` para que el
punto de 3 decimales sea alcanzable (con `step=0.1` el navegador lo ajustaría y
el problema volvería).

> Recomendación para el padre (fuera de mi alcance): que `sync-data.py` publique
> `forecast.json` con 3 decimales, o que la web consuma `forecast_state.json`
> directo. Hoy el redondeo a 2 decimales es la única fuente de divergencia entre
> `/prediccion` (109/4) y cualquier consumidor que use `forecast.json` como
> entrada exacta.

## 4. Verificación (salida real)

### Export

```text
$ /root/.venvs/29n/bin/python pipeline/simulador/export_base23.py
OK web/src/data/base23.json — 52 provincias, 19115 bytes
  Calibración (verificación): 4 iteraciones, desv 0.0091 pp
  Comprobación escenario central (simulador vs seats.json):
    suma de escaños = 350
    PP        138  (modelo 138)
    PSOE      109  (modelo 109)
    VOX        68  (modelo  68)
    ...
  Escenario central reproducido exactamente: SÍ
```

### Motor JS real (ejecutado en Node con un DOM mínimo)

Se extrae el `<script is:inline>` de la página y se ejecuta tal cual. Estado
inicial = punto del modelo:

```text
pie   : 350 escaños · escenario simulado
aria  : Escenario simulado: PP 138, PSOE 109, VOX 68 escaños.
suma  : Suma de los controles: 100,0 % → renormalizado a 100 %
central: {"PP":138,"PSOE":109,"VOX":68,"SUMAR":9,...,"PNV":4,...}
  PP: sim=138 central=138 OK
  PSOE: sim=109 central=109 OK
  VOX: sim=68 central=68 OK
```

Escenarios extremos (controles a los límites p10/p90) — todos con 350 escaños:

```text
central          total=350  PP 138 · PSOE 109 · VOX 68 · SUMAR 9 · PNV 4 · EH BILDU 7 · ERC 7
todos_max        total=350  PP 117 · PSOE 105 · VOX 66 · SUMAR 35 · PNV 3 · EH BILDU 7 · ERC 7
todos_min        total=350  PP 158 · PSOE 107 · VOX 65 · SUMAR 0 · PNV 6 · EH BILDU 7 · ERC 2
vox_max_pp_min   total=350  PP 122 · PSOE 105 · VOX 89 · SUMAR 9 · PNV 4 · EH BILDU 7 · ERC 6
sumar_max        total=350  PP 125 · PSOE 101 · VOX 62 · SUMAR 39 · PNV 3 · EH BILDU 7 · ERC 6
psoe_max_pp_min  total=350  PP 116 · PSOE 135 · VOX 66 · SUMAR 9 · PNV 3 · EH BILDU 7 · ERC 6
```

### Web

```text
$ npm run check
Result (25 files):
- 0 errors
- 0 warnings
- 0 hints

$ npm run build
▶ src/pages/simulador/index.astro
  └─ /simulador/index.html (+5ms)
[build] 8 page(s) built in 1.93s
[build] Complete!
```

Artefacto: `dist/simulador/index.html` (52 KB), `<title>Simulador 29N · 29N</title>`,
13 sliders, 4 bloques JSON embebidos, nota permanente presente.

## 5. Límites (sin maquillaje)

- El swing es **proporcional uniforme**: no captura terremotos locales ni
  elasticidades provinciales distintas. Es el mismo límite del modelo provincial.
- Los controles están acotados al **error propio del modelo** (p10–p90). Fuera de
  esa banda el simulador no deja moverse: no es una herramienta de «y si España
  votara como Francia», es un explorador del error publicado.
- Los intervalos del modelo son **empíricos** (errores del backtest), estimados
  con n=2–5 elecciones: ruidosos por diseño, y así se declara.
- El residual del universo modelado no recibe escaños, igual que en el modelo.

## Siguiente paso

Integrar `/simulador/` en la navegación (lo hace el padre en `Header.astro` tras
revisión) y, si se acepta la recomendación de §3, publicar el punto del forecast
con más precisión en `forecast.json`.
