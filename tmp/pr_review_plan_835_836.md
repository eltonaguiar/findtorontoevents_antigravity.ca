Multi-engine review of two open PRs from today's quant-performance-auditor agent run. Both target Goal #1 (phenomenal performance per asset class on /audit).

## PR #835 — fix(crypto): suppress st_fear_greed_contrarian from smart_picks scoring path
- Branch: fix/crypto-suppress-st-fear-greed-contrarian-2026-05-05
- Diff: 1 line — uncomments st_fear_greed_contrarian in alpha_engine/smart_picks_engine.py BANNED_SYSTEMS (line 210)
- Evidence: dashboard_data.json::performance.systems.claude_gainer_st.strategies.st_fear_greed_contrarian → WR 0.342, n=652, total_pnl_pct -182
- Wire-up: BANNED_SYSTEMS check at smart_picks_engine.py:1650 in main pick loop, exact-match string compare
- Risk: low (sibling st_fear_greed_contrarian_regime_filtered at line 262 unaffected)

## PR #836 — fix(commodity): suppress forex_copy_trader from COMMODITY emission via SOURCE_SYSTEM_BLOCKLIST_BY_CLASS
- Branch: fix/commodity-suppress-forex-copy-trader-2026-05-05
- Diff: 31 lines new — adds SOURCE_SYSTEM_BLOCKLIST_BY_CLASS dict at outcome_resolver.py:131 + helper _is_source_system_blocked_for_class at line 140 + gate twin to BLACKLISTED_STRATEGIES at line 700-710 inside resolve_single_pick
- Evidence: dashboard_data.json::performance.systems.forex_copy_trader → PF 0.31, n=46 on COMMODITY
- Pattern: blocklist (not allowlist) — surgical, reverses by removing the entry

## What I want from each engine

For each PR independently, return JSON:
{
  "pr_number": 835,
  "verdict": "MERGE|REQUEST_CHANGES|HOLD",
  "evidence_check": { "all_anchors_verified": bool, "files_exist": bool, "line_numbers_correct": bool },
  "wire_up_check": { "production_caller": bool, "exact_match_safe": bool },
  "risk_concerns": [{"severity": "blocking|major|minor", "claim": "...", "evidence": "..."}],
  "approve_reasons": [...]
}

Then a single overall recommendation: "merge both" / "merge one, hold other" / "request changes on N" with the rationale.

You have read access to the repo. Verify claims by grep/cat — do not trust the PR body.
