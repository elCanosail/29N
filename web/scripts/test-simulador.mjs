#!/usr/bin/env node
/**
 * test-simulador.mjs — contratos del Simulador 29N (`postbuild`).
 *
 * Nació de dos fallos reales:
 *   1. `base23.json` se quedó congelado el 15-10 mientras el modelo se
 *      regeneraba: el simulador arrancaba con PP al 35,4 % cuando el modelo
 *      publicaba 32,7 %, once escaños de diferencia en reposo. Se comprueba que
 *      el punto de partida coincide con `forecast.json`.
 *   2. El JS recreaba las filas de la tabla con `innerHTML`, perdiendo el
 *      atributo de scope de Astro: todo el CSS de la tabla dejaba de aplicarse y
 *      los números se pegaban en una sola línea. Se comprueba que el HTML
 *      servido trae las filas y las celdas ya creadas, con sus `data-*`.
 *
 * Sin dependencias ni red.
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const aquí = dirname(fileURLToPath(import.meta.url));
const web = join(aquí, '..');
const dist = join(web, 'dist', 'simulador', 'index.html');

const fallos = [];
const ok = (m) => console.log(`  ✓ ${m}`);
const mal = (m) => {
  fallos.push(m);
  console.log(`  ✗ ${m}`);
};

if (!existsSync(dist)) {
  console.error('test-simulador: falta dist/simulador/index.html. Ejecuta `npm run build`.');
  process.exit(1);
}

const base = JSON.parse(readFileSync(join(web, 'src', 'data', 'base23.json'), 'utf8'));
const forecast = JSON.parse(readFileSync(join(web, 'src', 'data', 'forecast.json'), 'utf8'));
const html = readFileSync(dist, 'utf8');

console.log('1. La base del simulador es la del modelo');
const punto = forecast.partidos.map((p) => [p.partido, p.punto]);
const desviados = punto
  .map(([k, v]) => [k, Math.abs((base.punto_modelo?.[k] ?? 0) - v)])
  .filter(([, d]) => d > 0.005);
if (!base.punto_modelo) mal('base23.json no trae punto_modelo');
else if (desviados.length === 0) ok(`los ${punto.length} partidos parten del punto de forecast.json`);
else
  mal(
    `base23.json está desfasado respecto al modelo: ${desviados
      .map(([k, d]) => `${k} ${d.toFixed(3)} pp`)
      .join(', ')} → regenera con pipeline/simulador/export_base23.py`,
  );

const suma = Object.values(base.punto_modelo ?? {}).reduce((a, b) => a + b, 0);
if (Math.abs(suma - 100) <= 0.05) ok(`el punto de partida suma ${suma.toFixed(2)} %`);
else mal(`el punto de partida suma ${suma.toFixed(3)} %, no 100`);

console.log('2. Filas y tramos servidos en el HTML (no los crea el JS)');
// Solo el marcado: el script inline también cita `data-fila`.
const filas = [...html.matchAll(/<div class="reparto__fila" data-fila="([^"]+)"/g)].map((m) => m[1]);
if (filas.length === base.partidos.length) ok(`${filas.length} filas, una por partido`);
else mal(`${filas.length} filas servidas y ${base.partidos.length} partidos`);
const faltanCeldas = base.partidos.filter(
  (p) =>
    !new RegExp(
      `data-fila="${p.replace(/[+$.^]/g, '\\$&')}"[\\s\\S]{0,600}?data-celda="escanos"[\\s\\S]{0,400}?data-celda="delta"[\\s\\S]{0,400}?data-celda="pct"`,
    ).test(html),
);
if (faltanCeldas.length === 0) ok('cada fila trae escanos, delta y pct');
else mal(`sin celdas marcadas: ${faltanCeldas.join(', ')}`);

const tramos = [...html.matchAll(/class="reparto__tramo"[^>]*data-partido="([^"]+)"/g)].map((m) => m[1]);
if (tramos.length === base.partidos.length) ok(`${tramos.length} tramos de barra servidos`);
else mal(`${tramos.length} tramos servidos y ${base.partidos.length} partidos`);

console.log('3. Marcador móvil');
if (/id="hud-dato"/.test(html) && /id="reset-hud"/.test(html)) ok('marcador y botón «central» presentes');
else mal('falta el marcador móvil (#hud-dato / #reset-hud)');

console.log('4. El JS actualiza, no recrea');
if (/filas\.innerHTML\s*=\s*''/.test(html)) mal("el script vacía #filas con innerHTML: perdería el scope de Astro");
else ok('no se vacía la tabla desde el script');

console.log('');
if (fallos.length) {
  console.error(`test-simulador: ${fallos.length} fallo(s)\n  - ${fallos.join('\n  - ')}`);
  process.exit(1);
}
console.log('test-simulador: OK — el simulador parte del modelo y sirve su tabla desde el HTML.');
