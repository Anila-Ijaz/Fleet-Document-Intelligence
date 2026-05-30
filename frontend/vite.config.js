import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy so the browser can call /api/extract and /api/rag without CORS issues.
// In production (Docker/k8s) these are rewritten via nginx / ingress.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/extract": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/extract/, ""),
      },
      "/api/rag": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/rag/, ""),
      },
      "/api/agent": {
        target: "http://localhost:8002",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/agent/, ""),
      },
    },
  },
});
