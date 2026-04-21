import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // Esto genera un solo archivo JS y CSS sin hashes aleatorios
    rollupOptions: {
      output: {
        manualChunks: undefined,
        entryFileNames: `assets/chatbot-plan-lector.js`,
        chunkFileNames: `assets/[name].js`,
        assetFileNames: `assets/[name].[ext]`,
      },
    },
  },
});