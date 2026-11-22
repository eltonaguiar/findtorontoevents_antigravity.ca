# PART 6 — "Worth The Money": Find, Falsify and Forward-Test a Real Allocatable Edge
**Author:** githubcopilot-mercury3AI · **Date:** 2026-11-22 · **Status:** EXECUTING
**Supersedes nothing.** Inherits the 8-gate desk standard from `PART5_EDGE_PROOF_PROJECT_PLAN.md`.

---

## 0. The mandate, stated honestly

The user's instruction: *"find us something extremely promising in terms of worthy of putting money in — e.g. mutual funds? ETFs."*

That is not a research question. It is a **fiduciary question**. The only honest answer format is:

> "Here is a specific, rules-based, allocatable sleeve. Here are its measured CAGR / vol / Sharpe / max-drawdown / turnover / cost drag over N years. Here is what it looks like against the alternatives a normal person could actually buy (SPY, 60/40, an aggressive-allocation mutual fund). Here is the exact set of gates it passes and fails. Here is the failure mode that would cost you money and how we would detect it within days. Here is the position size we would sanction today, and the evidence required to increase it."

Anything less — a PF number, a win rate, a dashboard cell — is theatre. Parts 1–5 produced 3 retractions of our own claims. Part 6 must not add a fourth.

### Why the pivot to ETFs/mutual-funds is the right call (evidence, not preference)

| Evidence | Finding | Source |
|---|---|---|
| The audit3 pick ledger | **0 / 67 tested cells survive every gate**; 295 of 362 cells are `INSUFFICIENT_N` | `PART2_RECONCILIATION.md`, `PART5_P0_P3_FINDINGS.md` |
| CRYPTO full population | n=6,874, WR 40.2%, net −0.3159%, **PF 0.8339** → KILL | `PART5_P0_P3_FINDINGS.md` |
| ETF class in the ledger | n=590, **+0.1577%–(per-trade)**, only class that did not blow up | Part 1 `ETF.md` |
| Peer retraction (freebuff) | CRYPTO "PROVEN" PF 1.313 → **0.2656** over 22,864 picks, −0.046%/trade gross | COMS `notes/freebuff-session-summary-crosscheck-20261122` |
| Peer review (zoo-savant) | PROMOTED shown at **n=0**; only CANDIDATE cell was **82% single-source** | COMS `notes/reply-freebuff-methodology-xcross-20261122` |
| Prior program verdict (July-edition skill) | "The one structural change: **reorient from crypto-ledger mining to ETF tactical asset allocation** (the one validated find)" | `.claude/skills/money-maker-ready-July112026edition/SKILL.md` |

**Conclusion:** directional crypto picking on our own ledger is measurement-broken and net-negative. The only asset class where a *retail-accessible, rules-based, capital-scalable* edge has repeatedly shown up in this repo's own history is **ETF tactical allocation**. So that is Track A. Everything else is Track B (repair) or Track C (opportunistic).

---

## 1. Non-negotiables (unchanged from Part 5, restated because they were violated 3×)

1. **No claim without a frozen population.** Every backtest writes a manifest with `sha256`, date range, universe hash, cost model, and code commit. If a number cannot be reproduced from the manifest, it does not exist.
2. **No "proven" off a backtest.** `PROVEN_T2` requires, at minimum, 100+ **forward** observations. Backtests can only reach `CANDIDATE`.
3. **2× cost stress is mandatory**, not optional. A sleeve that dies at 2× cost has no edge, only a fee-sensitivity.
4. **Window selection is the default killer.** Every result is computed on full history *and* the last 24 months *and* the last 12 months. A sign flip = not an edge, a regime fit.
5. **Multiplicity must be paid for.** Testing 27 variants means the best of 27 is not the best; DSR/BH must be applied and the *count of variants tested* must be disclosed.
6. **A delegated AI's opinion is not evidence.** It is a hypothesis generator. It enters the record only after I attach a file:line or a reproducible command. Unverified suggestions are logged as `UNVERIFIED` and quarantined in `DELEGATED_REVIEW.md`.
7. **Worth-the-risk means the boring comparison also wins.** Beating SPY on Sharpe is not enough; the sleeve must beat **what a human would actually buy instead** (60/40, target-date fund, or the static 80/20 they already own) *after* costs, on drawdown, and on the worst 12-month window.

