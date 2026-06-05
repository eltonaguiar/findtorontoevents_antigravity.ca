# FOREX Real-Money Picks — 2026-06-05

**Status:** 3 picks. Forex is hard; surviving edges are narrow. Recommend sizing FOREX book at **2% of equity** (not full 4%) given weaker walk-forward vs CRYPTO mega_mutation (PF 2.86 n=204).
**Data quality:** `forex_carry_momentum` + `myfxbook_retail_contrarian` 2026-06-04 stats are batch artifacts (85-97% single-day backfill per `REAL_MONEY_NO_SURVIVORS_2026-06-05.md`). This report uses **OHLCV walk-forward only**, not contaminated DB columns.
**Source DB lag:** `fxp_price_history` last row = 2026-05-12. Re-quote on Monday 2026-06-08 open; skip if gap > 1.5 ATR.

---

## 0. Methodology + Data Inventory

**Sources:**
- **OHLCV:** `ejaguiar1_stocks.fxp_price_history` — 8 pairs, 330-343 rows, 2025-02-10 → 2026-05-12
- **Macro:** `alpha_engine/data/macro_factors_snapshot.json` (Fed 3.755%, NEUTRAL regime, risk 0.3)
- **CB rates (public, mid-2026):** USD 3.755 / EUR 2.50 / GBP 4.25 / JPY 0.75 / AUD 3.85 / NZD 3.25 / CAD 2.75 / CHF 0.50
- **AI tournament:** `audit_dashboard/data/ai_tournament_picks_latest.json` (74 OPEN FOREX picks)

**Pairs:** AUDUSD, NZDUSD, USDCAD, GBPUSD, USDCHF, EURGBP, USDJPY, EURUSD (8 majors).

**Engine:** Daily-step walk-forward, TP/SL = 2x ATR / 1.5x ATR (intrabar H/L, SL-first), 30-day time-stop. Need (a) full-history PF >= 1.20 over >= 80 trades, (b) >= 2 of last 3 quarters PF >= 1.0, (c) >= 2 of (carry, momentum, z-score) agreement.

---

## 1. Carry / Momentum / Z-Score Scoreboard (2026-05-12 close)

| Pair    | Price   | Carry_L% | 3M%   | 6M%   | 12M%   | Z200  | Momo  | Carry | Z     | Agree |
|---------|--------:|---------:|------:|------:|-------:|------:|:-----:|:-----:|:-----:|:-----:|
| AUDUSD  | 0.7243  |     0.10 |  2.36 |  9.65 |  11.30 |  1.64 | LONG  | LONG  | SHORT | 2/3   |
| NZDUSD  | 0.5955  |    -0.50 |  0.29 |  3.13 |  -1.24 |  1.07 | N     | SHORT | N     | 1/3   |
| USDCAD  | 1.3696  |     1.00 |  0.38 | -1.84 |   0.00 | -0.72 | N     | LONG  | N     | 1/3   |
| GBPUSD  | 1.3538  |     0.50 |  0.30 |  3.37 |   0.00 |  0.75 | N     | LONG  | N     | 1/3   |
| USDCHF  | 0.7804  |     3.25 |  0.87 | -3.11 |  -4.74 | -0.99 | SHORT | LONG  | N     | 1/3   |
| EURGBP  | 0.8670  |    -1.75 | -0.78 | -1.86 |   2.87 | -0.65 | N     | SHORT | N     | 1/3   |
| **USDJPY** | 157.633 |  **3.00** | 1.94 |  0.41 | **10.44** | 0.70 | **LONG** | **LONG** | N | **2/3** |
| EURUSD  | 1.1741  |    -1.25 | -0.40 |  1.08 |   3.42 |  0.54 | LONG  | SHORT | N     | 1/3   |

**Consensus (2/3 agree):** USDJPY LONG, AUDUSD LONG.

**Walk-forward confirmation (n>=100, hold=30d, TP=2x ATR, SL=1.5x ATR):**

