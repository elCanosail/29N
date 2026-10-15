# Explorador de microdatos CIS — UI (29N)

Fecha: 2026-10-15 · Feature 2 del plan de valor diferencial (`docs/plans/features-diferenciales.md`).
Scope de escritura: `pipeline/microdatos/agrega.py`, `web/src/data/microdatos/`,
`web/src/pages/microdatos/`, `web/src/lib/microdatos-explorador.ts`, este documento.
**No se ha tocado** `Header.astro` (el nav lo engancha el padre), `DESIGN.md`,
`sync-data.py`, `data/processed/` (escritura) ni otras páginas. Sin commit ni push.

## 1. Qué se ha construido

La herramienta única del proyecto: los **532.498 microdatos del CIS (1977–2025)**
consultables desde la web, con agregados precalculados en estático y filtros
client-side (sin servidor).

- `pipeline/microdatos/agrega.py` → 5 JSON en `web/src/data/microdatos/`.
- `web/src/pages/microdatos/index.astro` → página `/microdatos/` con los filtros y las visualizaciones.
- `web/src/lib/microdatos-explorador.ts` → lógica de selección y dibujo de gráficos (SVG a mano, sin dependencias).

Todo agregado pondera **siempre** por `peso`. Los pesos se **normalizan por estudio**
(suma = n del estudio) antes de agrupar, porque los estudios no comparten escala de
ponderación (los europeas de 1989 traen pesos ~1e6); sin normalizar, un estudio
dominaría el agregado por su escala y no por su muestra.

## 2. Los cinco cortes (JSON)

| Archivo | Corte | Contenido |
|---|---|---|
| `por_anio.json` | Intención por año | n, % de intención por partido canónico, ideología media, % con recuerdo de voto |
| `por_provincia.json` | Intención por provincia | agregado 2015–2025, % por partido, n y nº de estudios por provincia |
| `ideologia_partido.json` | Ideología por partido votado | media, p25, p75 y distribución 1–10 de cada electorado |
| `perfil_partido.json` | Perfil por partido | edad media, % sexo, % por 6 niveles de estudios |
| `serie_ideologia.json` | Serie de ideología | media anual 1–10 con p25/p75 y n |

Cada archivo lleva su bloque `meta` con `generacion` (única fecha viva del archivo),
fuente, cobertura, ponderación, `base` y `advertencias`. Los bloques de datos no
contienen fechas del sistema → el script es reproducible: dos ejecuciones sobre el
mismo parquet producen datos idénticos (solo cambia `meta.generacion`).

### Decisiones de agregación documentadas

- **Partido canónico (familia política).** AP/UCD → PP; PODEMOS/UNIDAS PODEMOS/IU/
  Compromís/Más País → SUMAR; JUNTS/CIU → JXCAT; Geroa Bai → PNV; UPN → NA+; el resto
  de minoritarios → OTROS. Continuidad de series entre eras (DESIGN.md §2).
- **Base = censo.** Denominador = total de entrevistas del grupo (incluye abstención,
  NS, NC y no declarado). Los partidos suman < 100 % por eso. Comprobado: la suma de
  categorías da 100,0 % en todos los años y provincias.
- **Cobertura mínima de intención (≥ 50 %).** 10 estudios (2004–2011 y europeas 1989)
  no traen la pregunta de intención extraída; incluirlos fabricaría ceros falsos.
  Quedan fuera de los cortes de voto y aparecen como **hueco**, no como 0.
- **Edad 15–100.** Se descartan edad 0 y fuera de rango.
- **Estudios → 6 niveles**: Sin estudios · Primaria · Secundaria · FP · Superiores · NC/Otros.

### Verificación de los datos (sanity)

- Suma de categorías = 100,000 % en los 16 años con intención y en las 52 provincias.
- Ejemplos: 2019 PSOE 19,68 % / PP 10,66 % / VOX 3,52 % / SUMAR 8,25 %; 2023 PSOE 20,17 % /
  PP 18,35 % / VOX 7,56 % / SUMAR 13,34 %.
- Ideología por partido (media 1–10): CUP 2,28 · EH Bildu 2,30 · Sumar 2,92 · PSOE 3,60 ·
  PNV 4,73 · PNV/JxCat ~4,97 · PP 6,69 · VOX 7,62. Total 4,74. (Orden coherente
  izquierda→derecha, sin valores imposibles.)
- Provincias: n agregado entre 908 y 22.226 entrevistas (n por celda publicado siempre).

## 3. Página `/microdatos/`

- Cabecera editorial: eyebrow + `<h1>Microdatos CIS 1977-2025</h1>` + una línea de entrada.
- **Visual arriba** (regla de jerarquía DESIGN.md §5): filtros (columna izquierda sticky)
  + gráfico + tabla con los mismos números, en las primeras pantallas.
- **Texto abajo**: bloque «Cómo leerlo» con la base CIS, la ponderación, los huecos y el
  partido canónico, más un panel de advertencias de base.
