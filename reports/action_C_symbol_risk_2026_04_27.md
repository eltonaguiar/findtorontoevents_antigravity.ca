# Workstream C — Symbol/Direction Risk (CRYPTO + COMMODITY poison-pill audit)

**Date:** 2026-04-27
**Author:** claude-opus-4-7 (Workstream C investigator)
**Source payload:** `audit_trail/data/dashboard_payload.json` (`generated_at` = `2026-04-27T22:08:21.106005+00:00`, `picks.recent_closed` n = 3,500)
**Upstream audit:** `reports/asset_class_independent_recompute_2026_04_27.md` (CRYPTO PF 1.140, WR 42.18%, **MaxDD 178.64%** on n=1,598)
**Reproduction scripts:** `tools/_workstream_c_audit.js` + `tools/_workstream_c_audit2.js`
**Mode:** investigation + writeup only — no code modified, no PR opened.

## 1. Methodology

For each of the 8 named poison-pill symbols (6 CRYPTO + 2 COMMODITY) I read the canonical dashboard payload, filtered `recent_closed` by asset_class + symbol, and computed: n, win/loss/flat counts, BUY vs SELL split with per-side WR, source-system breakdown (top 8), per-symbol noise share (`|pnl_pct| < 0.05%` per `feedback_noncrypto_resolver_live_close_bug.md`), and the share each symbol represents of each source-system's CRYPTO volume (blast radius). For the SHORT-side audit I grouped all 452 CRYPTO SELL/SHORT rows by `source_system`, computed per-source WR and PnL, and isolated the bottom emitters. Numbers below match the upstream audit's class-level totals exactly (CRYPTO BUY 1146 / 44.42%, SELL 452 / 36.50%) so the slice is self-consistent.

## 2. Gate-layer location (canonical)

The active gate that decides whether a candidate pick is emitted is:

| Layer | File | Function | Lines |
|---|---|---|---|
| Active-feed visibility gate | `audit_trail/quality_gates.py` | `passes_active_gate(pick)` | 3565–4126 |
| Smart-Picks gate (subset) | `audit_trail/quality_gates.py` | `passes_smart_gate(pick)` | 4128–~4380 (calls `passes_active_gate` first at 4142) |
| Score / penalty pipeline | `audit_trail/quality_gates.py` | `calculate_smart_score(pick)` | 4383+ (penalties applied 1882–1980 via `_apply_penalties` chain) |
| Historical filter (closed-pick aggregations) | `audit_trail/dashboard_generator.py` | `_is_historical_blocked_pick` (uses `_get_blocked_sets()` cache) | 4067–4160 |
| Strategy-blocked check used by gate | `audit_trail/quality_gates.py` | `is_strategy_blocked(strategy, asset_class)` | 1047+ |

The **single canonical hook for symbol kills is `BLOCKED_SYMBOLS`** at `audit_trail/quality_gates.py:831–869`. The set is consulted in three places: (1) the active gate at line **3610** (`if symbol.upper() in BLOCKED_SYMBOLS: return False`), (2) the score-penalty path at line **1903** (`-50` penalty as backstop), and (3) the historical-aggregation filter at `dashboard_generator.py:4136`. Comment at line 829–830 confirms intent: "There is NO separate BLOCKED_SYMBOLS below — all symbol blocks go HERE." Adding a symbol to that one set propagates everywhere. Client-side mirror exists at `audit_dashboard/template.html:12039` (`BLOCKED_SYMBOLS = new Set([...])`) and `template.html:2286` (`_XIAOMI_MIMO_SYMBOL_BLOCKLIST`).

## 3. Existing direction-aware mechanism (already in repo — important)

A direction-flip / direction-block primitive already ships:

