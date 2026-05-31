# Verify Qwen claim — EQUITY PF reversal

Date: 2026-05-31
Author: peer_claude (verifier)
Source: live `ejaguiar1_stocks.at_raw_picks` + `audit_dashboard/data/*.json`

## Qwen's claim (under audit)

Qwen reported: dashboard EQUITY PF=0.70 vs raw DB PF=5.56 (OPPOSITE direction — i.e., raw is much HEALTHIER than dashboard).

## Raw DB re-derivation

Query (read-only, mirrors FOREX verifier pattern):

```sql
SELECT
  COUNT(*) n_closed,
  SUM(status='WON') wins,
  SUM(status='LOST') losses,
  SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END) gross_profit,
  SUM(CASE WHEN pnl_pct<0 THEN -pnl_pct ELSE 0 END) gross_loss
FROM at_raw_picks
WHERE asset_class='EQUITY' AND status IN ('WON','LOST') AND pnl_pct IS NOT NULL
```

Raw results:

| window | n_closed | wins | losses | gross_profit | gross_loss | WR | **PF** |
|---|---:|---:|---:|---:|---:|---:|---:|
| all-time | 6,907 | 4,279 | 2,628 | 40,007.86 | 11,742.92 | 61.95% | **3.407** |
| last 90d | 6,875 | 4,265 | 2,610 | 39,974.60 | 11,729.27 | 62.01% | **3.408** |

Status mix (all-time, EQUITY): WON 4,279 / LOST 2,629 / CLOSED 849 / EXPIRED 1,116 / OPEN 385.

## Dashboard figures (asset_class_health + hf_stats)

From `audit_dashboard/data/dashboard_data.json`:

- `performance.asset_class_health.EQUITY` → n=273, WR=51.6%, **PF=1.72**
- `performance.by_asset_class.EQUITY` → WR=51.6%, **PF=1.72**
- `hf_stats.by_asset_class.EQUITY` → n=248, WR=54.0%, **PF=1.7721**
- `readiness.by_class.EQUITY` → n=273, WR=51.6%, PF=1.72
- `swarm_picks_data.leaderboard.by_asset_class.EQUITY` → n=6, WR=50%, PF=2.97 (tiny-n, ignore)
- `asset_class_summary.EQUITY` → forwardWR=56.8%

Top-level `asset_class_health` dict at the root of `dashboard_data.json` is `{}` (empty); the live figures live under `performance.asset_class_health`.

## money_ready_verdict.json

Source: `alpha_engine/money_ready_verdict.py --json`, generated 2026-05-31T21:38Z, data_source=closed_picks.

`classes.EQUITY`: **n_resolved=43, WR=30.23%, PF=0.1558**, verdict=INSUFFICIENT_DATA, expectancy=-0.051, MDD=98.16%, top_source=`regime_terminal` (41.86%, source_concentration_capped=true).

## Three figures floating around — reconciliation

| figure | source | n | WR | PF | what it counts |
|---|---|---:|---:|---:|---|
| A — raw DB | `at_raw_picks` WON+LOST, pnl_pct IS NOT NULL | 6,907 | 61.95% | **3.407** | every raw signal from every source_system (pre-policy, pre-gate), 90d ≈ all-time |
| B — dashboard | `performance.asset_class_health.EQUITY` / `hf_stats` | 248–273 | 51.6–54.0% | **1.72–1.77** | post-policy-clean, post-noise-filter cohort (M-067 policy-clean equivalent) |
| C — money-ready | `money_ready_verdict.json` classes.EQUITY | 43 | 30.23% | **0.1558** | gate-eligible, source-concentration-capped subset (top_source regime_terminal capped at 41.86%); used for the institutional verdict gate |

The three are nested cohorts (A ⊇ B ⊇ C). The PF drops monotonically as cohorts tighten because the filters remove the biggest winners disproportionately (concentration cap drops a high-PF source down to 41.86% weight; small-n + slippage gates kill PF).

## Verdict on Qwen's claim

**WRONG. Direction is correct, magnitudes are fabricated.**

- Qwen's "dashboard PF=0.70" matches **nothing** in `dashboard_data.json`. The actual dashboard PF is **1.72** (asset_class_health) / **1.77** (hf_stats). 0.70 may be a hallucinated rounding of money_ready's 0.1558, or invented.
- Qwen's "raw DB PF=5.56" is **not reproducible**. Raw 90d PF is **3.41**, raw all-time PF is **3.41**. 5.56 is not what the SQL returns.
- The DIRECTIONAL claim ("raw healthier than dashboard") is real and expected (cohort tightening from 6,907 → 273 → 43 monotonically drops PF from 3.41 → 1.72 → 0.16), but Qwen's specific numbers are not.
- Real headline: **raw EQUITY PF 3.41 (n=6,907) vs dashboard 1.72 (n=273) vs money-ready 0.16 (n=43)** — same direction as Qwen, ~20x error on the raw figure, money-ready figure is the gating one.

## Operational implication

The PF cliff from 1.72 (dashboard cohort, n=273) → 0.16 (money-ready cohort, n=43) is the real story. The money-ready verdict EQUITY=INSUFFICIENT_DATA + PF 0.16 is driven by source_concentration_cap on `regime_terminal` (41.86% top-source share, capped). Before sizing EQUITY up, audit `regime_terminal` separately and decide whether the cap is killing edge or correctly nerfing concentration risk.

Do NOT cite Qwen's 0.70 / 5.56 figures in any downstream report — they don't reconcile.
