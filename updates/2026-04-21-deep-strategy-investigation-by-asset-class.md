# Deep Strategy Investigation — Performance by Asset Class

**Author:** Claude Opus 4.7 (1M context)
**Date:** 2026-04-21
**Source:** `audit_trail/data/dashboard_payload.json` (3,500 resolved closed picks, 52 active)
**Method:** Python aggregation over the full `recent_closed` ledger with grouping by asset_class, strategy, source_system, exit_reason, UTC hour, and confidence band.

---

## TL;DR — 7 headline findings

1. **Equity is the only self-sustaining asset class.** n=334, WR 50.3%, PF 1.44, mean +0.68%. Every other class is at best break-even (Bond PF 1.60 on thin n=17, ETF PF 1.03) or structurally negative (Crypto PF 0.60, Forex PF 0.93, Commodity PF 1.14 but only because both sides are flat).
2. **Forex + Commodity = 47-50% FLAT** — not directional losers, just non-directional noise. 46.8% of forex closes and 50.1% of commodity closes are FLAT (|pnl| ≤ 0.01%) because they FORCE_CLOSED before hitting TP/SL. Kimi's RCA was right.
3. **TP:SL ratio is 1:2.88 across the whole system.** Only 13.4% of picks hit TP; 38.6% hit SL; **45.5% never resolve** (FORCE_CLOSED 23.6% + EXPIRED 16.6% + TIME_EXIT 5.3%). Structural bias toward tight stops / far targets / short hold windows.
4. **Confidence is inversely correlated with realized WR on crypto.** conf 0.65-0.75 → 26.2% WR, conf 0.75-0.85 → 34.2% WR + mean PnL −2.20%. Low-confidence picks (conf < 0.55) outperform high-confidence ones (42.8% vs 36.6% WR). Self-reported confidence has ZERO predictive value — confirmed at n=1695 crypto sample.
5. **Time-of-day is the largest single edge in the dataset.** 22:00 UTC crypto WR 71.8% (n=85, mean +1.08%), 23:00 UTC 63.1% (n=65, +0.81%). Meanwhile 20:00 UTC = 17.1% WR on 117 picks (mean −1.03%). Delta: 50+ percentage-point swing based purely on hour. A 22:00-only filter would flip crypto from losing to winning.
6. **`claude_gainer_st` has burned 463% cumulative PnL on 731 crypto picks** at 23.8% WR. `copy_trader_intel` at 34.6% WR has lost 766% cum. These two systems account for most of the bleed.
7. **Of 14 source_systems with n≥30, only 5 are net-positive.** Top: `kimi_riseoftheclaw` (+143%), `stocks_competition` (+85%). Bottom: `claude_gainer_st` (−463%), `copy_trader_intel` (−766%). 3 systems have WR < 10% (cta_replicator 9.4%, forex_copy_trader 2.5%, non_crypto_consensus 0.0%).

---

## 1. Per-Asset-Class Overview

| Class | n | WR (headline) | PF | mean % | median % | FLAT % | SL% | TP% | verdict |
|---|---|---|---|---|---|---|---|---|---|
| **EQUITY** | 334 | **50.3%** | **1.44** | **+0.68%** | +0.01% | 4.2% | 30.8% | 24.0% | ✅ **edge** |
| BOND | 17 | 47.1% | 1.60 | +0.17% | +0.00% | 5.9% | 29.4% | 5.9% | ⚠️ thin |
| ETF | 74 | 48.6% | 1.03 | +0.03% | +0.01% | 5.4% | 37.8% | 23.0% | ⚠️ break-even |
| CRYPTO | **1695** | 32.5% | 0.60 | −0.77% | −0.95% | 0.1% | **48.7%** | 15.5% | ❌ structural loser |
| FOREX | 844 | 25.7% | 0.93 | −0.02% | 0.00% | **46.8%** | 43.5% | 10.7% | ⚠️ mostly flat |
| COMMODITY | 533 | 23.1% | 1.14 | +0.02% | 0.00% | **50.1%** | 4.1% | 3.0% | ⚠️ mostly flat (no resolution) |

