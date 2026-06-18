import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy forwards API calls to the FastAPI backend so the UI works without
// CORS fuss in development. In production, set VITE_API_URL to the backend URL.
export default defineConfig({
  // Base path is "/" locally; on GitHub Pages it is "/<repo>/" (set via VITE_BASE).
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
