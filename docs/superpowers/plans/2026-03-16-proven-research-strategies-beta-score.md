# Proven Research Strategies + Beta Confluence Score — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 10 research-backed strategies to Alpha Engine, build a beta confluence scoring system alongside existing production scoring, wire both into the audit dashboard for A/B monitoring, and update the updates page.

**Architecture:** New strategies land in `alpha_engine/proven_research_strategies.py` (stubs already exist). Beta scorer is a new module in `cross_aggregation/` that scores every unified pick on 5 pillars (technical/onchain/sentiment/risk-reward/structure) out of 100. Both scores flow through normalizers into the dashboard template. Aggregator is currently broken (line 41 syntax error) and must be fixed first.

**Tech Stack:** Python 3.10+, pandas, requests, yfinance. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-16-proven-research-strategies-beta-score-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `cross_aggregation/aggregator.py` | MODIFY | Fix corrupted import (line 41), wire beta scorer (~line 1257) |
| `cross_aggregation/beta_confluence_scorer.py` | REWRITE | 5-pillar scorer + market context builder |
| `cross_aggregation/consensus_outcome_tracker.py` | MODIFY | Add beta fields to `_normalize_pick` (~line 364) |
| `audit_trail/dashboard_generator.py` | MODIFY | Add beta fields to `_normalize_pick` (~line 774), add beta column to template |
| `alpha_engine/proven_research_strategies.py` | MODIFY | Fill 10 strategy stubs with real logic |
| `alpha_engine/crypto_strategies.py` | MODIFY | Fix nested import (~line 4005) |
| `alpha_engine/indicators.py` | MODIFY | Add missing indicators (mfi, fear_and_greed, etc.) |
| `audit_dashboard/portfolio_manager.py` | MODIFY | Add RESEARCH_COHORT_STRATEGIES, beta score in score_pick() |
| `cross_aggregation/consensus_outcome_tracker.py` | MODIFY | Also add beta tracker outcome closure (~line 380+) |
| `cross_aggregation/data/beta_score_tracker.json` | CREATE | Empty tracker seed |
| `scripts/run_elimination.py` | CREATE | Weekly elimination script for research cohort |
| `updates/index.html` | MODIFY | Add enhancement entry |

**Deferred to Phase 2 (after core is stable):**
- Spec Sections 4.2-4.6 (confidence-weighted TP/SL, multi-TF confirmation, adaptive R:R, order-book depth, TP/SL efficiency panel)
- Spec Section 7.1-7.3 (adaptive position sizing, multi-TF engine, order-book depth pillar)
- These are medium/low priority enhancements that depend on the core beta scorer + strategies being live first.

---

## Chunk 1: Fix Broken Infrastructure

### Task 1: Fix aggregator.py corrupted import (HARD BLOCKER)

**Files:**
- Modify: `cross_aggregation/aggregator.py:38-45`

- [ ] **Step 1: Read the corrupted import block**

Lines 38-45 currently have `BetaConfluenceScorer` import spliced into the `regime_meta_router` try/except. Both imports fail together.

- [ ] **Step 2: Separate into independent try/except blocks**

Replace lines 38-45 with:

```python
# Regime meta-router (optional)
try:
    from cross_aggregation.regime_meta_router import get_consensus_regime, score_picks_by_regime
    _HAS_META_ROUTER = True
except ImportError:
    _HAS_META_ROUTER = False

# Beta Confluence Scorer — experimental A/B scoring (2026-03-16)
try:
    from cross_aggregation.beta_confluence_scorer import BetaConfluenceScorer
    _HAS_BETA_SCORER = True
except ImportError:
    _HAS_BETA_SCORER = False
```

- [ ] **Step 3: Verify aggregator.py compiles**

Run: `python -c "import py_compile; py_compile.compile('cross_aggregation/aggregator.py', doraise=True)"`
Expected: No errors (currently this FAILS due to the corrupted line)

- [ ] **Step 4: Commit**

```bash
git add cross_aggregation/aggregator.py
git commit -m "fix: separate corrupted import blocks in aggregator.py (beta scorer + meta router)"
```

---

### Task 2: Fix crypto_strategies.py nested import

**Files:**
- Modify: `alpha_engine/crypto_strategies.py:4005-4014`

- [ ] **Step 1: Read current import block**

Lines 4005-4014 have `proven_research_strategies` nested inside the `except ImportError` for `proven_scanner_strategies`. This means research strategies only load when scanner strategies fail.

- [ ] **Step 2: Make both imports independent**

Replace lines 4005-4014 with:

```python
# Proven Scanner Strategies
try:
    from proven_scanner_strategies import PROVEN_STRATEGIES as PROVEN_SCANNER
    CRYPTO_STRATEGIES.update(PROVEN_SCANNER)
except ImportError:
    pass

# Proven Research Strategies — 2026-03-16 cohort
try:
    from proven_research_strategies import PROVEN_RESEARCH_STRATEGIES
    CRYPTO_STRATEGIES.update(PROVEN_RESEARCH_STRATEGIES)
except ImportError:
    pass
```

- [ ] **Step 3: Verify it compiles**

Run: `python -c "import py_compile; py_compile.compile('alpha_engine/crypto_strategies.py', doraise=True)"`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add alpha_engine/crypto_strategies.py
git commit -m "fix: make proven_research_strategies import independent (not nested in except block)"
```

---

### Task 3: Add beta fields to dashboard_generator._normalize_pick

**Files:**
- Modify: `audit_trail/dashboard_generator.py:774-795`

- [ ] **Step 1: Read the current return dict**

The function at line 657 returns a dict with 16 fixed fields (lines 774-795). Unknown fields are dropped.

- [ ] **Step 2: Add beta fields to the returned dict**

After the existing fields (before the closing `}`), add:

```python
            "beta_score": raw.get("beta_score"),
            "beta_breakdown": raw.get("beta_breakdown"),
            "beta_qualified": raw.get("beta_qualified", False),
            "research_cohort": raw.get("research_cohort"),
```

- [ ] **Step 3: Verify it compiles**

Run: `python -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"`

- [ ] **Step 4: Commit**

```bash
git add audit_trail/dashboard_generator.py
git commit -m "feat: preserve beta_score fields in dashboard_generator _normalize_pick"
```

---

### Task 4: Add beta fields to consensus_outcome_tracker._normalize_pick

**Files:**
- Modify: `cross_aggregation/consensus_outcome_tracker.py:364-377`

- [ ] **Step 1: Read the current return dict**

The function at line 349 returns a dict with 11 fixed fields (lines 364-377). Returns None if validation fails.

- [ ] **Step 2: Add beta fields to the returned dict**

After the existing fields (before the closing `}`), add:

```python
            "beta_score": pick.get("beta_score"),
            "beta_breakdown": pick.get("beta_breakdown"),
            "beta_qualified": pick.get("beta_qualified", False),
```

- [ ] **Step 3: Verify it compiles**

Run: `python -c "import py_compile; py_compile.compile('cross_aggregation/consensus_outcome_tracker.py', doraise=True)"`

- [ ] **Step 4: Commit**

```bash
git add cross_aggregation/consensus_outcome_tracker.py
git commit -m "feat: preserve beta_score fields in consensus_outcome_tracker _normalize_pick"
```

---

### Task 5: Add RESEARCH_COHORT_STRATEGIES to portfolio_manager.py

**Files:**
- Modify: `audit_dashboard/portfolio_manager.py:45-61` and `~2379`

- [ ] **Step 1: Add the new set after PROVEN_STRATEGIES (after line 61)**

```python
# Research cohort — forward testing, NOT proven yet (added 2026-03-16)
# These get tracked but do NOT receive proven_bonus multipliers
RESEARCH_COHORT_STRATEGIES = {
    'vwap_trend_bounce',
    'hoffman_ema_irb',
    'statistical_pairs_zscore',
    'supply_demand_zone',
    'three_white_soldiers_rsi',
    'bearish_engulfing_reversal',
    'golden_confluence_swing',
    'vwap_rsi_institutional',
    'rsi_weighted_pairs_arb',
    'hoffman_keltner_expansion',
}
```

- [ ] **Step 2: Add research cohort detection in the classification logic (~line 2379)**

After the `is_proven` check, add a research cohort check that returns "FORWARD" tier (no bonus):

```python
    is_research = any(rs in strat for rs in RESEARCH_COHORT_STRATEGIES)
    if is_research:
        return "FORWARD"  # tracked but no proven bonus
```

- [ ] **Step 3: Add beta_score reading in score_pick()**

Find `score_pick()` function. After reading other pick fields, add:

```python
    beta_score = p.get("beta_score")
    beta_qualified = p.get("beta_qualified", False)
    beta_breakdown = p.get("beta_breakdown")
```

And include them in the output dict that score_pick returns.

