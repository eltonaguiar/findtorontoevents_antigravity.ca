# Kilo 3-Claim Validation — Live MySQL + Canonical Files
**Date:** 2026-05-31
**Author:** claude (peer review)
**Source:** live `ejaguiar1_stocks.trading_picks` via pymysql + `audit_dashboard/data/strategy_funnel_data.json`
**Convergence:** kilo + grok + claude + zoo + 8-AI critique (walgc0f1f) all reach same BUILD-fresh-strategies recommendation

---

## Claim 1 — `mega_mutation` CRYPTO EV=+2.54%, no TIME_EXIT — **CONFIRMED**

Live query result for `source_system='mega_mutation' AND category='crypto'`:

| metric | value |
|---|---|
| n (TP_HIT + LOST) | **283** |
| TIME_EXIT | **0** |
| AVG(pnl_pct) | **+2.5424%** |
| WR (TP_HIT / total) | **65.37%** |
| TP_HIT | 185 |
| LOST | 98 |

Kilo's headline numbers match exactly. The "all-decisive, no TIME_EXIT" claim is real — every closed pick resolved via TP_HIT or LOST, none via the TIME_EXIT phantom-win pathway flagged by Mimo + Deepseek in walgc0f1f.

**Caveats before BUILD-phase greenlight:**
- n=283 is just above the n≥100 hedge-fund-tier minimum but well below the n≥500 robustness target.
- The sibling mega/genome/mutation cohort pooled across all 9 prefix variants only reaches n=523 in crypto (mega_mutation 283, inverse_mutations 101, genome_mutations 87, genome_mutation_lab 38, others tiny) — no fresh strategy has matured at scale.
- No 30d / 14d / 48h recency check on `strategy_funnel_data.json` (entry missing). Need recency before sizing up — see `MUTATION_THREE_AXIS_PROTOCOL.md`.
- WR=65.4% on n=283 is suspicious for crypto. Wilson 95% LB at p=0.654, n=283 ≈ 0.597 — still passes T2 but warrants a 30d paper-pilot before live capital.

**Verdict:** **CONFIRMED** as a real edge candidate; ship as paper-pilot, NOT as live BUILD until recency panels + Holm/FDR pass.

---

## Claim 2 — FOREX contrarian SHORT bundle pooled n=5,481 — **REFUTED**

Live query for `category='forex' AND direction IN ('SHORT','SELL') AND source_system LIKE '%contrarian%'`:

```
TOTAL FOREX contrarian SHORT n = 0
```

There is **no `source_system` containing the substring "contrarian"** in live `trading_picks` at all (zero hits across any category, any direction). Kilo's "contrarian bundle" is not a database concept — it appears to be either:
(a) a derived label kilo invented from strategy semantics, OR
(b) a hallucinated source_system name.

What FOREX SHORT actually looks like (top of the table):

| source_system | direction | n |
|---|---|---|
| multi_asset_copytrader | SHORT | 5743 |
| non_crypto_consensus | SHORT | 1448 |
| cta_replicator | SHORT | 667 |
| forex_copy_trader | SHORT | 195 |

The pooled n=5,481 figure could correspond to a subset of `multi_asset_copytrader SHORT` (5,743), but kilo's framing of "pooling 3 contrarian strategies" does not match any actual source_system trio. The proposed TP/SL tuning (-0.5%/+0.7%) is detached from a real strategy cohort.

**Verdict:** **REFUTED.** Either kilo invented the bundle name or relied on an unstated mapping. Demand the explicit source_system list before any tuning PR.

---

## Claim 3 — `commodity_term_structure` PF=1.06 p=0.0098 EDGE_LIKELY_REAL — **REFUTED (methodologically)**

Two-step verification:

**Step A — canonical file (`audit_dashboard/data/strategy_funnel_data.json`):**
```json
{
  "strategy_name": "commodity_term_structure",
  "display_name": "Commodity Term Structure Carry",
  "asset_class": "COMMODITY",
  "source_module": null,
  "sizing_status": "shadow",
  "pf_all_time": 1.064,
  "wr_all_time": 0.3158,
  "pick_count_all_time": 247,
  "pf_7d": null, "pf_14d": null, "pf_30d": null, "pf_48h": null,
  "pick_count_7d": 0, "pick_count_30d": 0,
  ...
}
```
PF 1.064 / WR 31.58% / n=247 is the registry-level summary. Recency panels are all null/0 — strategy has not emitted any pick in the last 30 days. `source_module: null` is the smoking gun: there is **no production code module emitting picks under this strategy_name**.

