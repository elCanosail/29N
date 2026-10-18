---
title: "Cómo leer una encuesta electoral: margen de error, ficha técnica y por qué dos encuestas nunca coinciden"
description: "Guía de cómo leer una encuesta electoral: ficha técnica, margen de error y por qué dos sondeos del mismo mes no coinciden. Ejemplos del dataset de 29N."
pubDate: 2026-10-18
updated: 2026-10-18
slug: "como-leer-una-encuesta-electoral"
keyword: "cómo leer una encuesta electoral"
---

# Cómo leer una encuesta electoral: margen de error, ficha técnica y por qué dos encuestas nunca coinciden

En la primera quincena de octubre de 2026, cinco casas publicaron sondeos sobre las generales del 29N: NC Report dio al PP un 34,1 % (n=1.000), GAD3 un 31,4 % (n=1.077), Sociometrica un 32,6 % (n=1.000), Sigma Dos un 31,9 % (n=2.017) y 40dB, en un barómetro flash de intención directa, un 20,5 % (n=800). Los cuatro primeros se parecen; el quinto, no. Y ninguno tiene por qué ser mentira: cada cifra responde a decisiones concretas —a quién se entrevista, cuándo, con qué técnica y sobre qué base se calcula el porcentaje—. Leer una encuesta es leer esas decisiones. Esta guía recorre la ficha técnica campo a campo, explica el margen de error con su fórmula y muestra por qué dos encuestas del mismo mes pueden separarse varios puntos sin que nadie engañe a nadie.

## La ficha técnica, campo a campo

Toda encuesta seria va acompañada de su ficha técnica. No es burocracia: es lo que permite saber qué miden exactamente esos porcentajes. La ley electoral española (LOREG, art. 69.2) obliga a publicarla en las encuestas que salen durante una campaña; las casas rigurosas la publican siempre. Estos son los campos que conviene mirar, con ejemplos reales de nuestro dataset.

### Ámbito

¿Qué elección y qué territorio? Una encuesta «hacia las generales» puede ser estatal o una proyección desde una comunidad. El Centre d'Estudis d'Opinió (CEO) publicó en octubre de 2026 una encuesta de n=2.000 con campo del 1 de septiembre al 5 de octubre sobre las generales proyectadas en Cataluña: su ámbito es catalán, y mezclarla con la serie estatal sin más sería un error de libro. En nuestro [comparador de encuestas](/encuestas/) el ámbito aparece siempre junto a cada estudio por esa razón.

### Fechas: el trabajo de campo no es la publicación

El campo es el periodo en que se realizan las entrevistas; la publicación puede llegar días después. GAD3 entrevistó del 26 al 28 de mayo de 2026 y publicó su barómetro para ABC el 1 de junio; NC Report trabajó del 1 al 6 de octubre y publicó el día 8. La consecuencia práctica: la encuesta no «ve» lo ocurrido después de su campo. Un debate entre el último día de entrevistas y la publicación no está en el dato, aunque el titular lo dé por hecho. Y si la casa no publica las fechas de campo —le ocurre a la encuesta de Sigma Dos del 12 de octubre de 2026—, la foto queda sin fecha. En nuestro dataset ese hueco se registra vacío; no se rellena de memoria.

### n: el número de entrevistas

Es el número de personas efectivamente entrevistadas, no el del panel ni el de contactos intentados. En octubre de 2026 nuestro dataset va de n=800 (40dB) a n=2.017 (Sigma Dos); el CIS trabaja con muestras de decenas de miles en sus preelectorales: n=29.201 en junio de 2023. Un n grande reduce el error aleatorio, pero no corrige los sesgos de método: una ponderación defectuosa con 20.000 entrevistas sigue siendo una encuesta mala.

### Universo

El universo es la población a la que se proyectan los resultados: normalmente los residentes de 18 años o más del territorio, aunque cada casa lo define y debe declararlo. Dos encuestas con universos distintos no son comparables, aunque sus porcentajes parezcan gemelos.

### La base: ¿el porcentaje está calculado sobre qué?

Es el campo que más engaña. Un mismo partido puede presentarse sobre censo (todos los mayores de edad), sobre población o sobre votantes (voto válido). El CIS registra voto directo declarado sobre censo: de ahí que sus cifras parezcan bajas. En su encuesta flash del 29 de abril de 2025, el PSOE salía con un 17,7 % y el PP con un 13,5 %, con un 20,2 % de «no sabe» y un 6,1 % de «no contesta» por delante de la mayoría de partidos. Las casas privadas, en cambio, publican estimación de voto sobre válido, y ahí esos mismos partidos rondan el 26 y el 32 %. La nota metodológica de nuestro dataset lo dice sin rodeos: «CIS = voto directo sobre censo (microdato); privados = estimación sobre voto válido. No son directamente comparables sin normalizar». Antes de comparar dos porcentajes, verifica la base.

## El margen de error: la fórmula

Toda muestra tiene error muestral. Con un 95 % de confianza y el peor escenario (un partido en torno al 50 %), el margen se aproxima con la fórmula:

±1/√n

Es decir, unos ±100/√n puntos porcentuales. Tres cálculos directos:

- n=400 → ±5,0 puntos
- n=1.600 → ±2,5 puntos
- n=3.000 → ±1,8 puntos

Aplicado a fichas reales de octubre de 2026: el flash de 40dB (n=800) arrastra unos ±3,5 puntos; GAD3 (n=1.077), ±3,0; Sigma Dos (n=2.017), ±2,2. La macroencuesta de Demoscopia de septiembre de 2025 (n=3.000) quedaba en ±1,8.

