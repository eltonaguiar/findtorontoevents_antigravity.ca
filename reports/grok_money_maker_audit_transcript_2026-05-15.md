# Grok Money-Maker Continual Improve Audit Transcript — 2026-05-15

**Date:** 2026-05-15  
**Session Type:** Strategic Quant Deep-Dive + Agent Swarm Coordination  
**Censored:** All API keys, personal tokens, and sensitive credentials redacted.

---

## Context & Trigger

User requested a "bigger picture" review of the entire prediction platform after the successful PR triage execution by Claude (8 bloated/divergent PRs closed, test debt reduced from 36 → 4 failures on main).

Key instruction:  
> Review the master action plan branch vs current state + open PRs. Deep dive the MySQL DBs, GitHub Actions, and data flow per asset class. Act as a senior quant trying to save a company with a gigantic multi-asset codebase. Do not trust existing stats — run your own analysis. Use subagents per asset class. Look for hidden insights. Produce a 90-day plan (SUPREME_PLAN_90days) + per-asset-class 90-day plans. Note that cotton is only one symbol inside COMMODITY.

User also referenced the "asset class" dropdown on `findtorontoevents.ca/audit` as the canonical list of classes to cover.

---

## Major Strategic Decisions Made

### 1. Asset Class Prioritization (Reality Check)

After cross-referencing live `dashboard_data.json` (2026-05-15), recent subagent deep dives, and historical audits:

**Current Ranking (Evidence-Based):**

| Rank | Asset Class   | Verdict                          | Key Risk / Hidden Insight |
|------|---------------|----------------------------------|-----------------------------|
| 1    | **COMMODITY** | Strongest edge, but contaminated | Cotton (CT=F) = 73% of PnL mass. Famous "90% WR" paper pilot was massively over-emitted (101 trades from 5 CFTC reports). True independent n is tiny. |
| 2    | **EQUITY**    | Best diversified candidate       | Powerful VIX-regime 12-1 momentum edge (PF 5.37 / MDD 7.3% in backtests) discovered but **unshipped**. Production universe is dangerously narrow (18 tickers, heavy AMD + pennies). |
| 3    | **ETF**       | High ROI "activate now"          | Sector rotation + VIX < 25 gate shows Tier-1 backtest stats (PF 3.22). Live is diluted by generic sources. Worth targeted parallel work. |
| 4    | **CRYPTO**    | Volume king, quality disaster    | Needs brutal universe reduction. Many toxic systems still active. |
| 5-6  | FOREX / BOND  | Not investment-grade             | Insufficient n or weak risk-adjusted returns. Data collection only. |
| -    | **Futures / Penny / Meme** | Worse than coin toss or not built | Explicitly called out by user as the worst categories in the audit dropdown. |

**Critical Realization:** The platform has excellent *research* in some areas (VIX regime for EQUITY/ETF, carry+momo for commodities) but production is running on contaminated or narrow universes.

### 2. 90-Day Strategic Philosophy

- **One diversified, trustworthy asset class > seven half-baked ones.**
- Cotton is **one symbol** — treating it as the entire COMMODITY bet is concentration suicide.
- Data quality and outcome tracking must be fixed first (DB Freshness + paper trading + resolver reliability).
- Use AI API keys intelligently for feature ideation and literature synthesis per class, never for production code without heavy verification.

### 3. Subagent Deployment Strategy

Deployed specialized subagents using the `money-maker-continual-improve` skill for parallel deep dives:

- COMMODITY (with explicit cotton concentration autopsy)
- EQUITY (VIX regime + universe quality)
- ETF (sector rotation + VIX gate activation)
- CRYPTO (universe reduction plan)

**Next batch planned** (after current set finishes):
- FOREX
- BOND
- FUTURES (separate from general COMMODITY)
- Low-Quality Equities (Penny Stocks + Meme Coins) — treated as its own high-risk category

### 4. Master Deliverables Created

- `reports/SUPREME_PLAN_90days.md` — Focused 90-day execution roadmap (single source of truth).
- `reports/SUPREME_PLAN_90days.html` — Clean companion HTML viewer.
- `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md`
- `reports/asset_class_90day_plan_EQUITY_2026-05-15.md`
- `reports/asset_class_90day_plan_ETF_2026-05-15.md`
- `reports/asset_class_90day_plan_CRYPTO_2026-05-15.md` (earlier)
- `updates/2026-05-15-ci-fail-cleanup-main-green.md` (earlier)
- `reports/claude_chat_audit_review_2026-05-15.md` (earlier comprehensive review)
- This transcript (`reports/grok_money_maker_audit_transcript_2026-05-15.md`)

All linked from `updates/index.html` following project format.

### 5. Key Hidden Insights Uncovered

- The COMMODITY "renaissance" numbers in the dashboard are still polluted by the May 13 COT over-emission scandal.
- The single best unshipped edge in the entire codebase is the **VIX-regime momentum filter** (works for both EQUITY and ETF).
- Production EQUITY universe is much worse than the research backtests (18 speculative names vs 30 clean large-caps).
- ETF has a genuinely strong, low-turnover, academic-grade strategy (11-sector rotation + VIX gate) that is mostly sitting on the shelf.

---

## 90-Day High-Level Roadmap (Summary)

**Phase 0 (Weeks 1-3):** Foundation
- DB Freshness Guardian fully enforced with GHA.
- Outcome tracking (paper + resolved) made reliable.
- Symbol universe + liquidity audit completed for all classes.

**Phase 1 (Primary Bet):** COMMODITY Cleanup + Diversification
- Re-aggregate historical COT emissions.
- Diversify beyond CT=F into 5–6 liquid futures with hard concentration caps.
- Wire full execution stack (sizing, slippage, kills).

**Phase 2 (Strong Parallel):** EQUITY
- Wire the discovered VIX-regime filter.
- Expand production universe to clean large-caps.
- Add real SEC/EDGAR depth for PEAD.

**Phase 3 (High-ROI Tertiary):** ETF
- Activate sector rotation emitter + VIX gate as default.
- Low effort, high diversification benefit.

**CRYPTO:** Aggressive pruning + universe shrink (maintenance mode).

**FOREX / BOND / Futures / Penny-Meme:** Data collection + research only.

---

## Notes on the Audit Dropdown (`findtorontoevents.ca/audit`)

The dropdown currently covers the main classes well:
- COMMODITY, EQUITY, ETF, CRYPTO, FOREX, BOND

**Gaps explicitly called out by user:**
- **Futures** — treated separately from general COMMODITY in some contexts; currently weak or under-built.
- **Penny Stocks + Meme Coins** — either not properly segmented or performing worse than a coin toss. Needs its own dedicated deep-dive category and likely heavy quarantine.

Future subagent work will treat "Low-Quality Equities (Penny/Meme)" as a distinct high-risk bucket.

---

## Next Actions (Immediate)

1. Wait for any remaining subagent output (FOREX, BOND, etc. if launched).
2. Commit all new reports + this transcript on a clean docs branch.
3. Spawn next wave of subagents for the missing categories.
4. Begin Phase 0 foundation work (DB Freshness enforcement + outcome tracking).

---

**This transcript is the censored record of the strategic "bigger picture" session** that shifted the project from idea-generation mode into focused, evidence-driven execution mode.

All decisions above were made in coordination with the `money-maker-continual-improve` skill and the live subagent fleet.

*End of transcript.*