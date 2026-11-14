# Peer review — finpredict-v2 (`MASTER_AUDIT.md`) and hilarious-seer (audit summary)

## finpredict-v2 — **CONFIRMED**

Their verdict: *"the pipeline is real engineering, but the published performance is not genuinely
profitable and not statistically sound. It is a multiple-testing + survivorship + stale-price
artifact,"* scored FAIL.

Every element is independently supported by this pass:

| Their claim | My independent measurement |
|---|---|
| Multiple-testing artifact | 170 benchmark ledgers → 4 pass at 95% vs 8.5 expected by chance |
| Survivorship | 142 symbols, 3,500 rows, every class decaying half-to-half (CRYPTO 0.952 → 0.608) |
| Stale prices | `data_freshness` stale warning; `after_cost_net_per_trade` null on 3,500/3,500 rows |
| Not profitable | PF 0.895 overall, −617.5pp; no class above its after-cost breakeven except EQUITY (t=1.52) |

The one thing I would add: their framework scopes the problem correctly but stops short of the
mechanism. The mechanism is stop-fill slippage (+828.0pp, 98.8% of the crypto loss) — see
`02_per_asset_class/ANALYSIS.md` §5. "Stale-price artifact" is true of the *reported* numbers; the
*realized* numbers have their own, larger defect.

Also worth noting: their `01_audit/recommendations/` folder (CI_GATES, DATA_CONTRACT, ROADMAP) is the
most implementable remediation set produced on 2026-11-14. DATA_CONTRACT in particular is the right
shape of fix for the field-population problems this pass found.

## hilarious-seer — **CONFIRMED on all three substantive claims**

1. *"Equity marginal edge but not significant"* — exactly right, and I can put numbers on it: EQUITY
   PF 1.154, +238.3pp, t=1.52, p=0.12, second half PF 0.977. It is the only class above its
   breakeven, and it is not established.
2. *"Heavy multiple-testing (361 families + mutations); survivor bias"* — corroborated and quantified:
   170 ledgers, 4 passes against 8.5 expected. The 361-family count and the 170-ledger benchmark are
   the same problem measured two ways.
3. *"Crypto worst (old median age, many zombies)"* — corroborated: CRYPTO is the only class with
   statistically significant *negative* expectancy (t=−4.84, p<0.001) and the only class with the
   stop-fill defect.

Their other findings — regime layer nearly empty (21 closed-with-regime vs 8,538 without), zombie rows,
freshness gaps — I did not re-verify and mark unverified; they are consistent with the payload's own
`regime_validation.data_coverage` and `data_freshness` sections.

**Minor correction:** the summary's "Observed: APIError 402 on ai-gateway.kilo.ai, roster updated"
section is infrastructure housekeeping, not an audit finding. It is correct to have fixed it, but it
should not sit inside an audit verdict — a reader scoring this document for audit content will weight
a model-roster fix as if it were evidence.

## Cross-program convergence

finpredict-v2, hilarious-seer, flaxen-hair, the research program, and this pass were run
independently, with different methods and different data slices. All five reach "not profitable, not
statistically sound." The only dissenting voice is flaxen-hair's profit document, and its dissent
resolves against it when read against the repo's own benchmark artifact.
