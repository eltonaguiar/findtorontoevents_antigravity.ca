# 2026-10-22 — "Mutual-Fund/ETF Company" Strategic Playbook

**Author:** Zoo (mercury-3), acting as the portfolio-construction lead for a turn-around
mutual-fund/ETF-style investment company.

**This doc covers the full ask:**
1. Deep-dive each asset class and say honestly where winners could come from.
2. Survey the current symbol universe and propose expansions.
3. Use **public mutual-fund data** (already captured by
   [`alpha_engine/mutual_fund_ranker.py`](alpha_engine/mutual_fund_ranker.py:1) →
   [`audit_dashboard/data/mutut_fund_rankings.json`](audit_dashboard/data/mutut_fund_rankings.json:1))
   to *derive* successful stocks/ETFs.
4. Produce the strategic playbook for how a company like ours goes from
   "barely any winning picks" to real winners across each asset class.

---

## 0. Executive summary (read this first)

We are not a broken *strategy* shop — we are a broken **product** shop. The single
most-validated, most-robust edge we own is a **tactical multi-asset rotation** on low-fee
ETFs (Sharpe 0.88-1.21, MaxDD cut ~2.5x vs SPY across 2007-2026, three independent
corroborating variants). Meanwhile, our *per-symbol stock/crypto pick* engine — the thing
we run every day — has **zero MONEY_READY classes** today
([`money_ready_verdict.json`](audit_dashboard/data/money_ready_verdict.json:1515) →
`money_ready: []`).

The honest strategic insight: **we already built the mutual-fund/ETF company — we just
haven't realized it.** The fix is to stop trying to make thousands of single-stock picks
behave like a winning book, and instead organize the company the way a real fund is run:

- **Core book (the "mutual fund"):** diversified, low-fee index sleeves (from public fund
  data → the T1/T2 funds below). This is the *safe, reliable* engine.
- **Tactical overlay (the "alpha"):** the validated rotation/VAA/PAA family that improves
  risk-adjusted return on top of the core. This is where "winners" across asset classes
  actually come from.
- **Research-only book (the lab):** the per-symbol crypto/stock picks remain a *research*
  pipeline — forward-monitor the few cells that clear gates (CRYPTO SHORT RSI30-50), but
  never fund them with client capital until forward-proven.

> **[P0] The biggest action item:** productize the tactical rotation as a 60/40-ish
> "tactical balanced ETF" wrapper and run it with *real* portfolio construction. Everything
> else below is support.

---

## 1. Asset-class deep-dive (what the data actually says)

All verdicts below come from the honest, gated framework in
[`money_ready_verdict.json`](audit_dashboard/data/money_ready_verdict.json:1),
[`top_edges_per_class.json`](audit_dashboard/data/top_edges_per_class.json:1), and the
`research/asset_class/*/run_*/p5_synthesis.md` family.

| Class | Money-ready? | Honest gate verdict | Why / evidence | Where a winner could come from |
|---|---|---|---|---|
| **CRYPTO** | **NO** | intrabar PF 0.89, all-class MDD ~100%, policy-clean PF 0.29. | Aggregate long-side negative. The *only* forward-valid signal: SHORT RSI30-50 (mined 2026-10-22). | **Forward-monitor** CRYPTO SHORT RSI30-50 (n=125, net PF 2.16, boot CI-LB 1.69, ex-top3 1.54); F2-WITH variant net PF 2.48. |
| **EQUITY** | **NO** | policy-clean PF 1.26 but bootstrap CI-LB ≈ 0 and top sleeves all single-source (concentration artifacts, 8-16 symbols). | The "winners" are frozen-exit / single-name artifacts, not real edge. | The **multi-asset rotation** uses equity ETFs (SPY/QQQ/IWM/EEM/EFA) as *sleeves*, which is the only equity exposure with real robustness. |
| **FOREX** | **NO** | intrabar truth negative; daily vs intrabar divergence flag. | No honest forward edge in the per-pair data. | Keep the **forex carry/momentum** ideas as research only; do not fund. |
| **COMMODITY** | **WATCH** | honest PF 1.03, but policy-clean PF 0.46 (frozen), concentration NG=F 33%. | The only class on watch — but on weak legs. | CT=F showed a real unblock candidate (post n=43, WR 81.4%, PF 6.33) → receptive for a **commodity futures sleeve** in the rotation universe. |
| **BOND** | **NO** | all `bond_*` PCI NO_EDGE / MIXED. | Duration/credit/term-premium all null. | Bonds are *not* a pick source — they are the **defensive sleeve** in the rotation (IEF/TLT/AGG/credit) and the safe core. |
| **ETF** | **NO** (as a *pick* source) | rotation backtests **MIXED**; but the *TAA family* is the strongest validated edge in the whole repo. | The name is misleading: ETF-level rotation is our #1 edge, it just isn't "funded" as a product. | **This is the company's product.** Validate/VP the rotation+VAA+PAA blend. |
| **FUTURES** | **NO** | all `futures_*` NO_EDGE. | Momentum/carry/regime all null. | Skip as a standalone pick source; only as commodity-sleeve exposure. |

