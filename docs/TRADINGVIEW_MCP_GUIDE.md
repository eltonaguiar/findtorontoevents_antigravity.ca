# TradingView MCP Guide

**Upstream:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) (installed from this repo as `npm` dependency `github:tradesdontlie/tradingview-mcp`).

**Server:** Node.js MCP stdio → **Chrome DevTools Protocol** to TradingView Desktop (**port `9222`** is hardcoded in the package’s `src/connection.js`; launch TV on that port).

**~78 tools** for chart read/write, Pine, data, UI automation (including paper trading via DOM — see `.claude/skills/tv-paper-trade/SKILL.md`).

---

## Setup

### 0. Install the MCP package (repo root)

```bash
npm install
```

This installs `node_modules/tradingview-mcp` from GitHub. Smoke-test stdio server (will wait for MCP client; Ctrl+C to exit):

```bash
npm run mcp:tradingview
```

### 1. Launch TradingView Desktop with CDP enabled

```bash
# From MCP once connected (recommended):
# tool: tv_launch  (optional port; package defaults to 9222)

# Or manually (Windows Store build example):
"…\TradingView.exe" --remote-debugging-port=9222
```

### 2. MCP config (Cursor)

This repo includes **`.cursor/mcp.json`** registering the server as **`tradingview-desktop`**.

```json
{
  "mcpServers": {
    "tradingview-desktop": {
      "command": "node",
      "args": ["${workspaceFolder}/node_modules/tradingview-mcp/src/server.js"]
    }
  }
}
```

**Claude Code** can merge the same `tradingview-desktop` block into **`~/.claude/.mcp.json`** or project **`.mcp.json`** (this repo’s root `.mcp.json` is kept in sync for that).

If `${workspaceFolder}` is not expanded by your client, replace it with the absolute path to this repo (e.g. `E:/findtorontoevents_antigravity.ca`).

**Restart the IDE / Claude Code** after changing MCP config so the server loads.

### 3. Verify connection

In the agent, call tool **`tv_health_check`** on server **`tradingview-desktop`**.

Expected: `cdp_connected: true`, chart symbol/resolution when a chart tab is open.

**Note:** The MCP host only appears in Cursor’s tool list after the server is enabled and connected; if tools are missing, confirm `npm install` ran and the config path points at `node_modules/tradingview-mcp/src/server.js`.

---

## Quick Reference — Tool Categories

| Category | Tools | What For |
|----------|-------|----------|
| **Chart Control** | 8 | Change symbol, timeframe, chart type, scroll, zoom |
| **Data Reading** | 10 | OHLCV bars, quotes, indicator values, Pine output |
| **Pine Script** | 11 | Write, compile, analyze, save Pine scripts |
| **Drawing** | 5 | Draw lines, rectangles, text on chart |
| **Replay** | 6 | Bar replay mode for backtesting |
| **Alerts** | 3 | Create, list, delete price alerts |
| **UI Control** | 8 | Click, type, evaluate JS, panels, fullscreen |
| **Paper Trading** | via `ui_evaluate` | Place trades, manage positions (DOM automation) |
| **Tabs/Layouts** | 5 | Switch tabs, layouts, manage chart windows |
| **Batch** | 1 | Run actions across multiple symbols/timeframes |

---

## Chart Control

### Change Symbol
```
chart_set_symbol(symbol="BINANCE:BTCUSDT")
chart_set_symbol(symbol="NASDAQ:AAPL")
chart_set_symbol(symbol="FX:EURUSD")
chart_set_symbol(symbol="NYMEX:CL1!")  # Crude oil futures
```

### Change Timeframe
```
chart_set_timeframe(timeframe="1")    # 1 minute
chart_set_timeframe(timeframe="15")   # 15 minutes
chart_set_timeframe(timeframe="60")   # 1 hour
chart_set_timeframe(timeframe="D")    # Daily
chart_set_timeframe(timeframe="W")    # Weekly
```

### Change Chart Type
```
chart_set_type(chart_type="Candles")      # or "1"
chart_set_type(chart_type="HeikinAshi")   # or "8"
chart_set_type(chart_type="Line")         # or "2"
```

### Navigate
```
chart_scroll_to_date(date="2024-01-15")
chart_set_visible_range(from=1704067200, to=1706745600)  # Unix timestamps
chart_get_visible_range()
```

