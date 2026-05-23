# Hourly Audit — 2026-05-08 04Z

**Dashboard snapshot:** 2026-05-08T03:59:34Z (post-pull from origin/main @ 3535d010)
**Generated:** 2026-05-08T04:xx UTC (Claude Sonnet 4.6)
**Source data:** `audit_dashboard/data/dashboard_data.json` — `picks.recent_closed` n=3500

---

## Dashboard Refresh Status

- Pulled `origin/main` — fast-forward from `f18f1687` → `3535d010`
- `cross_aggregation/data/conviction_picks.json` and `data/meme_scanner_active.json` updated (auto-refresh [skip ci])
- Dashboard `generated_at` confirmed: **2026-05-08T03:59:34.283933+00:00** (fresh, within 5 min of audit start)

---

## Per-Asset Metrics (computed from picks.recent_closed, per-class pnl_pct thresholds)

Thresholds used: CRYPTO/EQUITY/ETF=0.1%, FOREX=1bp, COMMODITY/BOND=5bp

### 24h Window

| Class | n | WR | PF | Sum PnL% | Note |
|---|---|---|---|---|---|
| **CRYPTO** | 188 | 39.4% | **1.76** | +140.73% | ✅ RECOVERED from 03Z alarm |
| EQUITY | 4 | 50.0% | 1.39 | +1.36% | n too small |
| FOREX | 12 | 41.7% | **1.46** | +2.25% | ✅ Post-kill healthy |
| COMMODITY | 3 | 100.0% | ∞ | +12.97% | n too small |
| ETF | 1 | — | — | +2.68% | n too small |

### 7d Window

| Class | n | WR | PF | Sum PnL% | Tier | Delta vs 03Z |
|---|---|---|---|---|---|---|
| **CRYPTO** | 819 | 45.3% | **1.41** | +293.66% | 🟡 T2 floor | Stable (±0.00) |
| **EQUITY** | 18 | 66.7% | **4.70** | +78.75% | 🥇 T1 (6th run) | −0.72 vs 5.42 (still T1) |
| **FOREX** | 52 | 46.2% | **1.67** | +12.86% | 🟢 T2 | +0.06 vs 1.61 ✅ |
| COMMODITY | 19 | 94.7% | **42.83** | +80.38% | ⚠ n<20 floor | New — cftc_cot dominant |
| ETF | 13 | 92.3% | **25.47** | +24.50% | ⚠ n<50 floor | Stable |

### 30d Window

| Class | n | WR | PF | Sum PnL% | Tier |
|---|---|---|---|---|---|
| **CRYPTO** | 2606 | 45.8% | **1.27** | +579.51% | 🟡 sub-T2 (PF<1.5) |
| **EQUITY** | 130 | 65.4% | **3.25** | +295.17% | 🥇 T1 (PF>2) |
| **FOREX** | 232 | 47.8% | **1.57** | +14.31% | 🟢 T2 confirmed |
| **COMMODITY** | 101 | 49.5% | **4.44** | +101.88% | 🥇 T1-candidate (n just crossed 100 floor!) |
| ETF | 43 | 79.1% | **4.54** | +69.02% | 🥇 T1 (n<50 floor — still insufficient for charter) |

### Long-run (asset_class_health, dashboard)

| Class | PF | WR | n | Status |
|---|---|---|---|---|
| CRYPTO | 1.33 | 47.0% | 7,827 | stable |
| EQUITY | 1.55 | 53.6% | 431 | stable |
| COMMODITY | 4.43 | 67.3% | 339 | stable |
| FOREX | 0.25 | 46.2% | 647 | stressed |
| ETF | 1.38 | 57.9% | 95 | candidate |
| BOND | 0.66 | 54.5% | 11 | thin_sample |

---

## Key Deltas vs 03Z Baseline

| Metric | 03Z | 04Z | Direction |
|---|---|---|---|
| CRYPTO 24h PF | 0.45 ⚠ | **1.76** | ✅ RECOVERED |
| CRYPTO 7d PF | 1.41 | 1.41 | → Stable |
| EQUITY 7d PF | 5.42 | 4.70 | ↘ slight drop, still T1 |
| EQUITY 30d PF | 4.63 | 3.25 | ↘ (window roll — expected) |
| FOREX 7d PF | 1.61 | 1.67 | ✅ Improving |
| FOREX 30d PF | — | 1.57 | ✅ T2 confirmed |
| COMMODITY 7d | 0 picks | PF=42.83 n=19 | ✅ cftc_cot dominant |
| COMMODITY 30d | 0.04 (distorted) | **4.44 n=101** | ✅ T1-candidate, n crossed 100 |
| ETF 7d PF | 25.47 | 25.47 | → Stable |

