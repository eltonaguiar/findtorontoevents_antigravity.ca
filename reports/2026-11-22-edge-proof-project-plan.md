# Edge-proof project plan — from "PF > 1 gross" to a capital-grade claim

**Date:** 2026-11-22 · **Author:** Buffy · **Status:** proposed, awaiting execution
**Scope:** every pick surface behind `/audit`, `/audit2`, `/audit3`, the forward book, and the 9 MySQL DBs.

---

## 0. The honest starting line

Nothing here is a money claim. As of today the desk has **no class-level edge that
survives cost**. The numbers below are the ones I would have to defend to an
investment committee, and they are the reason this plan exists rather than a
launch memo.

**Live per-class snapshot** (`audit_dashboard/data/dashboard_data.json`, gross /
net PF after the class cost model):

| Class | n | PF gross | PF net | Read |
|---|---|---|---|---|
| CRYPTO | 1,835 | 0.624 | 0.553 | structurally losing |
| EQUITY | 782 | 1.034 | **0.990** | only class with gross > 1; cost still eats it |
| ETF | 588 | 1.038 | 0.954 | gross > 1, net < 1 |
| FOREX | — | 1.203 | 0.857 | gross looks great, cost destroys it |
| BOND | — | 0.904 | 0.726 | losing |
| COMMODITY | — | 0.165 | — | broken, not merely bad — audit before quoting |
| FUTURES | 4 | — | — | n too small to mean anything |

**Full-population retraction (mine, 2026-11-22):** on 22,864 policy-clean crypto
picks the PF is **0.2656** at **−0.0464 %/trade gross**. Every class is negative
gross except ETF at n=32. First-touch reconciliation on 1,717 crypto picks shows
**54 % of exits differ** from the daily-close approximation — i.e. half of every
historical PF in this repo is an artifact of the exit convention. H-151 (funding
spread carry) is **REFUTED**: −0.2054 %/mo, t = −0.63.

**Forward book:** 5 entries OPEN (`alt_swing` LINK/AVAX/TIA, `momentum_ema_grid`
BTC/ETH), 0 closed, 0 scored. First score is arithmetically impossible until a
bar after the entry bar exists — not a bug, just an empty book.

**Hypothesis registry:** 108 hypotheses, but **29 distinct status strings** for
what should be a closed vocabulary (`PRE_REGISTERED` vs `PRE-REGISTERED`,
`UNTESTED` vs `REGISTERED-UNTESTED`, `forward-shadow`, `NULL`, and a status that
is a sentence: `REJECTED - only 0 scored windows (need 3)`). A registry whose
states cannot be counted cannot enforce M-107. Fixing this is P0.

**What is genuinely working:** the tooling. `deflated_sharpe`, `trial_counter`,
`benchmark_closed_ledger` (paired bootstrap vs same-window benchmark, random-entry
MC), `edge_stability_harness`, `walkforward_validator`, `anti_overfit_validator`,
`tools/forward_book.py`, `tools/verify_live_claim.py`, a resolver that can price
first-touch, and 875+ test files. The measurement layer is the asset; the alpha
is what we do not have yet.

---

## 1. Proof standard — G0–G8 (adopted from the peer Part 5 plan, pinned to repo checks)

A candidate is **not** "promising" until all nine pass. Each gate names the
artifact that proves it, so a claim can be checked without rerunning anything.

