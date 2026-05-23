# TradingView MCP — Proper Trade Flow (end-to-end, tested 2026-04-22)

**Tested on:** TV Desktop 3.1.0.7818 (WindowsApps), CDP port 9222.
**Worked examples:** 16 paper trades placed this session across `HIGHFWWRABV55_SCOREABOVE50_V4` and `zerounderscore` accounts.

The chart's one-click `buy-order-button` / `sell-order-button` places a MARKET order with TV's default bracket — **TV default is an inverted 0.67:1 R:R** (TP +2% / SL −3%). **You MUST override TP/SL via the Protect Position dialog** before moving on. This document shows the exact command sequence that works.

---

## Prerequisites

1. TV running with CDP enabled (version matters):
   ```powershell
   "C:\Program Files\WindowsApps\TradingView.Desktop_3.1.0.7818_x64__n534cwy3pjxzj\TradingView.exe" --remote-debugging-port=9222
   ```
   On older 3.0.0.7652 the flag is rejected (node-stub binary). On 3.1.0.7818 it works.

2. Verify CDP:
   ```
   mcp__tradingview-desktop__tv_health_check
   # expect: cdp_connected=true, api_available=true
   ```

3. Account switch via DOM click (NOT mouse coords — row y-positions shift with scroll):
   ```js
   // Step 1: open dropdown
   mcp__tradingview-desktop__ui_evaluate(expression=`document.querySelector('button.dropdownButton-dm1wtgNn').click(); 'opened'`)

   // Step 2: click target account row by exact text
   mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
     var divs = document.querySelectorAll('div.middle-RDCgMoEQ.hasTitle-RDCgMoEQ');
     for (var i=0; i<divs.length; i++) {
       if (divs[i].textContent.trim() === 'TARGET_NAME') { divs[i].click(); return 'clicked'; }
     }
     return 'not found';
   })()`)

   // Step 3: VERIFY (mandatory)
   mcp__tradingview-desktop__ui_evaluate(expression=`document.querySelector('span.accountName-dm1wtgNn').textContent.trim()`)
   // Must equal TARGET_NAME. Do NOT proceed otherwise.
   ```

   If step 2 finds 0 rows, the dropdown closed too fast. Re-run step 1 + step 2 in the same turn.

---

## Step 1 — Set chart symbol

```
mcp__tradingview-desktop__chart_set_symbol(symbol="NYSE:CVX")
# response: {success:true, symbol:"NYSE:CVX", chart_ready:false}
```

`chart_ready:false` is normal immediately after setting. Wait ~3 seconds before the chart data populates. If you call `quote_get` too early it returns `∅` or "Could not retrieve quote. The chart may still be loading."

```bash
sleep 3
```

Exchange prefix matters. Common valid prefixes:
| Asset | Prefix examples |
|---|---|
| US stocks | `NYSE:`, `NASDAQ:`, `AMEX:` |
| Crypto | `BINANCE:`, `OKX:`, `BYBIT:`, `COINBASE:` |
| Forex | `OANDA:`, `FX:`, `FXCM:` |
| ETFs | `AMEX:` (IWM/SPY/QQQ/XLE), `NASDAQ:` (TLT) |

Use `mcp__tradingview-desktop__symbol_search(query="SYM", type="crypto")` to enumerate when unsure. HYPE (Hyperliquid) is NOT on Binance — use `OKX:HYPEUSDT`.

---

## Step 2 — Verify price loaded

```
mcp__tradingview-desktop__quote_get()
# expect: {success:true, last:<price>, symbol:"NYSE:CVX", description:"Chevron..."}
```

Gotchas:
- If `description` comes back with a DIFFERENT symbol ("TAO / TetherUS"), the chart is stale — re-run `chart_set_symbol` and wait longer.
- `quote_get(symbol="X")` sometimes ignores the argument and returns whatever's on the currently-loaded chart. Safer to call `chart_set_symbol` first then `quote_get()` with no arg.

---

## Step 3 — Place market order (one-click chart button)

TV's chart has always-visible `buy-order-button` / `sell-order-button` widgets at the current bid/ask. Clicking either **immediately places a market order** with TV's default TP/SL bracket. No confirmation dialog.

```
mcp__tradingview-desktop__ui_click(by="data-name", value="buy-order-button")
# For SHORT: value="sell-order-button"
```

**⚠️ This creates an IMMEDIATE MARKET FILL**, not an order ticket you can review first. If you want a review-then-submit flow, use the order-ticket panel (see §7 Alternative flow).

---

## Step 4 — Verify fill + open Protect Position dialog

Find the new position row by symbol prefix and click its edit pencil in one call:

```js
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var rows = document.querySelectorAll('tr');
  for (var i=0;i<rows.length;i++){
    if ((rows[i].textContent||'').indexOf('NYSE:CVX')!==-1){
      var cells=rows[i].querySelectorAll('td');
      if (cells.length < 6) continue;
      var btn = rows[i].querySelector('button[data-name="edit-settings-cell-button"]');
      if (btn) btn.click();
      return {placed: cells[3].textContent.trim(), edit_clicked: !!btn};
    }
  }
  return 'not found';
})()`)
# expect: {placed:"187.32", edit_clicked:true}
```

