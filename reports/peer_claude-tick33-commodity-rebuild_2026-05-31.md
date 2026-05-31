# Tick 33 — COMMODITY Rebuild (PR #269 deep-dive follow-up, PR #276 structure-grounded)

**Date:** 2026-05-31
**Branch:** `fix/commodity-rebuild-tick33-2026-05-31`
**Author:** Claude Opus 4.7 (subagent, tick 33)

## Verdict source

- PR #269 deep-dive: 7 COMMODITY strategies analyzed. Class verdict = FAIL.
- PR #276 ground-truth: exact files/lines for every COMMODITY dispatch + gate surface.

## Per-strategy reality (post PR #276 verification on origin/main)

| Strategy | Status pre-tick33 | Action this PR |
|---|---|---|
| `cot_positioning` | Routed only via `("all","forex")` filter (`scanner.py:2097-2098`); reaches commodity via "all" only. TRIAGED falsified per #269. | None — de-facto already excluded from commodity dispatch. |
| `cftc_cot_commercial_signal` | Blocked at `production_scanner.py:2691` for `("commodity",...)`. | None — kill is intact. |
| `cta_cross_asset_tsmom` | FOREX leg killed in PR #275 (emitter cap). Commodity/equity legs still pass through `scanner.py:2191` on "all" filter. | **NEW BLOCK** `("commodity","cta_cross_asset_tsmom")`. |
| `futures_momentum` | Lives only in `multi_asset/scanner.py`. Banned for `futures` via `hedge_fund_quality_gate.FUTURES_BANNED_STRATEGIES`. No `futures→commodity` normalization → defense-in-depth needed. | **NEW BLOCK** `("commodity","futures_momentum")`. |
| `ema_stack_momentum` | Test-only (`live_forward_test.py:481`), Wire-Up-Rule DEAD CODE. Already blocked `("futures",...)`. | **NEW BLOCK** `("commodity","ema_stack_momentum")` (mirror — belt-and-suspenders). |
| `commodity_tsmom_12m` | Active with policy gate (lines 445-453). INSUFFICIENT-N (n=3). | None — keep on probation. |
| `gold_safe_haven` | Registered in `commodities_strategies.py:1076`, dispatched at `scanner.py:2101`, **but NO policy entry** → implicit default-deny. Per #269 best wired backtest (PF 1.98 / n=61) but UNREPLICATED LIVE. | **NEW POLICY ENTRY** under probation (`allow_without_forward=True`, `min_forward_wr=0.45`). |

## Verbatim BEFORE / AFTER

### File 1 — `alpha_engine/production_scanner.py` (block list)

BEFORE (lines 2691-2695 verbatim on origin/main @ `e33802026`):

```
            ("commodity", "cftc_cot_commercial_signal"),
            # Futures losers (Gate 5b already catches some)
            ("futures", "futures_mean_reversion"),
            ("futures", "ema_stack_momentum"),
        }
```

AFTER (after this PR):

```
            ("commodity", "cftc_cot_commercial_signal"),
            # 2026-05-31 (tick33): COMMODITY-leg blocks per PR #269 deep-dive verdict.
            # cta_cross_asset_tsmom: dispatched via scanner.py:2191 on
            #   ("all","forex","equity") filter and reaches commodity symbols
            #   through "all"-filter; confirmed loser per deep-dive (FOREX leg
            #   already capped at emitter via PR #275). Defense-in-depth block
            #   for any commodity emission from cta_replicator source_system.
            # futures_momentum: lives in multi_asset/scanner.py:91,2809 and is
            #   already banned via hedge_fund_quality_gate.FUTURES_BANNED + the
            #   ("futures","...") gate below — but commodity-category emission
            #   is not covered by the futures rule (no futures→commodity
            #   normalization). Defense-in-depth.
            # ema_stack_momentum: test-harness only per Wire-Up Rule
            #   (live_forward_test.py:481), already blocked for ("futures",...);
            #   mirror for commodity in case any future dispatch surface adds it.
            ("commodity", "cta_cross_asset_tsmom"),
            ("commodity", "futures_momentum"),
            ("commodity", "ema_stack_momentum"),
            # Futures losers (Gate 5b already catches some)
            ("futures", "futures_mean_reversion"),
            ("futures", "ema_stack_momentum"),
        }
```

### File 2 — `alpha_engine/non_crypto_policy.py` (policy entry)

BEFORE (lines 449-454 verbatim on origin/main @ `e33802026`):

```
        "min_forward_trades": 5,
        "min_forward_wr": 0.45,  # Below the published Sharpe but conservative
        "allow_without_forward": True,
    },
}
```

AFTER:

```
        "min_forward_trades": 5,
        "min_forward_wr": 0.45,  # Below the published Sharpe but conservative
        "allow_without_forward": True,
    },
    # 2026-05-31 (tick33): Gold safe-haven policy entry — formalize probation.
    # Already registered in alpha_engine/commodities_strategies.py:1076 and
    # dispatched via scanner.py:2101 (COMMODITY_STRATEGIES.update on
    # strategy_filter in {"all","commodity"}), but had NO policy gate so
    # default-deny via _default_policy was the implicit behavior. Per PR #269
    # deep-dive: best wired commodity backtest (PF 1.98 / n=61) but
    # UNREPLICATED LIVE. Probationary gate gives it room to build a real
    # forward record without blanket admission. Floor matches commodity_tsmom_12m
    # (min_forward_wr 0.45) since they share the same vol-targeted long-only
    # commodity-future regime profile.
    "gold_safe_haven": {
        "categories": {"commodity"},
        "min_confidence": 0.55,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.45,
        "allow_without_forward": True,  # Probation: build forward record
    },
}
```

## Self-red-team

- BEFORE blocks quoted byte-for-byte from `git show origin/main:<file>`.
- `python3 -m py_compile alpha_engine/non_crypto_policy.py alpha_engine/production_scanner.py` → PASS.
- No new imports introduced; structure preserved (tuple set + dict).
- Scanner dispatch surface UNCHANGED (no edits to `scanner.py:2097-2101`).
- Per PR #276 §C.1 "Correct diff targets for COMMODITY swap" — both files in this PR are on the canonical list. No edit to `multi_asset/scanner.py`, `commodity_kill_switch.py`, or `config.BLACKLISTED_STRATEGIES` — by design (these would over-reach: futures_momentum has no commodity-category prod call; commodity_kill_switch is a name-keyed switch already covering its scope).
- RT verdict: **PASS**.

## Out-of-scope (deliberately deferred)

- `cta_cross_asset_tsmom` COMMODITY emitter cap (mirror of PR #275 FOREX cap) — block at gate is sufficient to stop write; emitter trim can come if 30d block-count proves dominance.
- `gold_safe_haven` mutation/replication — needs price-path replay per `reference-sl-optimization-needs-pricepath`; pure backtest-PF tuning is unsafe.

## Action count

3 production actions:
1. Block `("commodity","cta_cross_asset_tsmom")`.
2. Block `("commodity","futures_momentum")` + `("commodity","ema_stack_momentum")`.
3. Policy entry `gold_safe_haven` (probation).
