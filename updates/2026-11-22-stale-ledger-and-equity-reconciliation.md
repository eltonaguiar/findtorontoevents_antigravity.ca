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

Both numbers are real. They are computed over different populations:

| population | n | PF | net exp %/trade |
|---|---|---|---|
| audit3 ledger class node (copilot's source) | 942 | 1.0755 | +0.1577 |
| money_ready policy_clean | 115 | 0.6016 | — |
| pf_registry policy_clean | 212 | 0.5189 | −0.0208 |
| pf_registry raw | 281 | 0.4388 | — |
| dashboard recent window, gross | 690 | 1.2289 | — |
| dashboard recent window, net 10bp | 690 | 1.1746 | — |

The audit3 node (n=942, WR 45.0%, mean cost 0.0515%) is the only affirmative EQUITY figure and it is affirmative **after cost** (+0.158%/trade). The policy-clean cohorts — 212 and 115 picks — put the same class at PF 0.52 and 0.60. The 730-pick difference is the whole disagreement: the policy filter excludes picks that audit3 keeps, and those excluded picks carry the profit.

**Verdict:** 'EQUITY is the only +alpha class' is true **for audit3's cohort** and false for the policy-clean cohort. My earlier 0.62 was the policy-clean number. Neither is wrong; quoting either without its n is. The conservative reading stands until the 730 excluded picks are individually justified — but copilot's +0.158%/trade net over 942 is a stronger claim than I gave credit for, and it deserves the justification step rather than dismissal.

For contrast, CRYPTO raw PF is 1.353 over 28,368 while policy-clean is 0.268 over 23,280 — the same ordering effect, much larger. Any 'only EQUITY' claim therefore depends entirely on which cohort the filter keeps.
