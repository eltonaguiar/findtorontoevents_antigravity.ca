# Hybrid Confluence + Tournament System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace solo-strategy trading with a confluence + tournament system that requires cross-family agreement, tracks combo strategies, and runs 3 parallel risk portfolios.

**Architecture:** Raw signals from 100+ strategies are grouped by symbol/direction. Only signals with 2+ indicator families agreeing pass the confluence gate. Each strategy/combo earns tiers (Challenger→Gold) through a tournament engine. Three parallel portfolios (conservative/moderate/aggressive) apply different thresholds. ML discovers winning combos after 200+ trades.

**Tech Stack:** Python 3.11, SQLite, LightGBM, existing alpha_engine modules (scanner.py, database.py, ml_ranker.py, config.py)

**Design Doc:** [docs/plans/2026-03-07-hybrid-confluence-tournament-design.md](2026-03-07-hybrid-confluence-tournament-design.md)

---

## Task 1: Add STRATEGY_FAMILIES mapping to config.py

**Files:**
- Modify: `alpha_engine/config.py` (append after line ~306)
- Test: `alpha_engine/tests/test_confluence.py` (create)

**Step 1: Write failing test**

```python
# alpha_engine/tests/test_confluence.py
import pytest

def test_strategy_families_covers_all_strategies():
    """Every active strategy must have a family assignment."""
    from alpha_engine.config import STRATEGY_FAMILIES
    from alpha_engine.crypto_strategies import CRYPTO_STRATEGIES
    from alpha_engine.forex_strategies import FOREX_STRATEGIES
    from alpha_engine.equity_strategies import EQUITY_STRATEGIES

    all_strategies = set(CRYPTO_STRATEGIES) | set(FOREX_STRATEGIES) | set(EQUITY_STRATEGIES)
    mapped = set(STRATEGY_FAMILIES.keys())
    missing = all_strategies - mapped
    assert not missing, f"Strategies missing family assignment: {missing}"


def test_strategy_families_valid_values():
    """All family values must be from the allowed set."""
    from alpha_engine.config import STRATEGY_FAMILIES, INDICATOR_FAMILIES
    for name, family in STRATEGY_FAMILIES.items():
        assert family in INDICATOR_FAMILIES, f"{name} has invalid family '{family}'"
```

**Step 2: Run test — expect FAIL** (STRATEGY_FAMILIES not defined)

```bash
cd alpha_engine && python -m pytest tests/test_confluence.py::test_strategy_families_covers_all_strategies -v
```

**Step 3: Implement STRATEGY_FAMILIES in config.py**

Add to the end of `alpha_engine/config.py`:

