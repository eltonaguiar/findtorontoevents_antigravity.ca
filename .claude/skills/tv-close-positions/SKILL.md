---
name: tv-close-positions
description: Close one or more TradingView paper positions safely. Verifies the account first (drift kills the wrong portfolio), uses row-level Close buttons (NOT the global flat-all), confirms close in the History/Trades log, and handles closed-market behavior (US equity after-hours, futures session gaps). Aliases — tv-close, tv-flat, close-positions.
---

# tv-close-positions

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

Two ways to close: (a) per-row Close button, (b) market-side reverse order. Default to (a) — it's idempotent, verifies cleanly, and skips order-panel state.

## Pre-flight (NON-NEGOTIABLE)

1. `tv-cdp-launch` returned green.
2. `tv-account-switch` verified the target account.
3. `tv-positions-read` snapshot in hand. You know which symbol is at which row index.
4. **Market-open check.** Equity/ETF after-hours closes route to next-open queue and execute at gap risk. Crypto is 24/7. Forex closes Fri 22:00 UTC → Sun 22:00 UTC. Futures session per CME calendar.

## Step 1 — Identify market state per symbol

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var rows = document.querySelectorAll('table tr');
  var SYM = /^[A-Z][A-Z0-9_]+:[A-Z][A-Z0-9!._]+$/;
  var out = [];
  rows.forEach((r,i)=>{
    var c = r.querySelectorAll('td');
    if (c.length < 6) return;
    var sym = (c[0]?.textContent||'').trim();
    if (!SYM.test(sym)) return;
    var hasCloseBtn = !!r.querySelector('button[aria-label="Close"], button.close-position');
    out.push({sym, hasCloseBtn});
  });
  return JSON.stringify(out);
})()`)
```

If `hasCloseBtn === false` for an equity at 22:00Z weekday, that's "market closed — close queued for next open." Decide whether to queue or wait.

| Asset | Open hours (UTC) | After-hours behavior |
|---|---|---|
| Crypto | 24/7 | Close immediately |
| US Equity / ETF | 13:30–20:00 Mon–Fri | TV queues a market order; fills at next 13:30Z bell with gap risk |
| Forex | 22:00 Sun → 22:00 Fri | Closed Sat + Sun day; queue or wait |
| CME Futures | 22:00 Sun → 22:00 Fri (1h daily break ~22:00) | Queue across the daily break |
| LSE / TSX / etc | Per local exchange | Same pattern as US |

Default policy: queue only with explicit user confirmation. Otherwise wait until market open.

## Step 2 — Close one symbol

Replace `BINANCE:BTCUSDT` with the exact symbol string from the snapshot (case-sensitive, includes exchange prefix).

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var rows = document.querySelectorAll('table tr');
  for (var i=0;i<rows.length;i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length < 3) continue;
    var sym = (cells[0]?.textContent||'').trim();
    if (sym !== 'BINANCE:BTCUSDT') continue;
    var btns = rows[i].querySelectorAll('button');
    for (var j=0;j<btns.length;j++) {
      var label = btns[j].getAttribute('aria-label') || btns[j].textContent.trim();
      if (label === 'Close' || label === 'close-position') {
        btns[j].click();
        return 'closed: ' + sym;
      }
    }
    return 'no-close-btn: ' + sym;
  }
  return 'not-found: BINANCE:BTCUSDT';
})()`)
```

Some TV builds show a confirmation modal — handle it:

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var confirm = document.querySelector('[data-name="confirm-button"], button[name="confirm"]');
  if (confirm) { confirm.click(); return 'confirmed'; }
  // Fallback by text
  var bs = document.querySelectorAll('button');
  for (var i=0;i<bs.length;i++) {
    var t = bs[i].textContent.trim();
    if (t === 'Close position' || t === 'Yes, close') { bs[i].click(); return 'confirmed-by-text:'+t; }
  }
  return 'no-modal';
})()`)
```

## Step 3 — Verify the close

Two checks. Both must pass before claiming "closed":

```javascript
// (a) symbol no longer in positions table
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var rows = document.querySelectorAll('table tr');
  var SYM = /^[A-Z][A-Z0-9_]+:[A-Z][A-Z0-9!._]+$/;
  for (var i=0;i<rows.length;i++) {
    var c = rows[i].querySelectorAll('td');
    if (c.length < 6) continue;
    var sym = (c[0]?.textContent||'').trim();
    if (sym === 'BINANCE:BTCUSDT') return 'STILL-OPEN';
  }
  return 'GONE';
})()`)
```

```javascript
// (b) History tab shows a fresh "Close … position" row in the last 60s
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var btns = document.querySelectorAll('button, [role="tab"]');
  for (var i=0;i<btns.length;i++) {
    if ((btns[i].textContent||'').trim() === 'History') { btns[i].click(); break; }
  }
  return 'history-clicked';
})()`)
```

Wait ~2s for the history table to refresh, then scan for the close event matching the symbol.

## Step 4 — Batch close (multiple symbols)

Loop Step 2 + Step 3 per symbol. Do NOT use a global "Close All" button — it's an irreversible flat-all across the entire portfolio. If the user explicitly asks "flat everything in this account", confirm twice before clicking it.

## Anti-patterns

| Anti-pattern | Damage |
|---|---|
| Closing without re-verifying account name | Closed the wrong portfolio. Production outage pattern. |
| Using `ui_click(by="text", value="Close")` | Matches the first Close button found — often a different row than intended |
| Skipping Step 3 verify | Modal blocked the click; you think it's closed but it's still open. P&L on the next read will betray you |
| Closing illiquid futures during the daily break | Order queues + slips on session reopen — significant gap risk |
| Closing in pre/post-market without flagging the slippage risk to the user | Equity gaps 0.5–3% routinely overnight; closing at 21:00Z eats spread |

## Companion skills

- `tv-cdp-launch`
- `tv-account-switch`
- `tv-positions-read` — pull snapshot before closing
- `tv-paper-trade` — placing trades (existing skill)
- `tv-debug`
