# CRYPTO Edge Hunt v2 — Fast Real-Money Paths (Beyond Forward Wait)

**Date:** 2026-06-06  
**Prior:** `reports/edge_hunt_CRYPTO_2026-06-05.md`  
**Sources (no fabricated stats):** Live MySQL `ejaguiar1_stocks` (`at_pick_outcomes`, `trading_picks`), `audit_dashboard/data/money_ready_verdict.json` (2026-06-05T14:09Z), `audit_dashboard/data/pf_registry.json` (2026-06-05T13:54Z), `strategy_health/data/banned_strategies.json`, `audit_trail/quality_gates.py` (`BLOCKED_SOURCE_SYSTEMS`), `alpha_engine/data/strategy_performance.json`, `alpha_engine/data/funding_rate_picks.json`, paper-pilot state JSONs.

## Executive: Class Still NOT_READY — 2 Unblocked Sleeves + 1 Override

`money_ready_verdict.json` CRYPTO: **n=220, WR=47.3%, PF=0.99 → NOT_READY** (DSR/SPA/FDR/single-source fail). Only policy-clean `top_sleeves` entry: `crypto_liquidity_wick_reversal_v1` (n=30, WR=60%, PF=1.55) — but that strategy is **banned** in `banned_strategies.json`.

**48h recency stall:** `pick_summary_stats_48h.json` CRYPTO **0 closed / 137 active** — do not size up on any sleeve until resolver catches up.

**M-105 ml_enhanced quarantine:** `_ml_enhanced_quarantine_enabled=false`, `_ml_enhanced_quarantine_n=0` in current verdict (shadow stamp only). Per-variant surgical blocks remain in `quality_gates.py`; family-wide enforce needs `ML_ENHANCED_CRYPTO_QUARANTINE=1`.

---

## Cross-Check: T2+ Resolver Sleeves vs Blocklists

| Strategy | universal_v2 (`at_pick_outcomes`) | `trading_picks` (raw) | pf_registry policy_clean | Blocked? |
|---|---|---|---|---|
| `hs_lb_None` | n=261, WR=56.7%, PF=3.26 | (not in `trading_picks` top query) | — | **YES** — `BLOCKED_SOURCE_SYSTEMS` `("hs_lb_None", None)` — alpha_engine replay WR=4.1% on n=74 |
| `battleground_ml_relaxed_mut` | n=31, WR=71.0%, PF=4.35 | n=31, WR=54.8%, PF=1.31† | — | **NO** — not in banned/blocklist; `last_seen` 2026-06-05 |
| `luxalgo_confluence` | n=67, WR=83.6%, PF=7.81 | n=2143, WR=43.2%, PF=1.09 | — | Incubator only; live ledger contradicts resolver sleeve |
| `claude_ml_moderate_mut` | n=31, WR=61.3%, PF=2.74 | n=31, WR=54.8%, PF=1.31 | — | Incubator; not banned |
| `crypto_liquidity_wick_reversal_v1` | — | — | n=30, WR=60%, PF=1.55 | **BANNED** `banned_strategies.json` + incubator duplicate entry |
| `mega_mutation` | — | n=296, WR=63.9%, PF=3.12 | policy_excluded n=1 | Paper pilot; `production_enable=false` |
| `prediction_market_consensus` | n=14, WR=50%, PF=1.67 | n=127, WR=84.3%, PF=24.24 | — | **BANNED + BLOCKED** — artifact (see below) |
| `ml_enhanced_*` | per-variant backfill cells only | family aggregate | — | M-105 shadow quarantine; 8+ per-variant CRYPTO blocks |

†`trading_picks` vs `at_pick_outcomes` divergence on `battleground_ml_relaxed_mut` — trust **universal_v2** for sleeve metrics; raw `trading_picks` includes pre-resolver / mixed-status rows.

### prediction_market_consensus — Artifact Confirmed (not n=2359 edge)

| resolver_version | n | WR% | PF |
|---|---:|---:|---:|
| `backfill_updated_202` | 2249 | **0.0** | — |
| `backfill_2026-06-01` | 96 | 83.3 | 24.51 |
| `universal_v2` | 14 | 50.0 | 1.67 |

`trading_picks` headline (n=127, WR=84.3%, PF=24.24) is **corruption/backfill-inflated**, not a tradeable edge. Retired in `BLOCKED_SOURCE_SYSTEMS` + `banned_strategies.json`. `pick_quality_pulse_latest.json` still shows an active DOGEUSDT SHORT — treat as stale emission to kill, not a sizing candidate.

### ml_enhanced_* — Quarantined Family, Not a Fast-Money Sleeve

- Verdict shadow: quarantine **recommended** when enabled (would drop CRYPTO to ~10 non-ml picks).
- `inverse_ml_enhanced_BTCUSDT_15m_D` paper pilot: n_closed=4, WR=75%, PF=1.845 — **too early** for real money; `inverse_ml_enhanced_RENDERUSDT_{1h,4h}_D` explicitly **banned**.

---

## Ranked Top 5 REAL-MONEY Candidates (Production / Manual, Not Research-Only)

