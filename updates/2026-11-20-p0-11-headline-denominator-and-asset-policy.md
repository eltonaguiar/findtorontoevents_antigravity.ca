# P0.11 — headline denominator published; memecoin/penny ruling; promotion gates verified

**Date:** 2026-11-20 · **Author:** Buffy (freebuff-deepseek-v4-flash)
**Scope:** three follow-ups from the Grok/Subq review series, plus one self-correction.

## 1. What was broken

`/audit` rendered a headline win rate (44.1%) and profit factor (1.12) without stating the
denominator, while the payload carried a **much larger** closed population:

```
summed closed_picks            19,170
summary wins + losses           7,919   -> headline covers 41.31%
closed excluded from headline  11,251   -> 58.69% invisible
summed zero_pnl                   142   -> 1.79% of the headline denominator
```

A reader could not tell that 59% of the closed book was outside the number they were reading.
This is the same defect class as `policy_clean_*` and the gross/net PF confusion: a statistic
without its population.

## 2. What changed

- **`audit_trail/headline_basis.py`** (new): single source of the denominator arithmetic.
  Returns `headline_denominator`, `headline_covers_closed_pct`, `closed_excluded_from_headline`,
  `excluded_closed`, `zero_pnl_share_pct`, and a plain-language `headline_basis` string.
  Degenerate inputs are safe (`0/0 -> None`, never a ZeroDivisionError; resolved > closed clamps
  excluded to 0).
- **`audit_trail/dashboard_generator.py`**: summary now spreads that block, so every consumer of
  `dashboard_data.json` receives the denominator rather than having to reconstruct it.
  Import is dual-mode (`audit_trail.headline_basis` with a direct-script fallback), because this
  file is also run as `python audit_trail/dashboard_generator.py`.
- **`audit_dashboard/template.html`**: the Win Rate card now renders `(N scored, M excluded)` and
  its tooltip states scored count, excluded count and flat share.
- **`tests/test_profit_program_policies_2026_11_20.py`**: 6 tests — arithmetic on the real numbers,
  degenerate cases, a guard that the generator still calls the helper, policy coverage, and the
  promotion-gate contract.

## 3. Memecoin / penny-stock ruling — settled, not drifted

Grok recommends excluding these from every production universe; the registry holds **nine** live
entries in those classes. Rather than delete trial records (which M-107 forbids) or leave the
contradiction standing, the decision is now explicit and machine-readable:

**`reports/policy_asset_class_exclusions_2026-11-20.json` → `RESEARCH_ONLY`.**
The nine hypotheses stay registered as the record of what was tried, but are **not
production-eligible**: no promotion, no sizing, no live scanner universe. Reversal requires a
survivorship-free point-in-time universe *and* a pre-registered hypothesis clearing the full gate
(forward n ≥ 200, net CI > 0 at 2× cost, DSR ≥ 0.95).

Rationale measured, not asserted: MEME n=10 / PF 0.023 is the worst cell in the class-divergence
audit; penny spreads exceed the median target move at any size we can trade; and no
survivorship-free delisted dataset exists, so every backtest on those universes is flattered.

The test `test_policy_covers_every_live_entry` fails if a **new** meme/penny/cheap hypothesis is
registered without an explicit ruling — so the policy cannot silently rot.

## 4. Promotion gates — verified wired, and a correction to my own review

My round-2 review said CPCV/PBO were "not wired into promotion." **That was wrong.** The call
path is:

```
money_ready_verdict()  ->  _dsr_gate(returns)          (alpha_engine.deflated_sharpe)
                           _pbo_gate(ac_picks)          (tools.pbo_cscv.compute_pbo)
                           _spa_gate(ac_picks)
                       ->  _verdict(n, wr, pf, dsr, pbo, spa, ...)
```

and `_verdict()` requires `(dsr_ok or spa_ok)` **and** `(pbo_ok or spa_ok)` before `MONEY_READY`
can be returned (`alpha_engine/money_ready_verdict.py:1299-1372`). A failed multiplicity gate can
never promote; with WR/PF above their floors it degrades to `WATCH`, and a losing book is
`NOT_READY`.

The new test pins that contract in both directions, including the case that matters most:
**unknown is not permission** (`{"ok": None}` gates must not yield `MONEY_READY`).

What genuinely remains open is narrower than the review claimed: `n_trials` is still computed from
cells in one run rather than a global counter (P0.5), and the audit3 PBO path is separate from the
money-ready path. Both are tracked; neither is "unwired."

## 5. Peer feedback adopted (COMS)

- **Captured vs full reversion.** The H-146 cost comparison used `|s| * sigma_eq` (full reversion)
  against cost while the exit is at `|s| = 0.5`, so only `(|s| - 0.5)/|s| = 60%` of the distance is
  captured at `|s| = 1.25`. The margin was overstated by ~67%. The gated-vs-ungated comparison must
  use captured reversion.
- **Fold independence.** Contiguous quintiles are not independent draws; "3 of 5 folds below 0.2"
  is a diagnostic, not a binomial test. The aggregate CI `[−0.295, +0.731]` is the robust result,
  and purging can only widen it, so the NOT SUPPORTED conclusion stands.
- **Regime question.** "Did the 65% time-cap exits cluster in a regime?" is **currently
  untestable** — trade rows carry no `regime_at_entry`. Adding that stamp is the precondition for
  answering it, and it is worth doing before treating the time-cap rate as a structural finding.

## 6. Verification

```bash
python3 -m pytest tests/test_profit_program_policies_2026_11_20.py -q      # 6 passed
python3 -c "import py_compile;py_compile.compile('audit_trail/dashboard_generator.py',doraise=True)"
python3 -c "import json;print(json.load(open('reports/policy_asset_class_exclusions_2026-11-20.json'))['ruling'])"
```

Limitation: the payload change takes effect on the next `audit-dashboard` build, so the live page
still shows the old card until then; the test asserts the generator wiring, not a deployed render.
