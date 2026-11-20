# P1-2 — Declaring the detectable effect size (M-107 amendment)

Date: 2026-11-20. Author: SUBQ seat.
Plan input: `plans/2026-11-20-remediation-plan.md` P1-3 ("Declare the detectable MDE … disclose the change under M-107").
Branch context: `zoo/p0-recovery-2026-11-20`; checkpoints `319be86fbe2`, `9fa7ea436b5`, `c12683134aa` untouched.
Nothing was committed, pushed, or stashed. No code file was edited by this task.

**This document is a disclosure. It changes no gate, no constant, and no acceptance criterion.**

---

## 1. The measurement

### Formula

The power calculation is the one already in the tree — I quote it, I did not change it:

```
alpha_engine/audit3_edge_hunt.py:76    POWER_Z = 2.8     # 80% power, two-sided 5%

:162  def required_n(effect_pct, sd_pct, z=POWER_Z):
          return int(math.ceil((z * sd_pct / abs(effect_pct)) ** 2))

:169  def required_n_mde(mde_pct, sd_pct, z=POWER_Z):
          return int(math.ceil((z * sd_pct / abs(mde_pct)) ** 2))

:385  "mde_pct": round(POWER_Z * sd / math.sqrt(len(vals)), 4)
```

So, for a class with observed standard deviation `sd` (per-trade net pnl, in percent) and `n` rows:

- **detectable effect** `mde(n) = POWER_Z · sd / √n`
- **rows needed** for a target effect `e`: `n(e) = ⌈(POWER_Z · sd / e)²⌉

`POWER_Z = 2.8` is a single constant standing for 80% power at two-sided α = 0.05 (1.96 + 0.84 ≈ 2.8).

### Inputs

Rows: the 3,500-row payload slice, through the canonical predicate
(`rows_source=payload_slice_canonical_predicate`, `audit_dashboard/data/dashboard_data.json`).
This is the same row set the panel ran on (P1-1). `sd` is the sample standard deviation of
`pnl_net_pct` per class; `n` is the row count per class.

### Per-class result

| class | n | sd (net %, per trade) | detectable at n (`POWER_Z·sd/√n`) | n needed for 0.05% | n needed for 0.10% |
|---|---|---|---|---|---|
| CRYPTO | 2070 | 6.7966 | **0.4183 %/trade** | 144,864 | 36,216 |
| EQUITY | 690 | 5.7562 | 0.6136 %/trade | 103,908 | 25,977 |
| ETF | 503 | 2.7741 | 0.3463 %/trade | 24,134 | 6,034 |
| FOREX | 199 | 0.9106 | 0.1807 %/trade | 2,601 | 651 |
| BOND | 28 | 0.8722 | 0.4615 %/trade | 2,386 | 597 |
| COMMODITY | 9 | 2.4509 | 2.2875 %/trade | 18,838 | 4,710 |
| FUTURES | 1 | 0.0000 | undefined (n=1, no variance estimate) | — | — |

Every class is "underpowered" at 0.05%/trade. **None of them is underpowered at its own
detectable effect** — that is a tautology — the point is that the *question* "can this class
detect anything?" has a per-class answer, and for FOREX (n=199, sd=0.91) it is 0.18%/trade,
while for COMMODITY (n=9) it is 2.29%/trade. Those are different statements, and the flat
"UNDERPOWERED" label erases the difference.

### CRYPTO arithmetic, explicitly

```
n   = 2070
sd  = 6.7966                       (net pnl % per trade, sample stdev)

detectable = 2.8 * 6.7966 / sqrt(2070)
           = 19.0305 / 45.4973
           = 0.4183 %/trade

for 0.05 %/trade:
  n = ceil((2.8 * 6.7966 / 0.05)^2)
    = ceil((380.6096)^2)
    = ceil(144863.7)
    = 144864
