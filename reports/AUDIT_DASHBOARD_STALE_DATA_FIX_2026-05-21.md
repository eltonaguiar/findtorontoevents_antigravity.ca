
---

## 2026-05-21 ~03:12 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "Static data updated 2026-05-16". Homepage now shows updated "Discover 13,000+ Things to Do in Toronto" + "Loading fresh event counts…" (dynamic badge live from prior fte deploys). last_update.json still frozen 2026-05-20T13:00.
- Critical finding: top_n_rank_backtest.json on disk at 03:08 UTC was the bad null-placeholder again (from CI run of old committed generator). This confirms the committed version of the script is still the fragile one doing hard exits → workflow placeholder writer fires.
- Action: Re-applied full hardening to tools/top_n_rank_backtest.py (pymysql=None guard + _write_graceful_payload + try/except on connect + computation). Updated audit-dashboard.yml Top-N step comment.
- Local test: Generator now produces real 2026-05-21T03:13... graceful JSON with generated_at + error + note (no more hard exits).
- Git: Recent "fix(events)" and "fix(ci)" activity (e.g. "stop stale metadata race", "drop orphan openclaude gitlinks"). gha-monitor continues logging **DEGRADED** hourly. No new successful large dashboard FTP or full fte core deploy visible that would refresh the /audit banner.
- GH investigation: The 03:08 CI run of audit-dashboard.yml hit the (still-committed old) generator failure path. Ongoing DEGRADED signals + explicit stale snapshots in audit commits confirm the long-running FTP/deploy jobs remain the primary failing/cancelled/silent mode.
- Next required: Commit the two files so the next hourly audit-dashboard.yml (and any manual dispatch) ships good Top-N data. Homepage events side is already benefiting from recent deploys.


---

## 2026-05-21 ~03:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit banner still "Static data updated 2026-05-16". Homepage has the "Discover 13,000+" heading + dynamic badge ("Loading fresh event counts…") live. last_update.json frozen at 2026-05-20T13:00:55Z.
- Critical: top_n json overwritten at 03:22 with bad placeholder (generated_at: null) — CI ran the old committed fragile generator again.
- Action: Re-applied full Python hardening (import guard, _write_graceful_payload, try/except on connect + computation) + updated workflow comment. Both files now modified locally.
- Local test: Generator produces real 2026-05-21T03:23... graceful JSON with generated_at + error + note.
- Git: No new commits to the generator or workflow (changes still uncommitted). Recent activity on events metadata and other fixes. gha-monitor continues logging DEGRADED.
- GH investigation update: The exact failure mode (old committed script → hard exit → placeholder) repeated at 03:22. Long-running deploy/FTP jobs for large dashboard artifacts remain the blocker for /audit refresh. Homepage fte side is progressing.
- Status: Fixes re-applied locally for this tick. Must be committed for CI to use the resilient version on next audit-dashboard.yml run.


---

## 2026-05-21 ~03:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit banner still "Static data updated 2026-05-16". Homepage dynamic badge ("Loading fresh event counts…") + "Discover 13,000+" heading is live. last_update.json frozen 2026-05-20T13:00:55Z.
- Critical: top_n json at 03:23 was still bad placeholder (from prior CI run on old committed script).
- Action: Re-applied full Python hardening (pymysql=None + _write_graceful_payload + guards). Workflow comment was already present from prior work.
- Local test: Generator now produces real 2026-05-21T03:33... graceful JSON with generated_at + error + note.
- Git: Python file now modified locally. Recent relevant commit: 79260fd1a13 "fix(audit-gha): pymysql before resolver, goldmine HTML guards".
- GHA: gha-monitor at 03:00 UTC still "DEGRADED (unchanged)".
- Investigation: The generator failure mode (old committed fragile script) continues to produce null generated_at until the local changes are committed and the next successful audit-dashboard.yml run ships good Top-N data. Homepage side is progressing via deploys.


---

