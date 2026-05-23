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
      if (r.id === id) {
        ws.removeListener('message', handler);
        if (r.result && r.result.result) resolve(r.result.result.value);
        else resolve(JSON.stringify(r));
      }
    };
    ws.on('message', handler);
    ws.send(JSON.stringify({ id, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true, awaitPromise: true } }));
    setTimeout(() => { ws.removeListener('message', handler); reject(new Error('timeout')); }, 8000);
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function protectPosition(symbol, tp, sl) {
  console.log(`\n=== Protecting ${symbol} TP=${tp} SL=${sl} ===`);

  // Click Protect button on the position row
  const clickResult = await evalJS(`(function(){ var rows=document.querySelectorAll('table tr'); for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td'); if(c.length&&(c[0].textContent||'').indexOf('${symbol}')>=0){var b=rows[i].querySelector('button[aria-label*="Protect"]'); if(b){b.click();return 'protect_ok';}}} return 'nf'; })()`);
  console.log('  Click:', clickResult);
  if (clickResult === 'nf') { console.log('  SKIP - no protect button'); return false; }

  await sleep(500);

  // Enable switches
  const swResult = await evalJS(`(function(){ var sw=document.querySelectorAll('[role="switch"]'); var r=[]; for(var i=0;i<sw.length;i++){if(sw[i].getAttribute('aria-checked')==='false'){sw[i].click();r.push('on_'+i);}else{r.push('ok_'+i);}} return r.join(','); })()`);
  console.log('  Switches:', swResult);

  await sleep(300);

  // Set TP and SL
  const setResult = await evalJS(`(function(){ var inputs=document.querySelectorAll('input[type="text"],input[inputmode="decimal"],input[inputmode="numeric"]'); var ns=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; ns.call(inputs[2],'${tp}'); inputs[2].dispatchEvent(new Event('input',{bubbles:true})); inputs[2].dispatchEvent(new Event('change',{bubbles:true})); ns.call(inputs[3],'${sl}'); inputs[3].dispatchEvent(new Event('input',{bubbles:true})); inputs[3].dispatchEvent(new Event('change',{bubbles:true})); return 'TP='+inputs[2].value+' SL='+inputs[3].value; })()`);
  console.log('  Set:', setResult);

  await sleep(300);

  // Click Confirm
  const confirmResult = await evalJS(`(function(){ var btn=document.querySelector('[data-name="place-and-modify-button"]'); if(btn){btn.click();return 'confirmed';} return 'no_btn'; })()`);
  console.log('  Confirm:', confirmResult);

  await sleep(500);
  return confirmResult === 'confirmed';
}

async function switchAccount(name) {
  console.log(`\n>>> Switching to ${name} <<<`);
  await evalJS(`(function(){ var btn=document.querySelector('button.dropdownButton-dm1wtgNn'); if(btn) btn.click(); return 'opened'; })()`);
  await sleep(500);
  const clicked = await evalJS(`(function(){ var all=document.querySelectorAll('div,span'); for(var i=0;i<all.length;i++){var t=(all[i].textContent||'').trim(); if(t==='${name}'){all[i].click();return 'clicked';}} return 'nf'; })()`);
  await sleep(800);
  const verify = await evalJS(`(function(){ var n=document.querySelector('span.accountName-dm1wtgNn'); return n?n.textContent.trim():'nf'; })()`);
  console.log(`  Account: ${verify} (${clicked})`);
  return verify === name;
}

async function readPositions() {
  const result = await evalJS(`(function(){ var rows=document.querySelectorAll('table tr'); var r=[]; for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td'); if(c.length>=6){var sym=(c[0].textContent||'').trim(); if(sym.indexOf('BINANCE')>=0){var side=(c[1]&&c[1].textContent||'').trim();var fill=(c[3]&&c[3].textContent||'').trim();var tp=(c[4]&&c[4].textContent||'').trim();var sl=(c[5]&&c[5].textContent||'').trim();r.push(sym+'|'+side+'|'+fill+'|TP:'+tp+'|SL:'+sl);}}} return r.join('\\n'); })()`);
  console.log('  Positions:');
  if (result) result.split('\n').forEach(l => console.log('    ', l));
  return result ? result.split('\n') : [];
}