```python
# ═══════════════════════════════════════════════════════════════
#  INDICATOR FAMILY CLASSIFICATION (for Confluence Engine)
# ═══════════════════════════════════════════════════════════════
INDICATOR_FAMILIES = {
    "momentum", "trend", "volume", "sentiment",
    "on_chain", "structure", "volatility",
}

STRATEGY_FAMILIES: dict[str, str] = {
    # ── Momentum ──
    "connors_rsi2_crypto": "momentum",
    "rsi_hidden_divergence": "momentum",
    "rsi_macd_confluence": "momentum",
    "stochrsi_oversold_bounce": "momentum",
    "entropy_adaptive_rsi": "momentum",
    "cross_sectional_momentum": "momentum",
    "spike_momentum_ignition": "momentum",
    "spike_rsi_extreme": "momentum",
    "spike_macd_divergence": "momentum",
    "community_rsi_extreme_reversal_crypto": "momentum",
    "tsmom_28d": "momentum",
    "momentum_mean_rev_blend": "momentum",
    "dynamic_momentum_scaling": "momentum",
    "sector_momentum_7d": "momentum",
    "moving_average_slope_momentum": "momentum",

    # ── Trend ──
    "btc_ichimoku_cloud": "trend",
    "btc_200d_sma_bounce": "trend",
    "multi_timeframe_ema_stack": "trend",
    "pentoshi_htf_structure": "trend",
    "community_ema_9_21_rsi_crypto": "trend",
    "community_momentum_breakout_volume_crypto": "trend",
    "halving_cycle_position": "trend",
    "supertrend_multi_timeframe": "trend",
    "kama_volatility_adaptive": "trend",

    # ── Volume ──
    "obv_divergence_breakout": "volume",
    "volume_climax_reversal": "volume",
    "vwap_sd_mean_reversion": "volume",
    "cmf_zero_line_cross": "volume",
    "mfi_smart_money_detection": "volume",
    "crypto_breakout_volume": "volume",
    "volume_profile_value_area": "volume",
    "cumulative_delta_divergence": "volume",
    "community_vwap_bounce_crypto": "volume",
    "spike_volume_explosion": "volume",
    "cascade_volume_detector": "volume",

    # ── Sentiment ──
    "crypto_fear_greed_contrarian": "sentiment",
    "funding_rate_extreme": "sentiment",
    "funding_rate_carry": "sentiment",
    "funding_rate_arbitrage": "sentiment",
    "oi_funding_squeeze": "sentiment",
    "ape_wisdom_social_momentum": "sentiment",
    "coingecko_trending_volume": "sentiment",
    "fear_greed_extreme_dca": "sentiment",
    "oi_price_divergence": "sentiment",

    # ── On-Chain ──
    "mvrv_sma_proxy": "on_chain",
    "hash_ribbon_buy": "on_chain",
    "stablecoin_buying_power": "on_chain",
    "nvt_overvaluation": "on_chain",
    "sopr_dip_buy_proxy": "on_chain",
    "onchain_composite_score": "on_chain",
    "hayes_liquidity_index": "on_chain",
    "whale_accumulation_detector": "on_chain",
    "exchange_netflow_reversal": "on_chain",

    # ── Structure ──
    "wyckoff_accumulation": "structure",
    "smart_money_fvg": "structure",
    "swing_failure_pattern": "structure",
    "break_of_structure": "structure",
    "liquidity_sweep_reversal": "structure",
    "community_ict_fvg_selective": "structure",
    "fractal_support_resistance": "structure",
    "double_top_bottom_detector": "structure",
    "head_shoulders_detector": "structure",
    "ascending_triangle_breakout": "structure",
    "breakout_retest_confirmation": "structure",
    "support_resistance_bounce": "structure",
    "multi_touch_level_strength": "structure",
    "failed_breakout_reversal": "structure",

    # ── Volatility ──
    "atr_volatility_breakout": "volatility",
    "vol_risk_premium": "volatility",
    "dvol_extreme_buy": "volatility",
    "spike_squeeze_breakout": "volatility",
    "spike_volatility_collapse": "volatility",
    "community_bb_squeeze_breakout_crypto": "volatility",
    "bollinger_mean_reversion": "volatility",
    "keltner_squeeze_detector": "volatility",
    "multi_sigma_reversal": "volatility",
    "ou_mean_reversion": "volatility",
    "variance_ratio_momentum": "volatility",
    "autocorrelation_exploiter": "volatility",
    "mean_reversion_halflife": "volatility",
    "vol_scaled_keltner": "volatility",

    # ── Event / Misc (assign to closest family) ──
    "altcoin_season_rotation": "trend",
    "btc_dominance_reversal": "trend",
    "crypto_weekend_drift": "momentum",
    "token_unlock_short": "sentiment",
    "liquidation_cascade_buy": "volume",
    "liquidation_cascade_bottom": "volume",
    "btc_dip_recovery": "structure",
    "narrative_rotation": "trend",
    "new_pair_momentum": "momentum",
    "cross_exchange_spread": "volatility",
    "momentum_crash_hedge": "volatility",
    "goplus_filtered_sniper": "volume",
    "altcoin_dip_amplifier": "trend",
    "unlock_scoring_enhanced": "sentiment",
    "hurst_mean_reversion": "volatility",
    "hurst_regime_adaptive": "volatility",
    "adaptive_vr_confluence": "volatility",

    # ── Forex strategies ──
    "forex_usd_momentum": "momentum",
    "london_breakout_gbpusd": "structure",
    "carry_trade_momentum": "sentiment",
    "intermarket_risk_on": "sentiment",
    "forex_session_breakout": "structure",
    "forex_range_breakout": "volatility",
    "forex_trend_follow": "trend",
    "forex_mean_reversion": "volatility",
    "forex_momentum_pullback": "momentum",
    "forex_news_reaction": "sentiment",
    "forex_asian_range_breakout": "structure",

    # ── Equity strategies ──
    "connors_rsi2_spy": "momentum",
    "connors_rsi2_qqq": "momentum",
    "vix_spike_reversal": "volatility",
    "opening_range_breakout": "structure",
    "triple_rsi_confirmation": "momentum",
    "spy_mean_reversion": "volatility",
    "qqq_momentum": "momentum",
    "sector_rotation_etf": "trend",
    "earnings_momentum": "sentiment",
    "dividend_yield_value": "sentiment",
    "small_cap_momentum": "momentum",
    "large_cap_quality": "trend",
    "spy_200d_bounce": "trend",
    "spy_rsi_extreme": "momentum",
}
```

Note: This mapping covers the core strategies. Any new strategy added to the system should also be added here. The test in Step 1 will catch any missing assignments.

**Step 4: Run tests — expect PASS**

```bash
cd alpha_engine && python -m pytest tests/test_confluence.py -v
```

If strategies are missing from the mapping (test fails), add them and re-run until green.

**Step 5: Commit**

```bash
git add alpha_engine/config.py alpha_engine/tests/test_confluence.py
git commit -m "feat(confluence): add STRATEGY_FAMILIES mapping for all strategies"
```

---

## Task 2: Create confluence_engine.py

**Files:**
- Create: `alpha_engine/confluence_engine.py`
- Modify: `alpha_engine/tests/test_confluence.py` (add tests)

**Step 1: Write failing tests**

Add to `alpha_engine/tests/test_confluence.py`:

