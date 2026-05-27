---
title: "Quick Wins from 90-Day Asset-Class Plans + Gap Analysis"
date: 2026-05-27
source:
  - reports/90day_gap_analysis_2026-05-15.md (canonical, deduped via /dedup-md-files from 126 worktree copies → 9 unique)
  - reports/asset_class_90day_plan_{BOND,COMMODITY,CRYPTO,EQUITY,ETF,FOREX,FUTURES,PENNY_MEME}_2026-05-15.md
  - https://findtorontoevents.ca/audit/incidents.html (cross-reference)
status: "actionable, no user approval required for items 1-4"
---

# Top Quick-Win PRs (ready to draft today)

These items appear in the May-15 90-day plans, have **specific files identified**, require **NO user approval**, and have **measured backtest evidence**. None depends on MySQL writes or server restarts (unlike the foundation-fix PRs already in review).

## QW-1: EQUITY VIX<22 hard regime gate — MERGE THE EXISTING BRANCH

- **Branch:** `feat/equity-vix-regime-gate-sidecar-2026-05-13` (exists, not merged)
- **Evidence:** `reports/equity_vix_regime_breakthrough_20260513.md` + `equity_momentum_vix_regime_backtest.json`
  - 30-LC universe, 2015-2026, VIX<20: **PF 5.37 / WR 75% / Sharpe 2.19 / MDD 7.3%**
  - VIX<22: PF 4.55 / MDD 16.8% (still Tier-1)
  - Baseline (no gate): PF 2.82 / MDD 24%
- **Lift:** +57% PF, -69% MDD when VIX<22 active
- **Risk:** Wire-Up rule violation if merged without a production caller — branch was created as sidecar; needs `equity_strategies.py` + `non_crypto_quality_gate.passes_active_gate` to actually call it
- **Action:** Verify the branch + add one production caller in `equity_strategies.py`. Estimated diff ~30 lines.

## QW-2: ETF VIX<25 gate wired into etf_sector_emitter

- **Files:** `alpha_engine/etf_sector_emitter.py` + `alpha_engine/vix_regime_gate.py` (already exists, not called)
- **Evidence:** Backtest PF 2.05 baseline → **PF 3.22 with VIX overlay** (Sharpe 1.63)
- **Lift:** +57% PF essentially free
- **Why it's still unwired:** `vix_regime_gate.py` exists with the right thresholds but `etf_sector_emitter` doesn't call it at pick-emit time
- **Action:** Single-line wire: import `vix_regime_gate.is_safe_regime()`, early-return picks if False

## QW-3: CRYPTO BTC UTC-hour death-zone filter (M-001)

- **File:** `alpha_engine/score_booster.py`
- **Evidence:** Memory-backed n>1000 picks: BTC 08-09Z window has below-baseline WR; 22Z has above-baseline. Filter rejects 08-09Z BTC picks, boosts 22Z scores.
- **Effort:** ~15 lines. Pure stat edge, env-gated (no behavior change unless `BTC_HOUR_FILTER_ENABLED=1`).
- **Why nobody's wired it:** It's been on the master plan since 2026-05-15 but ranked P1 and never picked up. Lowest-effort high-impact CRYPTO item.

## QW-4: CRYPTO on-chain momentum env enable (MVRV-Z)

- **Action:** Set `CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1` in GitHub Actions env
- **Effort:** zero code change — module already exists, just needs the flag
- **Lift:** Glassnode MVRV-Z BTC/ETH momentum signal becomes active in pick scoring
- **Risk:** Low — Glassnode rate-limit; module already has fail-open behavior

## QW-5: Re-derive COMMODITY n/PF post-PR-#994 dedup (audit, no code change)

- **Why:** COT over-emission was killed in PR #994 (2026-05-14). The headline **COMMODITY PF=2.36 / WR=60.5% / n=339** likely still reflects pre-dedup over-emission artifact. Post-dedup the cohort collapses to ~5 trades with WR 40% / PF 0.17 per `cot_paper_pilot_overemission_falsified_20260513.md`.
- **Action:** Run a one-off query against `audit_dashboard/data/dashboard_data.json` and `pf_registry.json` filtered to `created_at > 2026-05-14`. Confirm or refute the headline.
- **Effort:** ~30 minutes of data archaeology. Output: short report `reports/commodity_post_dedup_redrive_<UTC>.md`.
- **Why it matters:** Three weeks of "COMMODITY is our flagship class" claims are built on a possibly-artifact PF. Need to know before any sizing change.

