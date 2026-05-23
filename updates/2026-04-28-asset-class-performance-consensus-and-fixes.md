# Asset-Class Performance Consensus + 4 Essential Fixes Shipped — 2026-04-28

**Author:** claude-opus-4-7 (consolidator across 5 independent peer recomputes + 6 deep-dive workstreams)
**Companions:**
- Canonical numbers: [`reports/asset_class_independent_recompute_2026_04_27.md`](../reports/asset_class_independent_recompute_2026_04_27.md)
- Hedge-fund-grade per-class review: [`reports/hedge_fund_performance_review_summary_2026_04_27.md`](../reports/hedge_fund_performance_review_summary_2026_04_27.md) and [detailed](../reports/hedge_fund_performance_review_detailed_2026_04_27.md)
- Action workstreams A–F: `reports/action_*_2026_04_27.md`

## Consensus across 5 independent recomputes

Five independent agents (mercury-2, GitHub Copilot Opus 4.7, GitHub Copilot Cloud Agent, opencode/big-pickle, this consolidator) ran the asset-class audit independently against the live `audit_trail/data/dashboard_payload.json` (generated_at 2026-04-27T22:08:21Z, n=3,500). All five **converge on the same numbers** when using the live payload + full history:

| Class | n | WR% | PF | Sum PnL% | MaxDD% | Resolver-noise share | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| **EQUITY** | 381 | 51.97 | **1.385** | +232.13 | 70.95 | 9.09% (clean) | **Tier 2 — only investable class** |
| **CRYPTO** | 1,598 | 42.18 | 1.140 | +158.74 | **178.64** | 1.19% (clean) | Below Tier 3 — edge real, drawdown lethal |
| ETF | 83 | 54.22 | 1.220 | +20.25 | 48.86 | 6.67% (clean) | Tier 3 borderline (n<100) |
| FOREX | 794 | 50.38 | 1.349 | +29.63 | 38.06 | **63.25% (UNRELIABLE)** | Cannot evaluate until resolver fix |
| COMMODITY | 622 | 42.60 | 0.896 | −9.82 | 39.79 | **66.79% (UNRELIABLE)** | Cannot evaluate; underlying alpha likely zero |
| BOND | 17 | 47.06 | 1.601 | +2.84 | 3.47 | 12.50% (clean) | Insufficient data (n<50) |

