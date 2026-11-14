# Focus Decision — hilarious-seer Recommendation

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Basis:** SubQ comparison (12 candidates, 7 dimensions), peer adjudication (6 disputes), 3,500-row ledger re-analysis

---

## Summary

| Slot | Asset Class | Strategy | Rationale | Confidence |
|------|-------------|----------|-----------|------------|
| **1** | **CRYPTO** | Vol-targeted trend (ITERATION-005) | Best evidence, fixable blocker, highest peer consensus | Medium-High |
| **2** | **EQUITY** | RSI(2) on SPY/QQQ (H10) | Closest to proven, cleanest forward path, positive margin | Medium |
| **Diversifier** | **ETF** | Multi-asset trend | Most robust theoretical premium, reduces portfolio vol | Low-Medium |
| **Income sleeve** | **BTC carry** | Funding-rate spread | Low-risk, low-return, capital-intensive | Medium |

**Not recommended:** FOREX, BONDS (pure gap, no evidence), FUTURES/COMMODITIES (BLOCKED), MUTUAL FUNDS (structurally incompatible), VWAP (REJECTED)

---

## Why CRYPTO is Slot 1 (Despite Losing −837.8pp)

**The paradox:** CRYPTO is the worst-performing class in the ledger but the best candidate for profitability.

**Why:**
1. **The loss is explained by one fixable defect.** 98.8% of CRYPTO losses (−832.4pp of −837.8pp) come from stop fill slippage. One system (`kimi_riseoftheclaw`) accounts for 94% of that leak. Fix the fill → the class becomes measurable.
2. **Best evidence base.** ITERATION-005 has the strongest statistical backing of any strategy in the repo: net Sharpe 2.13, t=5.56, 10/10 assets positive, maxDD −17% vs B&H −36%.
3. **Highest peer consensus.** All 7 worktrees agree CRYPTO has the best chance after data fixes.
4. **Fix is already deployed.** Gap-aware fill was implemented today. Forward measurement can begin immediately.

**The caveat:** ITERATION-005 was downgraded from "PROVEN" to "best candidate" in peer adjudication. It tested absolute return > 0, not > benchmark. B&H of the same 10 assets had Sharpe ≈2.2. The value is drawdown control, not raw outperformance. **We must restate vs B&H before claiming alpha.**

**The test:**
- Forward test POSITION horizon only (n≥100, PF≥1.3, WR≥55%)
- Paired bootstrap vs B&H: pass_95 must be true
- 90-day paper trading before real capital

---

## Why EQUITY is Slot 2 (The Only Positive-Margin Class)

**childlike-airport's finding:** EQUITY is the only class with measured positive margin (+0.323% per trade vs 0.30% requirement) and the best-behaved exit bucket (TIME_EXIT WR 61.4%, PF 1.988).

**Why I concur with childlike-airport:**
1. **No major defect found.** Stops are respected (0.91× planned vs realized). No fill slippage crisis.
2. **Cleanest forward path.** H10 RSI(2) needs only a frozen-parameter forward test. No infrastructure build required.
3. **Lowest cost of being wrong.** A negative result just removes near-break-even emissions.

**The caveat:** H10 is borderline. DSR 0.9365 < 0.95. Single-day dependence (+11.20% on 2025-04-09). 2-day-lag Sharpe drops to 0.696. It may be beta, not alpha.

**The test (pre-registered):**
- 24-month history, n≥500 closed equity trades
- Benchmark: SPY total return (not zero)
- Gate: OOS Sharpe ≥ SPY Sharpe AND PF ≥ 1.15
- Stability: first-half PF ≥ 1.05 AND second-half PF ≥ 1.05
- Kill condition: fails any line → EQUITY is beta, stop emitting

---

## Why ETF is the Diversifier (Not a Primary Edge)

**The theoretical case:** Multi-asset trend is the most robust documented risk premium. The $300B+ CTA industry is built on it. It performs well in crises (trend gets short equities, long bonds/gold).

