# Web scaffold — 29N (Fase 5, paso 1)

**Fecha:** 2026-10-15 · **Autor:** agente (subagente de scaffold) · **Estado:** scaffold completo y verificado, sin deploy.

Scaffold de la web pública en `web/` con **Astro 5**, siguiendo `DESIGN.md` (contrato de diseño, formato Stitch) al pie de la letra. Contenido placeholder honesto: no hay ni un dato inventado; donde falta un número se nombra la fase que lo publicará.

---

## 1. Decisiones técnicas y por qué

### 1.1 Astro 5, salida estática, sin adapter todavía

- `astro@^5.18.2` + `output: 'static'`, `build.format: 'directory'`, `trailingSlash: 'always'`.
- **Sin adapter de Vercel.** El deploy es manual y de Fase posterior (indicación explícita de la tarea); añadir `@astrojs/vercel` ahora sería configurar un destino que no se ha decidido. `output: 'static'` se despliega en Vercel tal cual.
- **`site` sin fijar**, deliberadamente: no se inventa un dominio para no publicar metadatos falsos. Se fija antes del deploy.
- La web **solo lee**, no calcula (decisión ya tomada en `docs/plan.md`): la salida del pipeline será JSON estático.

### 1.2 Sin Tailwind 4 (decisión, no omisión)

DESIGN.md define un sistema **bespoke y tokenizado**: variables CSS con OKLCH, escalas `clamp()`, y componentes con reglas muy concretas (tablas sin cebra con reglas de 1 px, bandas de intervalo SVG, pliegos con notas al margen). Criterio aplicado:

- Los tokens de DESIGN.md **se traspasan tal cual** a `src/styles/tokens.css`. Con Tailwind habría que traducirlos a `@theme` → una capa intermedia que puede desincronizarse del contrato.
- Los componentes rey (tabla, banda, ficha) no son "árboles de utilidades": son CSS con container queries y SVG. En la práctica se escribirían igual, con Tailwind añadido encima.
- El coste real está en el resultado: **13,5 KB de CSS** para todo el sitio y cero dependencias de build añadidas.
- **Se puede añadir después** sin refactor traumático (`@tailwindcss/vite` + `@theme` mapeando las mismas custom properties). Si el equipo lo prefiere, es un cambio localizado en `astro.config.mjs` y `tokens.css`.

### 1.3 Tipografía: Fontsource, y solo los subconjuntos que usamos

Las tres familias del contrato, servidas en local (sin peticiones a Google Fonts):

| Familia | Entrada | Pesos |
|---|---|---|
| Newsreader (variable, `opsz`) | `@fontsource-variable/newsreader/opsz.css` + `opsz-italic.css` | 400–800, itálica |
| Source Sans 3 | `@fontsource/source-sans-3/latin-{400,600,700}.css` | 400/600/700 |
| IBM Plex Mono | `@fontsource/ibm-plex-mono/latin-{400,500}.css` | 400/500 |

- Se importan **solo los subconjuntos `latin`** de Source Sans 3 y Plex Mono (incluye el suplemento latin-1: `á é í ó ú ñ ü ¿ ¡`). Esto evitó enviar cyrillic/vietnamese.
- **Efecto medido:** `dist/` pasó de **1,6 MB a 848 KB** y de **37 a 11 ficheros `.woff2`**.
- Newsreader variable no ofrece entrada por subconjunto, así que emite también latin-ext y vietnamese; **el navegador no los descarga** porque el `unicode-range` del `@font-face` lo impide. Es coste de disco, no de red.

### 1.4 Tipos compartidos

`src/lib/tipos.ts` define `Columna`, `Celda`, `Fila`… El componente `DataTable` los importa y las páginas anotan sus arrays de columnas. Esto nació de una verificación real: `astro check` reportó 5 errores de tipo porque los literales de columna ensanchaban `tipo` a `string`. Se corrigió con el tipo compartido, no con `as any`.

### 1.5 Verificación de tipos incluida en el proyecto

`npm run check` → `astro check` (con `@astrojs/check` + `typescript` como devDependencies). Hoy: **0 errores, 0 avisos, 0 hints**.

---

## 2. Estructura creada

