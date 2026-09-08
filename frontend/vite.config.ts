import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
// @ts-ignore - JavaScript plugin without type definitions
import inlineCriticalCSS from './vite-plugin-inline-critical.js';

function createBackendProxy(rewriteAppBase = false) {
  return {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
    timeout: 600000,
    proxyTimeout: 600000,
    rewrite: rewriteAppBase ? (path: string) => path.replace(/^\/app/, "") : undefined,
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), inlineCriticalCSS()],
  base: "/",
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  /* No `manualChunks` for CSS any more. Every rule here named a stylesheet
     that no longer exists -- the chat, auth, profile, modal and admin route
     sheets are all Tailwind now -- and a chunking rule that matches nothing is
     one more thing to read. `cssCodeSplit` still splits per dynamic import. */
  build: {
    cssCodeSplit: true,
  },
  server: {
    port: 5173,
    host: "127.0.0.1",
    proxy: {
      "/auth": {
        ...createBackendProxy(),
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('proxyRes', (proxyRes, _req, _res) => {
            // Remove 'secure' flag from cookies in development
            const setCookie = proxyRes.headers['set-cookie'];
            if (setCookie) {
              proxyRes.headers['set-cookie'] = Array.isArray(setCookie)
                ? setCookie.map(cookie => cookie.replace(/; secure/gi, ''))
                : [(setCookie as string).replace(/; secure/gi, '')];
            }
          });
        }
      },
      "/sessions": createBackendProxy(),
      "/documents": createBackendProxy(),
      "/upload": createBackendProxy(),
      "/prompts": createBackendProxy(),
      "/query": createBackendProxy(),
      "/admin": createBackendProxy(),
      "/user": createBackendProxy(),
      // Fetched by `services/api/admin.ts::modelCatalog`. Without an entry
      // here Vite's SPA fallback answers it with index.html, and the settings
      // drawer then reads `providers` off a parsed HTML page.
      "/model-catalog": createBackendProxy(),
      "/api/v1": createBackendProxy(),
      "/api": createBackendProxy(),
      "/app/auth": createBackendProxy(true),
      "/app/sessions": createBackendProxy(true),
      "/app/documents": createBackendProxy(true),
      "/app/upload": createBackendProxy(true),
      "/app/prompts": createBackendProxy(true),
      "/app/query": createBackendProxy(true),
      // Note: /app/admin is handled by frontend router, not proxied to backend
      "/app/user": createBackendProxy(true),
      "/app/model-catalog": createBackendProxy(true),
      "/app/api": createBackendProxy(true),
    },
  },
});
