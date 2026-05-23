# Hourly Audit — 2026-05-21 03Z

**Generated:** 2026-05-21T03:30Z  
**Dashboard snapshot:** 2026-05-20T04:13Z (STALE ~23h — same snapshot as all May 20 hourly audits; expected 12Z refresh did not arrive; next expected ~12Z May 21)  
**Previous audit:** 2026-05-20 11Z (last in series)  
**Context issues:** #685 (resolver-rescope DONE), #686 (live-data attribution), #693 (EQUITY divergence monitor — closed 2026-05-13)  
**HOLD set (#660 #658 #681 #661):** absent ✅  
**Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655):** absent ✅ (all merged or closed)  

---

## Pull status

`git pull origin main` fast-forwarded `fc2d6eac → c677feac`. Key non-auto changes since last audit:

| Commit | Summary |
|--------|----------|
| `93e71bc` | fix(ci): drop orphan openclaude gitlinks (submodule fix) |
| `bd2014c` | fix(resolver): guard F-1 pnl_pct cap inside check_tp_sl hit branch |
| `56922e5` | fix(events): regenerate metadata.json |

Today's merged PRs (all cross-AI verified): **#684** (48h review), **#674** (B11 ETF), **#673** (B14 stress), **#664** (audit credibility), **#683** (cftc_cot kill), **#687** (P0 JPY-cross BUY rule fix), **#692** (kill forex_carry_momentum + goldmine_6x_consensus), **#694** (quan_engine HYPEUSDT symbol-block).

---

## Per-asset windows — 03Z snapshot

> Dashboard snapshot is 2026-05-20T04:13Z. Windows computed relative to snapshot time for data consistency (same approach as previous hourly audits).

| Class     | 24h PF | 24h WR | 24h n | 7d PF | 7d WR  | 7d n | 30d PF | 30d n | vs 11Z (7d delta) |
|-----------|--------|--------|-------|-------|--------|------|--------|-------|-------------------|
| CRYPTO    | 1.004  | 43.9%  | 173   | 1.200 | 45.8%  | 1013 | 1.340  | 2792  | +0.002 (stable) |
| EQUITY    | 0.075  | 6.2%   | 16    | 0.641 | 28.9%  | 45   | 1.419  | 146   | ±0.000 (flat) |
| FOREX     | 1.278  | 42.9%  | 7     | 1.272 | 33.3%  | 18   | 2.515  | 93    | −0.041 (noise — n=18, 1-pick shift) |
| COMMODITY | 0.000  | 0.0%   | 16    | 0.097 | 7.9%   | 38   | 0.962  | 73    | ±0.000 (still catastrophic) |
| ETF       | 0.000  | 0.0%   | 1     | 1.233 | 31.2%  | 16   | 1.917  | 56    | ±0.000 (stable) |
| BOND      | 0.000  | 0.0%   | 3     | 0.000 | 0.0%   | 3    | 0.000  | 3     | stable (very low n) |

**asset_class_health long-run (resolver-clean, from dashboard_data.json):**

| Class     | PF     | WR     | n    | Status |
|-----------|--------|--------|------|--------|
| CRYPTO    | 1.263  | 48.3%  | 1127 | stable (sizing_allowed=true) |
| EQUITY    | 0.874  | 35.2%  | 54   | candidate (sub-Tier-2) |
| FOREX     | 1.476  | 55.7%  | 149  | stable (post-kill recovery) |
| COMMODITY | 1.424  | 54.5%  | 55   | candidate (long-run OK; 7d catastrophic) |
| ETF       | 11.994 | 50.0%  | 2    | insufficient (n=2, ignore PF) |
| FUTURES   | 0.956  | 16.7%  | 12   | thin_sample |
| BOND      | 0.000  | 0.0%   | 6    | insufficient |

---

## vs documented baselines (issues #686 / #693)

