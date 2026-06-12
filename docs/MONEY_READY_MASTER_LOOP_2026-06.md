# MONEY-READY MASTER LOOP — June 2026 Edition
**The self-correcting plan that converges even while per-class performance is poor.**
Status: ACTIVE · Edition: 2026-06-11 · Review cadence: MONTHLY (next review due 2026-07-11)
Slash command: `/money-maker-ready-June112026edition` · Companion skills: `/money-maker-ready`, `/money-maker-readyv2`, `/db-schema`

---

## 0. For a brand-new AI agent: orientation in 90 seconds

- **The goal:** hedge-fund-grade picks per asset class on `findtorontoevents.ca/audit` (Tier-2 floor: PF≥1.5, WR≥50%, n≥100 honest; Tier-1 target PF≥2/WR≥55/MDD≤10).
- **The honest state (2026-06-11): 0/9 classes pass.** That number is TRUSTWORTHY — the measurement layer was rebuilt in June 2026 (entry-anchored intrabar resolution is the production default; the tournament was re-resolved; corrupt rows are quarantined with guards at ingest, resolver, and backfill layers).
- **Databases:** MySQL `mysql.50webs.com:3306` — `ejaguiar1_stocks` (live picks/outcomes: `trading_picks`, `at_signal_outcomes`, `tournament_picks`, `INCIDENT_*`/`ENHANCEMENT_*`/`FINDING_*`), `ejaguiar1_backtests` (backtest history), `ejaguiar1_backups` (MANDATORY backup target before ANY mutation). Connect ONLY via `tools/db_env.py` (`get_stocks_creds()` etc.). **Local agents: passwords resolve from env or `/home/eaguiar2015/dbpasses.txt` (gitignored — never commit/echo/print).** Remote agents: ask the operator for credentials.
- **Canonical truth surfaces:** `audit_dashboard/data/money_ready_verdict.json → classes.<CLASS>.intrabar_truth` (per-class honest n/WR/PF); `pf_registry.json::*policy_clean_net`; `entry_conditions_forward.json` (the live forward lane). NEVER cite raw `at_pick_outcomes`/dashboard tiles without the mandatory data-integrity filters in `/money-maker-readyv2`.
- **Key tools you will reuse:** `tools/build_intrabar_truth_by_class.py` (per-class honest ledger), `tools/stamp_entry_conditions.py` (forward lane), `tools/reresolve_intrabar_signal_outcomes.py` (honest re-resolution), the **replay harness pattern** in `reports/strategy_bt_crypto_2026-06-11.json` (entry-anchored, SL-wins-ties, strictly-pre-entry features, per-symbol-day dedup, net of costs: 16bp RT crypto / 4bp equity / 2bp FX), `tools/audit_pick_funnel/cli_track.py` (incidents), `tools/db_backup_to_backups.py` (backups; table names ≤64 chars; FK tables need CREATE-AS-SELECT).
- **Hard rules:** every performance claim labeled `(asset_class | n | timeframe)`; backup before mutate; pre-register before backtest (M-107); py_compile/yaml-check everything; never run dashboard generators locally; never trust subagent/peer statistics without direct-SQL re-verification.

## 1. Why months of effort produced no proven results (the diagnosis, settled)

Three independent investigations triangulated the same conclusion in June 2026:
1. **The scoreboard lied** (now fixed): close-walk/stale-window resolution inflated WR 23-24%; backfill contamination; wrong-symbol exit prices (a +93,965% "win"); duplicate emissions (79% dup rate in raw terminal rows); EXPIRED→WON mislabels. *Every* pre-June headline number is suspect.
2. **The losses are ENTRY-SELECTION losses, not exit-geometry losses**: σ-scaled TP/SL experiments returned NULL (WR falls exactly as TIME_EXIT is cured); the only conditions that beat baseline are entry-time conditions.
3. **There is no large, easily-harvestable edge in our universe at our costs**: 1,278 historical slices (Bonferroni), an 81-cell exit-geometry grid, and 80 fresh strategy designs with real net-of-cost replays all converge on the null. Wins that exist are SMALL (PF 1.3-1.5 class) and need disciplined accumulation, not discovery heroics.

