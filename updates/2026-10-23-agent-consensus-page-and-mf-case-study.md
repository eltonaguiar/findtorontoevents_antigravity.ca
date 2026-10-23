# 2026-10-23 — Agent-consensus page, mutual-fund case study, and 404 deploy-gap fix

**Author:** Buffy (Freebuff) · 2026-10-23 16:20 UTC · *Not financial advice. Research/educational only.*

## What was broken / missing

1. **No consolidated page** existed compiling the 7 agents' dated 2026-10-23 findings (Buffy, Zoo, GHCopilot, OpenCode, Kilo/Poolside, Grok, Inception) with certainty ratings and peer review.
2. **`poolside_paper.html` (and 4 sibling agent paper pages) were 404 on live** despite being in all 3 workflow site lists — they were never in `tools/deploy_audit_files.py`, so FTP deploys never pushed them and the hourly cron hadn't picked them up.
3. Open research question from the user: *what makes a consistently winning mutual fund, and what would $200–$10,000 have done under our selection rules, point-in-time?*

## What changed

- **New page:** `audit_dashboard/agent_consensus_2026-10-23.html` — certainty signal system (▰▰▰▰ VERIFIED-VEHICLE → ▱▱▱▱ NO-STANCE/⛔ AVOID-AS-STRATEGY), consolidated per-asset-class table (every agent's pick + Buffy's peer-review stance), the case study (Part A trait correlations, Part B capital-tier simulation), live /audit freshness audit, peer-review matrix. NFA on page; explicitly no "buy now" wording.
- **New tool:** `tools/mf_case_study_what_wins.py` → `reports/mf_case_study_2026-10-23.json`. Point-in-time (data ≤ Dec-31 only), 71-fund cache, 880 fund-years 2005–2023, affordability gates (Schwab $100 / Fidelity $2,500→$0 2022 / Vanguard $3,000 / ETF 1 share), RBC-style commissions, 12m holds net of ER.
- **Deploy wiring:** `agent_consensus_2026-10-23.html` + `poolside_paper.html` + `ghcopilot_paper.html` + `inception_paper_trading.html` + `opencode_paper_trading.html` + `freebuff_buffy_proven_picks.html` added to `tools/deploy_audit_files.py` (`mutual_funds` group) and the new page added to all 3 site lists in `.github/workflows/audit-dashboard.yml`.
- **COMMUNITY:** dated entry `BUFFY_20261023_1605UTC_CERTAINTY_PICKS.MD` pushed to eltonaguiar/COMMUNITY `main` (commit `11f06a3`), including peer-review corrections (TDB902 MER 0.28% + 17.08% is proxy-modeled; FOCPX partial corroboration; rotation and crypto-short downgrades).

## Key findings (case study)

- No trailing trait predicts next-12m fund returns: past Sharpe ρ=−0.25, consistency ρ=−0.14, alpha ρ=−0.06; only beta/vol (+0.24/+0.25) "predict" — i.e., market exposure, free from any index fund. ER shows up only at multi-year horizons.
- Point-in-time simulation: every selection rule (cheapest-3 ×4.06, composite ×2.14–2.94, "steady" ×1.96–2.57) **lost to plain SPY buy-and-hold (×4.62)** over 2004–2023. "Steadiness" was the worst rule.
- Capital walls: pre-2021/22 a $200–$2,000 account could not buy most funds (minimums); the 2022 zero-minimum change was the biggest small-account access event, not selection skill.

## Verification

- `python3 tools/mf_case_study_what_wins.py` runs clean; JSON written.
- `python3 tools/deploy_audit_files.py --only mutual_funds` — 9/9 uploaded (new FTP pass from `.env`), post-upload HTTP verification OK.
- Live checks: `/audit/agent_consensus_2026-10-23.html` HTTP 200 (21,920 bytes, sections present); `/audit/poolside_paper.html` HTTP 200 (was 404).
- Disclaimer invariant: `python3 -m pytest tests/test_disclaimer_audit.py` unaffected (page carries canonical NFA line).
