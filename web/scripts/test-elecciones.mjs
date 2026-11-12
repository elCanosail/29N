#!/usr/bin/env node
/**
 * test-elecciones.mjs — paridad entre lo que publica /elecciones/ y el escrutinio
 * oficial del Ministerio del Interior.
 *
 * Qué comprueba (issue #15, PR-1; origen #12.17):
 *   1. Cada elección de la web existe en el escrutinio provincial y al revés.
 *   2. Los escaños por candidatura, suma nacional, cuadran con los provinciales.
 *   3. Los votos por candidatura, suma nacional, cuadran con los provinciales.
 *   4. `pct` es votos/votos válidos, no una cifra escrita a mano.
 *   5. La suma de escaños es 350 en el Congreso y la de porcentajes cierra.
 *
 * Se ejecuta en `prebuild`: si la web y el dato oficial divergen, no hay build.
 * No necesita dependencias: solo fs. Sin red: los dos ficheros son del repo.
 */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const aquí = dirname(fileURLToPath(import.meta.url));
const raíz = join(aquí, '..', '..'); // raíz del repo
const WEB = join(raíz, 'web', 'src', 'data', 'elecciones.json');
const OFICIAL = join(raíz, 'data', 'processed', 'interior', 'results_provincial.jsonl');
const VALIDACION = join(raíz, 'data', 'processed', 'interior', 'validation.json');

let fallos = 0;
let comprobaciones = 0;
const ok = (cond, msg) => {
  comprobaciones++;
  if (!cond) {
    fallos++;
    console.log(`  ✗ ${msg}`);
  }
};

// ── carga ────────────────────────────────────────────────────────────────────
const web = JSON.parse(readFileSync(WEB, 'utf8'));
const elecciones = web.elecciones ?? [];
// Votos en blanco por elección: están en `válidos` pero no son candidatura, así que
// los porcentajes de candidatura suman 100 menos el blanco. Sin este dato, la suma
// parece un error cuando en realidad el escrutinio está completo.
const blancos = new Map();
try {
  const v = JSON.parse(readFileSync(VALIDACION, 'utf8'));
  for (const e of v.validaciones ?? []) {
    let b = 0;
    for (const p of Object.values(e.provincias ?? {})) b += p?.blanco ?? 0;
    blancos.set(e.id, b);
  }
} catch {
  console.log('  ! validation.json ilegible: no se puede cuadrar el voto en blanco');
}

const filas = readFileSync(OFICIAL, 'utf8')
  .split('\n')
  .filter((l) => l.trim())
  .map((l) => JSON.parse(l));

ok(elecciones.length > 0, 'elecciones.json no trae elecciones');
ok(filas.length > 0, 'results_provincial.jsonl vacío');

// Agregado provincial por elección y candidatura.
const agregado = new Map(); // eleccion → Map(partido_id → {votos, escanos})
for (const f of filas) {
  if (!agregado.has(f.eleccion)) agregado.set(f.eleccion, new Map());
  const m = agregado.get(f.eleccion);
  const prev = m.get(f.partido_id) ?? { votos: 0, escanos: 0 };
  m.set(f.partido_id, {
    votos: prev.votos + (f.votos ?? 0),
    escanos: prev.escanos + (f.escanos ?? 0),
  });
}

const enWeb = new Set(elecciones.map((e) => e.id));
const enOficial = new Set(agregado.keys());

// 1 · cobertura mutua
for (const id of enWeb) ok(enOficial.has(id), `la web publica ${id} pero el escrutinio no lo tiene`);
for (const id of enOficial) ok(enWeb.has(id), `el escrutinio tiene ${id} y la web no lo publica`);

// 2-5 · cifras
for (const e of elecciones) {
  const prov = agregado.get(e.id);
  if (!prov) continue;
  const cands = e.candidaturas ?? [];

  const escanosWeb = cands.reduce((s, c) => s + (c.escanos ?? 0), 0);
  const escanosProv = [...prov.values()].reduce((s, p) => s + p.escanos, 0);
  ok(
    escanosWeb === e.escanos_totales,
    `${e.id}: suma de escaños ${escanosWeb} ≠ escanos_totales ${e.escanos_totales}`,
  );
  ok(
    escanosWeb === escanosProv,
    `${e.id}: escaños web ${escanosWeb} ≠ escrutinio provincial ${escanosProv}`,
  );
  if (e.camara?.toLowerCase().includes('congreso')) {
    ok(escanosWeb === 350, `${e.id}: Congreso con ${escanosWeb} escaños en vez de 350`);
  }

  const votosWeb = cands.reduce((s, c) => s + (c.votos ?? 0), 0);
  const votosProv = [...prov.values()].reduce((s, p) => s + p.votos, 0);
  ok(
    votosWeb === votosProv,
    `${e.id}: votos web ${votosWeb} ≠ escrutinio ${votosProv} (Δ ${votosWeb - votosProv})`,
  );
  ok(
    votosWeb <= e.votos_validos,
    `${e.id}: votos a candidatura ${votosWeb} > válidos ${e.votos_validos}`,
  );

  // Cada candidatura: votos y escaños uno a uno contra el escrutinio.
  for (const c of cands) {
    const p = prov.get(c.partido_id);
    if (!p) {
      ok(false, `${e.id}: ${c.sigla || c.partido_id} está en la web y no en el escrutinio`);
      continue;
    }
    ok(
      c.votos === p.votos,
      `${e.id} · ${c.sigla}: votos ${c.votos} ≠ ${p.votos}`,
    );
    ok(
      c.escanos === p.escanos,
      `${e.id} · ${c.sigla}: escaños ${c.escanos} ≠ ${p.escanos}`,
    );
  }

  // pct derivado, no tecleado: tolerancia por el redondeo a 2 decimales.
  for (const c of cands) {
    if (!e.votos_validos) continue;
    const esperado = (c.votos / e.votos_validos) * 100;
    ok(
      Math.abs(esperado - (c.pct ?? 0)) <= 0.02,
      `${e.id} · ${c.sigla}: pct ${c.pct} ≠ calculado ${esperado.toFixed(2)}`,
    );
  }
  const sumaPct = cands.reduce((s, c) => s + (c.pct ?? 0), 0);
  const pctBlanco = e.votos_validos ? ((blancos.get(e.id) ?? 0) / e.votos_validos) * 100 : 0;
  ok(
    Math.abs(sumaPct + pctBlanco - 100) <= 0.5,
    `${e.id}: candidaturas ${sumaPct.toFixed(2)} % + blanco ${pctBlanco.toFixed(2)} % ≠ 100`,
  );
}

console.log(
  `\ntest:elecciones — ${comprobaciones} comprobaciones, ${fallos} fallos` +
    ` · ${elecciones.length} elecciones · ${filas.length} filas provinciales`,
);
if (fallos) {
  console.log('La web y el escrutinio oficial han divergido: no se publica.');
  process.exit(1);
}
