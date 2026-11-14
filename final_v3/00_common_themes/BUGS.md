# Common themes — bugs found across every review, including mine

Every item below is traceable to a file and a number. Where two sources disagree, the disagreement is
the finding. `PASS/FAIL` labels: **FAIL** = confirmed defect with measured impact; **OPEN** = confirmed
to exist but not yet explained; **PASS** = checked and clean.

Sources reviewed: my re-execution of the 3,500-row ledger; `final_v2/quant-audit-2026-11-14`;
`final_v2/finpredict-v2/*` (incl. `CORRECTIONS_v2.md`); `final_v2/hilarious-seer/*`;
`final_v2/fix-p0-safe-fixes-2026-11-14-main/*`; `final_v2/finpredict-v3` claims quoted by peers;
`research/profitability/` protocol v1–v4; the repo's own `benchmark_ledger_proof.json` and
`money_ready_verdict.json`.

---

## B1 — FAIL: a refuted strategy is still labelled "VALIDATED" in a live package

**Conflict, verbatim:**

| Source | Position on VWAP mean reversion |
|---|---|
| `final_v2/quant-audit-2026-11-14/05_final/VERDICT.md` | "Only approach passing all peer gates (Sharpe 3.76, PF 1.21, MDD 10%, PBO 0.489, DSR 1.0)" — deploy first |
| `final_v2/finpredict-v2/*`, `fix-p0-safe-fixes/01_peer_review/ADJUDICATION.md` | refuted; Sharpe/PBO certification does not survive re-examination |
| `fix-p0-safe-fixes` (same doc) | notes quant-audit's *other* package already refuted it, and that `FINAL_RECONCILIATION.md` accepts the correction |

Both files are on `main` today. An agent that reads only the quant-audit package will deploy a
refuted strategy. This is the highest-consequence bug in the repo because it actively misdirects.

**Also a red flag in the claim itself:** DSR = 1.0 and PBO = 0.489 are internally inconsistent
talking points — a deflated Sharpe of exactly 1.0 alongside a 49% probability of backtest overfitting
means at best half the apparent edge is selection.

**Root cause:** verdicts are prose. Nothing invalidates a conclusion when the evidence under it
changes, and nothing forces a reader to notice a newer refutation.

**Fix:** every verdict file carries `evidence_hash` + `generated_at`; a consumer refuses to act on a
verdict whose hash is stale; CI greps for `VALIDATED`/`PROVEN` and fails when the string appears
without a matching registry entry. (→ `../01_plan/GENERAL_FIXES.md` G3)

---

## B2 — FAIL: the same asset class reports incompatible counts and win rates

| Class | `money_ready_verdict` (20:58Z) | `pf_registry` (21:00Z) | `recent_closed` (this audit) |
|---|---|---|---|
| CRYPTO | n=3,705, WR 35.87%, PF 0.920 | n=22,055, WR 42.09%, PF 0.258 | n=1,966, WR 39.3%, PF 0.768 |
| EQUITY | n=250, WR 59.20%, PF 0.939 | n=469, WR 40.72%, PF 0.662 | n=738, WR 47.0%, PF 1.154 |
| ETF | n=45, WR 2.22%, PF 0.022 | n=19, WR 68.42%, PF 1.788 | n=567, WR 44.3%, PF 1.036 |

Three files, same hour, same repo. ETF spans **2.22% to 68.42% win rate** and PF 0.022 to 1.788 —
an 85× spread on the same asset class. CRYPTO sample sizes differ by 6×.

These cannot all be right, and they are not obviously all wrong either: different cohort filters
(policy-clean vs intrabar vs raw) legitimately produce different numbers. The defect is that **no
file states its filter chain**, so a reader cannot tell whether a difference is a bug or a different
question. That is how a losing class ends up looking like the best class.

**Fix:** one canonical cohort definition per class, published as a row-level query; every rate in every
artifact carries `{cohort_id, n, filter_hash}`; a reconciliation job diffs artifacts and fails CI when
two live files disagree on the same `cohort_id`. (→ G4)

---

## B3 — FAIL (fixed today): crypto stops filled late, and it was 98.8% of the class loss

Measured on 3,500 closed rows.

| | planned | realized | ratio |
|---|---:|---:|---:|
| CRYPTO stop loss | 1.919% | 2.956% | **1.54×** |
| EQUITY stop loss | 4.984% | 4.551% | 0.91× |
| ETF | 2.953% | 2.257% | 0.76× |
| FOREX | 1.096% | 0.751% | 0.69× |

