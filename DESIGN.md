# DESIGN.md — 29N

Sistema de diseño de la web pública de 29N: histórico de encuestas (CIS + encuestadores privados), resultados oficiales 1977–2023 y predicción provincial del 29N con TimesFM. Audiencia: periodistas y público general. Contenido en español.

Formato: especificación de [Google Stitch para DESIGN.md](https://stitch.withgoogle.com/docs/design-md/specification/).

---

## 1. Tema visual y atmósfera

**Dirección: "gaceta de datos" — editorial de periódico con rigor de organismo estadístico.**

La web se siente como la cruce entre una página de datos de un portal nórdico de datos abiertos ([data.norge.no](https://data.norge.no), [avoindata.fi](https://www.avoindata.fi)) y un artículo largo de [The Pudding](https://pudding.cool). Papel claro, tinta densa, reglas horizontales finas, números tabulares por todas partes. Nada de dashboards, nada de tarjetas con sombra, nada de "hero" con degradado.

- **Filosofía:** los datos son el héroe. Toda la superficie visual existe para que una tabla, una serie temporal o un mapa provincial se lean sin fricción y sin ambigüedad.
- **Densidad:** media-alta, herencia de GOV.UK y de la prensa escrita. El aire no se desperdicia en decoración: se usa para agrupar y jerarquizar.
- **Cero decoración sin función.** Si un elemento no ayuda a leer un dato, comparar dos fechas o entender una incertidumbre, no existe. No hay ilustraciones gratuitas, no hay iconos en cada titular, no hay glassmorphism ni degradados.
- **Honestidad visual = honestidad metodológica.** La estética replica los compromisos del repo: cada cifra enlaza a su fuente, cada predicción lleva intervalo, cada exclusión se documenta. El diseño no debe poder "maquillar" un dato: si un número está mal, tiene que verse mal.
- **Qué recordará el visitante:** las bandas de intervalo ámbar. En 29N la incertidumbre no es una letra pequeña: es el elemento gráfico protagonista y tiene un color propio, inconfundible.

**Referencias estudiadas y qué tomamos de cada una:**

| Referencia | Qué adoptamos |
|---|---|
| [GOV.UK Design System](https://design-system.service.gov.uk/) | Tipografía de lectura sobre papel claro, links siempre subrayados, foco visible amarillo de 3 px, lenguaje llano, formularios y tablas sin adornos. |
| [EU Design System (EUIP)](https://design-system.europa.eu/) | Jerarquía institucional sobria, breadcrumbs y encabezados predecibles, respeto por múltiples lenguas de datos oficiales. |
| [data.gov.es](https://data.gov.es) y portales nórdicos de datos abiertos | Densidad tabular honesta, descargas visibles junto al dato, metadatos y licencias en primer plano. |
| [The Pudding](https://pudding.cool) | El dato como narrativa: gráficos con anotación en el propio lienzo, escalas que se explican solas, intro editorial que engancha antes de la tabla. |

---

## 2. Paleta de color y roles

Espacio **OKLCH**. Toda la paleta está tintada hacia el tono de tinta (azul-pizarra frío), incluidos los neutros: no existe negro puro ni blanco puro. Contraste mínimo **AA (4.5:1)** para texto y **3:1** para gráficos grandes y bordes de significado; los pares listados están verificados.

### Superficies y tinta

| Token | Valor | Rol |
|---|---|---|
| `--papel` | `oklch(0.985 0.004 95)` | Fondo de página. Blanco cálido de papel de periódico. |
| `--papel-2` | `oklch(0.962 0.006 95)` | Banda alterna de tabla, fondos de sección de metodología. |
| `--papel-3` | `oklch(0.93 0.008 95)` | Estado hover de filas, código en línea. |
| `--tinta` | `oklch(0.24 0.02 260)` | Texto principal, ejes, líneas de datos. Casi negro azulado (~13.5:1 sobre papel). |
| `--tinta-2` | `oklch(0.42 0.02 260)` | Texto secundario, etiquetas de eje, metadatos (~7:1). |
| `--tinta-3` | `oklch(0.55 0.02 260)` | Sólo para texto terciario ≥18.66 px bold o equivalente AA; nunca para párrafos. |
| `--regla` | `oklch(0.87 0.01 260)` | Reglas horizontales, bordes de tabla, gridlines. |
| `--enlace` | `oklch(0.42 0.14 265)` | Links, siempre subrayados (~6.5:1). Subrayado también en hover. |
| `--foco` | `oklch(0.88 0.17 95)` | Anillo de foco: amarillo GOV.UK reinterpretado, 3 px. |
| `--accion` | `oklch(0.32 0.11 265)` | Botón primario (único). Fondo azul-tinta profundo, texto `--papel`. |

### Colores de significado (datos e incertidumbre)

| Token | Valor | Rol |
|---|---|---|
| `--intervalo` | `oklch(0.82 0.13 85)` @ 55–65% opacidad | **El color firma del proyecto.** Banda de incertidumbre en series y mapas. Nunca se usa para decorar. |
| `--intervalo-borde` | `oklch(0.72 0.14 85)` | Contorno de la banda / p10 y p90 marcados. |
| `--alerta` | `oklch(0.55 0.19 28)` | Errores de validación, encuestas excluidas, "datos insuficientes" cuando hay que leerlo rápido (~5:1 sobre papel). |
| `--ok` | `oklch(0.45 0.09 155)` | Validación superada, dato trazado y verificado. Verde apagado, nada "success-page". |

### Colores de partido (son datos, no marca)

Los colores de partido son una convención que la audiencia (periodistas) ya conoce: usarlos es claridad, no decoración. Se definen **estandarizados y con variantes de tinta** para que la identificación funcione en texto, línea y mapa:

| Partido / familia | Token | Valor | Uso |
|---|---|---|---|
| PSOE | `--p-psoe` | `oklch(0.52 0.17 28)` | Rojo convencional, ligeramente oscurecido para AA en texto. |
| PP | `--p-pp` | `oklch(0.45 0.13 250)` | Azul convencional oscurecido. |
| Vox | `--p-vox` | `oklch(0.52 0.12 145)` | Verde convencional. |
| Sumar / Izquierda (verde-púrpura) | `--p-sumar` | `oklch(0.50 0.13 320)` | Púrpura-magenta. |
| Podemos (histórico) | `--p-podemos` | `oklch(0.48 0.11 310)` | Púrpura más frío; en series se distingue de Sumar por **patrón**, no sólo tono. |
| Cs | `--p-cs` | `oklch(0.62 0.13 80)` | Naranja; sólo para ≥3:1 (trazo grueso o banda). |
| ERC / nacionalistas | `--p-erc` | `oklch(0.58 0.14 40)` | Amarillo-naranja. |
| PNV | `--p-pnv` | `oklch(0.50 0.10 200)` | Verde azulado. |
| Otros | `--p-otros` | `oklch(0.60 0.01 260)` | Gris tinta. |

Reglas de partido:

1. Los colores de partido **nunca** se usan en botones, links, fondos de página ni decoración. Su único dominio son gráficos, mapas, tablas y leyendas.
2. En una misma serie se distinguen por **tono Y luminosidad alternada** (nunca 6 líneas con la misma L). Los partidos históricamente confundidos para daltónicos (rojo/verde: PSOE–Vox) se separan además por luminosidad o patrón de trazo (`stroke-dasharray`).
3. Fuera del canvas del gráfico, el nombre del partido va siempre en texto (`--tinta`), con la muestra de color como apoyo.

### Antipatrones de color (prohibidos)

- Modo oscuro con acentos neón, cian sobre negro, degradados púrpura→azul.
- Texto gris sobre fondo de color: sobre superficies teñidas se usa un tono del propio `--papel`.
- Texto con degradado, y en general cualquier métrica "adornada".
- Usar el amarillo de foco (`--foco`) para otra cosa que no sea foco.

---

## 3. Reglas tipográficas

Tres familias, cada una con un trabajo. Nada de Inter, Roboto ni system-ui como identidad.

| Familia | Rol | Carga |
|---|---|---|
| **Newsreader** (Google Fonts, variable, `opsz`) | Titulares, intros editoriales, citas metodológicas, números romanos de sección. Tiene carácter de diario: nuestra voz. | Variable, `opsz` 6–72, pesos 400–800, itálicas para notas al margen. |
| **Source Sans 3** | Cuerpo, UI, tablas, labels de gráfico. Humanista, x-height alta, aguanta texto español denso y columnas estrechas. | Pesos 400/600/700. |
| **IBM Plex Mono** | Cifras tabulares, IDs de encuesta (p. ej. `CIS-3292`), fichas técnicas, fechas de campo, anotaciones de datos dentro de gráficos. | Pesos 400/500. |

Reglas duras:

1. **Cifras en datos: siempre `font-variant-numeric: tabular-nums`** (Plex Mono ya lo es). En tablas y ejes es innegociable: los dígitos alinean.
2. Los porcentajes de predicción se muestran como `42,1 %` (coma decimal, espacio fino antes de %): español periodístico.
3. Fechas en formato largo editorial (`3 de noviembre de 2019`) en prosa; ISO (`2019-11-10`) en tablas y metadatos, en Plex Mono.
4. Los números de encuesta y los identificadores (`CIS-3292`, `GAD3-2023-07`) son siempre Plex Mono: son "direcciones" hacia la fuente.

### Escala (fluida con `clamp()`)

| Token | Tamaño (móvil → desktop) | Peso | Uso |
|---|---|---|---|
| `--t-display` | `clamp(2.6rem, 7vw, 4.6rem)` | Newsreader 700 | Titular de portada. |
| `--t-h1` | `clamp(2rem, 4.5vw, 3rem)` | Newsreader 600 | Título de sección/página. |
| `--t-h2` | `clamp(1.5rem, 3vw, 2.1rem)` | Newsreader 600 | Subsección, título de gráfico. |
| `--t-h3` | `1.2rem` | Source Sans 700 | Encabezados de tabla, filtros. |
| `--t-body` | `1.0625rem` / `line-height 1.65` | Source Sans 400 | Prosa. Ancho máximo de medida: 68 ch. |
| `--t-small` | `0.875rem` / 1.5 | Source Sans 400 | Metadatos, pie de gráfico, notas. |
| `--t-data` | `0.9rem` | IBM Plex Mono 400 | Tablas de datos, ejes, IDs. |
| `--t-eyebrow` | `0.75rem`, `letter-spacing 0.12em`, mayúsculas | Source Sans 700 | Etiquetas de sección ("ENCUESTAS · 1979–2023"). Uso escaso, sólo sobre secciones. |

La jerarquía de una página de datos es: **titular Newsreader → regla horizontal → label mono → tabla/gráfico → nota pequeña**. Ese ritmo se repite en todo el sitio.

---

## 4. Estilos de componentes

### Navegación

- Header plano sobre `--papel`, altura 64 px, borde inferior de 2 px en `--tinta` (regla de periódico, no sombra).
- Wordmark "29N" en Newsreader 800 + descriptor "Datos electorales de España" en `--t-small`.
- Links de sección en Source Sans 600, subrayados en hover y en página activa (subrayado grueso de 3 px bajo el ítem activo, estilo GOV.UK).
- Sin mega-menus. Breadcrumbs (estilo EU design system) en páginas profundas, con `/` separador mono.

### Botones

| Variante | Estilo | Uso |
|---|---|---|
| Primario | Fondo `--accion`, texto `--papel`, radio 4 px, peso 600. | Uno por vista ("Ver predicción provincial", "Descargar CSV"). |
| Secundario | Borde 2 px `--tinta`, fondo transparente. | Acciones de la misma jerarquía ("Comparar elecciones"). |
| Ghost / link | Solo texto subrayado + flecha `→`. | "Ver ficha técnica", "Ver log de exclusiones". |

No hay más de un primario visible por vista. Radio global: 4 px (nada pill, nada de esquinas de 24 px "app").

### Tablas (componente rey)

- Bordes horizontales de 1 px en `--regla`; cabecera con borde inferior de 2 px en `--tinta` y en mayúsculas pequeñas.
- Filas: hover `--papel-3`; **sin cebra**, la regla basta.
- Columna de fecha y de cifras en Plex Mono tabular. Los porcentajes se alinean a la derecha.
- Toda tabla lleva encima su fuente clicable y su fecha de extracción, en `--t-small`.
- Ordenación por columna con botones reales accesibles (no `div` clicables).

### Gráficos

- Fondo transparente sobre `--papel`; gridlines horizontales de 1 px en `--regla`, **sin gridline vertical**.
- Ejes en `--tinta-2`, labels mono. Sin bordes de caja alrededor del gráfico.
- **Anotación en el lienzo:** al estilo The Pudding, los hitos se explican con texto directamente sobre el gráfico (notas de Newsreader itálica con línea guía de 1 px): p. ej. "moción de censura, jun 2017". Mejor una anotación buena que una leyenda larga.
- La leyenda sustituye al color cuando hay más de 6 series: etiquetas directas al final de la línea, no leyenda aparte.
- Tooltips: caja de `--tinta` con texto `--papel`, radio 4 px, contenido en mono: fecha, valor, intervalo, fuente.

### Mapa provincial

- Coroplético sobre silueta de provincias, categorías por quantiles o pasos fijos declarados en la leyenda (la leyenda muestra los cortes exactos, nunca "bajo/medio/alto" a secas).
- Provincias sin predicción válida: **trama de rayado** (`--papel-3` + `--regla`), nunca un gris ambiguo.
- Selección de provincia: borde 3 px `--tinta` + panel lateral sincronizado. Navegable por teclado (tabulación por provincia o lista paralela equivalente, ver §7).

### Formularios y filtros

- Estilo GOV.UK: label arriba del control, borde 2 px, foco con anillo `--foco` de 3 px + sombra interior `--tinta`.
- Los filtros del explorador son `checkbox`/`radio`/`select` nativos restyleados, no chips de diseño libre: deben poder usarse con lector de pantalla sin sorpresas.
- Errores: texto `--alerta` arriba del campo, borde del campo en `--alerta`, y resumen de errores al inicio del formulario con anclas.

### Estados

- **Cargando:** `skeleton` de líneas horizontales en `--papel-3` que respeta la forma de la tabla/gráfico. Sin spinners decorativos.
- **Vacío:** el estado vacío enseña, no disculpa. P. ej. para una provincia sin encuestas: *"No hay encuestas provinciales publicadas para Badajoz en esta legislatura. Los agregados autonómicos sí están disponibles →"*.
- **Error de dato (validación fallida):** banner plano de borde izquierdo 4 px en `--alerta` con enlace al log de exclusiones. El diseño del error es parte de la honestidad del proyecto.
- **Movimiento:** una sola entrada orquestada por página (stagger sutil de titular → regla → gráfico, 200–350 ms, `ease-out-quart`). Nada más. `prefers-reduced-motion` desactiva todo.

---

## 5. Principios de layout

- **Grid editorial:** contenedor máximo 1200 px; el contenido de prosa vive en una columna de 68 ch alineada a la izquierda, con margen asimétrico para notas al margen (200–280 px) en desktop. Nada centrado por defecto: titulares y textos a la izquierda, como un pliego.
- **Escala de espacio:** `--s-1: 4px · --s-2: 8px · --s-3: 16px · --s-4: 24px · --s-5: 40px · --s-6: 64px · --s-7: clamp(64px, 10vw, 128px)`. Ritmo deliberado: agrupaciones apretadas (`--s-2`) dentro de un bloque, separaciones grandes (`--s-6/7`) entre bloques — nunca el mismo padding en todas partes.
- **Reglas horizontales como costura:** los separadores son líneas de 1–2 px en `--regla`/`--tinta`, no espacios vacíos gigantes ni cajas.
- **Sin tarjetas por defecto.** Un dato no necesita caja. Las cajas se reservan para: el panel de provincia seleccionada, el banner de metodología y las fichas de encuesta dentro del explorador. Nunca tarjetas dentro de tarjetas, nunca grids de tarjetas idénticas con icono+titulo+texto.
- **El dato arriba:** en cada sección, el gráfico o la tabla aparece en las dos primeras pantallas de scroll. La prosa invita, el dato responde.

### Layout por secciones

**Home — "el resultado, luego el desglose":**
1. Cabecera: titular "29N, estimación de resultados" (Newsreader grande) + intro corta: proyección del resultado del 29N con intervalos; el desglose completo debajo y en secciones. Lenguaje de todo el sitio: estimación, proyección o predicción con intervalos — nunca "datos electorales" como propuesta de valor; el dato es el medio, la estimación es el producto.
2. Bloque héroe 1 — **el resultado en escaños**: escaños estimados por partido (sumas del modelo provincial, 10.000 simulaciones D'Hondt), con su intervalo al 95 %, a ancho completo. Línea mono: "Objetivo 29N · método: media ponderada + swing proporcional · backtest MAE publicado".
3. Bloque héroe 2 — el detalle en voto: estimación estatal de intención de voto con intervalo del 80 % (cuantiles del backtest) y, debajo, la serie ponderada que alimenta el modelo.
4. Tres entradas asimétricas (no grid de tarjetas) — **el desglose**: **Explorador de encuestas** (contador mono de encuestas indexadas), **Resultados 1977–2023**, **Proyección provincial** (mapa en miniatura). Composición 2/3 + 1/3 con desplazamiento vertical escalonado.
5. Banda de metodología: fondo `--papel-2`, borde superior 2 px `--tinta`, los 5 compromisos metodológicos y enlace a la página completa. Firma de confianza del sitio.

**Explorador de encuestas:**
- Layout de dos columnas: filtros a la izquierda (320 px, sticky) + tabla de resultados a la derecha.
- Filtros: encuestador, año(s), tipo (preelectoral/postelectoral), ámbito (estatal/autonómico), validación (solo válidas / incluir excluidas).
- Cada fila expande una ficha: tamaño muestral, fechas de campo, margen de error declarado, URL de la ficha técnica (obligatoria), estado de validación con motivo si fue excluida.
- Encima de la tabla: "N = 2.847 encuestas · actualizado 2026-10-12" en mono.

**Resultados históricos (1977–2023):**
- Línea temporal electoral horizontal como columna vertebral de la página (los años de elección como marcas en una regla).
- Selector de elección (por defecto: la última). Vista principal: tabla de escaños por candidatura con barras horizontales proporcionales (colores de partido), y disco de resultados descargable.
- Comparador: dos elecciones lado a lado con delta (+/− en mono, verde `--ok`/rojo `--alerta` **solo** para el signo, el valor siempre en tinta).
- Nota de contexto por elección en Newsreader itálica: disoluciones, pactos, particularidades del censo.

**Predicción provincial:**
- Mapa coroplético a la izquierda (60 %), panel de provincia a la derecha (40 %), sincronizados en ambos sentidos.
- Panel de provincia: nombre + cabecera, serie histórica de resultados reales (líneas de partido) y **banda de predicción TimesFM** (`--intervalo`) con línea central de mediana en `--tinta`. Lectura obligatoria bajo el gráfico: "Con los datos disponibles, el intervalo del 90 % para X es [a, b]. El modelo no afina más: aquí está el error del backtest →".
- Controles: elección del nivel de agregación (provincia / autonomía / estatal) y del partido.
- Encabezado de sección que **no vende**: "Qué predecimos y qué no" antes del mapa. El mapa es la recompensa, no el gancho.

**Metodología:**
- Long-form: columna de prosa de 68 ch + notas al margen mono con versiones de modelo, hiperparámetros y resultados de backtest.
- Índice pegajoso a la izquierda en desktop, `details/summary` nativos en móvil.
- Cada afirmación numérica sobre el modelo lleva su tabla de backtest o su enlace al repo. El log de exclusiones se renderiza como tabla ordinaria, sin maquillaje: es documentación, no marketing.

---

## 6. Profundidad y elevación

Sistema casi plano: **la jerarquía se construye con tinta, reglas y fondo, no con sombras.**

- Nivel 0 — página: `--papel`.
- Nivel 1 — bloques con contenido diferenciado (panel de provincia, ficha de encuesta): fondo `--papel-2` + borde 1 px `--regla`.
- Nivel 2 — overlays (tooltip, dropdown de filtros): fondo `--tinta` (tooltip) o `--papel` con **borde 2 px `--tinta`** y sombra única y sobria: `0 2px 8px oklch(0.24 0.02 260 / 0.18)`.
- Nivel 3 — foco: anillo `--foco` de 3 px con offset 2 px. Es el estado con más presencia visual del sistema, deliberadamente.

Prohibido: `box-shadow` en tarjetas estáticas, glassmorphism, neumorfismo, bordes de neón, sombras de colores.

---

## 7. Accesibilidad

Objetivo WCAG 2.2 AA (más allá donde es barato):

1. **Contraste:** texto ≥4.5:1 (los pares definidos en §2 lo cumplen); elementos gráficos y bordes con significado ≥3:1. Los colores de partido con L alta (Cs, ERC) se usan solo como relleno con borde oscuro o trazo grueso, nunca como texto sobre papel.
2. **No solo color:** partidos distinguidos por etiqueta directa + luminosidad/patrón; provincias sin dato rayadas; deltas de signo con `+`/`−` explícitos además del color. Test obligatorio contra deuteranopía y protanopía en cada gráfico nuevo.
3. **Mapas:** además del mapa, lista/tabla paralela de provincias con los mismos datos (seleccionable, ordenable). El mapa nunca es el único camino hacia un dato.
4. **Teclado:** todos los filtros, tablas, ordenaciones y la selección de provincia son operables por teclado con foco visible (`--foco`). El orden de tabulación sigue el orden de lectura.
5. **Lectores de pantalla:** cada gráfico lleva `role="img"`, `aria-label` descriptivo con la conclusión ("Intención de voto estatal 2023–2026: PSOE y PP empatan dentro del intervalo") y una tabla de datos alternativa (`<details>`) con los mismos números. Idioma `lang="es"` en `<html>` y en fragmentos en otras lenguas.
6. **Movimiento:** `prefers-reduced-motion` reduce a opacidades; ninguna animación transmite información única.
7. **Tipografía:** zoom al 200 % sin pérdida de contenido; medidas de línea ≤68 ch; ninguna cifra crítica solo en color o solo en un tooltip.
8. **Links:** siempre subrayados (GOV.UK); el subrayado no se quita nunca como único indicador de hover.

---

## 8. Comportamiento responsive

- Mobile-first. Breakpoints: `480px`, `768px`, `1080px`, `1280px` (contenedor completo). En componentes densos (tablas, mapa), **container queries** (`@container`) para decidir el layout por componente, no por viewport.
- **Tablas en móvil:** transformación en filas clave-valor (cada fila de encuesta se apila: fecha, encuestador, muestra, estado), conservando todos los datos. No se oculta ninguna columna con scroll-x salvo que haya ≥8 columnas; entonces scroll-x con primera columna fija y sombra-indicador.
- **Mapa provincial en móvil:** mapa arriba a alto completo; panel de provincia debajo (no modal). La selección se hace tocando el mapa o desde la lista paralela; el panel aparece anclado bajo el mapa con scroll automático suave.
- **Gráficos:** redibujados con tick-spacing reducido y anotaciones colapsadas a marcadores numerados con nota al pie; los datos nunca se amputan, se adapta su presentación.
- **Filtros en móvil:** colapsados tras un botón "Filtros (3 activos)" con contador; no drawer decorativo, `details` nativo.
- Touch targets ≥44 px. Header colapsa a menú `details` nativo, sin JS obligatorio para navegar.

---

## 9. Tono editorial y microcopy

Voz: **agencia de estadística con pluma de redactor**. Precisa, sobria, sin jerga sin traducir, sin titulares sensacionalistas — el propio proyecto se define como "intervalos, no titulares".

- Directo y en primera persona del proyecto: *"No publicamos la cifra exacta porque el modelo no la conoce."*
- La incertidumbre se explica, no se esconde: cada gráfico de predicción lleva una frase de lectura (qué es la mediana, qué es el intervalo, qué error tiene el backtest).
- Microcopy de método: preferir "no hay datos suficientes" a "próximamente"; "encuesta excluida por N<500 — ver motivo" a un silencio en la tabla.
- Nada de superlativos de marketing ("revolucionario", "el mejor"). Las únicas palabras fuertes permitidas son las que describen datos ("empate técnico dentro del intervalo", "cambio de 4 puntos, fuera del margen de error").
- Errores y estados vacíos en tono útil, nunca culpando al usuario: *"No encontramos encuestas con esos filtros. Prueba a ampliar el rango de años."*
- Español de España neutro, cifras con coma decimal, miles con punto fino o espacio: `12.345` en tablas mono, `12 345` en prosa larga.

## 10. Do's and Don'ts

**Do**

- Mostrar la banda de intervalo siempre que haya predicción; la mediana sola nunca viaja sola.
- Enlazar cada cifra a su fuente (ficha técnica, CIS, Interior) — clic visible y subrayado.
- Usar reglas horizontales y tinta para jerarquizar; dejar que las tablas respiren con ritmo de espaciado variable.
- Anotar los gráficos en su propio lienzo con Newsreader itálica.
- Documentar exclusiones y errores con el mismo cuidado tipográfico que los aciertos.
- Verificar cada par de color nuevo contra AA antes de usarlo.

**Don't**

- No publicar nunca una predicción como cifra puntual, ni en titular, ni en tarjeta, ni en tooltip.
- No usar colores de partido fuera de gráficos, mapas y tablas.
- No centrar titulares, no usar tarjetas con sombra, no meter iconos decorativos en cada sección.
- No usar el amarillo de foco, el ámbar de intervalo ni el rojo de alerta con fines estéticos.
- No ocultar una cifra crítica dentro de un hover o de una animación.
- No inventar precisión: si el backtest da ±3 puntos, la UI no muestra decimales que el modelo no justifica.
- No presentar el mapa como el único acceso al dato (siempre hay tabla paralela).

## 11. Guía rápida para agentes (prompt guide)

**Tokens esenciales:** papel `oklch(0.985 0.004 95)` · tinta `oklch(0.24 0.02 260)` · enlace `oklch(0.42 0.14 265)` · intervalo `oklch(0.82 0.13 85 / 0.6)` · foco `oklch(0.88 0.17 95)` · acción `oklch(0.32 0.11 265)`. Radio 4 px. Borde > sombra. 1 px `--regla` como separador universal.

**Recetas:**

- *"Página de detalle de encuesta"*: cabecera con ID en Plex Mono, ficha técnica en tabla clave-valor, serie histórica del encuestador con banda de intervalo, nota de validación (o motivo de exclusión con borde `--alerta`), link de descarga CSV.
- *"Gráfico de intención de voto"*: líneas de partido (§2), etiquetas directas al final, gridlines horizontales 1 px, anotaciones Newsreader itálica, tooltip tinta, tabla de datos accesible en `<details>`.
- *"Predicción provincial"*: mapa coroplético con leyenda de cortes exactos + trama para "sin predicción", panel de provincia con serie real + banda `--intervalo` + mediana `--tinta`, frase de lectura metodológica bajo el gráfico.
- *"Home"*: titular Newsreader grande, regla 2 px, gráfico héroe con intervalos, tres entradas asimétricas, banda de metodología en `--papel-2`.

**Frase de comprobación final:** antes de entregar cualquier pantalla, pregúntate: ¿se puede maquillar un dato con este diseño? Si la respuesta es sí, quita el diseño que lo permite.
