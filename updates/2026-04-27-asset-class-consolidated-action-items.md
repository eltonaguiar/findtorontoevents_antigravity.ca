# Asset Class -> World-Class Hedge Fund: Consolidated Action Items

**Author:** Claude (coordinator-synthesis)
**Date:** 2026-04-27
**Status:** Synthesis only. No production code changed. Quotes/cites the three source audits, does not re-run the math.

## Methodology + Scope

This file synthesizes three independent asset-class audits that landed on `origin/main` today.
It is NOT a replacement for them — read the originals if you need the per-class deep-dive.

| Audit | Author | Source cohort | n (closed) | Snapshot |
|---|---|---|---|---|
| `updates/2026-04-27-chatgpt-codex-asset-class-hf-ml-audit.md` | ChatGPT Codex | `audit_trail/data/dashboard_payload.json` `picks.recent_closed` | 3,500 | `generated_at` 2026-04-24T23:51:44Z |
| `updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md` | GitHub Copilot | same payload, later snapshot | 3,500 | `generated_at` 2026-04-27T19:16:20Z |
| `updates/2026-04-27-roocode-deepseek-asset-class-benchmark-ml-retrain-audit.md` | Roocode/DeepSeek | "Apr 24-27 closed picks" 4-day slice | ~711 | rolling |

**Cohort resolution rule.** The user asked "performance against a world-class hedge fund." That is a question about realized historical edge, not a 4-day what-if. Codex and Copilot both used the full 3,500-pick `recent_closed` cohort and so are the authoritative source for the per-class verdict in this synthesis. Roocode's 4-day slice (n=711) is treated as a supplementary recent-window signal, not the primary benchmark.

**Snapshot freshness.** I confirmed live state via small `python -c` against `audit_dashboard/data/dashboard_data.json`: `recent_closed` length 3,500 (generator-capped), `hf_stats.by_asset_class` populated for 7 classes, `generated_at` 2026-04-27T22:08:21Z. So Codex's "stale payload republished" finding (snapshot `2026-04-24T23:51:44Z` written 2026-04-27) was real at audit time but has since refreshed; Copilot's "`hf_stats` block was empty" was true in their loaded copy but is no longer.

## Headline State (per class)

Per-class numbers are quoted from Codex (n=3,500, 2026-04-24 snapshot) and Copilot (n=3,500, 2026-04-27 snapshot). Where they disagree on n=, both are shown — the three-day snapshot drift is itself a finding.

| Class | n (Codex) | n (Copilot) | WR | PF | Max DD | Consensus verdict |
|---|---:|---:|---:|---:|---:|---|
| EQUITY | 381 | 370 | ~52% | ~1.4 | ~-71% | Cleanest class. Tier 2 / near-skill-verified (PSR 0.9944, Calmar 3.25 per Codex). DD too deep. |
| CRYPTO | 1,598 | 1,627 | 36.6-42.2% | 0.83-1.14 | -134% to -679 units | Has alpha but badly packaged. Largest class by weight. The drag. |
| FOREX | 794 | 787 | ~50% | 1.31-1.35 | ~-40% | Mid-tier. Real positive edge, not elite. |
| ETF | 83 | 84 | 54-55% | 1.22-1.25 | ~-47% | Promising, n still thin. |
| COMMODITY | 622 | 610 | 42.1-42.6% | 0.89-0.93 | ~-33% | Clearest broken class by Codex; "fixable" by Copilot. PF<1 either way. |
| BOND | 17 | 17 | 47% | 1.60 | -3 | Insufficient data. Do not promote. |
| FUTURES | 2 | 2 | 100% | inf | 0 | Insufficient data. |
| UNKNOWN | 3 | 3 | 100% | inf | 0 | Tagging bug. Fix upstream. |

All three audits agree on direction for EQUITY (best), CRYPTO (worst-by-volume), FOREX (mid-tier-positive), and COMMODITY (broken/marginal). All three agree no class meets WORLD_CLASS_ROADMAP targets (Sharpe>=1.5, WR 55-65%, DD<10%).

## Where the Audits Disagree

1. **EQUITY direction.** Codex: "looking good, n=381, WR 51.97%, PF 1.385." Copilot: "Tier 2, n=370, WR 52.16%, PF 1.41." Roocode: "**broken, 0% WR on n=11, immediate protocol review**." DISPUTED → Roocode's 4-day cohort is too small (n=11) to support the verdict. The 3,500-pick cohort wins. Equity is the cleanest class, not broken. (Roocode's 0% WR may still be a real recent-window signal worth investigating but does NOT overturn the headline finding.)