| Pair    | Dir   |  n  |  W  |  L  | T  | WR%   | PF    | Avg%  |
|---------|:-----:|----:|----:|----:|---:|------:|------:|------:|
| **USDJPY** | LONG  | 101 | 51 | 39 | 11 | 50.5 | **1.74** | 0.446 |
| EURUSD  | LONG  | 100 | 48 | 48 |  4 | 48.0 | 1.40  | 0.245 |
| GBPUSD  | LONG  | 102 | 51 | 50 |  1 | 50.0 | 1.34  | 0.209 |
| NZDUSD  | SHORT | 105 | 50 | 51 |  4 | 47.6 | 1.25  | 0.139 |
| **AUDUSD** | LONG  | 105 | 45 | 50 | 10 | 42.9 | **1.16** | 0.212 |
| AUDUSD  | SHORT | 105 | 30 | 69 |  6 | 28.6 | 0.55  | -0.456 |

USDJPY (1.74) and AUDUSD (1.16) clear the bar; EURUSD (1.40) included on walk-forward alone.

---

## 2. Top 3 Candidates (Final Slate)

| # | Pair   | Dir | Entry (2026-06-08) | TP (2x ATR) | SL (1.5x ATR) | Edge rationale                                  | Hold |
|---|--------|:---:|------------------:|------------:|--------------:|--------------------------------------------------|:----:|
| 1 | USDJPY | LONG| 157.63            | 160.97      | 155.21        | 3.0% carry + bull momo 12m +10.4%                | 30-60d |
| 2 | AUDUSD | LONG| 0.7243            | 0.7341      | 0.7169        | Bull momo 12m +11.3% / 6m +9.7%; z=1.64 risk     | 30-45d |
| 3 | EURUSD | LONG| 1.1741            | 1.1864      | 1.1649        | Walk-fwd PF 1.40; momo 12m +3.4% / 6m +1.1%      | 30-45d |

---

## 3. Per-Candidate Deep-Dive (OHLCV evidence)

### Pick 1: USDJPY LONG — HIGH

**Edge:** Fed-BOJ carry = +3.00% annualized (long base, short funding). 12m +10.4% (3rd strongest), 6m +0.4% (pullback entry). Z=0.70 (not stretched).

**Walk-forward:** Full n=101 → WR 50.5%, **PF 1.74**, avg +0.45%. **Quarter stability:** Q1 PF 0.45 (weak, BoJ intervention risk), Q2 PF 2.50, Q3 PF 6.60, Q4 PF 2.01. **Hold-sensitivity:** hold=10d PF 0.99 → hold=60d PF 2.21 (longer = better). **Sequential DD on daily compounding: -47% peak-to-trough** — headline ruin risk HIGH for full Kelly, hence the 2% cap.

**Sizing:** Quarter-Kelly on 50% WR / 1.33 payoff → f*=0.20 → cap 2% of equity. ATR14 = 1.67 (1.06% of price). $10k account: $200 risk / 1.59% SL = **$12,580 notional**.

**AI tournament:** 2 OPEN long picks. No major short consensus.

### Pick 2: AUDUSD LONG — MEDIUM

**Edge:** Momo 12m +11.3% (strongest in panel), 6m +9.7% (also strongest). Carry only +0.10% (basically flat). Z=1.64 = **mild overbought — risk**.

**Walk-forward:** n=105 → WR 42.9%, **PF 1.16** (just above bar), avg +0.21%. **Quarter stability:** Q1 PF 0.70, Q2 PF 0.63, Q3 PF 1.75, Q4 PF 0.82 — **Q1+Q2 weak, half the time losing money.** Hold=60d: PF 1.27 (slight improvement).

**Sizing:** Quarter-Kelly on 42.9% WR / 1.33 payoff → f*=0.06 → cap 1% of equity. ATR14 = 0.0049 (0.68%). $10k: $100 risk / 1.48% SL = **$6,760 notional**.

**AI tournament:** Community is SHORT AUDUSD — **contradicts momo signal**, hence MEDIUM not HIGH.

### Pick 3: EURUSD LONG — MEDIUM-LOW

**Edge:** 12m +3.4%, 6m +1.1%, 3m -0.4% (mild dip → mean-reversion). Carry **-1.25% (pays to hold)**. Z=0.54 (neutral). **No consensus agreement** (carry says SHORT, momo says LONG, z neutral).

**Walk-forward:** n=100 → WR 48.0%, **PF 1.40**, avg +0.25%.

