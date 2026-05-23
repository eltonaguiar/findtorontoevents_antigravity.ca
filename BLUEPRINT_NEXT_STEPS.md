# Blueprint: Next Steps for Continuation

**Written by:** Buffy (Codebuff session 2026-04-22)
**Current branch:** `enh/crypto-tod-conf-deadzone`
**Last commit:** `a67903d027` — feat(quality-gates): add confidence dead-zone gate + expand crypto TOD death window

---

## What Was Done This Session

1. **HC Gate Parity Fix** (branch `fix/hc-gate-config-parity-2026-04-22`) — merged to main via PR #292
   - Synchronized `config/hc_gate_params.json` ↔ `audit_dashboard/hc_filter.js` ↔ `tools/dashboard_hc_rules.py`
   - Key param changes: scoreFloorEquity 50→45, trustScoreMinCrypto 6→4, independentGroupsMin 0→3
   - Added per-asset-class floors for Commodity/Futures/Bond/ETF
   - New tools: `tools/audit_pick_schema.py`, `tools/hc_rolling_impact.py`
   - Comprehensive changelog: `updates/2026-04-22-hc-gate-config-parity-full-changelog.md`

2. **Scratch File Cleanup**
   - Deleted 19+ `tmp_*.py` files across project
   - Deleted `apply_godlike_fixes.py` / `apply_godlike_fixes_v2.py`
   - Added `**/tmp_*` and `**/apply_godlike_*` to `.gitignore`

3. **Quality Gates Enhancement** (current branch `enh/crypto-tod-conf-deadzone`)
   - Added confidence dead-zone gate (0.65–0.75 range) for crypto picks
   - Expanded TOD death window to include 16:00–21:00 UTC
   - Committed as `a67903d027`, pushed to origin

---

## Next Steps (Priority Order)

### 🔴 P0 — Push Current Branch & Create PR
- Current branch `enh/crypto-tod-conf-deadzone` needs to be pushed to origin
- Create a PR targeting `main` with the confidence dead-zone + TOD expansion changes
- Include a .MD doc in `updates/` explaining the dead-zone investigation and TOD findings

### 🟡 P1 — Sync Local main
- `git checkout main && git pull origin main`
- Main now includes the merged PR #292 changes — local main is stale
- After syncing, rebase or merge `enh/crypto-tod-conf-deadzone` onto latest main if needed

### 🟡 P2 — Delete Merged Fix Branch
- `git branch -d fix/hc-gate-config-parity-2026-04-22` (local branch cleanup)
- Remote branch can also be deleted: `git push origin --delete fix/hc-gate-config-parity-2026-04-22`

### 🟢 P3 — Validate HC Gate Changes in Production
- Run `tools/hc_rolling_impact.py` to measure post-fix HC WR/PF improvement
- Run `tools/audit_pick_schema.py` to verify pick data schema health
- Check the deployed audit dashboard at the production URL to confirm HC params rendered correctly

### 🟢 P4 — Code Review the Quality Gates Change
- The `audit_trail/quality_gates.py` change (confidence dead-zone + TOD expansion) was committed but not code-reviewed
- Run `python3 -c "import py_compile; py_compile.compile('audit_trail/quality_gates.py', doraise=True)"` for syntax check
- Review the dead-zone thresholds (0.65–0.75) — are these optimal? Backtest data supported them?
- Review the TOD hours expansion (16–21 UTC) — verify against the PR #291 investigation findings

### 🟢 P5 — Forward-Validate the New Quality Gates
- Run a forward validation with the new confidence dead-zone gate active
- Compare WR before/after dead-zone gate to confirm it filters the non-monotonic zone
- If WR improves → merge PR; if neutral/negative → adjust thresholds

---

## Key Files to Know

| File | What It Is | Status |
|------|-----------|--------|
| `config/hc_gate_params.json` | HC gate source-of-truth (v4) | Merged to main |
| `audit_dashboard/hc_filter.js` | Front-end HC logic | Merged to main |
| `tools/dashboard_hc_rules.py` | Backend HC logic | Merged to main |
| `tools/audit_pick_schema.py` | Pick schema health auditor | Merged to main |
| `tools/hc_rolling_impact.py` | Rolling HC impact analysis | Merged to main |
| `audit_trail/quality_gates.py` | Quality gates (confidence + TOD) | On current branch, needs PR |
| `updates/2026-04-22-hc-gate-config-parity-full-changelog.md` | Full changelog | Merged to main |
| `.gitignore` | Now includes `**/tmp_*`, `**/apply_godlike_*`, `tradingview-mcp/` | On current branch |

---

## Git State

- **Current branch:** `enh/crypto-tod-conf-deadzone` (2 commits ahead of main for quality gates)
- **main:** Includes merged PR #292 (HC gate parity fixes)
- **Stale local branch:** `fix/hc-gate-config-parity-2026-04-22` (merged, can delete)
- **Working tree:** Clean (no uncommitted changes)

---

*End of blueprint. Hand off to next agent.*
