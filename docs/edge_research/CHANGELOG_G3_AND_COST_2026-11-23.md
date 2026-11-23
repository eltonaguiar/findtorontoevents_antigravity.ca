# Changelog — G3 gate defect + per-class cost corrections

**Date:** 2026-11-23 · **Worktree:** vanilla-handsaw · **Author:** Kilo
**Scope:** two corrections from this review that changed rankings. Paper only; zero capital.

---

## 1. G3 gate defect (fixed)

**What was wrong.** Gate **G3** ("deflated Sharpe with trial count stated") was implemented as a
*presence* check — `dsr is not None and dsr_n_trials is not None`. That let a pick with
**DSR 0.318 @ N=658** pass a gate whose whole purpose is multiplicity control. Presence is not
significance.

**Fix.** `tools/pick_gate.py` now requires the DSR to clear the deflation threshold:

```python
DSR_PASS = 0.95
g["G3"] = (p.dsr is not None and p.dsr >= DSR_PASS
           and p.dsr_n_trials is not None and p.dsr_n_trials >= 1)
```

**Effect on the rankings (rebuilt after fix).**

| Gate | Before fix | After fix |
|---|---|---|
| G1 (gross > 2× measured cost) | 15/69 | 15/69 |
| **G3 (DSR ≥ 0.95)** | *wrongly passing* | **0/69** |
| G2 (hold ≥ 1 day) | 0/69 | 0/69 |
| G4 (net annualised > 4.32% T-bill) | 0/69 | 0/69 |
| **All five gates** | 0 PASS | **0 PASS** |

Max per-symbol DSR is **0.318 (CVX)** — nothing is near 0.95. The deflation gate is now
**binding** alongside G2 (no hold-times) and G4 (T-bill hurdle). Verified: DSR 0.318 → G3 false,
DSR 0.97 → G3 true; `tests/test_verification_tools.py` passes; `tools/validate_gate_reports.py`
reports 0 violations.

**Why it matters.** The earlier "0 PASS" was defensible on G2 alone (missing hold-times). This
defect means G3 was *not* actually protecting the ranking, so "0 PASS" was, for a time, partly
accidental. After the fix the conclusion holds on three independent gates, not one.

---

## 2. Per-class cost correction (fixed)

**What was wrong.** A single round-trip cost of **12.87 bp** was applied to **every** asset class.
12.87 bp = 12.07 spread + 0.8 IBKR — and 12 bp is a *crypto-major* number. Applied to EQUITY/ETF
it overstated cost by roughly **6×**.

**The measured per-class model** (from
`reports/peer_claude-topic_execution-costs_deepseek_2026-05-31.md`):

| Cost bucket | Round trip (bp) | Used for |
|---|---|---|
| EQUITY_SP500 | **2.0** | EQUITY large caps, liquid ETFs |
| EQUITY_SMALLCAP | 7.5 | small caps |
| CRYPTO_MAJOR | **12–14** | BTC, ETH |
| CRYPTO_ALTCOIN | **25** | all other crypto |
| FOREX_MAJOR | **1.0** | major FX pairs |
| FOREX_CROSS | 3.2 | FX crosses |

**Resolution of the 4.97 vs 12.87 dispute.** Copilot's **1–5 bp** (n=191 names) matches
`EQUITY_SP500 ≈ 2 bp`; my **12.87 bp** matched `CRYPTO_MAJOR ≈ 12 bp`. Both were right for
their universe. The error was **mine** — one crypto cost applied to all classes.

**Effect.** With the correct 2 bp EQUITY cost, EQUITY clears **G1 on 16/26 picks** (was ~2 at
12.87 bp). The ranking still stands at **0 PASS** because G3 (DSR ≥ 0.95) and G2/G4 fail
independently — the verdict is *cost-insensitive*, as previously shown across 4.97–20 bp.

---

## 3. Files touched

- `tools/pick_gate.py` — G3 threshold (`DSR_PASS = 0.95`), glossary text
- `reports/asset_class_rankings.json` — rebuilt after G3 fix
- `reports/cost_per_class_model.json` — class-specific cost table + resolution
- `reports/distance_analysis.json` — G1–G4 with correct cost
- `reports/claims_killed.json` — G3 defect recorded under `killed` + `post_fix_state`
- `reports/deflation_programme.json` — `g3_gate_fix` note
- `tests/test_verification_tools.py` — 9 tests incl. G3 threshold behaviour

## 4. Net conclusion (unchanged by both fixes)

No pick clears all five gates; no class survives deflation. The only defensible real-money
action remains a **low-cost broad index ETF** (a buying decision, not an edge). Bar to beat it:
**+3.34%/yr excess at $1k tickets, +0.80%/yr at $25k**.

*Paper only. Zero capital. Not investment advice.*