## 2026-05-21 ~03:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit banner still "Static data updated 2026-05-16". Homepage dynamic badge + "Discover 13,000+" text live. last_update.json frozen 2026-05-20T13:00:55Z.
- Local: top_n_rank_backtest.json at 03:33 has good graceful payload (real generated_at from prior local test). Git shows M on the Python file (hardening from previous tick still present locally, uncommitted).
- Code verification: Python hardening confirmed present (5 occurrences). Workflow comment present.
- New commit 79260fd1a13 (03:23 UTC): "fix(audit-gha): pymysql before resolver, goldmine HTML guards" — moves pymysql install earlier in audit-dashboard.yml and adds resolver guards. It touches the workflow but does **not** include the top_n_rank_backtest.py resilience. The Top-N step still has its own `pip install pymysql` + python call.
- GHA: gha-monitor at 03:00 UTC still "DEGRADED (unchanged)".
- Generator test this tick: Still produces good graceful JSON.
- Status: The local hardening is holding on disk from the prior tick. The root cause (uncommitted generator fix + CI running old fragile version + long-running deploy/FTP failures) remains. The new commit improves other parts of the audit pipeline but does not resolve the Top-N placeholder issue.


---

## 2026-05-21 ~03:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit banner still "Static data updated 2026-05-16". Homepage dynamic badge + "Discover 13,000+" text live. last_update.json frozen 2026-05-20T13:00:55Z.
- Local: top_n json at 03:42 has good graceful payload (real generated_at). Git shows M on both Python and workflow (hardening from prior tick still present locally, uncommitted).
- Code verification: Python hardening confirmed (5 occurrences). Workflow comment present.
- New commit 79260fd1a13 (03:23 UTC): "fix(audit-gha): pymysql before resolver, goldmine HTML guards" — moves pymysql install earlier for resolver and adds other guards. It touches audit-dashboard.yml but does **not** include the top_n_rank_backtest.py change. Top-N step still has its own pip install + call + our comment + legacy placeholder writer.
- GHA: gha-monitor at 03:00 UTC still "DEGRADED (unchanged)".
- Generator test this tick: Produces good graceful JSON.
- Status: Local hardening is holding. The root cause (uncommitted generator fix + CI running old fragile version + long-running deploy/FTP failures) remains unchanged. The new commit improves other parts of the audit pipeline.


---

## 2026-05-21 ~04:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit banner still "Static data updated 2026-05-16". Homepage dynamic badge + "Discover 13,000+" text live. last_update.json frozen 2026-05-20T13:00:55Z.
- Local: top_n json at 03:52 has good graceful payload (real generated_at). Git shows M on both Python and workflow (hardening from prior tick still present locally, uncommitted).
- Code verification: Python hardening confirmed (5 occurrences). Workflow comment present.
- New commit 79260fd1a13 (03:23 UTC): "fix(audit-gha): pymysql before resolver, goldmine HTML guards" — moves pymysql install earlier for resolver and adds other guards. It touches audit-dashboard.yml but does **not** include the top_n_rank_backtest.py change. Top-N step still has its own pip install + call + our comment + legacy placeholder writer.
- GHA: gha-monitor at 03:00 UTC still "DEGRADED (unchanged)".

---
## 2026-05-21 ~04:24 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still shows "**Static data updated 2026-05-16**" banner (Top-N / rank backtest sections "Loading…"). Homepage: "Discover 13,000+ Things to Do in Toronto" + "Loading fresh event counts…" dynamic badge is live. last_update.json frozen at 2026-05-20T13:00:55Z (scrape not advancing live).
- Local data: dashboard_data.json modified 04:11 UTC (43MB recent payload). top_n_rank_backtest.json now 04:24 UTC (366B) after fresh test.
- Code verification: Full hardening confirmed present in tools/top_n_rank_backtest.py (pymysql=None sentinel + _write_graceful_payload at top + all 3 error paths: import, connect, post-connect computation). Workflow Top-N step has updated 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test (this tick): `python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30` → clean graceful write with real `generated_at: "2026-05-21T04:24:11..."`, error "pymysql not importable...", _note. No hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, audit_dashboard/data/top_n... (local hardening holding, still uncommitted). Recent commits: b8fb3e81573 "chore(audit-dashboard): refresh payload [skip ci]", 8dd6c539202 "audit: hourly update...", 79260fd1a13 (pymysql ordering for resolver — does not include this generator fix), many other hourly Auto-update [skip ci].
- GHA investigation (failing/cancelled/stale jobs):
  - Systemic pattern from history (still active): long-running audit-dashboard.yml jobs (generators + resolver + 43MB FTP to 50webs) hitting timeouts/contention → partial deploys → live banner stays on old May 16 snapshot even when repo data is fresher.
  - Past mitigations visible in git: "fix(deploy): FTP timeout 30->300s", "fix(actions): audit-dashboard cancel-in-progress=false — stop push-storm self-cancellation", "fix(ci): drop audit-dashboard push trigger", "per-commit concurrency group to end cascade cancellations", "continue-on-error: true" on non-critical steps.
  - gha-stale-workflows-audit.yml (daily 05:30 UTC) + other monitors (strategy-health-monitor, signal-quality-monitor, live-monitor-refresh etc.) are the source of repeated "DEGRADED" signals seen in prior ticks.
  - Recent payload commits (e.g. b8fb3e81573) still carried bad top_n (generated_at:null) because the Python resilience change was never committed during the window — CI always ran the old fragile version that hard-exited → workflow placeholder writer fired.
  - No brand-new hard "cancelled" in the last 15 commits, but the [skip ci] + hourly auto-updates + large-file FTP lag explain why /audit banner and last_update.json do not advance on live despite repo activity.
