# Copy Trading & Prediction Markets — Corrected Findings

**Date:** 2026-11-15 (AM)
**Status:** CORRECTS earlier claim that "copy trading and prediction markets have not produced winners" — and CORRECTS the subsequent claim that "COMMODITY copy-trader WR=93.8% is a real edge"
**Source:** Ground-truth verification against `alpha_engine/data/closed_picks.json`, `reports/commodity_deep_dive_swarm_2026-05-16.md` (retraction), `groksstuff.txt` (DB-level data)

---

## Executive Summary

**Both earlier claims were wrong.**

1. **First claim** ("copy trading and prediction markets have not produced winners") was too broad — prediction markets do show promising forward results (WR=79.09%, n=110, shadow mode), but PBO=0.603 blocks deployment.

2. **Second claim** ("COMMODITY copy-trader WR=93.8% is a real edge") is **debunked**. Ground-truth verification against `closed_picks.json` shows all 186 COMMODITY copy-trader picks were force-closed toxic with pnl=0 — zero resolved trades. The 93.8% claim was formally retracted on 2026-05-16 as a pre-dedup over-emission artifact.

**Bottom line: No asset class has a proven edge.** Copy trading COMMODITY is blocked (all force-closed toxic). Prediction markets are promising but unproven (PBO=0.603). All 9 asset classes remain `sizing_allowed: false`.

---

## Ground Truth from closed_picks.json

**File:** `alpha_engine/data/closed_picks.json` (503 total picks)

Picks where `source_system` contains "copytrader" — only `multi_asset_copytrader` matches (377 picks).

#### By asset class for `multi_asset_copytrader` (Ground Truth)

| Asset Class | Total | WON | LOST | FLAT | CLOSED (toxic) | WR (win/loss resolved) | WR (win/total) | Status |
|-------------|-------|-----|------|------|----------------|------------------------|----------------|--------|
| **COMMODITY** | **186** | **0** | **0** | 0 | 186 | **0.0%** | **0.0%** | ❌ All force-closed toxic |
| FOREX | 160 | 20 | 23 | 95 | 117 | 46.5% | 12.5% | ❌ Massive drag |
| **FUTURES** | **31** | **0** | **0** | 0 | 31 | **0.0%** | **0.0%** | ❌ All force-closed toxic |

#### COMMODITY picks — all 186 have identical resolution profile:
- `status`: `"CLOSED"` (never `"WON"` or `"LOST"`)
- `pnl_pct`: `0.0`
- `pnl_dollar`: `0.0`
- `exit_reason`: `"FORCE_CLOSED_TOXIC"`
- `_wr_excluded`: `true`
- `_wr_excluded_reason`: `"force_closed_toxic_admin"`

**Meaning: Zero of the 186 COMMODITY picks were ever resolved with an actual trading outcome.** There is no win rate to calculate — the denominator of resolved trades is 0.

#### COMMODITY symbols (186 picks across 8 symbols):
| Symbol | Count |
|--------|-------|
| SI=F (Silver) | 68 |
| PL=F (Platinum) | 68 |
| HG=F (Copper) | 42 |
| SB=F (Sugar) | 2 |
| KC=F (Coffee) | 2 |
| ZS=F (Soybeans) | 2 |
| CL=F (Crude) | 1 |
| ZC=F (Corn) | 1 |

---

## The 93.8% WR Claim — Where It Appears and Why It's Wrong

**Where the claim appears (all in plan/audit documents):**

| File | Line | Claim |
|------|------|-------|
| `archive/2026-05-31_testing_protocol_dedupe/reports_money_maker_ready_20260515T211949Z.md` | 212 | `multi_asset_copytrader` (COMMODITY only) \| 96 \| 93.8% \| est >3.0 |
| `WIRED_IN/.../algorithm_spec_commodity.md` | various | WR=93.8% (n=96) — pristine win rate |
| `WIRED_IN/.../justification_per_asset_class.md` | various | COMMODITY — WR 93.8-94.1%, n=96-102 |
| `WIRED_IN/.../elimination_log.md` | various | multi_asset_copytrader COMMODITY — WR=93.8%, n=96, real edge |

**The claim was DEBUNKED on 2026-05-16 as a pre-dedup artifact:**

| File | Line | Refutation |
|------|------|------------|
| `reports/commodity_deep_dive_swarm_2026-05-16.md` | 200 | WR 93.8% measured **before** COT dedup fix and is inflated. Post-dedup: WR~40%, PF~0.17. |
| `reports/commodity_deep_dive_swarm_2026-05-16.md` | 206 | REMOVED 2026-05-16: multi_asset_copytrader (WR 93.8% was CT=F over-emission artifact) |
| `reports/2026-05-25_policy_clean_vs_top_edges_funnel.md` | 86 | REMOVED 2026-05-16 after swarm deep-dive proved WR=93.8% PF=20.54 was pre-dedup artifact (46× over-emission on CT=F cotton). Post-dedup cell collapsed to WR=40% PF=0.17. |