```python
from datetime import datetime, timedelta


def _make_signal(strategy, symbol, direction, family, confidence=0.7, ml_score=0.6, timestamp=None):
    """Helper to create a test signal dict."""
    return {
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": direction,
        "family": family,
        "confidence": confidence,
        "ml_score": ml_score,
        "timestamp": (timestamp or datetime.utcnow()).isoformat(),
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "risk_reward": 2.0,
    }


def test_confluence_requires_two_families():
    from alpha_engine.confluence_engine import ConfluenceEngine
    engine = ConfluenceEngine(min_families=2, time_window_hours=4)

    signals = [
        _make_signal("rsi_a", "BTC-USD", "BUY", "momentum"),
        _make_signal("rsi_b", "BTC-USD", "BUY", "momentum"),  # same family
    ]
    result = engine.process_signals(signals)
    assert len(result) == 0, "Same-family signals should not form confluence"


def test_confluence_passes_with_two_families():
    from alpha_engine.confluence_engine import ConfluenceEngine
    engine = ConfluenceEngine(min_families=2, time_window_hours=4)

    signals = [
        _make_signal("rsi_a", "BTC-USD", "BUY", "momentum"),
        _make_signal("vol_a", "BTC-USD", "BUY", "volume"),
    ]
    result = engine.process_signals(signals)
    assert len(result) == 1
    assert result[0]["family_count"] == 2
    assert result[0]["symbol"] == "BTC-USD"


def test_confluence_separates_directions():
    from alpha_engine.confluence_engine import ConfluenceEngine
    engine = ConfluenceEngine(min_families=2, time_window_hours=4)

    signals = [
        _make_signal("rsi_a", "BTC-USD", "BUY", "momentum"),
        _make_signal("vol_a", "BTC-USD", "SELL", "volume"),  # different direction
    ]
    result = engine.process_signals(signals)
    assert len(result) == 0, "BUY and SELL on same symbol should not form confluence"


def test_confluence_time_window_filters_old():
    from alpha_engine.confluence_engine import ConfluenceEngine
    engine = ConfluenceEngine(min_families=2, time_window_hours=4)

    now = datetime.utcnow()
    old = now - timedelta(hours=5)
    signals = [
        _make_signal("rsi_a", "BTC-USD", "BUY", "momentum", timestamp=now),
        _make_signal("vol_a", "BTC-USD", "BUY", "volume", timestamp=old),
    ]
    result = engine.process_signals(signals)
    assert len(result) == 0, "Signal outside time window should be excluded"


def test_confluence_three_families_scored_higher():
    from alpha_engine.confluence_engine import ConfluenceEngine
    engine = ConfluenceEngine(min_families=2, time_window_hours=4)

    signals = [
        _make_signal("rsi_a", "BTC-USD", "BUY", "momentum"),
        _make_signal("vol_a", "BTC-USD", "BUY", "volume"),
        _make_signal("whale", "BTC-USD", "BUY", "on_chain"),
    ]
    result = engine.process_signals(signals)
    assert len(result) == 1
    assert result[0]["family_count"] == 3
    assert result[0]["confluence_score"] > 0


def test_confluence_multiple_symbols():
    from alpha_engine.confluence_engine import ConfluenceEngine
    engine = ConfluenceEngine(min_families=2, time_window_hours=4)

    signals = [
        _make_signal("rsi_a", "BTC-USD", "BUY", "momentum"),
        _make_signal("vol_a", "BTC-USD", "BUY", "volume"),
        _make_signal("rsi_b", "ETH-USD", "BUY", "momentum"),
        _make_signal("trend_b", "ETH-USD", "BUY", "trend"),
    ]
    result = engine.process_signals(signals)
    assert len(result) == 2
    symbols = {r["symbol"] for r in result}
    assert symbols == {"BTC-USD", "ETH-USD"}
```

**Step 2: Run tests — expect FAIL**

```bash
cd alpha_engine && python -m pytest tests/test_confluence.py -v -k "confluence"
```

**Step 3: Implement confluence_engine.py**

```python
"""Confluence Engine — requires cross-family agreement before trading.

A signal only becomes a candidate pick when 2+ strategies from different
indicator families fire on the same symbol in the same direction within
a configurable time window.
"""

from collections import defaultdict
from datetime import datetime, timedelta


class ConfluenceEngine:
    """Groups raw signals by (symbol, direction) and checks family diversity."""

    def __init__(self, min_families: int = 2, time_window_hours: float = 4.0):
        self.min_families = min_families
        self.time_window = timedelta(hours=time_window_hours)

    def process_signals(self, raw_signals: list[dict]) -> list[dict]:
        """Filter signals to only those with cross-family confluence.

        Args:
            raw_signals: List of signal dicts, each with keys:
                strategy, symbol, signal_type (BUY/SELL), family,
                confidence, ml_score, timestamp, entry_price, etc.

        Returns:
            List of confluence signal dicts with:
                symbol, direction, contributing_signals, family_count,
                families, confluence_score, best_entry, best_tp, best_sl
        """
        now = datetime.utcnow()
        groups = defaultdict(list)

        for sig in raw_signals:
            ts = self._parse_timestamp(sig.get("timestamp"))
            if ts and (now - ts) > self.time_window:
                continue  # too old
            key = (sig["symbol"], sig["signal_type"])
            groups[key].append(sig)

        results = []
        for (symbol, direction), signals in groups.items():
            families = set()
            for s in signals:
                if s.get("family"):
                    families.add(s["family"])

            if len(families) < self.min_families:
                continue

            score = self._compute_score(signals, families)
            best = self._pick_best_levels(signals)

            results.append({
                "symbol": symbol,
                "direction": direction,
                "contributing_signals": signals,
                "contributing_strategies": [s["strategy"] for s in signals],
                "family_count": len(families),
                "families": sorted(families),
                "confluence_score": score,
                "signal_count": len(signals),
                "entry_price": best["entry_price"],
                "take_profit": best["take_profit"],
                "stop_loss": best["stop_loss"],
                "avg_confidence": best["avg_confidence"],
                "avg_ml_score": best["avg_ml_score"],
            })

        # Sort by confluence score descending
        results.sort(key=lambda x: x["confluence_score"], reverse=True)
        return results

    def _compute_score(self, signals: list[dict], families: set) -> float:
        """Score confluence signal. Higher = more confident."""
        n_families = len(families)
        n_signals = len(signals)
        avg_conf = sum(s.get("confidence", 0.5) for s in signals) / max(n_signals, 1)
        avg_ml = sum(s.get("ml_score", 0.5) for s in signals) / max(n_signals, 1)

        score = (
            0.40 * min(n_families / 4.0, 1.0) +   # family diversity (max at 4)
            0.20 * avg_conf +                        # avg strategy confidence
            0.20 * avg_ml +                          # avg ML score
            0.10 * min(n_signals / 5.0, 1.0) +      # signal count (max at 5)
            0.10 * min(sum(s.get("risk_reward", 1.0) for s in signals) / n_signals / 3.0, 1.0)
        )
        return round(score, 4)

    def _pick_best_levels(self, signals: list[dict]) -> dict:
        """Pick best entry/TP/SL from contributing signals."""
        entries = [s["entry_price"] for s in signals if s.get("entry_price")]
        tps = [s["take_profit"] for s in signals if s.get("take_profit")]
        sls = [s["stop_loss"] for s in signals if s.get("stop_loss")]
        confs = [s.get("confidence", 0.5) for s in signals]
        mls = [s.get("ml_score", 0.5) for s in signals]

        return {
            "entry_price": sum(entries) / len(entries) if entries else 0,
            "take_profit": max(tps) if tps else 0,       # most optimistic TP
            "stop_loss": min(sls) if sls else 0,          # widest SL (safest)
            "avg_confidence": sum(confs) / len(confs) if confs else 0.5,
            "avg_ml_score": sum(mls) / len(mls) if mls else 0.5,
        }

    @staticmethod
    def _parse_timestamp(ts) -> datetime | None:
        if not ts:
            return None
        if isinstance(ts, datetime):
            return ts
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            return None
```