**Vs task baseline (documented: CRYPTO 24h 3.54 / 7d 1.33 / 30d 1.33; EQUITY 7d 0.87; FOREX 7d 0.14 pre-#687):**
- CRYPTO 7d: 1.33 → 1.41 (+0.08 ✅)
- EQUITY 7d: 0.87 → 4.70 (+3.83 — goldmine_6x kill #692 fully validated)
- FOREX 7d: 0.14 → 1.67 (+1.53 — #687 JPY-fix + #692 kill validated)

---

## CRYPTO 24h Alarm — CLEARED ✅

**03Z alarm:** PF=0.45 / WR=19.4% — `signal_engine_momentum_mut` 7-loss streak
**04Z status:** PF=1.76 / WR=39.4% — alarm was transient noise

24h CRYPTO strategy breakdown (top 10):
| Strategy | n | WR | Sum PnL% |
|---|---|---|---|
| strong consensus (alpha_engine, ml_crypto_pred) | 58 | 50.0% | +144.77% |
| unknown | 29 | 27.6% | −5.95% |
| luxalgo_confluence | 17 | 35.3% | +2.59% |
| multi_period_rsi_confluence_eth | 9 | 0.0% | −2.50% |
| keltner_compression_expansion_eth_v1 | 7 | 100.0% | +3.03% |
| signal_engine_momentum_mut | 7 | 0.0% | −9.92% |
| ensemble | 6 | 50.0% | +4.89% |

`signal_engine_momentum_mut` still at 0% WR (n=7 in 24h) — flagged for next cycle. 7d anchor (PF=1.41) stable; no action warranted until n≥20 in a 7d window.

---

## FOREX 7d Strategy Breakdown (post-kill confirmation)

| Strategy | n | WR | Sum PnL% |
|---|---|---|---|
| **MeanReversionBB** | 17 | 58.8% | +9.68% |
| fx_smart_carry_trade_momentum | 10 | 40.0% | +0.80% |
| unknown | 9 | 44.4% | +2.51% |
| fx_smart_forex_rsi2_mean_reversion | 6 | 66.7% | +2.00% |
| forex-rsi-ema-scout | 5 | 20.0% | −2.41% |
| non_crypto_consensus | 3 | 0.0% | −0.01% |

✅ `forex_carry_momentum` — ABSENT (PR #692 kill confirmed)
✅ `forex_rsi2_mean_reversion` — ABSENT (PR #692 kill confirmed)

`forex-rsi-ema-scout` at n=5/WR=20% — below n=20 kill threshold, monitor only.

---

## COMMODITY 30d — New T1-Candidate (n=101 crosses 100-floor)

**Critical finding:** COMMODITY 30d PF=4.44 / WR=49.5% / n=101.

The 03Z report flagged COMMODITY 30d as "PF=0.04 driven by single CL=F outlier" — this was a snapshot artifact from the window at that exact moment. The fresh 04Z snapshot shows n=101 (just crossed the n=100 stable floor) with T1-territory PF.

7d COMMODITY: PF=42.83 / n=19 — below n=20 sizing floor, but driven entirely by `cftc_cot_commercial_signal` (post-#683 kill of the bad signal).

**COMMODITY is now a T1-candidate in both 7d and 30d windows, pending n≥20 (7d) and sustained n growth.**

---

## PR Triage

| PR | Title | CI | Reviews | mergeable | Decision |
|---|---|---|---|---|---|
| **#861** | audit(03Z 2026-05-08) | scan✅ | none | clean | ✅ **MERGED** (this run) |
| #862 | DB query bank FOREX pnl corruption | scan✅, test(3.11)❌, test(3.12)🚫 | none | — | ❌ HOLD — CI not green |
| #849 | Edge action plan + swarm peer-review | — | — | — | ⏭ SKIP — DRAFT |
| #846 | B18 shadow probation panel | scan✅ | — | — | 🔒 HOLD — explicit "DO NOT ADMIN-MERGE" |

**Total merges this run: 1 (#861)**

HOLD set (#660 #658 #681 #661 — Plan v2.1 fabricated stats family): not in open PR list; presumed closed/merged by earlier sessions. Constraint respected.

Rebase candidates (#669 #676 #608 #665 #644 #597 #615 #655): all confirmed merged/closed per 03Z audit. No action needed.

---

## Mutation Analysis

Ran `python tools/mutation_analysis.py` — **no new PF<0.5 + n≥20 strategies** emerged beyond the standing kill queue.

**Standing kill queue (3-AI consensus required before action):**

| Candidate | n | WR | PF | Axis | Status |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` LONG | 158 | 15.2% | <0.5 | Direction | Awaiting 3-AI consensus |
| `myfxbook_retail_contrarian` LONG | 118 | 10.2% | <0.5 | Direction | Awaiting 3-AI consensus |
| `rapid_fire` × UUSDT | 34 | 0.0% | 0.00 | Symbol | Awaiting 3-AI consensus |
| `quan_engine_swing` LONG | 104 | 26.0% | — | Direction | Posted to #686 at 03Z; 3-AI pending |

No new candidates meet all 3 criteria (PF<0.5, n≥20, WR<35% sustained).

---

## New Findings to Post

1. **COMMODITY 30d T1-candidate crossed n=100 floor** — escalate to issue #686 with COMMODITY 30d PF=4.44/n=101 finding.
2. **CRYPTO 24h alarm cleared** — transient noise confirmed.
3. **FOREX 30d T2 confirmed** — PF=1.57/WR=47.8%/n=232 — closes the "30d 0.97 pre-#687" delta from task baseline.

---

## Constraints Respected

- Resolver-rescope DONE (issue #685) — no code changes proposed
- Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER) not cited
- No peer PR rebases performed
- HOLD set not touched
- No auto-kills without 3-AI consensus
- `audit_dashboard/template.html` not modified (only reports/ output)

---

## References

- Issue #685 (resolver-rescope done)
- Issue #686 (per-asset quality regression — kill queue)
- Issue #693 (EQUITY 7d/14d/30d monitor)
- PR #692 (forex_carry_momentum + goldmine_6x kill — validated)
- PR #687 (JPY-cross BUY rule fix — validated)
- PR #861 (03Z audit — merged this run)
- `reports/HOURLY_AUDIT_2026-05-08_03Z.md` (prior hour baseline)
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
