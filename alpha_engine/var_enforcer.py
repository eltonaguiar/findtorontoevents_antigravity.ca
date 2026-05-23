#!/usr/bin/env python3
"""
VaR Enforcer & Stress Testing — Phase 3 Hedge Fund Roadmap
============================================================
Enforces daily Value-at-Risk limits and runs stress test scenarios
on the current portfolio.

Components:
  1. Daily VaR Limit (2% target) — computes historical VaR(95%) from
     last 30 days of closed picks, returns a sizing multiplier [0.0-1.0]
  2. Stress Test Scenarios — simulates 5 tail-risk events, flags
     STRESS_WARNING if any scenario loss > 15%

Integration:
  - get_var_sizing_multiplier() is called from production_scanner after
    Kelly sizing to scale down positions when VaR budget is exceeded
  - apply_var_enforcement() is the batch function wired into the pipeline

Data files:
  - data/stress_test_results.json  (scenario outputs + warnings)
  - data/var_state.json            (current VaR state + multiplier)

Pure Python (no scipy). Backwards-compatible — never raises, returns
safe defaults on error.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# -- Windows UTF-8 fix --------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# -- Paths --------------------------------------------------------------------
_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"
_ROOT = _ENGINE_DIR.parent

VAR_STATE_PATH = _DATA_DIR / "var_state.json"
STRESS_TEST_PATH = _DATA_DIR / "stress_test_results.json"

# -- Configuration ------------------------------------------------------------
VAR_TARGET_PCT = 2.0        # Max daily VaR as % of portfolio
VAR_CONFIDENCE = 0.95       # 95th percentile
VAR_LOOKBACK_DAYS = 30      # Rolling window for historical VaR
STRESS_LOSS_THRESHOLD = 15.0  # % loss that triggers STRESS_WARNING

# Default portfolio value (used when env var not set)
DEFAULT_PORTFOLIO_VALUE = 10000


# =============================================================================
# Helpers
# =============================================================================

def _load_json(path: Path) -> list | dict:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_json(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"  [VAR] Could not write {path.name}: {e}")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _percentile(sorted_vals: list[float], pct: float) -> float:
    """Linear-interpolation percentile on a pre-sorted list."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    k = (pct / 100.0) * (n - 1)
    lo = int(math.floor(k))
    hi = min(lo + 1, n - 1)
    frac = k - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


# =============================================================================
# 1. Load closed picks for VaR computation
# =============================================================================

