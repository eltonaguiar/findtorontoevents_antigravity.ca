# Pick-Funnel single-source concentration audit — validated (2026-05-29)

Audit of findtorontoevents.ca/audit/pick_funnel.html for single-source concentration.
Data: live `at_raw_picks`, decisive picks (WON/LOST), all-time. Peer-reviewed via
/PeerReviewSwarmOptions (consult_multi reasoning4: nvidia/kimi, nous/Hermes-405B, fireworks/kimi).

## Finding: only CRYPTO is genuinely source-diversified. Everything else is concentrated.

The funnel flags single-source by **top-source-share > 60%**. That metric has a blind spot the
swarm flagged: it treats engine aliases as separate sources. Collapsing the alpha_engine family
(`alpha_engine_unified` + `AlphaEngine` + `alpha_engine`) and adding HHI:

| Class | decisive n | raw top-share | FAMILY top-share | HHI | verdict |
|-------|-----------:|--------------:|-----------------:|----:|---------|
| FUTURES | 2859 | 87.9% | **96.2%** (alpha_engine) | 0.93 | CONCENTRATED |
| ETF | 162 | 38.9% (looked "ok") | **72.2%** (alpha_engine) | 0.53 | **CONCENTRATED — was a false OK** |
| EQUITY | 8559 | 59.4% (smart_money) | 59.4% | 0.50 | CONCENTRATED (by HHI) |
| FOREX | 6224 | 54.3% | 59.1% (alpha_engine) | 0.47 | CONCENTRATED |
| MEMECOIN | 365 | 64.1% (audit_trail_local) | 64.1% | 0.46 | CONCENTRATED |
| PENNY_STOCK | 19 | 52.6% | 52.6% | 0.46 | concentrated (tiny n) |
| CRYPTO | 4915 | 32.0% (audit_trail_local) | 32.0% | 0.19 | OK — diversified |

## Peer-review consensus (3 models)
1. **Threshold:** >60% top-share is defensible but crude → **supplement with HHI ≥ 0.35** (and/or top-two ≥ 80%). For small-n classes (n<500, e.g. MEMECOIN/ETF/PENNY) raise the bar (~65%) for sampling error.
2. **FUTURES (96% family, HHI 0.93): "concentration, not edge" is CORRECT** — overwhelming at n=2859. Single-source is acceptable only if the source is an independent validated oracle; an internal engine's quirks/bugs are not a diversified, replicable signal.
3. **EQUITY (59%) & FOREX (54-59%) should be flagged too** — both clear HHI≥0.35.
4. **Remediation:** require **N≥2 independent sources** before any per-class edge claim; gate or down-weight concentrated classes out of active/smart picks; show HHI + family-collapsed share on the funnel, not just raw top-share.
5. **Biggest blind spot (now fixed here):** raw top-source-share treats engine aliases as distinct sources → it UNDERSTATES concentration (ETF read 39% but is 72% one engine family). Collapse aliases before computing.

## Action for the funnel
Add an HHI column + alias-collapsed family-share to `build_nav_surface_matrix.py` / the concentration
flag, and flag a class CONCENTRATED if (family-top-share > 60% OR HHI > 0.35). Under that rule, **6 of 7
classes are concentrated; only CRYPTO passes** — and even CRYPTO needs the Smart-Picks surface checked
separately (CLAUDE.md notes 91.7% single-source on the CRYPTO Smart-Picks cell).

Reproducer: `python3 -c` over `at_raw_picks` GROUP BY asset_class, source_system; collapse `alpha_engine*`→one; HHI = Σ(share²). NFA.

---
## CORRECTION (2026-05-29, after operator challenge): engine-family share is the WRONG unit

Operator's point: "one engine family doesn't necessarily mean concentrated if the engine runs
different strategies." **The data confirms this — the engine-family verdict above OVERSTATED concentration.**
`alpha_engine` is a META-ENGINE running many methodologically-distinct strategies. The correct unit is
the `strategy` field, not `source_system`. Strategy-level decisive-pick distribution:

| Class | engine-family share | # distinct strategies | top-strategy share | strategy HHI | corrected verdict |
|-------|--------------------:|----------------------:|-------------------:|-------------:|-------------------|
| FUTURES | 96% | 19 | 22.1% | 0.14 | DIVERSIFIED (cta_momentum 24 / cot_positioning 19 / futures_momentum 14 / golden_cross / connors_rsi2 / bb_mean_rev) |
| CRYPTO | 32% | 216 | 21.6% | 0.08 | DIVERSIFIED |
| ETF | 72% | 30 | 24.7% | 0.12 | DIVERSIFIED (engine label was misleading — NOT a real concentration) |
| FOREX | 59% | 61 | 32.7% | 0.20 | reasonably diversified |
| MEMECOIN | 64% | 21 | 25.2% | 0.15 | DIVERSIFIED |
| PENNY_STOCK | 53% | 10 | 21.1% | 0.14 | diversified (tiny n) |
| **EQUITY** | 59% | 48 | **59.4% (smart_money_consensus)** | **0.44** | **CONCENTRATED — the only genuine case** |

**Corrected conclusion:** measure concentration at the **strategy** level, not source_system/engine. By that
(correct) lens, **only EQUITY is strategy-concentrated** (`smart_money_consensus` = 59% of decisive EQUITY
picks, HHI 0.44). FUTURES/CRYPTO/ETF/FOREX/MEMECOIN are signal-diversified despite a single dominant engine label.

Engine-level concentration is a *secondary* risk (shared code/data/bug-surface, single point of failure) worth
monitoring, but it is NOT "concentration, not edge" — that label only fits single-STRATEGY dominance.

**Remediation (operator's 2nd point — "if concentrated to 1 strategy, add more"):** for EQUITY, add
diversified equity strategies (value/quality/PEAD/low-vol/cross-sectional momentum) to dilute
`smart_money_consensus` below ~40% / push strategy-HHI < 0.25. The other classes need no concentration action.

**Funnel fix (revised):** flag a class concentrated on **strategy-level** top-share > 50% OR strategy-HHI > 0.30
(NOT engine/source share). Under this correct rule: 1/7 classes (EQUITY) flagged, not 6/7.