Crypto overshoot totals **+832.4pp** against a class total of −837.8pp. By source system, the leak is
not spread out at all:

| source_system | n stopped | realized pp | at-stop pp | delta |
|---|---:|---:|---:|---:|
| **kimi_riseoftheclaw** | 174 | −988.3 | −261.0 | **+727.3** |
| luxalgo_filters | 371 | −668.6 | −585.8 | +82.8 |
| ml_bg_system_f | 69 | −403.8 | −373.0 | +30.8 |
| battleground | 36 | −31.4 | −54.0 | −22.6 (exits *inside* the stop) |

**One system accounts for 94% of the crypto fill leak.** That reframes the fix from "improve the
resolver" to "repair one tracker's exit writer".

`final_v2/finpredict-v2/01_audit/CORRECTIONS_v2.md` §C-C independently adopted this finding. My own
earlier error (calling `resolution_method` null the P0) is corrected in both places — see B5.

**Fixed today:** gap-aware fill (`audit_trail/stop_fill.py`, wired into
`universal_pick_resolver._check_tp_sl_intrabar`), plus a replay tool that measures it. Effect is
**breakeven, not profit** — see `../01_plan/BACKTEST_SIMULATIONS.md`.

---

## B4 — RESOLVED (new, deepest): every non-crypto "SL_HIT" mostly exited *before* the stop

This one is not in any peer package.

| Class | SL rows | exited **inside** the stop | share |
|---|---:|---:|---:|
| BOND | 21 | 18 | **86%** |
| ETF | 262 | 207 | **79%** |
| EQUITY | 304 | 201 | **66%** |
| FOREX | 104 | 61 | 59% |
| COMMODITY | 4 | 0 | 0% |

A row labelled `SL_HIT` whose exit price never reached the stop is not a stop-out. Two explanations,
and they imply opposite fixes:

1. **Trailing stop (benign labelling).** The trail ratcheted above the original stop; `stop_loss`
   records the *initial* level while the exit reflects the trailed one. Then the realized loss is
   correct and only the field semantics are wrong — the row should carry `stop_loss_initial` and
   `stop_loss_at_exit`.
2. **Mislabelled polled exit (real defect).** The writer closed at a polled price and stamped
   `SL_HIT` without checking the level. Then "SL_HIT" is not an exit reason at all and every
   exit-reason statistic in the dashboard is contaminated.

**Replay evidence (this session, 1h candles, 5-day window, deterministic samples):**

| Class | sampled | stop actually touched | **never touched** | recorded PnL on the touched subset |
|---|---:|---:|---:|---:|
| EQUITY | 25 | 11 | **14 (56%)** | −63.41pp total (mean −5.76%) |
| ETF | 25 | 15 | **10 (40%)** | −35.61pp total (mean −2.37%) |

So more than half were never stop-outs in the window — they are real losses, closed by something else
and stamped `SL_HIT`. That makes explanation (2) the leading one, with (1) still possible for the
touched subset (the replay does not truncate at the actual exit time, so some "touches" may post-date
the close). n=25 per class is enough to justify an investigation; it is not enough to rewrite the ledger.

**What would settle it:** resolver logs or the writers' own trail history for ~20 rows per class. Until
then, do not rank strategies by exit reason in these classes.

### B4 — RESOLVED 2026-11-14: it is the label, not the price

Settled with `tools/stop_fill_replay.py --truncate-at-exit`, which drops candles printed after the
pick's recorded exit (the earlier replay's own stated weakness — "some touches may post-date the
close"). On the never-touched rows it then asks a second question: did price ever reach the
**recorded exit price**?

| Class | sampled | stop touched | never touched | of the never-touched: reached a **different** level | never reached their own exit price |
|---|---:|---:|---:|---:|---:|
| EQUITY | 25 | 11 | 14 | **11** | 3 |
| ETF | 25 | 12 | 13 | **12** | 1 |

So explanation (2) is confirmed and (1) is the mechanism: these rows **did** hit a level — a trailed
stop, a target, or a max-hold exit — and were stamped `SL_HIT`. The residual 3 + 1 never traded at
their recorded exit price at all, which is data corruption rather than mislabelling.

**The consequence that matters, and it is the opposite of what the fill work assumed:** on the touched
subset, gap-aware filling makes EQUITY **worse** than the recorded number.