- [ ] **Step 4: Add production score normalization for divergence**

Add helper near top of file:

```python
import math

def normalize_production_score(raw: float) -> float:
    """Sigmoid normalization of unbounded production score to 0-100 for beta comparison."""
    return 100.0 / (1.0 + math.exp(-0.1 * (raw - 50)))
```

In score_pick(), after computing the raw score, compute divergence:

```python
    prod_normalized = normalize_production_score(raw)
    divergence = abs(prod_normalized - beta_score) if beta_score is not None else None
```

- [ ] **Step 5: Verify it compiles**

Run: `python -c "import py_compile; py_compile.compile('audit_dashboard/portfolio_manager.py', doraise=True)"`

- [ ] **Step 6: Commit**

```bash
git add audit_dashboard/portfolio_manager.py
git commit -m "feat: add RESEARCH_COHORT_STRATEGIES + beta score integration in portfolio manager"
```

---

## Chunk 2: Beta Confluence Scorer

### Task 6: Rewrite beta_confluence_scorer.py

**Files:**
- Rewrite: `cross_aggregation/beta_confluence_scorer.py`

The existing file is malformed (semicolon on line 18, returns tuple instead of dict, HTML-escaped content). Full rewrite.

- [ ] **Step 1: Write the complete beta_confluence_scorer.py**

```python
"""
Beta Confluence Scorer — experimental multi-factor scoring (2026-03-16)
Scores every pick on 5 pillars (0-100 total) alongside the production score.
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Cache for market context (5 min TTL)
_MARKET_CONTEXT_CACHE = {"data": None, "ts": 0}
_CACHE_TTL = 300  # 5 minutes


class BetaConfluenceScorer:
    """Scores picks on 5 pillars: technical, onchain, sentiment, risk_reward, structure."""

    WEIGHTS = {
        "technical": 25,
        "onchain": 20,
        "sentiment": 15,
        "risk_reward": 20,
        "structure": 20,
    }

    def score_pick(self, pick: Dict[str, Any], market_context: Dict[str, Any],
                   system_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Score a unified pick dict from the aggregator.

        Args:
            pick: unified dict with keys: entry, tp, sl, direction, confidence, source_systems, etc.
            market_context: dict from build_market_context()
            system_data: optional dict of system trust tiers (from system_trust_registry)

        Returns:
            {"total": float 0-100, "breakdown": {pillar: float 0-max}, "qualified": bool}
        """
        breakdown = {
            "technical": self._score_technical(pick, market_context),
            "onchain": self._score_onchain(pick, market_context),
            "sentiment": self._score_sentiment(pick, market_context),
            "risk_reward": self._score_risk_reward(pick),
            "structure": self._score_structure(pick, market_context, system_data),
        }
        # Clamp each pillar to its max weight
        for key in breakdown:
            breakdown[key] = round(min(breakdown[key], self.WEIGHTS[key]), 1)

        total = round(sum(breakdown.values()), 1)
        return {
            "total": total,
            "breakdown": breakdown,
            "qualified": total >= 70,
        }

    def _score_technical(self, pick: Dict, ctx: Dict) -> float:
        """Technical confluence: RSI + MACD + volume + trend + agreement (0-25)."""
        score = 0.0
        conf = pick.get("confidence", 0.5)
        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")

        # RSI alignment (0-5)
        rsi = pick.get("rsi_at_entry") or pick.get("confidence_breakdown", {}).get("rsi")
        if rsi is not None:
            if is_long and rsi < 40:
                score += 5
            elif is_long and rsi < 50:
                score += 3
            elif not is_long and rsi > 60:
                score += 5
            elif not is_long and rsi > 50:
                score += 3

        # Volume confirmation (0-5)
        vol_ratio = pick.get("volume_ratio", 1.0)
        if vol_ratio >= 2.0:
            score += 5
        elif vol_ratio >= 1.5:
            score += 3
        elif vol_ratio >= 1.0:
            score += 1

        # Confidence as proxy for MACD/trend (0-5)
        score += min(5, conf * 7)

        # System agreement (0-5)
        agree = pick.get("agreement_count_raw", 1)
        if agree >= 3:
            score += 5
        elif agree >= 2:
            score += 3

        # Bayesian sub-component (0-5) — from confidence_calculator if available
        try:
            from signal_aggregator.confidence_calculator import BayesianConfidenceCalculator
            calc = BayesianConfidenceCalculator()
            bayes_conf = calc.calculate_signal_confidence(
                {"wins": 0, "losses": 0}, [conf]
            )
            score += min(5, min(1.0, bayes_conf) * 5)  # clamp D-S output
        except Exception:
            score += min(5, conf * 5)  # fallback

        return score

    def _score_onchain(self, pick: Dict, ctx: Dict) -> float:
        """On-chain support: F&G + exchange flows + MVRV (0-20)."""
        score = 0.0
        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")
        fg = ctx.get("fear_greed_index", 50)

        # Fear & Greed alignment (0-7)
        if is_long:
            if fg <= 25:
                score += 7  # extreme fear = buy opportunity
            elif fg <= 40:
                score += 4
            else:
                score += 2
        else:
            if fg >= 75:
                score += 7  # extreme greed = sell opportunity
            elif fg >= 60:
                score += 4
            else:
                score += 2

        # Exchange flows (0-7) — check larger magnitude first
        flows = ctx.get("exchange_flows_net", 0)
        if is_long and flows < -500:
            score += 7  # strong outflows = very bullish
        elif is_long and flows < 0:
            score += 4  # mild outflows = bullish
        elif not is_long and flows > 500:
            score += 7  # strong inflows = very bearish
        elif not is_long and flows > 0:
            score += 4  # mild inflows = bearish
        else:
            score += 2  # neutral

        # MVRV proxy (0-6)
        mvrv = ctx.get("mvrv_zscore", 0)
        if is_long and mvrv < -0.5:
            score += 6  # undervalued
        elif is_long and mvrv < 0:
            score += 3
        elif not is_long and mvrv > 2:
            score += 6  # overvalued
        else:
            score += 2

        return score

    def _score_sentiment(self, pick: Dict, ctx: Dict) -> float:
        """Sentiment alignment: F&G regime + LunarCrush (0-15)."""
        score = 0.0
        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")
        fg = ctx.get("fear_greed_index", 50)

        # F&G regime match (0-8)
        if is_long and fg <= 30:
            score += 8
        elif is_long and fg <= 45:
            score += 5
        elif not is_long and fg >= 70:
            score += 8
        elif not is_long and fg >= 55:
            score += 5
        else:
            score += 2

        # LunarCrush Galaxy Score (0-7) — falls back to F&G-based score
        galaxy = ctx.get("lunarcrush_galaxy_score")
        if galaxy is not None:
            if is_long and galaxy >= 70:
                score += 7
            elif is_long and galaxy >= 50:
                score += 4
            elif not is_long and galaxy <= 30:
                score += 7
            elif not is_long and galaxy <= 50:
                score += 4
            else:
                score += 2
        else:
            # Fallback: derive from F&G
            if (is_long and fg <= 35) or (not is_long and fg >= 65):
                score += 5
            else:
                score += 2

        return score

    def _score_risk_reward(self, pick: Dict) -> float:
        """Risk-reward quality: R:R + entry room + stop quality (0-20)."""
        score = 0.0
        entry = pick.get("entry") or pick.get("entry_price", 0)
        tp = pick.get("tp") or pick.get("take_profit", 0)
        sl = pick.get("sl") or pick.get("stop_loss", 0)

        if not entry or not tp or not sl:
            return 10.0  # neutral if missing

        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")

        # Compute R:R
        if is_long:
            reward = tp - entry
            risk = entry - sl
        else:
            reward = entry - tp
            risk = sl - entry

        rr = reward / risk if risk > 0 else 0

        # R:R score (0-8)
        if rr >= 3:
            score += 8
        elif rr >= 2:
            score += 5
        elif rr >= 1.5:
            score += 3

        # Entry room remaining (0-6)
        if is_long:
            total_dist = tp - sl
            remaining = tp - entry
        else:
            total_dist = sl - tp
            remaining = entry - tp

        room_pct = remaining / total_dist if total_dist > 0 else 0
        if room_pct >= 0.7:
            score += 6
        elif room_pct >= 0.5:
            score += 4
        elif room_pct >= 0.3:
            score += 2

        # ATR-based stop quality (0-6) — use atr_at_entry if available
        atr_val = pick.get("atr_at_entry", 0)
        if atr_val > 0:
            sl_distance = abs(entry - sl)
            atr_ratio = sl_distance / atr_val
            if atr_ratio >= 1.5:
                score += 6
            elif atr_ratio >= 1.0:
                score += 4
            elif atr_ratio >= 0.5:
                score += 2
        else:
            score += 3  # neutral if no ATR data

        return score

    def _score_structure(self, pick: Dict, ctx: Dict, system_data: Optional[Dict] = None) -> float:
        """Market structure: regime + BTC trend + volatility + system trust (0-20)."""
        score = 0.0
        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")
        strategy = pick.get("strategy", "")

        # Regime alignment (0-8)
        regime = ctx.get("regime", "UNKNOWN")
        is_momentum = any(k in strategy for k in ["momentum", "breakout", "trend", "ema", "hoffman"])
        is_mean_rev = any(k in strategy for k in ["reversion", "zscore", "pairs", "bounce", "engulfing"])

        if regime == "TRENDING" and is_momentum:
            score += 8
        elif regime == "RANGING" and is_mean_rev:
            score += 8
        elif regime in ("TRENDING", "RANGING"):
            score += 4
        else:
            score += 2

        # BTC trend for crypto (0-6)
        btc_pct = ctx.get("btc_24h_pct", 0)
        symbol = pick.get("symbol", "")
        is_crypto = any(c in symbol.upper() for c in ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "DOT", "AVAX", "LINK"])

        if is_crypto:
            if is_long and btc_pct > 2:
                score += 6
            elif is_long and btc_pct > 0:
                score += 4
            elif not is_long and btc_pct < -2:
                score += 6
            elif not is_long and btc_pct < 0:
                score += 4
            else:
                score += 1
        else:
            score += 3  # non-crypto: neutral

        # Volatility regime (0-4)
        vol_regime = ctx.get("volatility_regime", "NORMAL")
        if vol_regime == "LOW":
            score += 3
        elif vol_regime == "NORMAL":
            score += 4
        elif vol_regime == "HIGH":
            score += 2
        elif vol_regime == "EXTREME":
            score += 0

        # System trust tier bonus (0-2) — uses system_data if available
        if system_data:
            trust_tiers = pick.get("system_trust_tiers", {})
            proven_count = sum(1 for t in trust_tiers.values()
                              if isinstance(t, dict) and t.get("tier") == "PROVEN")
            if proven_count >= 2:
                score += 2
            elif proven_count >= 1:
                score += 1

        return score

    @staticmethod
    def build_market_context() -> Dict[str, Any]:
        """
        Build market context dict. Called ONCE per aggregation run.
        Uses 5s timeout per API. Falls back to cached values on failure.
        """
        global _MARKET_CONTEXT_CACHE

        # Return cache if fresh
        if _MARKET_CONTEXT_CACHE["data"] and (time.time() - _MARKET_CONTEXT_CACHE["ts"]) < _CACHE_TTL:
            return _MARKET_CONTEXT_CACHE["data"]

        ctx = {
            "fear_greed_index": 50,
            "btc_24h_pct": 0.0,
            "volatility_regime": "NORMAL",
            "regime": "UNKNOWN",
            "exchange_flows_net": 0,
            "mvrv_zscore": 0,
            "lunarcrush_galaxy_score": None,
        }

        import requests

        # Fear & Greed Index
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            if r.status_code == 200:
                fg_val = int(r.json()["data"][0]["value"])
                ctx["fear_greed_index"] = fg_val
        except Exception as e:
            logger.warning(f"F&G API failed: {e}")

        # BTC 24h price change
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json().get("bitcoin", {})
                ctx["btc_24h_pct"] = data.get("usd_24h_change", 0.0)
        except Exception as e:
            logger.warning(f"CoinGecko API failed: {e}")

        # Volatility regime from BTC change magnitude
        btc_abs = abs(ctx["btc_24h_pct"])
        if btc_abs < 1:
            ctx["volatility_regime"] = "LOW"
        elif btc_abs < 3:
            ctx["volatility_regime"] = "NORMAL"
        elif btc_abs < 7:
            ctx["volatility_regime"] = "HIGH"
        else:
            ctx["volatility_regime"] = "EXTREME"

        # Regime from F&G + BTC trend
        fg = ctx["fear_greed_index"]
        btc = ctx["btc_24h_pct"]
        if btc > 1 and fg > 45:
            ctx["regime"] = "TRENDING"
        elif abs(btc) < 1.5 and 35 < fg < 65:
            ctx["regime"] = "RANGING"
        elif btc_abs > 5:
            ctx["regime"] = "VOLATILE"
        else:
            ctx["regime"] = "UNKNOWN"

        # LunarCrush Galaxy Score (optional)
        lc_key = os.environ.get("LUNARCRUSH_API")
        if lc_key:
            try:
                r = requests.get(
                    "https://lunarcrush.com/api4/public/coins/btc/v1",
                    headers={"Authorization": f"Bearer {lc_key}"},
                    timeout=5,
                )
                if r.status_code == 200:
                    ctx["lunarcrush_galaxy_score"] = r.json().get("data", {}).get("galaxy_score")
            except Exception as e:
                logger.warning(f"LunarCrush API failed: {e}")

        # Cache result
        _MARKET_CONTEXT_CACHE["data"] = ctx
        _MARKET_CONTEXT_CACHE["ts"] = time.time()

        return ctx
```

