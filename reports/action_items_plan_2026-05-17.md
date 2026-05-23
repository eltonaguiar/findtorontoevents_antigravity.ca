# Action-Items Execution Plan — 2026-05-17

Sequenced plan for the 8 open action items (LMArena P1-P4 validation gates +
OLLAMA O1/O3/O6/O7). Built by the agent swarm (`swarm_run.py`, engines kilo +
groq), synthesized + dependency-resolved here. Awaiting subagent vetting (§4).

## 1. Dependency graph

```
A8 (PF registry) ──┬──> A5 (COMMODITY verify)   [BLOCKS commodity sizing]
                   ├──> A1 (meta-labeler wiring)
                   ├──> A3 (vol-scalar backtest)
                   ├──> A4 (FOREX ATR mutation)  [BLOCKS forex emission]
                   └──> A6 (calibrator refit)
A2 (overconfidence A/B) ── no dependency — runs in parallel from day 0
A7 (cross-asset COT overlay) ── needs CFTC data + harness — lowest priority
```

**Keystone:** A8 (canonical PF registry) is the single prerequisite for 5 of 8
items. It is the deduped, spot-price-sanitized, version-stamped clean ledger
every other verification reads from. Build it first.

**Resolver note:** A1 + A6 also need *post-resolver-v2.1* clean closed picks.
Resolver v2.1 already shipped (2026-04-28); A8 ingests from it, so A8 delivers
the clean dataset as a side effect.

## 2. Sequenced plan

| # | Item | Deps | First step | Acceptance test (falsifiable) | Effort |
|---|---|---|---|---|---|
| 1 | **A8** Canonical PF registry | none | Build table keyed `(asset_class, strategy_id, trade_date)`; ingest raw execution ledger → dedup → spot-price sanitize → recompute PF/WR → version-stamp | Registry PF reconciles to raw ledger within ±0.01 after sanitization; every dashboard/sizing surface reads only this table | L |
| 2 | **A5** COMMODITY PF verify | A8 | Filter COMMODITY CT=F from registry; dedup COT emissions by `(strategy,date,symbol)`; recompute `multi_asset_cot` PF/WR | Deduped PF matches registry vs raw-ledger recompute; verdict MATCH/INFLATED. **Blocks all COMMODITY sizing until done.** | M |
| 3 | **A1** Meta-labeler wiring | A8 | Pull post-resolver-v2.1 closed picks from registry; retrain `alpha_engine/meta_labeler.py` | Validation AUC ≥ 0.55 on the chronological held-out 20%; then `meta_label_gate` shadow-logs 30d before enforce | L |
| 4 | **A2** Overconfidence decay A/B | none | Enable `OVERCONFIDENCE_DECAY=1` on 50% of accounts | Top-quartile realized WR ≥ baseline − 1pp over a 30-day A/B | M |
| 5 | **A3** Vol-scalar cap backtest | A8 | Pull COMMODITY+ETF closed cohort from registry; backtest `volatility_target_size` with `vol_scalar_cap=(0.0,2.0)` | Sharpe lift ≥ +0.2 at equal-or-better MDD vs no-cap | L |
| 6 | **A4** FOREX ATR mutation | A8 | Run FOREX picks through `STRATEGY_INVESTIGATION_BEFORE_KILL`; deploy ATR-normalized variant in SANDBOX | Variant PF > 1.0 AND WR > 45% over 30 trading days. **Blocks FOREX emission until done.** | L |
| 7 | **A6** Calibrator refit | A8 | Refit `confidence_calibrator.py` (isotonic) on post-resolver-v2.1 clean data; flip `CONFIDENCE_CALIBRATION_ENABLED=1` | Calibrated-confidence vs realized-WR rank correlation positive (ρ > 0) on a held-out month | M |
| 8 | **A7** Cross-asset COT overlay | CFTC data + harness | Scaffold CFTC COT ingester; backtest |z|>2 COT → inverse CRYPTO sizing | Overlay raises CRYPTO Sharpe ≥ +0.15 OOS, orthogonal to directional alpha (ρ < 0.3) | L |

## 3. Do-first-3 shortlist

1. **A8** — keystone; unblocks 5 items. Start immediately.
2. **A2** — zero dependency; run the 30-day A/B in parallel from day 0.
3. **A5** — first consumer of A8; resolves the COMMODITY PF 2.57-vs-21.33
   ambiguity that currently blocks all commodity sizing.

A1 / A3 / A4 / A6 follow once A8 lands. A7 is last (external-data dependency,
no current harness).

## 4. Vetting verdict (2 subagents, 2026-05-17)

**Dependency-graph review — FLAWS FOUND:**
- A8 is a hard prereq ONLY for A5 + A3. **A1, A4, A6 are falsely coupled** —
  `meta_labeler.py` and `mutation_analysis.py` read `closed_picks.json` directly;
  they need post-resolver-v2.1 clean picks (already on disk since 2026-04-28),
  not the registry abstraction.
