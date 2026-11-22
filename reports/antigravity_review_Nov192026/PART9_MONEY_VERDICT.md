# PART 9 — The Money Verdict: what is actually the best use of the capital
**Author:** githubcopilot-mercury3AI · **Date:** 2026-11-22 · **Status:** VERDICT (round 1)

> ## ⚠️ CORRECTIONS APPLIED 2026-11-22 — read `PART11_PEER_REVIEW_RESPONSE_AND_CORRECTIONS.md`
> Two claims in this document are **WITHDRAWN** after peer review:
> 1. **"AOA delivered 10.33% CAGR — above the S&P 500's 10.01%"** — AOA's first data point is **2008-11-11**, so its own return series never contains the 2008 crash while SPY's does. On a **common window (2008-12→2026-11)** SPY returns **14.02%** vs AOA **10.33%**. The claim does not survive. AOA remains a reasonable *risk* product, not an index-beater.
> 2. **All MaxDD figures below are MONTH-END sampled and therefore too kind.** SPY daily max drawdown over the same period is **−55.2%**, not −50.8%. From now on every drawdown published is `MDD_daily` with `MDD_month_end` shown alongside.
>
> What survives unchanged: **no alpha in any asset class**, risk gain not return gain, and nothing sanctioned at zero forward observations.

**Reproducer:** `/tmp/p6/money.py` · window **2007-05 → 2026-11** (234 months — contains 2008, 2020 and 2022) · $10,000 start · total return · 20bp per unit turnover · trend signals use data through **t−2** (the *conservative* of the three timing conventions, so nothing here can be accused of look-ahead)

---

## 0. Direct answer to "should we just buy a GIC?"

**No — not for capital you will not need for 10+ years.** Measured cost of full safety over this window: a 3.5%/yr GIC turns $10,000 into **$19,826**; simple S&P 500 buy-and-hold turned it into **$64,237**. The GIC "wins" on certainty and loses about **$44,411** of terminal wealth.

**But the honest middle is better than either extreme**, and that is the actual finding: a 100% equity position with a mechanical trend filter turned $10,000 into **$59,923** — 94% of the buy-and-hold outcome — while capping the worst drawdown at **−19.5%** instead of **−50.8%**. On a risk-adjusted basis nothing in the comparison beats it except a trend-gated 60/40 (Sharpe 1.011).

And the single most useful sentence in this document: **a plain, buyable 80/20 allocation ETF (AOA) delivered a higher CAGR than the S&P 500 (10.33% vs 10.01%) with less than half the drawdown (−23.0% vs −50.8%) and no rules to follow, no trading, no monitoring.** If the requirement is "one product, set and forget", that is the answer the data supports — not because it is clever, but because diversification plus rebalancing is the only free lunch and it is measurable.

---

## 1. The full comparison

| # | option | CAGR% | vol% | Sharpe | MaxDD% | worst 12m% | longest under-water (mo) | % +months | $10k becomes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **GIC 3.5% (ASSUMED, guaranteed)** | 3.56 | 0.0 | n/a¹ | 0.0 | +3.6 | 0 | 100 | **$19,826** |
| 2 | T-bills (SHY, measured) | 1.85 | 1.5 | n/a¹ | −5.4 | −5.1 | 36 | 65 | $14,294 |
| 3 | Bonds (AGG) | 2.95 | 4.6 | 0.648 | −17.1 | −15.6 | 76 | 59 | $17,615 |
| 4 | 60/40 SPY+IEF | 7.62 | 9.6 | 0.818 | −29.5 | −26.0 | 35 | 65 | $41,843 |
| 5 | VBIAX (Vanguard Balanced **mutual fund**) | 7.44 | 10.2 | 0.757 | −32.5 | −27.6 | 36 | 66 | $40,511 |
| 6 | VASGX (LifeStrategy Growth **MF**, 80/20) | 6.70 | 13.3 | 0.557 | −47.6 | −40.6 | 61 | 64 | $35,408 |
| 7 | VWELX (Wellington **MF**) | 7.73 | 10.4 | 0.767 | −32.6 | −28.7 | 37 | 64 | $42,702 |
| 8 | AOR (iShares 60/40 **ETF**) | 7.30 | 10.1 | 0.752 | −20.8 | −17.7 | 26 | 63 | $35,537 |
| 9 | **AOA (iShares 80/20 ETF)** | **10.33** | 13.0 | 0.826 | **−23.0** | −18.9 | 25 | 66 | **$58,707** |
| 10 | SPY buy & hold | 10.01 | 15.6 | 0.693 | −50.8 | −43.4 | 52 | 65 | $64,237 |
| 11 | Global equity EW buy & hold | 6.40 | 14.9 | 0.493 | −51.0 | −41.5 | 66 | 64 | $33,508 |
| 12 | Mutual-fund basket EW | 8.08 | 13.5 | 0.645 | −44.2 | −38.1 | 39 | 65 | $45,530 |
| 13 | **SPY + 10-month SMA (trend)** | **9.62** | 11.4 | **0.863** | **−19.5** | −18.6 | 24 | 66 | **$59,923** |
| 14 | Global EW + 10-month SMA | 6.71 | 10.8 | 0.657 | −25.8 | −24.7 | 32 | 66 | $35,464 |
| 15 | Mutual-fund basket + 10-month SMA | 8.11 | 9.8 | 0.850 | −18.5 | −17.0 | 23 | 67 | $45,771 |
| 16 | **60/40 with SPY trend leg** | 7.24 | 7.2 | **1.011** | **−11.3** | −10.1 | **18** | 65 | $39,056 |

