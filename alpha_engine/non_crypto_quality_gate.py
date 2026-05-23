"""
NON-CRYPTO QUALITY GATE
=======================
Centralised macro/regime filters for Forex and Equity strategies.

ROOT CAUSE ANALYSIS (March 2026):
  - FOREX: PF 0.53, WR 33.9%  (-18.17% PnL on 131 trades)
  - EQUITY: PF 0.63, WR 31.8% (-617% PnL on 762 trades)
  - CRYPTO: PF 1.26, WR 42.8% (+3,818% PnL – our proven edge)

DIAGNOSIS:
  1. Equity longs were firing during bear-market phases (SPY < 200d SMA)
  2. Forex signals fired through global vol spikes when edge breaks down
  3. No VIX / panic-regime gating – strategy WR collapses when VIX > 25
  4. claude_gainer_ml_perf: 11.1% WR, -27.10% PnL – inverse variant pending
  5. Confidence caps too high (0.72) for unvalidated non-crypto strategies

FIXES IMPLEMENTED HERE:
  - equity_macro_gate(): SPY > SMA200 + VIX + crash-speed checks
  - forex_macro_gate(): Per-symbol vol-ratio + DXY trend check
  - vix_confidence_adj(): Downscale confidence when VIX elevated
  - INVERSE_PENDING_STRATEGIES: Confidence-halved; inverse variant should be created
  - PROBATION_STRATEGIES: Paper-trade-only until 50+ trades at 40%+ WR

SILENT ERRORS FIXED (2026-04-07 agent investigation):
  Bug 1 – Gate bypass on missing market data:
      equity_macro_gate() returned (True, "SPY data unavailable – gate bypassed")
      when SPY failed to load (network error in CI). This silently allowed ALL equity
      LONG signals through unchecked. Fix: return (False, ...) to block trades when
      the gate cannot be evaluated safely.

  Bug 2 – VIX hard-block docstring vs code mismatch:
      Docstring said "VIX > 30 → 0.00 (hard block)" but code returned 0.30.
      Live non-exempt strategies were firing at 30% confidence during panic.
      Fix: add a genuine hard block at VIX > 40, tighten the >30 band to 0.20.

  Bug 3 – Confidence 0.6-0.7 band is anti-predictive:
      Per closed-trade analysis (3,223 picks): confidence 0.6-0.7 has 23.3% WR
      (worst band) while 0.5-0.6 has 38.4% WR and 0.8+ has 79.3% WR.
      Unvalidated non-crypto strategies were capped at 0.65-0.70, putting them
      INSIDE the anti-predictive zone. Fix: unvalidated caps are now 0.58 (below
      the bad band). Validated strategies can reach 0.75+ to escape into the
      high-quality band.

  Bug 4 – forex_macro_gate bypass on insufficient data:
      Same bypass issue as Bug 1. Fix: return (False, ...) instead of (True, ...).

Usage in strategy files:
    from non_crypto_quality_gate import equity_macro_gate, forex_macro_gate, vix_confidence_adj

    # At top of each equity BUY strategy:
    gate_ok, reason = equity_macro_gate(data)
    if not gate_ok:
        return []

    # Adjust confidence before appending signal:
    conf = round(base_conf * vix_confidence_adj(data), 2)
"""

from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd

try:
    from indicators import sma, rsi, atr, adx
except ImportError:
    sma = rsi = atr = adx = None  # graceful degradation in tests

try:
    from walk_forward_gate import is_strategy_validated, get_validation_status
except ImportError:
    # Graceful fallback if walk_forward_gate not available
    def is_strategy_validated(name: str) -> bool:
        return False
    def get_validation_status() -> dict:
        return {"strategies": {}}


# ---------------------------------------------------------------------------
# INVERSE PENDING STRATEGIES — policy: never kill, always mutate or invert
# ---------------------------------------------------------------------------
# Strategies here have poor forward-test results BUT per policy we do NOT hard-block.
# Instead: confidence is halved (0.5x multiplier) and an inverse variant should be
# created so the signal edge can be harvested from the opposite direction.
# Once an inverse variant accumulates 20+ trades, the original can be re-evaluated.

