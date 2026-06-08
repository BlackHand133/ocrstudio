import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// Dev: proxy /api to the FastAPI backend. Default :8000, override with
// VITE_API_TARGET (e.g. in frontend/.env.local) when that port is taken —
// e.g. VITE_API_TARGET=http://localhost:8001.
// Prod: the SPA is built to dist/ and served by FastAPI itself (same origin).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'VITE_');
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000';
  return {
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': apiTarget,
    },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        // Split heavy vendors into their own chunks for faster first load +
        // better browser caching (the app code changes far more often).
        manualChunks: {
          react: ['react', 'react-dom'],
          mantine: [
            '@mantine/core',
            '@mantine/hooks',
            '@mantine/notifications',
            '@mantine/dropzone',
          ],
          konva: ['konva', 'react-konva', 'use-image'],
          query: ['@tanstack/react-query', '@tanstack/react-virtual'],
        },
      },
    },
  },
  };
});