2. **COMMODITY severity.** Codex: "needs fixes now, negative cum return, negative risk-adjusted stats." Copilot: "fixable, not broken, low variance suggests TP/SL mis-sizing." Roocode: "marginal." Resolved: all three agree PF<1 and the class needs work, but the *root cause* is what Copilot calls TP/SL templates being wrong for the asset class — pointer to `updates/2026-04-22-deep-asset-class-edge-analysis.md`.

3. **`ml_battleground` health.** Codex: "best operational state, fresh artifacts." Copilot: "retraining is healthy, last cron tick 2026-04-24." Roocode: "historically catastrophic 1.9% WR on n=107, **systems A-E DISABLED**, but daily retrain still active — retraining bad data → worse model." DISPUTED → Codex+Copilot read the artifact freshness; Roocode read the YAML comments. Both can be true: ML stack is *retraining* but the *consumers* (systems A-E) may still be off. Action item: P1 verify which of A-E are wired vs commented out.

4. **`ml_gatekeeper` persistence.** Codex: "retraining persistence is likely broken — `audit-dashboard.yml` doesn't stage `ml_gatekeeper/models/`." Copilot: didn't separately audit gatekeeper persistence. Roocode: didn't audit. Treated as Codex-only finding, kept as P0 because it's specific and file-located.

5. **`ml_crypto_predictor` health.** Codex: "stale, `self_improvement.py` reads missing `results/v4_training_summary.json`." Copilot: "`production_models/*.pkl` last touched 2026-04-27 18:40, healthy." Both true: production .pkl is fresh (Copilot) AND the self-improvement entrypoint has a path bug (Codex). P0 fix the path; do not block the production model.

## P0 — This Week (5 items max)

Each item is named, file-located, and has a measurable validation signal.

1. **Fix `ml_crypto_predictor/self_improvement.py` summary-file path.** Codex: file reads `results/v4_training_summary.json` which is missing; current summary is at `ml_crypto_predictor/enhanced_models/results/training_summary.json`. **Validation:** `python ml_crypto_predictor/self_improvement.py --dry-run` exits 0 and prints a recent `trained_at`. (Source: Codex §ML 4.)

2. **Stage `ml_gatekeeper/models/` in the workflow commit path.** Codex: `audit-dashboard.yml` runs `ml_gatekeeper/gatekeeper.py` but does not git-add the refreshed `ml_gatekeeper/models/gatekeeper_model.joblib` / `training_report.json`. Result: CI retrains, never persists. Local artifact age was ~293h at audit. **Validation:** `git log -p .github/workflows/audit-dashboard.yml` shows `ml_gatekeeper/models/` in `git add`; next workflow run pushes a fresh `trained_at` timestamp. (Source: Codex §ML 2.)