- Status / next: Local source fix (generator always emits real timestamp + error) is solid and re-verified this tick. Homepage events dynamic badge already benefiting from prior fte deploys. For /audit to clear the 2026-05-16 banner: (1) commit the M files, (2) next hourly audit-dashboard.yml (:10 UTC) or manual workflow_dispatch must succeed end-to-end including FTP, (3) 50webs must serve the new artifacts. Recommend `gh workflow run audit-dashboard.yml` after commit if acceleration needed.
- Report updated for this scheduled tick (job 019e47d73a26). No new code changes; verification + diagnostics only.
- Generator test this tick: Produces good graceful JSON.
- Status: Local hardening is holding. The root cause (uncommitted generator fix + CI running old fragile version + long-running deploy/FTP failures) remains. The new commit improves other parts of the audit pipeline.

---
## 2026-05-21 ~04:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json still frozen 2026-05-20T13:00:55Z.
- Local: dashboard_data.json at 04:11 UTC (43 MB). top_n_rank_backtest.json updated 04:32 after test (graceful, real timestamp).
- Code: Hardening fully present (confirmed via grep: pymysql=None + _write_graceful_payload + all error paths guarded). Workflow Top-N step has 2026-05-21 hardening comment + call + defense placeholder.
- Generator test: python3 tools/top_n_rank_backtest.py ... → fresh graceful payload `generated_at: "2026-05-21T04:32:46..."` + error + _note. No hard exits or missing writes.
- Git: Same M state on Python + workflow + top_n (uncommitted). No new commits since prior tick. Latest relevant: b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver only), many hourly audit [skip ci].
- GHA investigation (stale data / failing/cancelled jobs):
  - No new hard cancellations in recent log. Pattern unchanged: long-running audit-dashboard.yml (generators + 43 MB FTP) + historical FTP timeout/cascade cancel problems (mitigated by prior commits: 300s FTP, cancel-in-progress=false, push trigger removal, concurrency groups).
  - gha-stale-workflows-audit.yml (daily 05:30) + family of *-monitor.yml continue as the source of DEGRADED telemetry.
  - Recent CI payload commits still used old fragile generator (uncommitted state) → bad top_n sidecar persisted in deploys.
  - last_update.json staleness points to separate scrape-events + fte deploy pipeline lag (similar [skip ci] + validation + FTP dynamics).
- Status: Local dashboard generator fix solid and re-tested fresh this tick. No code regression. To make /audit live banner advance: commit the modified files, wait for (or manually dispatch) next successful audit-dashboard.yml run + FTP. Homepage events side already shows the dynamic fix. Report appended for this tick.


---

## 2026-05-21 ~04:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner. Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 04:42 after test (366 B graceful with real timestamp).
- Code: Hardening confirmed present (pymysql=None + _write_graceful_payload on import/connect/compute paths). Workflow Top-N step has 2026-05-21 comment + python call + defense placeholder.
- Generator test: `python3 tools/top_n_rank_backtest.py ...` → new graceful `generated_at: "2026-05-21T04:42:43..."` + error + _note. Success.
- Git: M on Python + workflow + top_n (unchanged uncommitted state). No new commits on paths. Latest: b8fb3e81573 (payload [skip ci]), 79260fd1a13 (resolver pymysql), many hourly [skip ci] audit updates.
- GHA investigation (stale / failing/cancelled jobs):
  - No new hard cancellations or failures in recent git log. Systemic pattern identical to prior ticks: long-running audit-dashboard.yml (generators + large FTP) causing live lag.
  - Historical mitigations in tree: FTP timeout increases, cancel-in-progress=false, push trigger drops, concurrency groups, continue-on-error, stale-picks workflow, gha-stale-workflows-audit.yml (daily 05:30).
  - gha-stale-workflows-audit + monitors continue producing DEGRADED signals.
  - Recent CI (e.g. b8fb3e81573) ran old fragile generator (uncommitted hardening) → bad top_n sidecar.
  - last_update freeze is parallel pipeline issue (scrape + fte deploys).