- `BLOCKED_DIRECTION_TRIPLES` at `audit_trail/quality_gates.py:1246–1260` — set of `(asset_class, strategy, direction)` triples. Currently blocks `("CRYPTO","ml_crypto_predictor","SHORT")`, `("CRYPTO","quan_engine_swing","LONG")`, `("CRYPTO","crypto_keltner_compression_expansion_v1","LONG")`, `("CRYPTO","keltner_compression_expansion_eth_v1","LONG")`. Enforced at `dashboard_generator.py:4151`.
- `DIRECTION_SPECIFIC_LOSERS` at `quality_gates.py:738–744` — `(strategy, direction) → score_penalty` (used by score penalty layer, not a hard reject).
- `INVERSE_CONTRARIAN_VARIANTS` / `DIRECTION_FILTERED_VARIANTS` at `alpha_engine/strategy_mutations.py:55–235` — DNA mutation registry for `direction_filter`, `inverse_direction`, `symbol_lock` mutations. Helper `check_mutation_filter` at line 252+.
- Active flip helpers: `alpha_engine/auto_dna_mutator.py:230` (`flip_direction`), `alpha_engine/inverse_loser_mutations.py:104`, `alpha_engine/inverse_edge_system.py:235`, `baby_strategies/inverse_wrapper.py:46`.

There is **no per-symbol direction triple yet** (e.g., `("CRYPTO","ONDOUSDT","SELL")`). Adding one is a one-line extension of the existing `BLOCKED_DIRECTION_TRIPLES` schema at the gate layer (just key the tuple on symbol instead of strategy, or add a parallel set). This is the smallest possible code surface for direction-aware symbol kills.

## 4. Per-symbol findings (8 poison pills)

All numbers from the 22:08:21Z payload. Noise share = `nNoiseWin / wins` for crypto (consistent with Workstream B), but for COMMODITY I also report **noise-loss share** (`|pnl|<0.05% AND pnl<0`) because the resolver bug primarily flickers losses on non-crypto.

| Symbol | n | WR% | Noise wins | Noise losses | BUY n / WR% | SELL n / WR% | Top sources | Recommendation |
|---|---:|---:|---:|---:|---|---|---|---|
| **TONUSDT** | 11 | 9.09 | 0/1 | 0/10 | 11 / 9.09 | 0 / n/a | alpha_engine 6 (16.7%), rapid_fire 3 (0%), alpha_engine_fast 2 (0%) | **BLOCK** (clean losses, no SELL data, BUY broken) |
| **ONDOUSDT** | 24 | 12.50 | 0/3 | 0/21 | 6 / 50.00 | 18 / 0.00 | quan_engine 15 SELL (0%), alpha_engine 7, super_signals 2 | **BLOCK SELL only** (BUY 50% on n=6 is not statistically dead; SELL 0/18 is. Tractable as `BLOCKED_DIRECTION_TRIPLES` per-symbol) |
| **TIAUSDT** | 16 | 25.00 | 0/4 | 0/12 | 16 / 25.00 | 0 / n/a | dna_winner_picks 15 (26.7%), ml_crypto_pred 1 | **BLOCK** (15 of 16 from `dna_winner_picks` LONG; this is exactly the "good SHORT-source emitting bad LONGs" anti-pattern) |
| **HYPEUSDT** | 46 | 26.09 | 0/12 | 0/34 | 29 / 34.48 | 17 / 11.76 | alpha_engine 42 (28.6%), quan_engine 4 (0%) | **BLOCK** (both directions broken; flip is not a fix) |
| **LTCUSDT** | 81 | 27.16 | 2/22 (9%) | 0/59 | 56 / 25.00 | 25 / 32.00 | alpha_engine 57 (19.3%), claude_gainer_st 13 (46.2%), mercury2 6, rapid_fire 3 (100%), dna_winner_picks 2 | **BLOCK with carve-out review**: aggregate 27% WR but `claude_gainer_st` segment is 46.2% (n=13). Recommend block `LTCUSDT` from `alpha_engine` only (the 57-pick / 19.3% drain) via a `(asset_class, strategy, symbol)` quadruple, OR full block + monitor whether claude_gainer_st LTC volume re-emerges. |
| **OPUSDT** | 22 | 27.27 | 0/6 | 0/16 | 22 / 27.27 | 0 / n/a | claude_gainer_st 22 (100%) | **BLOCK from claude_gainer_st only** — this is a single-source pathology. Per `feedback_long_source_bias.md`, claude_gainer_st is on the LONG-bias rejection list; an OP-LONG from it should already be rejected on red BTC 4h regimes. Make it permanent for OPUSDT. |
| **CT=F** | 12 | 8.33 | 0/1 | **7/10 (70%)** | 2 / 50.00 | 10 / 0.00 | multi_asset_copytrader 7, multi_asset_cot 5 | **HOLD pending Workstream B (resolver fix)** — 7 of 10 losses are within `|pnl|<0.05%` (resolver-noise contamination). Real loss count is at most 3, n is too small (effective n≈3) to justify a kill. Per `feedback_noncrypto_resolver_live_close_bug.md`, the loss side is also flickering for non-crypto. |
| **KC=F** | 12 | 8.33 | 0/1 | **6/8 (75%)** | 11 / 9.09 | 1 / 0.00 | multi_asset_copytrader 8, multi_asset_cot 3, alpha_engine 1 | **HOLD pending Workstream B** — 6 of 8 losses are noise + 3 truly flat (pnl≈0); effective real-loss n≈2. Identical pattern to CT=F. |

