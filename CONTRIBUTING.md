# Contribuir a 29N

Gracias por el interés. Este proyecto vive del dato limpio y trazable. Antes de abrir un PR, lo esencial:

## Regla de oro

**Toda encuesta entra con la URL de su ficha técnica, sin excepciones.** Sin ficha técnica verificable, la encuesta no entra (o entra al log de exclusiones, que también es público).

## Qué se acepta con gusto

1. **Diccionario de partidos** (`pipeline/party_aliases.csv`): aliases, fusiones, candidaturas históricas (PODEMOS-IU-ALIANZA VERDE-SUMAR, PSC vs PSOE, Alianza Popular→PP…). Trabajo mecánico y muy agradecido.
2. **Encuestadores privados**: transcribir estimaciones de voto de fichas técnicas publicadas en prensa, con URL, fechas de trabajo (no solo publicación), `n` y metodología.
3. **Validaciones**: encontrar discrepancias entre nuestros totales y los oficiales. Son bugs de máxima prioridad.
4. **Metodología**: crítica del modelo de predicción. El backtest se puede reproducir; si encuentras un error, es una victoria del método.

## Qué no se acepta

- Estimaciones sin fuente o de memoria.
- Datos de encuestas resultos de interés partidista sin ficha técnica.
- Cualquier intento de reidentificación de individuos en los microdatos del CIS (están anonimizados; mantenerlo así es una condición ética del proyecto).
- Posicionamiento partidista en issues o PR.

## Proceso

1. Abre un issue primero si el cambio es grande (metodología, esquema de datos).
2. PR pequeño y atómico: una encuesta, un partido, una validación.
3. Para datos: incluye script de ingesta o CSV normalizado + URL de fuente en la descripción del PR.
4. **Antes de comitear datos, pasa la guardia**: `python3 pipeline/verificar_datos.py`.
   Comprueba que ningún JSON lleva marcas de conflicto, que todos parsean y que
   el total de encuestas no baja respecto a `origin/main`. Si sale con código 1,
   no se comitea: se arregla.

### Revisión y mezcla

`main` exige una aprobación. Cuando no hay nadie disponible para revisar —ni la
app de revisión ni una persona— el administrador del repositorio puede fusionar
saltándose el requisito (`gh pr merge <n> --squash --admin`), y el bypass queda
en el registro del ruleset. Es la salida de emergencia, no la norma: un PR de
datos sin revisar debe llevar en el cuerpo qué se verificó y con qué comando.

Lo que se aprendió a golpes: el 8 de noviembre un merge dejó `<<<<<<<` dentro de
`web/src/data/encuestas.json`; como `astro.config.mjs` hace `JSON.parse` de ese
fichero, la web no compilaba. La guardia del punto 4 existe por eso.

## Código

- Python 3.12+, estilo estándar, tests para el pipeline (`pytest pipeline/tests`).
- Web en Astro; los datos que lee la web son estáticos, la web no calcula.
- Pre-commit con gitleaks: no metas secretos, aunque "solo sea para probar".
