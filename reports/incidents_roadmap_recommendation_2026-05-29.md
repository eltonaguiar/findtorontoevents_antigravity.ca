# Incidents → Enhancement/Fixes Roadmap — recommendation (2026-05-29)

**Question (user):** does `incidents.html` have a timeframe, and what's the best way to stand up an enhancement/fixes roadmap?

## What already exists (don't rebuild)
- **Timeframe field is live.** `tools/audit_pick_funnel/cli_track.py` accepts `--target-release` on both incident + enhancement commands (commit `f4ab89a8f`), and `render_incidents_page.py::target_badge()` (lines 64-89) renders it as an EST-dated pill with traffic-light status: **OVERDUE Nd** (red), **due in ≤3d** (amber), **in ≤7d** (yellow), **in Nd** (green).
- **EST timestamps are live.** `created_est()` (lines 92-104) converts the DB's naive-UTC `created_at` to America/New_York for display (commit `43e1cb5fa`).
- Schema: `tools/ai_tournament/migrations/202605250400_incident_enhancement_per_class.sql` has per-class `INCIDENT_*` / `ENHANCEMENT_*` tables with `severity/status/target_release/expected_impact/effort/category`.

**So the roadmap is 90% built — the missing 10% is that `target_release` is NULL on essentially every existing row, so the badges render "—" and there is no actual schedule.**

## Recommended approach (lowest-effort path to a real roadmap)

1. **Backfill `target_release` via a triage policy, not by hand.** Use the existing `cli_track --target-release` so it stays auditable. Suggested SLA mapping (dates in EST):
   - Incidents: **P0 → +2 days, P1 → +7d, P2 → +21d, P3 → +60d**.
   - Enhancements: **HIGH impact → +14d, MEDIUM → +45d, LOW → +90d**, nudged by effort (XL adds 50%).
   This is a **DB write** → owned by the operator / the incidents agent; do NOT auto-run from a read-only session. A one-shot `tools/audit_pick_funnel/backfill_target_release.py --policy sla --dry-run` that prints the proposed dates first is the safe shape.

2. **Add a grouped "Roadmap" view** to `render_incidents_page.py` that buckets *open* items (`status in OPEN/TRIAGED/IN_PROGRESS` and `BACKLOG/VALIDATED/ACCEPTED`) by target window: **Overdue · This week · Next week · This month · Later · Unscheduled**, sorted by severity/impact within each bucket. All data already loaded in `load()` (lines 45-47); this is a pure presentation add — no new query. Render-only; the nightly `incidents` job publishes it (never run the generator locally).

3. **Make "Unscheduled" loud.** Any open P0/P1 with `target_release IS NULL` should show a red "UNSCHEDULED" chip — that's the backlog-rot signal. This turns the roadmap into a forcing function instead of a passive list.

4. **Tie it to Goal #1.** Tag each roadmap item with the asset class it advances (the per-class tables already exist) so the roadmap reads as "what unblocks CRYPTO/EQUITY/etc. to Tier 2," not generic tickets.

## Highest-priority items that should get a `target_release` first
From the plan-MD review (`reports/` + CLAUDE.md), the P0s that gate everything:
1. Unfreeze the forward-validator + drain the OPEN backlog (blocks every per-class metric).
2. Enforce the concentration gate **before** DSR/SPA (removes false-Tier-1 passes).
3. Fix the EXPIRED→WON resolver mislabel + dedup ghost rows (restores honest PF/WR).
4. **NEW (this session):** validate the Cycle 13-17 "6/6 proven edge" strategies OUT-OF-SAMPLE before they keep sizing — they were wired to production on in-sample/synthetic backtests while live data says 0/6 ready (see broadcast 2026-05-29).

## Bottom line
No new infrastructure needed. The roadmap = (a) a policy-driven `target_release` backfill [DB write, operator-owned] + (b) a ~40-line grouped render view + (c) a loud "UNSCHEDULED P0/P1" chip. Steps (b)/(c) are safe code-only changes; step (a) is the one that needs a human/owning-agent because it writes the DB.
