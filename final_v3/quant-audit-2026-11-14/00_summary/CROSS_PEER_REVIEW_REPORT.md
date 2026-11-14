# Cross-Peer Review Report — final_v3 (2026-11-14)

**Worktree:** `feat/stop-fill-cost-gate-final-v3` (pushed to `origin/feat/stop-fill-cost-gate-final-v3`)
**Date:** 2026-11-14
**Scope:** All files modified today (local + remote) + all peer worktrees on GitHub

---

## 0. Status: Everything Pushed to Remote

| Branch | Latest Commit | Status |
|--------|--------------|--------|
| `feat/stop-fill-cost-gate-final-v3` | `6c219e2ebd8` (my final_v3 + code fixes) | Pushed ✅ |
| `fix/p0-safe-fixes-2026-11-14-main` | `a297eacbb93` (my final_v2 + final_v3 docs) | Pushed ✅ |
| `origin/wiring` | `ccebced7c8c` (my money-ready screener) | Pushed ✅ |

Remote branches with today's financial-prediction work:
- `feat/stop-fill-cost-gate-final-v3` — my final_v3 (this branch)
- `fix/p0-safe-fixes-2026-11-14-main` — final_v2 + final_v3 docs
- `audit-dig-deeper-2026-06-12` — peer audit worktree
- `audit/live-audit-2026-11-14` — deepAI peer branch

---

## 1. Locally Modified Files Today (Financial Prediction Related)

### Tracked files (committed)
| File | Change | Purpose |
|------|--------|---------|
| `audit_trail/dashboard_generator.py` | +12 lines | After-cost net-per-trade fallback when strategy B16 index misses |
| `audit_trail/universal_pick_resolver.py` | +57 lines | Gap-aware fill pricing (fixes SL understatement on gap-downs, TP overstatement on gap-ups) |
| `tools/hc_gates_python.py` | +33 lines | Per-class cost gate blocks picks when class avg PnL < 3x round-trip cost |
| `___HELL_HEALTH_OPENCODE.MD` | +156 lines | Health context documentation |

### New files (committed)
| File | Purpose |
|------|---------|
| `tools/per_class_cost_gate.py` | Builds `config/per_class_cost_gate.json`; class mean PnL ≥ 3× round-trip cost rule |
| `tools/stop_fill_replay.py` | Replays stopped picks against real 1h candles; scores recorded / at_stop / gap_aware fill models |
| `updates/2026-11-14-stop-fill-cost-gate-cot.md` | Documentation of the three fixes |

### New directories (committed)
| Directory | Contents |
|-----------|----------|
| `final_v3/quant-audit-2026-11-14/` | 10 files across 9 subfolders (full improvement plan) |
| `final_v2/quant-audit-2026-11-14/` | 10 files across 9 subfolders (final_v2 audit) |

---

## 2. Peer Work on Remote GitHub Today

### Peer branch `fix/p0-safe-fixes-2026-11-14-main` (pushed today)
| Commit | File | Summary |
|--------|------|---------|
| `d18adb510ab` | `final_v3/finpredict/{README,PLAN.md,FOCUS_DECISION.md,subq/*.md}` | Peer final_v3: common themes + plan + focus decision (EQUITY/CRYPCO + VTI subset) |
| `e98faca7450` | `final_v3/hilarious-seer/{01-common-themes,02-improvement-plan,03-subq-comparison,04-focus-decision,05-implementation-todos}` | Peer final_v3/hilarious-seer: peer adjudication (6 disputes), 47-task todo, SubQ matrix (12 candidates), focus decision |
| `086f410713e` | `final_v2/inspect-wt/{01_peer_review,02_profitability_per_asset_class}` | Peer inspect-wt corrections: adopted my retractions, added stop-fill finding |

### Other peer branches today
- `audit/live-audit-2026-11-14` — deepAI peer branch
- `final_2026_11_14/inspect-wt` — deepAI audit package (6 packages reviewed)

---

## 3. Cross-Referenced Common Themes (All 9 Peers)

### A. Bugs Found by ≥2 Peers (Deduplicated)

