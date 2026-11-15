# Pre-Prompt Documentation
## What prompts hilarious-seer was responding to

**Date:** 2026-11-15  
**Worktree:** hilarious-seer  
**Agent:** Kilo (senior quant analyst)  

---

## Original User Request (paraphrased)

> Based on this info, get us some prompts to help a github repo for prediction of various financial investment asset classes like stocks/crypto/forex/bonds/etfs/commodities/mutual funds etc.
>
> You have a repo https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ that was being worked on for basically years with tons of AI agents, lots of .MD of research, strategies for stocks/crypto/forex/bonds/ETFS/mutual funds,.... and yet the dashboard output isn't profitable. The repo feeds into findtorontoevents.ca/audit where we have active picks, closed picks and an attempt at predictions for asset classes.
>
> review money-maker* files and RECOVERY_PROTOCOL*.MD and all Kimi* files and folders, where we had Kimi Agent Swarm research and review our project over time,
>
> We also had findtorontoevents.ca/updates/index.html where we talked about our strategies we tried.
>
> But overall, just give us some strategies to go through the repo, algorithms and find us 1 or more profitable asset classes, and timeframes, and TP/SL or other trading parameters, and a method to prove beyond a shadow of a doubt its profitable.
>
> Like if we hired the world's leading Quants or a stock expert, then a crypto expert, mutual fund expert etc. Despite trying so many strategies, we still were met with failure.
>
> What statistical measures should we consider to use. Use subagents and scan our repo for statistical and risk management methods/ mathematical functions/ machine learning algorithms and determine, what we've already tried, and determine room for other simulations we can adjust.
>
> -- Give me an enhanced prompt given the one above.

---

## Enhanced Prompt Provided by Mercury 3 (World-Class Quant Team Version)

The user received and adopted an enhanced prompt from Mercury 3 that specified:
- Phase 1: Inventory & Taxonomy (complete table of everything tried)
- Phase 2: Forensic Failure Analysis (10 failure modes)
- Phase 3: Gap Analysis & New Experiments
- Phase 4: The Proof Standard (10 non-negotiable gates)
- Phase 5: Required Statistical & Risk Metrics
- Phase 6: Deliverables (AUDIT_REPORT.md, STRATEGY_SHORTLIST.md, runnable code, PROOF_PROTOCOL.md, executive summary)

---

## Self-Engineering Prompt Request

The user then asked for a prompt that makes the AI *own* the workflow:
- Create its own dated workspace under WIRED_IN
- Run repo-mining pass first
- Store artifacts in harvested_ideas/, Plan/, experiments/, tracker/, proof/
- Commit and push to remote
- Include prediction tracker scaled to timeframe
- Include proof standard

---

## Divide-and-Conquer Request

The user asked me to:
> divide and conquer using subagents as needed to break down this task, perhaps by asset class, focusing on the highest probability asset class to find consistent profit? e.g. Bonds? Mutual funds? ETFs?
>
> We could also in theory try some low investment, but decent chances strategies, e.g. 10 penny stocks, where at least 1 would sky rocket? or a bit pricier like $2-5 stocks, etc.

I dispatched three parallel subagents:
1. **ETF/Mutual Fund deep dive** — passive beta + sector rotation + TAA
2. **CRYPTO deep dive (BTC-only)** — BTC trend/momentum signals
3. **Penny / low-priced stock research** — $2-5 range strategies

---

## Follow-Up: Deploy to WIRED_IN Subfolder

The user then asked:
> your work needs to be deployed to a sub-folder under https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/WIRED_IN date-time stamped and your work tree name or abbreviated name.
> share the prompt(s) you are responding to in a PRE_PROMPT.MD file in there also.

This file (`PRE_PROMPT.MD`) is the response to that request.

---

## Files Produced in This Folder

All files were generated in response to the above prompts and committed to this WIRED_IN subfolder:

| File | Purpose |
|------|---------|
| `README.md` | Consolidated reference combining all prompts, proof standards, failure diagnosis, Q&A |
| `MASTER_PROMPT.md` | Merged self-engineering + proof standard single-shot prompt |
| `QUANT_AUDIT_PROMPT.md` | Compressed single-agent prompt for Claude Code |
| `REPO_INVENTORY_HEADSTART.md` | Curated file/folder list to accelerate Phase 1 inventory |
| `AUDIT_REPORT_TEMPLATE.md` | Structured template for forensic audit reports |
| `STRATEGY_SHORTLIST_TEMPLATE.md` | Structured template for ranked strategy shortlists |
| `NEGATIVE_RESULT_DIAGNOSIS_TEMPLATE.md` | Failure classification matrix + decision tree |
| `PROOF_STANDARD_METRICS.md` | Cross-asset proof standard with thresholds and operational setup |
| `ETF_MF_AUDIT.md` | **Completed subagent audit** — ETF/MF deep dive with runnable backtest |
| `CRYPTO_AUDIT.md` | **Completed subagent audit** — BTC-only deep dive with runnable backtest |
| `PENNY_STOCK_AUDIT.md` | **Completed subagent audit** — Penny stock deep dive with runnable backtest |
| `PRE_PROMPT.MD` | This file — documents the prompts being responded to |

---

## Key Results

- **0/166 money-ready strategies** proven across all asset classes
- **ETF/MF:** TAA rotation in-sample robust (Sharpe 0.88, MaxDD -19%) but NOT forward-proven
- **CRYPTO:** 19+ strategies audited, ZERO pass proof gates; BTC SMA200 + RSI2 only candidate
- **PENNY:** CEF/BDC NAV discount is only viable path; true pennies <20% chance of clearing gates
- **Only viable path:** Passive beta (VTI/BND 60/40)

---

*Generated by hilarious-seer worktree, 2026-11-15*
