# Community / Plans / Updates — Winner-Lead Synthesis (2026-10-22)

**Author:** research-synthesis subagent
**Date:** 2026-10-22 UTC
**Scope:** synthesize the most recently-updated plans, updates docs, community GitHub work, and audit findings to extract actionable leads for "true winners" (proven high-edge picks).
**Constraint honored:** no production code modified; report-only.

---

## 1. Source index (all read this session, last-5-day files)

**Plans (`docs/superpowers/plans/`):**
- `docs/superpowers/plans/2026-10-22-audit-dashboard-quality.md`
- `docs/superpowers/plans/2026-10-20-audit-cohort-reconciliation-implementation.md`
- `docs/superpowers/plans/2026-10-19-combined-book-paper-trade-implementation.md`

**Community cross-agent work (`COMMUNITY/`):**
- `COMMUNITY/BUFFY_FINDINGS_AND_WINNER_STATUS.md`
- `COMMUNITY/OPENCODE_WINNING_CANDIDATE_AND_PLAN.md`
- `COMMUNITY/CROSS_AGENT_MASTER_PLAN_2026-10-22.md` (POOLSIDE_KILOCODE)
- `COMMUNITY/GHCOPILOT_KIMI_REVIEW_2026-10-22.md`
- `COMMUNITY/INCEPTION_VLLM_REVIEW_BUFFY_FINDINGS.md`
- `COMMUNITY/INCEPTION_VLLM_REVIEW_GHCOPILOT_PLAN.md`
- `COMMUNITY/INCEPTION_VLLM_REVIEW_OPENCODE_WINNING_CANDIDATE.md`
- `COMMUNITY/GHCOPILOT_MOMENTUM_VERIFICATION_2026-10-22.md`
- `COMMUNITY/GHCOPILOT_COPPER_VERIFICATION_2026-10-22.md`
- `COMMUNITY/MASTER_PLAN_GODLIKE_FRAMEWORK.md`, `COMMUNITY/MASTER_PLAN_2026-10-22.md`, `COMMUNITY/APPROACH.MD`

**Audit findings (repo root):**
- `AUDIT_CRITICAL_FINDINGS_OCT22.MD` (Buffy, 5-agent consolidation)
- `AUDIT_FINDINGS_GCOPILOT_OCt22.MD`, `AUDIT_ACTIONS_GCOPILOT_OCT22.MD`
- `AUDIT_FINDINGS_OPENCODE_OCT22.MD`, `AUDIT_FINDINGS_VLLMPAID_OCT22.md`
- `findings/nemotron_2026-10-20T0223Z.md`

**Updates (`updates/`):**
- `updates/2026-10-22-asset-class-review-hidden-winners.md` (Zod/Inception)
- `updates/2026-10-22-INCEPTION-plan-profit-pick.md`
- `updates/2026-10-22-db-quality-audit-inception.md`
- `updates/2026-10-22-walkforward-strategy-eval.md`
- `updates/2026-10-22-prediction-integrity-edge-verification.md`
- `updates/2026-10-19-combined-book-paper-trade-pilot.md`, `updates/2026-10-19-task10-benchmark-closed-ledger.md`
- `updates/2026-10-22-copytrader-active-lifecycle.md`, `updates/2026-10-22-youtube-live-key-wiring.md`

**Prior reports (today):**
- `reports/2026-10-22-top10-winners-reverse-engineered.md`
- `reports/2026-10-22-ml-stack-audit.md`
- `reports/METHOD_REVIEW_2026-10-19-what-actually-works.md`

---

## 2. What other agents / the community have already discovered

### 2.1 The dominant consensus: no directional class is PROVEN / MONEY-READY

Every agent converges on the same verdict — the measurement layer is corrupted, and **zero asset classes currently clear the strict promotion gate** (`money_ready = []`; 0/9 money-ready; all classes NOT_READY / WATCH / INSUFFICIENT_DATA). Sources: `AUDIT_CRITICAL_FINDINGS_OCT22.MD` §0/§7, `COMMUNITY/CROSS_AGENT_MASTER_PLAN_2026-10-22.md` §1, `updates/2026-10-22-asset-class-review-hidden-winners.md` §1.

