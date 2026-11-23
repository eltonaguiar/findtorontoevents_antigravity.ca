# pump-watch → cross-system consensus panel (todo 10) — built, pre-registered, REFUTED

**Date:** 2026-11-23
**Owner:** `copilot-cli-deepseek-flash`
**Closes:** todo #10 (was blocked on "a decision to proceed" — the operator's instruction to work through the backlog is that decision)
**Hypothesis:** `H-248` in `reports/hypothesis_registry.json`
**Artifacts:** `tools/pumpwatch_consensus.py`, `audit_dashboard/data/pumpwatch_consensus.json`, `audit_dashboard/pumpwatch_consensus.html`

---

## TL;DR

The spec (`reports/PUMPWATCH_CROSS_SYSTEM_SPEC_2026-11-23.md`) said: **pre-register
the consensus definition before measuring it**, then compare consensus picks against
single-system picks. That is what was built, in that order.

**Result: REFUTED.** Consensus picks are *worse* than single-system picks on the
point estimate, and neither arm beats zero after 25 bp of cost.

| Arm | n | Mean (net of 25bp) | Median | 95% CI | Win rate |
|---|---|---|---|---|---|
| Consensus (≥2 systems) | 26 | **−1.03%** | −1.60% | [−1.96, −0.08]% | 34.6% |
| Single-system control | 803 | **−0.27%** | −0.28% | [−0.59, +0.06]% | 38.6% |
| **Difference** | | **−0.76%** | | **[−1.74, +0.28]%** | |

## 1. Order of operations (this is the point)

M-107 exists because a threshold chosen after seeing results is not a test. So:

1. **Feed inventory verified from source** — the spec explicitly listed this as
   unverified. `findcryptopairs/pump-watch.html` fetches **7 URLs across 4 systems**:
   `kimi`, `alpha_engine`, `ml_battleground/system_f_clawsofdoom`, `mercury2`
   (active + closed ledgers).
2. **H-248 registered with status `PENDING`** — window (24h), `min_systems` (2), the
   three systems used, the field mapping, and the symbol-normalization rule were all
   committed **before the first run**. The registry entry carries a
   `symbol_normalization` field so the rule is auditable rather than buried in code.
3. **Then measured.**

Only three of the four systems have closed (resolved) ledgers available locally:
`kimi` publishes `live_competition.json`, which is a competition feed, not a
resolved pick ledger. It is therefore excluded — stated here rather than silently
dropped.

## 2. Method

- **Consensus**: same base asset **and** same direction, entries within a **24h**
  window, from **≥2 distinct** systems. Rows inside a cluster are averaged so a
  chatty system cannot dominate by row count.
- **Control**: clusters where exactly one system emitted the pick — same ledgers,
  same period. Without this arm "consensus works" is unfalsifiable.
- **Symbol normalization** (frozen pre-run, applied to both arms): upper-case, strip a
  trailing quote asset (`USDT`/`USDC`/`BUSD`/`USD`) and the suffixes
  `-PERP`/`PERP`/`=X`/`=F`, keep the leading alphabetic base. `BTCUSDT`,
  `BTC-USD` and `BTC` therefore all compare equal.
- **Cost**: 25 bp round trip subtracted from every cluster in both arms, so cost
  cannot masquerade as signal.
- **Inference**: percentile bootstrap, 2,000 resamples, **fixed seed**
  (`20261123`) so the CI is reproducible.

## 3. What the numbers actually say

The verdict is `REFUTED` because the pre-registered criteria required
`mean_diff_gt_0` **and** `ci_lb_gt_0`. Both failed.

But be precise about the strength of the claim:

- The **point estimate** is negative (−0.76%), i.e. agreement made things worse.
- The **95% CI on the difference spans zero** ([−1.74, +0.28]%), so "consensus is
  harmful" is **not** established either.
- The correct reading is: **no evidence that cross-system agreement carries
  information**, with a sign that leans the wrong way. n=26 is small.

The control arm matters for interpreting this: single-system picks are also
negative (−0.27%, CI [−0.59, +0.06]). So this is not "consensus destroys a good
edge" — there was no edge in these ledgers to destroy. That is consistent with the
estate-wide finding (0 of 6 classes with n ≥ 100 and PF > 1).

The economic reading is the honest prior from the spec: all three systems read the
same exchange OHLCV, so agreement is **redundancy, not independent confirmation**.

## 4. Limitations (which bound the conclusion)

- **`alpha_engine` contributes only 327 of 2,204 rows** — 1,874 rows have no
  `timestamp`, so they cannot be placed in time and are dropped. This makes the test
  effectively **claws-vs-mercury2**. The panel surfaces this count rather than
  hiding it.
- Rows were dropped for **missing fields, not for their outcome**, so the comparison
  is not biased by the exclusions — but generalization is limited.
- `mercury2` is 100% LONG in this sample; the SHORT consensus arm is
  correspondingly thin.
- `kimi` excluded (no resolved ledger), as declared above.

## 5. Deliverables

| Path | Purpose |
|---|---|
| `reports/hypothesis_registry.json` → `H-248` | pre-registration + recorded result, `status: REFUTED` |
| `tools/pumpwatch_consensus.py` | the measurement (frozen constants at the top of the file) |
| `audit_dashboard/data/pumpwatch_consensus.json` | machine-readable result the panel reads |
| `audit_dashboard/pumpwatch_consensus.html` | read-only panel: verdict, both arms, criteria, data limitations |

The panel was rendered and inspected locally before commit (verdict, both arm rows,
criteria list and the `alpha_engine: no timestamp — 1874` limitation all display).
It is deliberately **descriptive only** — no picks, no signals, no sizing, no
capital — and says so in a banner.

## 6. Reproduce

```bash
python3 tools/pumpwatch_consensus.py --cost-bps 25
# -> audit_dashboard/data/pumpwatch_consensus.json
# -> REFUTED, difference -0.761402% CI [-1.740535, 0.276123]
```

Because the bootstrap seed and the frozen constants are fixed, re-running reproduces
the same CI exactly.

---

Descriptive statistics over already-resolved paper ledger rows. Zero capital, no
picks, not investment advice.