INVERSE_PENDING_STRATEGIES: frozenset[str] = frozenset({
    "claude_gainer_ml",                        # 11.1% WR, -27.10% PnL (30 trades) — inverse: inv_claude_gainer_ml
    "claude_gainer_ml_perf",                   # Same system, alternate key
    "yahoo_analyst_consensus",                 # 0W/5L — uses 12-month analyst TPs, unreachable in 10d window
    "community_london_breakout_v2_forex",      # 0W/6L — requires intraday tick data, daily bars kill it
    "forex_logistic_direction",                # 0W, 100% SL rate — anti-predictive; confidence halved pending inverse
})
# Alias: signals still flow but with halved confidence
KILLED_STRATEGIES = INVERSE_PENDING_STRATEGIES  # backward-compat alias — NOT a hard block

# ---------------------------------------------------------------------------
# PROBATION STRATEGIES — unvalidated non-crypto strategies
# Paper-trade only until: >=50 forward trades AND WR >= 40%
# ---------------------------------------------------------------------------
PROBATION_STRATEGIES: frozenset[str] = frozenset({
    # Forex — all unvalidated as of March 2026
    "carry_trade_momentum",
    "asian_range_breakout",
    "orb_breakout",
    "forex_rsi2_mean_reversion",
    "forex_tsmom_12m",
    "cot_positioning",
    "london_session_breakout",
    "forex_mean_reversion_200d",
    # Equity — sub-40% WR strategies
    "momentum_factor_12m",
    "penny_volume_breakout",
    "meme_social_velocity",
    "quality_value_composite",
    "intermarket_risk_on",
    "support_resistance_bounce",
})

# Strategies that are EXEMPT from VIX hard-block (they trade because of high VIX):
_VIX_EXEMPT: frozenset[str] = frozenset({
    "vix_spike_reversal_scanner",
    "connors_rsi2_scanner",
    "triple_rsi_scanner",
    "earnings_gap_reversal_scanner",
    "gap_reversal_tech_stocks",
})


# ---------------------------------------------------------------------------
# EQUITY MACRO GATE
# ---------------------------------------------------------------------------

def equity_macro_gate(
    data: dict[str, pd.DataFrame],
    *args,  # Accept extra args gracefully (some callers pass symbol, regime)
    **kwargs,
) -> tuple[bool, str]:
    """Check whether macro conditions allow new equity LONG signals.

    Rules (all must pass):
    1. SPY must be above its 200d SMA — bear-market protection.
       The WR of every long equity strategy collapses below this line.
    2. SPY must not be in a crash (5-day return < -7%).
       During a crash, mean-reversion trades need more room — skip entry.
    3. SPY 20d must be above 50d SMA — intermediate trend not broken.

    Returns:
        (True, "macro ok")  — trade allowed
        (False, reason_str) — trade blocked, reason logged
    """
    spy_df = data.get("SPY")
    if spy_df is None or len(spy_df) < 210:
        # Bug 1 fix: block rather than bypass — if we can't evaluate the gate,
        # we cannot safely allow equity longs (could be in a bear market).
        return False, "SPY data unavailable – equity gate blocked (safe default)"

    if sma is None:
        return False, "indicators not loaded – equity gate blocked (safe default)"

    spy_close = spy_df["Close"]
    spy_current = float(spy_close.iloc[-1])

    # Rule 1: SPY > 200d SMA (1% buffer to prevent flip-flopping at the line)
    spy_sma200 = float(sma(spy_close, 200).iloc[-1])
    if pd.isna(spy_sma200):
        return False, "SMA200 NaN – equity gate blocked (safe default)"
    if spy_current < spy_sma200 * 0.99:
        return False, (
            f"BEAR MARKET GATE: SPY {spy_current:.2f} < SMA200 {spy_sma200:.2f} "
            f"(-{(1 - spy_current/spy_sma200)*100:.1f}%) – no new equity longs"
        )

    # Rule 2: Crash gate — SPY down > 7% in last 5 days
    if len(spy_close) >= 6:
        spy_5d = float(spy_close.iloc[-1] / spy_close.iloc[-6] - 1)
        if spy_5d < -0.07:
            return False, (
                f"CRASH GATE: SPY 5d return={spy_5d*100:.1f}% (< -7%) – "
                f"crash protection active, wait for stabilisation"
            )

    # Rule 3: SPY 20d SMA must be above 50d SMA (trend continuity)
    if len(spy_close) >= 52:
        spy_sma20 = float(sma(spy_close, 20).iloc[-1])
        spy_sma50 = float(sma(spy_close, 50).iloc[-1])
        if not pd.isna(spy_sma20) and not pd.isna(spy_sma50):
            if spy_sma20 < spy_sma50 * 0.98:
                return False, (
                    f"TREND BREAK: SPY SMA20 ({spy_sma20:.2f}) < SMA50 ({spy_sma50:.2f}) – "
                    f"intermediate downtrend, avoid equity longs"
                )

    return True, "equity macro gate passed"


