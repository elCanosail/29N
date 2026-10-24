# Ingesta IMOP ola 2 (23-10-2026) · 29N

**Fecha de trabajo:** 24-10-2026 · **Autor:** subagente (`29N ingesta IMOP 23-oct`)
· **Rama:** `feat/imop-23oct` (worktree `/tmp/29n-imop`, base `main` 55d293b) ·
**Sin push** (revisión del padre pendiente). El árbol principal
`/root/.openclaw/workspace/projects/29n` no se ha tocado, ni `web/src/pages/`
ni `web/src/components/`.

---

## 1. Encuesta localizada (regla de oro cumplida)

| Campo | Valor |
|---|---|
| Casa | **Imop Insights** (comitente: El Confidencial) — «ola 2» de la serie pre-electoral 29N |
| Estudio ID | `imop-2026-10-13` (patrón `imop-<inicio de campo>`, como `imop-2026-10-05` para la ola 1) |
| Campo | **13–16 octubre 2026** |
| Publicación | **23 octubre 2026** (EC `datePublished` 2026-10-23T05:00+02:00; imop.es «23 Octubre 2026») |
| n | **1.000 entrevistas** |
| Universo | Personas de 18 años y más censadas y con derecho a voto en las elecciones generales |
| Diseño | Aleatorio estratificado proporcional por CCAA y tamaño de municipio; cuotas por sexo, edad y nivel de estudios |
| Técnica | Híbrida CATI + CAWI (45%/55%; 70% móvil en telefónico) |
| Margen | ±3,3 pp (orientativo) |
| Ámbito | Nacional · elección «generales 2026» (29N) |

**URLs:**

- **Ficha del encuestador (fuente A):**
  `https://www.imop.es/encuesta-pre-electoral-el-confidencial-ola-2/` — título
  «encuesta pre-electoral el confidencial ola 2», cifras PP 28,5 % / PSOE 27,1 % /
  Vox 20,0 %, PP+Vox 195 escaños (123+72), campo 13–16 oct, n=1.000.
  ⚠️ Durante la sesión del 24-10 imop.es devolvía **HTTP 502** en todas sus páginas
  (también la de la ola 1: incidencia general del sitio, verificada con curl ×3 y
  Camoufox). El contenido se verificó vía el índice de búsqueda (texto íntegro de
  la página, publicado el 23-10) y se dejó constancia como exclusión-documentación
  en el fragmento. La URL existe y es la ficha técnica publicada.
- **Artículo del comitente (fuente B):**
  `https://www.elconfidencial.com/espana/2026-10-23/encuesta-imop-elecciones-29n-bloque-psoe-frente-amplio_4450302/`
  — HTTP 200 con Camoufox; ficha técnica íntegra extraída del DOM (ver §2) y
  JSON-LD con fecha 23-10-2026. Cuerpo tras muro para sesión anónima; cifras del
  texto citadas desde el texto indexado y contrastadas con el agregador.
- **Agregador de contraste (fuente C):**
  `https://www.electografica.com/2026/10/encuesta-imop-insights-261023.html` —
  HTTP 200 con curl; tabla completa de voto y escaños.

## 2. Cifras extraídas (verbatim, sin invención)

### Voto estimado (ola 2)

| Partido | % | Fuente literal |
|---|---:|---|
| PP | **28,5** | imop.es «28,5 % PP · primera fuerza»; EC «el 28,5% de los votos (-1,9%) y 123 escaños» |
| PSOE | **27,1** | imop.es «27,1 % PSOE · segunda fuerza»; EC «se sitúan en el 27,1% (+1,1%) y 113 escaños» |
| VOX | **20,0** | imop.es «20,0 % Vox · mayor avance»; EC «el 20% de los votos (+1%) y 72 escaños (+2)» |
| SUMAR («Frente Amplio») | **8,9** | EC «Frente Amplio pasa del 7,6% al 8,9% (+1,3%) y logra catorce escaños» |
| ERC | 2,2 | electografica (tabla completa) |
| JUNTS (JXCAT) | 1,2 | electografica |
| EH BILDU | 1,3 | electografica |
| PNV | 1,0 | electografica |
| BNG | 1,1 | electografica |
| CC | 0,6 | electografica |
| PODEMOS | 1,9 | EC «del 2,3% al 1,9%» — **no incluido en votos** (§4) |
| SALF | 1,2 | EC «SALF, que consigue el 1,2% (-0,2%)» — no incluido (§4) |
| Participación | 72,9 | electografica; EC «en torno al 73%, frente al 70,4% de 2023» |

