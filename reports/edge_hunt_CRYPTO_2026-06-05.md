# CRYPTO Edge Hunt — 2026-06-05

**Sources:** `pf_registry.json` (2026-06-05T13:54Z), `money_ready_verdict.json`, `strategy_tier_tracker_20260605T141049Z.md`, MySQL `ejaguiar1_stocks` via `get_stocks_creds()`, `pick_summary_stats_{14d,48h}.json`, `crypto_wf_forward_stats_latest.json`, `mega_mutation_state.json`.

## Executive Verdict: **BEST_CANDIDATE** (micro-size only; class NOT_READY)

CRYPTO is **NOT_READY** at class level (`money_ready_verdict.json`: n=220, WR=47.3%, PF=0.99, DSR/SPA/FDR fail). One policy-clean T2 sleeve exists; strongest lab edge (`mega_mutation`) is paper-pilot only until ~2026-06-12.

## Top 3 Candidates

| Strategy | n | WR | PF | Source | Single-src? | Scrutiny |
|---|---:|---:|---:|---|---|---|
| `crypto_liquidity_wick_reversal_v1` | 30 | 60% | 1.55 | forward (`pf_registry` policy_clean_net) | **Yes** (`file:battleground`) | T2 metrics ✅; SPA/DSR/single-src ❌; **14d closes=0** (SQL `trading_picks`) |
| `mega_mutation` | 109† | 61.5% | 2.79 | lab forward (`trading_picks` dedup SQL) | No (8 syms, 39 dates) | T2 lab ✅; **policy_excluded** (pf_registry n=1); forward pilot n=0 since 2026-06-05; HOLD unblock |
| `battleground_luxalgo` | 26 | 50% | 3.98 | forward | **Yes** (`battleground_luxalgo`) | PF ✅ WR=T3 only; single-src artifact; 14d=0 |

†Dedup SQL (incident #91 key): `source_system='mega_mutation'` → n=113 WR=62.8% PF=2.8; empty-`strategy` mutation rows n=109 WR=61.5% PF=2.79. Raw 296 rows pre-dedup.

**Not promoted:** Tournament `llm7_qwen` WIN=8/LOSS=2 (n=16) — artifact risk, no PF from `pnl_pct`. `gh_models_gpt4o` n=12 WR=67% — insufficient n.

## Fast-Money Path (This Week)

1. **Trade:** `crypto_liquidity_wick_reversal_v1` only — **0.25× normal size** (T2 sleeve, `money_ready_verdict.json` top_sleeves). BTCUSDT-heavy (31% class concentration).
2. **Paper-only:** `mega_mutation` via `mega_mutation_forward_pilot.py` — lab n=109 passes T2; `production_enable=false`, blockers: day_count<30, n<30 forward.
3. **Backtest+paper hybrid:** `crypto_verified_bollinger_mr` WF OOS PF=1.67 n=38 (`crypto_wf_forward_stats_latest.json`) — **0 forward closes**; do not enable prod flags yet.
4. **Skip:** Class-wide Smart Picks (policy_clean CRYPTO n=301 PF=1.00 WR=34.6% per tier tracker).

## Data Sources to Wire

| Module | Prod wired? | Notes |
|---|---|---|
| `funding_rate_arb` | **No** pick emitter in `production_scanner.py` (only `_fetch_negative_funding_rates` enrichment). H-006 harness **REJECTED** (`reports/h006_crypto_funding_rate_2026-05-18.md`). Sidecar: `crypto_funding_carry_winner.py`. |
| Onchain (`get_onchain_features`) | **Partial** — feature enrichment in `production_scanner.py:4781`; backtest PF=1.28 n=167 WARN (`reports/backtest_crypto_onchain_2026_05_12_0616Z.md`). |
| `copy_trader_intel` | **FOREX only** — reads `forex_copytrader_picks.json`; CRYPTO `copy_trader_intel` forward n=32 WR=0% PF=0 (tier tracker). |

## Kill Switches

- Class PF<1 or WR<50% on next `money_ready_verdict` refresh.
- `pick_summary_stats_48h.json`: CRYPTO **0 closed / 137 active** — halt size-up if resolver stall >72h.
- `pick_summary_stats_14d.json`: raw CRYPTO WR=40% PF=6.5 with **dup_groups=277** — ignore raw funnel; trust policy_clean_net only.
- Any sleeve: single-source share >60% or 14d WR collapse >15pp vs registry.
- `mega_mutation`: forward PF drift >30% from lab 2.79, or re-inflation dup factor >1.5×.
- Backtests DB unreachable locally (1045 auth) — no backtest-confirmed prod enable without re-verify.

---
*Generated 2026-06-05. Queries: `trading_picks` dedup CTE + `tournament_picks` status counts. No dashboard generators run.*
