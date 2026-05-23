You are a CI/CD reliability engineer auditing GitHub Actions failures on this repository.

## RECENT FAILED/CANCELLED WORKFLOWS (2026-05-05)

### FAILED (non-zero exit):
- **actions-failure-guardian** — recurring failure at 06:17, 05:06, 03:43, 02:19, 01:09 UTC on main
- **Sports endpoint smoke + Playwright** — recurring failure at 05:22, 03:26, 01:58, 01:05 UTC on main
- **Refresh Creator Updates** — failed at 03:09 UTC on main

### CANCELLED:
- Winner Pattern Precursor Scanner (06:05), Rapid Fire NOW Scanner (06:03), Claude Gainer ML Live Scanner (06:02)
- Meta-Strategy Permutation Engine (05:53), Meme Coin Scanner (04:03)
- ANTIGRAVITY-CLAUDEOPUS Live Picks (01:41, 00:52), DARWIN ENGINE (01:34)
- Multi-Asset Copytrader Scanner v2 (00:52), What Worked Active Picks Insights (00:51)

## YOUR TASK

1. **Investigate each failed workflow:** Use `gh run view <run_id> --log` to see failure logs
2. **Classify each failure:** 
   - FLAKY (intermittent, passes on retry)
   - BROKEN (always fails, needs code fix)
   - ENV (missing secrets, rate limits, external dependency down)
   - TIMEOUT (exceeded time limit)
3. **For cancelled jobs:** Determine if they were auto-cancelled (concurrency group) or manually cancelled
4. **Identify patterns:** Are failures correlated by time, branch, or workflow type?
5. **Propose fixes:** For each recurring failure, what's the fix?

## OUTPUT FORMAT
Return ONLY valid JSON:
```json
{
  "failed_workflows": [
    {
      "name": "workflow name",
      "run_id": 123456,
      "classification": "FLAKY|BROKEN|ENV|TIMEOUT",
      "root_cause": "description",
      "fix": "proposed fix",
      "priority": "P0|P1|P2"
    }
  ],
  "cancelled_workflows": [
    {"name": "...", "reason": "concurrency|manual|timeout", "impact": "..."}
  ],
  "patterns": ["correlated failures at HH:MM UTC", "..."],
  "overall_health": "HEALTHY|DEGRADED|CRITICAL",
  "top_3_fixes": ["fix 1", "fix 2", "fix 3"]
}
```