**Honest bottom line:** the *only* robustly-validated winner in the entire repo is the
**asset-class rotation / TAA family**. Everything else is either an artifact, a forward-
monitor candidate, or a support sleeve.

---

## 2. Symbol-universe survey & expansion

Current universes (from [`config/equity_universe.csv`](config/equity_universe.csv:1),
[`config/symbol_blocks.yaml`](config/symbol_blocks.yaml:1),
[`ETF_STRATEGY_REPORT.md`](tools/kimi_research_2026_05_20/ETF_STRATEGY_REPORT.md:92),
and [`symbol_reconciliation.json`](audit_dashboard/data/symbol_reconciliation.json:1)):

- **EQUITY:** 232 tickers in CSV, 214 `include=true`. Blocks: NIO, AMD, MSTR
  (poor-performance watch); full-unblock candidates CT=F (commodity), IMXUSDT (crypto);
  shadow candidates DYDXUSDT, TRXUSDT, CVX.
- **CRYPTO / FOREX / COMMODITY / BOND:** dynamic (see
  [`alpha_engine/universe_expander.py`](alpha_engine/universe_expander.py:1)).
- **ETF sleeve universe:** 18 ETFs (SPY, QQQ, VTI, VOO, DIA, ARKK, XLF, XLE, XLK, SLV,
  USO, EEM, EFA, SQQQ, TQQQ, UVXY); **IWM & GLD blacklisted**.
- **Mutual-fund universe:** 37 ranked funds (1 T1 Proven, 8 T2 Watch, 28 T3 Reject).

**Expansion recommendation (real, not shotgun):**

1. **Extend the ETF sleeve universe for the rotation** — the rotation uses
   *14 liquid asset-class ETFs*. The mutual-fund data points to sleeves we are currently
   *missing* as dedicated ETFs: **TIPS (FIPDX → TIP), value (VVIAX → VTV), small-cap
   (VSMAX → VB/IWM — currently blacklisted, review), REIT (VGSLX → VNQ), and dividend
   quality (SCHD/VIG)**. Adding these as rotation candidates is the *highest-value*
   universe expansion — it directly improves the product, not the research lab.
2. **Unblock CT=F (commodity futures)** — already a proven unblock candidate and a
   natural rotation sleeve; unblock in the *sleeve* path (not the per-symbol pick path).
3. **Forward-monitor crypto SHORT RSI30-50** as the only funded crypto candidate; do
   *not* expand the crypto long universe.
4. **Do NOT scale up the per-symbol pick universe** — the bottleneck is not symbol
   coverage, it's that single-symbol picks have no honest statistical edge. More symbols
   = more artifacts, not more winners.

---

## 3. Using public mutual-fund data to derive winning stocks/ETFs

We already run a defensible mutual-fund ranker (
[`alpha_engine/mutual_fund_ranker.py`](alpha_engine/mutual_fund_ranker.py:1), composite:
cost-22 / risk-26 / consistency-18 / downside-16 / capacity-10 / manager-8). Its output is
the *sleeve-level* truth we need:

### 3.1 What the ranker tells us (the "shopping list")

| Tier | Funds | Categories | What it means for us |
|---|---|---|---|
| **T1 Proven** | SWPPX (Schwab S&P 500, score 87.1, ER 0.02%) | US large blend | The **core US equity sleeve** — the safest passive building block. Buy VOO/VTI (0.03% ER). |
| **T2 Watch** | FSKAX (total mkt, 79.0), SFENX (EM, 77.0), FSMDX (mid, 76.1), FIPDX (TIPS, 74.1), VVIAX (value, 71.7), FXNAX (agg bond, 70.8), FSPGX (large growth, 67.2), VGSLX (REIT, 66.7) | International, bonds, TIPS, value, growth, REIT | These are the **diversifying sleeves** — exactly what the rotation needs. Map each to a low-fee ETF. |

- **The "derive successful stocks" answer:** the winners aren't a handful of hand-picked
  stocks — they are the *index holdings* of these T1/T2 funds. The safe, high-EWA way to
  "own the winners" is to own the **index funds themselves** (or their ETF equivalents),
  not to try to out-guess the index. SWPPX/FXAIX/VFIAX *are* the S&P 500's winning
  names, at 0.015-0.03% ER.
- **Where our per-symbol work adds real value:** the rotation overlay *tactically tilts*
  among these sleeves based on momentum (top-5 9m → rotate to bonds/cash when negative).
  This is the "winning across each asset class" the user is asking for — proven via
  public ETF/fund data.

### 3.2 The fund→ETF sleeve map (the concrete product)

