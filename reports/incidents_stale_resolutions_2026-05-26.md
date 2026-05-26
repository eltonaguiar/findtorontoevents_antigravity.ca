# Incident triage — 4 stale P0/P1 incidents verified resolved-in-fact

**Date:** 2026-05-26
**Triaged by:** claude-opus-4-7-desktop + 4 parallel subagent investigations
**Source:** findtorontoevents.ca/audit/incidents.html (rendered by `incidents-enhancements-nightly.yml`)

The incidents-feed pipeline keeps re-emitting 4 entries that are already fixed in code or were never live in the first place. Each is verified resolved with evidence below. The fixes already shipped; only the incident card needs retirement.

## INC #3 — sync_active_mysql_picks_to_json upstream writer missing

**Original claim (P0, OPEN):** "Root cause of 0.09% raw-pick outcome coverage. Proposed: new module `alpha_engine/active_picks_sync.py` invoked inline."
**Reporter:** opencode/ring-2.6-1t

**Verified resolved 2026-05-12:**
- File exists: `alpha_engine/active_picks_sync.py` (574 lines, full implementation matching incident spec)
- Tests exist: `tests/test_active_picks_sync.py` (264 lines)
- Design doc: `reports/active_picks_sync_pr2_design_2026-05-12.md`
- **Wired into production**: `.github/workflows/audit-dashboard.yml` "Active picks sync (LIVE)" step loops all 7 asset classes with `--apply` before resolver runs
- Manual override: `.github/workflows/resolver-step7-apply.yml` with `confirm == 'APPLY-SYNC'` gate
- Last 3 scheduled `audit-dashboard.yml` runs: `success`

**Action:** Close the incident. If raw-pick coverage is still flagged 0.09%, the real issue is downstream (coverage calculator) — NOT a missing writer.

## INC #11 — COT paper pilot over-emission

**Original claim (P0, OPEN):** "cot_paper_pilot.py counts the same signal multiple times across the CFTC release week. Recommended: deduplicate by CFTC release week."
**Reporter:** ring-2.6-1t

**Verified resolved 2026-05-13:**
- `alpha_engine/strategies/cot_paper_pilot.py:155-186` implements `dedupe_by_release_week()` (snaps entry date back to the most recent Tuesday, returns ISO year-week)
- `compute_paper_pnl` (line 200-204) calls `dedupe_by_release_week(raw_closed)` before counting wins/PF
- `gate_tier_and_dsr()` (line 294-338) withholds DSR and forces `SHADOW_INSUFFICIENT_N` when deduped `n < 20`
- Output JSON exposes `over_emission_ratio` for monitoring
- Wired in `.github/workflows/audit-dashboard.yml:270` runs the deduped pipeline every audit-dashboard cycle
- Falsification report: `reports/cot_paper_pilot_overemission_falsified_20260513.md`

**Action:** Close the incident.

## INC #13 — smart_picks.json 25 days stale

**Original claim (P0, OPEN):** "data/smart_picks.json last updated 2026-04-30. Recommended: re-run smart_picks_engine.py and wire to a daily cron."
**Reporter:** ring-2.6-1t

**Verdict: FALSE ALARM — wrong file path checked.**

The incident's stated path `data/smart_picks.json` does not exist. The real file lives at `alpha_engine/data/smart_picks.json` and was last updated 2026-05-25 20:29 UTC (~4 hours before triage). It is regenerated **hourly** by `.github/workflows/smart-picks-tracker.yml` (cron `54 * * * *`), last 5 runs `success`. The dashboard reads `smart_picks_feed` which is even fresher.

This is the same fabrication pattern flagged in `CLAUDE.md`:
> DO NOT trust unsourced model claims about /audit numbers. Several Cloudflare-hosted models (DeepSeek R1 Distill Qwen 32B in particular) confidently invent per-class WR/PF/Sharpe numbers when asked "look at findtorontoevents.ca/audit". They have no browser/tool access and will fabricate plausible-but-wrong figures.

**Action:** Close the incident. Add a guard in the incident-seeder prompt so Ring-2.6-1T checks `alpha_engine/data/` before claiming staleness.

## INC #18 — IPO asset class advertised on /audit with zero coverage

**Original claim (P2, OPEN):** "/audit lists IPO as one of the tracked asset classes but the codebase has zero IPO-specific strategy or pick writer."
**Reporter:** opencode/ring-2.6-1t + 1/3 swarm (low-confidence flag)

**Verdict: STALE — IPO is not in the live UI.**

`audit_dashboard/template.html` asset-class list (line ~12993) contains: CRYPTO, EQUITY, FOREX, COMMODITY, BOND, ETF, FUTURES. **No IPO entry.** Direct `curl` of `https://findtorontoevents.ca/audit/` returned zero matches for IPO outside the incidents-page text itself.

**Action:** Close the incident. The incident reporter labeled this 1/3 swarm confidence which already flagged it as low-signal.

## What's actually open and being worked on

| INC | Status | Action |
|---|---|---|
| #1 SUPREME EDGE post-hoc warning | **FIXED today** | Caveat shipped in `audit_dashboard/template.html:1151` (commit a1b9d7787) |
| #10 signal_outcomes 82d stale | **FIXED today** | MySQL mirror step added to `outcome-resolver.yml` (this commit) |
| #2/#12 ML calibration inversion | Diagnostic ready | 3-line patch at `smart_picks_engine.py:105` proposed; HITL gate |
| #6/#7 ghost rows + 29M open queue | SQL drafted | Read-only triage SQL + UNIQUE KEY migration; HITL gate (DB mutation) |
| #4/#5/#8/#9 DB integrity (pnl, WON, trust, FOREX clamp) | Awaiting HITL | UPDATE SQL drafted in earlier subagent reports |
| #14 summary_picks.json identical timestamps | No in-repo writer | Externally generated; needs producer-side investigation |

## Root-cause for the stale-incidents pattern

The seeder `tools/audit_pick_funnel/cli_track.py` runs nightly and re-emits incidents from peer-AI audit transcripts. It has no de-duplication against historical resolution evidence. Recommended enhancement (not in this PR): add a `--check-resolution` flag that scans `reports/incidents_*resolved*.md` for explicit resolution receipts and suppresses re-emission for matching titles.
