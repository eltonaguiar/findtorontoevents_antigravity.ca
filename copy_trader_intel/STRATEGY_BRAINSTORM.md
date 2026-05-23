# Copy Trader Reverse Engineering — Master Brainstorm
**Generated:** 2026-03-19 by 4-agent research team  
**Based on:** Audit of `copy_trader_intel/`, `alpha_engine/`, `genome/` codebases

---

## Current System Snapshot

| Component | File | Status |
|---|---|---|
| Multi-platform scraper | `main.py`, `unified_trader_research.py` | ✅ Working |
| OKX API scraper | `okx_scraper.py` | ✅ Working (no auth) |
| Hyperliquid scraper | `hyperliquid_scraper.py` | ✅ Working (no auth) |
| Strategy DNA extractor | `strategy_reverse_engineer.py` | ✅ Working |
| Clone pick generator | `strategy_clone_generator.py` | ✅ Working |
| Performance tracker | `performance_tracker.py` | ✅ Working |
| Pairwise agreement matrix | — | ❌ Not built |
| Per-trader equity curves | — | ❌ Not built |
| Market-regime filter | — | ❌ Not built |
| Enrichment pipeline | — | ❌ Designed in ENRICHMENT_RESEARCH.md |

### Core Gap: `MIXED_ADAPTIVE` Problem
The most common result from `strategy_reverse_engineer.py` is `entry_style: MIXED_ADAPTIVE`
— a catch-all for "we couldn't find a dominant single-timeframe entry pattern."  
Currently > 60% of traders get this label. The ideas below fix this systematically.

---

## LAYER 1 — Entry Condition Extraction Improvements

*These improve what we learn about HOW a trader enters, so clones are more accurate.*

### 1.1 Multi-Timeframe Alignment Score (MTF Score) ⭐ HIGH VALUE

**Problem:** We only analyze 1h klines. Most skilled traders align 3 timeframes simultaneously.

**Implementation:** At each entry timestamp, fetch 15m + 1h + 4h from Binance. Compute EMA(20/50) trend direction and RSI-zone per TF. Sum into MTF score (-6 to +6).

```python
def compute_mtf_score(symbol, entry_ts_ms):
    scores = {}
    for interval, lookback in [("15m", 200), ("1h", 100), ("4h", 50)]:
        klines = binance_klines(symbol, interval, lookback, endTime=entry_ts_ms + 60_000)
        closes = [float(k[4]) for k in klines]
        ema20 = compute_ema(closes, 20)
        ema50 = compute_ema(closes, 50)
        rsi = compute_rsi(closes)
        trend_dir = 1 if ema20 > ema50 else -1
        momentum = 1 if rsi > 55 else (-1 if rsi < 45 else 0)
        scores[interval] = trend_dir + momentum
    total = sum(scores.values())
    return {"mtf_total": total, "mtf_aligned": abs(total) >= 4,
            "mtf_direction": "LONG" if total > 0 else "SHORT"}
```

**New entry labels:** `MULTI_TF_ALIGNMENT_LONG`, `MULTI_TF_ALIGNMENT_SHORT` for entries where score ≥ |4|.
**Estimated fix rate:** Would reclassify ~30% of `MIXED_ADAPTIVE` entries.

---

### 1.2 Pullback-to-Structure Detection ⭐ HIGH VALUE

**Problem:** "EMA bounce" and "support touch then enter trend direction" is invisible to current binary BREAKOUT check.

**Implementation:** At entry: compute EMA20, EMA50, EMA200, ATR. If price within 0.5×ATR of EMA and trend direction is aligned = `EMA_PULLBACK`. Check if previous candle closed below EMA but entry opens above = `EMA_RECLAIM`.

```python
def detect_pullback_entry(entry_price, closes, highs, lows):
    ema20 = compute_ema(closes[:-1], 20)
    ema50 = compute_ema(closes[:-1], 50)
    atr = compute_atr(highs[:-1], lows[:-1], closes[:-1])
    if atr == 0: return "NONE"
    
    dist_ema20 = abs(entry_price - ema20) / atr
    prior_dist_ema20 = abs(closes[-2] - ema20) / atr
    trend_bullish = ema20 > ema50
    
    if trend_bullish and dist_ema20 < 0.5 and prior_dist_ema20 > 0.5:
        return "EMA20_PULLBACK_LONG"
    if trend_bullish and abs(entry_price - ema50) / atr < 0.6:
        return "EMA50_PULLBACK_LONG"
    return "NONE"
```

