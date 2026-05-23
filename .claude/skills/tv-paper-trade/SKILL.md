---
name: tv-paper-trade
description: Use when placing trades on TradingView paper trading portfolios, switching between accounts (SCALPER, TESTER, TRUSTOURSCORE, zerounderscore, BROKIE), or managing paper trading positions. Aliases - tvtrade, papertrade, place-picks
---

# TradingView Paper Trading Skill

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

Place, close, and manage positions across 5 paper trading portfolios via TradingView MCP.

## Portfolio Definitions

| Portfolio | Balance | Theme | SL Rule | TP Rule |
|-----------|---------|-------|---------|---------|
| SCALPER | ~$2K | Momentum scalps, cut losers fast | 0.5x ATR | 1.5x ATR (3:1 R:R) |
| TESTER | ~$3K | Experimental strategies, SHORT bias | 1x ATR | 1.5x ATR |
| TRUSTOURSCORE | ~$90K | Verified alpha, highest conviction only | 1x ATR | 2x ATR |
| BROKIE | ~$1K | Low-risk proven, always set TP/SL | 0.75x ATR | 1.5x ATR |
| zerounderscore | ~$100K | Diversified smart picks, balanced L/S | 1x ATR | 2x ATR |

## CRITICAL: Account Switching (DOM click — reliable)

**DO NOT use mouse coordinates** — row y-positions shift with scroll/window size. Use DOM:

### Step 1: Open dropdown
A bare `.click()` no longer opens it on TV 3.1.0.7818 — dispatch the full
pointer-event sequence:
```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var b=document.querySelector('button.dropdownButton-dm1wtgNn');
  if(!b)return 'nobtn';
  var r=b.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2;
  ['pointerover','pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
    var ev=t.indexOf('pointer')===0
      ?new PointerEvent(t,{bubbles:true,cancelable:true,clientX:cx,clientY:cy,pointerId:1})
      :new MouseEvent(t,{bubbles:true,cancelable:true,clientX:cx,clientY:cy});
    b.dispatchEvent(ev);
  });
  return 'opened';
})()`)
```

### Step 2: Click target account row by exact text
```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  // Hash-agnostic: TV rotates the class hash (was middle-RDCgMoEQ,
  // now middle-fY6nuScj on 3.1.0.7818). Match by stable class prefixes.
  var divs = document.querySelectorAll('div[class*="middle-"][class*="hasTitle-"]');
  for (var i=0; i<divs.length; i++) {
    if (divs[i].textContent.trim() === 'TARGET_NAME') { divs[i].click(); return 'clicked'; }
  }
  return 'not found';
})()`)
```
Replace `TARGET_NAME` with exact row text (no "USD" suffix): `THEWINNERS`, `SCALPER`, `TESTER`, `TRUSTOURSCORE`, `BROKIE`, or `zerounderscore`.

### Step 3: VERIFY (MANDATORY)
```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`document.querySelector('span.accountName-dm1wtgNn').textContent.trim()`)
```
Returned string must match target. If not, repeat steps 1-2.

**NEVER place a trade without verifying the account name first.**

## Swarm Tier Gate (M-010 Phase 2 — MANDATORY for swarm picks)

**When placing a pick that originates from `audit_dashboard/data/swarm_picks.json`,
always run the tier gate FIRST.** Only eligible picks (≥strong tier by default) may
be submitted for paper trading.

```bash
# Preview eligible picks (prints JSON to stdout):
python tools/swarm/get_eligible_picks.py --open-only --summary

# Get full eligible list:
python tools/swarm/get_eligible_picks.py --open-only --out-file /tmp/eligible.json
```

- **`strong` tier (default):** ≥66% model agreement, ≥3 models voted.
- **`unanimous` tier:** ≥95% model agreement, ≥3 models voted (highest conviction only).
- **`moderate` tier:** ≥50% agreement, ≥2 models (allowed if min_tier lowered explicitly).
- Kill-switch: `SWARM_TIER_GATE_ENABLED=0` → all picks pass (testing only).

Picks that fail the tier gate **must not be placed**. Document the blocked pick_id in
the session journal with the reason `m010_tier_gate_blocked`.

For non-swarm picks (manually selected, non-swarm-picks.json source), this gate does
not apply. Proceed directly to Step 1.

## Placing a Trade

