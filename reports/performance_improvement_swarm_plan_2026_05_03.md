# Performance Improvement Swarm Plan — 2026-05-03

Goal prioritized: **#1 — audit dashboard performance and integrity**.

## What Was Asked

Use the agent swarm effectively to answer:

1. Where is the current edge by asset class?
2. Where should a real-money user go on `findtorontoevents.ca/audit`: `Active Picks`, `Smart Picks`, `Verified Alpha`, `High Conviction`, or somewhere else?
3. Ask many agents/personas for a plan to improve each asset class.
4. Identify backtests and hedge-fund/quant-approved stats/frameworks that can be integrated for quick wins.

## Primary Answer

The current best real-money path is:

1. Open `/audit`.
2. Read the `Performance` / `? Guide` section first.
3. Go to `Active Picks`.
4. Use `Active Picks` as a shortlist only, not as proof of edge.
5. Prefer selective `EQUITY` and very selective `CRYPTO` subsets; treat `ETF` as watch/thin; avoid `FOREX`; keep `COMMODITY` diagnostic/paper until the PF vs walk-forward conflict is resolved.

Do **not** tell users that `Smart Picks`, `Verified Alpha`, or `High Conviction` are fully proven real-money routes yet. Current payload has:

- `77` active picks: `CRYPTO 38`, `EQUITY 29`, `FOREX 6`, `ETF 4`.
- `smart_picks_feed`: `4` picks, all `CRYPTO`.
- `0` active rows stamped with `is_smart_pick`, `is_verified_alpha`, or `hc_tier`.
- Verified Alpha backend allow-list: only `claws_of_doom`.
- UEPS says it is building track record `n=0/100`.

## Local Performance Audit

Command run: a read-only Python audit of `audit_dashboard/data/dashboard_data.json` using current `picks.recent_closed` (`n=3500`).

Recent-closed asset stats:

- `EQUITY`: `n=264`, `WR 56.3%`, `PF 1.64`, avg PnL `+0.856%`, sum PnL `+225.95%`.
- `ETF`: `n=86`, `WR 54.7%`, `PF 1.24`, avg PnL `+0.265%`.
- `CRYPTO`: `n=1537`, `WR 43.1%`, `PF 1.27`, avg PnL `+0.171%`.
- `COMMODITY`: `n=675`, `WR 44.1%`, `PF 1.04`, near-flat avg PnL.
- `FOREX`: `n=913`, `WR 48.6%`, `PF 1.41`, avg PnL `+0.025%`.
- `BOND`: `n=20`, `WR 55.6%`, `PF 1.72`, too thin.

Important band results:

- `EQUITY R:R 1.5-2.0`: `n=199`, `WR 54.8%`, `PF 1.78`, avg PnL `+1.154%`.
- `CRYPTO R:R 1.0-1.5`: `n=84`, `WR 56.0%`, `PF 1.69`.
- `CRYPTO R:R 1.5-2.0`: `n=808`, `WR 48.0%`, `PF 1.34`.
- `CRYPTO R:R >=2.0`: `n=622`, `WR 33.8%`, `PF 0.88`, negative avg PnL.
- `FOREX R:R 1.5-2.0`: `n=88`, `WR 25.6%`, `PF 0.58`.
- `CRYPTO confidence 0.85-0.90`: `n=23`, `WR 69.6%`, `PF 4.71`, promising but thin.
- `EQUITY confidence <0.60`: `n=140`, `WR 61.4%`, `PF 2.32`, surprising and needs source/feature audit before promotion.
- `FOREX confidence 0.70-0.80`: `n=543`, `WR 50.3%`, `PF 2.65`, conflicts with asset-health `PF 0.27`; needs window/resolver reconciliation.

Interpretation: `recent_closed` confirms Equity is the cleanest current edge candidate. It also confirms R:R bands must be derived per asset class and per window, not copied from old guide text.

## Swarm Runs

Prompt files:

- `swarm_runs/audit_performance_improvement_deep_dive_prompt_2026_05_03.md`
- `swarm_runs/audit_performance_improvement_compact_prompt_2026_05_03.md`

Large persona runs:

- `performance_improvement_cross_asset_2026_05_03`
- `performance_improvement_ml_validation_2026_05_03`
- `performance_improvement_regime_2026_05_03`
- `performance_improvement_rr_2026_05_03`
- `performance_improvement_costs_2026_05_03`
- `performance_improvement_forex_2026_05_03`

Compact broad run:

- `performance_improvement_compact_2026_05_03`

Engine health:

- Large schema/persona prompt produced useful Mercury outputs but empty raw bodies from several API engines. Treat those empty outputs as non-votes.
- Compact prompt produced useful votes from `inception`, `kilo`, `opencode`, plus substantive non-schema output from `agent` and `ollama_cloud`.
- Do not count `cerebras`, `deepseek`, `openrouter`, or `xai` empty bodies from the compact run as evidence.

## Swarm Consensus

### User Path Today

Consensus: use `Performance Guide` + `Active Picks`.

