#!/usr/bin/env node
/**
 * test-hemiciclo.mjs — contratos del hemiciclo de la home (`postbuild`).
 *
 * Patrón: test-needle.mjs. Comprueba sobre `dist/index.html` ya construido:
 *   1. El SVG existe y el anillo 29N tiene exactamente 350 círculos.
 *   2. El anillo 23J tiene exactamente 350.
 *   3. Existe la marca de mayoría con el texto «176».
 *   4. La leyenda contiene PP, PSOE y VOX con sus tres cifras (29N y 23J).
 *   5. El aria-label menciona la mayoría y el reparto.
 *   6. La suma de escaños de la leyenda es 350 en ambos anillos.
 *   7. El orden de partidos del gráfico es el ideológico fijado.
 *
 * Sin dependencias ni red. Si algo falla, `npm run build` falla.
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const aquí = dirname(fileURLToPath(import.meta.url));
const web = join(aquí, '..');
const dist = join(web, 'dist', 'index.html');

const fallos = [];
const ok = (m) => console.log(`  ✓ ${m}`);
const mal = (m) => {
  fallos.push(m);
  console.log(`  ✗ ${m}`);
};

if (!existsSync(dist)) {
  console.error('test-hemiciclo: no hay dist/index.html. Ejecuta `npm run build` antes.');
  process.exit(1);
}

const html = readFileSync(dist, 'utf8');

console.log('1. SVG y anillo 29N (350 círculos)');
const svg = html.match(/<svg[^>]*class="hemi__svg"[\s\S]*?<\/svg>/);
if (!svg) mal('no se encuentra el <svg class="hemi__svg">');
const svgTxt = svg ? svg[0] : '';
const circulos29 = [...svgTxt.matchAll(/data-anillo="29n"/g)].length;
if (circulos29 === 350) ok('350 círculos en el anillo 29N');
else mal(`el anillo 29N tiene ${circulos29} círculos, no 350`);

console.log('2. Anillo 23J (350 círculos)');
const circulos23 = [...svgTxt.matchAll(/data-anillo="23j"/g)].length;
if (circulos23 === 350) ok('350 círculos en el anillo 23J');
else mal(`el anillo 23J tiene ${circulos23} círculos, no 350`);
// Los círculos son <circle>, no otro elemento marcado por error.
const circles = [...svgTxt.matchAll(/<circle\b/g)].length;
if (circles === 700) ok('700 elementos <circle> en total (350 + 350)');
else mal(`hay ${circles} <circle>, se esperaban 700`);

console.log('3. Marca de mayoría');
const marca = svgTxt.match(/class="hemi__mayoria[\s\S]*?<\/g>/);
if (marca && /class="hemi__mayoria-linea"/.test(marca[0])) ok('línea radial discontinua presente');
else mal('falta la línea radial de mayoría');
// La etiqueta dice «mayoría absoluta · 176»: el test exige el número y el concepto.
if (marca && /class="hemi__mayoria-etiqueta[^"]*"[^>]*>[^<]*176[^<]*</.test(marca[0])) {
  ok('la etiqueta de la marca lleva el 176');
  if (/mayor[ií]a absoluta/i.test(marca[0])) ok('y dice «mayoría absoluta»');
  else mal('la marca no dice «mayoría absoluta»');
}
else mal('la marca de mayoría no lleva el texto «176»');

console.log('4. Leyenda: PP, PSOE y VOX con sus tres cifras');
const leyenda = html.match(/<ul class="hemi__leyenda"[\s\S]*?<\/ul>/);
const leyendaTxt = leyenda ? leyenda[0] : '';
if (!leyenda) mal('no se encuentra <ul class="hemi__leyenda">');
const filasLeyenda = [...leyendaTxt.matchAll(
  /data-partido="([^"]+)"\s+data-escanos-29n="(\d+)"\s+data-escanos-23j="(\d+)"/g,
)].map((m) => ({ clave: m[1], n29: Number(m[2]), n23: Number(m[3]) }));
for (const clave of ['PP', 'PSOE', 'VOX']) {
  const fila = filasLeyenda.find((f) => f.clave === clave);
  if (!fila) {
    mal(`falta ${clave} en la leyenda`);
    continue;
  }
  const texto = leyendaTxt.slice(leyendaTxt.indexOf(`data-partido="${clave}"`), leyendaTxt.indexOf('</li>', leyendaTxt.indexOf(`data-partido="${clave}"`)));
  const cifras = [fila.n29, fila.n23].every((n) => new RegExp(`>\\s*${n}\\s*<`).test(texto));
  if (cifras) ok(`${clave}: punto de color, sigla, ${fila.n29} (29N) y ${fila.n23} (23J)`);
  else mal(`${clave}: faltan las cifras visibles ${fila.n29}/${fila.n23}`);
}

console.log('5. aria-label: mayoría y reparto');
const aria = svgTxt.match(/aria-label="([^"]+)"/);
if (aria) {
  const t = aria[1];
  if (/mayor[ií]a absoluta/i.test(t) && /176/.test(t) && /de izquierda a derecha/.test(t) && /350/.test(t)) {
    ok('menciona la mayoría, 176, el reparto y los 350 escaños');
  } else mal(`aria-label incompleto: «${t.slice(0, 120)}…»`);
} else mal('el SVG no trae aria-label');

console.log('6. Suma de la leyenda = 350 en ambos anillos');
const suma29 = filasLeyenda.reduce((a, f) => a + f.n29, 0);
const suma23 = filasLeyenda.reduce((a, f) => a + f.n23, 0);
if (suma29 === 350) ok(`29N suma ${suma29}`);
else mal(`29N suma ${suma29}, no 350`);
if (suma23 === 350) ok(`23J suma ${suma23}`);
else mal(`23J suma ${suma23}, no 350`);

// Lo que dice la leyenda debe ser EXACTAMENTE lo que está dibujado: un reparto
// por fila (en vez de por ángulo) hace que los círculos por partido no cuadren
// con la leyenda aunque el total siga siendo 350. Esto lo caza.
const circulosPorPartido = (anillo) => {
  const out = {};
  const re = new RegExp(`data-anillo="${anillo}" data-partido="([^"]+)"`, 'g');
  for (const m of svgTxt.matchAll(re)) out[m[1]] = (out[m[1]] ?? 0) + 1;
  return out;
};
const dib29 = circulosPorPartido('29n');
const dib23 = circulosPorPartido('23j');
const desajuste = filasLeyenda.filter(
  (f) => (dib29[f.clave] ?? 0) !== f.n29 || (dib23[f.clave] ?? 0) !== f.n23,
);
if (desajuste.length === 0) ok('cada partido tiene en el SVG los escaños que anuncia la leyenda');
else mal(`leyenda y círculos divergen: ${desajuste.map((f) => `${f.clave} leyenda ${f.n29}/${f.n23} vs SVG ${dib29[f.clave] ?? 0}/${dib23[f.clave] ?? 0}`).join('; ')}`);

console.log('7. Orden ideológico de partidos');
const ORDEN = ['SUMAR', 'PSOE', 'ERC', 'EH BILDU', 'BNG', 'CUP', 'PNV', 'JXCAT', 'CC', 'NA+', 'PP', 'VOX'];
const ordenLeyenda = filasLeyenda.map((f) => f.clave);
const ordenEsperado = ORDEN.filter((k) => ordenLeyenda.includes(k));
if (ordenLeyenda.join('|') === ordenEsperado.join('|')) ok('la leyenda sigue el orden del gráfico');
else mal(`orden de leyenda inesperado: ${ordenLeyenda.join(', ')}`);
// El orden real de las cuñas se lee de los círculos: primera aparición de cada
// clave en el anillo 29N (ya ordenados de π a 0 en el markup).
const orden29 = [];
for (const m of svgTxt.matchAll(/data-anillo="29n" data-partido="([^"]+)"/g)) {
  if (!orden29.includes(m[1])) orden29.push(m[1]);
}
const esperado29 = ORDEN.filter((k) => orden29.includes(k));
if (orden29.join('|') === esperado29.join('|')) ok(`cuñas en orden: ${orden29.join(' · ')}`);
else mal(`cuñas desordenadas: ${orden29.join(', ')}`);

console.log('8. Geometría: sin solapes y dentro del lienzo');
// Sin esto, el círculo del 23J puede dibujarse con radio 4,5 y solo 6,67 de
// separación radial: 356 pares solapados y todos los escaños afectados.
const circulos = [...svgTxt.matchAll(
  /data-anillo="(29n|23j)"[^>]*cx="([\d.]+)"[^>]*cy="([\d.]+)"[^>]*r="([\d.]+)"/g,
)].map((m) => ({ anillo: m[1], x: +m[2], y: +m[3], r: +m[4] }));
const porAnillo = (a) => circulos.filter((c) => c.anillo === a);
for (const anillo of ['29n', '23j']) {
  const cs = porAnillo(anillo);
  if (cs.length !== 350) {
    mal(`${anillo}: ${cs.length} círculos, no 350`);
    continue;
  }
  let min = Infinity;
  for (let i = 0; i < cs.length; i++) {
    for (let j = i + 1; j < cs.length; j++) {
      const d = Math.hypot(cs[i].x - cs[j].x, cs[i].y - cs[j].y);
      if (d < min) min = d;
    }
  }
  const necesario = 2 * cs[0].r;
  if (min >= necesario * 0.95) ok(`${anillo}: separación mínima ${min.toFixed(1)} para diámetro ${necesario.toFixed(1)}`);
  else mal(`${anillo}: puntos solapados (${min.toFixed(1)} < ${necesario.toFixed(1)})`);
}
const fuera = circulos.filter((c) => c.x - c.r < 0 || c.x + c.r > 1000 || c.y - c.r < 0 || c.y + c.r > 560);
if (fuera.length === 0) ok('ningún escaño se sale del lienzo 1000×560');
else mal(`${fuera.length} escaños fuera del lienzo`);

console.log('9. aria-label: el 23J también se cuenta');
if (aria && /23J/.test(aria[1]) && /\d/.test(aria[1].split('23J')[1] ?? '')) {
  ok('la descripción accesible incluye el reparto del 23J');
} else mal('el aria-label no cuenta el reparto del 23J');

console.log('');
if (fallos.length) {
  console.error(`test-hemiciclo: ${fallos.length} fallo(s)\n  - ${fallos.join('\n  - ')}`);
  process.exit(1);
}
console.log('test-hemiciclo: OK — 350 + 350 escaños, mayoría en 176, leyenda y reparto cuadrados.');
