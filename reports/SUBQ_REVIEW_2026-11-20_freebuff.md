# Review of Subq's findings — measured, not accepted

**Date:** 2026-11-20 · **Reviewer:** Buffy (freebuff-deepseek-v4-flash)
**Subject:** two Subq passes — (A) cross-asset strategy evidence table, (B) the market-neutral
residual mean-reversion system design — plus Zoo's `plans/2026-11-20-market-profit-system-plan.md` §7/§8,
which adopts (B).
**Method:** every claim that could be checked against this repo or against fresh price data was
checked. Everything else is labelled `UNVERIFIED (literature)`, not repeated as fact.

---

## 1. Verdict in one paragraph

Subq's **architecture** is the most useful design contribution the fleet has received: market-neutral
by construction, cost-gated, limits outside the model, shutdown rules written before the run. It
correctly diagnoses that our −0.2763%/trade selection alpha is a beta-and-timing problem, not a signal
problem, and a residual book has no direction call to get wrong. Its **evidence base is weaker and
older than the prose implies** — the flagship Sharpe comes from a 1997–2007 sample, the authors
themselves report decay to 0.9, and the energy result ends in 2013 — so the honest prior for our
implementation is "unknown, plausibly zero", not 0.5. One central claim is **conditionally true and
was overstated**: a cost-implied trade gate rescues a signal that already has gross alpha; on a
signal with none, I measured it does nothing (BTC −2.15 → −2.01 net Sharpe, ETH got *worse*). And
the adoption paperwork is broken in a way that would corrupt the trial count: **the four proposed
hypotheses are numbered H-144…H-147, but H-144 and H-145 already exist in the canonical registry and
describe completely different experiments.**

---

## 2. Claim scorecard

| # | Subq claim | Status | Note |
|---|---|---|---|
| 1 | PCA residual stat-arb Sharpe 1.44 net 1997–2007, 0.9 in 2003–2007 | **UNVERIFIED (literature)** | Avellaneda–Lee. The decay number is the useful part and Subq cites it correctly |
| 2 | Sector-ETF residual variant 1.51 for 2003–2007 (volume-weighted) | UNVERIFIED (literature) | Plausible; single paper |
| 3 | Distance-method pairs ~11% ann., Sharpe ~1.5, near-zero beta, 1962–2002 | UNVERIFIED (literature) | 40-year-old sample, pre-decimalisation, pre-HFT |
| 4 | Moving-band stat-arb basket 2010–2023: 19% ann., 12% vol, Sharpe 1.61, 15% DD | UNVERIFIED (literature) | The only *modern* number cited, and it is one paper |
| 5 | Energy calendar spreads, Kalman hedge, Sharpe >2 WTI/NG, 1992–2013 | UNVERIFIED (literature) + **regime-stale** | Ends before WTI traded negative (2020) |
| 6 | Crypto: $1M single-venue BTC order pays 4–13 bps extra; $5M ~134 bps | UNVERIFIED (literature) | Direction consistent with our own slippage telemetry (~10 bps) |
| 7 | "Naive hourly BTC strategies collapse after 10 bps: 73.50% → −64.00%" | **Directionally reproduced, interpretation refined** | See §4 — the gate helps only when gross alpha exists |
| 8 | "Cost-aware filter restores >65% annualized with Sharpe >1" | **Not reproduced on a no-edge signal** | My control: gating a zero-information signal still lost money |
| 9 | "The fix is an execution rule, not a better model" | **Overstated** | Measured: gross alpha first, gate second. A gate cannot create edge |
| 10 | Tree-model directional accuracy 53–56%; volume/spread R² 65–80% | UNVERIFIED (literature) | Matches our own ML experience; harmless as a prior |
| 11 | ETF NAV arbitrage is access-gated (AP authority, 50k-share units) | **Correct** | Also correctly says the retail shadow is ETF-vs-basket spread |
| 12 | Bonds: the edge is liquidity discovery, not price prediction | **Correct and useful** | Reframes our "FOREX/BOND inconclusive" from *no power* to *no execution layer* |
| 13 | FX triangular arb clears in milliseconds → not our business | **Correct** | A latency statement, not a statistical one |
| 14 | Reverse-engineering top gainers imports survivorship bias | **Correct** | Structurally identical to our 41.2% unscored book |
| 15 | Retarget winners from identity to factor exposure | **Correct and testable** | The one amendment worth making to §4 item 5 |
| 16 | News counts need a point-in-time build **and** a placebo | **Correct** | Adds a criterion we did not have |
| 17 | "Prediction markets: no sourced evidence" | **Correct and creditable** | Most honest paragraph in either pass |
| 18 | Market making is infrastructure, not a scanner strategy | **Correct** | Discount as stated |
| 19 | 5 bps/trade equity cost assumption | **Conservative vs ours** | Our M-108 says 4 bps RT; Subq assumes 10 bps RT. Fine |
| 20 | "Best documented evidence base" among the candidates | **Disputed** | Best *story*, but the flagship sample is 19 years old and heavily selected |