| Class | recorded | at_stop | gap_aware |
|---|---:|---:|---:|
| EQUITY | −63.41 | −50.07 | **−83.62** |
| ETF | −30.45 | −31.55 | −32.11 |

With 45.5% of EQUITY touches gapping through, a stop-fill model is being fitted to trades that mostly
did not stop out. **Do not extend the stop-fill fix to non-crypto exits.** For EQUITY/ETF the work
item is reclassifying `exit_reason`, not improving the fill — until the label is right, every
R-multiple, breakeven-WR and PF figure for these classes divides by the wrong denominator.

n=25 per class: 11/14 and 12/13 is not a coin flip, but it is not a census either.

---

## B5 — FAIL: the exit taxonomy lives under a field name nobody was reading

`resolution_method` (used by the SQL upsert in `universal_pick_resolver`) is **NULL on all 3,500
dashboard rows**. The actually-populated field is `exit_reason`:

`SL_HIT 1,468 · TP_HIT 873 · FORCE_CLOSED 615 · TIME_EXIT 517 · UNKNOWN 22 · EXPIRED 5`

I got this wrong first and so did finpredict-v2; both packages now carry the correction
(`final_v2/.../CORRECTIONS_v2.md` §C-A). Two independent readers made the same mistake from the same
field — that is a naming defect, not two careless agents.

**Fix:** a field contract (`docs/DATA_CONTRACT.md` exists in finpredict-v2 — adopt it as canonical) plus
a CI assertion that `at_pick_outcomes.resolution_method` and the payload's `exit_reason` are populated
for ≥95% of closed rows, or the build fails. (→ G5)

---

## B6 — FAIL: a real 100× unit bug — in a *different* store than people think

- Dashboard `recent_closed`: **clean.** Recomputing `pnl_pct` from entry/exit prices reproduces
  **3,500/3,500** rows within 0.05pp, median error 0.000pp.
- MySQL `trading_picks` / sidefiles: **affected.** 17,632 percent-style rows vs 6,306 fraction-style
  rows (per `finpredict-v2` C-B).

This matters because reasoning from "the dashboard PnL is 100× off" to any conclusion about class
performance produces a wrong answer. The bug is real; it is just in the store that feeds *other* claims.

**Fix:** canonicalize at every write path (store percent only), with a migration assertion and a
read-side guard that rejects `|pnl| > 100` unless `unit` is declared. (→ G6)

---

## B7 — FAIL: FOREX is not 100% forex, and its allowlist was never enforced

- **49 of 277 rows (17.7%) are not spot FX**: 44 currency ETFs + 5 `EURUSDT` (a crypto pair).
- **105/277** carry date-only `entry_time`; a separate **44** are EST-stamped and unparseable.
- The currency allowlist appears **exactly once** in the repo — its own definition. Enforcement count: 0.

So the class that reads `PF 0.634 / −29.0pp` is a mixture, and its timestamps cannot support any
intraday claim.

**Fix:** enforce the allowlist at emit; split ETF-proxies into the ETF class; reject unparseable
timestamps at ingest rather than silently coercing. (→ G7)

---

## B8 — FAIL: nothing in this repo counts trials, and the count we can measure is damning

`audit_dashboard/data/benchmark_ledger_proof.json` evaluates **170 ledgers**:

- **4** pass paired bootstrap at 95%, against **8.5 expected by chance**.
- Fewer pass than chance predicts. That is the cleanest available statement that the search space
  contains no demonstrated edge.

Peer framing elsewhere states 658 trials → 32.9 expected false positives. Both are lower bounds; the
true trial count is unknown and uncounted.

**Fix:** every forward test is pre-registered with a trial ID; the registry increments on every run;
the pass threshold is |t| ≥ 3.5 (or BH-FDR q=0.10 across the *actual* count), never 1.96. (→ G8)

---

## B9 — FAIL: three independent freshness failures at once

| Component | Failure | Evidence |
|---|---|---|
| `fetch_prices.php` | HTTP **404** since 2026-04-29 | `fix-p0-safe-fixes` checklist |
| `signal_outcomes` resolution | **RED**, ~80 days stale | same |
| `hilarious-seer` crypto dataset | **172 days stale** | `final_v2/hilarious-seer/README.md` |

A prediction system whose prices stopped updating in April is not measuring predictions. Any metric
computed over a stale price feed is a fabrication with a timestamp.

