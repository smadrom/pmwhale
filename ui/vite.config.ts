import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В dev проксируем /api на Bun-сервер (по умолчанию :5178).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:5178",
    },
  },
  build: {
    outDir: "dist",
  },
});
