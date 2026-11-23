# conftest's high-VIX fix was a no-op: it set the wrong env var name

**Date:** 2026-11-23
**Branch:** `copilot/hub-audit-2026-11-23`

## What was broken

`tests/conftest.py` carried a documented fix for tests going red on high-VIX days:

```python
# Per-class hard VIX gates (2026-05-28) ... Tests that fixture EQUITY picks for
# OTHER gates therefore go red on any high-VIX day ... on 2026-11-16 VIX was
# 23.96 and main's CI Tests failed 14 gate tests ...
os.environ.setdefault("EQUITY_VIX_GATE_ENABLED", "0")
os.environ.setdefault("ETF_VIX_GATE_ENABLED", "0")
```

It never worked for ETFs. `ETF_VIX_GATE_ENABLED` is read by the *per-class* gate
(`audit_trail/quality_gates.py` ~6440), but **M-098 "etf_vix_gate"** (~9246) —
which fires at VIX ≥ 25 — reads a **different** set of names:
`ETF_VIX_GATE_DISABLED`, `ETF_VIX_GATE`, `ETF_VIX_GATE_THRESHOLD`,
`ETF_VIX_GATE_ENFORCE`.

So on 2026-11-23 (VIX > 25) M-098 still enforced and rejected every ETF pick in
the test fixtures.

## How it was found

`tests/test_etf_iwm_gld_kill.py::test_active_gate_allows_sector_and_broad_etfs`
failed with `assert False is True` and **no** `_hf_quality_gate_reason` marker, so
no named gate was admitting to the rejection. Ran with `--log-cli-level=INFO` —
nothing logged. Traced `passes_active_gate` with `sys.settrace` and caught the
return event:

```
DIAG result= False return-line(s)= [(9280, False)]
DIAG 9275: if _m098_enforce:
DIAG 9280:     return False
```

Line 9280 is M-098. The rejection also appended to
`reports/etf_vix_gate_log.jsonl` on every call — matching the test-pollution noise
seen on every suite run.

## What changed

One line added to `tests/conftest.py`:

```python
os.environ.setdefault("ETF_VIX_GATE_DISABLED", "1")
```

Plus a comment recording the name mismatch and why this is the right layer.

## Why this is a fix and not a weakened test

- `conftest.py`'s **stated intent** was already to neutralise network-VIX gates so
  gate tests measure gate logic rather than today's volatility. This sets the name
  the code actually reads — the intent is unchanged.
- `tests/test_m098_etf_vix_gate.py` re-enables the gate in its own fixture via
  `monkeypatch.setenv("ETF_VIX_GATE_DISABLED", "0")`, which overrides `setdefault`.
  Its **10 tests still pass**, including the explicit
  `ETF_VIX_GATE_DISABLED=1 skips the gate entirely` case.
- `test_m001_cot_stale_gate.py:64` and `test_m002_ctf_weekly_cap.py:78` already set
  `ETF_VIX_GATE_DISABLED=1` by hand — two independent test authors hit this exact
  problem and worked around it per-file. This centralises the same fix.

## Verification

Full suite, same invocation as CI (dirs + `-m "not integration and not network"`):

| | failed | passed | skipped |
|---|---|---|---|
| before | 24 | 7735 | 51 |
| after | **13** | **7746** | 51 |

Failure-set diff: **11 fixed, 0 new failures**. All 11 fixed are ETF:
7 × `test_etf_iwm_gld_kill`, 3 × `test_p1_gates_etf_tight_crypto_consensus`,
1 × `test_trust_tier_non_crypto_default_on`.

`tests/test_m098_etf_vix_gate.py`: **10 passed** (switch override intact).

## What this does NOT fix

13 pre-existing failures remain, each with a distinct non-VIX cause and needing a
domain decision rather than a mechanical edit:

- `test_m096_ctf_concentration_cap` (4) — blocked by `emitter_registry_gate
  toxic_pair:COMMODITY/multi_asset_cot`. Deciding whether that pair is *genuinely*
  toxic is an owner call; the registry has no env kill-switch.
- `test_equity_pead_strategy` (2) — signal counts 0 vs expected 1/3.
- `test_kimi_promotion_unblock` (2) — EQUITY picks blocked by another gate.
- `test_eagle2_phase0_gates` (1) — expected asset×strategy pair absent from the
  emitted set.
- `test_m001_cot_stale_gate` (1), `test_meta_effectiveness` (1),
  `test_ns_c_e_exec_gate_filters` (1), `test_pf_registry_tournament_db` (1).

All 13 are in CI's 69-entry known-drift quarantine, i.e. red on `main` too.
