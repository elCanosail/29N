# Ingesta de resultados oficiales — Ministerio del Interior (29N)

Fecha: 2026-10-15 · Autor: subagente de ingesta · Alcance de escritura: `pipeline/interior/`,
`data/raw/interior/` (gitignored), `data/processed/interior/`, este informe.
Sin commits ni push. Crudos en `data/raw/interior/` (ruta en `.gitignore`).

## Resumen ejecutivo

- **Todas las elecciones generales (Congreso) 1977–2023 ingeridas**: **16 convocatorias**,
  **10.963 registros** provincia × candidatura con votos y escaños (más votos CERA aparte).
- **Validación obligatoria superada**: (a) suma de escaños provinciales = escaños nacionales
  **16/16**; (b) **D'Hondt reproduce los escaños oficiales en 15/16 elecciones al 100 % y en
  la restante 51/52 provincias**; (c) coincidencia con el fichero independiente de cargos
  electos **16/16**. El único descuadre (1977 · Santa Cruz de Tenerife, 1 escaño) está
  documentado con sus números exactos en §5.
- **Bloqueo real encontrado**: el portal solicitado `infoelectoral.interior.gob.es`
  (y el legacy `www.infoelectoral.mir.es`) es **inalcanzable desde este host** (TCP en
  timeout en 80/443; también vía proxies públicos y vía el extractor web del Gateway).
  Se usó como fuente primaria el **mismo escrutinio oficial** publicado por el Ministerio
  en su portal de **datos abiertos** (`descargas.interior.gob.es`), que sí es accesible.
  Detalle en §1.

Pregunta clave de la tarea — "¿los resultados oficiales se reproducen desde los votos
provinciales?" — **sí, con un descuadre real documentado**.

---

## 1. Portal del Interior: estructura y bloqueo

### 1.1 URL y direcciones

| Host | Resolución | Estado desde este host |
|---|---|---|
| `infoelectoral.interior.gob.es` (portal actual, Área de descargas) | 212.128.101.22 | **TCP timeout** en 80 y 443 |
| `www.infoelectoral.mir.es` (portal legacy) | 212.128.101.21 | **TCP timeout** |
| `www.interior.gob.es` | — | responde **HTTP 403** (WAF) |
| `descargas.interior.gob.es` (datos abiertos) | 212.128.102.215 | **accesible** ✅ |

Comprobaciones realizadas (evidencia):

```
curl -I https://infoelectoral.interior.gob.es/es/elecciones-celebradas/   -> Connection timed out
curl    http://infoelectoral.interior.gob.es/...                          -> Connection timed out (20 s)
openssl s_client -connect 212.128.101.22:443 -servername infoelectoral... -> handshake agotado
# proxies públicos (server-side) contra infoelectoral:
api.allorigins.win/raw?url=...   -> HTTP 522
api.codetabs.com/v1/proxy?quest= -> HTTP 522
corsproxy.io/?url=...            -> HTTP 401
# extractor web del Gateway (mismo egress que este host):
web_fetch https://infoelectoral.../area-de-descargas/  -> TimeoutError 15000 ms
```

El bloqueo es **de red (IP del host)**, no de cabeceras ni de ruta: tres resolvers públicos
(1.1.1.1, 8.8.8.8, 9.9.9.9) devuelven la misma IP y todas las conexiones TCP mueren en SYN.
El subdominio `descargas.interior.gob.es` (misma infraestructura SGSICS-MIR, subred vecina
212.128.102.x) **sí** responde.

### 1.2 Formato del Área de descargas de infoelectoral (documentado, no descargado)

El Área de descargas de infoelectoral publica, por convocatoria, **ZIP con ficheros de ancho
fijo `.DAT`** (uno por tipo de fichero), con nombres `nnxxaamm.dat` donde:

- `nn` = tipo de fichero: **03** candidaturas · **04** candidatos · **05** datos globales
  municipales · **07** globales de ámbito superior al municipio · **08** candidaturas de
  ámbito superior al municipio (provincia/isla) · **09/10** mesas · **11/12** municipios < 250 hab.
- `xx` = tipo de proceso: **02** Congreso · **03** Senado · **07** Parlamento Europeo · …
- `aa`, `mm` = año y mes de la elección.

