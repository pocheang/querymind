import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
// @ts-ignore - JavaScript plugin without type definitions
import inlineCriticalCSS from './vite-plugin-inline-critical.js';

// Overridable because Windows reserves port ranges (Hyper-V / WSL) that can
// include 8000, and the dev server then has nothing to proxy to.
const BACKEND_TARGET = process.env.QUERYMIND_API_TARGET || "http://127.0.0.1:8000";

function createBackendProxy(rewriteAppBase = false) {
  return {
    target: BACKEND_TARGET,
    changeOrigin: true,
    timeout: 600000,
    proxyTimeout: 600000,
    rewrite: rewriteAppBase ? (path: string) => path.replace(/^\/app/, "") : undefined,
  };
}

// Every endpoint is /api/v1/... (ARC-06), so one prefix is proxied. The
// `secure` flag is stripped from cookies the backend sets: development is plain
// http, and a Secure cookie would never come back.
const stripSecureCookies = (proxy: any, _options: any) => {
  proxy.on("proxyRes", (proxyRes: any, _req: any, _res: any) => {
    const setCookie = proxyRes.headers["set-cookie"];
    if (setCookie) {
      proxyRes.headers["set-cookie"] = Array.isArray(setCookie)
        ? setCookie.map((cookie: string) => cookie.replace(/; secure/gi, ""))
        : [(setCookie as string).replace(/; secure/gi, "")];
    }
  });
};

const proxyConfig = {
  "/api": { ...createBackendProxy(), configure: stripSecureCookies },
  "/app/api": { ...createBackendProxy(true), configure: stripSecureCookies },
};

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
    proxy: proxyConfig,
  },
  preview: {
    port: 4173,
    host: "127.0.0.1",
    proxy: proxyConfig,
  },
});