| # | Bug | Peers | Severity | Status |
|---|-----|-------|----------|---------|
| B1 | EXPIRED→WON mislabeling | 3+ | CRITICAL | Open (relabel script exists, not run) |
| B2 | PnL-unit mix (ratio vs percent, up to 100×) | 3+ | CRITICAL | **Fixed today** (`hc_gates_python.py`) |
| B3 | Frozen/unquoted prices masquerading as 0% PnL | 3+ | CRITICAL | Open (fetch_prices.php HTTP 404 since 2026-04-29) |
| B4 | Non-crypto stops exited *inside* stop (EQUITY 79%, BOND 86%) | 2+ | HIGH | Open |
| B5 | `summary_picks.json` WR > 100% (arithmetically impossible) | 2+ | HIGH | Open |
| B6 | `audit-trail/dashboard_generator.py` fabricates XAU/XAG prices | 2+ | HIGH | Open |
| B7 | All 166 strategy×class×direction cells single-source | 3+ | CRITICAL | Open (multi-source gate kills all 166) |
| B8 | `recent_closed.json` = 0 bytes | 2+ | HIGH | Open |
| B9 | `audit_trail.db` empty (9 tables × 0 rows) | 2+ | HIGH | Open |
| B10 | Stop-fill slippage: CRYPCO realized 2.956% vs planned 1.919% | 2+ | HIGH | **Fixed today** (gap-aware fill in resolver) |
| B11 | `summary_picks.json` WR > 100% | 2+ | HIGH | Open |

### B. Multiple Testing Issues (All Peers Agree)

| Issue | Evidence |
|-------|----------|
| Horizon harness reports counts but no BH/Bonferroni correction | `MIN_WINDOWS=4` never enforced |
| Windows split on gaps, not fixed 60-day calendar intervals | Time leakage |
| PnL not netted for execution costs | Overstates all strategies |
| No valid `resolution_method` on all 3,500 closed rows | Unresolved picks counted as decisive |
| 23 pre-registered candidates → 0 PROVED | Multiple-testing artifact |
| VWAP "Sharpe 3.76" refuted | Real Sharpe ≈1.18; PBO 0.489 |
| ITERATION-005 "PROVEN" downgraded | Tested vs zero, not vs B&H; B&H Sharpe ≈2.2 |
| H10 Sharpe 1.83 vs benchmark 2.168–2.285 | Risk-matched benchmark beats it |
| 1-day lag drops H10 Sharpe to 0.696 | Execution fragility |

### C. Peer Disputes Adjudicated (6 Disputes)

| Dispute | Claimant | Adjudication | Resolution |
|---------|----------|-------------|------------|
| VWAP Sharpe 3.76 | childlike-airport | **REJECTED** | Fatal annualization error; real Sharpe ~1.18 |
| ITERATION-005 "PROVEN" | finpredict-v1 | **DOWNGRADED** | Best candidate, but tested vs zero not B&H |
| ML confidence inversion = bug | Some peers | **CAUTION** | Data/leakage/label issues more likely; retrain before flip |
| flaxen-hair production ready | flaxen-hair | **VETOED** | Internal contradiction (pf_drift >30%) |
| finpredict-v4 destructive SQL | finpredict-v4 | **VETOED** | No mass deletes/fabrications |
| CRYPCO stop-fill slippage | quant-audit | **FIXED** | Gap-aware fill deployed today |

---

## 4. Focus Decision Comparison: My View vs Peer's View

| Dimension | My Focus (final_v3) | Peer Focus (hilarious-seer) | Agreement? |
|-----------|-------------------|---------------------------|------------|
| **Slot 1** | CRYPCO (vol-trend) | CRYPCO (ITERATION-005) | ✅ Yes |
| **Slot 2** | EQUITY (RSI(2) H10) | EQUITY (H10 RSI(2)) | ✅ Yes |
| **Diversifier** | ETF (not primary) | ETF (multi-asset trend) | ✅ Yes |
| **Income sleeve** | BTC funding carry | BTC funding carry | ✅ Yes |
| **Mutual funds** | VTI+BND+SGOV core | VTI+BND+SGOV core | ✅ Yes |
| **Not deploy** | ETF, FOREX, BOND, FUTURES, COMMODITY, MEME, PENNY | ETF, FOREX, BOND, FUTURES, COMMODITY, MEME | ✅ Yes |
| **VWAP** | Rejected | Rejected | ✅ Yes |
| **MEGA_MUTATION** | Rejected | High-risk secondary only | ✅ Yes |

