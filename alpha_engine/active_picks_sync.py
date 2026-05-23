#!/usr/bin/env python3
"""active_picks_sync — bridges at_raw_picks (MySQL, ACTIVE rows) → closed_picks.json
when live price crosses TP/SL or signal_timestamp + MAX_HOLD_HOURS expires.

PR #1 — DRY-RUN ONLY. No writes. Logs proposed verdicts to
`reports/active_picks_sync_dryrun_<UTC>.json` so we can inspect the
proposed transitions before flipping the writer on.

Why this exists
---------------
The /audit DB Health panel reports Raw-Pick Outcome Coverage = 0.09%
(121 / 136,374 raw picks resolved). Per Investigator B 2026-05-12, the
hourly `audit_trail/universal_pick_resolver.py` correctly returns
"resolved 0 picks" because every entry already in
`alpha_engine/data/closed_picks.json` has terminal status. The MISSING
piece is whatever should be reading ACTIVE `at_raw_picks` rows from MySQL,
detecting TP/SL/time-exit, and writing terminal entries back so the
resolver has a non-empty input queue.

This module is the first PR of that fix. PR #2 will wire the writer
(MySQL UPDATE + JSON append per row, per Cerebras consult 2026-05-12).
PR #3 will integrate into audit-dashboard.yml as a new step BEFORE the
resolver.

Design refs
-----------
- Cerebras consult (agent aad788a0785b6a601, 2026-05-12) — recommended
  dry-run-first, new workflow step (not inline), per-row atomic UPDATE
  then JSON append, dedup by id, idempotent on restart.
- Investigator A (a2ad1dd7d9f7dc23a) — existing TP/SL detection at
  forward_validator.py:1182-1213 (logic reused here), price fetchers at
  api_failover.fetch_price and audit_trail/fetch_stock_prices.fetch_prices.
- Cerebras Q3 EQUITY max-hold was too short; revised to 24*5=120h (5d)
  matching CLAUDE.md "5-30 days" floor.
- PNL_WIN_THRESHOLD_BY_CLASS from outcome_resolver.py:115-126.

Usage
-----
    python -m alpha_engine.active_picks_sync                  # dry-run, CRYPTO
    python -m alpha_engine.active_picks_sync --asset-class EQUITY
    python -m alpha_engine.active_picks_sync --max-symbols 200
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

# Per-class WIN threshold (must mirror outcome_resolver.py:115-126).
PNL_WIN_THRESHOLD_BY_CLASS = {
    "CRYPTO": 0.001,    # 0.1bp
    "EQUITY": 0.0005,   # 5bp
    "FOREX":  0.0005,
    "COMMODITY": 0.0005,
    "FUTURES":   0.0005,
    "ETF":       0.0005,
    "BOND":      0.0005,
    "MEMECOIN":  0.001,
}

# Per-class max-hold-hours before EXPIRED. Cerebras suggested
# 'EQUITY': 24*7 but CLAUDE.md per-class horizons span 5-30 days; using
# 120h (5d) as floor matches the conservative end. Overridable via kwarg.
DEFAULT_MAX_HOLD_HOURS = {
    "CRYPTO":    48,     # 2 days
    "EQUITY":    120,    # 5 days (floor of 5-30d window)
    "FOREX":     120,    # 5 days
    "COMMODITY": 14 * 24,  # 14 days
    "FUTURES":   14 * 24,
    "ETF":       7 * 24,
    "BOND":      30 * 24,  # bonds slow-moving
    "MEMECOIN":  24,
}

TERMINAL_STATUSES = ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT", "EXPIRED",
                     "closed_win", "closed_loss")


def connect():
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_STOCKS_PASSWORD", "stocks"),
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=120,
    )


def fetch_active_picks(cur, asset_class: str, max_rows: int = 5000):
    """SELECT OPEN/ACTIVE rows for one asset class, oldest first per Cerebras Q4."""
    cur.execute("""
        SELECT id, source_system, symbol, asset_class, direction,
               entry_price, take_profit, stop_loss, status,
               signal_timestamp, recorded_at, strategy
        FROM at_raw_picks
        WHERE asset_class = %s
          AND status IN ('OPEN', 'ACTIVE')
          AND entry_price IS NOT NULL
          AND entry_price > 0
        ORDER BY signal_timestamp ASC
        LIMIT %s
    """, (asset_class, max_rows))
    return cur.fetchall()


def compute_verdict(pick: dict, live_price: float | None, max_hold_hours: int,
                    win_threshold: float) -> dict | None:
    """For a single ACTIVE pick + current price, decide whether it has
    transitioned to a terminal state.

    Returns None if pick stays OPEN; otherwise dict with verdict details.
    """
    if live_price is None or live_price <= 0:
        return None

    try:
        entry = float(pick.get("entry_price") or 0)
        tp = float(pick.get("take_profit") or 0) or None
        sl = float(pick.get("stop_loss") or 0) or None
    except (ValueError, TypeError):
        return None
    if entry <= 0:
        return None

    direction = str(pick.get("direction", "") or "").upper().strip()
    if direction in ("BUY",):
        direction = "LONG"
    elif direction in ("SELL",):
        direction = "SHORT"

    # TP/SL hit detection — same logic shape as forward_validator.py:1182-1213
    tp_hit = sl_hit = False
    if direction == "LONG":
        if tp and live_price >= tp:
            tp_hit = True
        elif sl and live_price <= sl:
            sl_hit = True
    elif direction == "SHORT":
        if tp and live_price <= tp:
            tp_hit = True
        elif sl and live_price >= sl:
            sl_hit = True

    # Time-exit detection.
    # BUGFIX (P0, 2026-05-17): the prior one-liner had broken ternary
    # precedence — `(A - B if C else D)` bound as `(A - B) if C else D`, so a
    # timezone-AWARE signal_timestamp hit the `else D` branch and `.total_seconds()`
    # was called on a datetime (not a timedelta), raising AttributeError and
    # crashing compute_verdict for every tz-aware pick. Normalize first, then
    # subtract.
    time_exit = False
    sig_ts = pick.get("signal_timestamp")
    if isinstance(sig_ts, datetime):
        if sig_ts.tzinfo is None:
            sig_ts = sig_ts.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - sig_ts).total_seconds() / 3600.0
        if age_hours > max_hold_hours:
            time_exit = True

    if not (tp_hit or sl_hit or time_exit):
        return None

    # Compute realized pnl_pct from entry+live_price for the close.
    if direction == "LONG":
        pnl_pct = (live_price - entry) / entry
    elif direction == "SHORT":
        pnl_pct = (entry - live_price) / entry
    else:
        pnl_pct = 0.0

    # Status by sign-coherence (mirrors the guard at outcome_resolver.py:1670).
    if tp_hit:
        if pnl_pct < -win_threshold:
            # contradiction — trust pnl sign, log it
            new_status = "LOST"
            new_reason = "TP_HIT_CONTRADICTION"
        else:
            new_status = "WON"
            new_reason = "TP_HIT"
    elif sl_hit:
        if pnl_pct > win_threshold:
            new_status = "WON"
            new_reason = "SL_HIT_CONTRADICTION"
        else:
            new_status = "LOST"
            new_reason = "SL_HIT"
    else:  # time_exit
        if pnl_pct > win_threshold:
            new_status = "WON"
            new_reason = "TIME_EXIT"
        elif pnl_pct < -win_threshold:
            new_status = "LOST"
            new_reason = "TIME_EXIT"
        else:
            new_status = "EXPIRED"
            new_reason = "TIME_EXIT"

    return {
        "id": pick.get("id"),
        "symbol": pick.get("symbol"),
        "direction": direction,
        "asset_class": pick.get("asset_class"),
        "strategy": pick.get("strategy"),
        "entry_price": entry,
        "exit_price": live_price,
        "tp": tp,
        "sl": sl,
        "pnl_pct": round(pnl_pct * 100, 4),  # report as percent
        "new_status": new_status,
        "exit_reason": new_reason,
        "tp_hit": tp_hit,
        "sl_hit": sl_hit,
        "time_exit": time_exit,
        "closed_at_proposed": datetime.now(timezone.utc).isoformat(),
    }


def fetch_live_prices(symbols: list[str], asset_class: str) -> dict[str, float]:
    """Per-class live-price fetcher with dedup. Reuses existing failover
    chains — alpha_engine/api_failover for CRYPTO, audit_trail/fetch_stock_prices
    for everything else. DRY-RUN mode tolerates failures (returns partial dict).
    """
    symbols = list(set(symbols))[:1000]  # Cerebras Q4 cap
    prices: dict[str, float] = {}
    if not symbols:
        return prices

    if asset_class == "CRYPTO":
        try:
            from alpha_engine.api_failover import fetch_price
        except Exception as e:
            print(f"# api_failover import failed: {e}", file=sys.stderr)
            return prices
        for sym in symbols:
            try:
                p = fetch_price(sym)
                if p and p > 0:
                    prices[sym] = float(p)
            except Exception:
                continue
    else:
        # yfinance batch.
        # FIX (2026-05-19, 4-AI consensus Grok+deepseek+xai+kilo): the prior
        # `yf.Tickers(" ".join(symbols)).history()` pattern was the root cause of
        # the pervasive `no_price` rate (multi_asset 35/35, stocks_competition
        # 123/124 etc.). For a multi-symbol request yfinance returns a
        # MultiIndex-column DataFrame, so the guard `"Close" in data.columns`
        # is False and EVERY symbol silently falls through to no_price.
        # `yf.download(..., group_by="ticker")` returns a stable per-ticker
        # MultiIndex (sym, "Close") that we can read deterministically; the
        # single-symbol case returns a flat-column frame. Symbols are kept in
        # their canonical write-time form (EURUSD=X / ES=F) — that IS the form
        # yfinance expects; stripping the suffix would break the fetch.
        try:
            import yfinance as yf
        except ImportError:
            print("# yfinance not installed; cannot fetch prices for "
                  f"{asset_class}", file=sys.stderr)
            return prices
        try:
            data = yf.download(
                tickers=" ".join(symbols),
                period="1d",
                interval="1m",
                group_by="ticker",
                auto_adjust=False,
                prepost=False,
                threads=True,
                progress=False,
            )
            if data is None or getattr(data, "empty", True):
                raise ValueError("yf.download returned empty data")
            for sym in symbols:
                try:
                    if len(symbols) == 1:
                        # single-symbol download -> flat-column frame
                        closes = data["Close"].dropna()
                    else:
                        # multi-symbol -> per-ticker MultiIndex (sym, field)
                        closes = data[sym]["Close"].dropna()
                    if len(closes):
                        prices[sym] = float(closes.iloc[-1])
                except Exception:
                    # one bad symbol must not poison the rest
                    continue
        except Exception as e:
            print(f"# yfinance batch fetch failed: {e}", file=sys.stderr)

    # Bug-2 fix 2026-05-18: fail loud on a non-empty non-crypto symbol set that
    # yields ZERO prices — almost always a symbol-format mismatch (EURUSD vs
    # EURUSD=X) or a yfinance outage, NOT a real "all stayed open" result.
    # In APPLY mode this raises (refuse to mass-skip). In DRY-RUN mode it emits
    # a GitHub Actions `::warning::` annotation so the silent-pass shows up in
    # the workflow run summary instead of disappearing into stderr noise.
    if asset_class != "CRYPTO" and symbols and not prices:
        msg = (f"active_picks_sync: 0/{len(symbols)} {asset_class} prices "
               f"fetched — likely symbol-format mismatch (e.g. EURUSD vs "
               f"EURUSD=X) or yfinance outage. Sample: {symbols[:5]}")
        if os.environ.get("ACTIVE_PICKS_SYNC_APPLY") == "1":
            print(f"# FAIL-LOUD: {msg}", file=sys.stderr)
            raise RuntimeError(
                f"{msg} — APPLY mode, refusing to proceed (would mass-skip).")
        # DRY-RUN: surface as a workflow annotation, not a silent green pass.
        print(f"::warning title=active_picks_sync zero-prices::{msg}")
        print(f"# WARN (dry-run): {msg}", file=sys.stderr)

    return prices


def apply_transition(cur, transition: dict) -> dict:
    """PR-#2 live writer: persist one transition to MySQL at_raw_picks.

    Atomic per-row UPDATE on the pick id. Idempotent: only UPDATEs rows
    that are still status='OPEN' or NULL (won't double-close). Returns
    a result dict with rowcount + error if any.
    """
    pid = transition.get("id")
    if pid is None:
        return {"ok": False, "id": None, "error": "missing_id"}
    try:
        sql = (
            "UPDATE at_raw_picks SET "
            "status=%s, exit_reason=%s, exit_price=%s, "
            "pnl_pct=%s, closed_at=NOW() "
            "WHERE id=%s AND (status IN ('OPEN','ACTIVE') OR status IS NULL)"
        )
        cur.execute(sql, (
            transition.get("new_status"),
            transition.get("exit_reason"),
            transition.get("exit_price"),
            transition.get("pnl_pct"),
            pid,
        ))
        return {"ok": True, "id": pid, "rowcount": cur.rowcount}
    except Exception as exc:
        return {"ok": False, "id": pid, "error": str(exc)[:200]}


def append_to_closed_picks_json(transitions: list[dict]) -> dict:
    """PR-#2 live writer: append closed entries to alpha_engine/data/closed_picks.json.

    Dedup by id against existing entries. Atomic write via temp + rename.
    """
    path = ROOT / "alpha_engine" / "data" / "closed_picks.json"
    existing = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8")) or []
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    seen = {str(p.get("id")) for p in existing if isinstance(p, dict) and p.get("id") is not None}
    appended = 0
    for t in transitions:
        tid = str(t.get("id"))
        if tid in seen:
            continue
        entry = {
            "id": t.get("id"),
            "symbol": t.get("symbol"),
            "direction": t.get("direction"),
            "asset_class": t.get("asset_class"),
            "strategy": t.get("strategy"),
            "entry_price": t.get("entry_price"),
            "exit_price": t.get("exit_price"),
            "pnl_pct": t.get("pnl_pct"),
            "status": t.get("new_status"),
            "exit_reason": t.get("exit_reason"),
            "closed_at": datetime.now(timezone.utc).isoformat(),
            # 2026-05-20: ALSO emit resolved_at so edge_stability_harness can see this pick
            # (peer freebuff discovery: quan_engine_scalp 5293 picks invisible because writer
            # never set resolved_at; harness reads resolved_at primarily)
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "_writer": "active_picks_sync_live",
        }
        existing.append(entry)
        seen.add(tid)
        appended += 1
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)
    return {"appended": appended, "total_after": len(existing)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--asset-class", default="CRYPTO",
                   help="Which asset class to dry-run (default CRYPTO)")
    p.add_argument("--max-symbols", type=int, default=1000,
                   help="Max unique symbols to fetch live prices for (default 1000 per Cerebras Q4)")
    p.add_argument("--max-rows", type=int, default=5000,
                   help="Max OPEN rows to read from at_raw_picks (default 5000)")
    p.add_argument("--max-hold-hours", type=int, default=None,
                   help="Override per-class max-hold-hours (default per DEFAULT_MAX_HOLD_HOURS)")
    p.add_argument("--out", default=None,
                   help="Output JSON path (default reports/active_picks_sync_dryrun_<UTC>.json)")
    # PR-#2: live-writer flip. Default OFF; explicit --apply opt-in.
    # Also gated on env ACTIVE_PICKS_SYNC_APPLY=1 to prevent accidental
    # CLI runs in unintended environments.
    p.add_argument("--apply", action="store_true",
                   help="Persist transitions: MySQL UPDATE at_raw_picks + "
                        "append alpha_engine/data/closed_picks.json. "
                        "Default OFF (dry-run). Also requires env "
                        "ACTIVE_PICKS_SYNC_APPLY=1.")
    args = p.parse_args()
    apply_writes = bool(args.apply) and os.environ.get("ACTIVE_PICKS_SYNC_APPLY") == "1"

    ac = args.asset_class.upper().strip()
    win_threshold = PNL_WIN_THRESHOLD_BY_CLASS.get(ac, 0.0005)
    max_hold = args.max_hold_hours or DEFAULT_MAX_HOLD_HOURS.get(ac, 168)

    print(f"# active_picks_sync DRY-RUN — asset_class={ac} "
          f"win_threshold={win_threshold} max_hold_hours={max_hold}",
          file=sys.stderr)

    try:
        conn = connect()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor(pymysql.cursors.DictCursor)
    rows = fetch_active_picks(cur, ac, max_rows=args.max_rows)
    # Keep cursor + connection open if we will apply writes after verdicts
    if not apply_writes:
        cur.close()
        conn.close()
    print(f"# active_rows_fetched={len(rows)}", file=sys.stderr)

    if not rows:
        print(f"# nothing to evaluate; bailing", file=sys.stderr)
        return

    # Dedupe symbols for price fetch
    symbols = sorted({r["symbol"] for r in rows if r.get("symbol")})
    symbols = symbols[: args.max_symbols]
    print(f"# unique_symbols={len(symbols)} (capped at {args.max_symbols})",
          file=sys.stderr)

    prices = fetch_live_prices(symbols, ac)
    print(f"# prices_fetched={len(prices)} of {len(symbols)}", file=sys.stderr)

    # Compute per-row verdicts
    transitions = []
    stay_open = 0
    no_price = 0
    by_reason = defaultdict(int)
    for r in rows:
        sym = r.get("symbol")
        if sym not in prices:
            no_price += 1
            continue
        verdict = compute_verdict(r, prices[sym], max_hold, win_threshold)
        if verdict is None:
            stay_open += 1
        else:
            transitions.append(verdict)
            by_reason[verdict["exit_reason"]] += 1

    # PR-#2 live-writer execution path
    apply_results = None
    if apply_writes and transitions:
        print(f"# APPLY MODE: persisting {len(transitions)} transitions",
              file=sys.stderr)
        try:
            n_ok = 0
            n_err = 0
            err_samples: list[dict] = []
            applied_ids: set[str] = set()
            for t in transitions:
                r = apply_transition(cur, t)
                if r.get("ok") and r.get("rowcount", 0) >= 1:
                    n_ok += 1
                    applied_ids.add(str(t.get("id")))
                else:
                    n_err += 1
                    if len(err_samples) < 10:
                        err_samples.append(r)
            conn.commit()
            # Bug-1 fix 2026-05-18: only append rows whose DB UPDATE actually
            # matched a row — prevents closed_picks.json / at_raw_picks divergence.
            json_result = append_to_closed_picks_json(
                [t for t in transitions if str(t.get("id")) in applied_ids])
            apply_results = {
                "db_updates_attempted": len(transitions),
                "db_updates_ok": n_ok,
                "db_updates_skipped_or_failed": n_err,
                "db_err_samples": err_samples,
                "closed_picks_appended": json_result["appended"],
                "closed_picks_total_after": json_result["total_after"],
            }
            print(f"# applied: db_ok={n_ok} db_skipped={n_err} "
                  f"json_appended={json_result['appended']}",
                  file=sys.stderr)
        except Exception as exc:
            apply_results = {"fatal_error": str(exc)[:300]}
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_class": ac,
        "mode": "APPLY (writes persisted)" if apply_writes else "DRY_RUN (no writes)",
        "apply_results": apply_results,
        "config": {
            "win_threshold": win_threshold,
            "max_hold_hours": max_hold,
            "max_symbols": args.max_symbols,
            "max_rows": args.max_rows,
        },
        "summary": {
            "active_rows_fetched": len(rows),
            "unique_symbols": len(symbols),
            "prices_fetched": len(prices),
            "would_close_total": len(transitions),
            "by_reason": dict(by_reason),
            "would_stay_open": stay_open,
            "no_price_available": no_price,
        },
        "transitions": transitions[:500],   # cap detail payload
        "transitions_truncated_at": 500 if len(transitions) > 500 else None,
        "nfa": "DRY-RUN ONLY — no MySQL UPDATE, no JSON append. "
               "Wire writes in PR #2 after this output looks sane.",
    }

    if args.out:
        out_path = ROOT / args.out
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = ROOT / f"reports/active_picks_sync_dryrun_{ac}_{stamp}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes)",
          file=sys.stderr)
    print(f"# would_close={len(transitions)} would_stay_open={stay_open} "
          f"no_price={no_price}", file=sys.stderr)
    for reason, n in by_reason.items():
        print(f"#   {reason}: {n}", file=sys.stderr)


if __name__ == "__main__":
    main()