**Estimated fix rate:** Reclassifies ~20% of `MIXED_ADAPTIVE`.

---

### 1.3 Funding Rate Fade / Alignment Context ⭐ HIGH VALUE

**Problem:** No funding rate context. Traders who "fade extreme funding" are completely different personalities from "trend riders" — but they look identical in the current system.

**API:** Hyperliquid: `POST /info {type: fundingHistory, coin: X}`  
Binance: `GET /fapi/v1/fundingRate` (public, no auth)

```python
def get_funding_context(coin, entry_ts_ms, trade_dir):
    data = hl_post({"type": "fundingHistory", "coin": coin,
                    "startTime": entry_ts_ms - 28_800_000, "endTime": entry_ts_ms})
    if not data: return None
    rates = sorted(data, key=lambda x: x["time"])
    recent_rate = float(rates[-1]["fundingRate"]) if rates else 0
    regime = ("EXTREME_NEGATIVE" if recent_rate < -0.0003 else
              "MILDLY_NEGATIVE"  if recent_rate < -0.00005 else
              "MILDLY_POSITIVE"  if recent_rate < 0.0003 else
              "EXTREME_POSITIVE" if recent_rate >= 0.0003 else "NEUTRAL")
    is_fade = ((trade_dir == "LONG" and "NEGATIVE" in regime) or
               (trade_dir == "SHORT" and "POSITIVE" in regime))
    return {"funding_regime": regime, "is_funding_fade": is_fade,
            "funding_at_entry": recent_rate}
```

**New archetypes:** `FUNDING_CONTRARIAN` (>60% fades), `TREND_WITH_FUNDING`. Both are highly clonable: when funding hits extreme levels, generate that trader's expected direction.

---

### 1.4 Open Interest Surge Detection (MEDIUM-HIGH)

**API:** `GET https://fapi.binance.com/fapi/v1/openInterestHist?symbol=X&period=1h&limit=48` (public)

**Signal:** OI Z-score at entry time. If trader consistently enters on `SURGE` (z > 1.5) = momentum follower. If enter on `CONTRACTION` = range-bound fader.

```python
def get_oi_context(symbol, entry_ts_ms):
    data = requests.get("https://fapi.binance.com/fapi/v1/openInterestHist",
                        params={"symbol": symbol, "period": "1h",
                                "limit": 48, "endTime": entry_ts_ms}).json()
    if not data or len(data) < 5: return None
    oi = [float(d["sumOpenInterest"]) for d in data]
    deltas = [(oi[i]-oi[i-1])/oi[i-1]*100 for i in range(1, len(oi))]
    mean_d, std_d = statistics.mean(deltas), statistics.stdev(deltas) or 0.001
    latest_delta = (oi[-1] - oi[-2]) / oi[-2] * 100
    z = (latest_delta - mean_d) / std_d
    return {"oi_delta_pct": round(latest_delta, 4), "oi_zscore": round(z, 2),
            "oi_regime": "SURGE" if z > 1.5 else "CONTRACTION" if z < -1.5 else "NORMAL"}
```

---

### 1.5 VWAP Displacement + OBV Slope (HIGH)

**Problem:** No institutional reference levels — VWAP is THE intraday level market makers and algos use.

**Signal:** `displacement = (entry_price - VWAP) / ATR`. Trader always entering within 0.3 ATR of VWAP = institutional-style execution. OBV slope confirms whether volume supports the move.

```python
def compute_vwap_context(klines, entry_price):
    typical = [(float(k[2])+float(k[3])+float(k[4]))/3 for k in klines]
    vols = [float(k[5]) for k in klines]
    vwap = sum(t*v for t,v in zip(typical, vols)) / sum(vols)
    closes = [float(k[4]) for k in klines]
    atr = compute_atr([float(k[2]) for k in klines],
                      [float(k[3]) for k in klines], closes)
    displacement = (entry_price - vwap) / (atr or 0.001)
    # OBV slope over last 5 candles
    obv, obv_vals = 0, []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        obv += vols[i] if d > 0 else (-vols[i] if d < 0 else 0)
        obv_vals.append(obv)
    obv_slope = (obv_vals[-1] - obv_vals[-5]) / 5 if len(obv_vals) >= 5 else 0
    return {"vwap_displacement_atr": round(displacement, 2), "entry_above_vwap": entry_price > vwap,
            "obv_slope_direction": "RISING" if obv_slope > 0 else "FALLING"}
```

