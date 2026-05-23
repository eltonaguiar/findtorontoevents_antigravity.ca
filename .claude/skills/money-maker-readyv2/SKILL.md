---
name: money-maker-readyv2
description: Ultimate statistical edge audit per asset class. Produces proven, real-money-grade filters for CRYPTO/EQUITY/COMMODITY/ETF/FOREX/BOND so that a quant or hedge fund manager would find the edge trustworthy. Extends money-maker-ready v1.1 with stronger success criteria, autonomous execution rules, and a weekly filter output. Use when the user says "/money-maker-readyv2", "prove the edge", "real money filters", or "ultimate statistical edge". Aliases - money-maker-readyv2, ultimate-edge, prove-edge.
---

# /money-maker-readyv2 — Ultimate Statistical Edge Audit

**Goal:** Produce proven, quantitatively-validated filters per asset class such that:
- Top picks grow a live balance over time
- Downside is limited (MDD≤20%, position sizing by Kelly/Hyro overlay)
- Winners beat losers (PF≥1.5, WR≥50%)
- A quant/hedge-fund manager would rate the edge trustworthy for real capital

Inherits all hard rules from `/money-maker-ready` (v1.1). This v2 adds:

## Success Criteria (ALL must be true before calling done)

1. **EQUITY**: Weekly filter output shows ≥5 picks with elite_score≥60, WR≥55% on historical analogs (n≥30 per filter bucket), PF≥1.5 on resolved picks.
2. **CRYPTO**: Sub-class filters (WR≥50%) identified and live — picks passing the filter have PF≥1.5 on resolved_n≥100.
3. **COMMODITY**: Post-COT-dedup clean picks accumulate; once n≥50 post-dedup, top strategy identified with PF≥1.5.
4. **ETF**: n≥150 on path to OOS_READY; PF maintained ≥1.3; top ETF strategies identified.
5. **FOREX**: Mutation protocol in progress; LONG-direction block evaluated by data; directional filter identified if WR≥50% exists.
6. **BOND**: Accumulating picks; top BOND strategy (if any) identified once n≥20.
7. **Kelly sizing**: All weekly filter picks have a computed position size (% of account) via `compute_position_size()` with DD-halt guard.

## Operating Rules (NON-NEGOTIABLE)

1. **PLAN FIRST** — numbered task list before any code.
2. **WORK AUTONOMOUSLY** — no clarifying Qs unless genuinely blocked.
3. **SELF-VERIFY** — after every step: run tests, inspect output, confirm it worked.
4. **DEBUG YOURSELF** — if it fails, diagnose + fix; don't hand back.
5. **USE EVERY TOOL** — terminal, code exec, real data.
6. **NO PLACEHOLDERS** — real components + real states; no TODOs.
7. **PROGRESS LOG** — track completed / in-flight / decisions / blockers.
8. **STAY ON GOAL** — off-spec discoveries: note + keep moving.
9. **IF BLOCKED** — log the wall, continue everything parallelizable.
10. **CHECK SUCCESS BEFORE STOPPING** — re-read criteria, confirm each is met.

## Data Sources (read, never invent)

| Source | Field | Purpose |
|--------|-------|---------|
| `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` | n, WR, PF | Verdict-grade resolved_n per class |
| `audit_dashboard/data/dashboard_data.json::walkforward.by_class` | oos_wr, oos_sharpe | OOS verification |
| `audit_dashboard/data/dashboard_data.json::fwd_vs_bt_divergence.rows` | BT vs OOS WR gap | Overfit detector |
| `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS` | current blocks | Active gate |
| `docs/PERFORMANCE_CHARTER.md` | Tier thresholds | T1/T2/T3 definition |

## Freshness Gate (FAIL-FAST if >2h stale)

```python
import json; from pathlib import Path; from datetime import datetime, timezone
d = json.loads(Path("audit_dashboard/data/dashboard_data.json").read_text())
age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(d["generated_at"].rstrip("Z")).replace(tzinfo=timezone.utc)).total_seconds()/3600
assert age_h < 2, f"STALE: {age_h:.1f}h — abort"
```

## Weekly Filter Output Format

After the audit, produce `reports/weekly_filter_<UTC>.md`:

```markdown
# Weekly Real-Money Filter — <DATE>

## EQUITY Top Picks Filter
- Criteria: elite_score≥60, asset_class=EQUITY, status=OPEN, direction=LONG
- Expected WR (historical analog): XX% (n=YY)
- Expected PF (historical analog): X.XX
- Kelly size: X.X% of account per pick

## [Repeat per class that has n≥100 resolved picks]

## How to Apply
1. Open findtorontoevents.ca/audit
2. Apply filter: [specific UI filter steps]
3. Size per Kelly recommendation
4. Exit: follow TP/SL as set on pick

## Risk Controls
- Max per-pick: X% of account (Kelly 0.25-fraction)
- Daily soft-stop: -2% total PnL triggers pause (Hyro overlay)
- DD halt: if rolling_30d drawdown > 30%, pause all sizing
```

## Execution Workflow

### Step 1 — Freshness preflight (fail-fast)
Run the freshness gate above. If stale, surface + ask.

### Step 2 — Per-class baseline
Read `asset_class_health`. Per class: n, WR, PF, Tier vs charter.

### Step 3 — Identify proven filter per class
For each class with resolved_n≥50, query (or derive from `dashboard_data.json`) the top-performing:
- Strategy family
- Direction (LONG vs SHORT)
- Confidence bucket (high/medium)
- Time-of-day window (if data available)

### Step 4 — Compute Kelly sizing
For each proven filter, use `alpha_engine/kelly_position_sizer.py::compute_position_size()` to output:
- % of account per pick
- Expected position size in USD at $10k account

### Step 5 — Write weekly filter report
Output `reports/weekly_filter_<UTC>.md` with filter per class + sizing.

### Step 6 — Verify picks hit the filter
Pull current OPEN picks from `audit_dashboard/data/dashboard_data.json::systems` or JSON pick sources. Apply each filter, count matches.

### Step 7 — Commit report
```bash
git add reports/weekly_filter_<UTC>.md
git commit -m "feat(edge): weekly real-money filter + Kelly sizing <DATE>"
```

## Quality Bar
- Code: clean, typed, follows project conventions
- Design: looks like a well-funded startup shipped it
- Output: survives a senior code review
- Docs: every new pattern / env var / decision logged

## Constraints (same as money-maker-ready v1.1)
- NEVER edit `audit_dashboard/index.html`
- NEVER run `audit_trail/dashboard_generator.py` locally
- NEVER add to BLOCKED_ASSET_STRATEGY_PAIRS without explicit user approval
- NEVER claim performance without `(asset_class | n | timeframe)` triple
- NEVER push without pulling first

## Final Deliverable
- Confirmation each success criterion is satisfied
- Every file created / modified
- How to run / test / deploy
- Proof (test output + filter + URL)
- Decisions made + known limitations
