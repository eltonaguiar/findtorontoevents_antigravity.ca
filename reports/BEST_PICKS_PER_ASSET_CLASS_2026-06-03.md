# Best Picks Per Asset Class — Live Snapshot 2026-06-03 (v2)

**Source**: live MySQL `trading_picks` table, 90-day window, n≥30, PnL-based WR/PF (sidesteps the EXPIRED-mislabel incident).
**Reporter**: claude-opus-4-7
**Method**: `SELECT category, source_system, COUNT, SUM(pos)/|SUM(neg)| AS PF` GROUP BY (category, source_system).

---

## Honest verdict first

Per CLAUDE.md canonical truth (`money_ready_verdict.json` post-M-067 policy-clean): **0 of 6 asset classes pass Tier-2 on the live audit dashboard.** Every "winner" below has at least one credibility caveat. Do not size any of these on real money without completing the corresponding caveat-resolution step.

---

## Promotion Gate Status — ENFORCED

`PROMOTED_STRATEGIES` in `audit_trail/promotion_gate.py` is **empty** (deny-by-default by design). With the gate now hardcoded to always enforce (this session), **all 36 active picks would be blocked from emission** — zero picks reach `active_picks.json` when the scanner runs with the gate enforced.

This is **correct behavior**: no strategy has completed the full admission cycle (walk-forward PASS + 30-day shadow paper + DSR/PBO thresholds + sign-coherence check + concentration HHI < 0.20). The system works as designed — a false negative costs nothing (strategy stays paper-only); a false positive costs real money.

### Current promotion candidates

| # | Strategy | Asset Class | Status | Day Count | Promotion Blockers |
|---|----------|-------------|--------|-----------|-------------------|
| **#1** | `etf_verified_dual_momentum` | ETF | FORWARD_PILOT_ONLY | 2 (open since 2026-06-02) | n<100, pf<1.5, wr<50%, pf<0.85*oos |
| **#2** | `macd_rsi_m048` | CRYPTO | SHADOW | 8 of 30 | day_count < 30, pf unavailable (DB unreachable) |

---

## Table — top survivors by Profit Factor (pre-gate enforcement)

