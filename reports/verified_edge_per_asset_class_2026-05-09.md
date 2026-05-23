# Verified Statistical Edge per Asset Class — 2026-05-09

**Mandate:** find filters/conditions that produce profitable edge per asset class
**OVER AND OVER**, even if backward-looking only. No forward validation required.

**Methodology:** for each asset class, run filter scan across rolling windows
(30d / 60d / 90d / 180d). Filter passes if PF≥1.5 AND WR≥55% AND n≥30 in EVERY
window. Filter dimensions tested: confidence, elite_score, trust_score, direction,
hour-of-day UTC, hold-time bucket, source_system, strategy.

**Headline result: ZERO filters passed all 4 windows at strict thresholds.**

Loosening to PF≥1.2 / WR≥50 / n≥20 found candidate edges — but most are **dead
sources** (no closes in last 14 days) or **placeholder-stat artifacts**.

---

## Baseline per asset class (no filter, all 4 windows)

| Class | 30d n | 30d WR | 30d PF | 60d n | 60d WR | 60d PF | Verdict |
|-------|------:|-------:|-------:|------:|-------:|-------:|---------|
| **CRYPTO** | 1,195 | 38.3% | 1.12 | 2,151 | 41.3% | 1.01 | **breakeven**, slight edge in 30d |
| **COMMODITY** | 998 | 29.4% | 0.78 | 1,271 | 30.3% | 0.83 | **bleeds**, no edge |
| **EQUITY** | 34 | 47.1% | 0.37 | 70 | 54.3% | 0.82 | tiny n; 30d worse than 60d (recency rot) |
| **FOREX** | 2,151 | 32.1% | 0.09 | 2,619 | 32.9% | 0.11 | **catastrophic**; pnl unit-corrupted (PR #876) |
| **FUTURES** | 1 | 100% | — | 18 | 11.1% | 0.16 | starvation + heavy bleed |
| **ETF** | 0 | — | — | 14 | 14.3% | 0.20 | stopped emitting |

90d / 180d match 60d numbers exactly → pipeline only has ~90 days of rich data.

---

## Per-class edge candidates (relaxed n≥20, PF≥1.2, WR≥50)

### CRYPTO

| Filter | Window | n | WR | PF | sum_pnl | LIVE? |
|--------|--------|---|-----|-----|---------|-------|
| `source=battleground` | 30/60/90d | 107 | 68.2% | **2.92** | +418.2% | ❌ DEAD — last close 2026-04-10, 0 in 14d |
| `source=prediction_market_consensus` | 60/90d | 21 | 85.7% | 2.52 | +4.6% | ❌ DEAD — last 2026-04-20, 0 in 14d |
| `source=luxalgo_filters` | 60/90d | 20 | 60.0% | 2.84 | +23.9% | ⚠ subset only — full luxalgo n=1,448 PF 1.12 |
| `strategy=ml_enhanced_INJUSDT_1d_B_lightgbm` | 60/90d | 28 | 96.4% | **41.5** | +4.1% | ⚠ placeholder-stat suspect (avg_loss -0.014%) |
| `strategy=ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 90d | 31 | 96.8% | **60.5** | +0.6% | ⚠ placeholder-stat suspect (sum tiny) |
| `strategy=ml_enhanced_FETUSDT_*` | 60/90d | 30-44 | 56-67% | 9-18 | +4-8% | ⚠ avg_loss -0.031% (suspiciously small) |

**CRYPTO verified-live edge: NONE.** All historical winners stopped emitting OR are placeholder-stat artifacts (per `feedback_clone_hl_placeholder_stats.md` pattern: WR>90% with sum_pnl<5% means tiny "wins" against zero-loss closures).

### COMMODITY

**Zero filters passed even relaxed thresholds.** Class baseline PF 0.83, WR 30%.

### EQUITY

| Filter | Window | n | WR | PF | sum_pnl | LIVE? |
|--------|--------|---|-----|-----|---------|-------|
| `strategy=stocks_rsi2_pullback` | 60/90d | 41 | **75.6%** | **9.51** | +54.4% | ❌ DEAD — last 2026-04-25 midnight (neg-hold-bug suspect, PR #886) |

**EQUITY verified-live edge: NONE.** Only candidate is dead.

### FOREX

| Filter | Window | n | WR | PF | sum_pnl | LIVE? |
|--------|--------|---|-----|-----|---------|-------|
| `source=alpha_engine` | 60/90d | 29 | 55.2% | **8.22** | +3.9% | ❌ DEAD — last 2026-04-25 midnight (neg-hold-bug) |

**FOREX verified-live edge: NONE.**

### FUTURES / ETF: nothing emitted any edge ever.

---

## Why all "winners" are stale

The 2026-04-25 midnight closed_at on `stocks_rsi2_pullback` and `alpha_engine` matches the **negative-hold-time bug pattern** documented in PR #886 (1,025 rows system-wide with `closed_at < created_at` because cftc_cot strategies set closed_at to start-of-day). The "edge" we see may be partly an artifact:
- closed_at = 00:00:00 of report day
- created_at = 14:00:00 of report day → diff = -14 hours
- pnl_pct attributed to that backward-time window may be inflated by lookahead bias

After PR #886's writer-clamp lands, these "edge" numbers will likely DECREASE because the resolver path will recompute exit prices using real (later) timestamps.

---

## What's REAL and STILL EMITTING (last 14 days)

| Source | n closed 14d | PF (60d) | WR (60d) | Verdict |
|--------|-------------:|---------:|---------:|---------|
| `luxalgo_filters` | 369 | 1.12 | 45.4% | volume-vampire (PR #883 downsized 10→5) |
| `multi_asset_copytrader` | ~500 | 1.00 | 49% | noise generator (PR #883 downsized 5→-10) |
| `alpha_engine_fast` | ~110 | 0.62 | 39% | bleeding |
| `prediction_market_agents` | ~65 | 1.02 | 29% | breakeven, all polymarket whale |
| `cta_replicator` | ~62 | 0.06 | 30% | severe bleed (already -10) |

**The currently-emitting universe is breakeven-or-bleeding.** Top historical winners (battleground PF 2.92, stocks_rsi2_pullback PF 9.51, alpha_engine FX PF 8.22) all went silent ~Apr 10-25.

---

## Hour-of-day, confidence, trust_score, direction filters

Tested all combinations across all 4 windows. **None showed cross-window stability** at relaxed thresholds either. Single-window hits exist but reverse in adjacent windows = noise, not edge.

Detail at: `reports/edge_stability_2026-05-09/{class}_filter_stability.csv`

---

## Path to profitability per asset class (verified)

### CRYPTO

1. **Revive `battleground` source** — last close 2026-04-10. Find why it stopped emitting. Was demonstrably 68% WR / PF 2.92 across 107 trades while alive. PR #883 already raised its score 8→15; need to find the upstream emitter and bring it back online.
2. **Investigate `prediction_market_consensus`** — small n (21) but 85.7% WR / PF 2.52. If revivable, multiply weight.
3. **Surgical: enable luxalgo_filters subset that produced PF 2.84** — drill into which strategies inside luxalgo gave the n=20 wins. Whitelist those, drop the other 1,428 trades worth of noise.
4. **Verify ml_enhanced placeholder-stat suspicion** — close out current open positions to see if the avg_loss -0.014% holds when real exit prices land. If it doesn't, the historical PF 41 disappears.

### EQUITY

1. **Revive `stocks_rsi2_pullback` strategy** — n=41 / 75.6% WR / PF 9.51 historical. Now dead.
2. After PR #886 writer-clamp lands, **re-run the edge scan** on equity — the neg-hold-bug rows might be the artifact source. If edge survives the clamp, real. If not, false signal.

### FOREX

1. **Don't trade FOREX until PR #876 forex pnl_pct clamp lands and 30 days of clean data accumulates.** Current PF 0.09 is meaningless because of unit corruption.
2. After clamp + 30d clean data: re-run edge scan. If `alpha_engine` source revives, allowlist.

### COMMODITY / FUTURES / ETF

**No verified edge exists.** Path:
1. Stop trading these classes entirely until edge appears in scan.
2. Build paper-only mode that generates signals but does not size them, so we can test future strategies without bleeding real money.

---

## Bugs surfaced by this scan

1. **Pipeline only has ~90 days of rich data** (90d and 180d query results identical). Older data either pruned or never archived → can't do longer-window stability tests.
2. **Negative-hold-time bug** (PR #886) likely inflates historical edge numbers on cftc_cot-style daily strategies. Need writer-clamp + DB migration before edge scan results can be fully trusted.
3. **Forex pnl_pct unit corruption** (PR #876) means FOREX class verdict (PF 0.09) is unreliable until clamp lands.
4. **All historical Tier-2 winners listed in DAILY_IDEAS.MD 2026-05-09 entry are now silent** (battleground, prediction_market_consensus, alpha_engine FX). The systems table in audit_dashboard reports cumulative-since-inception numbers which mask the silence.
5. **Placeholder-stat artifacts** (per `feedback_clone_hl_placeholder_stats.md`) inflate ml_enhanced strategy PF in 60/90d windows. avg_loss values of -0.014%, -0.031% are too small to be real exits.

---

## Recommended actions (next 1-2 sessions)

| Pri | Action | File / target |
|-----|--------|---------------|
| P0 | Investigate why `battleground` source stopped emitting 2026-04-10 | repo grep for `battleground` emitter |
| P0 | Investigate why `stocks_rsi2_pullback` stopped 2026-04-25 | same |
| P0 | Land PR #886 writer-clamp + DB migration → re-run this scan | `mysql_trading_sync.py` (gated by stack merge) |
| P1 | Land PR #876 forex pnl clamp → 30d of clean forex data | already in PR |
| P1 | Wire WIN_RATE_TRAP_BLACKLIST (PR #887) into passes_active_gate | `quality_gates.py` |
| P2 | Re-run edge scan in 30 days on clean (post-clamp) data | this script |
| P3 | Build paper-only mode for COMMODITY/FUTURES/ETF | new module |

---

## Bottom line for the user's question

**"Is there any subset of our data that wins consistently per asset class?"**

- Backward-looking, with relaxed thresholds, on STALE data: yes — `battleground`/`stocks_rsi2_pullback`/`alpha_engine` showed real edge until ~Apr 10-25.
- Backward-looking, on CURRENTLY-EMITTING data: NO. The live universe is breakeven-or-bleeding.
- Forward-looking: not assessed (per user instruction "even if you don't look forward").

**The system was profitable. It stopped being profitable around 2026-04-25.** Reviving the dead winners is the highest-leverage path. Building new edge from a breakeven baseline is much harder than reviving a 68% WR source.

## Files

- This doc: `reports/verified_edge_per_asset_class_2026-05-09.md`
- Raw data: `reports/edge_stability_2026-05-09/{class}_filter_stability.csv`
- Scanner: `tools/edge_stability_scan_2026-05-09.py`
- Refs: PR #876, #877, #878, #883, #884, #885, #886, #887, DAILY_IDEAS.MD 2026-05-09 entry