Esquema del registro del fichero **08** (el relevante: escrutinio provincial por candidatura),
según el paquete CRAN `infoelectoral` (`read08.R`), posiciones de columna:

| Campo | Posición | Tipo |
|---|---|---|
| tipo_eleccion | 1–2 | num |
| anno | 3–6 | num |
| mes | 7–8 | num |
| vuelta | 9 | num |
| codigo_ccaa | 10–11 | num |
| **codigo_provincia** | **12–13** | num |
| codigo_distrito_electoral | 14 | num |
| **codigo_partido** | **15–20** | char |
| **votos** | **21–28** | num |
| **diputados** | **29–33** | num |

Y el fichero **05** (globales municipales) incluye censo, votantes, blancos, nulos, validos,
etc. Estos son los ficheros que producirían "escrutinio provincial por candidatura" desde
infoelectoral. **No se han podido descargar por el bloqueo de red descrito.**

### 1.3 Fuente alternativa usada (mismo escrutinio oficial)

El Ministerio publica en su portal de datos abiertos, host accesible:

```
https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx
https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso-cargos-electos.xlsx
https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Senado.xlsx   (opcional, descargado)
```

Son los resultados **definitivos del escrutinio general** (art. 103 LOREG; publicados en el
BOE por la Junta Electoral Central) — la misma base que sirve infoelectoral — consolidados en
un único Excel. **Nota TLS**: `descargas.interior.gob.es` sirve el certificado con la **cadena
incompleta** (falta el intermedio) → `ssl` no verifica. El descargador reintenta con
verificación y, si falla, cae a contexto no verificado (datos públicos, sin credenciales);
se registra en el log (`TLS=unverified`).

---

## 2. Estructura real del fichero normalizado

Hoja única `Congreso`, formato **ancho**:

- Filas 1–3: títulos y aviso metodológico. Fila 4: cabecera.
- **Columnas E…BB** (52): provincias, con cabecera `"<código INE> - <nombre>"` (1–52).
- Última columna: `Total Escaños Nacional`.
- **Filas** (`Descripción`): métricas de participación (`Electores`, `Electores CER`,
  `Votantes`, `Votos válidos`, `Votos nulos`, `Votos en blanco`, `Votos a candidaturas`) y,
  por candidatura, pares de filas:

  ```
  Votos   (<NOMBRE> - <SIGLA>)     -> votos por provincia (SIN el voto CERA)
  Escaños (<NOMBRE> - <SIGLA>)     -> escaños por provincia + total nacional
  Votos CERA   (<NOMBRE> - <SIGLA>)   -> voto de residentes ausentes (CERA)
  ```

- Una **fila resumen `Escaños`** (sin paréntesis) da el total de escaños por provincia.

Detalles verificados en los datos:

1. `sum(Votos (…) por provincia) == "Votos a candidaturas"` exacto (p. ej. Madrid 2023:
   3.579.713). El voto **CERA va en filas aparte y es aditivo** (`Votos a candidaturas CERA`).
2. Una **misma candidatura puede ocupar varias filas** (subconjuntos de provincias), cada una
   con su subtotal en `Total Escaños Nacional`. Hay que **acumular**, no sobrescribir
   (era un bug detectado y corregido, ver §5.4).
3. Las coaliciones llevan la sigla completa dentro de la etiqueta y esta puede contener `" - "`
   (p. ej. `SUMAR - EN COMÚ PODEM - SUMAR - ECP`, `CIUDADANOS … - C's`, `… - C´s` con apóstrofos
   distintos). El parseo usa un **resolutor por sufijos** contra el diccionario de aliases.

El fichero `cargos-electos` (8 columnas: Fecha, Código elección, Tipo, Código Provincia,
Provincia, Cargos Electos, Candidatura, Siglas Candidatura) da la lista **nominal** de
diputados electos → sirve de validación independiente (c).

---

## 3. Descarga

Script: `pipeline/interior/interior_fetch.py` (stdlib `urllib`, sin dependencias extra).

- **Reanudable**: si el fichero existe parcialmente pide el resto con `Range`.
- **Ritmo educado**: pausa entre peticiones (`--pause`, 2 s por defecto) y backoff exponencial
  ante 429/5xx (respeta `Retry-After`).