If 'not found', the order didn't register — common causes:
- Available funds insufficient (TV silently drops the order on small accounts)
- Chart symbol mismatch (button clicked on stale chart)
- Market closed for the asset class (stocks on weekends)

---

## Step 5 — Set proper TP/SL via Protect Position dialog

After step 4, the dialog has 4 visible inputs:
- `vis[0]` = TP toggle (checkbox)
- `vis[1]` = TP price (text)
- `vis[2]` = SL toggle (checkbox)
- `vis[3]` = SL price (text)

(The order-ticket flow, §7, pushes these down by 1 because of an extra qty input at `vis[0]`.)

```js
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var ins = document.querySelectorAll('input');
  var vis=[]; for (var i=0;i<ins.length;i++){ if(ins[i].offsetParent!==null) vis.push(ins[i]); }
  if (vis.length < 4) return 'FAIL: '+vis.length+' inputs';
  var tpT=vis[0], tpP=vis[1], slT=vis[2], slP=vis[3];
  var nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  if (!tpT.checked) tpT.click();     // CRITICAL: toggle must be ON or price silently dropped on Confirm
  if (!slT.checked) slT.click();
  tpP.focus(); nativeSet.call(tpP,'192.75'); tpP.dispatchEvent(new Event('input',{bubbles:true})); tpP.dispatchEvent(new Event('change',{bubbles:true}));
  slP.focus(); nativeSet.call(slP,'184.32'); slP.dispatchEvent(new Event('input',{bubbles:true})); slP.dispatchEvent(new Event('change',{bubbles:true}));
  return {tp_t:tpT.checked, tp:tpP.value, sl_t:slT.checked, sl:slP.value};
})()`)
# expect: {tp_t:true, tp:"192.75", sl_t:true, sl:"184.32"}
```

**Why `nativeSet` + `dispatchEvent`:** React-rendered inputs ignore direct `.value=` assignment. You MUST use the property descriptor's setter, then dispatch `input` + `change` events so React updates its internal state. Without this the dialog looks correct but values don't "stick" and Confirm silently uses the old values.

**Side-sanity gate (MANDATORY):**
- LONG: `tp > entry > sl` — else ABORT (do NOT click Confirm)
- SHORT: `sl > entry > tp` — else ABORT

A wrong-side TP/SL fills-then-instantly-stops-out on the MARKET order.

---

## Step 6 — Confirm

```
mcp__tradingview-desktop__ui_click(by="text", value="Confirm")
# clicked.data_name == "place-and-modify-button"
```

The `place-and-modify-button` data-name is reused for both "Submit new order" and "Confirm position modification". Read button text to know which mode.

---

## Step 7 — Post-fill audit (MANDATORY)

After every trade, re-read the positions table and confirm TP/SL columns are populated:

```js
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var rows = document.querySelectorAll('tr'); var out=[]; var v=[];
  for (var i=0;i<rows.length;i++){
    var cells = rows[i].querySelectorAll('td');
    if (cells.length < 8) continue;
    var sym = cells[0]? cells[0].textContent.trim():'';
    if (sym.indexOf(':')===-1) continue;
    var tp = cells[4]? cells[4].textContent.trim():'';
    var sl = cells[5]? cells[5].textContent.trim():'';
    if (!tp || !sl) v.push(sym+': missing TP/SL');
    out.push({sym:sym, side:cells[1].textContent.trim(), qty:cells[2].textContent.trim(), entry:cells[3].textContent.trim(), tp:tp, sl:sl, last:cells[6].textContent.trim(), upnl:cells[7].textContent.trim()});
  }
  return {positions: out, violations: v};
})()`)
# expect: violations:[] — if non-empty, RE-OPEN Protect Position and set TP/SL before anything else
```

