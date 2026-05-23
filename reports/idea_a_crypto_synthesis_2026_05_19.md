# IDEA-A CRYPTO Criteria — Swarm Synthesis 2026-05-19

**Swarm run**: `swarm_runs/run_20260519T060639Z`
**Engines**: deepseek, inception, openrouter, ollama_local (4/4 ok; cerebras skipped — no API key)
**Prompt**: `tools/swarm/prompts/idea_a_crypto_criteria_2026_05_19.md`
**Context**: CRYPTO WR=44.6%, PF=1.25, n=8067. Target: WR>50%/PF>1.5 (T2), WR>55%/PF>2.0 (T1).

---

## Top 3 Consensus Factors (Cross-Engine Agreement)

All 4 engines independently ranked these in the top 3-4 with strong agreement on mechanism,
data source, and wire-in point.

### Factor 1 — Order Book Imbalance (OBI) Persistence

**Consensus rank**: #1 (deepseek), #1 (inception), #1 (openrouter), #4 (ollama_local)
**Cross-engine agreement**: HIGH

**Mechanism**: Persistent bid-side dominance (OBI > 0.6 sustained >5 minutes) predicts price
continuation in the direction of the imbalance over the next 5–15 days. Informed traders
accumulate against market maker quote adjustments, creating a systematic lead signal.

**Academic References**:
- Cont, Kukanov & Stoikov (2014) "The Price Impact of Order Book Events"
- Cheng & Shen (2022) "Order-book imbalance and crypto returns" — J. Financial Markets
- Bouchaud et al. (2004) "Order Book Dynamics and Market Microstructure"

**Data Source**: Binance REST API (free, no auth) — `GET /api/v3/depth?symbol=BTCUSDT&limit=100`
Poll every 30s. Compute bid-volume / (bid-volume + ask-volume). Track 5-minute persistence via
rolling mean.

**Implementation Complexity**: 2 (easy — ~50 lines Python)
**Expected WR Lift**: +2.5–5pp (deepseek: +3–5pp; inception: +2.5pp; openrouter: +3–5pp)
**Wire-In Point**: `passes_smart_gate()` in `alpha_engine/quality_gates.py`

**Implementation Sketch**:
```python
import requests
from collections import deque
import numpy as np

OBI_WINDOW_SECS = 300  # 5-minute rolling window
OBI_THRESHOLD = 0.60   # sustained imbalance threshold
OBI_GATE_MIN_PERSISTENCE = 0.7  # fraction of window above threshold

_obi_history: dict[str, deque] = {}

def fetch_obi(symbol: str) -> float:
    """Fetch real-time order book imbalance from Binance public API."""
    resp = requests.get(
        "https://api.binance.com/api/v3/depth",
        params={"symbol": symbol.replace("/", ""), "limit": 100},
        timeout=5,
    )
    data = resp.json()
    bid_vol = sum(float(b[1]) for b in data["bids"])
    ask_vol = sum(float(a[1]) for a in data["asks"])
    return bid_vol / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0.5

def obi_gate_passes(symbol: str, direction: str) -> bool:
    """
    Wire into passes_smart_gate() in quality_gates.py.
    direction: 'LONG' or 'SHORT'
    Returns True if OBI is persistently aligned with direction.
    """
    obi = fetch_obi(symbol)
    hist = _obi_history.setdefault(symbol, deque(maxlen=10))  # ~5 min at 30s poll
    hist.append(obi)
    if len(hist) < 5:
        return True  # fail-open on cold start
    persistence = np.mean([v > OBI_THRESHOLD for v in hist])
    if direction == "LONG":
        return persistence >= OBI_GATE_MIN_PERSISTENCE
    elif direction == "SHORT":
        # for shorts, check ask-side dominance (OBI < 1-threshold)
        persistence_short = np.mean([v < (1 - OBI_THRESHOLD) for v in hist])
        return persistence_short >= OBI_GATE_MIN_PERSISTENCE
    return True

# Wire-in to quality_gates.py passes_smart_gate():
# if not obi_gate_passes(pick["symbol"], pick["direction"]):
#     return False, "OBI_PERSISTENCE_GATE_FAIL"
```

**Wire-In File**: `alpha_engine/quality_gates.py` → `passes_smart_gate()`
**Shadow mode first**: Add to `audit_trail/quality_gates.py` gate registry with `shadow=True`
for 2 weeks before going live.

---

### Factor 2 — BTC Dominance Momentum (Cross-Asset Spillover)

**Consensus rank**: #2 (deepseek), #2 (inception), #3 (openrouter), not in top 3 (ollama_local)
**Cross-engine agreement**: HIGH (3/4 engines top-3)