Root cause (universally confirmed): the **frozen-exit resolver bug** in `audit_trail/universal_pick_resolver.py` (one stale price snapshot stamped across many picks → manufactured 90–100% WR clusters at a single exit price). Evidence: QUBT/IONQ/SOFI/PLTR (181–184 wins / 1 distinct exit day), AAPL `stocks_rsi2_pullback` (107W / 10 days / 3 prices), YM=F sentinel (+999999.9999%), BTCUSDT +370850% outlier. Detector rule (now canonical): `wins > 2 × distinct_exit_days` → artifact.

### 2.2 Claims that were made, then contested/rejected (important)

| Claim | Agent | Community verdict |
|---|---|---|
| `high_trust_momentum` (CRYPTO) PROVEN (n=206, WR 58.7%, PF 1.81) | OpenCode | **Downgraded to CANDIDATE** — decayed in Oct (WR 38.1%, −0.13%). Pooled bootstrap hid the decay. |
| `commodity_term_cot` HG=F PROVEN (n=815, PF 2.29) | OpenCode | **REJECTED** by INCEPTION + POOLSIDE — 12.4% frozen-exit contamination; clean n=8, PF 1.03. |
| Copy-trader / `multi_asset_copytrader` 88.9% WR, PF 10.24 | various | **Soft-resolution artifact** — multiple symbols at 100% WR with $0 losses; CRYPTO copy-trader is 0% WR. |
| ML/prediction sleeves (prediction_market_consensus, claude_ml_moderate_mut, ml_crypto_pred, Predictions) | — | **All negative** on hard-resolved trades (WR 37% / PF 0.89). |
| `regime_*` family (USDCHF PF 26.0, AAPL PF 49.3) | — | Frozen-exit artifact family; quarantined. |

### 2.3 The honest positives that survived

1. **Tactical rotation allocator** (ETF monthly momentum) — Sharpe 1.48 vs SPY 1.37, maxDD −7.1%, beats SPY risk-adjusted on 19 real month-end observations. Artifact-free (no resolver dependency). Built at `tools/tactical_rotation_tracker.py` + `audit_dashboard/data/tactical_rotation_status.json`.
2. **ML edge (validated, not yet live):** `ml_gatekeeper` (holdout +8.42pp WR, PF 2.206, p=0.0004) and `ml_consensus` (+10.71pp WR). Fresh models/reports dated 2026-10-22.
3. **`mega_mutation`** (Kimi, 4-symbol JUP/ENA/ADA/WIF) — legacy ledger n=171, WR 80.7%, PF 7.66, but **stale (Apr–Jun 2026)** and **not replay-validated**; current `at_raw_picks` cohort shows PF 1.69 only. Candidate for a sealed forward cohort, not proven.
4. **Hidden concentration winners** (from `updates/2026-10-22-asset-class-review-hidden-winners.md` §4): DOTUSDT +282% of alpha_engine PnL; EURGBP=X 74.9% of multi_asset_copytrader PnL (PF 3.24); battleground crypto PF 1.76; UEPS magic_formula equity book (22 open positions); GOOGL/FETUSDT/TONUSDT/STRKUSDT top-notch symbols (WR 69–100%, n 17–69).

---

## 3. Corroboration / contradiction with the known facts

### 3.1 Top-10 genuine winners today — CONFIRMED exactly
`reports/2026-10-22-top10-winners-reverse-engineered.md` matches the supplied top-10 list one-for-one (BNBUSDT +21.4, RNDR-USD +14.5, MSTR +10.7, AVAXUSDT +10.7, LINK-USD +9.1, NEARUSDT +7.6, XRP-USD +7.0, STXUSDT SHORT +5.6, NEARUSDT SHORT +5.5, STXUSDT LONG +5.2). All are genuine holds (TP_HIT / real closes); the two big ones (BNB, AVAX) are long-duration swing holds entered 2026-03-29 that resolved in-window. Source systems: alpha_engine, kimi_riseoftheclaw, luxalgo_confluence.

**Caveat:** these are *real individual closes*, not proof of a durable strategy edge — the community audit shows no tested directional class is proven. Treat them as hunting evidence, not certification.

