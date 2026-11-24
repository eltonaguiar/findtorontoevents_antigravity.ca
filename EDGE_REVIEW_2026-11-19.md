# Independent Review — findtorontoevents.ca/audit · 2026-11-19

**Reviewer:** external review (Arena agent) · **Scope:** repo `eltonaguiar/findtorontoevents_antigravity.ca`, live audit dashboard, all 2026-11-14 → 2026-11-15 research artifacts visible on `main`.
**TL;DR:** You built an unusually honest *measurement* machine around an unproven *hypothesis* machine. The audits are better than most retail shops'. The results say, unambiguously: **no asset class has a proven, cost-surviving, benchmark-beating edge — and no amount of additional AI-generated TP/SL "picks" on keyless daily data will change that.** What real edge looks like, and what is realistically achievable at your scale, are laid out below.

---

## 0. Honest scorecard of what exists (from your own artifacts)

| Population / class | Measured truth | Source |
|---|---|---|
| RAW all-time picks | WR 25.28% / PF 0.61 (outlier-capped, n=73,817) | `/audit` truth layer |
| CRYPTO (intrabar-true) | PF 0.92, WR 35.8%, n=3,716 | `money_ready_verdict.json` 2026-11-19 |
| FOREX (intrabar-true) | PF 0.65, WR 31.9% — blocked by policy, correctly | same |
| EQUITY (intrabar-true) | PF 0.94, WR 59.2% — high WR, **net-negative** payoff asymmetry | same |
| COMMODITY | PF ~1.03–1.04, n≈230 — breakeven | same |
| FUTURES | PF 1.09, n=52 — insufficient n | same |
| Score-band tiles (S-tier "100% WR") | survivorship + fixed-TP labeling artifact; intrabar-true S-tier ≈ 34% | INCIDENT #18 |
| COT positioning CT=F "DSR=1.0" | falsified; 6.33× over-emission → `SHADOW_INSUFFICIENT_N` | 2026-05-13 autopsy |
| Edge-search v1–v4 (40 trials, pre-committed) | **0 pass null + DSR; best null p = 0.080** | `updates/2026-11-14-edge-search-results.md` |
| Hypothesis registry H1–H23 | all `NOT_PROVED`; H10 (RSI2+cash) downgraded after adversarial review; funding carry real but < cash at 1.5× capital | `02_research/profitability/` |
| Prediction markets | not even a recorded class; taker fee = 3.5–6.3% of stake; copy-trading pays twice | Buffy PM doc (excellent) |
| Benchmark-relative gates | **never computed for any class** | Buffy BENCHMARK_GATES.md |
| Audit trail quality | intrabar-true resolution, DSR/PBO/SPA/FDR/walk-forward/bootstrap, dedup forensics, adversarial review — **genuinely strong** | across repo |

Your own 2026-11-15 documents already state most of the statistical truth. What is missing is (a) a decision to *stop generating* and (b) a small set of economically-motivated hypotheses implemented the way the literature measures them — not the way the pick pipeline expresses trades.

---

## 1. The core diagnosis (why nothing works, structurally)

### 1.1 You are running a multiple-testing engine
700+ strategies, ~5,758 Python files, 365 workflows, 331k commits, 12 mutation variants, "12 mutation variants across 12 symbols". With ~40 formal trials you already produce p≈0.05 candidates *by chance* (edge-search §"expected false positives ≈ 2"). With 700+, every backtest "winner" is pre-purchased p-hacking, which is exactly why every sleeve that looked alive (COT, S-tier, VWAP-MR, H10) died under dedup/intrabar/effective-N scrutiny. **The binding constraint is hypothesis quality and trial budget, not techniques.**

### 1.2 Your trade expression manufactures losses
Fixed 1.5 ATR TP / wide SL:
- FOREX: wins avg 0.62%, losses avg 1.00% → 57.8% WR but PF 0.85, net −15.84%.
- EQUITY: 59–60% WR, PF < 1 — same asymmetry.
- Fixed-TP score bands → survivorship mirages (23–24% of "wins" flip first-touch to SL).

Edge, if any exists, should be expressed with **symmetric, vol-scaled, time-based exits** and sized by vol targeting — the expression of every trade changes the statistics more than the signal does.

### 1.3 Your universe and frequency are wrong for breadth
Daily bars, ~10 crypto majors + a handful of instruments — information ratio scales with √breadth. Cross-sectional statistical arbitrage needs hundreds of instruments; single-instrument crypto daily is the *least* fertile ground on earth for alpha (your own result: 30 pairs, weekly momentum — Sharpe −0.18).