---

### 1.6 Liquidation Cascade Entry Detection (MEDIUM)

**Signal:** If entry is preceded (within 10 min) by an oversized wick candle (wick > 2.5x ATR on opposite side), trader is exploiting a liquidation flush. Label: `LIQUIDATION_CASCADE_FADE`.

**Data source:** Binance 5m klines + optional Hyperliquid `userFills` liquidation flag.

---

### 1.7 Market Session Win-Rate Decomposition ⭐ HIGH VALUE

**Problem:** A trader with 70% win rate on Asian session and 45% on NY session will only get cloned at the right time if we track this.

**Sessions:** Asian (00:00–08:00 UTC), London (07:00–14:00), NY (13:00–21:00), Overlap (13:00–16:00)

```python
SESSION_RANGES = {"ASIAN": (0,8), "LONDON": (7,14), "NY": (13,21), "OVERLAP": (13,16)}

def classify_session(hour_utc):
    for name, (start, end) in SESSION_RANGES.items():
        if start <= hour_utc < end:
            return name
    return "DEAD"

def decompose_session_performance(trades):
    by_session = defaultdict(lambda: {"trades": [], "wins": 0})
    for t in trades:
        s = classify_session(datetime.fromtimestamp(t["open_time"]/1000, tz=timezone.utc).hour)
        by_session[s]["trades"].append(t)
        if float(t["pnl"]) > 0: by_session[s]["wins"] += 1
    return {s: {"wr": v["wins"]/len(v["trades"]), "n": len(v["trades"])}
            for s, v in by_session.items() if v["trades"]}
```

**Down-stream use:** Clone picks for this trader only fire during their best session window.

---

### 1.8 ML Clustering for Entry Archetype Discovery (MEDIUM, future)

Instead of hard-coded entry style rules, collect a feature vector per trade:
```
[mtf_score, vwap_displacement, funding_regime_encoded, oi_zscore,
 rsi_at_entry, atr_ratio, hour_utc_encoded, dow_encoded, hold_hours, pnl_pct]
```
Run K-Means (k=6) or HDBSCAN on all traders' combined trade vectors.
Each cluster = a natural entry archetype. Name clusters by their centroid feature profile.
This auto-discovers patterns without human-coded rules.

---

## LAYER 2 — Consensus & Agreement Tracking Improvements

*These improve how we decide WHEN multiple traders agreeing should boost confidence.*

### 2.1 Pairwise Agreement Matrix ⭐ HIGH VALUE

**Problem:** We know 3 traders agree on SOLUSDT LONG — but we don't know if *these particular 3* have historically agreed and been right together.

**New file:** `data/pairwise_agreements.json` — keyed on `"traderA|traderB"`, tracks `n_agreed`, `n_wins`, `joint_win_rate`.

```python
def update_pairwise(closed_trade, pair_matrix):
    traders = closed_trade.get("confirming_traders", [])
    won = closed_trade["outcome"] == "TP"
    for a, b in combinations(sorted(traders), 2):
        key = f"{a}|{b}"
        if key not in pair_matrix:
            pair_matrix[key] = {"n_agreed": 0, "n_wins": 0, "joint_win_rate": 0.0}
        pair_matrix[key]["n_agreed"] += 1
        if won: pair_matrix[key]["n_wins"] += 1
        pair_matrix[key]["joint_win_rate"] = pair_matrix[key]["n_wins"] / pair_matrix[key]["n_agreed"]
    return pair_matrix

def get_pairwise_lift(traders, pair_matrix, baseline_wr=0.55):
    lifts = []
    for a, b in combinations(sorted(traders), 2):
        entry = pair_matrix.get(f"{a}|{b}")
        if entry and entry["n_agreed"] >= 5:
            lift = entry["joint_win_rate"] / baseline_wr
            lifts.append(min(lift, 1.5))  # cap at 1.5x
    return sum(lifts)/len(lifts) if lifts else 1.0

# Usage: adjusted_confidence = raw_confidence * pairwise_lift
# whale_2370roi + hl_titan_88 have 75% joint WR vs 55% baseline → lift = 1.36x
```

