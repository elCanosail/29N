/**
 * Tipos compartidos de la capa de datos de la web.
 * La web solo LEE datos ya calculados por el pipeline (docs/plan.md):
 * estos tipos describen lo que el JSON del pipeline deberá cumplir.
 */

/** Tipo de columna de DataTable. */
export type TipoColumna = 'texto' | 'mono' | 'barra' | 'delta';

export interface Columna {
  clave: string;
  etiqueta: string;
  tipo?: TipoColumna;
  alinear?: 'izq' | 'der';
  /** En tipo 'barra': valor de referencia para normalizar el ancho. */
  escala?: number;
}

export interface CeldaBarra {
  pct: number;
  color: string;
}

export interface CeldaDelta {
  valor: string;
  signo: '+' | '-' | '=';
}

export type Celda =
  | string
  | { texto: string }
  | { barra: CeldaBarra; texto?: string }
  | CeldaDelta;

/** Una fila de tabla: clave de columna → celda. */
export type Fila = Record<string, Celda>;
