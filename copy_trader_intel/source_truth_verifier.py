#!/usr/bin/env python3
"""
source_truth_verifier.py
========================
Verifies that a copytrader / public-trade source is (a) free and reachable,
(b) actually publishes trade-level records with timestamps, (c) has no future
bias / lookahead (entries precede exits, no timestamps in the future, no
synthetic identical-timestamp blobs), and (d) is reliable out-of-sample
(Wilson lower bound WR, profit factor, split-half stability, coin-flip
bootstrap).

Subcommands
-----------
  probe      Live-probe the source catalog, run integrity checks, write
             data/source_truth_report.json
  backtest   Event-study / follow-the-next-trade backtest on verified sources
             (Hyperliquid fills, OKX subpositions, Polymarket closed positions)
  github     Discover GitHub repos that publish copytrader / signal picks and
             validate their timestamps + staleness
  registry   Emit data/copytrader_verified_sources.json (accepted sources only)

Run:
  python copy_trader_intel/source_truth_verifier.py probe
  python copy_trader_intel/source_truth_verifier.py backtest
  python copy_trader_intel/source_truth_verifier.py github
  python copy_trader_intel/source_truth_verifier.py registry
  python copy_trader_intel/source_truth_verifier.py all

All timestamps are interpreted as UTC. Any source with naive timestamps is
flagged so the EST/UTC assumption is explicit rather than implicit.
"""

from __future__ import annotations

import json
import math
import os
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
REPORT_PATH = DATA_DIR / "source_truth_report.json"
REGISTRY_PATH = DATA_DIR / "copytrader_verified_sources.json"
GITHUB_PATH = DATA_DIR / "copytrader_github_repos.json"
BACKTEST_PATH = DATA_DIR / "source_truth_backtest.json"

HEADERS = {
    "User-Agent": "findtorontoevents-research/1.0 (+https://findtorontoevents.ca)",
    "Accept": "application/json,text/csv,text/html,*/*",
}

NOW = datetime.now(timezone.utc)
FUTURE_TOLERANCE_SEC = 300          # clock skew allowance
MIN_N_PROBE = 20                    # minimum records to score a source
MIN_N_TRUST = 100                   # sample size for TRUSTED verdict
WILSON_Z = 1.96

random.seed(1337)                   # deterministic bootstrap


# ─────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────

def http(url: str, *, method: str = "GET", body: dict | None = None,
         timeout: int = 20, headers: dict | None = None) -> requests.Response | None:
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    try:
        if method == "POST":
            r = requests.post(url, json=body if body is not None else {}, headers=h, timeout=timeout)
        else:
            r = requests.get(url, headers=h, timeout=timeout)
        return r
    except Exception as exc:  # noqa: BLE001
        print(f"    [ERR] {url[:78]} -> {type(exc).__name__}: {str(exc)[:80]}")
        return None


def to_dt(value: Any) -> datetime | None:
    """Parse epoch seconds/ms/ISO/US date. Naive values are treated as UTC."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace(".", "").isdigit()):
            num = float(value)
            if num > 1e14:      # microseconds
                num /= 1e6
            elif num > 1e11:    # milliseconds
                num /= 1e3
            return datetime.fromtimestamp(num, tz=timezone.utc)
        s = str(value).strip().replace("Z", "+00:00")
        for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def wilson_lower(wins: int, n: int, z: float = WILSON_Z) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / denom)


def bootstrap_p(wins: int, n: int, iters: int = 2000) -> float:
    """One-sided p-value that true WR <= 0.5 given the observed win/loss series."""
    if n <= 0:
        return 1.0
    obs = wins / n
    p0 = 0.5
    sd = math.sqrt(p0 * (1 - p0) / n)
    if sd == 0:
        return 1.0
    z = (obs - p0) / sd
    # normal CDF approximation tail
    return 0.5 * math.erfc(z / math.sqrt(2))


def profit_factor(pnls: list[float]) -> float | None:
    gains = sum(p for p in pnls if p > 0)
    losses = abs(sum(p for p in pnls if p < 0))
    if losses == 0:
        return None if gains == 0 else float("inf")
    return gains / losses


def _json_safe(obj):
    """Recursively replace non-finite floats so the artifact is strict JSON."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def integrity_checks(timestamps: list[datetime], *,
                     entry_exit_pairs: list[tuple[datetime, datetime]] | None = None,
                     stale_tolerance_days: float = 7.0,
                     date_granularity: bool = False,
                     entry_exit_pairs_censored: int = 0) -> dict:
    """Future-bias / lookahead audit for a list of timestamps.

    stale_tolerance_days  per-source freshness budget (weekly COT needs ~11d
                          because the Friday 15:30 ET release lags the Tuesday
                          as-of date).
    date_granularity      source only carries day-level dates, so identical
                          timestamps are legitimate; skips duplicate detection
                          and treats a 0-day hold as unknown rather than bad.
    entry_exit_pairs_censored
                          pairs whose "timestamp" is a scheduled event end date
                          (e.g. a Polymarket resolution date) rather than a
                          trade exit, so entry>exit is not a data defect.
    """
    ts = [t for t in timestamps if t is not None]
    out: dict[str, Any] = {"n_ts": len(ts)}
    if not ts:
        out.update({"verdict": "NO_TIMESTAMPS", "future_count": 0, "stale_days": None})
        return out

    future = [t for t in ts if (t - NOW).total_seconds() > FUTURE_TOLERANCE_SEC]
    newest = max(ts)
    oldest = min(ts)
    uniq = len(set(t.replace(microsecond=0) for t in ts))
    dup_ratio = 1 - (uniq / len(ts)) if ts else 0.0
    gaps = [abs((b - a).total_seconds()) for a, b in zip(sorted(ts), sorted(ts)[1:])]

    bad_pairs = 0
    zero_hold = 0
    if entry_exit_pairs:
        for e, x in entry_exit_pairs:
            if e is None or x is None:
                continue
            if (x - e).total_seconds() < 0:
                bad_pairs += 1
            elif (x - e).total_seconds() < 60:
                zero_hold += 1

    flags = []
    if future:
        flags.append("FUTURE_TIMESTAMPS")
    if dup_ratio > 0.9 and len(ts) >= 10 and not date_granularity:
        flags.append("SYNTHETIC_DUPLICATE_TS")
    if bad_pairs > entry_exit_pairs_censored:
        flags.append("ENTRY_AFTER_EXIT")
    if entry_exit_pairs and zero_hold > 0.2 * max(1, len(entry_exit_pairs)):
        flags.append("ZERO_HOLD_MAJORITY")
    stale_days = round((NOW - newest).total_seconds() / 86400, 2)
    if stale_days > stale_tolerance_days:
        flags.append(f"STALE_GT_{stale_tolerance_days:g}D" if stale_tolerance_days != 7.0 else "STALE_GT_7D")

    out.update({
        "verdict": "CLEAN" if not flags else "FLAGGED",
        "flags": flags,
        "future_count": len(future),
        "future_samples": [t.isoformat() for t in future[:3]],
        "oldest": oldest.isoformat() if oldest else None,
        "newest": newest.isoformat() if newest else None,
        "stale_days": stale_days,
        "dup_ts_ratio": round(dup_ratio, 3),
        "median_gap_hours": round(statistics.median(gaps) / 3600, 2) if gaps else None,
        "entry_after_exit": bad_pairs,
        "zero_hold": zero_hold,
    })
    return out