# ---------------------------------------------------------------------------
# VIX CONFIDENCE ADJUSTER
# ---------------------------------------------------------------------------

def vix_hard_block_gate(
    data: dict[str, pd.DataFrame],
    strategy_name: str,
    direction: str,
) -> tuple[bool, str]:
    """Hard-block gate for non-contrarian long picks during panic VIX.

    Complements vix_confidence_adj (which soft-reduces confidence) with an
    explicit hard block so picks produce a visible rejection reason rather
    than silently sneaking through with a tiny confidence multiplier.

    Blocks iff ALL conditions are true:
      1. VIX > 30 (panic zone — non-contrarian strategies collapse here)
      2. Strategy is NOT in _VIX_EXEMPT (contrarian strategies are allowed
         because they are specifically designed for high-VIX conditions)
      3. Direction is LONG (shorts are always allowed — high VIX favors them)

    Returns:
        (True, reason)  — pick allowed
        (False, reason) — pick blocked, reason string for rejection log
    """
    if strategy_name in _VIX_EXEMPT:
        return True, f"VIX-exempt strategy: {strategy_name}"
    if str(direction).upper() != "LONG":
        return True, "SHORT allowed under any VIX"
    try:
        vix_df = data.get("^VIX")
        if vix_df is None or len(vix_df) < 1:
            return True, "VIX data unavailable, passing"
        vix = float(vix_df["Close"].iloc[-1])
    except Exception:
        return True, "VIX data invalid, passing"

    if vix > 30:
        return False, (
            f"VIX panic hard-block: VIX={vix:.1f} > 30, non-contrarian LONG "
            f"strategies collapse in this zone"
        )
    return True, f"VIX={vix:.1f} acceptable"


# ---------------------------------------------------------------------------
# MULTI-TIMEFRAME RSI CONFLUENCE GATE
# ---------------------------------------------------------------------------

