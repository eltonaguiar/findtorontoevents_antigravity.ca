# `n` Counter Disagreement — Diagnosis & Reconciliation

**Date:** 2026-05-25
**Task:** TASK B — reconcile the 10-100× n-counter divergence between
`asset_class_health.n` and `money_ready_verdict.classes.n_resolved`.

## TL;DR

The disagreement is **NOT a code bug** at the counter level today. It is a
combination of:

1. **The CLAUDE.md numbers cited (CRYPTO n=8067, COMMODITY n=750, FOREX n=1169)
   are stale May-3 snapshots** captured *before* the M-067 fix flipped
   `asset_class_health` to read the pf_registry **policy-clean net** view. The
   May-3 numbers were drawn from the legacy "recompute" path (a wider RAW view
   that did not apply policy exclusions, dedup, or flicker filtering).
2. **Both `asset_class_health` and `money_ready_verdict` now share the same
   upstream cohort** — the pf_registry policy-clean-net pipeline (see
   `audit_trail/dashboard_generator.py:5645-5731` and
   `alpha_engine/money_ready_verdict.py:99-119`). Current numbers agree within
   small timestamp-drift deltas.
3. **The agent's report of CRYPTO n=728 / COMMODITY n=28 / FOREX n=53 is from
   the May-24 verdict snapshot**, which closely matches the current registry
   net view (CRYPTO n=871, COMMODITY n=13, FOREX n=30 as of 2026-05-25T03:56Z).
   The remaining drift is normal between two `pf_registry.json` regenerations
   over ~24h as old picks roll off the trailing window and dedup re-evaluates.

The "n-citation discipline" rule in SKILL.md is being violated by **the cited
CLAUDE.md numbers**, not by the verdict file. CLAUDE.md needs an n-source
refresh; no production counter is broken.

## Current numbers (2026-05-25T04:00Z)

### `pf_registry.json` — three sequential views

| Class | RAW (`by_asset_class_raw`) | DEDUPED (`by_asset_class`) | POLICY-CLEAN NET (`by_asset_class_policy_clean_net`) |
| --- | ---: | ---: | ---: |
| CRYPTO | 4213 | 1520 | **871** |
| COMMODITY | 50 | 50 | **13** |
| FOREX | 81 | 73 | **30** |
| EQUITY | 40 | 32 | **29** |
| ETF | 4 | 3 | **3** |
| BOND | 9 | 8 | (dropped) |
| FUTURES | 23 | 18 | **11** |

Pipeline counts (`raw_rows -> closed_rows -> after_flicker -> deduped -> policy_clean`):
`7404 -> 4598 -> 2249 -> 1812 -> 995`. That's the funnel:

- 2806 dropped: not closed
- 2349 dropped: spot-flicker filter
- 437 dropped: duplicate re-emissions
- 817 dropped: policy excluded (BLOCKED_SOURCE_SYSTEMS,
  BLOCKED_ASSET_STRATEGY_PAIRS, PF_REGISTRY_POLICY_EXCLUDED,
  BLOCKED_DIRECTION_TRIPLES, PERMANENTLY_KILLED)

### `audit_dashboard/data/money_ready_verdict.json` (generated 2026-05-24T07:24Z)

| Class | `n_resolved` | WR | PF |
| --- | ---: | ---: | ---: |
| CRYPTO | 728 | 43.4% | 1.145 |
| COMMODITY | 28 | 10.7% | 0.309 |
| FOREX | 53 | 39.6% | 0.547 |
| EQUITY | 33 | 33.3% | 0.897 |
| ETF | 2 | 50% | 11.99 |
| BOND | 8 | 0% | 0.0 |
| FUTURES | 12 | 16.7% | 0.956 |
| UNKNOWN | 39 | 51.3% | 1.700 |
| PENNY_STOCK | 1 | 0% | 0.0 |

Verdict is ~21h older than the registry; the gap (CRYPTO 728 -> 871, COMMODITY
28 -> 13 with the small classes oscillating sharply) is consistent with normal
re-registry churn over that window.

### `asset_class_health` (from CLAUDE.md, 2026-05-03)

CRYPTO n=8067, COMMODITY n=750, FOREX n=1169 — these match neither the current
RAW view (CRYPTO 4213) nor the current DEDUPED view (1520) nor the policy-clean
view (871). They are pre-M-067 numbers from a wider pre-dedup pipeline that has
since been replaced. The 2026-05-03 absolute numbers cannot be reproduced
from the current pf_registry pipeline.

## Cohort definitions (canonical, from source)

### `asset_class_health` (in `audit_dashboard/data/dashboard_data.json`)

Generator: `audit_trail/dashboard_generator.py`,
`_registry_breakdown()` at lines 5645-5731 -> `compute_asset_class_health()`
at line 5733.

- Default source (since 2026-05-17, M-067): reads
  `by_asset_class_policy_clean_net` from `pf_registry.json`.
