# Silent Failure Investigation: claude_gainer_st & kimi_riseoftheclaw

**Date:** 2026-04-29
**Investigator:** Claude (read-only)
**Source claim:** Round 2 4-AI panel — "claude_gainer_st emitted 0 picks since 2026-04-25, kimi_riseoftheclaw 16 vs 285 historical, both silent failures, SEV-1."
**Verdict:** **Mis-attributed root cause.** The emitters are healthy. The panel measured the wrong layer.

---

## TL;DR

### claude_gainer_st (CGS)
- **Cron is healthy.** `claude-gainer-short-term.yml` runs every 30 min on `:07/:37`, last 5 schedule runs all `success`. Most recent: `2026-04-29T15:48 UTC`.
- **Picks ARE being emitted.** `claude_gainer_ml/tracker/short_term_active.json` last commit `2026-04-29T16:03 UTC` with 12 fresh picks (scan_time `2026-04-29 16:02:25`). `short_term_closed.json` has **2,000 picks** with `321 resolved since 2026-04-25` and latest scan `2026-04-29 13:59`.
- **Picks are silently dropping inside the dashboard cap, not at the emitter.** Of those 321 recent CGS resolved picks, **only 0 appear in dashboard `recent_closed`** because they get crowded out of the `MAX_CLOSED_PICKS=3500` cap by the reservation logic in `_build_recent_closed_picks` (`audit_trail/dashboard_generator.py:5220`).

### kimi_riseoftheclaw (KIMI)
- **Cron is healthy.** `kimi-feb172026-live.yml` runs every 2h, last 5 runs all `success`.
- **Active picks present but lean.** `KIMI_RISEOFTHECLAW/data/active_picks.json` `lastUpdated 2026-04-29T15:18`, only **10 active picks** (3 EQUITY/ETF + 7 crypto including SAND/BNB/SOL/AVAX/LINK/NEAR/DOGE).
- **Real degradation, but partial.** `riseoftheclaw/data/signal_tracking.json` shows **41 WIN/LOSS signals since 2026-04-25** (vs ~285 historical baseline) — a ~50% drop, not 100%. Of those, 26 land in the dashboard. So `kimi_riseoftheclaw` is partially silent: the production rate dropped, plus the dashboard cap is also clipping recent rows.

---

## Last Successful Run Timestamps

| Source | Cron Last Run (workflow) | Active File mtime | Closed File latest resolved_at | Dashboard last `closed_at` |
| --- | --- | --- | --- | --- |
| `claude_gainer_st` | 2026-04-29T15:48 UTC (success) | 2026-04-29T16:03 UTC | 2026-04-29T16:03 UTC | **2026-04-21T09:23** |
| `kimi_riseoftheclaw` | 2026-04-29T14:43 UTC (success) | 2026-04-29T15:18 UTC | 2026-04-29T10:20 UTC (signal_tracking exit_time) | 2026-04-29T14:18 UTC |

CGS is the dramatic one — the data file is fresh through 16:03 UTC but the dashboard's most recent CGS row is **8 days behind**.

---

## Root Cause Diagnosis

### claude_gainer_st: **(F) Other** — *Dashboard cap/reservation crowd-out, not source failure*

The emitter, cron, file write, and dashboard load path are all correct. The bug is in `_build_recent_closed_picks` (`audit_trail/dashboard_generator.py:5220-5328`):

1. `MAX_CLOSED_PICKS = 3500` (line 148).
2. `RESERVED_NON_CRYPTO_CLOSED_PICKS = 2000` (line 150) — fills first, with per-class quotas across FOREX/EQUITY/COMMODITY/ETF/FUTURES/BOND. CGS is 100% CRYPTO so qualifies for **zero** of these slots.
3. `RESERVED_TRACK_RECORD_CLOSED_PICKS = 500` (line 149) — reserved for `_TRACK_RECORD_CLOSED_SOURCES` (`copy_trader_intel`, `multi_asset_copytrader`, `cta_replicator`, prediction-market sources) plus anything that passes `_is_verified_alpha_pick`.
4. CGS *does* pass `_is_verified_alpha_pick` via the `_REALIZED_ALPHA_SOURCES` whitelist at line 4984 — so technically eligible for the 500 slots — **but iteration is timestamp DESC**, and `multi_asset_copytrader` (1067 verified-alpha picks) plus `alpha_engine` (498 picks) saturate the 500-slot cap with their newer rows before CGS gets in.
5. The remaining ~1000 "most recent" residual slots compete on raw timestamp DESC. Recent crypto from `alpha_engine` (392), `super_signals` (119), `luxalgo_filters` (99), `baby_strats_forward` (98), `rapid_fire` (87) win those slots. CGS picks since 2026-04-25 are timestamp-comparable but lose head-to-head.

Net effect: CGS contributes 2,000 closed picks to the input, but only **28 survive the 3,500-cap stratified sampler**. All 28 are old (Apr 19–21 timestamps) and were preserved only because they happened to land before the heavy emitters started crowding the residual.

This is the same pattern called out in `feedback_dashboard_data_local_staleness.md` — but applied to a different downstream layer (cap exclusion vs. branch staleness).

### kimi_riseoftheclaw: **(B) Data source upstream + (F) cap clipping**