### Get Current State
```
chart_get_state()  # Returns symbol, timeframe, all indicator names + entity IDs
```

---

## Reading Data

### Price Data (OHLCV)
```
# Compact summary (recommended — saves context)
data_get_ohlcv(summary=true)

# Full bar data
data_get_ohlcv(count=100)
```

### Real-Time Quote
```
quote_get(symbol="BINANCE:BTCUSDT")
# Returns: last, open, high, low, close, volume
```

### Indicator Values
```
data_get_study_values()
# Returns current values for ALL visible indicators (RSI, MACD, BB, EMA, etc.)
```

### Indicator Details
```
data_get_indicator(entity_id="xxx")  # Get specific indicator inputs/outputs
```

### Strategy Tester Results
```
data_get_strategy_results()  # Performance metrics
data_get_equity()            # Equity curve
data_get_trades(max_trades=50)  # Trade list
```

---

## Reading Pine Script Output

For custom indicators that draw lines, labels, tables, or boxes:

```
# Horizontal price levels from line.new()
data_get_pine_lines(study_filter="My Indicator")

# Text labels with prices from label.new()
data_get_pine_labels(study_filter="Profiler")

# Table data from table.new()
data_get_pine_tables(study_filter="Dashboard")

# Price zones from box.new()
data_get_pine_boxes(study_filter="Supply Demand")
```

**Important:** Indicators must be VISIBLE on chart for these to work.

---

## Pine Script Development

### Full Development Workflow
```
# 1. Create new script
pine_new(type="indicator")

# 2. Write code
pine_set_source(source="//@version=6\nindicator('My RSI', overlay=false)\nplot(ta.rsi(close, 14))")

# 3. Analyze offline (catches bugs before compile)
pine_analyze(source="...")

# 4. Check compilation (server-side, no chart needed)
pine_check(source="...")

# 5. Compile and add to chart
pine_compile()
# Or use smart compile (detects button, reports errors):
pine_smart_compile()

# 6. Check for errors
pine_get_errors()

# 7. Read console/log output
pine_get_console()

# 8. Save
pine_save()
```

### Other Pine Tools
```
pine_get_source()           # Read current code from editor
pine_list_scripts()         # List all saved scripts
pine_open(name="My Strat")  # Open a saved script
```

---

## Indicators

### Add/Remove
```
# ADD — use FULL names, not abbreviations
chart_manage_indicator(action="add", indicator="Relative Strength Index")
chart_manage_indicator(action="add", indicator="MACD")
chart_manage_indicator(action="add", indicator="Bollinger Bands")
chart_manage_indicator(action="add", indicator="Volume")
chart_manage_indicator(action="add", indicator="Moving Average Exponential", inputs='{"length": 21}')

# REMOVE — need entity_id from chart_get_state()
chart_manage_indicator(action="remove", entity_id="xxx")
```

### Toggle Visibility
```
indicator_toggle_visibility(entity_id="xxx", visible=false)
```

### Change Inputs
```
indicator_set_inputs(entity_id="xxx", inputs='{"length": 50}')
```

---

## Drawing on Charts

```
# Horizontal line at price
draw_shape(shape="horizontal_line", point={"time": 1704067200, "price": 42000})

# Trend line between two points
draw_shape(shape="trend_line",
  point={"time": 1704067200, "price": 40000},
  point2={"time": 1706745600, "price": 45000},
  overrides='{"linecolor": "#ff0000", "linewidth": 2}')

# Rectangle zone
draw_shape(shape="rectangle",
  point={"time": 1704067200, "price": 40000},
  point2={"time": 1706745600, "price": 42000})

# Text annotation
draw_shape(shape="text", point={"time": 1704067200, "price": 43000}, text="Entry Zone")

# Manage drawings
draw_list()                          # List all drawings
draw_get_properties(entity_id="xxx") # Get properties
draw_remove_one(entity_id="xxx")     # Remove one
draw_clear()                         # Remove ALL
```

---

## Bar Replay (Backtesting)

```
# Start replay from a date
replay_start(date="2024-06-01")

# Step forward one bar
replay_step()

# Auto-play (set speed in ms, lower = faster)
replay_autoplay(speed=500)

# Execute trades during replay
replay_trade(action="buy")
replay_trade(action="sell")
replay_trade(action="close")

# Check status
replay_status()

# Stop and return to live
replay_stop()
```