### Step 1: Set Symbol
```
mcp__tradingview-desktop__chart_set_symbol(symbol="BINANCE:BTCUSDT")
```

### Step 1.5: PCG-5 PORTFOLIO-CONSTRUCTION GATE CHECK (NEW — 2026-05-12, shadow-mode default)

Before any side-control click, run the pick through `audit_trail/portfolio_gates.py::evaluate_pick()`. Verdict actions:

- `APPROVE` — proceed normally
- `APPROVE_HALF` — Gate 5 demoted the class to `risk_on_beta`; halve the size (`pick.qty *= 0.5`) then proceed
- `NET` — opposite-direction position on another account; close that first then re-evaluate
- `REJECT` — STOP. Document the rejection rationale in the trade journal. Do not place the trade.

Shadow mode (`PCG5_ENFORCE=0`, default): caller logs the verdict via `evaluate_pick` (auto-writes to `audit_dashboard/data/pcg5_log.json`) but is FREE to ignore. Phase 2 (after 7d shadow + acceptance gate clears): switch to `PCG5_ENFORCE=1` and respect REJECT.

Required pick fields for evaluator: `pick_id, account, symbol, direction, asset_class, size_usd`. Optional but recommended: `thesis_catalyst` (Gate 1 catalyst override), `unrealized_pnl_pct` per-position (Gate 4), `sl_at_breakeven/partial_close_done/trailing_stop_armed` flags.

```python
from audit_trail.portfolio_gates import evaluate_pick
v = evaluate_pick(my_pick, all_positions=cross_account_positions)
# Honor v["action"]: APPROVE / APPROVE_HALF / NET / REJECT
```

5 gates run: REGIME_DIRECTIONAL (Gate 1), CROSS_ACCOUNT_NET_POSITION (Gate 2), CONCENTRATION_REJECT (Gate 3), PROFIT_LOCK_SCAN (Gate 4), CROSS_CLASS_CORRELATION_DEMOTE (Gate 5). Full spec: `DAILY_IDEAS.MD` 2026-05-12 PCG-5 entry.

**Canonical PCG-5 implementation (2026-05-15):** `audit_trail/pcg5_gates.py` — `passes_pcg5_gate()`. Shadow mode active (`PCG5_SHADOW_MODE=1`). Log: `audit_dashboard/data/pcg5_log.json`. Activate live mode: `PCG5_SHADOW_MODE=0` after 30-day observation confirms gate logic is sound.

### Step 2: Set Order Type to Market
```
mcp__tradingview-desktop__ui_click(by="text", value="Market")
```

### Step 3: Set Direction
```javascript
// For LONG:
mcp__tradingview-desktop__ui_click(by="data-name", value="side-control-buy")
// For SHORT:
mcp__tradingview-desktop__ui_click(by="data-name", value="side-control-sell")
```

### Step 4: Set TP and SL via JavaScript — **HARD BLOCKER**
The order panel has 4 visible non-quantity inputs WHEN TP/SL section is expanded:
- visible[0] = TP ticks/points (ignore)
- visible[1] = TP price (SET THIS)
- visible[2] = SL ticks/points (ignore)
- visible[3] = SL price (SET THIS)

**CRITICAL:** If the TP/SL section is collapsed, `visible.length` will be 0 or 2 and
this step returns a fail string. **YOU MUST NOT PROCEED TO STEP 5 IF THIS STEP FAILS.**
Many violators on paper accounts came from agents who ignored the fail string and
executed the market order anyway — positions opened with no protection. **DO NOT DO THIS.**

**2026-05-15 observation:** After forcing "Market" tab, some tickets show only **2 visible price inputs** (direct price mode) instead of the classic 4-input ticks structure. In that case the two visible inputs are TP price (index 0) and SL price (index 1). Always count the actual visible non-quantity inputs at runtime before deciding which indices to set.

If the TP/SL inputs aren't visible, EXPAND the Exits panel first:
```
mcp__tradingview-desktop__ui_click(by="text", value="Exits")
// OR look for a toggle with data-name="exits-control-toggle" or "exit-settings-expand"
// OR use the "Limits" tab instead of "Market" if Market view hides TP/SL
```

