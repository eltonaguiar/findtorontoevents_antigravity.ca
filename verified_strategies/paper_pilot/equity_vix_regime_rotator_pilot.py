#!/usr/bin/env python3
"""equity_vix_term_structure_regime_rotator — 30-day shadow paper pilot.

Tracks the swarm-winner strategy (tools/equity_vix_regime_rotator.py) on a live
forward basis. Each daily tick:
  1. Pulls today's VIX9D/VIX/VIX3M + SPY close + ADX
  2. Classifies the regime per the pre-locked thresholds
  3. Records the would-be allocation in equity_vix_regime_rotator_paper_log.jsonl
  4. Updates the state file with regime distribution + day-count progress

NO REAL CAPITAL — shadow only. Promotion criteria (per swarm synthesis spec):
  - 30 days of forward shadow with realized Sharpe within 30% of OOS backtest 3.16
  - n_regime_switches in line with backtest density
  - No drawdown deeper than 5% (live MDD; OOS was -10.6% so we expect 30d < 5%)

After 30d clean, graduate from paper-shadow to half-conviction live sizing
(50% of Quarter-Kelly) until n>=100 paper trades confirm live PF>=1.3, then
full sizing.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.equity_vix_regime_rotator import (
    classify_regime, _fetch_closes, _compute_adx,
    VIX_SYMBOLS, RISK_ON_UNIVERSE, NEUTRAL_LEGS, RISK_OFF_LEGS,
    MOM_LOOKBACK, ADX_SYMBOL,
)

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "equity_vix_regime_rotator_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "equity_vix_regime_rotator_state.json"
STRATEGY_ID = "equity_vix_term_structure_regime_rotator"
PROMOTION_TARGET_DAYS = 30


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "strategy_id": STRATEGY_ID,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "day_count": 0,
        "regime_dist": {"RISK_ON": 0, "NEUTRAL": 0, "RISK_OFF": 0},
        "n_regime_switches": 0,
        "last_regime": None,
        "promotion_status": "SHADOW",
        "backtest_oos_sharpe": 3.16,
        "promotion_target_days": PROMOTION_TARGET_DAYS,
    }


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    state["last_update_utc"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(row: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _fetch_today_inputs() -> dict | None:
    """Pull today's VIX/SPY closes + ADX. Returns None on data failure."""
    from datetime import timedelta
    end = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=70)).strftime("%Y-%m-%d")  # enough for ADX + mom warmup
    try:
        vix9d = _fetch_closes("^VIX9D", start, end)
        vix = _fetch_closes("^VIX", start, end)
        vix3m = _fetch_closes("^VIX3M", start, end)
        adx_s = _compute_adx(ADX_SYMBOL, start, end)
        if vix9d.empty or vix.empty or vix3m.empty or adx_s.empty:
            return None
        # Latest values
        return {
            "VIX9D": float(vix9d.iloc[-1]),
            "VIX": float(vix.iloc[-1]),
            "VXV": float(vix3m.iloc[-1]),  # classify_regime reads "VXV" key
            "ADX": float(adx_s.iloc[-1]),
            "asof": str(vix.index[-1].date()),
        }
    except Exception as exc:
        print(f"[pilot] fetch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


def _pick_legs_for_today(regime: str) -> dict:
    """Determine today's would-be allocation."""
    if regime == "RISK_OFF":
        return {RISK_OFF_LEGS[0]: 0.5, RISK_OFF_LEGS[1]: 0.5}
    if regime == "NEUTRAL":
        return {NEUTRAL_LEGS[0]: 0.5, NEUTRAL_LEGS[1]: 0.5}
    # RISK_ON: would pick best-momentum equity ETF. For shadow, log full universe
    # and note the rank in a follow-up pass once we have momentum data.
    return {sym: 1.0 / len(RISK_ON_UNIVERSE) for sym in RISK_ON_UNIVERSE}  # equal-weight stub


def run_daily_tick() -> dict:
    state = _load_state()
    inputs = _fetch_today_inputs()
    if not inputs:
        print("[pilot] no data — skipping tick", file=sys.stderr)
        return state

    regime = classify_regime(inputs)
    legs = _pick_legs_for_today(regime)

    state["day_count"] = int(state.get("day_count", 0)) + 1
    state["regime_dist"][regime] = state["regime_dist"].get(regime, 0) + 1
    if state.get("last_regime") and state["last_regime"] != regime:
        state["n_regime_switches"] = int(state.get("n_regime_switches", 0)) + 1
    state["last_regime"] = regime

    _save_state(state)
    _append_log({
        "asof": inputs["asof"],
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "inputs": {k: round(v, 4) for k, v in inputs.items() if isinstance(v, float)},
        "would_be_allocation": legs,
        "day_count": state["day_count"],
    })
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one-shot", action="store_true",
                        help="Single tick + exit (default).")
    parser.add_argument("--show-state", action="store_true",
                        help="Print state and exit without ticking.")
    args = parser.parse_args()

    if args.show_state:
        print(json.dumps(_load_state(), indent=2))
        return 0

    state = run_daily_tick()
    print(f"[pilot] day={state['day_count']} regime={state.get('last_regime','?')} "
          f"regime_dist={state['regime_dist']} switches={state['n_regime_switches']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