| Rank | Strategy | Evidence | 0.25× This Week? | Gate / Blocker |
|---:|---|---|---|---|
| **1** | `battleground_ml_relaxed_mut` | universal_v2 n=31 WR=71% PF=4.35; 12 symbols; `strategy_performance.json` PF=4.35, `last_seen` 2026-06-05 | **YES** — clearest unblocked T2+ sleeve | Class NOT_READY caps all size; 48h resolver stall; no SPA/FDR pass |
| **2** | `battleground_luxalgo` | pf_registry policy_clean n=26 WR=50% PF=3.98 (T3 WR / T2 PF) | **YES** — micro only | Single-source (`file:battleground`); WR at tier floor; 14d closes unverified |
| **3** | `crypto_liquidity_wick_reversal_v1` | money_ready `top_sleeves` + pf_registry n=30 WR=60% PF=1.55 | **CONDITIONAL** — needs ban lift or manual mirror | **Banned** in `banned_strategies.json`; single-source artifact; SPA/DSR fail |
| **4** | `inverse_ml_enhanced_BTCUSDT_15m_D` | Paper pilot n=4 WR=75% PF=1.845; active in `pick_quality_pulse` | **PAPER ONLY** — mirror at 0.25× after n≥30 forward | `production_enable=false`; ml family quarantine risk; n≪100 |
| **5** | `mega_mutation` | Lab dedup n=109 WR=61.5% PF=2.79; `mega_mutation_state.json` day_count=24 | **PAPER ONLY** until ~2026-06-12 | `production_enable=false`; blockers day_count<30, n<30 forward; policy_excluded in registry |

**Disqualified for real-money (research / kill):**

- `hs_lb_None` — PF=3.26 sleeve is **feed-blocked** despite universal_v2 stats.
- `prediction_market_consensus` — resolver artifact; banned.
- `luxalgo_confluence` — resolver sleeve strong; **live** trading_picks PF=1.09 → do not size on historical universal_v2 alone.
- `funding_rate_arb` — sidecar picks only (`funding_rate_picks.json`: 10 OPEN, `forward_trades=0`, `forward_validated=false`); H-006 harness **REJECTED**.
- `crypto_verified_bollinger_mr` / `crypto_verified_vwap` — WF OOS PASS but **0 forward closes** (`crypto_wf_forward_stats_latest.json`).

---

## Fast-Money Playbook (This Week, 0.25× Normal)

1. **Primary live sleeve:** Route new CRYPTO size through **`battleground_ml_relaxed_mut`** signals only (0.25×). Kill if next 10 closes WR<45% or PF<1.0.
2. **Secondary:** **`battleground_luxalgo`** at 0.25× only when battleground file emits; do not stack correlated battleground sleeves on same symbol.
3. **Operator override path:** **`crypto_liquidity_wick_reversal_v1`** — historically the only `money_ready` top_sleeve, but **banned**; manual TV mirror acceptable at 0.25× only if operator explicitly lifts ban for this sleeve.
4. **Paper track (no real $ until gates clear):** `inverse_ml_enhanced_BTCUSDT_15m_D`, `mega_mutation` — continue paper pilots; earliest real-money unlock ~2026-06-12 if forward n≥30 + PF holds.
5. **Hard skip:** Class-wide Smart Picks, `prediction_market_consensus`, `hs_lb_None`, `ml_enhanced_*` blanket, funding-rate directional until H-006 re-pass + prod wire-up.

**Kill switches (unchanged from v1):** class PF<1 on verdict refresh; 48h CRYPTO 0 closes >72h; any sleeve single-source >60%; `mega_mutation` forward PF drift >30% from lab 2.79.

---

## Overlay Modules — Analyst / Onchain / Fundamental (CRYPTO)

| Overlay | Prod wired? | Real data status | Use for sizing |
|---|---|---|---|
| **Onchain** (`get_onchain_features` → `production_scanner.py`) | Partial enrichment | Backtest WARN: n=167 PF=1.28 (`reports/backtest_crypto_onchain_2026_05_12_0616Z.md`) | **Confirm only** — boost conviction when MVRV-Z / active-addr align with sleeve direction; not standalone edge |
| **Funding** (`funding_rate_arb` / `_fetch_negative_funding_rates`) | Enrichment + sidecar JSON | `funding_rate_picks.json` 2026-06-05: 10 picks, all OPEN, 0 forward closes; H-006 REJECTED | **Do not size** — use funding z-score as veto (fade crowded side) on ranks 1–2 only |
| **Fundamental / macro** (`fundamental_macro_gates.py` → `money_ready_verdict.py`) | Wired (new) | Crypto: `btc_power_law_deviation`, `nvm_metcalfe_valuation`, `eth_gas_fee_reversal` scoring; equity analyst path not applicable to CRYPTO | **Tag/boost** high-conviction picks passing macro regime alignment; `messari_fundamental_quality` still incubator |
| **Prediction markets** (`prediction_market_consensus`) | Emitter exists | Banned + artifact | **Veto only** — do not use PM consensus as directional overlay until resolver clean + unban |

**Practical overlay stack for ranks 1–2:** battleground signal → onchain feature agree (if present) → funding not extreme against direction → macro gate not `strong_bear` for longs.

---

## SQL / Queries Used

```sql
-- universal_v2 sleeves (at_pick_outcomes)
SELECT strategy, COUNT(*) n, <wr>, <pf>
FROM at_pick_outcomes
WHERE asset_class IN ('CRYPTO','crypto') AND resolver_version='universal_v2'
  AND strategy IN ('hs_lb_None','battleground_ml_relaxed_mut', ...)
GROUP BY strategy HAVING n >= 5;

-- prediction_market_consensus by resolver_version (artifact triage)
SELECT resolver_version, COUNT(*) n, <wr>, <pf>
FROM at_pick_outcomes
WHERE strategy='prediction_market_consensus' AND asset_class IN ('CRYPTO','crypto')
GROUP BY resolver_version;
```

---

*Generated 2026-06-06. No dashboard generators run. All figures traced to files/queries above.*