Then run Step 4:

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function() {
  var nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  var inputs = document.querySelectorAll('input');
  var visible = [];
  for (var i = 0; i < inputs.length; i++) {
    if (inputs[i].offsetParent !== null && inputs[i].id !== 'quantity-field') visible.push(inputs[i]);
  }
  if (visible.length >= 4) {
    visible[1].focus(); nativeSet.call(visible[1], 'TP_PRICE');
    visible[1].dispatchEvent(new Event('input', {bubbles: true}));
    visible[1].dispatchEvent(new Event('change', {bubbles: true}));
    visible[3].focus(); nativeSet.call(visible[3], 'SL_PRICE');
    visible[3].dispatchEvent(new Event('input', {bubbles: true}));
    visible[3].dispatchEvent(new Event('change', {bubbles: true}));
    // Verify values actually landed
    var tp_got = visible[1].value, sl_got = visible[3].value;
    if (String(tp_got) === 'TP_PRICE' && String(sl_got) === 'SL_PRICE') {
      return 'OK: TP=' + tp_got + ' SL=' + sl_got;
    }
    return 'VERIFY_FAIL: tp=' + tp_got + ' sl=' + sl_got;
  }
  return 'BLOCKER_FAIL: only ' + visible.length + ' inputs visible — TP/SL section collapsed. EXPAND Exits panel first, then re-run Step 4. DO NOT PROCEED TO STEP 5.';
})()`)
```

**GATE: Before running Step 5, check that Step 4 returned a string starting with "OK:".
If it returned "BLOCKER_FAIL" or "VERIFY_FAIL", stop and fix the state. NEVER execute
a market order without confirmed TP/SL set.**

**For LONG:** TP must be ABOVE current price, SL must be BELOW.
**For SHORT:** TP must be BELOW current price, SL must be ABOVE.

### Step 4.5: Side-Sanity Gate (MANDATORY — do NOT skip)

After Step 4 returned `OK: TP=X SL=Y`, read the current quote and assert:
- LONG → `tp > entry > sl`. If not, ABORT (do not click Buy/Sell).
- SHORT → `sl > entry > tp`. If not, ABORT (do not click Buy/Sell).

A wrong-side TP/SL fills at market and instantly stops out. Cycle-7 violators
(JTOUSDT/SUIUSDT/OPUSDT/KITEUSDT/BTCUSDT/ADAUSDT/LINKUSDT) were opened because
agents ignored the `BLOCKER_FAIL` string and clicked Buy/Sell anyway.

**`tools/tv_paper_tpsl_audit.py` now runs as a watchdog** — any position you
open without TP/SL (or with inverted TP/SL) is broadcast on the Redis bus
tagged with the time window. Do not be the agent that trips it.

### Step 5: Execute Order — **ONLY if Steps 4 AND 4.5 passed**
```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function() {
  var b = document.querySelectorAll('button');
  for (var i=0;i<b.length;i++) {
    var t = b[i].textContent.trim();
    if ((t.includes('Buy') || t.includes('Sell')) && t.includes('MARKET')) {
      b[i].click(); return 'Executed: ' + t;
    }
  }
  return 'not found';
})()`)
```

### Step 6: Verify Execution — **MANDATORY TP/SL AUDIT**
After execute, read the positions row for the newly-filled pick and **confirm TP and SL
columns are populated**. If either is blank, the trade opened without protection — use
the Protect Position dialog IMMEDIATELY to set them before doing anything else:

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function() {
  var rows = document.querySelectorAll('table tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length >= 10) {
      var sym = cells[0].textContent.trim();
      if (sym === 'BINANCE:SYMBOL_HERE') {
        var tp = cells[4].textContent.trim();
        var sl = cells[5].textContent.trim();
        if (!tp || !sl) {
          return 'VIOLATION: ' + sym + ' opened without TP/SL. Click Protect Position now.';
        }
        return 'OK: TP=' + tp + ' SL=' + sl;
      }
    }
  }
  return 'nf';
})()`)
```

If the audit returns "VIOLATION:", click the `button[data-name="edit-settings-cell-button"]`
on that position's row (or the row itself + the TP/SL cell), fill TP/SL in the Protect Position dialog / side panel, and click **Confirm**.

**Never leave a market order unprotected.** This is a hard rule. Positions without TP/SL
accumulate runaway losses on drawdown.

## Protect an Already-Open Position (VERIFIED 2026-05-15, TV Desktop 3.1.0)

Use this when a position is already filled but the TP/SL columns are empty.
This procedure was verified end-to-end on a live HYROTRADER BTCUSDT Long —
the row went from empty to `Take profit 80,500 / Stop loss 78,000`.

**The #1 trap:** "Protect Position" is **NOT a modal dialog**. It renders
**inline in the right-side trading panel** (the `Exits` section). Querying
`[role="dialog"]` returns nothing — that wasted hours of a peer agent's time.
**The #2 trap:** the TP/SL toggle is a React `input[role="switch"]` —
`.click()` the input ELEMENT directly, never the `switcher-*` / `thumb`
wrapper span (React ignores wrapper events). The price input stays **greyed /
disabled until its toggle is ON** — so toggle BEFORE price, always.

### Step P1 — open the inline Protect panel for that row
```
mcp__tradingview-desktop__ui_click(by="data-name", value="edit-settings-cell-button")
```

### Step P2 — enable BOTH toggles FIRST (before any price)
```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var cb=function(l){var b=[].slice.call(document.querySelectorAll('*')).find(function(e){
    return !e.children.length && e.textContent.trim()===l;});
    for(var i=0;i<6;i++){b=b.parentElement;if(b.querySelector('input[type="checkbox"]'))break;}
    return b.querySelector('input[type="checkbox"]');};
  ['Take profit, price','Stop loss, price'].forEach(function(l){
    var c=cb(l); if(c && !c.checked) c.click();});
  return 'toggles-on';
})()`)
```

