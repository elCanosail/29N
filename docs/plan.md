# Plan 29N — Predicción electoral por provincias

## Objetivo

Web que expone el histórico completo de encuestas electorales españolas (CIS exhaustivo + encuestadores privados), resultados oficiales de elecciones anteriores, y una predicción provincial del resultado del 29N usando TimesFM (Google Research, open source). Metodología científica, publicación pedagógica y periodística. Hospedado en Vercel.

**Frase del proyecto:** "Todo el dato electoral español, con predicción honesta y auditable."

## Decisiones (Chema, 15-10-2026)

- Predicción: TimesFM local (open source, sin coste de inference).
- Alcance de datos: CIS + Ministerio de Interior + encuestadores privados desde el día uno.
- Stack web: Astro + datos estáticos (JSON/Parquet), deploy Vercel.
- Nombre: **29N**. Repo nuevo: `elCanosail/29N` (supuesto a confirmar al crear).

## Fuentes de datos

| Fuente | Contenido | Acceso | Riesgo |
|---|---|---|---|
| CIS (Banco de Datos) | Serie PREELECTORALES desde 1979: microdatos, estimación de voto, variable provincia. Barómetros con intención de voto. | CSV abierto estudio a estudio con formulario; FID multi-estudio requiere registro | Scraping frágil; descarga no masiva |
| Ministerio de Interior (infoelectoral) | Escrutinio provincial/municipal por candidatura desde 1976 | Descarga abierta (procesos electorales) | Bajo |
| Encuestadores privados (GAD3, 40dB, Sigma Dos, NC Report, Simple Lógica, Más1, Demoscopia…) | Intención de voto estimada + ficha técnica | Recolecta de prensa y fichas técnicas; curación manual/semiautomática | Alto: sin fuente agregada, formato heterogéneo |

### Normalización

- IDs de partido: diccionario propio con aliases (PODEMOS-IU-ALIANZA VERDE-SUMAR, PSC vs PSOE, etc.). Nivel estatal vs autonómico separado.
- Fechas: campo de trabajo (`fieldwork_end`) + `published` separados; series ordenadas por fecha de trabajo, no de publicación.
- Muestra: `n`, ámbito (estatal/provincial), tipo (preelectoral/barómetro), metodología (CATI/CAWI/mixta).
- Toda encuesta guarda su fuente (URL de ficha técnica) y entra al log de exclusiones si no pasa validación.

## Modelo de predicción

1. **Serie estatal por partido**: intention-of-vote estimada por el CIS + encuestadores, ponderada (recencia, tamaño muestral, histórico de error del encuestador — pitchfork scoring contra resultados reales).
1b. **Efectos de casa y sesgo de incumbencia (Fase 4-bis, petición Chema 15-10-2026)**: para cada encuestador, error firmado histórico (última encuesta pre-electoral − resultado real) por partido; descomposición incumbencia vs. efecto fijo de partido; para el CIS, medir por separado el sesgo de la "estimación del modelo" publicada (tablas oficiales) y del "voto directo" de microdatos. Corrección aplicada con encogimiento empirical-bayes (n pequeño → corrección ~0), intervalos publicados tal cual. Medir, no asumir.
1c. **Microdatos: MRP y explorador (Fase 4-c, petición Chema 15-10-2026)**: extracción de variables individuales (demografía, provincia, ideología, recuerdo, intención) de los ~110 estudios descargados → dataset individual normalizado. Dos usos: (a) MRP (regresión multinivel + post-estratificación con censo INE por provincia) como candidato a reemplazar/mejorar el swing uniforme para la predicción provincial — validado por backtest contra 2015-2023; (b) explorador sociodemográfico pedagógico para la web. Caveats: variables que cambian de nombre por era, provincias pequeñas con n bajo, disponibilidad/licencia del censo INE por investigar.
2. **TimesFM**: forecast de la serie estatal por partido hasta el 29N, con intervalos.
3. **Desagregación provincial**: nowcasting por swing — resultados históricos provinciales (1976-2023) como base, ajuste con la variación nacional prevista. Validar contra 23J, 10N, 28A, 26J, 20D, 2015, 2011 (backtest).
4. **Ecuaciones de reparto**: escaños por provincia con método D'Hondt sobre 10.000 simulaciones (intervalos de predicción, no punto).
5. Salida: JSON por provincia → la web solo lee, no calcula.

**Honestidad metodológica obligatoria:** intervalos explícitos, error del backtest publicado, partidos pequeños con intervalos anchos. El log de exclusiones público (marca Elicita).

## Arquitectura

