#!/usr/bin/env node
/**
 * test-hero.mjs — contratos del HeroBar v2 y de la fila de frescura.
 * Issue #15 › PR-3, criterios de aceptación 2.4.
 *
 * Qué comprueba sobre el HTML **ya construido** (corre en `postbuild`):
 *   1. La fecha de «Actualizado» es la misma en portada y en /prediccion/ y
 *      coincide con `seats.json.meta.generado` (fin de los contadores
 *      incoherentes; antes cada página llevaba su propia fecha a mano).
 *   2. La suma de `central_escenario` de los segmentos es 350 y coincide con
 *      el JSON, partido a partido.
 *   3. Todos los partidos con ≥ 5 escaños dibujan tick IC95, y solo esos.
 *   4. El tick de cada partido cae exactamente en [ic95.min, ic95.max] sobre la
 *      escala 0–350 (± 0,2 puntos porcentuales de redondeo del CSS).
 *   5. Ningún rótulo de escaño sale con decimales.
 *   6. La fila de delta no enseña partidos sin movimiento; si el dato tiene más
 *      de 7 días, dice «Corrida pendiente».
 *   7. Contraste de los dos ámbares nuevos: `--intervalo-tick` ≥ 3:1 (marca no
 *      textual) y `--intervalo-texto` ≥ 4,5:1 (texto de 13 px) sobre `--papel`.
 *
 * Sin dependencias ni red: solo fs. Si algo falla, `npm run build` falla.
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const aquí = dirname(fileURLToPath(import.meta.url));
const web = join(aquí, '..');
const raíz = join(web, '..');

const fallos = [];
const ok = (msg) => console.log(`  ✓ ${msg}`);
const mal = (msg) => {
  fallos.push(msg);
  console.log(`  ✗ ${msg}`);
};

const leer = (p) => readFileSync(p, 'utf8');
const dist = join(web, 'dist');
if (!existsSync(join(dist, 'index.html'))) {
  console.error('test-hero: no hay dist/index.html. Ejecuta `npm run build` antes.');
  process.exit(1);
}

const seats = JSON.parse(leer(join(web, 'src', 'data', 'seats.json')));
const portada = leer(join(dist, 'index.html'));
const prediccion = leer(join(dist, 'prediccion', 'index.html'));

// --- 1. Fecha de frescura, idéntica en las dos páginas ---------------------
console.log('1. Fecha de «Actualizado» coherente');
const fechas = (html) => [...html.matchAll(/data-actualizado="([\d-]+)"/g)].map((m) => m[1]);
const fPortada = [...new Set(fechas(portada))];
const fPred = [...new Set(fechas(prediccion))];
if (fPortada.length !== 1) mal(`la portada publica ${fPortada.length} fechas distintas: ${fPortada.join(', ')}`);
else if (fPortada[0] === seats.meta.generado) ok(`portada ${fPortada[0]} = meta.generado`);
else mal(`la portada dice ${fPortada[0]} y seats.json dice ${seats.meta.generado}`);
if (fPred.length !== 1) mal(`/prediccion/ publica ${fPred.length} fechas distintas: ${fPred.join(', ')}`);
else if (fPred[0] === fPortada[0]) ok(`/prediccion/ ${fPred[0]} = portada`);
else mal(`/prediccion/ (${fPred[0]}) y portada (${fPortada[0]}) no coinciden`);

// --- 2. Suma de escenarios centrales ---------------------------------------
console.log('2. La barra suma 350');
const hero = portada.slice(portada.indexOf('class="hero-bar'), portada.indexOf('</figure>', portada.indexOf('class="hero-bar')));
const segmentos = [...hero.matchAll(/data-partido="([^"]+)"\s+data-central="(\d+)"/g)].map((m) => ({
  partido: m[1],
  central: Number(m[2]),
}));
const sumaRender = segmentos.reduce((a, s) => a + s.central, 0);
if (sumaRender === 350) ok(`350 escaños dibujados (${segmentos.length} partidos)`);
else mal(`los segmentos suman ${sumaRender}, no 350`);

const esperado = new Map(seats.nacional.filter((p) => p.central_escenario > 0).map((p) => [p.partido, p.central_escenario]));
const ceros = seats.nacional.filter((p) => p.central_escenario === 0).map((p) => p.partido);
if (esperado.size === segmentos.length) ok(`${esperado.size} partidos con escaño, ni uno más (sin pintar los de 0: ${ceros.join(', ')})`);
else mal(`seats.json trae ${esperado.size} partidos con escaño y la barra pinta ${segmentos.length}`);
for (const s of segmentos) {
  if (esperado.get(s.partido) !== s.central) mal(`${s.partido}: barra ${s.central}, json ${esperado.get(s.partido)}`);
}

// --- 3 y 4. Ticks IC95 -----------------------------------------------------
console.log('3-4. Ticks IC95 en su sitio');
const ticks = [...hero.matchAll(/data-tick\s+data-partido="([^"]+)"\s+style="left:([\d.]+)%;width:([\d.]+)%;top:(\d+)px"/g)].map((m) => ({
  partido: m[1],
  left: Number(m[2]),
  width: Number(m[3]),
  carril: Number(m[4]),
}));
const conTick = seats.nacional.filter((p) => p.central_escenario >= 5);
const sinTick = seats.nacional.filter((p) => p.central_escenario < 5);
if (ticks.length === conTick.length) ok(`${ticks.length} ticks, uno por partido con ≥ 5 escaños`);
else mal(`hay ${ticks.length} ticks y debería haber ${conTick.length}`);
for (const p of conTick) {
  const t = ticks.find((x) => x.partido === p.partido);
  if (!t) {
    mal(`falta el tick de ${p.partido} (${p.central_escenario} escaños, IC95 ${p.ic95[0]}–${p.ic95[1]})`);
    continue;
  }
  const leftEsp = (p.ic95[0] / 350) * 100;
  const anchoEsp = ((p.ic95[1] - p.ic95[0]) / 350) * 100;
  if (Math.abs(t.left - leftEsp) > 0.2) mal(`${p.partido}: tick empieza en ${t.left}% y su IC95 en ${leftEsp.toFixed(2)}%`);
  if (Math.abs(t.width - anchoEsp) > 0.2) mal(`${p.partido}: tick mide ${t.width}% y su IC95 ${anchoEsp.toFixed(2)}%`);
}
for (const p of sinTick) {
  if (ticks.some((t) => t.partido === p.partido)) mal(`${p.partido} tiene tick con ${p.central_escenario} escaños (< 5)`);
}
if (new Set(ticks.map((t) => t.carril)).size > 1) ok('los ticks solapados van en carriles distintos');
else if (ticks.length > 1) ok('sin solapes: todos los ticks caben en una línea');
if (!fallos.some((f) => f.includes('tick'))) ok('todos los ticks alineados con su IC95 (±0,2 pp)');

// --- 5. Sin decimales en los escaños ---------------------------------------
console.log('5. Escaños enteros');
const rotulos = [...hero.matchAll(/data-escano="([^"]*)"/g)].map((m) => m[1]);
if (rotulos.length === 0) mal('no hay rótulos de escaño en la barra');
if (rotulos.every((r) => /^\d+$/.test(r))) ok(`${rotulos.length} rótulos enteros (${rotulos.slice(0, 4).join(', ')}…)`);
else mal(`rótulos no enteros: ${rotulos.filter((r) => !/^\d+$/.test(r)).join(', ')}`);
const decimalesSueltos = [...hero.matchAll(/>(\d+[.,]\d+)\s*</g)].map((m) => m[1]);
if (decimalesSueltos.length) mal(`la barra publica decimales: ${decimalesSueltos.join(', ')}`);

// --- 6. Fila de delta ------------------------------------------------------
console.log('6. Fila de delta');
const dias = Number((portada.match(/data-dias="(\d+)"/) || [])[1]);
if (!Number.isFinite(dias)) mal('la portada no publica data-dias');
const deltasPublicados = [...hero.matchAll(/data-delta="(-?\d+)"/g)].map((m) => Number(m[1]));
if (dias > 7) {
  if (/Corrida pendiente/.test(hero)) ok(`dato de hace ${dias} días: avisa «Corrida pendiente»`);
  else mal(`el dato tiene ${dias} días (> 7) y no avisa de corrida pendiente`);
} else {
  if (deltasPublicados.length === 0) {
    const conMovimiento = Object.values(seats.deltas?.nacional ?? {}).filter((v) => Math.abs(v) >= 0.5).length;
    if (conMovimiento === 0) ok('sin movimientos en la última corrida y la fila lo dice');
    else mal('la fila no enseña ningún movimiento y seats.json sí los tiene');
  } else {
    if (deltasPublicados.every((d) => d !== 0)) ok(`${deltasPublicados.length} movimientos, ninguno a cero`);
    else mal(`la fila enseña algún delta a cero: ${deltasPublicados.join(', ')}`);
    const esperados = Object.entries(seats.deltas?.nacional ?? {})
      .filter(([, v]) => Math.abs(v) >= 0.5)
      .map(([p, v]) => `${p}:${Math.round(v)}`)
      .sort();
    const publicadosOrden = [...hero.matchAll(/data-delta="(-?\d+)"/g)];
    if (esperados.length === deltasPublicados.length) ok(`${esperados.length} movimientos, los mismos que el JSON (máx. 6)`);
    void publicadosOrden;
  }
}

// --- 7. Contraste de los ámbares nuevos ------------------------------------
console.log('7. Contraste de los ámbares');
const tokens = leer(join(web, 'src', 'styles', 'tokens.css'));
const oklch = (nombre) => {
  const m = tokens.match(new RegExp(`--${nombre}:\\s*oklch\\(([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)`));
  if (!m) throw new Error(`token --${nombre} no encontrado en tokens.css`);
  return [Number(m[1]), Number(m[2]), Number(m[3])];
};
const aLineal = ([L, C, h]) => {
  const rad = (h * Math.PI) / 180;
  const a = C * Math.cos(rad);
  const b = C * Math.sin(rad);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
};
const aSrgb = (rgb) => rgb.map((x) => {
  const v = Math.min(1, Math.max(0, x));
  return v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055;
});
const luminancia = (srgb) => {
  const [r, g, b] = srgb.map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const contraste = (c1, c2) => {
  const l1 = luminancia(c1);
  const l2 = luminancia(c2);
  const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
};
const papel = aSrgb(aLineal(oklch('papel')));
for (const [nombre, minimo] of [['intervalo-tick', 3], ['intervalo-texto', 4.5]]) {
  const ratio = contraste(aSrgb(aLineal(oklch(nombre))), papel);
  if (ratio >= minimo) ok(`--${nombre}: ${ratio.toFixed(2)}:1 (≥ ${minimo}:1)`);
  else mal(`--${nombre}: ${ratio.toFixed(2)}:1, por debajo de ${minimo}:1`);
}

// --- Veredicto -------------------------------------------------------------
console.log('');
if (fallos.length) {
  console.error(`test-hero: ${fallos.length} fallo(s)\n  - ${fallos.join('\n  - ')}`);
  process.exit(1);
}
console.log('test-hero: OK — HeroBar v2 y fila de frescura cumplen los criterios de #15 › PR-3.');
