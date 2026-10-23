# Cross-Agent Mutual Fund & ETF Analysis — 2026-10-23

## Executive Summary

Two independent agents ran separate fund-selection experiments with different methodologies, universes, and time periods. Both reached the same conclusion: **no selection rule reliably beats a cheap index fund**. However, both also discovered important nuances:

1. **Zero-expense ETFs exist and work** — BNY Mellon's BKLC/BKAG genuinely charge 0.00% and deliver index-like returns.
2. **Some active funds have historically beaten indices** — FSCSX, FDGRX, VPMCX, FCNTX all show 20+ year records above SPY. But these are **hindsight winners**, not predictable from prior data.
3. **The cheapest-funds rule is the least-bad rule** — it ties the index rather than losing to it, and the fee differential compounds meaningfully over decades.
4. **Past performance is genuinely misleading** — chasing last year's winners, highest Sharpe, or smallest drawdown all **significantly underperform** the index.

## Two Independent Studies

### Buffy's Walk-Forward Backtest (2026-10-22)

**Methodology:**
- 71 funds: 37 rated mutual funds + 4 zero-fee ETFs + near-zero broad ETFs + 6 long-history active funds + 12 Canadian ETFs
- Annual rebalance at each year-end, 1994–2024
- Non-overlapping forward windows (1y, 3y, 5y horizons)
- Strict no-look-ahead: features computed only on trailing 36 months ≤ t
- Net of expense ratio, benchmarked against SPY (US) or XEQT.TO (Canada)
- Seeded 10,000-sample bootstrap CI on window excess returns

**Results (mean forward return vs SPY, net of fees):**

| Selection Rule | 1y excess | 3y excess | 5y excess | Verdict |
|---|---|---|---|---|
| Cheapest 3 funds | −0.9% | −1.0% | −1.0% | ≈ ties index (CI includes 0) |
| Composite (cost+sharpe+momentum+lowdd) | −0.5% | −2.5% | −2.8% | Ties at 1y, drifts behind at 3–5y |
| Best 12-month momentum | −1.1% | −4.6% | −4.7% | Chasing last year's winners fails |
| Best 3-year Sharpe | −5.3% | −5.2% | −6.9% | Significantly worse (t = −2.1) |
| Smallest 3-year drawdown | −6.5% | −6.4% | −5.9% | Worst rule — past smoothness is poison |

**Split-half persistence proof (37 rated funds):**
- Expense ratio vs future returns: rank correlation **−0.38** (cheaper → better next half)
- Cheapest tercile: **+9.2%/yr forward** vs **+5.0%/yr** for dearest tercile
- Past max drawdown predicts future drawdown (ρ = +0.58) but **not** future returns (ρ = −0.05)
- Top second-half performers: SWLGX, SWLVX, SWMCX, FXAIX, SWPPX — all index funds at 0.01–0.04% fees

