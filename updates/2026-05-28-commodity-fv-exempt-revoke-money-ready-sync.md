# COMMODITY FV Exempt Revoke + Hourly money_ready_verdict Sync

**Date:** 2026-05-28  
**Report:** `reports/asset_class_performance_gate_exemptions_20260528.md`  
**Swarm review:** `swarm_runs/asset-class-exemptions-20260528T210955Z/` (DeepSeek confirmed all claims)

## What was broken

1. **`_COMMODITY_FV_EXEMPT`** still included `multi_asset_cot` and `multi_asset_copytrader` in `passes_smart_gate`, while comments at lines 7665–7667 document their **falsified** 6.33× COT over-emission. Unvalidated picks could enter Smart Picks.
2. **`money_ready_verdict.json`** refreshed only daily (`money-ready-snapshot.yml` 06:15 UTC) while `dashboard_data.json` updates hourly → Major Goal banner showed **13h stale** standalone verdicts vs embedded `money_ready_verdicts`.

## What changed

| File | Change |
|------|--------|
| `audit_trail/quality_gates.py` | `_COMMODITY_FV_EXEMPT` → `commodity_cot_contrarian` only |
| `.github/workflows/audit-dashboard.yml` | Run `tools/money_ready_snapshot.py` before `build_pf_registry.py`; commit `money_ready_verdict.json` |
| `tools/deploy_audit_files.py` | FTP-deploy `money_ready_verdict.json` + `regime_report.json` (`audit_data` tag) |
| `tests/test_commodity_fv_exempt_revoke.py` | Regression on frozenset contents |

## Verification

```bash
python3 -m pytest tests/test_commodity_fv_exempt_revoke.py -q
python3 tools/money_ready_snapshot.py
python3 -c "import json; d=json.load(open('audit_dashboard/data/money_ready_verdict.json')); print(d.get('generated_at'))"
```

Post-deploy:
```bash
curl -sS 'https://findtorontoevents.ca/audit/data/money_ready_verdict.json' | python3 -c "import sys,json;print(json.load(sys.stdin)['generated_at'])"
```

## Exemption policy (unchanged)

No asset class received a **real-money sizing** exemption. See report §3.
