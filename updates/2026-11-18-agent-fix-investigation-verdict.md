# Agent Fix Investigation — 2026-11-18

**Scope:** `eltonaguiar/BESTIEJOB` (job-hunt pipeline) + `findtorontoevents_antigravity.ca` worktree `bestiejobharvest-v4`

## BESTIEJOB Pipeline (remote main)

### Pipeline Health
- **Hourly Job Scan:** ✅ consistent success (2850→2858 listings in 24h)
- **Fresh CA sweep:** ✅ success every 3h
- **LinkedIn sweep:** ✅ daily success
- **Deploy GitHub Pages:** ✅ consistent success
- **Job Source Truth Check:** ❌ consistently fails (known issue — Adzuna API key mismatch)
- **Gap channels (Workday/Phenom/Oracle):** ❌ consistently fails (tenant config drift)
- **Agency board scan:** ✅ success

### Agent Fix Streams (last 60 commits)

| Agent | Commits | Pattern |
|-------|---------|---------|
| **github-actions[bot]** | ~45 | Hourly scan refresh, fresh CA sweep, automated data updates |
| **Hermes Agent** | ~10 | `chore(lessons):` hourly SN/SF scan checks — hourly sweep identifying fresh listings, merging verified postings into README |
| **Elton (human)** | ~3 | Manual scan commits + scan instructions |
| **Other bots** | ~0 | Pipeline is not triggered by other bot agents |

**Key finding:** The BESTIEJOB pipeline has no code-level "fixes" from agents — Hermes Agent performs operational scan/maintenance commits (`chore(lessons):`) that are pure data merges with zero code changes. The two consistently failing workflows (truth-check, gap-channels) are chronic issues that no agent has patched.

---

## Local Worktree (`bestiejobharvest-v4`)

### Update file volume (Nov 14-16 only): **90+ MD files**

Files cluster into these categories:

| Category | Count | Description |
|----------|-------|-------------|
| GHA audit/fix | ~15 | `gha-stale-data-sources`, `gha-verification-methodology`, `gha-best-practices-hardening`, `gha-disable-broken-workflows`, `gha-ic-analysis-missing`, etc. |
| Audit dashboard fixes | ~10 | `audit-quant-fixes-round{2,3,4}`, `audit-truth-layer-fixes`, `audit-strict-json-and-freshness-banner`, etc. |
| CI test fixes | ~5 | `ci-tests-sys-modules-leak-fix`, `ci-tests-trigger-filter-and-concurrency`, `ci-vix-gate-test-stabilization` |
| Profitability framework | ~4 | `profitability-framework`, `profitability-plan-execution`, `profitability-execution-summary` |
| Forward test/benchmark | ~6 | `forward-test-and-intraday-benchmarks`, `forward-validated-ledger-recompute`, `forward-clock-fill`, etc. |
| Asset class diagnosis | ~3 | `asset-class-diagnosis-and-skyrocket-research`, etc. |
| BESTIEJOB-related | ~5 | `bestiejobs-v2-fresh-scan-audit`, `bestiejobs-v2-merge-manifest`, `bestiejobs-v2-sn-sf-developer-jobs-discovery`, `bestiejobs-v2-sn-sf-wrapup-closeout` |
| ML audit | ~2 | `ML-AUDIT-childlike-airport`, etc. |

### Notable fix patterns across agents

1. **GHA stale data sources (2026-11-16):** Comprehensive audit of 7 stale data sources. Verdict: money_ready_count=0 is structural (no class passes PF≥1.5 or DSR≥0.95), not a bug. Swarm paper picks OLD.json (162d stale) — decommissioned experiment, not a rot.

2. **GHA verification methodology (2026-11-16):** 4-layer health monitoring framework (R1-R12 rules, queue depth, non-main audits, ad-hoc deep reports). Established 2026-11-16 baseline: 0 unexplained broken, 21 phantom runs (stable), 0 cancel churn. This is a foundation document, not a fix.

3. **CI test fixes:** Multiple rounds of CI stabilization — sys-modules-leak fix, trigger-filter-and-concurrency, vix-gate-stabilization. These are real, verified fixes with test assertions.

4. **Strict JSON publish gate (2026-11-16):** Added a `strict-json` validator that rejects `NaN`/`Infinity` in dashboard payloads before they reach the published `dashboard_data.json`. Prevents silent dashboard blanking.

5. **Regime terminal commit hardening (2026-11-16):** `safe_push.sh` retry logic for the regime-terminal bot's commit-and-push step. Prevents push-race work loss.

---

## Overall Verdict

**The local worktree has extensive investigation and documentation but relatively few landed code fixes.** The pattern is: agents investigate → write detailed `.MD` → leave the fix as a recommended remediation path. Actual code changes (GHA workflow tweaks, CI gate adjustments, JSON validators) are the minority (~15% of update files).

**For BESTIEJOB specifically:** The pipeline is stable — hourly scan, fresh CA sweep, LinkedIn sweep, and deploy all pass. Two workflows (truth-check + gap-channels) consistently fail but are non-blocking (scan data still reaches the board). **Hermes Agent** maintains the board via hourly raw scans that feed inbox/ submissions and `chore(lessons):` commits. No agent has attempted to fix the truth-check or gap-channel failures, nor added the batched subagent methodology proposed in this session.

**Three actionable gaps:**

1. **BESTIEJOB gap-channels + truth-check failures:** Chronic failures with no agent fix attempts. These are low-hanging fruit for a dedicated fix session.

2. **Update files without landed code:** ~85% of the 90+ Nov 14-16 update files are investigation-only. Many have clear remediation paths that were never executed.

3. **No batched subagent methodology deployed:** The proposed 4-batch system (Company Portals / Canadian Gov / GTA Municipal / SN-SF Partners) exists only as a design document from this session — not wired into any cron or GHA workflow.