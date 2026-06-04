import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  define: {
    // Map CRA-style env var to the production WebSocket URL
    'process.env.REACT_APP_WS_URL': JSON.stringify('wss://track.pureleven.com/api'),
  },
  server: {
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'https://ai.pureleven.com',
        changeOrigin: true,
        secure: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        journey: resolve(__dirname, 'journey/index.html'),
      },
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          flow: ['reactflow'],
          charts: ['recharts'],
        },
      },
    },
  },
});
