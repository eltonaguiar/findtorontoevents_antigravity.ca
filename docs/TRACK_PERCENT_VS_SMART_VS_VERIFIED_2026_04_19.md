# Track% vs Smart Picks vs Verified Alpha — Empirical Comparison

**Date:** 2026-04-19
**Data:** `audit_dashboard/data/dashboard_data.json` — `picks.recent_closed` (3500 rows, 3313 usable, 187 dropped for missing close timestamp)
**Anchor:** max(`closed_at`) = 2026-04-19T18:09:36Z
**Script:** `tools/track_percent_vs_smart_vs_verified.py`

## Methodology

For each closed pick we extract the close timestamp (`closed_at`), `pnl_pct`, `forward_wr` (pick level), `strat_fwd_wr` (strategy level), `trust_tier` / `at_issue_trust_tier`, and the at-issue gate inputs. Rolling windows are computed backward from max(close). For each picker we compute n, WR (wins / n where win = pnl_pct > 0), mean PnL%, total PnL%, profit factor PF = Σpos / |Σneg|, and a Sharpe-like mean/σ. The Smart Picks gate is `passes_smart_gate(pick)` after neutralizing the `status` field (closed picks would otherwise be short-circuited by the `passes_active_gate` status check). Track% is computed two ways: **pickwr** = `forward_wr >= 50%` (literal task spec), **stratwr** = `strat_fwd_wr >= 50%` (how the live dashboard filters and how Gemini computed its numbers).

## Comparison Table

All % numbers show win-rate; PF = profit factor; ΣPnL = summed pnl_pct.

### This week (0–7d), 2384 closed picks in window

| Picker | n | WR | mean PnL% | ΣPnL% | PF | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Smart Picks | 129 | 49.6% | +0.00 | +0.01 | 1.11 | 0.02 |
| Verified Alpha (PROVEN) | 498 | 14.5% | -0.90 | -446.71 | 0.17 | -0.80 |
| Track% — pick `forward_wr ≥ 50` | 622 | 42.8% | -1.05 | -650.41 | 0.67 | -0.12 |
| Track% — strat `strat_fwd_wr ≥ 50` | 524 | **52.3%** | +0.31 | **+163.18** | **1.96** | 0.15 |

### Last week (7–14d), 175 closed in window

| Picker | n | WR | mean PnL% | ΣPnL% | PF | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Smart Picks | 17 | 70.6% | -0.06 | -1.02 | 0.69 | -0.08 |
| Verified Alpha | 0 | — | — | — | — | — |
| Track% — pickwr | 38 | 73.7% | +1.61 | +61.06 | 3.65 | 0.40 |
| Track% — stratwr | 74 | 64.9% | +0.85 | +62.85 | **3.92** | 0.29 |

### This month (0–30d), 3086 closed in window

| Picker | n | WR | mean PnL% | ΣPnL% | PF | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Smart Picks | 153 | 54.2% | +0.22 | +33.83 | **11.04** | 0.21 |
| Verified Alpha | 498 | 14.5% | -0.90 | -446.71 | 0.17 | -0.80 |
| Track% — pickwr | 723 | 45.9% | -0.74 | -532.59 | 0.75 | -0.09 |
| Track% — stratwr | 941 | 52.5% | +0.33 | +307.90 | 2.12 | 0.16 |

### Last month (30–60d), 227 closed in window

| Picker | n | WR | mean PnL% | ΣPnL% | PF | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Smart Picks | 0 | — | — | — | — | — |
| Verified Alpha | 0 | — | — | — | — | — |
| Track% — pickwr | 81 | 53.1% | +0.18 | +14.95 | 1.15 | 0.05 |
| Track% — stratwr | 83 | 57.8% | +0.10 | +8.67 | 1.10 | 0.03 |

## Reconciliation vs Gemini