- Filtros nativos (`select`, restyleados GOV.UK): **Corte**, **Año**, **Provincia**.
  El campo de año/provincia se oculta cuando el corte no lo usa; `select` deshabilitado
  de verdad (`disabled`) para lectores de pantalla.
- Gráficos: líneas con etiquetas directas al final, banda `--intervalo` para la
  dispersión de ideología, barras con trama rayada para el no-voto (no color de partido).
- Accesibilidad (DESIGN.md §7): el SVG lleva `role="img"` y `aria-label` con la
  conclusión; debajo hay **siempre** una tabla con los mismos números; estado vacío útil;
  foco visible; sin desbordamiento horizontal a 390/768/1280 px.

## 4. Evidencia (salida real)

```
$ npm run check

> 29n-web@0.1.0 check
> astro check

21:03:50 [content] Syncing content
21:03:50 [content] Synced content
21:03:50 [types] Generated 58ms
21:03:50 [check] Getting diagnostics for Astro files in /root/.openclaw/workspace/projects/29n/web...
Result (25 files):
- 0 errors
- 0 warnings
- 0 hints
```

```
$ npm run build

> 29n-web@0.1.0 build
> astro build

21:03:55 [content] Syncing content
21:03:55 [content] Synced content
21:03:55 [types] Generated 35ms
21:03:55 [build] output: "static"
21:03:55 [build] mode: "static"
21:03:55 [build] directory: /root/.openclaw/workspace/projects/29n/web/dist/
21:03:55 [build] Collecting build info...
21:03:55 [build] ✓ Completed in 57ms.
21:03:55 [build] Building static entrypoints...
21:03:56 [vite] ✓ built in 1.27s
21:03:56 [build] ✓ Completed in 1.31s.

 building client (vite)
21:03:56 [vite] transforming...
21:03:56 [vite] ✓ 9 modules transformed.
21:03:56 [vite] rendering chunks...
21:03:56 [vite] computing gzip size...
21:03:56 [vite] dist/_astro/index.astro_astro_type_script_index_0_lang.BTO636fH.js  56.51 kB │ gzip: 15.80 kB
21:03:56 [vite] ✓ built in 75ms

 generating static routes
21:03:56 ▶ src/pages/404.astro
21:03:56   └─ /404.html (+11ms)
21:03:56 ▶ src/pages/encuestas/index.astro
21:03:56   └─ /encuestas/index.html (+33ms)
21:03:56 ▶ src/pages/index.astro
21:03:56   └─ /index.html (+11ms)
21:03:56 ▶ src/pages/metodologia/index.astro
21:03:56   └─ /metodologia/index.html (+9ms)
21:03:57 ▶ src/pages/microdatos/index.astro
21:03:57   └─ /microdatos/index.html (+3ms)
21:03:57 ▶ src/pages/prediccion/index.astro
21:03:57   └─ /prediccion/index.html (+29ms)
21:03:57 ▶ src/pages/resultados/index.astro
21:03:57   └─ /resultados/index.html (+35ms)
21:03:57 ▶ src/pages/simulador/index.astro
21:03:57   └─ /simulador/index.html (+6ms)
21:03:57 ✓ Completed in 172ms.

21:03:57 [build] 8 page(s) built in 1.63s
21:03:57 [build] Complete!
```

### Comprobación en navegador (Playwright + chromium del sistema)

Servido `web/dist` y cargado `/microdatos/` headless: **0 errores de consola /
0 pageerrors**. Los cinco cortes renderizan SVG y tabla:

```
{"cortes":5,"anios":17,"provs":53,"svg":true,"tabla":17,
 "aria":"Serie de intención de voto por año, 1977–2025, sobre censo CIS."}
serie_ideologia    {"svg":true,"rows":15}
intencion_provincia{"svg":true,"rows":22}
ideologia_partido  {"svg":true,"rows":17}
perfil_partido     {"svg":true,"rows":17}
intencion_anio     {"svg":true,"rows":17}
anio 2023 pie: Estudio(s) 2023 · 79.707 entrevistas · 79.707 con intención declarada
madrid  pie:   Madrid · 22.226 entrevistas (2015–2025) · % sobre censo (CIS)
```

Sin desbordamiento horizontal (`scrollWidth == innerWidth`) a 390, 768 y 1280 px.
(Se corrigió un desbordamiento de 14 px a 390 px: la ruta mono
`data/processed/microdatos/individual.parquet` forzaba el ancho mínimo de la columna
grid; resuelto con `minmax(0,…)` + `overflow-wrap: anywhere` en el bloque «Cómo leerlo».)

## 5. Reproducir

```bash
/root/.venvs/29n-micro/bin/python pipeline/microdatos/agrega.py   # regenera los 5 JSON
cd web && npm run check && npm run build                          # verificación
```

## 6. Siguiente paso (del padre)

1. Enganchar `/microdatos/` en `Header.astro` / portada (no lo hace este subagente).
2. Decidir si se añade enlace de descarga del JSON/parquet (feature 6, corpus abierto).
3. Revisar el diff y las pruebas antes de commit; push según política del repo.