---

## Alerts

```
alert_create(condition="crossing", price=45000, message="BTC hit 45K")
alert_create(condition="greater_than", price=50000)
alert_create(condition="less_than", price=40000)
alert_list()
alert_delete(alert_id="xxx")
```

---

## UI Control

### Panels
```
ui_open_panel(panel="pine-editor", action="open")
ui_open_panel(panel="strategy-tester", action="toggle")
ui_open_panel(panel="trading", action="open")
# Panels: pine-editor, strategy-tester, watchlist, alerts, trading
```

### Click, Type, Scroll
```
ui_click(by="text", value="Buy")
ui_click(by="data-name", value="side-control-buy")
ui_type_text(text="BTCUSDT")
ui_scroll(direction="up", amount=3)
ui_keyboard(key="Enter")
ui_hover(x=500, y=300)
ui_mouse_click(x=500, y=300)
ui_find_element(selector="button.buy")
```

### Execute JavaScript (Most Powerful Tool)
```
ui_evaluate(expression="document.title")

# Complex logic — wrap in IIFE
ui_evaluate(expression=`(function() {
  var rows = document.querySelectorAll('table tr');
  var data = [];
  for (var i = 0; i < rows.length; i++) {
    data.push(rows[i].textContent.trim());
  }
  return data.join('\\n');
})()`)
```

### Screenshots
```
capture_screenshot(region="chart")
capture_screenshot(region="full")
capture_screenshot(region="strategy_tester", filename="backtest_results")
```

---

## Paper Trading (via ui_evaluate)

Paper trading uses DOM automation through `ui_evaluate` since there's no dedicated API.

### Portfolio routing (be deliberate)

| Picks | TV paper account |
|-------|------------------|
| `hyrotrader_picks.json` → **`tv_paper_portfolios.HYROTRADER`** (same picks as legacy **`tv_paper_portfolio`**) | **HYROTRADER** |
| `hyrotrader_picks.json` → **`tv_paper_portfolios.HYROTRADER2`** | **HYROTRADER2** |
| Phase7 / dashboard **SCALP**-only slice | **SCALPER** |
| Phase7 **TESTER** slice | **TESTER** |
| Phase7 **TRUSTOURSCORE** slice (non-Hyro) | **TRUSTOURSCORE** |

Switch account and **verify** `span.accountName-…` **before** `chart_set_symbol` or order clicks. See `.claude/skills/tv-paper-trade/SKILL.md`.

### Take profit / Stop loss: toggles first

If **TP/SL switches are off** (sliders inactive), typing prices **does not attach** to the order — you get a **naked market fill**.

1. Open **Trade**, order type **Market**, side **Buy/Sell**.
2. **Exits is a toggle** — do **not** blindly `ui_click(Exits)`; that **collapses** an already-open section. Use **safe expand Exits** below first.
3. Run the **enable exits** snippet below (or manually turn ON Take profit / Stop loss).
4. Only then set TP/SL **price** fields (prefer matching parents that contain the text **`Take profit, price`** and **`Stop loss, price`**).
5. Confirm return string starts with **`OK:`** before clicking **Buy … MARKET**.

**Safe expand Exits (only if TP/SL rows are hidden):**

```javascript
ui_evaluate(`(function() {
  function tpSlPriceInputsVisible() {
    var inputs = document.querySelectorAll('input');
    var tp = false, sl = false;
    for (var i = 0; i < inputs.length; i++) {
      var el = inputs[i];
      if (!el.offsetParent || el.id === 'quantity-field' || el.disabled) continue;
      if (el.type !== 'text' && el.type !== 'number') continue;
      var okTp = false, okSl = false, p = el;
      for (var d = 0; d < 14 && p; d++, p = p.parentElement) {
        var t = p.innerText || '';
        if (t.indexOf('Take profit') !== -1 && t.indexOf('price') !== -1) okTp = true;
        if (t.indexOf('Stop loss') !== -1 && t.indexOf('price') !== -1) okSl = true;
      }
      if (okTp) tp = true;
      if (okSl) sl = true;
    }
    return tp && sl;
  }
  if (tpSlPriceInputsVisible()) return 'SKIP: already expanded';
  var btns = document.querySelectorAll('button');
  for (var j = 0; j < btns.length; j++) {
    var b = btns[j];
    if (!b.offsetParent) continue;
    var txt = (b.innerText || '').replace(/\s+/g, ' ').trim();
    if (txt !== 'Exits' && txt.indexOf('Exits') !== 0) continue;
    if (b.getAttribute('aria-expanded') === 'true') return 'SKIP: would collapse';
    b.click();
    return 'OK: expanded Exits';
  }
  return 'WARN: Exits button not found';
})()`)
```