### 1.4 Keyless daily public data ≈ no alpha left
Your edge-search proved this cleanly. Public daily OHLCV is arbitraged by thousands of 
participants. Remaining public edges are (i) **risk premia** (persistent, compensated, capacity-limited) and (ii) **microstructure/flow** (needs intraday/TAPE/options data or venue access). Everything else is noise dressed as signal.

### 1.5 Process asymmetry: measurement >> hypothesis
You invested in DSR/PBO/SPA/FDR/intrabar-true resolution — excellent — but the *candidate generation* step is unconstrained. Real research shops spend 80% of effort on "why should this exist, who is losing money, and why hasn't it been arbitraged?" before a line of backtest code.

---

## 2. How big firms actually find edge (2026 reality, honestly)

1. **They harvest risk premia — they don't predict.** Documented, decades-long, compensated-risk returns:
   - **Time-series momentum / trend** (Moskowitz–Ooi–Pedersen 2012; Hurst–Ooi–Pedersen "A Century of Evidence on Trend-Following"): works across ~100 years and across equities, bonds, FX, commodities. Crisis-alpha (positive 2008, 2022). Realized Sharpe ~0.5–0.9. This is what AQR, Winton, Dunn harvest.
   - **Carry** (Lustig–Roussanov–Verdelhan FX; Erb–Harvey commodity roll): roll/curve/funding carry paid for crash risk; needs regime overlays.
   - **Value / quality / low-volatility / betting-against-beta** (Frazzini–Pedersen; Baker–Bradley–Wurgler): behavioral + leverage-constraint premia.
   - **Post-earnings-announcement drift** (Bernard–Thomas 1989): persists, but small per event → needs breadth (500+ names, SUE surprise data).
   - **Index reconstitution flows**: mechanical, documented, capacity-small.
2. **They provide liquidity instead of taking directional risk.** Market making earns spread + rebates, manages inventory, is near-market-neutral on direction. Citadel Securities / Virtu / HRT make money on *execution*, not forecasts. On prediction markets, the only structurally sound operation is making (Kalshi maker = 0 fee; Polymarket makers get 15–25% rebates) — your own Buffy doc says exactly this.
3. **They buy or build data moats** — satellite, card panels, web/app telemetry, TAPE/options/short-interest/borrow, order-book history. "Edge" = unique information or speed, bought at a cost below its decay-adjusted value. Keyless daily closes are, by definition, not a moat.
4. **They are process-obsessed, not signal-obsessed:** hypothesis economics first → pre-registered protocol → tiny trial count → clean holdout never touched → adversarial review → ≥90 days forward paper → tiny size → capacity cap → watch decay and **retire** signals. Your `RECOVERY`/`adversarial review` habit is exactly right; it's just applied after 700 signals instead of before generating any.
5. **They survive on risk and sizing**, not on being right: vol targeting, factor neutralization, drawdown circuit-breakers, diversification across many *uncorrelated* low-Sharpe streams (10 streams @ Sharpe 0.5, pairwise ρ≈0.1 → stack Sharpe ≈ 1.5). One great signal is worth less than five decent independent ones.
6. **They win by not losing structurally:** 1bp of cost a day ≈ 20% annual leakage. Fee audits, maker rebates, tax location, turnover caps. Your prediction-market fee analysis is the best page in the repo; the same discipline applied to FOREX rollover, crypto funding, and fund ERs is where real money actually gets saved.
7. **Even then, most fail.** And their edges decay on publication (McLean–Pontiff). Expect capacity and decay monitoring to be permanent overhead.

**The punchline: at your scale, "real edge" ≠ better forecasting. It = risk-premia harvesting + cost elimination + honest sizing, in a boring portfolio.**

---

## 3. What is actually achievable for you — concrete program