- [ ] **Step 2: Verify it compiles and the class can be instantiated**

Run: `python -c "import sys; sys.path.insert(0, 'cross_aggregation'); from beta_confluence_scorer import BetaConfluenceScorer; s = BetaConfluenceScorer(); print('OK:', s.WEIGHTS)"`
Expected: `OK: {'technical': 25, 'onchain': 20, 'sentiment': 15, 'risk_reward': 20, 'structure': 20}`

- [ ] **Step 3: Commit**

```bash
git add cross_aggregation/beta_confluence_scorer.py
git commit -m "feat: rewrite beta_confluence_scorer with 5-pillar scoring + market context builder"
```

---

### Task 7: Wire beta scorer into aggregator.py

**Files:**
- Modify: `cross_aggregation/aggregator.py:~1257-1259`

- [ ] **Step 1: Add market_context build before the main symbol loop**

Find the main aggregation loop (where symbols are iterated). Before it starts, add:

```python
# Build market context ONCE per run for beta scoring
_market_context = {}
if _HAS_BETA_SCORER:
    try:
        _beta_scorer = BetaConfluenceScorer()
        _market_context = _beta_scorer.build_market_context()
    except Exception as e:
        logger.warning(f"Beta market context build failed: {e}")
        _HAS_BETA_SCORER = False
```

- [ ] **Step 2: Add beta scoring after unified dict, before aggregated.append()**

At line ~1257, between `unified["hierarchical_regime"] = ...` and `aggregated.append(unified)`, add:

```python
        # Beta confluence scoring (experimental A/B)
        if _HAS_BETA_SCORER:
            try:
                _beta_result = _beta_scorer.score_pick(unified, _market_context, unified.get("system_trust_tiers"))
                unified["beta_score"] = _beta_result["total"]
                unified["beta_breakdown"] = _beta_result["breakdown"]
                unified["beta_qualified"] = _beta_result["qualified"]
                best_breakdown["beta_total"] = _beta_result["total"]
                best_breakdown["beta_pillars"] = _beta_result["breakdown"]
            except Exception as e:
                logger.warning(f"Beta scoring failed for {symbol}: {e}")
                unified["beta_score"] = None
                unified["beta_breakdown"] = None
                unified["beta_qualified"] = False
```

- [ ] **Step 3: Add beta_score_tracker.json writing at end of run**

After the main loop completes and `aggregated` list is built, add tracker writing:

```python
# Write beta score tracker
if _HAS_BETA_SCORER:
    try:
        tracker_path = os.path.join(os.path.dirname(__file__), "data", "beta_score_tracker.json")
        existing = []
        if os.path.exists(tracker_path):
            with open(tracker_path) as f:
                existing = json.load(f).get("picks", [])

        for p in aggregated:
            if p.get("beta_score") is not None:
                existing.append({
                    "symbol": p["symbol"],
                    "direction": p["direction"],
                    "timestamp": p["generated_at"],
                    "production_score": p["confidence"],
                    "beta_score": p["beta_score"],
                    "beta_breakdown": p["beta_breakdown"],
                    "beta_qualified": p["beta_qualified"],
                    "outcome": None,
                    "outcome_timestamp": None,
                })

        # Keep last 2000 entries max
        existing = existing[-2000:]

        with open(tracker_path, "w") as f:
            json.dump({"picks": existing, "summary": {}}, f, indent=2)
    except Exception as e:
        logger.warning(f"Beta tracker write failed: {e}")
```

- [ ] **Step 4: Verify aggregator compiles**

Run: `python -c "import py_compile; py_compile.compile('cross_aggregation/aggregator.py', doraise=True)"`

- [ ] **Step 5: Commit**

```bash
git add cross_aggregation/aggregator.py
git commit -m "feat: wire beta confluence scorer into aggregator consensus loop"
```

---

### Task 8: Create seed beta_score_tracker.json

