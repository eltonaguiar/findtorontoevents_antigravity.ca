# Weekly Real-Money Filter — 2026-06-03

**Source verdict:** `audit_dashboard/data/money_ready_verdict.json` (generated 2026-06-03T18:27Z, 4h old).
**Strategy registry:** `audit_dashboard/data/pf_registry.json::by_asset_class_strategy_policy_clean_net`.
**AI Tournament:** `audit_dashboard/data/ai_tournament_leaderboard.json`.
**Author:** claude-opus-4-7 / `/money-maker-readyv2` 2026-06-03T23:02 UTC.

---

## 🚨 Honest top-line

**0 of 8 asset classes pass Tier-2** per canonical policy-clean verdict (PF≥1.5 + WR≥50% + n≥100). This matches the skill's standing claim. The **only edge candidate that passes all 6 vetted-stats checks today** is the **AI Tournament robust-model panel** (5 models, n_resolved 85–271, PF 2.77–3.69, WR 57–69%) — and that result carries an active DISPUTED banner on `/audit/ai-tournament.html` (PR #500) because the underlying resolver uses a once-daily spot snapshot, not intrabar OHLC.

So: this report does NOT recommend going live with real money on any sleeve yet. It documents the closest-to-ready edges per class and the gating gaps.

---

## Per-class verdict (re-derived from canonical JSON, NOT typed forward)