---

### 2.2 Exponential Time-Decayed Trust Score ⭐ HIGH VALUE

**Problem:** A trader who was great 6 months ago but has been losing recently still shows 68% win rate.

**Key math:** $\text{EWM WR} = \frac{\sum w_i \cdot \mathbf{1}[\text{win}_i]}{\sum w_i}$ where $w_i = e^{-\lambda \cdot \text{days\_ago}}$, $\lambda = 0.03$ (half-life ≈ 23 days)

```python
DECAY_LAMBDA = 0.03

def compute_ewm_trust(trade_history):
    now = datetime.utcnow()
    ww = tw = 0.0
    for t in trade_history:
        days_ago = (now - datetime.fromisoformat(t["closed_at"].replace("Z",""))).days
        w = math.exp(-DECAY_LAMBDA * days_ago)
        ww += w * (1 if t["outcome"] == "TP" else 0)
        tw += w
    ewm_wr = ww / tw if tw > 0 else 0.5
    recent_wins = sum(1 for t in trade_history[:5] if t["outcome"] == "TP")
    momentum = (recent_wins - 2.5) / 2.5  # -1 to +1
    penalty = 0.85 if momentum < -0.3 else 1.0
    return {"ewm_win_rate": round(ewm_wr, 4), "recency_momentum": round(momentum, 4),
            "effective_trust": round(ewm_wr * penalty, 4)}
```

**Example:** Trader with 68% all-time but 40% recent 30-day → effective_trust = 0.39 (vs misleadingly showing 0.68 today)

---

### 2.3 Cross-Platform Identity Deduplication (HIGH)

**Problem:** On-chain addresses (Hyperliquid, dYdX, GMX, Copin) are the same across platforms — one whale voting multiple times inflates consensus count.

**Layer 1 (easy):** Exact wallet address match across DEX platforms.
**Layer 2 (hard):** Behavioral fingerprint on CEX platforms (same symbol, same direction, within 5min, ±15% size).

```python
def deduplicate_picks_by_identity(active_picks, identity_map):
    """Reduce multi-platform same-address picks to max 1 vote."""
    canonical_votes = {}
    for pick in active_picks:
        canonical = identity_map.get(pick["source_trader"], pick["source_trader"])
        key = f"{canonical}|{pick['symbol']}|{pick['direction']}"
        if key not in canonical_votes:
            canonical_votes[key] = pick
        # else: skip — same identity already voting
    return list(canonical_votes.values())
```

---

### 2.4 Fuzzy Consensus Scoring (4-Dimension Agreement) (HIGH)

**Problem:** Current consensus = "same symbol + same direction." Too loose for quality signals.

**4-Factor Score:**
| Factor | Weight | Scoring |
|---|---|---|
| Symbol match | 35% | Binary 0 or 1 |
| Entry zone overlap | 30% | Score = 1 - (entry_diff% / 2%) |
| Timing proximity | 20% | Score = 1 - (hours_apart / 4h) |
| Leverage tier match | 15% | 1.0 if same tier, 0.3 if different |

**Threshold:** Only flag as consensus if total score ≥ 0.65

**Concrete example:**
```
Trader A: SOLUSDT LONG @ 185.50, 10x, entered 12:00
Trader B: SOLUSDT LONG @ 187.20, 8x,  entered 14:30

Symbol:     1.0 × 0.35 = 0.35
Entry zone: |187.20-185.50|/185.50 = 0.92% < 2% → 1.0 × 0.30 = 0.30
Timing:     2.5h → 0.375 × 0.20 = 0.075... actually: (1 - 2.5/4) = 0.375 → 0.075
Leverage:   both 5-20x → 1.0 × 0.15 = 0.15
Total: 0.35+0.30+0.075+0.15 = 0.875 → STRONG consensus ✓
```

---

### 2.5 Anti-Consensus Conflict Signal (MEDIUM-HIGH)

**When:** 2+ high-trust traders (effective_trust > 0.60) hold OPPOSING positions on same symbol.

**Action:** Reduce any existing consensus confidence on that symbol by 40%. Emit `CONFLICT` alert.