¹ **Sharpe is not meaningful for series with near-zero volatility.** T-bills show 1.212 and the GIC shows a division-by-zero. Reporting either as "risk-adjusted outperformance" is exactly the kind of number-laundering this project exists to stop. Cash is ranked on certainty, not Sharpe.

---

## 2. The three defensible answers, depending on the constraint

### If the question is "best risk-adjusted outcome, and I will follow one rule monthly"
**60/40 with a trend-gated equity leg** — Sharpe **1.011**, MaxDD **−11.3%**, worst 12-month **−10.1%**, never underwater more than **18 months**, 7.24% CAGR. This is the most survivable profile in the entire comparison: a drawdown one-fifth of buy-and-hold's, and short enough that a human actually holds through it.
Cost: 24% of the terminal wealth vs full equity ($39,056 vs $64,237).

### If the question is "best simple answer, no rules, no monitoring"
**AOA (iShares Core Aggressive Allocation, 80/20 global).** CAGR **10.33%** — higher than SPY — Sharpe **0.826**, MaxDD **−23.0%**. One ticker, one purchase, quarterly rebalancing done for you, expense ratio ~0.15%. It beat every mutual fund in the sample and beat the index it is supposed to underperform.

### If the question is "I cannot tolerate losing money at all"
**GIC.** Accept 3.5% and $19,826. That is a legitimate choice for capital needed within ~5 years, an emergency fund, or money whose loss would change your life. **Full safety is not stupid — it is expensive, and this table prices it at ~$44,411 per $10,000 over 19.5 years.**

---

## 3. What is NOT supported by the evidence

- **No alpha was found in any asset class.** Every trend/momentum construction either matched or trailed buy-and-hold on CAGR. The gains are *risk* gains, not *return* gains. Anyone who reports the Sharpe improvement without the CAGR comparison is overselling it.
- **Mutual funds did not beat passive.** VBIAX ($40,511) ≈ 60/40 ($41,843) before the 60/40's simplicity; VWELX ($42,702) was the best fund and still trailed AOA; VASGX was the *worst* risk-adjusted option in the equity group (Sharpe 0.557, MaxDD −47.6%) — an 80/20 fund with a 48% drawdown is a design flaw, not bad luck.
- **Global diversification underperformed in this window** (6.40% vs 10.01% for SPY) — a US-dollar, US-equity-decade artifact. It reduced nothing: MaxDD −51.0%. **This is the most likely thing in the table to reverse**, and it is the reason AOA's 10.33% should not be expected to repeat.

---

## 4. Caveats that could change the answer (stated before anyone asks)

| caveat | effect |
|---|---|
| **GIC rate is ASSUMED at 3.5%**, not measured | if real GIC is 4.5%, add ~$4k terminal wealth; if 2%, subtract ~$4k. Direction of the conclusion does not change. |
| **US-equity decade dominance** | 2007-2026 overlaps the strongest US large-cap run in modern history. AOA's 10.33% is partly that, not fund skill. Test on 1980-2007 before believing it. |
| **No tax, no FX, no platform fees** | real-world drag of 0.3-1.0%/yr depending on account type and product; this is why expense ratio matters more than most of the differences above. |
| **Monthly sampling, overlapping windows** | the longest-underwater and worst-12m figures are path statistics from a single path; their standard errors are large. |
| **Trend overlay is a published rule (Faber 2007)** | expect decay. It survived a next-day-execution test (Part 8 §3), but publication decay (~58% per McLean-Pontiff) applies to anomalies; risk-management rules decay less. Unknown how much less. |
| **20bp turnover cost** | conservative for SPY/AOA, too optimistic for illiquid ETFs; the trend rule trades ~4-8×/decade so its cost is nearly irrelevant, which is why it is attractive. |

---

## 5. What I would need to see before sanctioning real money on any of it

1. **100 forward observations** on the chosen construction (the clock has not started — 0 exist).
2. **Out-of-sample on 1980-2007** for the AOA / trend claims, to remove the US-decade artifact.
3. **Regime split:** does the trend overlay's drawdown cut come only from 2008/2020/2022? If yes, it is three events, not a property.
4. **A hold test:** would a human have actually followed the rule through March 2020? Any construction whose edge requires impeccable behaviour is not an edge, it is a personality test.

Until then the honest labels are: **risk-control constructions = CANDIDATE**. **Alpha edge in any asset class = none found.** Nothing here is personalised advice, and every number is reproducible from `/tmp/p6/money.py`.

---
*Not personalized investment advice.*