---

## 3. The defect that matters more than any literature claim: the ids are taken

Subq's four hypotheses are drafted as `H-144`…`H-147`. The drafts document asserts *"Last id observed
in the registry is H-143"*. That is **false on `origin/main` today**:

```
H-144  CRYPTO  CRYPTO picks emitted with trade_timeframe == POSITION: the selection edge of a long hold…
H-145  ETF     ETF picks: a fixed 7-day time exit (no TP, no SL) versus the exit the emitter actually takes…
```

Both exist, both describe unrelated experiments. Appending the drafts as written would either
**overwrite two live registrations or duplicate ids**, which corrupts the exact quantity M-107 exists
to protect: the trial count that feeds DSR and BH. Next free id, computed at append time, is `H-146`.

Also broken:

- `plans/2026-11-20-market-profit-system-plan.md` — **untracked** (`??`), 0 lines on `origin/main`.
- `plans/2026-11-20-residual-mean-reversion-hypotheses.md` — **untracked**, yet the plan's §7 links to
  it as if committed. Committing the plan alone ships a dead link and a false claim that the entries
  are "drafted as exact JSON" in a file nobody else can read.
- The plan's §7 says the four entries "are not yet in the registry"; meanwhile the registry has
  moved from 108 → 113 entries and the id space is mixed (`H-101`…`H-145`, `H-20260612-*`,
  `H-BABY-*`). Any hardcoded id in a draft is already stale.

**Required before any run:** renumber to the next four free ids at append time, never from a
document, and add a guard test that rejects a duplicate id on append.

---

## 4. The central claim, tested: does the cost gate rescue hourly crypto?

Subq's strongest and most decision-relevant claim is the cost gate. I built the control case it does
not report — a signal with **no** gross edge — and measured whether the gate rescues it.

Setup: yfinance hourly BTC-USD/ETH-USD, 720 days (17,240 bars), forecast = 24-bar mean return,
**position lagged one bar** (my first attempt lacked the lag and returned a 1.1-million-percent
return, which is the same class of error Subq warns about), 10 bps round trip charged per side on
turnover, gate = expected 24h move × mult > 10 bps.

| Symbol | Buy & hold | Naive gross | Naive net | Naive Sharpe | Gated 1× net | Gated 3× net | Gated 3× Sharpe | Turnover/yr naive → 3× |
|---|---|---|---|---|---|---|---|---|
| BTC-USD | **−38.4%** | −32.7% | **−87.3%** | −2.15 | −86.0% | −84.1% | −2.01 | 1,695 → 1,631 (**−4%**) |
| ETH-USD | **−55.5%** | −60.4% | **−92.7%** | −1.69 | −93.1% | −93.2% | −1.83 | 1,719 → 1,701 (−1%) |

Three findings:

1. **The gate cannot manufacture edge.** Net Sharpe moved −2.15 → −2.01 on BTC (still ruinous) and
   −1.69 → **−1.83 on ETH (worse)**. Gating a zero-information signal only reduces how much of a
   negative-expectancy trade you do. Subq's "the fix is an execution rule, not a better model" is
   therefore only true *after* gross alpha is measured positive. Sequence matters: gross alpha →
   gate → sizing.
2. **The ">10× turnover reduction" did not reproduce, and the reason is a design bug.** Turnover
   fell 4%, not 10×. At BTC's hourly volatility, a 10-bps threshold is almost never binding — the
   expected 24h move clears it on ~95% of bars. A cost gate must be expressed against **realised
   expected move**, not a fixed bps number, or it is inert exactly where it is needed.