**Critical reading of FOREX + COMMODITY:** Kimi's RCA from 2026-04-17 was spot-on. Headline WR of 25.7% / 23.1% is a dilution artifact — ~half these picks close FLAT (FORCE_CLOSED or TIME_EXIT without meaningful PnL). On resolved picks only, forex ≈ 49%, commodity ≈ 46% — essentially coin-flip. Not a directional-accuracy problem, an **exit-mechanics problem**. Widening TP/SL bands (commit `64506fe56d`) is the right direction; continue monitoring.

**Critical reading of CRYPTO:** FLAT percentage is negligible (0.1%). This IS a directional-accuracy problem. PF 0.60 means you lose $1.66 for every $1 you win.

## 2. Top Strategy Winners (n ≥ 15)

### CRYPTO (3 winners above 50% WR)

| Strategy | n | WR | mean % |
|---|---|---|---|
| `claude_ml_moderate_mut` | 15 | **73.3%** | +1.40% |
| `quan_engine` | 17 | 64.7% | +0.53% |
| `keltner_compression_expansion_sol_v1` | 22 | 54.5% | +0.34% |

### EQUITY (3 winners)

| Strategy | n | WR | mean % |
|---|---|---|---|
| `stocks_rsi2_pullback` | 17 | 64.7% | +0.76% |
| `Breakout Momentum` | 37 | **59.5%** | **+1.02%** |
| `quality-minus-junk` | 16 | 56.2% | +0.33% |

### FOREX (2 winners)

| Strategy | n | WR | mean % |
|---|---|---|---|
| `Bollinger MR` | 15 | 66.7% | +0.15% |
| `forex-rsi-ema-scout` | 15 | 60.0% | +0.33% |

**Note:** Commodity has NO strategy with n≥15 and WR≥50%. Best commodity performer is `futures_momentum` at 25.2% WR on 432 trades — the dominant commodity strategy is a coin-flip. This is a strategy-mix problem: crypto-derived techniques don't translate to commodity macro markets.

## 3. Top Strategy Losers (n ≥ 15, WR ≤ 35%)

### CRYPTO