```
web/
├── astro.config.mjs        Salida estática, trailing slash, sin adapter
├── package.json            Astro 5 + 3 Fontsource + check tooling
├── tsconfig.json           astro/tsconfigs/strict
├── public/favicon.svg
└── src/
    ├── lib/tipos.ts                    Tipos compartidos de la capa de datos
    ├── styles/
    │   ├── tokens.css                  DESIGN.md §2/§3/§5 traspasado literal
    │   └── base.css                    Reset + primitivas editoriales (GOV.UK-ish)
    ├── layouts/Base.astro              lang="es", fuentes, skip-link, header/footer
    ├── components/
    │   ├── Header.astro                Logo 29N + nav (details nativo en móvil)
    │   ├── Footer.astro                Licencia MIT + fuentes
    │   ├── Breadcrumbs.astro           Separador "/" en mono (EU Design System)
    │   ├── DataTable.astro             Tabla rey: fuente encima, tabular-nums, filas clave-valor en móvil
    │   ├── IntervalBand.astro          Banda de intervalo SVG (modos `esquema` / `vacio`)
    │   ├── SourceCard.astro            Ficha de fuente (nivel 1 de elevación)
    │   ├── Timeline.astro              Línea temporal electoral sobre una regla
    │   └── MapaProvincial.astro        Retícula del coroplético + trama "sin predicción"
    └── pages/
        ├── index.astro                 Portada asimétrica (2/3 + 1/3 escalonado)
        ├── encuestas/index.astro       Filtros (320 px sticky) + tabla + ficha
        ├── resultados/index.astro      Timeline + escaños + comparador
        ├── prediccion/index.astro      "Qué predecimos y qué no" → mapa + panel + tabla paralela
        ├── metodologia/index.astro     Long-form: prosa 68 ch + notas al margen en mono
        └── 404.astro
```

---

## 3. Evidencia

### 3.1 `npm run build` — salida real (exit code 0)

```
> 29n-web@0.1.0 build
> astro build

10:26:55 [content] Syncing content
10:26:55 [content] Synced content
10:26:55 [types] Generated 58ms
10:26:55 [build] output: "static"
10:26:55 [build] mode: "static"
10:26:55 [build] directory: /root/.openclaw/workspace/projects/29n/web/dist/
10:26:55 [build] Collecting build info...
10:26:55 [build] ✓ Completed in 78ms.
10:26:55 [build] Building static entrypoints...
10:26:56 [vite] ✓ built in 925ms
10:26:56 [build] ✓ Completed in 959ms.

 generating static routes 
10:26:56 ▶ src/pages/404.astro
10:26:56   └─ /404.html (+8ms) 
10:26:56 ▶ src/pages/encuestas/index.astro
10:26:56   └─ /encuestas/index.html (+4ms) 
10:26:56 ▶ src/pages/index.astro
10:26:56   └─ /index.html (+3ms) 
10:26:56 ▶ src/pages/metodologia/index.astro
10:26:56   └─ /metodologia/index.html (+3ms) 
10:26:56 ▶ src/pages/prediccion/index.astro
10:26:56   └─ /prediccion/index.html (+2ms) 
10:26:56 ▶ src/pages/resultados/index.astro
10:26:56   └─ /resultados/index.html (+2ms) 
10:26:56 ✓ Completed in 35ms.

10:26:56 [build] 6 page(s) built in 1.08s
10:26:56 [build] Complete!
```

### 3.2 `npm run check` — salida real

```
10:26:31 [content] Syncing content
10:26:31 [content] Synced content
10:26:31 [types] Generated 56ms
10:26:31 [check] Getting diagnostics for Astro files in /root/.openclaw/workspace/projects/29n/web...
Result (18 files): 
- 0 errors
- 0 warnings
- 0 hints
```

### 3.3 Rutas servidas en local (`python3 -m http.server` sobre `dist/`)

```
home=200
encuestas=200
resultados=200
prediccion=200
metodologia=200
```

### 3.4 Artefactos