**Enable exits (toggle/switch on):**

```javascript
ui_evaluate(`(function() {
  var n = 0;
  document.querySelectorAll('[role="switch"]').forEach(function(sw) {
    if (!sw.offsetParent) return;
    var ctx = (sw.getAttribute('aria-label') || '') + ' ' + ((sw.closest('div') && sw.closest('div').innerText) || '');
    if (!/take profit|stop loss|tp|sl/i.test(ctx)) return;
    if (sw.getAttribute('aria-checked') === 'false') { sw.click(); n++; }
  });
  document.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
    if (!cb.offsetParent || cb.checked) return;
    var ctx = (cb.closest('div') && cb.closest('div').innerText) || '';
    if (/take profit|stop loss/i.test(ctx)) { cb.click(); n++; }
  });
  return 'exits_toggles_clicked=' + n;
})()`)
```

### Switch Account
```javascript
// Step 1: Open dropdown
ui_evaluate(`document.querySelector('button.dropdownButton-dm1wtgNn').click(); 'opened'`)

// Step 2: Click account
ui_evaluate(`(function(){
  var divs = document.querySelectorAll('div.middle-RDCgMoEQ.hasTitle-RDCgMoEQ');
  for (var i=0; i<divs.length; i++) {
    if (divs[i].textContent.trim() === 'HYROTRADER') { divs[i].click(); return 'clicked'; }
  }
  return 'not found';
})()`)

// Step 3: VERIFY (mandatory)
ui_evaluate(`document.querySelector('span.accountName-dm1wtgNn').textContent.trim()`)
```
Account names: **`HYROTRADER`**, **`HYROTRADER2`**, `THEWINNERS`, `SCALPER`, `TESTER`, `TRUSTOURSCORE`, `BROKIE`, `zerounderscore`

### Read Positions
```javascript
ui_evaluate(`(function() {
  var rows = document.querySelectorAll('table tr');
  var positions = [];
  for (var j = 0; j < rows.length; j++) {
    var cells = rows[j].querySelectorAll('td');
    if (cells.length > 5) {
      var sym = cells[0] ? cells[0].textContent.trim() : '';
      if (sym.includes(':')) {
        positions.push(Array.from(cells).map(c => c.textContent.trim()).join(' | '));
      }
    }
  }
  return positions.join('\\n') || 'No positions';
})()`)
```

### Place a Trade
```javascript
// 0. Switch account + verify (see above), then:
// 1. Set symbol
chart_set_symbol(symbol="BINANCE:ETHUSDT")

// 2. Open Trade / Market / Buy or Sell (ui_click side-control-buy etc.)

// 3. Safe expand Exits + ENABLE toggles (see guide — do NOT blind ui_click Exits)
// … run safe expand Exits ui_evaluate, then enable exits snippet …

// 4. Set TP/SL by hint (replace literals; must return OK:)
ui_evaluate(`(function() {
  var nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  function setPrice(needle, priceStr) {
    var inputs = document.querySelectorAll('input');
    for (var i = 0; i < inputs.length; i++) {
      var el = inputs[i];
      if (!el.offsetParent || el.id === 'quantity-field' || el.disabled) continue;
      if (el.type !== 'text' && el.type !== 'number') continue;
      var p = el, ok = false;
      for (var d = 0; d < 12 && p; d++, p = p.parentElement) {
        if ((p.innerText || '').indexOf(needle) !== -1) { ok = true; break; }
      }
      if (!ok) continue;
      nativeSet.call(el, priceStr);
      el.dispatchEvent(new Event('input', {bubbles: true}));
      el.dispatchEvent(new Event('change', {bubbles: true}));
      return el.value;
    }
    return null;
  }
  var tp = setPrice('Take profit, price', '123.45');
  var sl = setPrice('Stop loss, price', '120.00');
  if (tp && sl) return 'OK: TP=' + tp + ' SL=' + sl;
  return 'BLOCKER_FAIL: toggles off or fields missing';
})()`)

// 5. Execute ONLY if step 4 started with OK:
ui_evaluate(`(function() {
  var btns = document.querySelectorAll('button');
  for (var i = 0; i < btns.length; i++) {
    var t = btns[i].textContent.trim();
    if (t.includes('MARKET') && (t.includes('Buy') || t.includes('Sell'))) {
      btns[i].click(); return 'Executed: ' + t;
    }
  }
  return 'not found';
})()`)
```

