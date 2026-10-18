// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// 29N — web pública.
// Salida 100% estática: la web solo lee JSON ya calculado por el pipeline
// (decisión de arquitectura en docs/plan.md: "la web solo lee, no calcula").
//
// `site` es el dominio canónico (requerido por sitemap y canonical URLs).
export default defineConfig({
  site: 'https://29n.info',
  output: 'static',
  trailingSlash: 'always',
  integrations: [sitemap()],
  build: {
    format: 'directory',
  },
  devToolbar: {
    enabled: false,
  },
});
