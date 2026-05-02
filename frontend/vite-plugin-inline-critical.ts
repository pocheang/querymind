import type { Plugin } from 'vite';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

export default function inlineCriticalCSS(): Plugin {
  return {
    name: 'vite-plugin-inline-critical',
    apply: 'build', // Only run during production builds
    transformIndexHtml(html) {
      // Read critical.css
      const criticalPath = resolve(__dirname, 'src/styles/core/critical.css');

      if (!existsSync(criticalPath)) {
        console.warn('[vite-plugin-inline-critical] critical.css not found, skipping inline');
        return html;
      }

      const criticalCSS = readFileSync(criticalPath, 'utf-8');

      // Inject into <head>
      return html.replace(
        '</head>',
        `<style id="critical-css">${criticalCSS}</style></head>`
      );
    }
  };
}
