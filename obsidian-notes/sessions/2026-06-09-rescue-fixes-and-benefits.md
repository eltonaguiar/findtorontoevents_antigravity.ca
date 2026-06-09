---
tags: [session, changelog, edge, fixes]
created: 2026-06-09
goal: "#1"
---

# Session 2026-06-09 — Rescue Fixes & Their Benefits

Multi-agent rescue round (claude + cursor + kilo + zoocode + grok). What changed and **why it helps**. Honest verdict unchanged: **0/9 asset classes money-ready**; the work fixes the *measurement layer* so future verdicts are trustworthy.

## Measurement-integrity fixes (the core "save the system" work)

| Fix | Commit | Benefit |
|-----|--------|---------|
| Backfill quarantine in `build_pf_registry` | earlier | Canonical registry no longer counts 77.8% backfill-contaminated rows → verdicts reflect real resolved trades |
| Per-class sane-pnl guard (pf_registry + picks-now) | earlier | Drops reverse-split / feed-bug rows (CADJPY +428%, NZDUSD −100%) that single-handedly inflated PF |
| EXPIRED-honest WR + banned/backfill filter in picks-now `load_db_edge` | earlier | GBPUSD "58.8%" → true ~7%; edge overlay only corroborates on genuinely-resolved, non-banned symbols |
| Intrabar re-resolution → **parallel columns** | `979b92a70b` | 15,027 picks now carry intrabar-true verdicts in `trading_picks.intrabar_*` (non-destructive, opt-in); canonical preserved |
| OHLCV deep backfill (SAVE-1, 180d) | `875f44c606` | Unblocked full-book intrabar replay (was 30d-limited): CRYPTO orig 47.1% → true **39.6%**, 21.9% TP→SL |
| TSMOM vol-scaled academic sleeve wired (SAVE-4) | `42e403e79d` | First academically-grounded sleeve in production path (trailing-stop exits structurally avoid the TIME_EXPIRED trap) |

## Loss-stopping gates (block bleeders at intake)

| Fix | Commit | Benefit |
|-----|--------|---------|
| Ban `multi_asset_scanner` | `7bbcfbe8e5` | Removes dominant FOREX bleeder (~9% WR / PF 0.21) |
| Ban FOREX bleeder family (carry_momentum 1% WR, rsi2 12.7%, …) | `d9c35b9277` | Stops ~3,600 garbage FOREX picks at intake (completes kilo FIX-1) |
| Per-class TP/SL caps at raw-insert chokepoints | `4470fbf0ed` | New picks can't ship 5×-oversized targets → fewer TIME_EXPIRE |
| picks-now: dividend double-multiply + neg-upside STRONG_BUY guard | `6053b3ebb7` | "Best picks now" no longer surfaces negative-expectancy names as STRONG_BUY |

## Infra / dashboard reliability (GHA + /audit)

| Fix | Commit | Benefit |
|-----|--------|---------|
| EAGLE2 policy strip rendered **twice** on /audit (async race) | `39a7982b43` | Dashboard no longer shows a duplicated banner |
| Unified Audit Dashboard None-sort crash (~60 fails) | `94726fbba4` | Unblocks `dashboard_data.json` (was stale since 06-03) → ML Gatekeeper + Verified Pilots recover |
| MySQL Trading Picks Sync import crash (~66 fails) | `94726fbba4` | DB sync green again (`python -m` invocation) |
| Daily Scrutiny scipy dep + AI-Leaderboard DB creds + deploy SKIP | `94726fbba4`,`5c924d42e0` | Three more workflows unreddened |
| Edge-stability FTP-deploy step | `9357bc5755` | "Edge Stability" freshness source stays green (was 27d stale: built but never deployed) |

## Governance / honesty

- **mega_mutation T1 REFUTED** (`dd3b44eabb`): "PF 2.86/n=204" is raw NULL-timestamp `trading_picks`; clean cohort n=13/30.8%/PF0.57. Vault corrected; per-symbol picks (NEAR/INJ/ATOM) were fabricated.
- **money-maker-ready skills** baked with mandatory data-integrity filters (`1c935a069f`) so future audits can't reproduce inflated numbers.
- **Peer-reviewed** the intrabar `--apply` (deepseek+ofox) before mutating production → caught look-ahead/in-place/tie-break/backup flaws; rebuilt non-destructive.

## Related
- [[reference/edge-rescue-roadmap]]
- [[incidents/resolver-intrabar-blocker]]
- [[incidents/incidents-live-summary]]
- [[strategies/strategy-catalog-clean-cohort]]
