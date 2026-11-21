# SubQ (savant-1.4) review of the gate hardening — five real defects fixed

Date: 2026-11-21. Scope: the artifacts from #1036–#1039 — the hybrid gate's
committed sidecar, the QA ledger's quarantine/self-consistency rules, the
tracker's FX cross-check, and the `anti_overfit.html` coverage panel.

## Why a second reviewer

Every one of those changes was green and every one was mine. A passing gate is
not the same as a correct gate, and the failure modes here are quiet ones: a
count field nobody reconciles, a fallback that looks protective and isn't, a
report that rotates its own history away. `subq-savant-1.4` (OpenAI-compatible
surface at `api.subq.ai/v1/chat/completions`, key resolved by
`tools/subq_consult.resolve_key`) was given the real files and asked for
line-anchored findings. Three parallel reviews ran; each finding below was
re-checked against the source before it was accepted, and one was rejected.

## Accepted and fixed

| # | Defect | Where | Fix |
|---|--------|-------|-----|
| 1 | `float(entry)` / `float(ext)` were unguarded in the market-data cross-check, so a row with `entry_price: null` and a live quote raised *before* `OUT_JSON` was written. The job died and the committed artifact stayed stale — the exact silent-staleness class this gate exists to catch. | `tools/qa_ledger.py` step 5 | coerce in a `try/except (TypeError, ValueError): continue`, then use the coerced values |
| 2 | The FX override preferred the failover feed on *any* gap > 0.25%. A gap proves only that the feeds disagree: an inverted or differently-mapped failover quote produces a huge gap, so the path meant to protect against a frozen tick was also the path that could publish a ~-99% PnL. | `tools/live_pnl_tracker.py` | override only inside the plausible band (0.25% < drift ≤ 5%); a wider gap keeps yfinance, logs both prices with the failover/yfinance ratio, and is left to the ledger's `MISMATCH` check |
| 3 | FOREX rows are priced by `alpha_engine.forex_price_failover` and validated against the same module, so `diff` is 0 by construction — a permanent false negative for the whole class. | `tools/qa_ledger.py` | new non-critical `unverified_source` counter, printed as `samefeed=N`. Not a flag: all 23 FOREX rows are priced this way, so flagging would be red every run |
| 4 | `record()` filtered the keyed entry out and appended it, so a retry moved an old entry to the end (it then looked newest to the panel) and, at the 50-entry cap, evicted one more historical entry per retry. | `tools/detect_merge_hybrid.py` | replace in place; evict only when an entry is actually appended |
| 5 | A file that was opened but failed to parse incremented `findings` yet was appended to neither `inspected_paths` nor `skipped`, so a `hybridised` verdict named no culprit. An unreadable report was also replaced with an empty one, silently. | `tools/detect_merge_hybrid.py` | count and name the path before parsing; warn on stderr when the report itself is unreadable |
| 6 | `--under .` became `./` and matched nothing; `--under foo` also missed a prefix naming a file exactly. | `tools/detect_merge_hybrid.py` | normalise both sides; `.`/empty means the whole tree |
| 7 | The panel's "last clean run" mixed phases, so a clean `staged` pass (46) sat beside a newer `rev-range` pass (1) and read as a regression. Its fetch-error text also asserted a cause it cannot know. | `audit_dashboard/anti_overfit.html` | the KPI is phase-labelled and only compares within the newest entry's phase; the error text reports the actual failure |

## Rejected

**"`f"{sym}=X"` is wrong for USD-prefixed pairs."** yfinance quotes `USDJPY=X`
and returns data for it — the frozen-JPY evidence that started this thread
(`159.707` served for two hours) is itself a yfinance price from that symbol.
Changing it would have replaced a working lookup with a guess.

## Verification

- `pytest tests/test_detect_merge_hybrid.py tests/test_qa_ledger_rules.py tests/test_live_pnl_fx_drift.py` → **40 passed** (17 new: `--under` normalisation, retry-at-cap, unparseable-path naming, null entry price, same-feed counter, four FX drift-band cases).
- Inline panel script extracted and `node --check`ed → clean.
- The gate still produces **0 critical** on the live artifact (183 picks), so none of the new rules is a false positive.

## Residual, not fixed here

- The tracker's FX override has no third signal for "which feed is stale"; the
  bound stops the catastrophic case, not the subtle one. A stored previous
  `current_price` would distinguish a frozen leg from a mapping error.
- `inspected_paths: []` on an entry cannot be told from "paths were rotated
  away" except by the count.