Dos consecuencias que casi ningún titular recoge. Primera: el margen aplica a cada cifra, y comparar dos exige aún más distancia, porque la incertidumbre de una diferencia entre dos partidos puede llegar a duplicar la de cada valor aislado. Segunda: una ventaja pequeña no es un liderazgo. En el barómetro de 40dB del 8 de octubre de 2026, el PSOE salía con un 23,0 %, el PP con un 20,5 % y VOX con un 20,1 %. Con ±3,5 puntos por cifra, la «ventaja» de 2,5 puntos del PSOE no permite afirmar nada: los tres están empatados dentro del margen. El titular honesto es «empate técnico», no «el PSOE se pone por delante».

## Por qué dos encuestas del mismo mes difieren

Con la ficha técnica y el margen sobre la mesa, las divergencias se ordenan en cinco causas.

1. **Azar muestral.** NC Report dio al PP un 34,1 % y GAD3 un 31,4 % en la misma quincena: 2,7 puntos que caben de sobra en sus márgenes combinados (±3,2 y ±3,0). Dos encuestas correctas nunca tienen por qué coincidir.
2. **Fechas de campo.** NC Report encuestó del 1 al 6 de octubre; Sociometrica, del 10 al 11. En campaña viva, cuatro días mueven décimas.
3. **Universo y base.** CIS sobre censo, privados sobre válido: ya lo vimos, no son comparables sin normalizar. Y dentro de los privados tampoco todos miden lo mismo: el barómetro de 40dB de octubre de 2026 es un «flash» de intención directa de voto, sin la cocina demoscópica —recuerdo de voto, simpatía, reparto de indecisos— que produce la estimación de voto. Por eso lo etiquetamos aparte y no lo sumamos a la serie de estimaciones.
4. **Efecto casa.** Cada casa tiene técnica (CATI telefónica, CAWI online, híbrida), cuotas y ponderación propias, y esa receta genera sesgos estables. La evidencia está en el pasado: al contrastar las encuestas de 2023 con el resultado real del 23J, el error absoluto medio por casa osciló entre 1,7 y 2,3 puntos —con apenas 1-3 encuestas por casa, no es un ranking— y el error se concentró en el PSOE, infravalorado sistemáticamente por casi todas las casas antes de la cita.
5. **La estimación.** Detrás de un «PP 33 %» hay decisiones concretas de reparto del voto blanco, el nulo, la abstención y las respuestas NS/NC. Dos casas con la misma materia prima pueden publicar estimaciones distintas.

## Señales de seriedad y señales de alarma

Señales de encuesta seria:

- Ficha técnica pública y completa: financiador, universo, fechas de campo, n, técnica, sistema de muestreo y margen de error.
- Distingue con claridad la intención directa de la estimación de voto.
- Mantiene series coherentes y explica los cambios de método.
- Publica también cuando el dato no le favorece. El CIS, por ejemplo, abre sus microdatos para que cualquiera pueda recalcular los porcentajes.

Señales de alarma:

- Sin fechas de campo o sin n: no se puede calcular el margen ni situar la foto en el tiempo.
- Porcentajes sin base declarada (¿censo, población, válidos?): cualquier comparación queda invalidada de partida.
- Ventajas dentro del margen convertidas en titulares de liderazgo.
- Muestras gigantes vendidas como garantía: el tamaño reduce el error aleatorio, no el sesgo.
- Encuestas de encargo sin financiador declarado, o casas que solo publican cuando les conviene.

Una regla mental para cerrar: si con la ficha no puedes reconstruir quién fue entrevistado, cuándo y sobre qué base se calculó cada porcentaje, la encuesta no es interpretable.

## Cómo lo validamos en 29N

En 29N trabajamos con un dataset de 67 encuestas de 10 casas (35 del CIS y 32 de nueve casas privadas), cada una con la URL de su ficha técnica y su extracto literal; lo que no consta en la fuente queda nulo. Normalizamos las bases —el voto directo del CIS sobre censo se convierte a voto válido para poder comparar— y contrastamos el rendimiento histórico de cada casa contra los resultados oficiales del Ministerio de Interior: así sabemos, por ejemplo, que los sondeos de 2023 infravaloraron al PSOE antes del 23J. Ese scoring se publica siempre con su tamaño de muestra, porque con 1-3 encuestas por casa un ranking sería trampa estadística. Puedes explorar las fichas verificadas en el [comparador de encuestas](/encuestas/) y leer la descripción completa del proceso en la [metodología](/metodologia/).

Leer bien una encuesta no exige desconfianza: exige las preguntas correctas. La ficha técnica las responde todas, cuando está completa.

## Preguntas frecuentes

### ¿Qué es el margen de error de una encuesta?

Es el intervalo dentro del cual puede estar el valor real con una confianza determinada, habitualmente el 95 %. Se aproxima con 1/√n: con n=1.000, unos ±3,2 puntos. Un 32 % con ese margen puede corresponder a un apoyo real entre el 28,8 % y el 35,2 %.

### ¿Por qué difieren las encuestas?

Por azar muestral, por fechas de campo distintas, por universos y bases de cálculo diferentes y por el «efecto casa» (técnica y ponderación propias de cada encuestador). Divergencias de 2-4 puntos entre casas el mismo mes son lo normal, no una anomalía.

### ¿Qué debe incluir una ficha técnica?

Financiador, ámbito y universo, fechas del trabajo de campo, número de entrevistas, técnica, sistema de muestreo y ponderación, margen de error y base de los porcentajes. La LOREG española exige estos datos a las encuestas publicadas durante una campaña electoral.

### ¿Qué significa que un porcentaje es «sobre censo»?

Que se calcula sobre todos los mayores de edad del censo, incluidos abstencionistas y respuestas NS/NC. Es la base habitual del CIS, y por eso sus cifras son más bajas que las de las casas privadas, que suelen publicar sobre voto válido. Compararlas sin normalizar produce errores groseros.