**Step 4: Run tests — expect PASS**

```bash
cd alpha_engine && python -m pytest tests/test_confluence.py -v
```

**Step 5: Commit**

```bash
git add alpha_engine/confluence_engine.py alpha_engine/tests/test_confluence.py
git commit -m "feat(confluence): add ConfluenceEngine with cross-family filtering"
```

---

## Task 3: Create tournament_engine.py

**Files:**
- Create: `alpha_engine/tournament_engine.py`
- Create: `alpha_engine/tests/test_tournament.py`

**Step 1: Write failing tests**

```python
# alpha_engine/tests/test_tournament.py
import pytest
import sqlite3
import tempfile
import os


def _make_db():
    """Create temp SQLite DB with tournament_state table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def test_new_strategy_starts_as_challenger():
    from alpha_engine.tournament_engine import TournamentEngine
    db_path = _make_db()
    try:
        engine = TournamentEngine(db_path, portfolio="moderate")
        tier = engine.get_tier("some_new_strategy")
        assert tier == "challenger"
    finally:
        os.unlink(db_path)


def test_promote_to_bronze():
    from alpha_engine.tournament_engine import TournamentEngine
    db_path = _make_db()
    try:
        engine = TournamentEngine(db_path, portfolio="moderate")
        # Record 10 trades with 60% WR
        for i in range(10):
            engine.record_trade("strat_a", won=(i < 6), pnl_pct=(3.0 if i < 6 else -2.0))
        engine.evaluate("strat_a")
        assert engine.get_tier("strat_a") == "bronze"
    finally:
        os.unlink(db_path)


def test_demote_on_consecutive_losses():
    from alpha_engine.tournament_engine import TournamentEngine
    db_path = _make_db()
    try:
        engine = TournamentEngine(db_path, portfolio="moderate")
        # Promote to bronze first
        for i in range(10):
            engine.record_trade("strat_b", won=(i < 6), pnl_pct=(3.0 if i < 6 else -2.0))
        engine.evaluate("strat_b")
        assert engine.get_tier("strat_b") == "bronze"
        # Now 5 consecutive losses
        for _ in range(5):
            engine.record_trade("strat_b", won=False, pnl_pct=-2.0)
        engine.evaluate("strat_b")
        assert engine.get_tier("strat_b") == "challenger"
    finally:
        os.unlink(db_path)


def test_combo_tracking():
    from alpha_engine.tournament_engine import TournamentEngine
    db_path = _make_db()
    try:
        engine = TournamentEngine(db_path, portfolio="moderate")
        combo_id = engine.get_combo_id(["vol_a", "rsi_b"])
        assert combo_id == "rsi_b+vol_a"  # sorted alphabetically
        engine.record_trade(combo_id, won=True, pnl_pct=5.0, entity_type="combo")
        state = engine.get_state(combo_id)
        assert state["wins"] == 1
        assert state["entity_type"] == "combo"
    finally:
        os.unlink(db_path)


def test_risk_per_tier():
    from alpha_engine.tournament_engine import TournamentEngine
    db_path = _make_db()
    try:
        engine = TournamentEngine(db_path, portfolio="moderate")
        assert engine.get_risk_pct("challenger") == 0.0
        assert engine.get_risk_pct("bronze") == 0.005
        assert engine.get_risk_pct("silver") == 0.01
        assert engine.get_risk_pct("gold") == 0.02
    finally:
        os.unlink(db_path)
```

**Step 2: Run tests — expect FAIL**

```bash
cd alpha_engine && python -m pytest tests/test_tournament.py -v
```

**Step 3: Implement tournament_engine.py**

