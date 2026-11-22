# Registry R5 cleared: six affirmative entries now carry numbers — 2026-11-22

## What was broken

`tools/registry_metric_audit.py` rule **R5** flags an affirmative status whose
`result` field is prose. Six hypotheses were in that state — H-120, H-126, H-127,
H-128, H-129, H-133 — which meant every one of their verdicts was unfalsifiable
by machine: you could not check whether the status followed from the numbers
because the numbers only existed inside a sentence.

Worse, three of the six contradicted themselves in plain English:
H-126's prose says "sub-bar (0.98<1.15)" under `FORWARD_SHADOW`;
H-133's says "STRONGEST candidate ... but NOT promotable ... beta+survivorship"
under `FORWARD_SHADOW`; H-127/128/129 say "Untested"/"BLOCKER" under a status
that asserts a forward shadow exists.

## What changed

Each `result` is now a dict. The original prose is preserved verbatim under
`summary` in every case — nothing was deleted, only structured.

| id | status before | status after | why |
|---|---|---|---|
| H-120 | SUPPORTED | **SUPPORTED** (unchanged) | the inflation rule *does* generalize: 3 confirmations, ratios 2.8x / 2.09x / 1.18x |
| H-126 | FORWARD_SHADOW | **TESTED_WEAK** | real and stable, CI-LB 0.980 vs 1.15 bar; not promoted |
| H-127 | FORWARD_SHADOW | **REGISTERED_BLOCKED_ON_DATA** | never backtested; COT ingestion missing |
| H-128 | FORWARD_SHADOW | **REGISTERED-UNTESTED** | never backtested; cost-amplitude blocker |
| H-129 | FORWARD_SHADOW | **REGISTERED-UNTESTED** | never backtested; lower priority than H-128 |
| H-133 | FORWARD_SHADOW | **TESTED_WEAK** | long-short CI-LB 0.967 < 1.15: beta + survivorship, not alpha |

Key figures now in the registry rather than in a paragraph:
H-126 `n=11205, n_eff=249, net_pf=1.160, ci_lb=0.980, is/oos 1.15/1.17`;
H-133 `net_pf=1.768, ci_lb=1.284, n_eff=47, ex-mega-cap long CI-LB 1.210,
beta-neutral long-short CI-LB 0.967`; H-120 `honest_pf 1.28 / 1.07 vs daily
2.67 / 1.26`, `honest_net_ci_lower_bound 0.92 / 0.77`, `promotable_survivor=false`.

## Disclosure: H-120's threshold was re-scoped

H-120's `acceptance_criteria` used to hold `min_ci_lb: 1.15` at top level next
to a rule string that says that bar governs *"a promotable survivor"* — which
the hypothesis explicitly does not claim. Left there, any structured metrics
would make the audit compare 0.92 against a bar for a different claim. The
number was moved into `promotion_bar: {min_ci_lb: 1.15, applies_to: ...}`,
with the `rule` string unchanged, and a new
`min_strategies_showing_inflation: 2` criterion that encodes what SUPPORTED
actually asserts (observed: 3). No threshold value was changed and no
hypothesis's claim was widened; the numbers 0.92 and 0.77 remain visible in
`honest_net_ci_lower_bound` — they simply no longer get compared to the wrong
claim.

## Verified

```
python3 tools/registry_metric_audit.py     (before) I1 57  R3-nonaff 7  R5 6
python3 tools/registry_metric_audit.py     (after)  I1 57  R3-nonaff 9  R5 0
R3 remaining: []      hypotheses: 111 -> 111 (none added, none dropped)
```

The two added `R3-nonaff` rows are the intended ones — H-126 `ci_lb=0.98 <
1.15` and H-133 `n_eff=47 < 80` — now machine-visible as "failed its own bar
and did not claim otherwise". Pre-fix snapshot kept at
`reports/2026-11-22-registry-numeric-audit-before-r5fix.json`.
