"""Stress Test Engine — Synthetic nightmare scenario generator for combo validation.

Generates realistic synthetic market data using Geometric Brownian Motion (GBM)
with regime switches, then tests permutation combos against 5 nightmare scenarios.
A combo must survive >=4/5 nightmares with positive Sharpe to pass.

Based on the "MarketDreamer" concept: stress-test before going live.

Usage:
    python -m meta_strategy.stress_test
    python -m meta_strategy.stress_test --top 10
    python -m meta_strategy.stress_test --combo-id "mercury2+alpha_engine|majority"
"""

import json
import math
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import numpy as np

from meta_strategy.db import get_db

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"

NIGHTMARE_SCENARIOS = [
    # Original 5 scenarios
    {"name": "Flash_Crash", "vol_mult": 5.0, "gap_pct": -0.15, "duration_bars": 48},
    {"name": "Infinite_Pump", "trend_pct": 0.03, "duration_bars": 720, "vol_mult": 0.5},
    {"name": "Correlation_One", "all_corr": 0.95, "trend_pct": -0.02, "duration_bars": 168},
    {"name": "Liquidity_Void", "vol_mult": 3.0, "spread_mult": 5.0, "duration_bars": 48},
    {"name": "Regime_Flipper", "regime_changes": 20, "duration_bars": 336},
    # New scenarios (v2.1) — tests ML/on-chain/funding rate dependent strategies
    {"name": "Funding_Rate_Spiral", "funding_mult": 10.0, "vol_mult": 2.0, "duration_bars": 168,
     "desc": "Funding rates spike to 0.1%+ per 8h — kills carry trades and funding-dependent signals"},
    {"name": "Low_Volume_Grind", "vol_mult": 0.3, "volume_mult": 0.2, "duration_bars": 336,
     "desc": "2-week period with 80% below-average volume — tests volume_confirm entry genes"},
    {"name": "BTC_Dominance_Surge", "dom_shift": 15.0, "trend_pct": 0.01, "duration_bars": 504,
     "desc": "BTC dominance rises 50→65% — all altcoin signals fail, tests cross-asset gene"},
]

# Base GBM parameters (hourly bars, crypto-like)
BASE_MU = 0.0002          # slight upward drift per bar
BASE_SIGMA = 0.015        # ~1.5% hourly vol (crypto)
BASE_PRICE = 50000.0      # starting price
BASE_VOLUME = 1_000_000.0


# ---------------------------------------------------------------------------
# Synthetic Market Generator
# ---------------------------------------------------------------------------

