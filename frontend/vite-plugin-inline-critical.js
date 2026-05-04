import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

export default function inlineCriticalCSS() {
  let root;

  return {
    name: 'vite-plugin-inline-critical',
    apply: 'build',

    configResolved(config) {
      root = config.root;
    },

    transformIndexHtml: {
      order: 'post',
      handler(html) {
        const criticalPath = resolve(root, 'src/styles/core/critical.css');

        if (!existsSync(criticalPath)) {
          console.warn('[vite-plugin-inline-critical] critical.css not found, skipping inline');
          return html;
        }

        try {
          const criticalCSS = readFileSync(criticalPath, 'utf-8');
          const sanitizedCSS = criticalCSS.replace(/<\/style>/gi, '<\\/style>');

          const transformed = html.replace(
            /<\/head>/i,
            `<style id="critical-css">${sanitizedCSS}</style>\n  </head>`
          );

          console.log('[vite-plugin-inline-critical] Successfully inlined critical CSS (' + criticalCSS.length + ' bytes)');
          return transformed;
        } catch (error) {
          console.error('[vite-plugin-inline-critical] Failed to inline critical CSS:', error);
          return html;
        }
      }
    }
  };
}