- `pipeline/` (Python): ingesta → normalización → validación → parquet/JSON. TimesFM corre aquí (batch, no en la web).
- `data/` versionada en repo (tamaños manejables tras normalizar).
- `web/` (Astro): histórico de encuestas, explorador de resultados por elección, predicción provincial 29N con mapa + tabla, ficha de cada encuesta con su ficha técnica, página de metodología.
- Deploy: Vercel. `DESIGN.md` obligatorio en raíz antes de tocar frontend (regla de casa).

## Fases

### Fase 0 — Scaffold (semana 1) — CERRADA 15-10-2026
- [x] Repo público creado: github.com/elCanosail/29N (esqueleto, CONTRIBUTING, licencia MIT, guardas de secretos)
- [x] TimesFM verificado: timesfm 3.0.2 (checkpoint 2.5-200m PyTorch) en CPU, intervalos nativos; 10 series × 600 pts en 1,64 s / 2,23 GiB (evidencia: docs/notes/timesfm-smoke.md). Hallazgo clave: quantiles devuelve 10 columnas (punto = col 5) y per_core_batch_size=1 serializa; fijar ≥ n_series (×5,6).
- [x] Descarga de 3 estudios CIS (3411 · 23J-2023, 3263 · 10N-2019, 3141 · 26J-2016) con parse y validación ≤0,05 pp contra tablas publicadas. Descarga directa por URL sin formulario; 429 → backoff obligatorio (evidencia: docs/notes/cis-probe.md)
- [x] DESIGN.md (formato Stitch) con referencias GOV.UK / EU Design System / portales nórdicos / The Pudding

### Fase 1 — Ingesta CIS completa (semanas 1-2)
- [ ] Catálogo de estudios CIS electorales/preelectorales (nº de estudio, fechas, ámbito)
- [ ] Descarga automatizada estudio a estudio (con formulario) o FID con registro
- [ ] Parser de microdatos → esquema normalizado (voto estimado, provincia, n, fechas)
- [ ] Diccionario de partidos con aliases v1
- [ ] Verificación: totales de una encuesta coinciden con las tablas publicadas del CIS (±0,1)

### Fase 2 — Resultados oficiales (semana 2)
- [ ] Ingesta de todas las generales 1977-2023 (provincial, por candidatura) desde infoelectoral
- [ ] Esquema normalizado + consistencia: sumas provinciales = escaños repartidos por D'Hondt de la elección
- [ ] Serie histórica de escaños y % por partido consultable

### Fase 3 — Encuestadores privados (semanas 2-4) — curación inicial cerrada 15-10-2026
- [x] Curración inicial: 32 encuestas de 9 encuestadores (2023-2026), 132 filas, toda con URL de ficha técnica + extracto (evidencia: docs/notes/encuestadores.md). Trackings diarios de campaña muestreados, no completos; serie 2019 pendiente
- [~] Scoring: MAE 23J calculado (Simple Lógica 1,73 … Imop 2,32) — valida el pipeline, n=1-3 por encuestador: NO es ranking fiable todavía. Scoring histórico robusto requiere serie 2015-2023
- [x] Esquema unificado con CIS (partidos canónicos del diccionario) + log de exclusiones público (8 exclusiones con motivo)
- [x] Correcciones de sondeo previo: "Hand Research" y "Cercle d'Estudis" no existen como encuestadores de generales (excluidos; homólogo real: CEO, ámbito catalán)
- [x] 18-10-2026, decisión Chema: la curación diaria ingiere directamente las encuestas claras y relevantes (intención de voto electoral con ficha técnica verificable) sin supervisión; las dudosas (ficha inaccesible, faltan n/fechas/universo, formato ambiguo) escalan a Chema; las no electorales se descartan con una línea. Implementado en la automatización `29n-exploracion-diaria`

### Fase 4 — Modelo (semana 4-5) — CERRADA 15-10-2026
- [x] Serie ponderada por partido con pesos de calidad (recencia exponencial, √n, scoring de encuestador, corrección EB de sesgo de casa restada)
- [x] Backtest contra 5 elecciones (20D-2015, 26J-2016, 28A-2019, 10N-2019, 23J-2023), sin fuga de datos, n=59: **baseline 1,234 pp · ensemble 1,236 · TimesFM 1,272**. Veredicto sin maquillaje: TimesFM NO mejora al baseline ingenuo (empate estadístico); punto primario = baseline, TimesFM publicado como contraste. Documentado en backtest.json y docs/notes/modelo.md
- [x] Desagregación provincial por swing proporcional con calibración por punto fijo (el aditivo destruía a los partidos concentrados)
- [x] Simulación D'Hondt 10.000 runs → escaños por provincia con intervalos; coherencia estatal-provincial verificada en fresco (3/3 tests, desviación máx 0,0085 pp)
- [x] Filtros documentados: CIS no_validada fuera, no estatales fuera, publicación incompleta fuera (incl. 40dB 08-10-2026)

