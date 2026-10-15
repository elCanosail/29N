/**
 * microdatos-explorador.ts — filtros y visualización client-side del explorador
 * de microdatos CIS (página /microdatos/, DESIGN.md §4 «Gráficos» y §7 «Accesibilidad»).
 *
 * Sin servidor: los agregados llegan como JSON estático (pipeline/microdatos/agrega.py)
 * y esta capa solo selecciona el corte y dibuja. Las cifras del gráfico siempre van
 * repetidas en una tabla accesible debajo (el gráfico nunca es el único camino al dato).
 *
 * Elementos del DOM que espera (definidos en la página):
 *   #mundo-corte, #mundo-anio, #mundo-provincia, #mundo-visor, #mundo-pie,
 *   #mundo-lectura, #mundo-tabla, #mundo-contador, #mundo-vacio.
 */
import { colorPartido } from './partidos';
import { num, entero } from './format';

// --- tipos de los JSON (espejo de agrega.py) -------------------------------
export type Intencion = Record<string, number | null>;

export interface AnioFila {
  anio: number;
  eleccion: string[];
  n_entrevistas: number;
  n_intencion: number;
  n_estudios: number;
  intencion: Intencion;
  ideologia_media: number | null;
  n_ideologia: number;
  pct_con_recuerdo: number | null;
}
export interface FilaAnio {
  meta: Record<string, unknown>;
  categorias: string[];
  partidos: string[];
  no_voto: string[];
  anios: AnioFila[];
}
export interface ProvinciaFila {
  codigo: number;
  provincia: string;
  n_entrevistas: number;
  n_estudios: number;
  intencion: Intencion;
}
export interface FilaProvincia {
  meta: Record<string, unknown>;
  partidos: string[];
  no_voto: string[];
  categorias: string[];
  nacional: { n_entrevistas: number; intencion: Intencion };
  provincias: ProvinciaFila[];
}
export interface FilaIdeologia {
  partido: string;
  n: number;
  ideologia_media: number | null;
  p25: number | null;
  p75: number | null;
  distribucion: number[] | null;
}
export interface FilaIdeoPartido {
  meta: Record<string, unknown>;
  escala: { min: number; max: number; etiquetas: string[] };
  total: FilaIdeologia;
  partidos: FilaIdeologia[];
}
export interface FilaPerfil {
  partido: string;
  n: number;
  edad_media: number | null;
  n_edad: number;
  sexo: { Hombre: number | null; Mujer: number | null; NC: number | null };
  estudios: Record<string, number | null>;
}
export interface FilaPerfilPartido {
  meta: Record<string, unknown>;
  niveles_estudios: string[];
  total: { n: number; edad_media: number | null; sexo: Record<string, number | null>; estudios: Record<string, number | null> };
  partidos: FilaPerfil[];
}
export interface FilaSerie {
  anio: number;
  media: number | null;
  p25: number | null;
  p75: number | null;
  n: number;
  n_estudios: number;
}
export interface FilaSerieIdeologia {
  meta: Record<string, unknown>;
  escala: { min: number; max: number };
  serie: FilaSerie[];
}
export interface Datos {
  porAnio: FilaAnio;
  porProvincia: FilaProvincia;
  ideologiaPartido: FilaIdeoPartido;
  perfilPartido: FilaPerfilPartido;
  serieIdeologia: FilaSerieIdeologia;
}

type Corte = 'intencion_anio' | 'serie_ideologia' | 'intencion_provincia' | 'ideologia_partido' | 'perfil_partido';

interface ConfigCorte {
  etiqueta: string;
  usaAnio: boolean;
  usaProvincia: boolean;
}

const CORTES: Record<Corte, ConfigCorte> = {
  intencion_anio: { etiqueta: 'Intención de voto por año', usaAnio: true, usaProvincia: false },
  serie_ideologia: { etiqueta: 'Ideología media por año', usaAnio: false, usaProvincia: false },
  intencion_provincia: { etiqueta: 'Intención por provincia (2015–2025)', usaAnio: false, usaProvincia: true },
  ideologia_partido: { etiqueta: 'Ideología por partido votado', usaAnio: false, usaProvincia: false },
  perfil_partido: { etiqueta: 'Perfil sociodemográfico por partido', usaAnio: false, usaProvincia: false },
};