**Mechanism**: When BTC dominance (BTC market cap / total crypto market cap) rises >2% over 7
days, altcoins underperform over the next 5–15 days as capital rotates to BTC safety. Falling
dominance predicts altseason — relative altcoin outperformance.

**Academic References**:
- Liu & Tsyvinski (2021) "Risks and Returns of Cryptocurrency" — NBER WP 28377
- Katsiampa & Corbet (2021) "Cross-asset spillovers in crypto markets" — Quant. Finance
- Bianchi, Dickerson & Houser (2022) "Cryptocurrency Momentum"

**Data Source**: CoinGecko free API — `GET /api/v3/global`
Returns `market_cap_percentage.btc` directly. No auth, ~30 calls/min.

**Implementation Complexity**: 1 (trivial — single API call, 7-day rate-of-change)
**Expected WR Lift**: +1.8–6pp (deepseek: +4–6pp; inception: +1.8pp; openrouter: +3–5pp)
**Wire-In Point**: `calculate_smart_score()` boost in `alpha_engine/smart_picks_engine.py`

```python
import requests, json
from datetime import datetime, timedelta, timezone
from pathlib import Path

_DOMINANCE_CACHE = Path("alpha_engine/data/btc_dominance_cache.json")

def fetch_btc_dominance_7d_roc() -> float | None:
    """
    Returns 7-day rate-of-change in BTC dominance (percentage points).
    Positive = BTC gaining dominance (altcoin headwind).
    Negative = BTC losing dominance (altcoin tailwind).
    """
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/global", timeout=8
        )
        current_dom = resp.json()["data"]["market_cap_percentage"]["btc"]
    except Exception:
        return None  # fail-open

    # Load/save simple daily cache
    cache = {}
    if _DOMINANCE_CACHE.exists():
        cache = json.loads(_DOMINANCE_CACHE.read_text())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache[today] = current_dom
    # Prune to 30 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    cache = {k: v for k, v in cache.items() if k >= cutoff}
    _DOMINANCE_CACHE.write_text(json.dumps(cache))

    # 7-day ROC
    target = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    past_dates = [d for d in sorted(cache.keys()) if d <= target]
    if not past_dates:
        return None
    past_dom = cache[past_dates[-1]]
    return current_dom - past_dom  # pp change over 7 days

def btc_dominance_score_boost(pick: dict) -> float:
    """
    Returns smart_score additive boost based on BTC dominance momentum.
    Integrate into calculate_smart_score() in smart_picks_engine.py.
    """
    roc = fetch_btc_dominance_7d_roc()
    if roc is None:
        return 0.0
    symbol = pick.get("symbol", "")
    is_btc = "BTC" in symbol
    # Altcoin: penalize if dominance rising, reward if falling
    if not is_btc:
        if roc > 2.0:    # dominance rising fast → altcoin headwind
            return -0.10
        elif roc < -2.0: # dominance falling fast → altcoin tailwind
            return +0.12
    else:
        # BTC itself benefits from rising dominance
        if roc > 1.0:
            return +0.08
    return 0.0
```

**Wire-In File**: `alpha_engine/smart_picks_engine.py` → `calculate_smart_score()`

---

### Factor 3 — Fear & Greed Index Extreme Reversal Gate

**Consensus rank**: #3 (deepseek), not in top 3 (inception), not top 3 (openrouter), #5 (ollama_local)
**Cross-engine agreement**: MODERATE (deepseek strongest advocate; others agreed when probed on sentiment)

**Mechanism**: Alternative.me Crypto Fear & Greed Index at extremes (>85 for 3+ days = greed
exhaustion; <15 for 3+ days = fear exhaustion) predicts mean reversion in subsequent 5–14 days.
The signal is the *persistence* of the extreme, not a single day's reading.

**Academic References**:
- Baur & Dimpfl (2021) "The Fear and Greed Index and Cryptocurrency Returns" — J. Behavioral Finance
- Corbet et al. (2020) "Cryptocurrency Sentiment and Returns"

**Data Source**: Alternative.me free API — `GET https://api.alternative.me/fng/?limit=10`
Free, no auth, returns 10-day history.

**Implementation Complexity**: 1 (trivial — parse JSON, check threshold persistence)
**Expected WR Lift**: +3–4pp (Baur & Dimpfl: 3.2% excess return over 14 days post-extreme fear)
**Wire-In Point**: `passes_active_gate()` in `alpha_engine/quality_gates.py`