### Step P3 — set TP + SL prices via the native setter
LONG: TP above fill, SL below. SHORT: TP below, SL above.
```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var num=function(l){var b=[].slice.call(document.querySelectorAll('*')).find(function(e){
    return !e.children.length && e.textContent.trim()===l;});
    for(var i=0;i<6;i++){b=b.parentElement;
      if([].slice.call(b.querySelectorAll('input')).some(function(i){
        return i.type!=='checkbox'&&i.offsetParent;}))break;}
    return [].slice.call(b.querySelectorAll('input')).find(function(i){
      return i.type!=='checkbox'&&i.offsetParent;});};
  var set=function(i,v){var s=Object.getOwnPropertyDescriptor(
      Object.getPrototypeOf(i),'value').set;
    i.focus();s.call(i,String(v));
    i.dispatchEvent(new Event('input',{bubbles:true}));
    i.dispatchEvent(new Event('change',{bubbles:true}));
    i.dispatchEvent(new KeyboardEvent('keydown',{bubbles:true,key:'Enter'}));
    i.blur();};
  set(num('Take profit, price'), TP_PRICE);
  set(num('Stop loss, price'), SL_PRICE);
  return 'prices-set';
})()`)
```

### Step P4 — Confirm
```
mcp__tradingview-desktop__ui_click(by="data-name", value="place-and-modify-button")
```
(`Discard` is `data-name="button-back"` — do not click that.)

### Step P5 — VERIFY (mandatory)
Re-read the position row (`[data-name="Paper.positions-table"]` → `tr.ka-row`,
columns: Symbol, Side, Qty, AvgFill, TakeProfit, StopLoss, …). The TP and SL
cells MUST now be non-empty. If still empty, repeat P2 (the toggle did not
take) — do NOT trade anything else on that book until protected.

### Protect-Position failure modes

| Failure | Cause | Fix |
|---|---|---|
| `[role="dialog"]` query returns nothing | Protect Position is inline, not modal | Query the right-side trading panel; anchor by `Exits` / label text |
| Toggle won't flip (clicking `switcher-*`/`thumb` span) | React switch ignores wrapper events | `.click()` the `input[role="switch"]` / `input[type="checkbox"]` directly |
| Price input greyed / disabled | Toggle still OFF | Enable the toggle in P2 BEFORE P3 |
| Confirm disabled / price silently dropped on Confirm | Value set without React `input`+`change` events, or toggle off | native-setter + `input`/`change`/Enter dispatch + toggle on |
| No `data-name` on toggles/inputs | TV uses rotating hashed CSS classes | locate by section-label text, walk up to the field block |
| MCP can't connect | TV on 9223, MCP defaults 9222 | `tv_health_check` → `cdp_connected:false` confirms it; CDP matches by `target_url` so this is rare |

## Closing a Position

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function() {
  var rows = document.querySelectorAll('table tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length > 3 && cells[0].textContent.includes('SYMBOL')) {
      var btns = rows[i].querySelectorAll('button');
      for (var j = 0; j < btns.length; j++) {
        if (btns[j].textContent.trim() === 'Close' || btns[j].getAttribute('aria-label') === 'Close') {
          btns[j].click(); return 'Closed SYMBOL';
        }
      }
    }
  }
  return 'not found';
})()`)
```

## Reading Current Positions

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function() {
  var rows = document.querySelectorAll('table tr');
  var positions = [];
  for (var j = 0; j < rows.length; j++) {
    var cells = rows[j].querySelectorAll('td');
    if (cells.length > 5) {
      var sym = cells[0] ? cells[0].textContent.trim() : '';
      if (sym.includes(':')) {
        positions.push(Array.from(cells).map(function(c) { return c.textContent.trim(); }).join(' | '));
      }
    }
  }
  return positions.join('\\n');
})()`)
```

## ATR-Based TP/SL Calculator

Approximate daily ATR percentages for common symbols:
| Symbol | ATR% | 0.5x ATR | 1x ATR | 1.5x ATR | 2x ATR |
|--------|------|----------|--------|----------|--------|
| BTCUSDT | 2.5% | 1.25% | 2.5% | 3.75% | 5.0% |
| ETHUSDT | 3.2% | 1.6% | 3.2% | 4.8% | 6.4% |
| SOLUSDT | 4.1% | 2.05% | 4.1% | 6.15% | 8.2% |
| BNBUSDT | 2.0% | 1.0% | 2.0% | 3.0% | 4.0% |
| XRPUSDT | 3.5% | 1.75% | 3.5% | 5.25% | 7.0% |
| ALGOUSDT | 5.0% | 2.5% | 5.0% | 7.5% | 10.0% |
| AVAXUSDT | 5.0% | 2.5% | 5.0% | 7.5% | 10.0% |
| LINKUSDT | 5.0% | 2.5% | 5.0% | 7.5% | 10.0% |
| DOGEUSDT | 4.0% | 2.0% | 4.0% | 6.0% | 8.0% |
| TRUMPUSDT | 8.0% | 4.0% | 8.0% | 12.0% | 16.0% |

## Scoring Data Integration

Before placing picks, check the scored data from:
- `audit_dashboard/data/dashboard_data.json` — scored active picks
- `alpha_engine/data/smart_picks.json` — curated top picks
- `alpha_engine/data/walkforward_results.json` — strategy validation

Key scoring rules:
- **Confidence 0.75-0.79 = SWEET SPOT** (87.4% WR)
- **Confidence 0.90+ = DANGER** (22.2% WR, overconfident)
- **Trust 6-7 = best tier** (76.9% WR)
- **Trust 1-3 = avoid** (38.0% WR)
- **SHORT outperforms LONG** in BEAR regime (56% vs 49% WR)
- **LONG + conf >= 0.80 = worst combo** (25% WR)

## Position Sizing Justification (MANDATORY)

Every trade MUST include a written justification for its position size BEFORE execution. State:

1. **Size chosen** (e.g., "3% of balance" or "5%")
2. **Why this size** — link it to one or more of: confidence score, trust tier, R:R, regime, correlation with existing positions, portfolio theme, liquidity, or volatility
3. **Deviation reason (if any)** — if you size differently than default for this portfolio, explain why (e.g., "downsized to 2% because SHORT in BEAR regime with low-trust strategy", "upsized to 8% because trust-7 PROVEN tier + 0.77 confidence sweet spot + uncorrelated to book")

Default sizing per portfolio (unless justified otherwise):
- SCALPER: 3-5% (tight stops allow larger % exposure)
- TESTER: 2-4% (experimental = smaller)
- TRUSTOURSCORE: 5-10% (high conviction allowed)
- BROKIE: 5-10% (tiny account, must meaningfully move balance)
- zerounderscore: 2-5% (diversified = smaller per-position)

If you place multiple differently-sized trades in one session, output a summary table with the size and justification for each. No trade goes in without a stated reason.

## DO NOT
- Place trades without verifying account first
- Place trades without stating position-size justification
- Use flat commission - use percentage-based (0.04-0.05%)
- Skip TP/SL on any trade
- Go all LONGs in BEAR regime
- Trust 0.90+ confidence picks blindly
