# Efectos de casa y sesgo de incumbencia — 29N (fase 4-bis)

Generado por `pipeline/sesgo/render_report.py` desde `data/processed/sesgo/house_effects.json`.

- Serie principal (casa × partido): **166 observaciones validadas** de 224 totales.

- Error firmado = `pct_encuesta − pct_real`, **misma base de porcentaje**: el microdato del CIS es *% sobre censo* y se compara con el resultado real sobre censo; el modelo publicado y los encuestadores privados son *% sobre voto válido* y se comparan con el resultado real sobre voto válido.

- Las **correcciones** se aplican restando: `pct_corregido = pct_encuesta − corrección`.


## 0. ¿Vive el sesgo del CIS en el modelo o en las respuestas?

Sobre el mismo conjunto de elecciones (2015-12-20, 2016-06-26, 2019-04-28, 2019-11-10, 2023-07-23):

- Voto directo de microdato reescalado a voto válido: **MAE = 1.79 pp** (sesgo medio -0.29 pp, n=47).

- Estimación publicada del modelo CIS: **MAE = 1.09 pp** (sesgo medio -0.25 pp, n=52).


**Lectura:** el modelo del CIS **reduce** el error absoluto medio en **0.71 pp** respecto a la respuesta directa. El sesgo direccional residual del CIS está, pues, **más en la respuesta directa** (infravaloración de PP y VOX y sobrevaloración de PSOE) que en el propio modelo, que corrige buena parte de él. No se observa una *sobrecorrección* sistemática hacia la izquierda mayor que la que ya traía el dato directo.


## 1. Error firmado medio por casa × partido

### CIS — serie microdato (voto directo, % sobre censo)

| partido | n | media | sd | IC95 bootstrap |
|---|---:|---:|---:|---|
| VOX | 2 | -4.70 | 1.20 | [-5.90, -3.50] |
| PP | 4 | -4.08 | 0.67 | [-4.72, -3.44] |
| UNIDAS PODEMOS | 4 | -2.64 | 5.04 | [-7.47, +2.17] |
| CIUDADANOS | 4 | -0.65 | 2.24 | [-3.18, +1.44] |
| JXCAT | 4 | -0.50 | 0.18 | [-0.67, -0.32] |
| CUP | 1 | -0.35 | 0.00 | [-0.35, -0.35] |
| IU | 1 | +0.34 | 0.00 | [+0.34, +0.34] |
| MÁS PAÍS | 1 | +0.29 | 0.00 | [+0.29, +0.29] |
| UPYD | 1 | -0.22 | 0.00 | [-0.22, -0.22] |
| PNV | 4 | -0.14 | 0.08 | [-0.22, -0.07] |
| PSOE | 4 | -0.14 | 1.07 | [-1.18, +1.06] |
| CC | 2 | -0.13 | 0.09 | [-0.22, -0.04] |
| BNG | 1 | -0.12 | 0.00 | [-0.12, -0.12] |
| PRC | 1 | -0.09 | 0.00 | [-0.09, -0.09] |
| ERC | 4 | +0.07 | 0.06 | [+0.03, +0.14] |
| NA+ | 1 | -0.07 | 0.00 | [-0.07, -0.07] |
| PACMA | 2 | +0.05 | 0.07 | [-0.01, +0.12] |
| EH BILDU | 4 | +0.05 | 0.05 | [-0.00, +0.10] |
| GEROA BAI | 2 | +0.01 | 0.01 | [-0.00, +0.02] |


### CIS — serie microdato normalizada (% sobre voto válido)

