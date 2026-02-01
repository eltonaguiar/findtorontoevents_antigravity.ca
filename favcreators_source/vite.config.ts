
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
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
  base: '/favcreators/', // Target deployment path
  build: {
    outDir: 'docs',
  },
});
