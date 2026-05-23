---
name: tv-account-switch
description: Switch between TradingView paper portfolios reliably using DOM index-click (NOT text-match, which has substring collisions on this user's account names). Verifies the post-switch account name, handles the dropdown's between-call auto-close, and warns when the user has manually clicked into a different account. Aliases — tv-switch, tv-account, tv-pick-acct.
---

# tv-account-switch

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

The user has ~13 paper portfolios with overlapping name substrings (`HIGHFWWRABV55_SCOREABOVE50`, `…_V2`, `…_V3`, `…_V4`). Text-match clicks pick the wrong row. Use DOM index instead.

## When to use

- Any workflow that operates on a specific paper account.
- After `tv-cdp-launch` returned green.
- Before reading positions, placing trades, or closing positions.

## Hard rules

1. **Never assume the current account.** Read `span.accountName-dm1wtgNn` before AND after every switch.
2. **Never trust text-match for the click.** Use index from a freshly-enumerated dropdown.
3. **Two MCP eval calls do not share dropdown state.** Each `ui_evaluate` is a fresh Runtime context; the dropdown auto-closes when focus shifts. Sequence: enumerate-in-one-eval → click-in-next-eval. Don't insert a third eval between them.
4. **The user can switch the account manually.** After any user message, re-verify before trading.

## Step 1 — Install helpers (once per page load)

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  window.__curAcct = function(){
    return document.querySelector('span.accountName-dm1wtgNn')?.textContent.trim() || '';
  };
  // The dropdown opens ONLY on a full pointer-event sequence — a bare
  // .click() stopped working on TV 3.1.0.7818 (verified 2026-05-17).
  window.__openDD = function(){
    var b = document.querySelector('button.dropdownButton-dm1wtgNn');
    if (!b) return 'nobtn';
    var r = b.getBoundingClientRect(), cx = r.left+r.width/2, cy = r.top+r.height/2;
    ['pointerover','pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){
      var ev = t.indexOf('pointer')===0
        ? new PointerEvent(t,{bubbles:true,cancelable:true,clientX:cx,clientY:cy,pointerId:1})
        : new MouseEvent(t,{bubbles:true,cancelable:true,clientX:cx,clientY:cy});
      b.dispatchEvent(ev);
    });
    return 'opened';
  };
  // Account-row class is a rotating hash (RDCgMoEQ -> fY6nuScj on 3.1.0.7818).
  // Match hash-agnostically so the skill survives the next TV version bump.
  window.__acctRowSel = 'div[class*="middle-"][class*="hasTitle-"]';
  window.__listAccts = function(){
    var divs = document.querySelectorAll(window.__acctRowSel);
    var out = [];
    divs.forEach((d,i)=>out.push({i, txt: d.textContent.trim()}));
    return out;
  };
  window.__pickIdx = function(idx){
    var divs = document.querySelectorAll(window.__acctRowSel);
    if (idx >= divs.length) return 'oob:' + divs.length;
    divs[idx].click();
    return 'clicked:' + divs[idx].textContent.trim();
  };
  return 'helpers ready';
})()`)
```

**Selector note (2026-05-17):** TV rotates the hashed CSS class on the account
rows — it was `div.middle-RDCgMoEQ.hasTitle-RDCgMoEQ`, now
`div.middle-fY6nuScj.hasTitle-fY6nuScj` on 3.1.0.7818. The helpers above match
`div[class*="middle-"][class*="hasTitle-"]` so they do not break on the next
bump. Also: the dropdown no longer opens on a bare `.click()` — `__openDD`
dispatches the full `pointerdown→mousedown→mouseup→click` sequence.

## Step 2 — Enumerate accounts

Open the dropdown and read the row list. The dropdown closes between MCP calls, so the read must be the very next eval.

Call 1 (use the `__openDD` helper — bare `.click()` no longer opens it):
```javascript
ui_evaluate(expression=`window.__openDD()`)
```

Call 2 (immediately after):
```javascript
ui_evaluate(expression=`(function(){var d=document.querySelectorAll('div[class*="middle-"][class*="hasTitle-"]');return JSON.stringify(Array.from(d).map((x,i)=>({i, txt:x.textContent.trim()})));})()`)
```

You get something like:
```
[{"i":0,"txt":"HIGHFWWRABV55_SCOREABOVE50_V3"},
 {"i":1,"txt":"HIGHFWWRABV55_SCOREABOVE50_V2"},
 {"i":2,"txt":"_MANUALBROKIE_CONV_TRUST6p4"},
 {"i":3,"txt":"__VERIFIEDALPHA"},
 ...
 {"i":10,"txt":"The Leap CryptoTradingView"},
 ...]
```

The last row is `Create account…` — skip it. `The Leap Crypto` is a TV-native account with a badge appended (`TradingView`) — also skip unless explicitly requested.

**Watch for invisible prefix differences.** `_MANUALBROKIE_CONV_TRUST6p4` has ONE underscore; `__VERIFIEDALPHA` has TWO. The user's reminder list often types both as `__…` — trust the DOM enumeration, not the user's message.

## Step 3 — Click by index

Re-open + click in two sequential calls. **Do not insert any other call between** — the dropdown will close.

Call 1:
```javascript
ui_evaluate(expression=`window.__openDD()`)
```

Call 2 (or just `window.__pickIdx(8)` if helpers are installed):
```javascript
ui_evaluate(expression=`(function(){var d=document.querySelectorAll('div[class*="middle-"][class*="hasTitle-"]');d[8].click();return 'clicked:'+d[8].textContent.trim();})()`)
```

Expected return: `clicked:<target name>`. If you get `Cannot read properties of undefined (reading 'click')`, the dropdown closed between calls — retry.

## Step 4 — Wait + verify (MANDATORY)

```bash
sleep 4    # account-switch animation + table refresh
```

```javascript
ui_evaluate(expression=`document.querySelector('span.accountName-dm1wtgNn')?.textContent.trim()`)
```

The returned string MUST equal the target. If not, repeat Step 3. Never proceed to position reads, trades, or closes without this match.

## Step 5 — Trade or read

You can now call `tv-positions-read`, `tv-paper-trade`, or `tv-close-positions` for this account.

## Anti-patterns (do NOT do these)

| Anti-pattern | Why it fails |
|---|---|
| `ui_click(by="text", value="HIGHFWWRABV55_SCOREABOVE50_V3")` | Matches the first row containing that substring — picks V2 or V4 if listed first |
| Single eval that opens dropdown, waits 500ms, then clicks | The Promise/setTimeout return value isn't awaited by MCP; result `{}` |
| Skipping the post-switch verify | Account-drift causes trades on the wrong portfolio (production outage 2026-05-09 — `feedback_tv_cdp_orchestrator_lessons_2026-05-09.md`) |
| Hard-coding indexes from memory | Order shifts when user adds/removes accounts. Always re-enumerate before clicking |

## Companion skills

- `tv-cdp-launch` — pre-flight
- `tv-positions-read` — what to call after the verified switch
- `tv-paper-trade` — placing orders (existing skill)
- `tv-close-positions` — bulk close
