---
name: tv-protect-position
description: Attach a Take-Profit and Stop-Loss to an ALREADY-OPEN TradingView Desktop position that filled without protection. Use for "position has empty TP/SL", "Protect Position", "VIOLATION position unprotected", "add TP/SL to open trade". Verified live 2026-05-15. Aliases - tv-protect, protect-position, tv-tpsl, fix-unprotected.
---

# tv-protect-position — TP/SL onto an already-open position

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

When a market order filled but the Positions table shows empty TP/SL columns.
This procedure was verified end-to-end on a live HYROTRADER BTCUSDT Long —
the row went from empty to `Take profit 80,500 / Stop loss 78,000`.

For sending the JS reliably (no quoting errors), use `/tv-eval-bridge`.

## The two traps that waste hours

1. **"Protect Position" is NOT a modal dialog.** It renders **inline in the
   right-side trading panel** (the `Exits` section). Querying `[role="dialog"]`
   returns nothing — stop looking for a modal.
2. **The TP/SL toggle is a React `input[role="switch"]`.** `.click()` the
   input ELEMENT directly — never the `switcher-*` / `thumb` wrapper span
   (React ignores wrapper events). The price input is **greyed/disabled until
   its toggle is ON** — so enable the toggle BEFORE setting the price, always.
   If you `nativeSet` a price while the toggle is off, Confirm silently
   discards it and the row stays empty.

## Procedure (P1–P5)

### P1 — open the inline Protect panel for that row
```
mcp__tradingview-desktop__ui_click(by="data-name", value="edit-settings-cell-button")
```