def _load_closed_picks() -> list[dict]:
    """Load closed picks from available sources.

    Tries dashboard_payload.json first (richer data), then closed_picks.json.
    """
    # Primary: dashboard_payload.json -> picks.recent_closed
    payload_path = _ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    if payload_path.exists():
        try:
            with open(payload_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            closed = data.get("picks", {}).get("recent_closed", [])
            picks = [
                p for p in closed
                if p.get("pnl_pct") is not None
                and not p.get("_auto_expired", False)
            ]
            if picks:
                return picks
        except Exception:
            pass

    # Fallback: closed_picks.json
    fallback_path = _DATA_DIR / "closed_picks.json"
    if fallback_path.exists():
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                picks = json.load(f)
            return [p for p in picks if p.get("pnl_pct") is not None]
        except Exception:
            pass

    return []


def _filter_recent_picks(picks: list[dict], days: int = 30) -> list[dict]:
    """Filter picks to only those closed within the last N days."""
    cutoff = (_now_utc() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = []
    for p in picks:
        exit_date = p.get("exit_date", "") or p.get("closed_at", "")
        if exit_date >= cutoff:
            recent.append(p)
    # If not enough recent data, use all available (graceful degradation)
    if len(recent) < 10:
        return picks
    return recent


# =============================================================================
# 2. Historical VaR computation
# =============================================================================

def _aggregate_daily_pnl(picks: list[dict]) -> list[float]:
    """Aggregate per-pick PnL into daily P/L values.

    Groups picks by exit_date and sums their pnl_pct per day.
    Returns a list of daily P/L percentages.
    """
    daily: dict[str, float] = {}
    for p in picks:
        date_key = p.get("exit_date", "") or ""
        if not date_key:
            # Try to extract date from closed_at
            closed_at = p.get("closed_at", "")
            if closed_at:
                date_key = closed_at[:10]
        if not date_key:
            continue
        pnl = float(p.get("pnl_pct", 0) or 0)
        daily[date_key] = daily.get(date_key, 0.0) + pnl

    if not daily:
        # Fall back to per-pick P/L if no date grouping possible
        return [float(p.get("pnl_pct", 0) or 0) for p in picks]

    # Sort by date and return values
    return [v for _, v in sorted(daily.items())]


def compute_historical_var(picks: list[dict],
                           confidence: float = 0.95) -> dict:
    """Compute historical VaR(95%) from closed picks.

    Returns dict with var_95, es_95, n_days, daily_pnl_stats.
    VaR is returned as a positive number (loss magnitude).
    """
    daily_pnl = _aggregate_daily_pnl(picks)

    if len(daily_pnl) < 5:
        return {
            "var_95": 0.0,
            "es_95": 0.0,
            "n_days": len(daily_pnl),
            "mean_daily_pnl": 0.0,
            "std_daily_pnl": 0.0,
            "sufficient_data": False,
        }

    sorted_pnl = sorted(daily_pnl)
    n = len(daily_pnl)
    mean_pnl = sum(daily_pnl) / n

    # Variance (sample)
    variance = sum((x - mean_pnl) ** 2 for x in daily_pnl) / max(n - 1, 1)
    std_pnl = math.sqrt(variance)

    # VaR at (1 - confidence) percentile
    cutoff_pct = (1.0 - confidence) * 100.0  # 5.0 for 95% confidence
    var_value = _percentile(sorted_pnl, cutoff_pct)
    var_95 = -var_value  # Positive = loss magnitude

    # Expected Shortfall (average loss beyond VaR)
    tail = [v for v in sorted_pnl if v <= var_value]
    if tail:
        es_95 = -(sum(tail) / len(tail))
    else:
        es_95 = var_95

    return {
        "var_95": round(var_95, 6),
        "es_95": round(es_95, 6),
        "n_days": n,
        "mean_daily_pnl": round(mean_pnl, 6),
        "std_daily_pnl": round(std_pnl, 6),
        "sufficient_data": True,
    }


# =============================================================================
# 3. VaR Sizing Multiplier
# =============================================================================

def get_var_sizing_multiplier(active_picks: list[dict] | None = None) -> float:
    """Compute the VaR-based sizing multiplier [0.0 - 1.0].

    Logic:
      1. Load last 30 days of closed picks
      2. Compute historical VaR(95%)
      3. Estimate current portfolio exposure from active picks
      4. If exposure * VaR(95%) > 2% of portfolio -> reduce proportionally
      5. Return multiplier (1.0 = no reduction, <1.0 = reduce sizes)

    This function never raises. Returns 1.0 on error.
    """
    try:
        # Load and filter closed picks
        all_closed = _load_closed_picks()
        recent = _filter_recent_picks(all_closed, days=VAR_LOOKBACK_DAYS)

        if len(recent) < 5:
            print(f"  [VAR] Insufficient data ({len(recent)} picks) -- multiplier=1.0")
            return 1.0

        # Compute historical VaR
        var_data = compute_historical_var(recent, VAR_CONFIDENCE)
        var_95 = var_data["var_95"]

        if var_95 <= 0:
            # No measurable downside risk (unlikely but safe)
            return 1.0

        # Estimate current exposure
        # Count active positions and their aggregate weight
        n_active = len(active_picks) if active_picks else 0
        if n_active == 0:
            return 1.0

        # Aggregate exposure: sum of position_size / portfolio_value
        # If position_size not available, assume equal weight
        portfolio_val = float(os.environ.get("ALPHA_PORTFOLIO_VALUE",
                                             str(DEFAULT_PORTFOLIO_VALUE)))
        total_exposure = 0.0
        for p in (active_picks or []):
            pos_size = p.get("position_size", 0)
            if pos_size > 0:
                total_exposure += pos_size / portfolio_val
            else:
                # Fallback: assume 2% per position (typical Half-Kelly)
                total_exposure += 0.02

        # Clamp exposure to reasonable range
        total_exposure = min(total_exposure, 1.5)  # Max 150% (leveraged)

        # Portfolio VaR estimate = exposure * historical VaR
        # VaR is in pnl_pct units (e.g., 0.02 = 2%)
        # Convert var_95 to percentage for comparison
        portfolio_var_pct = total_exposure * var_95 * 100.0

        # Target: portfolio VaR should not exceed VAR_TARGET_PCT (2%)
        if portfolio_var_pct <= VAR_TARGET_PCT:
            multiplier = 1.0
        else:
            # Scale down proportionally
            multiplier = VAR_TARGET_PCT / portfolio_var_pct
            multiplier = max(0.0, min(1.0, multiplier))

        # Save state for monitoring
        state = {
            "updated_at": _now_utc().isoformat(),
            "var_95_per_day": round(var_95, 6),
            "es_95_per_day": var_data["es_95"],
            "n_days_used": var_data["n_days"],
            "n_active_picks": n_active,
            "total_exposure": round(total_exposure, 4),
            "portfolio_var_pct": round(portfolio_var_pct, 4),
            "var_target_pct": VAR_TARGET_PCT,
            "sizing_multiplier": round(multiplier, 4),
            "warning": multiplier < 0.5,
        }
        _save_json(VAR_STATE_PATH, state)

        if multiplier < 1.0:
            print(f"  [VAR] Portfolio VaR={portfolio_var_pct:.2f}% > target {VAR_TARGET_PCT}% "
                  f"-- multiplier={multiplier:.3f}")
        else:
            print(f"  [VAR] Portfolio VaR={portfolio_var_pct:.2f}% <= target {VAR_TARGET_PCT}% "
                  f"-- no reduction needed")

        if multiplier < 0.5:
            print(f"  [VAR] WARNING: Severe VaR breach -- multiplier={multiplier:.3f} "
                  f"(below 0.5 threshold)")

        return multiplier

    except Exception as e:
        print(f"  [VAR] Enforcement failed (safe fallback=1.0): {e}")
        return 1.0


# =============================================================================
# 4. Stress Test Scenarios
# =============================================================================

def _estimate_pick_loss(pick: dict, market_shock_pct: float,
                        correlation: float = 1.0) -> float:
    """Estimate loss on a single pick given a market shock.

    Uses the pick's position_size or kelly_fraction to weight the loss.
    Correlation scales how much the asset moves with the market.
    """
    # Position weight (fraction of portfolio)
    portfolio_val = float(os.environ.get("ALPHA_PORTFOLIO_VALUE",
                                         str(DEFAULT_PORTFOLIO_VALUE)))
    pos_size = pick.get("position_size", 0)
    if pos_size > 0:
        weight = pos_size / portfolio_val
    else:
        weight = pick.get("kelly_fraction", 0.02)

    # Asset-specific shock = market shock * correlation
    asset_shock = market_shock_pct * correlation
    return weight * asset_shock


def _get_asset_correlation(pick: dict, scenario: str) -> float:
    """Return estimated correlation of this pick's asset to the scenario shock."""
    symbol = (pick.get("symbol", "") or "").upper()
    category = (pick.get("category", "") or "").lower()
    signal_type = (pick.get("signal_type", "") or "").upper()

    # Short positions benefit from crashes (inverted)
    direction = -1.0 if signal_type == "SELL" else 1.0

    if scenario == "btc_flash_crash":
        if "BTC" in symbol:
            return 1.0 * direction
        # Altcoins correlated at 0.85
        if category in ("crypto", "meme"):
            return 0.85 * direction
        if category == "forex":
            return 0.15 * direction  # Mild crypto-forex correlation
        return 0.05 * direction  # Equities minimal correlation

    elif scenario == "full_market_crash":
        if category in ("crypto", "meme"):
            return 1.0 * direction
        if category == "forex":
            return 0.4 * direction   # Risk-off hits forex carry
        return 0.7 * direction       # Equities also crash in March 2020

    elif scenario == "funding_rate_inversion":
        # Carry trades get hit, directional trades less affected
        strategy = (pick.get("strategy", "") or "").lower()
        if "carry" in strategy or "funding" in strategy:
            return 0.9 * direction
        if category in ("crypto", "meme"):
            return 0.3 * direction   # General crypto volatility
        return 0.05 * direction

    elif scenario == "stablecoin_depeg":
        # USDT depeg hits all USDT-denominated positions
        if "USDT" in symbol:
            return 0.5 * direction   # Partial pass-through
        if category in ("crypto", "meme"):
            return 0.3 * direction   # Contagion fear
        return 0.05 * direction

    elif scenario == "exchange_halt":
        # Can't close positions -- exposed to full market move
        # Assume a 10% adverse move while exchange is down
        if category in ("crypto", "meme"):
            return 1.0 * direction
        return 0.1 * direction       # Non-crypto unaffected

    return 0.5 * direction


def run_stress_tests(active_picks: list[dict] | None = None) -> dict:
    """Run 5 stress test scenarios on the current portfolio.

    Scenarios:
      a. BTC -20% flash crash (alts correlated at 0.85)
      b. Full market -30% (March 2020 style)
      c. Funding rate inversion (carry unwind)
      d. Stablecoin depeg (USDT -5%)
      e. Exchange halt (Binance down 24h)

    Returns dict with per-scenario losses and overall stress_warning flag.
    """
    try:
        if not active_picks:
            return {
                "updated_at": _now_utc().isoformat(),
                "scenarios": {},
                "stress_warning": False,
                "max_scenario_loss_pct": 0.0,
                "note": "No active picks to stress test",
            }

        scenarios = {
            "btc_flash_crash": {
                "description": "BTC -20% flash crash (alts at 0.85 correlation)",
                "market_shock_pct": -0.20,
            },
            "full_market_crash": {
                "description": "Full market -30% crash (March 2020 style)",
                "market_shock_pct": -0.30,
            },
            "funding_rate_inversion": {
                "description": "Funding rate inversion (carry trade unwind)",
                "market_shock_pct": -0.10,
            },
            "stablecoin_depeg": {
                "description": "USDT -5% stablecoin depeg",
                "market_shock_pct": -0.05,
            },
            "exchange_halt": {
                "description": "Binance down 24h (positions cannot close, assume -10% adverse move)",
                "market_shock_pct": -0.10,
            },
        }

        results = {}
        max_loss = 0.0
        stress_warning = False

        for scenario_name, scenario_cfg in scenarios.items():
            market_shock = scenario_cfg["market_shock_pct"]
            total_loss = 0.0
            pick_losses = []

            for pick in active_picks:
                corr = _get_asset_correlation(pick, scenario_name)
                loss = _estimate_pick_loss(pick, market_shock, correlation=corr)
                total_loss += loss
                pick_losses.append({
                    "symbol": pick.get("symbol", "?"),
                    "loss_pct": round(loss * 100, 4),
                })

            # Convert to percentage
            loss_pct = abs(total_loss * 100)

            # Sort by worst loss
            pick_losses.sort(key=lambda x: x["loss_pct"])

            breached = loss_pct > STRESS_LOSS_THRESHOLD
            if breached:
                stress_warning = True

            if loss_pct > max_loss:
                max_loss = loss_pct

            results[scenario_name] = {
                "description": scenario_cfg["description"],
                "market_shock_pct": market_shock * 100,
                "estimated_portfolio_loss_pct": round(loss_pct, 4),
                "breaches_threshold": breached,
                "threshold_pct": STRESS_LOSS_THRESHOLD,
                "top_losers": pick_losses[:5],  # Top 5 worst affected
                "n_picks_affected": len([p for p in pick_losses if p["loss_pct"] != 0]),
            }

        output = {
            "updated_at": _now_utc().isoformat(),
            "n_active_picks": len(active_picks),
            "scenarios": results,
            "stress_warning": stress_warning,
            "max_scenario_loss_pct": round(max_loss, 4),
        }

        _save_json(STRESS_TEST_PATH, output)

        # Console output
        print()
        print("  " + "=" * 56)
        print("  STRESS TEST RESULTS")
        print("  " + "=" * 56)
        for name, res in results.items():
            flag = " ** BREACH **" if res["breaches_threshold"] else ""
            print(f"  {res['description']}")
            print(f"    Portfolio loss: {res['estimated_portfolio_loss_pct']:.2f}%{flag}")
        print("  " + "-" * 56)
        if stress_warning:
            print(f"  STRESS_WARNING: Max scenario loss {max_loss:.2f}% > {STRESS_LOSS_THRESHOLD}% threshold")
        else:
            print(f"  All scenarios within {STRESS_LOSS_THRESHOLD}% threshold (max={max_loss:.2f}%)")
        print("  " + "=" * 56)

        return output

    except Exception as e:
        print(f"  [STRESS TEST] Failed (non-fatal): {e}")
        return {
            "updated_at": _now_utc().isoformat(),
            "scenarios": {},
            "stress_warning": False,
            "error": str(e),
        }


# =============================================================================
# 5. Pipeline Integration — batch function for production_scanner
# =============================================================================

def apply_var_enforcement(picks: list[dict]) -> list[dict]:
    """Apply VaR enforcement to all active picks.

    Called from production_scanner after Kelly sizing.
    Computes VaR multiplier and scales down all position sizes if needed.
    Also runs stress tests and logs results.

    Returns the same list with position_size adjusted.
    """
    try:
        # 1. Compute VaR sizing multiplier
        multiplier = get_var_sizing_multiplier(active_picks=picks)

        # 2. Apply multiplier to position sizes if < 1.0
        if multiplier < 1.0:
            adjusted = 0
            for p in picks:
                pos_size = p.get("position_size", 0)
                if pos_size > 0:
                    p["position_size"] = round(pos_size * multiplier, 2)
                    adjusted += 1
                # Also scale position_multiplier if present
                current_mult = p.get("position_multiplier", 1.0)
                p["position_multiplier"] = round(current_mult * multiplier, 2)
                p["_var_multiplier"] = round(multiplier, 4)

            print(f"  [VAR] Reduced {adjusted} positions by {(1-multiplier)*100:.1f}% "
                  f"(multiplier={multiplier:.3f})")

            if multiplier < 0.5:
                # Tag picks with warning for downstream alerting
                for p in picks:
                    p["_var_warning"] = True
                print(f"  [VAR] WARNING ALERT: VaR multiplier {multiplier:.3f} < 0.5 "
                      f"-- severe risk, consider manual review")

        # 3. Run stress tests (non-blocking, informational)
        run_stress_tests(picks)

        return picks

    except Exception as e:
        print(f"  [VAR] Enforcement pipeline failed (safe fallback=no changes): {e}")
        return picks


# =============================================================================
# CLI entry point
# =============================================================================

if __name__ == "__main__":
    print("[VAR ENFORCER] Running standalone diagnostics...")
    print()

    # Load closed picks
    closed = _load_closed_picks()
    recent = _filter_recent_picks(closed, days=VAR_LOOKBACK_DAYS)
    print(f"Closed picks: {len(closed)} total, {len(recent)} last {VAR_LOOKBACK_DAYS} days")

    # Compute VaR
    var_data = compute_historical_var(recent, VAR_CONFIDENCE)
    print(f"\nHistorical VaR(95%): {var_data['var_95']*100:.4f}%")
    print(f"Expected Shortfall:  {var_data['es_95']*100:.4f}%")
    print(f"Mean daily P/L:      {var_data['mean_daily_pnl']*100:.4f}%")
    print(f"Std daily P/L:       {var_data['std_daily_pnl']*100:.4f}%")
    print(f"Days in sample:      {var_data['n_days']}")

    # Load active picks for stress test
    active_path = _DATA_DIR / "active_picks.json"
    active_picks = []
    if active_path.exists():
        try:
            with open(active_path, "r", encoding="utf-8") as f:
                active_picks = json.load(f)
            if isinstance(active_picks, dict):
                active_picks = active_picks.get("picks", [])
        except Exception:
            pass

    print(f"\nActive picks for stress test: {len(active_picks)}")

    # Get multiplier
    mult = get_var_sizing_multiplier(active_picks=active_picks)
    print(f"\nVaR Sizing Multiplier: {mult:.4f}")

    # Run stress tests
    if active_picks:
        run_stress_tests(active_picks)
    else:
        print("\nNo active picks -- skipping stress test")