**Fix:** freshness gate per feed with a hard TTL; the dashboard build fails (not warns) when a feed
exceeds TTL; `tools/db_freshness_check.py` + the hourly guardian already exist — extend coverage to
these three. (→ G9, A5)

---

## B10 — FAIL: 53 undecisive rows are silently 1.5% of the ledger

53 of 3,500 rows sit at `pnl_pct = 0` with `FORCE_CLOSED`/non-decisive status. They are excluded from
decisive cohorts by the screener (correct) but included in naive totals (incorrect). Separately,
`EXPIRED→WON` relabeling is still pending — a label change that would move win rates without any trade
changing.

**Fix:** `decisive` becomes an explicit stored boolean, not an inferred filter; any run that relabels
outcomes writes an audit row with before/after counts. (→ G10)

---

## B11 — OPEN: the statistical gates exist but were verified only in a worktree copy

`alpha_engine/money_ready_verdict.py` defines `_FDR_GATE_ENFORCE` and `_SINGLE_SOURCE_GATE_ENFORCE`
with tests asserting they default **False**. Those files were found under
`.kilo/worktrees/finpredict-v3/` — **not confirmed in the main tree** by my search. Peers claim they
were enabled on a `wiring` branch; I could not verify that from here.

**So: FAIL to verify, not verified-passing.** Re-check before relying on either gate.

---

## B12 — FAIL: readiness is decorative

`readiness.by_class` returns `sizing_allowed: false` for **all nine classes** (BOND, COMMODITY,
CRYPTO, EQUITY, ETF, FOREX, FUTURES, MEME, PENNY_STOCK). The scanner emitted ~390 picks/month anyway.

A flag that never blocks anything is documentation. This is the single cheapest structural fix in the
repo: connect it, or delete it and stop implying a gate exists.

**Implemented today:** `tools/per_class_cost_gate.py` + wiring in `tools/hc_gates_python.py`, enforced
by default with fail-open on missing evidence. Retroactive simulation: keeping only the passing class
turns **−617.5pp into +238.3pp** while removing 78.9% of emissions.

---

## B13 — FAIL: 360 workflow files with no owner map and heavy schedule collisions

Measured this session: **360** workflow files; **161** have `concurrency:` (199 do not), **271** have
`timeout-minutes:` (89 do not), **39** still declare a `push:` trigger; many share the same cron
minute (20 on `0 6 * * *`). See `../01_plan/GITHUB_ACTIONS_FIXES.md` for the fix list.

> **Corrected 2026-11-14** after `final_v3/feat-stop-fill-cost-gate-final-v3/02-improvement-plan/GITHUB_ACTIONS_FIXES.md`
> caught it. This paragraph previously read "**0** have `concurrency:`, **0** have `timeout-minutes:`",
> which is false. The counts were verified twice — locally, and by an independent scan of `origin/main` —
> and the peer's 161/271/39 match exactly. Two of my own documents disagreed (the earlier PR text said
> "199 without `concurrency`"); the wrong one is the one that shipped. The conclusion is unaffected —
> 199 workflows that can race on the same output is still the defect — but a fabricated count in a bug
> report is exactly the failure being documented, so it is left visible rather than quietly edited. The `push:` trigger on `audit-dashboard.yml` was removed 2026-05-19 for a
real cancel-cascade; nothing prevents the same pattern from re-emerging in the other 359.

---

## B14 — epistemics: six peer reviews are one dataset read six times

Every package reviews the **same 3,500-row `recent_closed` window** (or the same 277-row FOREX slice,
or the same artifact files). Six agreeing agents are not six independent confirmations. Where they
agree, the agreement is about *this dataset*, not about the market.

This is not a bug in any package — they are honest about their inputs. It is a bug in reading them as
a panel. Any coverage claim ("we looked from many angles") must name how many **independent datasets**
were used: here, effectively one ledger plus one COT table plus one benchmark artifact.

---

## Themes, ranked by money moved if fixed

1. **B3 + B12** — fill fidelity and cost gate: together move −617.5pp toward +238.3pp on the same
   trades (in-sample, retroactive). Neither creates alpha.
2. **B2 + B4** — without reconciling denominators and exit semantics, every per-class number is
   provisional; this is what keeps the system from even *measuring* whether an edge exists.
3. **B1** — cheapest to fix, highest consequence per hour: one refuted strategy is currently
   advertised as deployable.
4. **B9** — anything stale invalidates everything downstream; stop computing on dead prices.
5. **B8** — until trial counts exist, every "validated" label is unfalsifiable.