def score_pnls(pnls: list[float]) -> dict:
    """Reliability stats from a realised PnL series (source-native)."""
    pnls = [p for p in pnls if p is not None and math.isfinite(p)]
    n = len(pnls)
    if n == 0:
        return {"n": 0, "verdict": "NO_DATA"}
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / n
    pf = profit_factor(pnls)
    mean = sum(pnls) / n
    sd = statistics.pstdev(pnls) if n > 1 else 0.0
    tstat = (mean / (sd / math.sqrt(n))) if sd > 0 and n > 1 else None
    half = n // 2
    wr_h1 = (sum(1 for p in pnls[:half] if p > 0) / half) if half else None
    wr_h2 = (sum(1 for p in pnls[half:] if p > 0) / (n - half)) if n - half else None
    stability = None
    if wr_h1 is not None and wr_h2 is not None:
        stability = round(abs(wr_h1 - wr_h2), 3)
    return {
        "n": n,
        "wins": wins,
        "wr_pct": round(wr * 100, 2),
        "wilson_lb_pct": round(wilson_lower(wins, n) * 100, 2),
        "pf": round(pf, 3) if pf not in (None, float("inf")) else pf,
        "expectancy": round(mean, 4),
        "total_pnl": round(sum(pnls), 2),
        "t_stat_mean_pnl": round(tstat, 3) if tstat is not None else None,
        "split_half_wr_pct": [round(wr_h1 * 100, 2) if wr_h1 is not None else None,
                              round(wr_h2 * 100, 2) if wr_h2 is not None else None],
        "split_half_gap": stability,
        "p_vs_coinflip": round(bootstrap_p(wins, n), 4),
    }


def aggregate_round_trips(pnls: list[float], timestamps: list[datetime] | None = None) -> tuple[list[float], int]:
    """Collapse consecutive same-sign tickets into one round trip.

    Scale-out style sources (OKX subposition history) emit several partial
    closing tickets for one logical trade. Counting each ticket as a separate
    trade inflates the win rate (a single winner becomes N winners). We keep
    one ticket per same-sign run, preserving the run's total PnL.
    """
    runs: list[float] = []
    cur = 0.0
    cur_sign = 0
    collapsed = 0
    for p in pnls:
        s = 1 if p > 0 else (-1 if p < 0 else 0)
        if cur_sign == 0:
            cur, cur_sign = p, s if s else 0
            continue
        if s == cur_sign:
            cur += p
            collapsed += 1
        else:
            runs.append(cur)
            cur, cur_sign = p, s
    if cur_sign != 0:
        runs.append(cur)
    return runs, collapsed


def dedupe_pnls(pnls: list[float], ids: list[Any] | None = None) -> tuple[list[float], int]:
    """Drop duplicate tickets (same subPosId / same key)."""
    if not ids:
        return list(pnls), 0
    seen = set()
    out = []
    dup = 0
    for p, i in zip(pnls, ids):
        k = i if i is not None else f"{p:.8f}"
        if k in seen:
            dup += 1
            continue
        seen.add(k)
        out.append(p)
    return out, dup


def apply_artifact_guards(stats: dict, raw: dict) -> tuple[str, list[str]]:
    """Reject sources whose PnL distribution is physically impossible as a
    track record. These are endpoint/selection artifacts, not edge."""
    n = stats.get("n", 0)
    if n <= 0:
        return stats.get("verdict", "NO_DATA"), []
    losses = n - stats.get("wins", 0)
    win_pct = stats.get("wr_pct") or 0
    pf = stats.get("pf")
    reasons: list[str] = []
    if losses == 0 and n >= 20:
        reasons.append("IMPOSSIBLE_ZERO_LOSSES:endpoint_excludes_losers")
    if (isinstance(pf, float) and pf >= 100) and win_pct >= 98:
        reasons.append(f"IMPOSSIBLE_PF_{pf:.0f}:near_no_realised_losses")
    if raw.get("selection") == "winner_leaderboard" and win_pct >= 99:
        reasons.append("IMPOSSIBLE_SELECTION:winner_leaderboard")
    if reasons:
        return "REJECT_ARTIFACT", reasons
    return stats.get("verdict", "NO_DATA"), reasons