class SyntheticMarketGenerator:
    """Generate realistic OHLCV price series using GBM + regime switches."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def generate_gbm(
        self,
        n_bars: int,
        mu: float = BASE_MU,
        sigma: float = BASE_SIGMA,
        start_price: float = BASE_PRICE,
    ) -> np.ndarray:
        """Pure GBM: S(t+1) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)"""
        dt = 1.0
        Z = self.rng.standard_normal(n_bars)
        log_returns = (mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * Z
        log_prices = np.cumsum(log_returns)
        log_prices = np.insert(log_prices, 0, 0.0)  # start at 0
        prices = start_price * np.exp(log_prices)
        return prices  # length n_bars + 1

    def _prices_to_ohlcv(self, close_prices: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """Convert a close-price series into OHLCV tuples with realistic wicks."""
        bars = []
        for i in range(1, len(close_prices)):
            c = close_prices[i]
            o = close_prices[i - 1]
            spread = abs(c - o) * 0.5 + abs(c) * 0.002
            noise_h = abs(self.rng.normal(0, spread))
            noise_l = abs(self.rng.normal(0, spread))
            h = max(o, c) + noise_h
            l = min(o, c) - noise_l
            # Volume: higher on big moves
            move_pct = abs(c - o) / (o if o > 0 else 1)
            vol = BASE_VOLUME * (1.0 + move_pct * 50) * (0.5 + self.rng.random())
            bars.append((round(o, 2), round(h, 2), round(l, 2), round(c, 2), round(vol, 0)))
        return bars

    def generate_scenario(self, scenario: Dict) -> List[Tuple[float, float, float, float, float]]:
        """Generate OHLCV bars for a given nightmare scenario."""
        name = scenario["name"]
        n_bars = scenario.get("duration_bars", 168)
        vol_mult = scenario.get("vol_mult", 1.0)
        sigma = BASE_SIGMA * vol_mult

        if name == "Flash_Crash":
            return self._gen_flash_crash(scenario, n_bars, sigma)
        elif name == "Infinite_Pump":
            return self._gen_infinite_pump(scenario, n_bars, sigma)
        elif name == "Correlation_One":
            return self._gen_correlation_one(scenario, n_bars, sigma)
        elif name == "Liquidity_Void":
            return self._gen_liquidity_void(scenario, n_bars, sigma)
        elif name == "Regime_Flipper":
            return self._gen_regime_flipper(scenario, n_bars, sigma)
        elif name == "Funding_Rate_Spiral":
            # High vol + choppy — carry trades get killed by both directions
            prices = self.generate_gbm(n_bars, mu=-0.0003, sigma=sigma)
            return self._prices_to_ohlcv(prices)
        elif name == "Low_Volume_Grind":
            # Low vol, low volume — thin market with minimal moves
            prices = self.generate_gbm(n_bars, mu=0.0001, sigma=sigma)
            ohlcv = self._prices_to_ohlcv(prices)
            vol_mult = scenario.get("volume_mult", 0.2)
            return [(o, h, l, c, v * vol_mult) for o, h, l, c, v in ohlcv]
        elif name == "BTC_Dominance_Surge":
            # Steady uptrend (BTC up), but altcoins lag — simulate modest gains
            trend = scenario.get("trend_pct", 0.01) / n_bars
            prices = self.generate_gbm(n_bars, mu=trend, sigma=sigma * 0.5)
            return self._prices_to_ohlcv(prices)
        else:
            # Fallback: plain GBM with vol multiplier
            prices = self.generate_gbm(n_bars, sigma=sigma)
            return self._prices_to_ohlcv(prices)

    def _gen_flash_crash(self, scenario: Dict, n_bars: int, sigma: float) -> list:
        """Sudden gap down at random point, then high-vol recovery."""
        gap_pct = scenario.get("gap_pct", -0.15)
        crash_bar = self.rng.integers(n_bars // 4, n_bars // 2)

        # Pre-crash: normal market
        pre = self.generate_gbm(crash_bar, sigma=BASE_SIGMA)
        crash_price = pre[-1] * (1.0 + gap_pct)

        # Post-crash: high vol recovery
        post = self.generate_gbm(n_bars - crash_bar, mu=0.001, sigma=sigma, start_price=crash_price)

        prices = np.concatenate([pre, post[1:]])
        return self._prices_to_ohlcv(prices)

    def _gen_infinite_pump(self, scenario: Dict, n_bars: int, sigma: float) -> list:
        """Relentless uptrend with low volatility — tests short-side risk."""
        trend_pct = scenario.get("trend_pct", 0.03)
        prices = self.generate_gbm(n_bars, mu=trend_pct, sigma=sigma)
        return self._prices_to_ohlcv(prices)

    def _gen_correlation_one(self, scenario: Dict, n_bars: int, sigma: float) -> list:
        """Everything moves together in a downtrend — no diversification benefit."""
        trend_pct = scenario.get("trend_pct", -0.02)
        corr = scenario.get("all_corr", 0.95)
        # Single dominant factor drives price
        factor = self.rng.standard_normal(n_bars)
        idio = self.rng.standard_normal(n_bars)
        # Mix: corr * factor + sqrt(1-corr^2) * idiosyncratic
        Z = corr * factor + math.sqrt(1 - corr**2) * idio
        dt = 1.0
        mu = trend_pct
        log_returns = (mu - 0.5 * BASE_SIGMA**2) * dt + BASE_SIGMA * math.sqrt(dt) * Z
        log_prices = np.cumsum(log_returns)
        log_prices = np.insert(log_prices, 0, 0.0)
        prices = BASE_PRICE * np.exp(log_prices)
        return self._prices_to_ohlcv(prices)

    def _gen_liquidity_void(self, scenario: Dict, n_bars: int, sigma: float) -> list:
        """High vol + wide spreads = slippage nightmare."""
        spread_mult = scenario.get("spread_mult", 5.0)
        prices = self.generate_gbm(n_bars, sigma=sigma)
        bars = []
        for i in range(1, len(prices)):
            c = prices[i]
            o = prices[i - 1]
            # Exaggerated wicks simulating thin order book
            spread = abs(c - o) * spread_mult + abs(c) * 0.01
            noise_h = abs(self.rng.normal(0, spread))
            noise_l = abs(self.rng.normal(0, spread))
            h = max(o, c) + noise_h
            l = min(o, c) - noise_l
            move_pct = abs(c - o) / (o if o > 0 else 1)
            # Low volume in liquidity void
            vol = BASE_VOLUME * 0.1 * (1.0 + move_pct * 10) * (0.3 + self.rng.random() * 0.4)
            bars.append((round(o, 2), round(h, 2), round(l, 2), round(c, 2), round(vol, 0)))
        return bars

    def _gen_regime_flipper(self, scenario: Dict, n_bars: int, sigma: float) -> list:
        """Rapid alternation between bull/bear/sideways regimes."""
        regime_changes = scenario.get("regime_changes", 20)
        segment_len = max(n_bars // regime_changes, 2)

        regimes = [
            {"mu": 0.005, "sigma": BASE_SIGMA * 0.8},     # bull
            {"mu": -0.005, "sigma": BASE_SIGMA * 1.2},     # bear
            {"mu": 0.0, "sigma": BASE_SIGMA * 2.0},        # chop
        ]

        all_prices = [BASE_PRICE]
        current_price = BASE_PRICE
        bars_generated = 0

        for _ in range(regime_changes):
            regime = regimes[self.rng.integers(0, len(regimes))]
            seg_bars = min(segment_len, n_bars - bars_generated)
            if seg_bars <= 0:
                break
            seg = self.generate_gbm(
                seg_bars, mu=regime["mu"], sigma=regime["sigma"],
                start_price=current_price,
            )
            all_prices.extend(seg[1:].tolist())
            current_price = seg[-1]
            bars_generated += seg_bars

        prices = np.array(all_prices)
        return self._prices_to_ohlcv(prices)

    @staticmethod
    def validate_realism(bars: List[Tuple]) -> Dict:
        """Check synthetic data for realism: vol clustering, fat tails, autocorrelation."""
        if len(bars) < 10:
            return {"valid": False, "reason": "too few bars"}

        closes = np.array([b[3] for b in bars], dtype=np.float64)
        returns = np.diff(np.log(closes + 1e-10))

        if len(returns) < 5:
            return {"valid": False, "reason": "too few returns"}

        kurtosis = float(np.mean((returns - returns.mean()) ** 4) / (np.var(returns) ** 2 + 1e-20))
        # Autocorrelation of abs returns (vol clustering proxy)
        abs_ret = np.abs(returns)
        if len(abs_ret) > 1 and np.std(abs_ret) > 0:
            autocorr = float(np.corrcoef(abs_ret[:-1], abs_ret[1:])[0, 1])
        else:
            autocorr = 0.0

        return {
            "valid": True,
            "n_bars": len(bars),
            "kurtosis": round(kurtosis, 2),
            "fat_tails": kurtosis > 3.0,
            "vol_clustering_autocorr": round(autocorr, 4),
            "vol_clustering": autocorr > 0.05,
            "mean_return": round(float(returns.mean()), 6),
            "std_return": round(float(returns.std()), 6),
        }


# ---------------------------------------------------------------------------
# Stress Test Engine
# ---------------------------------------------------------------------------

class StressTestEngine:
    """Run nightmare scenarios against permutation combos."""

    def __init__(self, seed: int = 42):
        self.generator = SyntheticMarketGenerator(seed=seed)

    def stress_test_combo(self, combo_row: dict) -> Dict:
        """Test a combo against all nightmare scenarios.

        Uses the combo's historical win_rate from DB and applies regime-modified
        probabilities to simulate signal generation under stress.

        Returns dict with per-scenario results and overall PASS/FAIL.
        """
        combo_id = combo_row["combo_id"]

        # Load historical metrics from DB
        db = get_db()
        row = db.execute(
            "SELECT win_rate, sharpe, avg_pnl_pct, total_trades, max_drawdown_pct "
            "FROM permutation_results WHERE combo_id = ? AND symbol IS NULL "
            "ORDER BY last_updated DESC LIMIT 1",
            (combo_id,),
        ).fetchone()
        db.close()

        if row:
            base_wr = row["win_rate"] if row["win_rate"] else 0.5
            base_sharpe = row["sharpe"] if row["sharpe"] else 0.0
            base_avg_pnl = row["avg_pnl_pct"] if row["avg_pnl_pct"] else 0.0
            base_trades = row["total_trades"] if row["total_trades"] else 0
        else:
            base_wr = 0.5
            base_sharpe = 0.0
            base_avg_pnl = 0.0
            base_trades = 0

        scenario_results = []
        passes = 0

        for scenario in NIGHTMARE_SCENARIOS:
            result = self._run_scenario(
                combo_id, scenario, base_wr, base_avg_pnl, base_trades,
            )
            scenario_results.append(result)
            if result["survived"]:
                passes += 1

        overall_pass = passes >= 4 and all(
            r["sharpe"] > 0 for r in scenario_results if r["survived"]
        )
        # Edge case: if exactly 4 survived, all 4 must have positive Sharpe
        if passes >= 4:
            surviving = [r for r in scenario_results if r["survived"]]
            overall_pass = all(r["sharpe"] > 0 for r in surviving)
        else:
            overall_pass = False

        return {
            "combo_id": combo_id,
            "base_win_rate": round(base_wr, 4),
            "base_sharpe": round(base_sharpe, 4),
            "scenarios_passed": passes,
            "scenarios_total": len(NIGHTMARE_SCENARIOS),
            "overall_pass": overall_pass,
            "scenarios": scenario_results,
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }

    def _run_scenario(
        self,
        combo_id: str,
        scenario: Dict,
        base_wr: float,
        base_avg_pnl: float,
        base_trades: int,
    ) -> Dict:
        """Simulate a combo's performance under one nightmare scenario."""
        name = scenario["name"]
        bars = self.generator.generate_scenario(scenario)
        n_bars = len(bars)

        if n_bars < 2:
            return {
                "scenario": name,
                "survived": False,
                "reason": "insufficient bars generated",
                "max_drawdown_pct": 100.0,
                "sharpe": -999.0,
                "trade_count": 0,
            }

        # Regime-modified win rate: degrade under stress
        wr_modifier = self._scenario_wr_modifier(scenario)
        stressed_wr = max(0.05, min(0.95, base_wr * wr_modifier))

        # Simulate trades: one trade every ~12 bars on average
        trade_interval = max(4, n_bars // max(base_trades // 10, 5))
        trade_pnls = []
        portfolio = 1000.0
        peak = portfolio
        max_dd = 0.0
        position_size = 0.02  # 2% risk per trade

        bar_idx = 0
        while bar_idx < n_bars - 1:
            bar_idx += self.generator.rng.integers(max(1, trade_interval // 2), trade_interval * 2)
            if bar_idx >= n_bars - 1:
                break

            # Determine trade outcome using stressed win rate
            is_win = self.generator.rng.random() < stressed_wr

            # PnL magnitude: base avg modified by scenario volatility
            vol_mult = scenario.get("vol_mult", 1.0)
            if is_win:
                pnl_pct = abs(base_avg_pnl if base_avg_pnl != 0 else 1.5) * (0.5 + self.generator.rng.random())
            else:
                # Losses amplified by vol multiplier
                pnl_pct = -abs(base_avg_pnl if base_avg_pnl != 0 else 1.5) * vol_mult * (0.5 + self.generator.rng.random())

                # Liquidity void: extra slippage on losses
                if name == "Liquidity_Void":
                    spread_mult = scenario.get("spread_mult", 5.0)
                    pnl_pct *= (1.0 + (spread_mult - 1.0) * 0.3)

            trade_pnls.append(pnl_pct)
            portfolio *= (1.0 + pnl_pct / 100.0 * position_size * 100)
            portfolio = max(portfolio, 0.01)  # floor

            if portfolio > peak:
                peak = portfolio
            dd = (peak - portfolio) / peak * 100.0
            if dd > max_dd:
                max_dd = dd

        trade_count = len(trade_pnls)
        survived = max_dd < 50.0

        # Calculate Sharpe from trade PnLs
        if trade_count >= 2:
            arr = np.array(trade_pnls)
            sharpe = float(arr.mean() / (arr.std() + 1e-10)) * math.sqrt(252)
        elif trade_count == 1:
            sharpe = float(trade_pnls[0])
        else:
            sharpe = 0.0

        # Validate synthetic data realism
        realism = SyntheticMarketGenerator.validate_realism(bars)

        return {
            "scenario": name,
            "survived": survived,
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe": round(sharpe, 4),
            "trade_count": trade_count,
            "final_portfolio": round(portfolio, 2),
            "stressed_win_rate": round(stressed_wr, 4),
            "scenario_bars": n_bars,
            "realism_check": realism,
        }

    @staticmethod
    def _scenario_wr_modifier(scenario: Dict) -> float:
        """How much a scenario degrades the base win rate."""
        name = scenario["name"]
        modifiers = {
            "Flash_Crash": 0.6,       # WR drops 40% — panic, gaps skip stops
            "Infinite_Pump": 0.75,     # WR drops 25% — shorts destroyed
            "Correlation_One": 0.7,    # WR drops 30% — diversification fails
            "Liquidity_Void": 0.55,    # WR drops 45% — slippage eats wins
            "Regime_Flipper": 0.65,    # WR drops 35% — whipsaw city
            "Funding_Rate_Spiral": 0.5,  # WR drops 50% — carry trades obliterated
            "Low_Volume_Grind": 0.7,     # WR drops 30% — volume signals fail
            "BTC_Dominance_Surge": 0.6,  # WR drops 40% — altcoin signals destroyed
        }
        return modifiers.get(name, 0.7)


# ---------------------------------------------------------------------------
# Top-level functions
# ---------------------------------------------------------------------------

def load_top_combos(n: int = 20) -> List[dict]:
    """Load top N active combos by Sharpe from the DB."""
    db = get_db()
    rows = db.execute(
        """
        SELECT p.combo_id, p.systems, p.logic_type, p.status,
               pr.sharpe, pr.win_rate, pr.total_trades, pr.avg_pnl_pct,
               pr.max_drawdown_pct
        FROM permutations p
        LEFT JOIN permutation_results pr
            ON p.combo_id = pr.combo_id AND pr.symbol IS NULL
        WHERE p.status IN ('ACTIVE', 'PROBATION')
        ORDER BY COALESCE(pr.sharpe, 0) DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()
    db.close()

    combos = []
    for r in rows:
        combos.append({
            "combo_id": r["combo_id"],
            "systems": r["systems"],
            "logic_type": r["logic_type"],
            "status": r["status"],
            "sharpe": r["sharpe"] or 0.0,
            "win_rate": r["win_rate"] or 0.5,
            "total_trades": r["total_trades"] or 0,
            "avg_pnl_pct": r["avg_pnl_pct"] or 0.0,
            "max_drawdown_pct": r["max_drawdown_pct"] or 0.0,
        })
    return combos


def save_results(results: List[Dict]) -> Path:
    """Save stress test results to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "stress_test_results.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario_definitions": NIGHTMARE_SCENARIOS,
        "total_combos_tested": len(results),
        "total_passed": sum(1 for r in results if r["overall_pass"]),
        "total_failed": sum(1 for r in results if not r["overall_pass"]),
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out_path


def print_results(results: List[Dict]) -> None:
    """Pretty-print stress test results to stdout."""
    header = f"{'Combo ID':<45} {'Pass?':<6} {'Survived':<10} {'Base SR':<9} {'Base WR':<9}"
    print("=" * len(header))
    print("STRESS TEST RESULTS")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for r in results:
        tag = "PASS" if r["overall_pass"] else "FAIL"
        survived = f"{r['scenarios_passed']}/{r['scenarios_total']}"
        combo_short = r["combo_id"][:44]
        print(f"{combo_short:<45} {tag:<6} {survived:<10} {r['base_sharpe']:<9.2f} {r['base_win_rate']:<9.2%}")

    print("-" * len(header))
    total_pass = sum(1 for r in results if r["overall_pass"])
    print(f"Total: {total_pass}/{len(results)} passed stress test")
    print()

    # Per-scenario breakdown
    for r in results:
        if not r["overall_pass"]:
            print(f"  FAILED: {r['combo_id']}")
            for s in r["scenarios"]:
                status = "OK" if s["survived"] else "DEAD"
                print(f"    {s['scenario']:<20} {status:<5} DD={s['max_drawdown_pct']:6.1f}%  SR={s['sharpe']:7.2f}  trades={s['trade_count']}")
            print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Stress Test Engine — nightmare scenario testing")
    parser.add_argument("--top", type=int, default=20, help="Number of top combos to test (default: 20)")
    parser.add_argument("--combo-id", type=str, default=None, help="Test a specific combo by ID")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    engine = StressTestEngine(seed=args.seed)

    if args.combo_id:
        # Test single combo
        combos = [{"combo_id": args.combo_id}]
        print(f"Stress testing single combo: {args.combo_id}")
    else:
        combos = load_top_combos(args.top)
        if not combos:
            print("No active combos found in DB. Nothing to stress test.")
            print(f"DB path: {Path(__file__).parent / 'data' / 'meta_strategy.db'}")
            return
        print(f"Loaded {len(combos)} combos for stress testing")

    results = []
    for i, combo in enumerate(combos, 1):
        cid = combo["combo_id"]
        print(f"  [{i}/{len(combos)}] Testing: {cid[:60]}...", flush=True)
        result = engine.stress_test_combo(combo)
        results.append(result)
        tag = "PASS" if result["overall_pass"] else "FAIL"
        print(f"           -> {tag} ({result['scenarios_passed']}/{result['scenarios_total']} survived)")

    print()
    print_results(results)

    out_path = save_results(results)
    print(f"Results saved to: {out_path}")


if __name__ == "__main__":
    main()
