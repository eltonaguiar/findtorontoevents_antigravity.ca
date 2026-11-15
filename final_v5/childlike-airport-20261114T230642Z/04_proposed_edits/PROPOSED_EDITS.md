# 04 — Proposed Edits (Concrete, Adjudicated)

Edits are proposals for maintainers; apply only after review in a clean branch with tests/repro where applicable.

## A. PnL / data integrity (P0)
| ID | Target | Proposed edit | Rationale / acceptance |
|---|---|---|---|
| PE-01 | `sync_all_picks_to_mysql.py` (and any PnL ingest) | Reject/flag rows with null/zero `entry_price` or missing side/qty; remove `%*100` heuristic; persist `pnl_unit`, `pnl_source`, `gross_pnl`, `net_pnl`, `quote_status`. | Eliminates unit coercion and fabricated returns. **Accept:** 0 unit/sign/calc mismatches on reconciliation set. |
| PE-02 | `audit_trail/universal_pick_resolver.py` | Keep gap-aware/conservative fill; populate `resolution_method/kind`, fill price, slippage; log when SL/TP not touchable intrabar. | Fixes stop-fill optimism (B3) and auditability (B5). **Accept:** replay parity on sampled gaps. |
| PE-03 | `audit_trail/dashboard_generator.py` | Stamp contract-faithful/caller-sourced after-cost fields; never emit “money-ready/pass” without cost+freshness+provenance gates; render UNQUOTED/STALE/NULL badges. | Prevents decorative readiness. **Accept:** gated UI states match backend. |
| PE-04 | `price_realism_check.py` & mark pipeline | Remove/retire hardcoded `expected_2026_prices`; validate against live/historical provider bounds + staleness; mark outliers `SUSPECT_MARK`. | Stops false realism. **Accept:** alerts on stale/hardcoded paths = 0. |
| PE-05 | Pick lifecycle jobs | Deterministic zombie/expiry resolver; require exit/mark evidence for terminal PnL; de-dup economic key. | Reduces 0%-forever/open-stale artifacts. **Accept:** open-age/stale counts within SLA. |

## B. Risk/cost/gating (P0/P1)
| ID | Target | Proposed edit | Rationale / acceptance |
|---|---|---|---|
| PE-06 | `tools/hc_gates_python.py` / CI | Enforce per-class net cost gate and freshness gate as blocking for “ready” labels; publish excluded counts. | Only cost-clearing, fresh classes emit. **Accept:** blocked when net<0 or stale. |
| PE-07 | `alpha_engine/regime_detector.py` coverage | Expand regime tagging coverage; persist `regime` per pick; fail-closed on missing regime for regime-dependent strategies. | Addresses ~0.25% coverage. **Accept:** coverage metric reported & thresholded. |
| PE-08 | Stats/validation (`alpha_engine/validation/statistical_gates.py`, harness) | Register trials (`n_trials`), compute DSR (effective-N), BH/Bonferroni, CSCV/PBO; require benchmark-relative tests. | Controls false discovery. **Accept:** no pass without adjusted significance. |

## C. MF/ETF plumbing (P1, evidence-gated)
| ID | Target | Proposed edit | Rationale / acceptance |
|---|---|---|---|
| PE-09 | `alpha_engine/asset_class.py`, MF pipeline | Add/wire `MUTUAL_FUND` (and ETF consistency) end-to-end: ingest, NAV/marks, costs (ER/load), next-NAV semantics, ledger. | Makes MF testable. **Accept:** reproducible NAV-based backtest. |
| PE-10 | MF/ETF universe config | Curate $0-min, no-load, ultra-low-ER subset (MF: FXAIX/FSKAX/SWPPX/SWTSX/FXNAX + FSMDX/FSSNX/FSGGX/SWISX; ETF: SCHB/VTI/ITOT/VOO/SPY, BND/AGG/SGOV, VXUS) with constraints metadata. | Low-capital, cost-controlled baseline. **Accept:** costs/constraints unit-tested. |

## D. QA/reporting (P0)
| ID | Target | Proposed edit | Rationale / acceptance |
|---|---|---|---|
| PE-11 | QA job/report (new, e.g. `tools/qa_pnl_validation.py`) | Implement 0%/blank-field validator per `05_qa_plan/QA_PLAN.md`; emit per-pick dispositions + aggregate rates. | Makes “0%” auditable. **Accept:** report covers all open & recently closed. |
| PE-12 | Docs/dashboards | Replace absolute claims with gated language (“candidate, not money-ready”) + n/window/gross-net/benchmark/source hash. | Prevents overstatement. **Accept:** copy lint/gate in CI optional. |

## Non-edits (explicit)
- No parameter mining/tuning to force pass; no capital promotion; no force-push; no inclusion of unrelated worktree changes.
