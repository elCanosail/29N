// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { readFileSync } from 'node:fs';

// 29N — web pública.
// Salida 100% estática: la web solo lee JSON ya calculado por el pipeline
// (decisión de arquitectura en docs/plan.md: "la web solo lee, no calcula").
//
// `site` es el dominio canónico (requerido por sitemap y canonical URLs).

// lastmod real por familia de URL: la fecha del dato que sirve la página, no la
// del build. Google usa lastmod para decidir si vale la pena volver a rastrear;
// mentir con la fecha del build entrena al buscador a ignorarlo.
const leer = (ruta) => JSON.parse(readFileSync(new URL(ruta, import.meta.url), 'utf8'));

const { encuestas } = leer('./src/data/encuestas.json');
const { provincias, meta: metaSeats } = leer('./src/data/seats.json');
const { elecciones } = leer('./src/data/elecciones.json');

const slugify = (t) =>
  String(t)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

const slugCasa = (casa) => {
  const especiales = { "CEO (Centre d'Estudis d'Opinió)": 'ceo' };
  return especiales[casa] ?? slugify(casa);
};

// El campo de campo puede venir como rango «2026-10-07/2026-10-08»: para
// lastmod vale el último día de campo, que es cuando el dato queda cerrado.
const comoFecha = (v) => {
  if (!v) return null;
  const txt = String(v);
  const ultimo = txt.includes('/') ? txt.split('/').filter(Boolean).pop() : txt;
  return /^\d{4}-\d{2}-\d{2}$/.test(ultimo) ? ultimo : null;
};

const fechaEncuestas = new Map();
const ultimaPorCasa = new Map();
for (const e of encuestas) {
  const d = comoFecha(e.fecha_publicacion) ?? comoFecha(e.fecha_trabajo);
  fechaEncuestas.set(`/encuestas/${String(e.id).toLowerCase()}/`, d);
  const casa = slugCasa(String(e.casa));
  const actual = ultimaPorCasa.get(casa);
  const candidata = comoFecha(e.fecha_trabajo) ?? comoFecha(e.fecha_publicacion);
  if (candidata && (!actual || candidata > actual)) ultimaPorCasa.set(casa, candidata);
}

const ultimaEncuesta = encuestas
  .map((e) => comoFecha(e.fecha_trabajo) ?? comoFecha(e.fecha_publicacion))
  .filter(Boolean)
  .sort()
  .pop();
const ultimaEleccion = elecciones.map((e) => e.fecha).sort().pop();
const generado = metaSeats?.generado?.slice(0, 10) ?? null;

const fechaProvincia = new Map(
  provincias.map((p) => [`/prediccion/${slugify(p.nombre)}/`, metaSeats?.generado?.slice(0, 10) ?? null]),
);
const fechaEleccion = new Map(elecciones.map((e) => [`/elecciones/${e.id}/`, e.fecha]));

const lastmodDe = (pathname) => {
  if (fechaEncuestas.has(pathname)) return fechaEncuestas.get(pathname);
  // El índice va antes que su rama: si no, «/encuestadores/» se confunde con
  // una casa sin nombre y se queda sin fecha.
  if (pathname === '/encuestadores/') return ultimaEncuesta ?? null;
  if (pathname.startsWith('/encuestadores/')) {
    const casa = pathname.replace('/encuestadores/', '').replace(/\/$/, '');
    return ultimaPorCasa.get(casa) ?? null;
  }
  if (fechaProvincia.has(pathname)) return fechaProvincia.get(pathname);
  if (fechaEleccion.has(pathname)) return fechaEleccion.get(pathname);
  if (pathname.startsWith('/prediccion')) return generado;
  // Páginas de sección: lastmod del dato que muestran, no del build.
  if (pathname === '/') return generado;
  if (pathname === '/encuestas/') return ultimaEncuesta ?? null;
  if (pathname === '/partidos/' || pathname === '/series/' || pathname.startsWith('/partidos/')) return generado;
  if (pathname === '/elecciones/') return ultimaEleccion ?? null;
  return null;
};

export default defineConfig({
  site: 'https://29n.info',
  output: 'static',
  trailingSlash: 'always',
  integrations: [
    sitemap({
      serialize(item) {
        const path = new URL(item.url).pathname;
        const lastmod = lastmodDe(path);
        return lastmod ? { ...item, lastmod } : item;
      },
    }),
  ],
  build: {
    format: 'directory',
  },
  devToolbar: {
    enabled: false,
  },
});
