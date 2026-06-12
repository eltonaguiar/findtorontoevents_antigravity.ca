# /thingstocheck_June2026 slash command

Invoke the `thingstocheck-june2026` skill (see .claude/skills/thingstocheck_June2026/SKILL.md).

This runs the full audit review of the trading prediction system edge, /audit/ pages, DBs, picks performance, why no profitable per class, hidden edge search, specific bugs (21.1% picks-now, gpt4_1 verify, kimi bias, stale portfolio/ai_leaderboard, FWD vs strat WR, synthetic, reverse splits, limits, losing portfolios, research NO_EDGE, etc.).

Workflow per skill:
- Update todos
- Fetch/analyze live pages
- Source review (manifest 47 buttons etc, gates, generators)
- Safe DB (backup first via db_backup_to_backups.py + db_env.py; targeted queries for performance per class/symbol-dir, FWD, conc, data issues)
- Concepts integration (copytrader, prediction markets, growth screener, meme/penny plans)
- Debug specifics
- Create/update PLAN_INSIGHTS_GROK_June122026_*.MD (unique)
- Append to main grok deep-dive MD (Pass 68+)
- Verifs (py_compile, loads, grep, queries, page status) + read outputs
- Use money-maker, audit-pick-flow, large-repo, verification, db-schema, hypothesis-registry, swarm if needed
- Goal #1, coord, read-only unless safe backup

Full prompt saved in the skill file.

Run with: activate the skill or directly reference /thingstocheck_June2026 .

Created 2026-06-12 per user request.