/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiTarget = process.env.VITE_API_TARGET ?? "http://localhost:8301";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5301,
    strictPort: true,
    proxy: { "/api": apiTarget },
  },
  preview: {
    port: 5301,
    proxy: { "/api": apiTarget },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
