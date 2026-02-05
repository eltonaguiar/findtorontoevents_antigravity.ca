
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { setupProxy } from './src/api/proxy';

export default defineConfig({
  plugins: [
    react(),
    {
      name: "favcreators-proxy",
      configureServer(server) {
        setupProxy(server);
      },
    },
  ],
  base: '/fc/', // Deploy path (avoids 500 on host for /favcreators/)
  build: {
    outDir: 'docs',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
      },
    },
  },
  server: {
    port: 5174, // 5173 is used by serve_local.py for main site at /
  },
});
