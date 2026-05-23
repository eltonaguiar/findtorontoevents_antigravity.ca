#!/usr/bin/env python3
"""Place ONE trade on the currently-active TV account via CDP.

Workflow:
  1. Set chart symbol
  2. Set order type (MARKET / LIMIT)
  3. Click Buy / Sell
  4. Set qty + TP/SL in the order panel
  5. SIDE-SANITY GATE — abort if LONG TP <= mid OR SL >= mid (and reverse for SHORT)
  6. Click execute (Buy/Sell ___ MARKET, or Place Order for LIMIT)
  7. For MARKET: open Protect Position dialog, enable toggles, set TP/SL, Confirm
  8. Audit row has TP/SL populated

Usage:
  python tools/tv_place_pick.py --symbol BINANCE:XRPUSDT --side BUY --type MARKET \
      --qty 2100 --tp 1.45 --sl 1.40
  python tools/tv_place_pick.py --symbol NASDAQ:AAPL --side BUY --type LIMIT \
      --qty 11 --limit 268.00 --tp 289.0 --sl 254.0

Requires TV launched with --remote-debugging-port=9222 --remote-allow-origins=*
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

THIS = Path(__file__).resolve()
sys.path.insert(0, str(THIS.parent))
from tv_cdp_runner import evaluate as cdp_eval  # type: ignore


def js(expr: str) -> str:
    res = cdp_eval(expr)
    if "exceptionDetails" in res or "exceptionDetails" in res.get("result", {}):
        raise RuntimeError(json.dumps(res, default=str)[:500])
    inner = res.get("result", {}).get("result", {})
    val = inner.get("value")
    if val is None:
        val = inner.get("description") or inner
    return str(val) if not isinstance(val, (dict, list)) else json.dumps(val)


def set_chart_symbol(sym: str) -> None:
    js("(function(){var b=document.querySelector('button[id=\"header-toolbar-symbol-search\"]');if(b)b.click();return 'opened';})()")
    time.sleep(1)
    expr = (
        "(function(){"
        "var inp=document.querySelector('input.search-lANubSc2');"
        "if(!inp)return 'nf';"
        "var setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
        "inp.focus();setter.call(inp,'" + sym + "');"
        "inp.dispatchEvent(new Event('input',{bubbles:true}));"
        "setTimeout(function(){inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,bubbles:true}));},700);"
        "return 'set';})()"
    )
    js(expr)
    time.sleep(3)


def read_live_mid() -> float | None:
    """Estimate live mid from order panel pre-fill TP/SL placeholders.

    Returns None if can't estimate. The order panel auto-suggests TP/SL near
    current price, so (suggested_tp + suggested_sl) / 2 is a decent live-mid.
    """
    expr = (
        "(function(){"
        "var inputs=document.querySelectorAll('input');"
        "var v=[];for(var i=0;i<inputs.length;i++){if(inputs[i].offsetParent && inputs[i].id!=='quantity-field')v.push(inputs[i]);}"
        "if(v.length<4)return JSON.stringify({err:'not_enough',n:v.length});"
        "return JSON.stringify({tp:v[1].value,sl:v[3].value});"
        "})()"
    )
    raw = js(expr)
    try:
        d = json.loads(raw)
        if "err" in d:
            return None
        tp = float(d["tp"])
        sl = float(d["sl"])
        return (tp + sl) / 2.0
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def setup_order(side: str, order_type: str, qty: float, limit: float | None, tp: float, sl: float) -> str:
    side_data = "side-control-buy" if side == "BUY" else "side-control-sell"
    type_text = "Market" if order_type == "MARKET" else "Limit"
    expr = (
        "(function(){"
        "var setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
        "var all=document.querySelectorAll('button,div[role=\"button\"],span');"
        "for(var i=0;i<all.length;i++){if((all[i].textContent||'').trim()==='" + type_text + "'){all[i].click();break;}}"
        "var sb=document.querySelector('[data-name=\"" + side_data + "\"]');"
        "if(!sb)return 'ERR_NO_SIDE';"
        "sb.click();"
        "var qty=document.querySelector('#quantity-field');"
        "if(!qty)return 'ERR_NO_QTY';"
        "qty.focus();setter.call(qty,'" + str(qty) + "');"
        "qty.dispatchEvent(new Event('input',{bubbles:true}));"
        "qty.dispatchEvent(new Event('change',{bubbles:true}));"
        "var inputs=document.querySelectorAll('input');var v=[];"
        "for(var i=0;i<inputs.length;i++){if(inputs[i].offsetParent!==null && inputs[i].id!=='quantity-field')v.push(inputs[i]);}"
        + (
            "if(v.length<5)return 'BLOCKER_LIMIT_INPUTS:'+v.length;"
            "v[0].focus();setter.call(v[0],'" + str(limit) + "');"
            "v[0].dispatchEvent(new Event('input',{bubbles:true}));"
            "v[0].dispatchEvent(new Event('change',{bubbles:true}));"
            "var tpi=2;var sli=4;"
            if order_type == "LIMIT" else
            "if(v.length<4)return 'BLOCKER_MARKET_INPUTS:'+v.length;"
            "var tpi=1;var sli=3;"
        ) +
        "v[tpi].focus();setter.call(v[tpi],'" + str(tp) + "');"
        "v[tpi].dispatchEvent(new Event('input',{bubbles:true}));"
        "v[tpi].dispatchEvent(new Event('change',{bubbles:true}));"
        "v[sli].focus();setter.call(v[sli],'" + str(sl) + "');"
        "v[sli].dispatchEvent(new Event('input',{bubbles:true}));"
        "v[sli].dispatchEvent(new Event('change',{bubbles:true}));"
        "return 'OK: tp='+v[tpi].value+' sl='+v[sli].value+' qty='+qty.value;"
        "})()"
    )
    return js(expr)


def side_sanity_gate(side: str, tp: float, sl: float, mid: float | None, limit: float | None = None) -> str:
    """Cycle-4 lesson LL2: enforce wrong-side TP/SL detection BEFORE execute.

    For LONG (BUY): TP > entry > SL.
    For SHORT (SELL): SL > entry > TP.

    Uses 'mid' (estimated from order panel placeholders) as proxy for entry.
    For LIMIT orders, also check limit_price is on right side of mid.

    Returns 'OK' if passes, 'BLOCKED: ...' if fails.
    """
    if mid is None:
        return "OK_SKIP_NO_MID"
    if side == "BUY":
        if not (tp > mid > sl):
            return f"BLOCKED: LONG side-sanity fail — need tp>mid>sl, got tp={tp} mid={mid} sl={sl}"
        if limit is not None and limit > mid * 1.5:
            return f"BLOCKED: LIMIT BUY price {limit} >> mid {mid} (>50% above) — likely stale"
    else:  # SELL
        if not (sl > mid > tp):
            return f"BLOCKED: SHORT side-sanity fail — need sl>mid>tp, got tp={tp} mid={mid} sl={sl}"
        if limit is not None and limit < mid * 0.5:
            return f"BLOCKED: LIMIT SELL price {limit} << mid {mid} (>50% below) — likely stale"
    return "OK"


def execute_market(side: str) -> str:
    label = "Buy" if side == "BUY" else "Sell"
    expr = (
        "(function(){var b=document.querySelectorAll('button');"
        "for(var i=0;i<b.length;i++){var t=(b[i].textContent||'').trim();"
        "if(t.includes('" + label + "')&&t.includes('MARKET')){b[i].click();return 'EXEC:'+t;}}"
        "return 'NF';})()"
    )
    return js(expr)


def execute_limit(side: str) -> str:
    label = "Buy" if side == "BUY" else "Sell"
    expr = (
        "(function(){var b=document.querySelectorAll('button');"
        "for(var i=0;i<b.length;i++){var t=(b[i].textContent||'').trim();"
        "if(t.includes('" + label + "')&&t.includes('LIMIT')){b[i].click();return 'EXEC:'+t;}"
        "if(t==='Place order'||t==='Place Order'){b[i].click();return 'EXEC:'+t;}}"
        "return 'NF';})()"
    )
    return js(expr)


def open_protect(symbol: str) -> str:
    sym_short = symbol.split(":")[-1]
    expr = (
        "(function(){var rows=document.querySelectorAll('table tr');"
        "for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td');"
        "if(c.length>3&&(c[0].textContent||'').includes('" + sym_short + "')){"
        "var btn=rows[i].querySelector('button[data-name=\"edit-settings-cell-button\"]');"
        "if(btn){btn.click();return 'opened';}"
        "}}return 'nf';})()"
    )
    return js(expr)


def fill_protect(tp: float, sl: float) -> str:
    """Cycle-4 lesson LL3: enable toggles via parent span.switcher-fwE97QDf,
    not by clicking the input checkbox directly."""
    expr = (
        "(function(){var setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
        "var inputs=document.querySelectorAll('input');var v=[];"
        "for(var i=0;i<inputs.length;i++){if(inputs[i].offsetParent!==null)v.push(inputs[i]);}"
        "if(v.length<4)return 'fail:'+v.length;"
        # Try parent-span click for toggle (LL3); fall back to direct input click
        "var switchers=[];var spans=document.querySelectorAll('span.switcher-fwE97QDf');"
        "for(var s=0;s<spans.length;s++){if(spans[s].offsetParent!==null)switchers.push(spans[s]);}"
        "if(!v[0].checked){if(switchers[0])switchers[0].click(); else v[0].click();}"
        "if(!v[2].checked){if(switchers[1])switchers[1].click(); else v[2].click();}"
        "v[1].focus();setter.call(v[1],'" + str(tp) + "');"
        "v[1].dispatchEvent(new Event('input',{bubbles:true}));"
        "v[1].dispatchEvent(new Event('change',{bubbles:true}));"
        "v[3].focus();setter.call(v[3],'" + str(sl) + "');"
        "v[3].dispatchEvent(new Event('input',{bubbles:true}));"
        "v[3].dispatchEvent(new Event('change',{bubbles:true}));"
        "return 'TPSL: tp='+v[1].value+' sl='+v[3].value+' tp_on='+v[0].checked+' sl_on='+v[2].checked;"
        "})()"
    )
    return js(expr)


def confirm_protect() -> str:
    expr = (
        "(function(){var b=document.querySelectorAll('button');"
        "for(var i=0;i<b.length;i++){var t=(b[i].textContent||'').trim();"
        "if(t==='Confirm'||t==='Modify'||t==='Save'){b[i].click();return 'click:'+t;}}"
        "return 'nf';})()"
    )
    return js(expr)


def audit_row(symbol: str) -> str:
    sym_short = symbol.split(":")[-1]
    expr = (
        "(function(){var rows=document.querySelectorAll('table tr');"
        "for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td');"
        "if(c.length>=6&&(c[0].textContent||'').includes('" + sym_short + "')){"
        "var tp=c[4]?c[4].textContent.trim():'';"
        "var sl=c[5]?c[5].textContent.trim():'';"
        "if(tp&&sl)return 'OK_AUDIT: tp='+tp+' sl='+sl;"
        "return 'AUDIT_FAIL_NO_TPSL';"
        "}}return 'AUDIT_NF';})()"
    )
    return js(expr)


def verify_account(expected: str) -> str:
    """Cycle-4 lesson LL5: account drift detection.
    Always call before each trade in a multi-account session."""
    actual = js("document.querySelector('span.accountName-dm1wtgNn').textContent.trim()")
    if actual.strip() != expected.strip():
        raise SystemExit(f"ACCOUNT_DRIFT: expected={expected!r} got={actual!r}")
    return actual


def read_fill_price(symbol: str) -> float | None:
    """Read the actual fill price from the Position row for the symbol.

    Cycle-4 LL1: NEAR was placed expecting entry $1.599 but filled at $1.570.
    SL set at $1.55 (designed as -3% of expected $1.599) was actually -1.3%
    of real fill — too tight, stopped out. Reading the actual fill lets us
    apply tp_pct/sl_pct relative to reality, not pre-fill expectation.

    Returns None if the row hasn't materialized yet (caller should retry).
    """
    sym_short = symbol.split(":")[-1]
    expr = (
        "(function(){var rows=document.querySelectorAll('table tr');"
        "for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td');"
        "if(c.length>=4&&(c[0].textContent||'').includes('" + sym_short + "')){"
        "var raw=(c[3]?c[3].textContent.trim():'').replace(/,/g,'');"
        "var f=parseFloat(raw);"
        "if(!isNaN(f)&&f>0)return String(f);"
        "}}return 'NF';})()"
    )
    raw = js(expr)
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def place(symbol: str, side: str, order_type: str, qty: float, tp: float | None, sl: float | None,
          limit: float | None = None, expected_account: str | None = None,
          tp_pct: float | None = None, sl_pct: float | None = None) -> dict:
    """Place a trade. tp/sl can be absolute prices OR pct distances.

    LL1 (2026-05-09): Use tp_pct/sl_pct (e.g. 0.03 for ±3%) to compute TP/SL
    relative to ACTUAL fill price, not pre-fill expected entry. For LIMIT
    orders, --limit is the entry — pct distances apply to that. For MARKET
    orders, fill price is read from Positions table after execute.
    """
    out = {"symbol": symbol, "side": side, "type": order_type}
    if tp_pct is not None or sl_pct is not None:
        print(f"→ {symbol} {side} {order_type} qty={qty} tp_pct={tp_pct} sl_pct={sl_pct}" + (f" limit={limit}" if limit else ""))
    else:
        print(f"→ {symbol} {side} {order_type} qty={qty} tp={tp} sl={sl}" + (f" limit={limit}" if limit else ""))

    if expected_account:
        out["account"] = verify_account(expected_account)

    set_chart_symbol(symbol)
    out["chart_set"] = True

    # LL1: pre-execute TP/SL — used only for the order panel + side-sanity gate.
    # For MARKET orders we'll RECOMPUTE post-fill if pct flags were given.
    pre_mid = None
    pre_tp = tp
    pre_sl = sl
    if (tp_pct is not None or sl_pct is not None):
        # Need a mid to materialize initial TP/SL. Use limit price for LIMIT,
        # else read order panel placeholder.
        if order_type == "LIMIT" and limit is not None:
            pre_mid = limit
        else:
            # Read panel mid placeholders BEFORE first setup_order call
            mid_probe = read_live_mid()
            pre_mid = mid_probe
        if pre_mid is None:
            out["error"] = "pct_mode_no_mid"
            return out
        if side == "BUY":
            if tp_pct is not None:
                pre_tp = round(pre_mid * (1 + tp_pct), 8)
            if sl_pct is not None:
                pre_sl = round(pre_mid * (1 - sl_pct), 8)
        else:  # SELL
            if tp_pct is not None:
                pre_tp = round(pre_mid * (1 - tp_pct), 8)
            if sl_pct is not None:
                pre_sl = round(pre_mid * (1 + sl_pct), 8)
        out["pre_mid"] = pre_mid
        out["pre_tp"] = pre_tp
        out["pre_sl"] = pre_sl

    if pre_tp is None or pre_sl is None:
        out["error"] = "missing_tp_or_sl"
        return out

    setup = setup_order(side, order_type, qty, limit, pre_tp, pre_sl)
    out["setup"] = setup
    if not setup.startswith("OK"):
        out["error"] = "setup_failed"
        return out

    # LL2 — side-sanity gate BEFORE execute
    mid = read_live_mid()
    out["mid"] = mid
    gate = side_sanity_gate(side, pre_tp, pre_sl, mid, limit)
    out["side_sanity"] = gate
    if gate.startswith("BLOCKED"):
        out["error"] = "side_sanity_blocked"
        out["status"] = "aborted"
        return out

    exec_res = execute_market(side) if order_type == "MARKET" else execute_limit(side)
    out["exec"] = exec_res
    if not exec_res.startswith("EXEC"):
        out["error"] = "exec_failed"
        return out
    time.sleep(2.5)

    # MARKET orders: audit + fix via Protect dialog. LIMIT orders carry TP/SL with the order.
    if order_type == "LIMIT":
        out["status"] = "complete_limit"
        return out

    # LL1: read ACTUAL fill price + recompute TP/SL from pct distances if given.
    fill_price = read_fill_price(symbol)
    out["fill_price"] = fill_price
    final_tp = pre_tp
    final_sl = pre_sl
    if fill_price is not None and (tp_pct is not None or sl_pct is not None):
        if side == "BUY":
            if tp_pct is not None:
                final_tp = round(fill_price * (1 + tp_pct), 8)
            if sl_pct is not None:
                final_sl = round(fill_price * (1 - sl_pct), 8)
        else:
            if tp_pct is not None:
                final_tp = round(fill_price * (1 - tp_pct), 8)
            if sl_pct is not None:
                final_sl = round(fill_price * (1 + sl_pct), 8)
        out["final_tp"] = final_tp
        out["final_sl"] = final_sl
        if (pre_tp != final_tp) or (pre_sl != final_sl):
            print(f"   LL1 fill-relative recompute: pre tp={pre_tp} sl={pre_sl} → fill={fill_price} → final tp={final_tp} sl={final_sl}")

    audit = audit_row(symbol)
    out["audit_pre_protect"] = audit
    # If pct-mode AND pre/final differ, ALWAYS go through Protect to apply final.
    pct_recompute_needed = (
        (tp_pct is not None or sl_pct is not None)
        and (final_tp != pre_tp or final_sl != pre_sl)
    )
    if audit.startswith("OK_AUDIT") and not pct_recompute_needed:
        out["status"] = "complete"
        return out

    if pct_recompute_needed:
        print(f"   pct-mode: applying fill-relative TP/SL via Protect dialog")
    else:
        print(f"   audit needs protect: {audit}")
    op = open_protect(symbol)
    out["open_protect"] = op
    if op != "opened":
        out["error"] = "protect_open_failed"
        return out
    time.sleep(1)

    fp = fill_protect(final_tp, final_sl)
    out["fill_protect"] = fp

    cp = confirm_protect()
    out["confirm_protect"] = cp
    time.sleep(2)

    final = audit_row(symbol)
    out["audit_final"] = final
    out["status"] = "complete" if final.startswith("OK_AUDIT") else "audit_failed"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--side", required=True, choices=["BUY", "SELL"])
    ap.add_argument("--type", required=True, choices=["MARKET", "LIMIT"], dest="order_type")
    ap.add_argument("--qty", required=True, type=float)
    ap.add_argument("--limit", type=float)
    ap.add_argument("--tp", type=float, help="Absolute TP price (use this OR --tp-pct)")
    ap.add_argument("--sl", type=float, help="Absolute SL price (use this OR --sl-pct)")
    ap.add_argument("--tp-pct", type=float, dest="tp_pct",
                    help="LL1: TP as fractional distance from fill (e.g. 0.03 = +3%% LONG / -3%% SHORT). For MARKET orders, applied to actual fill price post-execute, not pre-fill expected entry.")
    ap.add_argument("--sl-pct", type=float, dest="sl_pct",
                    help="LL1: SL as fractional distance from fill (e.g. 0.02 = -2%% LONG / +2%% SHORT). Same fill-relative semantics.")
    ap.add_argument("--expected-account", help="Verify this account is active before trade (LL5)")
    args = ap.parse_args()

    if args.tp is None and args.tp_pct is None:
        ap.error("Must provide --tp or --tp-pct")
    if args.sl is None and args.sl_pct is None:
        ap.error("Must provide --sl or --sl-pct")

    result = place(args.symbol, args.side, args.order_type, args.qty,
                   args.tp, args.sl, args.limit, args.expected_account,
                   tp_pct=args.tp_pct, sl_pct=args.sl_pct)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
