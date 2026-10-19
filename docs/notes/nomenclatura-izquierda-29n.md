# Nomenclatura de la izquierda en el 29N

**Fecha:** 2026-10-19 · **Estado:** decidido e implementado en la web

## Hecho verificado

Sumar no concurre como marca propia al 29N. La coalición registrada es
**Frente Amplio** (IU, Movimiento Sumar, Más Madrid y Comuns), sin Podemos.
Podemos presenta listas separadas en la mayoría de comunidades; solo hay lista
única en Canarias (Unidad del Pueblo Canario) y País Valencià
(Compromís-Front Valencià). En Galicia, Euskadi y Andalucía la izquierda llega
dividida en hasta tres papeletas.

Fuentes primarias consultadas (2026-10-16/19):

- Público: «Frente Amplio y Podemos concurrirán por separado el 29 de noviembre
  salvo en Canarias y País Valencià».
- Europa Press: «IU, Sumar, Iniciativa del Pueblo Andaluz y Equo concurrirán
  juntos el 29N en un Frente Amplio Por Andalucía sin Podemos».
- ABC: «Frente Amplio Aragón concurrirá el 29-N con un cabeza de cartel de
  Chunta y sin Podemos».
- El País: Movimiento Sumar llama al resto de partidos del Frente Amplio a
  negociar; el partido forma parte de la coalición, no se presenta solo.

Dentro del corpus de 29N, la ficha de Sociometrica (2026-10-01) ya describe al
«Frente Amplio, la nueva plataforma vinculada a Sumar», y la de 40dB
(2026-10-08) publica la opción como «Sumar / Frente Amplio». El CEO de Cataluña
publica «Comuns» y «Podemos» por separado.

## Decisión

1. **29N:** la candidatura se presenta como **Frente Amplio** en portada,
   predicción, simulador, mapa y comparativa de escaños. La sigla de mapa es
   **F. Amplio**.
2. **Histórico:** la clave interna `SUMAR` no cambia. La serie 1977–2026 se
   sigue modelando como una sola familia (IU → Podemos → Sumar → Frente Amplio)
   para no fabricar partidos fantasma. En las encuestas de 2023–2025 la etiqueta
   visible sigue siendo **Sumar**; en 2026 pasa a **Frente Amplio**.
3. **Cataluña:** la encuesta del CEO de 2026 se etiqueta **Comuns** (la marca de
   la coalición en Cataluña), no Frente Amplio.
4. **Podemos:** se muestra como **Podemos** cuando la encuesta lo publica
   separado en 2026. El modelo nacional no le asigna una serie propia porque las
   encuestas nacionales de la ventana no ofrecen una estimación separada con
   muestra suficiente; esto se declara en metodología.
5. **23J:** la barra histórica conserva la etiqueta **SUMAR**, porque en esa
   elección la familia concurrió con esa marca. La comparativa lo advierte.

## Implementación

- `web/src/lib/partidos.ts`: `NOMBRE_29N`, `nombre29N()` y `sigla29N()`.
- Portada: etiquetas de bandas, texto, serie y comparativa 23J.
- `BarraEscanos`: separa clave de datos (`SUMAR`) y etiqueta visible; el 29N
  usa «F. Amplio» y el 23J conserva «SUMAR».
- `SerieLinea`: acepta etiquetas visibles sin cambiar las claves de serie.
- `/encuestas/`: etiqueta por era y ámbito (Sumar, Frente Amplio, Comuns,
  Podemos).
- `/prediccion/`, `/simulador/` y cartograma: nombre y sigla del 29N.
- Metodología y microdatos: explican la familia y la división del voto.

## Límite declarado

El modelo sigue agregando el espacio de izquierda en una sola serie. No estima
por separado Frente Amplio y Podemos, ni las singularidades territoriales de
Canarias, País Valencià, Galicia, Euskadi y Andalucía. Es una limitación de los
datos publicados, no una afirmación de que concurran juntos.