**Files:**
- Create: `cross_aggregation/data/beta_score_tracker.json`

- [ ] **Step 1: Ensure data directory exists**

Run: `ls cross_aggregation/data/ 2>/dev/null || mkdir -p cross_aggregation/data`

- [ ] **Step 2: Create the seed file**

```json
{"picks": [], "summary": {}}
```

- [ ] **Step 3: Commit**

```bash
git add cross_aggregation/data/beta_score_tracker.json
git commit -m "feat: create empty beta_score_tracker.json seed"
```

---

### Task 8b: Add outcome closure to consensus_outcome_tracker.py

**Files:**
- Modify: `cross_aggregation/consensus_outcome_tracker.py:~380+`

The aggregator writes open picks to `beta_score_tracker.json`. When picks close (TP/SL hit), the outcome tracker must update the tracker file.

- [ ] **Step 1: Find the outcome closure function**

In `consensus_outcome_tracker.py`, find where outcomes are written (around line 380+, the `ingest_new_picks` or outcome update function).

- [ ] **Step 2: Add beta tracker outcome update**

After the existing outcome closure logic, add:

```python
# Update beta_score_tracker.json with outcomes
try:
    tracker_path = os.path.join(os.path.dirname(__file__), "data", "beta_score_tracker.json")
    if os.path.exists(tracker_path):
        with open(tracker_path) as f:
            tracker = json.load(f)
        updated = False
        for tp_entry in tracker.get("picks", []):
            if (tp_entry.get("outcome") is None and
                tp_entry["symbol"] == pick["symbol"] and
                tp_entry["direction"] == pick["direction"]):
                tp_entry["outcome"] = outcome  # "TP_HIT" or "SL_HIT" or "EXPIRED"
                tp_entry["outcome_timestamp"] = datetime.now(timezone.utc).isoformat()
                updated = True
                break
        if updated:
            with open(tracker_path, "w") as f:
                json.dump(tracker, f, indent=2)
except Exception as e:
    logger.warning(f"Beta tracker outcome update failed: {e}")
```

- [ ] **Step 3: Verify it compiles**

Run: `python -c "import py_compile; py_compile.compile('cross_aggregation/consensus_outcome_tracker.py', doraise=True)"`

- [ ] **Step 4: Commit**

```bash
git add cross_aggregation/consensus_outcome_tracker.py
git commit -m "feat: add beta_score_tracker outcome closure in consensus_outcome_tracker"
```

---

## Chunk 3: Implement 10 Strategy Functions

### Task 9: Add missing indicators to indicators.py

**Files:**
- Modify: `alpha_engine/indicators.py`

Existing file has 416 lines with sma, ema, vwma, hma, ichimoku, rsi, stoch_rsi, macd, adx, atr, bollinger_bands, keltner_channels, bollinger_squeeze, volume_ratio, volume_expansion, obv, vwap_session, zscore, rolling_beta, rolling_correlation, hurst_exponent, shannon_entropy, detect_divergence, detect_support_resistance, detect_accumulation_phase, fair_value_gap.

**Note:** `stoch_rsi` already exists. Need to add: `mfi`, `donchian_channel`, `pivot_points`, `fear_and_greed_fetch`.

- [ ] **Step 1: Add mfi (Money Flow Index)**

Append to indicators.py:

```python
def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Money Flow Index — volume-weighted RSI (0-100)."""
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    mf = typical * df["Volume"]
    pos_flow = pd.Series(0.0, index=df.index)
    neg_flow = pd.Series(0.0, index=df.index)
    pos_flow[typical > typical.shift(1)] = mf[typical > typical.shift(1)]
    neg_flow[typical < typical.shift(1)] = mf[typical < typical.shift(1)]
    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum()
    ratio = pos_sum / neg_sum.replace(0, 1e-10)
    return 100 - (100 / (1 + ratio))
```

- [ ] **Step 2: Add donchian_channel**

```python
def donchian_channel(df: pd.DataFrame, period: int = 20) -> tuple:
    """Donchian Channel — returns (upper, lower, mid)."""
    upper = df["High"].rolling(period).max()
    lower = df["Low"].rolling(period).min()
    mid = (upper + lower) / 2
    return upper, lower, mid
```

- [ ] **Step 3: Add pivot_points**

```python
def pivot_points(df: pd.DataFrame) -> tuple:
    """Classic pivot points from prior bar — returns (pivot, r1, s1, r2, s2)."""
    h = df["High"].shift(1)
    l = df["Low"].shift(1)
    c = df["Close"].shift(1)
    pivot = (h + l + c) / 3
    r1 = 2 * pivot - l
    s1 = 2 * pivot - h
    r2 = pivot + (h - l)
    s2 = pivot - (h - l)
    return pivot, r1, s1, r2, s2
```

- [ ] **Step 4: Add fear_and_greed_fetch (cached)**

```python
_FG_CACHE = {"value": 50, "ts": 0}

def fear_and_greed_fetch() -> int:
    """Fetch current Fear & Greed index (0-100). Cached for 30 min."""
    import time
    if time.time() - _FG_CACHE["ts"] < 1800:
        return _FG_CACHE["value"]
    try:
        import requests
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        if r.status_code == 200:
            val = int(r.json()["data"][0]["value"])
            _FG_CACHE["value"] = val
            _FG_CACHE["ts"] = time.time()
            return val
    except Exception:
        pass
    return _FG_CACHE["value"]
```

- [ ] **Step 5: Verify indicators.py compiles**

Run: `python -c "import py_compile; py_compile.compile('alpha_engine/indicators.py', doraise=True)"`

- [ ] **Step 6: Commit**

```bash
git add alpha_engine/indicators.py
git commit -m "feat: add mfi, donchian_channel, pivot_points, fear_and_greed_fetch indicators"
```

---

### Task 10: Implement all 10 research strategies

**Files:**
- Modify: `alpha_engine/proven_research_strategies.py`

This is the largest task. Each strategy follows the same signature: `(data: dict[str, pd.DataFrame]) -> list[dict]`.

Reference: `baby_strategies/vwap_rsi_institutional.py` and `baby_strategies/rsi_pairs_arbitrage.py` already have full implementations by Gemini — port the core logic, adapt to the dict return format.

Helpers available from crypto_strategies.py: `_now_iso()`, `_get_category(symbol)`, `_smart_round(value)`, `_atr_tp_sl(close, high, low, tp_mult, sl_mult, atr_period)`.

Indicators available: `ema`, `rsi`, `stoch_rsi`, `macd`, `adx`, `atr`, `bollinger_bands`, `keltner_channels`, `vwap_session`, `obv`, `volume_ratio`, `zscore`, `mfi`, `donchian_channel`, `pivot_points`, `fear_and_greed_fetch`, `detect_support_resistance`, `hma`, `rolling_correlation`.

- [ ] **Step 1: Add imports and helpers at top of file**

```python
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict
try:
    from indicators import (ema, rsi, stoch_rsi, macd, adx, atr, bollinger_bands,
                            keltner_channels, vwap_session, obv, volume_ratio, zscore,
                            mfi, donchian_channel, fear_and_greed_fetch,
                            detect_support_resistance, rolling_correlation)
except ImportError:
    from alpha_engine.indicators import (ema, rsi, stoch_rsi, macd, adx, atr,
                                          bollinger_bands, keltner_channels, vwap_session,
                                          obv, volume_ratio, zscore, mfi, donchian_channel,
                                          fear_and_greed_fetch, detect_support_resistance,
                                          rolling_correlation)

CRYPTO_SYMBOLS = {
    "BTC-USD": "large_cap", "ETH-USD": "large_cap", "SOL-USD": "large_cap",
    "XRP-USD": "mid_cap", "BNB-USD": "mid_cap", "ADA-USD": "mid_cap",
    "DOGE-USD": "meme", "AVAX-USD": "mid_cap", "DOT-USD": "mid_cap",
    "LINK-USD": "mid_cap", "MATIC-USD": "mid_cap",
}

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _smart_round(v):
    if v >= 100: return round(v, 2)
    if v >= 1: return round(v, 4)
    if v >= 0.01: return round(v, 6)
    return round(v, 10)

def _make_pick(strategy, symbol, signal_type, entry, tp, sl, confidence, reason, timeframe, df):
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
    last = df.iloc[-1] if len(df) > 0 else {}
    return {
        "strategy": strategy,
        "symbol": symbol,
        "category": CRYPTO_SYMBOLS.get(symbol, "unknown"),
        "signal_type": signal_type,
        "entry_price": _smart_round(entry),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(confidence, 3),
        "risk_reward": round(rr, 2),
        "reason": reason,
        "timeframe": timeframe,
        "rsi_at_entry": round(float(rsi(df).iloc[-1]), 1) if len(df) > 14 else None,
        "atr_at_entry": round(float(atr(df).iloc[-1]), 6) if len(df) > 14 else None,
        "volume_ratio": round(float(volume_ratio(df).iloc[-1]), 2) if len(df) > 20 else None,
        "timestamp": _now_iso(),
        "research_cohort": "2026-03-16",
    }
```