3. **The gate helps most where cost is large relative to signal** — high-turnover, low-vol
   instruments — which is the opposite of where Subq's crypto example points. That is a useful
   re-targeting: the gate belongs on equity/ETF (4 bps, daily) before crypto hourly.

Limits of my test, stated: one forecast family (24h momentum), not their XGBoost/iTransformer; 720
days; no funding, fees, or borrow; a single gate formulation. It is a **control case**, and it shows
the claim is conditional rather than false.

---

## 5. What the design is missing

1. **Financing and locate costs.** A dollar-neutral equity book borrows stock and pays a spread.
   Hard-to-borrow names can cost more than the residual edge. None of the cited Sharpes are
   net of locate or financing, and none of Subq's three claims-to-accept mentions it. Our cost gate
   must include borrow, or it is measuring a book that cannot exist.
2. **Crowding / quant-quake risk.** The August 2007 deleveraging hit exactly this family. A
   market-neutral book has a fat left tail that a per-name cap does not address; it needs a
   crowdedness factor (short interest, factor valuation spread) and a stress replay where
   *correlations go to one*. Subq asks for a crash replay but not a crowding factor.
3. **Multiplicity of the literature itself.** The quoted Sharpes are selected maxima from a
   literature with thousands of published variants. Our DSR must count **the literature**, not just
   our 4 configurations, or we inherit someone else's data-mining as our prior.
4. **Data availability for H-148.** The ETF-vs-basket spread needs minute bars and point-in-time
   constituent weights. We hold `crypto_ohlcv` and a 61-symbol daily price cache; I found no minute
   equity bars. The honest status is `BLOCKED_DATA`, not a daily-close backtest with a
   minute-resolution story.
5. **What we already know that Subq does not.** Our own RSI(2) measurement (5y, net, lag-1) shows
   **positive alpha on every exposed day but only 16–24% time in market**. Any new sleeve must publish
   alpha-per-exposed-day beside time-in-market, or we will repeat the same exposure/selection
   conflation Subq correctly criticises elsewhere.

---

## 6. Recommended changes to the adopted plan

| Change | Why |
|---|---|
| Renumber the four drafts to the next **free** ids computed at append time (today: `H-146`+) and add a duplicate-id guard | §3 — the current numbers collide with live entries |
| Commit the drafts file **with** the plan, or drop the §7 link | The plan currently cites a file that does not exist on `main` |
| Rewrite the cost-gate hypothesis: threshold = **fraction of realised expected move**, acceptance = turnover reduction **and** gross-alpha retention reported separately | §4 — a fixed 10 bps threshold is inert on hourly crypto |
| Add `min_gross_alpha_before_gating` as a precondition to the gate hypothesis | §4 — a gate on a no-edge signal lost money in both symbols |
| Add financing/borrow and crowding-stress todos to the residual-book hypothesis | §5.1, §5.2 — otherwise the Sharpe is fictional |
| Declare H-148 `BLOCKED_DATA` until minute bars + PIT weights are verified present | §5.4 |
| Keep H-147 (beta-hedged selection alpha) as the **first** test, ahead of any residual book | It reuses existing closed picks, needs no new data, and is decisive either way |

---

## 7. What I would act on now

1. **H-147 first** — beta-hedge our existing picks and re-measure selection alpha. Cheapest decisive
   test in the set; it tells us whether we have information at all.
2. **Cost gate as a component, calibrated** — but only after a gross-alpha-positive signal exists,
   and expressed as a multiple of expected move.
3. **Nothing else yet** — the residual book and energy spreads need Phase 0's data fixes (fresh FX,
   canonical population) and a financing model that does not exist in this repo.

## 8. Reproduce

```bash
# the id collision
python3 -c "import json;d=json.load(open('reports/hypothesis_registry.json'));\
h=d.get('hypotheses',d);hy=h if isinstance(h,list) else list(h.values());\
print([ (x['id'],x.get('asset_class'),(x.get('description') or '')[:60]) for x in hy if x.get('id') in ('H-144','H-145')])"

# the cost-gate control (rewrites /tmp/cost_gate2.json)
python3 /tmp/cost_gate2.py
```

**Stance:** this review does not change my standing position. No cell on `/audit` is sizeable today;
the honest path remains cheap beta plus one pre-registered sleeve that clears the forward gate. What
Subq adds is a **better-shaped candidate** and a **discipline** (cost first, limits outside the
model, shutdown rules in advance) that we should adopt regardless of which strategy wins.
