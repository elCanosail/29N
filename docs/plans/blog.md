# Plan — Blog editorial de 29N (sección `/blog/`)

**Estado:** propuesta — pendiente aprobación de Chema
**Fecha:** 2026-10-18 · **Autor:** Elcano · **Ventana:** 42 días hasta el 29N (29-11-2026)

## 1. Objetivo

Una sección `/blog/` con 3-5 artículos **sencillos, pedagógicos y periodísticos** que:

1. Capturan búsqueda orgánica alrededor del 29N en las 6 semanas de máxima demanda.
2. Convierten ese tráfico en uso de las herramientas del site (encuestas, predicción, simulador).
3. Construyen E-E-A-T: el único site español que muestra el dataset validado y la metodología detrás de cada cifra.

**Criterio editorial (regla de oro):** cada artículo exhibe **datos propios** que ningún medio tiene (el dataset de 67 encuestas con ficha verificada, el scoring de encuestadores, el simulador D'Hondt). Sin eso, seríamos un blog más compitiendo contra El País. Con eso, somos la fuente.

## 2. Diagnóstico técnico previo (verificado 18-10-2026)

| Check | Estado |
|---|---|
| sitemap.xml | ❌ 404 — pré-requisito bloqueante |
| robots.txt | ❌ 404 — pré-requisito bloqueante |
| Integración @astrojs/sitemap / RSS | ❌ no instalada |
| OG básico en Base.astro | ✅ (sin og:image) |
| Rendimiento (estático, sin JS de contenido) | ✅ |
| Search Console | ❓ sin verificar — requiere acción de Chema |

## 3. Arquitectura

- **Astro content collections**: `src/content/blog/*.md` con frontmatter tipado (`title, description, pubDate, updated, slug, keyword`).
- Rutas: `/blog/` (índice) + `/blog/[slug]/` (artículo). Estático, cero JS de contenido.
- **Estética "gaceta de datos"**: índice como lista editorial (no grid de cards), cuerpo en Newsreader, datos en Plex Mono, reglas 1px. Igual que el resto del site.
- **Feed RSS** (`/rss.xml`) para sindicación.
- **Enlazado interno**: enlace discreto desde la portada (bloque de datos) y footer; cada artículo enlaza ≥2 secciones de datos; las secciones principales enlazan el artículo relevante (contextual, no navbar).

## 4. Los artículos

### A1 — «Cómo leer una encuesta electoral: margen de error, ficha técnica y por qué dos encuestas nunca coinciden»
- **Slug:** `/blog/como-leer-una-encuesta-electoral/`
- **Keyword principal:** cómo leer una encuesta electoral. **Secundarias:** margen de error encuestas · ficha técnica encuesta · por qué varían las encuestas
- **Intención:** informativa evergreen con pico de campaña. Pieza ancla del blog.
- **Estructura:** qué es una ficha técnica (ámbito, fechas de campo, n, universo, base del %) → margen de error con ejemplo real del dataset (n=1.600 → ±2,5 pp) → por qué dos encuestas difieren (campo, universo, base, efecto casa) → señales de encuesta seria vs. encuesta de marketing → enlaces a `/encuestas/` y `/metodologia/`
- **Dato propio:** los 67 estudios del dataset, todos con ficha verificada; screenshots de la ficha técnica como evidencia.

### A2 — «Las coaliciones del 29N: quién se presenta con quién, circunscripción a circunscripción»
- **Slug:** `/blog/coaliciones-29n/`
- **Keyword principal:** coaliciones elecciones 29N. **Secundarias:** Frente Amplio elecciones · quién se presenta elecciones noviembre 2026 · UPN PP Navarra coalición
- **Intención:** informativa-actualidad. **Volumen pico AHORA** (el plazo de registro de coaliciones cerró esta semana; el papa es "mapa de los pactos").
- **Estructura:** la izquierda fragmentada (PSOE en solitario · Frente Amplio IU+MS+MM+Comuns · Podemos en solitario con excepciones) → excepciones territoriales (UPC Canarias, Compromís-Front Valencià, ChA-Frente Amplio Aragón) → la derecha (PP+UPN Navarra, CC-1ºCanarias) → el centro (D21) → qué implica para el reparto de voto y escaños → enlace a `/prediccion/`
- **Dato diferencial:** **tabla de coaliciones por circunscripción** construida del registro oficial de la JEC — ningún medio la tiene tabulada. Es la pieza con mayor potencial de enlaces externos (periodistas la citarán).
- **Mantenimiento:** página viva con fecha de "última actualización"; actualizar si hay cambios de candidatura.

### A3 — «Ley D'Hondt explicada: cómo se reparten los escaños y por qué no siempre gana quien más votos saca»
- **Slug:** `/blog/ley-dhondt/`
- **Keyword principal:** ley D'Hondt. **Secundarias:** cómo funciona la ley d'hondt · d'hondt explicado · reparto de escaños España
- **Intención:** pedagógica evergreen; consulta recurrente en vísperas electorales.
- **Estructura:** qué es → ejemplo paso a paso con los datos reales de 23J (una provincia pequeña vs. una grande) → por qué beneficia a los partidos concentrados → pruébalo con nuestros datos → CTA al `/simulador/`
- **Dato diferencial:** el ejemplo se calcula con el simulador propio; capturas o tabla generada de él.

### A4 — «Qué es el CIS: barómetro, preelectoral y cómo se lee cada cosa»
- **Slug:** `/blog/que-es-el-cis/`
- **Keyword principal:** CIS qué es. **Secundarias:** barómetro CIS · encuesta preelectoral CIS · CIS noviembre 2026
- **Intención:** pedagógica evergreen + timely con la publicación mensual del barómetro.
- **Estructura:** qué es el CIS → barómetro vs. preelectoral (la distinción que casi nadie explica) → cómo se pondera → dónde ver los 51 estudios CIS normalizados con validación ±0,1 pp → enlaces a `/encuestas/` y `/microdatos/`
- **Efecto colateral:** da puente editorial a la sección de microdatos (hoy fuera de menú).

### A5 (opcional, fase 2) — «Por qué fallan las encuestas (y cuándo no): el historial 2015-2023 evaluado con datos»
- **Slug:** `/blog/fiabilidad-encuestas/`
- Muestra el scoring MAE del propio pipeline (Simple Lógica 1,73 … Imop 2,32) y el backtest del modelo. Contenido único de máxima E-E-A-T. Solo si el calendario lo permite.

## 5. SEO técnico (gate de publicación — sin esto, no se publica)

1. `@astrojs/sitemap` + `robots.txt` → despliegue y verificación 200.
2. Por artículo: `<title>` ≤60 c., meta description 150-160 c., canonical, H1 único, slug corto en español sin stopwords.
3. **JSON-LD**: `BlogPosting` (con `datePublished/Modified`) + `FAQPage` en A1 y A3 (bloques pregunta-respuesta reales); `Organization` site-wide.
4. `og:image` 1200×630 por artículo con la estética de datos (imágen estática simple por artículo; no requiere pipeline).
5. RSS en `/rss.xml`.
6. **Search Console**: verificar 29n.info y enviar sitemap — *requiere acceso de Chema a la propiedad GSC*.
7. Enlazado interno revisado en fresco: portada → blog, blog → herramientas, herramienta → blog.
8. Verificación móvil 390 px (mismo protocolo que Fase 5) + Lighthouse SEO ≥ 95.

## 6. Calendario (contando 42 días)

| Cuándo | Qué |
|---|---|
| Fase 1 — esta semana | Infraestructura (sitemap, robots, /blog/, RSS, schema) + **A2 coaliciones** (urgente: pico de búsqueda ya) + **A1 cómo leer encuestas** |
| Fase 2 — semana del 26-oct | **A3 D'Hondt** + **A4 CIS** (alinear con la publicación del barómetro de noviembre) |
| Fase 3 — noviembre | A5 opcional; refresco de A2 si cambia el mapa de candidaturas |
| 24-29 nov | **Apagón LOREG**: sin publicación de datos de encuestas nuevas; artículos pedagógicos no se ven afectados |
| Post-29N | Sexta pieza natural: «predicción vs. resultado» — la rendición de cuentas del modelo en vivo |

## 7. Verificación y criterios de aceptación

- [ ] `astro check` 0 errores; build limpio; 200 en `/blog/` y todos los slugs
- [ ] sitemap.xml lista las URLs del blog; robots.txt 200 y apunta al sitemap
- [ ] Cada artículo valida su JSON-LD (validator.schema.org)
- [ ] Lighthouse SEO ≥ 95 en cada página nueva
- [ ] Cada artículo enlaza ≥2 secciones de datos y ≥1 artículo hermano
- [ ] Meta title/description dentro de límites de SERP
- [ ] Smoke test móvil 390 px sin overflow horizontal

## 8. Riesgos y notas honestas

- **Dominio joven:** a 42 días el objetivo realista es long-tail y herramientas, no términos cabeza («encuestas»). Search Console dará la verdad de datos; sin GSC volamos a ciegas.
- **E-E-A-T sin autor nominal:** atribución «Equipo 29N» + enlace a metodología reproducible. Si Chema quiere byline real, se añade en 5 minutos.
- **Contenido electoral (YMYL-adjacent):** rigor de fuentes y neutralidad — ya es regla del repo (CONTRIBUTING: nada de posicionamiento partidista).
- **A2 caduca:** es la pieza de mayor pico y menor vida útil; el coste de mantenimiento (actualizar si cambian candidaturas) está previsto.

## 9. Fuera de alcance

Backlink building, campañas de pago, redes sociales. El blog no es la estrategia de distribución: es el embudo de búsqueda hacia las herramientas.