| partido | n | media | sd | IC95 bootstrap |
|---|---:|---:|---:|---|
| VOX | 2 | -5.44 | 2.26 | [-7.70, -3.18] |
| PSOE | 4 | +4.06 | 3.73 | [+0.44, +7.69] |
| PP | 4 | -3.84 | 2.31 | [-6.26, -1.42] |
| UNIDAS PODEMOS | 4 | -2.17 | 7.39 | [-9.88, +4.43] |
| MÁS PAÍS | 1 | +0.88 | 0.00 | [+0.88, +0.88] |
| IU | 1 | +0.76 | 0.00 | [+0.76, +0.76] |
| ERC | 4 | +0.69 | 0.56 | [+0.14, +1.24] |
| CIUDADANOS | 4 | +0.57 | 2.40 | [-1.76, +3.01] |
| JXCAT | 4 | -0.56 | 0.15 | [-0.70, -0.41] |
| CUP | 1 | -0.42 | 0.00 | [-0.42, -0.42] |
| PACMA | 2 | +0.40 | 0.23 | [+0.17, +0.63] |
| UPYD | 1 | -0.30 | 0.00 | [-0.30, -0.30] |
| EH BILDU | 4 | +0.25 | 0.14 | [+0.09, +0.37] |
| CC | 2 | -0.13 | 0.12 | [-0.24, -0.01] |
| BNG | 1 | -0.11 | 0.00 | [-0.11, -0.11] |
| PRC | 1 | -0.10 | 0.00 | [-0.10, -0.10] |
| NA+ | 1 | -0.03 | 0.00 | [-0.03, -0.03] |
| GEROA BAI | 2 | +0.03 | 0.03 | [+0.00, +0.06] |
| PNV | 4 | -0.01 | 0.05 | [-0.05, +0.03] |


### CIS — serie modelo publicado (estimación, % sobre voto válido)

| partido | n | media | sd | IC95 bootstrap |
|---|---:|---:|---:|---|
| UNIDAS PODEMOS | 3 | -3.09 | 1.24 | [-4.75, -1.76] |
| VOX | 3 | -2.04 | 3.74 | [-7.17, +1.64] |
| CIUDADANOS | 4 | +2.03 | 2.78 | [-0.75, +4.43] |
| PP | 5 | -1.68 | 1.62 | [-3.06, -0.27] |
| PSOE | 5 | +0.72 | 2.05 | [-0.95, +2.59] |
| JXCAT | 3 | -0.48 | 0.17 | [-0.71, -0.34] |
| IU | 1 | +0.26 | 0.00 | [+0.26, +0.26] |
| ERC | 5 | +0.18 | 0.48 | [-0.24, +0.60] |
| CC | 5 | -0.11 | 0.09 | [-0.19, -0.04] |
| CUP | 2 | -0.11 | 0.31 | [-0.42, +0.20] |
| BNG | 2 | +0.09 | 0.19 | [-0.10, +0.28] |
| UPYD | 1 | +0.09 | 0.00 | [+0.09, +0.09] |
| PRC | 1 | -0.08 | 0.00 | [-0.08, -0.08] |
| PNV | 5 | -0.08 | 0.08 | [-0.15, -0.02] |
| EH BILDU | 5 | +0.05 | 0.18 | [-0.12, +0.20] |
| GEROA BAI | 2 | +0.01 | 0.04 | [-0.02, +0.05] |


### GAD3 — encuesta final 2023 (% sobre voto válido)

| partido | n | media | sd | IC95 bootstrap |
|---|---:|---:|---:|---|
| PP | 1 | +3.84 | 0.00 | [+3.84, +3.84] |
| PSOE | 1 | -3.08 | 0.00 | [-3.08, -3.08] |
| SUMAR | 1 | -0.83 | 0.00 | [-0.83, -0.83] |
| VOX | 1 | -0.68 | 0.00 | [-0.68, -0.68] |


### Sigma Dos — encuesta final 2023 (% sobre voto válido)

| partido | n | media | sd | IC95 bootstrap |
|---|---:|---:|---:|---|
| PSOE | 2 | -3.23 | 0.45 | [-3.68, -2.78] |
| PP | 2 | +1.74 | 0.60 | [+1.14, +2.34] |
| VOX | 2 | -1.18 | 0.00 | [-1.18, -1.18] |
| SUMAR | 2 | +1.12 | 0.15 | [+0.97, +1.27] |


### NC Report — encuesta final 2023 (% sobre voto válido)

| partido | n | media | sd | IC95 bootstrap |
|---|---:|---:|---:|---|
| PP | 1 | +4.14 | 0.00 | [+4.14, +4.14] |
| PSOE | 1 | -3.38 | 0.00 | [-3.38, -3.38] |
| VOX | 1 | -1.28 | 0.00 | [-1.28, -1.28] |
| SUMAR | 1 | -1.03 | 0.00 | [-1.03, -1.03] |


### Sociometrica — encuesta final 2023 (% sobre voto válido)

