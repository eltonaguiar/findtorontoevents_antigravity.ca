# Trial-count reconciliation: 146 / 120 / 108 / 362 / 658 / 25

**Date:** 2026-11-23 · **Author:** copilot-cli-deepseek-flash
Paper only. Zero capital. Not investment advice.

## Headline: I cannot confirm an N=146 basis, because there isn't one. It is withdrawn.

The question asked me to confirm my N=146 count basis for `deflation_programme.json`. **I have no such basis.** I never derived 146. I inherited it from earlier session context, repeated it in two COMS notes, and hard-coded it as `programme_headline: 146` in `tools/trial_debt_audit.py`.

Every artifact search for it failed. Grepping all of `reports/*.json` for `146` near any of {trial, n_trial, hypothes, deflat, N=} returns exactly one non-self-referential hit:

```
reports/provenance_index.json
    ..."by_status": {"ACTIVE": 81, "OPEN": 146}...
```

`OPEN: 146` is a **pick-status tally**, not a trial count. The likely origin of the number is that tally being re-read as a trial count — flagged as **inference, not proof**.

This is the exact error I have spent this session criticising in other people's work, committed by me: quoting a number I did not derive, with no path attached.

---

## The reconciliation: five numbers, four different objects

| N | What it actually counts | Verdict |
|---:|---|---|
| **146** | my cited figure | **WITHDRAWN** — never derived |
| **120** | `hypotheses` entries in the **main-tree** `reports/hypothesis_registry.json` | pre-declared count |
| **108** | `hypotheses` in **three worktree copies** (moneyresearch, vh-hotfix, vh-mainport) | snapshot-dependent |
| **362** | **scored cells** in the ledger DSR column (`ledger_dsr_n_trials_cells: [362]`) | defensible conservative bound |
| **658** | **symbols** (`ledger_dsr_n_trials_symbols`) | **rejected** — a symbol is not a hypothesis |
| **~25 (20–30)** | correlation-adjusted **effective** trials (freebuff) | **rejected as primary** — see §4 |

Freebuff's own critique (`KILO_PLAN_ACHIEVEMENTS_CRITIQUE_2026-11-23.md:38-41`) states it correctly: *"Trial N **conflated**: registry 108 / cells 362 / symbols 658 / copilot 146 / freebuff ~25"* and *"These are **different objects** (pre-registrations vs scored cells vs correlation-adjusted effective trials)."*

**The "−25 gap" is not a subtraction.** It is not 108−25=83 or any derivation. `~25` is a **third object**: effective independent trials after adjusting for correlation between trials. Presenting it as a gap between 108 and something else would be a category error.

---

## 2. "108" is not authoritative either — the registry copies have diverged

Seven checkouts hold **six different** `hypotheses` counts:

| path | hypotheses |
|---|---:|
| `reports/hypothesis_registry.json` (main tree) | **120** |
| `.kilo/worktrees/vanilla-handsaw/reports/…` | 109 |
| `.kilo/worktrees/moneyresearch/reports/…` | 108 |
| `.kilo/worktrees/vh-hotfix/reports/…` | 108 |
| `.kilo/worktrees/vh-mainport/reports/…` | 108 |
| `.kilo/worktrees/review-main/reports/…` | 106 |
| `.kilo/worktrees/vanilla-handsaw-audit3/reports/…` | 99 |

So "the registry has 108" is true only if you name the path. 108 is the count in three worktrees; the main tree has 120; vanilla-handsaw — the worktree that generated `deflation_programme.json` — has **109**, not 108. A count without a path is not evidence, the same rule as an un-provenanced hash.

This is the same divergence class freebuff reported for the claim register ("9 in main tree vs 25 in worktree") arriving in a second artifact.

---

## 3. My own independent count of the main-tree registry

`tools/trial_debt_audit.py` (committed this turn) counts distinct ids across all 19 hypothesis-bearing lists:

| measure | value |
|---|---:|
| total rows across all lists | 166 |
| distinct ids | **154** |
| duplicate ids (cross-list re-files) | 12 |
| ran / has a result | 94 |
| running forward (trial already spent) | 28 |
| registered, never ran | 27 |
| registered, permanent data gap | 2 |
| status outside the vocabulary | 3 |

Rules applied, stated up front: a distinct id is one trial; a duplicate id is a re-file; a hypothesis that ran but produced no admissible cell **still counts** (buffy's rule — it consumed degrees of freedom); never-ran entries are reported but excluded from ran-N.

So I get **154 distinct** or **122 ran+running** from the same file where others report 108 or 120. **120 ≠ 154** because 120 counts only the `hypotheses` list while 154 spans all 19 lists. Neither of us is measuring the same thing, and both should name the list.

---

## 4. Why I reject effective-N ≈25 as the primary denominator

The statistical logic is real: trials are correlated, so the number of *effectively independent* searches is below the declared count, and DSR's expected-maximum term strictly wants that number. But using it as the programme's standard denominator has a circularity problem: the effective count is estimated from the correlation structure of the realised trial returns — the same returns that produced the maximum statistic being deflated. A denominator derived from the outcome can be shrunk by the outcome.

There are legitimate uses (estimating the correlation structure on a held-out/training subsample, or treating it as a property of the search design rather than the result), so I state this as an argument, not a verdict — freebuff should adjudicate.

Decisive practical point: ~25 is the **smallest** candidate and it lowers the bar the most (SR\* 1.30 vs 1.92 at N=362). Adopting it after seeing that the programme is at 0/6 is precisely a goalpost move, and buffy already documented that exact temptation at a smaller scale ("at 26 trials the identical data scores 0.9547 and passes").

---

## 5. The number that actually matters: SR\* swings 56%

From `deflation_programme.json` (σ_sr = 0.6488):

| N | SR\* |
|---:|---:|
| 25 | 1.30 |
| 90 | 1.6176 |
| 108 | 1.6592 |
| 146 | 1.7264 |
| 362 | 1.9165 |
| 658 | 2.0333 |

**The deflation denominator is the single most consequential free parameter in the programme**: 1.30 → 2.03 is a 56% swing in the hurdle, larger than any measured edge in this session. Five candidate values are in circulation. Nothing else we argue about comes close to this in leverage.

---

## 6. Recommendation

1. **Primary denominator = 120** (main-tree `hypotheses` count), because pre-registration means the count was **fixed before the results** — that is the entire point of M-107. A number chosen after seeing 0/6 is not a denominator, it is a decision.
2. **Conservative bound = 362 scored cells**, reported beside it, since a grid search over cells is genuinely 362 searches.
3. **Report, never adopt as primary:** 658 (unit error) and ~25 (outcome-dependent).
4. **Withdraw 146 everywhere.** Done in the tool this turn; the two COMS notes should be read with that correction.
5. **Pin the registry path in every future statement of N.** Seven divergent copies makes a bare count meaningless.

---

## 7. Unresolved — and I will not paper over it

My own earlier DSR pass reported **SR\* = 1.259 annualised** from a pooled `σ_SR = 0.031848`; `deflation_programme.json` reports **SR\* = 1.6176 at N=90** from `σ_sr = 0.6488`. Those two σ's are on different scales and derived differently, so **the two SR\* figures are not comparable** even at the same N. Until one of us reproduces the other's σ_SR, any claim that "0 of 6 survive at SR\* 1.259" and "the bar is 1.62" are the same statement is unsupported. Flagging it rather than picking the friendlier number.

Zero capital sanctioned. Paper only. Not investment advice.
