#!/usr/bin/env python3
"""Validate PnL == 0.0 rows against real market data, and flag blank fields.

Why this exists
---------------
The live /audit payload publishes rows whose PnL is exactly 0.0%. Some are honest
(a position opened 30 minutes ago has not moved). Some are not. A 0.0% that means
"unknown" is indistinguishable from a 0.0% that means "flat" unless someone checks
the market.

This tool checks the market. It never rewrites a pick and never mutates history.
It emits one classification per row plus an exit code a CI job can gate on.

Classifications
---------------
JUST_OPENED              open, recent, entry == mark -> 0.0% is expected
FLAT_VERIFIED            market data confirms the exit matches its own day's close
STALE_MARK               open, market moved > tol, but the mark still equals entry
UNPRICED                 open, no current_price at all -> 0.0% is meaningless
FABRICATED_FLAT          closed flat, but exit_price is not the close on its exit date
UNVERIFIABLE_NO_ENTRY    no usable market close to check against (never "passes")
PNL_PRICE_MISMATCH       stated pnl disagrees with prices by > 1pp
NOT_ZERO                 pnl is not 0.0, not under test

The primary test for a closed row is exit_price vs the close ON ITS OWN EXIT DATE
(MARK_TOL slippage). Comparing exit against entry instead conflates "held a long
time so the market moved" with "the price was never looked up", and produces false
negatives whenever the entry is old. The entry->exit window is still reported as
context, not as the verdict.

Usage
-----
    python3 tools/pnl_zero_validator.py --payload /tmp/dd_live.json --max-rows 40
    python3 tools/pnl_zero_validator.py --payload https://findtorontoevents.ca/audit/data/dashboard_data.json
    python3 tools/pnl_zero_validator.py --payload ... --offline
    python3 tools/pnl_zero_validator.py --payload ... --json-out reports/pnl_zero_validation_live.json

Exit codes
----------
    0  clean
    1  fabricated flats, stale marks, mismatches, or blank fields on displayed rows
    2  bad input / cannot load payload
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (compatible; pnl-zero-validator/1.0)"}

# Tolerance = floor for suspicion, by class (see the plan, §4.2).
TOL = {
    "EQUITY": 0.0050,
    "ETF": 0.0050,
    "BOND": 0.0050,
    "CRYPTO": 0.0100,
    "FOREX": 0.0010,
    "FUTURES": 0.0075,
    "COMMODITY": 0.0075,
    "MEME": 0.0100,
    "PENNY_STOCK": 0.0100,
}
DEFAULT_TOL = 0.0050
MISMATCH_PP = 1.0   # stated vs implied, percentage points
MARK_TOL = 0.0025   # exit_price vs exit-date close: slippage allowance

BLANK = (None, "", "N/A", "None", "null", "nan")


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


# --------------------------------------------------------------------------- io
def load_payload(src: str) -> dict:
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(Path(src).read_text(encoding="utf-8"))


_CACHE: dict[str, list[dict] | None] = {}


def yahoo_symbol(symbol: str, asset_class: str) -> str:
    s = (symbol or "").strip().upper()
    if asset_class == "CRYPTO":
        if "-" in s:
            return s
        for suffix in ("USDT", "USDC", "BUSD", "USD"):
            if s.endswith(suffix) and len(s) > len(suffix):
                return f"{s[: -len(suffix)]}-USD"
        return f"{s}-USD"
    if asset_class == "FOREX":
        if s.endswith("=X"):
            return s
        if s.count("-") == 1:
            a, b = s.split("-")
            return f"{a}{b}=X"
    return s


def yahoo_daily(symbol: str, rng: str = "3mo") -> list[dict] | None:
    """Daily OHLC, oldest first. None if the symbol cannot be priced."""
    key = f"{symbol}|{rng}"
    if key in _CACHE:
        return _CACHE[key]
    u = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}?range={rng}&interval=1d"
    )
    rows: list[dict] | None = None
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
        res = (d.get("chart") or {}).get("result") or []
        if res:
            r0 = res[0]
            ts = r0.get("timestamp") or []
            q = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
            closes = q.get("close") or []
            opens = q.get("open") or []
            rows = []
            for i, t in enumerate(ts):
                if i < len(closes) and closes[i] is not None:
                    rows.append({
                        "date": datetime.fromtimestamp(t, timezone.utc).date().isoformat(),
                        "open": opens[i] if i < len(opens) else None,
                        "close": closes[i],
                    })
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        rows = None
    _CACHE[key] = rows
    return rows


def close_on_or_before(rows: list[dict] | None, day: str | None) -> float | None:
    if not rows or not day:
        return None
    best = None
    for r in rows:
        if r["date"] <= day:
            best = r["close"]
        else:
            break
    return best


def last_close(rows: list[dict] | None) -> float | None:
    return rows[-1]["close"] if rows else None


# ------------------------------------------------------------------ row helpers
def num(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def is_blank(v) -> bool:
    if isinstance(v, str):
        return v.strip() in BLANK
    return v is None or (isinstance(v, float) and v != v)


def day_of(v) -> str | None:
    if is_blank(v):
        return None
    s = str(v).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def implied_pct(row: dict) -> float | None:
    entry = num(row.get("entry_price"))
    mark = num(row.get("exit_price")) if not is_blank(row.get("closed_at")) else num(row.get("current_price"))
    if mark is None:
        mark = num(row.get("current_price"))
    if entry is None or mark is None or entry == 0:
        return None
    raw = (mark - entry) / entry * 100.0
    if str(row.get("direction", "")).upper() in ("SHORT", "SELL"):
        raw = -raw
    return raw


def declared_pnl(row: dict) -> float | None:
    for k in ("pnl_pct", "realized_pnl_pct", "pnl_percent"):
        if k in row:
            return num(row.get(k))
    return None


def _is_short(row: dict) -> bool:
    return str(row.get("direction", "")).upper() in ("SHORT", "SELL")


# ------------------------------------------------------------------ classifier
def classify(row: dict, *, offline: bool) -> dict:
    cls = (row.get("asset_class") or "BLANK").upper()
    tol = TOL.get(cls, DEFAULT_TOL)
    pnl = declared_pnl(row)
    closed = not is_blank(row.get("closed_at"))
    out = {
        "symbol": row.get("symbol"),
        "asset_class": cls,
        "direction": row.get("direction"),
        "closed": closed,
        "pnl_pct": pnl,
        "entry_price": num(row.get("entry_price")),
        "mark": num(row.get("exit_price")) if closed else num(row.get("current_price")),
        "tol_pct": tol * 100.0,
        "verdict": "NOT_ZERO",
        "detail": "",
        "real_move_pct": None,
        "exit_mark_error_pct": None,
        "blank_fields": [],
        "source": None,
    }
    if pnl is None or pnl != 0.0:
        return out

    entry, mark = out["entry_price"], out["mark"]

    blanks = []
    if closed:
        for f in ("exit_price", "closed_at", "exit_reason"):
            if is_blank(row.get(f)):
                blanks.append(f)
        if is_blank(row.get("entry_time")):
            blanks.append("entry_time")
    else:
        for f in ("current_price", "entry_price", "take_profit", "stop_loss"):
            if is_blank(row.get(f)):
                blanks.append(f)
    out["blank_fields"] = blanks

    # ------------------------------------------------------------- open rows
    if not closed:
        age = num(row.get("age_hours"))
        if mark is None:
            out["verdict"] = "UNPRICED"
            out["detail"] = "no current_price; 0.0% carries no information"
            return out
        if entry is not None and abs(mark - entry) <= 1e-9 and age is not None and age <= 2.0:
            out["verdict"] = "JUST_OPENED"
            out["detail"] = f"age {age:.1f}h, mark == entry; 0.0% is expected"
            return out
        if offline:
            out["verdict"] = "FLAT_UNCHECKED"
            out["detail"] = "offline: market not consulted"
            return out
        sym = yahoo_symbol(str(row.get("symbol")), cls)
        rows = yahoo_daily(sym)
        px = last_close(rows)
        out["source"] = f"yahoo:{sym}"
        if px is None:
            out["verdict"] = "UNPRICEABLE"
            out["detail"] = f"no market price for {sym}"
            return out
        if entry:
            move = (px - entry) / entry * 100.0
            if _is_short(row):
                move = -move
            out["real_move_pct"] = round(move, 4)
            if abs(move) > tol * 100.0:
                out["verdict"] = "STALE_MARK"
                out["detail"] = (
                    f"market moved {move:+.2f}% since entry but mark == entry "
                    f"(tol {tol*100:.2f}%)"
                )
            else:
                out["verdict"] = "FLAT_VERIFIED"
                out["detail"] = f"market move {move:+.2f}% within tol"
        return out

    # ----------------------------------------------------------- closed rows
    entry_day = day_of(row.get("entry_time"))
    exit_day = day_of(row.get("closed_at"))
    if offline:
        out["verdict"] = "FLAT_UNCHECKED"
        out["detail"] = "offline: market not consulted"
        return out

    sym = yahoo_symbol(str(row.get("symbol")), cls)
    rows = yahoo_daily(sym)
    out["source"] = f"yahoo:{sym}"
    if rows is None:
        out["verdict"] = "UNPRICEABLE"
        out["detail"] = f"no market price for {sym}"
        return out

    p0 = close_on_or_before(rows, entry_day) if entry_day else None
    p1 = close_on_or_before(rows, exit_day) if exit_day else None

    # PRIMARY TEST: a marked exit must equal the close on its own exit date.
    if p1 and mark is not None:
        mark_err = (mark - p1) / p1 * 100.0
        out["exit_mark_error_pct"] = round(mark_err, 4)
        if p0:
            mv = (p1 - p0) / p0 * 100.0
            if _is_short(row):
                mv = -mv
            out["real_move_pct"] = round(mv, 4)
        if abs(mark_err) > MARK_TOL * 100.0:
            out["verdict"] = "FABRICATED_FLAT"
            out["detail"] = (
                f"exit_price {mark:g} is not the {exit_day} close {p1:g} "
                f"(error {mark_err:+.2f}%, slippage tol {MARK_TOL*100:.2f}%)"
            )
        else:
            out["verdict"] = "FLAT_VERIFIED"
            win = (f"; holding-window move {out['real_move_pct']:+.2f}%"
                   if out.get("real_move_pct") is not None else "")
            out["detail"] = f"exit matches the {exit_day} close{win}"
        return out

    out["verdict"] = "UNVERIFIABLE_NO_ENTRY"
    out["detail"] = "no market close available for the exit date"
    return out


def mismatch_flag(row: dict) -> str | None:
    pnl, imp = declared_pnl(row), implied_pct(row)
    if pnl is None or imp is None:
        return None
    if abs(imp - pnl) > MISMATCH_PP:
        return f"stated {pnl:+.2f}% vs prices {imp:+.2f}%"
    return None


# ---------------------------------------------------------------------- report
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate PnL==0 rows against real market data")
    ap.add_argument("--payload", required=True)
    ap.add_argument("--max-rows", type=int, default=40)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--json-out", type=str, default=None)
    ap.add_argument("--show", type=int, default=12)
    args = ap.parse_args(argv)

    try:
        d = load_payload(args.payload)
    except Exception as e:  # noqa: BLE001
        print(f"FATAL: cannot load payload: {e}", file=sys.stderr)
        return 2

    picks = d.get("picks") or {}
    hero = picks.get("active") or []
    raw = picks.get("active_raw") or []
    closed = picks.get("recent_closed") or []
    print(f"payload       : {args.payload}")
    print(f"generated_at  : {d.get('generated_at')}")
    print(f"rows          : active={len(hero)} active_raw={len(raw)} recent_closed={len(closed)}")
    print()

    sections: dict[str, dict] = {}
    results: dict[str, list[dict]] = {}
    hard_fail = False

    for name, rows, limit, is_hero in (
        ("displayed_active", hero, 0, True),
        ("active_raw", raw, args.max_rows, False),
        ("recent_closed", closed, args.max_rows, False),
    ):
        zeros = [r for r in rows if declared_pnl(r) == 0.0]
        take = zeros if limit == 0 else zeros[:limit]
        classified = [classify(r, offline=args.offline) for r in take]
        results[name] = classified
        verdicts = Counter(c["verdict"] for c in classified)
        blank_rows = [c for c in classified if c.get("blank_fields")]
        mism = [(c, mismatch_flag(r)) for c, r in zip(classified, take)]
        mism = [(c, m) for c, m in mism if m]

        bad = verdicts.get("FABRICATED_FLAT", 0) + verdicts.get("STALE_MARK", 0) + len(mism)
        if is_hero:
            bad += verdicts.get("UNPRICED", 0) + verdicts.get("UNPRICEABLE", 0) + len(blank_rows)
        if name == "recent_closed":
            recent_unverifiable = sum(
                1 for c, r in zip(classified, take)
                if c["verdict"] == "UNVERIFIABLE_NO_ENTRY"
                and str(r.get("closed_at") or "")[:10] >= _days_ago(7)
            )
        else:
            recent_unverifiable = 0
        bad += recent_unverifiable

        sections[name] = {
            "rows_total": len(rows),
            "pnl_zero": len(zeros),
            "checked": len(classified),
            "verdicts": dict(verdicts),
            "rows_with_blank_fields": len(blank_rows),
            "pnl_price_mismatches": len(mism),
            "recent_unverifiable_7d": recent_unverifiable,
            "hard_fail": bad > 0,
        }
        hard_fail = hard_fail or bad > 0

        print(f"=== {name}: {len(zeros)} PnL==0 of {len(rows)} rows (checked {len(classified)}) ===")
        for v, n in verdicts.most_common():
            print(f"    {v:24s} {n}")
        if blank_rows:
            print(f"    rows with blank fields: {len(blank_rows)}")
        for c in classified[: args.show]:
            if c["verdict"] == "NOT_ZERO":
                continue
            rm = "" if c["real_move_pct"] is None else f" win={c['real_move_pct']:+.2f}%"
            bl = f" blanks={','.join(c['blank_fields'])}" if c.get("blank_fields") else ""
            print(f"      {str(c['symbol'])[:12]:12s} {c['verdict']:22s}{rm}{bl}  {c['detail']}")
        if mism:
            print(f"    PnL/price mismatches (> {MISMATCH_PP}pp): {len(mism)}")
            for c, m in mism[:4]:
                print(f"      {c['symbol']}: {m}")
        print()

    payload = {
        "payload": args.payload,
        "generated_at": d.get("generated_at"),
        "sections": sections,
        "rows": results,
        "hard_fail": hard_fail,
        "tolerances_pct": {k: v * 100 for k, v in TOL.items()},
        "mark_tolerance_pct": MARK_TOL * 100,
    }
    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2))
        print(f"wrote {p}")

    print("VERDICT:", "FAIL" if hard_fail else "PASS")
    if hard_fail:
        print("  fabricated flats, stale marks, mismatches, or blank displayed fields were found")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