| partido | n | media | sd | IC95 bootstrap |
|---|---:|---:|---:|---|
| PSOE | 1 | -3.38 | 0.00 | [-3.38, -3.38] |
| VOX | 1 | +1.32 | 0.00 | [+1.32, +1.32] |
| SUMAR | 1 | +0.87 | 0.00 | [+0.87, +0.87] |
| PP | 1 | +0.44 | 0.00 | [+0.44, +0.44] |


## 2. Sesgo de incumbencia

Grupo **EN Gobierno** = partidos del ejecutivo de turno que se presentan (ver `pipeline/sesgo/incumbency.json`, con fuentes). **FUERA** = el resto. Intervalos bootstrap (10 000 remuestreos, semilla 20261015).


> **Advertencia de potencia estadística:** con n=1–5 observaciones por grupo, los intervalos son anchísimos y **ningún sesgo de incumbencia se declara significativo** salvo que su IC95 excluya el 0. En los encuestadores privados solo hay **una elección (2023)**, de modo que su diferencia IN−OUT **no puede separarse del error específico de esa cita** y no debe leerse como sesgo estructural.


| casa | serie | grupo | n | media | IC95 bootstrap |
|---|---|---|---:|---:|---|
| CIS | micro_censo | EN Gobierno | 4 | -2.13 | [-4.28, +0.23] |
| CIS | micro_censo | FUERA | 43 | -0.77 | [-1.47, -0.16] |
| CIS | micro_censo | **IN − OUT** | — | -1.35 | [-3.67, +1.13] |
| CIS | micro_valid | EN Gobierno | 4 | +1.14 | [-5.41, +7.69] |
| CIS | micro_valid | FUERA | 43 | -0.42 | [-1.34, +0.35] |
| CIS | micro_valid | **IN − OUT** | — | +1.56 | [-5.29, +8.21] |
| CIS | est | EN Gobierno | 5 | +0.47 | [-2.00, +2.60] |
| CIS | est | FUERA | 47 | -0.33 | [-0.87, +0.17] |
| CIS | est | **IN − OUT** | — | +0.79 | [-1.53, +3.04] |
| GAD3 | privado | EN Gobierno | 1 | -3.08 | [-3.08, -3.08] |
| GAD3 | privado | FUERA | 3 | +0.78 | [-0.83, +3.84] |
| GAD3 | privado | **IN − OUT** | — | -3.86 | [-6.93, -2.25] |
| Sigma Dos | privado | EN Gobierno | 2 | -3.23 | [-3.68, -2.78] |
| Sigma Dos | privado | FUERA | 6 | +0.56 | [-0.44, +1.56] |
| Sigma Dos | privado | **IN − OUT** | — | -3.79 | [-4.99, -2.58] |
| NC Report | privado | EN Gobierno | 1 | -3.38 | [-3.38, -3.38] |
| NC Report | privado | FUERA | 3 | +0.61 | [-1.28, +4.14] |
| NC Report | privado | **IN − OUT** | — | -3.99 | [-7.53, -2.10] |
| Sociometrica | privado | EN Gobierno | 1 | -3.38 | [-3.38, -3.38] |
| Sociometrica | privado | FUERA | 3 | +0.88 | [+0.44, +1.32] |
| Sociometrica | privado | **IN − OUT** | — | -4.26 | [-4.70, -3.83] |


## 3. Correcciones (encogimiento empirical-bayes)

`correccion_i = media_error_i × n_i/(n_i + K)`, con **K = 5** (documentado en `docs/notes/sesgo.md`). Restar la corrección a la encuesta.


### CIS — modelo publicado

| partido | n | media_error | corrección EB |
|---|---:|---:|---:|
| UNIDAS PODEMOS | 3 | -3.09 | -1.16 |
| CIUDADANOS | 4 | +2.03 | +0.90 |
| PP | 5 | -1.68 | -0.84 |
| VOX | 3 | -2.04 | -0.76 |
| PSOE | 5 | +0.72 | +0.36 |
| JXCAT | 3 | -0.48 | -0.18 |
| ERC | 5 | +0.18 | +0.09 |
| CC | 5 | -0.11 | -0.06 |
| IU | 1 | +0.26 | +0.04 |
| PNV | 5 | -0.08 | -0.04 |
| CUP | 2 | -0.11 | -0.03 |
| BNG | 2 | +0.09 | +0.03 |
| EH BILDU | 5 | +0.05 | +0.02 |
| UPYD | 1 | +0.09 | +0.01 |
| PRC | 1 | -0.08 | -0.01 |
| GEROA BAI | 2 | +0.01 | +0.00 |