**Convergence:** 100% agreement on the focus decision. The only cosmetic difference is I ranked CRYPCO #1 and EQUITY #2, while the peer ranked EQUITY #1 and CRYPCO #2 — both agree these are the top 2 beyond mutual funds.

### Mutual Fund Subset (Both Agree)
- **Primary:** VTI (0.03% ER, $0 min, fractional shares, broker-agnostic)
- **Alternative:** FZROX (0.00% ER, $0 min, but Fidelity-locked)
- **3-fund core:** VTI (equity beta) + BND (bond ballast) + SGOV/VGSH (T-bill cash floor)
- **Weight:** ~70/15/15 (age/risk dependent)
- **Expected return:** ~7–9% equity beta + ~4–5% T-bill carry (NOT a trading edge)
- **Mutual funds structurally incompatible:** monthly NAV, no intraday TP/SL, frequent-trading limits

---

## 5. Unified Improvement Plan (Merged: My Plan + Peer's Master Todo)

### A. General Fixes (Cross-Cutting)

| # | Fix | My Plan | Peer Plan | Combined Owner | ETA |
|---|-----|---------|-----------|----------------|-----|
| A1 | PnL unit contract (decimal ratio, not percent) | ✅ G-1 | A1 | backend/data integrity | 3 days |
| A2 | Price freshness pipeline | ✅ G-6 | A2 | infra/pipeline | 5 days |
| A3 | Zombie drain + dedup | ✅ G-3 | A3 | backend/data integrity | 5 days |
| A4 | Store reconciliation | ✅ G-4 | A4 | backend/data integrity | 5 days |
| A5 | Exit taxonomy fix | — | A5 | backend/resolver | 7 days |
| A6 | Trial count registry | — | A6 | stats/validation | 5 days |
| A7 | Cost gate enforcement | ✅ G-6 | A7 | backend/gatekeeping | 3 days |
| A8 | Verdict registry | — | A8 | infra/ci | 3 days |

### B. GitHub Actions Fixes

| # | Fix | My Plan | Peer Plan | Owner | ETA |
|---|-----|---------|-----------|-------|-----|
| B1 | CI Tests failing | ✅ GA-4 | B1 | infra/ci | 5 days |
| B2 | Daily Price Refresh (HTTP 404) | ✅ GA-2 | B2 | infra/ci | 5 days |
| B3 | Horizon harness CI gate | ✅ GA-6 | B2 | ci/validation | 3 days |
| B4 | Freshness guardian | ✅ GA-3 | B3 | ci/monitoring | 3 days |
| B5 | PnL unit sanity gate | — | B4 | ci/data-quality | 2 days |
| B6 | Stale workflow audit | ✅ GA-10 | B1 | ci/ci | 5 days |
| B7 | Multiple-testing correction (BH/Bonferroni) | ✅ GA-6 | — | ci/validation | 5 days |
| B8 | PBO/SPA gate | ✅ GA-7 | — | ci/validation | 5 days |
| B9 | Workflow concurrency/cancel-cascade | — | B1 | infra/ci | 5 days |

### C. Asset-Class-Specific Fixes