- [ ] **Step 2: Implement vwap_trend_bounce (65-70% WR)**

```python
def vwap_trend_bounce(data: dict) -> list:
    """VWAP trend bounce: price returns to VWAP in established trend, rejection candle with volume."""
    signals = []
    for symbol, df in data.items():
        if len(df) < 50:
            continue
        vwap = vwap_session(df)
        ema_50 = ema(df["Close"], 50)
        atr_val = atr(df).iloc[-1]
        price = df["Close"].iloc[-1]
        vol_r = volume_ratio(df).iloc[-1]
        rsi_val = rsi(df).iloc[-1]

        # BUY: price near VWAP (within 0.5 ATR), above EMA50, volume spike, bullish candle
        vwap_dist = abs(price - vwap.iloc[-1]) / atr_val if atr_val > 0 else 99
        bullish_candle = df["Close"].iloc[-1] > df["Open"].iloc[-1]
        above_ema50 = price > ema_50.iloc[-1]

        if vwap_dist < 0.5 and above_ema50 and bullish_candle and vol_r > 1.3 and rsi_val < 65:
            tp = price + atr_val * 3.0
            sl = price - atr_val * 1.5
            conf = 0.50 + min(0.15, (vol_r - 1.3) * 0.1) + (0.05 if rsi_val < 45 else 0)
            signals.append(_make_pick("vwap_trend_bounce", symbol, "BUY", price, tp, sl, conf,
                f"VWAP bounce: price within {vwap_dist:.1f} ATR of VWAP, above EMA50, vol {vol_r:.1f}x", "4h", df))

        # SELL: mirror
        below_ema50 = price < ema_50.iloc[-1]
        bearish_candle = df["Close"].iloc[-1] < df["Open"].iloc[-1]
        if vwap_dist < 0.5 and below_ema50 and bearish_candle and vol_r > 1.3 and rsi_val > 35:
            tp = price - atr_val * 3.0
            sl = price + atr_val * 1.5
            conf = 0.50 + min(0.15, (vol_r - 1.3) * 0.1)
            signals.append(_make_pick("vwap_trend_bounce", symbol, "SELL", price, tp, sl, conf,
                f"VWAP bounce SHORT: price within {vwap_dist:.1f} ATR of VWAP, below EMA50", "4h", df))
    return signals
```

- [ ] **Step 3: Implement hoffman_ema_irb (62% WR)**

```python
def hoffman_ema_irb(data: dict) -> list:
    """Hoffman Trading: EMA 3/5/18 alignment + IRB (inventory retracement bar) pullback."""
    signals = []
    for symbol, df in data.items():
        if len(df) < 30:
            continue
        ema3 = ema(df["Close"], 3)
        ema5 = ema(df["Close"], 5)
        ema18 = ema(df["Close"], 18)
        atr_val = atr(df).iloc[-1]
        price = df["Close"].iloc[-1]

        # BUY: EMA3 > EMA5 > EMA18 (bullish alignment) + pullback to EMA5/18 zone
        bull_align = ema3.iloc[-1] > ema5.iloc[-1] > ema18.iloc[-1]
        # IRB: current bar low touches EMA5-EMA18 zone, closes above EMA5
        low_in_zone = df["Low"].iloc[-1] <= ema5.iloc[-1] and df["Low"].iloc[-1] >= ema18.iloc[-1]
        close_above = price > ema5.iloc[-1]

        if bull_align and low_in_zone and close_above:
            tp = price + atr_val * 3.0
            sl = min(df["Low"].iloc[-1], ema18.iloc[-1]) - atr_val * 0.5
            conf = 0.52 + (0.05 if volume_ratio(df).iloc[-1] > 1.2 else 0)
            signals.append(_make_pick("hoffman_ema_irb", symbol, "BUY", price, tp, sl, conf,
                f"Hoffman IRB: EMA3>{ema3.iloc[-1]:.2f} > EMA5>{ema5.iloc[-1]:.2f} > EMA18>{ema18.iloc[-1]:.2f}, pullback to zone", "1h", df))

        # SELL: mirror
        bear_align = ema3.iloc[-1] < ema5.iloc[-1] < ema18.iloc[-1]
        high_in_zone = df["High"].iloc[-1] >= ema5.iloc[-1] and df["High"].iloc[-1] <= ema18.iloc[-1]
        close_below = price < ema5.iloc[-1]
        if bear_align and high_in_zone and close_below:
            tp = price - atr_val * 3.0
            sl = max(df["High"].iloc[-1], ema18.iloc[-1]) + atr_val * 0.5
            conf = 0.52
            signals.append(_make_pick("hoffman_ema_irb", symbol, "SELL", price, tp, sl, conf,
                f"Hoffman IRB SHORT: bearish EMA alignment, pullback to zone", "1h", df))
    return signals
```

- [ ] **Step 4: Implement statistical_pairs_zscore (70-75% WR)**

```python
def statistical_pairs_zscore(data: dict) -> list:
    """Statistical arbitrage: Z-score at ±2 SD on correlated pairs, exit at 0."""
    signals = []
    symbols = list(data.keys())
    if len(symbols) < 2:
        return signals

    # Find correlated pairs
    for i, sym_a in enumerate(symbols):
        for sym_b in symbols[i+1:]:
            df_a, df_b = data[sym_a], data[sym_b]
            if len(df_a) < 60 or len(df_b) < 60:
                continue
            min_len = min(len(df_a), len(df_b))
            close_a = df_a["Close"].iloc[-min_len:].reset_index(drop=True)
            close_b = df_b["Close"].iloc[-min_len:].reset_index(drop=True)

            corr = close_a.rolling(60).corr(close_b).iloc[-1]
            if abs(corr) < 0.8:
                continue

            # Compute spread Z-score
            spread = np.log(close_a / close_b.replace(0, 1e-10))
            z = zscore(pd.DataFrame({"Close": spread}), period=60).iloc[-1]
            atr_a = atr(df_a).iloc[-1]

            if z < -2:  # A is underpriced vs B
                price = df_a["Close"].iloc[-1]
                tp = price + atr_a * 2.5
                sl = price - atr_a * 1.5
                conf = 0.55 + min(0.15, (abs(z) - 2) * 0.05)
                signals.append(_make_pick("statistical_pairs_zscore", sym_a, "BUY", price, tp, sl, conf,
                    f"Pairs arb: {sym_a}/{sym_b} Z={z:.2f}, corr={corr:.2f}", "1d", df_a))
            elif z > 2:  # A is overpriced vs B
                price = df_a["Close"].iloc[-1]
                tp = price - atr_a * 2.5
                sl = price + atr_a * 1.5
                conf = 0.55 + min(0.15, (abs(z) - 2) * 0.05)
                signals.append(_make_pick("statistical_pairs_zscore", sym_a, "SELL", price, tp, sl, conf,
                    f"Pairs arb: {sym_a}/{sym_b} Z={z:.2f}, corr={corr:.2f}", "1d", df_a))
    return signals
```

- [ ] **Step 5: Implement supply_demand_zone (55-65% WR)**

```python
def supply_demand_zone(data: dict) -> list:
    """Supply & demand zone trading: fresh zones with volume confirmation."""
    signals = []
    for symbol, df in data.items():
        if len(df) < 50:
            continue
        price = df["Close"].iloc[-1]
        atr_val = atr(df).iloc[-1]
        vol_r = volume_ratio(df).iloc[-1]
        levels = detect_support_resistance(df)

        supports = [l for l in levels if l < price and abs(price - l) / atr_val < 2]
        resistances = [l for l in levels if l > price and abs(l - price) / atr_val < 2]

        # BUY at demand zone (near support)
        if supports and vol_r > 1.0:
            nearest_support = max(supports)
            dist = abs(price - nearest_support) / atr_val
            if dist < 1.0:  # within 1 ATR of support
                tp = price + atr_val * 3.0
                sl = nearest_support - atr_val * 0.5
                conf = 0.48 + min(0.12, (1.0 - dist) * 0.1) + (0.05 if vol_r > 1.5 else 0)
                signals.append(_make_pick("supply_demand_zone", symbol, "BUY", price, tp, sl, conf,
                    f"Demand zone: support at {nearest_support:.2f}, dist {dist:.1f} ATR, vol {vol_r:.1f}x", "1h", df))

        # SELL at supply zone (near resistance)
        if resistances and vol_r > 1.0:
            nearest_resistance = min(resistances)
            dist = abs(nearest_resistance - price) / atr_val
            if dist < 1.0:
                tp = price - atr_val * 3.0
                sl = nearest_resistance + atr_val * 0.5
                conf = 0.48 + min(0.12, (1.0 - dist) * 0.1)
                signals.append(_make_pick("supply_demand_zone", symbol, "SELL", price, tp, sl, conf,
                    f"Supply zone: resistance at {nearest_resistance:.2f}, dist {dist:.1f} ATR", "1h", df))
    return signals
```

