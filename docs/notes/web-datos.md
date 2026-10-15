# Web con datos reales — 29N (Fase 5, parte 1)

**Fecha:** 2026-10-15 · **Autor:** agente (subagente Fase 5) · **Estado:** build verde, sin deploy.
**Alcance escrito:** `web/`, `web/sync-data.py`, este documento. **No** se tocó `data/processed/`
(solo lectura), `pipeline/` ni se hizo commit/push.

Objetivo: sustituir los placeholders honestos del scaffold por **datos reales del pipeline**,
con la web como lector puro (todo estático, cero `fetch` en runtime) y cada cifra de predicción
acompañada de su intervalo.

---

## 1. Puente de datos: `web/sync-data.py`

Único puente entre `data/processed/` (fuente de verdad) y `web/src/data/` (lo que Astro importa
en build). Determinista (sin aleatoriedad ni fechas del sistema) e idempotente.

```bash
/root/.venvs/29n/bin/python web/sync-data.py     # o: python3 web/sync-data.py
```

Salida real:

```
sync-data → web/src/data
  ✓ forecast.json          3.5 KB
  ✓ seats.json            30.7 KB   (31,6 KB tras corregir prob_ge1)
  ✓ backtest.json         19.7 KB
  ✓ series.json           18.8 KB
  ✓ elecciones.json      255.6 KB
  ✓ encuestas.json        42.3 KB
  ✓ exclusiones.json      20.4 KB
  ✓ sesgo.json             9.9 KB
listo.
```

### Inventario de entrada → salida

| Salida (web/src/data/) | Entrada (data/processed/) | Transformación |
|---|---|---|
| `forecast.json` | `modelo/forecast_state.json` | punto + cuantiles 0,1/0,2/0,5/0,8/0,9 por partido, ordenado por punto; `meta` con backtest, intervalos, normalización y advertencia |
| `seats.json` | `modelo/seats.json` | nacional (13) + 52 provincias con `media`, `ic95`, `prob_ge1` y `ganador` derivado; `meta` con coherencia y ratios de swing |
| `backtest.json` | `modelo/backtest.json` | MAE global/por partido, distribución de errores, cobertura y detalle por elección (predbaseline/TimesFM/ensemble/real + p10·p50·p90 del IC80 de TimesFM) |
| `series.json` | `modelo/series.csv` | serie mensual 2015-01 → 2026-11 en columnar compacto, 13 partidos, 1 decimal |
| `elecciones.json` | `interior/elections.json` + `partidos.json` | 16 generales con candidaturas nacionales resueltas (nombre/sigla) y `% sobre votos válidos` |
| `encuestas.json` | `cis/polls.jsonl` + `cis/studies.json` + `encuestadores/polls.jsonl` | 67 encuestas a nivel de estudio (35 CIS + 32 privados) con `partidos{}`, n, fechas, URL y base; dimensiones para los filtros |
| `exclusiones.json` | `cis/exclusions.json` + `encuestadores/exclusions.json` | log unificado (71 CIS + 8 encuestadores) |
| `sesgo.json` | `sesgo/house_effects.json` | resumen por casa×serie, comparación CIS, correcciones EB del CIS e incumbencia |

Tamaño total de `web/src/data/`: **≈ 410 KB**. `elecciones.json` es casi todo el peso (candidaturas
nacionales de 16 comicios); comprime muy bien y no entra en ninguna ruta crítica.

---

## 2. Qué se implementó por página

### Portada (`/`)
- **Predicción estatal 29N real**: PP 35,4 % (31,9–38,8), PSOE 29,1 % (23,5–34,8), VOX 20,6 %
  (16,6–24,6), Sumar 7,1 % (0,0–16,2). El componente `IntervalBand` reescrito dibuja banda p10–p90
  (color firma `--intervalo`) + punto (`--tinta`), con la sigla de partido como única muestra de
  color (el color no es el único canal). Los 9 partidos restantes van en un `<details>` **también
  con intervalo**.
- **Advertencia metodológica visible** (bloque `aviso-metodo`): método primario = baseline, TimesFM
  no mejora, intervalos empíricos y no probabilidad de resultado.
- **Serie que alimenta el modelo**: `SerieLinea` con la serie ponderada 2023-08 → 2026-11 (36 meses)
  para PP/PSOE/VOX/Sumar. Va **sin banda a propósito**: es un promedio de encuestas, no una
  predicción; etiquetada como tal.
- Tres entradas asimétricas con datos reales: contador del catálogo (67 encuestas), escaños reales
  de las cinco primeras candidaturas de 23J, y enlace a predicción provincial.
- Banda de metodología con backtest real (MAE baseline 1,234 pp · TimesFM 1,272 pp, no mejora).

### `/prediccion/`
- **Cartograma de las 52 provincias**: 11 × 9, una celda por provincia, colocada según su posición
  real y coloreada por el partido con más escaños esperados (agrupado a los tokens de DESIGN.md §2).
  La sigla va **escrita** en cada celda (no solo color).
