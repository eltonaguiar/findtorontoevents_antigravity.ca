"""J1-J5/M1-M5: adversarial peer review of the CORRECTED fund numbers."""
import json, urllib.request, sys

NUMBERS = """
Window 2021-11-15..2026-11-13, 1,255 daily adjusted closes (dividends reinvested,
independently verified via SGOV control: - price-only T-bill = 0%/yr, observed 3.90%/yr).
Cash hurdle Rf = 3.81%/yr.

FUNDS (fee-adjusted):                      net CAGR   vol    Sharpe  Sortino  maxDD
  FXAIX (S&P500 MF, 0.015%)                 11.66%    17.2%   0.457   0.652   -24.5%
  SPY   (S&P500 ETF, 0.0945%)               11.48%    17.3%   0.443   0.634   -24.5%
  FZROX (total mkt MF, 0.00%)               10.74%    17.6%   0.393   0.560   -25.1%
  VTI   (total mkt ETF, 0.03%)              10.49%    17.7%   0.379   0.539   -25.4%
  VTSAX (total mkt MF, 0.04%)               10.48%    17.6%   0.379   0.539   -25.4%
  BND   (total bond ETF, 0.03%)             -0.32%     6.1%  -0.680  -0.932   -17.3%
  SGOV  (0-3mo T-bill, 0.09%)                3.81%     0.2%   n/a     n/a     -0.03%

90% bootstrap CI on CAGR (21-day moving blocks, 1000 draws, fixed seed):
  SPY   [-0.10, 24.92]   FXAIX [0.01, 25.02]   VTI [-1.34, 24.09]
  BND   [-4.75, 4.17]    SGOV  [3.57, 4.27]

PAIRED DIFFERENCE (gross | fee advantage | NET):
  FXAIX-SPY  +0.051 | 0.0795 | +0.131   distinguishable from 0: NO
  FZROX-VTI  +0.192 | 0.0300 | +0.222   NO
  VTI-VTSAX  +0.013 | 0.0100 | +0.023   NO

SUB-PERIODS (FXAIX-SPY):  H1 gross +0.099 net +0.178 | H2 gross -0.021 net +0.059
  -> GROSS FLIPS SIGN, net stays positive. Only the FEE is durable.

60/40 SPY/BND rebalancing (5bp spread on traded fraction):
  buy&hold 7.45% CAGR / Sharpe 0.306 / turnover 0.00
  daily    7.03% / 0.282 / 2.28
  monthly  6.91% / 0.273 / 0.45
  quarterly 6.78% / 0.262 / 0.17
  -> more rebalancing LOWERED return (kept buying a falling bond sleeve).

FORWARD ANCHORS (fetched 2026-11-23): 13wk T-bill ^IRX = 4.12% as of 2026-11-20
  (vs 3.81% trailing SGOV); BND yield-to-maturity = 4.11% (vs -0.29% trailing CAGR).

CONCLUSIONS DRAWN:
 1. FXAIX's fee edge over SPY (0.0795pp/yr) is contractual and durable; its
    realised outperformance is noise and changed sign mid-window. You cannot
    show it "beat" SPY, only that it is cheaper.
 2. Ranking equity funds on 5y CAGR is unsupported - CIs span ~25pp.
 3. On CURRENT yields BND is expected to contribute ~+4%/yr, inverting the
    original "60/40 gives up return" conclusion.
 4. MF-vs-ETF is a tax-and-minimum question, not a return question.
 5. Futures are OUT OF SCOPE: adjusted closes cannot express roll yield,
    contango, margin or financing.
"""

PROMPT = f"""You are a skeptical quant reviewer. Below is a corrected analysis of
index-fund choice. Find the STRONGEST remaining methodological objection.

{NUMBERS}

Answer concisely:
A) The single most damaging remaining flaw (if any), stated precisely.
B) Any arithmetic or statistical error in the numbers above.
C) One confound that would change conclusion (3).
D) Verdict: are conclusions 1-5 supported by the evidence shown? For each: SUPPORTED / OVERSTATED / WRONG.
Do not restate the data. Be adversarial but fair. Under 350 words."""


def ask(model):
    body = json.dumps({"model": model, "prompt": PROMPT, "stream": False,
                       "options": {"temperature": 0.2, "num_predict": 700}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)["response"].strip()


for m in sys.argv[1:] or ["qwen2.5:32b"]:
    print(f"\n{'='*70}\n=== {m}\n{'='*70}")
    try:
        print(ask(m))
    except Exception as e:
        print(f"  ERROR: {e}")