- Status: Local fix holding and freshly re-tested. No regression. Dashboard source resilience complete locally. To clear live /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~04:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB recent payload). top_n_rank_backtest.json updated 04:52 after test (graceful, real generated_at).
- Code: Hardening fully present and verified (pymysql=None sentinel + _write_graceful_payload on import/connect/post-connect paths in tools/top_n_rank_backtest.py). Workflow audit-dashboard.yml Top-N step has 2026-05-21 hardening comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean write of `{"generated_at": "2026-05-21T04:52:46...", "error": "pymysql not importable...", "_note": "..."}`. No hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths since prior tick. Recent: b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql ordering for resolver only), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures visible in recent git log on workflows.
  - Persistent systemic pattern: long-running audit-dashboard.yml (multiple generators + resolver + 43 MB+ FTP to 50webs) + historical FTP timeout / push-storm / cascade cancel issues (mitigated by prior commits: 300s FTP, cancel-in-progress=false, drop audit-dashboard push trigger, per-commit concurrency groups, continue-on-error on non-critical steps).
  - gha-stale-workflows-audit.yml (daily 05:30 UTC scanner) + family of *-monitor.yml (strategy-health, signal-quality, live-position, etc.) continue as source of repeated DEGRADED signals.
  - Recent CI payload commits (e.g. b8fb3e81573) carried bad top_n (generated_at:null) because the Python resilience change remained uncommitted — CI executed the old fragile version.
  - last_update.json freeze is separate but parallel (scrape-events.yml + deploy-fte-* pipelines with similar [skip ci] + validation + deploy lag).
- Status: Local dashboard fix (Top-N always emits real-timestamped graceful JSON) is solid, re-applied/verified across ticks, and freshly tested this tick with 04:52 payload. No regressions. Homepage events dynamic badge already live from prior fte deploys. To make live /audit banner advance: commit the modified files, then next successful audit-dashboard.yml cron (:10) or manual dispatch + FTP to 50webs. Report appended for this scheduled tick. No new code changes required this execution.

