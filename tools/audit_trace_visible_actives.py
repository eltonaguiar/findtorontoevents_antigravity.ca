#!/usr/bin/env python3
"""
Replay audit_dashboard/template.html visibility logic EXACTLY on dashboard_data.json.

Shows per-step drop counts and (optional) which pick ids/symbols were removed.
Uses live HTTP prices (ExchangeRate-API + Binance + local stock_prices.json) to
mirror refreshLivePrices() _resolved_live TP/SL tagging.

Usage:
  python tools/audit_trace_visible_actives.py
  python tools/audit_trace_visible_actives.py path/to/dashboard_data.json
"""
from __future__ import annotations

import copy
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
STOCK_JSON = ROOT / "audit_dashboard" / "data" / "stock_prices.json"

# audit_dashboard/template.html BLOCKED_SYSTEMS (exact match, lowercased)
BLOCKED_SYSTEMS = {
    "mercury2_fast",
    "kimi_signal_tracking",
    "ml_bg_system_a",
    "ml_bg_system_b",
    "ml_crypto_pred_v12",
    "crypto_winners",
    "ml_bg_system_c",
    "ml_bg_ensemble",
    "signal_validation",
    "ml_bg_system_f",
    "quan_engine_scalp",
    "quan_engine_swing",
    "futures_ema_stack_momentum",
}

COMMODITY_MAP = {
    "XAGUSDT": {"base": "XAG", "quote": "USD"},
    "XAUUSDT": {"base": "XAU", "quote": "USD"},
    "XPTUSDT": {"base": "XPT", "quote": "USD"},
    "XPDUSDT": {"base": "XPD", "quote": "USD"},
}

KNOWN_STOCKS = {
    "SPY", "QQQ", "AAPL", "NVDA", "MSFT", "AMZN", "GOOG", "GOOGL", "META", "TSLA",
    "AMD", "AVGO", "ADBE", "CRM", "CSCO", "ORCL", "IBM", "NFLX", "JPM", "BAC", "WFC",
    "GS", "MS", "SCHW", "V", "MA", "JNJ", "PFE", "UNH", "LLY", "MRK", "ABBV", "XOM",
    "CVX", "COP", "SLB", "XLE", "HD", "WMT", "MCD", "NKE", "COST", "KO", "PEP", "PG",
    "DIS", "UBER", "CAT", "BA", "RTX", "GE", "HON", "LIN", "UPS", "NEE", "SO", "PLD",
    "AMT", "GLD", "SLV", "IWM", "HYG", "XLF", "SOXX", "NIO", "AMC", "RIOT", "COIN", "BB",
    "GC", "HG", "SI", "ZN", "YM",
}


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _is_blocked(name: str) -> bool:
    return (name or "").lower().strip() in BLOCKED_SYSTEMS


def _is_non_crypto_ac(ac: str) -> bool:
    u = (ac or "").upper()
    return u in ("FOREX", "EQUITY", "COMMODITY", "FUTURES", "BOND", "ETF")


def recompute_age_hours(pick: dict, now_ms: float) -> None:
    ts = pick.get("timestamp") or pick.get("created_at") or ""
    if not ts:
        return
    s = str(ts).strip()
    if not s.endswith("Z") and not any(x in s for x in ("+", "-")) and len(s) >= 16:
        s += "Z"
    try:
        # fromisoformat: replace Z
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ms = dt.timestamp() * 1000
        pick["age_hours"] = max(0.0, (now_ms - ms) / 3600000.0)
    except Exception:
        pass


def is_resolved_pick(p: dict) -> bool:
    rl = str(p.get("_resolved_live") or "").upper()
    st = str(p.get("status") or "").upper()
    oc = str(p.get("outcome") or "").upper()
    return rl in ("TP_HIT", "SL_HIT") or st in ("TP_HIT", "SL_HIT") or oc in ("TP_HIT", "SL_HIT")


def is_tp_hit_pick(p: dict) -> bool:
    rl = str(p.get("_resolved_live") or "").upper()
    st = str(p.get("status") or "").upper()
    oc = str(p.get("outcome") or "").upper()
    return rl == "TP_HIT" or st == "TP_HIT" or oc == "TP_HIT"


