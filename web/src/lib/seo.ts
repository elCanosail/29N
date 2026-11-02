/**
 * SEO — datos estructurados y utilidades de URL canónica.
 *
 * Un solo sitio del proyecto construye el JSON-LD para que todas las páginas
 * declaren lo mismo: organización, migas y el tipo propio de cada plantilla.
 * Regla: lo que se declara aquí tiene que estar visible en la página. Nada de
 * marcar datos que el visitante no ve.
 */

export const SITIO = 'https://29n.info';

/** URL absoluta y autocanónica. Astro normaliza con barra final: se respeta. */
export function canonica(pathname: string): string {
  const p = pathname.startsWith('/') ? pathname : `/${pathname}`;
  return new URL(p, SITIO).toString();
}

export function organizacion() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    '@id': `${SITIO}/#organizacion`,
    name: '29N',
    url: `${SITIO}/`,
    description:
      'Histórico de encuestas electorales españolas, resultados oficiales 1977–2023 y estimación provincial con intervalos.',
  };
}

export function sitioWeb() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    '@id': `${SITIO}/#web`,
    name: '29N',
    url: `${SITIO}/`,
    inLanguage: 'es-ES',
    publisher: { '@id': `${SITIO}/#organizacion` },
    potentialAction: {
      '@type': 'SearchAction',
      target: { '@type': 'EntryPoint', urlTemplate: `${SITIO}/encuestas/?q={search_term_string}` },
      'query-input': 'required name=search_term_string',
    },
  };
}

export function migas(items: { label: string; href?: string }[]) {
  const lista = [{ label: 'Portada', href: '/' }, ...items].map((it, i) => ({
    '@type': 'ListItem',
    position: i + 1,
    name: it.label,
    item: it.href ? canonica(it.href) : undefined,
  }));
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: lista,
  };
}

export function dataset(opciones: {
  nombre: string;
  descripcion: string;
  ruta: string;
  actualizado?: string;
  cobertura?: string;
  variables?: string[];
  licencia?: string;
  creador?: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: opciones.nombre,
    description: opciones.descripcion,
    url: canonica(opciones.ruta),
    inLanguage: 'es-ES',
    ...(opciones.actualizado ? { dateModified: opciones.actualizado } : {}),
    ...(opciones.creador ? { creator: { '@type': 'Organization', name: opciones.creador } } : {}),
    ...(opciones.cobertura ? { spatialCoverage: opciones.cobertura } : {}),
    ...(opciones.variables ? { variableMeasured: opciones.variables } : {}),
    license: opciones.licencia ?? 'https://opensource.org/licenses/MIT',
    isAccessibleForFree: true,
    publisher: { '@id': `${SITIO}/#organizacion` },
  };
}

export function articulo(opciones: {
  titulo: string;
  descripcion: string;
  ruta: string;
  publicado: string;
  modificado?: string;
  autor?: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: opciones.titulo,
    description: opciones.descripcion,
    url: canonica(opciones.ruta),
    inLanguage: 'es-ES',
    datePublished: opciones.publicado,
    dateModified: opciones.modificado ?? opciones.publicado,
    author: { '@type': 'Organization', name: opciones.autor ?? '29N' },
    publisher: { '@id': `${SITIO}/#organizacion` },
  };
}

export function faq(preguntas: { pregunta: string; respuesta: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: preguntas.map((q) => ({
      '@type': 'Question',
      name: q.pregunta,
      acceptedAnswer: { '@type': 'Answer', text: q.respuesta },
    })),
  };
}

/** Ficha de una encuesta: quién la hizo, cuándo, con qué muestra y qué publicó. */
export function fichaEncuesta(opciones: {
  casa: string;
  estudio: string;
  fechaTrabajo: string | null;
  fechaPublicacion: string | null;
  muestra: number | null;
  ambito: string | null;
  ruta: string;
  urlFuente: string | null;
  partidos: { partido: string; pct: number | null }[];
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Report',
    name: `Encuesta ${opciones.casa}${opciones.fechaTrabajo ? ` · ${opciones.fechaTrabajo}` : ''}`,
    url: canonica(opciones.ruta),
    inLanguage: 'es-ES',
    ...(opciones.fechaPublicacion ? { datePublished: opciones.fechaPublicacion } : {}),
    ...(opciones.fechaTrabajo
      ? {
          temporalCoverage: opciones.fechaTrabajo.includes('/')
            ? opciones.fechaTrabajo.replace('/', '/')
            : opciones.fechaTrabajo,
        }
      : {}),
    ...(opciones.urlFuente ? { isBasedOn: opciones.urlFuente } : {}),
    about: {
      '@type': 'Thing',
      name: `Intención de voto · elecciones generales de España${opciones.ambito ? ` · ${opciones.ambito}` : ''}`,
    },
    publisher: { '@id': `${SITIO}/#organizacion` },
    ...(opciones.partidos.length
      ? {
          measurementTechnique: 'Encuesta de intención de voto',
          variableMeasured: opciones.partidos
            .filter((p) => p.pct !== null)
            .map((p) => ({
              '@type': 'PropertyValue',
              name: `${p.partido} · intención de voto`,
              value: p.pct,
              unitText: '%',
            })),
        }
      : {}),
  };
}
