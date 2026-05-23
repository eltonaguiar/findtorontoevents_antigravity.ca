# Deep-Dive Supplemental Matrix (2026-05-14)

Supplement to the original deep-dive plan, based on `session-ses_1db6.md` extra items.

| item_id | status | evidence/check | verification command | notes |
|---|---|---|---|---|
| `cot_db_verifier_execution_evidence` | `PARTIAL` | dry-run passes; live run attempted and failed with DB auth error (captured) | `python tools/verify_multi_asset_cot_db.py --dry-run` and `python tools/verify_multi_asset_cot_db.py` | blocker captured with explicit mysql error |
| `cot_post_patch_verifier_available` | `COMPLETE` | verifier tool is present and callable | `python tools/verify_cot_post_patch.py --help` | ready for operator-backed run |
| `browser_drift_auto_paper_only_enforcement` | `MISSING` | no drift/paper-only enforcement tokens found in `money_ready_filter.js` | `rg "drift_alert|paper-only|paper_only|auto.*paper" audit_dashboard/money_ready_filter.js` | advisory-only behavior still implied |
| `strategy_level_staleness_contract` | `MISSING` | `production_scanner.py` lacks strategy-level stale fields contract (`strategy_stale_days`/`strategy_is_inactive`) | `rg "stale_since|strategy_stale_days|strategy_is_inactive" alpha_engine/production_scanner.py` | system-level stale metadata exists, strategy-level absent |
| `etf_xlf_xle_xlk_expansion_readiness` | `PARTIAL` | symbols exist in some strategy modules but not in scanner override contract used by supplemental check | see generated JSON report | requires explicit authoritative universe contract alignment |
| `bond_fred_key_path_presence` | `COMPLETE` | `FRED_API_KEY` wiring exists in macro pipeline | `rg "FRED_API_KEY" alpha_engine/macro_data_pipeline.py` | runtime secrets and source reliability still external |
| `dsr_browser_gate_parity` | `COMPLETE` | `_passesDsrGate` wired in `hc_filter.js` | `python -m pytest tests/test_deep_dive_verification_2026_05_14.py -q` | completed in prior execution |
| `smart_score_shadow_payload_visibility` | `COMPLETE` | `smart_score_v2_shadow` retained in dashboard payload keep-field list | `python -m pytest tests/test_deep_dive_verification_2026_05_14.py -q` | completed in prior execution |

## Supplemental prework outputs

- `reports/supplemental_prework_audit_2026_05_14.json` (machine-readable check report)
- `tools/supplemental_prework_audit.py` (repeatable prework checker)

