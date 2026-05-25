# Incidents + Enhancements Triage Process

**Status:** v1 draft, 2026-05-25
**Owner:** any agent picking up the `/audit/incidents.html` backlog
**Source of truth:** `audit_dashboard/data/incidents_enhancements_feed.json` (generated nightly from MySQL `INCIDENT_*` / `ENHANCEMENT_*` tables in `ejaguiar1_stocks`)
**Live page:** https://findtorontoevents.ca/audit/incidents.html

This document standardizes how we work the incident + enhancement backlog so the page stops being a write-only graveyard.

---

## 1. Current snapshot (2026-05-25 05:16 UTC)

- **Incidents:** 38 total — 18 P0, 12 P1, 5 P2, 3 P3
- **Status:** 33 OPEN, 4 TRIAGED, 1 RESOLVED
- **Asset class buckets:** OVERALL 19, CRYPTO 4, STOCKS 3, FOREX 3, COMMODITIES 3, BONDS 2, PENNY 2, ETFS 1, FUTURES 1
- **Enhancements:** 38 total — all BACKLOG, none assigned. 25 HIGH-impact, 13 MEDIUM. Effort: 8 S, 21 M, 8 L, 1 XL.
- **Quick wins (HIGH impact + S effort):** 5 — enhancement IDs 1, 2, 5, 8, 23.
- **Oldest "row age":** all ~1.6h, because the seed script re-INSERTs on every nightly run. This is a *bug, not a feature* — see §6 "known limitations of the current pipeline."
- **Reporter field NULL on 100% of JSON rows** — the seed script *has* `reporter` but `render_incidents_page.py` is not surfacing it into the sidecar JSON. Small bug to file.

### Top 10 by priority (P0, then created_at)
| # | id | class | status | title |
|---|----|-------|--------|-------|
| 1 | 1 | OVERALL | OPEN | trust_score NULL on 99.99% of closed picks |
| 2 | 2 | OVERALL | OPEN | 5 FOREX rows have pnl_pct < -100% (one at -106,700%) |
| 3 | 3 | OVERALL | OPEN | signal_outcomes table 82 days stale |
| 4 | 5 | OVERALL | OPEN | COT paper pilot over-emission (inflates SUPREME EDGE) |
| 5 | 6 | OVERALL | TRIAGED | ML calibration system-wide inverted |
| 6 | 8 | OVERALL | OPEN | smart_picks.json file 25 days stale |
| 7 | 1 (STOCKS) | STOCKS | OPEN | PEAD equity stuck in shadow mode |
| 8 | 10 | OVERALL | OPEN | PnL integrity mismatch on 38.97% of sampled closed picks |
| 9 | 11 | OVERALL | OPEN | WON status rows show avg pnl_pct = -41.1% |
| 10 | 12 | OVERALL | OPEN | 56,559 ghost rows in trading_picks (MATICUSDT cohort) |

Other P0s worth naming: forward_validator frozen 270h with 29.2M open rows; SUPREME EDGE cherry-picking caveat missing; smart_picks_engine confidence weighting structurally inverts the ranker.

---

## 2. Stale / mis-categorized / duplicate findings

- **No exact-title duplicates** in the current 38-row set, BUT thematically these cluster into 3 root causes that should be linked via `duplicate_of`:
  - **Resolver pipeline dead** — items #3 (signal_outcomes 82d stale), #6 (smart_picks.json 25d stale), #8 (forward_validator frozen 270h), and ID#3 in COMMODITIES (29.2M open positions). Single broken cron / dead process is plausibly responsible for all four.
  - **trading_picks data integrity** — items #1 (trust_score NULL), #2 (pnl<-100% clamp bypass), #10 (PnL mismatch 38.97%), #11 (WON labeling bug), #12 (ghost rows). One backfill+CHECK constraint sprint addresses all five.
  - **Confidence-derived ranking inverted** — items #6 (ML calibration inverted) and the per-class smart_picks_engine weighting incident. Same fix.