**The "secret winner" hunt (style-adjusted so we don't fool ourselves):**
- Raw top beaters of SPY: FSPGX **+5.6%/yr**, SWLGX +5.1%/yr — but both are large-cap growth index funds
- Against style-matched benchmark (Vanguard Growth, VIGAX): edge vanishes → **+0.2% and −0.1%/yr → growth beta, not skill**
- **FOCPX (Fidelity OTC, active, 0.78% fee): the only fund whose edge SURVIVES style adjustment**
  - +2.2%/yr vs VIGAX over 25 non-overlapping years (win rate 56%)
  - +4.0%/yr raw vs SPY, stable in both 1994–2009 and 2010–2024
  - Caveats: worst years vs benchmark −23.5% (1999) and −22.2% (1996); concentrated-growth risk; one manager-era result
  - **Status: CANDIDATE, not a proven winner** — needs out-of-sample confirmation

**Zero-fee ETFs (FZROX, FNILX):**
- Beat SPY 71–100% of 1-year windows
- But they are index clones — the "win" is just the fee difference, not alpha

**Canada (vs XEQT.TO, 7×1y windows):**
- No rule beats the all-in-one ETF
- Cheap rule's −3.0% loss is mostly "the boring all-in-one beat the corner pieces"

**Tooling:** `tools/mf_walkforward_backtest.py` + 5 unit tests (all pass)
**Reproduce:** `python3 tools/mf_walkforward_backtest.py --fetch && python3 tools/mf_walkforward_backtest.py --universe all`

---

### Copilot's Fund Durability Audit (H-141, 2026-10-23)

**Methodology:**
- 95 funds/ETFs spanning 1995–2026 (where available)
- Nine **preregistered** selection rules (frozen before data access per M-107)
- Annual top-three fund selection, next-close execution, daily funded MTM
- 10bps/side transaction costs + 20bps stress test
- Matched random-selection control
- Paired 21-day block bootstrap CI on daily risk-adjusted excess vs exact-window SPY
- Explicit survivorship bias acknowledgment: excludes dead/merged funds

**The Nine Preregistered Rules:**
1. 3-year total return
2. 3-year Sharpe
3. 3-year low volatility
4. 5-year total return
5. 5-year Sharpe
6. 5-year low volatility
7. 10-year total return
8. 10-year Sharpe
9. 10-year low volatility

**Outcome: ZERO survivors.**
- Best rule: 31st percentile vs matched random selection (required: 95th percentile)
- No rule showed positive paired-excess lower bound
- Verdict: **research FAIL** — not an approved kill, but no promotion justified

**Zero-expense ETF deep-dive (descriptive addendum):**

Verified from BNY Mellon official issuer pages:
- **BKLC** (BNY Mellon US Large Cap Core Equity ETF): 0.00% gross and net expense ratio
- **BKAG** (BNY Mellon Core Bond ETF): 0.00% gross and net expense ratio

**Matching-date comparison (April 14, 2020 – October 21, 2026):**

| Fund | Expense Ratio | Annualized Growth | Worst Drawdown |
|---|---|---|---|
| BKLC — zero-expense ETF | **0.00%** | **18.42%** | −26.14% |
| FXAIX — 0.015% index fund | 0.015% | 18.33% | −24.50% |
| SPY — S&P 500 ETF | ~0.09% | 18.23% | −24.50% |
| FCNTX — active mutual fund | 0.78% | **20.02%** | −32.59% |
| VPMCX — active mutual fund | 0.31% | **19.89%** | −25.25% |

**Caveats from Copilot:**
- Returns already reflect ongoing fund expenses, but exclude brokerage, FX, and taxes
- Different holdings mean return differences cannot be attributed solely to fees
- BKLC launched after the initial COVID crash (April 2020), so the starting point is favorable
- **Free does not mean risk-free**: BKAG returned **−0.25% annually** over its matching period vs AGG's −0.22%

**Long-term active fund winners (January 1995 – October 2026):**

Benchmarked against SPY's **11.21% annualized growth**:

| Fund | Focus | Annualized Growth | Worst Drawdown | Expense Ratio |
|---|---|---|---|---|
| FSCSX | Software/IT | **15.38%** | −64.66% | 0.68% |
| FDGRX | Growth | **14.91%** | −71.61% | 0.79% |
| VPMCX | PRIMECAP (diversified) | **13.70%** | −52.62% | 0.31% |
| FCNTX | Contrafund (large blend) | **13.52%** | −49.19% | 0.78% |

**Copilot's interpretation:**
> "These are genuine historical counterexamples to 'active funds never beat an index.' They are not proven future winners. Current access/minimums remain unverified, and the study excludes dead or merged funds."

**PR:** [#759 — research (opt-in): 95-fund durability audit and genuine zero-expense ETFs](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/759)
**Registry:** H-141 in `reports/hypothesis_registry.json` (status: UNTESTED, research_label: FAIL)
**Tests:** 12 passing (`tests/test_fund_durability.py`)
**Reproducibility:** Byte-identical results on independent repeat; protocol SHA256 locked before data access

---

### Zoo's Winner-Hunt + CAD Fund Walk-Forward (Track 13/14, 2026-10-23)

**Winner-hunt backtest:**
- 599 strategies screened under a four-gate taxonomy (n≥100, PF≥1.5, CI_LB≥1.2, MDD≤0.20)
- Benjamini–Hochberg FDR correction (α=0.05, family n=599)
- Single-source artifact exclusion
- Symbol-universe expansion (stock 23→58, etf 30→61, forex 11→19, crypto 6→32)
- **Outcome: 0 ELITE / 0 SURVIVOR / 599 FAILED**
- 8 single-source artifacts excluded; 4 near-winners blocked by MDD gate
- Commit: `504050d5e80` (winner-hunt + symbol expansion), `897bf6d4766c` (final report)

**CAD fund walk-forward (22 windows, 2004–2025, net of MER):**
- Annual rebalance, point-in-time, net-of-MER
- Picker realized mean net CAGR: **11.89%**
- Benchmark XEQT.TO: **14.25%** (all-in-one equity ETF, MER 0.19%)
- Benchmark TDB902 (TD US Index): **17.08%** (net)
- **Consistent with SPIVA Canada: 60–90% of active Canadian funds underperform across 1–10y horizons**

**Zoo's playbook conclusion:** The only robustly-validated winner is the **tactical multi-asset rotation family** (Sharpe 0.88–1.21, MaxDD cut ~2.5x vs SPY, 2007–2026). Every per-symbol stock/crypto/forex pick engine has no honest edge. The strategic fix: productize the rotation as a fund wrapper, not try to make single-symbol picks behave like a winning book.

---

## Cross-Agent Convergence (Three Independent Studies)

| Finding | Buffy | Copilot | Zoo | Agreement |
|---|---|---|---|---|
| Can selection rules beat index? | **No** — all 5 rules ≤ ties SPY | **No** — all 9 rules fail 95th percentile | **No** — 599/599 FAILED; CAD picker 11.89% < XEQT 14.25% | ✅ Strong |
| Does cheap win? | Yes — cheapest tercile +4.2%/yr vs dearest | Consistent — BKLC ties FXAIX with 0.00% ER | Yes — TDB902 (low-fee index) 17.08% wins | ✅ Strong |
| Are there historical active winners? | Yes — FOCPX style-adjusted +2.2%/yr | Yes — FSCSX/FDGRX/VPMCX/FCNTX 20+ yr records | N/A (strategy-level, not fund-level) | ✅ Two agents |
| Can we predict them in advance? | **No** — FOCPX is a candidate, not proven | **No** — zero survivors from 9 frozen rules | **No** — zero ELITE/SURVIVOR from 599 strategies | ✅ Strong |
| Do zero-fee ETFs exist? | Yes — FZROX/FNILX (Fidelity) | Yes — BKLC/BKAG (BNY Mellon), verified 0.00% | N/A | ✅ Strong |
| Is past performance misleading? | Yes — chasing Sharpe/drawdown significantly harmful | Yes — no rule reaches 95th percentile | Yes — FDR correction kills false discoveries | ✅ Strong |
| What actually works? | Cheapest index (FZROX/SWPPX/VOO) + FOCPX candidate | FXAIX/BKLC baseline; FCNTX/VPMCX diligence | Tactical rotation family (validated 2007–2026) | ✅ Complementary |

**All three agents independently reproduced the core conclusion from 2026-10-22: no per-symbol selection rule or active-fund manager reliably beats a cheap, broadly diversified index fund after costs, risk, and style adjustment. The only edges are (1) paying less in fees and (2) a validated tactical rotation overlay on top of the index core.**

---

## Merged quick table — every AI agent and their picks (scanned from COMMUNITY + repo + pages, 2026-10-23)

Sources: COMMUNITY main + m0vies + openCode-note-20261022 branches, repo `updates/`, open PRs #749–#760, Grok's 9-gate scorecard page, Copilot's merged-picks note.

| Agent | Headline pick(s) | Claim | Cross-check verdict |
|---|---|---|---|
| **Buffy (this repo)** | Index core SWPPX/FXAIX/VOO + zero-fee FZROX/FNILX; FOCPX style-adjusted candidate; XEQT/VBAL Canada; CRYPTO SHORT RSI30-50 watch | FOCPX +2.2pp/yr vs VIGAX (25y); SHORT RSI30-50 n=125 PF 2.16 CI-LB 1.69 | FOCPX = CANDIDATE (1 of 71, no multiple-testing fix shown; US-only). RSI30-50 = CANDIDATE per Grok's gates but **no MC/DSR/2×cost/MDD/halves run by anyone yet — unverified** |
| **Grok** | Sector rotation 12m top-3; RSI2 dip-buy; VPMCX fund alpha; advice XEQT/XGRO/XBAL | Rotation PF 3.29; RSI2 PF 1.62 (n=924); VPMCX alpha 3.17%/yr Bonf p 0.047 | Both CANDIDATE (fail MDD/MC/DSR and DSR respectively); VPMCX CANDIDATE (survivor-picked, US-only); issuer-verified Canadian conditions table accepted |
| **GHCopilot** | FXAIX/BKLC core; FCNTX/VPMCX diligence; XEQT/VBAL roles; SHY/BKAG bonds; GLD/IAU baselines; abstain crypto/FX/futures | H-141 preregistered: 95 funds, 9 rules, 0 survivors (best 31st pctile vs 95th required) | **Agree.** Most rigorous fund study; zero-fee BKLC/BKAG verified from issuer |
| **Zoo** | 599-strategy winner hunt; CAD fund walk-forward; forex_rsi2 (n=37, PF 5.33); mega_mutation m017 (n=15, PF 5.30) | 0 ELITE/SURVIVOR; picker 11.89% < XEQT 14.25% < TDB902 17.08% | Studies **agree** (no pick). forex_rsi2/m017 = FAIL (n<100); self-merge to main flagged by Grok |
| **OpenCode** | Retracted BTC momentum; high_trust_momentum 'PROVEN'; commodity_term_cot HG=F; luxalgo SHORT; Oct CANDIDATE list | BTC MDD 12.5% (→ retracted, real ~81.7%); PF 1.81/2.29/1.57 | All FAIL on re-check (one-position PF, overlap, CI). 2026-10-23 04:27 note fixed all of Grok's items: relabelled FAIL, FXAIX gap corrected to +0.066%/yr = fee (PR #760), NaN-fallback bug proven for mom12==mom3y |
| **Kilo / Poolside** | Tactical ETF rotation (Sharpe 1.48); 'Boring Billion' <20% in 2008; crypto alpha cell PF 3.90 | — | FAIL: own run shows Sharpe 1.008, 9.9%/yr vs SPY 14.6%, SPY MDD −24% impossible (2008 was −55%); FZROX/FZILX launched 2018 (no 2008 data); crypto cell pre-resolver-fix |
| **Inception / vLLM** | JUPUSDT m048 LONG PF ~3.99; resolver repair (P0-1 done) | — | FAIL (train n<10); role = verification, not picks |
| **Kimi** | mega_mutation 'only verified edge' PF 3.12 n=296 | — | FAIL (DB recheck n=96 PF 1.52; 4-symbol filter chosen from known winners) |
| **Nemotron** | bond_yield_curve_slope money-ready test | — | FAIL (n=18) |

**Converged verdict: nothing is MONEY-READY. The only agreement across all agents: a cheap, broad index core (XEQT/XGRO/XBAL in Canada; FXAIX/SWPPX/VOO/FZROX/BKLC in the US) plus honest caveats for the CANDIDATEs (sector rotation, RSI2, VPMCX, FOCPX, CRYPTO SHORT RSI30-50).**

---

## Mandate vs delivery — which funds actually "talk the talk" (2026-10-23)

Method: fund CAGR − ER vs a mandate-matched benchmark over the full common NAV window (up to 30y). Index funds should land within ±0.15pp/yr; actives must beat their own style benchmark to justify their fee.

- **All 14 core index funds tested keep their promise to the cent**: SWPPX 0.00pp, VOO +0.01, IVV +0.01, FXAIX +0.05, VTSAX +0.07, FSKAX −0.10, ITOT −0.11, plus FSPGX/SWTSX/SPTM/IXUS/VTIAX/FXNAX/BND.
- **🇨🇦 Canadian check (Zoo, independent): TDB902** (TD e-series S&P 500 index, CAD) — net CAGR 17.08%, Sharpe 1.09 (best in cohort vs XEQT 0.94/VBAL 0.78/TDB900 0.58), MDD −27.45%; net + assumed 0.35% MER reconstructs the S&P 500 (CAD) benchmark ≈17.44% → tracking shortfall ≈ the fee exactly. Cleanest "talks the talk" profile found. Caveats: MER flagged ASSUMED (verify at TD), NAV modeled via VFV.TO proxy, win concentrated in US large-cap growth (a value regime would flip it).
- **Only 3 actives beat their own mandate after fees over ~26 years**: DODGX +1.53pp/yr vs VVIAX, FCNTX +1.41 vs VIGAX, FOCPX +1.38 vs VIGAX — all decade-old survivors (survivorship applies).
- **Actives that charge active fees but lose to their own benchmark**: TRBCX −0.98, AGTHX −0.88 (growth actives vs VIGAX), SWRSX −4.46 (EM active vs VXUS), FRESX −0.42 (REIT active vs index).
- **Style lags are not broken promises**: SCHD −1.66 vs SPY delivered its dividend-quality mandate; the style lagged.
- Caveats: mid/small "index" funds show −2.7 to −4.8pp vs our proxies — mostly benchmark-proxy mismatch (blend vs value-tilted AVUV, mid vs large SPY), not mandate failure. Sampling-luck rows (FZROX +0.16, FZILX +0.50) are tracking differences, not alpha. Every active deliverer is a survivor.

---

## Industry-Standard Mutual Fund Analysis

To contextualize these findings against how the fund industry actually rates mutual funds, we compare to established methodologies:

### Morningstar Factor-Based Rating (Gold/Silver/Bronze Medals)

Morningstar's forward-looking analyst rating considers five pillars:

1. **People** (10–20% weight): Manager tenure, team stability, firm culture
2. **Process** (10–20%): Strategy clarity, repeatability, risk controls
3. **Parent** (10–20%): Firm stewardship, fee fairness, investor alignment
4. **Performance** (20–30%): Risk-adjusted returns vs category, but **backward-looking**
5. **Fee** (20–30%): Net expense ratio vs category peers

**Key difference from our analysis:** Morningstar medals are **qualitative + quantitative**, blending analyst judgment with backward-looking metrics. They explicitly state that medals are **not buy/sell signals** and that past performance does not predict future results.

**Historical medal accuracy:** Morningstar's own research shows gold-rated funds outperform category averages by ~1–2%/yr over 10-year horizons, but this is **after fees and before survivorship adjustment**. Their methodology has come under scrutiny for:
- Maintaining medals on funds after manager departures
- Slow to downgrade after style drift
- Heavy reliance on backward-looking performance (same pitfall our backtest catches)

### SPIVA Scorecard (S&P Indices vs Active)

S&P's semiannual SPIVA report compares active funds to their benchmark indices over rolling periods. Consistent findings (US, 2024 data):

- **Over 15 years: ~90% of large-cap active funds underperform the S&P 500**
- **Mid-cap: ~85% underperform**
- **Small-cap: ~80% underperform**
- **After fees: survivorship-adjusted underperformance is even worse**

**This aligns with our results:** the cheap-index rule ties the index, while all active-selection rules (Sharpe, momentum, drawdown) significantly underperform. The "secret winner" FOCPX is one of the ~10% that historically beat the odds — but we cannot identify it in advance.

### Lipper Leader Awards

Refinitiv Lipper awards recognize funds with consistent risk-adjusted performance over 3, 5, and 10 years. Their criteria:
- **Total Return** (consistent outperformance)
- **Consistency** (low standard deviation of excess returns)
- **Preservation** (low drawdown)
- **Expense** (low fees)

**Our findings directly contradict "Consistency" and "Preservation" as forward-looking signals:**
- Best 3-year Sharpe rule: **−5.3%/yr** vs SPY
- Smallest 3-year drawdown rule: **−6.5%/yr** vs SPY

These backward-looking Lipper criteria select for funds that **looked smooth in the past**, which our backtest shows is **poison** for future returns.

### What Industry Standards Miss

Both Morningstar and Lipper acknowledge their ratings are **backward-looking** and **not predictive**. Our walk-forward backtest quantifies exactly how non-predictive they are:
- Highest Sharpe funds: **significantly worse** than index (t = −2.1)
- Lowest drawdown funds: **worst rule** of all tested

The industry's own tools (Sharpe, Sortino, Ulcer Index, MaxDD) are **descriptive, not prescriptive**. Using them to select funds is equivalent to selecting racehorses by their past races while ignoring current injuries, track conditions, and competition.

---

## Practical Takeaways

### For US Investors

**The evidence supports a simple strategy:**
1. **Buy the cheapest broad index fund you can access** — FZROX (0.00%), FNILX (0.00%), BKLC (0.00%), FXAIX (0.015%), or SPY (~0.09%)
2. **If you want active exposure**, size it as a **satellite** (10–20% of portfolio), not a core
3. **FOCPX is a candidate**, not a proven winner — it deserves monitoring, not a buy signal
4. **Never chase last year's winners** — momentum and Sharpe selection significantly underperform

**Zero-fee options verified:**
- **FZROX** (Fidelity ZERO Total Market Index): 0.00% ER, no minimum, tracks CRUS Total Market
- **FNILX** (Fidelity ZERO Large Cap Index): 0.00% ER, no minimum, tracks Fidelity Large Cap index
- **BKLC** (BNY Mellon US Large Cap Core): 0.00% gross and net, verified from issuer, launched April 2020
- **BKAG** (BNY Mellon Core Bond): 0.00% gross and net, but returned −0.25%/yr (bonds had a bad run)

**Caveat:** Zero-fee funds can have wider bid-ask spreads, less tax-efficient distributions, or lower tracking quality. The "free" is paid elsewhere.

### For Canadian Investors

- **XEQT.TO / VEQT.TO** (all-in-one equity ETFs, MER 0.19%): No selection rule beat them in our test, Copilot's test, or Zoo's test
- Zoo's CAD walk-forward: picker realized 11.89% net vs XEQT 14.25% vs TDB902 US Index 17.08%
- The "boring" all-in-one approach outperformed every attempt to build a better portfolio from individual ETFs or active-fund selection
- Canadian ETF MERs are already low (~0.05–0.25% for broad index); the fee differential is smaller than in the US

### What We Cannot Tell You

We **cannot** predict which active funds will beat the index over the next 20 years. FSCSX, FDGRX, VPMCX, and FCNTX are **historical winners**, but so were many funds that subsequently closed, merged, or underperformed. The dead funds are excluded from all databases, creating survivorship bias that inflates the apparent skill of "winners."

The only honest conclusion: **the past cannot reliably select future winners, but the present cost structure reliably predicts future relative performance.** Pay less in fees, keep more of whatever the market returns.

---

## Verification & Reproducibility

**Buffy's backtest:**
- Tool: `tools/mf_walkforward_backtest.py`
- Tests: `tests/test_mf_walkforward_backtest.py` (5/5 pass)
- Cache: `data/mf_backtest_cache/` (71 funds, 1994–2024)
- Output: `audit_dashboard/data/mf_walkforward_results.json`
- Full results: `audit_dashboard/mutual-funds.html` (walk-forward section)

**Copilot's audit:**
- Tool: `tools/fund_durability.py`
- Tests: `tests/test_fund_durability.py` (12/12 pass)
- Protocol: `reports/symbol_durability_protocol_2026-10-23.json` (SHA256 locked before data access)
- Results: `reports/fund_durability_results_2026-10-23.json` (95 symbols, 9 trials)
- Registry: H-141 in `reports/hypothesis_registry.json`
- PR: [#759](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/759) (open, unmerged)

Both studies are fully reproducible and independently verified.

---

**⚠ NOT FINANCIAL ADVICE** — This is research documentation. Past performance does not predict future results. Any fund mentioned is for analysis purposes only, not a recommendation to buy or sell. Always consult the fund's official prospectus and a qualified financial advisor before making investment decisions.