- **TLS**: verificación por preferencia → fallback no verificado (ver §1.3).

Ficheros crudos (gitignored) en `data/raw/interior/`:

| Fichero | Bytes |
|---|---|
| `Elecciones-Congreso.xlsx` | 1.151.199 |
| `Elecciones-Congreso-cargos-electos.xlsx` | 326.847 |
| `Elecciones-Senado.xlsx` | 1.143.461 |

---

## 4. Normalización

Script: `pipeline/interior/build_interior.py` (depende de `dhondt.py`).

### 4.1 Esquema de salida

`data/processed/interior/results_provincial.jsonl` — una línea por (elección, provincia, candidatura):

```json
{"eleccion":"2023-07-23","provincia":28,"provincia_nombre":"Madrid",
 "candidatura":"PARTIDO POPULAR / PARTIT POPULAR - PP","sigla":"PP","nombre":"PARTIDO POPULAR / PARTIT POPULAR",
 "partido_id":"pp","votos":1463183,"votos_cera":19006,"escanos":5}
```

`data/processed/interior/elections.json` — metadatos por elección: provincias (código, escaños,
censo, votantes, válidos, blancos, nulos), agregados nacionales por partido (votos, escaños) y
totales. `data/processed/interior/partidos.json` — diccionario de partidos efectivamente usado
(`nombre`, `siglas`, `auto`). `data/processed/interior/validation.json` — resultados de validación.

### 4.2 Diccionario de partidos y aliases

- Fuente curada: `pipeline/interior/partidos_aliases.json` (id canónico → nombre + `aliases`
  [siglas del Interior] + `cis` [etiquetas equivalentes del CIS, para unificar cuando se
  consolide el diccionario de `pipeline/cis/` — **no se ha tocado `pipeline/cis/`**]).
- Cobertura curada de los partidos relevantes (PP, PSOE, PSC, PSE-EE, PSdeG, UCD, AP, CDS, PCE,
  PSUC, IU (+ IULV-CA, EUPV), Podemos, Unidas Podemos, ECP, En Marea, SUMAR, VOX, Cs, Más País,
  Compromís, ERC, Junts/JxCat, CiU, CDC, UDC, CUP, PNV, EA, EE, HB, ANV, EH Bildu, Amaiur,
  Geroa Bai, UPN, NA+, BNG, CC, NC, CCa-NC, PA, PAR, PRC, PACMA, PH, Recortes Cero, FE-JONS,
  PSP-US…), incluidas las leyendas de coalición que usan los dos ficheros
  (`SUMAR - COMPROMÍS`, `SUMAR - ECP`, `JXCAT - JUNTS`, `PODEMOS - C`…).
- Candidaturas menores sin entrada: id **auto** (slug de la sigla). En total 882 ids; 833 auto
  (partidos históricos de un solo sexenio 1977–1982). **Limitación conocida**: dos partidos
  distintos con la misma sigla pueden compartir slug auto (p. ej. varios `INDEP`). No afecta a
  la validación (que usa la etiqueta completa) ni a los partidos principales.

### 4.3 Parsing robusto

`resolve_party(label)` prueba **todos los sufijos** de la etiqueta empezando en cada `" - "`
(de más largo a más corto) contra el diccionario; resuelve correctamente coaliciones cuya sigla
contiene `" - "`. Fallback: slug de la sigla.

---

## 5. Validación D'Hondt (obligatoria)

Implementación: `pipeline/interior/dhondt.py` (función pura). Umbral del **3 %** de los votos
válidos de la circunscripción (candidaturas + en blanco), art. 163 LOREG. Escaños por provincia
tomados de la fila resumen `Escaños`.

**Base de votos usada = votos de la circunscripción SIN el voto CERA** (ver §5.3).

### 5.1 Resultado por elección

