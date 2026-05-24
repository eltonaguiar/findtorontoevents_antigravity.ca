# Confidence Methodology — AI Hedge Fund Simulation

## How Confidence is Assigned

No arbitrary numbers. Each pick's confidence is derived from one of three methods:

### Method 1: Persona Win Rate (PREFERRED)
When the persona has n >= 20 resolved picks, confidence = persona WR.
- PG SHORT → invert_losers persona WR=64% → **confidence 64%** ✅
- SOLUSDT LONG → vol_arb persona WR=65% → **confidence 65%** ✅
- TLT, SPY, GLD, SHY → risk_parity persona WR=62.5%, n=124 → **confidence 62.5%** ✅

### Method 2: Model-Reported Confidence (SECONDARY)
When the pick comes from a model that reported its own confidence (0-1 float or HIGH/MEDIUM/LOW string):
- MSFT LONG → model reported 30% → **confidence 30%** (model is uncertain)
- XOM SHORT → model reported 30% → **confidence 30%** (honest uncertainty)
- CL=F SHORT → model reported 80% → **confidence 80%** ⚠️ (may be overconfident)

### Method 3: Imputed (FALLBACK)
When no WR and no model-reported confidence exist:
- SI=F SHORT, NG=F SHORT → **confidence 50%** (coin-flip assumption)
- All PENNY, all FUTURES → **confidence 0%** (no data = no basis)

## Confidence Thresholds

| Level | Range | Meaning | Action |
|-------|-------|---------|--------|
| **HIGH** | ≥ 65% | WR-verified or strong model conviction | Full position size (1.5%) |
| **MEDIUM** | 50-64% | Reasonable confidence, some data backing | Slightly reduced (1.0-1.3%) |
| **LOW** | 30-49% | Honest uncertainty — system admits it doesn't know | Reduced size (0.5-0.75%) |
| **NONE** | < 30% or 0% | No data, no model, no WR | PAPER ONLY — no allocation |

## Why NOT Higher?

⚠️ **80% confidence on n=23 is mathematically unsupportable.**
The vol_arb persona has 65% WR but only 23 resolved picks. The 95% confidence interval on a 65% win rate from n=23 is roughly ±20%. Claiming 80% certainty on individual picks when the base rate is uncertain within a 20-point band is statistical malpractice. The Risk Manager flagged this as the "80% confidence epidemic."

⚠️ **ML calibration is SYSTEM-WIDE INVERTED.**
The live audit page warns: "Confidence is currently an anti-signal across asset classes. The confidence band of 0.85-0.90 is the WORST bucket with a 20% win rate." High model-reported confidence does NOT mean high win probability — it means the opposite in some bands.

## Why NOT Lower?

🟢 **30% confidence can be a FEATURE, not a bug.**
When a model reports 30% confidence on a pick with RR 2.1 (XOM SHORT), it's being honest. The system is telling you: "I'm not sure, but if I'm right the payout is large." This is exactly what you want from a risk system — honest uncertainty enables proper position sizing.

🟢 **Persona WR at n≥100 is the gold standard.**
risk_parity at 62.5% WR with n=124 is the most reliable confidence number in the entire system. It's not the highest, but it's the most trustworthy because the sample is large enough to narrow the confidence interval to ±7%.

## Calibration Gap

| Issue | Impact |
|-------|--------|
| 13 of 19 picks use estimated/imputed confidence | Only 6 picks have WR-verified confidence |
| Persona WR computed on ALL resolved data, not filtered by symbol/class | May overstate or understate symbol-specific WR |
| No Bayesian shrinkage applied | Small-n personas inflated: invert_losers WR 64% on n=11 could regress to mean |
| Confidence-to-WR mapping (Method 3) is linear and untested | 50% confidence → 50% WR assumed, but may not hold |