Column layout (positions table, zero-indexed):
| Idx | Column |
|---|---|
| 0 | Symbol |
| 1 | Side |
| 2 | Qty |
| 3 | Avg Fill Price |
| 4 | **Take Profit** |
| 5 | **Stop Loss** |
| 6 | Last Price |
| 7 | Unrealized P&L |
| 8 | Unrealized P&L % |
| 9 | Trade Value |

---

## Alternative flow — Order ticket panel (reviewed entry)

If you want to set qty/TP/SL BEFORE placing (not the one-click chart button), use the docked order ticket. Click a chart price once to bring it up, then:

```js
// The submit button starts as "Start creating order" until a side is chosen.
// Switch side first:
mcp__tradingview-desktop__ui_click(by="data-name", value="side-control-sell")   // for SHORT
// or                                         value="side-control-buy"           // for LONG

// Then set qty + TP/SL (5 visible inputs in this mode: vis[0]=qty, vis[1]=TP-toggle, vis[2]=TP, vis[3]=SL-toggle, vis[4]=SL):
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var ot = document.querySelector('[class*="orderTicket-"]');
  var ins = ot.querySelectorAll('input'); var vis=[];
  for (var i=0;i<ins.length;i++){ if(ins[i].offsetParent!==null) vis.push(ins[i]); }
  var qty=vis[0], tpT=vis[1], tpP=vis[2], slT=vis[3], slP=vis[4];
  var set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  if (!tpT.checked) tpT.click();
  if (!slT.checked) slT.click();
  qty.focus(); set.call(qty,'2'); qty.dispatchEvent(new Event('input',{bubbles:true})); qty.dispatchEvent(new Event('change',{bubbles:true}));
  tpP.focus(); set.call(tpP,'TP_PRICE'); tpP.dispatchEvent(new Event('input',{bubbles:true})); tpP.dispatchEvent(new Event('change',{bubbles:true}));
  slP.focus(); set.call(slP,'SL_PRICE'); slP.dispatchEvent(new Event('input',{bubbles:true})); slP.dispatchEvent(new Event('change',{bubbles:true}));
  var submit = ot.querySelector('[data-name="place-and-modify-button"]');
  return {submit_text: submit? submit.textContent.trim():'none'};
})()`)
// submit_text should now read "Sell {N} {SYM} MARKET" — NOT "Start creating order"

