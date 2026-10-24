# Plan — Horquillas visuales (estilo propio) + ingesta IMOP 23-oct (29N)

**Fecha:** 2026-10-24 · **Autor:** Elcano · **Aprobación:** Chema («Sigamos con 29n… electomanía.es… horquillas de escaños… encuesta de imop del 23 oct»)

## Contexto

- La traslación provincial y la vista CCAA están en producción (plan
  `traslacion-ccaa-provincia.md`, main → 9e4cb9e, desplegado).
- El modelo ya produce **horquillas de escaños** por partido: `seats.json → nacional[]`
  con `{media, ic95: [min, max], central_escenario, p_ge1}` de las 10.000 simulaciones
  D'Hondt. Hoy solo se publican como tabla; falta la pieza visual.
- `docs/notes/ingesta-imop-confidencial.md` documenta la vía de ingesta IMOP
  (staging fragment → `build_dataset.py` → cadena `build_series → forecast →
  provincial → sync-data` con `/root/.venvs/29n/bin/python`). Regla de oro:
  **toda encuesta necesita URL de ficha técnica publicada; sin URL → exclusión.**
- DESIGN.md: las bandas de intervalo ámbar (`--intervalo`) son el color firma del
  proyecto y «el elemento gráfico protagonista» — la horquilla debe usarlo.

## A) Ingesta IMOP del 23-oct (subagente 1, glm5.3)

- Localizar la publicación pública (El Confidencial / imop.es) de la encuesta IMOP
  publicada el 23-10-2026: URL + cifras por partido. **Si no hay URL pública,
  detenerse y reportar** (regla de oro).
- Crear fragmento de staging en `data/processed/encuestadores/_staging/`
  (formato verificado en `simplelogica_demoscopia.json`): fuente Imop Insights,
  estudio_id `imop-<fecha>`, fechas de campo/publicación, n, metodología, ámbito,
  URL, extracto con las cifras citadas, votos por partido.
- Ejecutar `build_dataset.py` y la cadena completa con el venv 29N:
  `build_series → forecast → provincial → sync-data` (localizar `sync-data` en el
  repo; si el paso final no existe como script, replicar lo documentado).
- Verificación: forecast.json y seats.json actualizados (fecha `generado` nueva),
  movimiento de cuotas razonable (±1-2 pp típico de una encuesta), sin ruptura de
  la suma 100 %, web regenerada.
- Commit en rama propia + evidencia en este documento.

## B) Horquillas de escaños, estilo propio (subagente 2, glm5.3)

- Nuevo componente SVG/CSS vanilla (sin dependencias JS) en `web/src/components/`
  consumiendo `seats.json → nacional[]`.
- Diseño (estilo propio, no copia de electomanía.es):
  - Una fila por partido, orden por media descendente.
  - Banda de horquilla: rango completo `ic95 [min, max]` en ámbar `--intervalo`
    (el color firma), con la franja `media ± desviación típica del backtest` en
    tono más denso si el dato lo permite.
  - Marcador central: `media` (punto) y `central_escenario` (tick) con leyenda.
  - Línea vertical de mayoría absoluta (176) con etiqueta.
  - Colores de partido normalizados del DESIGN.md; etiquetas min/max en los
    extremos de cada banda.
- Presentación estructurada al estilo electomanía (propia): tabla-resumen por
  partido (media, horquilla, ± vs 23J) junto al gráfico; jerarquía visual:
  gráfico primero, tabla después.
- Verificación: build + render en preview; las 13 filas del nacional; suma de
  medias = 350 coherente con la vista CCAA ya publicada.

## Checklist

- [ ] A1: URL pública de la encuesta IMOP 23-oct localizada y verificada.
- [ ] A2: fragmento de staging creado y validado contra la regla de oro.
- [ ] A3: cadena ejecutada; forecast/seats actualizados con evidencia.
- [x] B1: componente de horquillas con `--intervalo` y mayoría a 176.
- [x] B2: tabla-resumen estructurada (electomanía-style propio).
- [ ] Revisión del padre (diff + build + render) antes de push/merge.
- [ ] Push a main tras revisión; despliegue Vercel con el token de secrets.

## Criterios de aceptación

1. Ninguna cifra inventada: toda encuesta ingerida con URL y extracto verificable.
2. La horquilla representa las simulaciones existentes — cero números nuevos de modelo.
3. Estilo propio: ámbar `--intervalo` como firma, paleta de partidos del DESIGN.md,
   sin clonar el CSS de electomanía.es.
4. Build + check verdes; sin regresión en las páginas existentes.

## Evidencia

(Se rellena al cerrar cada ítem: commits, URLs, diff, movimientos de cuotas.)

### B) Horquillas de escaños, estilo propio (subagente 2) — 2026-10-24

**Rama y commits**

- Rama `feat/horquillas-visual` desde main (55d293b). Sin push: pendiente de revisión del padre.
- Commit de código: `9e4d85f` — `web/src/components/HorquillasEscanos.astro` (+408),
  `web/src/components/HorquillasTabla.astro` (+188), `web/src/pages/index.astro` (+54/−28),
  `web/src/pages/prediccion/index.astro` (+74). Total: 4 ficheros, +696/−28.
  Nota de proceso: el commit lo materializó el coordinador durante el run (mi `git commit`
  llegó con el árbol ya comprometido); el contenido es exactamente el de esta rama.