- **Panel sincronizado sin JavaScript**: mapa y tabla enlazan a `#prov-<código>`; el panel muestra
  la provincia apuntada vía `:target` y oculta la ayuda vía `:has(.prov-panel:target)`. 52 paneles
  con su `IntervalBand` de escaños (media + IC95) y la frase de lectura obligatoria.
- **Tabla paralela accesible** (52 filas): ganador, media, IC95, P(≥1) y escaños, navegable por
  teclado; el mapa nunca es el único camino al dato.
- Reparto **nacional** de escaños con banda (PP 136,5 [111–164] … PACMA 0 [0–0]) y la coherencia
  verificada (suma de medias = 350,0; desviación provincial ≤ 0,0085 pp).
- **Nota de mejora MRP**: se declara que un modelo MRP está en evaluación y que solo se publicará
  si supera el backtest. (Existe trabajo paralelo sin seguimiento en `pipeline/mrp/` y
  `data/processed/mrp/`; esta tarea **no** lo ha tocado.)
- Los selectores de nivel/partido siguen `disabled` con nota: la interactividad en cliente llega
  con JavaScript en una fase posterior.

### `/encuestas/`
- **Tabla de las 67 encuestas** (CIS + privados) con ID mono, casa, tipo, fechas de campo, n,
  ámbito, elección, PP/PSOE/VOX/Sumar y enlace a ficha técnica.
- **Filtros reales por casa / año / elección sin JavaScript**: radios nativos + CSS `:has()`.
  Se genera una regla por valor de dimensión (`.explorador:has(#fc-N:checked) [data-fila]:not(...)`)
  y cada fila lleva `data-casa` / `data-anio` / `data-eleccion`. Sin soporte de `:has()` no filtra
  y se ven todas las filas (degradación honesta, no un resultado falso). Se advierte que el
  contador no se recalcula al filtrar.
- **Ficha (`SourceCard`) por encuesta** con muestra, campo, publicación, metodología, ámbito, base
  del % y **URL de ficha técnica** obligatoria.
- **Log de exclusiones** público (79 entradas) además del de `/metodologia/`.
- Aviso LOREG (apagón de los 5 días previos) intacto.

### `/resultados/`
- **Timeline real** de las 16 generales (1977–2023), con la última marcada como activa; cada hito
  enlaza a su elección.
- **Escrutinio por elección** en `<details>` (la de 2023 abierta): 12 candidaturas con barras de
  escaños y % sobre válidos, desde Interior.
- **Comparador de partidos**: escaños de una candidatura en A vs B (emparejadas por `partido_id`),
  con Δ de signo +/− y valor en tinta. Tres pares de referencia (2023/2019-N, 2019-N/2019-A,
  2016/2015); el comparador libre llegará con JavaScript.
- Nota de contexto explícita: las notas editoriales por elección están **pendientes** y no se fingen.

### `/metodologia/`
- **Backtest con MAE por partido** (TimesFM / baseline / ensemble / ganador / n) y MAE por elección.
- **Veredicto sin maquillar**: «TimesFM NO mejora al baseline» (1,234 vs 1,272 pp, n = 59, σ = 2,56),
  y por eso el método primario publicado es el baseline.
- **Correcciones de sesgo**: efectos de casa con encogimiento EB, comparación CIS (microdato 1,79 pp
  vs modelo CIS 1,09 pp) y tabla de correcciones EB aplicadas a la serie del CIS.
- **Límites** en lenguaje llano (swing uniforme, intervalos empíricos, horizonte 1 mes, cobertura
  97,96 %, huecos históricos del CIS).
- **Log de exclusiones** como tabla ordinaria (79 filas).
- Long-form con índice pegajoso, notas al margen en mono y `details` nativo en móvil.

---

## 3. Evidencia (salida real)

### 3.1 `npm run build` — exit code 0

```
> 29n-web@0.1.0 build
> astro build

12:44:26 [content] Syncing content
12:44:26 [content] Synced content
12:44:26 [types] Generated 77ms
12:44:26 [build] output: "static"
12:44:26 [build] mode: "static"
12:44:26 [build] directory: /root/.openclaw/workspace/projects/29n/web/dist/
12:44:26 [build] Collecting build info...
12:44:26 [build] ✓ Completed in 97ms.
12:44:26 [build] Building static entrypoints...
12:44:29 [vite] ✓ built in 2.10s
12:44:29 [build] ✓ Completed in 2.15s.

 generating static routes 
12:44:29 ▶ src/pages/404.astro
12:44:29   └─ /404.html (+13ms) 
12:44:29 ▶ src/pages/encuestas/index.astro
12:44:29   └─ /encuestas/index.html (+30ms) 
12:44:29 ▶ src/pages/index.astro
12:44:29   └─ /index.html (+5ms) 
12:44:29 ▶ src/pages/metodologia/index.astro
12:44:29   └─ /metodologia/index.html (+6ms) 
12:44:29 ▶ src/pages/prediccion/index.astro
12:44:29   └─ /prediccion/index.html (+18ms) 
12:44:29 ▶ src/pages/resultados/index.astro
12:44:29   └─ /resultados/index.html (+27ms) 
12:44:29 ✓ Completed in 126ms.

12:44:29 [build] 6 page(s) built in 2.39s
12:44:29 [build] Complete!
```