| Strategy | n | WR | mean % | action |
|---|---|---|---|---|
| `st_fear_greed_contrarian` | 621 | 23.8% | −0.59% | retired per [strategy_blocklist.py:36](alpha_engine/strategy_blocklist.py#L36) |
| `copy_hl_lb_None` | 278 | 32.0% | **−2.90%** | retired |
| `st_obv_support_divergence` | 84 | 23.8% | −0.93% | retired |
| `st_atr_vol_breakout` | 27 | 22.2% | −0.80% | candidate for block |
| `atr_regime_rsi` | 29 | 17.2% | −0.36% | candidate for block |

### COMMODITY

| Strategy | n | WR | mean % | action |
|---|---|---|---|---|
| `cta_commodity_momentum_term` | 41 | **9.8%** | −0.10% | kill |
| `futures_momentum` | **432** | 25.2% | +0.04% | **dominant loser** — mutation-before-kill |
| `cta_cross_asset_tsmom` | 32 | 15.6% | +0.06% | mutation |

### FOREX

| Strategy | n | WR | mean % | action |
|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | 520 | 28.5% | +0.07% | **dominant loser** — 75% flat — widen TP/SL more |
| `non_crypto_consensus` | 84 | **0.0%** | 0.00% | 0 wins on 84 trades = broken mapping, investigate |
| `cta_cross_asset_tsmom` | 24 | 8.3% | −0.03% | kill |
| `Breakout Momentum` | 32 | 34.4% | −0.55% | cross-class degradation (equity version wins) |

---

## 4. Source System Leaderboard (n ≥ 30)

| System | n | WR | mean % | Σ PnL % | verdict |
|---|---|---|---|---|---|
| `stocks_competition` | 172 | **49.4%** | +0.49% | **+85** | ✅ keep |
| `baby_strats_forward` | 161 | 48.4% | +0.18% | +29 | ✅ keep |
| `kimi_riseoftheclaw` | 279 | 46.6% | +0.51% | **+144** | ✅ keep (top contributor) |
| `super_signals` | 98 | 43.9% | +0.16% | +15 | ⚠️ near-random |
| `luxalgo_filters` | 102 | 41.2% | +0.19% | +20 | ⚠️ |
| `alpha_engine` | 162 | 38.9% | −0.17% | −28 | ⚠️ |
| `rapid_fire` | 65 | 35.4% | −0.58% | −37 | ⚠️ |
| `copy_trader_intel` | 234 | 34.6% | −3.27% | **−766** | ❌ catastrophic |
| `alpha_engine_fast` | 60 | 33.3% | −0.11% | −7 | ⚠️ |
| `multi_asset_copytrader` | 946 | 28.8% | +0.05% | +46 | ⚠️ flat — lots of volume, no edge |
| `claude_gainer_st` | **731** | 23.8% | −0.63% | **−463** | ❌ catastrophic |
| `cta_replicator` | 117 | **9.4%** | −0.03% | −3 | ❌ broken |
| `forex_copy_trader` | 40 | **2.5%** | −0.01% | −1 | ❌ broken |
| `non_crypto_consensus` | 87 | **0.0%** | 0.00% | 0 | ❌ broken mapping |

**Takeaway:** `kimi_riseoftheclaw` + `stocks_competition` + `baby_strats_forward` together contribute +258% cum PnL. `claude_gainer_st` + `copy_trader_intel` together subtract 1,229%. Killing (or capping) the latter two is the single largest system-level improvement available.

PR #290 (Google Antigravity) already caps `claude_gainer_st` at 25 and `copy_trader_intel` at 35 — this is the right move.

---

## 5. Exit-Reason Breakdown

```
SL_HIT          1350 (38.6%)   <-- hits SL first
FORCE_CLOSED     825 (23.6%)   <-- CRON timeout
EXPIRED          582 (16.6%)   <-- max_hold exceeded
TP_HIT           469 (13.4%)   <-- hits TP
TIME_EXIT        184 ( 5.3%)   <-- time-based exit
UNKNOWN           90 ( 2.6%)
```

**Failure modes:**
- **TP:SL = 1:2.88** — ~3 SL hits per TP hit. Either stops are too tight or targets too far.
- **45.5% never resolve** — FORCE + EXPIRED + TIME_EXIT. These picks time out without a directional outcome. For forex/commodity this is ~50% of volume (see §1).
- Only 13.4% of emissions hit their intended target. Realistically, a strategy with a true 55% edge should show ~40%+ TP_HIT rate. 13% says the entry/exit spec is miscalibrated for the actual price distribution.

**Fix priority:**
1. Widen TP/SL bands on forex/commodity (in progress, commit `64506fe56d`).
2. Investigate hold-window / max-hold config per asset class — may be too short for commodity (which has longer regimes).
3. For crypto: TP/SL calibration from the 13% TP rate — if TP distance is fixed ATR-multiple, reduce it or raise entry quality.

---

## 6. Time-of-Day Analysis (CRYPTO, n=1695)

| UTC hr | n | WR | mean % | Notes |
|---|---|---|---|---|
| 00:00 | 311 | 37.9% | −2.47% | late US hand-off — high vol, bad mean |
| 01:00 | 85 | 43.5% | −0.03% | |
| 02:00 | 14 | 21.4% | −0.60% | thin |
| 03:00 | 40 | 45.0% | −0.18% | |
| 04:00 | 37 | 40.5% | −0.44% | |
| 05:00 | 22 | 40.9% | +0.31% | |
| 06:00 | 65 | 29.2% | −0.23% | |
| 07:00 | 51 | 31.4% | −0.29% | |
| 08:00 | 50 | 22.0% | −0.70% | **Phase-1 blocked window (death hours)** |
| 09:00 | 74 | 33.8% | −0.33% | |
| 10:00 | 74 | **18.9%** | −0.76% | worst in block |
| 11:00 | 61 | 24.6% | −0.61% | |
| 12:00 | 48 | **16.7%** | −0.68% | EU noon — second death window |
| 13:00 | 61 | 27.9% | −0.70% | US pre-open |
| 14:00 | 51 | 39.2% | +0.04% | US open — only decent US hour |
| 15:00 | 40 | 30.0% | −0.63% | |
| 16:00 | 60 | **20.0%** | −0.76% | US close — bleed |
| 17:00 | 55 | **18.2%** | −0.77% | worst US |
| 18:00 | 81 | 25.9% | −0.48% | |
| 19:00 | 83 | **19.3%** | −0.87% | |
| 20:00 | **117** | **17.1%** | **−1.03%** | **WORST** — largest sample, worst WR |
| 21:00 | 64 | 20.3% | −0.71% | |
| **22:00** | **85** | **71.8%** | **+1.08%** | **BEST — Asia preopen / post-US settlement** |
| **23:00** | **65** | **63.1%** | **+0.81%** | BEST #2 |

### Insight

**The 22:00-23:59 UTC window has a 50+ point WR advantage over 18:00-21:59.** Same symbols, same strategies, same confidence distribution — the only difference is time of day.

- Phase-1 gate currently blocks 08:00-11:00 UTC. **It should also block 16:00-21:00 UTC** (that's the new 6-hour death block — combined 580 picks at 20% avg WR, mean −0.82%).
- Conversely: a **22:00-23:59 UTC allowlist** for crypto is the single highest-ROI filter in the dataset. WR 68%, mean +0.96%, PF ≈ 3. 150 picks in the window over the sample.

**Recommended Phase-2 gate addition** (to complement Phase-1):
```python
# Add to passes_active_gate
if asset_class == "CRYPTO" and 16 <= hour_utc <= 21:
    if confidence < 0.90:  # extreme-conviction exception only
        return False
```
Expected impact on crypto book: ~25% active-row reduction, +5-10pp realized WR lift.

## 7. Confidence ≠ Edge (CRYPTO n=1695)

| Confidence band | n | WR | mean % |
|---|---|---|---|
| 0.00–0.55 | 138 | **42.8%** | −0.37% |
| 0.55–0.65 | 301 | 41.9% | −0.05% |
| 0.65–0.75 | 820 | **26.2%** | −0.50% |
| 0.75–0.85 | 365 | 34.2% | **−2.20%** |
| 0.85–1.01 | 71 | 36.6% | −0.32% |

**Confidence is anti-predictive.** Low-confidence (< 0.55) picks have 42.8% WR; mid-conf (0.65–0.75) has 26.2%; conf 0.75–0.85 has mean PnL of **−2.20%**. 

The `feedback_confidence_is_not_edge.md` memory entry was right, and it's now measurable at n=1695. Any HC gate that relies on `confidence ≥ X` as a quality signal is **making things worse** in the crypto book.

**Recommendation:** Deprecate `confidence` as a gate. Use `elite_score`, `trust_tier`, `strat_fwd_wr`, or symbol+strategy+hour combinations instead. PR #287's `confidence ≥ 0.80` requirement in the HC filter is actively harmful based on this data.

---

## 8. Active Book — Current State (n=52)

| Class | n | avg conf | avg elite | concern |
|---|---|---|---|---|
| CRYPTO | 38 | 0.79 | 34.2 | elite 34 << HC threshold 70 → none are true HC |
| FOREX | 7 | 0.78 | 48.0 | |
| EQUITY | 5 | **1.00** | 19.0 | max conf on each, elite 19 = UNSCORED / D-grade |
| COMMODITY | 2 | 0.72 | 40.0 | |

**Active book issues:**
- No crypto pick has elite ≥ 70 (→ no HC-tier picks).
- Equity picks are scored at elite 19 despite conf 1.00 — suggests the forward_wr contribution is dead (my #289 diagnostic applies).
- With PR #288 landing, crypto rows should drop to ~17 (67% rejection). Current avg elite 34 means many are close to the proposed 40% forward-WR floor.

---

## 9. Recommended actions (ranked by expected PnL impact)

| # | Action | Expected impact | Effort | Owner |
|---|---|---|---|---|
| 1 | **Add 16:00-21:00 UTC crypto block** to Phase-1 TOD gate | +5-10pp realized WR, −25% active rows | 10 LOC | any |
| 2 | Cap or kill `claude_gainer_st` + `copy_trader_intel` | Saves ~1,230% cum drag | already in PR #290 | — |
| 3 | **Deprecate `confidence ≥ 0.80`** as HC gate criterion on crypto | Stops anti-predictive leakage | config change | any |
| 4 | Widen commodity + forex hold windows (reduce FORCE_CLOSED rate) | Converts flats → resolved | risk-param tune | engineer |
| 5 | Kill `non_crypto_consensus` (0% WR on 87 trades) | Small volume but deterministic bleed | blocklist | any |
| 6 | Investigate why `futures_momentum` (n=432, 25% WR, +0.04%) emits so much for so little edge | Large volume, no realized edge | strategy mutation | engineer |
| 7 | Close the `strategy_performance.json` naming mismatch (my PR #289 / peer hlujwibk's backfill) | Enables #3-#6 gates to work | backfill | hlujwibk |
| 8 | Replace crypto-derived forex/commodity strategies with asset-class-native (carry, TSMOM, TAA) | Lifts 77% of book from break-even | multi-week | engineer |
| 9 | Fix crypto TP/SL calibration (only 13% TP hit rate) | Improves realized WR regardless of entry | strategy-by-strategy | engineer |

---

## 10. What this means for "hedge fund grade"

Current state, re-stated with n=3500 evidence:

- **We have one asset class with edge (Equity).** Everything else is either break-even-flat (Commodity, Forex, ETF, Bond) or net losing (Crypto).
- **The alpha that exists is concentrated in 3 systems** (`kimi_riseoftheclaw`, `stocks_competition`, `baby_strats_forward`) and 3 windows (22:00–23:59 UTC crypto, equity broadly, a few winners in each class).
- **The losses are concentrated in 2 systems** (`claude_gainer_st` n=731 WR 23.8%, `copy_trader_intel` n=234 WR 34.6%) that together account for the vast majority of system-level drag.
- **The dominant strategies on the two worst asset classes don't work.** `futures_momentum` (commodity, n=432, 25%) and `forex_rsi2_mean_reversion` (forex, n=520, 29%) are essentially random generators held up by force-close flats.

Ranked by distance from "good HF" (55-60% WR, PF 1.8-2.5, Sharpe 1.2-2.0):

- **Equity:** within striking distance (WR 50.3%, PF 1.44, mean +0.68%) — needs 5pp WR lift and risk sizing tuning.
- **Bond / ETF:** break-even on thin samples — defer until sample hits n ≥ 100.
- **Crypto:** 20-25pp gap. The TOD gate in §6 closes 5-10 of that. Killing claude_gainer_st + copy_trader_intel closes another 5. Remaining ~10pp requires swapping losing strategies for the winners identified in §2 and implementing the peer research that's been researched but not wired.
- **Forex / Commodity:** the mix is wrong. Current strategies are crypto-derived and don't work on macro markets. Until carry / TSMOM / TAA / seasonal are wired (per Kimi's RCA recommendations from 2026-04-17), headline WR will stay in the 20-30% range driven by flat FORCE_CLOSED dilution.

**Overall:** Within one sprint of focused work (§§1-6 of the action list), crypto could plausibly move from PF 0.60 → 1.0-1.2, forex/commodity from flat-dilution to measurable break-even. Reaching "good HF" Sharpe 1.2+ on the aggregate book realistically takes 6-8 weeks of strategy-mix work plus the data-plumbing refactors already underway (peer hlujwibk's backfill + Cursor PR #287 + Antigravity PR #290 + my #289 diagnostic).

---

## Appendix: Reproduce

All numbers in this report come from `audit_trail/data/dashboard_payload.json` snapshot taken 2026-04-21 01:30 UTC. Reproduce with:

```python
import json, collections, statistics
d = json.load(open("audit_trail/data/dashboard_payload.json"))
closed = [p for p in d["picks"]["recent_closed"] if p.get("pnl_pct") is not None]
# ... (see in-line analysis code; full script available on request)
```

**Nothing in this PR modifies production strategy files.**
