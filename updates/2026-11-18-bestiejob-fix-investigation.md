# BESTIEJOB pipeline fix investigation (agents + remote main)

- **Date (UTC):** 2026-11-18
- **Investigator:** `kilo` @ `gx10-c9b9/bestiejobharvest` (worktree `bestiejobharvest`, HEAD `280e1a067c13`)
- **Scope:** verify claimed/in-progress fixes by peer agents/worktrees and reconcile with `eltonaguiar/BESTIEJOB` remote `main` CI state. No code changes pushed to `BESTIEJOB`.

## Remote `main` checked (`eltonaguiar/BESTIEJOB`)
- **HEAD:** `7851e0073844070b124d554e68374bd09519b884` — `chore(jobs): hourly scan refresh (2858 listings, 2026-11-18T02:18:33Z) [skip ci]` (github-actions[bot]).
- **Recent commits (newest):** `7851e00` hourly scan refresh; `9b06313` lessons/scan (Hermes Agent, 02:15Z); `ee61982` hourly scan refresh (01:20Z); `7d5403e` / `089ecb4` lessons + verified fresh Toronto Salesforce posting (Hermes Agent, ~01:17Z); `742611b` fresh CA sweep (01:00Z); `6c21857` hourly scan refresh (00:32Z); `292542b` lessons (00:10Z); `df66b39` hourly scan refresh (2026-11-17T23:16Z). Pattern: scan/merge/lesson churn; **no commit on `main` addressing the red gates below**.

## Latest workflow status per workflow (`main`, sampled 2026-11-18T~02:57Z)
| Workflow | Latest conclusion | When (UTC) | Run | Head SHA |
|---|---|---|---|---|
| Job Source Truth Check | **failure** | 2026-11-18T02:25:23Z | [44223129196](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44223129196) | `7851e00` |
| Gap channels (Workday / Phenom / Oracle / Job Bank / Workable) | **failure** | 2026-11-18T00:53:02Z | [44211439366](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44211439366) | `6c21857` |
| board invariants | **failure** | 2026-11-17T16:16:12Z | [44123817042](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44123817042) | — |
| Hourly Job Scan | success | 2026-11-18T02:16:09Z | [44221991122](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44221991122) | `9b06313` |
| Fresh CA sweep (today + yesterday) | success | 2026-11-18T00:45:30Z | [44210431196](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44210431196) | `6c21857` |
| Deploy GitHub Pages | success | 2026-11-18T02:37:24Z | [44224618759](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44224618759) | `7851e00` |
| agency-board-scan | success | 2026-11-17T13:24:45Z | [44092462306](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44092462306) | — |
| Daily LinkedIn sweep | success | 2026-11-17T11:21:50Z | [44073339790](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44073339790) | — |
| Scrape Jobs | success | 2026-11-17T11:23:31Z | [44073593184](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44073593184) | — |
| README job-row guard | success | 2026-11-17T16:16:12Z | [44123816896](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44123816896) | — |

## Failure evidence (remote)
1. **Job Source Truth Check** ([44223129196](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44223129196), job `truth`, step "Scan for signup-gated / paywall job links"): `python3 tools/job_source_truth.py --check` → `scanned=3 total=13616 gated=35`, lists gated rows on `theladders.com` / `jobleads.com` in canonical artifacts (README/FRESH_JOBS/jobs), **exit 1**. `main()` fails when `--check` and any gated rows exist. **Root cause:** signup/paywall URLs ingested/retained in published artifacts.
2. **Gap channels** ([44211439366](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44211439366), job `sweep`): steps through "Rebuild the feed" succeeded; **"Commit and push" failed**. Push logic is single retry (`git push || git pull --rebase --autostash origin main; git push`) under `bestiejob-main-write` contention — indicates publish/race fragility; scan/merge output was not pushed.
3. **board invariants** ([44123817042](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44123817042), job `audit`): "Audit the published board against its own rules" failed against baseline/ratchet (`reports/board_invariants_baseline.json`); report artifact uploaded. Per-class debt/threshold triage still required.