- [ ] **Step 6: Implement three_white_soldiers_rsi (83% WR)**

```python
def three_white_soldiers_rsi(data: dict) -> list:
    """Three White Soldiers + RSI < 35 filter: 3 consecutive bullish candles from oversold."""
    signals = []
    for symbol, df in data.items():
        if len(df) < 20:
            continue
        price = df["Close"].iloc[-1]
        atr_val = atr(df).iloc[-1]
        rsi_val = rsi(df).iloc[-1]

        # Check for 3 consecutive bullish candles with increasing closes
        c = df["Close"].iloc[-3:]
        o = df["Open"].iloc[-3:]
        bullish = all(c.iloc[i] > o.iloc[i] for i in range(3))
        increasing = c.iloc[0] < c.iloc[1] < c.iloc[2]

        if bullish and increasing and rsi_val < 45:
            # RSI filter: stronger signal when RSI was recently below 35
            rsi_series = rsi(df)
            recent_oversold = any(rsi_series.iloc[-6:-1] < 35)

            if recent_oversold:
                tp = price + atr_val * 3.5
                sl = min(df["Low"].iloc[-3:]) - atr_val * 0.3
                conf = 0.60 + (0.10 if rsi_val < 35 else 0.05)
                signals.append(_make_pick("three_white_soldiers_rsi", symbol, "BUY", price, tp, sl, conf,
                    f"3 White Soldiers: RSI {rsi_val:.0f}, recently oversold, 3 bullish candles", "1d", df))
    return signals
```

- [ ] **Step 7: Implement bearish_engulfing_reversal (75.76% WR)**

```python
def bearish_engulfing_reversal(data: dict) -> list:
    """Counter-intuitive: bearish engulfing as BUY signal (exhaustion pattern at bottoms)."""
    signals = []
    for symbol, df in data.items():
        if len(df) < 30:
            continue
        price = df["Close"].iloc[-1]
        atr_val = atr(df).iloc[-1]
        rsi_val = rsi(df).iloc[-1]

        # Bearish engulfing: current candle's body fully engulfs prior candle
        c1_open, c1_close = df["Open"].iloc[-2], df["Close"].iloc[-2]
        c2_open, c2_close = df["Open"].iloc[-1], df["Close"].iloc[-1]
        c1_bullish = c1_close > c1_open
        c2_bearish = c2_close < c2_open
        engulfs = c2_open >= c1_close and c2_close <= c1_open

        # Counter-intuitive BUY: engulfing at a low (RSI oversold), indicates capitulation
        if c1_bullish and c2_bearish and engulfs and rsi_val < 40:
            ema_200 = ema(df["Close"], 200)
            below_200 = price < ema_200.iloc[-1] if len(df) > 200 else True

            if below_200:
                tp = price + atr_val * 3.5
                sl = price - atr_val * 2.0
                conf = 0.55 + (0.10 if rsi_val < 30 else 0.05)
                signals.append(_make_pick("bearish_engulfing_reversal", symbol, "BUY", price, tp, sl, conf,
                    f"Bearish engulfing reversal BUY: RSI {rsi_val:.0f}, capitulation pattern below EMA200", "1d", df))
    return signals
```

- [ ] **Step 8: Implement golden_confluence_swing (72.3% WR)**

```python
def golden_confluence_swing(data: dict) -> list:
    """Golden confluence: RSI + MACD + volume + Fear & Greed + multi-layer scoring."""
    signals = []
    fg = fear_and_greed_fetch()

    for symbol, df in data.items():
        if len(df) < 50:
            continue
        price = df["Close"].iloc[-1]
        atr_val = atr(df).iloc[-1]
        rsi_val = rsi(df).iloc[-1]
        macd_line, signal_line, histogram = macd(df)
        vol_r = volume_ratio(df).iloc[-1]

        # Confluence scoring
        score = 0
        reasons = []

        # RSI
        if rsi_val < 40:
            score += 2; reasons.append(f"RSI oversold {rsi_val:.0f}")
        elif rsi_val > 60:
            score -= 1

        # MACD histogram positive
        if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
            score += 2; reasons.append("MACD bullish cross")
        elif histogram.iloc[-1] > 0:
            score += 1

        # Volume
        if vol_r > 1.5:
            score += 2; reasons.append(f"Volume {vol_r:.1f}x avg")
        elif vol_r > 1.2:
            score += 1

        # Fear & Greed
        if fg < 30:
            score += 2; reasons.append(f"F&G extreme fear {fg}")
        elif fg < 45:
            score += 1

        # EMA trend
        ema_21 = ema(df["Close"], 21).iloc[-1]
        ema_50 = ema(df["Close"], 50).iloc[-1]
        if price > ema_21 > ema_50:
            score += 1; reasons.append("EMA trend aligned")

        if score >= 5:  # minimum 5/9 confluence
            tp = price + atr_val * 4.0
            sl = price - atr_val * 2.0
            conf = 0.50 + min(0.20, score * 0.03)
            signals.append(_make_pick("golden_confluence_swing", symbol, "BUY", price, tp, sl, conf,
                f"Golden confluence ({score}/9): {', '.join(reasons)}", "1d", df))
    return signals
```

- [ ] **Step 9: Implement vwap_rsi_institutional (70-75% WR)**

