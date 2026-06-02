# Quant strategy admissibility pipeline (2026-06-02)

## What shipped

1. **`docs/BACKTEST_ADMISSIBILITY_STANDARD.md`** — single 7-stage gate (pre-register → purged WF + costs → DSR/PBO → forward n≥100 → money_ready). Replaces ad-hoc promotion from `real_data_backtest.py` or raw leaderboard PF.

2. **`tools/strategy_admissibility_report.py`** — unified quant report JSON:
   - Live portfolio audit (81 books; 66 with open positions)
   - Per-class root causes + policy-clean money_ready
   - Edge map: `/audit/` vs ai-tournament vs pick_funnel vs verified lab
   - Writes `audit_dashboard/data/strategy_admissibility.json` + refreshes `verified_edge_status.json`

3. **`audit_dashboard/pf.html`** — strips invisible Unicode from `?key=` (fixes false-empty portfolio UI).

4. **`.github/workflows/verified-pilot-daily.yml`** — runs admissibility report after daily pilots.

## Verification

```bash
python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios
# → audit_dashboard/data/strategy_admissibility.json
# → portfolio_audit: 66/81 with open positions; deepseek_v4__aggressive open=11

curl -sA 'Mozilla/5.0' 'https://findtorontoevents.ca/audit/data/pf_portfolio_deepseek_v4__aggressive.json' | python3 -c "import json,sys; d=json.load(sys.stdin); print(len([p for p in d['positions'] if p.get('status')=='open']), 'open')"
```

## Key quant conclusions (unchanged)

- **Not mostly time** on production book — CRYPTO PF 0.89 policy-clean with n=377.
- **Edge location split:** tournament paper (deepseek_v4 n=208), pick_funnel CRYPTO RR cell (subset only), lab ETF DM (forward n<100).
- **Size capital only on** `money_ready_verdict` policy-clean — 0/9 classes ready.

Full write-up: `reports/quant_strategy_root_cause_review_2026-06-02.md`