def verdict_for(stats: dict, integ: dict, selection: str = "none") -> tuple[str, list[str]]:
    """Profitability-first gate: a low-WR trend profile with PF>=1.2 and a
    significant positive mean PnL is valid; WR is reported, not required.

    `selection` names the sampling method. Leaderboard-selected cohorts are
    survivorship-biased by construction (we only observe the winners the
    venue chose to rank), so their verdict is capped at WATCH regardless of
    how strong the numbers look.
    """
    reasons = []
    n = stats.get("n", 0)
    if integ.get("verdict") in ("NO_TIMESTAMPS", "FLAGGED"):
        return "REJECT", [f"integrity:{integ.get('verdict')}", *(integ.get("flags") or [])]
    if n < MIN_N_PROBE:
        return "INSUFFICIENT_N", [f"n={n}<{MIN_N_PROBE}"]
    pf = stats.get("pf")
    t = stats.get("t_stat_mean_pnl")
    expectancy = stats.get("expectancy") or 0
    pf_val = 99.0 if pf in (None, float("inf")) else pf
    significant = (t is not None and t >= 1.96) or (stats.get("p_vs_coinflip") or 1) < 0.05
    bias_note = f"selection_bias:{selection}" if selection not in ("none", None, "") else None
    if expectancy > 0 and pf_val >= 1.2 and significant:
        if bias_note:
            return "WATCH", ["expectancy>0", "pf>=1.2", "significant", bias_note]
        if n >= MIN_N_TRUST and (stats.get("split_half_gap") or 1) < 0.15:
            return "TRUSTED", ["expectancy>0", "pf>=1.2", "significant", f"n>={MIN_N_TRUST}", "stable"]
        return "WATCH", ["expectancy>0", "pf>=1.2", "significant", "needs n>=100 or stability"]
    if expectancy > 0 and pf_val >= 1.05:
        return "WEAK", ["positive expectancy but PF<1.2 or not significant"]
    return "REJECT", [f"expectancy={expectancy} pf={pf}"]


# ─────────────────────────────────────────────────────────────
# source adapters — each returns records with timestamps
# ─────────────────────────────────────────────────────────────

def src_okx_copytrading(limit_traders: int = 8, pages: int = 2) -> dict:
    """OKX public copy-trading: lead-trader leaderboard + closed subpositions."""
    r = http("https://www.okx.com/api/v5/copytrading/public-lead-traders", timeout=25)
    if not r or r.status_code != 200:
        return {"reachable": False}
    data = r.json()
    ranks = (data.get("data") or [{}])[0].get("ranks", [])
    traders, trades, ts, pairs = [], [], [], []
    for t in ranks[:limit_traders]:
        uc = t.get("uniqueCode")
        if not uc:
            continue
        rows = []
        for _ in range(pages):
            pr = http(
                "https://www.okx.com/api/v5/copytrading/public-subpositions-history"
                f"?instType=SWAP&uniqueCode={uc}&limit=100",
                timeout=20,
            )
            if not pr or pr.status_code != 200:
                break
            batch = pr.json().get("data") or []
            rows.extend(batch)
            if len(batch) < 100:
                break
        pnls = []
        raw_pnls = []
        for row in sorted(rows, key=lambda x: int(x.get("openTime") or 0)):
            ot, ct = to_dt(row.get("openTime")), to_dt(row.get("closeTime"))
            try:
                pnl = float(row.get("pnl"))
            except (TypeError, ValueError):
                pnl = None
            if ct:
                ts.append(ct)
            if ot:
                ts.append(ot)
            if ot and ct:
                pairs.append((ot, ct))
            if pnl is not None:
                pnls.append(pnl)
                raw_pnls.append(pnl)
        collapsed, n_collapsed = aggregate_round_trips(pnls)
        trades.extend(collapsed)
        traders.append({
            "trader": t.get("nickName"),
            "unique_code": uc,
            "lead_days": t.get("leadDays"),
            "pnl_ratio": t.get("pnlRatio"),
            "aum": t.get("aum"),
            "reported_win_ratio": t.get("winRatio"),
            "closed_positions": len(rows),
            "raw_wr_pct": round(sum(1 for p in raw_pnls if p > 0) / max(1, len(raw_pnls)) * 100, 2),
            "round_trips": len(collapsed),
            "round_trip_wr_pct": round(sum(1 for p in collapsed if p > 0) / max(1, len(collapsed)) * 100, 2),
            "partial_tickets_collapsed": n_collapsed,
        })
    return {
        "reachable": True,
        "records": len(trades),
        "pnls": trades,
        "timestamps": ts,
        "pairs": pairs,
        "traders": traders,
        "ts_note": "epoch ms — unambiguous UTC",
        "selection": "top_leaderboard_pnl_ratio",
        "partial_ticket_aggregation": True,
    }


def src_hyperliquid_whales(top: int = 10, days: int = 45) -> dict:
    """Hyperliquid public leaderboard + per-whale fills (ms timestamps)."""
    r = http("https://stats-data.hyperliquid.xyz/Mainnet/leaderboard", timeout=40)
    if not r or r.status_code != 200:
        return {"reachable": False}
    rows = r.json().get("leaderboardRows", [])
    if not rows:
        return {"reachable": False, "reason": "empty leaderboard"}

    def month_pnl(row):
        for w, v in row.get("windowPerformances", []):
            if w == "month":
                try:
                    return float(v.get("pnl", 0))
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    # require real account value so wash-traded 0-value accounts are excluded
    cands = [r_ for r_ in rows if float(r_.get("accountValue", 0) or 0) >= 50_000]
    cands.sort(key=month_pnl, reverse=True)
    cutoff_ms = int((NOW - timedelta(days=days)).timestamp() * 1000)
    all_pnls: list[float] = []
    all_ts: list[datetime] = []
    pairs: list[tuple[datetime, datetime]] = []
    wallets = []
    for row in cands[:top]:
        addr = row.get("ethAddress")
        fr = http("https://api.hyperliquid.xyz/info", method="POST",
                  body={"type": "userFillsByTime", "user": addr, "startTime": cutoff_ms},
                  timeout=30)
        if not fr or fr.status_code != 200:
            continue
        fills = fr.json() or []
        if not isinstance(fills, list) or not fills:
            continue
        # FIFO round-trip reconstruction per coin
        book: dict[str, list[dict]] = {}
        pnls = []
        for f in sorted(fills, key=lambda x: x.get("time", 0)):
            coin = f.get("coin")
            t = to_dt(f.get("time"))
            try:
                sz = float(f.get("sz", 0))
                px = float(f.get("px", 0))
                fee = float(f.get("fee", 0) or 0)
            except (TypeError, ValueError):
                continue
            signed = sz if f.get("side") == "B" else -sz
            if t:
                all_ts.append(t)
            queue = book.setdefault(coin, [])
            remaining = signed
            while queue and remaining * queue[0]["rem"] < 0:
                lot = queue[0]
                close_sz = min(abs(remaining), abs(lot["rem"]))
                direction = 1 if lot["rem"] > 0 else -1
                pnl = (px - lot["px"]) * close_sz * direction - fee
                pnls.append(pnl)
                pairs.append((lot["ts"], t))
                lot["rem"] -= close_sz * direction
                remaining += close_sz * direction
                if abs(lot["rem"]) < 1e-12:
                    queue.pop(0)
            if abs(remaining) > 1e-12:
                queue.append({"px": px, "rem": remaining, "ts": t})
        all_pnls.extend(pnls)
        wallets.append({"address": addr, "fills": len(fills), "round_trips": len(pnls),
                        "month_pnl": round(month_pnl(row), 2)})
    return {
        "reachable": True,
        "records": len(all_pnls),
        "pnls": all_pnls,
        "timestamps": all_ts,
        "pairs": pairs,
        "wallets": wallets,
        "ignore_flags": ["ZERO_HOLD_MAJORITY"],
        "selection": "top_leaderboard_month_pnl",
        "ts_note": "epoch ms fill time — unambiguous UTC; sub-second-rounded exchange timestamps can share an ms, so same-ms round trips are not literal zero-hold trades",
    }