---

## 2. What "extremely promising, worthy of money" must mean numerically

A sleeve is **ALLOCATABLE** only if it clears all six of these. These thresholds are set *before* running anything, so I cannot move them afterwards.

| # | Criterion | Threshold | Why this threshold |
|---|---|---|---|
| A1 | Net Sharpe (after 2× cost) ≥ SPY Sharpe + 0.20 | and ≥ 0.70 absolute | Sharpe is the unit of risk-adjusted return a fund-of-funds would actually trade on |
| A2 | Max drawdown ≤ 0.6 × SPY MDD | — | The single reason retail investors capitulate; if MDD is not materially smaller, they will not hold it |
| A3 | Survives chronological split-half | both halves net-Sharpe > 0 | Kills parameter fits and one-bull-run artifacts |
| A4 | Bootstrap CI on net Sharpe excludes 0 | 2,000 seeded resamples, 5th pct > 0 | Kills "it worked in this one ordering" |
| A5 | Parameter-robust | ≥80% of a declared variant grid within 25% of best | Kills single-cell luck (this is the one thing equity-momentum did pass: 27/27 PF>2.2) |
| A6 | Beats the "boring alternative" on ≥2 of 3 axes (net Sharpe, MDD, worst-12m) | 60/40 + target-date proxy | The honest counterfactual |

Tier labels used below: `INSUFFICIENT_N` / `WEAK` / `CANDIDATE` / `PROVEN_T2` (n_forward ≥ 100).

---

## 3. Tracks

### Track A — ETF tactical allocation (PRIMARY: this is the money answer)
Goal: produce **one** allocatable sleeve, or a defensible "none in this market" verdict.

Candidate sleeves, all rules-based, monthly rebalance, ETF-only, no forecasting:

| ID | Sleeve | Rule | Members |
|---|---|---|---|
| **A-1** | Dual momentum (GTAA-lite) | rank 12-1m total momentum; hold top-3 if positive else cash | SPY QQQ IWM EFA EEM TLT LQD HYG GLD DBC VNQ + BIL |
| **A-2** | Defensive asset allocation (DAA) | canary (VWO+BND) risk-on/off gate → momentum top-3 | broad set |
| **A-3** | Static 60/40 | SPY 60 / IEF 40 | benchmark, not a candidate |
| **A-4** | Vol-targeted risk parity | inverse-vol SPY/IEF/GLD + 10% vol target | — |
| **A-5** | Trend-following SPY | 200-day SMA filter, else BIL | — |
| **A-6** | Sector rotation | top-3 of 9 SPDR sectors by 6m momentum | XLK XLF XLE XLV XLI XLP XLY XLU XLB |
| **A-7** | Core-satellite | 80% A-1 + 20% A-6 | — |
| **B-1** | Aggressive-allocation mutual-fund proxy | AOA-like static basket | the counterfactual a retail investor buys |

Data: `yfinance` adjusted close (dividend-adjusted → total-return proxy), max history, daily → month-end resample. Costs: 5bp/side base, **10bp/side stress (2×)**, 20bp pessimistic. No leverage, no shorting, no options.

### Track B — Repair the measurement (SECONDARY, required for credibility)
`P1` honest re-resolution: re-resolve the audit ledger's closes against real bars with intrabar first-touch, emit `resolved_canonical_<date>.jsonl` with `resolver_version` + `first_touch_source`. Rationale: freebuff measured 54% of exits differ under honest resolution, and our own 430 forward rows claim 100% intrabar-first-touch — that claim is unverified against an independent source.

### Track C — Opportunistic cross-asset (TERTIARY)
Nothing enters Track C until Track A returns a verdict. If A yields nothing allocatable, "wait in cash/T-bills" is a legitimate, publishable answer.

---

## 4. Delegation architecture — bringing in outside AI judgement

The purpose is **not** to ask "what should we buy". It is to attack specific, falsifiable sub-problems where a different model's training distribution is a genuine diversification benefit: (a) what breaks this sleeve, (b) what did we fail to measure, (c) what is standard practice at a real desk.

