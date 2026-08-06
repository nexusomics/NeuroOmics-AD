import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the FastAPI backend so the browser only ever
// uses same-origin relative URLs (required for the sandboxed preview host).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // preview iframes use per-session *.e2b.app hosts — allow any host
    allowedHosts: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 2500,
    rollupOptions: {
      output: {
        manualChunks: {
          "plotly": ["plotly.js-dist-min"],
          "d3": ["d3"],
          "react": ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