async function placeOrder(symbol, side, tp, sl) {
  console.log(`\n+++ Placing ${side} ${symbol} TP=${tp} SL=${sl} +++`);
  const cleanSym = symbol.replace('BINANCE:', '');

  // Step 1: Click the symbol search button in the chart header
  await evalJS(`(function(){ var btn=document.querySelector('button[class*="searchButton"], [data-name="symbol-search-btn"], button[class*="apply-common"][class*="JQZ0HKD4"]'); if(btn){btn.click();return 'opened';} var bs=document.querySelectorAll('button'); for(var i=0;i<bs.length;i++){if(bs[i].querySelector('span[class*="value"]')){bs[i].click();return 'opened_alt';}} return 'nf'; })()`);
  await sleep(800);

  // Step 2: Type symbol in search
  await evalJS(`(function(){ var inputs=document.querySelectorAll('input[placeholder*="Search"],input[placeholder*="search"],input[data-role="search"],input[class*="search"]'); for(var i=0;i<inputs.length;i++){if(inputs[i].offsetParent!==null){inputs[i].focus();inputs[i].value='';var ns=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;ns.call(inputs[i],'${cleanSym}');inputs[i].dispatchEvent(new Event('input',{bubbles:true}));return 'typed';}} return 'no_search'; })()`);
  await sleep(1200);

  // Step 3: Click first matching result
  await evalJS(`(function(){ var items=document.querySelectorAll('[data-role="list-item"],[class*="listRow"],[class*="itemRow"]'); for(var i=0;i<items.length;i++){var t=(items[i].textContent||'');if(t.indexOf('${cleanSym}')>=0&&t.indexOf('Binance')>=0){items[i].click();return 'selected';}} if(items.length>0){items[0].click();return 'selected_first';} return 'nf'; })()`);
  await sleep(800);

  // Step 4: Click Buy/Sell side
  const sideBtn = side === 'Long' ? 'side-control-buy' : 'side-control-sell';
  await evalJS(`(function(){ var b=document.querySelector('[data-name="${sideBtn}"]'); if(b){b.click();return 'side_ok';} return 'nf'; })()`);
  await sleep(300);

  // Step 5: Enable TP/SL switches
  await evalJS(`(function(){ var sw=document.querySelectorAll('[role="switch"]'); for(var i=0;i<sw.length;i++){if(sw[i].getAttribute('aria-checked')==='false') sw[i].click();} return 'sw_ok'; })()`);
  await sleep(400);

  // Step 6: Set TP/SL values
  await evalJS(`(function(){ var inputs=document.querySelectorAll('input'); var visible=[]; for(var i=0;i<inputs.length;i++){if(inputs[i].offsetParent!==null&&inputs[i].id!=='quantity-field'&&inputs[i].type!=='checkbox') visible.push(inputs[i]);} var ns=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; if(visible.length>=2){ns.call(visible[0],'${tp}');visible[0].dispatchEvent(new Event('input',{bubbles:true}));visible[0].dispatchEvent(new Event('change',{bubbles:true}));ns.call(visible[visible.length>=4?2:1],'${sl}');visible[visible.length>=4?2:1].dispatchEvent(new Event('input',{bubbles:true}));visible[visible.length>=4?2:1].dispatchEvent(new Event('change',{bubbles:true}));return 'set_ok';} return 'set_fail:'+visible.length; })()`);
  await sleep(300);

  // Step 7: Execute
  const execResult = await evalJS(`(function(){ var bs=document.querySelectorAll('button'); for(var i=0;i<bs.length;i++){var t=(bs[i].textContent||'').trim(); if((t.indexOf('Buy')>=0||t.indexOf('Sell')>=0) && t.indexOf('${cleanSym}')>=0 && t.indexOf('MARKET')>=0){bs[i].click(); return 'exec:'+t;}} return 'nf'; })()`);
  console.log('  Execute:', execResult);
  await sleep(500);
  return execResult !== 'nf';
}

