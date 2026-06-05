# COMMODITY/FUTURES Edge Hunt — 2026-06-05

**Goal #1 audit.** Sources: `pf_registry.json` (2026-06-05T13:54Z), `money_ready_verdict.json`, `edge_stability_COMMODITY.json`, `commodity_term_cot_signals.json`, `cot_paper_pilot_status.json`, `reports/deep_dive_commodity_2026-06-05.md`, `reports/commodity_tsmom_backtest_2026-06-03.md`.

**Verdict: NO real-money statistical edge.** Class = `INSUFFICIENT_DATA` / `FAIL+INSUFF-N`. Do not size up.

---

## 1. pf_registry — policy-clean cohort (canonical)

| Slice | n | WR | PF | Tier |
|---|---:|---:|---:|---|
| `by_asset_class_policy_clean_net` | 6 | 50.0% | 3.06 | INSUFF_N |
| `money_ready_verdict` | 7 | 42.9% | 1.74 | INSUFFICIENT_DATA |
| Raw `by_asset_class` (undeduped) | 83 | 7.2% | 0.43 | FAIL |

All five policy-clean strategies are `INSUFF_N` (n=1–2): `commodity_tsmom_12m` (0W/2L, PF=0), `cta_golden_cross` (1W/0L), `feature_signals` (0W/1L, NG=F), `multi_asset_copytrader`, `regime_terminal`. DSR/PBO/SPA all null — "n too small" / "need ≥2 strategies with n≥20, got 0".

**Do not cite** policy-clean PF 3.06 as edge; n=6 is below min n=30 and n=100 forward gates.

---

## 2. CT=F concentration + falsified DSR

- Pre-2026-05-18: COMMODITY emissions were **73–76% CT=F** (`cot_positioning`), creating phantom WR (`updates/2026-05-18-commodity-ctf-concentration-cap.md`). `enforce_commodity_ctf_emission_cap()` now caps CT=F at ≤40%/scan.
- **Falsified headline:** Ring/cot_positioning claimed **DSR=1.0 / TIER_1_RENAISSANCE** (n=104). Deduped to **7.33× over-emission** of 6 unique CFTC releases → n=5–6, WR 33–40%, cum PnL negative (`cot_paper_pilot_status.json`, `reports/cot_paper_pilot_overemission_falsified_20260513.md`). DSR now **withheld** (`dsr: null`).
- `multi_asset_cot::CT` policy-clean: n=2, 0W/2L, PF=0. Memory entries citing "CT=F PROBATION WR 81%" are **stale** — disregard.

---

## 3. Strategy sleeves (live + backtest)

| Strategy | Forward n | Backtest | Status |
|---|---:|---|---|
| `commodity_tsmom_12m` | 2 (0W/2L) | REJECTED: PF 1.69, Sharpe 0.67, MDD −33.8%, alpha t=0.84 vs DBC | Banned (`banned_strategies.json`) |
| `cta_golden_cross` | 1 (COMMODITY; symbol SPY) | — | INSUFF_N; misclassified equity pick |
| `feature_signals` | 1 (NG=F loss) | — | `commodity_momentum` (CL/NG 20d) wired; `commodity_term_cot` opt-in only (`FACTOR_EMITTERS_ENABLED=1`) |
| `commodity_term_cot` | 0 closed | Sidecar | 3 picks 2026-06-05 (HG=F, ZW=F, ZC=F); `production_enable: false` |

No other commodity backtests in `verified_strategies/` (no `bt_backtest_trades` commodity sleeve found).

---

## 4. COT + term structure integration

`tools/feature_signals/commodity_term_cot.py`: Erb-Harvey roll yield (1M vs 6M) + Sanders COT contrarian, 50/50 composite. Honest nulls when 6M leg missing. Latest run: 8/8 symbols have term+COT; 3 picks above 75th percentile. **Not production-wired** — requires DSR/PBO/WFE pass + operator review.

---

## 5. Contamination warning (2026-06-04 backfill)

`deep_dive_commodity_2026-06-05.md`: **5,960 commodity closes on 2026-06-04 = 97%** of class history (resolver backfill). Walk-forward PASS cells (`futures_bb_mean_reversion`, `combined_confidence`) and scrutiny "T2-shaped" candidates are **batch artifacts**. Filter `closed_at != '2026-06-04'` before any re-evaluation.

`edge_stability_COMMODITY.json` 90d (includes backfill): WR 37.2%, PF 0.69, n=792 — sub-random after noise.

---

## Action plan (ranked)

1. **Hold sizing at zero** until forward n≥100 per sleeve with clean (post-backfill) data.
2. **Accumulate paper pilot** on `commodity_term_cot` (3 live picks) + deduped COT one-trade-per-release ledger.
3. **Re-run commodity_tsmom** only if params change; current gate-stack rejection is definitive.
4. **Exclude 2026-06-04** from all scrutiny/walk-forward SQL before next tier review.
5. **External benchmark** (post n≥100): DBC, KMLM, DBMF — not meaningful today.

**Reproduce:** `python3 tools/strategy_tier_tracker.py` · `python3 verified_strategies/commodity_tsmom_backtest.py` · `python3 -m tools.feature_signals.commodity_term_cot`