- **Mis-categorized:** item #4 (Top-N Rank tool 1045 access denied) is marked RESOLVED but never moved out of OVERALL — fine to leave, but counts against the OPEN backlog visually until it's filtered out.
- **Reporter field discrepancy:** seed has it, JSON sidecar drops it. Loss of provenance.
- **No `age_hours` field** in the JSON because seed re-INSERTS rows every nightly run (see §6).

---

## 3. The triage process

### 3.1 Triggers
- **Cron:** nightly 04:35 UTC — runs immediately after `incidents-enhancements-nightly.yml` (04:30 UTC) so the triage pass sees fresh data.
- **Weekly stale-sweep:** Sundays 12:00 UTC — escalates any P0 OPEN for >7 days, surfaces "should this be RESOLVED-as-WONTFIX?" candidates.
- **Manual:** `gh workflow run incidents-triage.yml -f incident_id=<id>` to target one.

### 3.2 Inputs
- `audit_dashboard/data/incidents_enhancements_feed.json` (canonical backlog)
- `audit_dashboard/data/db_health.json` (evidence for integrity-class incidents)
- Recent `reports/*.md` linked from each row's `link_md_path`
- `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` (for per-class regression checks after a fix)

### 3.3 Roles (one engine per stage, deliberately separated)
| Stage | Default engine | Output |
|-------|---------------|--------|
| CLAIM | Claude Opus 4.7 | Picks next P0 (oldest OPEN, no `assigned_to`). Updates row: `status=TRIAGED`, `assigned_to=<engine>`, `updated_at=NOW()`. |
| INVESTIGATE | grok (fast) or codex (deep) | Writes `reports/triage/INCIDENT_<id>_<slug>.md` with: reproducer, evidence (SQL/log lines), root-cause hypothesis, blast-radius. |
| PROPOSE-FIX | codex or claude | Either (a) one-shot SQL/code patch + rollback plan + success metric, OR (b) `## Wiring Plan` per the project's Wire-Up Rule when a new module is needed. NEVER commits without VERIFY. |
| VERIFY | a *different* engine from PROPOSE-FIX | Re-runs the success metric on a staging snapshot. On pass, opens PR + sets row to `RESOLVED` with `resolution_notes` + `resolved_at`. On fail, kicks back to INVESTIGATE with a counterexample. |

Why separation: the audit/calibration incidents themselves were caught precisely because multiple engines disagreed. Single-engine triage will re-introduce the same blind spots.

### 3.4 Exit criteria
A row may be set to `RESOLVED` only when ALL of:
1. Success metric in PROPOSE-FIX is reproducible by VERIFY engine on a fresh DB snapshot.
2. A linked PR (or SQL migration) is merged AND deployed (FTP for audit page; cron-run for resolver fixes).
3. The dashboard data point that motivated the incident has flipped (e.g., trust_score NULL rate < 5%; signal_outcomes max(resolved_at) within 48h; etc.).

Or to `WONTFIX` when:
- Cross-engine consensus says the cost of fixing exceeds the cost of disclaiming on the UI, AND the disclaimer is shipped.

### 3.5 Integration with the existing nightly workflow

The current `incidents-enhancements-nightly.yml` does seed → render → FTP-upload. It needs two surgical changes to support triage:

1. **Seed becomes append-only for triage state.** Change `seed_incidents_enhancements.py` so the `ON DUPLICATE KEY UPDATE` clause only touches `description`, `recommended_fix`, `updated_at` — never `status`, `assigned_to`, `resolution_notes`, `resolved_at`. Today, an engine that marks #1 TRIAGED loses that state on the next nightly run.
2. **Add an `incidents-triage.yml` workflow** that runs at 04:35 UTC. It:
   - reads the fresh JSON
   - emits the regression diff (any P0 that flipped RESOLVED→OPEN, any new P0)
   - posts the diff to the cross-PC bus AND to a `reports/triage/DAILY_<date>.md` card
   - kicks the CLAIM stage for the top OPEN P0 if no agent has been assigned in the last 24h.
