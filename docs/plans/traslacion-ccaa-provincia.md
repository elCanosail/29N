# Plan — Traslación por CCAA y provincias (29N)

**Fecha:** 2026-10-24 · **Autor:** Elcano · **Aprobación:** Chema ("adelante, GLM full y subagentes a tu discreción")

## Contexto y corrección de alcance

La petición original (traslación de predicciones por CCAA y provincias, inspirada en
la estimación de ElElectoral para Andalucía desde microdatos del CIS) se propuso
asumiendo que la capa geográfica faltaba. El recon profundo (2026-10-24) revela que
**ya está construida y en producción**:

- Traslación provincial **adoptada**: swing proporcional uniforme sobre la base 23J
  (`web/src/data/base23.json`) + calibración + D'Hondt por provincia + 10.000 simulaciones.
- Superficies web existentes: `prediccion/` (MapaProvincial + tablas por provincia con
  IC95), `index.astro` (escaños estatales desde el modelo provincial), `simulador/`
  (simulador del visitante acotado a p10–p90 del backtest).
- Backtest provincial 2015-2023 ya ejecutado, con decisión documentada en
  `docs/notes/mrp.md`: **el MRP no bate al swing uniforme** (MAE ~1,0 pp vs ~0,83 pp);
  la variante anclada empata. No se adopta, no se genera `seats_mrp.json`.
  Regla del proyecto: la honestidad manda sobre el branding — esta decisión NO se
  relitiga en este plan.
- Existe además módulo de microdatos CIS (`pipeline/microdatos/`) y scoring de
  encuestadores.

**Fuera de alcance (explícito):** re-adoptar el MRP, generar `seats_mrp.json`,
repetir el backtest del MRP, y publicar sin revisión de Chema.

## Alcance real (el delta que falta)

### A) Agregación por Comunidad Autónoma
- Hoy la web muestra los 52 territorios sin vista agregada por CCAA (verificado:
  0 referencias a ccaa en `web/src/components` y `web/src/lib`).
- Añadir a `prediccion/` (y opcionalmente `index/`): agrupación de las 52 provincias
  en sus 19 CCAA con escaños estimados por partido (suma de provincias),
  coherente con el total estatal (350).
- Mapeo provincia→CCAA: derivar de `web/src/data/base23.json` /
  `web/src/data/microdatos/por_provincia.json` (o fichero de datos propio).
- Sin nuevo cálculo de modelo: es agregación del output existente (`seats.json`,
  `forecast.json`).

### B) Benchmark ElElectoral (Andalucía)
- Referencia: tuit de @ElElectoral (2026-10-24) — estimación de generales para
  Andalucía desde microdatos del CIS: PP primera fuerza (+4 sobre PSOE),
  VOX ~20 %, Adelante sin representación.
- Comparar con nuestra traslación vigente para las 8 provincias andaluzas (61 escaños).
- Entregable: `docs/notes/benchmark-elelectoral.md` — tabla comparativa,
  metodologías (su MRP-CIS vs nuestro swing+encuestas), divergencias y lectura honesta.
- Opcional (solo si el tiempo acompaña): replicar su vía con el módulo
  `pipeline/microdatos/` como segunda señal. No bloquea el cierre del plan.

## Checklist

- [x] Rama `feat/ccaa-benchmark` desde main.
- [x] A1: mapeo provincia→CCAA disponible como dato (`web/src/data/provincias-ccaa.json`:
      19 CCAA, 52 provincias con códigos INE, sin duplicados; verificado contra seats.json).
- [x] A2: agregación CCAA en `prediccion/` (suma = 350 escaños ✓; verificación en build:
      la página lanza error si la suma de las 52 provincias deja de ser 350).
- [x] A3: estilo coherente con el sitio (honestidad: etiquetar como agregación
      del modelo provincial, sin prometer precisión adicional).
- [x] B1: comparativa Andalucía vs ElElectoral en `docs/notes/`.
- [x] B2: lectura de divergencias (metodología, fuentes, fechas de campo).
- [x] Verificación: `astro build` + `astro check` verdes; curación manual del
      render en preview.
- [ ] Revisión del padre (diff + build + render) antes de push/merge.
- [ ] Push a main tras revisión.

## Criterios de aceptación

1. La vista CCAA suma exactamente los escaños provinciales publicados (350). ✓ verificado
2. Ningún número nuevo "de modelo": solo agregación del output existente. ✓
3. El benchmark no presenta ElElectoral como validación externa definitiva —
   es un contraste entre metodologías distintas. ✓