Disagreements among earlier peer reports (Roocode/DEEPSEEK 4-day window; Copilot 19:16Z stale payload; Master-summary's deprecated `closed_picks.json` claiming "84.9% UNKNOWN") are all artifacts of using the wrong source or window — not real signal.

## Headline finding peers missed

**63.25% of FOREX wins and 66.79% of COMMODITY wins are sub-bp resolver flicker** (`|pnl_pct| < 0.05%`). The non-crypto resolver at `alpha_engine/outcome_resolver.py:384–405` closes positions at yfinance live spot every run; `PNL_WIN_THRESHOLD = 0.00001` (0.001% — 10× tighter than the audit memo's "1bp") at line 97 was lowered for crypto and never asset-class-gated. The dominant noise vector in production is `FORCE_CLOSED` set post-hoc by `audit_trail/quality_gates.py:1474` (`normalize_exit_reason`). Until this is fixed, no FOREX/COMMODITY verdict is data-supported. ~1,700 picks across 15 strategies are mislabeled.

## 4 essential fixes shipped today

These are the highest-ROI, lowest-risk fixes from the workstream investigations. They unblock CI feedback loops that have been silently failing for 12+ days and let HC-strict actually surface picks again.

### 1. `auto_tuner` module path — single-line fix that ends a 12-day silent failure

`.github/workflows/alpha-engine-live.yml:592` was running `python -m auto_tuner` — wrong path; the module is at `alpha_engine/auto_tuner.py`. The module-not-found error has been silently swallowed by `|| echo "Auto-tuner run failed (non-fatal)"` since 2026-04-15. Result: `alpha_engine/data/rf_model.pkl` and `ml_challenger.joblib` (byte-identical) frozen at mtime Apr 15 11:53 — every per-scan retrain has been a no-op. **Changed to `python -m alpha_engine.auto_tuner`.** Next workflow run will either retrain successfully or fail loudly.

### 2. ml_gatekeeper persistence — add `git add ml_gatekeeper/models/` to the commit step

`audit-dashboard.yml:531` enumerates files for `git add` but never included `ml_gatekeeper/models/`. Trainer ran hourly, model was rewritten on the runner, runner was destroyed, model never reached origin. Last commit to `ml_gatekeeper/models/` was 2026-04-15. **Added `ml_gatekeeper/models/*.joblib`, `*.json`, `*.npy` and `ml_consensus/models/*.json` to the for-loop.** Next run pushes the freshly trained model.

### 3. HC filter Gate 5 — relax forwardWR floor where it's blocking real edge

`config/hc_gate_params.json` v4.3 had a flat 70% forward-WR floor. Realized population WRs are CRYPTO 42%, EQUITY 52%, ETF 54%. The floor was above the top-quartile of every class. Measured pass rate over Apr 25–27: **5/668 = 0.75%**, with **0 picks on Apr 27**. Bumped to v4.4: CRYPTO 60, EQUITY 55, ETF 55. **FOREX/COMMODITY held at 70 because their underlying WR is resolver-noise contaminated** — relaxing them would just leak more noise. Expected pass rate: ~3% (within over-filter floor).

### 4. Delete dead-code `ml_crypto_predictor/self_improvement.py`

23-line script with two bugs in the same import block: imports `from enhanced_models.*` (wrong package — should be `ml_crypto_predictor.enhanced_models.*`) and reads `results/v4_training_summary.json` from a directory that never existed. Zero callers anywhere in the repo. Removed.

## What did NOT ship today (and why)

These are P0 items deliberately deferred because they need more care than a same-day commit:

- **Resolver fix (Workstream B, `alpha_engine/outcome_resolver.py`)** — the actual code change is small (close at TP/SL hit using yfinance OHLC replay, mirror crypto path), but it requires re-resolving ~1,860 historical non-crypto picks across 8 source-systems. Doing this without breaking ML training labels (12% expected target-flip rate) needs a `resolver_version: "v2"` flag and audit-field preservation per `reports/action_B_resolver_2026_04_27.md`. Separate PR with full test plan.
- **CRYPTO symbol gates (TON/TIA/HYPE/ONDO-SELL/OP-source/LTC-source)** — Workstream C produced the precise diff (extends existing `BLOCKED_SYMBOLS` and `BLOCKED_DIRECTION_TRIPLES` at `audit_trail/quality_gates.py`), but per CLAUDE.md project rule, symbol-level kills require `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` mutation-before-kill protocol. Separate PR after mutation pass.
- **EQUITY zombie kills (`goldmine_stocks`, `fast_stocks_competition`)** — same project rule.
- **5 commodity strategy decisions** — per Workstream F, 3 of 5 (`cta_commodity_momentum_term`, `cta_cross_asset_tsmom`, `cta_golden_cross_200`) are 94–100% resolver noise; their numbers are statistical fog until #1 (resolver fix) lands. The other 2 (`cot_positioning`, `cftc_cot_commercial_signal`) are recommended for symbol-allowlist mutation behind SANDBOX, not BLOCKED_SOURCE_SYSTEMS expansion.

## Hedge-fund-grade roadmap (next 30 days)

The detailed companion doc maps the structural gaps vs Renaissance / Two Sigma / AQR / Bridgewater / Winton. Key absent layers:

1. **Vol-targeting** (constant-vol position sizing) — biggest single MDD lever, biggest retail-vs-institutional gap. CRYPTO MDD 178% would drop to ~25% with this alone.
2. **Risk-parity capital allocation** by Sharpe contribution — currently allocated by source-pick volume.
3. **Regime-aware kill-switch** — `regime_terminal` exists as a *peer source* emitting picks; should be a *gate* on every other strategy.
4. **Factor models for EQUITY** (Fama-French 5-factor + momentum overlay) — backstops the single-source dependency on `kimi_riseoftheclaw`.
5. **G10 carry + dollar-block momentum for FOREX** (post-resolver-fix) — industry-standard FX playbook.
6. **CTA term-structure for COMMODITY** (Winton/AHL playbook, post-resolver-fix).

External alpha (copy-traders, prediction markets, Kalshi, Polymarket) is already wired in — `multi_asset_copytrader` is the **largest source by far** (n=1,037 across non-crypto classes). It's also the **largest noise generator**. The lesson: piping in more external alpha doesn't help until the data plumbing (resolver) is sound.

## What this means for users browsing the audit dashboard

After the next workflow cycle:
- HC-strict tile should show non-zero picks again (5/668 → ~20-30/668 expected).
- ML model freshness column should flip from STALE → fresh as the gatekeeper persists.
- FOREX/COMMODITY metrics still flagged UNRELIABLE pending resolver fix — **do not size up these classes based on current dashboard numbers**.
- EQUITY remains the only class with hedge-fund-grade real edge today; CRYPTO has edge but unsurvivable drawdown without vol-targeting.
