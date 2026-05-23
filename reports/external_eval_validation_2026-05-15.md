# External Evaluation — Claim Validation vs Codebase Reality

**Source:** External agent (`mimo-v2.5-pro` via `/gsd:update`) produced a multi-phase action plan citing per-asset-class PF/WR, raw WR, file states, PRs, and PCG-5 wiring.

**Validation date:** 2026-05-15
**Validator HEAD:** `a53f041f13d` on branch `docs/grok-part2-pr-bodies-2026-05-15`
**Source of truth for live numbers:** `audit_dashboard/data/dashboard_data.json` on origin/main (blob `b1e976ba998`)

## Verdict matrix

| Claim group | Verdict | Severity |
|---|---|---|
| Per-asset-class PF/WR/n | REFUTE — ALL 6 numbers stale | High |
| Overall raw WR 11.13% / PF 0.46 / n=55k+ | REFUTE — actual 45.2% / 1.21 / 29,025 | Critical |
| File existence (13 cited) | PARTIAL — 5 exist on main, 3 on unmerged branches, 5 never existed | Medium |
| PCG-5 + safety wiring | PARTIAL CONFIRM — portfolio_gates is shadow-only; protocol_state/safety_status/slippage_validator NOT on main | Medium |
| CT=F "active 4-week paper-pilot shadow" | REFUTE — zero CT=F picks anywhere | High |
| PR #1023-1026 status | CONFIRM exist; #1023 actually MERGED (not pending) | Low |
| master_plan SHA `80b513fa69c` | CONFIRM exists in history | N/A |

## Detail

### A. Performance numbers (asset_class_health)

| Class | Eval (stale ~2026-04-22) | Current origin/main (2026-05-15) | Delta |
|---|---|---|---|
| CRYPTO | PF 1.26 WR 44.8% | PF 1.36 WR 46.7% n=8011 | +0.10 PF |
| EQUITY | PF 1.42 WR 52.8% n=428 | PF 1.57 WR 51.9% n=420 | +0.15 PF |
| COMMODITY | PF 2.08 WR 48.7% | PF 2.49 WR 61.5% | +0.41 PF |
| ETF | PF 1.20 WR 53.4% | PF 1.48 WR 58.5% | +0.28 PF |
| BOND | PF 1.72 WR 55.6% n=18 | **PF 0.66 WR 54.5% n=11** | **-1.06 PF — REGRESSION** |
| FOREX | PF 0.28 WR 45.6% n=1.2k | PF 0.81 WR 52.3% n=342 | +0.53 PF |

BOND collapse is the only material regression. Sample size also dropped 18→11 (charter floor was already violated; now worse).

### B. Overall raw WR

Eval: "RAW WR 11.13% / PF 0.46 / n=55k+"
Live (`audit_dashboard/data/dashboard_data.json` summary block): **45.2% WR / PF 1.21 / n=29,025**

Magnitude of error suggests eval pulled from a different ledger or a corrupted view. Cannot identify source from given data.

### C. File existence

