# BANNED Tier Gate Leak Investigation — 2026-04-29

## TL;DR
- `passes_active_gate()` correctly hard-blocks BANNED-tier sources for **active** picks, but is **never applied to `recent_closed`** — 362 BANNED picks (10.3% of the 3,500-entry closed window) appear in the audit history and distort PF/WR calculations.
- Both `stocks_competition` and `rapid_fire` are actively generating picks **today** (last closed_at = 2026-04-29), confirming this is a live/ongoing leak, not just historical residue.
- Root cause is **Cause A**: emitters write directly to source JSON files without consulting the gate; the dashboard loader (`collect_all_picks`) ingests those closed rows unconditionally and `_build_recent_closed_picks` does no BANNED filtering.

---

## Reproduction

```
Total BANNED closed:  362
Sources: {'rapid_fire': 165, 'stocks_competition': 153, 'multi_asset': 30,
          'kimi_signal_tracking': 7, 'fast_stocks_competition': 6,
          'multi_asset_institutional': 1}
Total BANNED ACTIVE: 0      ← gate IS working for active display
_gate_passed distribution (recent_closed): {None: 362}   ← gate was NEVER applied
```

BANNED picks span from 2026-02-17 to 2026-04-29 (today). 286 of the 362 were closed
after 2026-04-01; 51 were closed after 2026-04-28.

---

## Sample BANNED Picks

### stocks_competition (153 picks)

| symbol | strategy | trust_tier | _gate_passed | wf_verdict | created_at | pnl_pct |
|--------|----------|------------|--------------|------------|------------|---------|
| ATER | top_gainers_momentum | BANNED | None | (none) | None | -15.01 |
| AMD | Breakout Momentum | BANNED | None | VIABLE | None | -6.49 |
| MRK | Bollinger MR | BANNED | None | MARGINAL | None | -1.66 |
| ABBV | Bollinger MR | BANNED | None | MARGINAL | None | -0.64 |
| LCID | Bollinger MR | BANNED | None | MARGINAL | None | -3.45 |
| UUP | Bollinger MR | BANNED | None | MARGINAL | None | +0.92 |
| MRK | Classic Momentum | BANNED | None | FAILING | None | -4.36 |
| AVGO | Trend Following | BANNED | None | (none) | None | +6.04 |

### rapid_fire (165 picks)

| symbol | strategy | trust_tier | _gate_passed | wf_verdict | created_at | pnl_pct |
|--------|----------|------------|--------------|------------|------------|---------|
| BBUSDT | macd_rsi_confluence | BANNED | None | FAILING | None | -2.73 |
| LUNCUSDT | macd_rsi_confluence | BANNED | None | FAILING | None | +4.69 |
| ORCAUSDT | macd_rsi_confluence | BANNED | None | FAILING | None | -2.95 |
| ZKPUSDT | macd_rsi_confluence | BANNED | None | FAILING | None | -5.69 |
| TURTLEUSDT | macd_rsi_confluence | BANNED | None | FAILING | None | -2.82 |
| GIGGLEUSDT | macd_rsi_confluence | BANNED | None | FAILING | None | +3.02 |
| LUNAUSDT | macd_rsi_confluence | BANNED | None | FAILING | None | -2.93 |
| PENGUUSDT | macd_rsi_confluence | BANNED | None | FAILING | None | +5.20 |

---

## Code Archaeology

### Gate implementation

`audit_trail/quality_gates.py`:
- **Line 588–591**: `BLOCKED_ACTIVE_TRUST_TIERS = {"BANNED", "AVOID", "UNTRUSTED"}` — the sentinel set.
- **Lines 933–994**: `BLOCKED_SOURCE_SYSTEMS` set includes `stocks_competition`, `fast_stocks_competition`. Note: `rapid_fire` is NOT in `BLOCKED_SOURCE_SYSTEMS` (it only has a score floor at line 4089); its BANNED status comes exclusively from `system_trust_registry.py`.
- **Lines 3626–3630**: `passes_active_gate()` hard-blocks any pick whose `trust_tier` is in `BLOCKED_ACTIVE_TRUST_TIERS`. Return `False` immediately.
- **Lines 4082–4086**: Also blocks picks whose `source_system` is in `BLOCKED_SOURCE_SYSTEMS` — a redundant second fence for stocks_competition (belt and suspenders).

