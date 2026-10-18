import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const entradas = (await getCollection('blog')).sort(
    (a, b) => b.data.pubDate - a.data.pubDate,
  );
  return rss({
    title: '29N — Blog',
    description:
      'Análisis y pedagogía electoral con datos: encuestas, coaliciones y el modelo del 29N.',
    site: context.site,
    items: entradas.map((e) => ({
      title: e.data.title,
      description: e.data.description,
      pubDate: e.data.pubDate,
      link: `/blog/${e.id}/`,
    })),
    customData: '<language>es-ES</language>',
  });
}