### 4.1 Channels available (verified this session)

| Chan | Mechanism | Verified capability | Best for |
|---|---|---|---|
| **D1** | `python3 tools/consult_multi.py --fanout all --prompt-file <q>` | **14 providers have keys**: nvidia, groq, cerebras, together, fireworks, github_models, huggingface, gemini_api, cloudflare, deepinfra, nous, mistral, aimlapi, hypereal | Breadth — "what breaks this" |
| **D2** | `/consult-PROXY` → `tools/freellm.py DebateTeam` (LiteLLM :4000, 15 groups) | multi-round structured debate | Depth — "rank these two sleeves" |
| **D3** | Kilo global config (`~/.config/kilo/kilo.jsonc`) — headless `kilo` | 30 provider groups incl. openrouter (15 models), aihubmix (22), topnotch (16), litellm-local (20), deepseek, kimi, xai, inception, cohere | Strong-model bias check |
| **D4** | `/consult-nvidia-models`, `/consult-cloudflare-models`, `/consult-ring`, `/consult-minimax` | per-vendor fan-out incl. reasoning models | Deep single-shot critique |
| **D5** | COMS bus `192.168.2.52:1883` → peer agents (freebuff, zoo-savant) | already exchanging methodology with us | Adversarial peer review |

Rate-limit discipline: the user explicitly flagged rate limits. **Sequential, not parallel.** One fan-out at a time, sanity-probe one completion before enrolling a provider group, and never re-run a channel that already answered.

### 4.2 The four delegation briefs (fixed, written to disk *before* sending)

| Brief | Question (falsifiable, no advice-seeking) | Channel | Expected artifact |
|---|---|---|---|
| **B1** | "Here is a fully specified ETF dual-momentum rule with measured stats. List the specific ways this backtest is lying to us. Prioritise: survivorship, look-ahead, rebalance-timing, dividend/total-return error, cost understatement, universe selection." | D1 (14-provider fan-out) | `DELEGATED/B1_brittleness_<provider>.md` |
| **B2** | "Rank A-1 vs A-6 vs A-7 for a retail allocator who must hold through a 30% drawdown. State which measured statistic would change your ranking." | D2 (DebateTeam, 2 rounds) | `DELEGATED/B2_debate.md` |
| **B3** | "Here are our 8 gates and our results table. Which gate is mis-specified, and what is the standard desk test we are missing?" | D3 (Kilo/OpenRouter strong models) | `DELEGATED/B3_gate_critique.md` |
| **B4** | "Peer review request: our ETF sleeve claims X. What measurement error would you look for first?" | D5 (COMS peers) | `DELEGATED/B4_peer_<agent>.md` |

**Every brief carries the mandatory `LEAKAGE-CONTEXT` block** (per `.claude/skills/consult-nvidia-models/SKILL.md`), listing H-101 COT look-ahead, M-095 CT=F re-emission, M-069 slippage re-judgment, QUALITY_BUCKETS circularity, plus our own retractions (EQUITY sign-flip, PF-2.94 downgrade). Multi-model consensus on corrupted inputs is worthless — that is how 5/5 NIM models once converged on "COMMODITY is your #1 alpha" off pre-dedup numbers.

### 4.3 Review / adoption protocol (the part that actually matters)

For each returned `.md`:

1. **Extract claims** into a table: `claim | model | falsifiable? | evidence offered | our file:line or command`.
2. **Adopt** only if it satisfies one of: (a) names a concrete defect in *our* code/output that I can reproduce, (b) proposes a computation with a citation-standard formula I can run, (c) contradicts another model on a fact that is checkable — the disagreement itself is the finding.
3. **Quarantine** as `UNVERIFIED` if it asserts a market fact with no source and no re-runnable test.
4. **Flag model failure modes** explicitly, per the standing rule: any model that endorses a known-contaminated signal without addressing the leakage block gets named in the review.
5. Publish `DELEGATED_REVIEW.md`: adopt / reject / quarantine, with the count of models that agreed vs disagreed. **Distribution, not average.** (3-engine unanimous `DATA_QUALITY_LEAKAGE` is the gold-standard pattern.)

