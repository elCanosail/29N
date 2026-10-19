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

/** token CSS por grupo (fallback histórico para partidos fuera del mapa). */
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

/** Color por partido concreto (DESIGN.md §2, Chema 15-10-2026: cada partido su color). */
export const COLOR_PARTIDO: Record<string, string> = {
  PP: 'var(--p-pp)', AP: 'var(--p-pp)', 'PP-AP': 'var(--p-pp)', CP: 'var(--p-pp)', UCD: 'var(--p-pp)',
  PSOE: 'var(--p-psoe)', PSC: 'var(--p-psoe)', 'PSE-EE': 'var(--p-psoe)', PSDEG: 'var(--p-psoe)',
  'PSIB-PSOE': 'var(--p-psoe)', 'PSN-PSOE': 'var(--p-psoe)',
  VOX: 'var(--p-vox)',
  SUMAR: 'var(--p-sumar)', PODEMOS: 'var(--p-podemos)', 'UNIDAS PODEMOS': 'var(--p-sumar)',
  IU: 'var(--p-sumar)', COMPROMIS: 'var(--p-sumar)', ECP: 'var(--p-sumar)', 'MÁS PAÍS': 'var(--p-sumar)',
  CIUDADANOS: 'var(--p-cs)',
  ERC: 'var(--p-erc)',
  'EH BILDU': 'var(--p-ehbildu)',
  JXCAT: 'var(--p-jxcat)', JUNTS: 'var(--p-jxcat)', CIU: 'var(--p-jxcat)',
  BNG: 'var(--p-bng)',
  CUP: 'var(--p-cup)',
  CC: 'var(--p-cc)',
  PNV: 'var(--p-pnv)', 'GEROA BAI': 'var(--p-pnv)',
  'NA+': 'var(--p-na)', UPN: 'var(--p-na)',
  PACMA: 'var(--p-pacma)',
};

/**
 * Nombres de candidatura del 29N. La familia del modelo conserva sus claves
 * históricas (SUMAR), pero la papeleta de 2026 es Frente Amplio: Sumar concurre
 * dentro de la coalición, no como marca propia.
 */
export const NOMBRE_29N: Record<string, string> = {
  SUMAR: 'Frente Amplio',
};

/** Nombre de la candidatura en el 29N; el resto de partidos no cambia. */
export function nombre29N(partido: string): string {
  return NOMBRE_29N[partido] ?? partido;
}

/** Sigla para etiquetas directas del 29N (el 23J conserva SUMAR). */
export function sigla29N(partido: string): string {
  return partido === 'SUMAR' ? 'F. Amplio' : sigla(partido);
}

export const NOMBRE_GRUPO: Record<GrupoPartido, string> = {
  pp: 'PP',
  psoe: 'PSOE',
  vox: 'VOX',
  sumar: 'Frente Amplio (familia Sumar)',
  cs: 'Ciudadanos',
  nacionalistas: 'Nacionalistas (ERC, JxCat, BNG, Bildu, CUP, CC)',
  pnv: 'PNV y familia navarra',
  otros: 'Otros y minoritarios',
};

/** Color de un partido concreto: primero su color propio, luego el de su grupo, y «otros» al final. */
export function colorPartido(partido: string | null | undefined): string {
  const explicito = partido ? COLOR_PARTIDO[partido] : undefined;
  if (explicito) return explicito;
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
