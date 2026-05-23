---
name: tv-positions-read
description: Read open positions from the TradingView Desktop positions table, with the symbol-regex filter that prevents the History tab's time-stamped rows from polluting the position list. Includes the violation audit (positions without TP/SL, inverted TP/SL relative to side). Aliases — tv-positions, tv-read-pos, read-positions.
---

# tv-positions-read

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

The DOM exposes positions through generic `<table>`s. The Positions tab and History tab share the same selector. If History is the foreground tab, a naive reader returns trade-log rows whose first cell (a timestamp) contains `:` and looks symbol-shaped. This skill pins to the Positions tab and tightens the symbol regex.

## When to use

- Before placing a trade (to read current exposure + correlation).
- Before closing positions (to know which Close button maps to which row).
- After every account switch (per `tv-account-switch` Step 5).
- For per-portfolio snapshots that feed into a swarm consult.

## Step 1 — Force the Positions tab to foreground

Even if the user previously selected History, click Positions. This is idempotent.

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var btns = document.querySelectorAll('button, [role="tab"]');
  for (var i=0;i<btns.length;i++) {
    if ((btns[i].textContent||'').trim() === 'Positions') {
      btns[i].click();
      return 'clicked-Positions';
    }
  }
  return 'tab-not-found';
})()`)
```

If the return is `tab-not-found`, the bottom-pane is collapsed. Click the pane toggle or scroll the layout into view first (rare — usually only after a fresh page load).

## Step 2 — Install the reader (once per page load)

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  // Symbol regex pins to EXCHANGE:TICKER format. Rejects 'YYYY-MM-DD HH:MM:SS' history rows.
  var SYM = /^[A-Z][A-Z0-9_]+:[A-Z][A-Z0-9!._]+$/;
  window.__readPos = function(){
    var rows = document.querySelectorAll('table tr');
    var out = [];
    for (var i=0;i<rows.length;i++) {
      var cells = rows[i].querySelectorAll('td');
      if (cells.length < 6) continue;
      var sym = (cells[0]?.textContent || '').trim();
      if (!SYM.test(sym)) continue;
      out.push({
        sym,
        side:  cells[1]?.textContent.trim(),
        qty:   cells[2]?.textContent.trim(),
        entry: cells[3]?.textContent.trim(),
        tp:    cells[4]?.textContent.trim(),
        sl:    cells[5]?.textContent.trim(),
        last:  cells[6]?.textContent.trim(),
        upnl:  cells[7]?.textContent.trim(),
        upct:  cells[8]?.textContent.trim()
      });
    }
    return out;
  };
  window.__curAcct = function(){
    return document.querySelector('span.accountName-dm1wtgNn')?.textContent.trim() || '';
  };
  return 'reader ready';
})()`)
```

Column order (verified 2026-05-14 on TVDesktop 3.1.0):

| Idx | Column | Notes |
|---|---|---|
| 0 | Symbol | `EXCHANGE:TICKER` |
| 1 | Side | `Long` / `Short` |
| 2 | Qty | Comma-separated (forex lots show as `42,434`) |
| 3 | Avg fill price | |
| 4 | Take profit | Empty string when missing |
| 5 | Stop loss | Empty string when missing |
| 6 | Last price | |
| 7 | Unrealized PnL | `+/-NNN.NNUSD` (uses Unicode minus `−`, not ASCII `-`) |
| 8 | Unrealized PnL % | `+/-N.NN%` |
| 9–13 | Trade value / Market value / Leverage / Margin / Expiration | Ignore for snapshot |

## Step 3 — Read + verify

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`JSON.stringify({
  acct: window.__curAcct(),
  pos:  window.__readPos()
})`)
```

Parse the JSON. **Verify `acct` matches the target portfolio** before persisting the snapshot.

## Step 4 — Violation audit (mandatory after read)

For each position, flag:

1. **Missing TP or SL** — `pos.tp === ''` or `pos.sl === ''`. Hard violation; per `tv-paper-trade` skill the position should not exist. Mitigate via Protect Position dialog.
2. **Inverted TP/SL relative to side:**
   - LONG: must satisfy `tp > entry > sl`. If `sl > entry`, the position is in trailing-stop territory (locking profit) — fine if `last > sl`, but flag for human review.
   - SHORT: must satisfy `sl > entry > tp`. Inversion = instant stop-out risk.
3. **Unicode minus in numbers** — `cells[7].textContent` returns `−167.50USD` with `−`, not ASCII `-`. Strip before `parseFloat`: `s.replace(/[−–]/g,'-')`.

Emit a violation block in your snapshot JSON, e.g.:

```json
{
  "sym": "NYSE:BAC", "side": "Long", "tp": "", "sl": "",
  "violation": "no TP/SL"
}
```

## Step 5 — Persist

Write one snapshot file per account:

```
reports/portfolio_review_<YYYY-MM-DD>/snapshot_<acct>.json
```

Body shape:
```json
{
  "acct": "...",
  "captured_at_utc": "2026-05-14T22:58Z",
  "pos": [{...}, {...}]
}
```

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| `cells[0].textContent.includes(':')` as the symbol test | Time stamps `HH:MM:SS` match. You get history rows. |
| Reading without forcing Positions tab | History rows poison the snapshot when user previously had History open. |
| `parseFloat(cells[7].textContent)` directly | `−` (U+2212) doesn't parse — value comes back NaN. Normalize first. |
| Trusting the qty number for sizing math without comma-stripping | `parseFloat("42,434")` = 42. Strip commas. |
| Reading positions immediately after `tv-account-switch` Step 3 | Table is mid-refresh. Always `sleep 4` first. |

## Companion skills

- `tv-cdp-launch` — pre-flight
- `tv-account-switch` — switch before reading
- `tv-paper-trade` — placing trades (existing skill)
- `tv-close-positions` — closes after reading
- `tv-debug` — when the reader returns nothing