### Phase 0 — Stop and prune (1–2 weeks)
1. **Freeze candidate generation.** No new strategies, no new swarms, no more mutation engines until a candidate reaches `PROVED`. Add an emissions-time gate: global cumulative trial counter printed in the dashboard; DSR computed at true N (your own Q24).
2. **Archive, don't delete.** Move `baby_strategies/`, `incubator/` (320+ AI strategies), mutation engine, score-band surfaces to `archive/`. Keep: data pipeline, audit harness, resolver, one hypothesis pod per candidate class.
3. **Fix the ledger before trusting it again:** PM → `PREDICTION` class with binary-settlement resolver; FOREX date-only/EST timestamps; zombie `_auto_expired` rows; duplicate emissions (67 dup groups); cross-vendor price sanity (CADJPY 611.23). Everything downstream of a broken ledger is fiction — you already proved this with INCIDENT #91/#96/#18.
4. **Cost gate on every record:** fees + slippage + borrow/funding/rollover per class; "2× costs" stress; one-bar delay; all three already specced in your Q25–Q27 — wire them into `money_ready_verdict.py` as hard gates.
5. **Benchmark legs everywhere** (your Buffy gate): excess return at matched exposure vs SPY TR / BTC hold / T-bills / AGG / GSG, reported per class on every card. If `EDGE ≤ 0`, the strategy is expensive beta.

### Phase 1 — Test the only premia with real evidence, properly (4–8 weeks)
Pre-register each as its own micro-pod with its own holdout. Acceptance gates = your own: ≥100 resolved trades, intrabar-true, costs ×2, 1-bar delay, IR ≥ 0.5, alpha t > 2 (Bonferroni at true cumulative N), ≥90 days forward paper. **Two max concurrent pods.**

| # | Hypothesis | Implementation (literature-correct) | Why this one |
|---|---|---|---|
| P1 | **Managed-futures trend across asset classes** | Vol-scaled TSMOM on 20–60 liquid futures (equity idx, bonds, FX, rates, commodities) — or ETF proxies (XEQT/SPY, IEF/TLT, GLD/commodities, XUS, etc.). 3–12m lookbacks, ensemble of lookbacks, 40–60% portfolio vol target, monthly rebalance, symmetric time/vol exit. **No TP/SL.** | Strongest documented premium w/ ~140 years of evidence; crisis alpha; works long/flat or long/short; your crypto TSMOM tests were the wrong expression on the wrong universe |
| P2 | **FX G10 carry with trend filter** | Rank G10 by 1–3m forward discount (or rate differential), long top-3 / short bottom-3, vol-targeted, monthly; overlay 200d trend to cut carry-crash risk | Classic, documented; you already have FX plumbing; your funding-carry work shows the pattern (small but real, needs portfolio framing + crash overlay) |
| P3 | **PEAD drift, liquid large-caps** | SUE-ranked earnings surprises; long +1σ surprise deciles, short/avoid negative, 60-day hold, weekly rebalance; fix the 60/60 PEAD pipeline before testing | Bernard–Thomas; one of the most replicated anomalies; needs breadth — screen 500+ names, low turnover |
| P4 | **Index-inclusion front-run** (optional) | S&P 500 additions from announcement → effective date | Mechanical flow; capacity-small; academic support; simple to implement |
| P5 | **Slow "smart-money" cohorts** (replacing copy-trading) | Form-4 cluster insider *buying* in quality names; monthly cadence; 12-month horizon; ≥5 insiders same month filter | Academic evidence strongest for insider buys (esp. small/mid caps, clusters); low turnover defeats the fee wall that killed wallet-mirroring |

