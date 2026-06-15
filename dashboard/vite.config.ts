import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'fix-html-paths',
      closeBundle() {
        const htmlPath = path.resolve(process.cwd(), 'dist/index.html');
        let html = fs.readFileSync(htmlPath, 'utf-8');
        
        // Fix asset paths to include /dashboard prefix
        html = html.replace(/src="\/assets\//g, 'src="/dashboard/assets/');
        html = html.replace(/href="\/assets\//g, 'href="/dashboard/assets/');
        
        fs.writeFileSync(htmlPath, html);
        console.log('Fixed asset paths in index.html');
      },
    },
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    base: '/dashboard/',
  },
});