```

The plan quoted ≈0.42% and ≈144,794. My measured values are **0.4183%** and **144,864**.
The 0.42% matches to the rounding shown. The 144,794 differs by 70 rows (0.05%) because it
implies `sd ≈ 6.7954` — a slightly different sd precision (rounded sd, or population rather
than sample stdev). The method is identical; only the sd input differs in the fourth decimal.
Reporting the difference rather than quietly adopting either number.

---

## 2. The declaration

**The 0.05%/trade MDE is not the operative threshold for judging whether a class is testable.**

0.05%/trade is the tribunal's PROVEN net-CI lower bound — a *pre-registered gate* for the
verdict word, not a statement about what a given book can resolve. Using it as the yardstick
for "is this class testable?" asks every class to clear a bar that only a book with ~145k
CRYPTO rows could clear. That is not a finding about the book; it is arithmetic about the
threshold.

**The operative question is: what effect can this n detect?** That is `POWER_Z·sd/√n`, the
third column above. A class is testable for an effect it can detect, and untestable for one
it cannot — per effect size, not per class.

**Declaration of measurement, not a change to any gate.** `POWER_Z`, `mde_pct`,
`required_n`, and `required_n_mde` keep their current values. The 0.05% gate keeps its
current value. What changes is only what is *published alongside* a verdict: the detectable
effect at the observed n, so "UNDERPOWERED" is read as "underpowered for 0.05%", not
"underpowered, full stop".

---

## 3. M-107 amendment block

**Dated 2026-11-20.**

- **Prior implicit threshold.** A single nominal MDE of **0.05 %/trade** was applied to every
  class, regardless of n or sd. It was never declared as a threshold for testability — it was
  the tribunal's PROVEN bound — but it was read that way, because the only power number in
  the output was the one computed at it.
- **Declared detectable effect, per class** (at the n and sd measured above):
  CRYPTO 0.4183 · EQUITY 0.6136 · ETF 0.3463 · FOREX 0.1807 · BOND 0.4615 ·
  COMMODITY 2.2875 %/trade · FUTURES undefined (n=1).
- **Why this is recorded rather than applied silently.** Changing what threshold counts as
  "testable" *after* seeing which classes came out underpowered is exactly the move M-107
  forbids doing quietly. I am not changing the threshold — I am publishing the per-class
  detectable effect so that a reader can see the 0.05% label was an unattainable bar for most
  classes, and can judge the book on an effect it could actually have detected.
- **No acceptance criterion in the hypothesis registry is altered by this document.**
  `reports/hypothesis_registry.json` is untouched. No verdict is re-worded, no gate is
  loosened, no class is promoted.
- **What is actually changing in code: nothing.** This is a disclosure. The code keeps its
  existing constant (`POWER_Z = 2.8`) and its existing gate (0.05%). A future change to the
  gate itself would need its own M-107 entry, its own review, and its own dated reason — it
  is not this document.

---

## 4. What this does and does not license

**It does NOT license calling a class profitable.** CRYPTO is below PF 1.0 on the net
measures (0.2628 net over the dashboard payload, 0.8339 net in the tribunal ledger — see
`reports/2026-11-20-p1-1-pf-reconciliation.md`). The fact that 0.42%/trade is detectable at
n=2,070 does not mean a 0.42%/trade edge exists. Detectable is not detected.

**It does NOT license dismissing the 0.05% gate either.** The gate is a pre-registered
criterion for the verdict word PROVEN; it stays. A class that cannot reach it is CANDIDATE,
not PROVEN — that is correct behaviour.

**It DOES license not calling a class "untestable" when the threshold was simply
unattainable.** FOREX at n=199 can resolve a 0.18%/trade effect; saying it is "untestable"
because it cannot resolve 0.05% is a statement about the threshold, not the data. The same
applies to a future re-run of CRYPTO on the canonical book: if the canonical book has more
rows than this slice, its detectable effect shrinks by √(n_slice/n_canonical) — and that is a
number worth quoting next to any verdict, which is the whole of this amendment.