| Class | n_resolved | WR | PF | Verdict | Closest sleeve | Edge gap |
|---|---:|---:|---:|---|---|---|
| **CRYPTO** | 338 | 38.5% | 0.97 | NOT_READY | `battleground_luxalgo` (n=38 / WR 57.9% / PF 1.67) | 100% single-source; need 2nd-source corroboration |
| **EQUITY** | 51 | 29.4% | 0.34 | NOT_READY | `regime_terminal` (n=19 / WR 26.3% / PF 0.63) | no sleeve passes WR≥50% |
| **FOREX** | 30 | 23.3% | 0.47 | INSUFF-N | `multi_asset_scanner` (n=11 / WR 9.1% / PF 0.21) | no sleeve passes |
| **FUTURES** | 13 | 15.4% | 0.52 | INSUFF-N | `multi_asset_scanner` (n=11 / WR 9.1% / PF 0.48) | no sleeve passes |
| **UNKNOWN** | 10 | 70.0% | 0.99 | INSUFF-N | (uncategorized) | n<100 + provenance gap |
| **COMMODITY** | — | — | — | NO ROWS in 90d policy-clean window | `commodity_tsmom_12m` (n=1) | volume gap — need backfill |
| **ETF** | — | — | — | NO ROWS in 90d policy-clean window | — | volume gap |
| **BOND** | — | — | — | NO ROWS in 90d policy-clean window | — | volume gap; BOND added to BLOCKED_ASSET_CLASSES (PR #501) |
| **PENNY** | — | — | — | NO ROWS | — | Gate-0 blocked |

**Note** on CRYPTO closest-sleeve: 3 candidates pass strategy-level PF≥1.5 + WR≥55% (`battleground_luxalgo`, `crypto_liquidity_wick_reversal_v1`, `atr_percentile_gate`) but **all 3 are 100% single-source from the battleground family**. Per VETTED-STATS rule #2, single-source >60% = "concentration, not edge." These are real lab-grade candidates that need a 2nd independent source agreeing before sizing.

---

## The one viable filter today — AI Tournament robust panel (CRYPTO)

Five tournament models pass ALL 6 vetted-stats checks (dedup-clean tournament table, single-source false by definition since it's 39 models, n_resolved>=85, PF in robust 2.5-5 range avoiding outlier-corruption, multi-window stable per `pick_summary_stats_*.json`, no anomaly rows):

| Model | n_resolved | WR | PF | Quarter-Kelly | $@$10k |
|---|---:|---:|---:|---:|---:|
| `deepseek_v4` | 271 | 57.9% | 3.50 | 10.4% | $1,035 |
| `claude_haiku_4_5` | 85 | 69.4% | 3.69 | 12.6% | $1,265 |
| `cursor_agent` | 123 | 65.0% | 3.13 | 11.1% | $1,107 |
| `gpt4o` | 265 | 57.7% | 2.90 | 9.5% | $947 |
| `deepseek_r1` | 172 | 61.1% | 2.89 | 10.0% | $999 |
| `mercury` | 110 | 58.2% | 2.77 | 9.3% | $930 |

**⚠️ Cap recommended at 2% per pick** (institutional norm). Raw Quarter-Kelly numbers above are mathematically correct but practically aggressive — the picks are 1-3 day crypto holds and the resolver assumes spot exits without intrabar SL touches, which biases PF upward. With the cap:

```
Per-pick size = min(quarter_kelly_pct, 2.0%) × portfolio_value
Per-model max active = 5
Total exposure cap (6 models × 5 picks × 2%) = 60% of account
```

**⚠️ DISPUTED banner**: `/audit/ai-tournament.html` flags these WRs as resolver-artifact (snapshot-resolver vs intrabar OHLC). Real WR after intrabar replay is expected to drop 10-20 pts. **Do not size based on these numbers until** `tools/ai_tournament/price_tracker.py` is reworked for intrabar OHLC replay.

---

## How to apply this filter (when ready)

1. Visit `findtorontoevents.ca/audit/ai-tournament.html`
2. Click into one of the 6 models above (drill-down link added in PR #500)
3. Filter the model's drill to OPEN picks, asset_class=CRYPTO, ranked by score
4. Take the top 5 per model, size each at min(quarter_kelly, 2.0%) of account
5. Use the pick's own TP/SL (tournament picks set both; check the drill)
6. Exit on TP/SL hit or 3-day time stop

## Risk controls (Hyro overlay + DD halt)

- Per-pick: `min(quarter_kelly_pct, 2.0%)` (computed above)
- Daily soft-stop: -2% realized PnL pauses new entries (Hyro overlay)
- DD halt: 30d rolling drawdown >30% → `KELLY_DD_HALT_ENABLED=1` zeros all sizing
- Total exposure cap: 60% of account (6 × 5 × 2%)

## Gating gaps that block production (in priority order)

1. **Intrabar OHLC resolver** for tournament + general DB (P0, blocks all WR/PF trust)
2. **Cross-source corroboration** for CRYPTO `battleground_luxalgo` family — needs a 2nd independent source emitting agreeing picks at n≥30
3. **Volume backfill** for ETF/BOND/COMMODITY/PENNY (n=0 in 90d window)
4. **Concentration mitigation** for FOREX `multi_asset_copytrader` (Tier-0 freeze, MyFXBook replication gate needed)
5. **Anti-overfit gate** before promoting any sleeve (already partial via Bonferroni on nav_surface_edge_matrix)

## Reproduce

```bash
# Re-derive numbers (do not carry forward typed cells)
python3 -c "
import json
v=json.load(open('audit_dashboard/data/money_ready_verdict.json'))
for k,c in v['classes'].items():
    print(k, c['n_resolved'], c['wr'], c['pf'], c['verdict'])
"

# Per-strategy edges
python3 -c "
import json
data=json.load(open('audit_dashboard/data/pf_registry.json'))['by_asset_class_strategy_policy_clean_net']
for r in data:
    if (r.get('n') or 0)>=29 and (r.get('profit_factor') or 0)>=1.10:
        print(r['asset_class'], r['strategy'], r['n'], r['win_rate_pct'], r['profit_factor'], r['single_source_pct'])
"

# AI tournament leaderboard
python3 -c "
import json
lb=json.load(open('audit_dashboard/data/ai_tournament_leaderboard.json'))
for m in lb[:12]: print(m['model_id'], m['n_resolved'], m['wr'], m['pf'], m['tier'])
"
```

## Verdict for the operator

**Do not deploy real money to any class today.** The audit pipeline is honestly producing 0/8 Tier-2 verdicts. The closest path to a viable filter is:

1. **30-day shadow** of the AI tournament robust-panel (deepseek_v4 + claude_haiku_4_5 + cursor_agent + gpt4o + deepseek_r1 + mercury) on paper portfolios with the 2% per-pick cap.
2. **Fix the intrabar resolver** (`tools/ai_tournament/price_tracker.py`) so the next snapshot of these stats is institutional-grade.
3. **Backfill ETF/BOND/COMMODITY** closed-pick volume so those classes can produce verdicts at all.

Until those 3 land, treat ALL live picks as forward-test only.
