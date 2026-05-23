# ai4trade Promotion Gate — Design

**Date:** 2026-04-14
**Status:** Approved (brainstorm phase)
**Owner:** This Claude Code instance
**Peer coordination:** Cursor owns the ingestor (`ai_trader_crowd_intel.py`). This module consumes its output and does not duplicate ingestion.

## Context

The user asked to investigate [HKUDS/AI-Trader](https://github.com/HKUDS/AI-Trader) and integrate "top performing strategies that stand the test of time and are statistically valid" as baby strategies.

Investigation surfaced two load-bearing facts that shape the design:

1. **The repo is not a strategy library.** It is an agent-native trading platform. Trading signals live on ai4trade.ai at runtime, published by registered agents via `/api/signals/feed`. There is no backtested code in the repo to import.
2. **The platform is ~2 weeks old.** No agent on it has a track record long enough to be called "statistically valid" or "test-of-time proven" today. Every top-PnL agent is a long-beta survivor of one BTC rally off $71–74K. Cursor's own investigation confirmed this and also flagged that most "top agents" are copy-followers of 4–6 originators — effective n of independent strategies is small.

These facts mean any integration shipped *now* is a **data-collection instrument**, not an alpha source. The validation has to happen in our forward pipeline over weeks, across at least one red BTC 4h regime period, before anything is promoted to a first-class baby strategy. This spec defines that validation layer.

## Scope

**In scope:**
- A promotion gate module that decides which ai4trade originator agents have earned a real `.py` file in `baby_strategies/`.
- A gate report artifact for audit.
- Auto-generation of wrapper files to a staging directory (`baby_strategies/pending/`); a human move activates them.
- Weekly demotion pass with mutation-before-kill semantics.

**Out of scope (Cursor owns):**
- Ingestion from `/api/signals/feed`.
- Agent self-registration against ai4trade.
- Normalization of raw signals into our pick schema.
- The `source_system="ai4trade"` tagging.

## Architecture

Single module: `alpha_engine/ai4trade_promotion_gate.py`.

```
Cursor's ingestor
      │
      ▼
 dashboard_data.json (source_system="ai4trade", agent_id per pick)
      │
      ▼
 forward-validation pipeline (existing, unchanged)
      │
      ▼
 ai4trade_promotion_gate.py  ← this spec
      │
      ├──► audit_dashboard/data/ai4trade_gate_report.json   (always)
      └──► baby_strategies/pending/ai4trade_agent_<id>.py   (on promotion)
             │
             └── human review + manual move ──► baby_strategies/
```

No new database tables. No new services. Reads what already exists. Writes two artifact paths.

## Gate Criteria

All must pass for promotion. Each failure is recorded with a reason string in the report.

| # | Criterion | Threshold | Rationale |
|---|-----------|-----------|-----------|
| 1 | Originator-only | Agent has ≥ 1 non-copy signal. Copies of other agent_ids are filtered even if the ingestor missed them. | Effective-n problem. Copy-followers inflate apparent breadth. |
| 2 | Forward sample size | n ≥ 30 **closed** picks | Minimum for stats to be non-vapor. Open picks don't count. |
| 3 | Time under test | ≥ 8 calendar weeks since first-tracked signal | The "test of time" clause. Hard floor, no exceptions. Backfilled ai4trade history does not count — first-tracked is first-tracked. |
| 4 | Regime coverage | Picks must span at least one red BTC 4h regime period of ≥ 48h | Prevents rally-only survivors. Hard requirement per user approval. |
| 5 | Tier-1 stats | WR ≥ 55%, PF ≥ 1.5, max DD < 20%, Darwin v2 ≥ existing-distribution median | Same bar as tier1_criteria_validator_v2. |
| 6 | Correlation floor | Pearson r of daily PnL vs top-5 existing baby strategies < 0.7 | Don't promote duplicates of what we already run. |
| 7 | LONG bias check | If ≥ 95% of picks are LONG, agent tagged `long_biased=true` and only promoted with an accompanying SHORT-source counter-agent | Enforces existing `feedback_long_source_bias.md` rule. |

## Outputs

### Always: `audit_dashboard/data/ai4trade_gate_report.json`

One record per tracked originator agent:

```json
{
  "generated_at": "2026-06-09T12:00:00Z",
  "agents": [
    {
      "agent_id": 784,
      "display_name": "ClaudeTrader",
      "first_tracked": "2026-04-14T00:00:00Z",
      "weeks_under_test": 8.1,
      "n_closed": 47,
      "wr_pct": 58.3,
      "pf": 1.62,
      "max_dd_pct": 14.1,
      "darwin_v2": 0.71,
      "long_pct": 97.0,
      "regime_coverage_hours_red_btc_4h": 72,
      "correlation_top5": 0.41,
      "gates": {
        "originator_only": "pass",
        "forward_sample": "pass",
        "time_under_test": "pass",
        "regime_coverage": "pass",
        "tier1_stats": "pass",
        "correlation_floor": "pass",
        "long_bias_check": "flag: long_biased=true, needs SHORT counter-agent"
      },
      "promotion_status": "blocked_on_short_counter"
    }
  ]
}
```

### On promotion: `baby_strategies/pending/ai4trade_agent_<id>.py`

Auto-generated from a template. Thin wrapper: its `scan()` returns the agent's live signals, filtered by our standard risk guards. A matching `.meta.json` records:

- Promotion date
- Full gate report snapshot that justified promotion
- Agent display name, first-tracked date, weeks under test

The file lands in `baby_strategies/pending/`, **not** `baby_strategies/`. A human reviews and moves it. This is deliberate — action-with-care for anything that becomes a first-class baby strategy.

## Demotion

Same gate re-runs weekly (scheduled via existing infra — not this spec's concern).

If a previously-promoted wrapper's stats fall below tier-1 for **2 consecutive weekly runs**:

1. The wrapper file is **not** deleted. Per `feedback_no_abort_ideas.md` and `feedback_mutate_before_kill.md`, we do not abandon implementations.
2. The agent is added to `BLOCKED_SOURCE_SYSTEMS` following the existing mutation-before-kill protocol (`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`).
3. A demotion record is appended to the wrapper's `.meta.json`.
4. The gate report records the demotion event so the audit dashboard can surface it.

## Deliberate Non-Features

- **No trading.** Promotion only means "eligible to be signaled by the normal scanner flow." This module never places orders.
- **No synthetic backfill.** First-tracked is first-tracked. Historical performance on ai4trade.ai before we started tracking is ignored.
- **No file writes to `baby_strategies/` directly.** Only to `baby_strategies/pending/`. Activation is a human move.
- **No ingestion.** That is Cursor's `ai_trader_crowd_intel.py`. If it breaks, this module reports zero-tracked-agents and exits clean.
- **No CLAUDE.md-level policy changes.** This is a new module; it does not edit existing pipeline code.

## Testing Strategy

- Unit tests for each gate criterion in isolation, using fixture picks that pass/fail each one.
- Integration test that feeds synthetic ai4trade picks through forward-validation → gate and checks report shape.
- A dry-run flag (`--dry-run`) that runs the gate but suppresses file generation in `pending/`.

## Open Questions (for implementation-plan phase)

- Where does the Darwin v2 "existing-distribution median" come from — snapshot-at-run-time or a frozen threshold? Lean: snapshot-at-run-time, recorded in the report.
- Regime-coverage check: which BTC 4h regime column in existing data? Lean: reuse the same column the HMM regime terminal reads.
- Correlation-floor computation: daily returns or per-pick PnL? Lean: daily returns, resampled.

These are sized for the implementation plan to resolve by reading existing code, not design-level decisions.
