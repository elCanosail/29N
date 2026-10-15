/**
 * partidos.ts — convención de color y agrupación de partidos (DESIGN.md §2).
 *
 * DESIGN.md define los colores de partido como una convención de la audiencia
 * (periodistas), no como marca. Aquí se mapea cada partido del universo
 * modelado a uno de los tokens del contrato, sin inventar colores nuevos.
 *
 * Los colores SOLO se usan en gráficos, mapas, tablas y leyendas (§2). Fuera del
 * canvas, el partido va en texto.
 */

export type GrupoPartido = 'pp' | 'psoe' | 'vox' | 'sumar' | 'cs' | 'nacionalistas' | 'pnv' | 'otros';

/** partido → grupo de color del contrato. */
export const GRUPO: Record<string, GrupoPartido> = {
  PP: 'pp', AP: 'pp', 'PP-AP': 'pp', CP: 'pp', UCD: 'pp',
  PSOE: 'psoe', PSC: 'psoe', 'PSE-EE': 'psoe', PSDEG: 'psoe',
  VOX: 'vox',
  SUMAR: 'sumar', PODEMOS: 'sumar', 'UNIDAS PODEMOS': 'sumar', IU: 'sumar',
  COMPROMIS: 'sumar', ECP: 'sumar', 'MÁS PAÍS': 'sumar',
  CIUDADANOS: 'cs',
  ERC: 'nacionalistas', JXCAT: 'nacionalistas', JUNTS: 'nacionalistas',
  'CIU': 'nacionalistas', BNG: 'nacionalistas', 'EH BILDU': 'nacionalistas',
  CUP: 'nacionalistas', CC: 'nacionalistas', PRC: 'nacionalistas',
  PNV: 'pnv', 'GEROA BAI': 'pnv', 'NA+': 'pnv', UPN: 'pnv',
};

/** token CSS por grupo. */
export const COLOR_GRUPO: Record<GrupoPartido, string> = {
  pp: 'var(--p-pp)',
  psoe: 'var(--p-psoe)',
  vox: 'var(--p-vox)',
  sumar: 'var(--p-sumar)',
  cs: 'var(--p-cs)',
  nacionalistas: 'var(--p-erc)',
  pnv: 'var(--p-pnv)',
  otros: 'var(--p-otros)',
};

export const NOMBRE_GRUPO: Record<GrupoPartido, string> = {
  pp: 'PP',
  psoe: 'PSOE',
  vox: 'VOX',
  sumar: 'Sumar y espacio a su izquierda',
  cs: 'Ciudadanos',
  nacionalistas: 'Nacionalistas (ERC, JxCat, BNG, Bildu, CUP, CC)',
  pnv: 'PNV y familia navarra',
  otros: 'Otros y minoritarios',
};

/** Color de un partido concreto (cae a «otros»). */
export function colorPartido(partido: string | null | undefined): string {
  const g = partido ? GRUPO[partido] ?? 'otros' : 'otros';
  return COLOR_GRUPO[g];
}

export function grupoPartido(partido: string | null | undefined): GrupoPartido {
  return partido ? GRUPO[partido] ?? 'otros' : 'otros';
}

/** Orden de la leyenda (mayor a menor presencia esperada). */
export const GRUPOS_ORDEN: GrupoPartido[] = [
  'pp', 'psoe', 'vox', 'sumar', 'nacionalistas', 'pnv', 'cs', 'otros',
];

/** Sigla corta para etiquetas directas en gráficos. */
export function sigla(partido: string): string {
  const s: Record<string, string> = {
    'EH BILDU': 'BILDU', 'UNIDAS PODEMOS': 'UP', 'MÁS PAÍS': 'MÁS',
  };
  return s[partido] ?? partido;
}
