# N5 — Paper portfolio: gate-checked loader, enforced refusal

**Date:** 2026-11-22
**Scope:** [`tools/paper_portfolio.py`](../tools/paper_portfolio.py), [`tests/test_paper_portfolio.py`](../tests/test_paper_portfolio.py)
**New mode:** `--load-from-gate`

## What was broken / missing

[`tools/paper_portfolio.py`](../tools/paper_portfolio.py) was honest plumbing with a
`purpose: plumbing_demo_not_validated_edge` stamp, but the honesty was a comment. Its
book held three arbitrary crypto demo positions, and `--add` could put anything in it.
The planned next step was "wire it to a real signal source" — but this programme has
now established that **no rule it tested beats holding the index**: all 9 forward-gate
pods report `(0, False)`, and the FOREX, equity-breakout, low-turnover and H-119
candidates were all killed or declared non-promotable. Populating the book from
"the best available" signal would be exactly the dishonesty this programme exists to
prevent.

So the correct deliverable is **not a populated book**. It is to make the emptiness
enforced by code instead of promised by a comment.

## What was added

### `--load-from-gate` (the only mode that can open a non-demo position)

1. **Reads the authoritative gate state.** It reuses the repo's own gate code:
   - [`forward_gate_block()`](../alpha_engine/audit3_tribunal.py:1603) with
     [`load_confirmatory()`](../alpha_engine/audit3_tribunal.py:925) on
     [`reports/audit3_confirmatory.json`](../reports/audit3_confirmatory.json) and
     [`reports/forward_observations.jsonl`](../reports/forward_observations.jsonl).
     `forward_gate_block` filters each pod's forward rows to those closed on/after
     `registered_at` and calls
     [`promotion()`](../alpha_engine/forward_observations.py:379), which applies
     `n >= 100`, net PF CI-LB > 1.0 **or** IR >= 0.5, 100% intrabar first-touch, and
     benchmark coverage >= 90%. **No threshold is re-implemented or relaxed.**
   - [`reports/hypothesis_registry.json`](../reports/hypothesis_registry.json) for the
     explicit `promotable` flag (read via
     [`hypothesis_status.iter_hypotheses()`](../alpha_engine/hypothesis_status.py:100)).
     An explicit `false` vetoes a pod even if its numbers would otherwise pass.
2. **Selects only pods that actually passed.** A pod is loadable only when the gate
   marks it `eligible` **and** the registry does not say `promotable: false`. There is
   no "best available", no "closest to passing", no fallback.
3. **Refuses cleanly when nothing passes.** It emits a machine-readable outcome
   (`loaded`, `reason: no_pod_passed_forward_gate`, `pods_checked`, `pod_results` with
   each pod's real `n` / `eligible` / `loadable` / `reasons`) and **does not save the
   book** — `book.json` stays byte-identical. The only code path that calls
   `save_book()` is `if outcome["loaded"] > 0`.
4. **If a pod ever does pass**, it opens a LONG position in the asset class's
   home-market instrument ([`PROXY_SYMBOL`](../tools/paper_portfolio.py)) at its last
   real quote, stamps the position `gated: true` plus `gate_n`/`gate_evidence`, and
   sizes it at 10% of starting cash. A symbol that cannot be quoted is skipped with a
   reason, never valued at a guess.

### Demo positions are flagged, not deleted

The three demo positions are kept. Every position now carries `gated: false` unless
loaded from the gate, and `--status` / `--mark` print
`DEMO BOOK - NOT GATE-BACKED` at the top with each row tagged `DEMO/UNGATED`
(`--status --json` adds a `gate_summary` block). Nothing pretends they were signals.

## Why the honest outcome is an enforced refusal

A loader that refuses proves the gate is real. A loader that loads "something" proves
only that it can be fooled. Since nothing in this programme has passed, the refusal is
the expected and correct result, and the tests lock it in.

## Test results

`python3 -m pytest tests/test_paper_portfolio.py -q`

```
................                                                         [100%]
16 passed in 0.79s
```

The 10 pre-existing tests all still pass (including the straddle-bar→SL and
net-of-2×-cost assertions, unweakened). The 6 new tests:

- `test_gate_real_state_refuses_and_leaves_book_untouched` — real gate state: zero
  positions added, `book.json` sha256 unchanged, demo position kept.
- `test_gate_real_state_outcome_is_refusal` — every real pod is non-loadable; outcome
  is `no_pod_passed_forward_gate`.
- `test_gate_synthetic_eligible_pod_produces_position` — a synthetic pod with 120
  mixed rows **does** load a `gated: true` position (proves capability, not just
  refusal). The fixture has wins *and* losses on purpose: an all-winner series has an
  infinite PF whose CI is not estimable, and the gate rightly refuses it.
- `test_gate_promotable_false_is_never_loadable` — same passing numbers but
  `promotable: false` ⇒ `eligible: true, loadable: false`, nothing loaded.
- `test_gate_unpriced_pod_is_skipped_not_guessed` — a passing pod with no quote is
  skipped, not valued at a guess.
- `test_status_labels_demo_positions_as_ungated` — `--status` prints the demo banner.

## Real refusal output (repo state, 2026-11-22)

```
$ sha256sum paper_portfolio/book.json
ed66a298a1eb8b187e3c039021948ec242183a5467fc2596ae6911fecdb95cf5  paper_portfolio/book.json
$ python3 tools/paper_portfolio.py --load-from-gate
REFUSED: no_pod_passed_forward_gate - no position opened, paper_portfolio/book.json unchanged (ed66a298a1eb)
  pods checked: 11
  POD-EQUITY-BREAKOUT              n=0    eligible=False no forward rows — nothing can promote
  POD-LUXALGO-SHORT                n=0    eligible=False pod status 'post_hoc' cannot confer confirmatory
  POD-CRYPTO-ENSEMBLE-GRADE        n=0    eligible=False pod status 'declined' cannot confer confirmatory
  POD-CRYPTO-VWAP-REVERSION        n=0    eligible=False pod is observe - registered for observation only
  POD-CRYPTO-BOLLINGER-MR          n=0    eligible=False pod is observe - registered for observation only
  POD-FABER-TAA                    n=0    eligible=False pod is observe - registered for observation only
  POD-FOREX-USDJPY-MOMENTUM        n=0    eligible=False pod is observe - registered for observation only
  POD-COMMODITY-ROLL-YIELD         n=0    eligible=False pod is observe - registered for observation only
  POD-CRYPTO-POSITION              n=0    eligible=False pod is observe - registered for observation only
  POD-ETF-DUAL-MOMENTUM            n=0    eligible=False pod is observe - registered for observation only
  POD-CRYPTO-BTC4H-RSIMACD         n=0    eligible=False pod is observe - registered for observation only
  This book holds no gate-backed positions because nothing passed.
$ sha256sum paper_portfolio/book.json
ed66a298a1eb8b187e3c039021948ec242183a5467fc2596ae6911fecdb95cf5  paper_portfolio/book.json
```

`book.json` hash is identical before and after. `--status` on the same book:

```
DEMO BOOK - NOT GATE-BACKED (3 position(s), none from --load-from-gate)
...
  OPEN BTC/USDT    LONG   qty 0.05 @ 60000  tp=66000.0 sl=57000.0  [OPEN] [DEMO/UNGATED]
```

## Explicit conclusion

**The paper portfolio remains empty of gate-backed positions because nothing passed.**
The three positions it holds are demo plumbing, marked as such, and are not signals.
`reports/forward_observations.jsonl` was not modified (md5
`fb4c12cf33fe18153661669df5540a55`).