```python
"""Tournament Engine — Darwinian tier progression for strategies and combos.

Strategies start as Challenger (paper-only) and earn promotion through
consistent forward performance. Each portfolio (conservative/moderate/aggressive)
has different promotion thresholds.
"""

import sqlite3
from datetime import datetime


# Promotion thresholds per portfolio
PORTFOLIO_THRESHOLDS = {
    "conservative": {"wr_bronze": 0.60, "wr_silver": 0.60, "wr_gold": 0.60, "pf_min": 1.3},
    "moderate":     {"wr_bronze": 0.50, "wr_silver": 0.50, "wr_gold": 0.50, "pf_min": 1.2},
    "aggressive":   {"wr_bronze": 0.45, "wr_silver": 0.45, "wr_gold": 0.45, "pf_min": 1.0},
}

TIER_RISK = {
    "challenger": 0.0,    # paper only
    "bronze":     0.005,   # 0.5% risk
    "silver":     0.01,    # 1.0% risk
    "gold":       0.02,    # 2.0% risk
}

TIER_ORDER = ["challenger", "bronze", "silver", "gold"]

# Minimum trades for promotion
MIN_TRADES_BRONZE = 10
MIN_TRADES_SILVER = 25
MIN_TRADES_GOLD = 50

CONSECUTIVE_LOSS_DEMOTE = 5


class TournamentEngine:
    """Manages tier progression for strategies and combo strategies."""

    def __init__(self, db_path: str, portfolio: str = "moderate"):
        self.db_path = db_path
        self.portfolio = portfolio
        self.thresholds = PORTFOLIO_THRESHOLDS[portfolio]
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tournament_state (
                    entity_id TEXT NOT NULL,
                    portfolio TEXT NOT NULL,
                    entity_type TEXT DEFAULT 'strategy',
                    tier TEXT DEFAULT 'challenger',
                    total_trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    avg_pnl REAL DEFAULT 0,
                    consecutive_losses INTEGER DEFAULT 0,
                    last_trade_date TEXT,
                    promoted_at TEXT,
                    demoted_at TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (entity_id, portfolio)
                )
            """)

    def get_tier(self, entity_id: str) -> str:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT tier FROM tournament_state WHERE entity_id=? AND portfolio=?",
                (entity_id, self.portfolio)
            ).fetchone()
        return row[0] if row else "challenger"

    def get_risk_pct(self, tier: str) -> float:
        return TIER_RISK.get(tier, 0.0)

    def get_state(self, entity_id: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM tournament_state WHERE entity_id=? AND portfolio=?",
                (entity_id, self.portfolio)
            ).fetchone()
        if not row:
            return {"entity_id": entity_id, "tier": "challenger", "wins": 0,
                    "losses": 0, "total_trades": 0, "entity_type": "strategy"}
        return dict(row)

    def record_trade(self, entity_id: str, won: bool, pnl_pct: float,
                     entity_type: str = "strategy"):
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT total_trades, wins, losses, total_pnl, consecutive_losses "
                "FROM tournament_state WHERE entity_id=? AND portfolio=?",
                (entity_id, self.portfolio)
            ).fetchone()

            if existing:
                total = existing[0] + 1
                wins = existing[1] + (1 if won else 0)
                losses = existing[2] + (0 if won else 1)
                total_pnl = existing[3] + pnl_pct
                consec = 0 if won else existing[4] + 1
                wr = wins / total if total > 0 else 0
                avg_pnl = total_pnl / total

                conn.execute("""
                    UPDATE tournament_state
                    SET total_trades=?, wins=?, losses=?, win_rate=?,
                        total_pnl=?, avg_pnl=?, consecutive_losses=?,
                        last_trade_date=?, updated_at=?
                    WHERE entity_id=? AND portfolio=?
                """, (total, wins, losses, wr, total_pnl, avg_pnl, consec,
                      now, now, entity_id, self.portfolio))
            else:
                wins = 1 if won else 0
                losses = 0 if won else 1
                wr = 1.0 if won else 0.0
                consec = 0 if won else 1
                conn.execute("""
                    INSERT INTO tournament_state
                    (entity_id, portfolio, entity_type, tier, total_trades, wins, losses,
                     win_rate, total_pnl, avg_pnl, consecutive_losses,
                     last_trade_date, updated_at)
                    VALUES (?,?,?,?,1,?,?,?,?,?,?,?,?)
                """, (entity_id, self.portfolio, entity_type, "challenger",
                      wins, losses, wr, pnl_pct, pnl_pct, consec, now, now))

    def evaluate(self, entity_id: str) -> str:
        """Evaluate promotion/demotion for an entity. Returns new tier."""
        state = self.get_state(entity_id)
        current_tier = state.get("tier", "challenger")
        total = state.get("total_trades", 0)
        wr = state.get("win_rate", 0)
        consec_losses = state.get("consecutive_losses", 0)
        avg_pnl = state.get("avg_pnl", 0)
        current_idx = TIER_ORDER.index(current_tier)

        new_tier = current_tier

        # ── Demotion checks ──
        if consec_losses >= CONSECUTIVE_LOSS_DEMOTE:
            new_tier = TIER_ORDER[max(0, current_idx - 1)]
        elif total >= 20 and wr < (self.thresholds["wr_bronze"] - 0.10):
            new_tier = TIER_ORDER[max(0, current_idx - 1)]

        # ── Promotion checks (only if no demotion) ──
        if new_tier == current_tier:
            if current_tier == "challenger" and total >= MIN_TRADES_BRONZE:
                if wr >= self.thresholds["wr_bronze"] and avg_pnl > 0:
                    new_tier = "bronze"
            elif current_tier == "bronze" and total >= MIN_TRADES_SILVER:
                if wr >= self.thresholds["wr_silver"] and avg_pnl > 0:
                    new_tier = "silver"
            elif current_tier == "silver" and total >= MIN_TRADES_GOLD:
                if wr >= self.thresholds["wr_gold"] and avg_pnl > 0:
                    new_tier = "gold"

        # ── Persist ──
        if new_tier != current_tier:
            now = datetime.utcnow().isoformat()
            promoted = new_tier if TIER_ORDER.index(new_tier) > current_idx else None
            demoted = new_tier if TIER_ORDER.index(new_tier) < current_idx else None
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tournament_state SET tier=?, promoted_at=COALESCE(?,promoted_at),
                    demoted_at=COALESCE(?,demoted_at), updated_at=?
                    WHERE entity_id=? AND portfolio=?
                """, (new_tier, now if promoted else None, now if demoted else None,
                      now, entity_id, self.portfolio))

        return new_tier

    @staticmethod
    def get_combo_id(strategies: list[str]) -> str:
        """Generate a deterministic combo ID from sorted strategy names."""
        return "+".join(sorted(strategies))

    def get_all_states(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tournament_state WHERE portfolio=? ORDER BY tier DESC, win_rate DESC",
                (self.portfolio,)
            ).fetchall()
        return [dict(r) for r in rows]
```

