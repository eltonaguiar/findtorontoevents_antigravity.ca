# PR #609 Review + Decomposition — 2026-05-02

**Subject:** Kimi's `fix/resolver-and-filters-2026-05-02` (PR #609 — 4 files, +73/-29)
**Verdict:** **DECOMPOSE** — do not merge as-is.
**This PR (PR-A):** Implements the resolver bug-fix portion only, on a fresh branch with corrections.

## Sources reviewed

- 3 parallel subagent reviews (code, JSON evidence, markdown reports)
- DeepSeek peer review of sister PR #607 (docs-only audit)
- Adversarial reviews of this decomposition by DeepSeek + Cerebras Qwen
- Prior Opus 4.7 Kimi-review session (2026-05-01T20:50Z) — original 5-bug catalog
- Independent GitHub Copilot review of PR #609 (concurred on retry-counter scope bug)

## What Kimi got right

1. **Bug 1B** — empty `ohlc_window=[]` falsy-bypass at line 608. Real bug.
2. **Bug 1A** — `RESOLVE_FAILED_BREAKEVEN` retry loop. Real bug.
3. **Bug 1D** — yfinance no-timeout. Real bug.
4. **Bug 1E** — entry-day lookahead. Real but second-order.
5. ETF "DEAD" label was based on n=19 — that verdict deserves re-derivation.

## What Kimi got wrong

### Code-level
- **Kimi's retry counter is incremented only in the breakeven block**, not in the empty-OHLC early-return path. Picks stuck on the no-touch path still loop forever (Copilot's PR-609 review independently caught this). My implementation increments at every retry-needed early return.
- **`signal.alarm`** is Unix-only — breaks on Windows (operator's platform). My implementation uses `concurrent.futures.ThreadPoolExecutor`.
- **Status="FLAT" alone** would count as CLOSED in MySQL aggregator (`mysql_client.py:674`). My implementation uses `exit_reason="RESOLVE_FAILED_MAX_RETRIES"` so WR aggregators can filter via `exit_reason.startswith("RESOLVE_FAILED")` while keeping `status="FLAT"` for compatibility.
- **`min_elite_score: 80→30`** in `hf_quality_gates.json` — file has `"enabled": false` (dead code) but is a footgun if anyone enables. Should be reverted per CLAUDE.md MUTATION_THREE_AXIS_PROTOCOL.
- **`matrix_symbol_gates.py`** in PR diff is byte-identical to main. Drop.

### Methodological (filter changes derived from corrupted data)
- Kimi's `shadow_blocked.json` evidence covers only **44 hours** (2026-04-21 → 2026-04-23, BTC rip). 141/141 KILLED_ALPHA = CRYPTO LONG. Pure regime + direction bias.
- "+969.5% left on table" uses `pnl_pct_if_traded` (24h fixed-horizon return), NOT realized TP/SL. Only 25/141 actually hit TP within 24h.
- Kimi IGNORES the SAVED bucket (-995.66% prevented). By Kimi's own math the gate is roughly **neutral**, not value-destroying.
- Equities L100 PF 2.90 / +176.74% IS the pattern the pre-fix resolver creates. Cannot be cited as evidence for "promoting equities" until post-fix data exists.
- Adversarial reviewers (DeepSeek + Cerebras Qwen) correctly note: **crypto resolution path is exchange-based, NOT yfinance**, so crypto data IS clean. Crypto-only filter changes (e.g., C-Tier blocking) are defensible. Non-crypto filter changes still require post-resolver-fix data.
- "Golden Portfolio +275%" is sum-of-windows arithmetic with no MDD, no overlap dedup. Pure look-back.

### Sequencing
Kimi's `AUDIT_IMPROVEMENTS_2026_05_02.md` Phase 1 lumps resolver fixes + gate lowering + symbol unbans + confidence band changes all "Deploy Today." Inverts CLAUDE.md's correct sequencing: fix resolver → observe clean data → recalibrate filters.

## Recommended decomposition

| PR | Scope | Status |
|---|---|---|
| **PR-A** (this one) | Resolver bug fixes ONLY: 1A retry cap, 1B empty-list guard, 1D Windows-safe yfinance timeout. Default-ON (bug fixes restoring intended behavior). 9 unit tests. | **Open now** |
| **PR-B** (defer ~14d) | Crypto-only filter changes (C-Tier block, etc.) — defensible on clean exchange-resolved data. Default-OFF + shadow flag. | Pending PR-A merge + 14d non-crypto observation |
| **PR-C** (defer ~14d + investigation) | Forex/non-crypto filter recalibration + symbol unbans. Requires `STRATEGY_INVESTIGATION_BEFORE_KILL.md` per banned symbol. | Pending PR-A merge + post-fix data + per-symbol mutation analysis |

## What to do with PR #609

**Recommend close as superseded** by this PR-A. PR #609's existing diff has the Windows-incompatible `signal.alarm`, the wrong `status="FLAT"`-without-distinguishable-exit_reason choice, and the un-counted retry path. A new branch with corrections is faster than amending.

## Bottom line

Resolver bugs are real, but the bundle is dangerous. This PR-A ships only the bug fixes — narrowly scoped, Windows-safe, with retry-counter on every early-return path. Filter recalibration and symbol unbans wait for clean post-fix data per CLAUDE.md.
