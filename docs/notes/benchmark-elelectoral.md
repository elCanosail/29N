# Benchmark — ElElectoral (Andalucía) vs traslación 29N

**Fecha:** 2026-10-24 · **Autor:** Elcano · **Estado:** contraste entre metodologías, no validación.

## La referencia

Tuit de [@ElElectoral](https://x.com/ElElectoral/status/2113904124974477649) del
24-10-2026: estimación de generales para **Andalucía** «a partir de microdatos del
CIS». Titulares del tuit: PP primera fuerza con ~4 puntos de ventaja sobre el PSOE,
VOX «roza el 20 %», Adelante lejos de representación. La imagen adjunta da la tabla
completa (verificada contra el resultado oficial de 23J: su columna 2023 reproduce
exactamente los escaños y porcentajes oficiales del Ministerio del Interior).

## Comparativa de escaños (Andalucía, 61 escaños)

Nuestra cifra es la **suma de las medias provinciales publicadas** en `seats.json`
(generado el 2026-10-16, 8 días antes que su estimación). ElElectoral publica una
horquilla por bloque; el punto medio se muestra solo como referencia de lectura.

| Bloque | 23J real (Interior) | ElElectoral oct-26 (horquilla · punto medio) | 29N (suma de medias provinciales) | Nuestra cifra dentro de su horquilla |
|---|---|---|---|---|
| PP | 25 (36,4 %) | 22–26 · 24 | **25,3** | Sí, cerca del centro |
| PSOE | 21 (33,5 %) | 18–22 · 20 | **18,6** | Sí, en el suelo |
| VOX | 9 (15,3 %) | 11–15 · 13 | **14,9** | Sí, en el techo |
| Izquierda al PSOE¹ | 6 (12,0 %) | 1–4 · 2,5 | **2,2** | Sí |
| **Total** | **61** | **61** (etiqueta del gráfico) | **61** en juego · medias suman 61,0 | — |

¹ Definiciones no idénticas: el bloque izquierdista de ElElectoral suma **Frente
Amplio + Podemos + Adelante Andalucía**; nuestro output publicado solo detalla la
familia SUMAR (Frente Amplio) — Podemos no aparece como clave propia en ninguna
provincia andaluza publicada. La comparación es aproximada por construcción.

Desglose de nuestras medias provinciales (`seats.json`): PP gana las 8 provincias
(Almería 2,71 · Cádiz 3,57 · Córdoba 2,73 · Granada 2,93 · Huelva 2,07 · Jaén 2,10 ·
Málaga 4,64 · Sevilla 4,52 escaños esperados); PSOE destaca en Sevilla (4,13) y VOX
empata a la baja con PSOE en Málaga (2,91 frente a 2,93).

## Contexto de voto (ojo: ámbitos distintos)

| Partido | ElElectoral Andalucía oct-26 | 29N forecast estatal² |
|---|---|---|
| PP | 33,5 % | 35,0 % |
| PSOE | 29 % | 28,8 % |
| VOX | 19,5 % | 20,4 % |
| Frente Amplio | 8 % (+3 Adelante +2 Podemos) | 7,0 % |

² El modelo no publica estimación de voto por provincia, así que el único veto
comparable es estatal. Se muestra como contexto, no como comparación: ámbitos y
fecha de corte difieren.

## Metodologías

| | ElElectoral | 29N |
|---|---|---|
| Datos base | Microdatos individuales del CIS (MRP con postestratificación) | Media ponderada de encuestas (CIS + privados) + swing proporcional uniforme desde 23J |
| Reparto | Estimación directa por comunidad | D'Hondt provincia a provincia + 10.000 simulaciones |
| Incertidumbre | Horquilla por bloque | IC95 por provincia y nacional; no se suman intervalos provinciales |
| Antigüedad | Publicada 24-10-2026 | Generada 16-10-2026 |

La decisión del proyecto sobre el MRP está documentada en
[`docs/notes/mrp.md`](mrp.md): en el backtest 2015–2023 el swing uniforme batió al
MRP propio (MAE ~0,83 pp frente a ~1,0 pp). Este benchmark **no reabre esa
decisión**; contrasta dos estimaciones ya construidas con vías distintas.

## Divergencias y lectura honesta

1. **El orden de fuerzas coincide**: PP > PSOE > VOX > izquierda en ambos, con PP
   primera fuerza. En un punto sensible (Andalucía, 61 escaños), dos metodologías
   sin parámetros compartidos aterrizan en el mismo territorio.
2. **Las diferencias de punto medio son pequeñas y dentro de lo esperable**:
   PP +1,3 y VOX +1,9 a nuestro favor, PSOE −1,4. Todas caben en la horquilla de
   ElElectoral y son muy inferiores al ancho de nuestros intervalos provinciales.
3. **El matiz relevante es la posición dentro de la horquilla**: nuestro PSOE cae
   en el suelo de su rango (18,6 frente a 18–22) y nuestro VOX en el techo
   (14,9 frente a 11–15). Si algo separa las dos lecturas es un VOX andaluz algo
   más fuerte en nuestro modelo — coherente con el ratio de swing calibrado de VOX
   (1,63 sobre 23J), el más agresivo del universo modelado.
4. **El desplome de la izquierda al PSOE es el consenso**: de 6 escaños (23J) a
   ~2, en ambos casos. ElElectoral lo matiza: Adelante sube para las autonómicas
   andaluzas pero «lejos de representación» en generales.
5. **Lo que NO se puede concluir**: que una metodología valide a la otra. Es una
   sola comunidad, con fechas de corte distintas (nuestros datos cierran 8 días
   antes; su columna de octubre mueve VOX +3,5 pp y PP −3 pp frente a su propia
   estimación de junio), definiciones de bloque no idénticas y sin intervalos
   comparables lado a lado (nosotros no sumamos intervalos provinciales; ellos no
   publican el suyo por provincia). El contraste es una señal de plausibilidad
   mutua, nada más.