`audit_trail/dashboard_generator.py`:
- **Line 12375**: `pick["trust_tier"] = get_tier(pick.get("source_system", ""))` — trust_tier is stamped on EVERY pick (active + closed) during the leaderboard-enrichment loop at line 12177.
- **Lines 13447–13450**: `_filter_active_picks_with_gate()` calls `passes_active_gate()` on **active** picks only, setting `_gate_passed=True/False` and removing BANNED picks.
- `_build_recent_closed_picks()` (line 5319): Pure recency/reservation sort — **no gate or BANNED filter of any kind**.
- `collect_all_picks()` (line 6669): stocks_competition rows ingested at lines 6790–6796 into `closed` bucket unconditionally; rapid_fire closed rows at lines 6758–6778 also unconditionally.

`cross_aggregation/system_trust_registry.py`:
- **Lines 386–398**: `rapid_fire` → `TIER_BANNED` (25% WR, -429% PnL, 152 trades, banned 2026-03-18).
- **Lines 393–399**: `stocks_competition` → `TIER_BANNED` (26.4% WR, 174 trades, banned 2026-03-18).
- **Lines 370–375**: `multi_asset` → `TIER_BANNED` (25.8% WR, PF 0.28, banned 2026-03-15).

### Emitter behavior

**`rapid_fire_data/pick_tracker.py`** (the lifecycle tracker):
- `make_closed_record()` (line 387) writes raw closed dict with `"source_system": "rapid_fire"` directly to `closed_picks.json` via `save_json(CLOSED_FILE, closed)` (line 485).
- **Zero calls to `passes_active_gate()`, `passes_smart_gate()`, or any trust-tier check.**

**`alpha_engine/isolated_signal_integrator.py`** (the active-pick feed for rapid_fire):
- Loads `rapid_fire_data/active_picks.json` and injects normalized picks into `production_scanner.py`'s active list (lines 51, 369–383, 511–636).
- Quality checks: asset_class identification, stablecoin filter, confidence >= 0.60, kill_list, status check — **no BLOCKED_SOURCE_SYSTEMS or trust_tier BANNED check.**
- However, `production_scanner.apply_quality_gates()` runs downstream (line 4961), and `dashboard_generator._filter_active_picks_with_gate()` runs after that — so active BANNED picks are **correctly blocked** before display (confirmed: 0 active BANNED picks in data).

**`STOCKS/competition/forward_picks.json`**:
- Modified 2026-04-24. Contains 283 OPEN and 1217 CLOSED picks (WON/LOST). The emitter continues generating picks today despite the ban recorded in the registry on 2026-03-18. The dashboard picks up closed rows unconditionally.

---

## Root Cause Diagnosis

**Root cause: (A) — Emitters write directly to source JSON files without consulting the gate; the closed-pick ingest path has no BANNED gate.**

### Evidence for (A)

1. All 362 BANNED picks have `_gate_passed=None`. The `_gate_passed` flag is only set by `_filter_active_picks_with_gate()`, which is only called on `active` picks (dashboard_generator.py line 13447). It is **never called on closed picks**. This is definitive: the gate was never consulted for these picks' lifecycle.

2. `rapid_fire_data/pick_tracker.py:make_closed_record()` and `save_json()` do not import or call any quality gate.

3. `alpha_engine/isolated_signal_integrator.py` imports no quality gate and does not check `BLOCKED_SOURCE_SYSTEMS`.