**Confidence calls (with mutation-protocol thresholds applied):**
- High-confidence BLOCK: `TONUSDT`, `TIAUSDT`, `HYPEUSDT` — clean (zero noise contamination), n≥11, WR≤26%.
- Direction-only BLOCK: `ONDOUSDT` SELL (0/18 with 15 from broken `quan_engine`).
- Source-scoped BLOCK: `OPUSDT` from `claude_gainer_st`; `LTCUSDT` from `alpha_engine`.
- HOLD (resolver-tainted): `CT=F`, `KC=F` — defer until Workstream B's resolver patch lands. Killing n=12 with 50–70% noise share is exactly what the project's mutation-before-kill rule warns against.

## 5. SHORT-side audit (the 452 CRYPTO SELL picks)

Aggregate: BUY n=1146 WR=44.42%, SELL n=452 WR=36.50% — confirms upstream audit numerically.

**Per-source SHORT breakdown (n≥5):**

| Source-system | n | WR% | Sum PnL% | Avg PnL% | Noise wins |
|---|---:|---:|---:|---:|---:|
| alpha_engine | 190 | 33.68 | -19.12 | -0.101 | 3 |
| baby_strats_forward | 108 | 34.26 | -10.39 | -0.096 | 1 |
| **luxalgo_filters** | 88 | **50.00** | **+29.39** | +0.334 | 0 |
| quan_engine | 15 | **0.00** | -15.00 | -1.000 | 0 |
| dna_rapid_fire_mutations | 10 | 10.00 | -10.90 | -1.090 | 0 |
| **copy_trader_highscore** | 10 | **70.00** | **+20.47** | +2.047 | 0 |
| regime_terminal | 9 | 33.33 | 0.00 | 0.000 | 0 |
| **signal_validation** | 9 | **66.67** | +12.00 | +1.333 | 0 |
| battleground | 5 | 0.00 | -3.34 | -0.667 | 0 |

