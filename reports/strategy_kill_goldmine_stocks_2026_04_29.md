# Strategy Kill: `goldmine_stocks` source on EQUITY

**Date:** 2026-04-29
**Author:** Claude Opus 4.7 (subagent under orchestrator)
**Goal:** #1 (audit dashboard performance — phenomenal performance across all asset classes)
**Branch:** `fix/kill-goldmine-stocks-2026-04-29`
**Protocol:** `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

---

## Finding

`goldmine_stocks` source on EQUITY is the largest single-source drag on EQUITY's
otherwise Tier-2-candidate 30-day cohort.

**Closed-pick evidence** (from `audit_dashboard/data/dashboard_data.json`,
`picks.recent_closed`, verified independently by orchestrator + Copilot stream):

| Metric | Value |
|---|---|
| Total picks (EQUITY) | 13 |
| Wins | 0 |
| Losses | 13 |
| Win rate | **0.0%** |
| Sum pnl_pct | **-53.36%** |
| Avg pnl_pct | -4.10% / trade |
| Direction split | 100% LONG, 0 SHORT |

**Source/strategy scope:** there are 14 `goldmine_stocks` rows in `recent_closed`
total; 13 are EQUITY-tagged (the one non-EQUITY row is excluded from this kill
scope). The 13 EQUITY picks split across three "consensus" tiers:

| Strategy | n | sum_pnl_pct | WR |
|---|---|---|---|
| `goldmine_6x_consensus` | 11 | -45.76% | 0.0% |
| `goldmine_5x_consensus` | 1 | -2.02% | 0.0% |
| `goldmine_7x_consensus` | 1 | -5.59% | 0.0% |

Note that the deepest-confluence pick (`goldmine_7x_consensus`) lost MORE than
the lighter `goldmine_5x_consensus` — consensus depth is **anti-correlated**
with WR. The signal itself is broken; this is not a "lower-confluence picks
hurt the cohort" story.

---

## Three-axis mutation autopsy

Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` we check whether any axis has a
winning subset before escalating to hard block.

### Direction axis

| Direction | n | WR | sum_pnl_pct |
|---|---|---|---|
| LONG  | 13 | 0.0% | -53.36% |
| SHORT |  0 | n/a  | n/a |

100% LONG. **No SHORT evidence base.** Inverse mutation is speculation,
not data-driven. **Not viable.**

### Symbol axis

| Symbol | n | WR | sum_pnl_pct |
|---|---|---|---|
| JNJ  | 4 | 0.0% | -18.54% |
| XOM  | 3 | 0.0% | -15.30% |
| ABBV | 2 | 0.0% |  -6.31% |
| CVX  | 2 | 0.0% |  -6.99% |
| MRK  | 1 | 0.0% |  -4.22% |
| GS   | 1 | 0.0% |  -2.02% |

These are all blue-chip defensives (healthcare, energy super-major, and one
investment bank). No symbol has a winning subset. The picks are losing on
healthy companies — the consensus signal itself, not a stock-selection edge,
is what's broken. Symbol allowlist not viable.

### Strategy axis

All three "consensus" tiers (5x / 6x / 7x) are 0% WR. The higher-confluence tier
lost more per trade. There's no within-source winning subset to gate on. Not
viable.

### Timeframe axis

Not applicable — `goldmine_stocks` picks do not carry timeframe labels in the
closed ledger; no slice possible.

### Mutation Quality Score

Per the protocol's `MutationQuality ≈ (WR_subset × n_subset) / n_total`
formula: with **zero winning trades across every axis**, every candidate
subset has WR=0. Mutation quality = 0. Hard block is the correct escalation.

---

## Verdict: **KILL** (Stage-5 hard block)

All three rehab axes blocked. Per
`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, "the composite-pair block in
`alpha_engine/strategy_blocklist.py::_RETIRED_SYSTEM_STRATEGY_PAIRS` (for
example `kimi_signal_tracking/default` on forex, added 2026-04-19) is
appropriate without further rehab" when the loss pattern is deterministic.
This case is the same shape: WR = 0% on n = 13 across 6 symbols, 3 strategies,
and 1 direction.

We add **three composite pairs** (not a strategy-wide block) to scope the kill
narrowly:

```python
("goldmine_stocks", "goldmine_5x_consensus")
("goldmine_stocks", "goldmine_6x_consensus")
("goldmine_stocks", "goldmine_7x_consensus")
```

This preserves any future use of these strategy names by other source systems
(none currently emit them) and any future `goldmine_stocks` strategies outside
the killed triple (e.g. a hypothetical `goldmine_4x_consensus`).

---

## Expected impact

Stops the **-53.36% sum pnl_pct** drag on the EQUITY 30d cohort going forward.
Note: this is the **realized** drag on closed picks already in the ledger. The
kill prevents *future* same-pattern bleed, not retro-recovery.

EQUITY 30d cohort recovery (pnl_pct terms): roughly **+53.36% sum_pnl_pct
restored** vs. the counterfactual where this source kept emitting at the same
volume and 0% WR.

---

## Rollback

```bash
GOLDMINE_STOCKS_KILL_DISABLED=1
```

Setting this env var on the runner bypasses all three composite pairs (without
affecting the unrelated `rapid_fire × macd_rsi_confluence` kill, which has its
own flag). Default unset = kill active.

---

## Wire-up

The blocklist is consumed by `alpha_engine/feed_hygiene.py` →
`is_valid_active_pick()`, which is called from the production pick-generation
path. No new caller is added; this is a config-only change to an already-wired
module. Wire-up rule satisfied (existing production caller).

---

## References

- Closed-pick evidence: `audit_dashboard/data/dashboard_data.json`,
  `picks.recent_closed[?source_system=='goldmine_stocks' && asset_class=='EQUITY']`
- Reproducer:
  ```bash
  python -c "
  import json
  d = json.load(open('audit_dashboard/data/dashboard_data.json'))
  rows = [p for p in d['picks']['recent_closed']
          if p.get('source_system')=='goldmine_stocks'
          and p.get('asset_class')=='EQUITY']
  wr = 100*sum(1 for p in rows if (p.get('pnl_pct') or 0)>0)/len(rows)
  s = sum((p.get('pnl_pct') or 0) for p in rows)
  print(f'n={len(rows)} WR={wr:.1f}% sum={s:+.2f}%')
  "
  ```
- Pattern precedent: `d9a9a3a6e2` (rapid_fire × macd_rsi_confluence kill, PR #509)
- Blocklist file: `alpha_engine/strategy_blocklist.py`
- Tests: `tests/test_strategy_blocklist_goldmine_stocks.py`
