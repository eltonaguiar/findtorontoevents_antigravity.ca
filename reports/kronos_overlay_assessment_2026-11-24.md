# Kronos overlay assessment (2026-11-24)

Provenance: [`alpha_engine/kronos_overlay.py`](alpha_engine/kronos_overlay.py) (390 lines), [`tests/test_kronos_overlay.py`](tests/test_kronos_overlay.py) (11 tests), the new [`tests/test_kronos_overlay_gaps.py`](tests/test_kronos_overlay_gaps.py) (13 tests), and [`reports/forward_observations.jsonl`](reports/forward_observations.jsonl) (430 usable rows).

## What Kronos is here

An opt-in overlay sidecar that would multiply a pick's `confidence` by 0.6–1.2 based on whether the Kronos foundation model agrees with the pick's direction. It is **not wired into production**: no module calls it. It degrades to a no-op when `torch` and `kronos` are absent, which they are on this machine (`HAVE_KRONOS = False`).

## What is proven

**The no-op guarantee holds.** With weights absent, three picks came back with every confidence unchanged and every multiplier at 1.0:

```
BTC   conf 0.5 -> 0.5  mult=1.0 stub=True
ETH   conf 0.7 -> 0.7  mult=1.0 stub=True
SOL   conf 0.3 -> 0.3  mult=1.0 stub=True
ALL CONFIDENCES UNCHANGED: True
ALL MULTIPLIERS 1.0     : True
```

So wiring it in could not corrupt production even if it were enabled today. That is the module's own design claim, now measured rather than asserted.

**The multiplier logic is fully specified by tests.** 24 tests pass (11 existing + 13 new). The new ones pin the band boundaries at exactly 2% and 0.5% (the code uses strict `>`), missing direction, SHORT agreeing with SHORT, the n<16 guard, the disabled env on the single-pick path, LRU eviction and hit-ordering, and the non-numeric-confidence guard.

## What is NOT proven, and cannot be here

**The multiplier table is unjustified.** Mapping agreement to 1.2 and disagreement to 0.6 is a design choice with no supporting measurement in the repo. Justifying it needs a recorded relationship between Kronos agreement and realised outcomes, and Kronos predictions cannot be produced without the weights.

**The underlying signal loses money before any overlay.** On the 430 forward rows a directional pick wins only 42.56% of the time, with a binomial z of −3.09 against a coin flip:

```
n=430 wins=183 win-rate=0.4256  binomial z vs coin flip = -3.086
```

That is significant at the 5% level in the *wrong* direction. A multiplier that raises confidence on agreeing picks would therefore amplify a losing signal rather than improve it. This is a stronger objection than "untested": the overlay would need to reverse the base signal's negative tilt to be worth anything, and nothing in the table does that.

## What I would NOT trust

- Any claim that the overlay "improves" picks. It has never run against real weights here, and the base signal it modifies is worse than chance.
- The 1.2/1.1/1.0/0.8/0.6 multipliers as calibrated values. They are arbitrary until measured against outcomes.
- The `kronos_confidence` saturation at 4% (`HIGH_CONVICTION_PCT * 2`). It is a display heuristic, not a probability.

## What would make this testable

Install `torch` and `kronos` with the Kronos-small weights, run the overlay in `KRONOS_OVERLAY_DRY_RUN=1` over the existing forward rows, and compare realised outcomes for agreeing versus disagreeing picks. Until then the honest status is: **logic verified, value unproven, base signal negative.**