### 3.2 `npm run check` — exit code 0

```
> 29n-web@0.1.0 check
> astro check

12:44:39 [content] Syncing content
12:44:39 [content] Synced content
12:44:39 [types] Generated 44ms
12:44:39 [check] Getting diagnostics for Astro files in /root/.openclaw/workspace/projects/29n/web...
Result (21 files): 
- 0 errors
- 0 warnings
- 0 hints
```

### 3.3 Verificación del HTML generado

| Comprobación | Comando | Resultado |
|---|---|---|
| Rutas servidas | `python3 -m http.server` sobre `dist/` + `curl -o /dev/null -w %{http_code}` | `/`, `/encuestas/`, `/prediccion/`, `/resultados/`, `/metodologia/` → **200** |
| Intervalos reales en portada | `grep` sobre `dist/index.html` | `31,9–38,9` presente; 13 filas de banda (4 + 9) |
| Filtros CSS inyectados | `grep ':has(#fc-' dist/encuestas/index.html` | reglas presentes; 67 filas con `data-fila` y sus `data-casa/data-anio/data-eleccion` |
| Paneles de provincia | `grep -o 'id="prov-N"' dist/prediccion/index.html` | **52** paneles + 52 celdas de cartograma |
| Reglas de sincronía | `grep 'prov-panel' dist/_astro/*.css` | `.prov-panel{display:none}` · `.prov-panel:target{display:block}` · `:has(.prov-panel:target) .panel-hint{display:none}` |
| Detalles de elección | `grep -o 'id="elec-' dist/resultados/index.html` | **16** (todas las generales) |
| Backtest y exclusiones | volcado de `dist/metodologia/index.html` | tabla MAE por partido y log con **79** filas |
| Sin placeholders obsoletos | `grep 'class="pendiente"' dist/**/*.html` | **0** (todas las secciones ya tienen datos) |

### 3.4 Tamaño

```
index.html          40 KB
encuestas/index.html 224 KB
prediccion/index.html 348 KB
resultados/index.html 228 KB
metodologia/index.html 76 KB
dist total          1,7 MB   (CSS 32 KB; el resto, fuentes y preloads de Fontsource)
```

---

## 4. Decisiones de honestidad y diseño

1. **Cero cifras de predicción sin intervalo.** Los únicos números sin banda son *hechos* (escrutinio
   oficial de Interior, MAE del backtest, recuentos de catálogo), nunca predicciones.
2. **La serie va sin banda**, con nota. El dato mensual publicado no trae intervalo; ponerle una
   banda inventada habría sido maquillar un promedio como predicción.
3. **Cartograma, no silueta.** No hay geometría provincial en el repo: dibujar una silueta
   aproximada sería un dato falso. Se dibuja un cartograma (celda por provincia) y se declara
   como pendiente la geometría fina.
4. **Colores de partido dentro del contrato.** No se añadieron tokens nuevos: los partidos del
   universo modelado se agrupan a los tokens de DESIGN.md §2 (`--p-pp`, `--p-psoe`, `--p-vox`,
   `--p-sumar`, `--p-cs`, `--p-erc` para nacionalistas, `--p-pnv`, `--p-otros`). La leyenda nombra
   los grupos y las celdas escriben la sigla, de modo que el color nunca es el único canal.
   *(Punto abierto para DESIGN.md: si se quieren tonos distintos para ERC/JxCat/BNG/Bildu, hay que
   ratificar tokens nuevos.)*
5. **Interactividad que no existe, no se finge.** Los selectores sin JavaScript van `disabled` con
   nota explicando qué falta; los filtros que sí funcionan sin JS (encuestas) se declaran como tales.
6. **El error se ve igual que el acierto.** El veredicto «TimesFM no mejora al baseline» ocupa un
   recuadro de borde `--alerta`, no una nota al pie.

### Lo que sigue como «pendiente», nombrado
- Notas editoriales por elección (resultados) — **sin redactar**.
- Selector interactivo de nivel/partido (predicción) y comparador libre (resultados) — **JavaScript**.
- Geometría provincial real del mapa — **mejora pendiente**.
- Modelo MRP — **en evaluación** (no se publica hasta que supere el backtest).
- Deploy — **fuera de alcance** (Vercel es manual y posterior).

---

## 5. Verificaciones no hechas (heredadas del scaffold)

1. **Revisión visual en navegador** (360 / 768 / 1440 px): no comprobada en este entorno.
2. **Test de daltonismo** (deuteranopía/protanopía) sobre los colores de partido.
3. **Zoom al 200 %** sin pérdida de contenido.
4. **Deploy**: explícitamente fuera de alcance.

---

## 6. Siguiente paso sugerido

1. Revisión visual humana y ajuste de ritmo vertical.
2. Ratificar en DESIGN.md la agrupación de color de partidos (o ampliar tokens).
3. Añadir el comparador libre y el selector de mapa en cliente (islas de JS, sin framework).
4. Decidir MRP con su backtest antes de publicarlo.
5. Fijar `site` en `astro.config.mjs` y desplegar en Vercel cuando se decida el dominio.
