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
from datetime import datetime, timezone
from pathlib import Path

import pymysql

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
        mid = p.get("model_id")
        if mid in CANONICAL_ID:
            p["model_id"] = mid = CANONICAL_ID[mid]
            n_merged += 1
        canon_prov = pmap.get(mid)
        if canon_prov and p.get("provider") != canon_prov:
            p["provider"] = canon_prov
            n_provider_set += 1

        # Display normalisations (no DB write):
        #  - OPEN picks shouldn't carry exit_price 0.0 (reads as "exited at $0");
        #    pnl_pct on OPEN is intentional *unrealized* PnL, left as-is.
        #  - canonical direction/asset-class vocab.
        if p.get("status") == "OPEN" and p.get("exit_price") == 0:
            p["exit_price"] = None
            n_norm += 1
        if p.get("direction") == "SELL":
            p["direction"] = "SHORT"
            n_norm += 1
        if p.get("asset_class") == "STOCKS":
            p["asset_class"] = "EQUITY"
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