### CIS — microdato normalizado

| partido | n | media_error | corrección EB |
|---|---:|---:|---:|
| PSOE | 4 | +4.06 | +1.81 |
| PP | 4 | -3.84 | -1.71 |
| VOX | 2 | -5.44 | -1.55 |
| UNIDAS PODEMOS | 4 | -2.17 | -0.96 |
| ERC | 4 | +0.69 | +0.31 |
| CIUDADANOS | 4 | +0.57 | +0.25 |
| JXCAT | 4 | -0.56 | -0.25 |
| MÁS PAÍS | 1 | +0.88 | +0.15 |
| IU | 1 | +0.76 | +0.13 |
| PACMA | 2 | +0.40 | +0.12 |
| EH BILDU | 4 | +0.25 | +0.11 |
| CUP | 1 | -0.42 | -0.07 |
| UPYD | 1 | -0.30 | -0.05 |
| CC | 2 | -0.13 | -0.04 |
| BNG | 1 | -0.11 | -0.02 |
| PRC | 1 | -0.10 | -0.02 |
| GEROA BAI | 2 | +0.03 | +0.01 |
| NA+ | 1 | -0.03 | -0.01 |
| PNV | 4 | -0.01 | -0.01 |


### GAD3

| partido | n | media_error | corrección EB |
|---|---:|---:|---:|
| PP | 1 | +3.84 | +0.64 |
| PSOE | 1 | -3.08 | -0.51 |
| SUMAR | 1 | -0.83 | -0.14 |
| VOX | 1 | -0.68 | -0.11 |


### Sigma Dos

| partido | n | media_error | corrección EB |
|---|---:|---:|---:|
| PSOE | 2 | -3.23 | -0.92 |
| PP | 2 | +1.74 | +0.50 |
| VOX | 2 | -1.18 | -0.34 |
| SUMAR | 2 | +1.12 | +0.32 |


### NC Report

| partido | n | media_error | corrección EB |
|---|---:|---:|---:|
| PP | 1 | +4.14 | +0.69 |
| PSOE | 1 | -3.38 | -0.56 |
| VOX | 1 | -1.28 | -0.21 |
| SUMAR | 1 | -1.03 | -0.17 |


### Sociometrica

| partido | n | media_error | corrección EB |
|---|---:|---:|---:|
| PSOE | 1 | -3.38 | -0.56 |
| VOX | 1 | +1.32 | +0.22 |
| SUMAR | 1 | +0.87 | +0.14 |
| PP | 1 | +0.44 | +0.07 |


## 4. Huecos de datos y limitaciones

- **Estudios CIS sin tabla publicada** (variable de voto elegida por heurística): quedan fuera de la tabla principal y se listan en el anexo. Varios están claramente mal normalizados (p. ej. 1326: UCD 23,5 frente a 5,0 real; 1533: PP 40,3 frente a 18,0; 1135 con 44 % de NS/NC).

- **Fin de campo del CIS**: solo se dispone de la fecha fin para los estudios con ficha técnica en `data/raw/cis`; para el resto se usa la fecha del catálogo (inicio de campo), marcada como `sin FT`.

- **Definición estricta (7 días)**: produce muy pocas observaciones (30; ver anexo). El CIS termina su campo habitualmente 2–5 semanas antes de la votación, así que la tabla principal usa la **última encuesta preelectoral** de cada casa como «final» (fallback documentado).

- **Encuestadores privados**: solo hay datos con resultado real para 2023; las encuestas de contexto 2024–2026 no tienen elección de referencia.

- **Descarga CIS en curso**: la ingesta de estudios sigue avanzando en segundo plano; n y cobertura pueden crecer.


## Anexo A — serie CIS no validada (referencia, no usar para correcciones)