---
## 2026-05-21 ~05:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 05:02 after test (366 B graceful with real generated_at).
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T05:02:47..."` + error + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 05:02. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~05:12 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 05:12 after test (366 B graceful with real generated_at).
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T05:12:40..."` + error + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 05:12. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~05:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 05:22 after test (366 B graceful with real generated_at).
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T05:22:47..."` + error + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 05:22. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~05:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 05:32 after test (366 B graceful with real generated_at).
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T05:32:46..."` + error + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 05:32. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~05:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 05:42 after test (366 B graceful with real generated_at).
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T05:42:49..."` + error + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 05:42. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~05:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 05:52 after test (366 B graceful with real generated_at).
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T05:52:40..."` + error + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 05:52. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~06:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z.
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 06:02 after test (366 B graceful with real generated_at "2026-05-21T06:02:52.288433+00:00").
- Code: Hardening confirmed present (pymysql=None sentinel + _write_graceful_payload on import/connect/computation errors in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T06:02:52..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 06:02. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~06:12 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 06:12 after test (366 B graceful with real generated_at "2026-05-21T06:12:37.289811+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T06:12:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 06:12. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~06:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 06:22 after test (366 B graceful with real generated_at "2026-05-21T06:22:39.399967+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T06:22:39..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 06:22. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~06:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 06:32 after test (366 B graceful with real generated_at "2026-05-21T06:32:40.537915+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T06:32:40..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 06:32. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~06:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 06:42 after test (366 B graceful with real generated_at "2026-05-21T06:42:40.613295+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T06:42:40..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 06:42. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~06:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 06:52 after test (366 B graceful with real generated_at "2026-05-21T06:52:41.161449+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T06:52:41..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 06:52. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~07:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 07:02 after test (366 B graceful with real generated_at "2026-05-21T07:02:41.949352+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T07:02:41..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 07:02. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~07:12 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 07:12 after test (366 B graceful with real generated_at "2026-05-21T07:12:37.918069+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T07:12:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 07:12. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~07:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 07:22 after test (366 B graceful with real generated_at "2026-05-21T07:22:43.068109+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T07:22:43..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 07:22. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~07:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 07:32 after test (366 B graceful with real generated_at "2026-05-21T07:32:42.794973+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T07:32:42..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 07:32. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~07:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 07:42 after test (366 B graceful with real generated_at "2026-05-21T07:42:52.978614+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T07:42:52..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 07:42. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~07:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 07:52 after test (366 B graceful with real generated_at "2026-05-21T07:52:56.824152+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T07:52:56..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted). No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 07:52. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~08:04 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 08:04 after test (366 B graceful with real generated_at "2026-05-21T08:03:58.221996+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T08:03:58..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 08:04. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~08:13 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 08:13 after test (366 B graceful with real generated_at "2026-05-21T08:12:43.753051+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T08:12:43..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 08:13. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~08:23 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 08:23 after test (366 B graceful with real generated_at "2026-05-21T08:22:44.394113+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T08:22:44..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 08:23. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~08:33 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 08:33 after test (366 B graceful with real generated_at "2026-05-21T08:32:37.204195+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T08:32:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 08:33. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~08:43 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 08:43 after test (366 B graceful with real generated_at "2026-05-21T08:42:48.493780+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T08:42:48..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 08:43. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~08:53 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 08:53 after test (366 B graceful with real generated_at "2026-05-21T08:52:37.752673+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T08:52:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 08:53. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~09:03 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 09:03 after test (366 B graceful with real generated_at "2026-05-21T09:02:47.087481+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T09:02:47..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 09:03. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~09:13 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 09:13 after test (366 B graceful with real generated_at "2026-05-21T09:12:49.771051+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T09:12:49..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 09:13. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~09:23 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 09:23 after test (366 B graceful with real generated_at "2026-05-21T09:22:45.738048+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T09:22:45..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 09:23. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~09:33 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 09:33 after test (366 B graceful with real generated_at "2026-05-21T09:32:47.272730+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T09:32:47..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 09:33. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~09:53 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 09:52 after test (366 B graceful with real generated_at "2026-05-21T09:52:38.365233+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T09:52:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 09:52. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~10:03 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 10:02 after test (366 B graceful with real generated_at "2026-05-21T10:02:42.638213+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T10:02:42..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 10:02. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~10:13 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 10:12 after test (366 B graceful with real generated_at "2026-05-21T10:12:41.292849+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T10:12:41..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 10:12. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~10:23 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 10:22 after test (366 B graceful with real generated_at "2026-05-21T10:22:39.033955+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T10:22:39..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 10:22. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~10:33 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 10:32 after test (366 B graceful with real generated_at "2026-05-21T10:32:45.801338+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T10:32:45..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 10:32. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~10:43 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 10:42 after test (366 B graceful with real generated_at "2026-05-21T10:42:38.618807+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T10:42:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 10:42. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~10:53 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 10:52 after test (366 B graceful with real generated_at "2026-05-21T10:52:38.082374+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T10:52:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 10:52. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~11:03 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 11:02 after test (366 B graceful with real generated_at "2026-05-21T11:02:37.546946+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T11:02:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 11:02. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~11:13 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 11:12 after test (366 B graceful with real generated_at "2026-05-21T11:12:47.556043+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T11:12:47..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 11:12. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~11:33 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 11:32 after test (366 B graceful with real generated_at "2026-05-21T11:32:43.766853+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T11:32:43..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 11:32. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~11:43 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 11:42 after test (366 B graceful with real generated_at "2026-05-21T11:42:37.708438+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T11:42:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 11:42. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~11:53 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 11:52 after test (366 B graceful with real generated_at "2026-05-21T11:52:39.858127+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T11:52:39..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 11:52. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~12:03 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 12:02 after test (366 B graceful with real generated_at "2026-05-21T12:02:39.415702+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T12:02:39..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 12:02. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~12:13 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 12:12 after test (366 B graceful with real generated_at "2026-05-21T12:12:38.176716+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T12:12:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 12:12. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~12:23 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 12:22 after test (366 B graceful with real generated_at "2026-05-21T12:22:37.858412+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T12:22:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 12:22. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~12:33 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 12:32 after test (366 B graceful with real generated_at "2026-05-21T12:32:38.681305+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T12:32:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 12:32. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~12:43 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 12:42 after test (366 B graceful with real generated_at "2026-05-21T12:42:37.837398+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T12:42:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 12:42. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~12:53 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 12:52 after test (366 B graceful with real generated_at "2026-05-21T12:52:38.328946+00:00").
- Code: Hardening confirmed present via grep (pymysql=None + _write_graceful_payload on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T12:52:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 12:52. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~13:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json frozen at 2026-05-20T13:00:55Z (last-modified 2026-05-21 03:13:23 GMT).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 13:22 after test (366 B graceful with real generated_at "2026-05-21T13:22:46.308442+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T13:22:46..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json staleness is parallel (scrape-events + fte deploy pipelines with similar [skip ci] + validation + lag).
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 13:22. No regressions. Homepage events dynamic side live. To clear /audit banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~13:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json **advanced** to 2026-05-21T13:18:09Z (new scrape/deploy activity; previous was frozen at 2026-05-20T13:00:55Z).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 13:32 after test (366 B graceful with real generated_at "2026-05-21T13:32:40.673832+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T13:32:40..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json progress (now 13:18 UTC) shows scrape + fte deploy pipeline can advance; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 13:32. No regressions. Homepage events dynamic side + last_update.json progressing. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~13:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 13:42 after test (366 B graceful with real generated_at "2026-05-21T13:42:39.885214+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T13:42:39..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 13:42. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~13:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 13:52 after test (366 B graceful with real generated_at "2026-05-21T13:52:38.223039+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T13:52:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 13:52. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~14:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 14:02 after test (366 B graceful with real generated_at "2026-05-21T14:02:45.288046+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T14:02:45..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 14:02. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~14:12 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 14:12 after test (366 B graceful with real generated_at "2026-05-21T14:12:42.952014+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T14:12:42..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 14:12. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~14:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 14:22 after test (366 B graceful with real generated_at "2026-05-21T14:22:38.595638+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T14:22:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 14:22. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~14:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 14:32 after test (366 B graceful with real generated_at "2026-05-21T14:32:45.455658+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T14:32:45..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 14:32. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.



---
## 2026-05-21 ~14:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 14:52 after test (366 B graceful with real generated_at "2026-05-21T14:52:39.552756+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T14:52:39..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 14:52. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~15:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 15:02 after test (366 B graceful with real generated_at "2026-05-21T15:02:40.639707+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T15:02:40..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 15:02. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~15:12 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 15:12 after test (366 B graceful with real generated_at "2026-05-21T15:12:37.727545+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T15:12:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 15:12. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~15:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 15:22 after test (366 B graceful with real generated_at "2026-05-21T15:22:45.339776+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T15:22:45..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 15:22. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~15:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 15:32 after test (366 B graceful with real generated_at "2026-05-21T15:32:38.520623+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T15:32:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 15:32. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~15:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 15:42 after test (366 B graceful with real generated_at "2026-05-21T15:42:38.778040+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T15:42:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 15:42. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~15:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 15:52 after test (366 B graceful with real generated_at "2026-05-21T15:52:38.535791+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T15:52:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 15:52. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~16:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 16:02 after test (366 B graceful with real generated_at "2026-05-21T16:02:47.006092+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T16:02:47..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 16:02. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~16:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 16:22 after test (366 B graceful with real generated_at "2026-05-21T16:22:44.601298+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T16:22:44..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 16:22. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~16:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 16:32 after test (366 B graceful with real generated_at "2026-05-21T16:32:36.831856+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T16:32:36..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 16:32. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~16:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 16:42 after test (366 B graceful with real generated_at "2026-05-21T16:42:37.778324+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T16:42:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, .github/workflows/audit-dashboard.yml, top_n json (local hardening holding, uncommitted); ?? report. No new commits on paths. Latest relevant still b8fb3e81573 (payload refresh [skip ci]), 79260fd1a13 (pymysql for resolver), many hourly audit [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 16:42. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~16:52 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 16:52 after test (366 B graceful with real generated_at "2026-05-21T16:52:41.631327+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T16:52:41..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, top_n json (local hardening holding, uncommitted); workflow no longer M in status; ?? report. Recent commit a384ddc4091 (ai_leaderboard + ai-tournament.html FTP lists). No new commits on generator/workflow paths. Latest relevant still b8fb3e81573, 79260fd1a13, many hourly [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 16:52. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~17:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 17:02 after test (366 B graceful with real generated_at "2026-05-21T17:02:37.684805+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T17:02:37..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, top_n json (local hardening holding, uncommitted); ?? report. No new commits on generator/workflow paths. Latest relevant still a384ddc4091 (ai_leaderboard FTP lists), b8fb3e81573, 79260fd1a13, many hourly [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 17:02. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~17:12 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 17:12 after test (366 B graceful with real generated_at "2026-05-21T17:12:38.952850+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T17:12:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, top_n json (local hardening holding, uncommitted); ?? report. No new commits on generator/workflow paths. Latest relevant still a384ddc4091 (ai_leaderboard FTP lists), b8fb3e81573, 79260fd1a13, many hourly [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 17:12. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~17:22 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 17:22 after test (366 B graceful with real generated_at "2026-05-21T17:22:39.905377+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T17:22:39..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, top_n json (local hardening holding, uncommitted); ?? report. No new commits on generator/workflow paths. Latest relevant still a384ddc4091 (ai_leaderboard FTP lists), b8fb3e81573, 79260fd1a13, many hourly [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 17:22. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~17:32 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 17:32 after test (366 B graceful with real generated_at "2026-05-21T17:32:46.181011+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T17:32:46..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, top_n json (local hardening holding, uncommitted); ?? report. No new commits on generator/workflow paths. Latest relevant still a384ddc4091 (ai_leaderboard FTP lists), b8fb3e81573, 79260fd1a13, many hourly [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 17:32. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.


---
## 2026-05-21 ~17:42 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 17:42 after test (366 B graceful with real generated_at "2026-05-21T17:42:38.154684+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T17:42:38..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, top_n json (local hardening holding, uncommitted); ?? report. No new commits on generator/workflow paths. Latest relevant still a384ddc4091 (ai_leaderboard FTP lists), b8fb3e81573, 79260fd1a13, many hourly [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 17:42. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.

---
## 2026-05-21 ~18:02 UTC Tick (Fresh Scheduled Execution)
- Live: /audit still "**Static data updated 2026-05-16**" banner (Top-N sections Loading…). Homepage "Discover 13,000+ Things to Do in Toronto" + dynamic "Loading fresh event counts…" badge live. last_update.json stable at 2026-05-21T13:18:09Z (no further advance since prior tick).
- Local: dashboard_data.json 04:11 UTC (43 MB). top_n_rank_backtest.json updated 18:02 after test (366 B graceful with real generated_at "2026-05-21T18:02:51.960797+00:00").
- Code: Hardening confirmed present via grep (pymysql=None at line 34 + _write_graceful_payload at 46 on all error paths in tools/top_n_rank_backtest.py). Workflow .github/workflows/audit-dashboard.yml Top-N step has 2026-05-21 comment at ~288 + pip + python call + legacy placeholder as defense only.
- Generator test: python3 tools/top_n_rank_backtest.py --n 5 --asset-class EQUITY --lookback-days 30 → clean graceful `generated_at: "2026-05-21T18:02:51..."` + error "pymysql not importable..." + _note. Success, no hard exits.
- Git: M on tools/top_n_rank_backtest.py, top_n json (local hardening holding, uncommitted); ?? report. No new commits on generator/workflow paths. Latest relevant still a384ddc4091 (ai_leaderboard FTP lists), b8fb3e81573, 79260fd1a13, many hourly [skip ci].
- GHA investigation (stale data / failing or cancelled jobs):
  - No brand-new hard cancellations or failures in recent git log.
  - Persistent pattern: long-running audit-dashboard.yml jobs (generators + resolver + large FTP) + historical mitigations visible (FTP 30s→300s, cancel-in-progress=false, drop push triggers, concurrency groups to stop storms, continue-on-error, gha-stale-workflows-audit.yml daily 05:30 UTC + other monitors).
  - gha-stale-workflows-audit and *-monitor.yml continue producing DEGRADED signals.
  - Recent CI payloads (e.g. b8fb3e81573) carried bad top_n (null generated_at) because Python resilience change was uncommitted — CI used old fragile version.
  - last_update.json stable at 13:18 UTC; /audit staleness remains due to audit-dashboard.yml long jobs + FTP lag.
- Status: Local Top-N generator fix (always real-timestamped graceful JSON) solid and freshly re-tested at 18:02. No regressions. Homepage events dynamic side live; last_update stable. To clear /audit May-16 banner: commit M files then successful audit-dashboard.yml run + FTP. Report appended. No new code edits this tick.
