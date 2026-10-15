/**
 * format.ts — formato de cifras y fechas según DESIGN.md §3.
 * Español de España: coma decimal, punto de millares en tablas, `42,1 %`.
 */

/** Porcentaje con coma decimal y espacio fino antes del signo. */
export function pct(v: number | null | undefined, dec = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return `${num(v, dec)} %`;
}

/** Número con coma decimal (sin unidad). */
export function num(v: number | null | undefined, dec = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return v.toFixed(dec).replace('.', ',');
}

/** Entero con separador de millares a la española: 12.345. */
export function entero(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return Math.round(v).toLocaleString('es-ES');
}

/** Rango con guion fino: «31,9 – 38,9». */
export function rango(a: number, b: number, dec = 1): string {
  return `${num(a, dec)} – ${num(b, dec)}`;
}

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

/** «2023-07-23» → «23 de julio de 2023» (formato largo editorial). */
export function fechaLarga(iso: string | null | undefined): string {
  if (!iso) return '—';
  const [a, m, d] = iso.slice(0, 10).split('-');
  if (!a || !m || !d) return iso;
  const mes = MESES[parseInt(m, 10) - 1] ?? m;
  return `${parseInt(d, 10)} de ${mes} de ${a}`;
}

/** «2023-07-23» → «23/07/2023» (tablas, mono). */
export function fechaCorta(iso: string | null | undefined): string {
  if (!iso) return '—';
  const [a, m, d] = iso.slice(0, 10).split('-');
  if (!a || !m || !d) return iso;
  return `${d}/${m}/${a}`;
}

/** Rango de campo «2023-06-05/2023-06-08» → «5–8 jun 2023»; si no, ISO corto. */
export function campo(txt: string | null | undefined): string {
  if (!txt) return '—';
  if (!txt.includes('/')) return fechaCorta(txt);
  const [ini, fin] = txt.split('/');
  if (!fin) return fechaCorta(ini);
  const [a1, m1, d1] = ini.split('-');
  const [a2, m2, d2] = fin.split('-');
  const mes = (m: string) => MESES[parseInt(m, 10) - 1]?.slice(0, 3) ?? m;
  if (a1 === a2) return `${parseInt(d1, 10)}–${parseInt(d2, 10)} ${mes(m2)} ${a1}`;
  return `${d1}/${m1}/${a1} – ${d2}/${m2}/${a2}`;
}
