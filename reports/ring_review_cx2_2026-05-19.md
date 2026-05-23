# Ring-2.6-1T Independent Review — CX2 Final (2026-05-19)

**Model:** inclusionAI Ring-2.6-1T via OpenRouter (`inclusionai/ring-2.6-1t`)  
**Prompt source:** `tools/swarm/prompts/ring_session_review_cx2_2026_05_19.md`  
**Run dir:** `swarm_runs/ring_cx2_review_20260519/`  
**Raw bytes:** 7,437 | Tokens used: 5,350

---

## 1. Walk-Forward Harness: Ensemble vs. Intraday

**Recommendation: (b) — Intraday data is the priority fix. But understand why.**

The fundamental problem is statistical power, not signal diversity. With 14 daily observations per walk-forward window, you cannot distinguish edge from noise at any conventional significance level. An equal-weight ensemble of 14 signals that individually fail sign-stability (0/14 windows passing) is **garbage averaged, not garbage reduced**. The √14 variance reduction assumes uncorrelated signals — your equity momentum and regime signals are almost certainly highly correlated, especially during stress regimes where you'd most need diversification. Realistic diversification benefit is likely √2–√3× at best, not 3.7×.

**Intraday is the correct lever** because it attacks the root cause:
- 5-min bars → ~1,092 observations per 14-day window → you can actually run meaningful hypothesis tests
- Existing signal logic (rolling std, momentum) translates naturally to intraday with appropriate bar aggregation
- You retain the option to downsample to daily for walk-forward evaluation while generating higher-frequency signals

**Caveats and sequencing:**
1. Validate that regime signals (252-day rolling std) still make sense at intraday — you may need to recalibrate the lookback to something like 504 × 5min bars ≈ equivalent to 252-day
2. Intraday introduces microstructure noise, bid-ask bounce, and liquidity variation — filter low-volume bars
3. After intraday infrastructure is stable, *then* consider an ensemble layer on top

**TL;DR:** Fix sample size first, then worry about diversification. You can't ensemble your way out of insufficient power.

**Claude/swarm prior verdict:** Ensemble first (free, zero infra), then intraday.  
**Ring verdict: Intraday first (fixes root cause — statistical power).** Both agree intraday is the ultimate solution; Ring flags the ensemble assumption of uncorrelated signals as likely violated.

---

## 2. Ban Protocol Architecture

The hardcoded dict is a liability. Here's Ring's target architecture:

**Recommended schema (SQLite/Postgres table):**

