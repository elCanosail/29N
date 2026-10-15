# 29N

Todo el dato electoral español, con predicción honesta y auditable.

29N expone el histórico completo de encuestas electorales españolas (microdatos del CIS y fichas técnicas de encuestadores privados), los resultados oficiales de todas las elecciones generales desde 1977, y una predicción por provincias de las próximas elecciones usando TimesFM (Google Research, open source).

**El valor es el método, no el resultado.** Este proyecto es partidistamente neutro: publica intervalos, no titulares.

## Qué hay aquí

```
pipeline/   Ingesta → normalización → validación → predicción (Python)
data/       Datos normalizados versionados (los crudos se re-descargan)
web/        Web pública (Astro, desplegada en Vercel)
docs/       Metodología, plan, notas de calidad
```

## Fuentes

- **CIS** (Banco de Datos): serie preelectoral desde 1979, microdatos abiertos. Fuente: cis.es
- **Ministerio de Interior** (infoelectoral): escrutinio provincial por candidatura desde 1977. Fuente: infoelectoral.mir.es
- **Encuestadores privados** (GAD3, 40dB, Sigma Dos, NC Report, y otros): recolectados de sus fichas técnicas publicadas en prensa. Toda encuesta entra con URL de su ficha técnica, sin excepciones.

## Reproducir

```bash
# Requisitos: Python 3.12+
python -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt
# (en construcción — ver docs/plan)
```

## Compromisos metodológicos

1. Todo dato de la web es trazable a su fuente y clicable.
2. El error del backtest se publica, sin maquillaje.
3. Las predicciones llevan intervalos, nunca cifras puntuales.
4. Las sumas provinciales cuadran con la predicción estatal (coherencia verificada).
5. Log de exclusiones público: una encuesta que no pasa validación se documenta.

## Estado

Fase 0 en curso. Ver `docs/plan.md` para fases y verificaciones.

## Licencia

Código bajo MIT. Los datos pertenecen a sus fuentes (CIS, Ministerio de Interior, encuestadores); este proyecto los procesa y enlaza, citando siempre su origen.

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md). El primer buen punto de entrada es el diccionario de partidos (aliases, fusiones y candidaturas históricas).
