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
