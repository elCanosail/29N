import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

export async function GET(context: APIContext) {
  const entradas = (await getCollection('blog')).sort(
    (a, b) => b.data.pubDate.getTime() - a.data.pubDate.getTime(),
  );
  return rss({
    title: '29N — Blog',
    description:
      'Análisis y pedagogía electoral con datos: encuestas, coaliciones y el modelo del 29N.',
    site: context.site!, // astro.config siempre define `site` (29n.info)
    items: entradas.map((e) => ({
      title: e.data.title,
      description: e.data.description,
      pubDate: e.data.pubDate,
      link: `/blog/${e.id}/`,
    })),
    customData: '<language>es-ES</language>',
  });
}
