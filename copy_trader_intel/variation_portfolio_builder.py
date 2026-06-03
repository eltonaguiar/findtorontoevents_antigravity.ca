#!/usr/bin/env python3
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

Variation Portfolio Builder
=============================
Creates test portfolios with varying interpretations of entry/exit rules.
Each variant runs independently and is scored on forward-testing performance.

Variants:
- Conservative: Tight TP, wide SL, high confidence gate
- Moderate: Standard parameters
- Aggressive: Wide TP, tight SL, low confidence gate
- Scalper: Very tight TP/SL, short hold
- Swing: Wide TP/SL, long hold

Output feeds into audit database with portfolio_variant tag.

Usage:
    python copy_trader_intel/variation_portfolio_builder.py
"""

import json
import sys
import os
import time
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# Fix Windows charmap encoding - force UTF-8 stdout/stderr
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Portfolio variant definitions
# ---------------------------------------------------------------------------

@dataclass
class PortfolioVariant:
    """Defines how a variant interprets entry/exit rules."""
    name: str
    tp_mult: float              # Multiplier applied to base TP distance
    sl_mult: float              # Multiplier applied to base SL distance
    min_confidence: float       # Minimum confidence gate (0-1)
    max_hold_multiplier: float  # Multiplier on base max hold duration
    max_positions: int          # Maximum concurrent positions
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


VARIANTS = {
    "conservative": PortfolioVariant(
        name="conservative",
        tp_mult=0.8,
        sl_mult=1.5,
        min_confidence=0.75,
        max_hold_multiplier=0.7,
        max_positions=5,
        description="Tight TP, wide SL, high confidence gate"
    ),
    "moderate": PortfolioVariant(
        name="moderate",
        tp_mult=1.0,
        sl_mult=1.0,
        min_confidence=0.65,
        max_hold_multiplier=1.0,
        max_positions=8,
        description="Standard parameters"
    ),
    "aggressive": PortfolioVariant(
        name="aggressive",
        tp_mult=2.0,
        sl_mult=0.8,
        min_confidence=0.55,
        max_hold_multiplier=1.5,
        max_positions=12,
        description="Wide TP, tight SL, lower confidence gate"
    ),
    "scalper": PortfolioVariant(
        name="scalper",
        tp_mult=0.5,
        sl_mult=0.5,
        min_confidence=0.60,
        max_hold_multiplier=0.3,
        max_positions=15,
        description="Very tight TP/SL, quick trades"
    ),
    "swing": PortfolioVariant(
        name="swing",
        tp_mult=3.0,
        sl_mult=1.5,
        min_confidence=0.70,
        max_hold_multiplier=2.0,
        max_positions=6,
        description="Wide TP/SL, patient holds"
    ),
}


# ---------------------------------------------------------------------------
# Helper: price fetching with failover (for live pick evaluation)
# ---------------------------------------------------------------------------

PRICE_APIS = [
    "https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api1.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api2.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
    "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}",
]


def _fetch_price(symbol: str) -> Optional[float]:
    """Fetch current price with 3+ API failover chain."""
    try:
        import urllib.request
    except ImportError:
        return None

    clean = symbol.upper().replace("-", "").replace("/", "")
    if not clean.endswith("USDT") and not clean.endswith("USD"):
        clean += "USDT"

    for api_template in PRICE_APIS[:3]:
        try:
            url = api_template.format(symbol=clean)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                price = float(data.get("price", 0))
                if price > 0:
                    return price
        except Exception:
            continue

    return None


# ---------------------------------------------------------------------------
# VariationPortfolioBuilder
# ---------------------------------------------------------------------------

class VariationPortfolioBuilder:
    """Builds and scores portfolio variants from the same pick set."""

    def __init__(self, starting_capital: float = 10000.0):
        self.capital = starting_capital
        self.variants = VARIANTS
        self.portfolios: dict = {}  # variant_name -> {equity, positions, trades, closed}

    def apply_variant_to_pick(self, pick: dict, variant: PortfolioVariant) -> Optional[dict]:
        """Adjust a pick's TP/SL/confidence based on variant rules.

        Returns adjusted pick or None if filtered out by confidence gate.
        """
        confidence = pick.get("confidence", pick.get("score", pick.get("ml_score", 0.5)))
        if isinstance(confidence, str):
            try:
                confidence = float(confidence.strip("%")) / 100
            except (ValueError, TypeError):
                confidence = 0.5

        # Normalize confidence to 0-1 range
        if confidence > 1:
            confidence = confidence / 100.0

        # Apply confidence gate
        if confidence < variant.min_confidence:
            return None

        adjusted = dict(pick)

        # Extract entry price (handle multiple field name conventions)
        entry = float(pick.get("entryPrice", pick.get("entry_price", pick.get("entry", 0))))
        base_tp = float(pick.get("targetPrice", pick.get("target_price", pick.get("tp", pick.get("take_profit", 0)))))
        base_sl = float(pick.get("stopPrice", pick.get("stop_price", pick.get("sl", pick.get("stop_loss", 0)))))

        if entry <= 0:
            return None

        # Determine direction
        direction = pick.get("direction", pick.get("signal", "LONG")).upper()
        if "SHORT" in direction or "SELL" in direction:
            direction = "SHORT"
        else:
            direction = "LONG"

        # Calculate and adjust TP/SL distances
        if direction == "SHORT":
            tp_dist = entry - base_tp if base_tp > 0 else entry * 0.03
            sl_dist = base_sl - entry if base_sl > 0 else entry * 0.02
            adjusted["targetPrice"] = round(entry - tp_dist * variant.tp_mult, 8)
            adjusted["stopPrice"] = round(entry + sl_dist * variant.sl_mult, 8)
        else:
            tp_dist = base_tp - entry if base_tp > 0 else entry * 0.03
            sl_dist = entry - base_sl if base_sl > 0 else entry * 0.02
            adjusted["targetPrice"] = round(entry + tp_dist * variant.tp_mult, 8)
            adjusted["stopPrice"] = round(entry - sl_dist * variant.sl_mult, 8)

        # Adjust max hold
        base_hold = int(pick.get("max_hold", pick.get("maxHold", 20)))
        adjusted["max_hold"] = max(1, int(base_hold * variant.max_hold_multiplier))

        # Tag with variant metadata
        adjusted["variant"] = variant.name
        adjusted["confidence_adjusted"] = confidence
        adjusted["direction"] = direction
        adjusted["entryPrice"] = entry

        return adjusted

    def simulate_portfolio(self, picks: list, variant_name: str) -> dict:
        """Run a portfolio simulation with variant-adjusted picks.

        Processes picks chronologically, enforces max_positions, tracks equity curve.
        Returns portfolio state with all trades and metrics.
        """
        variant = self.variants.get(variant_name)
        if not variant:
            return {"error": f"Unknown variant: {variant_name}"}

        equity = self.capital
        peak_equity = equity
        max_drawdown = 0
        positions: list = []
        closed_trades: list = []
        equity_curve: list = [{"equity": equity, "timestamp": "start"}]

        # Sort picks by timestamp if available
        sorted_picks = sorted(picks, key=lambda p: p.get("timestamp", p.get("date", "")))

        for pick in sorted_picks:
            now_str = pick.get("timestamp", pick.get("date", ""))

            # Check and close expired/hit positions first
            positions, newly_closed = self._check_exits(positions, pick)
            closed_trades.extend(newly_closed)
            for ct in newly_closed:
                equity += ct.get("pnl_usd", 0)

            # Apply variant adjustments to this pick
            adjusted = self.apply_variant_to_pick(pick, variant)
            if adjusted is None:
                continue

            # Enforce max positions
            if len(positions) >= variant.max_positions:
                continue

            # Size position (equal weight across max positions)
            position_size = equity / variant.max_positions
            if position_size <= 0:
                continue

            entry_price = float(adjusted.get("entryPrice", adjusted.get("entry_price", 0)))
            if entry_price <= 0:
                continue

            position = {
                "symbol": adjusted.get("symbol", adjusted.get("pair", "UNKNOWN")),
                "direction": adjusted.get("direction", "LONG"),
                "entry_price": entry_price,
                "tp": float(adjusted.get("targetPrice", 0)),
                "sl": float(adjusted.get("stopPrice", 0)),
                "size_usd": position_size,
                "max_hold": adjusted.get("max_hold", 20),
                "bars_held": 0,
                "variant": variant_name,
                "strategy": adjusted.get("strategy", adjusted.get("source", "unknown")),
                "entry_time": now_str,
            }
            positions.append(position)

            # Track equity and drawdown
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_drawdown:
                max_drawdown = dd

            equity_curve.append({"equity": round(equity, 2), "timestamp": now_str})

        # Force-close remaining positions conservatively (0 PnL)
        for pos in positions:
            closed_trades.append({
                **pos,
                "exit_price": pos["entry_price"],
                "exit_reason": "FORCE_CLOSE",
                "pnl_pct": 0,
                "pnl_usd": 0,
            })

        result = {
            "variant": variant_name,
            "variant_config": variant.to_dict(),
            "starting_capital": self.capital,
            "final_equity": round(equity, 2),
            "total_return_pct": round((equity - self.capital) / self.capital * 100, 2),
            "max_drawdown": round(max_drawdown, 4),
            "total_picks_seen": len(picks),
            "picks_accepted": len(closed_trades),
            "picks_filtered": len(picks) - len(closed_trades),
            "closed_trades": closed_trades,
            "equity_curve": equity_curve[-50:],  # Last 50 points for compact output
        }

        self.portfolios[variant_name] = result
        return result

    def _check_exits(self, positions: list, current_pick: dict) -> tuple:
        """Check if any positions should be closed based on current price info.

        Returns (remaining_positions, closed_trades).
        """
        remaining = []
        closed = []

        for pos in positions:
            pos["bars_held"] += 1
            symbol = pos["symbol"]

            # Try to get current price from the pick data (same symbol match)
            current_price = None
            pick_symbol = current_pick.get("symbol", current_pick.get("pair", ""))
            if self._normalize_symbol(pick_symbol) == self._normalize_symbol(symbol):
                current_price = float(current_pick.get("currentPrice",
                                      current_pick.get("current_price", 0)))

            if current_price and current_price > 0:
                entry = pos["entry_price"]
                direction = pos["direction"]

                # Check TP/SL hit
                hit_tp = False
                hit_sl = False
                if direction == "LONG":
                    if pos["tp"] > 0 and current_price >= pos["tp"]:
                        hit_tp = True
                    if pos["sl"] > 0 and current_price <= pos["sl"]:
                        hit_sl = True
                    pnl_pct = (current_price - entry) / entry * 100
                else:
                    if pos["tp"] > 0 and current_price <= pos["tp"]:
                        hit_tp = True
                    if pos["sl"] > 0 and current_price >= pos["sl"]:
                        hit_sl = True
                    pnl_pct = (entry - current_price) / entry * 100

                pnl_usd = pos["size_usd"] * pnl_pct / 100

                if hit_tp:
                    closed.append({**pos, "exit_price": current_price, "exit_reason": "TP_HIT",
                                   "pnl_pct": round(pnl_pct, 4), "pnl_usd": round(pnl_usd, 2)})
                    continue
                if hit_sl:
                    closed.append({**pos, "exit_price": current_price, "exit_reason": "SL_HIT",
                                   "pnl_pct": round(pnl_pct, 4), "pnl_usd": round(pnl_usd, 2)})
                    continue

            # Check max hold expiry
            if pos["bars_held"] >= pos["max_hold"]:
                closed.append({**pos, "exit_price": pos["entry_price"], "exit_reason": "TIME_EXPIRY",
                               "pnl_pct": 0, "pnl_usd": 0})
                continue

            remaining.append(pos)

        return remaining, closed

    @staticmethod
    def _normalize_symbol(sym: str) -> str:
        """Normalize symbol for comparison (BTC-USD, BTCUSD, BTCUSDT -> BTCUSDT)."""
        s = sym.upper().strip().replace("-", "").replace("/", "").replace(" ", "")
        if s.endswith("USD") and not s.endswith("USDT"):
            s += "T"
        return s

    def build_all_variants(self, picks: list) -> dict:
        """Build all portfolio variants from the same pick set.

        Returns dict of variant_name -> simulation results.
        """
        results = {}
        for vname in self.variants:
            print(f"  Building variant: {vname}...", end=" ", flush=True)
            result = self.simulate_portfolio(picks, vname)
            results[vname] = result
            accepted = result.get("picks_accepted", 0)
            ret = result.get("total_return_pct", 0)
            print(f"accepted={accepted} return={ret:+.2f}%")
        return results

    def score_variant(self, variant_name: str) -> dict:
        """Score a portfolio variant. Returns composite score 0-100.

        Composite = win_rate * 0.30 + profit_factor * 0.25 + sharpe * 0.25 + (1-drawdown) * 0.20
        """
        portfolio = self.portfolios.get(variant_name)
        if not portfolio:
            return {"variant": variant_name, "score": 0, "error": "Not simulated"}

        trades = portfolio.get("closed_trades", [])
        if not trades:
            return {"variant": variant_name, "score": 0, "components": {}}

        # Calculate component metrics
        pnls = [t.get("pnl_pct", 0) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        win_rate = len(wins) / len(pnls) if pnls else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses)) if losses else 0.01
        profit_factor = min(gross_profit / gross_loss, 10) if gross_loss > 0 else min(gross_profit, 10)

        # Sharpe ratio
        if len(pnls) >= 2:
            mean_pnl = sum(pnls) / len(pnls)
            variance = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
            std_pnl = math.sqrt(variance) if variance > 0 else 0.01
            sharpe = (mean_pnl / std_pnl) * math.sqrt(252) if std_pnl > 0 else 0
        else:
            sharpe = 0

        max_dd = portfolio.get("max_drawdown", 0)

        # Normalize components to 0-100 scale
        wr_score = min(win_rate * 100, 100)
        pf_score = min(profit_factor * 20, 100)       # PF of 5 = 100
        sharpe_score = min(max(sharpe + 2, 0) * 25, 100)  # Sharpe of 2 = 100
        dd_score = max((1 - max_dd) * 100, 0)

        # Weighted composite
        composite = (
            wr_score * 0.30 +
            pf_score * 0.25 +
            sharpe_score * 0.25 +
            dd_score * 0.20
        )

        return {
            "variant": variant_name,
            "score": round(composite, 2),
            "components": {
                "win_rate": round(win_rate, 4),
                "win_rate_score": round(wr_score, 2),
                "profit_factor": round(profit_factor, 3),
                "profit_factor_score": round(pf_score, 2),
                "sharpe_ratio": round(sharpe, 3),
                "sharpe_score": round(sharpe_score, 2),
                "max_drawdown": round(max_dd, 4),
                "drawdown_score": round(dd_score, 2),
            },
            "total_return_pct": portfolio.get("total_return_pct", 0),
            "trades": len(trades),
            "description": self.variants[variant_name].description,
        }

    def rank_variants(self) -> list:
        """Rank all variants by composite score. Returns sorted list of score dicts."""
        scores = []
        for vname in self.portfolios:
            score = self.score_variant(vname)
            scores.append(score)
        scores.sort(key=lambda x: x.get("score", 0), reverse=True)
        return scores


# ---------------------------------------------------------------------------
# Pick loading helpers
# ---------------------------------------------------------------------------

def _load_picks_from_file(filepath: Path) -> list:
    """Load picks from a JSON file, handling various formats."""
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["picks", "activePicks", "active_picks", "signals", "data", "results"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            if "symbol" in data or "pair" in data:
                return [data]
        return []
    except Exception as e:
        print(f"  [WARN] Could not load {filepath.name}: {e}")
        return []


def load_all_picks() -> list:
    """Load picks from all known pick files in the data directory."""
    pick_files = [
        "active_picks.json",
        "multi_asset_picks.json",
        "forex_futures_picks.json",
        "okx_picks.json",
        "bybit_picks.json",
        "bitget_picks.json",
        "binance_picks.json",
        "gmx_picks.json",
        "dex_picks.json",
        "drift_picks.json",
        "dune_picks.json",
        "htx_picks.json",
        "coinglass_picks.json",
        "okx_futures_picks.json",
    ]

    all_picks = []
    loaded_from = []

    for fname in pick_files:
        path = DATA_DIR / fname
        picks = _load_picks_from_file(path)
        if picks:
            all_picks.extend(picks)
            loaded_from.append(f"{fname}({len(picks)})")

    # Also check alpha engine picks
    alpha_picks_path = Path(__file__).parent.parent / "alpha_engine" / "data" / "active_picks.json"
    alpha_picks = _load_picks_from_file(alpha_picks_path)
    if alpha_picks:
        all_picks.extend(alpha_picks)
        loaded_from.append(f"alpha_active_picks({len(alpha_picks)})")

    print(f"[INFO] Loaded {len(all_picks)} total picks from: {', '.join(loaded_from) if loaded_from else 'none'}")
    return all_picks


# ---------------------------------------------------------------------------
# Sample data generator (for when no real picks are available)
# ---------------------------------------------------------------------------

def _generate_sample_picks() -> list:
    """Generate sample picks for demonstration when no real picks available."""
    import random
    random.seed(42)

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
               "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT"]
    picks = []

    base_time = datetime.now(timezone.utc) - timedelta(days=30)

    for i in range(100):
        sym = random.choice(symbols)
        direction = random.choice(["LONG", "SHORT"])
        entry = random.uniform(10, 50000)
        tp_dist = entry * random.uniform(0.01, 0.05)
        sl_dist = entry * random.uniform(0.005, 0.03)

        if direction == "LONG":
            tp = entry + tp_dist
            sl = entry - sl_dist
        else:
            tp = entry - tp_dist
            sl = entry + sl_dist

        picks.append({
            "symbol": sym,
            "direction": direction,
            "entryPrice": round(entry, 8),
            "targetPrice": round(tp, 8),
            "stopPrice": round(sl, 8),
            "confidence": round(random.uniform(0.45, 0.90), 2),
            "strategy": random.choice(["rsi_mean_reversion", "macd_crossover", "ema_crossover",
                                       "momentum_20d", "bollinger_breakout", "atr_breakout"]),
            "max_hold": random.choice([5, 10, 15, 20]),
            "timestamp": (base_time + timedelta(hours=i * 7)).isoformat(),
        })

    print(f"  [SAMPLE] Generated {len(picks)} sample picks for demonstration")
    return picks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  Variation Portfolio Builder")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Load picks from all sources
    picks = load_all_picks()
    if not picks:
        print("[WARN] No picks found - generating sample data for demonstration")
        picks = _generate_sample_picks()

    # Build all 5 variants
    print(f"\nBuilding {len(VARIANTS)} portfolio variants from {len(picks)} picks...")
    builder = VariationPortfolioBuilder(starting_capital=10000.0)
    variant_results = builder.build_all_variants(picks)

    # Score and rank
    print(f"\nScoring variants...")
    rankings = builder.rank_variants()

    # Save portfolio results (compact - no full trade lists)
    portfolios_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "starting_capital": 10000.0,
        "total_picks": len(picks),
        "variants": {},
    }
    for vname, vresult in variant_results.items():
        compact = dict(vresult)
        compact["closed_trades_count"] = len(compact.pop("closed_trades", []))
        compact.pop("equity_curve", None)
        portfolios_output["variants"][vname] = compact

    portfolios_path = DATA_DIR / "variation_portfolios.json"
    try:
        with open(portfolios_path, "w", encoding="utf-8") as f:
            json.dump(portfolios_output, f, indent=2, default=str)
        print(f"[SAVED] {portfolios_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save portfolios: {e}")

    # Save scores
    scores_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rankings": rankings,
        "best_variant": rankings[0]["variant"] if rankings else None,
        "best_score": rankings[0]["score"] if rankings else 0,
    }

    scores_path = DATA_DIR / "variation_scores.json"
    try:
        with open(scores_path, "w", encoding="utf-8") as f:
            json.dump(scores_output, f, indent=2, default=str)
        print(f"[SAVED] {scores_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save scores: {e}")

    # Print leaderboard
    print(f"\n{'='*70}")
    print("  VARIANT LEADERBOARD")
    print(f"{'='*70}")
    print(f"  {'Rank':<6} {'Variant':<15} {'Score':<8} {'WR%':<8} {'PF':<8} {'Return%':<10} {'MaxDD':<8} {'Trades':<8}")
    print(f"  {'-'*71}")

    for rank, entry in enumerate(rankings, 1):
        comp = entry.get("components", {})
        print(f"  {rank:<6} {entry['variant']:<15} {entry['score']:<8.1f} "
              f"{comp.get('win_rate', 0):<8.1%} {comp.get('profit_factor', 0):<8.2f} "
              f"{entry.get('total_return_pct', 0):<+10.2f} {comp.get('max_drawdown', 0):<8.2%} "
              f"{entry.get('trades', 0):<8}")

    if rankings:
        best = rankings[0]
        print(f"\n  BEST VARIANT: {best['variant']} (score: {best['score']:.1f})")
        print(f"  {VARIANTS[best['variant']].description}")

    print(f"\n[DONE] Variation portfolio analysis complete.")
    return rankings


if __name__ == "__main__":
    main()