- `dist/` = **848 KB**, 6 páginas HTML, 1 hoja de estilos (13,5 KB), 11 ficheros `.woff2`.
- Tokens OKLCH presentes en el bundle (verificado por `grep` sobre `dist/_astro/*.css`): `oklch(.24 .02 260)` (tinta), `oklch(.42 .14 265)` (enlace), `oklch(.32 .11 265)` (acción), `oklch(.45 .09 155)` (ok), `oklch(.52 .17 28)` (PSOE), `oklch(.45 .13 250)` (PP), etc.
- `git status` en la raíz del repo: solo `?? web/`. `node_modules/`, `dist/` y `.astro/` quedan fuera por el `.gitignore` existente. **No se tocó** `DESIGN.md`, `pipeline/`, `data/` ni se hizo commit/push.

---

## 4. Decisiones de contenido (honestidad)

Toda ausencia de dato se declara con un marcador `.pendiente` que nombra la fase:

| Zona | Marcador |
|---|---|
| Contador de encuestas, catálogo | `en construcción — dato disponible en Fase 1` |
| Escrutinio, escaños, comparador, timeline | `en construcción — dato disponible en Fase 2` |
| Serie estatal, backtest, intervalos | `en construcción — dato disponible en Fase 4` |
| Mapa provincial, JSON de predicción | `en construcción — dato disponible en Fase 5` |

- **Estados vacíos que enseñan**, no que se disculpan (DESIGN.md §4): p. ej. el catálogo explica que se publica al cerrar la Fase 1; el log de exclusiones explica por qué está vacío.
- **Los controles de filtro están `disabled`** a propósito: es más honesto un control inactivo explicado que un filtro que parece funcionar y no hace nada. Se muestran ya restyleados para fijar la estructura (controles nativos, operables por teclado).
- La banda de intervalo tiene modo `esquema` (dibuja la FORMA, rotulada `esquema · sin valores`) y modo `vacio` (esqueleto neutro en `--papel-3`). El color firma `--intervalo` **no** se usa para decorar nada.
- Años de elecciones generales 1977–2023 en la timeline: es un **hecho público**, no un dato inventado.

---

## 5. Accesibilidad implementada en el scaffold

- `lang="es"` en `<html>`; skip-link a `#contenido`.
- Foco visible `--foco` de 3 px con offset 2 px en todo lo interactivo.
- `DataTable`: `scope="col"`, fuente clicable **encima** de la tabla, y en móvil cada fila se apila como clave-valor vía **container query** (no se amputa ninguna columna).
- `IntervalBand`: `role="img"` con `aria-label`, más `<details>` con la tabla alternativa.
- `MapaProvincial`: el mapa nunca es el único camino; `prediccion/` incluye la **tabla paralela de provincias**.
- Deltas: el color marca **solo** el signo (`+`/`−`; `--ok`/`--alerta`) y el valor va en tinta; se añade texto oculto "sube/baja" para lectores de pantalla.
- Header en móvil: `details` nativo, sin JS para navegar.
- `prefers-reduced-motion` desactiva la única entrada orquestada.

---

## 6. Verificaciones pendientes (no hechas)

1. **Comprobación visual en navegador.** No fue posible en este entorno: Camoufox corre fuera del host y no alcanza el servidor local; Chromium headless escribió el PNG pero el `/tmp` de las llamadas `exec` no persiste entre invocaciones. **Pendiente:** abrir `npm run dev` y revisar portada, `/encuestas/` y `/prediccion/` en 360 / 768 / 1440 px.
2. **Test de daltonismo** (deuteranopía/protanopía) sobre los colores de partido, obligatorio antes de publicar cualquier gráfico nuevo (DESIGN.md §7.2).
3. **Zoom al 200 %** sin pérdida de contenido.
4. **Deploy:** explícitamente fuera de alcance. Vercel es manual y de fase posterior.

---

## 7. Siguiente paso sugerido

1. Revisión visual humana (pendiente nº 1) y ajustes finos de ritmo vertical.
2. Decidir si se adopta Tailwind 4 sobre esta base (§1.2) o se mantiene CSS nativo.
3. Fijar `site` en `astro.config.mjs` y añadir el adapter de Vercel **cuando** exista el dominio y la decisión de despliegue.
4. Sustituir los marcadores `.pendiente` por datos reales conforme cierren las fases 1, 2, 4 y 5 — el contrato de cada bloque ya está fijado en los tipos de `src/lib/tipos.ts`.