```python
def detect_conflicts(active_picks, trust_scores):
    by_symbol = defaultdict(lambda: {"LONG": [], "SHORT": []})
    for pick in active_picks:
        trust = trust_scores.get(pick["source_trader"], {}).get("effective_trust", 0.0)
        if trust >= 0.60:
            by_symbol[pick["symbol"]][pick["direction"]].append(
                {"trader": pick["source_trader"], "trust": trust})
    conflicts = []
    for sym, sides in by_symbol.items():
        if sides["LONG"] and sides["SHORT"]:
            conflicts.append({"symbol": sym, "long_traders": sides["LONG"],
                               "short_traders": sides["SHORT"],
                               "recommended_action": "AVOID_NEW_ENTRIES"})
    return conflicts
```

---

### 2.6 Early Mover Advantage Tracking (MEDIUM)

**Insight:** When a consensus forms, the FIRST trader to enter is usually the smartest (or has the best signal).

**Track:** For each consensus cluster, tag which trader entered first. Over time, track if "early movers" have higher win rates than "late movers" on the same consensus.

**Implementation:** Add `entry_rank_in_consensus: 1|2|3` to each pick. Track per-trader: `avg_entry_rank`, `win_rate_when_first`, `win_rate_when_late`. Weight first-mover opinion more heavily.

---

### 2.7 Tiered Trust Weighting for Consensus (HIGH)

**Problem:** A $50M Hyperliquid whale agreeing with a Bybit copy-follower shouldn't count equally.

**Tier weights:**
```python
PLATFORM_TIER_WEIGHTS = {
    "hyperliquid_whale":  1.5,   # large independent on-chain traders
    "hyperliquid":        1.2,   # standard HL traders
    "okx":                1.1,   # OKX copy trading
    "bitget_veteran":     1.1,   # >365 days on platform
    "bitget":             0.9,   # standard Bitget
    "bybit":              0.8,   # less verified
    "bingx":              0.7,
    "dex_clone":          0.6,   # strategy clones (not direct positions)
}

def weighted_consensus_score(agreeing_picks, trust_scores, tier_weights):
    total_weight = 0.0
    weighted_trust = 0.0
    for pick in agreeing_picks:
        tier = pick.get("platform_tier", pick.get("platform", "unknown"))
        tw = tier_weights.get(tier, 1.0)
        t = trust_scores.get(pick["source_trader"], {}).get("effective_trust", 0.5)
        weighted_trust += t * tw
        total_weight += tw
    return weighted_trust / total_weight if total_weight > 0 else 0.0
```

---

### 2.8 Historical Quorum Accuracy Tracker (HIGH LONG-TERM VALUE)

**What it builds:** "When exactly N traders agreed on symbol X with direction D — how often were they right?"

**Data structure:** `quorum_history.json` — keyed on `(symbol, direction, n_agreeing)` → rolling accuracy stats.

**Use:** If `BTC LONG n=3` has historically been 75% accurate but `ETH LONG n=2` is only 52% → different confidence floors per quorum count and symbol.

---

## LAYER 3 — Per-Trader Portfolio Simulation

*Each top trader gets their own independent portfolio, tracked forward with compound equity.*

### 3.1 Per-Trader Equity Curve Simulator ⭐ HIGH VALUE

**New file:** `data/trader_equity_curves.json` — one equity series per trader.

```python
class TraderPortfolio:
    def __init__(self, label, starting=10_000, allocation_frac=0.10):
        self.label = label
        self.equity = starting
        self.peak = starting
        self.max_dd = 0.0
        self.equity_curve = [starting]
        self.trades_log = []

    def apply_trade(self, pct_outcome, leverage=1.0):
        position = self.equity * self.allocation_frac
        raw_pnl = position * leverage * pct_outcome
        fee = position * leverage * 0.001  # 0.1% round-trip
        net_pnl = raw_pnl - fee
        self.equity += net_pnl
        self.equity_curve.append(round(self.equity, 2))
        self.peak = max(self.peak, self.equity)
        dd = (self.equity - self.peak) / self.peak
        self.max_dd = min(self.max_dd, dd)
        self.trades_log.append({"net_pnl": net_pnl, "equity": self.equity})

    def sharpe(self):
        import statistics
        returns = [self.equity_curve[i]/self.equity_curve[i-1]-1
                   for i in range(1, len(self.equity_curve))]
        if len(returns) < 2: return 0.0
        mean_r = statistics.mean(returns)
        std_r = statistics.stdev(returns)
        return (mean_r / std_r * (365**0.5)) if std_r > 0 else 0.0

    def calmar(self):
        if not self.max_dd: return 0.0
        annual_return = (self.equity/self.equity_curve[0]) - 1
        return annual_return / abs(self.max_dd)
```

