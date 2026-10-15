# Efectos de casa y sesgo de incumbencia (29N — fase 4-bis)

Fecha: 2026-10-15 · Alcance: `pipeline/sesgo/`, `data/processed/sesgo/`, este informe.
Sin commits ni push. No se toca `pipeline/cis/`, `pipeline/encuestadores/`,
`pipeline/interior/` ni `web/`.

## Objetivo

Medir los **efectos de casa** de los encuestadores (error firmado sistemático por
partido) y el posible **sesgo de incumbencia** —en particular del CIS— y producir
las **correcciones** para el modelo de predicción.

## Entradas (solo lectura)

| fuente | ruta | qué aporta |
|---|---|---|
| Serie CIS (microdato) | `data/processed/cis/polls.jsonl` | voto directo por estudio×partido (% sobre censo), 37 estudios descargados |
| Tablas del CIS | `data/raw/cis/estimacion/est*.txt` | "Voto directo" y "Estimación de voto CIS" publicadas |
| Encuestadores | `data/processed/encuestadores/polls.jsonl` | 32 encuestas privadas |
| Resultados reales | `data/processed/interior/elections.json` | votos por candidatura y totales (censo, válidos) |
| Fechas de campo CIS | `data/raw/cis/**/FT*.pdf` | ficha técnica (inicio/fin de campo) |

## Definiciones

- **Encuesta final.** El enunciado pide: fin de trabajo de campo dentro de los **7
  días naturales** previos a la votación (`definicion_estricta`). En la práctica
  esa ventana deja casi vacía la serie del CIS: su campo termina habitualmente
  **2–5 semanas** antes del día de la votación (p. ej. 3411: campo 8–27 jun 2023
  para la cita del 23 jul). Por eso la tabla principal usa la definición
  **operativa** (`definicion_operativa`, fallback documentado): la **última
  encuesta preelectoral** de cada casa cuyo campo terminó antes de la votación.
  El subconjunto estricto queda registrado en `observaciones_estricta_7d`.
- **Error firmado** = `pct_encuesta − pct_real`, **partido a partido sobre la
  misma base de porcentaje**:
  - microdato CIS → *% sobre censo*, comparado con el resultado real sobre censo
    (`votos_partido / censo`);
  - modelo CIS publicado y encuestadores privados → *% sobre voto válido*,
    comparado con el resultado real sobre voto válido
    (`votos_partido / votos_validos`).
- **Tres series CIS** para localizar el sesgo:
  - `micro_censo`: voto directo publicado por el CIS (% sobre censo);
  - `micro_valid`: el mismo voto directo **reescalado** a % sobre voto válido
    (base = partidos reconocidos + voto en blanco), comparable con el modelo;
  - `est`: columna "Estimación de voto CIS" del modelo publicado (% sobre válido).
- **Sesgo de incumbencia.** `incumbency.json` codifica el Gobierno de turno por
  elección (fuente: La Moncloa, Congreso, Wikipedia — citadas en el fichero). Se
  compara el error medio de los partidos **EN el Gobierno** frente al de los que
  están **FUERA**.

## Método

1. `party_canon.py` unifica en un mismo diccionario las etiquetas del CIS
   (`party_aliases.csv`) y los `partido_id` de Interior, **agregando las ramas
   territoriales** a su matriz nacional (PSC/PSE/PSdG→PSOE; AP/AP-PDP→PP; …) y
   resolviendo por año las **coaliciones dependientes de la era** (`ecp`→Unidas
   Podemos en 2016/2019 y →SUMAR en 2023; `compromis`→SUMAR en 2023…). Se
   valida contra los resultados oficiales conocidos.
2. `parse_estimacion.py` extrae las dos columnas de las tablas publicadas,
   sorteando los distintos formatos (margen de error, escaños, columna
   intermedia de voto sobre emitido en 3269).
3. `compute_house_effects.py` selecciona la encuesta final, calcula el error
   firmado, las tablas casa×partido, la incumbencia con **bootstrap** (10 000
   remuestreos, semilla 20261015) y las **correcciones EB**.
4. `render_report.py` genera `bias_report.md`.

### Corrección empirical-bayes

```
correccion_i = media_error_i × n_i / (n_i + K),   K = 5
```

