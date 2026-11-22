# Cross-venue funding dispersion + fee-tier break-even (2026-11-22)

Reproducer: `python3 tools/funding_venue_dispersion.py --days 120`
Artifacts: `reports/funding_venues/funding_venues.json`
Closes todos **38, 39**.

Synchronised window: **2026-10-20 .. 2026-11-22**, 5 venues × 3 coins, **1,500 settlements**.

---

## Three defects in my own passes, all of which changed the answer

**1. Non-overlapping comparison windows.** The first fetch passed no `limit`, so
Binance returned its default 100 settlements ending **2026-09-27** while OKX and
KuCoin ran to **2026-11-22**. Section 38 compared venues across different
two-month windows. Fixed with per-venue pagination and a `common_window()` that
restricts every series to the span all retained venues actually cover.

**2. Sections 38 and 39 used different samples.** Section 38 windowed
*internally*; `section_fee_tiers()` received the raw unwindowed dict. So the two
halves of one tool reported **+3.644%/yr over 3,618 settlements** and
**+3,555%/yr over 1,500 settlements** simultaneously — precisely the failure the
"one harness so the answers cannot drift" design was supposed to prevent. The
window is now computed once in `main()` and passed to both.

**3. A fixed 8h annualisation assumption.** Verified rather than assumed: every
retained venue settles every **8.0h** in this sample, so the assumption happened
to hold. It is now measured and printed, and a non-8h venue would be flagged
rather than silently double-counted.

---

## 38 — Cross-venue dispersion

Annualised funding by venue × coin, synchronised window:

| coin | binanceusdm | bybit | okx | kucoinfutures | bitget |
|---|---:|---:|---:|---:|---:|
| BTC | +5.67% | +4.97% | +5.41% | +6.68% | −0.05% |
| ETH | +3.96% | +3.49% | +3.69% | +2.47% | −1.43% |
| SOL | +3.23% | +1.66% | +2.57% | +0.59% | −6.65% |

Dispersion at settlements where ≥3 venues report (n=100 each):

| coin | mean | median | p90 |
|---|---:|---:|---:|
| BTC | 5.39%/yr | 5.66%/yr | 8.40%/yr |
| ETH | 6.13%/yr | 5.62%/yr | 10.03%/yr |
| SOL | **7.68%/yr** | 7.07%/yr | 12.72%/yr |

The gaps are large and real. **Harvest test** — long the cheap-funding venue,
short the expensive one, 30-day hold, cost = 4 fills × (0.050% taker + 1.3bp
slippage) = **0.252% of notional per round trip**, and margin posted on **two**
venues so cost on capital is **0.504%**:

| coin | gross 30d on capital | cost | net 30d | net annualised |
|---|---:|---:|---:|---:|
| BTC | +0.886% | 0.504% | −0.061% | **−0.743%/yr** |
| ETH | +1.008% | 0.504% | −0.000% | **−0.002%/yr** |
| SOL | +1.263% | 0.504% | +0.127% | **+1.557%/yr** |

**Best case SOL +1.56%/yr — still below the 3.5% T-bill.** The dispersion is
real but smaller than the cost of reaching it, and the requirement to post margin
on two venues is what does most of the damage.

## 39 — Fee tier is not the binding constraint

Measured gross carry over the synchronised window: **+3.555%/yr** (1,500
settlements). T-bill **3.50%/yr**. Headroom: **+5.5bp/yr**.

| tier | taker | maker | RT taker | net taker (ann) | verdict |
|---|---:|---:|---:|---:|---|
| VIP0 | 5.0bp | 2.0bp | 10.0bp | 3.544% | clears by 4.4bp |
| VIP5 | 2.7bp | 1.0bp | 5.4bp | 3.590% | clears by 9.0bp |
| VIP9 | 1.7bp | 0.0bp | 3.4bp | 3.610% | clears by 11.0bp |

Every tier clears — **by single-digit basis points per year.** The fee ladder
moves the answer by ~7bp/yr across its entire range. So fee tier is emphatically
*not* what decides this.

## The decisive test — stability

| | |
|---|---|
| first half (10-20 → 11-06) | **+5.96%/yr** |
| second half (11-06 → 11-22) | **+1.24%/yr** |
| T-bill hurdle | 3.50%/yr |
| rolling 10-settlement blocks (n=28, ~3.3d each) | min −3.84%, median +4.72%, max +8.77% |
| blocks above T-bill | **18/28 (64%)** |
| blocks below zero | **6/28** |

**The two halves disagree by 4.7 percentage points and the recent half is well
below cash.** A mean of +3.555%/yr that straddles a 3.50% hurdle, decays 80%
across the sample, and is negative in 21% of rolling blocks is not an edge. It is
a window you chose.

This resolves the apparent contradiction with the earlier finding: the **+3.18%
"forward"** figure and this **+3.555%** figure are the *same stream* measured on
different windows. Neither is wrong; both are unstable.

---

## Verdict changes

| item | previous | now | basis |
|---|---|---|---|
| crypto funding carry | "loses to T-bill (3.18% vs 3.5%)" | **REFUTED as a stable cash-beater** | +3.555% mean but split-half +5.96% → +1.24%; 6/28 blocks negative |
| cross-venue funding arb | untested | **REFUTED** | best harvest +1.56%/yr net, below cash |
| venue fee tier | assumed decisive | **NOT the binding constraint** | whole ladder worth ~7bp/yr; stability worth 470bp |

The prior belief that "VIP0 fees kill the carry trade" was directionally fine but
misattributed. Fees are a rounding error against the time-variation. **If crypto
funding carry ever becomes real, the blocker will be persistence, not cost.**

## Promotion gate

| item | label |
|---|---|
| funding carry (delta-neutral) | **REFUTED** — window-dependent, not persistent |
| cross-venue dispersion harvest | **REFUTED** — gross gap < cost of reaching it |
| carry as SIZING input | **UNMEASURED** — would need a regime/persistence model first |
