# Merged hedge-fund execution plan — external audit + fleet docs

**Canonical version:** `2026-04-02` (UTC anchor for Redis `HF_MERGED_EXECUTION_PLAN`)  
**Status:** Living document — **peer agents append** under [§8 Peer contributions](#8-peer-contributions-append-only).

---

## 0. Purpose

Consolidate:

1. **External live + code audit** (Mar 2026 slice: ~502 trades on dashboard metrics; structural critique: research vs live wiring, score zoo, stops, toxic systems, confidence inversion).
2. **Repo fleet reviews:** `docs/AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md`, `HEDGE_FUND_ENHANCEMENT_PLAN.md`, `EDGE_ADDENDUM.md`, `docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md`, `audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md`, `docs/AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md`.
3. **Prior Redis themes:** toxic lanes, DSR/FDR, TP/SL unity, Smart/VA surface, walk-forward calibration caveats (`docs/WALK_FORWARD_CALIBRATION_REVIEW_2026-04-06.md`).
4. **Google Antigravity feedback:** factor model + alt data, strict VA multi-TF (4h/D/W), VaR risk-parity sizing, regime MR/momentum, MC pre-VA gate, spread/slippage + ATR trails, WF backtests — see [§10](#10-google-antigravity-feedback-merged).
5. **Collected external quant feedback (Xiaomi MIMO + index):** [EXTERNAL_QUANT_FEEDBACK_COLLECTED_2026-04-07.md](./EXTERNAL_QUANT_FEEDBACK_COLLECTED_2026-04-07.md) — goldmine/sports leak, active score–PnL inversion, regime actives coverage, toxic systems.

**Single outcome:** one ordered backlog from **noise removal → geometry → routing → calibration → portfolio risk → execution**, with file-level hooks so any agent (Claude Code, Composer, Copilot, Codex) can claim work without duplicating scope.

---

## 1. Where everyone agrees (merge matrix)

| Theme | External audit | Multiclass fleet doc | HF enhancement plan |
|-------|----------------|----------------------|---------------------|
| **SL-heavy / tight stops** | 78.9% SL; R:R 3+ anti-predictive | Exit mix SL ≫ TP in CSV | Edge addendum: geometry first |
| **Toxic strategy / system** | `ml_crypto_predictor`-style IC poison | SANDBOX / forward_wr / consensus inflation | Anti-overfit + DSR/FDR + registry |
| **Confidence harmful at top** | 0.85+ WR collapse vs mid band | High conf + probation trust | Shrinkage / empirical Bayes (plan §) |
| **Smart / VA = real edge** | SMART ~64.5% WR; VA Spearman ~0.54 | Smart gate strict → often 0 rows; VA cohort strong | Narrow surface until pool recovers |
| **Research ≠ live** | Alpha engine vs momentum scanner | Same: gates vs scanner feeds | Wire WF / ranker to emission path |
| **Non-crypto broken at n** | Equity/Forex single-digit WR | Large closed n in export vs gated live thin | Separate models / allowlists |
| **Alt data + factors** | — | — | Quant stack; macro for FX/equity (**C4**) |
| **VaR / equal risk** | Flat sizing | — | Kelly/CVaR plan; risk parity (**B7**) |
| **WF + anti-overfit** | Live ≠ backtest | CSV + promotion | DSR/FDR + rolling cal (**B2/B5**) |
| **TCA / alpha decay** | Stale signal + costs | Fills gap | Spread/slippage (**D1**, **A5**) |

**Dedup rule:** If two bullets describe the same fix, **one work item** below owns it; cross-link only.

---

## 2. Unified phases (merged tiers)

### Phase A — P0 (weeks 1–2): stop the bleed

| ID | Work item | Detail | Primary code / artifacts |
|----|-----------|--------|---------------------------|
| **A1** | **TP/SL single module** | ATR/vol-aware SL minimum; align `dashboard_generator._vol_aware_tp_sl` with `universal_pick_resolver` fallbacks; re-bucket closed outcomes by vol tier. | `audit_trail/dashboard_generator.py`, pick resolver paths, `docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md` |
| **A2** | **Rolling IC / toxic firewall** | Per `source_system` (and strategy where stable): rolling IC or mean closed PnL; auto-block or probation after N closes + threshold (external: IC &lt; −0.05 @ 30+ trades). Persist decisions in registry / gates. | `audit_trail/quality_gates.py`, `anti_overfit_registry.json` (or successor), enrichment JSON |
| **A3** | **Confidence → empirical shrinkage** | Replace or cap raw “confidence” for promotion/display when `(strategy × symbol)` n is low; universe prior for n &lt; 5; no 85%+ label without closed-sample support. | Scoring pipeline + `elite_scorer` / dashboard fields |
| **A4** | **Narrow default surface** | Default risk UI / copy: **SMART + Verified Alpha + proven**; keep broad `active_raw` as research. | `dashboard_generator.py`, audit template |
| **A5** | **Truth layer + exports** | Fix empty paper-trading CSVs; join fills → pick IDs for TCA. | Paper exporter, `tools/` analysis scripts |

### Phase B — P1 (weeks 3–6): structure

| ID | Work item | Detail | Primary code / artifacts |
|----|-----------|--------|---------------------------|
| **B1** | **Regime-aware routing** | Map regime → allowed strategy families; hard off or size-down for wrong regime (e.g. alt vs BTC lesson). | `features/regime`, scanner emission, gates |
| **B2** | **Walk-forward calibration** | Rolling window (e.g. 60d) + isotonic or bucket calibration: `ml_score` → E[PnL]; **weekly** refresh from last K closes; surface “expected PnL” not raw model score. | `alpha_engine` calibration tools, `docs/WALK_FORWARD_CALIBRATION_REVIEW_2026-04-06.md` (fix post-hoc + slippage issues noted there) |
| **B3** | **Cross-asset correlation budget** | Rolling 30d correlation; cap factor-weighted exposure; forex/equity **separate** signal universes (macro / fundamentals). | `advanced_risk_system.py`, portfolio snapshots |
| **B4** | **Cross-sectional rank** | Prefer decile rank within universe over absolute threshold where data supports it; wire `ml_ranker` (or equivalent) into live candidate set. | `alpha_engine/ml_ranker.py`, emission path |
| **B5** | **Statistical promotion** | Deflated Sharpe, min OOS trades (e.g. 50+), BH-FDR on strategy tests; no promotion on 4-trade 100% WR. | `HEDGE_FUND_ENHANCEMENT_PLAN.md`, backtest pipeline |
| **B6** | **VA multi-timeframe confluence** | Tighten **Verified Alpha** when **4h + Daily + Weekly** agree (direction/structure); extends `_is_verified_alpha_pick` / HTF enrichment — reduces noise picks. | `audit_trail/dashboard_generator.py` (`_is_verified_alpha_pick`, HTF columns ~5411+) |
| **B7** | **VaR risk-parity sizing** | Size positions to **equal risk budget** (e.g. per-trade VaR or vol-target), not flat notionals; crypto vs ETF balanced contribution. | `advanced_risk_system.py`, `tools/hedge_fund_portfolio_risk_snapshot.py`, HF plan §2 |

### Phase C — P2 (weeks 6–12): alpha depth

| ID | Work item | Detail |
|----|-----------|--------|
| **C1** | **Microstructure stack** | Use funding, OI, liquidation proximity, on-chain where already ingested — as **features + gates**, not decoration. |
| **C2** | **Meta-labeling** | Primary direction + secondary “will primary hit barrier net of costs” model; size from meta prob × Kelly cap. |
| **C3** | **Asset-class specifics** | Crypto: liquidity tier + BTC-only vs alt models; Forex: carry/DXY/rates; Equity: fundamentals from existing alpha_engine factors; Commodities: contract-specific. |
| **C4** | **Alternative data factors** | Sentiment/news, developer activity (crypto), macro series (FX/equity) as **inputs to scoring/gates** — integrate only **live** sources with failover (no dummy series). | New or existing scrapers/APIs per asset class |
| **C5** | **Monte Carlo pre-VA gate** | Before promoting to VA (or parallel “stress badge”), run **large-N** path sims vs estimated vol; enforce portfolio policy on tail drawdown frequency (e.g. 1% threshold — tune from data). | MC utilities in `alpha_engine/`, `scripts/sports_monte_carlo.py` (pattern only); define cost/latency budget |

### Phase D — P3: execution + portfolio OS

| ID | Work item | Detail |
|----|-----------|--------|
| **D1** | **Execution + alpha decay** | TWAP/VWAP; **bid-ask spread + conservative slippage** in audit PnL / edge checks so “Active” stays positive net of costs; per-symbol slippage; optional **no new signals** in weak UTC hours (validate on closes first). |
| **D2** | **Drawdown + halt** | Daily / per-symbol limits; correlation halt; vol scaling (partially in gates — reconcile tiered DD with live monitor). |

---

## 3. Metrics to track (acceptance)

| Metric | Target direction | Notes |
|--------|------------------|--------|
| Overall pool WR | ↑ from ~30% | Segment by asset class |
| SL / TP exit ratio | SL share ↓ after A1 | Control for horizon |
| Spearman(score, PnL) | Maintain + on ml_score; improve elite where intended | Crypto vs non-crypto split |
| VA / SMART cohort | Preserve high IC; grow **count** only via B2/B4, not gate weakening | |
| Toxic system count | 0 live picks from blocked IC systems | |

---

## 4. Conflicts / sequencing notes

1. **ATR “wider stops”** can raise WR but change R:R distribution — must ship with **recalibrated TP** and reporting, not SL alone.  
2. **Isotonic on pooled data** without purge → optimistic; follow WF review: rolling train/test + side-aware costs.  
3. **Kill confidence display** vs **user UX**: prefer **internal** shrinkage + show “sample depth” and **calibrated** probability.

---

## 5. Redis bus coordination

- **Canonical topic:** `HF_MERGED_EXECUTION_PLAN` — full envelope points `doc_path_repo_relative: docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md`.  
- **Peer updates:** publish `HF_MERGED_PLAN_PEER_APPEND` with `{ "from": "claude-*", "summary": "...", "claims": ["A2","B1"], "doc_patch_hint": "optional" }` **or** commit directly to §8 below.  
- **Composer / Cursor:** republish `HF_MERGED_EXECUTION_PLAN` after substantive §8 or phase edits so fleet log shows fresh `ts`.

Publisher: `tools/bus_post_hf_merged_execution_plan.py`.

---

## 6. Claude Code agent checklist (handoff)

1. Read this file + `HEDGE_FUND_ENHANCEMENT_PLAN.md` §Current vs Gap.  
2. Pick **one P0 ID** (recommend **A2** or **A1** first), branch, implement, run `python tools/validate_php52.py` on touched PHP and existing Python checks for audit trail.  
3. Append a row to [§8](#8-peer-contributions-append-only) with `from`, date, IDs touched, PR/commit.  
4. `PUBLISH alpha_engine_bus` using `HF_MERGED_PLAN_PEER_APPEND` or rerun `bus_post_hf_merged_execution_plan.py` if you merged materially into §2–§4.

---

## 7. Related repo links

- [AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md](./AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md)  
- [AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md](./AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md)  
- [AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md](./AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md)  
- [REDIS_BUS_SCHEMA.md](./REDIS_BUS_SCHEMA.md) / [REDIS_BUS_CHANGELOG.md](./REDIS_BUS_CHANGELOG.md)  
- [GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md](./GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md)  
- [EXTERNAL_QUANT_FEEDBACK_COLLECTED_2026-04-07.md](./EXTERNAL_QUANT_FEEDBACK_COLLECTED_2026-04-07.md) — index + Xiaomi MIMO deep audit  
- Root: `HEDGE_FUND_ENHANCEMENT_PLAN.md`, `EDGE_ADDENDUM.md`

---

## 8. Peer contributions (append-only)

| UTC | Agent (`from`) | IDs claimed / done | Notes |
|-----|----------------|-------------------|--------|
| 2026-04-02 | `cursor-composer` | Plan authorship | Initial merge of external audit + fleet docs; bus `HF_MERGED_EXECUTION_PLAN`. |
| 2026-04-07 | `cursor-composer` | Doc + bus | `EXTERNAL_QUANT_FEEDBACK_COLLECTED` — Xiaomi MIMO quant audit + master feedback index (§0 in that doc). |

*(Claude / others: add rows below; do not delete prior rows.)*

---

## 9. External audit — raw headline numbers (reference only)

Source: user-provided feedback (Mar 2026 dashboard slice ~502 trades). Validate on current `dashboard_data.json` before treating as live truth.

- Top 20% `ml_score`: ~60% WR, ~+4.2% avg PnL; Spearman `ml_score` ~+0.3; `confidence` ~+0.27; `elite_score` weak on crypto (~0.012).  
- By class: Crypto ~31.8% WR; Equity ~10%; Forex ~6.2%; SMART tier ~64.5% WR; VA overlap Spearman ~0.54.  
- Pain points: ~30% overall WR; R:R 3+ bucket 0% WR; single toxic system flipping ensemble IC; overconfidence bucket underperforming.

These motivated **A1–A5** and **B1–B2**; numbers must be **recomputed** in-repo (`tools/analyze_audit_scores_vs_pnl.py`, etc.) on each release.

---

## 10. Google Antigravity feedback (merged)

**Full capture:** [GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md](./GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md).

**Theme → backlog ID**

| Antigravity theme | IDs |
|-------------------|-----|
| Multi-factor / alt data | **C4** (+ **B3** macro routing for FX/equity) |
| VA = 4h + D + W confluence | **B6** |
| VaR / risk-parity sizing | **B7** |
| Regime: MR vs momentum (ADX/Hurst) | **B1** |
| MC before VA (tail / max DD policy) | **C5** |
| Spread, slippage, alpha decay | **D1**, **A5** |
| ATR trailing / dynamic stops | **A1** |
| Walk-forward backtests | **B2**, **B5** |

**Compliance video:** Not linked in source feedback; add URL to the capture doc when you have it.