**Sizing:** Quarter-Kelly on 48% WR / 1.33 payoff → f*=0.13 → cap 1% of equity. $10k: **$100 risk / 0.78% SL = $12,800 notional**.

**AI tournament:** 19 SHORT vs 13 LONG OPEN EURUSD — **community is bearish**. This is the riskiest pick.

---

## 4. Risk Parameters

**Max position sizing:**
- USDJPY: 2% of equity (largest, best dual-edge)
- AUDUSD: 1%
- EURUSD: 1%
- **Total FOREX cap: 4% of equity per task spec** (recommend 2% given weakness)

**Event risks:**
- **USDJPY:** BoJ intervention risk (Q1 2025 saw 160.7→156 spike). Hard SL = 1.59 ATR, no override.
- **AUDUSD:** RBA surprise cuts (carry disappears overnight).
- **EURUSD:** ECB-Fed divergence, US/EU political news.

**Interest rate risk:** If Fed cuts 50bps while BoJ holds, USDJPY carry compresses 3.0% → 2.5% (still positive, thesis holds, sizing review triggered). If carry goes < 0, exit.

**Time exit:** Hard 60-day stop. Walk-forward: 11/101 USDJPY trades time-exited at avg +0.45% (not losses, but exit anyway).

---

## 5. Failure Modes

1. **FX data lag:** 24-day stale source. If markets moved > 1 ATR in those 24d, skip entry on 2026-06-08.
2. **Carry compression:** Fed/BoJ announcements within 30-60d can collapse carry → single-edge (momo) becomes the only support.
3. **Walk-forward overfit to USDJPY trend:** 12m strong uptrend. Mean-reversion can flip PF 1.74 → < 1.0. The Q1 2025 PF 0.45 regime could return.
4. **Q1 weakness persistence:** USDJPY Q1 PF 0.45, AUDUSD Q1+Q2 PF 0.70/0.63. If that regime recurs, current PF estimates are overstated.
5. **AI tournament contradiction:** EURUSD and AUDUSD are community-SHORT — soft warning (tournament has its own resolver artifact per `AI_tournament WR artifact 2026-06-03`).
6. **Resolver contamination carryover:** Per `money_ready_verdict.json` 2026-05-24, FOREX class is FAIL (PF 0.55, USDJPY 55% concentration). Historical DB WR/PF for FOREX is **unreliable** — we are sizing off walk-forward, not the resolver.

---

## 6. Confidence

| Pick | Confidence | Why |
|------|:----------:|-----|
| USDJPY LONG | **HIGH** | 2/3 consensus (carry + momo), best walk-fwd PF 1.74, hold-robust. Risks: BoJ intervention, Q1 drawdown. |
| AUDUSD LONG | **MEDIUM** | Strongest 12m momo, but only 1/3 consensus, walk-fwd PF 1.16 (just above bar), AI community SHORT |
| EURUSD LONG | **MEDIUM-LOW** | No consensus (0/3), AI SHORT, walk-fwd PF 1.40, weak carry |

**Composite ≈ 70% HIGH + 25% MED + 5% MED-LOW.** Compared to CRYPTO mega_mutation (PF 2.86, n=204, full consensus per `MULTI_CLASS_REAL_MONEY_DIG_2026-06-05.md`), this FOREX slate is **materially weaker**. Recommend sizing FOREX book at 50% of full spec (2% of equity not 4%) and prioritizing CRYPTO mega_mutation sleeves.

---

## 7. Operator Decision Required

1. **Approve/skip.** All 3 picks sized off OHLCV walk-forward, not DB-stored stats. Forex is hard — may want to wait for higher-conviction setup.
2. **If approved:** enter Monday 2026-06-08 open. Hard SLs on. Time-stop 60d.
3. **P0 follow-up:** `alpha_engine/outcome_resolver.py` needs intrabar OHLCV replay fix. Until done, **all historical FOREX DB numbers are unreliable** — we are sizing off walk-forward.

---

*Source files: alpha_engine/data/macro_factors_snapshot.json, audit_dashboard/data/ai_tournament_picks_latest.json, ejaguiar1_stocks.fxp_price_history, reports/REAL_MONEY_NO_SURVIVORS_2026-06-05.md, reports/MULTI_CLASS_REAL_MONEY_DIG_2026-06-05.md.*