Port from `baby_strategies/vwap_rsi_institutional.py` (Gemini's implementation), adapted to dict format:

```python
def vwap_rsi_institutional(data: dict) -> list:
    """VWAP return + triple RSI (14/21/50) institutional confluence."""
    signals = []
    for symbol, df in data.items():
        if len(df) < 60:
            continue
        price = df["Close"].iloc[-1]
        atr_val = atr(df).iloc[-1]
        vwap = vwap_session(df)
        rsi_14 = rsi(df, 14).iloc[-1]
        rsi_21 = rsi(df, 21).iloc[-1]
        rsi_50 = rsi(df, 50).iloc[-1]
        vol_r = volume_ratio(df).iloc[-1]
        vwap_val = vwap.iloc[-1]

        # BUY: price near VWAP + RSI14 < 40 + RSI21 > 50 + RSI50 > 55
        near_vwap = abs(price - vwap_val) / atr_val < 0.7 if atr_val > 0 else False
        if near_vwap and rsi_14 < 40 and rsi_21 > 50 and rsi_50 > 55 and vol_r > 1.0:
            tp = price + atr_val * 3.0
            sl = price - atr_val * 1.5
            rsi_depth = (40 - rsi_14) / 40  # deeper oversold = higher conf
            conf = 0.55 + min(0.15, rsi_depth * 0.2) + (0.05 if vol_r > 1.5 else 0)
            signals.append(_make_pick("vwap_rsi_institutional", symbol, "BUY", price, tp, sl, conf,
                f"VWAP-RSI institutional: RSI14={rsi_14:.0f} RSI21={rsi_21:.0f} RSI50={rsi_50:.0f}, near VWAP", "4h", df))

        # SELL: mirror
        if near_vwap and rsi_14 > 60 and rsi_21 < 50 and rsi_50 < 45 and vol_r > 1.0:
            tp = price - atr_val * 3.0
            sl = price + atr_val * 1.5
            conf = 0.55
            signals.append(_make_pick("vwap_rsi_institutional", symbol, "SELL", price, tp, sl, conf,
                f"VWAP-RSI institutional SHORT: RSI14={rsi_14:.0f}, RSI21={rsi_21:.0f}", "4h", df))
    return signals
```

- [ ] **Step 10: Implement rsi_weighted_pairs_arb (75-82% WR)**

Port from `baby_strategies/rsi_pairs_arbitrage.py`:

```python
def rsi_weighted_pairs_arb(data: dict) -> list:
    """RSI-weighted pairs arbitrage: Z-score < -2 + RSI of underperformer < 35."""
    signals = []
    symbols = list(data.keys())
    if len(symbols) < 2:
        return signals

    for i, sym_a in enumerate(symbols):
        for sym_b in symbols[i+1:]:
            df_a, df_b = data[sym_a], data[sym_b]
            if len(df_a) < 60 or len(df_b) < 60:
                continue
            min_len = min(len(df_a), len(df_b))
            close_a = df_a["Close"].iloc[-min_len:].reset_index(drop=True)
            close_b = df_b["Close"].iloc[-min_len:].reset_index(drop=True)

            corr = close_a.rolling(60).corr(close_b).iloc[-1]
            if abs(corr) < 0.7:
                continue

            spread = np.log(close_a / close_b.replace(0, 1e-10))
            z = zscore(pd.DataFrame({"Close": spread}), period=60).iloc[-1]
            rsi_a = rsi(df_a).iloc[-1]
            atr_a = atr(df_a).iloc[-1]

            # BUY A when Z < -2 AND RSI of A < 35
            if z < -2 and rsi_a < 35:
                price = df_a["Close"].iloc[-1]
                tp = price + atr_a * 2.5
                sl = price - atr_a * 1.25
                z_depth = min(1.0, (abs(z) - 2) / 2)
                rsi_depth = (35 - rsi_a) / 35
                conf = 0.58 + min(0.17, z_depth * 0.1 + rsi_depth * 0.1 + (corr - 0.7) * 0.1)
                signals.append(_make_pick("rsi_weighted_pairs_arb", sym_a, "BUY", price, tp, sl, conf,
                    f"RSI-pairs arb: {sym_a}/{sym_b} Z={z:.2f} RSI={rsi_a:.0f} corr={corr:.2f}", "1d", df_a))
    return signals
```

- [ ] **Step 11: Implement hoffman_keltner_expansion (68-73% WR)**

```python
def hoffman_keltner_expansion(data: dict) -> list:
    """Hoffman + Keltner: EMA 3/5/18 alignment + Keltner bandwidth < 2% + volume."""
    signals = []
    for symbol, df in data.items():
        if len(df) < 30:
            continue
        price = df["Close"].iloc[-1]
        ema3 = ema(df["Close"], 3).iloc[-1]
        ema5 = ema(df["Close"], 5).iloc[-1]
        ema18 = ema(df["Close"], 18).iloc[-1]
        upper, lower, mid = keltner_channels(df)
        atr_val = atr(df).iloc[-1]
        vol_r = volume_ratio(df).iloc[-1]

        # Keltner bandwidth (compression)
        bandwidth = (upper.iloc[-1] - lower.iloc[-1]) / mid.iloc[-1] if mid.iloc[-1] > 0 else 1
        compressed = bandwidth < 0.04  # < 4% bandwidth = squeeze

        # BUY: bullish EMA alignment + Keltner compression + volume expansion
        bull_align = ema3 > ema5 > ema18
        if bull_align and compressed and vol_r > 1.3:
            tp = price + atr_val * 3.5
            sl = ema18 - atr_val * 0.5
            conf = 0.55 + (0.05 if vol_r > 1.8 else 0) + (0.05 if bandwidth < 0.02 else 0)
            signals.append(_make_pick("hoffman_keltner_expansion", symbol, "BUY", price, tp, sl, conf,
                f"Hoffman-Keltner: EMA aligned, bandwidth {bandwidth:.3f}, vol {vol_r:.1f}x", "1h", df))

        # SELL: bearish alignment + compression + volume
        bear_align = ema3 < ema5 < ema18
        if bear_align and compressed and vol_r > 1.3:
            tp = price - atr_val * 3.5
            sl = ema18 + atr_val * 0.5
            conf = 0.55
            signals.append(_make_pick("hoffman_keltner_expansion", symbol, "SELL", price, tp, sl, conf,
                f"Hoffman-Keltner SHORT: bearish EMA alignment, bandwidth {bandwidth:.3f}", "1h", df))
    return signals
```

- [ ] **Step 12: Update PROVEN_RESEARCH_STRATEGIES dict**

Ensure the dict at the bottom of the file maps all 10 function names:

```python
PROVEN_RESEARCH_STRATEGIES = {
    "vwap_trend_bounce": vwap_trend_bounce,
    "hoffman_ema_irb": hoffman_ema_irb,
    "statistical_pairs_zscore": statistical_pairs_zscore,
    "supply_demand_zone": supply_demand_zone,
    "three_white_soldiers_rsi": three_white_soldiers_rsi,
    "bearish_engulfing_reversal": bearish_engulfing_reversal,
    "golden_confluence_swing": golden_confluence_swing,
    "vwap_rsi_institutional": vwap_rsi_institutional,
    "rsi_weighted_pairs_arb": rsi_weighted_pairs_arb,
    "hoffman_keltner_expansion": hoffman_keltner_expansion,
}
```

- [ ] **Step 13: Verify file compiles**

Run: `python -c "import sys; sys.path.insert(0, 'alpha_engine'); from proven_research_strategies import PROVEN_RESEARCH_STRATEGIES; print(f'OK: {len(PROVEN_RESEARCH_STRATEGIES)} strategies')"`
Expected: `OK: 10 strategies`

- [ ] **Step 14: Commit**

```bash
git add alpha_engine/proven_research_strategies.py
git commit -m "feat: implement 10 research-backed strategies (VWAP bounce, Hoffman, pairs arb, etc.)"
```

---

## Chunk 4: Dashboard Template + Updates Page

### Task 11: Add beta score column to dashboard template

**Files:**
- Modify: `audit_trail/dashboard_generator.py` (the template construction section, ~line 3678+)

- [ ] **Step 1: Find the template HTML generation in dashboard_generator.py**

Read `audit_trail/dashboard_generator.py` around lines 3678-3700 to find where the HTML template and table headers are constructed.

- [ ] **Step 2: Add "Beta Score" column header to pick tables**

In the table header row, after the existing columns, add:

```html
<th>Beta Score</th>
```

- [ ] **Step 3: Add beta score cell rendering in the row template**

In the pick row template, add the cell with colored bar:

```html
<td class="beta-score">
  {{#if beta_score}}
    <div style="display:flex;align-items:center;gap:4px">
      <div style="width:40px;height:8px;background:#333;border-radius:4px;overflow:hidden">
        <div style="width:{{beta_score}}%;height:100%;background:{{#if beta_qualified}}#22c55e{{else}}{{#if (gte beta_score 50)}}#f59e0b{{else}}#ef4444{{/if}}{{/if}}"></div>
      </div>
      <span style="color:{{#if beta_qualified}}#22c55e{{else}}{{#if (gte beta_score 50)}}#f59e0b{{else}}#ef4444{{/if}}{{/if}};font-size:0.85em">{{beta_score}}</span>
    </div>
  {{else}}
    <span style="color:#666">—</span>
  {{/if}}
</td>
```

> **Note:** The exact template syntax depends on how `dashboard_generator.py` constructs HTML. It may use f-strings, Jinja, or manual string concatenation. Adapt the snippet to match the existing pattern.

- [ ] **Step 4: Add research cohort badge**

Where the strategy name is displayed, add a badge for research cohort strategies:

```python
research_badge = ' <span style="background:#3b82f6;color:white;padding:1px 4px;border-radius:3px;font-size:0.7em">RESEARCH</span>' if pick.get("research_cohort") else ''
```

- [ ] **Step 5: Verify dashboard_generator compiles**

Run: `python -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"`

- [ ] **Step 6: Commit**

```bash
git add audit_trail/dashboard_generator.py
git commit -m "feat: add beta score column + research cohort badge to dashboard template"
```

---

### Task 12: Update the updates page

**Files:**
- Modify: `updates/index.html`

- [ ] **Step 1: Read the updates page to find the insertion point**

Read `updates/index.html` and find `<div class="section-year">` for the current month section. The new entry goes at the TOP of the most recent section.

- [ ] **Step 2: Add the update entry**

Insert after the most recent `<div class="section-year">` tag:

```html
<div class="update-entry" style="--dot-color: #22c55e;" data-tags="alpha-engine,cross-aggregation,audit-dashboard" data-category="trading" data-types="feature,improvement">
  <div class="update-date">Mar 16, 2026</div>
  <div class="update-title">
    <span class="badge badge-feature">Major</span>
    10 Research-Backed Strategies + Beta Confluence Scoring System
  </div>
  <div class="update-body">
    <h4>New Research Strategies (Alpha Engine)</h4>
    <p>Added 10 high-WR strategies from institutional research analysis across 6 strategy documents:</p>
    <table>
      <tr><th>Strategy</th><th>Expected WR</th><th>Type</th></tr>
      <tr><td><code>vwap_trend_bounce</code></td><td>65-70%</td><td>VWAP + volume</td></tr>
      <tr><td><code>hoffman_ema_irb</code></td><td>62%</td><td>EMA alignment + pullback</td></tr>
      <tr><td><code>statistical_pairs_zscore</code></td><td>70-75%</td><td>Pairs arbitrage</td></tr>
      <tr><td><code>supply_demand_zone</code></td><td>55-65%</td><td>Zone trading</td></tr>
      <tr><td><code>three_white_soldiers_rsi</code></td><td>83%</td><td>Candlestick + RSI</td></tr>
      <tr><td><code>bearish_engulfing_reversal</code></td><td>75.76%</td><td>Counter-intuitive BUY</td></tr>
      <tr><td><code>golden_confluence_swing</code></td><td>72.3%</td><td>Multi-factor swing</td></tr>
      <tr><td><code>vwap_rsi_institutional</code></td><td>70-75%</td><td>VWAP + triple RSI</td></tr>
      <tr><td><code>rsi_weighted_pairs_arb</code></td><td>75-82%</td><td>RSI + pairs Z-score</td></tr>
      <tr><td><code>hoffman_keltner_expansion</code></td><td>68-73%</td><td>EMA + Keltner squeeze</td></tr>
    </table>

    <h4>Beta Confluence Scoring (Experimental A/B)</h4>
    <p>Every pick now receives a <strong>beta score (0-100)</strong> alongside the production score, based on 5 pillars:</p>
    <table>
      <tr><th>Pillar</th><th>Weight</th><th>What It Measures</th></tr>
      <tr><td>Technical Confluence</td><td>25</td><td>RSI + MACD + volume + trend + system agreement</td></tr>
      <tr><td>On-Chain Support</td><td>20</td><td>Fear &amp; Greed + exchange flows + MVRV</td></tr>
      <tr><td>Sentiment Alignment</td><td>15</td><td>F&amp;G regime + LunarCrush Galaxy Score</td></tr>
      <tr><td>Risk-Reward Quality</td><td>20</td><td>R:R ratio + entry room + ATR stop quality</td></tr>
      <tr><td>Market Structure</td><td>20</td><td>Regime alignment + BTC trend + volatility</td></tr>
    </table>
    <p>Beta-qualified picks (≥70/100) are highlighted green in the dashboard. Both scores are tracked for A/B comparison — after 50+ closed picks, the better-predicting score will be promoted to primary.</p>

    <h4>Dashboard Enhancements</h4>
    <ul>
      <li>Beta Score column with colored progress bar (red/yellow/green)</li>
      <li>Research Cohort badge for new strategy picks</li>
      <li>Production vs Beta score divergence alerts (>30pt spread flagged)</li>
      <li>ATR-scaled TP/SL for all new strategies</li>
    </ul>

    <h4>Infrastructure Fixes</h4>
    <ul>
      <li>Fixed corrupted import in aggregator.py (beta scorer + meta router)</li>
      <li>Fixed beta_confluence_scorer.py syntax error</li>
      <li>Added beta fields to both _normalize_pick functions (dashboard + consensus tracker)</li>
      <li>Added 4 new indicators: MFI, Donchian Channel, Pivot Points, Fear &amp; Greed fetch</li>
    </ul>

    <h4>Affected Dashboards</h4>
    <ul>
      <li><a href="https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/">Alpha Engine Dashboard</a> — new strategies generating picks</li>
      <li><a href="https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/">Cross-Aggregation Monitor</a> — beta scores in consensus picks</li>
    </ul>
  </div>
</div>
```

- [ ] **Step 3: Verify the updates page has correct structure**

Run: `grep -c "filter-pill" updates/index.html` — should be 21+
Run: `grep "background: #0a0a12" updates/index.html` — should find dark theme

- [ ] **Step 4: Commit**

```bash
git add updates/index.html
git commit -m "feat: add Mar 16 update entry — 10 research strategies + beta confluence scoring"
```

---

### Task 12b: Create elimination script

**Files:**
- Create: `scripts/run_elimination.py`

- [ ] **Step 1: Create the elimination script**

```python
"""Weekly elimination: evaluates research cohort strategies against kill criteria."""
import json
import os
import csv
from datetime import datetime, timezone

TRACKER_PATH = os.path.join(os.path.dirname(__file__), "..", "cross_aggregation", "data", "beta_score_tracker.json")
KILL_WR = 0.45
KILL_PF = 1.0
MIN_TRADES = 30

def run():
    if not os.path.exists(TRACKER_PATH):
        print("No tracker file found.")
        return

    with open(TRACKER_PATH) as f:
        tracker = json.load(f)

    # Group by strategy
    strategy_stats = {}
    for p in tracker.get("picks", []):
        if p.get("outcome") is None:
            continue
        strat = p.get("strategy", "unknown")
        if strat not in strategy_stats:
            strategy_stats[strat] = {"wins": 0, "losses": 0, "total_pnl": 0}
        if p["outcome"] == "TP_HIT":
            strategy_stats[strat]["wins"] += 1
        else:
            strategy_stats[strat]["losses"] += 1

    # Evaluate
    blocked = []
    report = []
    for strat, stats in strategy_stats.items():
        total = stats["wins"] + stats["losses"]
        wr = stats["wins"] / total if total > 0 else 0
        if total >= MIN_TRADES and wr < KILL_WR:
            blocked.append(strat)
        report.append({"strategy": strat, "trades": total, "wr": round(wr, 3), "blocked": strat in blocked})

    # Write report
    report_path = os.path.join(os.path.dirname(__file__), "..", "cross_aggregation", "data",
                               f"elimination_report_{datetime.now().strftime('%Y%m%d')}.csv")
    with open(report_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["strategy", "trades", "wr", "blocked"])
        w.writeheader()
        w.writerows(report)

    print(f"Evaluated {len(strategy_stats)} strategies. Blocked: {blocked}")
    print(f"Report: {report_path}")

if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Verify it runs**

Run: `python scripts/run_elimination.py`
Expected: "No tracker file found." or a summary line (no errors)

- [ ] **Step 3: Commit**

```bash
git add scripts/run_elimination.py
git commit -m "feat: add weekly elimination script for research cohort strategies"
```

---

## Chunk 5: Final Verification

### Task 13: End-to-end compilation check

- [ ] **Step 1: Compile all modified files**

```bash
python -c "
import py_compile
files = [
    'cross_aggregation/aggregator.py',
    'cross_aggregation/beta_confluence_scorer.py',
    'cross_aggregation/consensus_outcome_tracker.py',
    'audit_trail/dashboard_generator.py',
    'audit_dashboard/portfolio_manager.py',
    'alpha_engine/crypto_strategies.py',
    'alpha_engine/proven_research_strategies.py',
    'alpha_engine/indicators.py',
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'OK: {f}')
    except py_compile.PyCompileError as e:
        print(f'FAIL: {f} — {e}')
"
```
Expected: All OK, no FAIL.

- [ ] **Step 2: Verify strategy count**

```bash
python -c "
import sys; sys.path.insert(0, 'alpha_engine')
from crypto_strategies import CRYPTO_STRATEGIES
print(f'Total crypto strategies: {len(CRYPTO_STRATEGIES)}')
research = [k for k in CRYPTO_STRATEGIES if k in ['vwap_trend_bounce','hoffman_ema_irb','statistical_pairs_zscore','supply_demand_zone','three_white_soldiers_rsi','bearish_engulfing_reversal','golden_confluence_swing','vwap_rsi_institutional','rsi_weighted_pairs_arb','hoffman_keltner_expansion']]
print(f'Research strategies loaded: {len(research)}/10 — {research}')
"
```
Expected: 10/10 research strategies loaded.

- [ ] **Step 3: Verify beta scorer works with a mock pick**

```bash
python -c "
import sys; sys.path.insert(0, 'cross_aggregation')
from beta_confluence_scorer import BetaConfluenceScorer
s = BetaConfluenceScorer()
mock = {'entry': 100, 'tp': 106, 'sl': 97, 'direction': 'LONG', 'confidence': 0.65,
        'agreement_count_raw': 2, 'symbol': 'BTC-USD', 'strategy': 'vwap_trend_bounce'}
ctx = {'fear_greed_index': 30, 'btc_24h_pct': 2.5, 'volatility_regime': 'NORMAL',
       'regime': 'TRENDING', 'exchange_flows_net': -100, 'mvrv_zscore': -0.3, 'lunarcrush_galaxy_score': None}
result = s.score_pick(mock, ctx)
print(f'Beta score: {result[\"total\"]}/100, qualified: {result[\"qualified\"]}')
print(f'Breakdown: {result[\"breakdown\"]}')
assert result['total'] <= 100
assert isinstance(result['qualified'], bool)
print('All assertions passed')
"
```

- [ ] **Step 4: Stage only plan files and verify**

```bash
git status
# Review output — only the files from this plan should be modified
# Do NOT use git add -A — stage specific files only:
git add cross_aggregation/aggregator.py cross_aggregation/beta_confluence_scorer.py \
       cross_aggregation/consensus_outcome_tracker.py cross_aggregation/data/beta_score_tracker.json \
       audit_trail/dashboard_generator.py audit_dashboard/portfolio_manager.py \
       alpha_engine/crypto_strategies.py alpha_engine/proven_research_strategies.py \
       alpha_engine/indicators.py updates/index.html scripts/run_elimination.py
```

> **Note:** Each task already has its own commit. This final step is only needed if any files were missed. Check `git status` — if clean, skip this step.