### 3.2 ML validated lift — CONFIRMED exactly
`reports/2026-10-22-ml-stack-audit.md` confirms `ml_gatekeeper` (+8.42pp WR holdout, PF 2.206, p=0.0004) and `ml_consensus` (+10.71pp WR). Both validated on real closed picks, fresh 2026-10-22. **Critical gap:** neither is wired to emit live active/closed pick files yet — the validation is paper-level.

### 3.3 Missing-from-universe proven winners — CONFIRMED exactly
The reverse-engineered report lists the same 8 expansion symbols: **AUDJPY=X, GBPJPY=X, BAT-USD, CRV-USD, ZECUSDT, WLD-USD, XTZ-USD, MINAUSDT**. These won historically but are absent from the active universe. Highest-ROI expansion because they already proved they can win.

### 3.4 Contradiction flagged (must not be missed)
The reverse-engineered report ranks `multi_asset_copytrader` as the **best window win-rate source (82.1% WR)**. The community audit **contradicts this**: `AUDIT_CRITICAL_FINDINGS_OCT22.MD` CF-4 and OpenCode flag the same source as a **soft-resolution artifact** (88.9% WR with $0-loss rows). → **Do not lean into copy-trader as a winner source.** This is the single most important contradiction to resolve before acting.

---

## 4. Prioritized actionable winner leads

### 🔴 PURSUE IMMEDIATELY (validated / high-ROI / artifact-free)

**L-1 — Operationalize `ml_gatekeeper` as an active pick-gating filter.**
Rationale: strongest validated ML edge (holdout +8.42pp WR, PF 2.206, p=0.0004; lift largest in CRYPTO +23.8pp, EQUITY +13.7pp, FOREX +38.1pp). Apply on top of already-profitable base strategies. Currently validated but **not emitting live picks** — wire `ml_gatekeeper/data/active_picks.json`/`closed_picks.json` so `audit_trail/dashboard_generator.py` consumes it. Source: `reports/2026-10-22-ml-stack-audit.md` §4.1; `ml_gatekeeper/models/training_report.json`.

**L-2 — Wire `ml_consensus` output (feed dormant).**
+10.71pp WR lift vs single-pick. Report exists; output files empty. Populate `ml_consensus/data/active_picks.json` and let the dashboard resolve. Source: `ml_consensus/models/consensus_report.json`; `reports/2026-10-22-ml-stack-audit.md` §4.2.

**L-3 — Expand the active universe with the 8 proven-winner symbols.**
AUDJPY=X, GBPJPY=X, BAT-USD, CRV-USD, ZECUSDT, WLD-USD, XTZ-USD, MINAUSDT. They already won and are simply not being scanned. Source: `reports/2026-10-22-top10-winners-reverse-engineered.md` §3/§4.

**L-4 — Hunt LONG in liquid crypto majors (direction + asset class edge).**
65.8% of genuine wins are LONG; window WR LONG 42.5% vs SHORT 39.0%. Favor BTC, ETH, SOL, LINK, NEAR, STX, AVAX, INJ, TIA, ARB, JUP, SUI via `signal_validation` MomentumEMA + `alpha_engine` + `kimi_riseoftheclaw` momentum/RSI scouts. Concentration of closings at 14:00Z and 21:00Z. Source: reverse-engineered report §2/§4.

**L-5 — Ship the tactical-rotation allocator as the defensible "product".**
Sharpe 1.48 vs SPY 1.37, artifact-free, already built. Forward-track on monthly cron with frozen params (TOP_N=5, lookback=6m, cash=AGG); paper ≥3 months before sizing. Source: `AUDIT_CRITICAL_FINDINGS_OCT22.MD` §2/§4 B; `COMMUNITY/BUFFY_FINDINGS_AND_WINNER_STATUS.md` §5.

### 🟡 CANDIDATE — seal forward cohorts (pursue after the resolver/artifact fix is merged)