// HC picks sorted by score
const HC_PICKS = [
  { sym: 'XRPUSDT', side: 'Long', tp: '1.41', sl: '1.29' },
  { sym: 'ETHUSDT', side: 'Long', tp: '2300', sl: '2120' },
  { sym: 'FETUSDT', side: 'Long', tp: '0.265', sl: '0.225' },
  { sym: 'BNBUSDT', side: 'Long', tp: '630', sl: '585' },
  { sym: 'NEARUSDT', side: 'Long', tp: '1.43', sl: '1.27' },
  { sym: 'FILUSDT', side: 'Long', tp: '3.10', sl: '2.65' },
  { sym: 'DYDXUSDT', side: 'Long', tp: '0.55', sl: '0.45' },
  { sym: 'OPUSDT', side: 'Long', tp: '0.50', sl: '0.40' },
  { sym: 'DOTUSDT', side: 'Long', tp: '3.30', sl: '2.80' },
  { sym: 'ALGOUSDT', side: 'Long', tp: '0.12', sl: '0.095' },
];

// Hyrotrader picks by rank
const HYRO_PICKS = [
  { sym: 'BTCUSDT', side: 'Long', tp: '110000', sl: '95000' },
  { sym: 'ETHUSDT', side: 'Long', tp: '2300', sl: '2120' },
  { sym: 'SOLUSDT', side: 'Long', tp: '70', sl: '58' },
  { sym: 'BNBUSDT', side: 'Long', tp: '630', sl: '585' },
  { sym: 'XRPUSDT', side: 'Long', tp: '1.41', sl: '1.29' },
  { sym: 'LINKUSDT', side: 'Long', tp: '7.5', sl: '6.0' },
  { sym: 'AVAXUSDT', side: 'Long', tp: '12', sl: '9.5' },
];

const args = process.argv.slice(2);
const cmd = args[0];

(async () => {
  await connect();
  console.log('Connected to TradingView CDP');

  if (cmd === 'fix-xiaomi') {
    await protectPosition('SHIBUSDT', '0.00000680', '0.00000555');
    await protectPosition('FETUSDT', '0.28', '0.23');
    await sleep(500);
    await readPositions();
  }
  else if (cmd === 'fix-one') {
    // fix-one SYMBOL TP SL
    await protectPosition(args[1], args[2], args[3]);
    await sleep(500);
    await readPositions();
  }
  else if (cmd === 'do-portfolio') {
    const account = args[1];
    const isHyro = account.includes('HYROTRADER');
    const picks = isHyro ? HYRO_PICKS : HC_PICKS;

    if (!(await switchAccount(account))) {
      console.log('FAILED to switch to', account);
      process.exit(1);
    }
    await sleep(500);

    const positions = await readPositions();
    const count = positions.length;
    console.log(`\n  ${account}: ${count} positions`);

    // Fix missing TP/SL on existing positions
    for (const pos of positions) {
      const parts = pos.split('|');
      const sym = parts[0].replace('BINANCE:', '');
      const tpVal = parts[3].replace('TP:', '').trim();
      const slVal = parts[4].replace('SL:', '').trim();
      if (!tpVal || !slVal) {
        const fill = parseFloat(parts[2]);
        const pick = picks.find(p => p.sym === sym);
        if (pick) {
          await protectPosition(sym, pick.tp, pick.sl);
        } else {
          // Default: TP +8%, SL -5%
          const tp = (fill * 1.08).toPrecision(6);
          const sl = (fill * 0.95).toPrecision(6);
          await protectPosition(sym, tp, sl);
        }
      }
    }

    // Add picks if < 5
    if (count < 5) {
      const existing = positions.map(p => p.split('|')[0].replace('BINANCE:', ''));
      const needed = 5 - count;
      let added = 0;
      for (const pick of picks) {
        if (added >= needed) break;
        if (existing.includes(pick.sym)) continue;
        await placeOrder('BINANCE:' + pick.sym, pick.side, pick.tp, pick.sl);
        added++;
      }
    }

    await sleep(500);
    console.log('\n=== Final state ===');
    await readPositions();
  }
  else if (cmd === 'validate') {
    const account = args[1];
    if (!(await switchAccount(account))) { console.log('FAIL switch'); process.exit(1); }
    await sleep(500);
    const positions = await readPositions();
    let bad = 0;
    for (const pos of positions) {
      const parts = pos.split('|');
      const tpVal = parts[3].replace('TP:', '').trim();
      const slVal = parts[4].replace('SL:', '').trim();
      if (!tpVal || !slVal) { bad++; console.log('  MISSING:', pos); }
    }
    if (bad === 0) console.log(`  ${account}: ALL OK (${positions.length} positions, all have TP/SL)`);
    else console.log(`  ${account}: ${bad} positions missing TP/SL!`);
  }

  ws.close();
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