def normalize_crypto_sym(raw: str) -> tuple[str, float]:
    sym = raw.replace("-", "")
    mult = 1.0
    if len(sym) >= 2 and sym[0] == "k" and sym[1].isupper():
        sym = sym[1:]
        mult = 1000.0
    if len(sym) >= 5 and sym[0] == "K" and sym[1:4].isalpha() and sym.endswith("USDT"):
        if not sym.startswith("KAS") and not sym.startswith("KDA"):
            sym = sym[1:]
            mult = 1000.0
    if sym.startswith("1000"):
        sym = sym[4:]
        mult = 1000.0
    sym = sym.replace("_", "")
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym += "USDT"
    return sym, mult


def fetch_usd_rates() -> dict[str, float]:
    """Match template ExchangeRate-API parse: 1 unit currency = X USD."""
    url = "https://open.er-api.com/v6/latest/USD"
    with urllib.request.urlopen(url, timeout=15) as r:
        d = json.loads(r.read().decode())
    rates = d.get("rates") or {}
    m: dict[str, float] = {"USD": 1.0}
    for cur, rate in rates.items():
        if rate and rate > 0:
            m[cur] = 1.0 / float(rate)
    return m


def fetch_binance_prices(symbols: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for sym in symbols:
        try:
            q = urllib.parse.quote(sym)
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={q}"
            with urllib.request.urlopen(url, timeout=10) as r:
                row = json.loads(r.read().decode())
            out[sym] = float(row["price"])
        except Exception:
            pass
    return out


def apply_forex_resolved(picks: list[dict], usd_rates: dict[str, float]) -> int:
    """Mutate picks: set _resolved_live for =X and COMMODITY_MAP symbols. Returns count updated."""
    updated = 0
    for p in picks:
        sym = p.get("symbol") or ""
        if "=X" not in sym and sym not in COMMODITY_MAP:
            continue
        if sym in COMMODITY_MAP:
            pair = COMMODITY_MAP[sym]
        else:
            core = sym.replace("=X", "")
            if len(core) != 6:
                continue
            pair = {"base": core[:3], "quote": core[3:6]}
        br = usd_rates.get(pair["base"])
        qr = usd_rates.get(pair["quote"])
        if not br or not qr:
            continue
        live_price = br / qr
        entry = _f(p.get("entry_price"))
        if entry <= 0 or live_price <= 0:
            continue
        tp = _f(p.get("take_profit"))
        sl = _f(p.get("stop_loss"))
        direction = str(p.get("direction") or p.get("signal_type") or "").upper()
        is_short = direction in ("SHORT", "SELL")
        if is_short:
            p["pnl_pct"] = round((entry - live_price) / entry * 100, 4)
        else:
            p["pnl_pct"] = round((live_price - entry) / entry * 100, 4)
        if tp and entry:
            if is_short:
                if live_price <= tp * 1.001:
                    p["_resolved_live"] = "TP_HIT"
                elif sl and live_price >= sl * 0.999:
                    p["_resolved_live"] = "SL_HIT"
            else:
                if live_price >= tp * 0.999:
                    p["_resolved_live"] = "TP_HIT"
                elif sl and live_price <= sl * 1.001:
                    p["_resolved_live"] = "SL_HIT"
        updated += 1
    return updated


def load_stock_baked() -> dict[str, float]:
    if not STOCK_JSON.exists():
        return {}
    try:
        data = json.loads(STOCK_JSON.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in (data.get("prices") or {}).items() if float(v) > 0}
    except Exception:
        return {}


def apply_stock_and_server_prices(picks: list[dict], baked: dict[str, float]) -> int:
    """Non-crypto stock path + server current_price loop (template ~2252-2551)."""
    updated = 0
    for p in picks:
        sym = p.get("symbol") or ""
        sym_nf = sym.replace("=F", "")
        if "=X" in sym or sym.endswith("USDT") or sym.endswith("USD") or sym.endswith("-USD"):
            continue
        if str(p.get("asset_class") or "").upper() == "EQUITY" or sym_nf in KNOWN_STOCKS:
            live = baked.get(sym) or baked.get(sym_nf)
            entry = _f(p.get("entry_price"))
            if live and entry > 0:
                is_short = str(p.get("direction") or "").upper() in ("SHORT", "SELL")
                p["pnl_pct"] = round(
                    ((entry - live) / entry * 100) if is_short else ((live - entry) / entry * 100),
                    4,
                )
                tp = _f(p.get("take_profit"))
                sl = _f(p.get("stop_loss"))
                if tp and entry:
                    if is_short:
                        if live <= tp * 1.001:
                            p["_resolved_live"] = "TP_HIT"
                        elif sl and live >= sl * 0.999:
                            p["_resolved_live"] = "SL_HIT"
                    else:
                        if live >= tp * 0.999:
                            p["_resolved_live"] = "TP_HIT"
                        elif sl and live <= sl * 1.001:
                            p["_resolved_live"] = "SL_HIT"
                updated += 1
                continue
        server_price = _f(p.get("current_price"))
        entry = _f(p.get("entry_price"))
        if entry > 0 and server_price > 0 and abs(server_price - entry) / entry >= 0.00001:
            is_short = str(p.get("direction") or "").upper() in ("SHORT", "SELL")
            p["pnl_pct"] = round(
                ((entry - server_price) / entry * 100)
                if is_short
                else ((server_price - entry) / entry * 100),
                4,
            )
            tp = _f(p.get("take_profit"))
            sl = _f(p.get("stop_loss"))
            if tp and entry:
                if is_short:
                    if server_price <= tp * 1.001:
                        p["_resolved_live"] = "TP_HIT"
                    elif sl and server_price >= sl * 0.999:
                        p["_resolved_live"] = "SL_HIT"
                else:
                    if server_price >= tp * 0.999:
                        p["_resolved_live"] = "TP_HIT"
                    elif sl and server_price <= sl * 1.001:
                        p["_resolved_live"] = "SL_HIT"
            updated += 1
    return updated


def apply_crypto_prices(picks: list[dict], price_map: dict[str, float]) -> int:
    updated = 0
    for p in picks:
        raw = p.get("symbol") or ""
        sym = raw
        if COMMODITY_MAP.get(sym):
            continue
        if not (
            sym.endswith("USDT")
            or sym.endswith("USD")
            or sym.endswith("-USD")
            or (str(raw).startswith("1000"))
            or (len(raw) > 1 and raw[0] == "k" and raw[1].isupper())
            or str(p.get("asset_class") or "").upper() == "CRYPTO"
        ):
            continue
        api_sym, mult = normalize_crypto_sym(raw)
        raw_price = price_map.get(api_sym)
        if raw_price is None:
            for alt in (
                api_sym.replace("USD", "USDT"),
                api_sym + "USDT",
                api_sym + "USD",
            ):
                if alt in price_map:
                    raw_price = price_map[alt]
                    break
        if raw_price is None:
            continue
        live_price = float(raw_price) * mult
        entry = _f(p.get("entry_price"))
        if not live_price or not entry:
            continue
        direction = str(p.get("direction") or "").upper()
        if direction == "SHORT":
            p["pnl_pct"] = round((entry - live_price) / entry * 100, 4)
        else:
            p["pnl_pct"] = round((live_price - entry) / entry * 100, 4)
        tp = _f(p.get("take_profit"))
        sl = _f(p.get("stop_loss"))
        if tp and entry:
            if direction == "SHORT":
                if live_price <= tp * 1.001:
                    p["_resolved_live"] = "TP_HIT"
                elif sl and live_price >= sl * 0.999:
                    p["_resolved_live"] = "SL_HIT"
            else:
                if live_price >= tp * 0.999:
                    p["_resolved_live"] = "TP_HIT"
                elif sl and live_price <= sl * 1.001:
                    p["_resolved_live"] = "SL_HIT"
        updated += 1
    return updated


def trace_step(name: str, before: list[dict], after: list[dict]) -> None:
    dropped = [p for p in before if p not in after]
    print(f"  {name}: {len(before)} -> {len(after)}  (removed {len(dropped)})")
    for p in dropped[:25]:
        pid = p.get("id") or p.get("symbol") or "?"
        print(
            f"      - {pid}  sys={p.get('source_system')}  trust={p.get('trust_tier')}  "
            f"_resolved_live={p.get('_resolved_live')}  status={p.get('status')}"
        )
    if len(dropped) > 25:
        print(f"      ... and {len(dropped) - 25} more")


def run_get_base_visible(picks: list[dict], show_all: bool, show_tp_hits: bool) -> list[dict]:
    """Mirror getBaseVisibleActivePicks (includeResolved=False)."""
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    out = [copy.deepcopy(p) for p in picks]
    for p in out:
        recompute_age_hours(p, now_ms)

    before = out[:]
    out = [
        p
        for p in out
        if _f(p.get("entry_price")) > 0 and _f(p.get("entry_price")) <= 1_000_000
    ]
    trace_step("1_entry_sanity (0<entry<=1e6)", before, out)

    if not show_all:
        before = out[:]
        out = [p for p in out if not _is_blocked(str(p.get("source_system") or ""))]
        trace_step("2_blocked_system", before, out)

        before = out[:]
        out = [
            p
            for p in out
            if str(p.get("trust_tier") or "").upper() not in ("BANNED", "UNTRUSTED")
        ]
        trace_step("3_trust_tier BANNED/UNTRUSTED", before, out)

        before = out[:]
        kept = []
        for p in out:
            age = p.get("age_hours")
            if age is None:
                age = 999.0
            pnl = _f(p.get("pnl_pct"))
            max_age = 336.0 if _is_non_crypto_ac(str(p.get("asset_class") or "")) else 48.0
            if age > max_age and abs(pnl) < 1:
                continue
            kept.append(p)
        out = kept
        trace_step("4_stale_flat (age>max_age & |pnl|<1)", before, out)

        before = out[:]
        out = [
            p
            for p in out
            if not (
                str(p.get("source_system") or "").lower() == "rapid_fire"
                and _f(p.get("score")) < 10
            )
        ]
        trace_step("5_rapid_fire score<10", before, out)

    before = out[:]
    kept = []
    for p in out:
        if not is_resolved_pick(p):
            kept.append(p)
            continue
        if show_tp_hits and is_tp_hit_pick(p):
            kept.append(p)
    out = kept
    trace_step("6_hide resolved TP/SL (unless showTpHits for TP only)", before, out)
    return out


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    if not path.exists():
        print("Missing:", path)
        return 1
    print("Loading", path, "...")
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_active = (data.get("picks") or {}).get("active") or []
    print("Raw D.picks.active length:", len(raw_active))
    summary_n = (data.get("summary") or {}).get("total_active_picks")
    if summary_n is not None:
        print("summary.total_active_picks:", summary_n)

    print("\n--- Pipeline A: JSON only (no live _resolved_live mutation) ---\n")
    run_get_base_visible(raw_active, show_all=False, show_tp_hits=False)

    print("\n--- Pipeline B: After live price mutation (same order as refreshLivePrices) ---\n")
    mutated = [copy.deepcopy(p) for p in raw_active]
    # Clear any stale _resolved_live from file for deterministic run
    for p in mutated:
        p.pop("_resolved_live", None)

    print("Fetching USD rates (forex)...")
    usd = fetch_usd_rates()
    n_fx = apply_forex_resolved(mutated, usd)
    print(f"  Forex/commodity picks touched: {n_fx}")

    baked = load_stock_baked()
    n_st = apply_stock_and_server_prices(mutated, baked)
    print(f"  Stock/server-price picks touched: {n_st}")

    crypto_syms = []
    sym_mult = {}
    for p in mutated:
        raw = p.get("symbol") or ""
        if COMMODITY_MAP.get(raw):
            continue
        if not (
            raw.endswith("USDT")
            or raw.endswith("USD")
            or raw.endswith("-USD")
            or str(raw).startswith("1000")
            or (len(raw) > 1 and raw[0] == "k" and raw[1].isupper())
            or str(p.get("asset_class") or "").upper() == "CRYPTO"
        ):
            continue
        api_sym, _ = normalize_crypto_sym(raw)
        if api_sym not in sym_mult:
            sym_mult[api_sym] = []
        sym_mult[api_sym].append(raw)
    crypto_syms = list(sym_mult.keys())
    print(f"Fetching Binance prices for {len(crypto_syms)} symbols...")
    pm = fetch_binance_prices(crypto_syms)
    n_cr = apply_crypto_prices(mutated, pm)
    print(f"  Crypto picks touched: {n_cr}")

    tp_sl = [p for p in mutated if p.get("_resolved_live") in ("TP_HIT", "SL_HIT")]
    print(f"\nPicks tagged _resolved_live TP_HIT or SL_HIT: {len(tp_sl)}")
    for p in tp_sl:
        _pid = p.get("id", "")
        _ids = str(_pid)[:60] if _pid is not None else ""
        print(
            f"  {p.get('symbol')}  {p.get('_resolved_live')}  id={_ids}  "
            f"dir={p.get('direction')} entry={p.get('entry_price')} tp={p.get('take_profit')}"
        )

    print("\n--- Final visibility (after mutation) ---\n")
    run_get_base_visible(mutated, show_all=False, show_tp_hits=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
