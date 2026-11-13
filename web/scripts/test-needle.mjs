#!/usr/bin/env node
/**
 * test-needle.mjs — contratos de Needle29N (issue #15 › PR-4).
 *
 * Comprueba sobre `dist/index.html` ya construido (`postbuild`):
 *   1. Las tres probabilidades existen, son enteras y suman 100 (±0,1).
 *   2. Cada una casa con `seats.json.bloques` tras redondear a entero.
 *   3. El rango de escaños de cada bloque está a la vista y coincide con `ic95`.
 *   4. Las cifras no llevan decimales (se publica «6 %», nunca «5,9 %»).
 *   5. La nota de método dice el número real de simulaciones (`meta.n_runs`).
 *   6. La composición de cada bloque cita los partidos que trae el JSON.
 *
 * Sin dependencias ni red. Si algo falla, `npm run build` falla.
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const aquí = dirname(fileURLToPath(import.meta.url));
const web = join(aquí, '..');
const dist = join(web, 'dist');

const fallos = [];
const ok = (m) => console.log(`  ✓ ${m}`);
const mal = (m) => {
  fallos.push(m);
  console.log(`  ✗ ${m}`);
};

if (!existsSync(join(dist, 'index.html'))) {
  console.error('test-needle: no hay dist/index.html. Ejecuta `npm run build` antes.');
  process.exit(1);
}

const html = readFileSync(join(dist, 'index.html'), 'utf8');
const seats = JSON.parse(readFileSync(join(web, 'src', 'data', 'seats.json'), 'utf8'));
const bloques = seats.bloques;
if (!bloques) {
  console.error('test-needle: seats.json no trae `bloques`. ¿Falta el PR-2 en esta rama?');
  process.exit(1);
}

const esperado = {
  izquierda: Math.round(bloques.izquierda.p_ge176 * 100),
  derecha: Math.round(bloques.derecha.p_ge176 * 100),
  ninguno: Math.round(bloques.p_ninguno * 100),
};

console.log('1-2. Probabilidades');
const leidos = Object.fromEntries(
  [...html.matchAll(/data-bloque="(izquierda|derecha|ninguno)"\s+data-pct="([^"]+)"/g)].map((m) => [m[1], m[2]]),
);
const faltan = Object.keys(esperado).filter((k) => !(k in leidos));
if (faltan.length) mal(`falta la cifra de: ${faltan.join(', ')}`);
const noEnteras = Object.entries(leidos).filter(([, v]) => !/^\d+$/.test(v));
if (noEnteras.length) mal(`probabilidades no enteras: ${noEnteras.map(([k, v]) => `${k}=${v}`).join(', ')}`);
const suma = Object.values(leidos).reduce((a, v) => a + Number(v), 0);
if (Math.abs(suma - 100) <= 0.1) ok(`las tres suman ${suma} %`);
else mal(`las tres probabilidades suman ${suma} %, no 100`);
for (const [clave, valor] of Object.entries(esperado)) {
  if (leidos[clave] === undefined) continue;
  if (Number(leidos[clave]) === valor) ok(`${clave}: ${valor} % casa con seats.json`);
  else mal(`${clave}: la web dice ${leidos[clave]} % y seats.json redondea a ${valor} %`);
}

console.log('3. Rango de escaños a la vista');
const needle = html.slice(html.indexOf('class="needle"'), html.indexOf('</section>', html.indexOf('class="needle"')));
for (const [clave, bloque] of [['izquierda', bloques.izquierda], ['derecha', bloques.derecha]]) {
  const rango = `${bloque.ic95[0]}–${bloque.ic95[1]} escaños`;
  if (needle.includes(rango)) ok(`${clave}: «${rango}»`);
  else mal(`${clave}: falta el rango «${rango}» junto a la cifra`);
}
if (/sin mayoría/.test(needle)) ok('ninguno se rotula «sin mayoría»');

console.log('4. Sin decimales');
const decimales = [...needle.matchAll(/>(\d+[.,]\d+)\s*%/g)].map((m) => m[1]);
if (decimales.length === 0) ok('ninguna probabilidad con decimales');
else mal(`probabilidades con decimales: ${decimales.join(', ')}`);

console.log('5. Nota de método');
const runs = new Intl.NumberFormat('es-ES').format(seats.meta.n_runs);
if (needle.includes(`${runs} simulaciones`)) ok(`${runs} simulaciones, como meta.n_runs`);
else faltan.push(`nota de método con ${runs}`);
if (faltan.length) mal(`no se lee «${runs} simulaciones» en el bloque`);

console.log('6. Composición de bloques citada');
const limpio = (t) => t.replace(/\s+/g, ' ');
// El componente publica «A, B, C y D»: la lista se compara con ese mismo formato.
const composicion = (ps) => ps.join(', ').replace(/, ([^,]*)$/, ' y $1');
for (const [clave, bloque] of [['izquierda', bloques.izquierda], ['derecha', bloques.derecha]]) {
  if (limpio(needle).includes(limpio(composicion(bloque.partidos))) ) ok(`${clave}: cita ${bloque.partidos.length} partidos`);
  else mal(`${clave}: la web no cita la composición (${composicion(bloque.partidos)})`);
}
if (/\/metodologia\/#bloques/.test(needle)) ok('enlaza a /metodologia/#bloques');
else mal('falta el enlace a /metodologia/#bloques');

console.log('');
if (fallos.length) {
  console.error(`test-needle: ${fallos.length} fallo(s)\n  - ${fallos.join('\n  - ')}`);
  process.exit(1);
}
console.log('test-needle: OK — Needle29N cumple los criterios de #15 › PR-4.');
