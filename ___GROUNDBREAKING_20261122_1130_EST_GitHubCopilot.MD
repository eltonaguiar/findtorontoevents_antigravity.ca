# ___GROUNDBREAKING_20261122_1130_EST_GitHubCopilot.MD

## The project's "strongest HONEST money-ready lead" has zero forward evidence and is net-breakeven on its own sample

`reports/hypothesis_registry.json` describes **H-119** as *"The project's strongest
HONEST money-ready lead"*, status `FORWARD_ACCRUING`, gate `~2026-06-25`.

On `2026-11-22` it holds **430 rows** in `reports/forward_observations.jsonl`. I
had restored those rows from git earlier today after a data-destruction bug and
still owed an answer to R8: *attribute them, or write them off.*

The answer is neither. They are **100% backfilled**, and when their statistics are
computed honestly they do not support the word "strongest" at all.

---

### 1. Provenance: 0 of 430 rows are forward-creditable

A forward observation must be written **before** its own outcome exists. Test:

| check | result |
|---|---|
| distinct `created_at` dates | **1** (`2026-11-19`) |
| rows created AFTER their own `closed_at` | **430 / 430 (100%)** |
| created-minus-closed | min **1.3 d**, median **103.4 d**, max **162.5 d** |
| closed BEFORE H-119 was registered (`2026-06-13`) | **106 / 430 (25%)** |

Every row was written in a single bulk insert on 2026-11-19, after the outcome was
already known, in some cases 163 days after. Twenty-five percent closed before the
hypothesis that supposedly predicted them even existed.

**This is a retroactive backfill sitting in a file named `forward_observations`.**
Any forward clock that reads this ledger credits H-119 with 430 observations on a
day it has zero.

I am not calling the rows worthless. They are a legitimate *historical* sample. They
are simply not forward observations, and nothing may count them as such.

### 2. The statistic, recomputed from raw rows

H-119's registered test is *net-of-16bp-RT-crypto PF CI-LB, symbol-day clusters,
min_n=150, min_ci_lb=1.15, concentration<35%*. The ledger stores `fees=0.0` and
`funding=0.0` on all 430 rows, so **net is not in the file** — I apply the
hypothesis's own registered 16bp rather than inventing one.

I also checked the obvious trap: `slippage_bps` is a constant `16.0` on every row,
which looks like the cost is already deducted. It is not — LONGs split 76 below /
101 above the resolver exit, so `exit_px` is unadjusted and deducting 16bp does not
double-count. (I checked this specifically because the correction *helped* the
hypothesis, and a correction that helps me is the one I trust least.)

**8 rows carry resolver prices that disagree with the recorded exit by >10%**
(worst: DOTUSDT entry 0.5848, resolver exit **0.854** — a 46% price error;
NEARUSDT 1.9499 vs 1.3704). Those are resolver errors, not resolutions. Screened at
10% and both scopes reported, because silently dropping bad rows is how a sample
gets curated into a result:

| scope / price | n | clusters | gross PF | **net-16bp PF** | net mean | CI-LB |
|---|---:|---:|---:|---:|---:|---:|
| all / resolver | 430 | 374 | 1.042 | 0.940 | −9.60 bp | 0.712 |
| all / exit_px | 430 | 374 | 1.272 | 1.115 | +13.48 bp | 0.882 |
| **clean / resolver** | 422 | 367 | 1.094 | **0.978** | −3.22 bp | **0.775** |
| **clean / exit_px** | 422 | 367 | 1.203 | **1.050** | +5.88 bp | **0.850** |

Removing the 8 broken rows moves the answer by ~0.04, so **the conclusion is not
driven by the data errors.** The two price conventions bracket **breakeven**
(0.978–1.050) and neither CI-LB (0.775–0.850) comes within 0.30 of the 1.15 gate.

**Verdict: net-breakeven after its own cost assumption. Does not pass its own gate.**

Concentration passes (top symbol JUPUSDT 5.1%, 109 symbols) — so this is not a
concentration artefact either. It is simply a strategy whose gross edge (~+12.8 bp
per trade) is very nearly exactly consumed by a 16 bp round trip. That is the same
cost wall I measured everywhere else in this programme, now confirmed on the lead
the project was most confident about.

### 3. R8 disposition

**QUARANTINE. Do not attribute, do not delete.**

- The 430 rows stay in the ledger as history, tagged as backfilled.
- They must not count toward `n`, toward `FORWARD_ACCRUING`, or toward any gate.
- H-119's status `FORWARD_ACCRUING` is misleading while its forward count is **0**.

### 4. Reproducer

```
python3 tools/h119_ledger_audit.py
# -> reports/h119_ledger_audit/h119_ledger_audit.json
```

Read-only. Does not rewrite the ledger; quarantine is the registry owner's call and
this file only produces the evidence for it.

---

## Why this matters beyond H-119

This is the **fifth** independent measure in this programme to land on the same
number: intraday crypto (per-trade edge 2.5 bp vs ≥12 bp cost), ETF breakout
(4.7 bp vs 5.1 bp), the unreproduced breakout pod (PF 1.479 → 1.00), funding carry
(3.18%/yr vs a 3.5% T-bill at VIP0 fees), and now the flagship directional crypto
lead (gross +12.8 bp vs 16 bp cost).

**The pattern is not "we have not found the edge yet". It is "gross edges exist and
are consistently about the size of the round trip."** Any strategy search that does
not model cost at the same resolution as signal will keep producing PF > 1.4 on
paper, and this registry has now produced at least two of those.

Zero forward observations support any of the positive claims. Not investment advice.

*Evidence class: LEDGER PROVENANCE + STATISTIC RECOMPUTE. No capital sanctioned.*
