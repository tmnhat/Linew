import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env': {},
    'process': 'undefined',
  },
  build: {
    outDir: 'dist',
    lib: {
      entry: 'src/wordpress-entry.tsx',
      name: 'LinewPredictionWidget',
      fileName: 'widget',
      formats: ['iife'],
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
  server: {
    port: 3000,
  },
});
