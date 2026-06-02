# Source-System Concentration Cap — Spec & Patch

**Date:** 2026-06-02
**Source:** EAGLE_JUNE2_claude-opus-4-7.md §7.1 (top priority 30-day action)
**Problem:** FUTURES has 85% `multi_asset_scanner` (artifact), UNKNOWN 89% `file:alpha_engine` (artifact), EQUITY 40% `regime_terminal` (single strategy). Existing `concentration_cap.py` enforces per-symbol + per-sector caps but NOT per-source-system.

## What this patch does

Adds a third cap to `alpha_engine/concentration_cap.py`:

```python
def passes_source_system_cap(asset_class: str, source_system: str, active_picks: list[dict]) -> tuple[bool, str]:
    """Reject new emits where the source-system already dominates the class.

    Per EAGLE_JUNE2 §4.1 + 7.1: top_source > 50% AND n < 50 → reject.
    Above n=50, HHI < 0.30 hard cap (per feedback-concentration-strategy-not-engine).
    """
    if not source_system:
        return True, "no source_system field"

    class_picks = [p for p in active_picks if (p.get("asset_class") or "").upper() == asset_class.upper()]
    n = len(class_picks)

    if n < 1:
        return True, f"empty class"

    # Cold-start escape: below n=10, don't apply
    if n < MIN_ACTIVE_FOR_CAP:
        return True, f"cold-start n={n} < {MIN_ACTIVE_FOR_CAP}"

    # Count by source_system
    by_source: dict[str, int] = {}
    for p in class_picks:
        s = (p.get("source_system") or p.get("source") or "UNKNOWN").upper()
        by_source[s] = by_source.get(s, 0) + 1

    cur_count = by_source.get(source_system.upper(), 0)
    cur_pct = 100.0 * cur_count / n
    post_count = cur_count + 1
    post_pct = 100.0 * post_count / (n + 1)

    # Hard HHI block: source > 50% AND n < 50
    if post_pct > 50.0 and n < 50:
        return False, (
            f"source_system_cap: {source_system} would be {post_count}/{n+1} "
            f"= {post_pct:.1f}% > 50% cap (current n={n} < 50 hard gate)"
        )

    # Soft HHI block: post-add HHI > 0.30
    if n >= 50:
        new_by_source = dict(by_source)
        new_by_source[source_system.upper()] = post_count
        new_total = n + 1
        hhi_post = sum((c / new_total) ** 2 for c in new_by_source.values())
        if hhi_post > 0.30:
            return False, (
                f"source_system_cap: HHI would be {hhi_post:.3f} > 0.30 (post-add). "
                f"Top sources: {sorted(new_by_source.items(), key=lambda x: -x[1])[:3]}"
            )

    return True, f"ok ({source_system} {cur_count}->{post_count}/{n+1} = {post_pct:.1f}%)"
```

## Wire-up

Two call sites, in the same pattern as the existing `passes_concentration_cap`:

1. `alpha_engine/production_scanner.py` — call before any new emit lands in the active picks list
2. `audit_trail/quality_gates.py::passes_active_gate` — call alongside the existing per-symbol cap (~line 7002, per `concentration_cap.py` docstring)

Add a kill-switch env var `SOURCE_SYSTEM_CAP_ENABLED` (default 1, opt-out for emergency).

## Expected impact (per EAGLE_JUNE2 §7.1)

| Class | Live state | After cap |
|---|---|---|
| FUTURES | 85% multi_asset_scanner, 15% diversified | Reject new multi_asset_scanner emits until n ≥ 50 with HHI ≤ 0.30 → diversified 15% grows to 30%+ over the next 30-60 days |
| UNKNOWN | 89% file:alpha_engine, 11% diversified | Same pattern — force diversification |
| EQUITY | 40% regime_terminal | 40% < 50% so no hard block, but if regime_terminal climbs to 51% AND n<50, block. Soft HHI check activates at n≥50. |
| FOREX | 34% multi_asset_scanner | No block (under 50%) |
| CRYPTO | 23% file:battleground | No block (under 50%) |

**Net: FUTURES WR should lift by ~5pp (8pp of the 85% concentration is the underperforming source) just from forcing diversification on the next 30 days of emits.**

## Test plan

1. `python3 -m py_compile alpha_engine/concentration_cap.py` OK
2. Unit test: `passes_source_system_cap("FUTURES", "multi_asset_scanner", [...12 multi_asset_scanner + 1 other...])` → `(False, "source_system_cap: ... 92.3% > 50%")`
3. Unit test: same call with n=60 and HHI=0.25 → `(True, "ok ...")`
4. Integration: read existing `pf_registry.by_asset_class_policy_clean_net` and verify the cap matches the reported `top_source_share` field on every class

## Rollback

`SOURCE_SYSTEM_CAP_ENABLED=0` to disable. Permanent rollback = `git revert <commit>`.

## Why this is the highest-leverage 30-day action

The concentration cap is a single small change that mechanically moves WR on the most-failed class (FUTURES) without touching any strategy logic. It doesn't require:
- New strategies
- New data feeds
- Resolver fixes
- Backtest re-runs
- Forward n accumulation

It just enforces what the dashboard already says is broken.

## Files touched

- `alpha_engine/concentration_cap.py` (add `passes_source_system_cap`)
- `alpha_engine/production_scanner.py` (call site + env-var kill switch)
- `audit_trail/quality_gates.py` (call site in `passes_active_gate`)

## Status

**NOT YET MERGED.** This is a spec. The actual patch should be a small PR (~30 lines + tests) once the operator gives the go-ahead. Reason: this changes production emission behavior, and per CLAUDE.md "Do NOT autonomously produce code-diff PRs from a single agent's imagined function names + line numbers" — needs a 2nd-agent review pass before merge.
