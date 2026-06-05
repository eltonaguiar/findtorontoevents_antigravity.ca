# Real-Money Edge Hunt — All Asset Classes (2026-06-05)

**Mission:** Find defensible statistical edge per class **without waiting months** for forward n→100. Six parallel subagents + live DB verification.

**Honest headline:** **0/6 classes are MONEY_READY.** Closest tradeable sleeves exist in CRYPTO + EQUITY (resolver/outcomes tables), with lab/backtest shortcuts for ETF/FOREX/BOND.

**Sources:** `pf_registry.json` (2026-06-05T13:54Z), `money_ready_verdict.json`, live MySQL `at_pick_outcomes` / `trading_picks`, per-class reports in `reports/edge_hunt_*_2026-06-05.md`.

---

## Class scoreboard

| Class | Verdict | Best forward sleeve | n | WR | PF | Fast-path source | Size this week |
|-------|---------|---------------------|---:|---:|---:|------------------|----------------|
| **CRYPTO** | NOT_READY | `crypto_liquidity_wick_reversal_v1` | 30 | 60% | 1.55 | forward policy_clean | **0.25× micro** |
| **EQUITY** | INSUFF_DATA | `MeanReversionBB` | **214** | **55.6%** | **1.88** | `at_pick_outcomes` | **0.25× paper book** |
| **ETF** | INSUFF_DATA | `etf_verified_dual_momentum` | 0 fwd | — | 2.75 OOS | backtest+paper pilot | **0% live** |
| **FOREX** | FROZEN | `forex_carry_g10` | 13 bt | 69% | 2.11 | backtest | **0%** (HARD_DISABLE) |
| **COMMODITY** | INSUFF_DATA | — | 6 | — | — | term_cot sidecar | **0%** |
| **BOND** | INSUFF_DATA | `bond_tlt_ief_v3` (orphan bt) | 6 live | 33% | 3.16* | orphan backtest | **0%** |

\*BOND live PF is single-source artifact (100% `bond_scanner`); do not trust until n≥100.

---

## Per-class actions (this week)

### CRYPTO — BEST_CANDIDATE (class still fails gates)

- **Trade:** `crypto_liquidity_wick_reversal_v1` only — T2 on policy_clean (n=30, PF=1.55). Single-source flag; 0 closes in 14d panel.
- **Paper:** `mega_mutation` — DB n=296 WR=63.9% PF=3.12 pre-dedup; dedup ~109 PF=2.79. **BLOCKED** until ~2026-06-12 (swarm HOLD).
- **Skip:** class-wide Smart Picks (policy_clean n=301 PF=0.99 WR=34.6%), `battleground_luxalgo` (single-src PF inflation), tournament `llm7_qwen` (n=16).
- **Wire later:** funding_rate_arb (H-006 REJECTED), onchain enrichment only.

### EQUITY — NO_EDGE_YET (hidden sleeve found)

- **Class poison:** `regime_terminal` n=17 WR=17.6% PF=0.19 — **block emissions**.
- **Best stats (verified SQL):** `MeanReversionBB` in `at_pick_outcomes`: **n=214, WR=55.6%, PF=1.88** — clears T2 on n alone; not dominant in policy_clean pf_registry because class is diluted by regime_terminal.
- **Earnings / PEAD:** `data/earnings/{AAPL,MSFT,GOOGL,XYZ}/latest.json` real; last beats Apr 2026 — **no fresh 3-day entry window** until July earnings. PEAD shadow via `equity_pead_strategy.py` (H-010 REJECTED on 30d hold).
- **UEPS / value:** `ueps_picks.json` — quality overlay; today's value_screener scored n=1 → 0 picks.
- **Killed:** `yahoo_analyst_consensus` (0% WR), `stocks_rsi2_pullback` (banned; disputed n=5 vs n=1221 outcomes).

**Week 1 playbook:** MeanReversionBB-only paper book + block regime_terminal EQUITY.

### ETF — NO_EDGE live; BEST_CANDIDATE lab

- Live class PF=0.80 on n=11 (`cta_golden_cross` leak).
- **`etf_verified_dual_momentum`:** backtest PF=3.57 n=48; WF OOS PF=2.75 n=11; paper pilot **0 closed** (XLK open).
- **30d checkpoint:** ~2026-07-02 if monthly rebalance closes fire.
- **Do not** enable scanner flags until forward n≥30 shadow.

### FOREX — FROZEN

- `FOREX_HARD_DISABLE=1`; class n=22 WR=22.7%.
- **`multi_asset_scanner`** n=11 WR=9.1% — dominant leak.
- **Fast path:** extend `forex_carry_g10` backtest to n≥30 → 30d paper → clear hard-disable. Allowlist: `cta_cross_asset_tsmom` (SHORT) + `forex_carry`.
- Tournament WR=57.6% but PF=0.57 — research only.

### COMMODITY — NO_EDGE

- Registry n=6–7; Jun-04 backfill contaminated 90d stats.
- CT=F / DSR Tier-1 claims **falsified** (COT over-emission).
- Paper-only: `commodity_term_cot` (production_enable=false).

### BOND — INSUFF-N

- ~78 `at_raw_picks` accumulating; 14d: 45 closed WR=46.7% PF=1.12.
- Orphan backtests: `bond_tlt_ief_v3` PF=1.29, `bond_hyg_lqd_v1` PF=1.62 — **zero production_scanner callers**.
- Fast path: wire TLT/IEF rotation into `bond_scanner`; enable `bond_duration_momentum` shadow.

---

## Acceleration ladder (skip months of blind forward)

| Tier | Method | Classes | Requirement |
|------|--------|---------|-------------|
| A | **Isolated sleeve paper** | CRYPTO, EQUITY | n≥30 closed, PF≥1.5, no single-src >60% |
| B | **Backtest + paper parity** | ETF, FOREX, BOND | OOS PF≥1.5 + 30d forward PF≥0.85×OOS |
| C | **Fundamental overlay** | EQUITY | UEPS rank + MeanReversionBB timing |
| D | **Earnings catalyst** | EQUITY | PEAD on surprise≥5% within 3d of report |

**Do not** promote from tournament-only or pf_registry n<30 no-loss sleeves.

---

## Reproduce

```bash
PYTHONPATH=. python3 alpha_engine/money_ready_verdict.py --json
python3 tools/strategy_tier_tracker.py --min-n 15
python3 tools/money_ready_snapshot.py
```

Per-class deep dives: `reports/edge_hunt_{CRYPTO,EQUITY,ETF,FOREX,COMMODITY,BOND}_2026-06-05.md`

---

*Generated 2026-06-05 after 6 parallel edge-hunt subagents + live DB cross-check (mega_mutation n=296; MeanReversionBB n=214).*