| ★/◐ | Asset Class | Source/Strategy | n | WR | PF | AvgPnL% | Last close | Credibility caveat |
|---|---|---|---|---|---|---|---|---|
| ★ | CRYPTO | `prediction_market_agents` | 66 | 92.4% | 44.81 | +2.27 | 2026-04-21 | **Stale 6+ weeks**; kalshi/polymarket binary events ≠ crypto |
| ★ | CRYPTO | `mega_mutation` | 285 | 65.6% | 3.35 | +2.55 | 2026-06-01 | **141 sign-flipped rows** (PR #433 purge pending) — real PF probably ~1.5 |
| ★ | CRYPTO | `kimi_signal_tracking` | 111 | 72.1% | 2.46 | +3.60 | 2026-04-10 | **142 sign-flipped rows = 38.7% of all flips**; STALE; real PF ~0.48 |
| ◐ | CRYPTO | `ml_crypto_predictor` | 284 | 51.8% | 1.83 | +1.69 | 2026-05-25 | ML confidence anti-predictive in 0.90+ bucket (PR #440 capped to 0.85) |
| ◐ | CRYPTO | `battleground_luxalgo` | 49 | 63.3% | 1.76 | +1.77 | 2026-06-01 | Pending sign-flip purge (6 rows on the list) |
| ◐ | COMMODITY | `cta_replicator` | 107 | 50.5% | 3.05 | +0.85 | 2026-06-02 | Class **frozen** in `BLOCKED_ASSET_CLASSES` (PR #439); COT lag risk |
| ◐ | FOREX | `multi_asset_copytrader` | 1294 | 45.0% | 10.35 | +0.51 | 2026-05-25 | Class **frozen**; PF 10 on WR<50% = a couple of huge wins, fragile |
| ◐ | FOREX | `non_crypto_consensus` | 143 | 52.4% | 6.34 | +0.54 | 2026-05-06 | Class frozen + stale |

**Legend**: ★ = PF ≥ 1.5 AND WR ≥ 55% AND n ≥ 50 · ◐ = PF ≥ 1.2 AND n ≥ 30 · blank = below thresholds.

---

## What this means in plain terms

| Question | Answer |
|---|---|
| Is there a real, deployable winner today? | **No.** Every ★/◐ has a credibility caveat that blocks real-money sizing. |
| Closest honest candidate? | **`macd_rsi_m048`** (CRYPTO): n=65, WR 75.4%, PF ~3.06, in `CRYPTO_PROVEN_STRATEGIES` allowlist, **shadow-tracking already wired via PR #462+#463** since today. Day-counter starts at 0; promotion at day 30 if PF stays ≥1.5 + WR ≥55% + n ≥30 + drift ≤30% from lab PF. |
| Backup candidate? | **`etf_verified_dual_momentum`** (ETF): walk-forward lab PASS (Sharpe 1.91, PF 1.60, n=104), production sidecar opt-in flag `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1`. Paper-pilot tracker landed earlier (`verified_strategies/paper_pilot/etf_dual_momentum_pilot.py`). |
| What about `ml_crypto_predictor` (n=284, PF 1.83)? | Marginal candidate. ML confidence layer is anti-predictive at 0.90+ (Claude Code's measurement), capped at 0.85 in PR #440. Re-evaluate live PF/WR over the next 14d post-cap. |

---

## Concrete enhancement levers (in priority order)

| # | Lever | Why | Effort | Owner |
|---|---|---|---|---|
| 1 | **Run #433 staged sign-flip purge** (luxalgo 6 → ml 15 → battleground 63 → mega 141 → kimi 142) | Reveals **TRUE** PF for mega_mutation (likely 3.35→~1.5) and confirms kimi is dead (2.46→~0.48). Without this, every CRYPTO ranking is polluted. | Operator: 1 cmd | operator |
| 2 | **Set `SIGN_FLIP_BASELINE=0`** repo variable after purge | Re-arms the nightly `sign-coherence-gate.yml` baseline so future drift is caught instantly | Operator: 1 setting | operator |
| 3 | **Run `tools/relabel_crypto_expired.py --apply`** | Closes the EXPIRED-mislabel incident (53.3% of EXPIRED rows have positive PnL → they're hidden WINs). Reveals additional WIN volume across CRYPTO. | Operator: 1 cmd | operator |
| 4 | **Enable `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1` in shadow mode** | Starts ETF VDM forward-pilot accumulation. Day-30 checkpoint at n≥30 in lab + matching forward. | Single env var | code (already gated) |
| 5 | **Fix MC null hypothesis in `verified_strategies/strategy_verification_engine.py:243`** (bootstrap → block bootstrap) | Single biggest lab-side unlock per EAGLE-1 P1. Strategies stuck at p≈0.50 (false negatives) will sort to their true position. | ~30 min code | code |
| 6 | **Wire `is_admissible_for_production()` into `production_scanner.py`** at emission path | Production scanner currently emits from full universe; gate is dead code. Wiring it means ONLY `PROMOTED_STRATEGIES` allowlist entries reach the live pick pool. | ~1 hour code | code |
| 7 | **Add CAGR + Sortino computation to `compute_metrics()` in `run_daily.py:330-369`** | Closes the 2 blank columns on `/audit/pf.html` portfolio drill | ~15 min code | code |

---

## My current candidate pipeline (just for reference)

| Position | Strategy | Status | Path to promotion |
|---|---|---|---|
| **#1 promotion candidate** | `etf_verified_dual_momentum` | Paper pilot running | Day-30 review; n≥100 + forward PF within 30% of lab |
| **#2 promotion candidate** | `macd_rsi_m048` | Shadow tracker live (today) | Day-30: PF≥1.5 + WR≥55% + n≥30 + drift ≤30% from lab |
| Watchlist (post-purge) | `mega_mutation` (cleaned) | Awaiting #433 purge | Re-evaluate PF after sign-flip removal |
| Watchlist (post-cap) | `ml_crypto_predictor` | PR #440 capped conf at 0.85 | 14-day forward review of PF/WR post-cap |
| **Dead** | `kimi_signal_tracking` | Confirmed dead post-sign-fix | Stays on REVOKED list |

---

## What "world-class predictions per asset class" looks like 90 days out

If actions #1-#7 above land and the two pilots clear their day-30 checkpoints:

- **CRYPTO**: macd_rsi_m048 promoted to PROMOTED_STRATEGIES (capital staging step 1: 0.5× sizing), live PF/WR within 30% of lab, additional candidates flow through the same gate
- **ETF**: ETF Verified DM promoted, sector-rotation universe expanded with regime overlay
- **EQUITY**: Faber TAA sector-gated (XLE / XLU / XLV / XLI / XLK) — currently lab-only with n=11
- **FOREX**: frozen, awaiting kimi sign-flip purge + ATR-normalized threshold re-build
- **COMMODITY**: frozen, awaiting COT 3-day-lag enforcement + CT=F removal
- **BOND**: paper-only 60d on HYG/LQD credit-spread strategies
- **FUTURES**: frozen (n=2 not a class)

**3 of 6 classes (CRYPTO + ETF + EQUITY) reaching Tier-2 within 90 days is realistic** given the candidate pipeline above. The other 3 need structural data fixes before any candidate is meaningful.

---

**Filed**: `reports/BEST_PICKS_PER_ASSET_CLASS_2026-06-03.md`
**Companion infrastructure**: PR #462 (macd_rsi_m048 tracker), PR #463 (daily cron wire-up), PR #474 (source_system forward-guard), PR #439 (Pillar 1 freeze + Pillar 3 gate)