| Gate | Requirement | Proof artifact in this repo |
|---|---|---|
| **G0** Population integrity | Full policy-clean set, N declared before scoring, no window/parameter choice, no lookahead | `build_clean_ledger_v2.py` output + the pre-registered N in the hypothesis record |
| **G1** Honest resolution | Real-bar first-touch exits, not daily-close approximation | resolver first-touch path; reconciliation report (54 % mismatch is the baseline to beat) |
| **G2** Net expectancy | Bootstrap 95 % CI (2,000 seeded resamples) **lower bound > 0** net of cost | `benchmark_closed_ledger.py` / `bootstrap_verified_edges.py` |
| **G3** 2× cost stress | CI-LB still > 0 at **2× measured slippage** | same harness, `cost_multiplier=2` |
| **G4** Multiplicity | Benjamini–Hochberg q ≤ 0.1 **and** Deflated Sharpe ≥ 0.95 with n_trials = *all* cells tested | `deflated_sharpe.py` + `trial_counter.py` |
| **G5** Stability | Chronological split-half: both halves net mean > 0; no single fold PF < 0.9 | `walkforward_validator.py` / `edge_stability_harness.py` |
| **G6** Concentration | No symbol > 60 % of a cell; no source > 90 % of an aggregate | cell composition table in the harness output |
| **G7** Mechanism sanity | ≥ 3 distinct outcomes, ≥ 3 symbols, payoff not a 2-point grid, no parameter-count games | hypothesis record + trade outcome histogram |
| **G8** Forward evidence | Own pod, rows closed **after** registration, n ≥ 100, net PF ≥ 1.1 with benchmark leg positive | `forward_book.json` pod + `benchmark_ledger_proof.json` |

G8 is deliberately expensive: **n ≥ 100 closed forward trades**. At the book's
current 5 entries/week that is ~5 months for one rule. That is the real cost of a
capital-grade claim, and pretending otherwise (promoting at n = 0) is exactly the
failure mode the peer review caught.

### Sample-size reality check

With per-trade edge μ and σ ≈ 1R, 80 % power at α = 0.05 two-sided needs
n ≈ (2.80·σ/μ)²:

| μ per trade | n required |
|---|---|
| 0.05 R | 3,136 |
| 0.10 R | 784 |
| 0.20 R | 196 |

So a strategy that must be detected at 0.05 R/trade needs > 3,000 trades. Any
sleeve we promote with n < 196 and μ < 0.2 R is **not proven**, whatever its
backtest PF. This table should be quoted every time someone says "it's working".

---

## 2. Tracks, ranked by evidence quality (not by promise)

**T1 — Equity cross-sectional quality/momentum (highest priority).** The only
class with gross PF > 1 at meaningful n (782). Its problem is cost, not signal:
net 0.990 means we are ~1 % short. Levers: fewer, larger, slower trades; limit
entries instead of market; drop the symbols whose spread exceeds the expected
edge. Kill if no subset clears G2–G3 after P3.

**T2 — ETF trend/cross-sectional momentum.** Gross 1.038 / net 0.954 at n=588,
but full-population n=32 the other way. Needs the full-population rescore before
any claim. ETFs have the cheapest cost model in the book, so a small real edge
can survive.

**T3 — FOREX, gated hard.** Gross 1.203 / net 0.857. This class is a cost problem
wearing an alpha costume: 35 PF points of cost. Only viable with a structurally
cheaper execution assumption (limit fills, or funding/carry capture that pays us
to hold). Do not spend P3 budget here unless T1/T2 stall.

**T4 — Crypto directional: quarantined.** 22,864 picks at PF 0.2656 and
−0.0464 %/trade gross is not a tuning problem, it is a negative-expectancy
machine. Reopen only for *non-directional* mechanisms (funding/basis, liquidity
provision) registered as new hypotheses with no directional leg.

**T5 — COMMODITY / BOND: data audit before any statistic.** PF 0.165 is more
likely a pricing/roll bug than a signal. Audit pricing first; no hypothesis
spend until the data passes G0.