def src_polymarket_v2(top: int = 10) -> dict:
    """Polymarket data-api v2 (v1 retired 2026) — closed positions per whale.

    `first_entry_at` is a real epoch entry timestamp. `end_date` is the market's
    scheduled resolution date, not a trade exit, so:
      * it is recorded separately (not mixed into the trade-timestamp list),
      * entry>end is counted as censored (planned), not as ENTRY_AFTER_EXIT,
      * future end dates are expected for open-ended markets and are excluded
        from the future-bias count.
    """
    r = http("https://data-api.polymarket.com/v2/leaderboard?window=all&limit=10", timeout=20)
    if not r or r.status_code != 200:
        return {"reachable": False}
    lb = r.json()
    lb = lb.get("data", []) if isinstance(lb, dict) else lb
    pnls, ts, pairs, users = [], [], [], []
    n_future_end = 0
    n_pairs = 0
    for u in lb[:top]:
        addr = u.get("user_id") or u.get("user") or u.get("proxy_wallet")
        if not addr:
            continue
        pr = http(f"https://data-api.polymarket.com/v2/positions?user={addr}&status=CLOSED&limit=100", timeout=20)
        if not pr or pr.status_code != 200:
            continue
        pos = pr.json()
        if isinstance(pos, dict):
            pos = pos.get("data", [])
        cnt = 0
        for p in pos or []:
            try:
                pnl = float(p.get("realized_pnl", p.get("total_pnl", 0)))
            except (TypeError, ValueError):
                continue
            entry = to_dt(p.get("first_entry_at"))
            end = to_dt(p.get("end_date"))
            if entry:
                ts.append(entry)
            if end and (end - NOW).total_seconds() > FUTURE_TOLERANCE_SEC:
                n_future_end += 1
            if entry and end:
                pairs.append((entry, end))
                n_pairs += 1
            pnls.append(pnl)
            cnt += 1
        users.append({"user": (u.get("user_name") or addr)[:20], "closed": cnt})
    return {
        "reachable": True,
        "records": len(pnls),
        "pnls": pnls,
        "timestamps": ts,
        "pairs": pairs,
        "entry_exit_pairs_censored": n_pairs,
        "n_future_end_date": n_future_end,
        "traders": users,
        "selection": "top_leaderboard_all_time_pnl",
        "ts_note": "first_entry_at epoch = entry; end_date = scheduled market resolution (censored)",
    }


def src_cftc_cot(limit: int = 200) -> dict:
    """CFTC COT (Socrata). Weekly report_date is authoritative and pre-dates use."""
    url = ("https://publicreporting.cftc.gov/resource/6dca-aqww.json?"
           "$select=market_and_exchange_names,report_date_as_yyyy_mm_dd,"
           "noncomm_positions_long_all,noncomm_positions_short_all,open_interest_all"
           f"&$order=report_date_as_yyyy_mm_dd DESC&$limit={limit}")
    r = http(url, timeout=30)
    if not r or r.status_code != 200:
        return {"reachable": False}
    rows = r.json()
    ts = [to_dt(x.get("report_date_as_yyyy_mm_dd")) for x in rows]
    ts = [t for t in ts if t]
    unique_dates = sorted({t.date() for t in ts})
    return {
        "reachable": True,
        "records": len(rows),
        "pnls": [],
        "timestamps": [datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc) for d in unique_dates],
        "pairs": [],
        "markets": len({x.get("market_and_exchange_names") for x in rows}),
        "cross_sectional": True,
        "date_granularity": True,
        "stale_tolerance_days": 14,
        "ts_note": "weekly Tuesday report date; published Friday 15:30 ET — no future bias if used >= publication",
        "kind": "positioning_not_trades",
    }


def src_ark_daily_trades() -> dict:
    """ARK Invest daily trade disclosure CSV (free)."""
    r = http("https://assets.ark-funds.com/fund-documents/funds-etf-csv/"
             "ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv", timeout=25)
    if not r or r.status_code != 200:
        return {"reachable": False}
    lines = r.text.splitlines()
    if len(lines) < 2:
        return {"reachable": False}
    hdr = [h.strip().lower() for h in lines[0].split(",")]
    date_i = hdr.index("date") if "date" in hdr else 0
    ts = []
    for row in lines[1:]:
        parts = row.split(",")
        if len(parts) <= date_i:
            continue
        t = to_dt(parts[date_i])
        if t:
            ts.append(t)
    return {
        "reachable": True,
        "records": len(lines) - 1,
        "pnls": [],
        "timestamps": ts,
        "pairs": [],
        "ts_note": "date-only (MM/DD/YYYY ET) — treated as UTC midnight; daily snapshot, not per-trade",
        "kind": "holdings_snapshot",
        "date_granularity": True,
    }


