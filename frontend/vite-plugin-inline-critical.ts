import type { Plugin } from 'vite';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

export default function inlineCriticalCSS(): Plugin {
  return {
    name: 'vite-plugin-inline-critical',
    apply: 'build', // Only run during production builds
    transformIndexHtml(html, ctx) {
      // Read critical.css
      const root = ctx.server?.config.root || process.cwd();
      const criticalPath = resolve(root, 'src/styles/core/critical.css');

      if (!existsSync(criticalPath)) {
        console.warn('[vite-plugin-inline-critical] critical.css not found, skipping inline');
        return html;
      }

      try {
        const criticalCSS = readFileSync(criticalPath, 'utf-8');
        const sanitizedCSS = criticalCSS.replace(/<\/style>/gi, '<\\/style>');

        // Inject into <head>
        return html.replace(
          /<\/head>/i,
          `<style id="critical-css">${sanitizedCSS}</style></head>`
        );
      } catch (error) {
        console.error('[vite-plugin-inline-critical] Failed to read critical.css:', error);
        return html;
      }
    }
  };
}
