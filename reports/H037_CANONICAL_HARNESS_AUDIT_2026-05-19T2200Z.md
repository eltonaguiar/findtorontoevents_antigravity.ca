# H-037 audit — canonical-harness clearance check

**TL;DR:** H-037 (VIX term-structure carry) **does NOT pass the unmodified
`tools/edge_stability_harness.py`**. Registry status block claims
`admissible: true` based on a **custom local walk-forward** that does not
match the rule-M-107 pre-registered test_statistic. Canonical verdict =
**UNTESTED (density gap)**, not PASS. The 17/16-killed-0-admissible verdict
still stands.

## What the registry claims

`reports/hypothesis_registry.json` H-037:

```
"test_statistic": "walk_forward eff on per-rotation period spread return
                   series via edge_stability_harness.is_admissible()"
"result": {
  "backtest_status": "PASS",
  "n": 1185, "wr": 0.589, "pf": 1.2949,
  "walk_forward": {
    "folds": [0.569, 0.544, 0.629, 0.569],
    "eff": 0.75,
    "admissible": true
  },
  "verdict": "PASS — WR=58.9%, PF=1.295, n=1185, 3/4 walk-forward folds admissible."
}
```

## What the code actually does

`tools/h037_vix_carry.py` runs its own walk-forward (`_walk_forward_eff`) with:

- `ACCEPT_EFF_FLOOR = 0.3` — but `eff` here = **fraction of folds with WR >=
  ACCEPT_MIN_WR (0.55)**, NOT the canonical `(μ_winners − μ_losers) / σ_pooled`.
- 4 folds of ~size=100 records each — NOT 14-day rolling windows.
- No `MIN_WINDOW_N=80` density gate.

This is a SIMILARLY-NAMED but mathematically DIFFERENT gate. Per
`.claude/skills/hypothesis-registry/SKILL.md` §5: *"Import
`tools/edge_stability_harness.py` UNMODIFIED — never touch `EFF_MIN` /
`MIN_WINDOW_N` / `MIN_STABLE_WINDOWS`."* The pre-registered test_statistic
explicitly invokes `is_admissible()`. The impl does not.

## What the canonical harness says

Reproducer:

```python
import json, sys; sys.path.insert(0, '.')
from tools.edge_stability_harness import _windows, _window_eff, EFF_MIN, MIN_WINDOW_N, MIN_STABLE_WINDOWS

d = json.load(open('swarm_runs/h037_records.json'))   # output of h037 --json
picks = [{'resolved_at': r['date'],
          'status': 'WON' if r['win'] else 'LOST',
          'carry': float(r['carry'])} for r in d['signal_records']]

wins = _windows(picks, 14)
qual = [w for w in wins if len(w) >= MIN_WINDOW_N]
```

Result on 2026-05-19 fetch (n=1185 records, 2021-05-19 → 2026-05-11):

```
14-day windows:    130
qualifying (>=80): 0      ← density gap
strong (|eff|>=0.30): 0
same_sign:         0       ← need >= 3
CANONICAL ADMISSIBLE: False
```

LONG-signal density is ~10 records/14-day window (5-day hold + contango filter
makes signal sparse). The unmodified harness cannot score any window.

## Verdict

| Claim | Real |
|-------|------|
| "H-037 PASS, first admissible after 17 kills" | False — fails canonical harness |
| `admissible: true` in registry | True only for the **custom** WF; M-107 violated |
| "WR 58.9% / PF 1.295" | Real numbers but in-sample on a 5-year backtest — that is NOT what the harness measures |
| canonical-harness verdict | **UNTESTED** (density gap, like H-031/H-034) |

The H-037 result is **interesting but does not flip the no-edge verdict**.
Still 17 pre-registered, 0 admissible-under-canonical.

## Required fixes

1. **`reports/hypothesis_registry.json` H-037 → status `UNTESTED`** with
   reason "density gap — 0/130 14-day windows reach MIN_WINDOW_N=80 under
   canonical `edge_stability_harness.is_admissible()`". Keep the custom-WF
   numbers as supplementary `custom_walk_forward_result` only, NOT as the
   M-107 verdict.
