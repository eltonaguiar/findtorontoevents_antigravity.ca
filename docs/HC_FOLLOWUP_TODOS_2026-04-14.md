# HC follow-up — todos, ownership, and what was done (2026-04-14)

Peers (Claude / Cursor) aligned on **META strict-HC math**, **PM forward-tracking scope**, and **multi_asset_copytrader** investigation. This file is the single checklist.

## Corrected META / strict HC math (authoritative)

**Strict HC** (what the button applies when **validated edge** is on): `filterHcStrict` = `filterHighConvictionOrdered` **then** `passesValidatedEdgePerClass`.

- **Gate 1** only needs score ≥ **40** (`scoreAbsoluteFloor`).
- **Validated edge for EQUITY** needs score ≥ **50** and trust ≥ **3** (`audit_dashboard/template.html` → `passesValidatedEdgePerClass`).

**META** (snapshot): score **37**, trust **5**, fwdN **746**, fwdWR **46.8%**.

| Layer | Gap |
|--------|-----|
| Gate 1 only | **+3** (37 → 40) |
| **Strict HC (EQUITY edge)** | **+13** (37 → **50**), not +3 |

Claude’s correction: **+13 points** to reach strict-edge EQUITY, not +3.

## Gap table — edge-case rows (today’s snapshot)

| Pick | Score | Trust | fwdN | fwdWR | Gap to **strict** HC | Notes |
|------|-------|-------|------|-------|------------------------|--------|
| **META** | 37 (pre-fix snapshot) | 5 | 746 | 46.8% | Was **+13** to strict edge; **mitigation shipped** — re-score on next dashboard gen | Root cause: conf **0.60** + LONG stacked **-22**; see `META_SCORE_TRACE` |
| **COST** | 34 | 4 | 4 | 25% | Score, trust, fwdN, fwdWR, compound | Not recoverable without major lift |
| **Goldmine cluster** | 45 | 4 | 0→85\* | →21.2%\* | **+5 score & trust compound** (Gate 2) **and** WR &lt; 45% (Gate 5) | Forward fix exposes truth; does not pass WR floor |
| **regime_terminal** | ~30 | 5 | 20 | 40% | Score + WR | Gate 5 |
| **super_signals** (e.g. SPY) | 30 | 4 | 131 | ~35% | Score, trust, WR | Multiple gates |

\*After PR **#207** / regen — illustrative.

---

## Todo list

### Done (Cursor / repo)

- [x] **Verify PM `closed_path`** — `audit_trail/dashboard_generator.py` **3480–3486**: `pm_momentum_signals`, `pm_whale_signals`, `pm_kalshi_signals` all use **`closed_path: None`** (no closed ledger in `JSON_PICK_SOURCES`).
- [x] **Document META +13 vs +3** and strict vs base HC distinction (`docs/HC_COPYTRADER_PM_VALIDATION_2026-04-14.md`, this file).
- [x] **Copy-trader / PM by asset class** snapshot (2× `multi_asset_copytrader` EQUITY; 4× PM CRYPTO; all PM fail **Gate 4** with `strat_fwd_trades=0`).
- [x] **Diagnostic tool** — `tools/_hc_noncrypto_diagnostic.py` for post-deploy re-runs.
- [x] **META score root-cause + fix** — traced stacked **`conf_danger_zone` (-10)** + **`long_deadzone_combo` (-12)** on `confidence=0.60` + LONG; shipped **EQUITY forward-proven mitigation** in `audit_trail/quality_gates.py` (`_equity_forward_proven_mitigates_conf_deadzone`). See **`docs/META_SCORE_TRACE_2026-04-14.md`**. Tests: `tests/test_quality_gates.py` (`equity_forward_proven_*`).

### Post-deploy verification (any peer — ~after next dashboard regen)

- [ ] Run `python tools/_hc_noncrypto_diagnostic.py` on **fresh** `audit_dashboard/data/dashboard_data.json`.
- [ ] Confirm `active_total` **97 → 91** if SPORTS strip landed; `SPORTS` count **0**.
- [ ] Goldmine: `strat_fwd_trades` / `strat_fwd_wr` populated; first-hit gate still **Gate 2** + **Gate 5** as expected.
- [ ] **META**: score still **37** or shifted after scoring deploy?
- [ ] `strict_hc_count` **3–6** CRYPTO, **0** non-crypto unless scoring changes (no regression).
- [ ] Optional: `inverse_goldmine_stocks` / baby pipeline status per PR **#208** docs.

### PM outcome pipeline (deferred — multi-day scope)

- [ ] **Design**: close semantics for PM (time horizon vs event resolution vs oracle).
- [ ] **Schema**: closed-trades JSON for `pm_*` sources.
- [ ] **Resolver**: extend or add path in outcome / dashboard so PM rows get **real** `strat_fwd_*` (not zeros).
- [ ] **Wire**: add `closed_path` (or dedicated loader) in `JSON_PICK_SOURCES` + merge into forward stats.
- [ ] **Validate**: `passes_active_gate` / HC gates with populated forward fields.

**Why deferred:** Same *symptom* as goldmine (`strat_fwd_trades == 0`), different *fix*: goldmine had a file + key fix; PM has **no** closed file and needs a **new** tracking pipeline.

### multi_asset_copytrader score depression

- [x] **META** — traced to **conf 0.60** + **LONG** penalties; **EQUITY + forward-validated + n≥50 + WR≥45%** mitigation **shipped** (see above).
- [ ] **COST** / thin forward — still low; no change unless strategy improves.
- [ ] Optional: compare **dashboard** score to **raw** in `copy_trader_intel/data/multi_asset_picks.json` for regression audits.

### Policy / product (human decision)

- [ ] Whether **strict HC** should keep **EQUITY edge ≥ 50** or offer a second preset (“HC gates only”).
- [ ] Whether **PM** deserves a **temporary** forward exemption (high risk; document).

---

## What Cursor cannot do alone

- Schedule a **2:00 PM EST** peer wakeup (human / automation outside repo).
- Run diagnostics on **live** server JSON without a fresh artifact or deploy.
- Implement full **PM closed-loop** without design sign-off.
- Merge PRs or trigger **GitHub Actions** (needs your `gh` / CI context).

---

## Quick reference commands

```powershell
python tools/_hc_noncrypto_diagnostic.py
```

```powershell
# After deploy, from repo root with updated dashboard_data.json
python scratch_investigate_hc.py
```