Escaños publicados: PP 123, PSOE 113, VOX 72, FA 14, Podemos 1, ERC 8, Junts 4,
Bildu 6, PNV 5 (de 4), BNG 2 (pierde uno), CC 1. PP+Vox = **195** (−6); bloque
izquierdo 129 (+6). (Los escaños no entran al modelo: se recalcula con D'Hondt.)

### Ficha técnica EC (DOM, verbatim)

> Fechas de campo: Del 13 al 16 de octubre de 2026. · Universo: Personas de 18
> años y más censadas y con derecho a voto en las elecciones generales. ·
> Tamaño muestral: 1.000 entrevistas · Diseño muestral: Aleatorio estratificado
> proporcional por CCAA y tamaño de municipio. Control de cuotas por sexo y edad
> y nivel de estudios · Técnica de entrevista: Metodología híbrida, mediante la
> combinación de entrevista telefónica (CATI) y entrevista online (CAWI), con
> una distribución aproximada de 45%/55%. En el canal telefónico, el 70% de las
> entrevistas se realizó con individuos contactados a través de teléfono móvil. ·
> Margen de error: ±3,3 puntos porcentuales en las estimaciones.

## 3. Fragmento y cadena ejecutada

- Fragmento: `data/processed/encuestadores/_staging/imop_ola2.json` (formato
  `simplelogica_demoscopia.json`; 10 partidos en `votos`; `fuente_votos_adicionales`
  documenta EC/electografica para los pequeños).
- Cadena con `/root/.venvs/29n/bin/python` (24-10-2026):

```
build_dataset.py  → 5 fragmentos, 33 encuestas, 148 filas; Imop Insights: 4→5 estudios
                    imop-2026-10-13: 10 filas (PP/PSOE/VOX/SUMAR/ERC/JXCAT/EH BILDU/PNV/BNG/CC)
build_series.py   → OK series.json
forecast.py       → OK forecast_state.json
provincial.py     → OK seats.json — 10.000 runs; coherencia escaños suma=349.99 (ok=True);
                    votos max dev=0.0122 pp (ok=True)
web/sync-data.py  → 9 JSON escritos en web/src/data/
```

- Filtro BIG4 pasa: 28,5+27,1+20,0+8,9 = **84,5 ≥ 75**.

## 4. Decisiones de mapeo (mismas que la ola 1)

1. **«Frente Amplio» → SUMAR**: nueva marca del espacio Sumar; serie comparable
   (ola 1: 7,6 → ola 2: 8,9, el +1,3 que publica EC).
2. **PODEMOS 1,9 excluido de `votos`**: el alias canonicaliza a UNIDAS PODEMOS y
   `FAMILY` lo plegaría a SUMAR; en 2026 concurre en solitario (mismo criterio que
   la ola 1). Plegarlo introduciría un salto artificial de ~1,9 pp en la serie SUMAR
   no comparable con las observaciones previas.
3. **SALF 1,2 excluido**: mapea a OTROS (residual no modelado). UPN/AA constan 0,0.
4. Partidos pequeños (ERC, Junts, EH Bildu, PNV, BNG, CC) desde EC (escaños) +
   electografica (voto %): IMOP solo publica los 4 grandes (criterio ola 1).

## 5. Movimiento de cuotas (antes → después)

Baseline = árbol limpio en 55d293b (datos al 16-10, `generado: 2026-10-16`).
«Después» = cadena del 24-10 (`generado: 2026-10-24`). Suma punto = 100,0 ✓.

| Partido | Punto antes | Punto después | Δ pp | Escaños media antes | después |
|---|---:|---:|---:|---:|---:|
| PP | 35,002 | 34,501 | **−0,501** | 134,5 | 132,3 (−2,2) |
| PSOE | 28,814 | 28,830 | +0,016 | 105,5 | 105,6 (+0,1) |
| VOX | 20,360 | 20,472 | +0,112 | 65,8 | 66,5 (+0,7) |
| SUMAR | 7,023 | 7,297 | **+0,274** | 14,8 | 15,4 (+0,6) |
| ERC | 2,399 | 2,395 | −0,004 | 8,7 | 8,7 |
| EH BILDU | 1,420 | 1,417 | −0,003 | 6,4 | ~6,4 |
| JXCAT | 1,203 | 1,259 | +0,056 | — | — |
| BNG | 1,199 | 1,198 | −0,001 | — | — |
| PNV | 0,983 | 1,040 | +0,057 | — | — |
| CC/PACMA/CUP/NA+ | — | — | ≤0,001 | — | — |

Dirección coherente con la encuesta (PP −1,9 dentro de su ola; VOX +1; FA +1,3):
la nueva observación tira de PP a la baja frente a la media del corpus de octubre
y levanta levemente VOX y SUMAR. Cuotas dentro del rango típico (máx 0,5 pp).

Escaños tras la ingesta: PP 132,3 IC95 [107,160] · PSOE 105,6 [71,136] ·
VOX 66,5 [41,93] · SUMAR 15,4 [0,51]; suma de medias 349,99 (redondeo, ok=True).

## 6. Verificación

- `forecast.json` y `seats.json` regenerados con `generado: 2026-10-24` (antes
  2026-10-16); suma 100,0; coherencia provincial ok=True.
- Hashes antes → después (cambian, como debe ser): `forecast_state.json`
  b19f26fb→3aec39b4; `seats.json` (modelo) 24ad6dc5→682688c1; `web forecast.json`
  0e5391d0→17efa0ec; `web seats.json` e086e5bd→3129f40e.
- **Build web en verde:** `cd web && npm run build` → «11 page(s) built in 2.84s ·
  Complete!» (node_modules se instaló en el worktree; sin tocar el árbol principal).
- `git status`: solo ficheros esperados (fragmento nuevo + regenerados de datos +
  sincronizados web/src/data). Sin cambios en `web/src/pages/` ni
  `web/src/components/`.

## 7. Hallazgo adicional (para el padre, no corregido aquí)

- `web/src/data/reparto23.json` comprometido incluía, en `meta.nota`, la frase
  «; en el 29N esa familia concurre como Frente Amplio», que el generador
  `web/sync-data.py::gen_reparto23()` NO produce. La regeneración la perdía;
  se ha **restaurado la frase a mano** para mantener el diff limpio (el fichero
  queda igual que el comprometido), pero la divergencia persiste: la próxima
  regeneración la volverá a perder salvo que se añada la frase al generador.
  Decisión de alcance dejada al padre (tocar `sync-data.py` no entra en esta
  ingesta y podría colisionar con el agente paralelo).

## 8. Limitaciones / honestidad

- imop.es estaba caída (502) durante toda la sesión: la ficha del encuestador se
  verificó por índice de búsqueda y vía la ficha íntegra del artículo de EC
  (DOM). Si el padre lo desea, reintentar la URL cuando el sitio vuelva.
- Los % de los partidos pequeños proceden del agregador electografica (los escaños,
  de EC); no alteran el punto salvo marginalmente (Δ ≤ 0,06 pp en JXCAT/PNV).
- La comparación «antes» usa el corpus comprometido a 55d293b (evolucionado desde
  la nota de ingesta del 16-10, que refleja otra instantánea del corpus).
