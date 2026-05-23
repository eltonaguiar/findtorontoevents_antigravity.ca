# Proposed approach v3 — remaining /audit enhancement items (2026-04-20)

**Supersedes:** v1 ([`REMAINING_ENHANCEMENT_PROPOSALS_2026_04_20.md`](REMAINING_ENHANCEMENT_PROPOSALS_2026_04_20.md)) and v2 ([`REMAINING_ENHANCEMENT_PROPOSALS_V2_2026_04_20.md`](REMAINING_ENHANCEMENT_PROPOSALS_V2_2026_04_20.md))

**Status:** revised after 6 peer reviewers (Engineering, Product, Statistical, Ollama-style Ops, DeepSeek-style Formal, Mercury-style Quant). All 6 agreed v2's Phase 0 "ship today" banner was not safe to ship as written.

## What all six reviewers converged on

**Do NOT ship the PF-only banner.** Numbers in isolation mislead users who then size positions on them.

### Six independent critiques (by reviewer)

| Reviewer | Core critique |
|---|---|
| Engineer | Wrong layer, `setdefault` propagates stale, ordering bug (is_smart_pick reads stale trust_tier), concurrency across N scanners |
| Product | v1 sequencing backwards, Phase 0 was user-facing priority |
| Statistical | PF 1.61 @ n=62 has 95% CI ~[1.15, 2.30]; "most reliable" overclaims; post-block subset is survivorship fit |
| Ollama-ops | Phase 0 isn't really 30 min; banner failure modes undefined; Wilson LB band will flicker without hysteresis |
| DeepSeek-formal | Wilson LB ≥ 0.45 at n=20 only discriminates WR 0.78 vs 0.50 (not 0.60 vs 0.50); nested feeds not independent; `is_smart_pick` signature ambiguous; block-bootstrap needed |
| Mercury-quant | Banner is risk-naked without Sharpe/DD/net-of-cost; regime decomposition required; S4-gate violation (62 picks likely in single regime) |

## What's actually shippable (v3 plan)

### Phase 0 — REFRAME (not banner; ~15 min)

Instead of a PF-only banner that reviewers say is misleading, ship the **minimum non-misleading user-facing change**:

**(a) Hide the n=0 Guide band** (`PROVEN + confidence 0.8-0.9`). Simple, honest. Universally approved by reviewers. ~5 min.

**(b) Tier-trust legend** (descriptive only — no numbers):
> 🟢 **High Conviction** — strictest gate. Retained for small-sample edge validation.
> 🔵 **Smart Picks** — passes per-asset floors + direction filters.
> 🟡 **Verified Alpha** — proven trust tier; check sub-cohort before sizing.
> ⚪ **Active** — all live picks.

No PF numbers. Descriptive only. Users still understand the hierarchy without over-promised point estimates. ~10 min.

**Defer the PF banner entirely** until Phase 4 (below) delivers risk-adjusted metrics.

### Phase 1 — At-issue stamping (unchanged from v2, ~3 hours)

Engineer review changes stand:
- Stamping lives in `audit_trail/stamp_pick_quality.py` (post-trust_tier, serialized)
- Overwriting semantics (not `setdefault`)
- `at_issue_*` twins written once at ACTIVE → CLOSED transition

**NEW from DeepSeek:** make `is_smart_pick`'s signature explicit:
```python
def is_smart_pick(pick: dict) -> bool:
    """Evaluate against gate state AT pick's open timestamp.
    
    Reads at_issue_trust_tier / at_issue_strat_fwd_wr if stamped; else
    returns None (not False — caller must distinguish 'failed gate' from
    'not stampable at this time').
    """
```

Tier membership is `tier_at_entry(pick) := tier(pick, T_open(pick))` — immutable post-open.

### Phase 2 — Backfill (revised, ~1 day)

v2 said "else current state" fallback. DeepSeek: that's a look-ahead leak. Mercury: whole dataset becomes contaminated.

**Revised:** picks lacking `at_issue_trust_tier` get `is_smart_pick = null`, not a fake stamp. Coverage ratio published (e.g. "stamped: 2,100/3,500 picks"). Analytics must exclude nulls from denominators.

Statistical-review addition: use **blocklist @ `T_open(pick)`**, not HEAD, when evaluating retrospective counterfactuals. Git-log the blocklist file for point-in-time state.

### Phase 3 — HC evaluator parity test (revised, ~0.5 day)

Ollama-ops: don't use headless browser in CI. DeepSeek: 500 picks is too few to catch rare divergence.

**Revised:** port `hc_filter.js` to a Node CLI (pure function eval), run against **full 3,500 closed picks** offline. Commit the parity-diff artifact. Continuous shadow-eval for 2 weeks post-launch comparing JS vs Python on every new pick.

### Phase 4 — Risk-adjusted metrics pipeline (NEW; gates any future banner)

Mercury + Statistical reviewers: no banner ships without these. Required per-feed metrics for any public number:

