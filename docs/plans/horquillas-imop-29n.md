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
- [ ] B1: componente de horquillas con `--intervalo` y mayoría a 176.
- [ ] B2: tabla-resumen estructurada (electomanía-style propio).
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