### Fase 4-c — Microdatos/MRP — CERRADA 15-10-2026
- [x] Dataset individual: 532.498 entrevistas, 55 estudios, 1977-2025 (individual.parquet); validación 35/35 a ±0,1 pp (Δmax 0,0322 pp); censo INE 66600 identificado (MRP viable, con límites documentados)
- [x] MRP provincial: construido y evaluado con backtest de 5 elecciones (52 provincias). **Veredicto: NO supera al swing uniforme** (swing gana 4/5 en ambos tests; MRP anclado en ruido). No adoptado; comparación completa en docs/notes/mrp.md. Hallazgo: la geografía real de la última elección es un predictor provincial más fuerte que la demografía
- [x] Censo INE 66600 descargado y normalizado (8.736 celdas, supuestos documentados); post-estratificación 29N calibrada (desviación 0,0098 pp)

### Fase 5 — Web y publicación — CERRADA 15-10-2026
- [x] Web conectada a datos reales (Fase 5 parte 1): sync-data.py reproducible (8 JSON), portada con bandas de intervalo, cartograma 52 provincias sin JS, 67 encuestas con ficha y filtros, timeline 16 elecciones, metodología con veredicto TimesFM vs baseline sin maquillar. Build exit 0, astro check 0 errores
- [x] Deploy Vercel: **https://encuestas29n.vercel.app** (proyecto elcanoapps/encuestas29n, framework astro fijado en vercel.json, token verificado en almacén de secretos). Smoke test: 200 en las 5 rutas. Historial del dominio: 29n.vercel.app ocupado por proyecto ajeno (vercel.app es espacio global) → renombrado del proyecto y Chema eligió encuestas29n.vercel.app (15-10-2026); 29n-eta retirado
- [x] Verificación mobile (iPhone 13, 390px, Chromium + CDP): 0 overflow horizontal en las 5 rutas; cartograma desplazable con celdas de 41 px; áreas táctiles ≥37 px (timeline, migas, pie); etiquetas de filtro 44 px; tablas ajustadas o con scroll propio. Fix aplicado: min-width 0 en la cadena del grid del panel doble (el layout móvil se expandía a 524 px)
- [~] Pendiente honrado: test de daltonismo y zoom 200 %

### Fase 5 — Web y publicación (semanas 5-6)
- [ ] `DESIGN.md` (Google Stitch format)
- [ ] Astro: home, explorador de encuestas, explorador de resultados, predicción 29N, metodología
- [ ] Mapa provincial interactivo + comparativa predicción vs última encuesta
- [ ] Deploy Vercel + dominio
- [ ] Apagón LOREG: la sección de encuestas oculta resultados de los 5 días previos al 29N

## Criterios de aceptación

1. Cualquier dato de la web es trazable a fuente (URL de estudio/ficha técnica) y clicable.
2. Backtest publicado: error histórico del modelo, sin maquillaje.
3. Predicción provincial con intervalos, no cifras puntuales.
4. Reproducible: `pipeline` corre de cero en un clon limpio (README con instrucciones).
5. Suma de predicciones provinciales = predicción estatal (coherencia interna verificada).

## Repositorio público (decisión Chema, 15-10-2026)

- Repo público en GitHub desde el inicio para atraer colaboradores. Todo el dato es público por naturaleza; la curación de encuestadores privados es el trabajo paralelizable ideal para contribuciones.
- Fuera del repo: secretos (credenciales FID, API keys, tokens Vercel — vía env vars y GitHub secrets, guard con gitleaks), crudos masivos del CIS (re-descargables con el pipeline; en repo solo outputs normalizados), y cualquier vínculo con otros proyectos del ecosistema.
- Contribuciones: CONTRIBUTING.md (ficha técnica obligatoria por PR de datos, no reidentificación de microdatos), issues públicas, diccionario de partidos como primer buen primer-issue, etiquetas good-first-issue.
- Neutralidad partidista explícita en README: el valor es el método, no el resultado.

## Riesgos

- **Formulario CIS**: si el scraping automático falla, plan B = descarga asistida por lotes (el formulario es por estudio, ~60 estudios electorales; factible manualmente en sesiones).
- **Encuestadores privados**: calidad irregular y sin fuente única; mitigado por scoring y log de exclusiones.
- **Intervalos provinciales anchos** en partidos pequeños: publicar tal cual, es parte del valor científico.
- **Cupo Vercel**: datos estáticos, sin problema previsto.

## Evidencia y verificación

- Cada fase cierra con prueba documentada en este archivo (comando ejecutado, output, diff).
- Validaciones cruzadas: totales CIS vs tablas oficiales; escaños vs resultados reales; coherencia estatal-provincial.

## Siguiente paso

Fase 0: crear repo y smoke test de TimesFM + descarga de los 3 estudios CIS de muestra.