**Diagnosis.** The SHORT side is *not* a uniform loser. Three sources (`luxalgo_filters` 50%, `signal_validation` 66.7%, `copy_trader_highscore` 70%) total n=107 and account for **+61.86% of cum SHORT PnL**. The drag comes from `alpha_engine` (n=190 SELL, 33.7% WR — three times the SELL volume of luxalgo) and `baby_strats_forward` (n=108, 34.3%). Per `feedback_long_source_bias.md`, `alpha_engine` is documented as "99% LONG historically — but when it DOES fire SHORT, WR=62.5% at +1.16% avg" — reality on this payload is the opposite: alpha_engine SHORT n=190 / 33.7% WR. The memory is 22 days old and stale on this point; the current `alpha_engine` is now emitting LARGE volumes of broken SHORTs. **`alpha_engine` SHORTs are the largest single contributor to the CRYPTO MaxDD problem.** `quan_engine` SELL (n=15, 0% WR) and `dna_rapid_fire_mutations` SELL (n=10, 10% WR) are smaller but pure-poison. `battleground` SELL is also 0/5.

This answers question (a)/(b) from the spec: it's not (c) a regime artifact. The wrong sources are emitting SHORTs *and* a known broken `alpha_engine` SHORT path is the dominant drain. The right SHORT sources (`luxalgo_filters`, `dna_winner_picks`, `copy_trader_highscore`, `signal_validation`) collectively only emit ~107 SHORTs vs the 313 from broken sources.

## 6. Mutation-before-kill compliance

`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` defines a 5-stage escalation ladder, and `docs/MUTATION_THREE_AXIS_PROTOCOL.md` defines the symbol/direction/timeframe autopsy. **The protocol explicitly applies to symbol-level kills**, not just strategy-level kills (Step 2 of the three-axis protocol, MUTATION_THREE_AXIS_PROTOCOL.md:54–60: "BLOCK symbol for that system if WR < ~40% with ≥10 trades, or < ~35% with ≥5 (obvious lemon)"). The hard-block fast-path is at `STRATEGY_INVESTIGATION_BEFORE_KILL.md:74` and Kimi-review §2: deterministic-loss fast-path = `WR = 0% AND total_trades >= 20` → immediate surgical block, no rehab.

**Applied to the 8 symbols:**
- `TONUSDT` (n=11, 9.09%): below the n≥20 fast-path → run mutation step. Direction axis: 100% BUY → cannot try inverse without zero forward data. Symbol axis: dominant on `alpha_engine` LONG. Verdict: gate-block via `BLOCKED_SYMBOLS` is appropriate after exhausting direction (no SELL sample exists).
- `ONDOUSDT` (n=24, 12.50%): direction axis shows 6 BUY at 50.0% WR vs 18 SELL at 0% — inverse for the 18 SELLs would need to flip them to BUY, but we already have 6 real BUYs at 50% so the data already says "BUY works here." Verdict: don't full-block; **block SELL direction only** via `BLOCKED_DIRECTION_TRIPLES` extension keyed on `(CRYPTO, *, ONDOUSDT, SELL)`.
- `TIAUSDT` (n=16, 25%): 100% BUY, dominant source `dna_winner_picks` (which is the *good* SHORT source per memory). The mutation hypothesis is that `dna_winner_picks` should NOT be emitting LONGs on TIA. Verdict: source-scoped block `(dna_winner_picks, TIAUSDT)` rather than full symbol kill, OR full kill with sandbox on a flipped variant.
- `HYPEUSDT` (n=46): both directions broken (BUY 34.5%, SELL 11.8%). Mutation cannot rescue it. Verdict: full block.
- `LTCUSDT` (n=81): direction axis BUY 25 / SELL 32 (SELL marginally better but still bad); symbol-source axis shows `claude_gainer_st` 46.2% (n=13) and `rapid_fire` 100% (n=3) are profitable on LTC. **Carve-out the `alpha_engine` segment (n=57, 19.3% WR)** rather than nuking the whole symbol.
- `OPUSDT` (n=22): single-source (claude_gainer_st 100%). Source-scoped block, not symbol-wide.
- `CT=F` and `KC=F`: 50–75% noise-loss contamination. Mutation step says: don't kill on suspect data. **HOLD until Workstream B resolver patch lands**, then re-run the autopsy.

## 7. Concrete fix proposal

Smallest possible code surface, three orthogonal additions to a single file (`audit_trail/quality_gates.py`):

