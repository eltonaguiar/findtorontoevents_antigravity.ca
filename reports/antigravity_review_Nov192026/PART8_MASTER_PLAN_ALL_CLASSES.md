# PART 8 — Master Plan: One Phase Per Asset Class
**Author:** githubcopilot-mercury3AI · **Date:** 2026-11-22 · **Status:** EXECUTING
**Inherits:** P6 6-criteria ALLOCATABLE test · P7 statistic stack (PSR/DSR/PBO/power) · 8-gate desk standard

---

## 0. Scope correction (accepted)

The prior sweep set `--min-n 100`. That silently deleted **BOND (n=35), FUTURES (n=4), ETF slices, PENNY_STOCK, MUTUAL_FUND, INDEX** — a class with 4 rows must appear labelled `INSUFFICIENT_N`, never vanish. Full ledger inventory, no minimum:

| class | n | WR | PF | net%/trade | CI-lo | 2×-CI-hi | DSR | required_n | MDE | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 6,874 | 40.2% | 0.834 | −0.316 | −0.579 | −0.178 | 0.000 | 1,556 | 0.15 | **KILL** |
| EQUITY | 942 | 45.0% | 1.075 | +0.158 | −0.428 | +0.692 | 0.011 | 10,138 | 0.52 | WEAK |
| ETF | 590 | 42.9% | 0.996 | −0.004 | −0.439 | +0.383 | 0.001 | 3,388,052 | 0.33 | WEAK |
| FOREX | 279 | 36.6% | 0.665 | −0.138 | −0.354 | +0.024 | 0.000 | 384 | 0.16 | WEAK |
| COMMODITY | 45 | 15.6% | 0.117 | −3.510 | −5.542 | −2.167 | 0.000 | 18 | 2.19 | **KILL** |
| BOND | 35 | 40.0% | 0.654 | −0.184 | −0.384 | −0.018 | 0.000 | 214 | 0.46 | WEAK |
| FUTURES | 4 | 50.0% | 1.872 | +1.285 | −2.948 | +5.369 | — | 123 | 7.11 | **INSUFFICIENT_N** |
| PENNY_STOCK | 0 | — | — | — | — | — | — | — | — | **NO DATA** |
| MUTUAL_FUND | 0 | — | — | — | — | — | — | — | — | **NO DATA** |
| INDEX | 0 | — | — | — | — | — | — | — | — | **NO DATA** |

Two facts fall out immediately:
1. **`required_n` for ETF is 3.39 million.** The class-level ETF "verdict" from the pick ledger is statistically uninformative — not because ETF is bad, but because per-*trade* ETF picking has an edge so close to zero relative to its dispersion that no realistic sample could resolve it. **This is why the ETF opportunity is at the *portfolio* level, not the pick level.**
2. Three of ten classes have **never been measured at all**. That is the biggest gap in the project, and it is fixable with free data (done — 61 new series pulled, `MANIFEST2` sha `fd075cd4…`).

---

## 1. Phase map

| Phase | Class | Status now | Primary question | Delivery |
|---|---|---|---|---|
| **P8.0** | cross-cutting | — | Is our *detector* trustworthy? | gate power curve, effect injection |
| **P8.1** | EQUITY | WEAK ← ledger | Does cross-sectional skill exist net of 20bp? | IC/IR + decile L/S |
| **P8.2** | ETF | WEAK ← ledger | Is there a *portfolio* that beats buyable alternatives? | 9 sleeves vs 6 real funds |
| **P8.3** | MUTUAL_FUND | **never measured** | Do any real funds beat their index after fees? | 9 funds, 1980-2026 |
| **P8.4** | BOND | WEAK, n=35 | Is duration beta masquerading as edge? | curve carry+roll vs duration-hedged |
| **P8.5** | FOREX | WEAK, n=279 | Is "edge" actually carry beta? | carry-decomposed, vs passive carry basket |
| **P8.6** | COMMODITY | KILL, n=45 | Does roll yield rescue/destroy it? | roll-inclusive futures |
| **P8.7** | FUTURES | INSUFF, n=4 | Is time-series momentum real across 17 contracts? | TSMOM battery |
| **P8.8** | INDEX | **never measured** | Can anything beat the index itself? | 8 indices, trend/vol-target overlays |
| **P8.9** | PENNY_STOCK | **never measured** | Is the cost gate even reachable? | cost-cushion arithmetic |
| **P8.10** | CRYPTO | KILL ← ledger | Is anything left after honest costs? | cross-sectional + trend, 11 coins |
| **P8.11** | synthesis | — | What, if anything, is allocatable? | verdict table + sizing + forward harness |

---

## 2. Per-phase specification

Each phase runs the **same five instruments** so results are comparable across classes:
- **Battery:** buy&hold · 12-1 cross-sectional momentum (top-3, lag 1m) · 1-month reversal · 10-month trend filter · vol-target overlay · (class-specific extra).
- **Stat stack:** CAGR, vol, Sharpe, MDD, Calmar, worst-12m, PSR, DSR (with disclosed trial count K), block-bootstrap 5th pct, split-half, 2×/4× cost, CVaR95, longest underwater, HHI.
- **Tier:** `INSUFFICIENT_N` / `WEAK` / `CANDIDATE` / `PROVEN_T2` — PROVEN requires ≥100 forward observations, always.

### P8.0 — Detector validation (must run first)
`edge_stability_harness` demands `eff≥0.30` on windows of `n≥80`, where the MDE at n=80 is ≈0.44 — **it can pass what it cannot detect**. Plant known edges in synthetic pick streams, run the real gate, publish TPR/FPR. Then inject a known drift into *real* bars and confirm the pipeline recovers sign and magnitude. Exit: a published operating-characteristic table, and a written statement of what "11/11 killed" actually means.

