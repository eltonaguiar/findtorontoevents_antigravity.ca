#!/usr/bin/env python3
"""
Contrarian Predictions Strategy — Invert social media prediction signals.

THESIS:
    Social media crypto predictions (Reddit, TradingView, Twitter) have a
    historically verified ~15.6% real win rate on 32 sane closed trades.
    Inverting every signal yields an 84.4% win rate with Sharpe 0.68.

    The crowd is reliably wrong. We fade them.

MECHANISM:
    1. Read active predictions from predictions/data/predictions.db
    2. Invert: LONG -> SHORT, SHORT -> LONG
    3. Swap TP/SL targets
    4. Apply confidence weighting by platform reliability:
       - Reddit: 100% historically wrong (inv WR = 100%, n=14) -> highest confidence
       - Twitter analysts: 80% wrong (inv WR = 80%, n=5)
       - TradingView: 69% wrong (inv WR = 69.2%, n=13)
    5. Filter: only invert predictions with sane TP/SL (within 50% of entry)
    6. Output signals compatible with strategy_runner.py format

CAVEATS:
    - Only 32 sane closed trades so far. Need 50+ for statistical significance.
    - Heavy TP/SL data corruption from scrapers (11 of 43 closed had garbage values).
    - Reddit's 100% inverse WR is likely inflated by corrupt TP parsing.
    - This is a PAPER TRADING strategy until we get 100+ validated inversions.

Usage:
    # Scan mode — get current inverted signals
    python -m trading.contrarian_predictions --mode scan

    # Backtest mode — show historical inversion performance
    python -m trading.contrarian_predictions --mode backtest

    # Integration — import and use in strategy_runner.py
    from trading.contrarian_predictions import ContrarianPredictions
    cp = ContrarianPredictions()
    signals = cp.scan()
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ── Configuration ──

# Platform inverse reliability (based on historical analysis)
# Higher = more reliably wrong = higher confidence in inversion
PLATFORM_CONFIDENCE = {
    "reddit": 0.90,       # 100% inv WR on 14 trades (discount for small sample + data issues)
    "twitter": 0.72,      # 80% inv WR on 5 trades
    "tradingview": 0.62,  # 69.2% inv WR on 13 trades
    "stocktwits": 0.60,   # No data yet, assume moderate
    "youtube": 0.55,      # No data yet, assume lower
    "polymarket": 0.50,   # Prediction markets are more efficient, lower inversion value
}

# Symbol inverse reliability (based on historical analysis)
# Symbols where predictions are most reliably wrong
SYMBOL_BONUS = {
    "BTCUSDT": 0.10,   # 0% orig WR (100% inv), n=6
    "ETHUSDT": 0.10,   # 0% orig WR (100% inv), n=9
    "LINKUSDT": 0.05,  # 20% orig WR (80% inv), n=5
    "BNBUSDT": 0.05,   # 0% orig WR (100% inv), n=2
    "DOGEUSDT": 0.05,  # 0% orig WR (100% inv), n=1
    "SOLUSDT": 0.03,   # 33% orig WR (67% inv), n=3
}

# Sanity thresholds — reject predictions with garbage TP/SL
MAX_TP_DEVIATION_PCT = 50.0   # TP must be within 50% of entry
MAX_SL_DEVIATION_PCT = 50.0   # SL must be within 50% of entry
DEFAULT_TP_PCT = 3.0           # Default TP if not available (3%)
DEFAULT_SL_PCT = 2.0           # Default SL if not available (2%)

# Minimum predictions age before inverting (avoid front-running)
MIN_AGE_MINUTES = 5

DB_PATH = Path(__file__).parent.parent / "predictions" / "data" / "predictions.db"


class ContrarianPredictions:
    """Invert social media predictions into tradeable signals."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.strategy_name = "contrarian_predictions"

    def _get_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def scan(self) -> List[Dict]:
        """
        Read active predictions and return inverted signals.

        Returns signals in strategy_runner.py format:
        {
            "symbol": "BTCUSDT",
            "direction": "SHORT",  # inverted from original LONG
            "strategy": "contrarian_predictions",
            "entry_price": 84500.0,
            "take_profit": 81965.0,
            "stop_loss": 86190.0,
            "confidence": 0.85,
            "indicators": {...},
        }
        """
        conn = self._get_db()
        active = conn.execute(
            "SELECT * FROM predictions WHERE status = 'ACTIVE' ORDER BY scraped_at DESC"
        ).fetchall()
        conn.close()

        if not active:
            print("[contrarian] No active predictions to invert.")
            return []

        signals = []
        skipped_corrupt = 0
        skipped_no_entry = 0

        for pred in active:
            pred = dict(pred)
            entry = pred.get("entry_price")
            tp = pred.get("take_profit")
            sl = pred.get("stop_loss")
            direction = pred.get("direction", "").upper()
            symbol = pred.get("symbol", "")
            platform = pred.get("platform", "").lower()
            predictor = pred.get("predictor_id", "")

            if not entry or entry <= 0:
                skipped_no_entry += 1
                continue

            if direction not in ("LONG", "SHORT"):
                continue

            # ── Sanity check TP/SL ──
            if tp and entry:
                tp_dev = abs(tp - entry) / entry * 100
                if tp_dev > MAX_TP_DEVIATION_PCT:
                    skipped_corrupt += 1
                    continue
            if sl and entry:
                sl_dev = abs(sl - entry) / entry * 100
                if sl_dev > MAX_SL_DEVIATION_PCT:
                    skipped_corrupt += 1
                    continue

            # ── Invert direction ──
            inv_direction = "SHORT" if direction == "LONG" else "LONG"

            # ── Invert TP/SL ──
            # For a LONG->SHORT inversion:
            #   Original LONG TP (above entry) becomes SHORT SL (above entry)
            #   Original LONG SL (below entry) becomes SHORT TP (below entry)
            # For a SHORT->LONG inversion:
            #   Original SHORT TP (below entry) becomes LONG SL (below entry)
            #   Original SHORT SL (above entry) becomes LONG TP (above entry)
            if tp and sl:
                inv_tp = sl   # Their stop loss is our take profit
                inv_sl = tp   # Their take profit is our stop loss
            elif tp:
                # Only TP provided — use it as our SL, compute TP from defaults
                inv_sl = tp
                if inv_direction == "LONG":
                    inv_tp = round(entry * (1 + DEFAULT_TP_PCT / 100), 8)
                else:
                    inv_tp = round(entry * (1 - DEFAULT_TP_PCT / 100), 8)
            elif sl:
                # Only SL provided — use it as our TP, compute SL from defaults
                inv_tp = sl
                if inv_direction == "LONG":
                    inv_sl = round(entry * (1 - DEFAULT_SL_PCT / 100), 8)
                else:
                    inv_sl = round(entry * (1 + DEFAULT_SL_PCT / 100), 8)
            else:
                # No TP/SL — use defaults
                if inv_direction == "LONG":
                    inv_tp = round(entry * (1 + DEFAULT_TP_PCT / 100), 8)
                    inv_sl = round(entry * (1 - DEFAULT_SL_PCT / 100), 8)
                else:
                    inv_tp = round(entry * (1 - DEFAULT_TP_PCT / 100), 8)
                    inv_sl = round(entry * (1 + DEFAULT_SL_PCT / 100), 8)

            # ── Validate inverted TP/SL direction consistency ──
            if inv_direction == "LONG":
                if inv_tp <= entry or inv_sl >= entry:
                    # Fall back to defaults
                    inv_tp = round(entry * (1 + DEFAULT_TP_PCT / 100), 8)
                    inv_sl = round(entry * (1 - DEFAULT_SL_PCT / 100), 8)
            else:  # SHORT
                if inv_tp >= entry or inv_sl <= entry:
                    inv_tp = round(entry * (1 - DEFAULT_TP_PCT / 100), 8)
                    inv_sl = round(entry * (1 + DEFAULT_SL_PCT / 100), 8)

            # ── Confidence scoring ──
            base_confidence = PLATFORM_CONFIDENCE.get(platform, 0.55)
            symbol_bonus = SYMBOL_BONUS.get(symbol, 0.0)
            confidence = min(base_confidence + symbol_bonus, 0.95)

            # Boost confidence if predictor is known to be bad
            # (could integrate with predictor tier system later)

            signals.append({
                "symbol": symbol,
                "direction": inv_direction,
                "strategy": self.strategy_name,
                "entry_price": entry,
                "take_profit": inv_tp,
                "stop_loss": inv_sl,
                "confidence": round(confidence, 3),
                "indicators": {
                    "original_direction": direction,
                    "original_predictor": predictor,
                    "original_platform": platform,
                    "platform_inv_reliability": PLATFORM_CONFIDENCE.get(platform, 0.55),
                    "inversion_reason": f"Fading {platform} {predictor} {direction} call",
                },
            })

        # Sort by confidence descending
        signals.sort(key=lambda s: s["confidence"], reverse=True)

        # Deduplicate: if multiple predictors call the same symbol+direction,
        # keep the highest confidence one (consensus makes inversion stronger)
        seen = {}
        deduped = []
        for sig in signals:
            key = (sig["symbol"], sig["direction"])
            if key not in seen:
                seen[key] = sig
                deduped.append(sig)
            else:
                # Multiple predictors agree = stronger consensus to fade
                existing = seen[key]
                existing["confidence"] = min(existing["confidence"] + 0.03, 0.95)
                existing["indicators"]["consensus_count"] = (
                    existing["indicators"].get("consensus_count", 1) + 1
                )

        print(f"[contrarian] {len(active)} active predictions -> "
              f"{len(deduped)} inverted signals "
              f"(skipped {skipped_corrupt} corrupt, {skipped_no_entry} no entry)")

        return deduped

    def backtest(self) -> Dict:
        """
        Compute historical inversion performance from closed predictions.

        Returns analysis dict with original vs inverted metrics.
        """
        conn = self._get_db()
        closed = conn.execute("""
            SELECT id, predictor_id, platform, symbol, direction,
                   entry_price, take_profit, stop_loss,
                   status, outcome_pnl_pct, scraped_at, resolved_at
            FROM predictions
            WHERE status IN ('TP_HIT', 'SL_HIT', 'EXPIRED_WIN', 'EXPIRED_LOSS')
              AND outcome_pnl_pct IS NOT NULL
        """).fetchall()
        conn.close()

        preds = [dict(r) for r in closed]
        if not preds:
            return {"error": "No closed predictions found"}

        # Separate sane from corrupt
        sane = [p for p in preds if abs(p["outcome_pnl_pct"]) <= 100]
        corrupt = [p for p in preds if abs(p["outcome_pnl_pct"]) > 100]

        if not sane:
            return {"error": "No sane closed predictions (all have |PnL| > 100%)"}

        # Original performance
        pnls = [p["outcome_pnl_pct"] for p in sane]
        orig_wins = sum(1 for x in pnls if x > 0)
        orig_wr = orig_wins / len(pnls) * 100
        orig_avg = sum(pnls) / len(pnls)

        # Inverted performance
        inv_pnls = [-x for x in pnls]
        inv_wins = sum(1 for x in inv_pnls if x > 0)
        inv_wr = inv_wins / len(inv_pnls) * 100
        inv_avg = sum(inv_pnls) / len(inv_pnls)

        # Sharpe ratio
        inv_sharpe = 0.0
        if len(inv_pnls) >= 3:
            mean = sum(inv_pnls) / len(inv_pnls)
            std = (sum((x - mean) ** 2 for x in inv_pnls) / (len(inv_pnls) - 1)) ** 0.5
            inv_sharpe = round(mean / std, 4) if std > 0 else 0.0

        # Max drawdown (cumulative inverted PnL)
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for pnl in inv_pnls:
            cum += pnl
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd

        # By platform breakdown
        from collections import defaultdict
        by_platform = defaultdict(list)
        for p in sane:
            by_platform[p["platform"]].append(p["outcome_pnl_pct"])

        platform_stats = {}
        for plat, plat_pnls in by_platform.items():
            pw = sum(1 for x in plat_pnls if x > 0)
            platform_stats[plat] = {
                "n": len(plat_pnls),
                "orig_wr": round(pw / len(plat_pnls) * 100, 1),
                "inv_wr": round((1 - pw / len(plat_pnls)) * 100, 1),
                "orig_avg_pnl": round(sum(plat_pnls) / len(plat_pnls), 2),
                "inv_avg_pnl": round(-sum(plat_pnls) / len(plat_pnls), 2),
            }

        return {
            "total_closed": len(preds),
            "sane_count": len(sane),
            "corrupt_count": len(corrupt),
            "original": {
                "win_rate": round(orig_wr, 1),
                "avg_pnl": round(orig_avg, 4),
                "total_pnl": round(sum(pnls), 4),
            },
            "inverted": {
                "win_rate": round(inv_wr, 1),
                "avg_pnl": round(inv_avg, 4),
                "total_pnl": round(sum(inv_pnls), 4),
                "sharpe": inv_sharpe,
                "max_drawdown": round(max_dd, 2),
            },
            "by_platform": platform_stats,
            "verdict": (
                "DEPLOY" if inv_wr > 65 and inv_sharpe > 0.3 and len(sane) >= 20
                else "MONITOR" if inv_wr > 55
                else "REJECT"
            ),
            "min_trades_for_significance": 50,
            "current_trades": len(sane),
            "needs_more_data": len(sane) < 50,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Contrarian Predictions — fade the crowd"
    )
    parser.add_argument(
        "--mode",
        choices=["scan", "backtest"],
        default="scan",
        help="scan = generate inverted signals, backtest = show historical performance",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of human-readable",
    )
    args = parser.parse_args()

    cp = ContrarianPredictions()

    if args.mode == "scan":
        signals = cp.scan()
        if args.json:
            print(json.dumps(signals, indent=2, default=str))
        else:
            print(f"\n{'='*70}")
            print(f"  CONTRARIAN PREDICTIONS — Inverted Signals")
            print(f"  Strategy: Fade social media consensus")
            print(f"{'='*70}\n")

            if not signals:
                print("  No signals available.\n")
                return

            for sig in signals:
                ind = sig["indicators"]
                print(
                    f"  {sig['symbol']:<12s} {sig['direction']:>5s}  "
                    f"conf={sig['confidence']:.3f}  "
                    f"TP={sig['take_profit']:.2f}  SL={sig['stop_loss']:.2f}  "
                    f"[fade {ind['original_platform']}:{ind['original_predictor']} "
                    f"{ind['original_direction']}]"
                )

                if "consensus_count" in ind:
                    print(f"    ^ {ind['consensus_count']} predictors agree (stronger fade)")

            print(f"\n  Total signals: {len(signals)}")

    elif args.mode == "backtest":
        results = cp.backtest()
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"\n{'='*70}")
            print(f"  CONTRARIAN PREDICTIONS — Historical Backtest")
            print(f"{'='*70}\n")

            if "error" in results:
                print(f"  Error: {results['error']}\n")
                return

            o = results["original"]
            i = results["inverted"]

            print(f"  Closed trades (sane):  {results['sane_count']}")
            print(f"  Corrupt (excluded):    {results['corrupt_count']}")
            print()
            print(f"  {'Metric':<25s} {'Original':>12s} {'Inverted':>12s}")
            print(f"  {'-'*25} {'-'*12} {'-'*12}")
            print(f"  {'Win Rate':<25s} {o['win_rate']:>11.1f}% {i['win_rate']:>11.1f}%")
            print(f"  {'Avg PnL':<25s} {o['avg_pnl']:>11.2f}% {i['avg_pnl']:>11.2f}%")
            print(f"  {'Total PnL':<25s} {o['total_pnl']:>11.2f}% {i['total_pnl']:>11.2f}%")
            print(f"  {'Sharpe':<25s} {'N/A':>12s} {i['sharpe']:>12.4f}")
            print(f"  {'Max Drawdown':<25s} {'N/A':>12s} {i['max_drawdown']:>11.2f}%")
            print()

            print(f"  By Platform:")
            for plat, stats in results["by_platform"].items():
                print(
                    f"    {plat:<15s} n={stats['n']:>2}  "
                    f"origWR={stats['orig_wr']:>5.1f}%  "
                    f"invWR={stats['inv_wr']:>5.1f}%  "
                    f"invAvgPnL={stats['inv_avg_pnl']:>+7.2f}%"
                )

            print()
            print(f"  Verdict: {results['verdict']}")
            if results["needs_more_data"]:
                print(f"  WARNING: Only {results['current_trades']} trades. "
                      f"Need {results['min_trades_for_significance']}+ for significance.")
            print()


if __name__ == "__main__":
    main()