**Dashboard output:** Timeline chart per trader. Sort by Calmar ratio, not win rate.

---

### 3.2 Kelly Criterion Position Sizing ⭐ HIGH VALUE

**Formula:** $f^* = \frac{W \cdot R - L}{R}$ where $W$ = win rate, $L = 1-W$, $R = \text{avg\_win} / \text{avg\_loss}$

Use quarter-Kelly ($0.25 \cdot f^*$) to avoid over-leverage. Clamp to [2%, 20%].

```python
def kelly_fraction(win_rate, avg_win_pct, avg_loss_pct, kelly_mult=0.25):
    if avg_loss_pct == 0 or win_rate <= 0: return 0.02
    R = abs(avg_win_pct / avg_loss_pct)
    L = 1.0 - win_rate
    full_kelly = (win_rate * R - L) / R
    if full_kelly <= 0: return 0.02  # No edge → minimum size
    return float(max(0.02, min(0.20, kelly_mult * full_kelly)))

# Recalibrate every 10 forward-tested trades using rolling 50-trade window
```

**Example:** Bg-ATM: 90.3% WR, avg_win=0.5%, avg_loss=-0.36%  
→ R = 1.39, full_kelly = (0.903×1.39 - 0.097)/1.39 = 0.833  
→ quarter-Kelly = 20.8% → clamped to **20%** of equity per trade

---

### 3.3 Coin-Conditional Edge Matrix + Wilson Score (HIGH)

**Problem:** Trader A might be 90% on BTC but 50% on altcoins. We shouldn't clone their altcoin trades.

**Wilson lower bound** (95% CI for win rate given limited samples):
$$W_{lower} = \frac{\hat{p} + z^2/2n - z\sqrt{\hat{p}(1-\hat{p})/n + z^2/4n^2}}{1 + z^2/n}$$

```python
def wilson_lower(p_hat, n, z=1.96):
    if n == 0: return 0.0
    center = p_hat + z**2 / (2*n)
    spread = z * ((p_hat*(1-p_hat)/n) + z**2/(4*n**2))**0.5
    return (center - spread) / (1 + z**2/n)

def build_coin_edge_matrix(coin_breakdown):
    matrix = {}
    for entry in coin_breakdown:
        w_lower = wilson_lower(entry["win_rate"], entry["trades"])
        sample_weight = min(math.log1p(entry["trades"]) / math.log1p(50), 1.0)
        matrix[entry["coin"]] = {
            "raw_wr": entry["win_rate"],
            "wilson_lower": round(w_lower, 4),
            "edge_score": round(w_lower * sample_weight, 4),
            "tradeable": w_lower >= 0.55
        }
    return matrix
```

**Only generate clone picks for coins where `tradeable == True`.**

---

### 3.4 Market Regime Classifier + Trader Regime Suitability (HIGH)

**4 regime types:**
- `STRONG_TREND_UP` — ADX > 25, price > EMA20 > EMA50
- `STRONG_TREND_DOWN` — ADX > 25, price < EMA20 < EMA50
- `RANGING` — ADX < 20, oscillating
- `VOLATILE_CHOP` — ATR/price > 2.5% AND ADX < 25

**Per-trader regime tagging:** Tag each historical trade with regime at entry time. Compute per-regime win rate. At runtime:  
`regime_suitability = regime_wr - overall_wr`  
→ Only activate trader if `regime_suitability >= -0.05` (less than 5% worse than their baseline in this regime).

**Enables:** "Turn off swing traders in choppy markets, turn off mean-reversion traders in strong trends."

---

### 3.5 Trader Correlation Matrix + Diversification Score (HIGH)

**Problem:** Some traders are highly correlated (their P&L moves together daily) — allocating to both = redundancy, not diversification.

**Implementation:** Align all traders' daily forward-test P&L onto shared timeline → Pearson correlation matrix → cluster traders with |ρ| > 0.70 → from each cluster, keep only the highest-Sharpe member.

