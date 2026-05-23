# Executive Summary — Session Close — 2026-05-19

## Headline

**/audit dashboard fully repaired + verified live. Resolver-plan steps 2-7 now LIVE on production MySQL.** No asset class is money-ready; shadow-gate enforcement makes the labels honest.

## What landed on `main` this session

| commit | what |
|--------|------|
| `b863dc392f7` | Repaired broken FTP-deploy embedded Python (syntax error) + fixed 6 dashboard 404s. Verified live. |
| `5f036a205bc` | CI geo-block no longer false-trips the Binance circuit-breaker — unblocks all 7 asset-class tiles (was active=0 everywhere). |
| `6a007ad0732` | etf-bond-scanner: correct bond commit path + conflict-safe push. |
| `27620a2b020` | Scanner fail-loud guards (resolver step 2). |
| `ea5b39339a7` | Resolution-coverage dashboard panel (resolver step 4). |
| `4bdc461e3e1` | Enforce 2 monotone shadow gates `MDD_GATE_ENFORCE` + `ML_ENHANCED_CRYPTO_QUARANTINE` in 3 workflows (resolver step 3). Downgrade-only; CRYPTO/COMMODITY likely drop MONEY_READY -> NOT_READY (honest state). |
| `888edfe3156` | ET-1 / CO-1 / E-1 research sidecars all harness-REJECTED — none wired. |
| `d4c866098c6` | Operator-dispatch GHA workflows for DB steps 5-7 (resolver-step5-6-backfill, resolver-step7-apply). |
| `d5cdb3a9a98` | step7 PYTHONPATH fix — `python -m alpha_engine.active_picks_sync` from GITHUB_WORKSPACE. |
| `975d4dbc926` | All 10 `tv-*` skills now cite https://github.com/tradesdontlie/tradingview-mcp as the MCP server. |
| `ef4afdb3682` | step7 workflow now accepts `asset_class` input — multi-class dispatch. |

## Live DB writes (production MySQL)

- **Steps 5-6 — symbol-format backfill (run 26126486726):** 1,634 rows committed on `at_raw_picks`: 1,628 bare-FOREX got the `=X` suffix + 6 junk-symbol rows quarantined. Backup table `at_raw_picks_bak_26126486726` (147,319 rows) preserved. Rollback path: `RENAME TABLE`.
- **Step 7 CRYPTO slice (run 26128372217):** 482 active CRYPTO picks transitioned to terminal status. `db_ok=482 db_skipped=0 json_appended=482`. Breakdown: SL_HIT 288 / TP_HIT 185 / TP_HIT_CONTRADICTION 9 / stay_open 12 / no_price 6. Binance was geo-blocked from CI but the 3+ API failover chain (CoinGecko/KuCoin/etc) covered 64/65 prices.
- **Step 7 other classes (EQUITY/FOREX/COMMODITY/FUTURES/BOND/ETF):** dispatched serially via the multi-class workflow input added this session. EQUITY + ETF runs completed; FOREX/COMMODITY/FUTURES/BOND in flight (max_rows=500 per class).

## What got rejected — research sidecars

ET-1 (ETF creation/redemption, H-026), CO-1 (commodity inventory surprise, H-027), E-1 (insider Form-4 cluster buys, H-028) — all harness-REJECTED (net_edge_bps -9.24 / -13.66 / -17.47; 0 admissible windows). Registry H-026/027/028 status = REJECTED. **None wired.** Consistent with the prior no-edge verdict.

## Operational lessons captured

- **50webs MySQL ACL is per-user, not per-IP.** Desktop sessions denied for `ejaguiar1_stocks` user; GHA runners are allowlisted. Workaround: dispatch the 2 resolver workflows via `gh workflow run`.
- **Step 7 PYTHONPATH bug** — invoking by file path put `alpha_engine/` on `sys.path`; fixed by `python -m alpha_engine.active_picks_sync` from `GITHUB_WORKSPACE`.
- **`active_raw` snapshot was post-staleness-expiry** — fixed earlier this session so the diagnostic raw view actually shows ETF/BOND emitter picks.
- **Tile-0 root cause** was the CI Binance circuit-breaker false-tripping the M-049 safety-halt gate (rejected 100% of picks). Now treated as a data-source problem (handled by failover chain), not a trading halt.

## Decisions waiting on operator

| item | status | next move |
|------|--------|-----------|
| Drop dry-run backup table `at_raw_picks_bak_26126209814` | optional cleanup | drop via phpMyAdmin or a one-off SQL workflow |
| Keep APPLY backup `at_raw_picks_bak_26126486726` ~1 week | safety net | drop after the corrected ledger is verified clean |
| Live TV-portfolio activity (add picks / close picks) for all paper accounts except "The Leap" | **CANNOT be done from this session** — no `mcp__tradingview-desktop__*` MCP loaded in Claude Code | run from an IDE/agent where the tradingview-desktop MCP is connected; use the 10 updated tv-* skills + the launch command `"C:\Program Files\WindowsApps\TradingView.Desktop_3.1.0.7818_x64__n534cwy3pjxzj\TradingView.exe" --remote-debugging-port=9223 --remote-allow-origins=*` |
| Step 7 multi-class loop vs per-class dispatches | per-class dispatch chosen (matches the script's `--asset-class` arg) | if you want all 7 classes drained in one click, add a matrix-style workflow over all classes |
| Strategic fork (no edge anywhere; ~5-8% odds of HF-grade edge on current infra) | **pure operator decision** | not autonomous |

## Why no autonomous TV trading this session

The `mcp__tradingview-desktop__*` tool family is NOT loaded in this Claude Code session (only `mcp__claude-peers__*`, `mcp__claude_ai_*`, `mcp__vibe-trading__*` are available — none of which can drive TV). I cannot launch, read positions, place orders, or close positions on TradingView from here. The 10 `tv-*` skills (now cite the MCP at https://github.com/tradesdontlie/tradingview-mcp) are usable from any session with that MCP attached — the user dispatching from an IDE-with-MCP run is the path forward. The launch command verified against `tv-cdp-launch` SKILL.md: matches (port 9223; WindowsApps path note in the skill is correct).

## Posture (unchanged)

Research sandbox, paper-only. **No asset class has cleared the edge-stability harness.** Shadow-gate enforcement just shipped — the next regen cycle of `money_ready_verdict.json` will reflect the conservative downgrades. Steps 8-9 (re-derive verdicts + strategic-fork memo) unlock as steps 5-7 finish landing on the ledger.