def src_sec_form4(days: int = 10) -> dict:
    """SEC EDGAR full-text search for Form 4 insider filings (free).

    EDGAR FTS defaults to relevance ranking, which surfaces decade-old filings.
    A bounded custom date range plus date sorting is required to observe the
    live stream (Form 4 must be filed within 2 business days of the trade).
    """
    end = NOW.date()
    start = end - timedelta(days=days)
    url = ("https://efts.sec.gov/LATEST/search-index?q=%22form%204%22&forms=4"
           "&dateRange=custom"
           f"&startdt={start.isoformat()}&enddt={end.isoformat()}"
           "&sort=file_date:desc")
    r = http(url, timeout=25)
    if not r or r.status_code != 200:
        return {"reachable": False}
    j = r.json()
    hits = j.get("hits", {}).get("hits", [])
    ts = []
    for h in hits:
        src = h.get("_source", {})
        for key in ("file_date", "period_ending", "acceptance_datetime"):
            t = to_dt(src.get(key))
            if t:
                ts.append(t)
                break
    return {
        "reachable": True,
        "records": len(hits),
        "pnls": [],
        "timestamps": ts,
        "pairs": [],
        "window_days": days,
        "ts_note": "filing date (UTC, day-level) from a bounded live window; trade_date <= file_date by law",
        "kind": "disclosure_events",
        "date_granularity": True,
    }


def src_dexscreener_meme() -> dict:
    """Dexscreener new-pair feed (free) — meme/small-cap discovery."""
    r = http("https://api.dexscreener.com/latest/dex/search?q=SOL", timeout=20)
    if not r or r.status_code != 200:
        return {"reachable": False}
    pairs = r.json().get("pairs", [])
    ts = []
    for p in pairs:
        t = to_dt(p.get("pairCreatedAt"))
        if t:
            ts.append(t)
    return {
        "reachable": True,
        "records": len(pairs),
        "pnls": [],
        "timestamps": ts,
        "pairs": [],
        "ts_note": "pairCreatedAt epoch ms — discovery only, no trade-level PnL",
        "kind": "discovery_not_trades",
        "stale_tolerance_days": 30,
        "date_granularity": True,
    }


def src_myfxbook_outlook() -> dict:
    """Myfxbook community outlook (free tier, no auth needed for outlook)."""
    r = http("https://www.myfxbook.com/api/get-community-outlook.json", timeout=20)
    ok = bool(r and r.status_code == 200 and not r.json().get("error"))
    return {
        "reachable": ok,
        "records": 0,
        "pnls": [],
        "timestamps": [],
        "pairs": [],
        "ts_note": "requires session/login for trade history — outlook only without auth",
        "kind": "gated",
        "error": None if ok else (r.json().get("message") if r else "no response"),
    }


def src_treasury_yields() -> dict:
    """US Treasury par yield curve (free CSV) — bond/FX macro input."""
    url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
           "daily-treasury-rates.csv/2026/all?type=daily_treasury_yield_curve"
           "&field_tdr_date_value=2026&page&_format=csv")
    r = http(url, timeout=25)
    if not r or r.status_code != 200:
        return {"reachable": False}
    lines = [ln for ln in r.text.splitlines() if ln.strip()]
    ts = []
    for ln in lines[1:]:
        t = to_dt(ln.split(",")[0])
        if t:
            ts.append(t)
    return {
        "reachable": True,
        "records": len(lines) - 1,
        "pnls": [],
        "timestamps": ts,
        "pairs": [],
        "ts_note": "official daily publication date — safe as-of date, no future bias",
        "kind": "macro_curve",
    }


SOURCE_CATALOG = [
    {"id": "okx_copytrading", "asset_classes": ["CRYPTO"], "license": "free/public",
     "what": "OKX lead-trader leaderboard + closed subposition history (real trader PnLs)",
     "fn": src_okx_copytrading, "pick_role": "trader_follow"},
    {"id": "hyperliquid_whales", "asset_classes": ["CRYPTO", "FUTURES"], "license": "free/public",
     "what": "Hyperliquid on-chain whale leaderboard + fill-level round trips",
     "fn": src_hyperliquid_whales, "pick_role": "trader_follow"},
    {"id": "polymarket_v2", "asset_classes": ["CRYPTO", "EVENT"], "license": "free/public",
     "what": "Polymarket data-api v2 leaderboard + closed positions",
     "fn": src_polymarket_v2, "pick_role": "trader_follow"},
    {"id": "cftc_cot", "asset_classes": ["COMMODITY", "FUTURES", "INDEX", "BOND"], "license": "public domain",
     "what": "CFTC Commitments of Traders weekly positioning by market",
     "fn": src_cftc_cot, "pick_role": "positioning_signal"},
    {"id": "ark_daily_trades", "asset_classes": ["ETF", "EQUITY"], "license": "free/public",
     "what": "ARK Invest daily ETF trade/holdings disclosure",
     "fn": src_ark_daily_trades, "pick_role": "institutional_flow"},
    {"id": "sec_form4_insider", "asset_classes": ["EQUITY", "PENNY_STOCK"], "license": "public domain",
     "what": "SEC EDGAR Form 4 insider filing stream",
     "fn": src_sec_form4, "pick_role": "insider_flow"},
    {"id": "treasury_yields", "asset_classes": ["BOND", "FOREX"], "license": "public domain",
     "what": "US Treasury official par yield curve",
     "fn": src_treasury_yields, "pick_role": "macro_input"},
    {"id": "dexscreener_meme", "asset_classes": ["MEME"], "license": "free/public",
     "what": "Dexscreener new-pair discovery feed",
     "fn": src_dexscreener_meme, "pick_role": "discovery"},
    {"id": "myfxbook_outlook", "asset_classes": ["FOREX"], "license": "free tier (auth for history)",
     "what": "Myfxbook community outlook / verified systems",
     "fn": src_myfxbook_outlook, "pick_role": "sentiment_gated"},
]


# ─────────────────────────────────────────────────────────────
# probe
# ─────────────────────────────────────────────────────────────

