// src/api/proxy.ts
// Vite dev server: mock FavCreators API so notes, list, login work without PHP (same behavior as serve_local.py).

import type { ViteDevServer } from 'vite';

const SAVE_NOTE_JSON = JSON.stringify({ status: 'success', message: 'Note saved (local mock)' });
const SAVE_CREATORS_JSON = JSON.stringify({ status: 'success' });
const GET_ME_JSON = JSON.stringify({
  user: { id: 0, email: 'admin', role: 'admin', provider: 'admin', display_name: 'Admin' },
});
const GET_NOTES_JSON = JSON.stringify({ '6': 'Guest default note for Starfireara (local mock)' });
const GET_MY_CREATORS_JSON = JSON.stringify({ creators: [] });
const STATUS_JSON = JSON.stringify({
  ok: true,
  db: 'connected',
  read_ok: true,
  notes_count: 1,
  starfireara_note: 'Guest default note for Starfireara (local mock)',
  get_notes_sample: { '6': 'Guest default note for Starfireara (local mock)' },
});

function sendJson(res: { setHeader: (name: string, value: string) => void; end: (body: string) => void }, body: string) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.end(body);
}

export function setupProxy(server: ViteDevServer) {
  // Mock /fc/api/* and /favcreators/api/* so get_notes, get_me, get_my_creators, save_note, save_creators, creators/bulk, login work
  server.middlewares.use((req, res, next) => {
    const path = (req.url || '').split('?')[0];
    const isFcApi = path.startsWith('/fc/api/') || path.startsWith('/favcreators/api/');
    if (!isFcApi) {
      next();
      return;
    }

    // GET
    if (req.method === 'GET') {
      if (path.includes('get_notes.php')) {
        sendJson(res, GET_NOTES_JSON);
        return;
      }
      if (path.includes('get_me.php')) {
        sendJson(res, GET_ME_JSON);
        return;
      }
      if (path.includes('get_my_creators.php')) {
        sendJson(res, GET_MY_CREATORS_JSON);
        return;
      }
      if (path.includes('status.php')) {
        sendJson(res, STATUS_JSON);
        return;
      }
      if (path.includes('sync_creators_table.php')) {
        sendJson(res, JSON.stringify({ ok: true, tables_created: true, creators_synced: 0, guest_list_updated: false }));
        return;
      }
    }

    // POST
    if (req.method === 'POST') {
      if (path.includes('save_note')) {
        sendJson(res, SAVE_NOTE_JSON);
        return;
      }
      if (path.includes('save_creators')) {
        sendJson(res, SAVE_CREATORS_JSON);
        return;
      }
      if (path.includes('sync_creators_table.php')) {
        sendJson(res, JSON.stringify({ ok: true, creators_synced: 0, guest_list_updated: true }));
        return;
      }
      if (path.includes('add_creator_for_guest.php')) {
        let body = '';
        req.on('data', (chunk) => { body += chunk; });
        req.on('end', () => {
          try {
            const data = JSON.parse(body || '{}');
            const creator = data.creator || {};
            sendJson(res, JSON.stringify({ status: 'success', creator }));
          } catch {
            sendJson(res, JSON.stringify({ error: 'Invalid request' }));
          }
        });
        return;
      }
      if (path.includes('creators/bulk')) {
        sendJson(res, SAVE_CREATORS_JSON);
        return;
      }
      if (path.includes('login.php')) {
        let body = '';
        req.on('data', (chunk) => { body += chunk; });
        req.on('end', () => {
          try {
            const data = JSON.parse(body || '{}');
            if (data.email === 'admin' && data.password === 'admin') {
              sendJson(res, JSON.stringify({ user: JSON.parse(GET_ME_JSON).user }));
            } else {
              sendJson(res, JSON.stringify({ error: 'Invalid credentials' }));
            }
          } catch {
            sendJson(res, JSON.stringify({ error: 'Invalid request' }));
          }
        });
        return;
      }
    }

    next();
  });

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