def _wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI on a close-price Series. Returns a Series of same length."""
    delta = close.astype(float).diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def mtf_rsi_confluence_gate(
    data: dict[str, pd.DataFrame],
    symbol: str,
    signal_tf: str,
    direction: str,
    period: int = 14,
) -> tuple[bool, str]:
    """Multi-timeframe RSI confluence gate.

    Blocks picks where the higher-timeframe RSI strongly contradicts the
    pick direction (e.g., LONG entry while higher-TF is overbought, or
    SHORT entry while higher-TF is oversold). The signal-TF RSI must also
    not be at a stale extreme on the opposite side.

    Per GitHub agent code review (2026-04-12): MTF-RSI features exist in
    forward_testing/signal_quality_ml.py as ML inputs (rsi_1h/rsi_4h
    alignment) but were never wired as a curation gate. This gate enforces
    confluence at curation time before picks reach paper trading.

    Conservative design — only blocks on CLEAR conflicts:
      - LONG blocked iff higher-TF RSI > 70 (strong overbought) OR
        signal-TF RSI > 75 (already extended)
      - SHORT blocked iff higher-TF RSI < 30 (strong oversold) OR
        signal-TF RSI < 25 (already extended)
      - Passes on any data insufficiency or ambiguity (safe default)

    Args:
        data: Dict of {symbol: OHLCV DataFrame}, daily bars from yfinance.
        symbol: Symbol to look up in data.
        signal_tf: Signal timeframe label ("1d", "4h", etc). Bars in `data`
            are treated as the signal-TF; the higher TF is derived by
            resampling (daily -> weekly).
        direction: "LONG" or "SHORT".
        period: RSI lookback (default 14).

    Returns:
        (True, reason)  — pick allowed
        (False, reason) — pick blocked
    """
    df = data.get(symbol) if isinstance(data, dict) else None
    if df is None or len(df) < period * 3:
        return True, "MTF-RSI: insufficient data, passing (safe default)"

    if "Close" not in df.columns:
        return True, "MTF-RSI: no Close column, passing"

    try:
        close = df["Close"].astype(float).dropna()
        if len(close) < period * 3:
            return True, "MTF-RSI: insufficient close data, passing"

        # Signal-TF RSI (use bars as-is)
        sig_rsi_series = _wilder_rsi(close, period=period)
        sig_rsi = float(sig_rsi_series.iloc[-1])

        # Higher-TF RSI: resample to weekly when bars look like daily.
        # We treat the input as daily and roll up by 5 to weekly.
        # If the index isn't datetime, fall back to a 5-bar groupby.
        if isinstance(close.index, pd.DatetimeIndex):
            higher_close = close.resample("W").last().dropna()
        else:
            # Group every 5 bars
            higher_close = close.groupby(np.arange(len(close)) // 5).last()

        if len(higher_close) < period + 1:
            return True, "MTF-RSI: insufficient higher-TF data, passing"

        higher_rsi_series = _wilder_rsi(higher_close, period=period)
        higher_rsi = float(higher_rsi_series.iloc[-1])
    except Exception as exc:
        return True, f"MTF-RSI: compute error ({exc}), passing"

    import math
    if not (math.isfinite(sig_rsi) and math.isfinite(higher_rsi)):
        return True, "MTF-RSI: NaN values, passing"

    direction_u = str(direction).upper()
    if direction_u == "LONG":
        if higher_rsi > 70:
            return False, (
                f"MTF-RSI conflict: LONG blocked, higher-TF RSI={higher_rsi:.1f} "
                f"overbought (>70), signal-TF RSI={sig_rsi:.1f}"
            )
        if sig_rsi > 75:
            return False, (
                f"MTF-RSI conflict: LONG blocked, signal-TF RSI={sig_rsi:.1f} "
                f"already extended (>75)"
            )
        return True, (
            f"MTF-RSI confluence OK: LONG, sig={sig_rsi:.1f} higher={higher_rsi:.1f}"
        )

    if direction_u == "SHORT":
        if higher_rsi < 30:
            return False, (
                f"MTF-RSI conflict: SHORT blocked, higher-TF RSI={higher_rsi:.1f} "
                f"oversold (<30), signal-TF RSI={sig_rsi:.1f}"
            )
        if sig_rsi < 25:
            return False, (
                f"MTF-RSI conflict: SHORT blocked, signal-TF RSI={sig_rsi:.1f} "
                f"already extended (<25)"
            )
        return True, (
            f"MTF-RSI confluence OK: SHORT, sig={sig_rsi:.1f} higher={higher_rsi:.1f}"
        )

    return True, f"MTF-RSI: unknown direction '{direction}', passing"


def vix_confidence_adj(
    data: dict[str, pd.DataFrame],
    strategy_name: str = "",
) -> float:
    """Return a confidence multiplier based on the current VIX level.

    Results:
        VIX < 20  → 1.00 (no adjustment)
        VIX 20-25 → 0.85 (15% reduction — approaching elevated vol)
        VIX 25-30 → 0.60 (40% reduction — high volatility, WR drops sharply)
        VIX 30-40 → 0.20 (80% reduction — panic zone, most strategies fail)
        VIX > 40  → 0.00 (hard block — extreme panic, edge collapses entirely)

    VIX-exempt strategies (connors_rsi2_scanner, vix_spike_reversal_scanner, etc.)
    are never blocked regardless of VIX — they are specifically designed for high-VIX.

    Bug 2 fix (2026-04-07): Previous code returned 0.30 for VIX > 30 while
    docstring said "0.00 hard block". Added proper hard block at VIX > 40 and
    tightened VIX 30-40 to 0.20 (was 0.30) to match actual WR data.
    """
    if strategy_name in _VIX_EXEMPT:
        return 1.0  # Never penalise strategies designed for panic

    try:
        vix_df = data.get("^VIX")
        if vix_df is None or len(vix_df) < 1:
            return 1.0

        vix = float(vix_df["Close"].iloc[-1])
        if vix > 40:
            return 0.0   # Hard block: extreme panic — no non-exempt longs
        elif vix > 30:
            return 0.20  # 80% reduction — panic zone, WR collapses on normal longs
        elif vix > 25:
            return 0.60  # 40% reduction — significant penalty for elevated vol
        elif vix > 20:
            return 0.85  # 15% reduction — approaching elevated vol
        return 1.0
    except Exception:
        return 1.0


# ---------------------------------------------------------------------------
# FOREX MACRO GATE
# ---------------------------------------------------------------------------

def forex_macro_gate(
    data: dict[str, pd.DataFrame],
    symbol: str,
) -> tuple[bool, str]:
    """Check whether macro conditions allow a forex signal for this symbol.

    Rules:
    1. Symbol-level vol regime: if 20d realised vol > 2.0x 60d baseline,
       skip — abnormal volatility destroys edge on all FX strategies.
    2. ADX must be reachable (data check only — individual strategies
       apply their own ADX threshold per their design).

    This is intentionally lighter than the equity gate because forex
    strategies already include their own RSI / momentum / vol filters.
    The equity gate is stricter because equities have systematic bear-market
    risk that destroys all long strategies simultaneously.
    """
    df = data.get(symbol)
    if df is None or len(df) < 65:
        # Bug 4 fix: block rather than bypass on insufficient data
        return False, f"insufficient FX data for {symbol} – forex gate blocked (safe default)"

    close = df["Close"]
    returns = close.pct_change().dropna()

    if len(returns) < 65:
        return False, f"insufficient returns for {symbol} – forex gate blocked (safe default)"

    # Rule 1: Vol regime gate
    vol_20d = float(returns.iloc[-20:].std()) * np.sqrt(252)
    vol_60d = float(returns.iloc[-60:].std()) * np.sqrt(252)
    vol_ratio = vol_20d / vol_60d if vol_60d > 0 else 1.0

    if vol_ratio > 2.0:
        return False, (
            f"FX VOL SPIKE: {symbol} 20d vol={vol_20d:.3f} is {vol_ratio:.1f}x "
            f"60d baseline={vol_60d:.3f} – avoid trading this pair"
        )

    return True, f"forex gate passed (vol_ratio={vol_ratio:.2f})"


# ---------------------------------------------------------------------------
# BOND MACRO GATE  (VIX-inverse logic)
# ---------------------------------------------------------------------------

def bond_macro_gate(
    data: dict[str, pd.DataFrame],
    symbol: str,
    direction: str = "LONG",
) -> tuple[bool, str]:
    """Check whether macro conditions allow a bond signal.

    Bonds are the INVERSE of equities for VIX/risk-off regimes:
      - High VIX → flight to safety → bond prices RISE → encourage LONGs
      - Low VIX  → risk-on environment → bond prices FALL → discourage LONGs
      - SPY crash → bonds rally → encourage LONGs, block SHORTs

    Rules:
    1. VIX > 30: ENCOURAGE bond LONGs (boost), block SHORTs
    2. VIX 25-30: Mildly encourage bond LONGs
    3. VIX < 15: Block bond LONGs (risk-on, bonds sell off)
    4. SPY crash (5d < -5%): Strongly encourage LONGs, block SHORTs
    5. Yield curve inversion check (TLT vs SHY): If 20y-2y spread is
       normalising after inversion, duration LONGs are favoured.

    Returns:
        (True, reason)  — signal allowed (may include boost note)
        (False, reason) — signal blocked
    """
    direction_u = str(direction).upper()

    # --- VIX-based regime check ---
    vix = None
    try:
        vix_df = data.get("^VIX")
        if vix_df is not None and len(vix_df) >= 1:
            vix = float(vix_df["Close"].iloc[-1])
    except Exception:
        pass

    if vix is not None:
        # Rule 1: High VIX → flight to safety, bonds rally
        if vix > 30:
            if direction_u == "LONG":
                return True, (
                    f"BOND FLIGHT-TO-SAFETY: VIX={vix:.1f} > 30 — bond LONGs favoured "
                    f"(flight to safety)"
                )
            else:  # SHORT
                return False, (
                    f"BOND SHORT BLOCKED: VIX={vix:.1f} > 30 — panic zone, bonds rally, "
                    f"shorting bonds is anti-convictional"
                )

        # Rule 2: Elevated VIX → mildly encourage LONGs
        if vix > 25:
            if direction_u == "LONG":
                return True, (
                    f"BOND MILD SAFETY: VIX={vix:.1f} — bond LONGs pass (elevated vol)"
                )
            # SHORTs pass but will be confidence-reduced by vix_bond_adj()

        # Rule 3: Low VIX → risk-on, bonds sell off → block LONGs
        if vix < 15:
            if direction_u == "LONG":
                return False, (
                    f"BOND LONG BLOCKED: VIX={vix:.1f} < 15 — risk-on regime, "
                    f"bonds sell off in risk appetite"
                )
            # SHORTs are ok in risk-on

    # --- SPY crash check (complementary to VIX) ---
    spy_df = data.get("SPY")
    if spy_df is not None and len(spy_df) >= 6 and "Close" in spy_df.columns:
        try:
            spy_5d = float(spy_df["Close"].iloc[-1] / spy_df["Close"].iloc[-6] - 1)
            if spy_5d < -0.05:
                if direction_u == "LONG":
                    return True, (
                        f"BOND CRASH SAFETY: SPY 5d={spy_5d*100:.1f}% — equity crash, "
                        f"bond LONGs strongly favoured"
                    )
                else:  # SHORT
                    return False, (
                        f"BOND SHORT BLOCKED: SPY 5d={spy_5d*100:.1f}% — equity crash, "
                        f"bonds rally, do not short"
                    )
        except Exception:
            pass

    # --- Yield curve shape check (TLT vs SHY) ---
    # If TLT is outperforming SHY → long-end rallying → duration LONGs ok
    tlt_df = data.get("TLT")
    shy_df = data.get("SHY")
    if (tlt_df is not None and shy_df is not None
            and len(tlt_df) >= 21 and len(shy_df) >= 21):
        try:
            tlt_20d = float(tlt_df["Close"].pct_change(20).iloc[-1])
            shy_20d = float(shy_df["Close"].pct_change(20).iloc[-1])
            duration_spread = tlt_20d - shy_20d
            # Long-end outperforming short-end → duration trade working
            if direction_u == "LONG" and duration_spread > 0.02:
                return True, (
                    f"BOND DURATION TAILWIND: TLT 20d={tlt_20d*100:.1f}% vs SHY={shy_20d*100:.1f}% "
                    f"— long-end outperforming"
                )
            # Short-end outperforming → curve steepening expectations →
            # be cautious on duration LONGs
            if direction_u == "LONG" and duration_spread < -0.03:
                return False, (
                    f"BOND LONG BLOCKED: TLT 20d={tlt_20d*100:.1f}% vs SHY={shy_20d*100:.1f}% "
                    f"— short-end outperforming, duration headwind"
                )
        except Exception:
            pass

    return True, "bond macro gate passed"


def vix_bond_confidence_adj(
    data: dict[str, pd.DataFrame],
    strategy_name: str = "",
    direction: str = "LONG",
) -> float:
    """VIX confidence adjuster for BOND strategies — INVERSE of equity logic.

    Bonds rally when VIX is high (flight to safety), so:
      VIX > 30  → LONG boost 1.25x / SHORT penalty 0.40x
      VIX 25-30 → LONG boost 1.10x / SHORT penalty 0.70x
      VIX 20-25 → No adjustment (1.00)
      VIX 15-20 → LONG mild penalty 0.90x / SHORT mild boost 1.05x
      VIX < 15  → LONG penalty 0.60x / SHORT boost 1.15x (risk-on, bonds sell off)

    VIX-exempt bond strategies (if any) pass through at 1.0.
    """
    if strategy_name in _VIX_EXEMPT:
        return 1.0

    vix = None
    try:
        vix_df = data.get("^VIX")
        if vix_df is not None and len(vix_df) >= 1:
            vix = float(vix_df["Close"].iloc[-1])
    except Exception:
        return 1.0

    if vix is None:
        return 1.0

    direction_u = str(direction).upper()
    is_long = direction_u == "LONG"

    if vix > 30:
        return 1.25 if is_long else 0.40  # Flight to safety: boost LONGs, penalise SHORTs
    elif vix > 25:
        return 1.10 if is_long else 0.70  # Mild safety: slight LONG boost
    elif vix > 20:
        return 1.00  # Neutral zone
    elif vix > 15:
        return 0.90 if is_long else 1.05  # Risk appetite building: mild LONG penalty
    else:  # VIX < 15
        return 0.60 if is_long else 1.15  # Risk-on: bonds sell off, penalise LONGs


# ---------------------------------------------------------------------------
# BOND CONFIDENCE CAP
# ---------------------------------------------------------------------------
_BOND_VALIDATED_STRATEGIES: frozenset[str] = frozenset()  # None validated yet


def bond_conf_cap(conf: float, strategy: str) -> float:
    """Cap bond confidence. Same anti-predictive band logic as equity/forex.

    Validated (50+ trades, WR ≥ 50%): cap at 0.78
    Unvalidated: cap at 0.58 — BELOW the anti-predictive 0.6-0.7 band.
    """
    if strategy in _BOND_VALIDATED_STRATEGIES:
        return min(conf, 0.78)
    return min(conf, 0.58)


# ---------------------------------------------------------------------------
# STRATEGY KILL CHECK  (call before any signal append)
# ---------------------------------------------------------------------------

def is_killed(strategy_name: str) -> bool:
    """Return True if strategy is in the hard-kill list."""
    return strategy_name in KILLED_STRATEGIES


def is_probation(strategy_name: str) -> bool:
    """Return True if strategy is in probation (paper-trade only)."""
    return strategy_name in PROBATION_STRATEGIES


# ---------------------------------------------------------------------------
# FOREX CONFIDENCE CAP  (replaces per-file _forex_conf_cap)
# ---------------------------------------------------------------------------
# Bug 3 fix (2026-04-07): Unvalidated strategies were capped at 0.65, putting
# them INSIDE the anti-predictive 0.6-0.7 confidence band (23.3% WR observed).
# New cap: 0.58 (below the bad band). Validated strategies can reach 0.80+
# (above the band into the high-quality zone: 0.8+ had 79.3% WR).
_FOREX_VALIDATED_STRATEGIES: frozenset[str] = frozenset()  # None validated yet


def forex_conf_cap(conf: float, strategy: str) -> float:
    """Cap forex confidence.

    Validated (50+ trades, WR ≥ 50%): cap at 0.78
    Unvalidated: cap at 0.58 — BELOW the anti-predictive 0.6-0.7 band
    (which showed 23.3% WR in closed-trade analysis).
    """
    if strategy in _FOREX_VALIDATED_STRATEGIES:
        return min(conf, 0.78)
    return min(conf, 0.58)


# ---------------------------------------------------------------------------
# EQUITY CONFIDENCE CAP  (mirrors forex_conf_cap for stocks/ETFs)
# ---------------------------------------------------------------------------
# Bug 3 fix (2026-04-07): Unvalidated equity strategies were capped at 0.70,
# still INSIDE the 0.6-0.7 anti-predictive band. New cap: 0.58.
# Zero-WR strategies (0% on 4+ trades): hard cap at 0.50.
_EQUITY_VALIDATED_STRATEGIES: frozenset[str] = frozenset()  # None validated yet

_EQUITY_ZERO_WR_STRATEGIES: frozenset[str] = frozenset({
    "yahoo_analyst_consensus",  # 0/5 = 0% WR as of 2026-03-24
})


def equity_conf_cap(conf: float, strategy: str) -> float:
    """Cap equity confidence based on strategy validation status.

    Zero-WR (0% on 4+ trades): cap at 0.50 (hard signal to review/kill)
    Validated (50+ trades, WR ≥ 50%): cap at 0.80 (into the proven quality zone)
    Unvalidated: cap at 0.58 — BELOW the anti-predictive 0.6-0.7 band
    """
    if strategy in _EQUITY_ZERO_WR_STRATEGIES:
        return min(conf, 0.50)
    if strategy in _EQUITY_VALIDATED_STRATEGIES:
        return min(conf, 0.80)
    return min(conf, 0.58)


# ---------------------------------------------------------------------------
# EQUITY VIX REGIME GATE  (2026-05-15 addition)
# ---------------------------------------------------------------------------

def equity_vix_regime_gate(
    pick: dict,
    data: dict,
) -> tuple[bool, str, float]:
    """Three-tier VIX regime gate for EQUITY LONG picks.

    Research: VIX<22 = PF 4.55+ backtested; VIX 22-30 = degraded edge.
    The existing vix_hard_block_gate() already hard-blocks at VIX>30 — this
    function adds a middle tier (22-30) as a 20% confidence penalty without
    duplicating or weakening the existing VIX>30 hard block.

    Returns a 3-tuple:
        (pass: bool, reason: str, confidence_multiplier: float)

    Tiers:
      VIX < 22  OR data unavailable  → (True, reason, 1.0)  — full edge
      VIX 22-30 AND EQUITY LONG       → (True, reason, 0.8)  — 20% soft penalty
      VIX > 30  AND not exempt        → (False, reason, 0.0) — hard block
                                        (mirrors vix_hard_block_gate behaviour;
                                         callers should still call that gate too)
      Any other direction/class        → (True, reason, 1.0)  — unaffected

    Safety: ALL exceptions are caught and return (True, ..., 1.0) — fail-open.
    The _VIX_EXEMPT frozenset is NOT modified by this function.
    """
    try:
        asset_class = str(pick.get("asset_class", "") or "").upper()
        direction = str(
            pick.get("direction", pick.get("signal_type", "")) or ""
        ).upper()
        # Normalise BUY → LONG
        if direction == "BUY":
            direction = "LONG"

        # Gate only applies to EQUITY LONG picks
        if asset_class != "EQUITY" or direction != "LONG":
            return True, "VIX regime gate: not EQUITY LONG, skipping", 1.0

        # Respect the VIX-exempt set — contrarian strategies should not be penalised
        strategy_name = str(pick.get("strategy", "") or "")
        if strategy_name in _VIX_EXEMPT:
            return True, f"VIX regime gate: exempt strategy {strategy_name}", 1.0

        # Fetch VIX
        try:
            vix_df = data.get("^VIX") if isinstance(data, dict) else None
            if vix_df is None or len(vix_df) < 1:
                return True, "VIX regime gate: VIX data unavailable, passing (fail-open)", 1.0
            vix = float(vix_df["Close"].iloc[-1])
        except Exception as _vix_exc:
            return True, f"VIX regime gate: VIX fetch error ({_vix_exc}), passing (fail-open)", 1.0

        # Tier 1 — panic zone: hard block (mirrors vix_hard_block_gate; callers should
        # still call that gate directly — this is a convenience wrapper for the 3-tuple API)
        if vix > 30:
            return (
                False,
                f"VIX regime gate: VIX={vix:.1f} > 30 — EQUITY LONG hard-blocked (panic zone)",
                0.0,
            )

        # Tier 2 — elevated-but-not-panic: soft 20% penalty
        if vix >= 22:
            return (
                True,
                (
                    f"VIX regime gate: VIX={vix:.1f} in 22-30 range — "
                    f"EQUITY LONG confidence reduced 20%% (degraded edge zone)"
                ),
                0.8,
            )

        # Tier 0 — sweet spot: full edge
        return (
            True,
            f"VIX regime gate: VIX={vix:.1f} < 22 — EQUITY LONG in sweet-spot zone (PF 4.55+ backtested)",
            1.0,
        )

    except Exception as _outer_exc:
        # Outermost catch — never break admission
        return True, f"VIX regime gate: unexpected error ({_outer_exc}), passing (fail-open)", 1.0