**Diversification score:** $D = 1 - \frac{\sum_{i\ne j} |\rho_{ij}|}{N(N-1)}$ — target D > 0.6

---

### 3.6 Conviction Scoring — Graduated Position Sizing (MEDIUM-HIGH)

Instead of binary take/skip, score each pick 0–100 across 4 sub-factors (25 pts each):

| Sub-factor | Signal |
|---|---|
| Coin edge score | Wilson lower bound for this coin |
| Regime suitability | Regime win rate delta |
| Session timing | Overlap with trader's peak UTC hours |
| Momentum alignment | RSI/VWAP aligns with trader's direction bias |

**Position size modifier:** $size = \text{kelly\_size} \times \sqrt{conviction/100}$

A 100% conviction trade gets full Kelly. A 40% conviction gets 63% of Kelly.

---

### 3.7 ATR-Dynamic TP/SL (MEDIUM)

**Problem:** Fixed avg TP/SL percentages ignore current volatility. A 0.5% TP is too tight on an ETHUSDT 1-hour range of 2%.

**Implementation:** Compute ATR(14) on 1h at entry time. Set:
- TP = entry ± `tp_atr_mult × ATR` (default 1.5)
- SL = entry ∓ `sl_atr_mult × ATR` (default 0.8)

Where multipliers are derived from the trader's historical avg_win_pct / ATR_at_entry ratio across their closed trades.

---

### 3.8 Meta-Portfolio: Sharpe-Weighted Capital Allocation Across Traders (HIGH)

**Last step:** Treat each trader's portfolio as an "asset." Allocate a total capital pool across traders using their rolling 90-day Sharpe ratios as weights (normalized to sum to 1.0).

```python
def meta_portfolio_weights(trader_portfolios):
    sharpes = {label: max(p.sharpe(), 0.01) for label, p in trader_portfolios.items()}
    total = sum(sharpes.values())
    return {label: s/total for label, s in sharpes.items()}

# Result: "Allocate 35% to whale_2370roi, 28% to Bg-ATM, 20% to CrowleyZhou, ..."
```

---

## LAYER 4 — Data Enrichment Pipeline

*Add market context fields to each pick so we understand WHY a signal fired.*

### 4.1 Minimum Viable Enrichment Set (all FREE, no auth)

| Signal | API | What it tells us |
|---|---|---|
| Aggregate funding rate | Binance `GET /fapi/v1/fundingRate`, OKX, Bybit | Crowding direction, contrarian setups |
| OI 24h % change | Binance `GET /fapi/v1/openInterestHist` | New money entering vs leaving |
| Fear & Greed Index | `https://api.alternative.me/fng/?limit=1` | Macro sentiment regime |
| Deribit put/call ratio | `GET https://www.deribit.com/api/v2/public/get_book_summary_by_currency` | Institutional options bias |
| Deribit DVOL (crypto VIX) | `GET https://www.deribit.com/api/v2/public/get_volatility_index_data` | IV regime — high IV = don't chase |

**New `enrichment` block in `active_picks.json`:**
```json
{
  "enrichment": {
    "funding_rate_pct": -0.0024,
    "funding_regime": "EXTREME_NEGATIVE",
    "oi_24h_change_pct": 5.2,
    "fear_greed_index": 28,
    "fear_greed_label": "Fear",
    "btc_put_call_ratio": 0.72,
    "deribit_dvol": 61.3,
    "enrichment_ts": "2026-03-19T14:00:00Z"
  }
}
```

### 4.2 Secondary Sources (free tier / free API key)

| Source | What | Threshold |
|---|---|---|
| Coinglass (free key) | Liquidation heatmap, long/short ratio | Free registration required |
| Glassnode (free tier) | SOPR (on-chain capitulation signal) | Tier 1 free |
| GeckoTerminal | DEX buy/sell pressure on token | Fully free |
| DexScreener | Pool-level buy ratio, volume spikes | Fully free |
| CFTC COT reports | CME institutional BTC/ETH positioning | Free, weekly at cftc.gov |

### 4.3 Enrichment Pipeline Architecture

