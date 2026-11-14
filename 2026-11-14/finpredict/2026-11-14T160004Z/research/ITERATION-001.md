# ITERATION-001 — Data-purity gate first, candidate seeds (2026-11-14 18:15Z)

Ran the proof bar's first two gates (purity + multiple-testing) over the canonical policy-clean ledger `audit_dashboard/data/pf_registry.json::by_asset_class_strategy_policy_clean_net` (683 strategy rows) and `anti_overfit_audit.json` (80 audited strategies).

## Result: FAIL at gate 1 — the ledger is contaminated, so nothing is "provable" yet

**15 strategies pass a naive Bonferroni test on win-rate (PF>1), but all 15 are CRYPTO with WR 77–98% and PF 5–56** — statistically impossible in real trading. They are the frozen-price / placeholder cohort the audit already proved fake, not edge:

| strategy | n | WR | PF | verdict |
|---|---|---|---|---|
| ADX Trend Confirmation | 213 | 97.2% | 56.7 | frozen-verified-batch |
| mega_mut_macd_rsi_m084 | 124 | 90.3% | 49.4 | mega-mutation (implausible) |
| CorrKamaAdaptiveStrategy | 142 | 95.8% | 37.3 | frozen-verified-batch |
| CorrVwapZscoreReversionStrategy | 179 | 95.5% | 35.1 | frozen-verified-batch |
| Multi-Timeframe Trend Alignment | 394 | 87.1% | 11.1 | frozen/implausible |
| Price Acceleration Detector | 234 | 77.4% | 5.6 | implausible |
| (+ 9 more of the same shape) | — | — | — | artifact |

**Conclusion of iteration 1:** the honest, provable finding is *negative* — the apparent crypto "edges" are fabricated/frozen-price artifacts. A profitable approach **cannot be proven on this ledger until gate 1 (purity) is applied**. This is the first, mandatory iteration result.

## Candidate seeds (plausible, not yet proven) — to validate after purity fix

These have credible WR (40–53%) and modest PF (1.2–1.7), i.e. they are *not* artifacts, but their PnL is still unverified against the contamination:

| strategy | class | n | WR | PF | caveat |
|---|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | FOREX | 1,464 | ~? | 1.645 | HIGH_AUTOCORR (from anti-overfit) |
| `Bollinger Squeeze Breakout` | CRYPTO | 745 | 46.7% | 1.44 | |
| `CCI Reversal Scout` | CRYPTO | 257 | 44.4% | 1.31 | mean-reversion |
| `VerifiedStochRsiStrategy` | CRYPTO | 231 | 50.2% | 1.66 | |
| `MeanReversionBB` | EQUITY | 201 | 49.8% | 1.41 | |

None clears the bar today (PF < 1.5 except one, no CI, contamination unresolved).

## Next iteration (002)

1. Apply purity filters to the per-trade ledger (exclude frozen/unquoted, flat-3% cohort, forward-seed batch, zero-entry, single-source ≥40%).
2. Re-aggregate PF/WR on the clean subset.
3. Run `benchmark_closed_ledger.py` (bootstrap + random-entry MC) on the surviving seeds.
4. Report which seeds survive — expect 0–2.

*Tooling:* `pf_registry.json` (policy-clean), `anti_overfit_audit.json` (DSR/autocorr), `benchmark_closed_ledger.py` (bootstrap), `walkforward_validator.py` (OOS). MySQL `at_signal_outcomes.intrabar_pnl_pct` is the eventual source of truth for purity.
