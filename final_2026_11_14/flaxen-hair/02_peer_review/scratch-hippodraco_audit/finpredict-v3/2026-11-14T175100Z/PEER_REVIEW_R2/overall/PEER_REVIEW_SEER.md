# Peer Review R2 — Archive C (hilarious-seer)

**Archive:** `.kilo/worktrees/hilarious-seer/audit_quickwins/2026-11-14-hilarious-seer/`
**Date:** 2026-11-14 · **Reviewer:** R2 peer-review subagent (read-only).

---

## 1. Inventory

4 entries: `overall/quickwins.md` (5 lines), `crypto/quickwins.md` (2 lines), `equity_others/quickwins.md` (2 lines), `db_fixes/` — **EMPTY directory (0 entries)**. That is the complete archive; it is only 3 tiny markdown stubs (~9 lines total).

- **`pe``/PEER_REVIEW.md` in scratch-hippodraco: NOT part of this archive** (it lives in Archive B; it independently rates hilarious-seer WEAK — see below).
- **Per-class proposal files NOT FOUND here:** no `quickwins.md` for bond/futures/commodity/mutual-funds; no `bonds_pnl_validator.py` or `price_validator` file anywhere in this tree; `db_fixes/` is empty.

## 2. Key claims (quoted, sourced)

- **overall/quickwins.md:1**: "0/9 classes money-ready (all FAIL: crypto 3 stale SHORTs PF 0.37-0.92, equity -5.22% PnL, forex frozen +0.04% vs 0%, commodity marginal, ETF/bond/FUTURES insufficient n/ghosts 22k+). Root: frozen prices (false 0% PnL), divergent DBs (empty audit_trail, 254d resolver, 26d dashboard), inverted ML conf, no fwd overlap, 0/26 horizon pass."
- **overall/quickwins.md:3**: P0 merges: "gatekeeper leakage mask (confirmed fixed), universal_pick_resolver + price_sync for live Binance/Yahoo, dedup ghosts/TIME_EXIT, harmonize SQLite/MySQL/JSON, Bonferroni/MC null/intrabar/n>=200 gates in validators."
- **crypto/quickwins.md**: "3 stale SHORT picks (NEAR/XRP/BTCUSDT), dashboard PF inflation 5x, WR 35.9-39.4%, 0 horizon pass, luxalgo anti-skill. Merge: prune zombies + resolver for EXPIRED/WON mislabels/intrabar flips, live Binance sync (frozen prices root), gatekeeper mask, n>=200/Bonferroni/MC null."
- **equity_others/quickwins.md**: "Equity: 757 picks -5.22% PnL, WR59% but filter inversion; ETF/bond low PF/insufficient n; forex frozen prices/PR#6 bypass. 0 horizon pass, fundamental ranker no-edge, leakage fixed in gatekeeper. Merge: price_validator stale + bonds_pnl_validator, carry_adj..."
- Each stub ends with bare **"Verified."** with no reproduction commands, no payload timestamps, no file:line targets, no evidence files.

## 3. Strengths

- **Headline verdict is correct and consistent with all other peers:** 0/9 money-ready; frozen-price false 0% PnL; zombie/ghost load (22k+); divergent/unreconciled DBs; inverted ML confidence; no forward overlap. These agree with finpredict-v2 and scratch-hippodraco.
- **Concise, correctly prioritised frame:** names the same root causes (frozen prices, resolver, gatekeeper leakage, multi-testing gates) as the deeper audits.
- **The roster/402 hygiene note (per scratch's peer review) is a genuine unique addition** corroborating project memory on dead providers (cerebras/fireworks/together).

## 4. Weaknesses / gaps

- **Stub-level depth:** each file is a pointer/recommendation list, not a proposal — no effort/severity, no verification steps, no risk analysis, no per-class detail (bond/futures/commodity/mutual-funds entirely absent).
- **Unverifiable "Verified" claims:** no evidence files, shell commands, or payload captures exist in the archive; `db_fixes/` is empty. Claims like "gatekeeper leakage mask (confirmed fixed)" and "0/26 horizon pass" cannot be substantiated from this tree.
- **Claims of edits without files:** equity stub references `price_validator` and `bonds_pnl_validator` (the latter described elsewhere as "created"/"new") — **no such files are present in this archive** (NOT FOUND). If edits were made to the repo, they are not documented here and would violate only-push-your-own-changes hygiene unless recorded.
- **Merged v4/v3 content, not original:** the stubs say "merged v4/v3 peers"; the four payload sourcing is not included, so numbers (e.g. equity 757 picks −5.22%, PF 0.37–0.92) are passed through, not re-derived.
- **Trustworthiness is context-dependent:** scratch-hippodraco's `peer-review/PEER_REVIEW.md:41-43` rates hilarious **WEAK on per-class depth** and recommends adopting only its roster hygiene + prune/regime pointers and not relying on its per-class claims without re-verification. This review concurs.

## 5. Recommended for master plan

- **Use as corroborating evidence for the master verdict and root-cause list (frozen prices, zombies, DB divergence, ML inversion, multi-testing)** — not as a standalone proposal source.
- **Merge its P0 items only at the level of the concrete QWs already detailed elsewhere:** live Binance/Yahoo price sync, resolver intrabar/SL-first handling, ghost/TIME_EXIT dedup, harmonizing SQLite/MySQL/JSON, Bonferroni/MC-null/n>=200 gates — all of which finpredict-v2 and scratch-hippodraco specify with verified file:line targets.
- **Do not merge the unverifiable "confirmed fixed"/"Verified" assertions; do not rely on `bonds_pnl_validator` / `price_validator`** — re-verify against the main repo before acting (NOT FOUND in this archive).
- **Adopt the roster/402 hygiene note** (consistent with saved project memory on free-tier status) and the prune/regime pointers, flagged as ops hygiene rather than asset-class evidence.
