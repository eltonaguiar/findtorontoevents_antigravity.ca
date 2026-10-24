# 2026-10-23 — Fund "Say vs Do" Promise-Fidelity Audit (`fund_say_vs_do.py`)

> **NOT FINANCIAL ADVICE** — research/QA only. No recommendations, no signals. Past performance does not guarantee future results.
>
> Author: **OPENCODE_BEAM** (opencode/beam-free) · Date: 2026-10-23 · Branch: `oc/fund-walkforward-review-fixes` (PR #760)

## What was asked

The user asked for an honest analysis of which mutual funds actually **"talk the talk"** — i.e. whether funds *perform* the way their official documents (factsheets / Fund Facts / Fidelity performance tables) say they do — rather than another performance-screen.

## What was built

New tool: `tools/fund_say_vs_do.py` → `audit_dashboard/data/fund_say_vs_do.json`.

For each fund the tool freezes **official-document claims** (objective, benchmark, MER, risk rating, published calendar/period returns — each with source URL and as-of date), then independently recomputes what the fund actually delivered from Yahoo Finance adjusted closes and runs six checks:

| Check | Pass criterion |
|---|---|
| `calendar_check` | published calendar year vs recomputed ≤0.5pp (≤1.0pp for 1-decimal rounded published values) |
| `period_check` | published 1/3/5/10y (and `si`/`life`) NAV CAGR vs matched-window recompute ≤0.75pp |
| `tracking_doc` | published fund−benchmark gaps within ±0.30pp of expected ≈ −MER (index-like funds) |
| `tracking_independent` | recomputed 5y fund vs benchmark proxy (fee/div adjusted) within tolerance |
| `beta_r2` | monthly beta / R² vs benchmark proxy (5y) — style honesty |
| `risk_vs_rating` | realized 5y vol band vs documented CSA risk rating (where stated) |

Plus **peer-agent claim verdicts** (do other agents' fund claims survive recomputation?).

Universe: **XEQT, VFV, TDB902** (Canadian, user-relevant) + **FXAIX, FSPGX, FOCPX** (US).

## Findings — fund verdicts (5 KEPT / 0 DRIFT / 1 UNVERIFIABLE)

| Fund | Verdict | Key evidence |
|---|---|---|
| **XEQT** (MER 0.19%) | **KEPT** | published calendar max Δ 0.29pp; periods Δ ≤0.27pp; vol 13.4% within doc "Medium (3/5)"; beta 0.90 / R² 0.96 vs ACWI proxy |
| **VFV** (MER 0.08%) | **KEPT** | periods recompute within **0.01–0.09pp** of published; tracking −0.11pp/yr mean vs expected −0.08; calendar minor flags 2016/2019 (rounded published values, ≤0.87pp) |
| **TDB902** (MER 0.28%) | **KEPT (doc-verified)** | no Yahoo series (e-series not exchange-listed) → cross-source: TD Fund Facts 10y 15.1% (2026-05-31) vs Fund Library F-series 10y 15.49% (Oct 2026) consistent; fund−bench 10y −0.54pp on 0.28 MER; risk "medium" matches proxy vol 17.9% |
| **FXAIX** (0.015%) | **KEPT** | 1y/3y/5y/10y recompute within **0.03pp**; β=1.00, R²=1.00 vs S&P 500 TR; published tracking gap −0.04pp/yr ≈ fee; `life` (1988) UNVERIFIED — Yahoo FXAIX history starts 2011-05-04 |
| **FSPGX** (0.035%) | **KEPT** | all periods incl. `life` within 0.24pp; β 0.94 / R² 0.984 vs VUG (=Russell 1000 Growth proxy); tracking −0.04pp/yr = fee exactly |
| **FOCPX** (0.73→0.78%) | **UNVERIFIABLE (data-limited)** | Yahoo MF series inconsistent across windows (1y −12.21pp, 3y +2.98pp, 5y +0.45pp vs published) → distribution handling unreliable; **not** treated as doc drift. Doc-internal claim (fund beats its NASDAQ benchmark by +3.8pp/yr over 5y) is directionally corroborated by independent recompute (+3.56pp) |

## Findings — peer-agent claim verdicts

| Claim (source) | Verdict | Evidence |
|---|---|---|
| "FXAIX 5-yr 15.7%/yr, Sharpe 1.03, MDD −23.9%" (Grok deep-dive) | **FAIL — period mislabeled** | 15.72 is FXAIX's **1-year** (as-of 09/30/2026); 5y published 13.78 / recomputed 13.78; recomputed 5y Sharpe (rf=0) 0.85, MDD −24.5 |
| "FSPGX 5-yr 18.2%/yr" (Grok deep-dive) | **FAIL — period mislabeled** | 18.12 is FSPGX's **10-year**; recomputed 5y 13.64 |
| "TDB902 17.08% CAGR" (Zoo winner-hunt) | **FAIL — not confirmed** | both document sources: 15.1% (10y, Fund Facts) / 15.49% (10y, Fund Library F-series); claim is 1.6–2.0pp/yr higher |
| "FOCPX +2.2pp/yr vs VIGAX, 25y" (Buffy) | **PASS (partial window)** | available overlap 2001–2024 (Yahoo VIGAX starts 2000-11): mean annual excess **+2.88pp** (band ±0.75), win 70.8% vs claimed 56%; sub-period 2010–24 = +2.18pp ("stable both legs" corroborated); 1994–2009 leg not verifiable on Yahoo |
| "XEQT MER 0.19%" (GHCOPILOT) | **PASS** | matches iShares factsheet Sep 2026 (older ETF Facts 0.20%; fee cut eff. 2025-12) |

## Uniqueness vs peers (duplicate-check, S3)

Grepped `COMMUNITY/` + `updates/2026-10-2*` for factsheet/Fund Facts/say-vs-do/promise-fidelity work: **zero hits**. Grok's `GROK_20261023_0027_FUND_DEEP_DIVE.md` is a price-derived stats table (no doc-claim recompute); Zoo's `mf_walkforward` tests criteria predictiveness; Buffy's 71-fund screen is performance selection; GHCopilot's crosscheck covers scorecard code. **Nobody else did official-document claim fidelity** — this tool is the complement to all of them (they measure *returns*; this measures *honesty of the stated numbers*).

**Post-commit re-check (same morning):** agent commit `b7a0efc781a` added `updates/2026-10-23-cross-agent-fund-analysis.md` § "Mandate vs delivery" — related but different method: they compute *fund CAGR − ER vs mandate-matched benchmark proxies over up to 30 years* (14 index funds "track to the cent"; DODGX/FCNTX/FOCPX beat style benchmarks). They do **not** recompute printed factsheet/Fund Facts/Fidelity-table claims, don't test calendar-year rows, risk ratings, beta/R², or peer-agent claims. Complementary, not duplicated. **One reconciliation needed:** that doc adopts Zoo's *TDB902 17.08%* as a "talks-the-talk" fact, but its own caveat says the number is **VFV.TO-proxy-modelled with an assumed 0.35% MER** — while TD's official Fund Facts prints **15.1% (10y, as-of 2026-05-31)** and Fund Library's F-series prints 15.49%. Both can coexist only if clearly labelled: *17.08 = proxy reconstruction* ≠ *TDB902's documented return*. Our FAIL verdict applies to the claim *as a TDB902 documented CAGR*.

Reused assets: TD Fund Facts + Fund Library F-series citation (TDB902), Fidelity/Vanguard/iShares official performance tables (claims layer), GHCopilot's 0.9477 one-slot stat (feeds page banner reconciliation), Zoo's 17.08 claim (now verdict-checked).

## Data caveats (documented in JSON)

- **FXAIX `life`**: Yahoo history starts 2011-05-04 → since-1988 return not verifiable from Yahoo (marked `unverified_windows`, not FAIL).
- **FOCPX**: Yahoo mutual-fund series shows inconsistent distribution handling across windows → period check `UNVERIFIABLE` with data-quality caveat; reverify against Fidelity official page before treating as doc drift.
- **TDB902**: not exchange-listed → doc-only mode (cross-source check substitutes for NAV recompute).
- **VIGAX pre-2000**: no Yahoo series → Buffy's 1994–2009 leg unverifiable (partial-window verdict explicitly labeled).
- Proxies: `^SP500TR × USDCAD` for CAD-denominated S&P benchmarks; VUG+0.04pp for Russell 1000 Growth; `^IXIC`+0.9pp est. dividends for NASDAQ Composite; VT+0.06pp for ACWI sanity.

## Verification performed

1. `py_compile` clean.
2. Full run → 6 funds checked, 10,998 price rows × 11 tickers downloaded.
3. Assertion suite (run after final version): schema keys, all 6 fund keys present, verdict expectations (FXAIX/VFV/XEQT/FSPGX/TDB902 KEPT, FOCPX UNVERIFIABLE), FXAIX `life` in `unverified_windows` not fails, FOCPX caveat present, 3 claim FAILs + XEQT-MER PASS, **no credential-like strings in output JSON**, anchor numbers present (FXAIX 1y published = 15.72, VFV 1y published = 18.12) → **all pass**.

## How to rerun

```bash
python3 tools/fund_say_vs_do.py            # writes audit_dashboard/data/fund_say_vs_do.json
python3 tools/fund_say_vs_do.py --out /tmp/test.json
```

## Related

- `updates/2026-10-23-fund-walkforward-review-fixes.md` (PR #760: FXAIX fee-gap/NaN-fallback proofs)
- Page: `audit_dashboard/opencode_paper_trading.html` — say-vs-do scorecard card (deployed via PR #760)
- COMMUNITY: `OPENCODE_20261023_SAYVSDO.MD`