mcp__tradingview-desktop__ui_click(by="data-name", value="place-and-modify-button")
```

**Qty units:**
- Default is `% balance`. qty=2 → TV auto-computes N units from account balance × leverage.
- FX: qty=2 → ~2,460 units (2 micro-lots × leverage).
- Crypto: qty=2 → ~152 DOT at ~$1.29 (on 10x leverage paper account).
- Stocks: qty=2 → 0.99 shares at $112 (fractional allowed).
- ETFs: qty=2 may round to **0 shares** on small accounts — IWM @ $275 needs ~28% of a $981 account for 1 share. Toggle the `% balance` button next to qty to switch to USD value or Shares.

**If submit button reads "Buy 0 {SYM} MARKET":** qty resolved to 0. Increase % or switch unit mode.

---

## Full command sequence worked example — CVX LONG on zerounderscore

```js
// 1. switch account + verify
ui_evaluate("document.querySelector('button.dropdownButton-dm1wtgNn').click(); 'opened'")
ui_evaluate("(function(){ var d=document.querySelectorAll('div.middle-RDCgMoEQ.hasTitle-RDCgMoEQ'); for(var i=0;i<d.length;i++){if(d[i].textContent.trim()==='zerounderscore'){d[i].click(); return 'clicked';}} return 'not found';})()")
ui_evaluate("document.querySelector('span.accountName-dm1wtgNn').textContent.trim()")  // "zerounderscore" ✓

// 2. set symbol + wait
chart_set_symbol(symbol="NYSE:CVX")
bash> sleep 3
quote_get()  // confirms NYSE:CVX, last ~187.32

// 3. market order via chart button
ui_click(by="data-name", value="buy-order-button")

// 4. verify fill + open protect dialog
ui_evaluate(/* row-finder + edit-click per §4 */)  // {placed:"187.32"}

// 5. set TP 192.75 / SL 184.32 with toggles ON
ui_evaluate(/* TP/SL setter per §5 */)   // {tp_t:true, tp:"192.75", sl_t:true, sl:"184.32"}

// 6. confirm
ui_click(by="text", value="Confirm")

// 7. audit
ui_evaluate(/* positions table reader per §7 */)
// violations:[] ✓ — CVX shows TP=192.75, SL=184.32
```

Result row: `NYSE:CVX | Long | 0.98 | 187.32 | 192.75 | 184.32 | ...`

---

## Checklist for other agents

Before placing any trade:
- [ ] `tv_health_check` returned `cdp_connected:true`
- [ ] Current account verified via `span.accountName-dm1wtgNn` read (matches intended target)
- [ ] Chart symbol is the one you want (check via `quote_get().description`)
- [ ] Side-sanity math done on paper: LONG needs TP>entry>SL; SHORT needs SL>entry>TP
- [ ] Position size justification written (% of balance, leverage, trade value in USD)

After every trade:
- [ ] Positions table shows your symbol with non-empty TP and SL columns
- [ ] TP/SL direction matches side (no inversions)
- [ ] `mcp__claude-peers__set_summary` updated if running alongside other agents

Common silent-failure modes:
- Protect Position dialog toggles OFF — prices appear set but dropped on Confirm. Always click toggle if `.checked !== true`.
- React controlled-input ignored direct `.value=` without `nativeSet`. Always use property-descriptor setter + `input` and `change` events.
- Chart price showed `∅` — symbol changed but data not loaded. Wait, don't retry-spam.
- Order ticket submit reads "Start creating order" — means no side selected. Click `side-control-buy` / `side-control-sell` first.
- ETF qty=2% rounds to 0 shares on small accounts — use higher %, switch to Shares unit via the `% balance` toggle, or skip to a cheaper ETF.

## Known environment quirks

- TV 3.0.0.7652 (node-stub) rejects `--remote-debugging-port=9222`. Upgrade to 3.1.0.7818+.
- `mcp__tradingview-desktop__tv_launch` does NOT search `WindowsApps\TradingView.Desktop_*` — launch manually via the direct exe path.
- `quote_get(symbol="X")` sometimes ignores the argument — use `chart_set_symbol` first.
- `data-name="edit-settings-cell-button"` pencil icon — the only reliable hook into the Protect Position dialog. Don't try inline edit.
- `place-and-modify-button` data-name is reused for both submit and confirm — always read button text.