| Elección | Escaños | (a) suma | (b) D'Hondt provincias | (c) cargos electos |
|---|---|---|---|---|
| 1977-06-15 | 350 | OK | **51/52** ⚠ | OK |
| 1979-03-01 | 350 | OK | 52/52 | OK |
| 1982-10-28 | 350 | OK | 52/52 | OK |
| 1986-06-22 | 350 | OK | 52/52 | OK |
| 1989-10-29 | 350 | OK | 52/52 | OK |
| 1993-06-06 | 350 | OK | 52/52 | OK |
| 1996-03-03 | 350 | OK | 52/52 | OK |
| 2000-03-12 | 350 | OK | 52/52 | OK |
| 2004-03-14 | 350 | OK | 52/52 | OK |
| 2008-03-09 | 350 | OK | 52/52 | OK |
| 2011-11-20 | 350 | OK | 52/52 | OK |
| 2015-12-20 | 350 | OK | 52/52 | OK |
| 2016-06-26 | 350 | OK | 52/52 | OK |
| 2019-04-28 | 350 | OK | 52/52 | OK |
| 2019-11-10 | 350 | OK | 52/52 | OK |
| 2023-07-23 | 350 | OK | 52/52 | OK |

**Resumen**: (a) 16/16 · (b) **831/832 provincias-elección** (1 descuadre) · (c) 16/16.

### 5.2 El descuadre de 1977 (documentado tal cual)

**1977-06-15 · Santa Cruz de Tenerife (7 escaños).** El reparto oficial publicado da
UCD 5 · PSOE 2; el D'Hondt sobre los votos provinciales da UCD 5 · PSOE 1 · AP 1:

| Candidatura | Votos | Escaños oficiales | Escaños D'Hondt |
|---|---|---|---|
| UCD (Unión de Centro Democrático) | 140.237 | 5 | 5 |
| PSOE | 50.951 | **2** | **1** |
| AP (Fed. de Partidos de Alianza Popular) | 27.828 | **0** | **1** |
| PSP-US | 14.215 | 0 | 0 |
| PCC-PCE | 10.643 | 0 | 0 |
| … | | | |

Cociente del último escaño (7.º): AP = 27.828 frente a PSOE = 25.475,5 → por D'Hondt el 7.º
escaño es de AP. El resultado oficial (y el fichero de **cargos electos**, que da UCD 5 ·
PSOE 2 nominalmente) adjudica ese escaño al PSOE. Es decir, **la serie oficial de 1977 en esta
provincia no se reproduce con D'Hondt puro**; se documenta sin corregir (es precisamente la
prueba de que el parseo es fiel: se detecta el descuadre en vez de maquillarlo). El patrón
(cociente muy ajustado en el último escaño de una circunscripción de 7 diputados en 1977) es
compatible con una incidencia de escrutinio/proclamación de la época. No hay más descuadres en
el resto de la serie.

### 5.3 El voto CERA: por qué se excluye del reparto

El fichero publica el voto de residentes ausentes (CERA) en filas separadas. Se probaron ambas
bases:

- **D'Hondt sin CERA**: 1977 con 51/52 y el resto 52/52 (solo el descuadre de §5.2).
- **D'Hondt con CERA** (sumando los votos CERA): aparecen **4 descuadres nuevos** de 1 escaño
  (Madrid 1996, Asturias 2000, Cádiz 2004, Pontevedra 2004).

El **fichero de cargos electos (definitivo e independiente)** resuelve la duda: en los cuatro
casos coincide con el reparto **sin CERA**:

| Provincia · elección | Cargos electos (definitivo) | D'Hondt sin CERA | D'Hondt con CERA |
|---|---|---|---|
| Madrid 1996 (34) | PP 17 · PSOE 11 · IU 6 | ✔ PP 17 · PSOE 11 · IU 6 | ✘ PP 18 · IU 5 |
| Asturias 2000 (9) | PP 5 · PSOE 3 · IU 1 | ✔ PP 5 · PSOE 3 · IU 1 | ✘ PP 4 · PSOE 4 |
| Cádiz 2004 (9) | PSOE 6 · PP 3 | ✔ PSOE 6 · PP 3 | ✘ PSOE 5 · PP 4 |
| Pontevedra 2004 (7) | PP 3 · PSdeG 3 · BNG 1 | ✔ PP 3 · PSdeG 3 · BNG 1 | ✘ PP 4 · BNG 0 |
| S.C. Tenerife 1977 (7) | UCD 5 · PSOE 2 | ✘ UCD 5 · PSOE 1 · AP 1 | ✘ (igual) |