**Why it's not a primary focus:**
1. **No repo evidence yet.** H16 failed SPA (p=0.488). H18 WF was borderline (0.37).
2. **Long build time.** Needs 10+ year history, 50 ETFs, risk-parity weighting, roll handling.
3. **Lower return potential.** Expected Sharpe 0.4–0.8 vs CRYPTO's 0.5–2.1.

**When to build:** After CRYPTO is proven and live. ETF is the natural second sleeve for portfolio construction.

---

## Why MUTUAL FUNDS Are Excluded (Structural, Not Optional)

**The user asked:** "Mutual funds is very high chance to be profitable — what about a subset needing less money in, lower maintenance fees, less capital required?"

**The answer:** Mutual funds ARE likely profitable over long horizons — because of the **equity risk premium**, not because of any prediction edge. This system adds nothing to them. They are structurally incompatible with the pick-trading model (monthly NAV, no intraday TP/SL, frequent-trading limits).

**The alternative:** **ETFs.**

| Feature | Mutual Fund | ETF |
|---------|-------------|-----|
| Intraday trading | No | Yes |
| Expense ratio | 0.60–1.20% (active) | 0.03–0.20% (index) |
| Minimum investment | $1,000–$3,000 | $0 (fractional shares) |
| Maintenance | Annual rebalancing | Same |
| Tax efficiency | Lower (capital gains distributions) | Higher (in-kind creation) |
| Live PnL | No | Yes |

**Recommendation:** If the user wants low-cost, low-maintenance, low-capital exposure, use **broad-market index ETFs** (VTI, VOO, VXUS) instead of mutual funds. These are procurement decisions, not research problems. The system should track them as portfolio ballast, not as pick targets.

---

## What I Would NOT Do (Explicit Exclusions)

| Temptation | Why Not | Peer Source |
|---|---|---|
| Deploy VWAP mean reversion (Sharpe 3.76) | **REJECTED** — fatal annualization error; real Sharpe ~1.18 | finpredict-v2, finpredict-v3 quant-audit |
| Claim ITERATION-005 is "PROVEN" | Downgraded to "best candidate"; must restate vs B&H | finpredict-v3 quant-audit |
| Flip ML confidence thresholds without retrain | Data/leakage issues dominate; needs retrain + parity | scratch-hippodraco |
| Unblock FUTURES/COMMODITY without real feed | Crypto proxies = statistical malpractice | scratch-hippodraco, finpredict-v2 |
| Add mutual funds as a pick class | Monthly NAV incompatible; no intraday edge possible | All peers |
| Mine more strategies (beyond 683) | N≈658 ⇒ ~32.9 false positives by chance | finpredict-v3 |
| Tune commodity COT until it passes | 4-of-170 problem; re-fitting is overfitting | childlike-airport |

---

## 90-Day Success Criteria

**Day 90 success is NOT "profitable."** It is:

1. **One class (CRYPTO) with a pre-registered, benchmark-relative result and a known trial count.**
2. **One class (EQUITY) with a clean forward OOS result.**
3. **Trustworthy measurement:** all PnL units correct, all prices live, all stores reconciled.

That is the first point at which "is this profitable?" becomes a question this repo can answer.

---

## Resource Allocation Recommendation

| Priority | Allocation | Focus |
|----------|-----------|-------|
| P0 | 50% | Data fixes (PnL units, price freshness, zombie drain) |
| P1 | 30% | CRYPTO trend (forward test, benchmark restatement) |
| P2 | 15% | EQUITY H10 (clean forward OOS) |
| P3 | 5% | ETF trend (database build, backtest) |

---

## Final Recommendation

**Focus on CRYPTO and EQUITY.** Fix the data first. Prove CRYPTO trend with benchmark-relative tests. Run EQUITY H10 clean forward. Add ETF only after the first two are live. Everything else is blocked by prerequisites or rejected by evidence.

**Do not deploy anything until Phase 0 is complete.** No PnL claim is trustworthy on broken data. Phase 0 is the foundation. Everything else is decoration.
