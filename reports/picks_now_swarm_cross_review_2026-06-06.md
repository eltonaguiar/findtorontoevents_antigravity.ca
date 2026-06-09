# 2026-06-06 Swarm Cross-Review: picks_now_professional.py (RISK_OFF picks)

**Context:** Live page deployed for the 2026-06-06 RISK_OFF multi-asset quant screener output (tools/picks_now_professional.py + audit_dashboard/data/picks_now.json + reports/PICKS_NOW_2026-06-06.md). Top actionable: AMZN 133 (EQUITY, 62 analysts, TREND+DIP, DB n=5 WR=20% weak), AVGO 128, GOOGL 121, QQQ/IWM ETFs ~96, TLT/IEF BONDS safest low-vol 75, FOREX mean-rev, CRYPTO weak. Regime: RISK_OFF. ELI5 + vol-adjusted sizing + DB edge overlay. 0/9 money-ready per verdict (n>=100 clean, WR>=50, PF>=1.5, MDD<20).

**Method:** LiteLLM proxy alive (models: paid/free-mode-large, nvidia-deepseek, openrouter-ring-1t, claude-haiku, etc.). Used `python3 tools/consult_multi.py --fanout diverse5` (nvidia/kimi-k2.6, groq/qwen3-32b, cerebras/llama3.1-8b [404 err], together/llama-3-8b, fireworks [412 err]) with full leakage-aware prompt (Goal #1 0/9 + recency + 14d/48h + DB weaknesses + ELI5 + sizing + regime context block). Results in /tmp/picks_swarm_review_2026-06-06/. Parallel subagent synthesized (read_file/grep only on outputs + prompt).

**Synthesis (rigorous, from 3 successful providers; quotes/paraphrases):**

**Edge/DB:** Mostly beta + analyst momentum + technicals in selloff, **not statistical alpha**. DB 10% weight = **noise** (AMZN n=5 WR20% avg_pnl=-0.63; AVGO n=18 WR=0% negative). "DB overlay adds NOISE, not value... anecdotal... violates basic thresholds." "Inconsistent" with 0/9 admission yet still scoring/labels STRONG_BUY on tops. Core: "beta-capture + analyst-momentum ... masquerading as edge-driven."

**Risk/sizing (RISK_OFF):** Vol-adjusted (ATR/Kelly, halved high-vol) "defensible" but **regime-naïve**. AMZN 28%vol 5% size / SL 4.5% "~0.16 std dev. Stop too tight... whipsaw." AVGO 71%vol "Should be 0% or tiny." Equity concentration (top-3 + flagged ETFs still promoted = "Gate failure"). Bonds (TLT/IEF) "BEST RELATIVE" / "safest" but under-ranked. "In RISK_OFF, buy-the-dip on momentum is precisely the wrong regime."

**ELI5 honesty:** **Partially cherry-picked / overclaims.** AMZN ELI5: "likely to bounce back", RSI "below the normal range... undervalued", Bollinger "rarely stays below for long" — unsubstantiated (no prob, no DB support WR=20%, survivorship bias in bull markets, factually imprecise). "Missing from ELI5: DB... buried in data table, not narrative." "omits ... 0/9 money-ready." Good that tool states 0/9 in risk note, but "cognitive dissonance" with STRONG_BUY labels on weak-history names.

**Per-class/recency:** BONDS/qualified FOREX (GBP n=114 ~59%WR) "strong RISK_OFF play". EQUITY "AVOID or 1% spec". ETFs "HARD PASS" (conc+beta). CRYPTO "AVOID" (negative mom, low DB). **14d/48h pick_summary_stats + DB recency + forward (48h delay paper) MANDATORY** before any sizing. "If RISK_OFF persists >3d, invalidate TREND+DIP." "Verify no cluster of -4.5% SL hits."

**Verdict + recs (4/10 or "low confidence" / "not ready to paper these specific picks today"):** Attractive bridge signals exist, but weak DB on tops, 0/9 reality, ELI5 overclaims, regime-naive sizing/conc, missing recency/forward = Goal #1 non-compliant for promotion/sizing.

**Top 3 concerns:**
1. 0/9 + DB as noise/inconsistency (honesty/edge failure).
2. ELI5 overclaims + cherry-picking (misleading narrative).
3. RISK_OFF mismatch + concentration gate failure (risk/recency exposure).

**Actionable code changes (synthesized; implemented in follow-up subagent edit):**
- **DB gate (in score() before W_DB_EDGE):** if n < 20 (or 30): db_w=0; flag insufficient. elif n<100: capped 5%. Only high-n + WR>50% + PF>1.5 gets full. If avg_pnl<0: floor 0. (Pre-score/ELI5.)
- **ELI5 always-inject (in builder):** if db_n<20 or db_wr<45: append exact "Honesty caveat: DB n=... WR=... (below threshold). 0/9 ... ALWAYS verify 14d/48h ... NFA/paper only."
- **Regime-conditional (in risk_off/JSON + main):** prefix based on regime; conditional weights (halve mom/analyst in RISK_OFF); surface in JSON for web (picks-now.html etc.).

**Files:** Swarm outputs /tmp/picks_swarm_review_2026-06-06/{nvidia__..., groq__..., together__...}.md + run.log + prompt. Code fixes in tools/picks_now_professional.py (py_compile OK). Prior review card in updates/index.html.

**Next:** Re-verify with 14d/48h panels + concentration. Paper only (TV skill). Implement further (regime filter, conc cap, DSR proxy). Re-swarm after gates. Document this in updates/ (before AUTO marker). NFA.

Refs: CLAUDE.md Goal #1 + recency + 0/9 + deep-dive + Wire-Up; AGENTS.md (subagents + doc every + own changes); current picks_now.json + MD + prior updates 2026-06-06 card.
