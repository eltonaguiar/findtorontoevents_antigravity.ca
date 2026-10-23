# Refined Investment Strategy — Mutual Funds/ETFs First (2026-10-23)

**Author:** Zoo (subagent) · **Date:** 2026-10-23 · **Scope:** Prioritize Mutual Funds/ETFs as the primary allocation, with per-asset-class viability analysis and cross-agent synthesis.

> *Not financial advice. Research/educational only. Past performance does not guarantee future results.*

---

## 1. Priority 1 — Mutual Funds/ETFs

The evidence across every agent (INCEPTION, OpenCode BEAM, Grok, GHCopilot, Poolside/KiloCode, Buffy) converges on one actionable conclusion: **the only durable, forward-tested, cost-inclusive edge is owning a broad low-fee index**. The winner-hunt backtest screened **599 strategies → 0 ELITE / 0 SURVIVOR**, while the mutual-fund walk-forward found the picker's mean net CAGR (**11.89%**) underperforms simply holding **XEQT (14.25%)** or **TDB902 (17.08%)** net of costs. The allocation priority is therefore **Mutual Funds/ETFs first**, exclusively passive, fee-minimized.

### 1.1 Primary vehicles

| Fund | Type | Net CAGR | MER | Role |
|------|------|---------:|----:|------|
| **XEQT** (iShares Core Equity ETF Portfolio) | All-equity ETF of ETFs (CAD) | 14.25% | ~0.20% | Core Canadian all-equity allocation |
| **TDB902** (TD e-Series U.S. Index Fund) | Low-cost US index mutual fund (CAD) | 17.08% | ~0.34% | US equity core (e-Series) |
| **BKLC** (BNY US Large Cap Equity) | Zero-fee S&P 500 ETF (US) | 18.42% | **0.00%** | Cheapest US broad index |
| **VOO / FXAIX / VFV.TO** | S&P 500 index | — | 0.03–0.15% | US index core alternatives |
| **SHY / BKAG** | Short-term bonds / zero-fee broad bond | — | 0.00–0.15% | Cash-equivalent / bond sleeve |

### 1.2 Execution conditions (minimum buy-in, fees, no-fee status)