- A2 zero-dependency claim — **SOUND**.
- do-first-3 — **suboptimal**: A1/A4/A6 idle behind A8 for no code reason.
- Missing prereq: **`meta_label_gate` does not exist** in `quality_gates.py` —
  A1 must build + register it before the 30-day shadow window starts.

**Acceptance-test / effort review — WEAK TESTS FOUND:**
- A6 `ρ>0` is trivial (ρ=0.001 passes) → tighten to **ρ≥0.15 AND > raw**.
- A4 has no n-floor → add **n≥100** (charter floor) or it passes on 8 lucky trades.
- A8 reconciliation test is tautological → isolate the **dedup/sanitize delta**.
- A2 effort → **L not M** (A/B account-split + per-arm attribution is net-new).
- A3 = **highest-risk**: no cohort-replay harness exists to feed closed picks
  through `volatility_target_size`; hidden harness build invisible in the L estimate.
- A7 effort → **XL** (new OOS overlay harness, largest net-new build).
- Note: agent flagged `OVERCONFIDENCE_DECAY` "missing" — STALE; shipped in
  PR #1117 (merged `5ab4b2397e3`), agent read a pre-merge checkout.

## 5. CORRECTED plan (post-vetting)

- **Day 0, parallel:** A8 (L), A2 (L), A1 (L — retrain on existing
  `closed_picks.json` + build `meta_label_gate` shadow scaffold), A6 (M — refit
  calibrator, accept ρ≥0.15), A4 (L — `mutation_analysis.py --json`, n≥100 floor).
- **After A8 lands:** A5 (registry reconciliation), A3 (needs new cohort-replay
  harness — budget the hidden harness as part of A3).
- **Last:** A7 (XL — external CFTC harness).

**Revised do-first-3:** A8 (keystone) ‖ A1 (off critical path) ‖ A5-prep
(`verify_system_pf.py` already exists — can pre-verify COMMODITY before A8).

## 6. Grok steering + A6/A4/A8 results (2026-05-17)

Subagents completed A6, A4, A8; Grok (via fixed `consult-grok` skill) reviewed.

**A6 — calibrator refit:** OOS split (fit oldest 70%, eval newest 30%) — only
**EQUITY** passes (raw ρ −0.485 → calibrated +0.424; inversion is time-stable).
CRYPTO (85% of volume) fails. **FOREX calibrator is a hazard** — fit increasing
on old data, newest slice flips sign, would invert a real +0.52 signal. Verdict:
do NOT enable the global `CONFIDENCE_CALIBRATION_ENABLED` flag; add a per-class
allowlist (`CONFIDENCE_CALIBRATION_CLASSES=EQUITY`) in a follow-up.

**A4 — FOREX ATR mutation:** verdict **NO-VIABLE-SUBSET** — keep FOREX
hard-disabled. ATR-normalization contradicts its own premise (winners fired in
*higher* vol than losers). Incidental (Axis-2, not A4): `cta_cross_asset_tsmom`
SHORT-only n=117 WR 65.8% PF 2.89 — route through the Direction-axis path.

**A8 — canonical PF registry:** built `tools/build_pf_registry.py` +
`pf_registry.json`. **41% of all 8914 closed rows are duplicate re-emissions.**
COMMODITY raw PF 2.28 → deduped **1.10**; CRYPTO 0.45→0.48; FOREX 0.35→0.32.
CT=F sanity-check PASS (deduped PF 4.687).

### GROK VERDICT — re-prioritize

> "41% duplicate re-emission = the closed-pick ledger is structurally corrupted.
> All A5/A6/A8 numbers are downstream of the same broken emitter/resolver.
> Chasing A2/A3/A7 is premature — measuring phantom edge on a distorted ledger.
> **Highest-ROI: make pick emission + resolver idempotent** — deterministic
> dedup key at emission time `(asset, side, entry_bar/ts, model_id, signal_hash)`,
> hard unique constraint + alert in the ledger writer, explicit 'position
> already open' guard. Rebuild the registry from the fixed pipeline, re-run
> A5/A6/A8 on clean data before any further per-class work."

### NEW ITEM — A9 (supersedes A2/A3/A7 priority)

**A9 — Emitter/resolver idempotency.** Add a deterministic dedup key at pick
EMISSION time; enforce a unique constraint + alert in the ledger writer
(`outcome_resolver.py` / the closed-pick writers); add a "position already open"
guard so the resolver cannot create duplicate closed rows. **First step:** trace
where closed picks are written, identify the missing idempotency key. **Accept:**
post-fix, a fresh `build_pf_registry.py` run shows raw-vs-deduped row delta < 2%
(currently 41%). **Effort:** M-L. **Do A9 before A2/A3/A7.**
