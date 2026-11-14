# quant-audit-2026-11-14 — Final Deliverable (2026-11-14)

**Worktree:** `quant-audit-2026-11-14` (`.worktrees/quant-audit-2026-11-14`)  
**Branch:** `audit/quant-remediation-plan`  
**Auditor:** Quantitative auditor / investment manager (opencode)  
**Date:** 2026-11-14  
**Repo:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/

This folder consolidates my quantitative audit of the prediction system at
findtorontoevents.ca/audit (stocks, crypto, forex, bonds, ETFs, mutual funds).
Everything is read-only/additive tooling + findings — no live pipeline code was
changed as part of the audit itself.

## Contents

| Subfolder | What's here | Status |
|---|---|---|
| `01_audit/` | Quantitative audit findings: per-class win rates, expectancy, MDD, money-ready gate results on `recent_closed_array.json` | findings |
| `02_tools_guardian/` | Runnable guardian tooling: `money_ready_screener.py` (166-cell gate screener) + remediation plan | runnable |
| `03_peer_reviews/` | Cross-peer review synthesis (childlike-airport, finpredict-v2, finpredict-v3) | review |
| `04_research_validation/` | Screener findings document + evidence of 0/166 passing cells | evidence |
| `05_final/` | Summary / verdict docs (placeholder — see 04) | final |
| `06_evidence/` | Raw screener results JSON (179KB, all 166 cells with gate pass/fail reasons) | evidence |

---

## Added by the Freebuff auditor (same worktree, later pass)

Two agents worked in `.worktrees/quant-audit-2026-11-14`. The subfolders above are the opencode
screener deliverable, left untouched. The folders below are a **second, independent pass** that
adjudicates every peer claim of 2026-11-14 by re-execution where possible.

| Subfolder | What's here |
|---|---|
| `00_executive_summary/` | Table of every peer claim with verdict: REPRODUCED / REFUTED / PARTIAL / CORROBORATED |
| `01_peer_reviews/` | Per-peer reviews: `deepai_live_audit`, `kilo_childlike_airport`, `iteration_005`, `finpredict_family`, `seer_scratch_flaxen` |
| `02_my_findings/` | My audit, remediation plan and 40-trial edge search (all already merged to `main` via #767/#768) |
| `03_local_recently_modified/` | Inventory + triage of the 358 untracked / 1 modified local files, and root hygiene |
| `04_remote_github/` | Branch, PR and `main`-churn state; which branches are superseded or unmergeable |
| `05_verification/` | Reproduction of deepAI variant C (their script, live payload), with the payload copy of the script |
| `06_recommendations/` | Consolidated P0–P3 actions and the single go/no-go metric |

### Headline of the second pass

- **deepAI variant C reproduces exactly** (`n=237 WR=47.3% PF=1.26 +98.7pp z=-0.84`, null 0/800) —
  the only peer profitability claim that survives re-execution, still sub-T2 and selection-based.
- **Kilo's "VALIDATED" VWAP claim is refuted** on its own numbers: 12.7% total over ~22 months at
  Sharpe 3.76 implies 1.84%/yr volatility on 40%-sized 4h crypto — impossible. PBO 0.489 is also
  labelled PASS by an inverted gate (`< 0.5`); the repo standard is ≤ 0.10.
- **ITERATION-005's trend result is real but mislabelled** "PROVEN": its Sharpe 2.13 is below its own
  buy-and-hold benchmark (≈2.2), and t=5.56 tests mean>0, which beta also passes.
- **`resolution_method` is `None` for all 3,500 `recent_closed` rows** — the single fact blocking
  certification of any PF in the system, including variant C.

## Verdict (bottom line)

**No asset class is money-ready on the live ledger.** My screener applied the full
Tier-2 money-ready gate contract (n≥100, WR≥50%, PF≥1.5, net expectancy>0 with CI
lower bound>0, MDD<20%, multi-source, regime-direction consistency) to all 166
strategy×class×direction cells in `recent_closed_array.json` (3,447 decisive picks,
53 non-decisive excluded). **0/166 cells pass all gates.**

Every class fails on at least one gate; most fail on several. All 166 cells are
single-source (100% from one `source_system`). Only 1 cell clears n≥100
(`luxalgo_confluence` CRYPCO LONG, n=563) and it fails on WR (44.0%), PF (1.24),
MDD (289.5%), and single-source (94%).

## Reconciliation with peer findings

Peers (childlike-airport / kilo) found statistically-valid profitable approaches
EXIST in backtest research:

| Approach (peer) | Asset Class | Sharpe | PF | PBO | Status |
|---|---|---|---|---|---|
| Regime-Filtered VWAP MR (kilo) | Crypto 4h | 3.76 | 1.21 | 0.489 | VALIDATED |
| Vol-Targeted Trend (kilo) | Crypto daily | 2.13 | 1.40 | — | PROVEN |
| Walk-Forward Variant C (deepAI) | Equity/ETF | — | 1.26 | p<0.0013 | PILOT |

These are NOT contradictory with my 0/166 result: Kilo's approaches live in
separate backtest harnesses (`/tmp/kilo/*.py`), not in the deployed
`recent_closed_array.json` ledger. The gap is between research and production —
no profitable approach from research has been deployed into the live pick ledger.

## Highest-value production defects (multi-peer-verified)

1. **0/9 asset classes money-ready** (`money_ready_verdict.json`)
2. **EXPIRED picks mislabeled as WON** (survivorship bias inflating WR)
3. **53 picks frozen at pnl_pct=0%** (stale/unresolved)
4. **All 166 cells single-source** (no multi-source confirmation)
5. **7 GitHub workflows failing**, Unified Audit Dashboard cancelled ~70% of hours
6. **No mutual fund class anywhere** (not in asset_class.py, gatekeeper, or any picker)
7. **CRYPCO expectancy −5.86% (CI [−4.96%, −4.38%])** — statistically significant negative

## For the coordinator

1. Sign off the remediation plan (`02_tools_guardian/REMEDIATION_PLAN_2026-11-14T2100Z.md`)
2. Deploy `money_ready_screener.py` as a CI gate (`02_tools_guardian/tools/`)
3. Adopt Kilo's regime-filtered VWAP MR as the first production candidate (crypto only)
4. Fix EXPIRED→WON relabeling and zombie drain before any gate can pass
5. Add MUTUAL_FUND class to asset_class.py + gatekeeper ASSET_CLASS_MAP

## Cross-peer references

- `final_2026_11_14/childlike-airport/` — Kilo's audit (stale data, PnL contradictions, profitable approaches)
- `final_2026_11_14/finpredict-v2/` — Finpredict v2 (reconciliation backbone, CI gates G1-G13)
- `final_2026_11_14/finpredict-v3/` — Finpredict v3 (data-hygiene audit, horizon validation, guardian tools)

### Note on folder completeness

`01_audit/` was left empty by the opencode pass (its findings live in `04_research_validation/`);
git does not track empty directories, so that path will not appear on GitHub. `05_final/` is a
placeholder by the sibling's own description. All other listed folders contain files.
