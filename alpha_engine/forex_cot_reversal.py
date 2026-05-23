"""FOREX COT Positioning Reversal — Grok-4 edge-research #5 sidecar.

Strategy: ``forex_cot_positioning_reversal``
Family:   ``community`` (sentiment overlay, registered in config.STRATEGY_FAMILIES)
Expected: PF ~1.6, ~15h horizon (weekly COT releases drive multi-day moves).
Source:   reports/edge_research_synthesis_2026_05_12.md

Mechanic
--------
Fade extreme non-commercial (speculator) positioning in FX majors.
  - Compute 52-week percentile rank of weekly net non-commercial position.
  - When pct >= 80 for two consecutive weekly reports -> SHORT pair.
  - When pct <= 20 for two consecutive weekly reports -> LONG pair.
  - Optional commercial-hedger confirmation: commercial net opposes
    speculators in the same window (+ veto weight).

Universe: EURUSD, GBPUSD, USDJPY, AUDUSD (CFTC Financial-Futures majors).
Note: 6J (JPY futures) is USD/JPY inverted -- a YEN-future speculator long
maps to a USDJPY SHORT.

DEFAULT-OFF: returns [] unless ``FOREX_COT_REVERSAL_ENABLED=1``.

FOREX sizing cap (CRITICAL)
---------------------------
Per CLAUDE.md MAJOR GOAL #1 (FOREX directive) and PR #909, FOREX picks
are hard-capped at 0 size until system-wide FOREX PF >= 0.8 (today: PF
0.27 post-noise-filter, n=1169 -- still below floor). Therefore every
pick emitted by this module ships with::

    confidence       = 0.0   (preserves the unscaled signal in raw_confidence)
    raw_confidence   = 0.55-0.70 (the strategy's real conviction)
    status           = "paper_only"
    forex_size_capped = True

When the FOREX floor lifts (live PF >= 0.8), flip confidence back to
raw_confidence via the dashboard adapter; no code change here is required
to participate in paper-only validation.

## Wiring Plan
Target:  audit_trail/dashboard_generator.py JSON_PICK_SOURCES
Path:    alpha_engine/data/forex_cot_reversal_signals.json
Adapter: reuse the existing community-overlay adapter; pass-through
         ``raw_confidence`` while keeping ``confidence=0`` until floor lifts.
Date:    after 2-week paper validation + FOREX PF >= 0.8.
Sync:    .github/workflows/forex-agent.yml -- add a step after the existing
         cot_positioning invocation:
             ``python -m alpha_engine.forex_cot_reversal``
         (env-gate the step on ``FOREX_COT_REVERSAL_ENABLED=1``).

Rollback: unset ``FOREX_COT_REVERSAL_ENABLED`` -> module returns [].
Stale-data guard: skip if latest CFTC FX report > 14d old.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.cftc_cot_forex_fetcher import FOREX_CONTRACTS, fetch_cot  # noqa: E402

STRATEGY_NAME = "forex_cot_positioning_reversal"
ASSET_CLASS = "FOREX"

EXTREME_LONG_PERCENTILE = 80   # speculator crowd long  -> contrarian SHORT
EXTREME_SHORT_PERCENTILE = 20  # speculator crowd short -> contrarian LONG
LOOKBACK_WEEKS = 52
CONFIRM_WEEKS = 2              # require 2 consecutive weekly extremes
MAX_REPORT_AGE_DAYS = 14
RAW_CONFIDENCE_MIN = 0.55
RAW_CONFIDENCE_MAX = 0.70


def _is_enabled() -> bool:
    return os.environ.get("FOREX_COT_REVERSAL_ENABLED") == "1"


def _parse_int(val) -> int:
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _is_stale(latest_iso: str, now: Optional[datetime] = None) -> bool:
    if not latest_iso:
        return True
    try:
        d = datetime.strptime(latest_iso[:10], "%Y-%m-%d").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return True
    n = now or datetime.now(timezone.utc)
    return (n - d) > timedelta(days=MAX_REPORT_AGE_DAYS)


def _percentile_rank(window: np.ndarray, value: float) -> float:
    """Inclusive percentile rank of `value` within `window` (0-100)."""
    if window.size == 0:
        return 50.0
    return float(np.mean(window <= value) * 100.0)


def compute_signal(reports: list, now: Optional[datetime] = None) -> dict:
    """Compute the COT-reversal signal for one contract.

    Returns dict with keys: signal (BUY/SELL/NEUTRAL), direction
    (LONG/SHORT/NEUTRAL), raw_confidence (0-1), percentile_rank,
    prior_percentile_rank, current_net, latest_date, stale, reason,
    commercial_confirms (bool).
    """
    base = {"signal": "NEUTRAL", "direction": "NEUTRAL",
            "raw_confidence": 0.0, "stale": False,
            "commercial_confirms": False}
    if not reports or len(reports) < LOOKBACK_WEEKS:
        return {**base, "reason": "Insufficient COT history (<52w)"}

    nc_nets: list[float] = []
    cm_nets: list[float] = []
    dates: list[str] = []
    for r in reports:
        nc_long = _parse_int(r.get("noncomm_positions_long_all"))
        nc_short = _parse_int(r.get("noncomm_positions_short_all"))
        cm_long = _parse_int(r.get("comm_positions_long_all"))
        cm_short = _parse_int(r.get("comm_positions_short_all"))
        nc_nets.append(float(nc_long - nc_short))
        cm_nets.append(float(cm_long - cm_short))
        dates.append(str(r.get("report_date_as_yyyy_mm_dd", "") or "")[:10])

    if len(nc_nets) < LOOKBACK_WEEKS:
        return {**base, "reason": "Insufficient valid rows"}

    latest_date = dates[0] if dates else ""
    if _is_stale(latest_date, now=now):
        return {**base, "stale": True, "latest_date": latest_date,
                "reason": f"Latest COT {latest_date} > {MAX_REPORT_AGE_DAYS}d old"}

    arr = np.asarray(nc_nets, dtype=float)
    current_net = float(arr[0])
    prior_net = float(arr[1]) if arr.size > 1 else current_net
    # Percentile of latest within trailing 52w (excluding current point
    # gives a slightly less biased rank but we keep inclusive to match
    # commodity_cot_contrarian).
    rank = _percentile_rank(arr[:LOOKBACK_WEEKS], current_net)
    prior_rank = _percentile_rank(arr[1:LOOKBACK_WEEKS + 1], prior_net)

    # 2-week confirmation: both current and prior must be on the same extreme.
    both_long = (rank >= EXTREME_LONG_PERCENTILE
                 and prior_rank >= EXTREME_LONG_PERCENTILE)
    both_short = (rank <= EXTREME_SHORT_PERCENTILE
                  and prior_rank <= EXTREME_SHORT_PERCENTILE)

    if both_long:
        signal, direction = "SELL", "SHORT"
        extremity = (rank - EXTREME_LONG_PERCENTILE) / (100.0 - EXTREME_LONG_PERCENTILE)
        reason = (f"Non-commercial net at {rank:.0f}th pct (prior {prior_rank:.0f}). "
                  "Speculator crowd extremely long for 2 weeks -> fade SHORT.")
    elif both_short:
        signal, direction = "BUY", "LONG"
        extremity = (EXTREME_SHORT_PERCENTILE - rank) / EXTREME_SHORT_PERCENTILE
        reason = (f"Non-commercial net at {rank:.0f}th pct (prior {prior_rank:.0f}). "
                  "Speculator crowd extremely short for 2 weeks -> fade LONG.")
    else:
        return {**base, "percentile_rank": round(rank, 1),
                "prior_percentile_rank": round(prior_rank, 1),
                "current_net": current_net, "latest_date": latest_date,
                "reason": f"No 2-week extreme (pct {rank:.0f}, prior {prior_rank:.0f})"}

    extremity = float(np.clip(extremity, 0.0, 1.0))
    raw_conf = RAW_CONFIDENCE_MIN + (RAW_CONFIDENCE_MAX - RAW_CONFIDENCE_MIN) * extremity

    # Commercial confirmation: commercials should be on the opposite side
    # of the speculators (they're the natural hedger counterparty).
    current_cm = cm_nets[0] if cm_nets else 0.0
    if direction == "SHORT" and current_cm < 0:
        commercial_confirms = True
    elif direction == "LONG" and current_cm > 0:
        commercial_confirms = True
    else:
        commercial_confirms = False
    if commercial_confirms:
        raw_conf = min(RAW_CONFIDENCE_MAX, raw_conf + 0.05)

    return {
        "signal": signal,
        "direction": direction,
        "raw_confidence": round(raw_conf, 3),
        "percentile_rank": round(rank, 1),
        "prior_percentile_rank": round(prior_rank, 1),
        "current_net": current_net,
        "latest_date": latest_date,
        "stale": False,
        "commercial_confirms": commercial_confirms,
        "reason": reason,
    }


def forex_cot_reversal_picks(now: Optional[datetime] = None) -> list[dict]:
    """Public entry point. Returns picks list; [] when gated OFF or no signal.

    Per CLAUDE.md FOREX directive: ``confidence=0`` and
    ``status='paper_only'`` until system-wide FOREX PF >= 0.8.
    """
    if not _is_enabled():
        return []

    n = now or datetime.now(timezone.utc)
    n_iso = n.isoformat()
    picks: list[dict] = []

    for sym, info in FOREX_CONTRACTS.items():
        result = fetch_cot(sym)
        reports = result.get("reports", []) if isinstance(result, dict) else []
        sig = compute_signal(reports, now=n)
        if sig["signal"] == "NEUTRAL":
            continue

        # USD/JPY inversion: YEN futures speculator long == USDJPY SHORT.
        direction = sig["direction"]
        signal_label = sig["signal"]
        if info.get("invert_for_usd_base"):
            direction = "SHORT" if direction == "LONG" else "LONG"
            signal_label = "SELL" if signal_label == "BUY" else "BUY"

        picks.append({
            "symbol": sym,
            "pair": info.get("futures_code", ""),
            "direction": direction,
            "signal": signal_label,
            "strategy": STRATEGY_NAME,
            "asset_class": ASSET_CLASS,
            "category": "forex",
            "timeframe": "1w",
            # FOREX hard-cap per CLAUDE.md / PR #909 until PF >= 0.8.
            "confidence": 0.0,
            "raw_confidence": sig["raw_confidence"],
            "status": "paper_only",
            "forex_size_capped": True,
            "generated_at": n_iso,
            "timestamp": n_iso,
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "percentile": sig["percentile_rank"],
            "prior_percentile": sig["prior_percentile_rank"],
            "current_net": sig["current_net"],
            "latest_cot_date": sig["latest_date"],
            "commercial_confirms": sig["commercial_confirms"],
            "cot_reason": sig["reason"],
            "reason": (f"COT reversal {sym}: {sig['reason']}"
                       + (" Commercial hedgers confirm."
                          if sig["commercial_confirms"] else "")),
            "notes": ("Contrarian fade of crowded speculator positioning. "
                      "FOREX size-capped to 0 until live PF >= 0.8 "
                      "(see CLAUDE.md FOREX directive)."),
        })

    return picks


if __name__ == "__main__":
    print(f"FOREX_COT_REVERSAL_ENABLED="
          f"{os.environ.get('FOREX_COT_REVERSAL_ENABLED')}")
    out = forex_cot_reversal_picks()
    print(f"emitted {len(out)} picks (paper_only)")
    for p in out:
        print(f"  {p['direction']:5s} {p['symbol']:6s} "
              f"raw_conf={p['raw_confidence']} pct={p['percentile']} "
              f"prior={p['prior_percentile']} cm_conf={p['commercial_confirms']}")
    out_dir = _REPO_ROOT / "alpha_engine" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "forex_cot_reversal_signals.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scanner": STRATEGY_NAME,
            "picks": out,
        }, f, indent=2)
    print(f"saved -> {out_path}")