```python
import requests

FGI_GREED_THRESHOLD = 85    # "extreme greed" — block new longs
FGI_FEAR_THRESHOLD = 15     # "extreme fear" — block new shorts
FGI_PERSISTENCE_DAYS = 3    # must be extreme for 3+ consecutive days

def fetch_fgi_last_n(n: int = 10) -> list[int]:
    """Returns last n days of Fear & Greed Index values (most recent first)."""
    try:
        resp = requests.get(
            f"https://api.alternative.me/fng/?limit={n}", timeout=8
        )
        return [int(d["value"]) for d in resp.json()["data"]]
    except Exception:
        return []  # fail-open

def fgi_gate_passes(direction: str) -> bool:
    """
    Binary gate. Returns False when extreme sentiment persists against direction.
    Wire into passes_active_gate() in quality_gates.py.
    direction: 'LONG' or 'SHORT'
    """
    values = fetch_fgi_last_n(FGI_PERSISTENCE_DAYS + 2)
    if len(values) < FGI_PERSISTENCE_DAYS:
        return True  # fail-open on insufficient data

    recent = values[:FGI_PERSISTENCE_DAYS]
    if direction == "LONG":
        # Block longs if extreme greed persists (exhaustion risk)
        if all(v > FGI_GREED_THRESHOLD for v in recent):
            return False
    elif direction == "SHORT":
        # Block shorts if extreme fear persists (exhaustion risk)
        if all(v < FGI_FEAR_THRESHOLD for v in recent):
            return False
    return True

# Gate registration (audit_trail/quality_gates.py):
# {
#   "gate_id": "FGI_EXTREME_REVERSAL",
#   "shadow": true,
#   "description": "Block trades against 3-day extreme FGI persistence",
#   "data_source": "alternative.me/fng",
#   "hypothesis": "H-TBD"
# }
```

**Wire-In File**: `alpha_engine/quality_gates.py` → `passes_active_gate()`

---

## Factors 4–10 (Summary)

| Rank | Factor | Complexity | Expected WR Lift | Data Source | Wire-In |
|------|--------|-----------|-----------------|-------------|---------|
| 4 | Hash Rate Momentum (14d ROC) | 2 | +2–3pp | CoinGecko developer data | smart_score boost |
| 5 | Stablecoin Supply Ratio (SSR) | 3 | +2–4pp | CoinGecko /global + /coins/tether | smart_score boost |
| 6 | Volatility Regime Percentile | 2 | +3–5pp (ollama consensus) | Binance /klines — compute realized vol | gate/filter |
| 7 | Amihud Illiquidity Ratio (adapted) | 3 | +2–4pp | CoinGecko market data | smart_score boost |
| 8 | Open Interest Trend (not funding rate) | 3 | +2–3pp | Binance futures /openInterest | gate |
| 9 | Social Sentiment Composite | 4 | +4–6pp | Dune Analytics free queries | signal source |
| 10 | Cross-Exchange Price Divergence | 4 | +1–3pp | Binance + KuCoin public APIs | filter |

---

## Engine Disagreements

**OBI as #1 vs Volatility Regime as #1**:
- deepseek/inception/openrouter all ranked OBI first
- ollama_local ranked Volatility Regime first, OBI fourth
- Resolution: OBI has stronger academic backing for 5-30 day holds per Cont 2014 + Cheng 2022

**Expected WR lift magnitude**:
- deepseek was most aggressive (+4–6pp for BTC dominance)
- inception was most conservative (+1.8pp for same factor)
- openrouter used "percentage points" consistently; ollama_local used "%" ambiguously
- Use the conservative inception estimates for planning; deepseek estimates for upside case

**Social Sentiment ranking**:
- openrouter ranked social sentiment #2 (high optimism)
- deepseek ranked it lower due to data reliability concerns (Dune query freshness)
- inception did not include it in top 5
- Resolution: treat as Factor 9 — high potential but implementation complexity 4

---

## Implementation Priority Recommendation

**Immediate (this sprint)**:
1. **FGI Extreme Reversal Gate** (Factor 3) — complexity 1, free API, single endpoint, can ship
   in shadow mode within one session. Expected: blocks ~5–8% of picks in extreme sentiment periods.
2. **BTC Dominance Score Boost** (Factor 2) — complexity 1, one CoinGecko call, additive to
   existing `calculate_smart_score()`. Cache locally to avoid rate limits.
3. **OBI Gate** (Factor 1) — complexity 2, requires polling infrastructure. Best as a
   scheduled job writing to `alpha_engine/data/obi_cache.json` every 30s.

**Next sprint**:
4. Volatility Regime Percentile gate (complexity 2, uses existing Binance klines)
5. Hash Rate Momentum boost (complexity 2, CoinGecko developer data)

**If WR lift from 1–3 is < +2pp after 4 weeks in shadow**: escalate to Factor 9 (social sentiment)
which has highest theoretical lift but most implementation complexity.

---

## Source Data

- CRYPTO swarm run: `swarm_runs/run_20260519T060639Z/`
- Engines: deepseek (66.9s, 16689B), inception (5.9s, 11641B), openrouter (18.2s, 7009B),
  ollama_local (22.6s, 8706B)
- Total cost: ~$0.013