3. **Add per-symbol contribution cap (max 5%) in feedback retrainer.** Copilot: `feedback_training_report.json` shows MATICUSDT n=1,033 WR 0% feeding 13% of crypto labels — poison pill. Memory `project_confidence_rho_matic_artifact.md` confirms 1,033 -0.15 ghost rows; cleaner ran 2026-04-25 (PR #374) but trainer doesn't enforce cap. **File:** `ml_crypto_predictor/enhanced_models/feedback_trainer.py`. **Validation:** rerun next 12h cron; report's top-symbol-contribution % <= 5%. (Source: Copilot §Risks 3.)

4. **Verify `ml_battleground` consumer wiring (Systems A/B/C vs A-E).** Roocode: "Systems A-E DISABLED, but daily retrain still active." Codex: "best operational state." Need a single grep over `.github/workflows/ml-battleground-*.yml` to confirm which `system_*_filter` outputs are actually consumed by `audit_trail/quality_gates.py` or the scanner pipeline. **Validation:** a one-page artifact at `reports/ml_battleground_wiring_2026_04_27.md` listing each of A/B/C/D/E with status `wired | retrained_orphan | disabled`. (Source: Codex §ML 1 vs Roocode §3.2 Gap 2.)

5. **Tighten HC-strict for CRYPTO.** Copilot: raise `forwardWRMinPctCrypto` 45 -> 55 and `scoreFloorCrypto` 55 -> 60 in `config/hc_gate_params.json`. Roocode: graduated multiplier instead of binary fwdWR cut, lower trust min 8 -> 6. **File:** `config/hc_gate_params.json` + `audit_dashboard/hc_filter.js:290-434`. **Validation:** 7-day forward CRYPTO WR climbs above 45% on `hf_stats.rolling_metrics`. (Source: Copilot Recs Immediate 1, Roocode Short-term 5-6.)

## P1 — This Sprint

1. **Add class-aware drawdown caps.** All three audits agree every class fails the WR/Sharpe/DD targets; Codex makes DD the headline gap. (Codex P1.2; Copilot's HC-strict fix indirectly addresses; Roocode silent.) Wire into `cross_aggregation/portfolio_manager.py` (referenced in `WORLD_CLASS_ROADMAP.md` Phase 2.3).
2. **Split feedback model by `asset_class_code`.** Copilot's "no per-asset model heads" risk: every retrain mixes crypto-dominant data, drowning equity/ETF signal. Train `feedback_model_crypto.joblib` and `feedback_model_noncrypto.joblib`; route in `ml_crypto_predictor/enhanced_models/feedback_trainer.py`. (Source: Copilot Recs Next 1.)
3. **Re-route capital toward EQUITY/FOREX/ETF.** Codex P1.1: "Active board was effectively CRYPTO + COMMODITY only" despite cleaner closed-book stats elsewhere. Inverse-vol allocator (`tools/risk_parity_allocator.py` from `updates/2026-04-21-hedge-fund-gap-fillers.md`) flips CRYPTO from 47% pick share to 8.4% target weight. Move from shadow to enforce.
4. **Reclassify UNKNOWN asset-class rows at source.** All three audits flag the n=3 UNKNOWN bucket. Copilot notes peer WIP at `tools/fix_unknown_asset_class.py`. Land it.
5. **CI guard: fail if Mercury2 PSR fails 2 consecutive retrains.** Copilot's risk #4: `mercury2/data/training_summary.json` shows `psr_pass=false` while `dsr_pass=true`. (Source: Copilot Recs Next 2.)

## P2 — Backlog

1. Re-audit commodity strategy families for resolver / flat-close pathology. Codex P2.1; reinforced by memory `project_perf_audit_2026_04_21.md` (5 CTA strategies 60-100% flat-close, n=684 affected) and `feedback_noncrypto_resolver_live_close_bug.md` (`outcome_resolver.py:384-405` closes at yfinance spot, ~1,700 picks across 15 strategies mislabeled).
2. Annualized rollup tile on dashboard so "per-trade Sharpe 0.134" is not compared to "annual Sharpe 1.5." (Source: Copilot Recs Longer 2.)
3. Centralized retrain-status dashboard. Roocode §3.2 Gap 1 + Gap 5 (15+ retrain mechanisms, no aggregation). Surface every model's `last trained_at` on `audit_dashboard/index.html`.
4. Symbol-level WR gate (`<25% over 20+ picks` -> block). Roocode: TAOUSDT n=62 -11.30% unblocked. (Source: Roocode P1.)
5. Repair `alpha_engine/meta_labeler` artifact persistence. Codex §ML 5: code exists, `alpha_engine/meta_labeler_model.pkl` missing.

## Items NOT to Ship (refuted)

1. **Roocode's "EQUITY broken, 0% WR" → DISPUTED.** Cohort n=11 over 4 days vs Codex/Copilot n=370-381 over the full ledger showing WR ~52% PF ~1.4. Per `feedback_label_asset_class.md` rule, do not act on un-headlined small-n claims.
2. **Codex's "republishing stale JSON" as a P0 → DOWNGRADE.** Verified live: `audit_dashboard/data/dashboard_data.json` `generated_at` is 2026-04-27T22:08Z, current. Was real at audit time, has self-resolved. Keep watching, don't ship.
3. **Roocode's "ML Battleground systems A-E DISABLED" as a strategy ban.** DISPUTED — Codex+Copilot show the retrain stack is healthy and System A/B/C succeed. Verify wiring (P0 #4) before claiming the consumers are off.
4. **Roocode's "Renaissance 4d equivalent ~+0.5-1.0%" benchmark.** Roocode mixes daily-decimated annual returns with our raw 4-day pick PnL — the comparison is incoherent and not used here. Use `WORLD_CLASS_ROADMAP.md` (Sharpe>=1.5, WR 55-65%, DD<10%) and `updates/2026-04-21-hedge-fund-gap-fillers.md` (PSR>=0.995, Calmar>=3) instead.
5. **Any non-crypto WR/PF claim that hasn't filtered for `exit_reason in {TP_HIT, SL_HIT}`.** Per memory `feedback_noncrypto_resolver_live_close_bug.md`: `outcome_resolver.py:384-405` closes at yfinance spot + 1bp WIN threshold at `:97`; ~1,700 picks across 15 non-crypto strategies are mislabeled. Codex's COMMODITY/FOREX/EQUITY numbers ARE susceptible to this — flagged as DISPUTED magnitude (direction holds, magnitude inflated by mislabeling).

## Per-Class Roadmap to WR 55-65% / Sharpe>=1.5 / DD<10%

- **EQUITY** (n=370-381, closest): keep the pipeline, harden DD via class-aware caps (P1.1). Already PSR 0.9944, Calmar 3.25 per Codex — needs DD reduction not rewrite.
- **FOREX** (n=787-794): tighter exits, regime-aware routing. PSR 0.76 needs to climb. (Codex §FOREX.) NOTE: realized numbers are suspect per the resolver bug — verify with TP_HIT/SL_HIT-only filter before allocating.
- **ETF** (n=83-84): grow the sample before promoting. Copilot: keep monitoring.
- **CRYPTO** (n=1,598-1,627): tighten HC strict (P0.5) + per-symbol cap (P0.3) + asset-class-headed feedback model (P1.2). Memory `feedback_clone_hl_placeholder_stats.md` adds: quarantine `clone_hl_copy_*` rows with identical (score, n, fwd_wr) triples before any HC-label account trade.
- **COMMODITY** (n=610-622): re-tune TP/SL templates per `updates/2026-04-22-deep-asset-class-edge-analysis.md`; audit CTA flat-close pathology (P2.1). Resolver fix is upstream.
- **BOND/FUTURES**: do not benchmark until n>=50 with stable WR.

## ML Retraining Gaps (consolidated)

| System | Codex verdict | Copilot verdict | Roocode verdict | Synthesis |
|---|---|---|---|---|
| `ml_battleground` | Best operational state | Healthy retraining cron | Systems A-E disabled (consumer side) | RETRAIN healthy; CONSUMER wiring P0 #4 |
| `ml_gatekeeper` | Persistence broken | not separately audited | not audited | Codex-only finding, P0 #2 |
| `alpha_engine/ml_ranker` | Stale; production path unclear | not separately audited | Active per auto_tuner | Verify production_scanner.py exercises it (P2) |
| `ml_crypto_predictor` | Stale + path bug | Production .pkl fresh 18:40 | Active 12h cron | Self-improver path P0 #1; production model OK |
| `alpha_engine/meta_labeler` | Code exists, artifact missing | not audited | Active daily via daily_runs.yml | DISPUTED freshness; P2.5 |
| `mercury2` | not separately audited | DSR pass / PSR fail | Active weekly | P1 #5 PSR-fail CI guard |
| `ml_consensus` | Rules engine, not retrainable | not audited | not audited | Codex correct: not an ML failure |

Cross-cut from Roocode §3.2: 15+ retrain mechanisms with no aggregation point. Centralized status dashboard P2 #3.

## Open Questions

1. Which of `ml_battleground` Systems A-E are actually consumed by `audit_trail/quality_gates.py`? (P0 #4.)
2. After the resolver fix lands (`outcome_resolver.py:384-405` per memory), do COMMODITY/FOREX/EQUITY WR/PF stay positive? Re-run the per-class table with `exit_reason in {TP_HIT, SL_HIT}` filter only.
3. Should the asset-class-headed feedback model (P1 #2) be a hard router or a soft ensemble? Copilot leaves it open.
4. The 3-day snapshot drift Codex flagged (snapshot 2026-04-24 file written 2026-04-27): is it republish-from-cache or generator clock skew? Live state was healthy at synthesis time; root cause not yet identified.

## References

- `updates/2026-04-27-chatgpt-codex-asset-class-hf-ml-audit.md`
- `updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md`
- `updates/2026-04-27-roocode-deepseek-asset-class-benchmark-ml-retrain-audit.md`
- `audit_dashboard/WORLD_CLASS_ROADMAP.md`
- `updates/2026-04-21-hedge-fund-gap-fillers.md`
- `updates/2026-04-22-deep-asset-class-edge-analysis.md` (cited by Copilot, Codex)
- Memory: `feedback_noncrypto_resolver_live_close_bug.md`, `feedback_clone_hl_placeholder_stats.md`, `project_confidence_rho_matic_artifact.md`, `project_perf_audit_2026_04_21.md`, `feedback_phantom_halt_alert_bug.md`, `feedback_circuit_breaker_stale_state_leak.md`, `feedback_label_asset_class.md`
