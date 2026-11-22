# H-151 net share issuance backtest — added and run to a verdict

**What this is.** A new module, `tools/h151_net_issuance.py`, implementing the H-151
spec that was pre-registered earlier the same day in `reports/hypothesis_registry.json`.
Before this change the registry carried the hypothesis with `result: {}` — a claim
with no evidence behind it.

**What it does.** Reads the existing `tools/cache/sec_companyfacts/` cache (no new
downloads for fundamentals), builds `NIS = ln(shares_t / shares_{t-4q})` point-in-time
from filed dates, applies the frozen split guard, forms quintiles, holds bottom long /
top short for one month with next-open entry, and runs the H-149 backtest helpers —
harness, cost model, delisting haircut, FF4 regression — by importing them rather than
reimplementing them. Harness self-check asserts it is unmodified before any test runs.

**Result.** `NOT_PROVEN` with the first refutation condition triggered: the net
long-short spread is **-0.2054 %/month**, FF4 alpha
-0.3567 %/month (t = -0.63), appraisal ratio
-0.199. Registry status moved `PRE_REGISTERED` → `REFUTED`.

**How it was verified.**
- `python3 -m py_compile tools/h151_net_issuance.py` — clean.
- `--self-check` — harness observed thresholds equal the published ones
  (`EFF_MIN 0.3`, `MIN_WINDOW_N 80`, `MIN_STABLE_WINDOWS 3`), `unmodified: true`.
- Full run: 29109 records from 131 formations,
  568 priced names, 52 s wall clock.
- Artifact written and re-read: `reports/h151_net_issuance_2026-11-22.json`.

**Not claimed.** That the issuance effect is absent in the full US universe. Median leg
size is 43 names against a registered 100 minimum and the sample
is the mid-cap-oriented 756-CIK cache, so the sign is trustworthy in-sample and the
magnitude is not portable. Full discussion: `reports/2026-11-22-h151-net-issuance.md`.

**Also in this change.** `TOOLS.md` gains the local fleet map that was verified live
today, including the :8000 vLLM launch (Qwen3.6-35B-A3B-NVFP4) and the reasoning-budget
trap that makes short calls return empty content.
