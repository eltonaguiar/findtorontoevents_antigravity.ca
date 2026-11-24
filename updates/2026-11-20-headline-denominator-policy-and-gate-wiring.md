# Headline denominator, asset-class ruling, and a correction about gate wiring

**Date:** 2026-11-20 · **Author:** buffy (freebuff-deepseek-v4-flash)
**Scope:** three queued items from the profit-program todo ledger (P0.11, the meme/penny
question, gate wiring) plus one self-correction.

## 1. P0.11 — the headline now publishes its denominator

**Broken:** `/audit` computed `overall_win_rate` and `profit_factor` on
`wins + losses + flat` and rendered them with no indication of that basis, while **11,251 of
19,170 closed picks (58.7%)** sat outside the number. The same payload also carried three
different total-PnL conventions (`total_pnl_pct`, `_sum_raw`, `_compounded_ew`) without saying
which was canonical.

**Changed:**
- `audit_trail/headline_basis.py` (new) — one function owning the arithmetic:
  `headline_denominator`, `headline_covers_closed_pct`, `closed_excluded_from_headline`,
  `excluded_closed`, `zero_pnl_share_pct`, `headline_basis` (plain-English label).
- `audit_trail/dashboard_generator.py` — summary block now spreads `**_headline_basis(...)`;
  import is dual-mode (package and direct-script) so `python audit_trail/dashboard_generator.py`
  keeps working.
- `audit_dashboard/template.html` — the Win Rate card renders
  `(7,919 scored, 11,251 excluded)` and its tooltip carries the flat share.

**Verified:** helper arithmetic on the real numbers (7,919 / 11,251 / 41.31% / 1.79% flat);
`py_compile` clean; 6 tests green in `tests/test_profit_program_policies_2026_11_20.py`.

**Not verified:** the generator was not re-run (34 MB payload build), so the rendered page has
not been visually checked; the next cron build is the first real render.

## 2. Memecoin and penny stocks — settled, explicitly

Grok recommends excluding them from every production universe; the registry carried nine live
entries. Ruling recorded in `reports/policy_asset_class_exclusions_2026-11-20.json`:

**`RESEARCH_ONLY`** — the nine hypotheses stay registered (M-107 requires the trial record to
survive) but are not production-eligible: no promotion, no sizing, no live scanner universe.
Reversal requires a survivorship-free point-in-time universe *and* a pre-registered hypothesis
clearing the full gate.

Rationale: MEME n=10 PF 0.023 (worst cell in the book); PENNY n=4 with spreads exceeding the
median target move; no delisted-inclusive universe, so every backtest is flattered.

**Enforced:** `test_policy_covers_every_live_entry` fails when a new MEME/PENNY/CHEAP entry
appears without a ruling. The decision can't rot silently.

## 3. Correction — the promotion gates were already wired

My review `GROK_REVIEW_ROUND2_VALIDATION_2026-11-20_freebuff.md` marked CPCV/PBO as
"wired into promotion? **No**". That was wrong, and based on a grep that did not follow call
sites:

- `alpha_engine/money_ready_verdict.py:1677` computes `_dsr_gate(returns)`
- `:1678` computes `_pbo_gate(ac_picks)`
- `:1679` computes `_spa_gate(ac_picks)`
- all three are passed into `_verdict(...)`, which requires `(dsr_ok or spa_ok)` **and**
  `(pbo_ok or spa_ok)` before returning `MONEY_READY`.

So the gates exist *and* are enforced on the promotion path. What is genuinely missing is the
global trial count (`n_trials` is per-run, P0.5) and coverage of the other `/audit` producers —
not wiring.

**Newly documented behaviour (found while writing the test):** a class failing DSR and PBO with
PF ≥ 1 returns **`WATCH`**, not `NOT_READY`. That is correct — WATCH is "unproven near-miss",
not promotion — but it was implicit and is now asserted in
`test_verdict_requires_dsr_and_pbo` so a future refactor cannot hide it either way.

## 4. Tests

```
python3 -m pytest tests/test_profit_program_policies_2026_11_20.py -q
6 passed
```

Covers: helper arithmetic, degenerate/negative inputs, generator integration string, policy
coverage of every live entry, and the gate matrix (good/bad/neutral × DSR/PBO/SPA, PF<1 hard route).
