# Ingesta automática de encuestas (hasta el 29N)

Decisión de Chema (18-10-2026, `docs/plan.md` Fase 3): **las encuestas claras y
relevantes se ingieren sin supervisión; las dudosas escalan; las no electorales
se descartan con una línea.** Hasta el 24-10 eso se hizo a mano. Desde el
2026-11-02 hay una cadena que lo hace sola cada día.

## Qué corre

```
pipeline/cron_encuestas.py                 ← entrada (la llama el cron de Hermes)
 ├─ encuestadores/electografica.py         descubre y extrae (feed Blogger)
 ├─ encuestadores/ingesta_auto.py          valida, contrasta y escribe staging
 ├─ encuestadores/build_dataset.py         partidos canónicos + fuentes
 ├─ modelo/build_series.py                 serie ponderada
 ├─ modelo/forecast.py                     forecast estatal (baseline + TimesFM)
 ├─ modelo/provincial.py                   provincial + D'Hondt
 └─ web/sync-data.py                       JSON de la web
```

Códigos de salida: `0` nada nuevo (silencio), `10` encuestas nuevas y web
regenerada, `1` fallo.

## De dónde se descubren

`https://www.electografica.com/feeds/posts/default?alt=json` — el feed público
de Blogger. Es la única fuente con un listado estable de encuestas de generales
con fecha, encuestadora y ficha técnica. Se filtran las entradas
`ESPAÑA · Elecciones generales` con fecha de publicación posterior a la última
ingerida; el resto (autonómicas, municipales, extranjeras) se ignora.

## Cómo se extrae

De la propia entrada, sin navegador: el bloque «Ficha técnica» (encuestadora,
cliente, fechas de campo, método, muestra, margen) y el panel de estimación de
voto (una fila por partido con su porcentaje). Los porcentajes están en
atributos `data-w` del panel, así que no hace falta interpretar el dibujo.

## Qué se acepta y qué escala

| Condición | Resultado |
|---|---|
| Falta encuestadora, muestra, fechas o método | **escala** |
| Muestra fuera de 200–20.000 | **escala** |
| Campo cerrado hace más de 45 días | **escala** |
| Publica menos de 5 partidos o suma de voto fuera de 85–102 % | **escala** (publicación incompleta) |
| Falta el desglose de PP, PSOE, VOX o SUMAR | **escala** |
| Ninguna de las tres cifras principales aparece en la fuente original | **escala** |
| Ya ingerida (misma casa + mismo fin de campo) | se ignora |

Las escaladas se acumulan en `data/processed/cron/escaladas.json` y el informe
diario las lista con el motivo exacto y la URL.

## Partidos

Se ingieren las diez formaciones del modelo: PP, PSOE, VOX, SUMAR, ERC, JXCAT,
EH BILDU, PNV, BNG, CC.

- **Frente Amplio (FA) es la marca de SUMAR en 2026.** Las casas lo publican de
  tres formas —`FA` sola, `FA-FV-UPC` ya agregada, o `FA` + `COMPROMÍS-FV` +
  `UPC` en filas separadas— y las tres **se suman** al mismo partido. Validado
  contra Colmena de Datos: Sigma Dos 26-10 da FA 8,2 = 7,4 + 0,8.
- **Podemos** concurre en solitario en 2026: plegarlo a SUMAR alteraría la serie
  (mismo criterio que IMOP el 24-10). Se documenta por encuesta, no se ingiere.
- SALF, UPN, Aliança Catalana, D21, IE y EV quedan fuera con su razón escrita.

## LOREG

El artículo 69.7 prohíbe publicar encuestas en los cinco días anteriores a la
votación. **Desde el 2026-11-24 el script sigue detectando pero no reescribe la
web**: las candidatas quedan en staging y se publican después del 29N. El
informe diario lo dice explícitamente mientras esté activo.

## Cron

Job de Hermes `29n-encuestas-diario`, 09:30 Europe/Madrid, `workdir`
`/home/nan/work/29n`. El prompt manda ejecutar el script, revisar el diff que
produce y, si hay encuestas nuevas, commit + push (Vercel despliega solo). Si el
script devuelve escaladas, se las pasa a Chema con el motivo en lugar de
decidir por su cuenta un dato en duda.

## Verificación

- `python3 pipeline/encuestadores/electografica.py --desde 2026-10-24` — qué ve.
- `python3 pipeline/encuestadores/ingesta_auto.py --desde 2026-10-24` — qué
  aceptaría, sin escribir nada.
- `python3 pipeline/cron_encuestas.py --seco` — la cadena en seco.