**Step 4: Run tests — expect PASS**

```bash
cd alpha_engine && python -m pytest tests/test_tournament.py -v
```

**Step 5: Commit**

```bash
git add alpha_engine/tournament_engine.py alpha_engine/tests/test_tournament.py
git commit -m "feat(tournament): add TournamentEngine with tier progression and combo tracking"
```

---

## Task 4: Create portfolio_manager.py

**Files:**
- Create: `alpha_engine/portfolio_manager.py`
- Create: `alpha_engine/tests/test_portfolio.py`

**Step 1: Write failing tests**

```python
# alpha_engine/tests/test_portfolio.py
import pytest
import tempfile
import os


def _make_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def test_three_portfolios_independent():
    from alpha_engine.portfolio_manager import PortfolioManager
    db_path = _make_db()
    try:
        pm = PortfolioManager(db_path)
        assert len(pm.portfolios) == 3
        assert set(pm.portfolios.keys()) == {"conservative", "moderate", "aggressive"}
    finally:
        os.unlink(db_path)


def test_conservative_requires_three_families():
    from alpha_engine.portfolio_manager import PortfolioManager, PORTFOLIO_CONFIGS
    assert PORTFOLIO_CONFIGS["conservative"]["min_families"] == 3
    assert PORTFOLIO_CONFIGS["moderate"]["min_families"] == 2
    assert PORTFOLIO_CONFIGS["aggressive"]["min_families"] == 2


def test_circuit_breaker_freezes():
    from alpha_engine.portfolio_manager import PortfolioManager
    db_path = _make_db()
    try:
        pm = PortfolioManager(db_path)
        port = pm.portfolios["conservative"]
        # Simulate 5% drawdown (conservative circuit breaker)
        port.current_pnl = -500  # -5% of $10k
        assert port.is_frozen()
    finally:
        os.unlink(db_path)


def test_position_limits():
    from alpha_engine.portfolio_manager import PortfolioManager, PORTFOLIO_CONFIGS
    assert PORTFOLIO_CONFIGS["conservative"]["max_positions"] == 10
    assert PORTFOLIO_CONFIGS["moderate"]["max_positions"] == 20
    assert PORTFOLIO_CONFIGS["aggressive"]["max_positions"] == 30
```

**Step 2: Run tests — expect FAIL**

```bash
cd alpha_engine && python -m pytest tests/test_portfolio.py -v
```

**Step 3: Implement portfolio_manager.py**

```python
"""Portfolio Manager — runs 3 parallel portfolios with independent risk profiles.

Each portfolio (conservative/moderate/aggressive) tracks its own P&L, positions,
circuit breaker state, and tournament engine.
"""

from datetime import datetime
from alpha_engine.tournament_engine import TournamentEngine


PORTFOLIO_CONFIGS = {
    "conservative": {
        "min_families": 3,
        "max_positions": 10,
        "max_per_symbol": 1,
        "max_same_direction": 4,
        "circuit_breaker_pct": 0.05,  # 5%
        "starting_capital": 10_000.0,
        "kelly_cap": 0.03,
    },
    "moderate": {
        "min_families": 2,
        "max_positions": 20,
        "max_per_symbol": 2,
        "max_same_direction": 6,
        "circuit_breaker_pct": 0.10,  # 10%
        "starting_capital": 10_000.0,
        "kelly_cap": 0.05,
    },
    "aggressive": {
        "min_families": 2,
        "max_positions": 30,
        "max_per_symbol": 3,
        "max_same_direction": 8,
        "circuit_breaker_pct": 0.15,  # 15%
        "starting_capital": 10_000.0,
        "kelly_cap": 0.08,
    },
}


class Portfolio:
    """Single portfolio with its own state."""

    def __init__(self, name: str, config: dict, tournament: TournamentEngine):
        self.name = name
        self.config = config
        self.tournament = tournament
        self.starting_capital = config["starting_capital"]
        self.current_pnl = 0.0
        self.open_positions = []
        self.frozen_at = None

    @property
    def current_capital(self) -> float:
        return self.starting_capital + self.current_pnl

    @property
    def drawdown_pct(self) -> float:
        if self.current_pnl >= 0:
            return 0.0
        return abs(self.current_pnl) / self.starting_capital

    def is_frozen(self) -> bool:
        return self.drawdown_pct >= self.config["circuit_breaker_pct"]

    def can_open_position(self, symbol: str, direction: str) -> bool:
        if self.is_frozen():
            return False
        if len(self.open_positions) >= self.config["max_positions"]:
            return False
        symbol_count = sum(1 for p in self.open_positions if p["symbol"] == symbol)
        if symbol_count >= self.config["max_per_symbol"]:
            return False
        dir_count = sum(1 for p in self.open_positions if p["direction"] == direction)
        if dir_count >= self.config["max_same_direction"]:
            return False
        return True

    def accepts_confluence(self, family_count: int) -> bool:
        return family_count >= self.config["min_families"]

    def record_pnl(self, pnl_dollar: float):
        self.current_pnl += pnl_dollar

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "capital": round(self.current_capital, 2),
            "pnl": round(self.current_pnl, 2),
            "pnl_pct": round(self.current_pnl / self.starting_capital * 100, 2),
            "drawdown_pct": round(self.drawdown_pct * 100, 2),
            "open_positions": len(self.open_positions),
            "frozen": self.is_frozen(),
            "config": self.config,
        }


class PortfolioManager:
    """Manages 3 parallel portfolios."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.portfolios = {}
        for name, config in PORTFOLIO_CONFIGS.items():
            tournament = TournamentEngine(db_path, portfolio=name)
            self.portfolios[name] = Portfolio(name, config, tournament)

    def route_signal(self, confluence_signal: dict) -> list[tuple[str, Portfolio]]:
        """Determine which portfolios accept this confluence signal.

        Returns list of (portfolio_name, Portfolio) that accept it.
        """
        family_count = confluence_signal.get("family_count", 0)
        symbol = confluence_signal.get("symbol", "")
        direction = confluence_signal.get("direction", "BUY")

        accepted = []
        for name, port in self.portfolios.items():
            if not port.accepts_confluence(family_count):
                continue
            if not port.can_open_position(symbol, direction):
                continue
            accepted.append((name, port))
        return accepted

    def get_comparison(self) -> dict:
        """Generate comparison report across all 3 portfolios."""
        return {name: port.to_dict() for name, port in self.portfolios.items()}
```

