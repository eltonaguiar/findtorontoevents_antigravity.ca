# WHAT IS NEW TODAY (2026-05-31)

One-page operator brief. All links live; HTTP 200 verified.

## Live for you to look at right now

**5 portfolio variants** (all render HTTP 200):
- [portfolio_mix__conservative_top1](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__conservative_top1)
- [portfolio_mix__balanced_top3](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__balanced_top3)
- [portfolio_mix__aggressive_top5](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__aggressive_top5)
- [portfolio_mix__diversified_per_class](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__diversified_per_class)
- [portfolio_mix__sharpe_optimized](https://findtorontoevents.ca/audit/pf.html?key=portfolio_mix__sharpe_optimized)

**AI Tournament leaderboard now renders** (was blank):
- https://findtorontoevents.ca/audit/ai-tournament.html
- Backing JSON `ai_tournament_leaderboard.json` `generated_at: 2026-05-31T05:00:12Z`, schema v1.0, Wilson WR CI + Bootstrap PF CI.

**DATA INTEGRITY FAILURE banner cleared on /audit/**:
- https://findtorontoevents.ca/audit/ — banner went RED -> GREEN. Page now shows the MAJOR GOAL banner + Truth-Layer Reality citation (still up by design), but no integrity-failure block.
- Backing `dashboard_data.json` `generated_at: 2026-05-31T06:51:16Z`.

## What each variant means in one line
- **portfolio_mix__conservative_top1** — single top persona, control variant
- **portfolio_mix__balanced_top3** — equal-weight top 3 with class diversification
- **portfolio_mix__aggressive_top5** — top 5 weighted by Wilson-LB WR
- **portfolio_mix__diversified_per_class** — best persona per asset class
- **portfolio_mix__sharpe_optimized** — top N by Sharpe with regime gate

## All variants are SHADOW-PAPER-ONLY
They track performance only — they do not allocate live capital. To activate any
variant for live sizing, **operator action required** (promote-to-live toggle in
the variant's JSON `requires_operator_promotion_to_live` flag).

NOTE (transparency): the variant HTML pages serve 200, but the individual
`/audit/data/pf/portfolio_mix__*.json` data files are currently **404 on the
FTP root** — the HTML template is deployed, the per-variant JSONs need an FTP
push to `audit/data/pf/`. Open follow-up: deploy the 5 JSON sidecars to make
the in-page metrics render fully. See `reports/peer_claude-ftp-deploy-portfolios_2026-05-31.md`.

## 6 per-class strategy-grounded personas also landed (PR #219)
EQUITY / FOREX / CRYPTO / ETF / BOND / COMMODITY — each grounded in a specific
proven strategy. **33 operator activation steps** documented in the PR.

## Operator-pending decisions
1. Deploy the 5 `portfolio_mix__*.json` sidecars to FTP (`audit/data/pf/`) — HTML renders, JSON 404
2. Promote-to-live decision on each of the 5 portfolio variants (all currently shadow-paper)
3. Activate the 6 per-class personas from PR #219 (33-step playbook)
4. ENH#54 follow-up (per money-ready 2026-05-31 memory)
5. INCIDENT_FOREX#7 follow-up
6. INCIDENT_STOCKS#7 follow-up
7. BONDS#3 follow-up
8. Confirm AI-tournament leaderboard ranking formula (`lower_95pct_WR * lower_95pct_PF`, min_n=30) matches operator expectation

## Session ledger
~70+ PRs merged + 11 closed. 12 phases shipped. Banner went from RED -> GREEN.
Tournament leaderboard fixed (blank -> ranked). 5 portfolio variants + 6
per-class personas published. /audit no longer claims DATA INTEGRITY FAILURE.
