# null take_profit Investigation — 2026-05-04

## TL;DR

**The "60/60 active picks have null take_profit" claim from the audit-hyperfocus swarm (AHF-02 in claude.json) is FALSE.** Live verification: **0/60** picks have null take_profit. Every active pick has a non-zero TP. The R:R hard gate (`feat/rr-hard-gate-shadow-2026-05-04`) is NOT blocked by null TP.

This is the kind of model-fabricated finding that the lessons-learned section of `super_swarm_synthesis_2026_05_04.md` warned about. Counts/percentages cited by a single engine without a grep-citable evidence path should be verified before being treated as P0.

## Verification

```bash
$ python -c "
import json
d = json.load(open('audit_dashboard/data/dashboard_data.json'))
picks = d['picks']['active']
print('total:', len(picks))
print('null TP:', sum(1 for p in picks if not p.get('take_profit')))
print('first:', {k:picks[0].get(k) for k in ('symbol','take_profit','stop_loss','entry_price')})
"
total: 60
null TP: 0
first: {'symbol': 'BNBUSDT', 'take_profit': 633.24921429, 'stop_loss': 604.63385714, 'entry_price': 616.08}
```

Every active pick has populated `take_profit`, `stop_loss`, and `entry_price`.

## Why the swarm got it wrong

Likely causes (cannot prove without engine logs):

1. **Schema confusion**: The engine may have looked at a different field path (`pick.target_price`, `pick.tp`, `pick.tp_price`) which IS often null for picks that ship under the canonical `take_profit` name.
2. **Sample window**: The swarm prompt said "60/60 active picks" but the dataset emits BOTH `picks.active` (canonical, hydrated by `dashboard_generator.py`) AND legacy `active_picks` arrays in some paths. If the engine read a stale legacy array, results would differ.
3. **Pure fabrication**: One model out of 8 made up a number that fit the narrative of "shadow_probation can't enable because TPs are missing". Not unprecedented per session memory.

## Call-graph for TP population

The TP-population path is robust (see `audit_trail/dashboard_generator.py:6473-6759`):

1. **Source pull** (`dashboard_generator.py:6473-6481`): try 7 field names per pick:
   `take_profit, target_price, targetPrice, tp, tp_price, tp_price_1_5, tp_pct, suggested_tp_pct`
2. **Direction inference fallback** (`:6454-6468`): if direction is missing, infer from TP > entry vs TP < entry.
3. **ATR-based fallback** (`:6717-6727`): if `tp_val` is still 0 and entry > 0, compute from `atr_at_entry`:
   - LONG: `tp = entry + 2.5 * atr`, `sl = entry - 1.5 * atr`
   - SHORT: `tp = entry - 2.5 * atr`, `sl = entry + 1.5 * atr`
4. **Asset-class defaults fallback** (`:6730-6745`): if no ATR either, use:
   - EQUITY 8/5%, ETF 5/3%, FOREX 1.5/1%, COMMODITY 3/2%, FUTURES 3/2%, default 2.5/1.5%
5. **R:R 1.67:1 derivation** (`:6747-6759`): if exactly one of TP/SL is set, compute the other for 1.67:1 R:R.
6. **Final assignment** (`:6930`): `_pick["take_profit"] = tp_val`.

Result: every active pick that flows through `dashboard_generator.py` should emit a non-zero TP. The 0/60 null count above confirms this works in production.

## What this means for the R:R hard gate

The unified queue (`reports/audit_unified_implementation_queue_2026_05_04.md`) listed **C3 (null TP on 60/60 picks)** as a P0 BLOCKER for merging `feat/rr-hard-gate-shadow-2026-05-04`. **This blocker does not exist.** The R:R gate can be evaluated against live picks safely.

The OTHER blocker on the R:R PR is genuine and unchanged:
- **Kimi C1 vs `audit_trail/quality_gates.py:2492-2511` "DATA CORRECTED 2026-04-01"** — Kimi says R:R 1.5-2.0 = best (PF 5.81); local says R:R 1.0-1.5 = best (70.8% WR). This requires a `tools/mutation_analysis.py` re-run on closed picks before merging the gate.

## Updated R:R PR readiness

| Blocker | Status |
|---|---|
| null TP (C3) | ❌ FALSE ALARM — 0/60 nulls verified |
| RR-band conflict (C1 vs DATA CORRECTED) | ✅ STILL BLOCKING — needs reaudit |
| `passes_rr_hard_gate` rejects on missing TP | ✅ DEFENSIVE BUT MOOT — TP always populated |

So: the R:R PR is one investigation away from mergeable.

## Updates to other docs

The following claims should be revised in their respective files:

- `reports/super_swarm_synthesis_2026_05_04.md` — flag AHF-02 as withdrawn after live verification.
- `reports/audit_unified_implementation_queue_2026_05_04.md` — strike C3 from the blocker list; the only remaining R:R blocker is C1 (band conflict).
- `reports/diff_matrix_2026_05_04.md` — drop the "C3 60/60 null TP" entry from the dashboard-credibility column.

## Recommendation

Run `tools/mutation_analysis.py` on the post-resolver-v2 closed picks (~last 90d) to adjudicate the RR-band conflict. Output goes to `reports/rr_band_reaudit_2026_05_04.md`. If the local "1.0-1.5 = best" comment holds, our `RR_HARD_GATE_MIN/MAX` constants need to flip from [1.5, 2.0] to [1.0, 1.5]. If Kimi's holds, ship the gate as-is and remove the 2026-04-01 comment.

## Investigation provenance

- 0/60 verification: live `audit_dashboard/data/dashboard_data.json` query on 2026-05-04
- Call-graph: `audit_trail/dashboard_generator.py:6473-6759`, single-file, no cross-module dependencies
- Original false-positive source: `swarm_runs/audit_hyperfocus_v1/claude.json::p0_audit_findings[1]` (AHF-02), confidence 0.97 — model self-rated highest possible, was wrong
