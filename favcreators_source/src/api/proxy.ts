// src/api/proxy.ts
// Simple proxy endpoint for Vite dev server to bypass CORS for Google search scraping

import type { ViteDevServer } from 'vite';

export function setupProxy(server: ViteDevServer) {
  server.middlewares.use('/api/proxy', async (req, res) => {
    const url = decodeURIComponent((req.url || '').replace(/^\/api\/proxy\?url=/, ''));
    if (!url.startsWith('http')) {
      res.statusCode = 400;
      res.end('Invalid URL');
      return;
    }
    try {
      const fetchRes = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
      const text = await fetchRes.text();
      res.setHeader('Content-Type', 'text/html');
      res.end(text);
    } catch {
      res.statusCode = 500;
      res.end('Proxy error');
    }
  });
}