**Hard rule:** no delegation output changes a number in Track A. It can only (i) add a new test, (ii) void a test we ran, (iii) change a tier. Numbers come from code I ran.

---

## 5. Execution phases

| Phase | Deliverable | Gate to exit |
|---|---|---|
| **P6.0** | `PART6_WORTH_THE_MONEY_PLAN.md` (this doc) deployed + COMS broadcast | in review repo `main` |
| **P6.1** | Real-bar ETF data pull + manifest (`sha256` per series, vendor, as-of) | manifest reproducible |
| **P6.2** | Sleeve engine + full-history results for A-1..A-7, B-1, incl. costs base/2×/4× | results table + manifest `sha256` |
| **P6.3** | Falsification battery: split-half (A3), bootstrap CI 2,000 (A4), variant grid (A5), window sensitivity (24m/12m), "boring alternative" (A6) | gate scorecard, no exceptions |
| **P6.4** | Delegation round: B1 (D1) → review; B3 (D3) → review; B2 (D2) → review; B4 (D5 COMS) | `DELEGATED_REVIEW.md` published |
| **P6.5** | Verdict: `CANDIDATE` or `WEAK` or `REJECTED`, with sanction sizing | explicit tier + size + kill-criteria |
| **P6.6** | Forward-test harness live: daily ledger, 2× cost shadow, gate dashboard, promotion rule = 100 forward obs | first rows written to `reports/forward_observations.jsonl` |

**Sizing rule (pre-committed):** `WEAK` → $0. `CANDIDATE` → at most **10%** of risk capital, and only as a paper/live-shadow sleeve for 90 days. `PROVEN_T2` → up to 40% with a documented kill-switch (drawdown > 1.5× backtest MDD, or 6 consecutive losing months). No exemptions.

---

## 6. Deliverables (all in `28_MERCURY3_PER_CLASS_REVIEW_2026-11-22/`)

1. `PART6_WORTH_THE_MONEY_PLAN.md` — this plan
2. `PART6_ETF_MANIFEST.md` — universe, data provenance, sha256, cost model, code commit
3. `PART6_ETF_RESULTS.md` — full results table + gate scorecard per sleeve
4. `PART6_FALSIFICATION.md` — split-half, bootstrap, variant grid, window sensitivity
5. `DELEGATED/*.md` — raw outside-AI suggestions (unmodified, quarantined by default)
6. `DELEGATED_REVIEW.md` — adopt / reject / quarantine + model failure-mode flags
7. `PART6_VERDICT.md` — the allocatable answer: sleeve, size, kill-criteria, what to watch weekly
8. `PART6_FORWARD_HARNESS.md` — the forward-test rig + promotion gate

## 7. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| yfinance dividend adjustment ≠ true total return | Sharpe biased either way | cross-check 3 tickers against FMP total-return; disclose delta |
| Ex-post ETF universe (only survivors tested) | overstates returns | restrict to broad-index core for the headline number; quantify sector-ETF-inclusive delta |
| Monthly-close rebalance look-ahead | overstates | signal computed on month-end close, executed at **next** month-end close (T+1 bar) |
| Overfitting via variant grid | false CANDIDATE | 27-variant disclosure + DSR with trials count |
| Rate-limit / cost on 14-provider fan-out | wasted effort | sequential, probe-first, cached outputs |
| Delegated model hallucinating a statistic | contamination | hard rule §4.3: delegation cannot change a number |
| Success looks "too good" | it's probably wrong | any Sharpe > 1.5 triggers a mandatory re-audit before it is reported as such |

## 8. Definition of done

- A named sleeve (or an explicit "nothing qualifies"), with a **reproducible** manifest.
- A gate scorecard where **every** gate is PASS/FAIL/NOT-RUN — no blanks, no "n/a".
- A published delegation review where outside opinions were actually adopted or rejected with reasons, not merely collected.
- A running forward harness that will, on its own, promote or kill the sleeve without further human judgement.
- Zero new claims that a future session will have to retract.

---
*Not personalized investment advice. Any allocation figure is a research sanction subject to the gates above, not a recommendation to trade.*
