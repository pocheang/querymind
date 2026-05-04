import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
// @ts-ignore - JavaScript plugin without type definitions
import inlineCriticalCSS from './vite-plugin-inline-critical.js';

export default defineConfig({
  plugins: [react(), inlineCriticalCSS()],
  base: "/app/",
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  build: {
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Component-level CSS splitting (Phase 4)
          if (id.includes('components/modals.css')) {
            return 'modal-styles';
          }
          if (id.includes('components/dropdowns.css')) {
            return 'dropdown-styles';
          }
          if (id.includes('components/tooltips.css')) {
            return 'tooltip-styles';
          }

          // Route-specific CSS splitting (Phase 3)
          if (id.includes('pages/auth') || id.includes('themes/light/auth') || id.includes('themes/dark/auth')) {
            return 'auth-styles';
          }
          if (id.includes('pages/chat') || id.includes('themes/light/chat') || id.includes('themes/dark/chat')) {
            return 'chat-styles';
          }
          if (id.includes('pages/admin') || id.includes('themes/light/admin') || id.includes('themes/dark/admin')) {
            return 'admin-styles';
          }
          if (id.includes('pages/profile')) {
            return 'profile-styles';
          }
        }
      }
    }
  },
  server: {
    port: 5173,
    host: "127.0.0.1",
    proxy: {
      "/auth": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
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
      "/sessions": { target: "http://127.0.0.1:8000", changeOrigin: true, timeout: 600000, proxyTimeout: 600000 },
      "/documents": { target: "http://127.0.0.1:8000", changeOrigin: true, timeout: 600000, proxyTimeout: 600000 },
      "/upload": { target: "http://127.0.0.1:8000", changeOrigin: true, timeout: 600000, proxyTimeout: 600000 },
      "/prompts": { target: "http://127.0.0.1:8000", changeOrigin: true, timeout: 600000, proxyTimeout: 600000 },
      "/query": { target: "http://127.0.0.1:8000", changeOrigin: true, timeout: 600000, proxyTimeout: 600000 },
      "/admin": { target: "http://127.0.0.1:8000", changeOrigin: true, timeout: 600000, proxyTimeout: 600000 },
      "/user": { target: "http://127.0.0.1:8000", changeOrigin: true, timeout: 600000, proxyTimeout: 600000 },
    },
  },
});