**K = 5** encoge las medias hacia 0 cuando hay pocas observaciones: con n=1 la
corrección queda al 17 % de la media; con n=5 al 50 %; con n=10 al 67 %. Se fija
en 5 (no se estima) porque con 1–5 elecciones por casa cualquier estimación de la
varianza entre casas sería ruido; 5 es un prior deliberadamente conservador
("no creas una media de una sola encuesta"). La corrección se **resta** a la
encuesta: `pct_corregido = pct_encuesta − corrección`.

## Hallazgos (cifras reales)

- **El sesgo del CIS está más en la respuesta directa que en el modelo.** Sobre
  las 5 elecciones con ambas series (2015–2023), el error absoluto medio del
  voto directo reescalado es **1,78 pp**, y el del modelo publicado **1,09 pp**:
  el modelo **reduce** el error en **0,69 pp**.
- **Dirección del sesgo del voto directo (normalizado):** infravalora **VOX
  (−5,4 pp)**, **PP (−3,8 pp)** y **Unidas Podemos (−2,2 pp)** y sobrevalora
  **PSOE (+4,1 pp)**. El modelo reduce casi todas esas brechas (PP −1,7; VOX
  −2,0; UP −3,1; PSOE +0,7), pero **no elimina** la infravaloración de PP/VOX ni
  UP; el sesgo izquierda-derecha del modelo es del orden de **2–2,5 pp**
  (PP − PSOE ≈ −2,4 pp).
- **Encuestadores privados 2023:** todos **infravaloran al PSOE** (gobernante,
  −3,1 a −3,4 pp) y **sobrevaloran a PP** (GAD3 +3,8; NC Report +4,1; Sigma Dos
  +1,7). Sigma Dos es el menos sesgado en PP.
- **Incumbencia:** la diferencia IN−OUT del CIS-modelo es **+0,79 pp**
  (IC95 [−1,53, +3,05]) → **no significativa**. En los privados la diferencia es
  negativa (≈ −3,8 pp) pero descansa en **una sola elección**, así que no es un
  sesgo estructural medible.

## Advertencias

- **Potencia estadística.** Los grupos de incumbencia tienen n=1–5. Los
  intervalos bootstrap son enormes; **no se declara ningún sesgo sin su IC** y
  ninguno excluye el 0 salvo las diferencias de los privados, que están
  contaminadas por ser de una única cita electoral.
- El **MAE** mezcla sesgo y varianza; sirve para comparar series, no para
  corregir partido a partido (para eso están las correcciones EB).
- El signo de la corrección es "restar": una media negativa (encuesta baja)
  implica una corrección negativa que **sube** el porcentaje corregido.

## Huecos de datos detectados

1. **Estudios CIS sin tabla publicada** quedan fuera de la tabla principal
   (`calidad = no_validada`). Varios están mal normalizados sin poder validarlos:
   - **1135** (1977): 44 % de NS/NC, solo 20 % de cobertura de partidos.
   - **1181/1183** (1979): cobertura 34,5 % / 0,5 %.
   - **1326** (1982): UCD 23,5 pp frente a 5,0 real; **1533** (1986): PP 40,3
     frente a 18,0. La variable de voto elegida por heurística no es la de
     intención de voto publicada.
   - **3416** (2023, estudio metodológico de campaña): "Otros" 12,5 %; no
     reproducible como voto directo.
2. **Falta de ficha técnica** (`FT*.pdf`) para varios estudios antiguos: la fecha
   fin de campo se desconoce (se usa la fecha del catálogo, que es de **inicio**
   de campo; se marca `end_source = sin FT`).
3. **Cobertura temporal del microdato CIS**: no hay estudios preelectorales
   normalizados para 2000, 2004, 2008 y 2011 (la descarga sigue en curso en
   segundo plano). El análisis validado se concentra en 2015–2023.
4. **Encuestadores privados**: solo 2023 tiene resultado real; las encuestas de
   2024–2026 no tienen cita electoral de referencia y quedan fuera de los errores.
5. **Definición estricta (7 días)**: apenas produce observaciones; se documenta
   aparte para no confundirla con la tabla principal.

## Reproducir

```bash
python3 pipeline/sesgo/compute_house_effects.py   # series, tablas, bootstrap, EB
python3 pipeline/sesgo/render_report.py           # bias_report.md
```

Salidas: `data/processed/sesgo/house_effects.json`, `bias_report.md`.
