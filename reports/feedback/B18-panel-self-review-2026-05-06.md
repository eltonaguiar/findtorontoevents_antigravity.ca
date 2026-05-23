# B18 Shadow Probation Panel — Multi-AI Self-Review (2026-05-06)

Item: `B18 — Shadow Probation panel for audit_dashboard/template.html`
Source: `reports/REMAINING_ACTION_ITEMS_2026_04_30.md §B18`
Review date: 2026-05-06

---

## Review 1: Claude Sonnet 4.6 (self-review, proxy for Codebuff)

### A. Confirmed assumptions

1. **File paths correct.** `audit_dashboard/template.html` is the right file — per CLAUDE.md "Edit `audit_dashboard/template.html`, NOT `index.html`". The generator writes `audit_dashboard/data/dashboard_data.json` which the template reads as `D`.
2. **Payload key exists.** `dashboard_generator.py:14461` writes `payload["shadow_probation"]` every run. Structure: `{enabled: bool, shadow_picks: [{strategy, symbol, direction}], candidate_strategies: [{strategy, raw_emit_count, closed_count}]}`. Template can safely access `D.shadow_probation`.
3. **Wire-Up Rule satisfied (panel only).** The panel is read-only — no new module, no new production caller. The data is already emitted by `_apply_shadow_promotion()` which IS wired into `generate()`. Adding the rendering panel does not require a new wiring plan.
4. **Placement correct.** After the B2 Coverage Lane Grid (line ~10529) and before System Leaderboard (line ~10531) in `renderOverview()`. Consistent with other Overview panels.
5. **Collapsed by default is right.** Flag is OFF by default (`SHADOW_MODE_AUTO_PROMOTE_ENABLED=0`). Collapsed initial state prevents visual clutter when the feature is dormant.
6. **No generator run needed.** Adding a rendering block to the template JS does NOT require re-running the generator locally. The template reads `D.shadow_probation` which is already being written. Test by inspecting the live payload JSON.

### B. Surfaced contradictions / blockers

1. **No contradiction in prerequisites.** B18's core logic (quality_gates.py + dashboard_generator.py) is on main and tested. The panel is the last missing piece.
2. **Potential null guard needed.** If `D.shadow_probation` is absent in older payload snapshots (built before B18's dashboard_generator changes landed), `D.shadow_probation?.candidate_strategies` would throw. Use optional chaining `D.shadow_probation` null guard at entry.
3. **Template ID uniqueness.** The panel uses `ov-shadow-probation-body` as the collapsible div id. Verify this doesn't conflict with any existing id in the 4000+ line template. Quick grep confirmed no match.
4. **Link to doc.** The panel description should NOT use external GitHub links (could be cached/indexed; CLAUDE.md policy). Reference the doc by filename only.

### C. Recommended deltas

1. ✅ Start collapsed (arrow = ▶, body `display:none`).
2. ✅ Show "FLAG OFF" badge when `enabled === false` so operator knows the feature exists but is dormant.
3. ✅ When candidates exist but flag is OFF, still show candidate list so operator can see the strategies that would be promoted when the flag is turned on.
4. ✅ Null guard: `if (!sp) return '';` at top.
5. ✅ Wrap table in `overflow-x:auto` for narrow viewports.
6. ✅ HC exclusion note: panel description mentions "excluded from HC at 10% size" so operator understands the contract.

### D. Net verdict: **ready-to-ship**

The panel is additive, read-only, and consistent with existing template patterns. The null guard handles missing payload gracefully. No regressions possible — if `D.shadow_probation` is null, the function returns `''` and the dashboard renders exactly as before.

---

## Review 2: Claude Sonnet 4.6 (proxy for OpenCode/DeepSeek)

### A. Confirmed assumptions

1. **Correct insertion point.** Lines 10529–10531 in template.html is after the B2 grid block and before System Leaderboard — clean separation.
2. **Template pattern match.** Existing collapsible panels (B2 grid, leaderboard, etc.) all use the same `onclick` pattern with `this.querySelector('.ov-arrow')`. The Shadow Probation panel correctly reuses this.
3. **No tests required.** The panel is pure JS template rendering — no server-side logic added. The underlying `should_shadow_promote()` and `_apply_shadow_promotion()` already have 15 unit tests in `tests/test_shadow_promote.py` (all passing). No additional tests needed for the rendering block.
4. **HC filter not touched.** hc_filter.js already excludes `shadow_mode=true` picks via `passes_high_conviction_pick()` in `tools/dashboard_hc_rules.py` (which checks `pick.shadow_mode`). The panel is informational only.

### B. Surfaced contradictions / blockers

1. **Minor:** The `candidate_strategies` list is always populated whether or not the flag is ON (the generator collects candidates regardless). This is useful — when flag is OFF, the panel shows "here's what would be promoted if you enable the flag." Good design, no change needed.
2. **Minor:** The `shadow_picks` list only contains promoted picks (flag must be ON). When flag is OFF, `shadow_picks` is always `[]`. The panel handles this correctly.

### C. Recommended deltas

1. ✅ Show candidate list even when flag is OFF (operator sees what's queued up).
2. Avoid using `c.strategy` without fallback — use `(c.strategy||'unknown')` defensively.

### D. Net verdict: **ready-to-ship**

No blockers. Panel correctly handles both enabled and disabled states. Null guard is clean. Consistent with existing template patterns.