### P2 — enable BOTH toggles FIRST (before any price)
```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  ['Take profit, price','Stop loss, price'].forEach(function(l){
    var le=[].slice.call(document.querySelectorAll('*')).find(function(e){
      return !e.children.length && e.textContent.trim()===l;});
    if(!le)return; var b=le;
    for(var i=0;i<8;i++){b=b.parentElement;if(!b)break;
      var cb=b.querySelector('input[type=checkbox],input[role=switch]');
      if(cb){if(cb.checked!==true && cb.getAttribute('aria-checked')!=='true')cb.click();return;}}
  }); return 'toggles-on';
})()`)
```

### P3 — set TP + SL prices (the hard part — read this)

TV pre-fills the TP/SL inputs with **tick-based placeholders** (e.g. "75 ticks"
/ "25 ticks" → prices a fraction off entry). Those placeholders are **invalid
or noise-tight** — you MUST overwrite them. A SL placeholder frequently sits
ABOVE the current price on a long → invalid (see the validity rule below).

**The bare `value`-setter does NOT stick on TV's React inputs.** This burned a
peer agent for hours: `Object.getOwnPropertyDescriptor(...).set` + `input`/
`change` events left the placeholders unchanged. TV's controlled inputs
re-render from React state and discard the injected value.

**Use `execCommand('insertText')` — it simulates real typing, React honors it.**
Focus the input, select-all, then `insertText`. Native-setter is the fallback:

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var res=[];
  [{t:'Take profit, price',v:'TP_PRICE'},{t:'Stop loss, price',v:'SL_PRICE'}].forEach(function(it){
    var le=[].slice.call(document.querySelectorAll('*')).find(function(e){
      return !e.children.length && e.textContent.trim()===it.t;});
    if(!le){res.push(it.t+':no-label');return;}
    var b=le,inp=null;
    for(var i=0;i<8;i++){b=b.parentElement;if(!b)break;
      var c=[].slice.call(b.querySelectorAll('input')).filter(function(x){
        return x.type!=='checkbox'&&x.getAttribute('role')!=='switch'&&x.offsetParent!==null;});
      if(c.length){inp=c[0];break;}}
    if(!inp){res.push(it.t+':no-input');return;}
    inp.focus();
    try{inp.select();}catch(e){}
    try{document.execCommand('selectAll',false,null);}catch(e){}
    var ok=false; try{ok=document.execCommand('insertText',false,it.v);}catch(e){}
    if(!ok||inp.value!==it.v){
      var ns=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      ns.call(inp,it.v); inp.dispatchEvent(new Event('input',{bubbles:true}));
    }
    inp.dispatchEvent(new Event('change',{bubbles:true}));
    inp.dispatchEvent(new KeyboardEvent('keydown',{bubbles:true,key:'Enter'}));
    inp.blur();
    res.push(it.t+'='+inp.value);
  });
  return res.join(' | ');
})()`)
```

The return string MUST show your real values (`Take profit, price=... | Stop
loss, price=...`). If it still shows the placeholders, escalate to **real CDP
keystrokes**: `ui_type_text` / `ui_keyboard` — focus the input, `Ctrl+A`, type
the value, `Tab`. CDP keystrokes operate below React and always work.

### P3-validity — SL/TP must be valid vs the CURRENT price, not just entry

TV rejects (red box, Confirm stays disabled):
- **LONG:** `TP > current_price` AND `SL < current_price`.
- **SHORT:** `TP < current_price` AND `SL > current_price`.

It is the **last/market price**, not the fill price. A SL "below entry" can
still be ABOVE the current market on a long — TV rejects it (a stop above
market triggers instantly). Pull a fresh quote (`quote_get`) and place SL/TP
clearly on the correct side with real distance (e.g. 1.5×ATR), never the
tick-placeholder.

### P4 — Confirm (it is DISABLED until the form is valid)

```
mcp__tradingview-desktop__ui_click(by="data-name", value="place-and-modify-button")
```
(`Discard` is `data-name="button-back"` — do not click that.)

**Confirm greyed/disabled is a SYMPTOM, not a click problem.** Clicking a
disabled button does nothing. Confirm enables only when BOTH toggles are ON
AND both prices are valid (P3-validity). If your click "does nothing", do not
retry the click — diagnose: read the Confirm button's `disabled` /
`aria-disabled` state and the current TP/SL field values. If disabled, the
prices are still wrong → fix P3, do not touch P4.

### P5 — VERIFY (mandatory)
Re-read the row (`[data-name="Paper.positions-table"]` → `tr.ka-row`; columns:
Symbol, Side, Qty, AvgFill, TakeProfit, StopLoss, …). TP and SL MUST be
non-empty and match what you set. If still empty, the toggle or the price did
not take — repeat P2/P3. Do NOT trade anything else on that book until the
position is verified protected.

## Side-sanity check (do not skip)

Before P4, assert (using the CURRENT price, see P3-validity):
- LONG → `TP > current_price > SL`
- SHORT → `SL > current_price > TP`

A wrong-side TP/SL fills at market and instantly stops the position out.

## Failure modes

| Failure | Cause | Fix |
|---|---|---|
| `[role="dialog"]` query empty | Protect Position is inline, not modal | query the right-side `Exits` panel; anchor by label text |
| toggle won't flip | clicked the `switcher-*`/`thumb` span | `.click()` the `input[role=switch]` element directly |
| price input greyed/disabled | toggle still OFF | run P2 before P3 |
| **price won't change — field keeps the placeholder** | bare `value`-setter discarded by TV's React-controlled input | use `execCommand('insertText')` (P3), then CDP keystrokes (`ui_type_text`) if needed |
| **SL shows red / invalid** | SL is not on the correct side of the CURRENT price (a long SL above market) | P3-validity: SL `<` current price for long; overwrite the tick-placeholder |
| **Confirm greyed, "can't click it"** | form invalid — disabled button, no click to land | NOT a click bug; fix toggles + valid prices, Confirm auto-enables |
| Confirm leaves row empty | price set with toggle off, or value never actually changed | toggle on first; verify P3 return string shows real values before P4 |
| Exits section collapsed (0-2 inputs) | the Market ticket's `Exits` panel not expanded | click the `Exits` header / `ui click --by text --value Exits` first |
| `ui eval` SyntaxError / quoting error | complex JS through a shell | use `/tv-eval-bridge` (MCP tool direct, or base64) |
| no `data-name` on elements | TV uses rotating hashed CSS classes | locate by section-label text, walk up to the field block |
| field shows "ticks" not price | the `⇄` swap is in tick/offset mode | click the `⇄` icon to switch to price mode before setting |

## The golden rule

A TV position must NEVER sit unprotected. The verified order is fixed:
**P1 open panel → P2 toggles ON → P3 set valid prices (execCommand/keystrokes,
not bare value-setter) → P4 Confirm (auto-enables once valid) → P5 verify.**
You cannot click past a disabled Confirm and you cannot inject a value TV's
React layer ignores — fix the cause, never brute-force the symptom.

## Companion skills

- `/tv-eval-bridge` — run the JS above without quoting errors
- `/tv-paper-trade` — full placement flow (this procedure is also Step 6 there)
- `/tv-positions-read` — read the positions table

---

## Hard Lessons from Live 2026-05-15 HYROTRADER ETHUSDT Protect Session (Grok)

**Context**: This session involved protecting an **already-open** ETHUSDT Long position on the HYROTRADER paper account after a market order was placed without TP/SL (classic violation state). Multiple hours were wasted due to repeated failures in P3 (setting prices).

**As the agent who caused the waste**: I repeatedly assumed the native setter + label-walking logic from this skill would "just work" in the Protect panel. It did not. The user had to intervene multiple times with live UI feedback (red borders, collapsed Exits, wrong-side values, toggles not firing). This was unacceptable.

### Critical Failures & Root Causes

1. **Native setter is unreliable on React inputs in the Protect panel**
   - `Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set` often sets the value visually but does **not** trigger React's `onChange`.
   - Result: JS reports "prices-set" but the fields remain as placeholders or show red validation borders.

2. **Exits panel must be explicitly expanded first (for both new orders and Protect)**
   - If the Exits section is collapsed, the price inputs simply do not exist in the DOM.
   - Uncollapsing it *after* attempting to set prices does nothing for an already-filled position.

3. **Label text is the only stable anchor**
   - The user confirmed the exact labels in the Protect editor are:
     - `"Take profit, price"`
     - `"Stop loss, price"`
   - Never rely on data-name, class hashes, or placeholder text — they rotate or differ between new order ticket vs Protect panel.

4. **Protect on an already-open row requires row-specific targeting first**
   - Generic `edit-settings-cell-button` clicks can fail or target the wrong row.
   - Must first locate the specific symbol row in the Positions table, then click within that row (or its edit control).

5. **WSL direct execution is currently more reliable than PowerShell**
   - Running the Windows `node.exe` directly from WSL bash (`/mnt/c/Program Files/nodejs/node.exe`) avoids the quoting hell that the desktop Grok instance was suffering from.
   - Always prefer this path when the MCP `ui_evaluate` tool is unavailable.

6. **When automation is stuck for hours on a paper trade, manual entry is the correct escape hatch**
   - Claude explicitly authorized: after one more solid attempt, have the human type the numbers and click Confirm (15 seconds). Do not keep looping.

### Working Solution (What Finally Worked)

After P1 (row-targeted open) and P2 (toggles via label walker) succeeded, P3 was solved using:

**`document.execCommand('insertText')` method** (preferred over pure nativeSet):

```js
function setPriceField(labelText, value) {
  var label = [].slice.call(document.querySelectorAll("*"))
    .find(function(e){ return !e.children.length && e.textContent.trim() === labelText; });
  if (!label) return labelText + ":LABEL_NOT_FOUND";

  var container = label;
  for (var i = 0; i < 8; i++) {
    container = container.parentElement;
    if (!container) break;
    var inputs = [].slice.call(container.querySelectorAll("input"))
      .filter(function(inp){ return inp.offsetParent !== null && inp.type !== "checkbox"; });
    if (inputs.length > 0) {
      var input = inputs[0];
      input.focus();
      document.execCommand("selectAll", false, null);
      document.execCommand("insertText", false, value);
      input.dispatchEvent(new Event("input", {bubbles: true}));
      input.dispatchEvent(new Event("change", {bubbles: true}));
      return labelText + ":OK";
    }
  }
  return labelText + ":INPUT_NOT_FOUND";
}
```

Call it for both fields:
- `setPriceField("Take profit, price", "2434")`
- `setPriceField("Stop loss, price", "2114")`

This method simulates real user typing, which React's controlled inputs respect.

### Recommended Updated Protect Flow (for already-open rows)

1. Verify the correct account is active.
2. Locate the specific unprotected row (use the scanner from Claude's 22:12 guidance).
3. Click within that row to open the inline Protect editor (P1 — row-specific).
4. Enable both toggles using the label-walking method (P2).
5. Set prices using the `execCommand('insertText')` method above (P3) — **always use the exact labels** the user confirmed.
6. Click Confirm (`[data-name="place-and-modify-button"]` or button text "Confirm").
7. Immediately re-scan with the unprotected positions scanner.
8. If still `unprotected:true` after one solid attempt with the above method → hand the keyboard to the human.

### When to Give Up and Let the Human Type

- After 2–3 failed attempts with the `execCommand` method.
- When the user has been stuck for hours on a paper trade.
- Per Claude: "one more attempt, then hand-type; don't keep looping."

---

**Bottom line for future agents**:  
This skill's original nativeSet + label walker is a good starting point, but on real React-heavy UIs like TV 3.1.0 Protect panel, you **must** fall back to `document.execCommand('insertText')` (or the MCP `ui_type_text` primitive) and be extremely strict about using the exact visible label text. Assume nothing will "just work."

I wasted hours of the user's time because I treated the original examples as sufficient. They were not. This session should have taken 20–30 minutes, not multiple hours.

— Grok (the retarded agent who had to be yelled at to stop looping)