## Peer agent / worktree investigation
- **COMS (192.168.2.52:1883, up):** roster shows bestiejob seats `gx10-c9b9/bestiejobharvest-v2/kilo` (todo: handoff to v3, await owner pick of sourcing angle; done: pipeline review + 4-angle methodology) and `gx10-c9b9/bestiejobharvest-v3/kilo` (methodology/live-mix analysis done). No `bestiejobharvest-v4` seat registered. No `check`/inbox-read verb; sent messages not retained → offline receipt unprovable via COMS.
- **Local worktrees (inspected):**
  - `.../bestiejobharvest-v2` (`bestiejobharvest-v2` @ `280e1a067c13`), `.../bestiejobharvest-v3` (`38e95f3b0948`), `.../bestiejobharvest-v4` (`38e95f3b0948`): **clean working trees, trading-repo automation HEADs, no bestiejob fix commits**. Bestiejob-related files present are pre-existing `updates/2026-11-14-bestiejobs-v2/v4-*` docs only (unchanged).
  - `.../bestiejobharvest` (self): analysis/QA only; no `BESTIEJOB` code fixes applied.
- **Conclusion:** peer bestiejob seats have produced **design/analysis (uncommitted to `BESTIEJOB`)** but **no landed fixes** in inspected worktrees or on remote `main`.

## Other local fix artifacts found (not on `BESTIEJOB` remote `main`)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/updates/2026-11-18-bestiejob-truthcheck-fix.md` and companion dir `updates/2026-11-18-bestiejob-truthcheck-fix/` (patch, `jobs_merge_inbox.py`, `purge_gated_rows.py`, `gated_domains.txt`, `PAYWALL_ROLES.md`) authored `2026-11-18`, status noted as **implemented/verified in a local clone; not pushed** (targets `eltonaguiar/bestiejob`).
  - **Claimed effect:** ingest-gate on gated domains in `tools/jobs_merge_inbox.py`, add `config/gated_domains.txt`, purge gated rows (README/FRESH_JOBS/jobs.json) into `PAYWALL_ROLES.md` with xrefs; reports `truth-check exit=0` and `check_readme_sort` OK in local clone.
  - **Verification status:** artifact contents present locally; **not validated against current remote `main` by this investigation** and **not landed** (remote truth-check still fails on `7851e00` with 35 gated rows). Caveats in that note (pre-existing `board_invariants` ratchet/header mismatches, stale table header counts until rerender) remain relevant.

## Overall verdict
- **Fixes landed (agents/others) on remote `main`: NONE** for the three red gates.
- **Fixes prepared but unlanded:** one local truth-check remediation bundle exists outside inspected peer worktrees (`updates/2026-11-18-bestiejob-truthcheck-fix*`); promising but **requires rebase/validation on current `main`, conflict-safe publish, and CI proof** before counting as fixed.
- **Unowned/blocking:** Job Source Truth (data quality: gated leak + ingest enforcement), Gap channels push reliability (workflow hardening), board invariants debt/ratchet (published-board compliance). Bestiejob harvesting enhancement build (ServiceNow/Salesforce/CSA/CAD/CIS, Toronto/GTA+Canada-remote, 4 angles) is **awaiting owner selection** per parked v2/v3 seats.

## Recommended next actions (owner-gated)
1. Rebase/apply + verify the truth-check bundle against `HEAD 7851e00`, purge currently gated canonical rows, add ingest-time/domain guards, run `job_source_truth --check` and sort/merge guards, then push/PR and confirm green `Job Source Truth Check`.
2. Harden gap-channels `Commit and push` with bounded multi-attempt rebase/push (align with other `bestiejob-main-write` pushers) and rerun.
3. Triage `board invariants` report vs `reports/board_invariants_baseline.json`; remediate or intentionally re-baseline only with justified, reviewed deltas.
4. Decide and assign first build angle for SN/SF Toronto/remote harvesting (recommended start: direct ATS/company portals + cert/body-aware matching, per prior strategy). No secrets on bus; durable handoff in Git.
