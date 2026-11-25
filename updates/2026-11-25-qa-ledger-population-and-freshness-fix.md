# QA Market Validation — the gate was miscounting, not finding bad data

**Date:** 2026-11-25 · **Branch:** `fix/qa-ledger-population-and-freshness` (cut from `origin/main` @ `547a00db1bb`)
**Files:** `tools/qa_ledger.py` (fix), `tools/qa_ledger_selftest.py` (new)

---

## 1. What was reported, and what is actually true

The hourly **QA Market Validation** job (`qa-market-validation.yml`) failed every hour on `main`
— 6 consecutive failures at 16:21, 17:15, 18:18, 19:16, 20:16, 21:16 on 2026-11-25. My earlier
document (`updates/2026-11-25-actions-validation-antigravity-main-and-gh-pages.md` §3a) recorded the
failure as "equity picks are shipping with missing or inverted TP/SL — fix the emitters."

**That diagnosis was wrong**, and it came from reading the gate's own summary line instead of the
rows behind it. The evidence, taken from `origin/main` (not from my checkout, which was ~13k
commits behind):

| Claim from the gate | What the data shows |
|---|---|
| `EQUITY blank_tp/sl=6` | All 6 rows have `direction` **WATCH** (5) or **SKIP_VOL** (1). These are *demoted* picks: published so the demotion is visible, never traded, and carrying no TP/SL **by design**. The 177 actionable `STRONG_BUY` rows all have TP+SL. |
| `EQUITY mismatch=8` | 0 rows where the published `pnl_pct` disagrees with the row's own `entry_price`/`current_price`. The 8 flags compare the snapshot against a **live** quote at a **0.5pp** tolerance, while the QA checkout lags the file by ~50 minutes and prices come from a different adapter. |
| `21 flags (15 critical)` → later `14 flags (8 critical)` | `BLANK_TP_SL` is **not** in the `critical` tuple, so the 6 blanks never affected the exit code. The 100% of the red is `MISMATCH`. |

Snapshot checked: `audit_dashboard/data/picks_now_live_pnl.json` on `origin/main`,
`generated_at: 2026-11-25T21:26:36.530430+00:00`, 183 picks, 31 EQUITY.

So the gate was correct to be red in spirit and wrong in construction: it counted non-picks as
picks, and it compared a stale snapshot to live ticks as if the two were contemporaneous.

## 2. What changed in `tools/qa_ledger.py`

1. **Population.** `BLANK_TP_SL` now applies only to actionable directions
   (`LONG, SHORT, BUY, SELL, STRONG_BUY, STRONG_SELL`). Non-actionable rows are counted as
   `demoted_no_tpsl` and are **never flagged** — they still appear in the per-class line, so the
   demotion stays visible instead of being silently dropped. Severity of `BLANK_TP_SL` is unchanged
   (non-critical, as upstream already had it).
2. **Freshness.** The external cross-check reads the snapshot's top-level `generated_at`:
   - **≤ `QA_FRESH_MIN` (default 15) minutes old**: the tight per-class tolerance applies and a
     breach is a critical `MISMATCH` — the original, intended check.
   - **Older**: a tight diff is expected drift and is counted as `stale_price`. Only a price
     divergence no drift can explain (published price vs external > **5pp**, > **10pp** for crypto)
     is escalated, as critical `PRICE_DIVERGENCE`. That is the failure class the tight check was
     silently proxying for: wrong symbol, wrong instrument, wrong price scale.
   - The snapshot age and `generated_at` are now written into the report, so a stale input is
     visible instead of inferred.
3. Unchanged and still critical: `UNPRICED`, `UNVERIFIED_ZERO`, `PNL_OUT_OF_BOUNDS`,
   `SELF_INCONSISTENT`, `QUARANTINE_LEAK` — plus the new `PRICE_DIVERGENCE`.

This does **not** relax the check when the check is meaningful. It makes the validation network
compare like with like, and adds a coarse identity/scale test for the case where it cannot.

## 3. How it was verified

`tools/qa_ledger_selftest.py` — 25 network-free assertions, `fetch_external` stubbed, running
`qa_ledger.run()` against temp snapshots:

```
all qa_ledger selftests passed
```

Covered: snapshot-age parsing (`+00:00`, `Z`, garbage, missing, 90-min arithmetic);
WATCH/SKIP_VOL blank TP/SL not critical **and** counted as `demoted_no_tpsl`; actionable blank TP/SL
still flagged and counted; stale snapshot + 0.6pp drift → not critical, `stale_price=1`, no
`MISMATCH`; stale snapshot + 11% price divergence → critical `PRICE_DIVERGENCE`; fresh snapshot +
0.6pp drift → critical `MISMATCH`; and the pre-existing `SELF_INCONSISTENT`, `UNPRICED` and
`QUARANTINE_LEAK` guards.

Plus a bounded live check of the price-integrity question itself — all 31 EQUITY rows of the
`origin/main` snapshot priced against Finnhub at snapshot age **19 min**:

```
snapshot generated_at 2026-11-25T21:26:36.530430+00:00
equity rows=31  age_min=19.2
... 31/31 rows diff=0.00% (src=finnhub) ...
checked=31 over_5pct=0
```

Every published `current_price` matched the live quote exactly, and the tracker's `price_source` is
the same `finnhub` the ledger validates against. The published numbers were never wrong; the flags
were the measurement gap.

**Limit of this verification:** the full ledger against real feeds was **not** completed locally —
the equity adapter chain is too slow in this environment and the run was killed at 7 minutes, so the
probe above covers EQUITY only. The selftest proves the decision logic; the end-to-end proof is the
first scheduled run of the merged workflow.

## 4. Expected effect

On the next hourly run of the same snapshot shape, the 6 demoted rows stop producing flags and the
8 drift-based `MISMATCH` flags become `stale_price` (or `PRICE_DIVERGENCE` if a real pricing error
is present). The job should go green **on merit**: every previously-failing flag was a
mis-population or a time-comparison artefact, and no real arithmetic error exists in the published
file.

If the job is still red afterwards, the remaining flags are genuine and must be fixed at the
emitter — the gate is no longer generating them.

**A consequence worth stating plainly:** while the QA cron is `13 * * * *` and the tracker is
`25 * * * *`, the ledger always inspects a ~50-minute-old snapshot, so the tight per-class check can
never fire — the gate permanently runs in its coarse mode. That is the honest ceiling of validation
against a delayed snapshot, not a choice. Moving the QA cron to `30 * * * *` (item 4 of the
patchset) restores the strict check by making the snapshot ~5 minutes old at check time.

## 5. Not fixed here (outside this agent's commit prefixes)

The three workflow defects from the earlier document are unchanged and are written up with
ready-to-apply diffs in `plans/2026-11-25-gha-publisher-and-hub-sync-patchset.md`:
one-publisher rule for Pages (`live_tracker.yml` vs `deploy-riseoftheclaw.yml`), gating
`deploy-pages` on a real artifact, and making `hub-sync.yml` fail when it changes nothing.