3. **Render the TRIAGE DASHBOARD strip** at the top of `incidents.html`: counts of P0 OPEN / TRIAGED / RESOLVED-this-week, oldest OPEN age, top-3 unassigned. Cheap to add to `render_incidents_page.py`.

---

## 4. Investigation plans for 3 highest-priority items

### 4.1 Incident #3 — signal_outcomes table 82 days stale (resolver dead)
**Why this first:** every forward-WR claim on the dashboard sits downstream of this table. Fixing #1 (trust_score) without fixing #3 means HC overlay shows live counts on stale outcomes.

**Check (do not fix yet):**
- `SELECT MAX(resolved_at), COUNT(*) FROM at_signal_outcomes;` — confirm 2026-03-04 is still the high-water mark.
- `git log --since=2026-02-25 --until=2026-03-10 -- alpha_engine/outcome_resolver.py alpha_engine/forward_validator.py` — look for a deploy that coincides with the resolver going silent.
- `ls -lt logs/` — find the most recent outcome-resolver log; tail for the last successful write and the first error.
- `crontab -l` on whichever host owns the resolver (or check `.github/workflows/*resolver*.yml`) — confirm the cron is actually firing.
- Check whether `DB_PASS_STOCKS` rotated around 2026-03-04 (same root cause as RESOLVED incident #4).
- DB-credential location: per `memory/db-credential-location.md`.

**Tables / files relevant:** `at_signal_outcomes`, `trading_picks` (source rows), `alpha_engine/outcome_resolver.py`, `alpha_engine/forward_validator.py`, `.github/workflows/forward-validator-*.yml` (if exists).

### 4.2 Incident #1 — trust_score NULL on 99.99% of closed picks
**Why next:** unblocks the High-Conviction overlay AND directly invalidates the cited "CRYPTO 60.3% N=562 / EQUITY 68.1% N=72" headline. Cheap to verify scope.

**Check:**
- `SELECT COUNT(*), COUNT(trust_score) FROM trading_picks WHERE status IN ('TP_HIT','SL_HIT','LOST','WON','EXPIRED');` — confirm the 38,884 / 38,889 ratio.
- `grep -rn "trust_score" alpha_engine/ tools/ audit_trail/ | head -50` — find every writer; identify which path is supposed to populate it.
- `audit_dashboard/hc_filter.js` — read the HC threshold gate and figure out which field is *populated* and could serve as the gate without a backfill (likely `elite_score` per the seed note).
- Decide between (a) backfill from strategy registry, (b) repoint gate to `elite_score`, (c) ship UNVERIFIABLE banner. Multi-engine vote.

**Tables / files:** `trading_picks.trust_score`, `audit_dashboard/hc_filter.js`, `audit_dashboard/template.html` (HC overlay section), strategy registry (likely `alpha_engine/strategy_registry.py` or similar).

### 4.3 Incident #5 — COT paper pilot over-emission (inflates SUPREME EDGE)
**Why third:** the dashboard's headline SUPREME EDGE (DSR=1.0 / WR 86.5%) is the single most visible claim on `/audit`. If it's a duplicate-counting artifact, it's actively misleading anyone sizing real money. Confirmed by 3 engines.

**Check:**
- `cot_paper_pilot.py` — find the loop that emits picks. Count distinct CFTC release timestamps vs total emitted rows.
- `SELECT DATE(created_at), COUNT(*) FROM trading_picks WHERE strategy='cot_positioning' GROUP BY DATE(created_at) ORDER BY 1;` — should show ~1 release/week; bug case will show ~100/day.
- Recompute DSR/WR/PF on the deduped set (group by ISO week of CFTC release).
- Cross-check with the SUPREME EDGE callout block in `audit_dashboard/template.html` — does the page already cite n? If n is small post-dedup, the SUPREME EDGE classification may not survive.

**Tables / files:** `cot_paper_pilot.py`, `trading_picks` (filtered by `strategy='cot_positioning'`), `audit_dashboard/template.html` SUPREME EDGE block, `audit_dashboard/data/top_edges_per_class.json`.

---

## 5. External-AI second opinions

See:
- `reports/2026-05-25_incidents_triage_consult_codex.md`
- `reports/2026-05-25_incidents_triage_consult_grok.md`
- `reports/2026-05-25_incidents_triage_consult_gemini.md`

Synthesis below.

---

## 6. Known limitations of the current pipeline (must-fix to enable triage)

1. **Seed re-INSERTS every night** with `ON DUPLICATE KEY UPDATE` touching status fields. Any human/agent edit is silently overwritten. Make seed append-only for status/assigned_to/resolution.
2. **No real `age_hours`.** Every row appears 1.6h old. Either: (a) preserve original `created_at` via ON DUPLICATE KEY UPDATE that excludes `created_at`, or (b) track first-seen separately.
3. **`reporter` is in the seed but not the JSON sidecar.** Fix `render_incidents_page.py` to include it.
4. **No `assigned_to` ever populated.** Add a small CLI in `tools/audit_pick_funnel/` to set/clear assignments without touching the seed.
5. **No diff-tracking between nightly snapshots.** Add the regression-diff job in §3.5.

---

## 7. Final recommended action list (synthesis of consults + own analysis)

### What the three engines agreed on
- **The 4-stage process is the right shape but too heavy for a 38-row backlog.** All three said: keep it, but thin it. Grok: "the high-value pieces — append-only seed, post-render P0 regression diff, TRIAGE DASHBOARD — should land immediately; the rest can wait until volume justifies ceremony." Codex: collapse stages but keep persistent `status / assignee / first_seen_at / resolved_at / success_metric`. Gemini: collapse CLAIM into INVESTIGATE.
- **The biggest unstated risk is that the entire performance universe is corrupted.** Grok: "the 'Tier 2 candidate' numbers and money-ready decisions are untrustworthy no matter how pretty the UI." Codex: "you may be measuring a corrupted universe." Gemini: "if you can't trust the WON/LOST label, no amount of AI triage on the dashboard will save the project."
- **Append-only seed is non-negotiable.** Codex and Gemini both volunteered the same fix: derive a deterministic `finding_key` (asset_class + issue_type + normalized title hash), `ON DUPLICATE KEY UPDATE` only `updated_at` + evidence fields, and add a REGRESSED status so a resolved P0 reappearing flips state instead of cloning a row.

### Where the engines disagreed with my initial Top-10 ranking
My initial intuition was to push **#1 trust_score NULL** to the top because it blocks the HC overlay. The consults flipped this:

- **Grok** put **#5 (ML calibration inverted)** first because it's "the single largest 'garbage signal at the top of the funnel' problem — it actively ranks every downstream pick." Trust_score is second.
- **Codex** put the **liveness/integrity spine** first: `signal_outcomes` stale → forward_validator frozen → smart_picks.json stale → PnL integrity → WON labeling → trust_score → COT → ML inversion. The argument: "before optimizing strategies, protect the audit pipeline from garbage-in confidence."
- **Gemini** went hardest on the inversion: "#5 ML inversion is *active poison* — you are weighting a 14% WR signal at 35% in your engine. This is negative alpha. Fix this to stop the bleeding." Then #2 (PnL clamp) because "one -106,700% row makes every Average PnL and Total ROI on the site a work of fiction."

**Resolution:** all three converge on **data + math integrity before headline/narrative fixes.** trust_score NULL drops from #1 to ~#3. COT also drops because — Grok's framing — it's "reputation-risk, not operational daily damage." Only Gemini ranked the COT/SUPREME-EDGE narrative high, and only as #3.

### Final ordered action list

**Phase 0 — Make the page triage-capable (this week, ~3h)**
1. Patch `seed_incidents_enhancements.py` to (a) derive a deterministic `finding_key` hash, (b) be append-only on `status`, `assigned_to`, `resolution_notes`, `resolved_at`, `first_seen_at`, and (c) flip resolved → `REGRESSED` (new status value) instead of cloning a row when the same `finding_key` re-emerges.
2. Patch `render_incidents_page.py` to surface `reporter`, real `age_hours` derived from `first_seen_at`, and a top-of-page TRIAGE DASHBOARD strip (P0 OPEN / P0 TRIAGED / RESOLVED-this-week / oldest OPEN age / top 3 unassigned).
3. Add a post-render diff job that alerts only on P0/P1 status flips and age>7d (Gemini: "don't alert on P3 to keep S/N high").
4. Skip the `[skip ci]` commit on no-op nights (Grok suggestion — cuts noise).
5. Add `duplicate_of` links: resolver-dead cluster (#3, #6, #8, COMMODITIES#3) and integrity cluster (#1, #2, #10, #11, #12).

**Phase 1 — Stop the bleeding (next 1-2 sessions) — reordered per consults**
1. **#5 — Invert the confidence contribution in `smart_picks_engine`** (or repoint to `trust_score`/`elite_score`). Gemini: "stop the bleeding." Grok concurs as highest priority. Validate with paired-bucket test on closed picks.
2. **#2 — One-line FOREX clamp backfill**: `UPDATE trading_picks SET pnl_pct=-100 WHERE pnl_pct<-100 AND category='FOREX'`. Then add a CHECK constraint. Gemini: this single fix makes every site-wide ROI figure honest.
3. **#3 — Restart the resolver / unfreeze forward_validator**. Codex put this at #1 of integrity spine; it unblocks every downstream forward-WR claim including verification of every other fix.
4. **#1 — trust_score** path decision (backfill vs repoint vs disclaim). Multi-engine vote.
5. **#4 — COT dedup + add SUPREME EDGE caveat banner** on the page (incident #16 is the banner; #5/COT is the underlying dedup). The banner is cheap and earns immediate credibility back even before the dedup ships.

**Phase 2 — Integrity sprint (next week)**
- Single-PR backfill addressing #10 (PnL mismatch), #11 (WON labeling), #12 (ghost rows), plus CHECK constraints to prevent recurrence. Gemini: "the core state machine is decoupled from reality" — this is the highest-stakes work.
- Investigate the writer emitting the 20,474 identical MATICUSDT rows. Until that writer is found, dedup is a band-aid.

**Phase 3 — Process bedding-in**
- Stand up `incidents-triage.yml` at 04:35 UTC (post-seed).
- Run CLAIM/INVESTIGATE/PROPOSE/VERIFY across at least 2 engines so single-engine blind spots are caught — but follow Codex/Gemini's advice and collapse to one artifact per stage, one row update per stage, no separate `reports/triage/` doc unless the incident is P0.
- HITL gate on PROPOSE-FIX → VERIFY transition for anything touching production DB rows (Gemini's hard requirement).
- Add auto-resolution: if the nightly auditor re-runs and the condition (e.g., signal_outcomes stale > 7d) is no longer true, flip `status=RESOLVED` automatically (Gemini suggestion). This means the seed becomes the truth, not the agent.
- Review WONTFIX:RESOLVED ratio after 2 weeks; if WONTFIX > 30%, raise the bar for what gets seeded as P0.

---

## Consult appendix

Engines used (all returned in <60s):
- **grok** (`~/.grok/bin/grok -p`) — 3.0KB reply
- **codex** (`~/.hermes/node/bin/codex exec`) — 9.4KB reply (note: codex's bubblewrap sandbox blocked its own file reads — `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` — so it answered from the prompt alone; still produced the cleanest framework recommendations)
- **gemini** (`~/.hermes/node/bin/gemini -p`) — 3.0KB reply

Full replies: `reports/2026-05-25_incidents_triage_consult_{grok,codex,gemini}.md`.