interface Render {
  svg: string;
  aria: string;
  pie: string;
  lectura: string;
  tabla: string;
}

// --- utilidades ------------------------------------------------------------
const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const qs = <T extends HTMLElement>(id: string): T | null => document.getElementById(id) as T | null;

/** Color de una categoría: partido → su color; no-voto/no declarado → tinta neutra. */
function colorCategoria(categoria: string, noVoto: string[]): string {
  const neutras = [...noVoto, 'NO DECLARADO'];
  return neutras.includes(categoria) ? 'var(--tinta-3)' : colorPartido(categoria);
}

const esNeutra = (categoria: string, noVoto: string[]): boolean =>
  [...noVoto, 'NO DECLARADO'].includes(categoria);

// --- constructores de gráficos (SVG) ---------------------------------------
/** Barras horizontales por categoría. */
function barrasCategorias(
  items: { label: string; valor: number; color: string; neutra: boolean }[],
  unidad: string,
): string {
  if (items.length === 0) return '';
  const W = 760;
  const padL = 128;
  const padR = 84;
  const filaH = 26;
  const H = items.length * filaH + 16;
  const max = Math.max(...items.map((i) => i.valor), 1);
  const anchoMax = W - padL - padR;
  const barras = items
    .map((it, k) => {
      const w = Math.max(2, (it.valor / max) * anchoMax);
      const y = k * filaH + 6;
      const relleno = it.neutra ? 'url(#trama-neutra)' : it.color;
      return `
      <text x="${padL - 8}" y="${y + 13}" class="eje" text-anchor="end">${esc(it.label)}</text>
      <rect x="${padL}" y="${y}" width="${w.toFixed(1)}" height="14" fill="${relleno}" stroke="${it.color}" stroke-width="${it.neutra ? 1 : 0}"></rect>
      <text x="${padL + w + 6}" y="${y + 12}" class="valor">${num(it.valor, 1)} ${unidad}</text>`;
    })
    .join('');
  return `<svg class="grafico" viewBox="0 0 ${W} ${H}" role="img">
    <defs><pattern id="trama-neutra" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="6" stroke="var(--tinta-3)" stroke-width="1.5"></line>
    </pattern></defs>
    ${barras}
  </svg>`;
}

