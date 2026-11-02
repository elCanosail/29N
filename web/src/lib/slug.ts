/** Slug para URLs de entidad: minúsculas, sin tildes, guiones. */
export function slug(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/** Slug de una casa encuestadora, con los casos que ya tienen nombre público. */
export function slugCasa(casa: string): string {
  const especiales: Record<string, string> = {
    'CEO (Centre d\'Estudis d\'Opinió)': 'ceo',
    Sociometrica: 'sociometrica',
    'Imop Insights': 'imop-insights',
    'Simple Lógica': 'simple-logica',
    'Demoscopia y Servicios': 'demoscopia-y-servicios',
  };
  return especiales[casa] ?? slug(casa);
}
