import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * Blog editorial de 29N (docs/plans/blog.md).
 * Un fichero .md por artículo; el `id` de la entrada es el nombre del fichero
 * sin extensión y define la ruta /blog/<id>/.
 */
const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string().max(200),
    pubDate: z.coerce.date(),
    updated: z.coerce.date().optional(),
    slug: z.string(),
    keyword: z.string(),
  }),
});

export const collections = { blog };