/** Serie de líneas con etiquetas directas al final. Los huecos rompen la línea. */
function lineas(
  anios: number[],
  series: { label: string; color: string; valores: (number | null)[] }[],
  opts: { yMax: number; yLabel: string; banda?: { lo: (number | null)[]; hi: (number | null)[]; color: string } | null },
): string {
  const W = 760;
  const H = 340;
  const pad = { a: 46, d: 104, s: 22, i: 44 };
  const n = Math.max(anios.length - 1, 1);
  const x = (i: number) => pad.a + (i / n) * (W - pad.a - pad.d);
  const y = (v: number) => pad.s + (1 - (v - 0) / (opts.yMax - 0)) * (H - pad.s - pad.i);
  const refs = [0, 0.25, 0.5, 0.75, 1].map((t) => t * opts.yMax);

  const tramo = (vals: (number | null)[]): string => {
    let d = '';
    let abierto = false;
    vals.forEach((v, i) => {
      if (v === null) { abierto = false; return; }
      d += `${abierto ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
      abierto = true;
    });
    return d.trim();
  };

  let bandaPath = '';
  if (opts.banda) {
    const { lo, hi, color } = opts.banda;
    const arriba = hi.map((v, i) => (v === null ? null : `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).join(' ');
    const abajo = lo.map((v, i) => (v === null ? null : `L${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).reverse().join(' ');
    bandaPath = `<path d="${arriba} ${abajo} Z" fill="${color}" stroke="none"></path>`;
  }

  const ticks = anios
    .map((a, i) => `<text x="${x(i)}" y="${H - 12}" class="eje" text-anchor="middle">${a}</text>`)
    .join('');

  const cuerpo = series
    .map((s) => {
      const d = tramo(s.valores);
      const ult = [...s.valores].reverse().find((v) => v !== null);
      const idxUlt = s.valores.reduce<number>((acc, v, i) => (v !== null ? i : acc), 0);
      return `${d ? `<path d="${d}" class="linea" style="stroke:${s.color}"></path>` : ''}` +
        (ult !== undefined && ult !== null
          ? `<text x="${x(idxUlt) + 6}" y="${y(ult) + 4}" class="etiqueta" style="fill:${s.color}">${esc(s.label)}</text>`
          : '');
    })
    .join('');

  return `<svg class="grafico" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
    ${refs.map((v) => `<line x1="${pad.a}" y1="${y(v)}" x2="${W - pad.d}" y2="${y(v)}" class="rejilla"></line>`).join('')}
    ${refs.map((v) => `<text x="${pad.a - 6}" y="${y(v) + 4}" class="eje" text-anchor="end">${num(v, 0)}</text>`).join('')}
    ${bandaPath}
    ${cuerpo}
    ${ticks}
    <text x="${pad.a}" y="${pad.s - 6}" class="eje">${esc(opts.yLabel)}</text>
  </svg>`;
}

/** Puntos con rango p25–p75 sobre el eje 1-10. */
function puntos(
  filas: FilaIdeologia[],
  escala: { min: number; max: number },
): string {
  const W = 760;
  const padL = 128;
  const padR = 96;
  const filaH = 30;
  const H = filas.length * filaH + 34;
  const x = (v: number) => padL + ((v - escala.min) / (escala.max - escala.min)) * (W - padL - padR);
  const rejilla = [1, 3, 5, 7, 10]
    .map((t) => `<line x1="${x(t)}" y1="18" x2="${x(t)}" y2="${H - 20}" class="rejilla"></line>
      <text x="${x(t)}" y="${H - 6}" class="eje" text-anchor="middle">${t}</text>`)
    .join('');
  const cuerpo = filas
    .map((f, k) => {
      const y = 24 + k * filaH;
      if (f.ideologia_media === null) return '';
      const xm = x(f.ideologia_media);
      const xa = f.p25 !== null ? x(f.p25) : xm;
      const xb = f.p75 !== null ? x(f.p75) : xm;
      const color = colorPartido(f.partido);
      return `
      <text x="${padL - 8}" y="${y + 5}" class="eje" text-anchor="end">${esc(f.partido)}</text>
      <line x1="${xa.toFixed(1)}" y1="${y}" x2="${xb.toFixed(1)}" y2="${y}" stroke="var(--regla)" stroke-width="6"></line>
      <circle cx="${xm.toFixed(1)}" cy="${y}" r="5" fill="${color}"></circle>
      <text x="${xb + 8}" y="${y + 5}" class="valor">${num(f.ideologia_media, 1)}</text>`;
    })
    .join('');
  return `<svg class="grafico" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img"
    aria-label="Ideología media autoubicada por partido votado, escala 1 (izquierda) a 10 (derecha).">
    ${rejilla}${cuerpo}
    <text x="${x(escala.min)}" y="12" class="eje">1 izquierda</text>
    <text x="${x(escala.max)}" y="12" class="eje" text-anchor="end">10 derecha</text>
  </svg>`;
}

// --- tablas accesibles -----------------------------------------------------
function tabla(cabeceras: string[], filas: string[][], nota?: string): string {
  const th = cabeceras.map((c, i) => `<th scope="col"${i === 0 ? '' : ' class="der"'}>${esc(c)}</th>`).join('');
  const tr = filas
    .map((f) => `<tr>${f.map((c, i) => `<td${i === 0 ? '' : ' class="mono der"'}${i === 0 ? ' scope="row"' : ''}>${esc(c)}</td>`).join('')}</tr>`)
    .join('');
  return `<table class="tabla-micro"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>
    ${nota ? `<p class="nota">${esc(nota)}</p>` : ''}`;
}

// --- renders por corte -----------------------------------------------------
function renderIntencionAnio(d: Datos, anio: string): Render {
  const { porAnio } = d;
  const catsOrden = [...porAnio.partidos, ...porAnio.no_voto, 'NO DECLARADO'];
  if (anio === 'todos') {
    const años = porAnio.anios.map((a) => a.anio);
    const series = porAnio.partidos
      .map((p) => ({ label: p, color: colorPartido(p), valores: porAnio.anios.map((a) => a.intencion[p] ?? null) }))
      .filter((s) => s.valores.some((v) => v !== null && v > 0.5));
    const yMax = Math.max(30, ...series.flatMap((s) => s.valores.filter((v): v is number => v !== null))) * 1.1;
    const svg = lineas(años, series, { yMax, yLabel: '% sobre censo (CIS) · intención declarada' });
    const top = series.slice(0, 6);
    const filas = porAnio.anios.map((a) => [String(a.anio), ...top.map((s) => {
      const v = a.intencion[s.label];
      return v === null || v === undefined ? '—' : num(v, 1);
    })]);
    return {
      svg,
      aria: `Serie de intención de voto por año, 1977–2025, sobre censo CIS.`,
      pie: 'Intención declarada, % sobre censo (CIS) · 1977–2025 · huecos = años sin la pregunta extraída.',
      lectura: 'La suma de partidos y no-voto es 100 % porque el denominador es la muestra CIS completa: incluye abstención, NS y NC. Los años 2004–2011 aparecen como hueco: esos estudios no traen la pregunta de intención extraída.',
      tabla: tabla(['Año', ...top.map((s) => s.label), 'n'], filas, 'Seis partidos con mayor intención media en la serie.'),
    };
  }
  const a = porAnio.anios.find((x) => String(x.anio) === anio);
  if (!a) return vacio();
  const items = catsOrden
    .map((c) => ({ label: c, valor: a.intencion[c] ?? 0, color: colorCategoria(c, porAnio.no_voto), neutra: esNeutra(c, porAnio.no_voto) }))
    .filter((it) => it.valor > 0.05)
    .sort((x, y2) => y2.valor - x.valor);
  const svg = barrasCategorias(items, '%');
  return {
    svg,
    aria: `Intención de voto en ${a.anio}, sobre censo CIS.`,
    pie: `Estudio(s) ${a.anio} · ${entero(a.n_entrevistas)} entrevistas · ${entero(a.n_intencion)} con intención declarada · % sobre censo (CIS).`,
    lectura: `En ${a.anio} la intención de voto se reparte entre ${items.length} categorías. El bloque de no-voto y no declarado no es ruido: es parte del censo y explica por qué los partidos suman menos de 100 %.`,
    tabla: tabla(['Categoría', '%'], items.map((it) => [it.label, num(it.valor, 1)]),
      `Ideología media declarada: ${a.ideologia_media !== null ? num(a.ideologia_media, 2) : 'sin dato'} · con recuerdo de voto: ${a.pct_con_recuerdo !== null ? num(a.pct_con_recuerdo, 1) + ' %' : 'sin dato'}.`),
  };
}

function renderSerieIdeologia(d: Datos): Render {
  const { serieIdeologia } = d;
  const años = serieIdeologia.serie.map((s) => s.anio);
  const series = [
    { label: 'Media', color: 'var(--tinta)', valores: serieIdeologia.serie.map((s) => s.media) },
    { label: 'p25', color: 'var(--tinta-3)', valores: serieIdeologia.serie.map((s) => s.p25) },
    { label: 'p75', color: 'var(--tinta-3)', valores: serieIdeologia.serie.map((s) => s.p75) },
  ];
  const svg = lineas(años, series, {
    yMax: 10,
    yLabel: 'media 1-10 (1 izquierda · 10 derecha)',
    banda: { lo: serieIdeologia.serie.map((s) => s.p25), hi: serieIdeologia.serie.map((s) => s.p75), color: 'var(--intervalo)' },
  });
  const filas = serieIdeologia.serie.map((s) => [String(s.anio), num(s.media, 2), num(s.p25, 1), num(s.p75, 1), entero(s.n)]);
  return {
    svg,
    aria: 'Evolución de la ideología media autoubicada por año, escala 1 a 10.',
    pie: 'Media ponderada de autoubicación 1-10 · banda p25–p75 · 1977–2025.',
    lectura: 'La banda p25–p75 muestra la dispersión real del electorado: la media apenas se mueve, pero la mitad central va del 3 al 5 en casi todos los años. El hueco 2004–2011 son estudios sin la variable extraída, no un valor 0.',
    tabla: tabla(['Año', 'Media', 'p25', 'p75', 'n'], filas),
  };
}

function renderIntencionProvincia(d: Datos, prov: string): Render {
  const { porProvincia } = d;
  const catsOrden = [...porProvincia.partidos, ...porProvincia.no_voto, 'NO DECLARADO'];
  let intencion: Intencion;
  let nombre: string;
  let n: number;
  if (prov === 'nacional') {
    intencion = porProvincia.nacional.intencion;
    nombre = 'España (nacional)';
    n = porProvincia.nacional.n_entrevistas;
  } else {
    const p = porProvincia.provincias.find((x) => String(x.codigo) === prov);
    if (!p) return vacio();
    intencion = p.intencion;
    nombre = p.provincia;
    n = p.n_entrevistas;
  }
  const items = catsOrden
    .map((c) => ({ label: c, valor: intencion[c] ?? 0, color: colorCategoria(c, porProvincia.no_voto), neutra: esNeutra(c, porProvincia.no_voto) }))
    .filter((it) => it.valor > 0.05)
    .sort((x, y2) => y2.valor - x.valor);
  const svg = barrasCategorias(items, '%');
  const aviso = n < 500 ? ` Muestra pequeña (n = ${entero(n)}): el margen es amplio y la cifra se publica con esa advertencia.` : '';
  return {
    svg,
    aria: `Intención de voto en ${nombre}, agregado 2015–2025, sobre censo CIS.`,
    pie: `${nombre} · ${entero(n)} entrevistas (2015–2025) · % sobre censo (CIS).`,
    lectura: `Agregado de todos los estudios CIS de 2015–2025 en ${nombre}. ${aviso || 'La muestra agregada permite una lectura provincial, pero no sustituye a una encuesta provincial específica.'}`,
    tabla: tabla(['Categoría', '%'], items.map((it) => [it.label, num(it.valor, 1)]), `n = ${entero(n)} entrevistas agregadas.`),
  };
}

function renderIdeologiaPartido(d: Datos): Render {
  const { ideologiaPartido } = d;
  const filas = ideologiaPartido.partidos;
  const svg = puntos(filas, ideologiaPartido.escala);
  const t = tabla(['Partido', 'Media', 'p25', 'p75', 'n'],
    filas.map((f) => [f.partido, num(f.ideologia_media, 2), num(f.p25, 1), num(f.p75, 1), entero(f.n)]),
    `Total (quienes se autoubican): media ${num(ideologiaPartido.total.ideologia_media, 2)} · n = ${entero(ideologiaPartido.total.n)}.`);
  return {
    svg,
    aria: 'Ideología media autoubicada por partido votado, escala 1 izquierda a 10 derecha.',
    pie: 'Media (punto) y rango p25–p75 (barra) de autoubicación 1-10 por intención de voto.',
    lectura: 'El orden va de izquierda (CUP, Bildu, Sumar) a derecha (VOX, PP). La barra gris cubre la mitad central de cada electorado: partidos con media parecida pueden tener electorados muy distintos en dispersión.',
    tabla: t,
  };
}

function renderPerfilPartido(d: Datos): Render {
  const { perfilPartido } = d;
  const filas = perfilPartido.partidos.filter((f) => f.edad_media !== null);
  const svg = barrasCategorias(
    filas.map((f) => ({ label: f.partido, valor: f.edad_media ?? 0, color: 'var(--tinta)', neutra: false })),
    'años',
  );
  const t = tabla(['Partido', 'Edad media', '% Hombre', '% Mujer', 'n'],
    filas.map((f) => [f.partido, num(f.edad_media, 1), num(f.sexo.Hombre, 1), num(f.sexo.Mujer, 1), entero(f.n)]),
    `Total: edad media ${num(perfilPartido.total.edad_media, 1)} años.`);
  return {
    svg,
    aria: 'Edad media del electorado declarado por partido.',
    pie: 'Edad media ponderada por partido (intención de voto), 1977–2025.',
    lectura: 'La edad media ordena el electorado: de partidos jóvenes (PACMA, CUP) a mayores (PP). El corte de estudios y sexo, partido a partido, está en la tabla.',
    tabla: t,
  };
}

function vacio(): Render {
  return { svg: '', aria: '', pie: '', lectura: '', tabla: '' };
}

// --- montaje ---------------------------------------------------------------
export function montarExplorador(d: Datos): void {
  const selCorte = qs<HTMLSelectElement>('mundo-corte');
  const selAnio = qs<HTMLSelectElement>('mundo-anio');
  const selProv = qs<HTMLSelectElement>('mundo-provincia');
  const visor = qs<HTMLDivElement>('mundo-visor');
  const pie = qs<HTMLParagraphElement>('mundo-pie');
  const lectura = qs<HTMLParagraphElement>('mundo-lectura');
  const tablaEl = qs<HTMLDivElement>('mundo-tabla');
  const vacioEl = qs<HTMLParagraphElement>('mundo-vacio');
  if (!selCorte || !selAnio || !selProv || !visor || !tablaEl) return;

  // opciones
  selCorte.innerHTML = (Object.keys(CORTES) as Corte[])
    .map((c) => `<option value="${c}">${esc(CORTES[c].etiqueta)}</option>`)
    .join('');
  selAnio.innerHTML = `<option value="todos">Todos los años</option>` +
    d.porAnio.anios.map((a) => `<option value="${a.anio}">${a.anio}</option>`).join('');
  selProv.innerHTML = `<option value="nacional">España (nacional)</option>` +
    d.porProvincia.provincias.map((p) => `<option value="${p.codigo}">${esc(p.provincia)}</option>`).join('');

  const pintar = (): void => {
    const corte = selCorte.value as Corte;
    const cfg = CORTES[corte];
    selAnio.disabled = !cfg.usaAnio;
    selProv.disabled = !cfg.usaProvincia;
    const anioCampo = selAnio.closest('[data-campo]') as HTMLElement | null;
    const provCampo = selProv.closest('[data-campo]') as HTMLElement | null;
    if (anioCampo) anioCampo.hidden = !cfg.usaAnio;
    if (provCampo) provCampo.hidden = !cfg.usaProvincia;

    let r: Render = vacio();
    if (corte === 'intencion_anio') r = renderIntencionAnio(d, selAnio.value);
    else if (corte === 'serie_ideologia') r = renderSerieIdeologia(d);
    else if (corte === 'intencion_provincia') r = renderIntencionProvincia(d, selProv.value);
    else if (corte === 'ideologia_partido') r = renderIdeologiaPartido(d);
    else r = renderPerfilPartido(d);

    const hayDatos = r.svg !== '';
    if (vacioEl) vacioEl.hidden = hayDatos;
    visor.innerHTML = hayDatos ? `<figure class="grafico-marco">${r.svg}</figure>` : '';
    if (pie) pie.textContent = r.pie;
    if (lectura) lectura.textContent = r.lectura;
    tablaEl.innerHTML = r.tabla;
    // el SVG lleva aria-label descriptivo (DESIGN.md §7.5)
    const svgEl = visor.querySelector('svg');
    if (svgEl && r.aria) svgEl.setAttribute('aria-label', r.aria);
  };

  selCorte.addEventListener('change', pintar);
  selAnio.addEventListener('change', pintar);
  selProv.addEventListener('change', pintar);
  pintar();
}