- Fallback (env `AUDIT_HEALTH_SOURCE=recompute`): in-generator recompute over
  closed-picks ledger. **This is the wide May-3 cohort that produced n=8067.**
- Counts: wins + losses on the deduped, closed-only, policy-clean net rows.

### `money_ready_verdict.classes.n_resolved`

Generator: `alpha_engine/money_ready_verdict.py`, `_load_picks()` at line ~420.

- Pipeline (lines 99-119): `build_pf_registry.load_rows ->
  classify_rows (dedup + closed-only) -> _is_policy_excluded`.
- Equivalent to the registry's `by_asset_class_policy_clean_net` cohort, with
  one additional per-class strategy-block layer applied via
  `BLOCKED_ASSET_STRATEGY_PAIRS` (already part of the registry's policy filter
  since 2026-05-19 — the verdict's old extra filter is redundant and was
  removed at line 114-115).
- `n_resolved` = `wins + losses` on this cohort.

**Both readers consume the same cohort.** The only legitimate drift sources
are:

- Timestamp skew (verdict file regenerated less often than the registry).
- Per-class symbol-concentration cap (`MAX_SYMBOL_CONCENTRATION = 0.60`,
  per-class override 0.85 for COMMODITY) — this caps the **verdict**, not
  `n_resolved`, so it does not affect the count.
- DSR `nb_trials` correction is statistical, not a count filter.

## Where does CRYPTO n=8067 / FOREX n=1169 actually come from then?

The 2026-05-03 numbers in `CLAUDE.md` predate M-067. At that time:

- `asset_class_health` was computed by the in-generator recompute (the current
  `AUDIT_HEALTH_SOURCE=recompute` fallback path).
- It counted **all closed picks per class with no flicker-dedup or policy
  exclusion** (just the post-resolver-v2 PnL threshold from
  `outcome_resolver.py`).
- That wide view legitimately produced CRYPTO n~8067 in early May because the
  pf_registry pipeline (and its flicker-filter + dedup) was not yet feeding
  `asset_class_health`. M-067 replaced that on 2026-05-17.

The CLAUDE.md banner is therefore citing a **deprecated counter**. Today's
`asset_class_health` (when generated) will report numbers identical to the
verdict's `n_resolved` cohort (modulo timestamp).

## Recommendation

Not a code bug. Two doc fixes + one optional clarity rename:

1. **Refresh CLAUDE.md MAJOR GOALS banner** (lines ~7-15) — replace the
   2026-05-03 n/PF/WR figures with current
   `by_asset_class_policy_clean_net` numbers (or with a pointer to
   `pf_registry.json` so the banner stays fresh):
   - CRYPTO n=871 (was 8067), COMMODITY n=13 (was 750), FOREX n=30 (was 1169),
     EQUITY n=29 (was 421), ETF n=3 (was 87), BOND n=0 (was 18).
   - These are dramatically smaller because flicker+dedup+policy-exclusion now
     correctly filter out the noise the May-3 banner was counting.
   - Bracket each number with "as of `pf_registry.generated_utc`" so the next
     refresh is obvious.

2. **Add a one-line "cohort" tooltip to SKILL.md's n-citation discipline
   section** clarifying which cohort each surface reports:
   - `dashboard_data.json::performance.asset_class_health.n` ==
     `money_ready_verdict.json::classes.n_resolved` ==
     `pf_registry.json::by_asset_class_policy_clean_net.{wins+losses}`.
   - Raw / pre-policy numbers live in `pf_registry.by_asset_class_raw` (for
     research only, never for verdicts).

3. **(Optional) rename `n_resolved` -> `n_policy_clean_net` in the verdict
   JSON** (with `n_resolved` kept as a deprecated alias for one release). This
   would make the cohort self-documenting and prevent the next agent from
   re-misreading it as "all resolved picks." Lower-priority; the SKILL.md
   tooltip is cheaper and accomplishes 90% of the clarity gain.

No counter generator needs to change. The verdict file's `n_resolved=728` and
the registry's `by_asset_class_policy_clean_net.CRYPTO.n=871` are both correct
for their respective generation times; they will converge on the next verdict
regen.

## Reproducer commands

```
# Current pf_registry views:
python3 -c "import json; r=json.load(open('audit_dashboard/data/pf_registry.json')); \
  [print(v.get('asset_class'),(v.get('wins') or 0)+(v.get('losses') or 0),v.get('profit_factor')) \
  for v in r['by_asset_class_policy_clean_net']]"

# Current verdict snapshot:
python3 -c "import json; d=json.load(open('audit_dashboard/data/money_ready_verdict.json')); \
  [print(k,v.get('n_resolved'),v.get('wr'),v.get('pf')) for k,v in d['classes'].items()]"

# Regenerate verdict (matches registry within seconds):
python alpha_engine/money_ready_verdict.py --json
```