| Claim | Gemini | Mine (`strat_fwd_wr`) | Mine (`forward_wr`) | Match |
|---|---|---|---|---|
| This Week Track% WR / PF | 54.2% / 1.99 | **52.3% / 1.96** | 42.8% / 0.67 | ✅ stratwr |
| This Week Track% ΣPnL | +16264% | +163.18 (×100 scale diff) | -650.41 | ✅ stratwr, Gemini appears to report basis-points |
| Last Week Track% WR / PF | 64.9% / 3.92 | **64.9% / 3.92** | 73.7% / 3.65 | ✅ exact stratwr |
| This Month Track% WR / PF | 54.0% / 2.13 | **52.5% / 2.12** | 45.9% / 0.75 | ✅ stratwr |
| This Month Smart PF | 3.01 | **11.04** | — | ⚠ discrepancy (see below) |
| This Week Smart PF | 0.62 | 1.11 | — | ⚠ discrepancy |
| Verified Alpha PF (week / month) | 0.63 / 0.70 | 0.17 / 0.17 | — | ⚠ much worse than Gemini reported |
| Missing Track% | 11/3529 (cold-start) | **1/3313** (`hyperopt_bollinger_mr`) | 0/3313 | ⚠ Gemini overstated |

**Key reconciliation finding:** Gemini's Track% uses strategy-level `strat_fwd_wr`, not the pick-level `forward_wr` the task spec named. On that definition all three Track% numbers match Gemini to within 2pp/0.03 PF. The "16264%" is basis-points scaling of +163.18% cumulative.

**Smart / Verified disagreement:** Gemini's Smart PF figures are quite different from mine. Possible causes: (a) Gemini may have applied `passes_smart_gate` without neutralizing status (which rejects all closed picks → n=0, undefined PF), or used a score/trust heuristic rather than the live gate; (b) the PROVEN trust tier is extremely narrow in the closed set — the 498 PROVEN picks are all within 7 days, overwhelmingly losing (14.5% WR), suggesting a recent registry assignment backfilled onto already-losing trades (a tagging regression worth investigating separately).

## Bug Report — Track% field hygiene

1. **Strategies with > 20 picks but 0 populated `strat_fwd_wr`:** none. Every strategy with meaningful sample has strategy-level forward WR populated.
2. **Inconsistent (strategy, symbol) population:** 0 cases with n≥5 where some symbols have strat_fwd_wr set and others do not. Population is strategy-wide, not symbol-wide — by design.
3. **Artificially clamped values (n>10, >80% at 0.0 or 1.0):** none detected. 76 picks (across 35 strategies, mostly n=1–6 each) have `forward_wr == 0.0`; all appear to be legitimate cold-start strategies with no winning forward trades yet.
4. **`forward_wr` vs `forward_win_rate` disagreement:** `forward_win_rate` is never populated (0 picks), so no field-level disagreement exists. However, **pick-level `forward_wr` vs strategy-level `strat_fwd_wr` diverges by >10pp in 386 picks**. Examples:
   - `drawdown_recovery_rsi_sol` SOLUSDT: forward_wr=64.3%, strat_fwd_wr=30.0%
   - `drawdown_recovery_rsi_eth` ETHUSDT: 72.9% vs 45.5%
   - `copy_hl_lb_None` across DYDX/APE/OP/ARB/INJ/SUI: 60.7% vs 34.3%

   This is expected (symbol-within-strategy specialization) but it explains why the two Track% definitions give such different results: `forward_wr` favors single-symbol hot streaks that don't generalize, while `strat_fwd_wr` filters the whole strategy.
5. **Missing `strat_fwd_wr`:** 1 pick (`hyperopt_bollinger_mr`). Gemini's "11/3529" count appears to have inflated the problem; the live picture is far cleaner. Their "all cold-start strategies (tsmom_volscaled, kalshi_mtf_consensus)" claim does not match the current snapshot at all.

## Verdict

**Gemini's Track% claim is materially correct when read through the dashboard's actual filter (`strat_fwd_wr ≥ 50%`).** Within this week (n=524), Track%-stratwr beats Smart Picks on all of n, ΣPnL, and WR — but Smart Picks edges it on PF at longer windows (30d PF 11.04 vs Track% 2.12, though Smart's n is only 153 vs 941). The leadership is real-but-narrow: Track% is a higher-coverage heuristic that captures much of Smart's alpha with 4× the volume.

**However**, the task's literal Track% definition (`forward_wr ≥ 50%`) produces the opposite verdict — pickwr Track% is negative-PF this week and this month. Readers should be explicit about which field they mean; the 386 picks with >10pp divergence between the two show this is not academic.

**Verified Alpha** is the clear loser: 498 PROVEN picks this month with WR 14.5%, PF 0.17, ΣPnL -447%. This looks like a trust-tier tagging regression rather than strategy underperformance and merits a separate investigation (check when `at_issue_trust_tier == 'PROVEN'` was assigned and whether it was computed at-issue or backfilled).