**XEQT (ETF in — trades like a stock on any brokerage**
- **Minimum buy-in:** 1 share (trades continuously; no contribution minimum, no $100 minimum).
- **Monthly fees:** none — it is a listed ETF, not an auto-withdrawal mutual fund.
- **No-fee status:**
  - **Questrade:** ETF buys are **commission-free** (only sells carry a small commission). XEQT is in Questrade's free-ETF list.
  - **RBC Direct Investing:** no monthly account/admin fee for most account types; ETF buys incur a flat commission (~$9.95) unless enrolled in a commission-waiver program (e.g. RBC's regular ETF purchase plans or promotions). No recurring monthly fee on the holding itself.

**TDB902 (TD e-Series mutual fund) — needs a TD Direct Investing account + e-Series enrollment**
- **Minimum buy-in:** $100 initial per fund; **$25** per subsequent purchase. This minimum is **waived** when enrolled in TD's **automatic contribution plan** ($25+/month).
- **Monthly fees:** none on e-Series funds themselves, but TD Direct Investing charges a **$25/yr (or similar) administration fee** on account balances **under $15,000** unless you (a) are enrolled in an auto-contribution plan, or (b) hold a qualifying package. Keep balances above the threshold or automate contributions to avoid it.
- **No-fee status:** e-Series funds have a rock-bottom MER (TDB902 ~0.34%) and no sales load (no front-end/back-end load). RBC equivalent delivery of US index exposure via **RBC e-Series equivalents** or a US-listed zero/low-fee ETF (BKLC/VOO) avoids the e-Series account requirement.

**Net guidance:** in Canada, start with **Questrade + XEQT** (free ETF buys, no admin fee, all-equity one-ticket core). If a TD account is already open, add **TDB902** via auto-contribution to waive the $100/$25 minimum and the sub-$15k admin fee. Use **BKLC** where US-listed trading is accessible to get a true 0.00% expense ratio.

---

## 2. Asset Class Viability Analysis

Verdict per class: **viable as a passive core** vs **not viable as an active/skill play**.

| Asset class | Viable? | Why |
|---|---|---|
| **Mutual Funds/ETFs** | ✅ Viable (passive core) | Only class with a forward-tested, cost-inclusive edge — the fee edge. Walk-forward: XEQT 14.25%, TDB902 17.08% net CAGR beat the active picker (11.89%). No active fund edge survives. |
| **Equity / Stocks** | ⚠️ Index core only | No certified individual-stock pick. Index (FXAIX/SWPPX/VFIAX, Sharpe ~1.03) is viable; single-stock "alpha" claims (rs-breakout-scout, AAPL RSI) are weak/thin (n<100, CI dips below 1.0). |
| **Crypto** | ❌ Not viable (no real-money) | No PROVEN class. Only CANDIDATE SHORTs (prediction_market_consensus PF 2.11, crypto_short_rsi3050 PF 2.16). High volatility, corrupt historical scoreboard, frozen-exit bug inflated win-rates. No real-money allocation. |
| **Bonds/Fixed Income** | ✅ Viable (cash-equivalent sleeve) | SHY (cash-equiv, Sharpe 1.05), BKAG (free broad bond). No proven tactical bond pick — the only candidate (bond_yield_curve_slope, PF 9.44) rejected on n=18<100. |
| **Commodities** | ⚠️ Hedge baseline only | GLD/IAU viable as a hedge reference (not a skill play). Tactical commodity signals rejected/weak (commodity_term_cot REJECTED). |
| **Forex** | ❌ Not viable (abstain) | Data contaminated / thin. All leads flagged (myfxbook_retail_contrarian, forex_zscore_200d_fade) — abstain until Phase-0 data integrity passes. |
| **Futures** | ❌ Not viable (blocked) | PF 0.29, WR 46.1% — clearly negative edge. Abstain. |
| **Penny / Memecoin / Options** | ❌ Not viable | No honest, forward-tested candidate in any agent's output. No recommendation. |

**Why the allocation pivots to funds/ETFs:** every directional (active) class fails the strict gates — either no sample (n<100), no profit-factor edge (PF<1.5), contaminated data, or a corrupt scoreboard. The **only** measurement that survived re-tests is the passive index net-of-cost return. That is not "alpha"; it is the arithmetic of fees — and it is the only edge that is *guaranteed* to persist.

---

## 3. Cross-Agent Synthesis

All six agents independently converged on the same verdict — **no directional class is MONEY-READY / PROVEN** — but they differ in *what they highlight* within that shared "no winner" frame.

| Agent | Funds/ETFs stance | Other-class picks (CANDIDATE only) | Why they differ from the fund-first view |
|---|---|---|---|
| **OpenCode BEAM** | "Always VOO/FXAIX" (walk-forward YES) | Crypto SHORT prediction_market_consensus (PF 2.11); bond_yield_curve_slope (PF 9.44); forex_zscore_200d_fade SHORT (PF 1.44) | Treats index as the *baseline* and spends more energy listing per-class CANDIDATEs; its bond/forex/futures classes mostly FAIL/REHAB. |
| **Poolside/KiloCode** | Master plan: no agent proved a class; ETF TAA (MRBB+200d) RESEARCH-VAL | crypto_short_rsi3050 SHORT (PF 2.16, null 99.8th pct — strongest null rejection) | Focuses on statistical rigor; highest-confidence single candidate is a crypto SHORT, but still not forward-proven. Emphasizes risk-control rotation over fund-picking. |
| **Grok** | "Boring Billion" (FZROX 50/FZILX 25/FNDF 10/SHY 10/GLD 5); fund ranker "product" | GLD/DBC core; commodity_term_cot REJECTED; myfxbook_retail_contrarian (PF ~2.43) | Won the broad-index "boring" framing, breaking it into a multi-ETF barbell rather than a single XEQT ticket. |
| **GHCopilot** | BKLC/BKAG 0% fee; FCNTX/VPMCX diligence only; XEQT/VBAL CA | SHY cash-equiv (MDD 5.71%); rs-breakout-scout LONG weak; forex abstain | Closest to the fund-first conclusion — emphasizes 0% fee funds and honesty about active-fund drawdowns (MDD ~49–52%). |
| **Buffy** | Monthly TAA (MRBB+200d, IBS+200d) | Crypto SHORT RSI(14) 30–50 (PF 2.16, strong) | Adds a tactical rotation overlay on top of the index core — the only "extra" that survived as a *risk-control* tool, not alpha. |

**Why the picks differ:** the differences are about **emphasis and methodology**, not contradictory data. OpenCode and Grok hunt for per-class CANDIDATEs (and report more of them). KiloCode applies the strictest statistical gates (so it yields the *fewest* defensible candidates). Buffy adds a tactical overlay to reduce drawdown. All six agree on the bottom line: **no active/directional pick is investable; the cheapest broad index is the only defensible core.** This report therefore synthesizes them into the fund-first priority.

---

## 4. Recommended Allocation (research/educational framework — not automated trading)

1. **Core (70–80%):** XEQT (Questrade, free ETF buys) or TDB902 (TD e-Series, auto-contribution to waive minimums/admin fee); BKLC where US-listed access exists.
2. **Bond/cash sleeve (10–20%):** SHY (cash-equivalent) + BKAG (free broad bond).
3. **Hedge reference (≤10%):** GLD/IAU gold, only as a hedge.
4. **Do not deploy** any CANDIDATE (crypto SHORTs, tactical bond slope, forex fades) into real money until forward cohorts seal and the scorekeeper is repaired on clean data.
5. **Avoid** penny/memecoin/options/futures — no honest candidate exists.

---

## 5. Required Disclaimer

> *Not financial advice. Research/educational only. Past performance does not guarantee future results. Fund fees, minimums, and no-fee program details (e.g. Questrade free ETF buys, RBC Direct Investing commissions, TD e-Series $100/$25 minimums and sub-$15k admin fee) are subject to change and should be verified with the applicable institution before acting.*