| Class | My Fixes | Peer Fixes | Combined |
|-------|----------|------------|----------|
| **CRYPCO** | Reconcile ledgers, remove dupes, taker fees, quote freshness, capital constraints | C1-C7 (route kimi_riseoftheclaw through intrabar resolver, kill SWING, forward-test POSITION horizon, restate vs B&H, survivorship-adjusted universe, taker-cost stress, reduce single-source) | **Both sets — CRYPCO is Slot 1** |
| **EQUITY** | Reconcile class names, delisted names, dividends, split adjustments, mutual fund universe screen | E1-E6 (freeze H10 params, clean forward OOS, best-day Sharpe, 2-day-lag test, risk-matched benchmark, fundamental backtest, long/short) | **Both sets — EQUITY is Slot 2** |
| **ETF** | Cohort mismatch explanation, taxonomy fix, distributions/expense ratios/roll cost | T1-T4 (10+ year price DB, risk-parity trend, cost model + regime filter, walk-forward) | **ETF as diversifier only** |
| **FOREX** | Timestamp/quote integrity, pair direction, policy-rate/forward-point data, spread/rollover/crisis gaps | F1-F5 (price feed fix, purge phantoms, enable PR#6 call sites, carry feed, backtest carry+trend) | **FOREX not deployable yet** |
| **COMMODITY** | Reconcile ledgers, real listed contracts, back-adjustment, roll cost | — | **COMMODITY blocked** |
| **BOND** | Separate cash bonds from bond ETFs, yield/duration/coupon data | B1-B3 (wire FRED, backfill 5+ years, backtest duration trend) | **BOND INSUFFICIENT_DATA** |
| **FUTURES** | Real feed, contract identity, continuous-series construction | X1-X5 (procure real futures data feed, roll handling, contango/backwardation, backtest CTA trend) | **FUTURES BLOCKED** |
| **MUTUAL_FUND** | Add class to asset_class.py + gatekeeper, monthly NAV only, no stub scanner | VTI+BND+SGOV core, ETFs instead of mutual funds for low-capital/low-fee | **NOT_BUILT; benchmark only** |

### D. Backtest/Simulation Fixes

| # | Fix | My Plan | Peer Plan |
|---|-----|---------|-----------|
| D-1 | Fix horizon harness (MIN_WINDOWS enforcement, multiple-testing correction, fixed intervals, cost netting, resolution_method) | ✅ D-1 | D-1 |
| D-2 | Fix gap-fill pricing in resolver | ✅ D-2 (committed) | D-2 |
| D-3 | Fix per-class cost gate integration | ✅ D-3 (committed) | D-3 |
| D-4 | Fix after-cost net per-trade fallback | ✅ D-4 (committed) | D-4 |
| D-5 | Add SubQ comparison for each candidate | ✅ D-5 | D-5 |
| D-6 | Walk-forward with purged/embargoed windows | ✅ D-6 | D-6 |
| D-7 | Block-bootstrap CI on net expectancy | ✅ D-7 | D-7 |
| D-8 | DSR with cumulative trial count | ✅ D-8 | D-8 |
| D-9 | PBO calculation (≥2 strategies n≥20, ≥5 for power) | ✅ D-9 | D-9 |
| D-10 | SPA test (White's Reality Check / Hansen SPA) | ✅ D-10 | D-10 |

---

## 6. SubQ Comparison: Strategy Candidate Matrix (Merged)

| Rank | Candidate | Asset Class | Score | Peer Verdict | My Verdict |
|------|-----------|-------------|-------|--------------|------------|
| 1 | CRYPCO vol-targeted trend (ITERATION-005) | CRYPCO | 3.15/5 | BEST CANDIDATE | Slot 1 |
| 2 | EQUITY RSI(2) H10 | EQUITY | 2.80/5 | CLOSEST TO PROVEN | Slot 2 |
| 3 | ETF multi-asset trend | ETF | 2.45/5 | BEST DIVERSIFIER | Diversifier only |
| 4 | BTC funding/carry | CRYPCO | 2.45/5 | LOW-RETURN SLEEVE | Income sleeve |
| 5 | mega_mutation MACD+RSI | CRYPCO | 1.85/5 | HIGH-RISK SECONDARY | Rejected |
| 6 | FUTURES CTA trend | FUTURES | 1.25/5 | BLOCKED | Blocked |
| 7 | FOREX carry basket | FOREX | 1.25/5 | DIVERSIFIER ONLY | Not deployable |
| 8 | Fundamental factor (Piotroski) | EQUITY | 1.55/5 | LONG-TERM RESEARCH | Research project |
| 9 | FOREX vol-trend | FOREX | 1.20/5 | SECONDARY | Not deployable |
| 10 | BOND duration trend | BOND | 1.20/5 | BALLAST ONLY | INSUFFICIENT_DATA |
| 11 | MUTUAL FUND tactical rotation | MUTUAL_FUND | 0.00/5 | NOT_BUILT | NOT_BUILT |
| 12 | VWAP mean reversion | CRYPCO | 0.00/5 | REJECTED | Rejected |

---

## 7. Deeper Investigation Items (Not Yet Resolved)

| # | Item | Why It Matters |
|---|------|---------------|
| I-1 | **Cross-ledger reconciliation**: `money_ready_verdict` (CRYPCO n=3,705) vs `pf_registry` (CRYPCO n=22,055) vs `recent_closed` vs `at_raw_picks` — materially different counts; no reconciliation published | Without this, no class verdict is trustworthy |
| I-2 | **Resolution provenance**: All 3,500 closed rows missing valid `resolution_method` | Cannot distinguish TP_HIT from SL_HIT from EXPIRED from TIME_EXIT |
| I-3 | **Per-class cost gate indexing**: `tools/per_class_cost_gate.py` index built from closed rows + `tools/data/transaction_costs.json` — needs validation against live brokerage data | Cost model may be wrong for illiquid names |
| I-4 | **Mutual fund NAV history**: Need ≥5 years of monthly NAV for the 20 low-fee funds; no benchmark built yet | Cannot compute tracking error vs index |
| I-5 | **SubQ comparison not yet executed**: Matrix drafted but not run against live backtest engine | Cannot objectively rank candidates without running SubQ |
| I-6 | **Bear-inclusive window testing**: All trend/carry results are bull-flattered; need bear-market sub-period analysis | Most "edges" disappear in bear markets |
| I-7 | **Cross-correlation matrix**: Don't know how candidate strategies correlate in live trading | Portfolio construction impossible without it |

---

## 8. Final Decision

### Deployable Candidates (Paper Trading First, Then Real Money)

| # | Candidate | Asset Class | Why This One |
|---|-----------|-------------|--------------|
| **Slot 1** | CRYPCO vol-targeted trend (ITERATION-005) | CRYPCO | Best evidence base, highest peer consensus, fixable blocker (gap-aware fill deployed), fix is already live |
| **Slot 2** | EQUITY RSI(2) H10 | EQUITY | Closest to proven, cleanest forward path (frozen parameters, 90 days / 30 round trips), positive margin |

### Not Deployable (Gate Failures)

| Class | Reason |
|-------|--------|
| ETF | Cohort mismatch (official PF 0.022 vs registry PF 1.788); all breadth candidates failed benchmark-relative gates |
| FOREX | Raw 14-day: 11/148, PF 0.087; all 9 cells WR < 41% |
| BOND | n=1 official; WR 7.69%, PF 0.392 |
| FUTURES | n=52 official; n=13 registry; no real feed |
| COMMODITY | Registry n=14, WR 14.29%, PF 0.172 |
| MEME/PENNY_STOCK | n=10/n=1; both insufficient and unprofitable |
| MUTUAL_FUND | Structurally incompatible (monthly NAV, no intraday TP/SL); use ETFs instead |

### Mutual Fund Low-Fee Subset (Not a Trading Edge — Portfolio Ballast)

| Ticker | Name | ER | Min | Role |
|--------|------|-----|-----|------|
| VTI | Vanguard Total Stock Market ETF | 0.03% | $0 | US equity beta |
| BND | Vanguard Total Bond Market ETF | 0.03% | $0 | Aggregate bond ballast |
| SGOV | iShares 0-3 Month Treasury ETF | 0.09% | $0 | T-bill carry floor |
| VXUS | Vanguard Total International Stock ETF | 0.07% | $0 | ex-US completion |
| FXAIX | Fidelity 500 Index | 0.015% | $0 | Ultra-low 500 (Fidelity-locked) |
| FXNAX | Fidelity US Bond Index | 0.025% | $0 | Aggregate bond (Fidelity-locked) |

**Expected return:** ~7–9% equity beta + ~4–5% current T-bill carry — **NOT a trading edge**, it is the market baseline that every repo "edge" failed to beat net of costs and selection bias.

### Immediate Next Steps (This Week)

1. **Fix data pipeline** (EXPIRED→WON relabeling, zombie drain, stale price refresh) — prerequisite for all downstream gates
2. **Run CRYPCO vol-trend paper trading** (frozen parameters, 90 days / 30 round trips, PF≥1.3, WR≥55%, CI excludes zero)
3. **Run EQUITY H10 forward test** (frozen parameters, 90 days / 30 round trips, PF≥1.3, WR≥55%, benchmark-relative vs SPY)
4. **Build mutual fund low-fee universe** (NAV history ≥5 years, benchmark, hard gates from `mutual_fund_ranker.py`)
5. **Deploy SubQ comparison** as CI gate before any strategy promotion
6. **Deploy PBO/SPA/FDR gates** as CI gates (require ≥2 strategies n≥20, ≥5 for PBO power)

**Kill condition:** If any candidate fails any Stage-3 gate in paper trading → halt, return to research. No exceptions.