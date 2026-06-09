# Registry Block Verification — 2026-06-09 (GROUND TRUTH)

**Purpose:** stop the multi-agent oscillation on which emitters to block. During the
money-ready-bridge sweep, three different number sources disagreed for the same emitter
(`pf_registry` policy-clean slice, a fabricated subagent stat, and direct SQL). This file
records the **authoritative source = a direct, class-scoped query against live `trading_picks`**
(not pf_registry, not a subagent claim, not the intrabar ledger — those are derived/sampled views).

Query shape (resolved cohort, pnl-based):
```
status IN ('TP_HIT','SL_HIT','LOST','WIN','WON','LOSS','TIME_EXIT') AND pnl_pct IS NOT NULL
WR = wins/n ; PF = sum(+pnl)/abs(sum(-pnl)) ; class-scoped on category
```

## Verdicts

| Emitter | Class | n | WR | PF | cum PnL | Verdict | Action |
|---|---|---|---|---|---|---|---|
| `copy_trader_intel` | CRYPTO | 248 | 38.3% | **0.37** | strongly − (avg −2.25%/trade) | **REAL LOSER** | **BLOCK** (re-blocked) |
| `cftc_socrata` | COMMODITY | 26 | 26.9% | 4.22 | **+9.14%** | net-positive (outlier-dependent, low WR) | **DO NOT BLOCK** — only positive COMMODITY source; monitor fragility |
| `copy_trader_bybit` | CRYPTO | 17 | 23.5% | 2.24 | +0.90% | marginal/break-even | leave blocked (conservative; re-evaluate at n≥30) |
| `approach_b_ml_breakout` | CRYPTO | 0 live | — | — | — | unverifiable (no live resolved rows) | leave blocked (harmless no-op) |
| `cta_replicator` | EQUITY | 0 live | — | — | — | unverifiable | leave blocked (harmless) |
| `etf_all_strategies` | ETF | 0 live | — | — | — | unverifiable | leave blocked (harmless) |
| `etf_scanner` | ETF | 0 live | — | — | — | unverifiable | leave blocked (harmless) |
| `multi_asset_scanner` | FOREX | 0 live | — | — | — | already banned upstream | leave blocked (harmless) |

## Key corrections to the record
- **`copy_trader_intel` is NOT 34.5% WR / PF 2.12.** That figure was a **fabricated subagent
  recompute**. Direct SQL = 38.3% WR / **PF 0.37** / −2.25% avg per trade. A 38% WR with PF 0.37
  means the few wins are tiny and the many losses are large → unprofitable. The 2026-05-18
  investigation (`docs/STRATEGY_INVESTIGATION_copy_trader_intel_CRYPTO_2026-05-18.md`) was correct.
- **`cftc_socrata` is NOT 0% WR / PF 0.0** (the stated block reason). Direct SQL = 26.9% WR /
  PF 4.22 / **+9.14% cumulative**. Low WR + outlier-driven PF, but net-positive — it is COMMODITY's
  only positive contributor; blocking it removes the class's positive segment. Kept unblocked.

## Provenance discipline (why this file exists)
- `pf_registry` policy-clean numbers are a **filtered/sampled slice** (small-n per strategy) and
  diverge materially from the full resolved cohort. Do not block on them alone.
- Subagent-reported quantitative stats have a known fabrication rate
  (`feedback-subagent-stat-fabrication-2026-06-05`). **Always re-verify n/WR/PF/avg with a direct
  class-scoped `trading_picks` query before blocking or unblocking.**
- The intrabar ledger (`at_signal_outcomes.intrabar_*`) is the honest *outcome-resolution* view for
  WR/PF on first-touch; it is the right source for the money-ready VERDICT, but the block/keep
  decision above is made on the full resolved cohort (broadest evidence).

## New emitters guarded this session (emit-but-don't-size)
- `alpha_engine/etf_vix_regime_rotation.py` — emits `forward_test_only=True` / `forward_validated=False`.
  PF=4.50/WR=80.8% is a backtest claim; build forward n, never size until intrabar-true n≥30.
- `alpha_engine/run_atr_gate.py` — emits `forward_test_only=True`. `atr_percentile_gate` has n=2 live /
  0 intrabar; correctly NOT in `CRYPTO_PROVEN_STRATEGIES`.

## futures_momentum (open re-audit, NOT actioned)
Intrabar-true COMMODITY `futures_momentum` = n=57, WR 50.9%, PF 2.68 — contradicts the 2026-05-06
FUTURES kill (0% WR on 56 closed). Different asset_class scoping. **Do NOT un-ban unilaterally**
(H-005 re-block history exists). Forward-track only; queue for the strategy-decision swarm.
