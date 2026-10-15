# Plan de valor periodístico diferencial — 29N

**Principio (Chema, 15-10-2026):** pocas herramientas, profundas. Cada feature debe
ser algo que ningún medio español ofrezca hoy. No cantidad: calidad.

**Estado 15-10-2026:** 1, 2 y 6-parcial ya viven en la web; 3, 4 y 5 son las
apuestas pendientes ordenadas por relación valor/esfuerzo.

---

## 1. Trazabilidad radical — YA VIVO

Cada cifra de la web enlaza a su ficha técnica o fuente oficial. Los medios citan
«según una encuesta»; nosotros enlazamos el documento exacto, con fecha de campo
y tamaño muestral.

- Diferencial: cifra a cifra, no noticia a noticia.
- Esfuerzo: hecho (log de exclusiones público incluido).

## 2. El error del modelo, publicado como contrato — YA VIVO

Backtest MAE por partido y por elección, y el veredicto TimesFM vs baseline
sin maquillaje. Los medios publican predicciones; nadie publica cuánto se
equivoca su modelo ni con qué intervalos.

- Diferencial: la honestidad como producto, no como disclaimers.
- Esfuerzo: hecho.

## 3. Efectos de casa medidos, no acusados — LA JOYA PERIODÍSTICA

Sesgo sistemático por encuestador con intervalos bootstrap: CIS-modelo frente
a voto directo, privados frente a resultados reales. La tabla de «ratings» de
encuestadores que FiveThirtyEight popularizó en EE. UU. y que en España nadie
mantiene. Medimos con IC95; no acusamos.

- Diferencial: único en España; la página /encuestadores con el MAE histórico
  de cada casa y su error en 23J ya apunta ahí.
- Esfuerzo: bajo — los datos están calculados (sesgo.json); falta renderizar
  la página y mantenerla viva con cada elección.

## 4. Explorador de microdatos CIS 1977–2025 — LA HERRAMIENTA ÚNICA

532.498 entrevistas individuales consultables: provincia, edad, sexo,
estudios, ideología autopositionada, recuerdo e intención de voto. Filtros
sin servidor (agregados precalculados en estático).

- Diferencial: los medios no tocan los microdatos; los investigadores pagan
  por ellos. Ningún medio español ofrece esto.
- Esfuerzo: medio — precalcular agregados por cruce (provincia × era) y una
  UI de filtros sobre los parquet → JSON estático.

## 5. Proyección provincial abierta — COMPLETANDO EL MAPA

El mapa por partido seleccionable ya funciona (vanilla JS sobre datos
estáticos). Falta la descarga: CSV de la proyección completa (52 provincias ×
partidos, media e IC95) y del histórico de encuestas normalizado.

- Diferencial: entregar los datos brutos de la proyección, no solo el mapa.
- Esfuerzo: bajo — los JSON ya están; un botón de descarga y el CSV.

## 6. Corpus abierto y reproducible — LA MARCA

Todo el dataset normalizado (encuestas, resultados 1977-2023, sesgo, series)
descargable desde la web, con el pipeline público en el repo. Los medios
guardan sus datos como secreto comercial; nosotros los entregamos con el
método.

- Diferencial: la transparencia como foso competitivo.
- Esfuerzo: bajo — página de descargas sobre los JSON/parquet ya versionados.

---

## Selección de Chema (15-10-2026, 20:49)

**En construcción:**

1. **Trazabilidad** — ya viva; se mantiene como contrato.
2. **Explorador de microdatos CIS 1977–2025** — agregados precalculados por cruce
   (provincia × edad × ideología × año) → JSON estático + UI de filtros sin servidor.
3. **Simulador «¿qué pasaría si…?»** — con diseño honesto: sliders por partido
   acotados al IC95 del backtest (el error propio del modelo), redistribución
   proporcional sobre la base 23J y D'Hondt en cliente. Etiquetado como
   exploratorio y dentro del error del modelo.
4. **Cron diario de exploración de nuevas encuestas hasta el 29N** — ingesta
   automática de nuevos estudios CIS (pipeline validado), detección de candidatas
   privadas (electografica, imop; GAD3/Sigma Dos con anti-bot → candidatas para
   curación manual), regeneración de datos y aviso en el chat.

**Descartadas por ahora:** efectos de casa como página dedicada (los datos
siguen en sesgo.json y metodología), CSV de proyección y corpus descargable
como páginas dedicadas (el repo público ya cumple ese papel).
