# Stale ledger, live ledger, and the EQUITY "+alpha" disagreement — 2026-11-22

## 1. Why every number this session was a month old

`audit_dashboard/data/dashboard_data.json` is **gitignored** (`.gitignore:222`) and
untracked, so it is a local artifact that nothing refreshes on this machine. The
copy present here was built **2026-10-19T19:40**, its newest closed pick was
2026-10-19, and it held **0 picks from the last 7 days** — exactly the "~34 days
stale" a peer reported.

Production was never stale. The live file:

```
generated_at   2026-11-22T04:00:19Z
last-modified  Sun, 22 Nov 2026 04:07:44 GMT
content-length 25,804,703
repo_sha       749e356a05f97d12d0dafdaab340880ed4a75f23
payload_lag    2,488s
```

So the correct fix was not to re-run the generator — it was to stop reading a
30-day-old local cache. The live build has been fetched over it and **all analyses
regenerated** (`reports/2026-11-22-ledger-net-cost-oos.*`, `...-data-health.*`,
`...-first-touch.*`). The stale copy is kept at `/tmp/dashboard_data.stale-20261019.json`.

## 2. Current build, net of cost

| class | n | PF gross | PF net | exp gross % | exp net % |
|---|---|---|---|---|---|
| CRYPTO | 1,835 | 0.624 | 0.553 | -0.7589 | -0.9589 |
| EQUITY | 782 | 1.034 | 0.990 | +0.0768 | -0.0232 |
| ETF | 588 | 1.038 | 0.954 | +0.0438 | -0.0562 |
| FOREX | 204 | 1.203 | 0.857 | +0.0424 | -0.0376 |
| COMMODITY | 50 | 0.165 | 0.153 | -2.8119 | -2.9319 |
| BOND | 37 | 0.904 | 0.726 | -0.0456 | -0.1456 |
| FUTURES | 4 | 2.026 | 1.901 | +1.4353 | +1.3153 |

Data health on the current build: **EXIT_SIGN=22**, **FLAT=40**, **GAIN_BEYOND_LEVELS=420**, **LEVELS=48**, **NO_MOVE=1**.

First-touch on the current build: 1787 crypto picks re-walked, 974 first-touch changes, recorded PF 0.620 -> honest 0.907.

## 3. Settling 'EQUITY is the only +alpha class'

My first pass at this compared a stale local `money_ready_verdict.json` against a
stale local `audit3_ledger.json`, and concluded EQUITY was really 0.52-0.60. That
conclusion was wrong for the same reason the ledger numbers were wrong. Re-fetched
from the live surfaces:

| surface (LIVE) | generated | n | PF | WR | net exp %/trade |
|---|---|---|---|---|---|
| audit3 EQUITY | 2026-11-22T06:35 | 956 | **1.0499** | 44.8% | **+0.1058** |
| audit3 CRYPTO | 2026-11-22T06:35 | 6,926 | 0.7886 | 39.4% | −0.4183 |
| money_ready EQUITY policy_clean | 2026-11-22T03:58 | 121 | **1.0800** | 34.7% | — |
| money_ready CRYPTO policy_clean | 2026-11-22T03:58 | 22,287 | 0.2621 | 41.0% | — |

Local copies, for contrast: EQUITY policy_clean 0.6016 (n=115) and audit3 EQUITY
1.0755 (n=942), both generated 2026-11-20 — two days stale, which was enough to
flip the sign of the policy-clean number.

**Verdict: copilot is right, and I was wrong.** On current data EQUITY is the only
class with PF above 1 on both the audit3 cohort (1.05, n=956, +0.106% net) and the
policy-clean cohort (1.08, n=121). CRYPTO is 0.26-0.79 and negative net.

Two limits on that verdict, so it is not over-read:
* On the 782-pick recent window, EQUITY is PF 1.034 **gross** and 0.990 **net at
  10bp**, expectancy +0.0768% gross / −0.0232% net. So it clears 1.0 only on the
  audit3 cohort and only by ~5%, and it does not clear cost on every cut.
* "Only positive class" is not "+alpha at scale": 121 pick-weight policy-clean
  picks and a 5% PF margin is a candidate, not an edge.

The general lesson, which applies to the whole session: **gitignored artifacts on
this machine lag production by 2-34 days and quoting them silently flips signs.**
Every number in this report is now from a live fetch, with the fetch timestamp on it.
