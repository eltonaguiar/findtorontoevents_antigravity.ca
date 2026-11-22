# H-150 backtest + audit2/audit3 proof-surface decision

**Date:** 2026-11-22
**Files added:** `tools/h150_gpa_backtest.py`, `tools/lms_consult.py`, `reports/2026-11-22-h150-backtest-result.md`,
`reports/2026-11-22-audit2-vs-audit3-forward-test-decision.md`,
`plans/2026-11-22-h149-h150-forward-proof-plan.md`,
`reports/h150_gpa_backtest_2026-11-22.json`, `reports/h150_gpa_backtest_2026-11-22_w60.json`, `reports/h150_ttm_validation_full.json`
**Files changed:** `reports/hypothesis_registry.json` (H-150 status + result)

## What was broken / missing

1. H-150 was `PRE-REGISTERED` with the signal validated but **the backtest unrun**, so the
   registry carried a live hypothesis with no verdict — the state that invites a later,
   looser run to be treated as the first one.
2. TTM validation rested on 30 companies with comparable pairs (250-filer sample). Too narrow
   to claim the construction holds.
3. No surface was designated for forward-testing a backtest-proven strategy. `/audit2` and
   `/audit3` both existed; neither had been chosen, and audit2's forward clock could not
   promote anything.

## What changed

- `tools/h150_gpa_backtest.py`: the frozen H-150 spec — SEC filers seed 149, cap $2B–$10B,
  top quintile z ≥ 0.8416, **next-session-open** entry, exit at the first month-end ≥ 20 and
  ≤ 60 calendar days, 20 bp round-trip with 2× stress, FF4 regression, unmodified
  `edge_stability_harness`. Emits a five-gate verdict; the harness import is the same
  file-path import H-149 uses, and `--self-check` asserts the published thresholds.
- Full-sample TTM validation (`--sample-n 2600`): **2,427 pairs / 984 companies, 92.95 % within
  1 %** of the audited 10-K figure, 95.51 % within 5 %, median rel err 0.0, p90 0.00095.
- Decision memo: `/audit3` is the proof surface (`forward_gate_block` is the only enforced
  promotion rule and it consumes audit2's pod manifest as input); `/audit2` is registration and
  display only.
- Plan for the remaining workstreams, including the delisted-price blocker.

## Result

H-150: **NOT_PROVEN** on 4,753 records / 817 book records / 119 formations.
Book net +0.7318 % vs universe +0.7217 %; bottom quintile +1.1894 % → L/S **−0.4576 %**;
FF4 alpha **−0.6903 %/mo, t = −1.41**, R² 0.721, MKT 1.28, **SMB 1.004**.
The harness is `UNTESTED` at the 14-day window because ~18 records per window is below its
80-record floor — reported as untestable, not as a pass.

## How verified

- `python3 tools/h150_gpa_backtest.py --self-check` → `unmodified: true`, thresholds
  `EFF_MIN=0.3 / MIN_WINDOW_N=80 / MIN_STABLE_WINDOWS=3`.
- `py_compile` on the new module; full run completed end-to-end and wrote its artifact.
- Registry parses under the strict duplicate-key guard; H-150 slice edited by targeted text
  replacement, not a whole-file re-serialisation, and the result block verified present exactly
  once.
- `pytest tests/test_registry_duplicate_keys.py tests/test_hypothesis_status.py` → see commit.

## Operational note

`FMP_API_KEY` in `~/dbpasses.txt` is a **dead credential** (HTTP 401 on `stable/`, 403 on
`v3/`), so the delisted-ticker route stays open only with a new vendor key (Polygon, Tiingo or
CRSP/WRDS). No secret values were printed or committed — only key names and status codes.

## Correction (same day, after review)

`factor_fit()` reported an information ratio of −0.0 by averaging the OLS residuals. With an
intercept in the fit that mean is exactly zero, so the number could not move and the gate could
never read true or false on evidence. It is now an **appraisal ratio** (-0.524, = monthly alpha
/ sd(FF4 residuals) × √12) plus a model-free **book-vs-universe IR** (-0.003); tracking error
4.5618 %/mo. Both artifacts were regenerated, every other number reproduced exactly, and the
verdict stayed NOT_PROVEN.

`tools/lms_consult.py` was added to query the LAN LM Studio box (11 models, `--list`, single or
fan-out, OpenAI-compatible with the native endpoint as fallback). Two models reviewed this
backtest; every specific finding they raised was wrong, and neither caught the IR defect. The
client is kept because the fan-out is useful for cheap second opinions, with the caveat that
these models need state-verifiable prompts and their claims must be checked against the code.