**L-6 — `mega_mutation` (JUP/ENA/ADA/WIF)** — strongest claimed historical signal (WR 80.7%, PF 7.66 legacy). Reconstitute executable rules first, reconcile trade identity (GHCOPILOT caveat), then seed a sealed forward cohort. Source: `COMMUNITY/GHCOPILOT_KIMI_REVIEW_2026-10-22.md` §2; `COMMUNITY/CROSS_AGENT_MASTER_PLAN_2026-10-22.md` §4 C-1.

**L-7 — Selective `ml_enhanced_*` combos** with PF 95% CI entirely above 1.0: `ml_enhanced_INJUSDT_1d_B_lightgbm` LONG (PF 35.6), `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` LONG (PF 10.36), `ml_enhanced_FETUSDT_1d_B_lightgbm` LONG (PF 6.02), `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` LONG (PF 4.34). **Historical/ledger family — no live generator exists**; must regenerate before promotion. Exclude the 12 destroyer combos. Source: `reports/2026-10-22-ml-stack-audit.md` §4.4.

**L-8 — AAPL `vt_equity_two_day_rsi_reversal`** — single-ticker hypothesis (n=1 symbol); re-run across the pre-registered 10-ticker universe after the re-emission fix and exit-price guard. Not a class edge. Source: `COMMUNITY/BUFFY_FINDINGS_AND_WINNER_STATUS.md` §4; `COMMUNITY/INCEPTION_VLLM_REVIEW_BUFFY_FINDINGS.md` §2.4.

**L-9 — FOREX class (n=26, PF 3.15)** — interesting but below strict gate; watch only. Source: `updates/2026-10-22-INCEPTION-plan-profit-pick.md` §1.

### ⚫ DEAD ENDS (contradicted, rejected, or negative-edge — do not pursue)

- **Copy-trader / `multi_asset_copytrader`** — soft-resolution artifact; lifecycle fix stops bleeding but creates no wins.
- **`high_trust_momentum`** — decayed in Oct; candidate only, not money-ready.
- **`commodity_term_cot` HG=F** — rejected (12.4% artifact; clean PF 1.03).
- **ML/prediction sleeves** (prediction_market_consensus, claude_ml_moderate_mut, ml_crypto_pred, Predictions) — all negative on hard resolution.
- **`regime_*` / RSI-pullback cells** (USDCHF, AAPL PF 49.3/26.0) — frozen-exit artifact family.
- **Full `ml_enhanced_*` family** — mostly destroyers (12/22 PF<1); only 4–5 selective combos qualify.
- **`crypto_gainer_ml` / `claude_gainer_ml` / `ml_battleground`** — PF 0.63 / F1=0 / PF 0.426.
- **`crypto_ml_edge`, `local_gpu_trainer`, `ml_crypto_predictor` v5** — broken/stale (no runnable artifacts; total_models=0).
- **Mutual-fund ranker** — a ratings product, not a trade signal; inverted on the only resolved sample.
- **`super_signals` strong-consensus & `mega_mutation` same-second fills** — instant/synthetic fills; exclude from PnL rankings until fixed.

---

## 5. Recommendations

**Do now (this week):**
1. Merge the resolver fix + artifact detector + copy-trader lifecycle fix (blockers — every other winner claim depends on clean resolution). Branch status per `COMMUNITY/CROSS_AGENT_MASTER_PLAN_2026-10-22.md` §5.
2. Operationalize `ml_gatekeeper` + `ml_consensus` live outputs (L-1, L-2) — the only *statistically validated* edges in the repo.
3. Add the 8 missing winner symbols to the active universe (L-3) and favor LONG crypto-major hunting (L-4).
4. Seed a sealed forward cohort for `mega_mutation` (L-6) after rule reconstruction.

**Do not:**
- Do not promote `high_trust_momentum`, `commodity_term_cot`, or any copy-trader-derived high-WR source to "money-ready".
- Do not ship any directional pick from the corrupted (un-fixed) resolver data.
- Do not treat the top-10 today as a durable edge — treat them as hunting evidence only.

**Productization (only after forward validation):** tactical rotation as the stable low-risk instrument (L-5); mutual-fund ranker as a ratings product.

---

*files synthesized above are all within the last ~5 days (2026-10-18 → 2026-10-22). No production code was modified.*

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