**Step 4: Run tests — expect PASS**

```bash
cd alpha_engine && python -m pytest tests/test_portfolio.py -v
```

**Step 5: Commit**

```bash
git add alpha_engine/portfolio_manager.py alpha_engine/tests/test_portfolio.py
git commit -m "feat(portfolio): add PortfolioManager with 3 parallel risk profiles"
```

---

## Task 5: Wire confluence into scanner.py

**Files:**
- Modify: `alpha_engine/scanner.py` (lines ~826 and ~1347)

**Step 1: Write integration test**

Add to `alpha_engine/tests/test_confluence.py`:

```python
def test_annotate_signals_with_family():
    """Signals should get family annotation from STRATEGY_FAMILIES."""
    from alpha_engine.config import STRATEGY_FAMILIES

    signal = {"strategy": "connors_rsi2_crypto", "symbol": "BTC-USD", "signal_type": "BUY"}
    family = STRATEGY_FAMILIES.get(signal["strategy"], "unknown")
    signal["family"] = family
    assert signal["family"] == "momentum"
```

**Step 2: Run test — expect PASS** (this is a logic validation test)

**Step 3: Modify scanner.py**

In `run_strategies()` (after line ~826, where signals are collected), add family annotation:

```python
# After signals are collected from all strategies:
from alpha_engine.config import STRATEGY_FAMILIES

for sig in all_signals:
    sig["family"] = STRATEGY_FAMILIES.get(sig.get("strategy", ""), "unknown")
```

In `main()` (around line ~1347, after `run_strategies()` returns), add confluence filtering:

```python
# After: signals = run_strategies(data, context, strategy_filter)
# Add confluence filtering (feature-flagged):
use_confluence = os.environ.get("ALPHA_CONFLUENCE", "0") == "1"
if use_confluence:
    from alpha_engine.confluence_engine import ConfluenceEngine
    min_fam = int(os.environ.get("ALPHA_MIN_FAMILIES", "2"))
    ce = ConfluenceEngine(min_families=min_fam, time_window_hours=4.0)
    confluence_signals = ce.process_signals(signals)
    logger.info(f"Confluence: {len(signals)} raw → {len(confluence_signals)} after {min_fam}+ family filter")
    # Flatten back to individual signals but mark them as confluence-approved
    approved_strategies = set()
    for cs in confluence_signals:
        for s in cs["contributing_signals"]:
            s["confluence_score"] = cs["confluence_score"]
            s["confluence_families"] = cs["family_count"]
            approved_strategies.add((s["strategy"], s["symbol"], s["signal_type"]))
    signals = [s for s in signals if (s["strategy"], s["symbol"], s["signal_type"]) in approved_strategies]
```

**Step 4: Test locally with dry-run**

```bash
cd alpha_engine && ALPHA_CONFLUENCE=1 ALPHA_MIN_FAMILIES=2 python scanner.py --dry-run --crypto-only 2>&1 | grep "Confluence:"
```

Expected: `Confluence: N raw → M after 2+ family filter` where M <= N

**Step 5: Commit**

```bash
git add alpha_engine/scanner.py alpha_engine/tests/test_confluence.py
git commit -m "feat(scanner): wire confluence engine into signal pipeline (feature-flagged)"
```

---

## Task 6: Wire tournament into pick opening

**Files:**
- Modify: `alpha_engine/scanner.py` (in `open_new_picks()` around line ~998)

**Step 1: Add tournament recording to close_pick flow**

In the section of `main()` where picks are closed (around line ~1341, `check_open_picks()`), add tournament recording after each pick close:

```python
# After pick is closed (in check_open_picks or after close_pick call):
use_tournament = os.environ.get("ALPHA_TOURNAMENT", "0") == "1"
if use_tournament:
    from alpha_engine.tournament_engine import TournamentEngine
    for portfolio_name in ["conservative", "moderate", "aggressive"]:
        te = TournamentEngine(str(DB_PATH), portfolio=portfolio_name)
        te.record_trade(
            entity_id=pick["strategy"],
            won=(pick["status"] == "WON"),
            pnl_pct=pick["pnl_pct"],
        )
        # Also record combo if confluence data exists
        combo_strats = pick.get("extra", {}).get("confluence_strategies")
        if combo_strats and len(combo_strats) > 1:
            combo_id = te.get_combo_id(combo_strats)
            te.record_trade(combo_id, won=(pick["status"] == "WON"),
                          pnl_pct=pick["pnl_pct"], entity_type="combo")
        te.evaluate(pick["strategy"])
```

