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

## No-features (por disciplina)

- Simulador de escenarios «¿qué pasaría si…?»: especulación, no predicción.
- Predicciones diarias: ruido, y el modelo está pensado para la fecha.
- Gamificación ni quizzes: diluyen la herramienta.

## Prioridad sugerida

1. **Feature 3** (efectos de casa, página por encuestador) — la más
   periodística y la más barata: los datos ya están calculados.
2. **Feature 6** (página de descargas del corpus) — refuerza la marca y es
   casi gratis.
3. **Feature 4** (explorador de microdatos) — la más única y defensable;
   requiere diseño de agregados.
4. **Feature 5** (CSV de la proyección) — redondea el mapa.