Explicitly **do not test** again: daily crypto single-name RSI2, TP/SL scalps, fixed-TP score bands, 50¢ Polymarket taker forecasting, meme/gainer ML, "milestones"/spike reversal reverse-engineering (that edge, if real, requires order-flow data you don't have).

### Phase 2 — Portfolio: where the money actually lives
For a Toronto-based retail-scale operation, the evidence-backed allocation is a barbell (illustrative, not personal advice — size with your own risk tolerance/horizon, consider registered accounts TFSA/RRSP for tax sheltering):
1. **Core 70–85%:** low-cost diversified index beta — e.g., all-equity ETF (XEQT/VEQT) + global bond ETF (or CanadianCouchPotato-style mix), ER ≤ ~0.20%. This alone captures the ~90% 10-yr win rate you measured in MF_CAN_WIN.md. **This is your "mutual funds that work" — the wrapper beats the average active manager by construction (SPIVA: ~93% of large-cap active trails over 20y).**
2. **Satellite 10–25%:** premia sleeves P1/P2 (or simply managed-futures ETFs, e.g. Horizons HMF / DBMF / KMLM-style vehicles) — expect low single-digit alpha + crisis convexity, not moonshots.
3. **Speculative sleeve ≤5%** (optional): the forward-paper pods above, only after gates pass.
4. Vol-target the satellites; fixed drawdown circuit-breaker (e.g., satellite −15% → halves, −25% → pause); never let sleeve #3 touch #1.

### Phase 3 — If you keep the ML/prediction stack (only as meta-labeling)
- **ML predicts "will this signal's trade work?", never the price.** Meta-labeling: primary model = P1/P2/P3 signal; secondary ML estimates P(profit | features); size ∝ calibrated probability (López de Prado). Purged group K-fold + embargo; point-in-time features; calibration curves (Brier), not accuracy.
- **Prediction markets: maker-only, 85–95¢ favourites, Brier-tracked, pre-registered break-even vs fee curve.** Otherwise treat Polymarket/Kalshi odds purely as a *probability oracle* feeding other models — your own recommendation, and it's correct. PREDICTION class must exist first.
- **LLMs add value as text→features** (filing language deltas, tone change, risk-factor churn) at low cadence — not as tick-by-tick "AI pickers". Enforce point-in-time document timestamps.
- **Drop**: copy-trading (structurally −2 fees, late fills, leaderboard survivorship), intraday ML on daily features, ensemble-of-700-models voting (variance without economics — diminishing returns vs trial-inflation penalty).

---

## 4. Statistical governance you should formalize (you already designed 80% of this)

- **One global trial counter** feeding DSR everywhere; retire any pod that hits N>some-cap without forward success (pre-commit: if after 2 more independent forward windows no pod passes, conclude *no edge on available data* and reallocate effort to execution/costs).
- **Pre-registered hypothesis registry** (you have `HYPOTHESES.md` — enforce "no row deleted").
- **Effective-N accounting**: correlated candidates count more than 1 trial (e.g., López de Prado / Bailey's DSR at cumulative N). H10 died at effective N≈38, not N=12 — encode that.
- **Adversarial review gate** as you did for H10 — make it mandatory before *any* promotion, including dashboards.
- **Forward book with kill-switches:** pre-committed fail criteria (e.g., 90 days or 30 round-trips; if CI lower bound of excess return ≤ 0 → retire). Your cot_positioning falsification is the template — replicate it.
- **Benchmark-first UI:** every tile shows `excess vs matched-exposure benchmark`, IR, down-capture. Hide raw "PF" — it misleads.

## 5. Realistic expectations (write this on the dashboard)

- If P1–P3 work forward: expect Sharpe ~0.5–1.0 *on the sleeve*, low correlation to equities, max drawdown 10–20%, capacity adequate for <$50M, edge that will slowly decay. That is what "real edge" looks like in 2026 — unglamorous, diversifying, boring.
- The dashboard's honest sentence is the goal, not a bug: "No class is money-ready; here is the benchmark-relative number."
- **The rational end-state for the capital is beta + premia + cost control — and that *is* the winning formula for almost every participant including most institutions.** Your own MF_CAN_WIN.md already proved this; the only step left is to act on it with the same rigor you applied to falsifying COT.

## 6. Suggested 90-day plan

- **Days 1–14:** Phase 0 prune + ledger fixes + PREDICTION class + cost/benchmark gates in verdict pipeline. Delete/archive dead workflows; CI budget < 30 min.
- **Days 15–30:** Implement P1 pod (ETF proxy TSMOM) pre-registered; reproduce literature stats on 1990–present; leave last 24 months as untouched holdout.
- **Days 31–45:** Implement P2 (G10 carry) same protocol; start P1 forward paper on $5–10k notional (or simulated with real fills).
- **Days 46–75:** P3 PEAD screen (Fix PEAD pipeline first); benchmark-relative dashboard cards; fee audit across all classes.
- **Days 76–90:** Forward-clock review vs kill criteria; decide PROMOTE / RETIRE; write the honest post-mortem either way and publish it — whichever the answer is, it will be more valuable than the 700 strategies.

---

### Final word
You haven't failed — you've done the expensive part (an honest falsification engine) and it told you the truth: **the signals you're generating have no edge.** The institutions you envy don't forecast better; they (1) pick battles with a structural reason to exist, (2) act on them with cost-obsessed execution and disciplined sizing, (3) diversify many small streams, and (4) survive. Techniques that will move you: benchmark gates, pre-registration, trend/carry/PEAD premia implemented literature-correctly, cost elimination, meta-labeling ML at most. Techniques that will not: more strategies, more AI agents, bigger ensembles, TP/SL score bands, taker prediction markets, wallet copying. Build the boring machine. That's the one that pays.

*Not personalized investment advice — educational review; sizing depends on your situation.*