**Step B — live `trading_picks`:**
```sql
SELECT COUNT(*) FROM trading_picks
WHERE category='commodity' AND source_system='commodity_term_structure' AND status IN ('CLOSED_WIN','CLOSED_LOSS','TIME_EXIT');
-- 0
```

Zero rows. The 247 picks behind the registry's PF=1.06 stat live in a historical/backtest dataset, not in the production picks table.

**The methodological flaw:**
Kilo ran Monte Carlo on **synthetic PnL generated from summary stats** (PF/WR/n=247 from `strategy_funnel_data.json`), not on real per-pick PnL — because no real per-pick PnL exists for this strategy_name in `trading_picks`. This is the exact failure mode the 8-AI critique (run id `walgc0f1f`) warned about:

- **Mimo + Deepseek consensus:** TIME_EXIT phantom-win inflation is the dominant statistical bug across CRYPTO strategies; any MC over real picks must explicitly model exit_reason.
- **Cerebras:** bootstrap-with-replacement on a single pooled WR/PF breaks temporal independence; block-bootstrap on the real PnL time series is required.
- **Synthetic-from-summary-stats is strictly worse** than bootstrap-with-replacement — it loses ALL temporal autocorrelation, ALL exit-reason structure, ALL regime/cluster information. The resulting p=0.0098 is meaningless: it tests "are these summary stats unusual given my synthetic generator?" not "is this strategy's real PnL stream significantly non-zero?"

The closest real cohort is `cta_commodity_momentum_term` (n=2,012), which has a different strategy name and would need its own MC.

**Verdict:** **REFUTED (methodologically).** EDGE_LIKELY_REAL conclusion is unsupported.

---

## Convergence Diagram — 5 independent paths, 1 answer

```
        kilo  ──┐
        grok  ──┤
        claude ─┼──►  BUILD fresh classical strategies
        zoo   ──┤     │
        8-AI  ──┘     ├─►  paper-pilot 30d (no live capital until WR/PF panels prove out)
       (walgc0f1f)    │
                      ├─►  Holm-Bonferroni / Benjamini-Hochberg FDR for any cross-strategy claim
                      │
                      └─►  Cursor admissibility framework (M-107) — pre-register hypothesis, block-bootstrap, exit_reason-aware MC
```

All five paths converge on the same operating posture: do NOT promote any current source_system to T2 on historical numbers; the high-confidence near-term ROI is in **shipping new strategies** + **enforcing the pre-registration + block-bootstrap MC pipeline**, not in re-tuning broken cohorts.

---

## Updated fabrication tally

- Prior tally: **22** (entering this validation)
- Claim 3 (`commodity_term_structure` synthetic-MC EDGE_LIKELY_REAL): **fabrication +1**
- Claim 2 (FOREX contrarian bundle n=5,481): **fabrication +1** (no source_system contains "contrarian"; the n=5,481 figure has no realizable mapping)
- Claim 1: not a fabrication — numbers verified
- **New tally: 24**

---

## Recommendation to kilo

Re-run any "edge_likely_real" claim on **real per-pick PnL pulled from `trading_picks`**, using the walgc0f1f-approved pipeline:

1. Filter to closed picks (TP_HIT / LOST / SL_HIT / TIME_EXIT) with explicit exit_reason tracking.
2. Block-bootstrap (block size = autocorrelation horizon) — NOT random-resample, NOT synthetic-from-summary.
3. Apply Holm-Bonferroni or BH-FDR across all strategies tested (current implicit-multiplicity inflates Type I to ~unbounded).
4. Pre-register the hypothesis in `reports/hypothesis_registry.json` before running the harness (M-107 rule).
5. Require recency panels (`pf_30d`, `pf_14d`, `pf_48h`) before any BUILD-phase greenlight, per `MUTATION_THREE_AXIS_PROTOCOL.md`.

For `commodity_term_structure` specifically: the strategy has no production emitter (`source_module: null`). Either wire one up + collect 30d of fresh picks, or kill the registry entry. Do not size capital against null-emitter registry stats.

---

## Files / refs

- Live query log: this report (queries inlined above)
- Canonical funnel: `audit_dashboard/data/strategy_funnel_data.json` (commodity_term_structure block)
- Money-ready verdict: `audit_dashboard/data/money_ready_verdict.json` (2026-05-24)
- 8-AI critique: walgc0f1f (Mimo + Deepseek + Cerebras synthesis)
- Mutation protocol: `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- Pre-registration rule: M-107 / `.claude/skills/hypothesis-registry/SKILL.md`
- Branch HEAD at validation time: `e2f33ac0f` on `peer-claude/updates-entry-testing-protocol-dedupe-2026-05-31`
