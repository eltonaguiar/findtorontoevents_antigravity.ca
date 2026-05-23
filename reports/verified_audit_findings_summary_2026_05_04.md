# Verified Audit Findings — Master Summary (2026-05-04)

This is the canonical "what's real" doc. Cross-tabulates every numeric claim made by external sources (Kimi, Hermes, Comet, prior swarms) and internal code comments against live verification on `alpha_engine/data/closed_picks.json` (n=7,472), `audit_dashboard/data/dashboard_data.json`, and feature registries.

## Verification scoreboard (11 prior claims)

| # | Source | Claim | Verdict | Live data |
|---|---|---|---|---|
| 1 | AHF-02 (Claude swarm, conf 0.97) | "60/60 active picks have null take_profit" | **REJECTED** | 0/60 picks null |
| 2 | Kimi C1 | "R:R 1.5-2.0 = golden zone, PF 5.81" | **REJECTED** | Live PF 0.36 (worst band) |
| 3 | `quality_gates.py:2492-2511` "DATA CORRECTED 2026-04-01" | "R:R 1.0-1.5 = 70.8% WR best" | **REJECTED** (stale) | Live 46.3% (n=7,472 vs original n=1,868) |
| 4 | Hermes Round-1 | "5 stale crypto strategies, last pick 2026-04-08" | **UNVERIFIABLE** | 0 strategies match in `closed_picks.json` |
| 5 | Comet | "Conf sweet spot 0.75-0.79 = 86% WR" | **REJECTED** | Live n=93, WR 38.7%, PF 0.69 |
| 6 | Comet | "Conf >=0.90 worse than random" | **DEGENERATE** | n=1 in 7,472 picks |
| 7 | Comet | "Trust 6-7 = 77% WR vs 0-1 = 33.8%" | **SCHEMA FABRICATED** | `trust_score` field doesn't exist; only `trust_tier` (3 picks) |
| 8 | Comet | "SHORT dramatically outperforms LONG" | **CLOSE but both PF<1** | LONG 29.8%/0.37 vs SHORT 46.3%/0.65 |
| 9 | Comet | "1 of 46 ML features active" | **REJECTED** | 9/40 in schema; 9/18 in trained model. Direction right, ratio sensational |
| 10 | Comet | "Battleground DNA: 62% WR, +161% PnL" | **REJECTED** | No strategy by that name. Closest aggregate: 57.8% WR / +28.58pp / PF 1.84 / n=109 |
| 11 | Comet | "DOTUSDT dominates portfolio PnL" | **REJECTED** | DOTUSDT is rank #7. **TRXUSDT actually dominates at -$36,151 (117% of total loss)** |

**Box score:** 0/11 fully verified at face value. 1 close-but-unprofitable, 5 outright rejected, 2 schema/data-fabricated, 2 degenerate (n too small), 1 close-but-magnitude-wrong.

This is a meta-finding worth its own bullet: **the audit dashboard's surrounding narrative has been carrying multiple incorrect numeric claims simultaneously** — internal code comments, external auditors, and AI swarm engines all contribute. Always grep-cite + recompute before merging anything tier-changing.

---

## Findings that DID verify (or surfaced during verification)

These are the actionable, grep-citable, sample-sized findings that emerged from the four investigation rounds. **Each is the basis for a small targeted PR.**

### 1. LONG conf [0.80, 0.85) is a real edge band

- **Live**: n=120, WR 62.5%, PF 5.83, +0.082% avg PnL
- Adjacent bands far worse: [0.75, 0.80) PF 0.69, [0.85, 0.90) sample-thin
- Comet pointed to the wrong bucket but the correct phenomenon (a confidence sweet-spot does exist)
- **Action**: confidence-shaping function in `audit_trail/quality_gates.py` — bonus for [0.80, 0.85), neutral elsewhere, no penalty for >=0.90 (sample too small to penalize)
- Companion SHORT [0.75, 0.80): n=21, PF 2.44 — second profitable cell, smaller sample

### 2. TRXUSDT is the dollar-loss concentration risk (NOT DOTUSDT)

- **Live**: TRXUSDT contributes -$36,151 across closed picks = **117% of total absolute loss** (i.e., other symbols net positive but TRXUSDT alone exceeds the aggregate loss)
- Comet (and prior session lore) tagged DOTUSDT — DOTUSDT is rank #7 by abs(pnl_pct) at 6.9%
- **Action**: `BLOCKED_SYMBOLS = ["TRXUSDT", ...]` in `alpha_engine/scanner.py` or position-sizer cap to 0.5%. Per CLAUDE.md mutate-before-kill, run `tools/mutation_analysis.py --json --symbol TRXUSDT` first.

### 3. `ml_enhanced_FETUSDT_1d_B_lightgbm` is buried elite

- **Live**: PF 9.43, +7.59pp, n=44 — meets Tier-1 PF, sample size approaches T2 floor
- Currently tagged `asset_class=UNKNOWN`, so it doesn't surface in any per-class panel
- **Action**: ensure it's in `tier2_proven_strategies` once asset_class=CRYPTO is back-filled (see #5)

### 4. CT=F (cotton) drives the COMMODITY R:R 1.0-1.5 PF 7.99 entirely

- **Live**: 71 of 72 picks (98.6%) in that band are CT=F. KC=F (1 pick) lost.
- Note: COMMODITY card on `/audit` already has a concentration warning, but it's pinned to KC=F (147% of class PnL via `system_clean_metrics`). That's a different cohort. The R:R-band cohort concentration is on CT=F.
- **Action**: dual-symbol concentration disclosure on COMMODITY card (CT=F + KC=F).

### 5. Asset-class tagger gap — 92% UNKNOWN