Two-part cause, both real:

1. **Upstream KIMI is producing fewer signals.** `signal_tracking.json` summary shows `total_signals=1056`, lifetime WR `12.7%`, `total_pnl=-536.99%` — the system is in a regime collapse the way the panel suggested. The active list has only 10 picks, way below historical baseline (typical was 30–60). Volume genuinely is down.
2. **Same dashboard cap clipping** as CGS — KIMI is partially saved by `_VERIFIED_ALPHA_COPY_SOURCES`-adjacent rules (it's not in that set, but its non-crypto picks (171 EQUITY + 69 ETF) qualify for the 2,000 NC reservation), so it isn't 100% wiped.

Of 41 KIMI WIN/LOSS resolutions since 2026-04-25 in `signal_tracking.json`, 26 made it into `dashboard_data.json`. ~15 lost to cap.

---

## Recommended Fixes

### Fix 1 (HIGH PRIORITY — restores CGS visibility): Add `claude_gainer_st` to `_VERIFIED_ALPHA_COPY_SOURCES`

**File:** `audit_trail/dashboard_generator.py:4630`
**Change:** Add `"claude_gainer_st"` to the set. CGS already has the realized track record (540 closed, 63.0% WR, +248% cum per the comment block at line 4980). This forces every CGS pick into the 500-slot track-record reservation, where iteration is per-source-aware enough to prevent multi_asset_copytrader from monopolizing.

**Even stronger:** Add a per-source reservation floor (e.g., guarantee at least 100 slots to any source in `_REALIZED_ALPHA_SOURCES`) so a high-volume verified source can't crowd out a lower-volume one.

### Fix 2 (MEDIUM): Rename the panel's misdiagnosis in `reports/ai_round2_synthesis_2026_04_29.md`

The "0 picks emitted since 2026-04-25" claim was measured by counting `claude_gainer_st` rows in `dashboard_data.json` `picks.recent_closed`. That measurement crosses the cap-stratification layer. Future panels should directly count `claude_gainer_ml/tracker/short_term_closed.json` rows by `resolved_at`. (Recommended: add a cross-check helper at `tools/source_emission_audit.py` that loads the raw source files, not the dashboard payload.)

### Fix 3 (LOW — for KIMI specifically): Investigate KIMI signal generation drop

KIMI emission rate genuinely dropped (~50% week-over-week per signal_tracking summary). Separate investigation needed into `KIMI_FEB172026/live_scanner.py` regime/threshold logic — but this is a strategy/regime issue, not a wiring issue. The panel's "auto-halt CRYPTO until kimi re-emits" recommendation is appropriate IF the SEV-1 framing is downgraded to "regime watch."

### Fix 4 (P0 watchdog from panel verdict): Source-liveness watchdog

The panel's recommendation for a `>70% volume drop watchdog` is still valid even after this diagnosis — but it MUST measure at the source-file layer (`short_term_closed.json` mtime + row count by date), not the dashboard layer, or it will keep producing false-positive SEV-1s like this one.

---

## Estimated Recovery After Fix 1

If `claude_gainer_st` lands in `_VERIFIED_ALPHA_COPY_SOURCES`, the next dashboard generation cycle should restore approximately:
- **~150–250 CGS picks/week visible** in `recent_closed` (matching scan rate of ~60/day × 7 days minus dedup).
- **CGS asset-class WR/PF charts will populate** (currently empty for the recent window).
- **HIGH_CONVICTION/strong-take cohort math will re-enable CGS contribution** (the 540-closed/63-WR realized alpha).

The KIMI fix has lower impact — only ~15 additional picks would have been retained per week from cap-clip. The bulk of KIMI's degradation is upstream regime issue, not wiring.

---

## Cross-References

- `audit_trail/dashboard_generator.py:148` — `MAX_CLOSED_PICKS=3500`
- `audit_trail/dashboard_generator.py:4630` — `_VERIFIED_ALPHA_COPY_SOURCES` (the fix target)
- `audit_trail/dashboard_generator.py:4984` — `_REALIZED_ALPHA_SOURCES` (already lists CGS — but it's downstream of the iteration order)
- `audit_trail/dashboard_generator.py:5220` — `_build_recent_closed_picks` (cap stratification)
- `audit_trail/dashboard_generator.py:3538-3541` — CGS source registration (correct)
- `claude_gainer_ml/tracker/short_term_closed.json` — 2,000 closed picks, 321 resolved since 2026-04-25
- `KIMI_RISEOFTHECLAW/data/active_picks.json` — 10 active, healthy emit
- `riseoftheclaw/data/signal_tracking.json` — 41 closed since 2026-04-25, 1056 total
- `reports/ai_round2_synthesis_2026_04_29.md:60` — original panel claim (mis-diagnosed root cause)
- `feedback_dashboard_data_local_staleness.md` — adjacent class of bug

---

## Methodology Note for Future Audits

Counting `source_system` cardinality in `dashboard_data.json` `picks.recent_closed` is **not** a measure of source emission rate. The 3,500-pick cap with reservation logic is a stratified, lossy projection. Always cross-check against the underlying source data file before claiming a silent failure. A 5-min check on the raw `short_term_closed.json` would have caught this before the panel fired SEV-1.
