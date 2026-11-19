# Forward-evidence contract shipped; H-119 registry vintage refreshed (2026-11-19)

## What was broken

External review §5.8, agreed and deferred twice: there is no `forward_observations`
ledger, so audit3 can only re-score history and `PROVEN_T2` from live data is
**undefined**. Three things were missing at once — the row shape, one definition of net
return, and any rule saying how much forward evidence promotes a hypothesis.

Separately, `reports/hypothesis_registry.json` still carried H-119's registration-time
`result` (n=108), i.e. the same stale vintage that #907 fixed on the dashboard card.

## What changed

* `alpha_engine/forward_observations.py` — schema + validator (including the
  `hypothesis_id` → registry FK), one net-return definition, append with idempotent
  dedupe, integrity verifier, per-hypothesis **clock**, and the promotion rule.
* Promotion requires all of: `n_forward >= 100`; net PF CI-LB > 1.0 **or** IR ≥ 0.5;
  `intrabar_first_touch` on 100% of rows; `benchmark_leg_ret` on ≥90%. Excess vs the
  benchmark leg is reported as a descriptor, not gated — no threshold is calibrated yet.
* `reports/forward_observations.jsonl` — created, **0 rows**, on purpose.
* `tests/test_forward_observations.py` — 24 tests, one per clause, so a silently dropped
  gate fails the suite rather than changing a verdict.
* H-119 `result` in the registry gets a dated `2026-11-19 update`: n=431, net PF 1.119
  (CI-LB 0.9158), IS/OOS 1.079/1.157, top-symbol JUPUSDT 5.1%, `min_n=150` MET, only
  `net_ci_lb_gt_1.15` failing. The pre-registered `acceptance_criteria` are left
  untouched — pre-registration is immutable; the *result* is what accrues.
* `docs/FORWARD_LEDGER_CONTRACT_2026-11-19.md` — the contract in one page.

## Verification

* `pytest tests/test_forward_observations.py` — 24 passed
* `--verify` → `n_rows: 0, ok: true, registry_hypotheses: 131`
* `--clock H-119` → `0/100 forward rows, status NO_FORWARD_ROWS`, no invented ETA
* `--promotion H-119` → `eligible=False`, reason `no forward rows — nothing can promote`

## Limitations, stated plainly

* **No ingestion adapter.** The module cannot read MySQL here, so the ledger is empty and
  `PROVEN_T2` remains unreachable from forward evidence. audit3's zero PROVEN verdicts
  are correct until rows exist.
* **audit3 does not yet read the ledger.** Wiring the promotion rule into
  `audit3_tribunal` (so PROVEN_T2 is *gated* on forward rows, not merely defined by them)
  is the next step and is deliberately separate: with 0 rows it would gate nothing today
  but would change verdict logic the moment rows arrive.
* Same-date cluster bootstrap is inherited from `tools/pf_ci_lower.py`; it was not
  re-derived here.
