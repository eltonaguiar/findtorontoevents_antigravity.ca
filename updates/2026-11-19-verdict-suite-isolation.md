# Verdict suite green again, and leaked keys redacted (2026-11-19)

## 1. Why 7 `test_money_ready_verdict.py` tests were failing

They were not one bug, and they were not caused by #904 either. Instrumenting the
high-edge fixture (400 wins at +5%, 100 losses at -2%, COMMODITY) showed:

```
n=500  wr=0.8  pf=9.21  n_ok=True  wr_ok=True  pf_ok=True  dsr_ok=True  spa_ok=True
top_symbol_share=0.2   top_source_share=1.0   source_concentration_capped=True
_verdict(all gates ok) -> MONEY_READY
_verdict(recency unknown) -> NOT_READY
```

Two fixture gaps, both of which the verdict is *right* to act on:

1. **`source_system` was a single value for every pick.** COMMODITY's source cap is
   0.60, so a 100%-single-source class is capped — exactly the behaviour that stops
   one feed from promoting a class. The fixture now spreads over three sources by
   default (tests that specifically exercise the cap still pass one source).
2. **No `closed_at`.** `_recency_gate` returns `None` when it cannot date the
   sample, and `_verdict` treats unknown recency as `NOT_READY`. Every synthetic row
   now carries a timestamp inside the recency window.

`_verdict()` itself was never at fault: called with every gate ok it returns
`MONEY_READY`, and with `recency_ok=None` it returns `NOT_READY`. Both correct.

The autouse fixture also holds `_FDR_GATE_ENFORCE` and `_SINGLE_SOURCE_GATE_ENFORCE`
in shadow, because every fixture here is one strategy and these tests cover
concentration, WR floors and ML quarantine — not those two gates, whose real
coverage is `tests/test_money_ready_fdr_gate.py`. No assertion was weakened; the
fixtures just stopped failing a gate they never intended to exercise.

## 2. Leaked keys found in tracked files

Scanning every tracked text file for credential shapes turned up real-looking
`sk-` API keys in **three committed files**:

* `reports/session_action_scan_2026-05-17.md`
* `reports/transcript_scan_CE_2026_05_18.md`
* `.env.example` (three values, all real-looking rather than placeholders)

All are now `sk-<REDACTED>`, and a re-scan reports **0 tracked files** holding a
real-looking `sk-` key. Two things remain outside what a redaction can fix:

* **The values are still in git history.** They must be rotated; editing the file
  removes them from `HEAD`, not from clones.
* `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js:49` contains a Google API key
  (`AIza…`, 39 chars) in client-side JavaScript. Client keys are often intended to
  be public, but they must be restricted by HTTP referrer in the Cloud console —
  otherwise anyone can spend the quota. Left in place because removing it would
  break the page; flagged for restriction.

The DB hostname `mysql.50webs.com` appears in 383 tracked files (skills, docs,
scripts) and `dbpasses.txt` is referenced in 186. Neither is a credential, but on a
public repository they are useful reconnaissance: they tell someone where to point
a password spray. Worth removing from prose over time; not done here because it
would touch unrelated documentation.

## Verification

* `pytest tests/test_money_ready_verdict.py` — see commit; the 7 are green with the
  fixtures fixed and no assertion changed.
* `pytest tests/test_money_ready_wr_semantics.py tests/test_money_ready_fdr_gate.py
  tests/test_audit3_cost_basis.py tests/test_resolved_closed_view.py
  tests/test_per_class_cost_gate.py` — 47 passed.
* `pytest tests/test_audit3_{enforcement,coverage_alpha,tribunal}.py` — 39 passed.
* Post-redaction secret scan — 0 real-looking `sk-` keys in tracked files.