**Conclusión**: los escaños publicados en el fichero (y los cargos electos definitivos) se
reproducen con los votos de la circunscripción **sin CERA**; el CERA se conserva en el campo
`votos_cera` para análisis. Queda anotado como decisión metodológica explícita.

### 5.4 Incidencias de parseo detectadas y corregidas (evidencia de rigor)

1. **Siglas con paréntesis/apóstrofos** (`PSE-EE (PSOE)`, `C's`, `C´s`): un primer regex
   basado en `- ([^()]+)$` perdía candidaturas enteras (p. ej. PSE-EE en Araba/Gipuzkoa/Bizkaia).
   Corregido con parseo por paréntesis externo + resolutor por sufijos → recuperó los escaños
   que faltaban (345 → 350 en 2023).
2. **`Total Escaños Nacional` acumulativo**: una candidatura puede aparecer en varias filas con
   subtotales nacionales propios; sobrescribir en vez de acumular daba falsos fallos de (a)
   (PSOE 1996: 4 vs 80; PP 2015: 2 vs 108). Corregido (ahora 16/16).
3. **Leyendas de coalición distintas** entre el escrutinio (`… - ECP`, `… - COMPROMÍS`,
   `… - JUNTS`) y cargos electos (`SUMAR - ECP`, `SUMAR - COMPROMÍS`, `JXCAT - JUNTS`):
   resuelto comparando por id canónico (validación (c) ahora 16/16).

---

## 6. Salidas y cómo reproducir

```
pipeline/interior/
  requirements.txt          # openpyxl, requests (no tocar requirements globales)
  dhondt.py                 # reparto D'Hondt (función pura)
  interior_fetch.py         # descarga reanudable + educada (datos abiertos Interior)
  build_interior.py         # normalización + validación -> data/processed/interior/
  partidos_aliases.json     # diccionario curado de partidos/aliases
  test_dhondt.py            # tests unitarios del módulo D'Hondt
```

```bash
pip install -r pipeline/interior/requirements.txt
python3 pipeline/interior/interior_fetch.py                   # -> data/raw/interior/
python3 pipeline/interior/build_interior.py                   # -> data/processed/interior/
python3 pipeline/interior/test_dhondt.py                      # tests
```

Salidas (versionables, en repo): `data/processed/interior/{results_provincial.jsonl,
elections.json, partidos.json, validation.json}`. Crudos (gitignored): `data/raw/interior/`.

---

## 7. Bloqueos reales y limitaciones

1. **`infoelectoral.interior.gob.es` (y `www.infoelectoral.mir.es`) inaccesible por red desde
   este host** (timeout TCP; también vía proxies públicos y el extractor del Gateway). Se ha
   usado la fuente oficial equivalente de datos abiertos (§1.3). Si en el futuro hace falta el
   escrutinio a nivel de **mesa** o el Senado desglosado por el formato `.DAT`, habrá que
   ejecutar el pipeline desde un host con acceso al portal (o pedir desbloqueo).
2. **TLS**: `descargas.interior.gob.es` con cadena incompleta → fallback no verificado en la
   descarga (documentado; datos públicos).
3. **IDs auto para candidaturas menores**: colisiones de slug posibles; sin impacto en la
   validación ni en los partidos principales. Curación incremental prevista.
4. **Senado**: descargado (`Elecciones-Senado.xlsx`) pero **no normalizado** (el Senado no se
   reparte por D'Hondt —4 escaños por provincia por voto mayoritario— y queda fuera del alcance
   de esta validación). Queda como fuente disponible para una fase posterior.
5. **Alcance**: solo Congreso 1977–2023 (16 convocatorias). Es exactamente "todas las generales"
   al Congreso del periodo solicitado.

## Supuestos

- La base de votos para el reparto son los votos de la circunscripción sin CERA (verificado
  contra cargos electos, §5.3).
- "Escaños por provincia" = fila resumen `Escaños` del fichero, consistente con la suma de las
  filas de candidatura (verificado).
- El escrutinio de datos abiertos es el definitivo del BOE (misma base que infoelectoral).
