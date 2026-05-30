import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev: proxy /api to the FastAPI backend on :8000.
// Prod: the SPA is built to dist/ and served by FastAPI itself (same origin).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
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
});
