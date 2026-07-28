import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Default to an empty counter id so the index.html placeholder builds cleanly when unset;
// real deployments override it via .env or the environment (which dotenv will not override).
process.env.VITE_YANDEX_METRIKA_ID ??= "";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/auth": "http://localhost:8000",
    },
  },
});