```sql
CREATE TABLE ban_list (
    id INTEGER PRIMARY KEY,
    entity TEXT NOT NULL,           -- e.g., "TRXUSDT", "H-021"
    type TEXT NOT NULL,             -- symbol / strategy / source
    ban_type TEXT NOT NULL,         -- temporary / conditional / permanent
    reason TEXT NOT NULL,
    evidence_ref TEXT,              -- link to backtest/issue
    banned_by TEXT,
    ban_date DATE,
    review_date DATE NOT NULL,      -- auto-computed
    status TEXT DEFAULT 'active',   -- active / expired / permanent
    reviewed_by TEXT,
    review_outcome TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Tier durations:**
- `temporary`: 7/14/30 day auto-expiry
- `conditional`: persists until a specific re-test passes
- `permanent`: requires explicit senior sign-off

**Automation:**
- Scheduled job (daily) scans for `review_date <= today AND status='active'` → posts alert with evidence links
- Overdue items (TRXUSDT/CVX/XOM at 11 days) get escalated
- GHA workflow validates ban list integrity on each push (no orphaned references)

**Audit trail:** Every status change logged with who/when/why. No silent edits.

**Alignment with ban_protocol_audit_2026-05-19.md Rec 1:** Ring independently recommends same JSON/DB migration with review_date automation — confirms Rec 1+2 as highest priority.

---

## 3. Grok Code Quality: Systemic Prompting Fix

The root cause: **Grok was treated as an authority on formulas it doesn't actually know.** LLMs pattern-match plausible-looking math; they don't compute.

**Required prompting protocol going forward:**

**Step 1 — Formula pinning in system prompt:**
```
# DSR FORMULA (B&L 2014, eq. 4): norm.cdf((SR - E[maxSR]) / sr_std)
# DO NOT modify this formula. DO NOT multiply SR by norm.cdf().
# Copy exactly as stated above.
```

**Step 2 — Assertion block:**
```
Assertions (VIOLATIONS FAIL THE RESPONSE):
- DSR = norm.cdf((sharpe - mean_sharpe) / std_sharpe)
- DSR ≠ sharpe * norm.cdf(...)
- PBO requires CPCV combinatorial enumeration, NOT 1-WR²
```

**Step 3 — Multi-round correction log (prepend to every round):**
```
PRIOR CORRECTIONS (must be respected):
- Rounds 1-8: DSR was WRONG (sr * norm.cdf). Correct: norm.cdf((SR-E)/std).
- Rounds 1-9: PBO 1-WR² is WRONG. Never use this.
- Round 9: vol.mean() on scalar = 0 bug. Use series input.
```

**Step 4 — Separation of concerns:**
- Use Grok for orchestration, I/O, data pipelines, glue code
- **Human writes statistical formulas.** Grok wraps them.

**Step 5 — Mandatory unit test with hand-computed expected output** for every formula.

**Meta-lesson (Ring's words):** *"LLMs are excellent at plumbing, terrible at math. Treat them accordingly."*

---

## 4. H-035 Kill Verdict

**Ring verdict: Confirmed kill. Evidence is against edge, not regime-dependence.**

Reasoning:
- Sign-flipping without a regime classifier is noise. Genuine regime-dependent signal would show asymmetric behavior (strong in one regime, flat in another), not oscillation: SHORT +0.547 → −0.496 → +0.07, LONG −0.626 → +0.138 → −0.231.
- The "only in high-funding" hypothesis is unfalsifiable as currently structured. To test it requires: (1) ex-ante regime definition (e.g., 8h funding > p75 of 90-day rolling), (2) signal run ONLY in those windows, (3) consistent positive eff in filtered subset. None of this was done pre-kill.
- Funding carry is one of the most-arbitraged crypto strategies. Any settlement pressure is priced almost instantly.
- Sign-flip across consecutive windows = no stable direction = no edge.

**Pre-registration requirement to resurrect:** Register in hypothesis_registry.json with:
- Ex-ante regime classifier definition
- Minimum n per regime (≥50)
- OOS test plan for filtered subset

---

## 5. EQUITY Validation: Fastest Path to n≥100

**Ring recommendation: Extend time window + targeted universe expansion (combined)**

**Option A — Extend time window (fastest, ~30 min of work):**
- Extend from 1Y to 3Y lookback
- Expected yield: ~69 × 3 ≈ 207 picks (assuming similar pick rate)
- Risk: regime non-stationarity (momentum 2021-2023 ≠ 2024-2026)
- Mitigation: rolling 1Y sub-samples to check stability

**Option B — Systematic universe expansion (~1 week):**
- Add liquid names where momentum has economic rationale (high 12-2M return, sufficient volume)
- Pre-screen: exclude anything that degrades PF below 1.1 or WR below 45%
- Target: add 40-50 well-justified names → n≈110-120

**Ring's recommendation:** Option A first (3Y window), validate stability via rolling sub-samples, then Option B if still below 100 after extending. Avoid adding noise symbols to hit a target — regime consistency check is the guard.

---

## Summary of Ring Verdicts vs. Prior Consensus

| Question | Swarm/Claude Prior | Ring-2.6-1T | Alignment |
|---|---|---|---|
| Walk-forward fix | Ensemble first, then intraday | **Intraday first** (ensemble assumption violated) | PARTIAL — both agree intraday is final answer |
| Ban protocol | JSON registry + monitor script | DB table + automated review alerts | ALIGNED (same structure) |
| Grok prompting | Reject wrong formulas, use statistical_gates.py | Formula pinning + assertion blocks + correction log | ALIGNED + Ring adds concrete protocol |
| H-035 | TESTED_KILL | **Confirmed kill** — sign-flip = noise, not regime signal | FULLY ALIGNED |
| EQUITY n≥100 | Accumulate organic picks | Extend time window to 3Y first | NEW — actionable concrete path |

**Key new insight from Ring:** The ensemble √14 assumption of uncorrelated signals is likely violated — equity/regime signals correlate during stress. Intraday is the correct first fix. And for EQUITY: extend time window to 3Y as the fastest path to n≥100.