**Corollary:** the answers to the five classic failure hypotheses are now *measurable* (Section 3). The system's true historical failure was running H1 (broken measurement) for months while believing it was running H2-H4.

## 2. THE VELOCITY PRINCIPLE (the structural correction — from a 7-engine adversarial review)

The naive loop ("one lever per class per week, wait for live n≥100") **circles instead of converging**: at 10-20 clean live resolutions/month/class, every decision takes 6-18 months (grok + groq + gpt-4o-mini consensus critique, 2026-06-11).

**The correction: sample velocity comes from deep-history replay, not calendar time.**
- We hold 180d × 1h bars for ~315 crypto symbols and growing equity/ETF history; the replay harness produces honest, cost-aware, time-split-tested results at n=500-2,500 **in minutes** (proven: the 80-design sweep).
- Therefore: **discovery and iteration happen in PARALLEL REPLAY** (dozens of variants at once, FDR-controlled as a family), and **live forward lanes only CONFIRM finalists** (which needs only n≈80-150, i.e. weeks not quarters).
- **Focus beats breadth:** at most 2-3 focus classes at a time (currently CRYPTO + COMMODITY — the only class with honest PF>1 — with EQUITY data-building in background). The other classes stay in measurement-only mode until a focus slot opens.
- **Gates use CI lower bounds, not point estimates:** promote when the 95% CI lower bound of PF > 1.15 net-of-costs at n≥80 forward (grok's bar), plus time-split stability and concentration <35% (<25% for sizing).

## 3. The five-hypothesis diagnostic (run WEEKLY; each has a measurable test + a remedy)

| # | Hypothesis | Test (cheap, automated) | Remedy when it scores highest |
|---|---|---|---|
| H1 | Resolver/measurement error | **Structural** audit, not just random: (a) stratified spot-replay (10 per class × recent week) vs independent bars; (b) the standing guards' counters (sign-coherence gate, exit-ratio rejections, one-sided-resolution checker, dup-rate). Any structural artifact = HALT everything else | Fix resolver first. Nothing else matters while H1 is red. |
| H2 | Strategies only win in backtests | Walk-forward-vs-forward divergence per sleeve (needs #132 WF refresh); replay-vs-live PF gap on the same rule | Demote to shadow (mutate-before-kill); tuning family CLOSED after 2 comparisons |
| H3 | Not enough data / signal supply | signals-per-month per class vs n-needed; bar-coverage (no_data share); universe breadth | Free APIs (Section 6) + widen universe + raise emission frequency **in the shadow lane only** |
| H4 | External signals are mispriced trust (Polymarket/Kalshi/copytrader/analyst) | Per-source honest scorecard: WR/PF vs the class baseline at n≥30, EXPIRED-inclusive, deduped | Keep/kill per source by evidence. (History: myfxbook + ig_contrarian + multi_asset_copytrader already killed this way; `prediction_market_consensus` needs a clean-cohort verdict — open item) |
| H5 | Measurement coverage gaps | resolved/emitted ratio per class; NULL-pnl count (watch: was regrowing via 3 writer paths, fixed 2026-06-11); classes with 100% one-sided outcomes | Extend resolution coverage (bars, keyspace joins) before judging the class |

## 4. The operating loop (weekly cadence, parallel execution)

```
MEASURE (Mon)    -> refresh honest ledger + coverage metrics + H1 structural audit
DIAGNOSE (Mon)   -> score H1-H5 per focus class; pick the top hypothesis PER CLASS
ACT (Tue-Thu)    -> PARALLEL: replay-variant batches on focus classes (FDR-controlled family,
                    pre-registered before running); plumbing fixes; data additions (shadow lane)
FORWARD (always) -> the lanes accrue automatically; promote/kill ONLY at pre-registered bars
RATCHET (Fri)    -> weekly scorecard .MD committed; CI guards updated WITH any behavior change
                    (tests ship in the same commit — the #129 discipline); incidents filed/resolved
```

**Anti-circling rules:** (a) every replay batch is pre-registered (hypothesis + falsification) BEFORE running; (b) a class with 3 consecutive null weekly cycles rotates OUT of focus (its slot goes to the next class); (c) anything promoted must survive an independent re-derivation (different agent, direct SQL) — the anti-fabrication layer; (d) refuted items go on the do-not-relitigate list and STAY there.

## 5. Portfolio mathematics (the validation mandate)

The Model Portfolios / Risk-Managed Books must compute **defensible** performance before anyone trusts a book:
- **TWR** (time-weighted): geometric linking of daily equity-curve returns — never sum per-trade pnl_pct (the historical sum-of-percentages bug class; `tests/test_card_metrics.js` locks one instance).
- **MWR** (money-weighted/XIRR) where flows exist (books with additions/withdrawals).
- **Attribution** (Brinson-lite): per class × strategy contribution to book PnL, so "which sleeve made/lost the money" is a query, not a guess.
- **Risk-adjusted:** Sharpe/Sortino from the daily curve (not per-trade), Calmar, MDD peak-to-trough, plus the factor-exposure overlay (ENH#161: BTC/SPY/VIX beta + de-gross kill-switch — designed, unbuilt).
- **Daily independent P&L reconciliation** (grok's fund-grade demand): book equity recomputed from fills must match the displayed curve within tolerance; divergence = incident.
- *Implementation status:* an engine audit ran 2026-06-11 (workflow wf_c35c2f25); its findings + the minimal honest portfolio-math module spec are appended as ADDENDUM A when complete. Until then, treat all portfolio return figures as UNVALIDATED.

## 6. Free data additions (the H3 remedy menu, per class)

| Class | Free source | What it unlocks |
|---|---|---|
| EQUITY | SEC EDGAR (earnings, filings), FRED, yfinance | PEAD-class event anchors; macro gates |
| FOREX | FRED policy rates (needs `FRED_API_KEY` in CI — operator), ECB/BOE feeds | LIVE carry differentials (incident #18: current carry is a hardcoded snapshot) |
| COMMODITY | CFTC COT real API (needs key — operator), EIA, yfinance =F | Real positioning data (current COT is a proxy) |
| CRYPTO | Binance/KuCoin/CoinGecko klines (have), funding-rate snapshots | Wider universe + funding conditioning |
| BOND/ETF | FRED yields (have locally), yfinance | Supply for the thinnest classes |
| Cross | Polymarket/Kalshi public APIs (have) | Only with per-source scorecards (H4) |

## 7. Pre-registered checkpoint calendar (already running — do not re-tune, just judge)

| Date | Checkpoint | Bar |
|---|---|---|
| 2026-06-14 | `pead_equity` review gate | ≥100 shadow picks AND PF≥1.5 AND WR≥50 → probation; else continue shadow or kill |
| ~2026-06-13-16 | COMMODITY crosses n=100 honest | First honest class verdict: dedup + time-split + concentration analysis, published |
| ~2026-06-16-20 | FOREX crosses n=100 honest | Same |
| ~2026-06-25 | `crypto_rsi5070_us` at n≥150 | WR≥50 AND PF≥1.5 AND R1/R2/R3 re-pass → probation; else drop |
| 2026-07-09 | `crypto_eu_us_handoff` LONG out-of-sample | Identical replay on post-06-10 entries: net PF≥1.3 at n≥80 → shadow-emission; else archive (family CLOSED) |
| Monthly (11th) | THIS DOCUMENT + the skill | Edition review: what converged, what circled, what the next edition changes |

## 8. Inherited wisdom (hybridized from FOOLPROOF_ACTION_PLAN + the 2026-06 sweeps)

Kept from the Kimi-era FOOLPROOF plan: per-class playbooks, explicit kill criteria, layered verification, the principle that plans carry INTENT not numbers (its snapshot numbers self-contradicted within days — never quote a plan's PF/WR as current). Added beyond it (what it lacked, which is why it failed): an honest measurement layer to execute against, pre-registration discipline, replay velocity, CI ratchets, and the anti-fabrication verification layer. ADDENDUM B will carry the full concept-mapping when the review lands.

**Do-not-relitigate (refuted; re-deriving these wastes money):** stocks_rsi2_pullback promote · CRYPTO direction-flip at sync · futures_momentum (dedup artifact) · forex_rsi2 small-n · luxalgo "best-in-system" · MeanReversionBB (nominal fills) · trust=7 edge · alpha_engine×CRYPTO 80.6% (synthetic) · kimi_ultimate_proven_edge (self-admitted synthetic) · VRP pilot · myfxbook/ig_contrarian · tournament/leaderboard WR as sizing signals.

## 9. External heavyweight review (operator-deployed)

This plan itself should be attacked by an agent outside this lineage. **Ready-to-paste task for Cursor/opencode/kilocode:**

> Read `docs/MONEY_READY_MASTER_LOOP_2026-06.md` in repo findtorontoevents_antigravity.ca. You are a hostile quant reviewer. Independently verify 3 of its factual claims against the repo/DB (creds: `/home/eaguiar2015/dbpasses.txt` locally, or ask the operator). Then answer: (1) which loop step will fail first in practice and why; (2) what is the single highest-leverage missing piece; (3) does the velocity principle (replay-n over live-n) hold statistically for THIS data, or does the 6-week resolution era invalidate it; (4) propose one concrete experiment we have not run. Write your review to `reports/MASTER_LOOP_EXTERNAL_REVIEW.MD` with file:line evidence. Do not trust any number in the plan without re-deriving it.

## 10. Success definition (so we know if THIS plan is working)

By 2026-09-11 (3 editions out): ≥2 classes with honest n≥100 AND PF 95%-CI-lower-bound >1.15 net in the FORWARD lane (not replay), portfolio books with validated TWR/attribution, and zero P0 measurement incidents open >7 days. If after 2 editions no class has improved its CI lower bound, the loop itself goes under review — the meta-ratchet.

---
## ADDENDUM A — Portfolio-math audit results (2026-06-11, wf_c35c2f25; full detail: reports/master_loop_inputs_2026-06-11.json)
- The books are NAV-based (not sum-of-percentages) and flow-free, so TWR=MWR=total-return **by accident**; structurally honest headline.
- **P0 FIXED (53982150): direction-blind NAV marking** — open SHORTs (282 live) were sign-flipped (2× the move wrong), corrupting daily returns, drawdown, the breaker input, and sizing. Historical PF_NAV_SNAPSHOT rows since 2026-05-29 carry the distortion — flag, do not trust pre-fix book curves.
- STILL OPEN (filed): `sharpe_30d` is full-history mislabeled; Sharpe annualized over irregular snapshot gaps (weekday-only cron, 24/7 crypto books); CAGR uses snapshot-count not calendar days; "MTD" is inception-to-date. Remedy spec: daily equity curve → geometric-link TWR, calendar-aware annualization, true MTD anchor, Brinson-lite attribution per class×strategy, daily independent P&L reconciliation.

## ADDENDUM B — FOOLPROOF plan post-mortem + revived concepts (2026-06-11)
Why it failed: built on the corrupted measurement layer (every headline verdict later falsified); stats applied to contaminated pooled series (DSR=1.0 on CT=F-concentrated data); checkbox theater (completion = code merged, never outcome-conditioned); prose gates never compiled into code; amendment churn ignored as the meta-signal that measurement itself was broken; multi-AI convergence mistaken for verification; deadline-driven capital pressure.
**Revived into this loop** (worth building, never built): (1) the monkey-test null benchmark (beat the 95th pct of 1,000 random strategies — cheap overfit killer, complements DSR/PBO); (2) symmetric AUTO-DEMOTION (rolling 30d Sharpe<0.5 or PF<1.0@50 trades demotes from the allowlist — the ladder must go down, not just up); (3) the Level-5 breadth throttle (no 4th class until 3 are live-profitable) — encoded here as the 2-3 focus-class rule; (4) cross-strategy correlation gate (>0.7 pairwise cap) — stronger than HHI; (5) institutionalize the cross-AI stat-divergence audit (the one FOOLPROOF exercise that worked: adversarial subagents, file:line-cited, sha256-deterministic) as a RECURRING monthly claims audit; (6) the cotton-style evidence pack with the systematically-skipped item (d): live forward confirmation at projected PF before any tier claim.

## ADDENDUM C — Pages-calc audit (2026-06-11): P0s fixed same-day
esc() undefined killed pick_funnel's Strategy Funnel (FIXED 71f21326, deployed); template "Max Drawdown" was range-not-drawdown (FIXED a4c25166); Σ-PnL card relabeled non-compound. Filed for follow-up: headline-cards population mismatch (statsFiltered branch inversion: default = recent-2000-only vs full-book; trust-book mode shows full-book cards over a narrowed table); total_pnl_pct server-redefinition vs template label.

## ADDENDUM D — External hostile review triage (2026-06-12; review: reports/MASTER_LOOP_EXTERNAL_REVIEW.MD)
Overall grade B; every finding verified before adoption:
- **ADOPTED + FIXED (was grade F): forward-lane automation** — `stamp_entry_conditions.py` had no cron; the pre-registered checkpoints were not accruing data. Now runs in the hourly dashboard build + JSON committed (aba100e67f). (Reviewer's "output file does not exist" was a stale-checkout error — the file was on main — but the automation gap was real.)
- **ADOPTED (doc): intrabar_truth derivation transparency** — the filter chain producing n=1154 from raw n=1283: (1) `intrabar_resolved_at IS NOT NULL AND intrabar_status IN ('TP_HIT','SL_HIT')` (TIME_EXIT/ambiguous excluded from WR), (2) quarantined/sign-flip rows carry NULL pnl and drop out, (3) per the builder `tools/build_intrabar_truth_by_class.py` (read it — it IS the reproducible derivation). The raw-vs-filtered −2.4pp WR delta is conservative-direction (filters remove more apparent winners).
- **ADOPTED (doc): the "23-24% WR inflation" claim downgraded to its provable form** — the original magnitude came from pre-fix investigations (`reports/shadow_diff_entry_anchored_2026-06-10.json`: 29.4% tp/sl flip-rate on open picks; tournament paired re-resolution: −9.7pp WR; pre-June row-level misclassification still visible: 9.8%). The DB no longer holds the original labels (overwritten by honest re-resolution; backups exist in ejaguiar1_backups). Cite those three artifacts, not a bare "23-24%".
- **ADOPTED: PBO disambiguation** — 0.822 is the GLOBAL CPCV PBO (`tools/cpcv_pbo_results.json`); `classes.*.pbo` in the verdict JSON is a different per-class field. Plan text now says "global PBO".
- **ADOPTED (build item, elevated): monkey-test null benchmark** — `tools/monkey_test_benchmark.py` per the reviewer's spec (1,000 random strategies, same universe/costs; candidates must beat the 95th percentile) wired as a pre-filter before any replay batch. THE highest-leverage unbuilt defense.
- **ADOPTED (metric): the velocity principle gets its own falsification test** — when rsi5070 reaches n≥80 forward, compute forward-PF / replay-PF; ≥0.8 = principle holds; <0.5 = recalibrate the loop. Pre-registered here.
- **ALREADY-DONE (reviewer missed it): Q4's proposed experiment** (LONG-only handoff + RSI band) — that IS the v2 control run: LONG-only 1.0×ATR PF 1.3797 n=536 (`reports/strategy_bt_crypto_handoff_v2_2026-06-11.json`; the handoff entry rule already embeds RSI 50-70 for longs). Family CLOSED; the Jul-9 out-of-sample window is its next legitimate test. No new tuning.
- **PARTIAL: do-not-relitigate precision** — tournament-WR ban now states the reason (58.5% MISPRICED_ENTRY + single-snapshot resolution); futures_momentum stays refuted (dedup evidence stands) but may re-enter ONLY via a fresh pre-registered replay under the loop's own rules.

## ADDENDUM E — GROK4_3 deep review processed (2026-06-12; source: docs/GROK4_3_JUNE112026.MD, 348KB multi-pass)
Verdict received: "strongest, most honest, most executable plan the repo has produced... core weakness: the self-correcting properties live in prose and opt-in sidecars." Adopted:
- **P0 FIXED — the fail-closed admission gate exists now: `tools/loop_preflight.py` (d81256b6d4).** Run before ANY replay batch / promotion / scorecard publish: blocks on H1 red (sign-incoherence, NULL-pnl regrowth), missing M-107 pre-registration, closed families, and do-not-relitigate matches; fails CLOSED on check errors; skips require an explicit logged flag. First live run already warned: 7d emission dup-rate 69% (forward-lane n quality item).
- **UNIFIED LIFECYCLE STATES (replaces the fragmented gate numbers Grok flagged):**

| State | Entry bar | Where it lives |
|---|---|---|
| research-replay | pre-registered (M-107) + preflight GO | replay harness artifacts |
| shadow-forward | replay: net PF≥1.3, R1 time-split, conc<35%, family open | forward lanes (auto-accruing) |
| probation | forward: n≥80 AND 95% CI-LB(PF)>1.15 net AND R1/R2 re-pass | promotion_gate allowlist |
| money-ready | honest n≥100, PF≥1.5, WR≥50, ≥3 months, multi-source, intrabar-validated | money_ready_verdict MONEY_READY |
| sizing-eligible | money-ready + conc<25% + MDD≤20% + portfolio-math validated + operator sign-off | real capital (none today) |
Every other number in this doc defers to this table. AUTO-DEMOTION applies at every level (Addendum B #2).
- **Taxonomy pinned:** the verdict tracks 10 classes (incl. CHEAP_STOCKS/MEME/PENNY_STOCK); "0/9" = the 9 non-degenerate; future references use "0/10 tracked, 0/9 non-degenerate".
- **§4 cadence gains a PORTFOLIO lane:** RATCHET (Fri) now includes the portfolio-math checklist (incident #133 items) until Addendum A's module lands — it cannot be deprioritized silently.
- **Per-class replay-readiness metrics** added to MEASURE: max-achievable honest replay n this week, bar-coverage %, regime-spread note (COMMODITY currently thin: replay n=35 vs CRYPTO 970).
- **Registry seeding:** the hypothesis registry had 0 entries despite bt artifacts carrying voluntary pre-registration metadata — active families (handoff forward-obs, rsi5070, monkey-test baseline) get registry entries as part of the next weekly cycle so the preflight PREREG check has teeth.
- NOT adopted: Grok's verdict-surface numbers for FOREX/ETF (57.5%/1.79, 73.5%/2.05) as anything but Layer-A — the intrabar surface stays canonical (its own cross-check showed the same).

## ADDENDUM F — opencode GHA health monitor (2026-06-12; source: ___HELL_HEALTH_OPENCODE.MD)
Peer-operated 15-min monitor active (tools/gh_actions_monitor.py). Its open items are predominantly OPERATOR-level: verify MySQL secrets in GH (sync auth failures), 50webs IP-block check, GH token permissions, Pages deploy, and the medium-term 50webs-migration evaluation. The loop treats recurring MySQL-auth workflow failures as an H1-adjacent watch item (resolution coverage depends on DB reachability from runners).

## ADDENDUM G — nex-n2-pro review adopted (2026-06-12; reports/MASTER_LOOP_NEX_N2_REVIEW.md)
- **NEW GATE (no prior reviewer suggested it): the capacity/cost-regime stress matrix.** Before any candidate enters PROBATION, re-run its replay under adverse cases: cost multipliers ×0.5/×1/×2/×4, entry-latency slips of 1/5/15 minutes (enter at the bar price N minutes after signal), and volume caps (position ≤1%/5% of the entry bar's volume as a spread/liquidity proxy). Requirement: PF CI-lower-bound >1.15 survives in ≥3 adverse cases with no material rank collapse. The lifecycle table's shadow-forward→probation transition now includes this. Rationale: fixed 16/4/2bp costs are too clean for any "money-ready" claim.
- **Over-claim corrected:** the goal line now reads "institutional-DISCIPLINE picks" rather than implying deployable hedge-fund capital process today; "money-ready" remains the gate name, not a current-state description.
- **Confirmed strength (third independent confirmation):** the measurement/anti-fabrication architecture is the system's most defensible asset — quarantines, direct-SQL re-derivation, entry-anchored replay, fail-closed preflight, do-not-relitigate. It is an audit/control engine first.
- Flaw #1 (replay thinness vs stationarity/fills) overlaps Grok's velocity caveat — already covered by the pre-registered forward/replay falsification test + this new stress matrix.

## ADDENDUM H — Component-level consults synthesized (2026-06-12; artifacts: reports/component_consults_2026-06-12/)
7 reviewers (nex-n2-pro ×5 component deep-dives, grok repo-grounded, groq/qwen3-32b, kimi-k2.6, llama3) on five loop components. Unanimous items SHIPPED; specs recorded for the build queue:
- **SHIPPED — preflight v2 hardening** (unanimous): canonical NFKC+casefold family matching with explicit alias lists (substring matching was the most gameable rule), `--stage promotion|publish` now BLOCKS on the 69% emission dup-rate (replay still warns — it dedups internally), `--skip` requires `--skip-reason`.
- **EFFECTIVE-N (nex; adopt into all promotion bars):** raw n overstates evidence 5-10× when same-day picks share shocks. Cluster by trade-date, n_eff = n/(1+(m̄−1)ρ) with intraclass ρ on binary outcomes; PF CIs via cluster bootstrap. The n≥80/100 bars now mean **n_eff**, not raw n.
- **STRESS MATRIX v1 (nex+grok+kimi consensus on 1h-bar honesty):** minute-level latency slips are unvalidatable fiction on hourly bars — v1 = bar-level slips (signal at bar close → execute at next-bar open / +1 / +2 bars) × cost multipliers ×0.5/1/2/4. Volume-cap cases are LABELED "unfalsifiable bounds" until participation-rate modeling with bar-to-bar volume variance exists. Pre-specify which ≥3 adverse cells must pass (no post-hoc cell selection — kimi's p-hack warning).
- **WEEKLY DIAGNOSTIC RUBRIC (nex, mechanical 0-3 per hypothesis):** H1 by reconciliation-error rate (0: ≤0.5% bad rows; 3: >5%); H2 by live-vs-backtest decay (0: ≤20% + live t>2; 3: >70% or sign flip); H3 by n_eff (0: ≥500; 3: <100); H4 by independent-source agreement + IC; H5 by uncovered-exposure %. Hash-lock the rubric per week BEFORE scoring; ties break toward the hypothesis whose remedy is cheapest-reversible.
- **MONKEY-TEST FAIRNESS (nex):** randoms must match the candidate's trade count (or distribution); match hold-distribution ONLY when testing entry/direction skill; identical universe/costs/overlap rules; pre-specify the decision statistic — PF is fragile (ratio instability), prefer the t-stat or PF CI-LB vs the random distribution.
- **EMITTER BACK-PRESSURE (grok):** the gate sits after emission — analytics dedup cannot fix the 69% re-emission flow. The real remedy stays the emission-hygiene handoff (extend signal-week dedup to ungated writers) + a future rule: emitters whose lane conditions show sub-baseline forward performance get throttled.

## ADDENDUM I — nemotron + MiMo reviews VALIDATED with direct SQL (2026-06-12)
**nemotron-3-ultra** (docs/nemotron-3-ultra-free_JUNE112026.md): its Layer-A-vs-intrabar numbers match our verified figures exactly (credible data work). Verdict on its content: diagnosis = confirmation of the plan (good); mitigations = already in Addenda E/H (redundant); the "3 new alpha": **Earnings PEAD is ALREADY a running shadow sleeve (Jun-14 gate — not new)**; **COT Momentum is data-blocked** (COT is a proxy; needs the CFTC key — operator item) ; **Funding-Rate Mean-Reversion is the one genuine new candidate** → queued for M-107 pre-registration AFTER funding-rate history is wired (plan §6 unlock). "Vetted by the swarm" without replay evidence = brainstorm-grade; the lifecycle table governs.
**MiMo V2.5**: the strongest data verification of any reviewer — 182,809 outcomes / 32.3% WR / kimi_riseoftheclaw 77% share @ 28.4% WR ALL CONFIRMED to the decimal. BUT the triage matters:
- **"Kill kimi_riseoftheclaw" is MOOT**: it is dormant (zero 7-day emissions; 4 trading_picks rows ever, last 2026-03-09; 0 intrabar-resolved rows; toxic slices already blocked in quality_gates:2231). The REAL adoption: its 140k dormant rows dominate raw table aggregates — **any analytics on at_signal_outcomes MUST exclude or segment dormant research firehoses**, or aggregate WR/n claims (incl. MiMo's own "strategies are broken" framing) describe a dead source, not the live system. The honest intrabar surface is unaffected (it has 0 rows there).
- **"Replay harness doesn't exist in the codebase" — CONFIRMED and ADOPTED**: the methodology lives only in reports + /tmp scripts. Build item (with the monkey-test): commit `tools/replay_harness.py` as the reusable, pre-registration-aware implementation.
- "324 baby strategies" NOT confirmed (25 matching files; 55 strategy files). "FOREX BLOCKED/DISABLED" is STALE (re-enabled 2026-06-05 — that contradiction is open incident FOREX#19). "Tier chaos (5 overlapping systems)" — fair; the Addendum-E lifecycle table is the unifier and other tier vocabularies should be mapped onto it in the July edition.

## ADDENDUM J — 5-peer-doc triage + the lane stall (2026-06-12)
Subagent-verified review of KILO / CURSOR / FREEBUFF+BUFFY / MINIMAX (all persisted to main):
- **P0A IMPLEMENTED (20b3a58ef9)**: the intrabar lane had NO hourly driver — 0 new resolutions for 46h (max stamp Jun-10 06:49) starved every forward checkpoint. Hourly capped re-resolve (500/run, idempotent, backed-up) + truth rebuild now run in the dashboard build. CURSOR's P0 finding, independently verified live.
- **CURSOR = strongest doc** (claims reproduce under independent SQL). luxalgo SHORT independently re-derived: dedup n=42, 66.7%, PF 1.90 (vs 38/71.1/2.21) — clears the T2 floor under both dedup keys; remains the single probation-track sleeve, forward-only, n→100.
- **KILO = lowest-trust**: real numbers on the CONTAMINATED raw surface; 3 of 6 root causes refuted (make_pick_id has entry_price; kill_gate IS wired at quality_gates:7092; replay tools exist). Its 40-strategy doc enters only via M-107 + preflight.
- **BUFFY/FREEBUFF**: intrabar baselines verified EXACT; M-108/111 gates present (uncommitted working tree at review time); picks-now clustering UNDERSTATED — live 479 open / 37 unique symbols (AMZN×47). One-position-per-ticker rec endorsed (peer owns the file).
- **MINIMAX**: "0/7 PF>1" REFUTED as stated (3/7 have PF>1; 0 pass full T2 stands); missing-blockers list verified → adopted: `tools/pf_ci_lower.py` (the §10 referee — makes the imminent COMMODITY/FOREX n=100 verdicts mechanical) + M-107 registration for the 4 monitor strategies. Both queued next.
- Remaining from the TOP-5: P0B kill-list implementation (route via quality_gates, NOT production_scanner duplication — Buffy's coordination note + my P0C exemption note both apply).

## ADDENDUM K — ML audit + the kimi correction (2026-06-12; report: reports/ml_algorithms_usage_audit_2026-06-12.md)
- **CORRECTION to Addendum I:** kimi_riseoftheclaw was emission-dormant but **ingestion-ACTIVE** — its corpus re-inserted EVERY hourly run because timestamp-less rows bypass the UNIQUE dedup (MySQL NULLs). MiMo's instinct was righter than my "moot": the data-layer kill was needed. **FIXED at the writer (7dfc7ff0f6) + 141,344 pollution rows purged with backup (aso_kimi_nullts_bk_20260612T063922Z)** — at_signal_outcomes is now 43,083 real rows; raw-aggregate stats are meaningful again.
- ML estate verdicts (24 surfaces): reviver pair ACTIVE-HARMFUL (both directions lose — structural; incident filed + M-105 default-ON queued); ml_crypto_predictor ACTIVE-MARGINAL (PF 1.07 gross trimmed = net-negative; scale-outlier incident filed); gatekeeper A/B WIRED-NOT-ROUTING (last-mile file/field mismatch — incident filed; cheap + high-info); 5 zombie workflows ~40 runs/day (enhancement filed); ~12 orphaned ML modules listed for archive. Positives: the ML health gate is correctly HALTING ML sizing (health 0.06); genome_mutation_lab is the only positive honest slice (73.7%/4.43, n=57 — watch only).