1. **Sharpe** (annualized, per-trade stdev-based)
2. **Max drawdown** (% equity, duration)
3. **Net-of-cost PF** (assuming realistic taker fees + 10-20 bps slippage; state the assumption)
4. **Expectancy in R** (average win / average loss)
5. **Regime decomposition**: 3×3 grid (F&G bucket × BTC-trend regime). Flag any cell with n<10.
6. **95% CI on PF** via block-bootstrap on `strategy_id` (not independent-sample CI). Use `as_of` timestamp; refresh weekly.

Only once all six are computed and freshened weekly should a headline number appear on /audit.

### Phase 5 — Wilson LB gate revision (NEW; for Guide band re-enablement)

v2 proposed `wilson_lb ≥ 0.45 AND n ≥ 20`. DeepSeek computed: at n=20, WR=0.65 vs 0.50 has only 42% power. The gate discriminates 0.78 vs 0.50.

**Revised gate:**
- `wilson_lb ≥ 0.52` (requires meaningful positive edge, not just "probably above random")
- `n ≥ 50` (for ~80% power at 15pp effect)
- **Hysteresis**: activate at 0.52, deactivate at 0.47. Prevents band from flickering.
- **Bonferroni**: if multiple filters use this gate, α=0.05/k → confidence 1-0.05/k.

### Phase 6 — MFE/MAE (NEW, medium-term)

Mercury: without MFE/MAE on closed rows, no one can answer "survivable DD?" for position sizing. Closed-pick schema expansion needed.

- Add `max_favorable_excursion_pct`, `max_adverse_excursion_pct` to `_CLOSED_PICK_KEEP_FIELDS`.
- Upstream writers need to populate these at TP/SL resolution. Not trivial — likely a 2-3 day plumbing task.

Not on the critical path, but must happen before position-sizing recommendations are made.

## Revised sequencing

| Phase | Effort | User visible | Ship order |
|---|---|---|---|
| 0 — Hide n=0 band + descriptive legend | ~15 min | Yes (minimal) | 1 |
| 1 — At-issue stamping (post-trust_tier) | ~3 h | No | 2 |
| 3 — HC parity test (Node CLI, full 3,500) | ~0.5 d | No | 3 |
| 2 — Backfill w/ null-stamp + blocklist@T | ~1 d | Partial | 4 |
| 5 — Wilson LB gate revision + hysteresis | ~2 h | Partial | 5 |
| 4 — Risk-adjusted metrics pipeline | ~3-5 d | **Yes (future banner)** | 6 |
| 6 — MFE/MAE schema + writer plumbing | ~2-3 d | No | 7 |

Phase 0 is now ~15 min (descriptive only, no numbers). The banner that v2 promised is deferred to Phase 4 after risk-adjusted metrics land.

## Six key changes from v2 → v3

1. **Phase 0 banner dropped.** Replaced with descriptive-only legend + hide n=0 band.
2. **Wilson LB gate raised from 0.45 → 0.52 with hysteresis**, n from 20 → 50. Bonferroni added.
3. **`is_smart_pick` signature fixed**: tier_at_entry, not recomputed per render.
4. **Backfill null-stamps unknowns** instead of forward-filling from current gate.
5. **Blocklist snapshot by timestamp** (git-log @ T_open), not HEAD.
6. **New Phase 4** (risk-adjusted metrics) gates any future headline number.

## Open questions where v3 is still uncertain

1. Descriptive legend copy — are the four labels (🟢🔵🟡⚪) intuitive, or does this need user testing?
2. Is n≥50 too strict? Some feeds (HC itself at n=62) barely clear it. Raising it to 100 would exclude HC. Thoughts?
3. Should Phase 4 block-bootstrap on `strategy_id` or `(strategy_id, symbol, direction)`? The latter is more conservative.
4. MFE/MAE plumbing — is there appetite for the 2-3 day schema work, or defer indefinitely?
5. Banner copy design once Phase 4 lands: 6 metrics per feed is a lot of text. Progressive disclosure (one-line summary + expandable detail) or full table?

## Reviewer attribution

- **Engineer-lens** (v1 critique, incorporated in v2): wrong layer, setdefault, ordering, concurrency
- **Product-lens** (v1 critique, incorporated in v2): sequencing, 30-min MVP
- **Statistical** (v2 critique, incorporated in v3): CI, survivorship, power
- **Ollama-ops** (v2 critique, incorporated in v3): deployment risks, band flicker, CI browser flake
- **DeepSeek-formal** (v2 critique, incorporated in v3): formal power analysis, signature ambiguity, nested feeds, block-bootstrap
- **Mercury-quant** (v2 critique, incorporated in v3): risk-naked banner, S-ladder gate, regime decomp, MFE/MAE absence

Six reviewers, six critiques incorporated, v3 is the synthesis.

---

## Cross-references

- v1: `docs/REMAINING_ENHANCEMENT_PROPOSALS_2026_04_20.md`
- v2: `docs/REMAINING_ENHANCEMENT_PROPOSALS_V2_2026_04_20.md`
- `docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md`
- `docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md`
- `docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md` — S-stage ladder cited by Mercury