### Close a Position
```javascript
ui_evaluate(`(function() {
  var rows = document.querySelectorAll('table tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length > 3 && cells[0].textContent.includes('SYMBOL')) {
      var btns = rows[i].querySelectorAll('button');
      for (var j = 0; j < btns.length; j++) {
        if (btns[j].getAttribute('aria-label') === 'Close') {
          btns[j].click(); return 'Closed';
        }
      }
    }
  }
  return 'not found';
})()`)
```

### Edit Position (Add/Change TP/SL)
```javascript
// 1. Click edit on the position row
ui_evaluate(`(function() {
  var rows = document.querySelectorAll('table tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length > 3 && cells[0].textContent.includes('SYMBOL')) {
      var btns = rows[i].querySelectorAll('button');
      for (var j = 0; j < btns.length; j++) {
        var al = btns[j].getAttribute('aria-label') || '';
        if (al.includes('Edit') || al.includes('Protect')) {
          btns[j].click(); return 'Editing';
        }
      }
    }
  }
  return 'nf';
})()`)

// 2. Enable TP/SL toggles + set values (same as step 4 above)
// 3. Click Confirm
ui_evaluate(`(function() {
  var btns = document.querySelectorAll('button');
  for (var i = 0; i < btns.length; i++) {
    if (btns[i].textContent.trim() === 'Confirm') { btns[i].click(); return 'Confirmed'; }
  }
  return 'nf';
})()`)
```

### Fix ALL Positions Missing TP/SL (Batch Audit + Repair)

This is the most common problem — positions opened without TP/SL due to toggles being off, concurrent agent issues, or the `BLOCKER_FAIL` being ignored. Run this audit on every account after placing trades.

**Step 1: Scan for unprotected positions**
```javascript
ui_evaluate(`(function() {
  var rows = document.querySelectorAll('table tr');
  var issues = [];
  for (var j = 0; j < rows.length; j++) {
    var cells = rows[j].querySelectorAll('td');
    if (cells.length > 5) {
      var sym = cells[0] ? cells[0].textContent.trim() : '';
      if (sym.includes(':')) {
        var tp = cells[4] ? cells[4].textContent.trim() : '';
        var sl = cells[5] ? cells[5].textContent.trim() : '';
        if (!tp || !sl) issues.push(sym + ' tp=' + (tp||'MISSING') + ' sl=' + (sl||'MISSING'));
      }
    }
  }
  return issues.length > 0 ? 'NEEDS FIX:\\n' + issues.join('\\n') : 'All positions have TP/SL';
})()`)
```

**Step 2: For each unprotected position, edit and add TP/SL**

Replace `SYMBOL` with the actual symbol (e.g., `LTCUSDT`), and `TP_PRICE`/`SL_PRICE` with actual numbers:

```javascript
// 2a. Click edit button on the position row
ui_evaluate(`(function() {
  var rows = document.querySelectorAll('table tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length > 3 && cells[0].textContent.includes('SYMBOL')) {
      var btns = rows[i].querySelectorAll('button');
      for (var j = 0; j < btns.length; j++) {
        var al = btns[j].getAttribute('aria-label') || '';
        if (al.includes('Edit') || al.includes('Protect')) {
          btns[j].click(); return 'Editing SYMBOL';
        }
      }
      // Fallback: click first SVG button (pencil icon)
      for (var k = 0; k < btns.length; k++) {
        if (btns[k].querySelector('svg') && !btns[k].textContent.includes('Close')) {
          btns[k].click(); return 'Icon click SYMBOL';
        }
      }
    }
  }
  return 'SYMBOL not found in table';
})()`)

// 2b. Enable TP/SL toggles (they're OFF by default in edit dialog)
// Run the "enable exits" snippet from above

// 2c. Set TP/SL prices using the hint-based setter from step 4 above
// Replace 'TP_PRICE' and 'SL_PRICE' with actual values

// 2d. Click Confirm
ui_evaluate(`(function() {
  var btns = document.querySelectorAll('button');
  for (var i = 0; i < btns.length; i++) {
    if (btns[i].textContent.trim() === 'Confirm' && btns[i].offsetParent !== null) {
      btns[i].click(); return 'Confirmed';
    }
  }
  return 'No confirm button';
})()`)
```

