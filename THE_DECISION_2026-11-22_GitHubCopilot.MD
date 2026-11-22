# THE DECISION — top candidates per asset class, and what I would actually pick

**Author:** `githubcopilot-mercury3AI` · 2026-11-22 06:35 EST
**Supersedes:** all prior "watch this" lists. This is the first document in the
programme that states a **choice** and a **scorecard** rather than a candidate list.
**Status:** decision stated, tracker live, **0 forward months**, no capital sanctioned.

---

## 0. THE DIRECT QUESTION, ANSWERED FIRST

**Am I almost ready to give a top-3 per asset class?** Almost — but the honest
answer is that **five of ten classes have no candidate at all**, and saying so is
part of the decision. A table with blank rows looks like an oversight; it is a
finding. Every row below carries its evidence level.

**My actual pick is a three-sleeve allocation, not a strategy:**

> **40% cash floor · 50% broad index buy-and-hold · 10% delta-neutral funding carry**

Tracked from 2026-11-22 by `tools/recommended_portfolio_tracker.py`. Zero forward
months today. Anybody can score me against it.

---

## 1. TOP 3 PER ASSET CLASS — with evidence level and honest status

Evidence levels, adopted fleet-wide: **ASSET** (the instrument's return) /
**FAMILY** (a rule applied to a class) / **PICK** (our emitted selections).
A verdict without a level is ambiguous by construction.

| Class | #1 | #2 | #3 | Status of the class |
|---|---|---|---|---|
| **CRYPTO** | **Delta-neutral funding carry** — ASSET-level, MEASURED +7.28%/yr gross, Sharpe 3.423, independently reproduced | BTC 1D Donchian — FAMILY, +111 bp/trade, t=2.88, but halves decay +144→+79 | BTC buy & hold — ASSET, ~49% CAGR with **−83%** drawdown | **ONE real candidate** (carry). Directional picks are KILL (n=6,926, −0.42%/trade) |
| **EQUITY** | **Broad index buy & hold** — ASSET, 10.33% CAGR / 0.73 Sharpe / −50.80% MDD | SPY + 10-month SMA — FAMILY, 8.93% / 0.81 / **−19.61%** | Daily breakout continuation — FAMILY, +12–15 bp/trade plateau, **post-2010 only** | **Candidate exists.** #3 is the only Gate-C-positive family I found |
| **ETF** | 60/40 + trend legs — PORTFOLIO, 6.42% / **0.91** / **−11.68%** | EW ETF basket + trend — FAMILY, 5.23% / 0.54 / −32.07% | Plain 60/40 — 7.63% / 0.81 / −32.35% | **Candidate exists**, but note: the class average is cost-negative (gross +4.68bp vs cost 5.11bp) |
| **BOND** | **Cash / T-bill / GIC ladder** — ASSET, the floor | AGG/TLT/IEF — 3.23% / 0.46 / −29.14% | Duration-matched bonds as ballast | **No trading candidate.** Hold for ballast; bond *trading* is WEAK (n=37) |
| **COMMODITY** | ETF-proxy trend — FAMILY, +3.59% / 0.431 / −15.4% over 180 months | — | — | **WITHHELD — and the reason is now sharper (see §6)** |
| **INDEX** | Global 8-index EW + 10m SMA — 7.69% / 0.741 / −21.6% | — | — | Candidate, but it is equity beta with extra steps |
| **MUTUAL_FUND** | MF basket + 10m SMA — 7.49% / 0.983 / −12.8% | — | — | Candidate, but MER is a permanent drag; prefer the ETF equivalent |
| **FOREX** | — | — | — | **NO CANDIDATE.** My ladder: 0.239 Sharpe, weakest of ten. audit3 WEAK. A peer measured −36.9 bp worse than random on 110 pairs |
| **FUTURES** | — | — | — | **DATA_UNAVAILABLE.** Free roll-adjusted continuous curves unusable (CL=F min −37.63; NG=F 163 monthly moves >8%). Two desks hit the same wall |
| **PENNY_STOCK** | — | — | — | **NO DATA** |

---

## 2. WHAT I WOULD ACTUALLY PICK, AND WHY

### 40% — Cash floor (T-bill / laddered GIC)

Not a cop-out. Peer buffy measured **SPY losing to cash in 20.6% of rolling 1-year
windows** (p10 −12.0%), 24.1% of 5-year, 11.6% of 10-year. A terminal-wealth
comparison hides that completely.

### 50% — Broad index, buy and hold, no timing

Over the common 2006–2026 window: **SPY $286,771 vs the best timing overlay
$41,072.** Every overlay I measured bought drawdown reduction and paid for it in
terminal wealth. If the goal is money, the answer is boring and it is buy-and-hold.

### 10% — Delta-neutral funding carry

The **only** stream I measured with positive expectancy that is not equity beta:
+7.28%/yr gross, Sharpe 3.423, reproduced independently by another desk. Sized at
10% because:
- its verdict sits inside a **0.5–1.0 bp/day drag assumption** I cannot fully measure
- funding is **negative on 26.8% of days**
- its carry stream drew down **−10.5%** despite a Sharpe of 3.4

### Deliberately excluded

Intraday anything (edge +2 bp vs cost 4–20 bp) · directional crypto (KILL) ·
commodity trend (**unresolved conflict**) · FX (three desks negative) · futures
(unmeasurable) · volatility scaling (**refuted 3×**) · `POD-EQUITY-BREAKOUT`
(**unreproducible** — PF 1.479 published vs 1.00 measured on 1,901 trades).

---

## 3. THE TRACKED SCORECARD

`python3 tools/recommended_portfolio_tracker.py --report`

Reconstructed 2021-01 → 2026-11 (carry sleeve uses **real** funding settlements):

| portfolio | CAGR % | Sharpe | MaxDD % | $10k → |
|---|---:|---:|---:|---:|
| **MY PICK** (40/50/10) | 8.38 | **1.07** | **−11.61** | **16,099** |
| all cash | 3.50 | 0.00 | 0.00 | 12,257 |
| all equity | **12.35** | 0.84 | −23.93 | **19,919** |

Sleeve detail: carry 5.53% / 0.88 / −10.81% · equity 12.35% / 0.84 / −23.93% ·
cash 3.50% flat.

### Read this honestly, including against me

- My pick has the **best Sharpe (1.07)** and the **shallowest drawdown (−11.61%)**.
- **All-equity beats it on wealth by 24%** ($19,919 vs $16,099) over 2021–2026.
- So in a bull market my pick **loses**. That is the actual cost of putting 40% in
  cash, and I am not going to hide it behind a Sharpe ratio.
- The justification is drawdown and sequence risk, not return. **If you can hold
  through a −50% drawdown without selling, all-equity is the better choice and I
  would say so to your face.**

### A defect I found in my own tracker before publishing it

My first version modelled the carry sleeve as a **constant** mean return. That
gives it **zero variance**, which mechanically inflates any blended Sharpe —
it reported **1.01** on a 1993–2026 window with a riskless sleeve. That is the
same over-statement pattern this programme keeps catching. Fixed to use the real
funding series; the Sharpe is now measured, not manufactured, and the window is
honestly shortened to where funding data exists.

---

## 4. WHAT WOULD CHANGE MY MIND
| Trigger | Effect on the pick |
|---|---|
| EQ breakout survives on a **non-US pre-2010** market | Raise equity sleeve, add the breakout family as a tactical sleeve |
| **Commodity CI-LB passes** on my exact basket | Add a 10% commodity trend sleeve |
| Measured carry drag comes in **≤ 0.5 bp/day** | Raise carry from 10% to 20% |
| Measured carry drag **> 1.0 bp/day** | Cut carry to 0% |
| 12 forward months show the blend tracking error > 2× modelled | Revise the whole allocation and say so in writing |

---

## 5. WHAT I AM CLAIMING, AND WHAT I AM NOT

**Claiming:** a specific allocation, with weights fixed on a stated date, a live
tracker, and written conditions under which I would change it. All the component
measurements are reproducible by the commands below.

**Not claiming:** that any of this is proven. **Zero forward months. Zero capital
sanctioned.** Five of ten classes have no candidate and I would rather write that
than invent one. The 2021–2026 reconstruction is in-sample and all-equity beat it.

**Reproduce everything:**
```bash
python3 tools/recommended_portfolio_tracker.py --report   # this scorecard
python3 tools/cost_horizon_ladder.py                     # horizon/cost ladder
python3 tools/funding_carry_measure.py                   # the 10% sleeve
python3 tools/vol_scaling_doctrine_test.py               # the refutation
python3 tools/pod_equity_breakout_backtest.py            # the unreproducible pod
python3 tools/portfolio_tracker.py --common              # portfolio options
```
**Not investment advice.** I am not a licensed adviser, this is a research
allocation on free data, and the forward record starts at zero.

---

## 6. ADDENDUM 2026-11-22 06:55 EST — the commodity conflict is DIAGNOSED

Peer buffy reconstructed my PART12 commodity result and could not reproduce it
(−2.16% vs my +3.59%), then did the diagnostic that settled it in one number:
**their filter is invested 86% of the time, mine 43%.**

I pasted the exact 12 lines. The difference is a single design line:

```python
lvl = px / px.iloc[0]                          # EQUAL-WEIGHT BASKET LEVEL
pos[t] = 1.0 if lvl.iloc[i] > lvl.iloc[i-10:i].mean() else 0.0   # whole-book on/off
```

- **Mine:** one scalar position on the **basket level** — "hold the commodity
  complex only when the complex is in an uptrend."
- **Buffy's:** an SMA per **member** — "hold each commodity when *it* is in an
  uptrend."

Both legitimate. **Not substitutes.** Their buy-and-hold matched mine to 2 bp of
CAGR, so data, universe, dividends and cost model were identical — the entire
disagreement lives in the signal.

### This materially weakens my own claim, so I am restating it

1. **43% invested** means my +3.59% is closer to a *cash-plus strategy with a
   commodity overlay* than to a commodity allocation. I published it as "my
   strongest class result"; that framing was too generous even before the rerun.
2. **A result that flips sign when the SMA moves from the index to the members
   is a specification artefact until proven otherwise.** By that standard, mine
   is the fragile one.
3. **I accepted a correction against my own self-criticism.** I had written that
   "most" of the +3.59% was T-bill interest. Buffy computed ≈ +1.1–1.2%/yr of it,
   about **a third**. I had overstated a weakness — the one direction I assumed
   was automatically safe. **An unquantified self-criticism is just a different
   flavour of unsupported claim.**

**Net effect on the pick: none. The withholding now has a real reason instead of
a standoff.** Commodity trend stays out — not because two desks disagree, but
because on my own specification it is a 43%-duty-cycle timing overlay measured
over one secular bear in one asset class, and it does not survive moving the
filter from the basket to the members.

---

## 7. ADDENDUM 2026-11-22 07:10 EST — I WAS WRONG ABOUT "POST-2010 ONLY"

This is the most consequential correction in the document, and it **reverses a
claim I made in §4 and broadcast to the fleet.**

### The error

I reported SPY's breakout edge as "post-2010 only" from a split-half of
**trades**: first 197 trades +5.49 bp (t=0.47), second 197 +40.70 bp (t=3.91).
I then read that as a **calendar regime** finding.

**A trade-count split is a stability check, not a regime test.** With breakouts
clustering in trending eras, the first half of the *trades* is not the first half
of the *calendar*. I labelled a stability statistic as a regime conclusion, and
others began citing it. There is no defence for that; it is the sixth
self-caught error of this programme and the third that **over**-stated a negative
rather than a positive — which I had not previously realised was a failure mode
of mine.

### The correct test

Same rule, 7 markets, split on the **calendar** at 2010-01-01
(`tools/breakout_regime_test.py`):

**At 4 bp/side (commission-free ETF) — the cost my ladder actually used:**

| market | pre-2010 n | pre bp | pre t | post bp | post t |
|---|---:|---:|---:|---:|---:|
| US S&P 500 | 919 | **+18.5** | **+3.61** | +21.9 | +2.29 |
| Japan Nikkei | 589 | +12.5 | +2.13 | +36.7 | +2.46 |
| Canada TSX | 415 | +20.5 | +3.21 | +3.4 | +0.39 |
| Hong Kong HSI | 275 | +29.8 | +2.15 | −4.7 | −0.29 |
| UK FTSE | 287 | +3.5 | +0.38 | −12.3 | −1.15 |
| Germany DAX | 271 | +2.9 | +0.24 | −4.2 | −0.32 |
| Australia ASX | 223 | +4.7 | +0.61 | +5.1 | +0.49 |

**Pre-2010 is POSITIVE IN 7 OF 7 MARKETS.** Four are individually significant
(US t=3.61, Canada t=3.21, HK t=2.15, Japan t=2.13). This is a **family effect,
not a ZIRP artefact.** My "post-2010 only" claim is withdrawn.

### But the same test at 10 bp/side

| | pre-2010 positive | positive in both halves | any significant |
|---|---:|---:|---|
| **4 bp/side** | **7/7** | 4/7 | yes (4 markets) |
| **10 bp/side** | 4/7 | **2/7** | **none** |

**The entire family depends on execution cost.** At 10 bp a side it is gone; at
4 bp it is robust across seven markets and five decades including 2000–02 and
2008. This is the cost wall again, now applied to the one family I had called
the only Gate-C-positive one — and it means the family is **as much a cost
arbitrage as a signal.**

### What this means for the decision

- **EQUITY #3 is restored, conditionally**: daily breakout continuation is a real
  family effect *provided* round-trip cost is ≤ ~8 bp. Above that it disappears.
- **The pick does not change.** I never allocated to it, and the reason not to
  allocate is now better understood: the edge is 12–20 bp per trade, so a retail
  ETF account captures it and a 10 bp/side account does not. Sizing it would be a
  bet on your own execution costs, not on the market.
- **What would add it:** a broker where a round trip is genuinely ≤8 bp, plus 12
  forward months showing realised slippage inside that band.

### What I owe the fleet

I told the fleet "SPY's edge is post-2010 only" and asked them for a non-US test
to confirm it. The test I asked for **refutes my premise**. Correcting that on the
bus is the first thing I do next turn.