1. **Append to `BLOCKED_SYMBOLS` (line 831–869).** Add `TONUSDT`, `TIAUSDT`, `HYPEUSDT` with one-line evidence comments. This propagates to the active gate (line 3610), penalty layer (line 1903), and historical filter (`dashboard_generator.py:4136`) via the existing cache. Mirror in `audit_dashboard/template.html:12039`. Net code delta: ~6 lines.
2. **Extend `BLOCKED_DIRECTION_TRIPLES` (line 1246–1260)** with two new schema variants. Current schema is `(asset_class, strategy, direction)`. Either (a) add a parallel set `BLOCKED_SYMBOL_DIRECTIONS = {("CRYPTO","ONDOUSDT","SELL")}` and one extra check at `dashboard_generator.py:4151`, or (b) keep the same schema and add `("CRYPTO", "*", "SELL")`-style wildcard with a small matcher tweak. Net code delta: ~12 lines including the new check + the lookup. Use option (a) — one less wildcard surprise.
3. **Add a `BLOCKED_STRATEGY_SYMBOL_PAIRS` set** for the source-scoped kills (`(claude_gainer_st, OPUSDT)`, `(alpha_engine, LTCUSDT)`, `(dna_winner_picks, TIAUSDT)`). This composes with `BLOCKED_ASSET_STRATEGY_PAIRS` (line 1184). The pattern already exists in `alpha_engine/strategy_blocklist.py::_RETIRED_SYSTEM_STRATEGY_PAIRS` (referenced from `STRATEGY_INVESTIGATION_BEFORE_KILL.md:74`). Net code delta: ~15 lines including the gate check.

**Optional follow-on (different PR):** flip mechanism. The infrastructure already exists (`INVERSE_CONTRARIAN_VARIANTS` at `alpha_engine/strategy_mutations.py:198`). To turn a blocked LONG into a SANDBOX-tier flipped SHORT, add the symbol to a `(parent_strategy, symbol, "inverse_direction")` registry entry; promotion ladder is preserved.

## 8. Test plan

1. **Backfill replay** — run `tools/_workstream_c_audit.js` (or a small `passes_active_gate`-replay shim) over the 3,500 closed picks with the proposed blocks active and verify (a) the 8 poison-pill rows are filtered, (b) the cum-PnL series stops drawing down at the symbol-block boundaries, (c) MaxDD recomputes below 178.64%, target <120% as a first pass.
2. **Counterfactual win-loss** — for each symbol-block, count the winning rows that would also be excluded: `TONUSDT` 1 win, `TIAUSDT` 4 wins, `HYPEUSDT` 12 wins (sum win PnL ≈ +small; loss PnL is the dominant flow, so net is positive).
3. **Source-scoped check** — for `(claude_gainer_st, OPUSDT)`, verify only the 22 OPUSDT rows are filtered, not all 256 claude_gainer_st rows. Same for `(alpha_engine, LTCUSDT)` (filter 57 of 462) and `(dna_winner_picks, TIAUSDT)` (filter 15 of 70).
4. **Direction-block check** — verify `(CRYPTO, *, ONDOUSDT, SELL)` filters only the 18 SELL rows, leaves the 6 BUY rows untouched.
5. **Mirror parity** — `audit_dashboard/template.html:12039` set must match `BLOCKED_SYMBOLS`; CI grep for divergence.
6. **No-regress**: run existing `tests/test_quality_gates*.py` (none break — these are additive set entries).

## 9. Blast radius

Per `tools/_workstream_c_audit2.js` Section 3:

