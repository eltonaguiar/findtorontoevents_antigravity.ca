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

let ws, msgId = 0;
async function connect() {
  const wsUrl = await getWsUrl();
  return new Promise((resolve, reject) => {
    ws = new WebSocket(wsUrl);
    ws.on('open', () => resolve());
    ws.on('error', reject);
  });
}

function evalJS(expr) {
  return new Promise((resolve, reject) => {
    const id = ++msgId;
    const handler = (msg) => {
      const r = JSON.parse(msg);
      if (r.id === id) { ws.removeListener('message', handler); resolve(r.result?.result?.value); }
    };
    ws.on('message', handler);
    ws.send(JSON.stringify({ id, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true, awaitPromise: true } }));
    setTimeout(() => { ws.removeListener('message', handler); reject(new Error('timeout')); }, 8000);
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

const ACCOUNTS = ['SCALPER','THEWINNERS','zerounderscore','XIAOMI MIMO','HYROTRADER','AG_PROVENEDGETEST','BROKIE','CURSORTEST','HYROTRADER2','TESTER','TRUSTOURSCORE'];

(async () => {
  await connect();
  console.log('=== FULL PORTFOLIO VALIDATION ===\n');

  let totalPos = 0, totalMissing = 0;
  const results = [];

  for (const acct of ACCOUNTS) {
    // Switch account
    await evalJS(`(function(){ var btn=document.querySelector('button.dropdownButton-dm1wtgNn'); if(btn) btn.click(); return 'ok'; })()`);
    await sleep(500);
    await evalJS(`(function(){ var all=document.querySelectorAll('div,span'); for(var i=0;i<all.length;i++){var t=(all[i].textContent||'').trim(); if(t==='${acct}'){all[i].click();return 'clicked';}} return 'nf'; })()`);
    await sleep(800);

    const verify = await evalJS(`(function(){ var n=document.querySelector('span.accountName-dm1wtgNn'); return n?n.textContent.trim():'nf'; })()`);
    if (verify !== acct) {
      console.log(`[FAIL] ${acct} - couldn't switch (got: ${verify})`);
      results.push({ acct, positions: 0, missing: 0, status: 'SWITCH_FAIL' });
      continue;
    }

    await sleep(300);

    const posData = await evalJS(`(function(){ var rows=document.querySelectorAll('table tr'); var r=[]; for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td'); if(c.length>=6){var sym=(c[0].textContent||'').trim(); if(sym.indexOf('BINANCE')>=0){var tp=(c[4]&&c[4].textContent||'').trim();var sl=(c[5]&&c[5].textContent||'').trim();r.push(sym+'|TP:'+tp+'|SL:'+sl);}}} return r.join('\\n'); })()`);

    const positions = posData ? posData.split('\n').filter(Boolean) : [];
    let missing = 0;
    const details = [];
    for (const pos of positions) {
      const parts = pos.split('|');
      const sym = parts[0];
      const tp = parts[1].replace('TP:', '').trim();
      const sl = parts[2].replace('SL:', '').trim();
      if (!tp || !sl) {
        missing++;
        details.push(`  MISSING: ${sym} TP:${tp||'---'} SL:${sl||'---'}`);
      }
    }

    totalPos += positions.length;
    totalMissing += missing;

    const status = missing > 0 ? 'NEEDS_FIX' : 'OK';
    const icon = missing > 0 ? '[!!!]' : '[ OK]';
    console.log(`${icon} ${acct.padEnd(20)} ${positions.length} positions, ${missing} missing TP/SL`);
    if (details.length > 0) details.forEach(d => console.log(d));
    results.push({ acct, positions: positions.length, missing, status });
  }

  console.log('\n=== SUMMARY ===');
  console.log(`Total positions: ${totalPos}`);
  console.log(`Missing TP/SL: ${totalMissing}`);
  console.log(`Status: ${totalMissing === 0 ? 'ALL CLEAR' : totalMissing + ' POSITIONS NEED FIXING'}`);

  ws.close();
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