| partido | n | media | sd | IC95 bootstrap |
|---|---:|---:|---:|---|
| SUMAR | 1 | +7.73 | 0.00 | [+7.73, +7.73] |
| UCD | 2 | +5.73 | 12.69 | [-6.96, +18.42] |
| CDS | 1 | -3.73 | 0.00 | [-3.73, -3.73] |
| VOX | 3 | -3.68 | 1.74 | [-5.90, -1.66] |
| PSOE | 8 | -2.99 | 4.81 | [-6.44, +0.14] |
| UNIDAS PODEMOS | 5 | -2.10 | 4.64 | [-6.18, +1.75] |
| PP | 6 | -1.54 | 11.43 | [-9.58, +9.11] |
| IU | 3 | -0.87 | 1.43 | [-2.87, +0.34] |
| BNG | 3 | +0.75 | 1.07 | [-0.12, +2.27] |
| JXCAT | 7 | -0.70 | 0.31 | [-0.94, -0.47] |
| CIUDADANOS | 4 | -0.65 | 2.24 | [-3.18, +1.44] |
| MÁS PAÍS | 1 | +0.29 | 0.00 | [+0.29, +0.29] |
| UPYD | 1 | -0.22 | 0.00 | [-0.22, -0.22] |
| PNV | 7 | -0.22 | 0.12 | [-0.31, -0.13] |
| CUP | 2 | -0.12 | 0.22 | [-0.35, +0.10] |
| PACMA | 3 | +0.10 | 0.09 | [-0.01, +0.21] |
| CC | 3 | -0.10 | 0.08 | [-0.22, -0.04] |
| ERC | 5 | +0.10 | 0.07 | [+0.03, +0.16] |
| PRC | 1 | -0.09 | 0.00 | [-0.09, -0.09] |
| NA+ | 1 | -0.07 | 0.00 | [-0.07, -0.07] |
| EH BILDU | 5 | -0.04 | 0.19 | [-0.23, +0.08] |
| PAR | 1 | +0.01 | 0.00 | [+0.01, +0.01] |
| GEROA BAI | 3 | +0.01 | 0.01 | [-0.00, +0.02] |


## Anexo B — estudios CIS usados (calidad y cobertura)

| estudio | elección | fin de campo | fuente fecha | n | calidad | cobertura partidos (% censo) | NS+NC (% censo) |
|---|---|---|---|---:|---|---:|---:|
| 1135 | 1977-06-15 | — | sin FT | 27260 | no_validada | 20.28 | 44.25 |
| 1181 | 1979-03-01 | 1979-02-03 | FT (ficha técnica) | 25516 | no_validada | 34.548 | 55.564 |
| 1183 | 1979-03-01 | — | sin FT | 24395 | no_validada | 0.516 | 0.805 |
| 1324 | 1982-10-28 | 1982-10-01 | FT (ficha técnica) | 24793 | no_validada | 50.381 | 21.931 |
| 1326 | 1982-10-28 | 1982-10-20 | FT (ficha técnica) | 24832 | no_validada | 49.703 | 24.015 |
| 1533 | 1986-06-22 | 1986-05-16 | FT (ficha técnica) | 1800 | no_validada | 80.819 | 0.0 |
| 7789 | 1989-10-29 | — | sin FT | 27421 | no_validada | 58.695 | 27.433 |
| 2207 | 1996-03-03 | — | sin FT | 6642 | no_validada | 65.156 | 24.111 |
| 7715 | 2015-12-20 | 2015-11-16 | FT (ficha técnica) | 6242 | no_validada | 76.107 | 9.63 |
| 3117 | 2015-12-20 | 2015-11-16 | FT (ficha técnica) | 17452 | validada | 61.909 | 25.209 |
| 3141 | 2016-06-26 | 2016-05-22 | FT (ficha técnica) | 17488 | validada | 62.282 | 22.037 |
| 3242 | 2019-04-28 | 2019-03-18 | FT (ficha técnica) | 16194 | validada | 51.33 | 38.071 |
| 3263 | 2019-11-10 | 2019-10-13 | FT (ficha técnica) | 17650 | validada | 52.635 | 32.753 |
| 3411 | 2023-07-23 | 2023-06-27 | FT (ficha técnica) | 29201 | validada | 77.568 | 16.97 |
| 3415 | 2023-07-23 | 2023-07-12 | FT (ficha técnica) | 8798 | validada | 77.503 | 17.65 |
| 3416 | 2023-07-23 | 2023-07-22 | FT (ficha técnica) | 27058 | no_validada | 44.461 | 4.516 |