- Mercury: `Performance Guide`, with `EQUITY` / `ETF` most OK but caveated.
- Kilo: `Active Picks`, real-money OK only for `EQUITY` / `ETF`.
- OpenCode: `Active Picks > EQUITY/ETF`, avoid `FOREX`, `COMMODITY`, broad `CRYPTO`.
- Local data adds nuance: `ETF` is still thin/noisy, so it is watch-only rather than real scale.

Final user-path recommendation:

- Real money: selective `EQUITY` first.
- Small/paper/selective: crypto subsets, especially validated ML/proven/confidence bands.
- Watch only: ETF until sample grows.
- Paper/diagnostic: Commodity.
- Avoid: FOREX until diagnostic is complete.

### Asset Verdicts

| Asset | Verdict | Why |
|---|---|---|
| `EQUITY` | Selective / strongest edge candidate | Recent-closed `PF 1.64`, `WR 56.3`, walk-forward Sharpe `3.527`; still noisy and PF only slightly above T2 in recent closed, below T2 in `asset_class_health` (`PF 1.42`). |
| `ETF` | Watch / thin | Good WR and high Sharpe, but only `86` recent closed and `12` WF folds with huge std. |
| `CRYPTO` | Selective subset only | Aggregate WR/PF are weak; bands like `confidence 0.85-0.90` look good but have small `n=23`. |
| `COMMODITY` | Paper/diagnostic | Asset health says PF strong, recent closed near-flat PF `1.04`, walk-forward Sharpe negative. |
| `FOREX` | Avoid/rescue | Asset health severe (`PF 0.27`), recent closed conflicting (`PF 1.41`), R:R bands bad. Needs resolver/window/feed audit. |

## Recommended Framework Integrations

Priority order:

1. `ML4T Diagnostic` or equivalent DSR/PSR/CPCV tooling — use for Deflated Sharpe, Probabilistic Sharpe, PBO, purged CV, and multiple-testing correction.
2. `vectorbt` — quick fast backtest engine for R:R band sweeps, confidence-band sweeps, and per-asset vectorized what-if tests.
3. `quantstats` — lightweight tear sheets and dashboard-friendly risk metrics.
4. `RiskLabAI.py` — Lopez de Prado methods: triple barrier, purged/CPCV, feature importance, HRP/NCO. Higher integration effort but strong institutional fit.
5. `skfolio` — portfolio optimization/risk budgeting once per-asset edges are validated.

## Backtest Standard Before Promotion

Minimum before any asset class gets promoted to real-money/high-conviction:

- Closed-book sample `n>=100` clean trades for asset-level claims.
- Per-filter sample floor: ideally `n>=50`, with Wilson lower bound reported.
- Out-of-sample/walk-forward pass with fold dispersion shown.
- DSR and PSR for every headline Sharpe.
- Multiple-testing correction across searched filters/strategies.
- Purged or combinatorial purged CV with embargo for overlapping horizons.
- Cost/slippage model per asset class.
- Regime split: trend/chop/high-vol/low-vol and stress windows.
- PBO / parameter-stability check for any optimized filter.

## Top Actions

1. **Build R:R band audit script and wire it to dashboard copy.**
   - First target: `forward_test_gates.py`, dashboard Guide R:R copy, and a report from `picks.recent_closed`.
   - Evidence: current local audit shows `CRYPTO >=2.0R` is bad in recent closed, while `EQUITY 1.5-2.0R` is good.

2. **Stamp active rows with Smart Pick / Verified Alpha / HC tiers or remove overconfident UI claims.**
   - First target: `audit_trail/stamp_pick_quality.py`, `audit_trail/feed_membership.py`, dashboard active-row rendering.
   - Current active payload has zero stamps.

3. **Run FOREX resolver/window diagnostic.**
   - Reconcile `asset_class_health PF 0.27` vs current `recent_closed PF 1.41`.
   - Check feed schema, latency, resolver threshold, exit reasons, and time-window mismatch.

4. **Add DSR/PSR cards for Equity and ETF.**
   - Show Sharpe with std/folds/CI, not just headline OOS Sharpe.

5. **Create a commodity divergence report.**
   - Reconcile asset health `PF 1.78`, recent-closed `PF 1.04`, and WF Sharpe `-2.412`.

6. **Crypto subset isolation.**
   - Confirm whether `confidence 0.85-0.90`, ML-enhanced, and proven strategy cohorts survive `n>=50`, costs, and multiple-testing correction.

7. **Treat UEPS as building until it has closed data.**
   - Keep user-facing label honest: `n=0/100`.

8. **Add framework sidecar, not direct production dependency first.**
   - Start with `tools/quant_validation_sidecar.py` that imports optional libraries if installed and emits JSON metrics consumed by dashboard/reporting.

## Do Not Claim Yet

- Do not claim ETF is “strong edge” despite high Sharpe; it is thin/noisy.
- Do not claim Smart Picks / Verified Alpha / HC are fully validated active paths; current rows are unstamped.
- Do not claim broad crypto edge; only subsets may work.
- Do not kill FOREX without resolving the window/resolver contradiction.
- Do not promote commodity until the PF vs WF conflict is explained.