| File | Eval implied | Reality |
|---|---|---|
| tools/db_freshness_check.py | should exist | NEVER EXISTED |
| tools/verify_citations.py | should exist | NEVER EXISTED |
| tools/cross_db_consistency.py | should exist | NEVER EXISTED |
| tools/cot_lag_corrector.py | proposed PR-A | NEVER EXISTED (skeleton in `reports/grok_evaluation_2026-05-15.md` only) |
| alpha_engine/strategies/pead_piotroski.py | proposed PR-B | NEVER EXISTED (skeleton in grok eval only) |
| alpha_engine/direction_bias.py | implied | NEVER EXISTED |
| alpha_engine/position_sizer.py | implied wired | EXISTS on main |
| alpha_engine/concentration_cap.py | implied wired | EXISTS on main, WIRED via production_scanner.enforce_sector_concentration_cap |
| audit_trail/portfolio_gates.py | shadow-only | EXISTS on main, **SHADOW-ONLY** (line 1-8 docstring: "DO NOT actually block. Caller decides whether to honor.") |
| audit_trail/protocol_state.py | implied wired | **ONLY ON FEATURE BRANCHES** `feat/phase-j-banner-kilo-cleanup`, `fix/mercury2-p0-audit-truth`. NOT on origin/main. |
| audit_trail/safety_status.py | implied wired | **ONLY ON FEATURE BRANCHES** (same as above) |
| audit_trail/slippage_validator.py | proposed M-016/041 (PR #1026) | **ONLY ON FEATURE BRANCHES** (same as above) |

Phase J commit `d3995f5ac4d` added 940 lines across the 3 safety files. Commit lives on branches `feat/phase-j-banner-kilo-cleanup-2026-05-15` and `fix/mercury2-p0-audit-truth-2026-05-15`. Neither merged to main. **The safety infrastructure the eval treats as "in shadow" is actually orphaned in unmerged branches.**

### D. PCG-5 + COT MATCH + DB freshness

- **PCG-5 / portfolio_gates**: SHADOW-ONLY on main. Confirmed via `audit_trail/portfolio_gates.py:1-8`. No `evaluate_pick()` caller in `production_scanner.py` / `score_booster.py` / `smart_picks_engine.py`. Eval is correct.
- **concentration_cap**: WIRED via `production_scanner.py:enforce_sector_concentration_cap()` + `quality_gates.py:passes_concentration_cap`. Eval was wrong to imply absent.
- **slippage_validator drift CB**: NOT on main; lives in unmerged Phase J branch. Eval's "carry forward PR #1026" framing matches reality.
- **COT MATCH gate**: confirmed NEVER EXISTED. Aligned with master plan M-008.
- **DB freshness guardian**: confirmed NEVER EXISTED. Aligned with master plan M-002.

### E. CT=F Cotton pilot

Eval: "cot_positioning + CT=F is the only thing in active 4-week paper-pilot shadow"

Reality:
- `alpha_engine/data/smart_picks.json` → 0 CT=F picks
- `alpha_engine/data/active_picks.json` → 0 CT=F picks
- `audit_dashboard/data/dashboard_data.json` → no CT=F symbol exposed in active or recent_closed

**Zero CT=F picks anywhere on main.** The "4-week paper-pilot shadow" framing is invented. The unblock work in master plan M-008/M-021 hasn't actually produced a live pilot yet. Any action plan that recommends "$500-$2k to CT=F upon 7-day shadow soak" is sequencing failure — there is no shadow to soak.

### F. PR claims (#1023-1026)

| PR | Eval implied | Reality (gh pr list) |
|---|---|---|
| #1023 | active/open | MERGED 2026-05-15T02:04:04Z (feat: tv-skills) |
| #1024 | active/open | CLOSED 2026-05-15T02:13:58Z (feat: hermes-symbol-blocks) |
| #1025 | active/open | CLOSED 2026-05-15T02:30:20Z (feat: upstream) |
| #1026 | active/open + carry-forward | OPEN 2026-05-15T03:13:15Z (feat: Phase J ML-calibration) |

PR #1026 is the carrier for the safety files. **If #1026 doesn't merge, the entire safety stack referenced in the eval's Phase 2 (PCG-5 + drift CB + slippage_validator) stays orphaned.**

### G. master_plan SHA

`80b513fa69c` exists. Confirmed via `git log --all --oneline | grep 80b513fa69c`. Verdict: CONFIRM.

## Implications for the eval's 4-phase plan

| Phase | Eval recommendation | Validation impact |
|---|---|---|
| Phase 1 (Days 1-7) — DB freshness + Wire-Up audit + DSR/PSR | Acceptable. Files never existed. Aligned with M-002 / M-040 / M-039. |
| Phase 2 (Days 8-14) — Move PCG-5 from shadow to enforce + slippage_validator drift CB | **Blocked.** Phase J safety files (protocol_state/safety_status/slippage_validator) are on unmerged branches. **Step zero is to merge PR #1026 or cherry-pick `d3995f5ac4d` to main BEFORE wiring.** Eval skipped this. |
| Phase 3 (Days 15-21) — Cotton pilot init + COT MATCH gate | **Blocked.** Zero CT=F picks exist. Phase ordering wrong: M-008 (MATCH gate) + M-021 (lag correction) must produce a pilot stream FIRST, then 7-day soak, then size. Eval reads as if pilot already exists. |
| Phase 4 (Days 22-30) — Micro real-money CT=F $500-2k | **Blocked on Phase 3 actually generating signals.** Real-money sizing should also wait on DSR/PSR thresholds the eval itself listed but didn't gate on. |

## Recommendations to operator

1. **Reject eval's per-class numbers and raw WR claim**. Cite this doc when peers reference them. Source-of-truth is current `audit_dashboard/data/dashboard_data.json` on origin/main.
2. **Investigate BOND regression** (PF 1.72 → 0.66, n 18 → 11). Only material regression in the period. Likely candidates: ghost rows, resolver edge case, single-pick blow-up. Spawn a deep-dive subagent against `audit_dashboard/data/dashboard_data.json` `by_asset_class.BOND.recent_closed`.
3. **Decide on PR #1026** (Phase J safety stack). Two paths:
   - Merge as-is — gets protocol_state/safety_status/slippage_validator on main, even if not yet wired into production gates
   - Reject — accept that safety infrastructure has to be rewritten from scratch; close M-016/M-041 and reopen
4. **Cotton pilot precondition**: instead of "$500-$2k on Day 22", first verify the M-008/M-021 work produces any CT=F pick at all. Set a precondition: "≥10 CT=F picks emitted in shadow over 7 days at PF>1.5 net-of-cost" → then size.
5. **Don't treat eval as actionable until validated**. The pattern (stale numbers + phantom files + invented pilot status) is the same failure mode flagged in memory `project_hermes_phantom_work_2026-05-09` — external agents producing plausible-sounding work that doesn't survive disk verification.

## Provenance

Investigation conducted via subagent `caveman:cavecrew-investigator` + direct git verification. Evidence cited inline. No fixes applied — this is a verification doc only.