| Mutual fund (from ranker) | Category | ETF sleeve for rotation/core |
|---|---|---|
| SWPPX / FSKAX | US large / total market | **VOO / VTI** (0.03%) |
| FSPGX | Large growth | QQQ (tech) or VUG |
| VVIAX | Large value | VTV (value) — *add* |
| FIPDX | TIPS / inflation | **TIP** — *add* |
| FXNAX | US aggregate bond | AGG / BND (defensive) |
| VSMAX (T3 reject, clone) | Small cap | VB / IWM — *review blacklist* |
| SFENX / EM | Emerging | EEM |
| VGSLX | REIT | VNQ — *add* |
| VDADX (from rotation report) | Dividend quality | SCHD / VIG — *add* |

> The rotation report already reached the same conclusion: for buy-and-hold the winners
> are the **0.03% ER total-market index funds**; the tactical rotation improves
> risk-adjusted return *on top* of those.

---

## 4. The playbook: how we go from "barely any winners" to real winners

### 4.1 Reframe: we are a fund, not a picker

Every "no winner" conclusion in §1 is the *per-symbol pick* lens. Through the **fund
lens**, the company already has a winning engine. The pivot:

**Phase A — Build the "Tactical Balanced Fund" (the product, P0).**
- Core: 60-70% diversified index sleeves (from §3.2 map).
- Overlay: 30-40% tactical rotation (top-5 9m momentum, absolute-momentum filter) using
  the extended cigar universe; blend with VAA-G4/PAA1 (validated family).
- Tooling already exists: `tools/tactical_rotation_tracker.py`,
  `tools/tactical_blend_tracker.py`. Turn the monthly status JSON into a public,
  forward-tracked record (this is the mutual-fund "NAV" proof).

**Phase B — Defend the core with honest gatekeeping (what we already built).**
- Keep the money-ready framework as the *approval* gate. No sleeve goes into the core
  book unless it's a T1/T2 fund equivalent.
- Crypts/stock picks stay in the research lab: forward-monitor CRYPTO SHORT RSI30-50.
  Only promote to the funded book after a fresh-forward cohort clears the promotion bar.

**Phase C — Expand the sleeve universe deliberately (§2).**
- Add TIP, VTV, VNQ, SCHD to the rotation candidates; unblock CT=F as a commodity sleeve.
- Re-run the rotation backtest with the expanded universe to confirm the edge holds.

**Phase D — Publish a track record (the mutual-fund thing).**
- The validation evidence (Sharpe/Calmar/MaxDD/thirds) is already computed for the rotation
  family over 2007-2026. Turn `tactical_rotation_status.json` and the daily tracker into a
  public performance page — this is how a fund proves itself.

### 4.2 What NOT to do

- ❌ Do NOT scale the per-symbol pick universe — more symbols ≠ more winners, and the
  data shows the picks engine has no honest edge today.
- ❌ Do NOT fund crypto-long or per-pair forex — both are net-negative in aggregate.
- ❌ Do NOT claim any winner is "proven" without forward data — the blockchain
  validation (bootstrap CI-LB, ex-top3, FDR, both-regimes) must precede any funded claim.

---

## 5. Files consulted

- [`audit_dashboard/data/money_ready_verdict.json`](audit_dashboard/data/money_ready_verdict.json:1)
- [`audit_dashboard/data/mutut_fund_rankings.json`](audit_dashboard/data/mutut_fund_rankings.json:1)
- [`alpha_engine/mutual_fund_ranker.py`](alpha_engine/mutual_fund_ranker.py:1)
- [`reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`](reports/TACTICAL_ROTATION_EDGE_2026-07-04.md:1)
- [`tools/kimi_research_2026_05_20/ETF_STRATEGY_REPORT.md`](tools/kimi_research_2026_05_20/ETF_STRATEGY_REPORT.md:92)
- [`config/equity_universe.csv`](config/equity_universe.csv:1), [`config/symbol_blocks.yaml`](config/symbol_blocks.yaml:1)
- [`audit_dashboard/data/symbol_reconciliation.json`](audit_dashboard/data/symbol_reconciliation.json:1)
- [`audit_dashboard/data/top_edges_per_class.json`](audit_dashboard/data/top_edges_per_class.json:1)
- `research/asset_class/*/run_*/p5_synthesis.md`
- `updates/2026-10-22-cross-check-picks-entry-conditions.md`, `updates/2026-10-22-other-entry-conditions-investigation.md`

## 6. Next actions (concrete)

1. [P0] Write a `TACTICAL_BALANCED_FUND` product spec (core sleeve weights + overlay) and
   turn `tactical_blend_tracker.py` into the funded record.
2. [P1] Extend the rotation universe with TIP / VTV / VNQ / SCHD + unblock CT=F; re-run
   the rotation backtest to confirm the enlarged-universe edge.
3. [P1] Keep CRYPTO SHORT RSI30-50 as the single funded forward-monitor crypto candidate.
4. [P2] Add a public "fund performance" page fed by the tactical rotation status JSON.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
