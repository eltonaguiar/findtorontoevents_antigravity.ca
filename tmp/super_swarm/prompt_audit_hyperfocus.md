# HYPERFOCUS: /audit + /audit/hyrotrader Deep Review

You are one of 11 engines doing a HYPER-DETAILED review of two prediction-edge dashboards:
- https://findtorontoevents.ca/audit
- https://findtorontoevents.ca/audit/hyrotrader (Hyrotrader prop firm challenge tracker)

## Live state evidence (already verified by prior swarm)

`audit_dashboard/data/dashboard_data.json`:
- `asset_class_health.FOREX`: PF 0.27 / WR 46.4% / n=1169 (sub-floor)
- `asset_class_health.CRYPTO`: PF 1.25 / WR 44.6% / n=8067 BUT `hf_stats.by_asset_class.CRYPTO`: PF 0.89 / WR 37.5% / n=1650 (recent subset shows degradation)
- `asset_class_health.EQUITY`: PF 1.41 / WR 52.7% / n=421 (T2-candidate)
- `asset_class_health.COMMODITY`: PF 1.78 / WR 46.9% / n=750 (PF tier-2 but WR sub-50)
- `asset_class_health.BOND`: PF 1.72 / WR 55.6% / n=18 (n below floor)
- `asset_class_health.ETF`: PF 1.24 / WR 55.2% / n=87 (borderline)
- `shadow_probation.enabled = false` despite documented R:R [1.5, 2.0] PF 5.81 edge
- 11/11 strategies in HIGH degradation alert
- Portfolio MDD 680.66% / Ulcer Index 332 (likely mark-to-market, not realized)
- EQUITY raw PnL 363.32 vs capped 35.71 — 10x outlier-driven gap
- COMMODITY KC=F = 147% of class PnL
- HYROTRADER: `trading_days_logged = 0` despite -70.66 USDT PnL
- `hyro_quan_bridge.json`: only BTCUSDT (14 symbols dropped, stale since Apr 18)
- HYROTRADER: all picks have null entry/stop/target prices

## Kimi audit verdict per asset class

| Asset | Kimi verdict | Gates passed/failed |
|---|---|---|
| Equity | SAFE | PF 1.72 ✅ / WR 53.1 ✅ / OOS Sharpe +3.527 ✅ / n=256 ✅ / Q-Kelly +5.3% ✅ |
| Crypto B | CAUTION | PF 1.28 ✅ / WR 45.0 ❌ / OOS -0.242 ❌ / n=940 ✅ / Q-Kelly +2.4% ✅ |
| Forex | DANGEROUS | PF 0.27 ❌ / WR 21.4 ❌ / OOS -1.406 ❌ / n=195 ✅ / Q-Kelly +3.5% ✅ |
| Commodity | DANGEROUS | PF 0.02 ❌ / WR 21.2 ❌ / OOS -2.412 ❌ / n=143 ✅ / Q-Kelly +0.4% ✅ |
| ETF | CAUTION | PF 1.10 ❌ / WR 52.9 ✅ / OOS 6.368 ⚠️ (12 folds artifact) / n=12 ❌ / Q-Kelly +2.9% ✅ |

Note: Kimi's numbers (PF 1.72 for Equity) differ from live (PF 1.41) — different time slices. Investigate.

## Charter floors
- T2: PF>1.5 / WR>50 / MDD<20 / n≥100
- T1 (Renaissance): PF>2 / WR>55 / MDD<10 / n≥200

## What I want from you (JSON envelope)

```json
{
  "engine": "<your name>",
  "verdict_summary": "<2-3 sentences on /audit + /audit/hyrotrader health>",
  "p0_audit_findings": [
    {
      "id": "AHF-XX",
      "page": "audit|hyrotrader",
      "claim": "<concrete>",
      "evidence_path": "<dashboard_data.json::field or hyro_quan_bridge.json::field>",
      "fix": "<file:line>",
      "severity": "critical|high|medium",
      "confidence": 0.0-1.0
    }
  ],
  "kimi_vs_live_reconciliation": [
    {"asset": "EQUITY", "kimi_pf": 1.72, "live_pf": 1.41, "explanation": "<why they differ>", "which_to_trust": "kimi|live|both_partial"}
  ],
  "hyrotrader_specific_concerns": [
    "<e.g. trading_days_logged=0 with non-zero PnL is impossible>"
  ],
  "missing_dashboard_features": [
    "<institutional-grade things /audit should show>"
  ],
  "ranked_top_5_implementations": [
    {"id": "IMPL-X", "title": "...", "files_to_edit": [...], "estimated_complexity": "S|M|L"}
  ]
}
```

## Hard rules

- Do NOT recommend blanket asset-class halts (CLAUDE.md mutate-before-kill protocol).
- DO surface dashboard-credibility issues (contradictions, look-ahead artifacts, single-symbol concentration).
- DO cite exact dashboard_data.json paths.
- Hyrotrader prop-firm context: 5%-daily / 8%-total drawdown bands.

Output ONLY the JSON envelope.
