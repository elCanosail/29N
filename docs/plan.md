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

### Fase 0 — Scaffold (semana 1)
- [ ] Repo `29N` creado con estructura `pipeline/` + `web/`
- [ ] Python env + TimesFM instalado y smoke test (forecast de serie juguete)
- [ ] Descarga manual de 3 estudios CIS preelectorales recientes (3496, 3486 o equivalentes 23J/10N) + parse del CSV

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

### Fase 3 — Encuestadores privados (semanas 2-4)
- [ ] Curración inicial: encuestas 2023-2026 de los principales encuestadores (ficha técnica de prensa)
- [ ] Scoring histórico de cada encuestador (error medio absoluto contra resultado real)
- [ ] Esquema unificado con CIS; log de exclusiones público desde el inicio

### Fase 4 — Modelo (semana 4-5)
- [ ] Serie ponderada por partido con pesos de calidad
- [ ] TimesFM estatal + backtest contra ≥5 elecciones (MAE por partido documentado)
- [ ] Desagregación provincial por swing + validación backtest provincial
- [ ] Simulación D'Hondt 10.000 runs → JSON de predicción por provincia con intervalos

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