**T6 — Measurement infrastructure (runs in parallel, always).** Registry status
normalisation, per-entry TP/SL in the book schema (currently rule-level only, so
an entry cannot be scored independently), benchmark leg on every forward entry,
first-touch reconciliation folded into the resolver, cost model per venue, and
the QA-workflow silent-revert fix landed today (#1054) so source files stop being
rewritten by data jobs.

---

## 3. Phases and hard acceptance gates

**P0 — Freeze the measurement (½ day).** Normalise registry statuses to a closed
vocabulary; snapshot the population and the N for every class; record the trial
count that G4 will use; add per-entry TP/SL to `forward_book.json`.
*Acceptance:* registry counts sum to 108 with ≤ 8 statuses; `trial_counter` value
recorded; book schema carries TP/SL per entry.

**P1 — Honest re-resolution (1–2 days).** Re-resolve the full population with
first-touch on real bars, not daily close. *Acceptance:* ≥ 95 % of exits resolved
by first-touch; the delta vs the old convention published (baseline: 54 % differ).

**P2 — Full-population, cost-true rescoring (1 day).** Score every class with
G2 + G3 (bootstrap CI-LB, then 2× cost). *Acceptance:* a table with n, net mean,
CI-LB, CI-LB@2× cost per class and per cell — no cell quoted without its n.

**P3 — Candidate deep tests (2–3 days).** Only T1/T2 cells that survived P2 go
through G4–G7. *Acceptance:* each candidate has a harness run ID, BH q, DSR with
the real n_trials, split-half result, and a concentration table.

**P4 — Register and wire (½ day).** Survivors get a hypothesis record with the
frozen spec and enter the forward book as pods with benchmark legs.
*Acceptance:* every promoted pod has `registered_at` before its first forward row.

**P5 — Forward testing (the actual proof, weeks not days).** Books accrue
untouched; weekly scorecard publishes n, net PF, benchmark-relative return, and
gate status. *Acceptance for "proven":* G8 — n ≥ 100 closed, net PF ≥ 1.1, CI-LB
> 0, benchmark leg positive.

---

## 4. Forward-test sleeve design

- **Capital:** paper, fixed notional per trade; no compounding, so PF is not
  inflated by position sizing.
- **Frozen specs:** entry/exit rules and cost bps are fixed at registration.
  Any change requires a new hypothesis ID (M-107).
- **Benchmark leg:** every entry carries the same-window benchmark (SPY for
  equity/ETF, BTC-USD for crypto). A sleeve that matches its benchmark is beta
  and gets killed regardless of PF.
- **Promotion:** only via G8. No exceptions, no "small live test" shortcuts.
- **Kill:** drawdown ≤ −8 % of sleeve notional, or PF < 0.9 over the last 40
  closed trades, or CI-LB crossing 0 at the weekly review → stand down; re-entry
  needs a new hypothesis, not a tweak.
- **Cadence:** daily resolve (`tools/forward_book.py --resolve --publish`),
  weekly scorecard, monthly full-gate review.

---

## 5. What would make me concede there is no edge

Pre-committed now, so it cannot be rationalised later:

> If, after P2 and P3, **no** candidate reaches G2 + G3 with n ≥ 196 and
> μ ≥ 0.2 R **gross**, then there is no directional edge in the data this desk
> can access, and the honest deliverable is the measurement layer plus a pivot to
> non-directional mechanisms (funding/basis, liquidity provision, prediction-market
> arbitrage) — not another round of parameter tuning.

That is a real possibility. The evidence so far (every class negative gross at
full population except ETF at n=32) points at it more than it points away.

---

## 6. Phase board — every todo, with the check that proves it done

Each phase is a checklist. A box is only ticked when its **validation** command
has been run and its output is pasted into the phase log under
`reports/phase_logs/`. No box is ticked on inspection alone.

### P0 — Freeze the measurement (½ day)

- [ ] **P0.1** Define a closed status vocabulary (target ≤ 8: `UNTESTED`,
      `PRE_REGISTERED`, `TESTING`, `FORWARD_OBSERVATION`, `PAPER_PILOT`,
      `SUPPORTED`, `REFUTED`, `KILLED`) and write `reports/registry_status_vocab.md`.
- [ ] **P0.2** Map all 108 current statuses into it (`PRE-REGISTERED` →
      `PRE_REGISTERED`; `REGISTERED-UNTESTED`/`UNTESTED_DATA_GAP` → `UNTESTED`;
      `forward-shadow`/`FORWARD_SHADOW`/`SHADOW_LIVE`/`SHADOW_IMPLEMENTATION` →
      `FORWARD_OBSERVATION`; `TESTED_KILL`/`KILLED`/`FAILED_ARCHIVED` → `KILLED`;
      `TESTED_WEAK`/`NULL`/`REJECTED*`/`HARNESS_REJECTED` → `REFUTED`;
      `TESTED_PASS*`/`SUPPORTED`/`CLOSED` → `SUPPORTED`).
- [ ] **P0.3** Record the trial count that G4 will consume (`trial_counter`),
      with the timestamp, so the DSR denominator cannot drift later.
- [ ] **P0.4** Add per-entry `tp_pct`/`sl_pct`/`benchmark` to `forward_book.json`
      so an entry is scorable without consulting the rule table.
- [ ] **P0.5** Snapshot N per class into `reports/population_freeze_2026-11-22.json`.

**Validation:** `python3 tools/registry_audit.py --check-statuses` exits 0 and
prints ≤ 8 distinct statuses summing to 108; `pytest tests/test_registry_vocab.py
tests/test_forward_book_schema.py -q` passes; `git show HEAD:reports/population_freeze_2026-11-22.json`
contains an `n` for every class (no nulls).

### P1 — Honest re-resolution (1–2 days)

- [ ] **P1.1** Resolve the full population by real-bar first-touch (the resolver
      already supports it; the default path still uses daily close).
- [ ] **P1.2** Publish the delta table vs the daily-close convention per class.
- [ ] **P1.3** Wire the reconciliation into the resolver as a standing report so
      the 54 % mismatch cannot silently come back.

**Validation:** first-touch coverage ≥ 95 % (`unresolved_intrabar / n < 0.05`);
`pytest tests/test_first_touch_reconciliation.py -q` passes; the delta report
`reports/first_touch_delta_2026-11-22.md` quotes per-class n and % changed.

### P2 — Full-population, cost-true rescoring (1 day)

- [ ] **P2.1** Score every class and every surviving cell with bootstrap CI-LB
      (2,000 seeded resamples).
- [ ] **P2.2** Repeat at 2× measured cost (G3).
- [ ] **P2.3** Publish `reports/rescore_2026-11-22.md` — no cell without its n,
      net mean, CI-LB, and CI-LB@2×.

**Validation:** `python3 -m alpha_engine.benchmark_closed_ledger --picks <ledger>
--fetch SPY BTC-USD --fetch-picks --out reports/...` completes and the JSON
carries `ci_lb` and `ci_lb_2x`; `pytest tests/test_benchmark_closed_ledger.py -q`
passes (33 deterministic tests, incl. the coin-flip MC gate).

### P3 — Candidate deep tests (2–3 days)

- [ ] **P3.1** Only T1/T2 cells that cleared G2+G3 enter G4–G7.
- [ ] **P3.2** Run multiplicity honestly: BH q ≤ 0.1 **and** DSR ≥ 0.95 with
      n_trials = every cell tested, not just the winner.
- [ ] **P3.3** Split-half + fold table; concentration table; mechanism-sanity
      histogram (≥ 3 outcomes, ≥ 3 symbols, not a 2-point payoff grid).

**Validation:** `pytest tests/test_deflated_sharpe.py tests/test_dsr_baseline_skip.py
tests/test_dsr_trial_baselines.py -q` passes; `python3 tools/check_walkforward_gate.py`
reports every fold ≥ 0.9 PF and both halves net-positive; each candidate row in the
report links its harness run ID.

### P4 — Register and wire (½ day)

- [ ] **P4.1** Survivors get a frozen hypothesis record (spec hash, cost bps,
      benchmark, N).
- [ ] **P4.2** Each enters the forward book as a pod with `registered_at` set
      **before** its first forward row.
- [ ] **P4.3** Announce promotions to the fleet (see §8 COMS protocol).

**Validation:** `python3 tools/verify_promotion_order.py` exits 0 (asserts
`registered_at < min(entry dates)` for every pod); `pytest tests/test_forward_book.py
tests/test_hypothesis_registry.py -q` passes.

### P5 — Forward testing (weeks)

- [ ] **P5.1** Daily: `python3 tools/forward_book.py --resolve --publish`.
- [ ] **P5.2** Weekly: scorecard with n, net PF, benchmark-relative return, gate
      status per pod — published even when n is small (an empty book is a fact,
      not a failure).
- [ ] **P5.3** Monthly: full G0–G8 review; promotions and kills recorded in the
      registry, not in chat.
- [ ] **P5.4** Kill conditions enforced automatically: −8 % DD, PF < 0.9 over the
      last 40 closed, or CI-LB crossing 0.

**Validation:** `python3 tools/check_g8.py --pod <id>` exits 0 only at n ≥ 100
closed with net PF ≥ 1.1, CI-LB > 0 and benchmark leg positive;
`pytest tests/test_forward_book.py -q` passes; the weekly scorecard file exists
with a `generated_at` newer than 7 days.

### Gate → phase map

| Phase | Gates it must clear for its own exit |
|---|---|
| P0 | G0 prerequisites (declared N, closed vocabulary, trial count) |
| P1 | G1 (honest resolution ≥ 95 % first-touch) |
| P2 | G2, G3 (net CI-LB > 0, and at 2× cost) |
| P3 | G4, G5, G6, G7 |
| P4 | registration integrity (pre-registration ordering) |
| P5 | G8 (n ≥ 100 closed forward trades) |

---

## 7. COMS protocol — how the phases talk to the fleet

The desk is multi-agent; a plan that never leaves this repo will be re-litigated
every session. Each phase therefore has mandatory comms, on the existing
`COMMUNICATION/coms` tool plus the MQTT `notes/` topic.

**Command surface**
- `coms check --agent buffy` — drain my inbox (run at the start of every session
  and at every phase boundary).
- `coms send --to <agent> --subject ... --body ...` — peer message.
- `mosquitto_sub -h 192.168.2.52 -t 'notes/<slug>' -W 2` — read a shared note;
  `mosquitto_pub` to post one.

**Per-phase duties**

| Phase | Outbound | Inbound obligation |
|---|---|---|
| P0 | Announce the frozen population + vocabulary and the trial count (other agents' DSR numbers depend on that denominator) | Ack within 24 h; flag any hypothesis a peer is already testing so we do not double-count trials |
| P1 | Publish the first-touch delta (it changes every historical PF in the fleet's dashboards) | Ask Mercury3 whether their exit convention matches; reconcile or state the divergence |
| P2 | Publish the rescoring table with n on every row | Peer claims get re-derived from data before adoption — e.g. the "34-day-stale `dashboard_data.json`" claim was wrong (the file is gitignored and rebuilt hourly) |
| P3 | Post candidate list + harness run IDs before promotion, soliciting objections for 48 h | Objections must be answered in writing or the candidate waits |
| P4 | Announce promotions with symbol, entry, TP/SL, strategy, and gate status | Ask the paper-trader agent to mirror the pod |
| P5 | Weekly scorecard note (n, net PF, benchmark-relative, kill status) | Any peer kill/contradiction gets investigated same-week, not next month |

**Rules of engagement**
1. Peer claims are hypotheses, not facts: cite the file/commit that proves or
   refutes before repeating it.
2. Never announce a promotion before G8; announce *candidacy* and its gate status.
3. Every COMS message that changes a plan decision gets quoted in the phase log.
4. Silence is not agreement: an unanswered objection blocks promotion.

---

## 8. Immediate next actions (this week)

1. P0 registry normalisation + book schema TP/SL (small, mechanical).
2. P1 first-touch reconciliation wired into the resolver as a standing report.
3. P2 rescoring table published under `reports/`.
4. T6: sweep `.github/workflows/` for other `git reset --soft` data jobs that can
   silently revert source (the class of bug fixed today in #1054).
5. Weekly scorecard page wired to the forward book so the book's emptiness is
   visible rather than implied.

---

## 9. What this plan deliberately does not do

- It does not claim an edge, a return, or a probability of profit.
- It does not tune parameters to make a backtest pass; every candidate is
  pre-registered with its N.
- It does not call anything "ready" before G8, and G8 is n ≥ 100 closed forward
  trades.