- **Live**: 6,886 of 7,472 closed picks have `asset_class="UNKNOWN"`
- This single bug washes out every per-class metric on `/audit` (already disclosed in Tier-A #2 PF footnote, but the root cause is upstream)
- **Action**: highest-EV follow-up. Likely fix in `audit_trail/dashboard_generator.py::_normalize_asset_class()` or `_resolve_asset_class()`. After fix, regenerate `closed_picks.json` and re-run the per-asset R:R slice — many "UNKNOWN" picks are likely CRYPTO and may yield a real per-class signal.

### 6. ML feature dormancy — 9/40 (or 9/18 in trained model)

- **Live**: `feature_importance.json` shows 9 of 18 features have nonzero weight; `ml_ranker.py:344-418` declares 9 of 33; v2 schema has 40 fields with 9 active
- Direction is right (lots dormant), ratio is sensational
- **Action**: cull the 9 dormant funding/OBI features OR retrain with them activated — defer until upstream ML retraining cycle

### 7. R:R no usable global gate

- **Live**: every R:R band with n>30 has PF < 1.0 cross-class
- Per-asset slice yielded only one apparent signal (COMMODITY 1.0-1.5) which collapsed under symbol-concentration scrutiny (CT=F fluke)
- **Action**: ship `feat/rr-hard-gate-shadow-2026-05-04` as **Option D (diagnostic-only logger)** for 14d. Don't enforce. Update `quality_gates.py:2492-2511` to drop the +10/0/-5/-10 score adjustments (acting on stale numbers). See `reports/rr_band_reaudit_2026_05_04.md` + `reports/rr_band_per_asset_2026_05_04.md`.

### 8. EQUITY raw-vs-capped 10× gap

- Already surfaced in audit hyperfocus AHF-06 + shipped as inline tooltip in `df7a8729746`
- **Verified**: `system_clean_metrics.alpha_engine.total_pnl_raw=363.32` vs `total_pnl_capped=35.71` per `dashboard_data.json`
- **No new action** — already disclosed.

---

## Patterns across the verification rounds

1. **Round numbers are suspicious.** Every claim using a round percentage (62%, 77%, 86%, 161%) was rejected or off. Real edges have less round numbers (62.5%, 5.83 PF, 117% of total loss).
2. **Schema names are often wrong.** Comet referenced `trust_score` (doesn't exist), confused per-pick conf with rolling-WR conf, conflated raw-PnL and capped-PnL. Always grep the field before citing it.
3. **Single-symbol flukes look like alphas.** Both COMMODITY-1.0-1.5 (CT=F 71/72) and any "asset class X has edge" claim need a per-symbol breakdown before being trusted.
4. **n<30 is meaningless.** Multiple claims (Hermes Round-1 NBA +164% on n=3; Comet conf>=0.90; Kimi BOND PF 25.9 on n=8) all collapse on sample-size check.
5. **Stale internal comments are as bad as fabricated external claims.** The 2026-04-01 "DATA CORRECTED" comment in `quality_gates.py` was correct against an older sample but became wrong after the data grew. Code comments need timestamps + sample-size — and someone needs to re-verify them periodically.

## What this means for the multi-Claude session

- **`feat/audit-score-tooltips-2026-05-04`** branch (now 13 commits, tip `b38de66b74d`) is the consolidated outcome of this session. It ships the verified narrative + tooltips + per-asset n-guard + hyrotrader credibility fixes.
- **`feat/rr-hard-gate-shadow-2026-05-04`** branch (`149fbacd375`) must be REWRITTEN before merge — currently targets the worst R:R band per live data. Recommend Option D (diagnostic-only logger).
- **The 5 ready-for-PR branches** are still ready: `feat/rr-hard-gate-shadow`, `fix/today-tomorrow-week-zero-events`, `fix/sports-stale-data-hardening`, plus the new `chore/super-swarm-synthesis` and `feat/audit-score-tooltips`.

## Recommended next PRs (in priority order)

1. **`fix/asset-class-tagger-2026-05-04`** — close the 92% UNKNOWN gap. Single highest-EV change.
2. **`feat/audit-confidence-sweet-spot-bonus-2026-05-04`** — wire LONG [0.80, 0.85) bonus into `quality_gates.py`. Small, targeted, evidence-cited.
3. **`block/symbol-trxusdt-2026-05-04`** — add TRXUSDT to BLOCKED_SYMBOLS pending mutation analysis. Per CLAUDE.md.
4. **`fix/quality-gates-rr-band-recalibration-2026-05-04`** — remove the stale +10/0/-5/-10 R:R score adjustments.
5. **`feat/rr-diagnostic-logger-2026-05-04`** — Option D, 14d shadow log without filtering.
6. **`fix/audit-dashboard-concentration-warnings-2026-05-04`** — surface TRXUSDT, CT=F, KC=F concentrations explicitly on the dashboard.

## Evidence trail

| Report | Purpose |
|---|---|
| `reports/super_swarm_synthesis_2026_05_04.md` | 3-surface super-swarm (origin) |
| `reports/null_take_profit_investigation_2026_05_04.md` | AHF-02 fabrication discovered |
| `reports/rr_band_reaudit_2026_05_04.md` | Both Kimi C1 and 2026-04-01 comment rejected |
| `reports/rr_band_per_asset_2026_05_04.md` | CT=F single-symbol fluke discovered; Option D recommendation |
| `reports/comet_claims_verification_2026_05_04.md` | Comet conf-band + trust-band rejected |
| `reports/comet_strategy_verification_2026_05_04.md` | TRXUSDT + ml_enhanced_FETUSDT discovered |
| `reports/verified_audit_findings_summary_2026_05_04.md` | **This file** — master summary |