- Commit de documentación: este mismo bloque (segundo commit de la rama).

**Qué se construyó**

- `HorquillasEscanos.astro`: gráfico de horquillas por partido, una fila por partido
  ordenada por media descendente (re-sort defensivo en el componente). Banda íntegra
  `ic95 [min, max]` en ámbar `--intervalo` con contorno `--intervalo-borde`; marcador
  central doble: punto = media, trazo = `central_escenario` (mediana), formas distintas
  y no solo color (§7.2); línea discontinua de mayoría absoluta (176) repetida como
  fondo de cada pista (alineación por subgrid, sin JS) + anotación Newsreader itálica
  en el eje; etiquetas min/max en los extremos; leyenda completa bajo el gráfico.
  Sin JavaScript ni dependencias de charts.
- `HorquillasTabla.astro`: tabla-resumen — media, horquilla IC95, mediana, P(≥1 esc.),
  escaños reales del 23J y Δ vs 23J con signo explícito (+/− coloreado, valor en tinta);
  tfoot con la coherencia (350,0 medias · 350 esc. 23J · Δ +0,0). Compartida por las
  dos presentaciones del componente.
- `/prediccion`: la sección nacional de `IntervalBand` se sustituye por las horquillas
  con tabla visible (jerarquía gráfico primero, tabla después). Checks en build:
  filas del nacional = universo modelado (`base23.meta.universo_modelado`) y suma de
  medias ≈ `meta.coherencia.suma_medias_escanos` (tolerancia 0,1) — el build falla
  antes de publicar mal, mismo criterio que la vista CCAA.
- Portada (`index.astro`): versión sobria en el bloque plegable de precisión — los dos
  `IntervalBand` se sustituyen por un único gráfico de 13 filas con la tabla en
  `<details>`. El resto de la portada no cambia.

**Decisiones de diseño**

- La «franja densa media ± desviación típica del backtest» del plan §B **no se publica**:
  `seats.json → nacional[]` no incluye la desviación típica y el criterio de aceptación 2
  prohíbe inventar números de modelo. La banda íntegra IC95 queda preparada para acoger
  esa franja si el modelo la emite.
- Δ vs 23J desde `reparto23.json`: es la agregación canónica de `elecciones.json` (23J)
  por familias del modelo que ya publica la portada; recalcular familias aquí habría
  arriesgado la coherencia del Δ con lo publicado (criterio 2: cero números nuevos).
- Min/max: cuando la banda es estrecha (≤12 % de la escala) o puntual, una única
  etiqueta «min–max» centrada/anclada evita solapes; cerca de 0/100 % se ancla al borde
  para no salirse de la pista. PACMA (0–0) se renderiza como fila presente (13 filas).
- Dark mode: el sitio es light-only hoy (`meta color-scheme="light"`, sin tokens oscuros
  en `tokens.css`); el componente no fija ningún color literal — solo tokens semánticos,
  listo para tokens oscuros si se definen.
- Mobile-first (container queries <620px): pista a ancho completo, media junto al
  nombre, el eje conserva la anotación de mayoría; tabla con scroll-x y primera columna
  fija con sombra-indicador (patrón ya establecido por la tabla de CCAA; se mantienen
  TODAS las columnas visibles con scroll, nada oculto).
- Nota de proceso: la primera iteración definía la tabla como JSX en el frontmatter y
  el build fallaba (Astro no admite JSX en frontmatter); refactor a componente propio.

**Verificación**

- `npm run build` ✓ (11 páginas) · `npm run check` ✓ (31 ficheros, 0 errores,
  0 avisos, 0 hints).
- HTML dist (`/prediccion/`): 13 × `pista__banda`, 13 × `pista__media`,
  13 × `pista__central`, 14 segmentos de línea de mayoría (13 filas + eje), anotación
  «Mayoría absoluta · 176» y tfoot Total = 350,0 / 350 / +0,0; los 13 partidos con fila
  (incluido PACMA). Portada: 13 bandas en el bloque de precisión.
- Coherencia con la vista CCAA ya publicada: misma fuente (`seats.json`), suma de medias
  350,01 ≈ 350 (desviación 0,01 declarada en `meta.coherencia`), guardas de build activas.
- Render en preview (`astro preview`, 127.0.0.1:4321) con capturas chromium headless a
  1280 px y 390 px más portada con `<details>` abierto; revisión de píxeles (el run no
  podía adjuntar imágenes): papel (251,250,247) real, 13 franjas de fila a ~52 px con el
  patrón esperado (bandas anchas PP/PSOE/VOX/Frente A; etiquetas únicas «min–max» en las
  estrechas), columna discontinua de mayoría en x≈97,8 % de la pista, y apilado a ancho
  completo en móvil. Capturas temporales en `web/.evidencia/`, borradas tras revisión.

**Bloqueos**: ninguno.
