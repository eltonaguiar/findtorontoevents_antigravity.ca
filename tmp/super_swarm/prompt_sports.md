# Super-Swarm Analysis: findtorontoevents.ca/live-monitor/sports-betting.html

You are one of 11 diverse AI engines reviewing the **sports betting picks page**. Goal: find correctness/UX bugs, audit edge claims, and recommend tightening of the picks pipeline.

## Context

- Page: https://findtorontoevents.ca/live-monitor/sports-betting.html
- Backend: PHP endpoints in `live-monitor/api/` (`sports_picks.php`, `sports_bets.php`, `sports_odds.php`, `sports_value_analyze.php`) → MySQL DB on 50webs.
- Status (Apr 27): 6/6 pytest smoke + 20/20 Playwright across 4 device profiles green.
- Sport-specific tier-vs-ROI: NBA STRONG TAKE +164% (n=3) vs NHL STRONG TAKE −100% (n=3). Sport-specific gates are the tuning axis.
- Recent fixes: PR #777 (EST date bucketing via `Intl.DateTimeFormat.formatToParts`); per-card age chip + 24h stale banner + HTTP 503 on DB fail (just landed in branch).
- Known concern: failover to torontoevent.net mirror silently served 9-day-old picks before age-chip fix.
- Pipeline: `tools/deploy_sports_files.sh` ships to 50webs (no shell on host). CI: `.github/workflows/sports-smoke-and-e2e.yml`.

## Your task — JSON envelope

```json
{
  "engine": "<engine name>",
  "verdict_summary": "<2-3 sentences>",
  "edge_claim_audit": [
    {
      "claim": "<e.g. NBA STRONG TAKE +164%>",
      "n": <integer>,
      "concern": "<small-n / regime / vig / CLV / survivorship>",
      "verdict": "credible|underpowered|likely_overfit|disputed",
      "fix": "..."
    }
  ],
  "page_bugs": [
    {"id": "SB-XX", "severity": "...", "issue": "...", "repro": "...", "fix": "...", "confidence": 0.0-1.0}
  ],
  "data_integrity": [
    {"concern": "<stale/timezone/closing-line-drift/vig-not-shown>", "evidence": "...", "fix": "..."}
  ],
  "responsible_gambling": {
    "current_state": "<adequate|partial|missing>",
    "gaps": ["..."],
    "recommendations": ["..."]
  },
  "missing_features_for_proven_performance": [
    {"feature": "CLV tracking", "value": "high|medium|low", "rationale": "..."}
  ],
  "sport_specific_gate_recommendations": {
    "NBA": "...", "NHL": "...", "NFL": "...", "MLB": "...", "UFC": "...", "soccer": "..."
  },
  "ranked_top3_priorities": ["..."]
}
```

## Rules

- Numbers like +164% / −100% on n=3 are NOT statistically significant — flag this directly.
- CLV (closing-line value) is the gold-standard edge proxy; audit if it's tracked.
- Vig/juice handling: are picks ROI-net or gross? Sportsbook fees integrated?
- Responsible-gambling disclaimer required by Ontario AGCO regs.
- No fabricated stats. Cite endpoint or file path for evidence.

Output ONLY the JSON envelope.