```
On new pick generated:
  → [async] fetch_funding_context(symbol)      ~ 200ms
  → [async] fetch_oi_context(symbol)           ~ 300ms
  → [cached] get_fear_greed_index()            ~ 100ms (cache 1h)
  → [cached] get_deribit_context(coin)         ~ 400ms (cache 30min)
  → Merge all into pick["enrichment"] dict
  → Write updated pick to active_picks.json
  → Score pick's "enrichment_alignment": +1 for each signal confirming direction
```

**Enrichment alignment score:** Count how many enrichment signals support the trade direction. A pick with funding_fade + fear + low-dvol + oi_surge all confirming = `enrichment_alignment: 4/4` = highest quality entry.

---

## LAYER 5 — New Monitoring Features

### 5.1 Active Position Mirror Tracker
**For each open position from a top trader:** Track price distance to TP/SL in real-time. Alert when approaching (within 20% of target). Track "time in trade" — if trader holds longer than their historical median, flag as "conviction hold."

### 5.2 Trader Regime Report Card
Daily report: for each tracked trader, show their last 10 trades tagged with: entry style, funding at entry, regime, session, outcome. Human-readable table that lets you spot patterns visually before the algorithms do.

### 5.3 New Trader Discovery Pipeline
Current system uses a fixed `SEED_WALLETS` list. Automate discovery:
1. Daily: fetch fresh OKX leaderboard, filter new traders > 90% win rate for 30+ days
2. Daily: fetch HL leaderboard, filter wallets with > 200% 60-day ROI and < 30% drawdown
3. Auto-onboard: run 30-day fill analysis, generate DNA profile, add to `SEED_WALLETS` if edge score > 60

### 5.4 Symbol-pair Agreement Heatmap
**New dashboard view:** Matrix heatmap. Rows = traders. Columns = symbols. Color intensity = current open position conviction. Instantly shows: what are the most "agreed upon" open positions across all traders right now?

---

## Implementation Priority Order

| Priority | Feature | Module to create/modify | Estimated complexity |
|---|---|---|---|
| 1 | Pairwise agreement matrix + early mover | New: `pairwise_tracker.py` | Low |
| 2 | EWM trust score with decay | Modify: `performance_tracker.py` | Low |
| 3 | Session win-rate decomp + session filter | Modify: `strategy_reverse_engineer.py` | Low |
| 4 | MTF alignment score at entry | Modify: `strategy_reverse_engineer.py` | Medium |
| 5 | Funding rate context at entry | Modify: `strategy_reverse_engineer.py` | Low |
| 6 | Per-trader equity curves + Kelly sizing | New: `trader_portfolio.py` | Medium |
| 7 | Coin-conditional Wilson edge matrix | Modify: `strategy_clone_generator.py` | Low |
| 8 | Enrichment pipeline (funding, OI, F&G) | New: `enrichment_pipeline.py` | Medium |
| 9 | Anti-consensus conflict detection | Modify: `performance_tracker.py` | Low |
| 10 | Fuzzy 4-dimension consensus scoring | Modify: `main.py` consensus logic | Medium |
| 11 | Market regime classifier + filter | New: `regime_classifier.py` | Medium |
| 12 | Meta-portfolio Sharpe allocation | New: `meta_portfolio.py` | High |
| 13 | OI + VWAP entry context | Modify: `strategy_reverse_engineer.py` | Medium |
| 14 | Cross-platform identity deduplication | New: `identity_dedup.py` | High |
| 15 | ML clustering for entry archetypes | New: `entry_clusterer.py` | High |

---

## Quick Wins (Build This Week)

1. **`pairwise_tracker.py`** — 80 lines of Python, huge signal lift. Start recording pairwise agreement data NOW so it builds up over time.
2. **EWM trust in `performance_tracker.py`** — add `effective_trust` field alongside `win_rate`. 30 lines of math.
3. **Session decompose in `strategy_reverse_engineer.py`** — tag every historical trade with session, add per-session win rate to output. 40 lines.
4. **Fear & Greed + funding in `enrichment_pipeline.py`** — 2 API calls, single JSON file written alongside active_picks.json. 60 lines.
5. **Anti-consensus conflict detector** — scan active_picks for opposing high-trust picks, write `active_conflicts.json`. 50 lines.

These 5 quick wins can be built and tested in a single day and immediately improve signal quality.

---

*All pseudocode in this document is designed to be drop-in compatible with the existing `copy_trader_intel/` module pattern. Existing scrapers remain unchanged — new modules consume and enrich their output.*
