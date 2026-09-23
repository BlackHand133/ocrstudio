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
    rolldownOptions: {
      output: {
        // Split heavy vendors into their own chunks for faster first load +
        // better browser caching (the app code changes far more often).
        // A module matching several groups goes to the highest priority, so
        // React stays in its own chunk instead of inside whichever library
        // pulled it in first (under Rollup's manualChunks it ended up empty).
        codeSplitting: {
          groups: [
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/, priority: 40 },
            { name: 'mantine', test: /node_modules[\\/]@mantine[\\/]/, priority: 30 },
            {
              name: 'konva',
              test: /node_modules[\\/](konva|react-konva|react-reconciler|its-fine|use-image)[\\/]/,
              priority: 30,
            },
            { name: 'query', test: /node_modules[\\/]@tanstack[\\/]/, priority: 30 },
          ],
        },
      },
    },
  },
  };
});
