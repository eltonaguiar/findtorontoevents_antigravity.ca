# mercury2_fast — Strategy Investigation Before Kill

**Date:** 2026-05-17
**Protocol:** `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
**Data source:** `audit_trail/quality_gates.py` block comments (2026-05-14 dragger quarantine); `alpha_engine/data/closed_picks.json` (8,421 rows, file mtime 2026-05-15)
**Verdict:** **ALREADY-BLOCKED** — confirmed correct. No data in current snapshot; block pre-dates current closed_picks.json. Keep blocked.

---

## 1. Headline numbers (from block comments — source of truth)

| Metric | Value (BLOCKED_SOURCE_SYSTEMS comment) | Value (BLOCKED_ASSET_STRATEGY_PAIRS comment) |
|---|---|---|
| n | **14** | **32** |
| Win rate | **25.0%** | not stated |
| Profit factor | **0.02** | **0.07** |
| Cumulative PnL | **−639%** | **−140%** |
| Asset class blocked | All (source-level) | CRYPTO specifically |

The two block entries use different n/PF values — likely from different audit dates. Both are catastrophically negative. The BLOCKED_SOURCE_SYSTEMS entry (line 1708, n=14, PF 0.02) pre-dates the BLOCKED_ASSET_STRATEGY_PAIRS entry (line 2354, n=32, PF 0.07, 2026-05-14 quarantine). Both agree: this strategy is a systematic loser.

**Data availability:** mercury2_fast appears in ZERO rows of the current `closed_picks.json` (8,421 rows across 13 source_systems). The picks were either:
- Written to a separate data store before the current snapshot
- Purged as part of the 655k stale-row cleanup (PA console action still pending)
- Emitted only to the live DB and never ingested into the JSONL

Mutation analysis on the closed JSONL is therefore not possible. The block was added with sufficient evidence at the time (2026-05-14 dragger quarantine after money-maker-ready P0 audit).

---

## 2. AXIS 1 — SYMBOL

**Cannot evaluate** — no rows in current closed_picks.json for mercury2_fast. Symbol-axis mutation would require ≥30 rows per symbol and ≥10% of total to be viable. With n=14–32 total, no single symbol can reach viability even if all rows were for one symbol.

**Symbol axis: N/A — insufficient data for mutation. DEAD by sample size.**

---

## 3. AXIS 2 — DIRECTION

**Cannot evaluate** — no rows in current snapshot. With n≤32 total, even a 100%-LONG or 100%-SHORT split would produce only 32 rows. Step-5 mutation guard requires n≥100 for the winning subset. Direction axis cannot clear the bar.

**Direction axis: N/A — insufficient data. DEAD by sample size.**

---

## 4. AXIS 3 — TIMEFRAME

"fast" in the strategy name implies a scalp/short-term timeframe. With no data, a timeframe split is not computable.

**Timeframe axis: N/A — no data.**

---

## 5. Source system context

mercury2_fast is a variant of the mercury2 family (fast = shorter timeframe / scalp). The base source `mercury2` is separate from the blocked `mercury2_fast` — see quality_gates.py line 5096:

> `# 2026-05-09: NEW source distinct from blocked mercury2_fast.`

This confirms the two are tracked independently. The block on mercury2_fast does NOT block mercury2 picks.

---

## 6. Current block status — ALREADY FULLY BLOCKED

| Line | Structure | Entry |
|---|---|---|
| 1708 | `BLOCKED_SOURCE_SYSTEMS` | `"mercury2_fast"` — "14 trades, 25% WR, −639% PnL, PF 0.02" |
| 2354 | `BLOCKED_ASSET_STRATEGY_PAIRS` | `("CRYPTO", "mercury2_fast")` — "n=32, −140% PnL, PF 0.07" |

The strategy is hard-blocked at both the source-system level (all asset classes) and the CRYPTO asset-class level. Defense-in-depth is present. It cannot reach production picks.

---

## 7. VERDICT — ALREADY-BLOCKED (confirm; no action needed)

- **Sample size:** n=14–32 — below the Step-5 mutation minimum of n≥100 on any subset. Mutation protocol cannot produce a viable candidate regardless of axis.
- **Performance:** PF 0.02–0.07 at system level. Both extremes of the reported range are catastrophic (break-even requires PF≥1.0).
- **Data availability:** Zero rows in current closed_picks.json — likely pruned from the MySQL ghost-row backlog or emitted to live DB only.
- **Mutation verdict:** ALL AXES N/A — sample too small to evaluate any subset.
- **Block status:** ALREADY-BLOCKED in 2 structures across `quality_gates.py`. Correct and sufficient.

**Recommendation:** Keep mercury2_fast blocked. No `quality_gates.py` edit is needed. The mutate-before-kill investigation is hereby documented as complete with N/A finding on all axes due to sample-size floor. Block is upheld.

---

*Reproducer:* `grep -n "mercury2_fast" audit_trail/quality_gates.py` — shows all block entries. Filter `alpha_engine/data/closed_picks.json` by `strategy == "mercury2_fast"` or `source_system == "mercury2_fast"` returns 0 rows in current snapshot (mtime 2026-05-15).