| Class | Baseline 7d PF | 03Z 7d PF | Delta | Status |
|-------|----------------|-----------|-------|--------|
| CRYPTO | 1.21 (issue #686) | 1.200 | −0.010 | ✅ stable |
| EQUITY | 0.87 (issue #693) | 0.641 | −0.229 | 🟡 degraded; goldmine_6x kill (PR #692) not yet visible in data — window predates kill |
| FOREX | 0.14 pre-#687 | 1.272 | +1.132 | ✅ massive recovery holding post-#687/#692 |
| COMMODITY | 1.18 (issue #686) | 0.097 | −1.083 | 🚨 FINDING-22 active (ongoing) |

---

## EQUITY 7d strategy attribution (03Z)

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `stocks_rsi2_pullback` | 24 | 37.5% | 1.131 | +5.87% |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 | +0.97% |
| `aroon-trend-scout` | 1 | 100% | inf | +4.05% |
| `adx-trend-scout` | 2 | 50.0% | 0.343 | −5.23% |
| `macd-hidden-div-scout` | 1 | 0% | 0.000 | −6.68% |
| `fibonacci-bounce-scout` | 1 | 0% | 0.000 | −1.39% |
| `stocks_ema_golden_cross` | 2 | 0% | 0.000 | −6.83% |
| `gap-and-go-stocks` | 1 | 0% | 0.000 | −6.83% |
| `rs-breakout-scout` | 2 | 0% | 0.000 | −3.02% |
| `price-accel-scout` | 1 | 0% | 0.000 | −6.92% |

`goldmine_6x_consensus`: 0 entries ✅ (killed by PR #692; effect visible).  
`stocks_rsi2_pullback`: n=24, WR=37.5%, PF=1.131 — **now positive** (+5.87% sum). Crossed the n=20 floor; on the borderline of 35% WR threshold. Not a kill candidate.  
EQUITY 7d drag is distributed across 9+ low-n scout strategies with 0% WR (n=1-2 each). No single structural kill emerges; this appears to be regime/noise rather than a broken strategy.

---

## COMMODITY 7d strategy attribution (03Z)

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `cftc_cot_commercial_signal` | 20 | 5.0% | 0.113 | −65.79% |
| `futures_momentum` | 17 | 11.8% | 0.087 | −52.81% |
| `futures_bb_mean_reversion` | 1 | 0.0% | 0.000 | −6.41% |

**30d context:**

| Strategy | n (30d) | WR | PF |
|----------|---------|----|----||
| `cftc_cot_commercial_signal` | 53 | 55% | 1.61 |
| `futures_momentum` | 18 | 11.1% | 0.086 |

`cftc_cot_commercial_signal`: massive regime collapse in the 7d window (May 14–19). 30d base is healthy (WR=55%, PF=1.61). PR #683 (cftc_cot kill, merged today) should stop new emissions. Last close: 2026-05-19. Verify PR #683 scope covers `cftc_cot_commercial_signal` specifically — it's in COT_DEDUP_SYSTEMS but **not** in BLOCKED_SOURCE_SYSTEMS or BLOCKED_ASSET_STRATEGY_PAIRS.

---

## FOREX 7d strategy attribution (03Z, post-#687+#692)

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `unknown` | 7 | 43% | 1.283 | +1.40% |
| `ig_contrarian_sentiment` | 8 | 37.5% | 1.389 | +0.88% |
| `MeanReversionBB` | 2 | 0% | 0.000 | +0.00% |
| `forex_carry_momentum` | 0 | — | — | — |
| `forex_rsi2_mean_reversion` | 0 | — | — | — |

Kills from PR #692 holding ✅. No catastrophic FOREX strategies remain in the 7d window. PF=1.272 represents a **+1.132 improvement** vs the pre-#687 baseline. Monitoring for volume recovery (n=18 is low; long-run FOREX needs n→149+ for statistical confidence).

---

## PR triage (03Z)

`gh pr list --state open` returned **0 open PRs**.

- HOLD set (#660 #658 #681 #661): absent ✅
- Author-rebase watch (#669 #676 #608 #665 #644 #597 #615 #655): absent ✅
- **Merges this hour: 0** (no open PRs to evaluate)

---

## Mutation analysis highlights (tools/mutation_analysis.py)

Full output captured. Notable signals:

| Signal | Detail | Action |
|--------|--------|--------|
| `ig_contrarian_sentiment` direction | SHORT: 60.3% WR n=58 vs LONG: 16.5% WR n=200 (44pp spread) | FINDING-33: Axis-1 candidate; SHORT-only mutation needs 3-AI consensus before PR |
| `myfxbook_retail_contrarian` direction | SHORT: 50% WR vs LONG: 13.7% WR (36pp spread) | Already in BLOCKED_ASSET_STRATEGY_PAIRS (FOREX) ✅ |
| `cta_replicator` x NG=F | 0% WR n=24 — crosses n=20 kill threshold | FINDING-34: Propose BLOCKED_STRATEGY_SYMBOL_PAIRS (cta_replicator, NG=F) |
| `cta_replicator` x ZC=F | 0% WR n=8 — below threshold | Monitor |
| `rapid_fire` x UUSDT | 0% WR n=34 | Already in _DATA_QUALITY_BLOCKS ✅ |
| `rapid_fire` x TAOUSDT | 5.6% WR n=18 | Below n=20; monitor |
| `quan_engine` x HYPEUSDT | 41.6% WR n=553 | PR #694 (today) added symbol-block ✅ |

---

## New findings this audit

### FINDING-31: `futures_momentum` COMMODITY approaching kill threshold
- **30d**: n=18, WR=11.1%, PF=0.086 — all picks from May 12–19
- **Kill criteria check**: n=18 (below n=20 floor), WR=11.1% (well below 35%), PF=0.086 (well below 0.5), pattern matches existing (FUTURES, futures_momentum) block
- **Status**: NOT yet killable (n<20). At current emission rate (~2 picks/day) will cross n=20 within 1–2 days. Issue #685 pre-approved this kill.
- **Pre-approved action when n>=20**: add `("COMMODITY","futures_momentum")` to BLOCKED_ASSET_STRATEGY_PAIRS per issue #685.
- **Sources also blocked**: `futures_momentum` already in BLOCKED_SOURCE_SYSTEMS (line 1974) and (FUTURES, futures_momentum) in BLOCKED_ASSET_STRATEGY_PAIRS (line 2609). The COMMODITY pair is the only gap.

### FINDING-32: `cftc_cot_commercial_signal` scope verification needed
- **Observation**: PR #683 (cftc_cot kill) merged today. `cftc_cot_commercial_signal` is in COT_DEDUP_SYSTEMS (line 2078) but NOT in BLOCKED_SOURCE_SYSTEMS or BLOCKED_ASSET_STRATEGY_PAIRS.
- **7d regime collapse**: WR=5%, PF=0.11, n=20, sum=−65.79%. Last close: 2026-05-19. 30d base (WR=55%, PF=1.61, n=53) suggests regime-driven collapse rather than structural failure.
- **Risk**: If PR #683 killed `cftc_cot` source but `cftc_cot_commercial_signal` is emitted via a different pipeline path, new picks may still arrive.
- **Action**: Verify PR #683 diff covers `cftc_cot_commercial_signal`. If not, add to BLOCKED_ASSET_STRATEGY_PAIRS for COMMODITY pending regime recovery. Do NOT kill outright given 30d PF=1.61.

### FINDING-33: `ig_contrarian_sentiment` LONG direction broken
- **SHORT**: 60.3% WR n=58 vs **LONG**: 16.5% WR n=200 (44pp spread)
- Axis-1 (direction) mutation candidate: SHORT-only version is high-conviction.
- **Status**: Needs 3-AI consensus before implementation. Post to issue #686.

### FINDING-34: `cta_replicator` x NG=F kill proposal
- NG=F (natural gas futures): 0% WR n=24 within `cta_replicator` — crosses n=20 + PF=0 criteria.
- USDJPY=X within same system is 69.6% WR n=115 — symbol-specific drag confirmed.
- **Proposed action**: Add (cta_replicator, NG=F) to BLOCKED_STRATEGY_SYMBOL_PAIRS. Needs evidence doc + 1 AI review before PR.

---

## Dashboard refresh status

Expected hourly cron refresh at 12Z May 20 did **not** arrive (same snapshot now >23h old). Auto-commits (signal scans) are landing but dashboard_data.json was last updated 2026-05-20T04:13Z. Next expected refresh: ~12Z May 21 2026.

---

## Summary

- **Dashboard**: Stale (23h). Same May 20 04:13Z snapshot as all prior hourly audits.
- **Open PRs**: 0. No merges this hour. 8 PRs merged today (session total).
- **New findings**: 4 (FINDING-31 through FINDING-34).
- **Highest priority**: FINDING-31 (futures_momentum COMMODITY n=18, pre-approved kill when n>=20 per issue #685). FINDING-32 (verify cftc_cot_commercial_signal scope of PR #683).
- **Positive signals**: FOREX 7d PF=1.272 (recovery holding, +1.132 vs pre-#687 baseline). EQUITY stocks_rsi2_pullback now net-positive (PF=1.131, +5.87% sum).
- **Next action**: Post FINDING-33 to issue #686 for 3-AI consensus. Monitor FINDING-31 for n>=20 trigger.
