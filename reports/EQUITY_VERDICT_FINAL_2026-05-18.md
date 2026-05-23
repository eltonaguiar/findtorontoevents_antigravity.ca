# EQUITY Verdict — FINAL — 2026-05-18

Closes the multi-turn EQUITY contradiction investigation (PRs #1213, #1215).
Supersedes the "resolver broken" sub-claim in `equity_source_reconcile_2026-05-18.md`.

## The chain

1. Swarm Option A → `at_consensus_picks` MySQL shows EQUITY WR 1.2% (n=738).
2. `equity_source_reconcile` → 4+ EQUITY records, WR 1.2%–53.3%. Root cause
   posited: "no canonical resolved-pick set" + "non-crypto resolver broken".
3. **Investigator correction:** the non-crypto resolver is **NOT broken** —
   fixed in `outcome_resolver.py` v2 (2026-04-28) / v2.1 (05-02) / v2.2 (05-09):
   per-class 5bp threshold, bar-replay TP/SL detection, TIME_EXIT_REPLAY. The
   `at_consensus_picks` WR 1.2% is the resolver *correctly* classifying a weak
   consensus-layer pick set, not a bug.
4. **The canonical source already exists:** `pf_registry.json` (M-067,
   `canonical_view = by_asset_class_policy_clean_net`).

## The canonical answer

`pf_registry.json::by_asset_class` (policy-clean, net-of-slippage, deduped):

| class | n | WR | PF | verdict |
|-------|---|-----|-----|---------|
| **EQUITY** | **33** | **33.3%** | **0.60** | **NO EDGE** |
| COMMODITY | 173 | 42.2% | 1.11 | sub-floor |
| CRYPTO | 6353 | 41.0% | 0.88 | sub-floor |
| FOREX | 475 | 25.3% | 52.5* | *single-pair outlier — fake |
| FUTURES | 127 | 4.7% | 0.11 | catastrophic |

`counts`: raw 14,704 rows → closed 12,054 → deduped 7,209 → **policy-clean
2,446**. Dropped: **4,830 duplicate re-emissions + 4,763 policy-excluded**.

## Why the dashboard said EQUITY WR 53%

`asset_class_health` / `hf_stats` / `by_asset_class` (dashboard) report EQUITY
WR 52–54% because they **recompute independently on the un-deduped,
non-policy-clean ledger** — counting the 4,830 duplicate re-emissions and
4,763 policy-excluded picks. `asset_class_health` has a registry-backed mode
(`_registry_backed_ac_breakdown`, M-067) but it is gated `AUDIT_HEALTH_SOURCE=
registry` and defaults to the legacy recompute.

**The "EQUITY = best candidate / T2 / SAFE" label — in Kimi's audit, the
HYPERFOCUS data, the MASTER_ACTION_PLAN — was an inflated-data artifact.** The
canonical policy-clean number is EQUITY PF 0.60, WR 33%, n=33.

## Verdict

EQUITY has **no edge** — canonical-confirmed. The session's no-edge conclusion
holds for EQUITY too; it was only ever in doubt because the dashboard surfaced
a non-canonical inflated view. No class in `pf_registry.json` policy-clean
clears the bar — every one sub-floor or outlier-fake.

## The one real fix (upstream, peer-coordinated)

Not the resolver (fine). The fix: **make the dashboard default to the canonical
`pf_registry.json` source** — flip `AUDIT_HEALTH_SOURCE` to `registry`, and
point `hf_stats` / `by_asset_class` at the same registry view. Then `/audit`
stops showing the inflated 53% and shows the verdict-grade 33%. That is a
`dashboard_generator.py` change (peer-hot — coordinate with codebuff).

Until then: cite `pf_registry.json::by_asset_class` for any EQUITY claim, never
the dashboard tiles.