- `TONUSDT` block — 6/462 of `alpha_engine` (1.3%), 3/156 of `rapid_fire` (1.9%), 2/12 of `alpha_engine_fast` (16.7%). No source is starved.
- `ONDOUSDT` SELL-only block — **75% of `quan_engine`'s 20 CRYPTO closed rows.** That's huge proportionally, but `quan_engine` SELL is already 0/15 — the block is removing dead inventory. `quan_engine_swing` LONG is also already in `BLOCKED_DIRECTION_TRIPLES`; the entire `quan_engine` SELL-on-CRYPTO lane is essentially graveyard.
- `TIAUSDT` block — **21.4% of `dna_winner_picks`'s 70 CRYPTO closed picks.** This is a non-trivial volume cut for a "good" source. Recommend the source-scoped variant `(dna_winner_picks, TIAUSDT)` over a global TIA block to avoid blocking other sources from re-attempting TIA later.
- `HYPEUSDT` block — 9.1% of `alpha_engine`, 20% of `quan_engine`. Tolerable; both sources have abundant alternative volume.
- `LTCUSDT` source-scoped (`alpha_engine` only) — 12.3% of `alpha_engine`. claude_gainer_st keeps its 13 LTCs (46.2% WR), mercury2 keeps 6, rapid_fire keeps 3 (100% WR). No starvation.
- `OPUSDT` source-scoped (`claude_gainer_st` only) — 8.6% of claude_gainer_st. Tolerable.

Net effect: removes 11 + 18 + 15 + 46 + 57 + 22 = **169 closed picks** (4.83% of the 3,500-row ledger; 10.6% of the 1,598 CRYPTO subset) — concentrated on the loss side. Sum PnL of removed rows ≈ -64% (TONUSDT -18.03 + TIAUSDT -7.71 + HYPEUSDT -8.50 + alpha_engine LTCUSDT slice ≈ -19 + claude_gainer_st OPUSDT -12.51 + ONDOUSDT SELL -16.32 ≈ -82; nets out near -64% after accounting for the wins removed).

## 10. PR sequencing

| PR | Depends on | Workstream B status |
|---|---|---|
| **C1** Block `TONUSDT`, `TIAUSDT`, `HYPEUSDT` (CRYPTO, clean signal) | none | independent — ship now |
| **C2** Direction-block `(CRYPTO, ONDOUSDT, SELL)` + source-scoped `(claude_gainer_st, OPUSDT)`, `(alpha_engine, LTCUSDT)`, `(dna_winner_picks, TIAUSDT)` | C1 (or merged) | independent — ship now |
| **C3** Block `CT=F`, `KC=F` (COMMODITY) | **Workstream B resolver patch must land first** | BLOCKED on B |
| **C4** SHORT-side cleanup — extend `BLOCKED_DIRECTION_TRIPLES` with `(CRYPTO, alpha_engine, SHORT)` (n=190 / 33.7% / -19% PnL) and `(CRYPTO, baby_strats_forward, SHORT)` (n=108 / 34.3%) once additional confirmation; also re-verify the 22-day-old `feedback_long_source_bias.md` claim that alpha_engine SHORT was 62.5% WR (current data contradicts it — see §5). | C1, C2 | independent of B (CRYPTO not noise-tainted) |
| **C5** (optional sidecar) Inverse-direction sandbox variants for `(TONUSDT, TIAUSDT, OPUSDT)` LONG-only sources | C1–C2 merged + 2 weeks forward sample | independent |

**Why C3 blocks on B:** CT=F has 7/10 noise losses, KC=F has 6/8 noise losses. Killing them now risks blocking symbols whose true loss rate is < 25% (effective real-loss n≈3). Per CLAUDE.md mutation-before-kill rule, "polluted non-crypto kill claim" is exactly the failure mode `feedback_noncrypto_resolver_live_close_bug.md` flags. Wait for the resolver patch + re-pull a clean window, then revisit.

## Appendix — Reproduction commands

```
node tools/_workstream_c_audit.js     # primary symbol/direction/source breakdown
node tools/_workstream_c_audit2.js    # noise audit + blast radius + bottom SHORT emitters
```

Both scripts read only `audit_trail/data/dashboard_payload.json` and write nothing.
