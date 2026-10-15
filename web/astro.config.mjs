// @ts-check
import { defineConfig } from 'astro/config';

// 29N — web pública.
// Salida 100% estática: la web solo lee JSON ya calculado por el pipeline
// (decisión de arquitectura en docs/plan.md: "la web solo lee, no calcula").
//
// Nota: `site` se fija antes del deploy en Vercel (pendiente de Fase 5).
// No se inventa un dominio aquí para no publicar metadatos falsos.
export default defineConfig({
  output: 'static',
  trailingSlash: 'always',
  build: {
    format: 'directory',
  },
  devToolbar: {
    enabled: false,
  },
});