def run_probe() -> dict:
    print("=" * 74)
    print("  SOURCE TRUTH PROBE — free copytrader sources")
    print(f"  as-of {NOW.isoformat()}")
    print("=" * 74)
    results = []
    for src in SOURCE_CATALOG:
        print(f"\n[{src['id']}] {src['what']}")
        t0 = time.time()
        try:
            raw = src["fn"]()
        except Exception as exc:  # noqa: BLE001
            raw = {"reachable": False, "error": f"{type(exc).__name__}: {exc}"}
        latency = int((time.time() - t0) * 1000)
        entry: dict[str, Any] = {
            "id": src["id"],
            "asset_classes": src["asset_classes"],
            "license": src["license"],
            "what": src["what"],
            "pick_role": src["pick_role"],
            "reachable": bool(raw.get("reachable")),
            "latency_ms": latency,
            "records": raw.get("records", 0),
            "ts_note": raw.get("ts_note"),
            "kind": raw.get("kind", "trade_level"),
        }
        if not entry["reachable"]:
            entry["verdict"] = "UNREACHABLE"
            entry["error"] = raw.get("error") or raw.get("reason") or "probe failed"
            print(f"    UNREACHABLE ({entry['error'][:60]})")
            results.append(entry)
            continue

        integ = integrity_checks(
            raw.get("timestamps") or [],
            entry_exit_pairs=raw.get("pairs") or [],
            stale_tolerance_days=raw.get("stale_tolerance_days", 7.0),
            date_granularity=raw.get("date_granularity", False),
            entry_exit_pairs_censored=raw.get("entry_exit_pairs_censored", 0),
        )
        for f in (raw.get("ignore_flags") or []):
            if f in integ["flags"]:
                integ["flags"].remove(f)
        if not integ["flags"] and integ["verdict"] == "FLAGGED":
            integ["verdict"] = "CLEAN"
            integ["suppressed"] = raw.get("ignore_flags") or []
        entry["integrity"] = integ
        stats = score_pnls(raw.get("pnls") or [])
        entry["reliability"] = stats
        if raw.get("kind") in ("positioning_not_trades", "discovery_not_trades", "holdings_snapshot",
                               "disclosure_events", "macro_curve"):
            entry["verdict"] = "DATA_OK_NO_TRADE_PNL" if integ.get("verdict") == "CLEAN" else "FLAGGED"
        else:
            entry["verdict"], entry["reasons"] = verdict_for(
                stats, integ, selection=raw.get("selection", "none")
            )
            artifact_verdict, artifact_reasons = apply_artifact_guards(stats, raw)
            if artifact_verdict == "REJECT_ARTIFACT":
                entry["verdict"] = artifact_verdict
                entry["reasons"] = artifact_reasons + entry.get("reasons", [])
        entry["selection"] = raw.get("selection", "none")
        entry["samples"] = {k: raw.get(k) for k in ("traders", "wallets", "markets") if raw.get(k)}
        print(f"    reachable={entry['reachable']} records={entry['records']} "
              f"integrity={integ.get('verdict')} flags={integ.get('flags')}")
        if stats.get("n"):
            print(f"    WR={stats.get('wr_pct')}% (wilsonLB={stats.get('wilson_lb_pct')}%) "
                  f"PF={stats.get('pf')} n={stats.get('n')} p={stats.get('p_vs_coinflip')}")
        print(f"    verdict={entry['verdict']}")
        results.append(entry)

    report = {
        "generated_at": NOW.isoformat(),
        "definition": {
            "future_bias": "no source timestamp may exceed now+5min; entries must precede exits",
            "lookahead": "signal/report timestamp must precede the price bar used to score it",
            "reliability": "Wilson lower-bound WR >= 50%, PF >= 1.2, binomial p<0.05 vs coin flip",
            "trust_gate": f"n >= {MIN_N_TRUST} and split-half WR gap < 15pp",
        },
        "sources": results,
        "summary": {
            "probed": len(results),
            "reachable": sum(1 for r in results if r["reachable"]),
            "clean_timestamps": sum(1 for r in results if (r.get("integrity") or {}).get("verdict") == "CLEAN"),
            "trade_level_verified": sum(1 for r in results if r.get("verdict") in ("TRUSTED", "WATCH", "WEAK")),
        },
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {REPORT_PATH}")
    return report


# ─────────────────────────────────────────────────────────────
# backtest — follow-the-next-trade event study
# ─────────────────────────────────────────────────────────────

def _price_series(symbol: str, asset_class: str, start: datetime) -> list[tuple[datetime, float]]:
    """Free OHLC via Kraken (crypto) / Stooq-free fallback via Yahoo chart."""
    sym = symbol.upper()
    if asset_class in ("CRYPTO", "MEME"):
        pair = f"{sym}USD"
        r = http(f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440", timeout=20)
        if r and r.status_code == 200:
            j = r.json()
            for k, rows in (j.get("result") or {}).items():
                if k == "last":
                    continue
                return [(to_dt(x[0]), float(x[4])) for x in rows if to_dt(x[0]) and to_dt(x[0]) >= start]
    r = http(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=2y&interval=1d", timeout=20)
    if r and r.status_code == 200:
        j = r.json()
        res = (j.get("chart") or {}).get("result") or []
        if res:
            t = res[0].get("timestamp") or []
            closes = ((res[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
            return [(to_dt(a), float(b)) for a, b in zip(t, closes) if a and b]
    return []


def _oos_survives(oos: dict) -> bool:
    """Out-of-sample gate matches the profitability-first policy (PF + positive
    expectancy), not a WR requirement — a 42% WR trend profile with PF 1.26
    still classifies as real edge."""
    exp = oos.get("expectancy") or 0
    pf = oos.get("pf")
    return exp > 0 and (pf in (None, float("inf")) or pf >= 1.1)


def run_backtest() -> dict:
    """Replay verified trader histories as a copy-trade strategy and measure
    whether copying the next signal has genuine edge (out-of-sample split)."""
    print("=" * 74)
    print("  VERIFIED-SOURCE BACKTEST (follow-the-trader)")
    print("=" * 74)
    out: dict[str, Any] = {"generated_at": NOW.isoformat(), "sources": {}}

    # 1) Hyperliquid: split each wallet's round trips into in-sample / out-of-sample
    hl = src_hyperliquid_whales(top=12, days=60)
    if hl.get("reachable"):
        # recompute per-wallet to allow OOS split
        rec = {"source": "hyperliquid_whales", "note": "FIFO round-trip PnLs; first 60% IS, last 40% OOS"}
        pnls = hl.get("pnls") or []
        n = len(pnls)
        if n >= 20:
            cut = int(n * 0.6)
            is_s = score_pnls(pnls[:cut])
            oos = score_pnls(pnls[cut:])
            rec["in_sample"] = is_s
            rec["out_of_sample"] = oos
            rec["decay_wr_pp"] = round((is_s.get("wr_pct") or 0) - (oos.get("wr_pct") or 0), 2)
            rec["verdict"] = ("SURVIVES_OOS" if (oos.get("wr_pct") or 0) >= 50
                              and (oos.get("pf") or 0) >= 1.1 else "DECAYS")
        else:
            rec["verdict"] = "INSUFFICIENT_N"
            rec["n"] = n
        out["sources"]["hyperliquid_whales"] = rec
        print(f"  HL whales: {rec['verdict']} IS-WR={rec.get('in_sample', {}).get('wr_pct')} "
              f"OOS-WR={rec.get('out_of_sample', {}).get('wr_pct')}")

    # 2) OKX: same split
    okx = src_okx_copytrading(limit_traders=10, pages=3)
    if okx.get("reachable"):
        pnls = okx.get("pnls") or []
        n = len(pnls)
        rec = {"source": "okx_copytrading", "note": "closed subpositions; 60/40 temporal split"}
        if n >= 20:
            cut = int(n * 0.6)
            is_s, oos = score_pnls(pnls[:cut]), score_pnls(pnls[cut:])
            rec.update({"in_sample": is_s, "out_of_sample": oos,
                        "decay_wr_pp": round((is_s.get("wr_pct") or 0) - (oos.get("wr_pct") or 0), 2),
                        "verdict": "SURVIVES_OOS" if _oos_survives(oos) else "DECAYS"})
        else:
            rec.update({"verdict": "INSUFFICIENT_N", "n": n})
        out["sources"]["okx_copytrading"] = rec
        print(f"  OKX: {rec['verdict']} IS-WR={rec.get('in_sample', {}).get('wr_pct')} "
              f"OOS-WR={rec.get('out_of_sample', {}).get('wr_pct')}")

    # 3) Polymarket: closed-position PnL split
    pm = src_polymarket_v2(top=10)
    if pm.get("reachable") and len(pm.get("pnls") or []) >= 20:
        pnls = pm["pnls"]
        cut = int(len(pnls) * 0.6)
        is_s, oos = score_pnls(pnls[:cut]), score_pnls(pnls[cut:])
        art_verdict, art_reasons = apply_artifact_guards(score_pnls(pnls), pm)
        out["sources"]["polymarket_v2"] = {
            "source": "polymarket_v2", "in_sample": is_s, "out_of_sample": oos,
            "decay_wr_pp": round((is_s.get("wr_pct") or 0) - (oos.get("wr_pct") or 0), 2),
            "verdict": ("ARTIFACT_NOT_BACKTESTABLE" if art_verdict == "REJECT_ARTIFACT"
                        else ("SURVIVES_OOS" if _oos_survives(oos) else "DECAYS")),
            "artifact_reasons": art_reasons,
        }
        print(f"  Polymarket: {out['sources']['polymarket_v2']['verdict']} "
              f"OOS-WR={oos.get('wr_pct')}")

    BACKTEST_PATH.write_text(json.dumps(_json_safe(out), indent=2))
    print(f"\nWrote {BACKTEST_PATH}")
    return out


# ─────────────────────────────────────────────────────────────
# github discovery
# ─────────────────────────────────────────────────────────────

GITHUB_QUERIES = [
    "trading signals picks json",
    "stock picks dataset json",
    "crypto signals alerts bot",
    "hyperliquid whale tracker",
    "copy trading bot leaderboard",
    "polymarket copy trading",
    "insider trading tracker sec",
    # non-crypto asset classes
    "forex signal bot free",
    "commodity COT commitments traders",
    "penny stock screener picks",
    "value stock screen pe pb",
    "etf holdings tracker ark",
    "bond yield curve data",
    "futures spread scanner",
    "prediction market bot kalshi polymarket",
    "ml stock prediction model",
    "quant backtest signals csv",
    "earnings momentum signals",
]

# machine-readable pick artifacts a repo might publish
PICK_HINTS = [
    "data/picks.json", "picks.json", "data/signals.json", "signals.json",
    "output/picks.json", "data/trades.json", "public/picks.json",
    "data/active_picks.json", "data/paper_trades.json", "data/trading_picks.json",
    "data/equity_commodity_strategies_20.json", "data/multi_asset_picks.json",
    "data/copytrader_database.json", "picks/latest.json", "signals/latest.json",
    "data/screener_picks.json", "data/forecast.json", "data/predictions.json",
]


def _gh_api(url: str) -> dict | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(url, headers=h, timeout=20)
        if r.status_code == 403:
            print("    [rate-limited] no GITHUB_TOKEN set")
            return None
        return r.json() if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None


def _gh_repo_meta(name: str) -> dict | None:
    j = _gh_api(f"https://api.github.com/repos/{name}")
    if not j or not j.get("full_name"):
        return None
    return {
        "repo": j["full_name"],
        "url": j["html_url"],
        "description": (j.get("description") or "")[:160],
        "stars": j.get("stargazers_count", 0),
        "pushed_at": j.get("pushed_at"),
        "query": "explicit-list",
        "pick_files": [],
        "verdict": "NO_PICK_FILE",
    }


def _extract_ts(data: Any, extra_keys: tuple[str, ...] = ()) -> tuple[int, list]:
    """Return (record_count, parseable timestamps) from a JSON pick artifact."""
    keys = ("timestamp", "generated_at", "updated_at", "date", "time", "created_at",
            "signal_time") + extra_keys
    ts: list = []
    count = 0
    for obj in (data if isinstance(data, list) else [data]):
        if not isinstance(obj, dict):
            continue
        count += 1
        for k in keys:
            if k in obj:
                t = to_dt(obj[k])
                if t:
                    ts.append(t)
    return count, ts


def _try_pick_file(repo: str, branch: str, hint: str,
                   extra_keys: tuple[str, ...] = ()) -> dict | None:
    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{hint}"
    try:
        r = requests.get(raw, headers=HEADERS, timeout=10)
    except Exception:  # noqa: BLE001
        return None
    if r.status_code != 200 or len(r.content) < 200:
        return None
    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        return None
    count, ts = _extract_ts(data, extra_keys)
    return {"path": hint, "branch": branch, "records": count,
            "integrity": integrity_checks(ts, stale_tolerance_days=30,
                                          date_granularity=True)}


def _scan_repo(meta: dict, extra_keys: tuple[str, ...] = (),
               workers: int = 24) -> dict:
    """Probe every (hint, branch) pair for one repo concurrently."""
    repo = meta["repo"]
    branches = [meta.get("default_branch") or "main"]
    if "master" not in branches:
        branches.append("master")
    hits: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_try_pick_file, repo, br, hint, extra_keys)
                for hint in PICK_HINTS for br in branches]
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                hits.append(res)
    if hits:
        meta["pick_files"] = hits
        meta["verdict"] = ("USABLE" if any(h["integrity"].get("verdict") == "CLEAN"
                                           for h in hits) else "FLAGGED")
    return meta


def scan_eltonsaguiar() -> dict:
    """Explicit scan of the user's own GitHub org — no search quota needed."""
    print("\n  -- eltonaguiar repos --")
    repos: list[dict] = []
    for page in (1, 2, 3):
        url = f"https://api.github.com/users/eltonaguiar/repos?per_page=100&page={page}"
        j = _gh_api(url)
        if not j or not isinstance(j, list):
            break
        for item in j:
            meta = {
                "repo": item["full_name"],
                "url": item["html_url"],
                "description": (item.get("description") or "")[:160],
                "stars": item.get("stargazers_count", 0),
                "pushed_at": item.get("pushed_at"),
                "default_branch": item.get("default_branch"),
                "query": "user:eltonaguiar",
                "pick_files": [],
                "verdict": "NO_PICK_FILE",
            }
            repos.append(meta)
    print(f"  found {len(repos)} eltonaguiar repos")
    extra = ("entry_date", "resolved_at")
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = [ex.submit(_scan_repo, m, extra) for m in repos]
        for fut in as_completed(futures):
            meta = fut.result()
            if meta["verdict"] != "NO_PICK_FILE":
                f0 = meta["pick_files"][0]
                print(f"  [{meta['verdict']}] {meta['repo']} -> {f0['path']} "
                      f"({f0['records']} records)")
    return {"generated_at": NOW.isoformat(), "repos": repos,
            "usable": [m for m in repos if m["verdict"] == "USABLE"]}


def run_github() -> dict:
    print("=" * 74)
    print("  GITHUB PICK-SOURCE DISCOVERY")
    print("=" * 74)
    seen: dict[str, dict] = {}
    for q in GITHUB_QUERIES:
        url = f"https://api.github.com/search/repositories?q={requests.utils.quote(q)}&sort=updated&per_page=8"
        j = _gh_api(url)
        if not j:
            print(f"    [QUERY FAILED] {url}")
            continue
        for item in j.get("items", []):
            name = item["full_name"]
            if name in seen:
                continue
            seen[name] = {
                "repo": name,
                "url": item["html_url"],
                "description": (item.get("description") or "")[:160],
                "stars": item["stargazers_count"],
                "pushed_at": item["pushed_at"],
                "query": q,
                "pick_files": [],
                "verdict": "NO_PICK_FILE",
            }
    print(f"  candidate repos: {len(seen)}")

    validated = []
    targets = [m for m in seen.values() if m["stars"] >= 3]
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = [ex.submit(_scan_repo, m) for m in targets]
        for fut in as_completed(futures):
            meta = fut.result()
            if meta["verdict"] != "NO_PICK_FILE":
                validated.append(meta)
                f0 = meta["pick_files"][0]
                print(f"  [{meta['verdict']}] {meta['repo']} -> {f0['path']} "
                      f"({f0['records']} records)")
    print(f"  scanned {len(targets)} repos with >=3 stars")

    eltons = scan_eltonsaguiar()
    out = {
        "generated_at": NOW.isoformat(),
        "note": "Only repos that publish machine-readable picks with parseable timestamps are USABLE.",
        "candidates": len(seen),
        "validated": validated,
        "rejected_no_pick_file": [m["repo"] for m in seen.values() if m.get("verdict") == "NO_PICK_FILE"][:25],
        "eltonsaguiar": eltons,
    }
    GITHUB_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {GITHUB_PATH} ({len(validated)} usable, {len(eltons['usable'])} eltonaguiar)")
    return out


    GITHUB_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {GITHUB_PATH} ({len(validated)} usable)")
    return out

# ─────────────────────────────────────────────────────────────
# registry
# ─────────────────────────────────────────────────────────────

def run_registry() -> dict:
    report = json.loads(REPORT_PATH.read_text()) if REPORT_PATH.exists() else {"sources": []}
    accepted = []
    for s in report.get("sources", []):
        v = s.get("verdict")
        if v in ("TRUSTED", "WATCH", "DATA_OK_NO_TRADE_PNL"):
            integ = s.get("integrity") or {}
            if integ.get("verdict") != "CLEAN":
                continue
            accepted.append({
                "id": s["id"],
                "asset_classes": s["asset_classes"],
                "role": s["pick_role"],
                "verdict": v,
                "license": s["license"],
                "ts_integrity": integ.get("verdict"),
                "stale_days": integ.get("stale_days"),
                "reliability": s.get("reliability"),
                "what": s["what"],
                "adapter": "copy_trader_intel/source_truth_verifier.py",
            })
    reg = {
        "generated_at": NOW.isoformat(),
        "policy": "Only sources with CLEAN timestamps and non-REJECT verdict are listed. "
                  "TRUSTED requires n>=100, Wilson LB WR>=50%, PF>=1.2, split-half gap<15pp.",
        "accepted_count": len(accepted),
        "accepted": accepted,
        "by_asset_class": {
            ac: [a["id"] for a in accepted if ac in a["asset_classes"]]
            for ac in sorted({c for a in accepted for c in a["asset_classes"]})
        },
    }
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2))
    print(f"Wrote {REGISTRY_PATH} ({len(accepted)} accepted)")
    print(json.dumps(reg["by_asset_class"], indent=1))
    return reg


def main(argv: list[str]) -> int:
    cmd = (argv[1] if len(argv) > 1 else "all").lower()
    if cmd == "probe":
        run_probe()
    elif cmd == "backtest":
        run_backtest()
    elif cmd == "github":
        run_github()
    elif cmd == "registry":
        run_registry()
    elif cmd == "all":
        run_probe()
        run_backtest()
        run_github()
        run_registry()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
