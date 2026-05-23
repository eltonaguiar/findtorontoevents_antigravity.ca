#!/usr/bin/env python3
"""Reproduction script for docs/forensics/dormant_ml_strategies_2026-04-13.md.

Read-only forensic. Stdlib only. Run from repo root:

    python tools/forensic/dormant_ml_reproduce.py

For each of ``ml_enhanced_FETUSDT_1d_B_lightgbm`` and
``ml_enhanced_RENDERUSDT_4h_D_ensemble_stack`` this script:

1. Loads every ledger that can reference them
   (alpha_engine/data/{closed,active}_picks.json and
   ml_crypto_predictor/enhanced_models/live_picks/{active,closed,all}_picks*.json).
2. Counts rows, first/last timestamps, 48h/7d windows, raw WR, profit factor.
3. Detects duplicate closed-picks clusters by
   (strategy, symbol, entry_price, exit_price, pnl_pct).
4. Checks whether the joblib model files exist on disk and prints size/mtime.

The script makes **no writes** and imports nothing outside the Python stdlib.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

TARGETS = (
    "ml_enhanced_FETUSDT_1d_B_lightgbm",
    "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack",
)

MODEL_FILES = (
    os.path.join(
        REPO_ROOT,
        "ml_crypto_predictor",
        "enhanced_models",
        "models",
        "FETUSDT_1d_B_lightgbm.joblib",
    ),
    os.path.join(
        REPO_ROOT,
        "ml_crypto_predictor",
        "enhanced_models",
        "models",
        "RENDERUSDT_4h_D_ensemble_stack.joblib",
    ),
)

LEDGERS = [
    (
        "alpha_engine/data/closed_picks.json",
        os.path.join(REPO_ROOT, "alpha_engine", "data", "closed_picks.json"),
        "closed",
    ),
    (
        "alpha_engine/data/active_picks.json",
        os.path.join(REPO_ROOT, "alpha_engine", "data", "active_picks.json"),
        "active",
    ),
    (
        "ml_crypto_predictor/.../live_picks/closed_picks.json",
        os.path.join(
            REPO_ROOT,
            "ml_crypto_predictor",
            "enhanced_models",
            "live_picks",
            "closed_picks.json",
        ),
        "mlcp_closed",
    ),
    (
        "ml_crypto_predictor/.../live_picks/active_picks.json",
        os.path.join(
            REPO_ROOT,
            "ml_crypto_predictor",
            "enhanced_models",
            "live_picks",
            "active_picks.json",
        ),
        "mlcp_active",
    ),
    (
        "ml_crypto_predictor/.../live_picks/all_picks_log.json",
        os.path.join(
            REPO_ROOT,
            "ml_crypto_predictor",
            "enhanced_models",
            "live_picks",
            "all_picks_log.json",
        ),
        "mlcp_log",
    ),
]


TS_KEYS = (
    "closed_at",
    "close_time",
    "resolved_at",
    "exit_time",
    "timestamp",
    "created_at",
    "generated_at",
    "entry_time",
)


def load_rows(path: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  !! failed to load {path}: {e}")
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def parse_ts(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(float(v), tz=timezone.utc)
        except Exception:
            return None
    if not isinstance(v, str):
        return None
    s = v.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def row_ts(row: dict):
    for k in TS_KEYS:
        if k in row and row.get(k):
            dt = parse_ts(row.get(k))
            if dt is not None:
                return dt
    return None


def row_strategy(row: dict) -> str:
    for k in ("strategy", "source_system", "source", "strategy_name"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    model_variant = row.get("model_variant")
    if isinstance(model_variant, str) and model_variant:
        return f"ml_enhanced_{model_variant}"
    return "UNKNOWN"


def row_pnl(row: dict):
    v = row.get("pnl_pct")
    if v is None:
        v = row.get("actual_pnl_pct")
    if v is None:
        v = row.get("pnl")
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def profit_factor(pnls):
    gw = sum(p for p in pnls if p > 0)
    gl = -sum(p for p in pnls if p < 0)
    if gl <= 0:
        return float("inf") if gw > 0 else None
    return gw / gl


def window_count(trades, now, days):
    cutoff = now - timedelta(days=days)
    return [t for t in trades if t[0] >= cutoff]


def analyze_strategy(strategy: str, now: datetime) -> None:
    print(f"\n{'=' * 72}\n{strategy}\n{'=' * 72}")

    per_ledger_rows: dict = {}
    for label, path, tag in LEDGERS:
        rows = load_rows(path)
        matches = [r for r in rows if row_strategy(r) == strategy]
        per_ledger_rows[tag] = matches
        print(
            f"  {label}: total={len(rows):>6}  "
            f"matches={len(matches):>4}"
        )
        if matches:
            tss = [row_ts(r) for r in matches]
            tss_ok = sorted(t for t in tss if t is not None)
            if tss_ok:
                print(
                    f"     first ts: {tss_ok[0].isoformat()}   "
                    f"last ts: {tss_ok[-1].isoformat()}"
                )
                hours_since = (now - tss_ok[-1]).total_seconds() / 3600
                print(f"     last ts age: {hours_since:.1f}h before now")

    # Metrics on alpha_engine closed_picks (what strategy_trust.py sees)
    closed = per_ledger_rows.get("closed", [])
    trades = []
    for r in closed:
        pnl = row_pnl(r)
        dt = row_ts(r)
        if pnl is None or dt is None:
            continue
        trades.append((dt, pnl, r))
    trades.sort(key=lambda t: t[0])

    if trades:
        pnls = [p for _, p, _ in trades]
        wins = sum(1 for p in pnls if p > 0)
        pf = profit_factor(pnls)
        pf_s = f"{pf:.2f}" if pf is not None and not math.isinf(pf) else str(pf)
        print(
            f"\n  alpha_engine/closed_picks metrics:  n={len(trades)} "
            f"wins={wins}  raw_wr={wins / len(trades):.3f}  "
            f"pf={pf_s}"
        )

        last_48h = window_count(trades, now, 2)
        last_7d = window_count(trades, now, 7)
        print(
            f"  last_48h: n={len(last_48h)}  "
            f"pf={profit_factor([t[1] for t in last_48h])}  "
            f"wins={sum(1 for t in last_48h if t[1] > 0)}"
        )
        print(
            f"  last_7d:  n={len(last_7d)}  "
            f"pf={profit_factor([t[1] for t in last_7d])}  "
            f"wins={sum(1 for t in last_7d if t[1] > 0)}"
        )

        # Duplicate-cluster detection: group by (entry_price, exit_price, pnl_pct)
        buckets = defaultdict(list)
        for _, _, r in trades:
            key = (
                r.get("entry_price"),
                r.get("exit_price"),
                round(float(r.get("pnl_pct") or 0), 6),
            )
            buckets[key].append(r)
        dup_clusters = [
            (key, rows) for key, rows in buckets.items() if len(rows) > 1
        ]
        if dup_clusters:
            print("\n  DUPLICATE CLUSTERS in alpha_engine/closed_picks:")
            for key, rows in sorted(
                dup_clusters, key=lambda x: -len(x[1])
            ):
                entry, exit_, pnl = key
                print(
                    f"    {len(rows):>3}× entry={entry} exit={exit_} "
                    f"pnl={pnl:+.4f}"
                )
                dates = sorted(
                    {(r.get("entry_date") or "")[:10] for r in rows}
                )
                print(f"         distinct entry_date values: {dates}")
        else:
            print("\n  DUPLICATE CLUSTERS: none")

        # Exit reason histogram over the full history vs recent 7d
        all_reasons = Counter(r.get("exit_reason") for _, _, r in trades)
        recent_reasons = Counter(
            r.get("exit_reason") for _, _, r in last_7d
        )
        print(f"\n  exit_reason (all):   {dict(all_reasons)}")
        print(f"  exit_reason (7d):    {dict(recent_reasons)}")

    # mlcp all_picks_log status distribution (how alive the upstream pipeline is)
    log_rows = per_ledger_rows.get("mlcp_log", [])
    if log_rows:
        statuses = Counter(r.get("status") for r in log_rows)
        outcomes = Counter(r.get("outcome") for r in log_rows)
        print(
            f"\n  mlcp/all_picks_log: n={len(log_rows)} "
            f"statuses={dict(statuses)}"
        )
        print(f"                      outcomes={dict(outcomes)}")
        generated = sorted(
            r.get("generated_at") for r in log_rows if r.get("generated_at")
        )
        if generated:
            print(
                f"                      first gen: {generated[0]}\n"
                f"                      last  gen: {generated[-1]}"
            )


def check_model_files() -> None:
    print("\n" + "=" * 72)
    print("Model file audit")
    print("=" * 72)
    for path in MODEL_FILES:
        if not os.path.exists(path):
            print(f"  MISSING: {path}")
            continue
        st = os.stat(path)
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        print(
            f"  OK:      {os.path.basename(path)}  "
            f"size={st.st_size:>10} bytes  "
            f"mtime={mtime.isoformat()}"
        )


def main() -> int:
    now = datetime.now(tz=timezone.utc)
    print(
        f"Dormant ML forensic reproduce — now={now.isoformat()} "
        f"repo_root={REPO_ROOT}"
    )
    for strat in TARGETS:
        analyze_strategy(strat, now)
    check_model_files()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