4. `dashboard_generator.collect_all_picks()` ingests closed rows from `STOCKS/competition/forward_picks.json` (stocks_competition) and `rapid_fire_data/now_picks.json` + `rapid_fire_data/closed_picks.json` (rapid_fire) with no BANNED filter.

5. The emitters remain **actively producing picks today** (stocks_competition: last generated 2026-04-24; rapid_fire now_picks: last scan_time 2026-04-29 13:58:50). This is not historical data — the leak is ongoing.

### Evidence against (B) — trust_tier computed after gate

The gate check at `passes_active_gate()` line 3627 reads `trust_tier` from the pick dict. But `trust_tier` is stamped at line 12375 in the leaderboard loop **before** the gate call at line 13447. For active picks, the sequence is correct. The issue is that `passes_active_gate` is never called at all for closed picks.

### Evidence against (C) — per-source override

No per-source override exists in the gate code. `BLOCKED_SOURCE_SYSTEMS` at line 4084 correctly blocks stocks_competition for active picks. The bypass is not an override — it's an omission.

### Evidence against (D) — purely historical

51 BANNED picks were closed after 2026-04-28 (yesterday). The emitters are running today. This is an active leak.

---

## Concrete Next-Action Recommendation

**Add a BANNED-tier filter to `_build_recent_closed_picks()` in `audit_trail/dashboard_generator.py`.**

Specific change: in `_build_recent_closed_picks()` (line 5319), before or inside the final `ordered` sort, filter out picks whose `source_system` is in `BLOCKED_SOURCE_SYSTEMS` (imported from `quality_gates.py`). This is a single-line filter that mirrors what `passes_active_gate()` already does for active picks.

```python
# Proposed addition at top of _build_recent_closed_picks(), after line 5333:
from audit_trail.quality_gates import BLOCKED_SOURCE_SYSTEMS
ordered = [p for p in ordered
           if str(p.get("source_system") or "").lower() not in BLOCKED_SOURCE_SYSTEMS]
```

Alternatively (stronger): apply `get_tier(source_system) != "BANNED"` to also catch sources like `multi_asset` and `rapid_fire` that are BANNED via the trust registry but not in `BLOCKED_SOURCE_SYSTEMS`.

**Secondary fix**: stop the emitters. `STOCKS/competition/forward_picks.json` was last modified 2026-04-24 and continues generating OPEN picks. If the competition runner still feeds it, it should be gated at the source.

---

## Estimated Impact

- **362 BANNED picks** currently pollute `recent_closed` (10.3% of the 3,500-entry window).
- BANNED picks have **PF = 0.880** (45.3% WR, gross win 496.2%, gross loss 564.0%) vs non-BANNED PF = 1.301 (46.1% WR).
- Removing BANNED picks would raise the visible closed-window PF from ~1.17 (blended) to **1.301** — a material improvement to reported edge.
- This is an **active leak**: rapid_fire is generating picks today; stocks_competition generated picks as recently as 2026-04-24.
- No active BANNED picks are currently displayed (active gate works). The damage is confined to closed-pick analytics, PF/WR leaderboards, and forward-validation stats that draw from `recent_closed`.

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Removing BANNED closed picks changes audit trail history — old PF numbers won't match | Medium | Document the change; it improves accuracy, not corrupts it |
| `BLOCKED_SOURCE_SYSTEMS` and trust-registry BANNED sets may diverge (rapid_fire is trust-BANNED but not in BLOCKED_SOURCE_SYSTEMS) | Medium | Filter on both: `get_tier(source) == "BANNED"` covers both paths |
| Filtering closed picks may hide performance context needed for the mutation/investigation pipeline | Low | The `all_closed_including_expired` list (separate variable) is unaffected and available for research |
| Stocks_competition emitter still running — fix to closed ingest doesn't stop future generation | High | Also gate the emitter or remove the competition runner cron; closing ingest fix alone is insufficient long-term |
