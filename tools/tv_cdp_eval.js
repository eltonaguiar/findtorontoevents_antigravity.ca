const WebSocket = require('ws');
const http = require('http');

async function getWsUrl() {
  return new Promise((resolve, reject) => {
    http.get('http://localhost:9222/json', (res) => {
      let d = ''; res.on('data', c => d += c); res.on('end', () => {
        const tabs = JSON.parse(d);
        const tv = tabs.find(t => t.url && t.url.includes('tradingview'));
        if (tv) resolve(tv.webSocketDebuggerUrl);
        else reject(new Error('No TradingView tab'));
      });
    }).on('error', reject);
  });
}

async function evaluate(expr) {
  const wsUrl = await getWsUrl();
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    ws.on('open', () => {
      ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true, awaitPromise: true } }));
    });
    ws.on('message', (msg) => {
      const r = JSON.parse(msg);
      if (r.id === 1) {
        ws.close();
        if (r.result && r.result.result) resolve(r.result.result.value);
        else resolve(JSON.stringify(r));
      }
    });
    ws.on('error', reject);
    setTimeout(() => { ws.close(); reject(new Error('timeout')); }, 5000);
  });
}

const expr = process.argv[2];
if (!expr) { console.error('Usage: node tv_cdp_eval.js "expression"'); process.exit(1); }
evaluate(expr).then(r => console.log(r)).catch(e => console.error('ERR:', e.message));