4. Build y check en verde; sin regresión visual en las páginas existentes. ✓

## Decisiones tomadas (para revisión del padre)

- **Sin intervalos a nivel CCAA:** los intervalos provinciales no se suman (no es
  estadísticamente válido) y `seats.json` no conserva el detalle por simulación
  necesario para calcularlos. La sección lo declara expresamente y enlaza al
  desglose provincial y al nacional. Choca a medias con el "la mediana nunca viaja
  sola" de DESIGN.md: se resuelve documentándolo, no inventando un intervalo.
- **Medias en céntimos:** la suma de medias se hace con aritmética entera
  (céntimos de escaño) y redondeo comercial a un decimal, para que un `.x5` exacto
  no oscile entre 8,3/8,4 según el orden en coma flotante.
- **Columnas de partido:** las diez fuerzas con media estatal ≥ 1,5 escaños en el
  orden nacional publicado + «Otros» (NA+, CUP, PACMA…). Evita una tabla de 14
  columnas con mayorías de celdas vacías.
- **Sin sección CCAA en la home:** la portada abre con el reparto estatal; añadir
  la agregación ahí duplicaba información y rompía la sobriedad. La vista vive en
  `prediccion/`, su sitio natural (el plan la marcaba opcional en home).
- **`astro check` en verde exigía tocar ficheros ajenos:** main ya traía 5 errores
  TS preexistentes (`rss.xml.ts` sin tipo de `context`, orden de fechas con `Date`
  en `rss.xml.ts` y `blog/index.astro`). Corregidos con cambios de tipado sin
  cambio de comportamiento (commit separado para que el padre lo revise suelto).

## Evidencia

**Tarea A — agregación CCAA**
- Fichero nuevo `web/src/data/provincias-ccaa.json`: 19 CCAA (códigos INE 01–19),
  52 provincias, 0 duplicados, cobertura completa comprobada contra `seats.json`.
- `web/src/pages/prediccion/index.astro`: sección «Por comunidad autónoma ·
  agregación del modelo provincial» entre el bloque nacional y los controles del
  mapa. 19 filas ordenadas por escaños en juego, 10 columnas de partido + «Otros»,
  fila Total con 350 y pie explicando el redondeo (suma de medias mostrada:
  349,9). Guard de build: falla si la suma ≠ 350.
- Verificación celda a celda (script Decimal ROUND_HALF_UP sobre el HTML
  compilado vs cálculo independiente): 19 filas + tfoot sin discrepancias.

**Tarea B — benchmark ElElectoral**
- Imagen del tuit descargada vía syndication API de X (`tweet-result`),
  transcrita con visión en 3 pasadas (completa + recortes de escaños y voto).
  La columna 2023 de la imagen coincide exactamente con el resultado oficial de
  Interior (PP 25/36,4 %, PSOE 21/33,5 %, VOX 9/15,3 %, Sumar 6/12,0 %), lo que
  valida la transcripción. El OCR local (tesseract) sirvió de segundo contraste.
- Nota en `docs/notes/benchmark-elelectoral.md`: tabla de escaños (horquillas vs
  suma de nuestras medias provinciales), contexto de voto con el aviso de ámbitos
  distintos, metodologías cara a cara y 5 puntos de lectura honesta. Sin
  presentación como validación; sin relitigar el MRP (se referencia `mrp.md`).

**Verificación técnica**
- `npm run build`: verde (11 páginas).
- `npm run check`: verde (0 errores, 0 avisos; los 5 errores TS preexistentes de
  main corregidos en commit propio).
- Suma CCAA = 350: verificada en el JSON, en el render (tfoot) y protegida con
  guard de build.
- Render curado con captura headless (chromium playwright 1243) a 1280 px:
  sección legible, tabla alineada, Total 350 visible; colores de partido y bandas
  ámbar presentes (verificación por muestreo de píxeles). Sin regresiones en
  componentes existentes.

**Commits** (en `feat/ccaa-benchmark`, sin push — pendiente de revisión)
1. `fix(web): tipa el GET del RSS y ordena las fechas del blog con getTime`
2. `feat(web): vista agregada por comunidad autónoma en la predicción`
3. `docs: benchmark ElElectoral (Andalucía) y evidencia del plan CCAA`

## Siguiente paso

Revisión de Chema → push → cutover de la página. Después: benchmark como
sección pública opcional en 29n.info si Chema lo quiere.
