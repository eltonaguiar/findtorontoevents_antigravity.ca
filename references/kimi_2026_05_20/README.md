# Kimi Research Bundle — Archived Reference

**Original location:** `tools/kimi_research_2026_05_20/`
**Date:** 2026-05-20
**Size:** 18,091 lines across ~30 files
**Source:** Kimi Agent parallel fleet deployment (8 subagents)
**Audit report:** `reports/KIMI_BUNDLE_AUDIT_2026-05-21.md`

---

## What Was Kept

| File | Why |
|------|-----|
| `statistical_validation_framework.py` | **Ported to `alpha_engine/`** — proper bootstrap, Monte Carlo (4 scenarios), BH-FDR, risk-parity ensemble. 1,119 lines, genuine value. |
| All other files | **Archived here for reference** — design patterns, strategy enumeration ideas, report narratives |

---

## Caveats

**Do NOT deploy any of these files to production without independent validation on real data.**

Key issues with the bundle:
- `six_gate_validated_strategy.py` — Gates 4 and 5 have implementation bugs. All gates validated on circular synthetic data (data generator bakes in the signals the strategy trades). Trade recommendations are `ASSET_00..` on synthetic prices with `stop_loss: null`.
- Asset-class harnesses — Generate 2,474+ strategies but use synthetic symbols and are not wired to any real data source. No DB connections, no price feed integration.
- Reports — Marketing narrative. Not reliable as evidence without source code verification.

**Production-ready alternatives already in `alpha_engine/`:**
- `walkforward_validator.py` (607 lines) — Walk-forward validation on real data
- `forward_validator.py` (3,749 lines) — Forward validation of picks
- `score_booster.py` (1,668 lines) — Scoring and boosting logic
- `statistical_validation_framework.py` (1,119 lines) — Now ported, adds bootstrap CI, FDR correction, multi-scenario MC

---

## What Could Be Useful Here

- **Strategy enumeration ideas** — The per-asset-class strategy lists (200+ crypto strategies, 1,094 forex strategies) are useful brainstorming references when building new strategy generators.
- **Factor class patterns** — `CrossSectionalMomentum`, `MeanReversionFactor`, `CarryFactor`, `TrendFilter` in `six_gate_validated_strategy.py` are well-designed individually.
- **Report structure** — The per-asset-class report format is a good template.
