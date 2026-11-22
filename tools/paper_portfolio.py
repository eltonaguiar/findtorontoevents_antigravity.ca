#!/usr/bin/env python3
"""Paper portfolio tracker: real quotes, mark-to-market, TP/SL, dated snapshots.

This is PLUMBING, not an edge. No strategy in this repo has passed a promotion
gate, so the P&L this book produces says nothing about future returns. The book
is stamped ``purpose: plumbing_demo_not_validated_edge`` on disk.

What it does that the rest of the repo did not:
  1. marks OPEN positions to market with a real quote,
  2. tracks a cash balance and an equity curve,
  3. writes a committed dated snapshot (paper_portfolio/snapshots/YYYY-MM-DD.json).

What it REUSES (does not rebuild):
  - TP/SL intrabar resolution: ``audit_trail.universal_pick_resolver._check_tp_sl_intrabar``
    (already SL-first / pessimistic: when a bar straddles both levels, the stop wins).
  - the price paths that already work: ccxt for crypto, the on-disk ECB
    ``data/forex_rate_cache`` for FX, yfinance last (Yahoo has 429'd in this repo).

Accounting model (standard, works for long and short):
  - LONG open:  cash -= qty*entry + entry_fee
  - SHORT open: cash += qty*entry - entry_fee
  - LONG close: cash += qty*exit - exit_fee
  - SHORT close: cash -= qty*exit + exit_fee
  - equity = cash + sum(signed market value)   (long +qty*px, short -qty*px)
  - unrealized_pnl is GROSS mark-to-market; unrealized_net subtracts the
    estimated exit fee. Costs are per side, default 10 bp.

Usage:
  python3 tools/paper_portfolio.py --init --cash 10000
  python3 tools/paper_portfolio.py --add BTC/USDT LONG 0.05 --entry 60000 --tp 66000 --sl 57000 --strategy demo
  python3 tools/paper_portfolio.py --mark
  python3 tools/paper_portfolio.py --status
  python3 tools/paper_portfolio.py --mark --json
  python3 tools/paper_portfolio.py --load-from-gate

--load-from-gate is the only mode that can put a NON-demo position in the book.
It reuses the real forward gate (``alpha_engine.audit3_tribunal.forward_gate_block``,
which itself calls ``forward_observations.promotion``) and opens a position ONLY
for a pod that passes it. When nothing passes - the current reality - it REFUSES,
prints a machine-readable refusal, and leaves ``book.json`` byte-identical.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BOOK_DIR = ROOT / "paper_portfolio"
BOOK_FILE = BOOK_DIR / "book.json"
EQUITY_FILE = BOOK_DIR / "equity_curve.jsonl"
SNAP_DIR = BOOK_DIR / "snapshots"
FOREX_CACHE = ROOT / "data" / "forex_rate_cache"
# The three authoritative gate inputs (read-only; this tool never writes them).
MANIFEST = ROOT / "reports" / "audit3_confirmatory.json"
FORWARD_LEDGER = ROOT / "reports" / "forward_observations.jsonl"
REGISTRY_FILE = ROOT / "reports" / "hypothesis_registry.json"

SCHEMA_VERSION = 1
DEFAULT_COST_BPS = 10.0
PURPOSE = "plumbing_demo_not_validated_edge"
CRYPTO_QUOTES = ("USDT", "USDC", "USD", "EUR", "BTC", "ETH")
#: The instrument a gated pod would be expressed in - the asset class's own
#: home-market default, not a stock pick. Explicitly refused rather than guessed:
#: a pod with no mapping here is skipped with a reason.
PROXY_SYMBOL = {
    "POD-EQUITY-BREAKOUT": "SPY",
    "POD-ETF-DUAL-MOMENTUM": "SPY",
    "POD-CRYPTO-VWAP-REVERSION": "BTC/USDT",
    "POD-CRYPTO-BOLLINGER-MR": "BTC/USDT",
    "POD-CRYPTO-POSITION": "BTC/USDT",
    "POD-CRYPTO-BTC4H-RSIMACD": "BTC/USDT",
    "POD-FOREX-USDJPY-MOMENTUM": "USDJPY",
    "POD-COMMODITY-ROLL-YIELD": "GLD",
    "POD-FABER-TAA": "SPY",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    """Path relative to ROOT when possible, else the absolute path."""
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


# ------------------------------------------------------------------ resolution
def _resolver():
    """Import the existing intrabar TP/SL helper (SL-first). None if unavailable."""
    try:
        from audit_trail.universal_pick_resolver import _check_tp_sl_intrabar
        return _check_tp_sl_intrabar
    except Exception:
        return None


def resolve_tp_sl(pos: dict, bar: dict) -> tuple[str, float] | None:
    """Resolve a position against one OHLC bar.

    Returns ("TP"|"SL", exit_px) or None. Uses the repo's existing SL-first
    helper; falls back to an equivalent local implementation (also SL-first)
    only if that import is unavailable.
    """
    tp, sl = pos.get("tp"), pos.get("sl")
    if not tp and not sl:
        return None
    direction = (pos.get("direction") or "LONG").upper()
    fn = _resolver()
    if fn is not None:
        pick = {
            "direction": direction,
            "entry_price": pos["entry_px"],
            "take_profit": tp or 0,
            "stop_loss": sl or 0,
            "timestamp": pos.get("entry_ts"),
        }
        res = fn(pick, [bar])
        if res:
            reason, exit_px, _pnl = res
            return ("TP" if reason.startswith("TP") else "SL", float(exit_px))
        return None
    # Local fallback: SL checked before TP on purpose (pessimistic).
    high, low = bar.get("high"), bar.get("low")
    if direction == "LONG":
        if sl and low is not None and low <= sl:
            return ("SL", float(sl))
        if tp and high is not None and high >= tp:
            return ("TP", float(tp))
    else:
        if sl and high is not None and high >= sl:
            return ("SL", float(sl))
        if tp and low is not None and low <= tp:
            return ("TP", float(tp))
    return None


# ------------------------------------------------------------------ book state
def new_book(starting_cash: float, cost_bps: float) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": utcnow(),
        "updated_utc": utcnow(),
        "purpose": PURPOSE,
        "starting_cash": float(starting_cash),
        "cash": float(starting_cash),
        "cost_bps_per_side": float(cost_bps),
        "realized_pnl_gross": 0.0,
        "realized_pnl_net": 0.0,
        "fees_paid": 0.0,
        "positions": [],
        "closed": [],
    }


def load_book() -> dict:
    if not BOOK_FILE.exists():
        raise SystemExit(f"no book at {_rel(BOOK_FILE)} - run --init first")
    return json.loads(BOOK_FILE.read_text())


def save_book(book: dict) -> None:
    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    book["updated_utc"] = utcnow()
    BOOK_FILE.write_text(json.dumps(book, indent=2) + "\n")


def _bps(book: dict) -> float:
    return float(book.get("cost_bps_per_side", DEFAULT_COST_BPS)) / 1e4


def open_position(book: dict, symbol: str, direction: str, qty: float, entry_px: float,
                  tp: float | None = None, sl: float | None = None,
                  strategy: str = "manual", source: str = "cli") -> dict:
    direction = direction.upper()
    if direction not in ("LONG", "SHORT"):
        raise SystemExit("direction must be LONG or SHORT")
    if qty <= 0 or entry_px <= 0:
        raise SystemExit("qty and entry price must be positive")
    notional = qty * entry_px
    fee = notional * _bps(book)
    if direction == "LONG" and book["cash"] < notional + fee:
        raise SystemExit(f"insufficient cash: need {notional + fee:.2f}, have {book['cash']:.2f}")
    if direction == "LONG":
        book["cash"] -= notional + fee
    else:
        book["cash"] += notional - fee
    book["fees_paid"] += fee
    pos = {
        "id": f"{symbol}|{direction}|{utcnow()}",
        "symbol": symbol,
        "direction": direction,
        "qty": float(qty),
        "entry_px": float(entry_px),
        "entry_ts": utcnow(),
        "tp": float(tp) if tp else None,
        "sl": float(sl) if sl else None,
        "strategy": strategy,
        "source": source,
        # gated=False until --load-from-gate proves a pod passed the forward gate.
        "gated": False,
        "entry_fee": round(fee, 8),
        "status": "OPEN",
        "last_px": None,
        "last_mark_ts": None,
        "last_mark_source": None,
    }
    book["positions"].append(pos)
    return pos


def close_position(book: dict, pos: dict, exit_px: float, reason: str, mark_ts: str | None = None) -> dict:
    qty = pos["qty"]
    exit_notional = qty * exit_px
    exit_fee = exit_notional * _bps(book)
    if pos["direction"] == "LONG":
        book["cash"] += exit_notional - exit_fee
        gross = (exit_px - pos["entry_px"]) * qty
    else:
        book["cash"] -= exit_notional + exit_fee
        gross = (pos["entry_px"] - exit_px) * qty
    net = gross - pos.get("entry_fee", 0.0) - exit_fee
    book["realized_pnl_gross"] += gross
    book["realized_pnl_net"] += net
    book["fees_paid"] += exit_fee
    rec = {
        "id": pos["id"], "symbol": pos["symbol"], "direction": pos["direction"],
        "qty": qty, "entry_px": pos["entry_px"], "exit_px": float(exit_px),
        "entry_ts": pos["entry_ts"], "exit_ts": mark_ts or utcnow(),
        "reason": reason, "strategy": pos.get("strategy"), "source": pos.get("source"),
        "gated": bool(pos.get("gated")),
        "gross": round(gross, 8), "fees": round(pos.get("entry_fee", 0.0) + exit_fee, 8),
        "net": round(net, 8),
    }
    book["closed"].append(rec)
    book["positions"] = [p for p in book["positions"] if p["id"] != pos["id"]]
    return rec


# ---------------------------------------------------------------- price source
def _crypto_pair(symbol: str) -> tuple[str, str] | None:
    s = symbol.upper().strip()
    if "/" in s:
        base, quote = s.split("/", 1)
        return base, quote
    for q in CRYPTO_QUOTES:
        if s.endswith(q) and len(s) > len(q):
            return s[: -len(q)], q
    return None


def _forex_price(symbol: str) -> dict | None:
    s = symbol.upper().replace("/", "").replace("-", "")
    if len(s) != 6 or not (s[:3].isalpha() and s[3:].isalpha()):
        return None
    f = FOREX_CACHE / f"{s}.csv"
    if not f.exists():
        return None
    try:
        with f.open() as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("close")]
        if not rows:
            return None
        last = rows[-1]
        return {"px": float(last["close"]), "ts": last["date"] + "T00:00:00Z",
                "source": "forex_rate_cache (ECB close, not live)"}
    except Exception:
        return None


def _ccxt_price(symbol: str) -> dict | None:
    pair = _crypto_pair(symbol)
    if pair is None:
        return None
    base, quote = pair
    try:
        import ccxt
    except Exception:
        return None
    for ex_id in ("binance", "kraken", "coinbase"):
        try:
            ex = getattr(ccxt, ex_id)({"enableRateLimit": True, "timeout": 15000})
            ex.load_markets()
            sym = f"{base}/{quote}"
            if sym not in ex.markets:
                if f"{base}/USDT" in ex.markets:
                    sym = f"{base}/USDT"
                elif f"{base}/USD" in ex.markets:
                    sym = f"{base}/USD"
                else:
                    continue
            t = ex.fetch_ticker(sym)
            px = t.get("last") or t.get("close")
            if px:
                ts = t.get("datetime") or utcnow()
                return {"px": float(px), "ts": ts, "source": f"ccxt:{ex_id}:{sym}"}
        except Exception:
            continue
    return None


def _yf_price(symbol: str) -> dict | None:
    try:
        import yfinance as yf
    except Exception:
        return None
    try:
        d = yf.download(symbol, period="1d", interval="1m", progress=False, threads=False)
        if d is None or len(d) == 0:
            return None
        close = d["Close"].dropna()
        if len(close) == 0:
            return None
        px = float(close.iloc[-1])
        ts = close.index[-1].isoformat()
        return {"px": px, "ts": ts, "source": "yfinance:1m"}
    except Exception:
        return None


def fetch_price(symbol: str) -> dict | None:
    """Real quote for a symbol, or None. Never returns a guess.

    Order: on-disk FX (ECB) -> ccxt crypto -> yfinance.
    """
    for fn in (_forex_price, _ccxt_price, _yf_price):
        got = fn(symbol)
        if got and got.get("px"):
            return got
    return None


# --------------------------------------------------------------------- marking
def mark_book(book: dict, price_fn=fetch_price) -> dict:
    """Fetch per open symbol, resolve TP/SL, return the run payload.

    A symbol with no price is marked STALE and EXCLUDED from equity - never
    valued at entry price, zero, or a guess.
    """
    ts = utcnow()
    prices: dict[str, dict] = {}
    closed_now: list[dict] = []

    for pos in list(book["positions"]):
        sym = pos["symbol"]
        if sym not in prices:
            got = price_fn(sym)
            if got:
                prices[sym] = {"px": got["px"], "ts": got.get("ts"), "source": got.get("source")}
            else:
                prices[sym] = {"px": None, "ts": None, "source": None, "stale": True}
        quote = prices[sym]
        if quote["px"] is None:
            pos["status"] = "STALE"
            pos["last_px"] = None
            pos["last_mark_ts"] = ts
            pos["last_mark_source"] = None
            continue
        px = quote["px"]
        pos["status"] = "OPEN"
        pos["last_px"] = px
        pos["last_mark_ts"] = ts
        pos["last_mark_source"] = quote["source"]
        bar = {"open": px, "high": px, "low": px}
        hit = resolve_tp_sl(pos, bar)
        if hit:
            reason, exit_px = hit
            rec = close_position(book, pos, exit_px, reason, mark_ts=ts)
            rec["mark_source"] = quote["source"]
            closed_now.append(rec)

    positions_value = 0.0
    unrealized_gross = 0.0
    unrealized_net = 0.0
    stale = []
    open_rows = []
    for pos in book["positions"]:
        px = pos.get("last_px")
        if pos.get("status") != "OPEN" or px is None:
            stale.append(pos["symbol"])
            open_rows.append({**pos, "market_value": None, "unrealized": None})
            continue
        sign = 1 if pos["direction"] == "LONG" else -1
        mv = sign * pos["qty"] * px
        gross = (px - pos["entry_px"]) * pos["qty"] * sign
        est_exit_fee = pos["qty"] * px * _bps(book)
        positions_value += mv
        unrealized_gross += gross
        unrealized_net += gross - est_exit_fee
        open_rows.append({**pos, "market_value": round(mv, 8),
                          "unrealized": round(gross, 8),
                          "unrealized_net": round(gross - est_exit_fee, 8)})

    equity = book["cash"] + positions_value
    payload = {
        "ts_utc": ts,
        "cash": round(book["cash"], 8),
        "positions_value": round(positions_value, 8),
        "equity": round(equity, 8),
        "realized_pnl": round(book["realized_pnl_net"], 8),
        "realized_pnl_gross": round(book["realized_pnl_gross"], 8),
        "fees_paid": round(book["fees_paid"], 8),
        "unrealized_pnl": round(unrealized_gross, 8),
        "unrealized_pnl_net": round(unrealized_net, 8),
        "n_open": len(book["positions"]),
        "n_closed": len(book["closed"]),
        "prices": prices,
        "closed_now": closed_now,
        "stale_symbols": sorted(set(stale)),
        "purpose": PURPOSE,
    }
    return payload


def append_equity(payload: dict) -> None:
    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    with EQUITY_FILE.open("a") as fh:
        fh.write(json.dumps(payload) + "\n")


def write_snapshot(book: dict, payload: dict) -> Path:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    day = payload["ts_utc"][:10]
    path = SNAP_DIR / f"{day}.json"
    snap = {**payload, "schema_version": SCHEMA_VERSION, "purpose": PURPOSE,
            "starting_cash": book["starting_cash"],
            "cost_bps_per_side": book["cost_bps_per_side"],
            "positions": book["positions"],
            "closed": book["closed"]}
    # Same-day re-marks replace the snapshot (latest mark wins) but the
    # equity_curve.jsonl keeps every point.
    path.write_text(json.dumps(snap, indent=2) + "\n")
    return path


# ----------------------------------------------------------- gate-checked loader
def _promotable_map(registry_file: Path) -> dict[str, bool]:
    """hypothesis_id -> the registry's explicit ``promotable`` flag.

    Absent means "no explicit flag", which is NOT the same as True: the gate
    decides, and only an explicit ``false`` vetoes a pod that would otherwise pass.
    """
    try:
        data = json.loads(Path(registry_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, bool] = {}
    try:
        from alpha_engine.hypothesis_status import iter_hypotheses
        records = list(iter_hypotheses(data))
    except Exception:
        records = data.get("hypotheses") or [] if isinstance(data, dict) else []

    def walk(node):
        if isinstance(node, dict):
            hid, val = node.get("id"), node.get("promotable")
            if isinstance(hid, str) and isinstance(val, bool):
                out.setdefault(hid.strip().upper(), val)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(records)
    return out


def _manifest_pods(manifest_file: Path) -> list[dict]:
    try:
        data = json.loads(Path(manifest_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [p for p in (data.get("pods") or []) if isinstance(p, dict)]


def evaluate_gate(manifest_file: Path = MANIFEST, ledger_file: Path = FORWARD_LEDGER,
                  registry_file: Path = REGISTRY_FILE) -> dict:
    """Every pod's real gate result, judged by the repo's own gate code.

    Reuses ``forward_gate_block`` (which filters to the pod's own forward rows
    since ``registered_at`` and calls ``forward_observations.promotion``) - no
    threshold here is re-implemented or relaxed. A pod is loadable only when the
    gate marks it eligible AND the registry does not say ``promotable: false``.
    """
    from alpha_engine.audit3_tribunal import forward_gate_block, load_confirmatory

    manifest = load_confirmatory(str(manifest_file))
    block = forward_gate_block(manifest, str(ledger_file))
    promotable = _promotable_map(registry_file)
    results: list[dict] = []
    for pod in _manifest_pods(manifest_file):
        pid = pod.get("id")
        res = (block.get("pods") or {}).get(pid)
        if res is None:  # declined/post_hoc/retired pods are hidden by the gate
            results.append({"pod": pid, "status": pod.get("status"),
                            "hypothesis_id": pod.get("hypothesis_id"),
                            "n": 0, "eligible": False, "loadable": False,
                            "reasons": [f"pod status {pod.get('status')!r} cannot "
                                        "confer confirmatory"], "gate_seen": False})
            continue
        hid = str(res.get("hypothesis_id") or "").upper()
        flag = promotable.get(hid)
        reasons = list(res.get("reasons") or [])
        loadable = bool(res.get("eligible")) and flag is not False
        if res.get("eligible") and flag is False:
            reasons.append("registry marks hypothesis promotable: false")
        results.append({
            "pod": pid, "status": res.get("status"), "hypothesis_id": res.get("hypothesis_id"),
            "n": int(res.get("n_forward") or 0), "eligible": bool(res.get("eligible")),
            "promotable": flag, "loadable": loadable, "reasons": reasons, "gate_seen": True,
        })
    return {"ledger": _rel(ledger_file), "ledger_fingerprint": block.get("fingerprint"),
            "n_rows": block.get("n_rows"), "manifest": _rel(manifest_file),
            "pods": results}


def load_from_gate(book: dict, gate: dict | None = None) -> tuple[dict, dict]:
    """Open gated positions only for pods that pass the real gate.

    Returns (outcome, book). When no pod is loadable the book is returned
    UNTOUCHED - the caller must not save it, so ``book.json`` stays
    byte-identical. A passing pod gets a LONG position in the asset class's home
    market instrument at its last real quote; a symbol that cannot be quoted is
    skipped (never valued at a guess). Market orders carry no TP/SL because the
    gate does not publish levels.
    """
    gate = gate or evaluate_gate()
    pods = gate["pods"]
    outcome: dict = {"loaded": 0, "pods_checked": [p["pod"] for p in pods],
                     "pod_results": pods, "loaded_positions": []}
    passing = [p for p in pods if p.get("loadable")]
    if not passing:
        outcome["reason"] = "no_pod_passed_forward_gate"
        return outcome, book
    for pod in passing:
        symbol = PROXY_SYMBOL.get(str(pod.get("pod") or "").upper())
        if symbol is None:
            outcome.setdefault("skipped", []).append(
                {"pod": pod["pod"], "reason": "no instrument mapped for pod"})
            continue
        quote = fetch_price(symbol)
        if not quote or not quote.get("px"):
            outcome.setdefault("skipped", []).append(
                {"pod": pod["pod"], "symbol": symbol, "reason": "no real quote"})
            continue
        px = float(quote["px"])
        alloc = min(float(book["cash"]) * 0.10, float(book["starting_cash"]) * 0.10)
        qty = alloc / px if px > 0 else 0.0
        if qty <= 0:
            outcome.setdefault("skipped", []).append(
                {"pod": pod["pod"], "symbol": symbol, "reason": "no allocatable cash"})
            continue
        pos = open_position(book, symbol, "LONG", qty, px, strategy=pod["pod"],
                            source=f"forward-gate:{pod.get('hypothesis_id') or '-'}")
        pos["gated"] = True
        pos["gate_n"] = pod.get("n")
        pos["gate_evidence"] = pod.get("reasons") or []
        outcome["loaded"] += 1
        outcome["loaded_positions"].append(pos["id"])
    if outcome["loaded"] == 0:
        outcome["reason"] = "no_pod_passed_forward_gate"
    return outcome, book


# ------------------------------------------------------------------- printing
def _fmt(x, nd=2):
    if x is None:
        return "-"
    return f"{x:,.{nd}f}"


def _banner(book: dict) -> str | None:
    """Loud demo label whenever no open position is gate-backed."""
    positions = book.get("positions") or []
    if any(p.get("gated") for p in positions) or not positions:
        return None
    return (f"DEMO BOOK - NOT GATE-BACKED ({len(positions)} position(s), none from "
            "--load-from-gate)")


def _describe(book: dict) -> dict:
    """Book plus an explicit gate summary (never rewrites the stored book)."""
    positions = book.get("positions") or []
    n_gated = sum(1 for p in positions if p.get("gated"))
    return {**book,
            "gate_summary": {
                "n_positions": len(positions),
                "n_gated": n_gated,
                "n_demo_ungated": len(positions) - n_gated,
                "gate_backed": n_gated > 0,
                "note": ("positions are demo entries until --load-from-gate "
                         "proves a pod passed the forward gate"),
            }}


def print_payload(payload: dict, book: dict) -> None:
    banner = _banner(book)
    if banner:
        print(banner)
    print(f"paper portfolio mark  {payload['ts_utc']}   [{PURPOSE}]")
    print(f"  cash          {_fmt(payload['cash'])}")
    print(f"  positions val {_fmt(payload['positions_value'])}")
    print(f"  EQUITY        {_fmt(payload['equity'])}   "
          f"(start {_fmt(book['starting_cash'])})")
    print(f"  realized net  {_fmt(payload['realized_pnl'])}   "
          f"unrealized {_fmt(payload['unrealized_pnl'])}  "
          f"(net of est. exit cost {_fmt(payload['unrealized_pnl_net'])})")
    print(f"  open={payload['n_open']} closed={payload['n_closed']}  "
          f"cost={book['cost_bps_per_side']:.0f}bp/side")
    if payload["closed_now"]:
        for c in payload["closed_now"]:
            print(f"  CLOSED {c['symbol']} {c['reason']} @ {c['exit_px']}  net {c['net']:+.4f}")
    print()
    hdr = f"  {'symbol':<12}{'dir':<6}{'gate':<6}{'qty':>12}{'entry':>14}{'mark':>14}{'uPnL':>12}  source/status"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for p in book["positions"]:
        gflag = "GATED" if p.get("gated") else "demo"
        px = p.get("last_px")
        if p.get("status") != "OPEN" or px is None:
            note = "STALE - no price (excluded from equity)"
            mark = "-"
            upnl = "-"
        else:
            sign = 1 if p["direction"] == "LONG" else -1
            upnl = f"{(px - p['entry_px']) * p['qty'] * sign:+,.2f}"
            mark = _fmt(px, 4)
            note = p.get("last_mark_source") or ""
        print(f"  {p['symbol']:<12}{p['direction']:<6}{gflag:<6}{p['qty']:>12g}"
              f"{_fmt(p['entry_px'], 4):>14}{mark:>14}{upnl:>12}  {note}")
    if payload["stale_symbols"]:
        print(f"\n  WARNING: no price for {payload['stale_symbols']} - "
              "excluded from equity, NOT valued at entry or zero.")
    print("\n  NOTE: plumbing demo. Zero strategies in this repo are validated; "
          "this P&L means nothing about future returns.")


# ----------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Paper portfolio tracker (plumbing demo)")
    ap.add_argument("--init", action="store_true", help="create/reset the book")
    ap.add_argument("--cash", type=float, default=10000.0, help="starting cash for --init")
    ap.add_argument("--force", action="store_true", help="allow --init to overwrite")
    ap.add_argument("--cost-bps", type=float, default=DEFAULT_COST_BPS, help="per-side cost bp")
    ap.add_argument("--add", nargs=3, metavar=("SYMBOL", "DIRECTION", "QTY"),
                    help="record an entry")
    ap.add_argument("--entry", type=float, help="entry price for --add")
    ap.add_argument("--tp", type=float, help="take profit")
    ap.add_argument("--sl", type=float, help="stop loss")
    ap.add_argument("--strategy", default="manual")
    ap.add_argument("--source", default="cli")
    ap.add_argument("--mark", action="store_true", help="fetch prices, resolve, write equity+snapshot")
    ap.add_argument("--status", action="store_true", help="print book without fetching")
    ap.add_argument("--load-from-gate", action="store_true",
                    help="open positions ONLY for pods that pass the real forward gate "
                         "(refuses, leaving book.json untouched, when none do)")
    ap.add_argument("--manifest", help="pod manifest (default reports/audit3_confirmatory.json)")
    ap.add_argument("--ledger", help="forward ledger (default reports/forward_observations.jsonl)")
    ap.add_argument("--registry", help="hypothesis registry (default reports/hypothesis_registry.json)")
    ap.add_argument("--json", action="store_true", help="machine output")
    args = ap.parse_args(argv)

    if args.load_from_gate:
        book = load_book()
        before = hashlib.sha256(BOOK_FILE.read_bytes()).hexdigest() if BOOK_FILE.exists() else None
        gate = evaluate_gate(Path(args.manifest) if args.manifest else MANIFEST,
                             Path(args.ledger) if args.ledger else FORWARD_LEDGER,
                             Path(args.registry) if args.registry else REGISTRY_FILE)
        outcome, book = load_from_gate(book, gate)
        if outcome["loaded"] > 0:  # the ONLY path that writes the book
            save_book(book)
        after = hashlib.sha256(BOOK_FILE.read_bytes()).hexdigest() if BOOK_FILE.exists() else None
        outcome["book"] = _rel(BOOK_FILE)
        outcome["book_sha256_before"] = before
        outcome["book_sha256_after"] = after
        outcome["book_unchanged"] = before == after
        if args.json:
            print(json.dumps(outcome, indent=2))
        elif outcome["loaded"] > 0:
            print(f"loaded {outcome['loaded']} gated position(s) from {outcome['book']}")
            for pid in outcome["loaded_positions"]:
                print(f"  LOADED {pid}")
        else:
            print(f"REFUSED: {outcome['reason']} - no position opened, "
                  f"{outcome['book']} unchanged ({str(before)[:12]})")
            print(f"  pods checked: {len(outcome['pods_checked'])}")
            for p in outcome["pod_results"]:
                r = (p.get("reasons") or ["-"])[0]
                print(f"  {p['pod']:<32} n={p.get('n', 0):<4} eligible={str(p.get('eligible')):<5} {r}")
            print("  This book holds no gate-backed positions because nothing passed.")
        return 0

    if args.init:
        if BOOK_FILE.exists() and not args.force:
            raise SystemExit(f"{_rel(BOOK_FILE)} exists - pass --force to overwrite")
        book = new_book(args.cash, args.cost_bps)
        save_book(book)
        BOOK_DIR.mkdir(parents=True, exist_ok=True)
        EQUITY_FILE.touch()
        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        out = {"ok": True, "book": _rel(BOOK_FILE),
               "starting_cash": book["starting_cash"],
               "cost_bps_per_side": book["cost_bps_per_side"], "purpose": PURPOSE}
        print(json.dumps(out, indent=2) if args.json else
              f"initialized {_rel(BOOK_FILE)} cash={book['starting_cash']:.2f} "
              f"cost={book['cost_bps_per_side']:.0f}bp/side  [{PURPOSE}]")
        return 0

    if args.add:
        book = load_book()
        if args.entry is None:
            raise SystemExit("--add requires --entry PX")
        sym, direction, qty = args.add[0], args.add[1], float(args.add[2])
        pos = open_position(book, sym, direction, qty, args.entry,
                            tp=args.tp, sl=args.sl, strategy=args.strategy, source=args.source)
        save_book(book)
        out = {"ok": True, "position": pos, "cash": round(book["cash"], 8)}
        print(json.dumps(out, indent=2) if args.json else
              f"added {pos['direction']} {pos['qty']:g} {pos['symbol']} @ {pos['entry_px']:g}"
              f"  tp={pos['tp']} sl={pos['sl']}  cash now {book['cash']:.2f}")
        return 0

    if args.mark:
        book = load_book()
        payload = mark_book(book)
        save_book(book)
        append_equity(payload)
        snap = write_snapshot(book, payload)
        if args.json:
            print(json.dumps({**payload, "snapshot": _rel(snap)}, indent=2))
        else:
            print_payload(payload, book)
            print(f"  equity -> {_rel(EQUITY_FILE)}  snapshot -> {_rel(snap)}")
        return 0

    if args.status:
        book = load_book()
        if args.json:
            print(json.dumps(_describe(book), indent=2))
        else:
            banner = _banner(book)
            if banner:
                print(banner)
            print(f"book {_rel(BOOK_FILE)}  updated {book['updated_utc']}  [{book.get('purpose')}]")
            print(f"  cash {book['cash']:.2f}  start {book['starting_cash']:.2f}  "
                  f"realized net {book['realized_pnl_net']:.4f}  fees {book['fees_paid']:.4f}")
            for p in book["positions"]:
                gflag = "GATED" if p.get("gated") else "DEMO/UNGATED"
                print(f"  OPEN {p['symbol']:<12}{p['direction']:<6} qty {p['qty']:g} "
                      f"@ {p['entry_px']:g}  tp={p['tp']} sl={p['sl']}  "
                      f"[{p['status']}] [{gflag}]")
            print(f"  closed trades: {len(book['closed'])}")
            if not any(p.get("gated") for p in book["positions"]):
                print("  NOTE: no position here came from --load-from-gate; "
                      "these are demo entries, not signals.")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
