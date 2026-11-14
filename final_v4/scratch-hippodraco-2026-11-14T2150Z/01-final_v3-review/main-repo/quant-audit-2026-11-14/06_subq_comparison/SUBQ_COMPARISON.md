# SubQ Comparison & Coverage Analysis (final_v3, 2026-11-14)

**Purpose:** Use SubQ (subquery) comparison to evaluate coverage across strategy options before recommending any asset class for deployment.  
**Method:** For each candidate strategy, run SubQ across:
1. **Universe coverage** — how many symbols/asset classes does it cover?
2. **Time coverage** — how much historical data is available?
3. **Cost coverage** — are slippage, fees, funding, borrow, roll modeled?
4. **Regime coverage** — bull, bear, sideways, crisis, low-vol?
5. **Source coverage** — single vs multi-source confirmation?

---

## SubQ Matrix: Candidate Strategies

| Candidate | Asset Class | Universe | Time Span | Costs Modeled | Regimes Tested | Sources | Coverage Score | SubQ Verdict |
|---|---|---|---|---|---|---|---|---|
| Regime-filtered VWAP MR (kilo) | CRYPCO | 5 symbols (BTC, ETH, SOL, XRP, ADA) | ~22 months (4h, yfinance-capped 730d) | 20 bps round trip | Bull/bear/choppy claimed | Single (kilo's harness) | 3/10 | **REJECT** — PBO 0.489 > strict 0.3, single-source, n=129 borderline, not re-executed |
| Vol-Targeted Trend (kilo) | CRYPCO | Not specified (daily) | Not specified | Not specified | Not specified | Single | 2/10 | **REJECT** — insufficient evidence |
| Walk-Forward Variant C (deepAI) | EQUITY/ETF | n=237 | Not specified | Costs NOT deducted | Not specified | Single | 2/10 | **REJECT** — emissions cloned/repeated, null compares selection vs random only |
| H10 SPY/QQQ RSI(2) cash | EQUITY | SPY, QQQ | 2018-01-02 → 2026-11-13 (OOS 2024+) | 5 bps | Bull/bear claimed | Single (H10 only) | 4/10 | **HOLD** — PASSED_GATES but NOT PROVED; effective N≈38 → DSR 0.9365; single-day dependence; T-bill carry component |
| H22 BTC funding carry | CRYPCO | 1 symbol (BTC) | OOS 2024-01-01 → 2026-11-13 | 10 bps | Not specified | Single | 3/10 | **REJECT** — n=10 < 30; capital-adjusted CAGR below T-bill |
| H16_ETF_XS_MOM | ETF | Not specified | OOS 2024-01-02 → 2026-11-13 | 5 bps | Not specified | Single | 3/10 | **REJECT** — n=24 < 30, DSR 0.386, SPA p=0.488 |
| H18_ETF_TSMOM_BREADTH | ETF | Not specified | OOS 2024-01-02 → 2026-11-13 | 5 bps | Not specified | Single | 3/10 | **REJECT** — fails "0.3 above benchmark" (1.00 vs 0.99) |
| CRYPCO daily 50/200 trend (proposed) | CRYPCO | Frozen liquid universe | Not yet run | To be modeled | Bull/bear | To be multi-source | 0/10 | **PROPOSED** — needs SubQ run |
| EQUITY sector-neutral QVM (proposed) | EQUITY | Fixed large-liquid universe | Not yet run | To be modeled | Bull/bear | To be multi-source | 0/10 | **PROPOSED** — needs SubQ run |

---

## SubQ Coverage Gaps Identified

| Gap | Evidence | Impact |
|---|---|---|
| No multi-source confirmation for any candidate | All 166 live cells single-source; all research candidates single-source | Cannot validate any edge independently |
| No cost modeling for most candidates | Only H10 (5bps), H16/H18 (5bps), H22 (10bps), VWAP (20bps) have costs; most peers don't model costs | Overstates profitability |
| No regime diversity testing | Most candidates claim bull/bear but don't test bear-inclusive OOS separately | IT-005 trend failed bear-inclusive rerun (Sharpe 0.57, p=0.200) |
| No SubQ comparison run at all | This is the first SubQ matrix | Cannot compare coverage objectively |
| No multiple-testing correction in horizon harness | `MIN_WINDOWS=4` not enforced; no BH/Bonferroni | False positive risk |
| No block-bootstrap CI on net expectancy | Not implemented in harness | Cannot exclude zero expectancy |

---

## SubQ Recommendation

**Run SubQ on exactly two candidates before any deployment:**

1. **CRYPCO daily 50/200-day time-series trend** (long/flat, vol-targeted) — highest n in live ledger (3,705), longest candidate history
2. **EQUITY monthly sector-neutral QVM** — second-highest n (250), WR 59.2% though PF <1.0

Both need: multi-source confirmation, cost modeling, regime testing, multiple-testing correction, block-bootstrap CI, SubQ coverage score ≥7/10 before deployment consideration.