### P8.1 — EQUITY
Data: survivorship-aware large/mid-cap basket + cross-sectional panel. Tests: rank-IC per horizon (1/5/21/63d), IC decay, decile long-short net 20bp, factor-neutral alpha (Carhart + NW t), and a **breadth** test (does it work on 200 names or only 20?). Killed already: PEAD 30d (H-010). Blocked: H-016 needs 1-min bars (paid). Exit: is there net cross-sectional skill, and is it momentum, reversal, or neither.

### P8.2 — ETF
Already have 9 sleeves measured (PART6 results). Finish: variant grid → DSR with K disclosed, PBO via `tools/pbo.py`, and the **honest counterfactual** (AOA/AOR/VBIAX/VASGX/60-40). Exit: best sleeve vs best buyable fund, on Sharpe, MDD and worst-12m.

### P8.3 — MUTUAL_FUND
Data: VWELX, DODGX, SEQUX, PRWCX, VTSAX, VFIAX, VBIAX, VASGX, VBMFX (1980→2026, real NAVs, fees already netted). Tests: CAGR/Sharpe/MDD vs VFIAX & SPY; rolling 10-yr excess; persistence (does last-decade winner win next decade?); fee drag. Exit: are mutual funds a *product* answer (yes/no) rather than an edge — and which one, if any, has durable alpha.

### P8.4 — BOND
Tests: duration beta decomposition; carry+roll-down vs duration-hedged excess return; curve-momentum (2s10s) re-test **with correct publication/measurement timing**; convexity check. Exit: is any bond result more than duration exposure.

### P8.5 — FOREX
Data: 8 majors + rate differentials (FRED key available). Tests: momentum, carry (long high-yielder), value (PPP), and the decisive one — **regress the strategy on a passive carry basket**; if R²>0.7 the "edge" is carry beta. Exit: net-of-spread alpha vs carry benchmark.

### P8.6 — COMMODITY
Tests: roll-inclusive returns (front vs second contract), term-structure carry, seasonality, COT **lagged T+3**. Exit: does roll yield explain the entire result.

### P8.7 — FUTURES
Data: 17 continuous contracts. Tests: TSMOM (1/3/6/12m, long-short, vol-scaled), cross-sectional momentum, crisis-alpha check (2008, 2020, 2022). Exit: is the documented TSMOM premium present in this sample net of roll and commission.

### P8.8 — INDEX
Tests: buy&hold each index; 10-month trend filter; vol-target; drawdown comparison across US/EU/JP/HK/CA. Exit: is there a *systematic* overlay that improves the index itself — this is the "can we beat the S&P" question in its purest form.

### P8.9 — PENNY_STOCK
Tests: survivorship-biased basket is disclosed; the real deliverable is **arithmetic** — round-trip cost for sub-$5 OTC (spread 100–500bp) vs median measured edge (~20–40bp). Compute the **cost cushion** and the break-even spread. Exit: either a cost-feasible construction or a documented *structural* impossibility (a legitimate, publishable negative result).

### P8.10 — CRYPTO
Tests: cross-sectional momentum across 11 majors, trend filter, vol-target; honest 30–60bp costs; benchmark vs BTC buy&hold. Exit: does anything beat simply holding BTC risk-adjusted after real costs.

### P8.11 — Synthesis
One table: class → best construction → Sharpe/MDD/worst-12m → tier → **what it costs you to be wrong**. Sanction sizing per P6 pre-commitment (WEAK=$0, CANDIDATE≤10% for 90 days paper, PROVEN≤40% with kill-switch). Then wire the forward harness.

---

## 3. Delegation protocol (other AI keys)

Channels verified live: `tools/consult_multi.py` (**14 providers have keys**: nvidia, groq, cerebras, together, fireworks, github_models, huggingface, gemini_api, cloudflare, deepinfra, nous, mistral, aimlapi, hypereal) · `/consult-PROXY` DebateTeam · Kilo global config (30 provider groups incl. openrouter 15 models, aihubmix 22, topnotch 16) · per-vendor `/consult-*` · COMS peers.

Two distinct uses, never mixed:

**(a) Industry research** — per class, ask: *what does the professional literature and desk practice say the durable return sources are for this class, what has decayed post-publication, and what data would we need to test the surviving ones?* Output → `DELEGATED/RESEARCH_<class>_<provider>.md`.

**(b) Method critique** — *given these numbers and this gates, what is wrong with our measurement?* Output → `DELEGATED/CRITIQUE_<phase>_<provider>.md`.

Both carry the mandatory `LEAKAGE-CONTEXT` block. Adoption rule (§4.3 of P6): a delegated claim enters the record only if it names a checkable defect in our code/output, proposes a re-runnable computation, or contradicts another model on a checkable fact. **No delegation output may change a number I computed.**

Rate-limit discipline: sequential, probe-first, cache outputs, never re-ask a channel that answered.

---

## 4. Exit criteria for the whole of Part 8

- Every one of the 10 classes has a verdict with `n`, and `INSUFFICIENT_N`/`NO DATA` are stated as such rather than omitted.
- Every verdict carries PSR/DSR with the trial count K disclosed.
- At least one class reaches `CANDIDATE`, **or** the project publishes a defensible "only beta is available; here is the best beta" answer with the measured cost of each alternative.
- The forward harness is live and will promote/kill without further human judgement.

---
*Not personalized investment advice.*