**Current DB-level data** (`groksstuff.txt:1588`): commodity `multi_asset_copytrader` n=635 WR=34.3% PF=0.74 — consistent with a losing strategy, not a 93.8% winner.

**Current `closed_picks.json`**: 186 COMMODITY picks, ALL unresolved (status=CLOSED, pnl=0, force_closed_toxic) → WR is undefined (0/0 resolved), effectively 0%.

---

## Per-Class CopyTrader Results (Ground Truth vs. Audit Report)

| Class | Audit Report Claim | Ground Truth (closed_picks.json) | Discrepancy |
|-------|-------------------|----------------------------------|-------------|
| COMMODITY | n=96, WR=93.8% | n=186, WR=0% (all force-closed toxic) | Claim is false — all picks unresolved |
| EQUITY | n=28, WR=42.9% | n=28, WR=42.9% | Matches |
| FOREX | n=662, WR=14.8% | n=160, WR=12.5% (win/total) | n differs (662 vs 160) — audit report may include open picks |
| FUTURES | n=157, WR=2.5% | n=31, WR=0% (all force-closed toxic) | Claim is false — all picks unresolved |

---

## Prediction Markets (Kalshi / Polymarket) — Shadow Mode Candidate

**Source:** `backtest_results/rigorous_backtest_CRYPTO_20260602_124831.json`, `verified_strategies/paper_pilot/`

### Performance Data

| Source | Metric | Value |
|--------|--------|-------|
| Backtest | n | 89 |
| Backtest | WR | 89.89% |
| Backtest | PF | 24.51 |
| Backtest | DSR | 9.36 |
| Backtest | **PBO** | **0.603** ⚠️ (above 0.10 gate) |
| Walk-forward | 7 folds, all WFE=1.0 | avg_os_sharpe=1.39 |
| Paper pilot | resolved n | 837 |
| Paper pilot | WR | 64.76% |
| Paper pilot | PF | 2.02 |
| Paper pilot | max_drawdown | -69.17% |
| Forward dashboard | n | 110 |
| Forward dashboard | WR | 79.09% |
| Forward dashboard | PF | 13.20 |
| Forward dashboard | shadow_mode | true |

**Critical Concern: PBO=0.603**

PBO (Probability of Backtest Overfitting) = 0.603 means there's a ~60% probability the backtest results are overfitted. This is **above the 0.10 threshold** required for money-ready deployment.

**Recommendation:** Prediction markets are promising but NOT yet money-ready due to PBO > 0.10. Continue shadow mode forward testing. Kill switch: WR floor 55%, n_min 50. Currently `pick_count: 0` — not emitting live picks.

---

## Recommended Actions

| ID | Action | Priority |
|----|--------|----------|
| Block `(FUTURES, multi_asset_copytrader)` | P0 — all 31 picks force-closed toxic, WR=0% | DONE (quality_gates.py line 2715) |
| Block `(COMMODITY, multi_asset_copytrader)` | P0 — all 186 picks force-closed toxic, WR=0% | PENDING |
| Mutate-before-kill `(FOREX, multi_asset_copytrader)` | P1 — 160 picks at 12.5% WR needs axis analysis | PENDING |
| Continue prediction market shadow mode | P1 — PBO=0.603 blocks deployment | ONGOING |
| Wire prediction markets into primary pick emission | P2 — currently pick_count=0 | PENDING |

---

## Files Referenced

| File | What It Contains |
|------|-----------------|
| `alpha_engine/data/closed_picks.json` | Ground truth — 503 picks, 377 with multi_asset_copytrader source |
| `reports/commodity_deep_dive_swarm_2026-05-16.md` | Retraction of 93.8% WR claim |
| `groksstuff.txt:1588` | DB-level data: commodity multi_asset_copytrader n=635 WR=34.3% PF=0.74 |
| `backtest_results/rigorous_backtest_CRYPTO_20260602_124831.json` | Prediction market consensus backtest |
| `verified_strategies/paper_pilot/prediction_market_consensus_pilot.json` | Paper pilot results |
| `verified_strategies/paper_pilot/prediction_market_consensus_dashboard.json` | Forward dashboard |
| `audit_trail/quality_gates.py` | Blocking mechanism (line 2715: FUTURES copy-trader blocked) |