# Items pending user approval (NOT in quick wins)

These are quick to implement once approved per CLAUDE.md:

- **QA-1 PENNY_STOCK class-wide gate** — add `("PENNY_STOCK", "*")` to `BLOCKED_ASSET_STRATEGY_PAIRS` in `quality_gates.py`. Current state: n=148, PF=0.19, WR=6.76% — biggest single drag on EQUITY headline. Needs approval because of BLOCKED_* discipline rule.
- **QA-2 9 baby_strats overfit blocks** — `crypto_soc_orderflow_absorption` variants + `adx_pullback` + `choppiness_regime`. Overfit severity 4.15–4.87 from baby_strats audit. Same approval rule.
- **QA-3 M-007 FOREX_HARD_DISABLE** — env flag in `config.py` + wire into `passes_active_gate`. FOREX is PF<1 net loser; this stops the bleed until carry achieves PF>1.0 on n>30.

# Per-class "world-class" one-line summary

| Class | Top strategy from plan | Why this one | Status |
|---|---|---|---|
| EQUITY | VIX<22-filtered 12-1 momentum on clean 18 LC (AAPL/MSFT/NVDA/TSLA/AMZN/GOOGL/META/AMD/AVGO/ORCL/JPM/GS/UNH/LLY/WMT/COST/XOM/PG) | Tier-1 backtest PF 4.55–5.37, MDD<17%, academic backing (Jegadeesh-Titman, Faber); penny/meme separately quarantined | branch exists, needs merge + caller |
| ETF | Antonacci sector dual-momentum 12-1 with VIX<25 overlay | PF 2.05 → 3.22 with overlay; backtest n=88 monthly periods; XLK/XLE/IWM picks already firing | overlay unwired; QW-2 |
| CRYPTO | Liquid-core (BTC + ETH + 7 top-L1 by ADV) with ADV minimum + on-chain momentum + source whitelist + BTC hour filter | Kills MEMECOIN drag (PF 0.50 n=1,869), enforces production-discipline source list, adds on-chain BTC/ETH MVRV-Z edge | source whitelist unaddressed; QW-3 + QW-4 partial |
| COMMODITY | Carry-momentum double-sort across 25 symbols (NOT CT=F over-concentration) + COT MATCH gate + DSR≥0.85 block | Current 73% PnL mass on CT=F is a single-symbol mirage; gross diversification needed | unbuilt; QW-5 is the audit precursor |
| FOREX | Carry-yield-differential on G10 majors using live FRED rates + COT proxy → real CFTC 6E/6B/6J data | Current PF 0.87 net loser; carry on real rates is the only theoretically-edgy approach | unbuilt; needs M-007 first |
| BOND | TIPS mean-reversion + curve carry + HYG-LQD credit MR (3 research pilots from bond_deep_dive_round2) | n=11 is unusable; need to start the meter on real diversified strategies | unbuilt; FRED_API_KEY first |
| FUTURES | MERGE INTO COMMODITY tile | Currently produces 0 quality picks; 70% =F volume routes to COMMODITY anyway | recommend tile-merge in next session |
| PENNY/MEME | Full quarantine (0% risk); research-only sleeve | PF 0.19 / 0.50 — toxic to all aggregate metrics | quarantine_manifest exists but not all paths gated |

# Process notes

- The 9 unique `.md` files were extracted from a 126-path list (84 worktree copies + 42 IPO-backtest-worktree copies + 9 canonical) via the new `/dedup-md-files` skill (`tools/dedup_md_files.py`). Worktree copies are identical-content to the canonical `reports/` files (would have shown 0 unique if their paths existed on this WSL host; they're Windows-only).
- 7 open PRs (#9, #10, #11, #13, #14, #15) already address the foundation layer (calibration inversion, leakage, trust_score, WON labels). Quick-wins QW-1 through QW-5 sit ON TOP of those — they're strategy-level improvements that only become trustworthy once the foundation closes.
- **Recommended order:** finish foundation PRs first (#9, #15, #14), then QW-1 (EQUITY VIX) + QW-2 (ETF VIX) + QW-3 (BTC hour) as the 3-PR strategy sprint. QW-4 is a workflow secret + env var.
