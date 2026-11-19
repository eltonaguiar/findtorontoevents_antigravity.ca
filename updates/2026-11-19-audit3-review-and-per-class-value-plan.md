# audit3 review, COMS reconciliation, and the measured per-class value plan (2026-11-19)

Review of `/audit3` as merged, of every audit3 `.MD` that landed today, and of the two
COMS handoffs — then the one thing that was missing from all of them: a slice-level
test of *where*, if anywhere, a pick beats matched exposure.

Everything below was run against `origin/main` = `aca4bcd70e2` (after #910) in a clean
worktree, with the live payload and read-only DB access.

## 1. What I verified on merged main (not assumed)

| Check | Result |
|---|---|
| `test_audit3_forward_gate` + `forward_observations_ingest` + `tribunal` + `enforcement` + `expectancy_gates` | **84 passed** |
| forward gate survived the #910 consolidation | `forward_gate_block()` intact; `_promote(cell, forward)` intact |
| gate state on the live book | `enforced: true`, `n_rows: 430`, fingerprint `5771c6fac172ca46`, `read_errors: []` |
| pre-registered pod | `POD-EQUITY-BREAKOUT`: `n_forward 0` — "no forward rows, nothing can promote" |
| H-119 hypothesis | 430 rows, net PF 1.1147, CI-LB 0.9213, IR 0.0429, intrabar first-touch 100%, benchmark 80% → **not eligible** |
| live ledger | 3,500 rows, 41 cells tested of 179, **0 PROVEN**, 3 CANDIDATE, 37 WEAK, 1 KILL (2.44%), 138 insufficient |
| segments | 60 tested: 10 harmful, 6 positive, 0 proven |
| coverage | 3,500 of 14,627 closed picks = **23.9%** |
| selection alpha in the ledger | `available: false` — the committed sidecar is not passed by CI |

So the consolidation did not undo the forward gate, and the gate remains the reason
`n_proven = 0`. That is a *measured* zero, which is the improvement over "no forward
evidence exists".

## 2. Review of the `.MD`s that landed today

All of these are on main now; this is what they collectively say and where they are
already stale.

| Doc | Verdict |
|---|---|
| `docs/AUDIT3_REVIEW_2026-11-19.md`, `updates/2026-11-19-audit3-tribunal-f1f2-n1-n2-n3-n4-n5-n7.md` | Sound. F1 block bootstrap, F2 split-half, N1 persistence, N2 churn, N3 recency, N4 materiality floor, N7 freeze — all present in merged code and covered by tests. |
| `docs/EDGE_IDEAS_BACKLOG_2026-11-19.md` | The best document in the repo right now: every idea has a kill criterion, and §3 lists what is already built so it stops being re-proposed. §14 v3 delta is accurate on all but two rows. |
| `docs/FUND_MANAGER_QUICK_VIABLE_PLAN_2026-11-19.md` | Right on doctrine (WR never gates a sleeve), **wrong on which class to back** — see §5 below. |
| `docs/MONEY_READY_STATE_AND_TIMELINE_2026-11-19.md` | Correct method and correctly pessimistic, but its numbers are already stale: it says 16,330 closed picks / 21.4% coverage / 1 CANDIDATE; today it is 14,627 / 23.9% / 3 CANDIDATE. |
| `docs/FINANCE_DB_SCHEMA_SPEC.md` | Useful; the Appendix A corrections (every price table omitted) are the reason it can be trusted. |
| `docs/FORWARD_LEDGER_CONTRACT_2026-11-19.md` + `updates/2026-11-19-forward-gate-ingest-selection-alpha.md` | Updated by me earlier today: ingestion wired, 430 rows, reconciliation rule. |
| `docs/AUDIT3_FEEDBACK_RESPONSE_2026-11-19.md` | Row-by-row response to the external review; the `forward_observations` row is now "shipped and filled". |
| `updates/2026-11-19-audit3-2x-cost-required-gate.md` | Verified: `stress_2x_ok` is a hard gate, and the CANDIDATE it examined passes it (no verdict churn). |
| `updates/2026-11-19-audit3-canonical-fullbook-verification.md`, `...-premerge-research-poc.md` | Both honest: the canonical book scores 8,735 rows (53.5%) and **refutes the slice's only candidate**. |
| `updates/2026-11-19-*.md` (12 consolidation docs), `reports/quant_auditor_deep/2026-11-19.md` | Consistent with the merged code. |

**Consensus across today's docs:** no directional-prediction edge on public data; the
losses are exit geometry plus costs; the durable public edges are risk premia; and no
new strategy may be generated while a P0 is open (N7 is armed — `tools/strategy_freeze_gate.py`
exits 1). I agree with all of it, and my measurements below sharpen rather than
contradict it.

**Where they disagree with the data, I say so:**

1. The fund-manager memo nominates **EQUITY** as the premium pod on the strength of
   "+0.61 OOS Sharpe". Measured selection alpha for EQUITY is **+0.114%/pick
   [−0.407, +0.593]** — indistinguishable from zero — and its positive slices are all
   conditioned on *hitting take-profit* (§5). That is not evidence of selection skill.
2. `MONEY_READY` says one CANDIDATE; the merged ledger produces three. One of them
   (`MomentumEMA`) has selection alpha **−4.725%/pick (q = 0.024)**: it made +0.759%/trade
   while lagging simply holding the same instruments.
3. The v3 delta leaves "one smart-picks definition" open; still open.

## 3. `/audit3` surface — what improved, what is still misleading

Improved and verified: coverage panel states the denominator on every render; dead
tier-2 tile and "Renaissance T1/T2/T3" labels gone; PF-lift "POSITIVE" card removed;
canonical mode declared (`canonical|payload_slice`); 2×-cost column present.

Still wrong, in priority order:

1. **The strongest gate is invisible.** `audit_dashboard/audit3.html` contains **zero**
   occurrences of `forward_gate`. A reader cannot tell that PROVEN_T2 is gated on a
   ledger, nor see the 430 rows, the fingerprint, or the pod clock. The gate exists and
   is enforced — the page just doesn't say so.
2. **The alpha gate reports "not available" in production.** CI does not pass
   `--alpha reports/selection_alpha_2026-11-19.json`, so the G8 alpha gate is inert and
   every class reads `beta_dominant` without a number next to it. The sidecar is
   committed; it should be the default.
3. **CANDIDATE does not mean "has skill".** All three candidates are `discovery`
   namespace, so the alpha gate never applies to them. `MomentumEMA` is the proof.
4. **No hold-time breakdown.** The one thing that separates the book's winners from its
   losers is `trade_timeframe`, and no surface shows it (§5).

## 4. COMS review

Two handoffs plus my own bus bug report. Read in full, cross-checked against the repo.

**`COMS_HANDOFF_2026-11-19.md` (code agent, main tree)** — accurate on substance, and
its #1 recommendation is unexecuted: it lists 8 files as *uncommitted*, and they are
still uncommitted now (`audit3_tribunal.py`, `audit3_edge_hunt.py`,
`forward_observations_ingest.py`, `forward_validator.py`,
`multi_asset_copytrader_scraper.py`, two test files, one new workflow). That is the
single largest operational risk in the repo today: a worktree switch or a `checkout`
loses P0-4/P0-5/P1-1…P1-5 without a commit to recover it. Its warning #5 ("n_proven is
held at 0 by the forward gate") matches my measurement exactly.

Coordination hazard it does not mention: **P1-4 edits my `forward_observations_ingest.py`**
to add the `POD-EQUITY-BREAKOUT` condition. That change exists only in the dirty tree,
so the committed module will not emit those rows — and running `--apply` from their
tree will conflict with the version on main. Whoever lands it must rebase onto the
committed adapter rather than overwrite it.

**`COMS_AUDIT3_HANDOFF_2026-11-19.md` (kilo / vanilla-handsaw)** — F1/F2/N1–N5/N7 are
indeed in merged code; its "smallest step" proposals for N6/E11/E12/E13/E14 are the
right size. One number is stale in a way that matters for planning: it quotes
CRYPTO LONG −0.442%/pick and ETF LONG −0.272%/pick, both from the pre-#909 snapshot;
today they are **−0.525%** and **−0.119%**. Same sign, so the conclusion stands, but do
not re-quote the old figures.

**`updates/2026-11-18-coms-bug-report.md` (mine)** — now clearly load-bearing: B1 (send
with zero subscribers is discarded and still prints `sent`) and B4 (no non-blocking
read verb) mean **"I told the fleet" is not evidence**. The proof is this very review:
both handoffs survived only because they are files in git, not bus messages. Keep
handoffs as repo files; treat the bus as a wake-up ping.

## 5. The missing measurement: where does a pick beat holding?

`/audit3` answers per class, which is unactionable. I added `--rows-out` to
`alpha_engine/audit3_selection_alpha.py` (one JSON line per covered pick) and
`tools/alpha_slice_scan.py`, which tests 73 slices at n ≥ 30 and applies **BH across the
whole batch** (q ≤ 0.10, positive mean, CI lower bound above zero).

2,475 picks, **10 slices survive**. The distinction that matters is whether a slice is
knowable *at issue time*:

### Pre-committable (known when the pick is emitted — these can become filters)

| Slice | n | alpha/pick | 95% CI | q |
|---|---|---|---|---|
| `trade_timeframe = POSITION` | 149 | **+2.242%** | [+1.195, +3.330] | <0.001 |
| `CRYPTO / POSITION` | 145 | **+2.006%** | [+0.969, +3.077] | 0.001 |
| `rr_ratio >= 2.0` | 43 | **+0.940%** | [+0.513, +1.326] | <0.001 |
| `trade_timeframe = INTRADAY` | 2,071 | **−0.132%** | [−0.231, −0.031] | 0.044 |
| `CRYPTO / INTRADAY` | 1,581 | **−0.155%** | [−0.260, −0.053] | 0.015 |
| `ETF / INTRADAY` | 256 | **−0.265%** | [−0.488, −0.033] | 0.073 |
| `EQUITY / INTRADAY` | 234 | +0.174% | [−0.331, +0.696] | 0.619 (n.s.) |
| `trade_timeframe = SWING` | 248 | −1.603% | [−6.188, +2.612] | 0.606 (n.s.) |

**This is the answer to "what would provide the most value per class".** The book's
alpha is not spread evenly across classes — it is concentrated in long-hold positions,
and the loss is concentrated in intraday crypto and ETF. CRYPTO as a class reads
−0.162%/pick while CRYPTO positions read **+2.006%** on 145 picks.

### Outcome-conditioned (only knowable after the exit — diagnostics, never filters)

| Slice | n | alpha/pick | q | Reading |
|---|---|---|---|---|
| EQUITY LONG, exit = TP | 80 | +2.288% | <0.001 | winners beat hold |
| CRYPTO SHORT, exit = TP | 205 | +0.869% | <0.001 | shorts are being taken where the drift is down |
| ETF LONG, exit = TP | 74 | +0.446% | 0.065 | |
| **CRYPTO LONG, exit = TP** | 377 | **−2.590%** | 0.065 | **TP is too tight: even the winners lagged holding** |
| **EQUITY LONG, exit = SL** | 85 | **−2.150%** | <0.001 | stop-outs are whipsaw, not protection |
| **ETF LONG, exit = SL** | 116 | **−1.016%** | <0.001 | same |
| CRYPTO SHORT, exit = OTHER | 323 | −0.560% | 0.014 | non TP/SL exits leak |

Note what this does to the earlier claim that "crypto longs lose 0.44%/pick because of
beta": the crypto-long cohort *that hit take-profit* still gave up **2.59 points per
pick** versus holding. That is exit design, measured, not inferred.

### Strategy level

`mega_mutation_macd_rsi_m048` +5.567%/pick (n=57, q<0.001) is the single largest
surviving slice — and the reason to be careful: it is one mutation among hundreds, BH
covers the 73 slices in this scan and not the 700+ strategies ever tried. It is a
pre-registration candidate, not a finding. `luxalgo_confluence` (n=1,211) is **harmful**
at −0.203%/pick (q=0.008) and should stay in the denylist discussion.

## 6. Ranked plan — what to do, in value order, per class

1. **Stop emitting INTRADAY for CRYPTO and ETF** (keep shadow rows). Measured bleed
   −0.155%/pick on 1,581 crypto picks and −0.265%/pick on 256 ETF picks, both BH-significant.
   No new code: a filter plus shadowing, reversible, and it closes the largest part of
   the −0.131% overall alpha without inventing anything.
2. **Pre-register a POSITION-timeframe pod** (crypto first, then equity). This is the
   only *pre-committable* positive slice in the book (+2.006%, n=145) and the only path
   I found where selection alpha is positive and not an artefact of the exit reason.
   Retrospective, so it must go through M-107 and accrue forward rows before it can
   promote — but it is what the 90-day clock should be pointed at.
3. **Redesign exits against measured priors** (E14, now with numbers): widen crypto-long
   TP (TP hits −2.59 vs hold), soften equity/ETF stops (SL hits −2.15 / −1.02 vs hold),
   and A/B a vol-scaled time exit on the same signals.
4. **Make the alpha gate real in CI**: pass the committed
   `reports/selection_alpha_2026-11-19.json` by default, so the ledger stops publishing
   `available: false` and the page can show a number instead of a blank.
5. **Render the forward gate on `/audit3`**: rows, fingerprint, pod clocks, and why
   PROVEN_T2 is empty. One panel; the data is already in the payload.
6. **Apply the alpha gate to discovery CANDIDATEs** as at least a `beta_dominant` flag —
   `MomentumEMA` would have been caught by it.
7. **FX backfill (E11)** remains the only way FOREX becomes measurable at all; nothing
   above touches FOREX, BOND, COMMODITY or FUTURES because they have no price coverage.

Per class, in one line each:

* **CRYPTO** — alpha lives in POSITION (+2.006%), loss lives in INTRADAY (−0.155%);
  the LONG TP is too tight (−2.590% on winners).
* **EQUITY** — class alpha is noise (+0.114%); the entire profile is exit geometry
  (TP +2.288%, SL −2.150%), and it is the only class where intraday is not negative.
* **ETF** — essentially all of the class loss is intraday (−0.265% of 256 picks);
  monthly/position only, and stops cost 1.02%/pick.
* **FOREX / BOND / COMMODITY / FUTURES** — unmeasurable until E11; report as absent,
  never as zero.

## 7. What I changed in this commit

* `tools/alpha_slice_scan.py` — slice scan with BH over every slice examined, explicit
  `survives` / `hurts` flags, and per-class rollup that attributes a slice to a class
  only when the slice *is* about that class.
* `alpha_engine/audit3_selection_alpha.py` — `--rows-out` per-pick JSONL (opt-in; the
  existing summary output is unchanged).
* `tests/test_alpha_slice_scan.py` — 5 tests: class attribution, exit buckets, BH
  bounds, noise rejected while a planted +2% edge survives, harmful slice flagged.
* `reports/alpha_slice_scan_2026-11-19.json` — the run behind every number above.

## 8. Limits (read before quoting this)

* The scan is **discovery on the same book**. BH corrects for the 73 slices examined,
  not for the 700+ strategies the repo has tried or for the slices I chose to define.
  `POSITION` and `rr>=2.0` are pre-registration candidates, not permissions.
* Exit-reason slices are conditioned on the outcome and are diagnostics about exit
  geometry only. Do not ship them as filters.
* Coverage is the payload slice (2,475 of 3,500 scored picks), not the canonical book
  (8,735 rows). Alpha may differ on the canonical denominator.
* Bars are 1h crypto / daily equity-ETF with a 3h/5d tolerance; there is no intrabar
  fill model inside the alpha calculation, so alpha is if anything overstated for
  fast strategies.

*Not investment advice. Every number is reproducible with the two commands below.*

```bash
python3 alpha_engine/audit3_selection_alpha.py --picks audit_dashboard/data/dashboard_data.json \
  --out /tmp/sa.json --rows-out /tmp/alpha_rows.jsonl
python3 tools/alpha_slice_scan.py --rows /tmp/alpha_rows.jsonl --out /tmp/scan.json
```

## 9. Correction log — the scanner's test shipped red twice

Recorded because it is the kind of thing that should not be discovered later:

* #912 and #913 merged `tests/test_alpha_slice_scan.py` with one failing test
  (`test_noise_does_not_survive_but_a_real_edge_does`). `gh pr merge` does not run
  tests, and I chained the merge behind the test command instead of gating on its
  exit status, so a red test reached `main` twice.
* **The tool was correct both times; the fixture was wrong.** It planted the real
  +2%/pick POSITION edge inside CRYPTO and then asserted that `class:CRYPTO` must
  *not* survive. A class that contains a genuine edge is supposed to read positive —
  the assertion was testing the opposite of the tool's contract.
* Fix: the "noise must not survive" assertion now uses a class made only of
  symmetric zero-mean noise (ETF), and the per-class expectations are stated
  explicitly. Production code unchanged; **no number in this document changes.**
* Process fix taken from it: gate a merge on the test command's exit status, never
  on the PR having been created.
* Residual cause after the fixture move: `class:CRYPTO` and `class_tf:CRYPTO/POSITION`
  both sat at +2.000 with n=40, so which one "wins" depends on sort order. The
  assertion now checks the surviving alpha value (and that the slice is
  class-scoped) rather than a tied slice name.
