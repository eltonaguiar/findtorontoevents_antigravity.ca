# Corrigendum — money_maker_ready_20260512T194402Z.md

**Filed:** 2026-05-12T21:05Z
**Original report:** `reports/money_maker_ready_20260512T194402Z.md`
**Investigator output:** task `afb3e40cba505a6a1`

## What the original report got wrong

Section 1 claimed `asset_class_health.n=0` was a structural bug. **It is not.**
I read the wrong field names from the payload:

| What I queried | Correct field name |
|---|---|
| `m.get('n')` | `m.get('resolved_n')` |
| `m.get('wr_pct')` | `m.get('win_rate')` |
| `m.get('pf')` | `m.get('profit_factor')` |

The schema lives at `audit_trail/dashboard_generator.py:5428-5439` and
emits the canonical fields `resolved_n` / `win_rate` / `profit_factor`.
The 2026-05-11 audit plan inherited the same wrong-field assumption,
and the V1 bug claim has propagated since.

The cavecrew-investigator I spawned on this misread the code by
following my framing — it traced a real `continue` at
`dashboard_generator.py:13670` after `b["closed"] += 1`, but that
`continue` only skips win/loss accumulation for picks that fail
`_is_valid_resolved_pick(p)`. The valid picks DO accumulate, and the
non-zero `resolved_n` values below confirm the accumulator works.

## Actual current per-class state (dashboard_data.json @ 2026-05-12T20:28Z, 0.45h old)

| Class | resolved_n | WR % | PF | Total PnL % | Status | Tier |
|---|---|---|---|---|---|---|
| **COMMODITY** | 422 | 67.5 | **3.89** | +686.77 | stable | **Tier 1 candidate** (PF>2, WR>55, n>200) |
| EQUITY | 447 | 53.2 | 1.55 | +376.68 | stable | Tier 2 (PF>1.5, WR>50, n>100) |
| ETF | 107 | 56.1 | 1.34 | +37.48 | stable | sub-T2 (PF<1.5) |
| CRYPTO | 7935 | 46.5 | 1.36 | +3019.29 | stable | sub-T2 (WR<50) |
| FOREX | 1355 | 46.1 | **0.29** | **-1026.15** | **stressed** | confirmed sub-floor (PF<1, big PnL drag) |
| BOND | 11 | 54.5 | 0.66 | -1.53 | thin_sample | n below floor |
| FUTURES | 0 | 0 | null | 0 | insufficient | empty |
| UNKNOWN | 6 | 50.0 | 2.40 | +0.13 | insufficient | empty |

## Verdict change (vs original report)

| Item | Original | Corrected |
|---|---|---|
| V1 asset_class_health.n=0 | "STILL BROKEN — blocks every verdict" | **NOT A BUG** — wrong field-name lookup |
| COMMODITY tier | "PHANTOM (n=0)" | **Tier 1 candidate** (PF 3.89, WR 67.5%, n=422) |
| EQUITY tier | "PHANTOM" | **Tier 2 confirmed** (PF 1.55, WR 53.2%, n=447) |
| CRYPTO tier | "PHANTOM" | sub-T2 (WR 46.5% < 50%) but stable |
| FOREX status | "PHANTOM" | **stressed** confirmed (PF 0.29, -1026 PnL%) |

## What this means for the remaining P0 cluster (plan 20260512T204143Z)

- **P0-#1 multi_asset_cot PF=19.93 verification** — STILL VALID. Number
  still implausible. DB cross-check still warranted.
- **P0-#2 asset_class_concentration disclosure** — STILL VALID. The
  fact that COMMODITY n=422 with PF=3.89 looks like Tier-1 raises the
  ALSO valid question of "how much of that is CT=F alone?". `_toxic_concentration`
  at system level exists; class-level rollup still missing.
- **P0-#3 capped_vs_raw_pnl_gap** — STILL VALID. EQUITY +376% total
  vs CRYPTO +3019% — capping policy disclosure still useful.
- **V1 asset_class_health bug** — **DROP from todo list**. Was a
  reader bug, not a writer bug.
- **V2 hf_stats cron 20d stale** — STILL VALID. Drift KS_D 0.31
  unrefreshed since 2026-04-22.

## Lesson

When a dashboard field reads `0` across the board, **first verify the
field name**, then claim the bug. The original audit + 2026-05-11 plan
both inherited this without verification — should have grepped the
writer.

Updated reproducer command (use this going forward):

```bash
python -c "
import json, pprint
d = json.load(open('audit_dashboard/data/dashboard_data.json', encoding='utf-8'))
pprint.pprint(d['performance']['asset_class_health'])
"
```

NFA — research surface only.