**Step 2: Adjust position sizing based on tier**

In `compute_position_size()` (line ~959), add tier-based risk override:

```python
# At the top of compute_position_size, after getting risk params:
use_tournament = os.environ.get("ALPHA_TOURNAMENT", "0") == "1"
if use_tournament:
    from alpha_engine.tournament_engine import TournamentEngine
    te = TournamentEngine(str(DB_PATH), portfolio="moderate")  # default portfolio
    tier = te.get_tier(strategy_name)
    tier_risk = te.get_risk_pct(tier)
    if tier_risk == 0.0:  # challenger = paper only
        return 0.0  # skip this pick in live trading
    risk_pct = min(risk_pct, tier_risk)  # tier caps the risk
```

**Step 3: Commit**

```bash
git add alpha_engine/scanner.py
git commit -m "feat(scanner): wire tournament engine into pick close + position sizing (feature-flagged)"
```

---

## Task 7: Add dashboard metrics for confluence + tournament

**Files:**
- Modify: `alpha_engine/live_dashboard.html` (add confluence stats section)

**Step 1: Add confluence metrics to JSON exports**

In `scanner.py` main(), after the existing JSON exports (line ~1430), add:

```python
# Export confluence + tournament state
if use_confluence or use_tournament:
    from alpha_engine.tournament_engine import TournamentEngine
    tournament_data = {}
    for pname in ["conservative", "moderate", "aggressive"]:
        te = TournamentEngine(str(DB_PATH), portfolio=pname)
        tournament_data[pname] = te.get_all_states()

    with open(DATA_DIR / "tournament_state.json", "w") as f:
        json.dump(tournament_data, f, indent=2, default=str)
    logger.info(f"Exported tournament state for 3 portfolios")
```

**Step 2: Commit**

```bash
git add alpha_engine/scanner.py
git commit -m "feat(scanner): export tournament_state.json for dashboard consumption"
```

---

## Task 8: Enable in GitHub Actions workflow

**Files:**
- Modify: `.github/workflows/alpha-engine-live.yml`

**Step 1: Add environment variables to the scan step**

Find the step that runs `python scanner.py` and add:

```yaml
env:
  ALPHA_CONFLUENCE: "1"
  ALPHA_TOURNAMENT: "1"
  ALPHA_MIN_FAMILIES: "2"
```

**Step 2: Add tournament_state.json to git add**

In the commit step, add:

```yaml
git add alpha_engine/data/tournament_state.json || true
```

**Step 3: Commit**

```bash
git add .github/workflows/alpha-engine-live.yml
git commit -m "feat(ci): enable confluence + tournament in live scanner workflow"
```

---

## Task 9: Run backtest validation

**Step 1: Run a dry-run scan with confluence enabled**

```bash
cd alpha_engine && ALPHA_CONFLUENCE=1 ALPHA_MIN_FAMILIES=2 python scanner.py --dry-run 2>&1 | tail -20
```

Verify:
- Confluence filtering reduces signals (expect 30-60% reduction)
- No errors or crashes
- Family annotations are correct

**Step 2: Run with tournament enabled**

```bash
cd alpha_engine && ALPHA_CONFLUENCE=1 ALPHA_TOURNAMENT=1 python scanner.py --dry-run 2>&1 | tail -20
```

Verify:
- Tournament state is created in `alpha_engine/data/tournament_state.json`
- All strategies start as "challenger"

**Step 3: Commit any fixes**

```bash
git add -A && git commit -m "fix: resolve integration issues from confluence+tournament dry run"
```

---

## Task 10: Update existing plan docs and push

**Step 1: Update CRYPTO_PREDICTION_IMPROVEMENT_PLAN.md**

Add a section referencing the new system:

```markdown
## Confluence + Tournament System (March 2026)
- Design: docs/plans/2026-03-07-hybrid-confluence-tournament-design.md
- Implementation: docs/plans/2026-03-07-hybrid-confluence-tournament-plan.md
- Feature flags: ALPHA_CONFLUENCE=1, ALPHA_TOURNAMENT=1
- Status: Deployed, collecting data for 90-day evaluation
```

**Step 2: Push everything**

```bash
git push origin main
```

---

## Summary: File Changes

| File | Action | Lines |
|------|--------|-------|
| `alpha_engine/config.py` | Modify | +120 (STRATEGY_FAMILIES dict) |
| `alpha_engine/confluence_engine.py` | Create | ~120 lines |
| `alpha_engine/tournament_engine.py` | Create | ~200 lines |
| `alpha_engine/portfolio_manager.py` | Create | ~130 lines |
| `alpha_engine/tests/test_confluence.py` | Create | ~100 lines |
| `alpha_engine/tests/test_tournament.py` | Create | ~80 lines |
| `alpha_engine/tests/test_portfolio.py` | Create | ~50 lines |
| `alpha_engine/scanner.py` | Modify | +40 (confluence + tournament wiring) |
| `.github/workflows/alpha-engine-live.yml` | Modify | +5 (env vars) |

**Total new code:** ~850 lines across 7 files
**Feature flags:** `ALPHA_CONFLUENCE=1`, `ALPHA_TOURNAMENT=1` — can be disabled instantly
