"""
Rebuild ai_tournament_picks_latest.json from the authoritative DB.

The /audit/ai-tournament.html page (and model.html drill-down, plus
build_model_summary.py and update_leaderboard.py) read
audit_dashboard/data/ai_tournament_picks_latest.json as a flat list of pick
dicts. Historically that file was produced by merge_submissions_to_latest.py,
which globs data/ai_tournament/submissions/*.json. That path is fragile: when
the picks fleet writes data/ai_tournament/picks_YYYYMMDD.json (consumed by
ingest_to_db.py) but the per-model submission files are missing/stale, the
merge silently keeps an old snapshot. On 2026-05-28 this stranded the page on
3 models (May-26) while the DB held 42 models / 12 active that day.

ingest_to_db.py already writes every model's picks into
ejaguiar1_stocks.tournament_picks, so the DB is the complete, fresh source of
truth. This rebuild reads it directly and writes the flat snapshot the page
expects — no dependency on the submissions/ glob.

Usage:  DB_PASS_STOCKS=... python tools/ai_tournament/rebuild_latest_from_db.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql

# Shared canonical normalization (direction/asset_class/persona + symbol-class
# overrides for dual-class tickers like CL=F/IWM/TLT). Authored by a peer in the
# 2026-05-28 audit; we reuse it here — the primary rebuild path — so the fixes
# persist on every regen instead of being reverted from the DB's raw values.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize_pick  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LATEST = REPO / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"
CONFIG = REPO / "config" / "model_persona_mapping.json"

# Some config-fleet rows were ingested before ingest_to_db.py learned to write
# provider, so ~20% of DB rows have provider NULL (all 15 such model_ids are in
# config/model_persona_mapping.json). We backfill provider for DISPLAY from the
# config — no DB write — so the page's Provider column is never blank.
_INTERNAL_PROVIDERS = {
    "alpha_engine": "AlphaEngine (internal)",
    "gpt4o": "OpenAI (GPT-4o)",
}

# Provider-route alias collapse (DISPLAY only — raw model_id stays untouched in
# the DB). The same underlying model+version was ingested under two model_ids
# (one per API route), splitting its leaderboard stats into two rows. We map the
# alias -> a single canonical model_id so the summary/leaderboard builders (which
# group by model_id) merge them. Decision triangulated 2026-05-28 via the LiteLLM
# proxy + the stored provider strings — see TOURNYFIND_CLAUDE_OPUS47.MD.
#   MERGED:   grok3+grok3_direct (Grok-3), ring_261T+ring26_1t (Ring-2.6-1T),
#             gh_models_gpt4o+aimlapi_gpt4o (GPT-4o, different aggregators).
#   NOT merged: minimax_m2 vs m2_5, kimi K2 vs K2.6 — genuinely different versions.
CANONICAL_ID = {
    "grok3_direct": "grok3",
    "ring26_1t": "ring_261T",
    "gh_models_gpt4o": "gpt4o",
    "aimlapi_gpt4o": "gpt4o",
}


def _provider_map() -> dict[str, str]:
    out = dict(_INTERNAL_PROVIDERS)
    try:
        cfg = json.loads(CONFIG.read_text())
        for mid, c in cfg.get("models", {}).items():
            prov = c.get("provider")
            if prov:
                out[mid] = prov
    except (OSError, json.JSONDecodeError):
        pass
    return out

# Columns the page/builders read; excludes heavy internals like
# _model_api_response and dedup hashes to keep the snapshot lean.
FIELDS = (
    "model_id", "provider", "persona_id", "asset_class", "symbol", "direction",
    "entry_price", "take_profit", "stop_loss", "thesis", "strategy_name",
    "catalyst", "confidence", "timeframe", "expected_hold", "status",
    "exit_price", "pnl_pct", "exit_reason", "submitted_at", "resolved_at",
)


def _connect() -> pymysql.connections.Connection:
    pw = os.environ.get("DB_PASS_STOCKS", "")
    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=pw,
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=3306,
        connect_timeout=25,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _coerce(p: dict) -> dict:
    for k in ("entry_price", "take_profit", "stop_loss", "exit_price", "pnl_pct"):
        if p.get(k) is not None:
            try:
                p[k] = float(p[k])
            except (TypeError, ValueError):
                p[k] = None
    for k in ("submitted_at", "resolved_at"):
        v = p.get(k)
        if isinstance(v, datetime):
            p[k] = v.astimezone(timezone.utc).isoformat()
    return p


def main() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT {', '.join(FIELDS)} FROM tournament_picks "
            "ORDER BY submitted_at DESC"
        )
        picks = [_coerce(dict(r)) for r in cur.fetchall()]
    finally:
        conn.close()

    # Collapse provider-route aliases (display-only) then normalise provider:
    #  - config/internal-known model_ids get the canonical provider string
    #    (overwrite, so a merged group reads one consistent provider),
    #  - models we don't know keep whatever the DB stored (rich variants).
    pmap = _provider_map()
    n_merged = n_provider_set = n_norm = 0
    for p in picks:
        # Shared canonical pass first: direction (SELL->SHORT), asset_class
        # (STOCKS->EQUITY), persona fallback, and symbol-class overrides that
        # un-split dual-class tickers (CL=F/GC=F/...->COMMODITY, IWM/XLI->ETF,
        # TLT->BOND) so a symbol never lands in two per-class buckets.
        normalize_pick(p)
        mid = p.get("model_id")
        if mid in CANONICAL_ID:
            p["model_id"] = mid = CANONICAL_ID[mid]
            n_merged += 1
        canon_prov = pmap.get(mid)
        if canon_prov and p.get("provider") != canon_prov:
            p["provider"] = canon_prov
            n_provider_set += 1

        # OPEN picks shouldn't carry exit_price/pnl_pct 0.0 placeholders (read
        # as "exited at $0" / "flat 0.00%"). Every OPEN row's pnl_pct is 0 or
        # null in the DB (no live unrealized PnL is computed), so the 0.0 is an
        # uncomputed placeholder, not a real mark-to-market — null renders as
        # "—". Resolved-pick stats are unaffected (builders aggregate WIN/LOSS).
        if p.get("status") == "OPEN":
            if p.get("exit_price") == 0:
                p["exit_price"] = None
                n_norm += 1
            if p.get("pnl_pct") == 0:
                p["pnl_pct"] = None
                n_norm += 1

    LATEST.write_text(json.dumps(picks, indent=2))
    n_models = len({p.get("model_id") for p in picks})
    n_open = sum(1 for p in picks if p.get("status") == "OPEN")
    n_null_prov = sum(1 for p in picks if not p.get("provider"))
    print(
        f"[rebuild_latest] wrote {LATEST.relative_to(REPO)} — "
        f"{len(picks)} picks, {n_models} models, {n_open} open; "
        f"alias rows remapped {n_merged}, provider normalised {n_provider_set}, "
        f"field normalisations {n_norm}, blank-provider {n_null_prov}"
    )


if __name__ == "__main__":
    main()
