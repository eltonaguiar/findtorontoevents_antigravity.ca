# Audit Supplements Index — `audit-supplements-dsr-calibration-2026-05-02`

**Branch:** 9 commits ahead of origin/main · **Tests:** 68 passing across 7 modules · **New deps:** none
**Wiring:** 1 wired (default-off env flag), 7 opt-in sidecars. Does NOT touch `outcome_resolver.py`, kill-list, vol-targeting, `template.html`, or `audit-dashboard.yml`.

## Modules

| # | Module | Output | Tests | Wiring |
|---|---|---|---|---|
| 1 | `alpha_engine/confidence_calibrator.py` — per-class isotonic. CRYPTO inversion confirmed (38.2% vs 41.8% on n=1514). | `alpha_engine/data/confidence_calibrators.json` | 5 | **WIRED** behind `CONFIDENCE_CALIBRATION_ENABLED=1` |
| 2 | `tools/dsr_audit.py` — DSR with N=1213 from `dna_mutations.json` instead of N=209. | `tools/data/dsr_audit_results.json` + report | (extends) | sidecar |
| 3 | `tools/pick_notarizer.py` — SHA-256 of `picks.active`, append-only log. | `audit_trail/notary/notary_log.jsonl` | 8 | sidecar |
| 4 | `tools/wr_posterior.py` — Beta-Bernoulli + 95% CI + P(WR>50%). 9 winners, 18 kill candidates. | `tools/data/wr_posterior_results.json` | 9 | sidecar |
| 5 | `tools/wr_posterior_timeseries.py` — decay tracker. Flag if P(>50%) drops ≥0.30 from rolling-max. | `tools/data/wr_posterior_timeseries.json` | 8 | sidecar |
| 6 | `tools/preregistration_verifier.py` — YAML ledger + `yaml_hash` + notary entry. PASS/FAIL/PENDING/INVALID. | `audit_trail/preregistration/<id>.yaml` + `tools/data/preregistration_status.json` | 19 | sidecar |
| 7 | `tools/notary_anomaly_check.py` — 6 detectors: regression, schema, swing, stuck, identical-triple, malformed. | `tools/data/notary_anomaly_status.json` | 10 | sidecar |
| 8 | `tools/factor_attribution.py` — alpha/beta decomposition via `np.linalg.lstsq`. | `tools/data/factor_attribution_results.json` | 9 | sidecar |

## The 7 future-PR audit columns

| Column | Source | Tooltip |
|---|---|---|
| Calibrated conf | `confidence_calibrators.json` | "Per-class isotonic-regression-calibrated P(win)." |
| DSR (real N) | `dsr_audit_results.json` | "Deflated Sharpe with N=1213. >0 survives haircut." |
| Notary | `notary_log.jsonl` | "SHA-256 of `picks.active`. `verify --git-sha`." |
| P(WR > 50%) | `wr_posterior_results.json` | "Posterior probability true WR > 50%." |
| WR-decay | `wr_posterior_timeseries.json` | "🔻 if latest P(>50%) dropped ≥0.30 from rolling-max." |
| Pre-reg | `preregistration_status.json` | "PASS/FAIL/PENDING vs author's pre-committed threshold." |
| α share | `factor_attribution_results.json` | "% of return from alpha vs factor exposure." |

## Cooperation

```
dashboard_data.json
  ├─ picks.active ─→ pick_notarizer ─→ notary_log.jsonl ─→ notary_anomaly_check
  └─ picks.recent_closed ─→ outcome_resolver labels (Theme B in flight)
                                ├─→ wr_posterior.posterior_stats (shared)
                                │     ├─→ wr_posterior_timeseries (decay)
                                │     └─→ preregistration_verifier.compute_metric
                                └─→ factor_attribution (numpy lstsq)

confidence_calibrator ─→ smart_picks_engine._compute_ml_composite (WIRED)
dsr_audit ─→ extends tools/deflated_sharpe.py + reads dna_mutations.json
```

## Post-resolver-fix re-fit (when cloud agent's Theme B lands)

1. `python -m alpha_engine.confidence_calibrator fit`
2. `python tools/dsr_audit.py`
3. `python tools/wr_posterior.py`
4. `python tools/wr_posterior_timeseries.py`
5. `python tools/factor_attribution.py`
6. `python tools/preregistration_verifier.py verify-all`

`pick_notarizer` and `notary_anomaly_check` are resolver-independent.

## Caveats (from each docstring)

1. **Calibrator** — FOREX/COMMODITY/EQUITY labels partially resolver-noise; CRYPTO cleaner.
2. **DSR** — even N=1M only deflates 1 strategy. Bottleneck is upstream Sharpe inflation.
3. **Notarizer** — git-history timestamp; v2 = OpenTimestamps anchor.
4. **WR posterior / decay** — independence assumption; intervals are tighter than reality.
5. **Pre-registration** — render on /audit is a follow-up PR.
6. **Anomaly canary** — pure-python detectors; not Isolation Forest on 31MB payload.
7. **Factor attribution** — in-sample proxy; canonical version needs Ken French / dollar-block externals.

## How to land

PR title: **"Audit credibility supplements: 7 sidecar modules + 1 wired calibrator (68 tests)"**
Body uses sections 1, 2, 3, 6 above. Follow-up rendering PR is a separate change.