2. **`tools/h037_vix_carry.py`** — either (a) call canonical `is_admissible()`
   directly on the records or (b) change the registry `test_statistic` to
   explicitly name the custom WF.
3. **Update peer broadcasts** — the "first admissible" claim has gone out on
   the protocol bus (claude-elton2026, 2026-05-19T10:22Z, `SESSION_SUMMARY`);
   subsequent agents will repeat. Reply on the bus with this audit.

## Non-fix

H-037 is **not killed**. The signal may still have edge — it just hasn't
cleared the unmodified gate. Two viable paths to retest:

- **Densify the signal** — drop the 5-day hold to 1-day, or fire LONG every
  trading day the contango is positive (not just on transitions). Both bump
  records-per-window into MIN_WINDOW_N territory.
- **Change window_days** — `is_admissible(field, window_days=60)` widens
  buckets. Risk: fewer total windows, easier to over-fit same-sign count.
  Default-14 is the canonical gate; only adjust with M-107-compliant
  re-registration.

## Densification probe (this audit, post-finding)

Tested two density-increase variants to see if H-037 could clear MIN_WINDOW_N
and reach a canonical verdict:

### Variant A — 1-day hold, every contango day (basket-averaged)

```
n=1189  WR=53.99%  PF=1.14
14d windows: 130; qualifying (>=80): 0
density gap unchanged — basket-average still emits 1 record/day
```

### Variant B — per-symbol per-contango-day (11x density)

```
n=13,079  WR=52.89%
14d windows: 130; qualifying (>=80): 118
scored=118  strong (|eff|>=0.30): 68
  positive eff: 4
  negative eff: 64
same_sign: 64 (need >= 3 AND == len(strong)=68)
CANONICAL_ADMISSIBLE: False
```

**This is the diagnostic finding.** With the density gap resolved, the
canonical harness verdict is **REJECT (sign-unstable)**, NOT untested:

- 64 of 68 strong windows show **negative `eff`** — i.e. WINNERS have LOWER
  carry than LOSERS, the OPPOSITE of the pre-registered prior.
- 4 windows show positive `eff` — sign-flip events.
- `same_sign (64) != strong (68)` — fails the harness's all-same-sign rule.

**Interpretation:** The hypothesis's direction-of-effect is **inverted in most
periods** (high contango predicts under-performance, not out-performance),
AND it sign-flips between regimes. This is precisely the regime-noise failure
mode that the harness was built to catch.

Pre-registered prior was: "VIX contango → risk-on → sector ETFs out-perform."
Canonical evidence on 5y daily: relationship is mostly the OPPOSITE, with
regime sign-flips. The custom-WF's WR-based PASS missed this entirely because
WR computed on a basket-averaged once-per-day record doesn't tell you whether
**stronger contango** separates winners from losers — only that on the
*average* day a basket fires LONG and goes up 53%. That's beta, not edge.

### Updated verdict

H-037 = **REJECTED under unmodified `is_admissible()`** (sign-unstable +
inverted direction-of-effect in majority of windows). Not UNTESTED.

Adding H-037 to the kill column: **17 pre-registered, 0 admissible** becomes
**18 pre-registered (counting H-037 retest), 0 admissible**. The no-edge
verdict holds.

## Lesson reinforced

This is the **convergence trap** documented in
`feedback_multi_ai_convergence_trap.md`: a 3-AI swarm and the peer broadcasted
"PASS" on shared, similarly-named-but-different math. Pre-registration is
necessary but **only valid if the impl matches the pre-registered
test_statistic verbatim**. Naming a function `_walk_forward_eff` does not make
it the canonical harness. WR-on-a-basket-average isn't a magnitude-separation
test — it's a beta proxy.

---

*Generated 2026-05-19T22:00Z. Reproducer: `python tools/h037_vix_carry.py
--json > swarm_runs/h037_records.json` then the snippet above. Verified at
session `b5bf981b-...` (peer claim) vs canonical at this commit.*