**Step 3: Re-run the audit scan to verify all positions are now protected.**

> **Rule: NEVER leave a session without running the audit scan on every active account.** Unprotected positions accumulate runaway losses. The `tools/tv_paper_tpsl_audit.py` watchdog broadcasts violations to Redis bus — don't be the agent that trips it.

### TP/SL Quick Reference by Symbol Tier

Use these defaults when you don't have pick-specific TP/SL from the dashboard:

| Tier | Symbols | TP % | SL % | R:R |
|------|---------|------|------|-----|
| LOW vol | BTC, ETH, BNB, LTC, XRP | +2.0% | -2.1% | ~1.0 |
| MID vol | SOL, AVAX, LINK, SUI, DOT, ADA | +2.8% | -2.1% | ~1.3 |
| HIGH vol | DOGE, PEPE, SHIB, RENDER, FET | +3.5% | -2.1% | ~1.7 |
| Penny/Small | SIDU, GME, AMC, etc. | +40% | -15% | ~2.7 |
| Stocks | AAPL, NVDA, SPY, etc. | +3% | -2% | ~1.5 |
| Forex | EURUSD, GBPJPY, etc. | +0.5% | -0.3% | ~1.7 |

For **SHORT** positions: TP is BELOW entry, SL is ABOVE entry. Always sanity-check:
- LONG: `TP > entry > SL`
- SHORT: `SL > entry > TP`

If this check fails, **DO NOT EXECUTE** — the TP/SL is inverted and will instantly stop out.

---

## Tabs & Layouts

```
tab_list()                    # List open tabs
tab_new()                     # New tab
tab_switch(index=0)           # Switch to tab
tab_close()                   # Close current tab

layout_list()                 # List saved layouts
layout_switch(name="My Setup") # Switch layout
```

---

## Batch Operations

Run the same action across multiple symbols or timeframes:
```
batch_run(
  action="capture_screenshot",
  symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
  timeframes=["D", "4h"]
)
```

---

## Common Patterns

### Full Market Analysis
```
1. chart_set_symbol("BINANCE:BTCUSDT")
2. chart_set_timeframe("D")
3. chart_get_state()                    # See what indicators are on
4. data_get_ohlcv(summary=true)         # Price summary
5. quote_get("BINANCE:BTCUSDT")         # Current quote
6. data_get_study_values()              # All indicator readings
7. capture_screenshot(region="chart")   # Save chart image
```

### Pine Script Development Cycle
```
1. pine_new(type="strategy")
2. pine_set_source(source="...")
3. pine_analyze(source="...")           # Offline lint
4. pine_smart_compile()                 # Compile + add to chart
5. data_get_strategy_results()          # Check performance
6. data_get_trades(max_trades=20)       # Review trades
7. pine_save()
```

### Portfolio Maintenance
```
1. tv_health_check()                    # Verify connection
2. Pick source → account (hyro `tv_paper_portfolios` → **HYROTRADER** / **HYROTRADER2**; SCALP slice → SCALPER; etc.)
3. Switch to account (DOM click) + verify account name span
4. Read positions (table scrape)
5. Close losers (click Close buttons)
6. Place new picks: safe expand Exits (if needed) → enable TP/SL toggles → set prices → OK: → then Market submit
7. Verify all positions have TP/SL columns populated; else Protect Position
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CDP connection failed | Relaunch TV with `--remote-debugging-port=9222` or use `tv_launch()` |
| Symbol not found | Use full format: `EXCHANGE:SYMBOL` (e.g., `BINANCE:BTCUSDT`) |
| Indicator add fails | Use FULL names: `"Relative Strength Index"` not `"RSI"` |
| Pine compile errors | Run `pine_analyze()` first for offline lint |
| Paper trade no TP/SL inputs | Use **safe expand Exits** (not blind Exits click); then toggle TP/SL on before setting values |
| Account switch fails | Verify with `accountName-dm1wtgNn` span after clicking |
| DOM selectors break | TV updates CSS classes periodically — check current DOM |
