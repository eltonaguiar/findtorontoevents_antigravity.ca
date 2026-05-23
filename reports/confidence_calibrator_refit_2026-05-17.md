# Confidence Calibrator Refit — Evidence Report (A6)

**Date:** 2026-05-17
**Goal:** #1 (per-asset-class edge on `/audit`)
**Module:** `alpha_engine/confidence_calibrator.py`
**Artifact refit:** `alpha_engine/data/confidence_calibrators.json` (generated 2026-05-17T03:57:39Z)
**Data source:** `audit_dashboard/data/dashboard_data.json::picks.recent_closed` — 3,500 closed picks
**Eval helper:** `tools/eval_confidence_calibrator.py`

## What was done

1. Refit per-class isotonic calibrators via `python -m alpha_engine.confidence_calibrator fit`.
   Picks source = `recent_closed` (3,500 rows). Fit succeeded for CRYPTO/ETF/EQUITY/FOREX/COMMODITY;
   BOND skipped (n=12 < `_MIN_FIT_N`=30).
2. Evaluated calibration quality with Spearman rank correlation (ρ) between confidence and realised
   outcome (win=1 / loss=0), for raw vs calibrated confidence.
3. Acceptance bar (vetted plan): **calibrated ρ ≥ 0.15 AND calibrated ρ > raw ρ.**

## Result 1 — In-sample ρ (fit and eval on all 3,500 picks)

| Class     | n     | raw ρ    | calibrated ρ | in-sample verdict |
|-----------|-------|----------|--------------|-------------------|
| CRYPTO    | 2966  | -0.0699  | +0.0919      | KEEP-OFF          |
| ETF       | 105   | -0.0245  | +0.1164      | KEEP-OFF          |
| EQUITY    | 252   | -0.1673  | +0.2340      | ENABLE            |
| FOREX     | 96    | +0.0217  | +0.0998      | KEEP-OFF          |
| COMMODITY | 67    | +0.1262  | +0.1762      | ENABLE            |
| BOND      | 12    | -0.1276  | n/a          | INSUFFICIENT-N    |

**In-sample numbers are NOT trustworthy on their own.** Isotonic regression is monotone and picks its
own direction (`increasing="auto"`) to maximise fit on the training data. As a result calibrated ρ is
always ≈ `+|raw ρ|` — the calibrator cannot do worse than flipping the sign of the raw ordering. The
in-sample table therefore only tells us the calibrator *can* fit the historical sign; it does not tell
us the sign generalises.

## Result 2 — Out-of-sample ρ (fit on oldest 70%, eval on newest 30%) — the decisive test

| Class     | test n | raw ρ    | calibrated ρ | OOS verdict      |
|-----------|--------|----------|--------------|------------------|
| CRYPTO    | 952    | -0.0598  | +0.0747      | KEEP-OFF         |
| EQUITY    | 30     | -0.4854  | +0.4236      | ENABLE           |
| FOREX     | 27     | +0.5180  | **-0.5180**  | INSUFFICIENT-N   |
| COMMODITY | 27     | +0.0804  | +0.0330      | INSUFFICIENT-N   |
| ETF       | 13     | -0.1666  | +0.0514      | INSUFFICIENT-N   |
| BOND      | 0      | n/a      | n/a          | INSUFFICIENT-N   |

Key findings:
- **EQUITY** — the only class that passes the bar out-of-sample. The confidence inversion is stable
  in time (raw ρ negative on both old and new slices), so the decreasing calibrator generalises:
  cal ρ +0.42 ≥ 0.15 and beats raw ρ.
- **FOREX** — a cautionary case. Train slice fit the calibrator *increasing*; the newest 30% has the
  **opposite sign** (raw ρ +0.52). The stale increasing calibrator therefore **actively destroys a
  real signal**, flipping +0.52 to -0.52. FOREX confidence sign is unstable — do NOT calibrate.
- **CRYPTO** — out-of-sample cal ρ +0.07, below the 0.15 bar. The inversion is weak and the
  calibrator does not lift it past threshold. KEEP-OFF.
- **ETF / COMMODITY / BOND** — out-of-sample test n is 0–13, far below `_MIN_FIT_N`. The in-sample
  "ENABLE" for COMMODITY does not survive the split (n=27, cal ρ +0.03). INSUFFICIENT-N.

## Per-class verdict

| Class     | Verdict          | Rationale |
|-----------|------------------|-----------|
| EQUITY    | **ENABLE**       | OOS cal ρ +0.42 ≥ 0.15 and > raw ρ; inversion stable across time split (n=252 total, n=30 OOS). |
| CRYPTO    | KEEP-OFF         | OOS cal ρ +0.07 < 0.15; weak/unstable inversion. |
| FOREX     | KEEP-OFF         | Sign of confidence flips between slices; stale calibrator inverts a real +0.52 signal. Dangerous to enable. |
| COMMODITY | INSUFFICIENT-N   | In-sample ENABLE does not survive time split (OOS n=27, cal ρ +0.03). Re-evaluate at n≥100. |
| ETF       | INSUFFICIENT-N   | OOS n=13. Re-evaluate at n≥100. |
| BOND      | INSUFFICIENT-N   | n=12 total, below `_MIN_FIT_N`=30; no calibrator fit. |

## Overall recommendation on `CONFIDENCE_CALIBRATION_ENABLED`

**Do NOT flip the global `CONFIDENCE_CALIBRATION_ENABLED` flag on.** The flag is all-or-nothing across
every asset class, and only 1 of 6 classes (EQUITY) passes the acceptance bar out-of-sample. Enabling
globally would apply unvalidated CRYPTO/FOREX/COMMODITY/ETF calibrators — and for FOREX the current
calibrator demonstrably *inverts* a real signal. CRYPTO is 85% of closed-pick volume, so a global
enable is dominated by a calibrator that fails the bar.

**Recommended path:**
1. Keep `CONFIDENCE_CALIBRATION_ENABLED=0` (unchanged — not modified by this task).
2. The refreshed `confidence_calibrators.json` is committed so it is current when a per-class enable
   mechanism lands.
3. **Follow-up (separate PR): make calibration per-class opt-in.** Add a per-class allowlist (e.g.
   `CONFIDENCE_CALIBRATION_CLASSES=EQUITY`) checked inside `calibrate()`, so EQUITY — the one class
   with proven, time-stable edge — can be calibrated without risking the others. That PR can cite
   this report as its evidence.
4. Re-fit cadence: the in-code docstring's known-limitations note still applies — resolver-bug label
   contamination affects FOREX/COMMODITY/EQUITY win labels. EQUITY's inversion survived the time split
   regardless, but a daily GH Actions refit step remains advisable.

## Reproducer

```
python -m alpha_engine.confidence_calibrator fit          # refit calibrators.json
python -m tools.eval_confidence_calibrator                 # in-sample raw vs cal rho
python -m tools.eval_confidence_calibrator --oos           # out-of-sample 70/30 time split
```
