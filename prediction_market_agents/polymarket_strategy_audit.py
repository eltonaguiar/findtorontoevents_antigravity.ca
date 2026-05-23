#!/usr/bin/env python3
"""Build a focused audit snapshot for notable Polymarket crypto wallets."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from copy_trader_intel.polymarket_scraper import _score_wallet, fetch_candidate_leaderboard

FOCUS_KEYS: tuple[str, ...] = (
    "0x8dxd",
    "justdance",
    "bonereader",
    "coinman2",
    "0xf705fa045201391d9632b7f3cde06a5e24453ca7",
    "0x751a2b86cab503496efd325c8344e10159349ea1",
)

DATA_OUT = Path(__file__).resolve().parent / "data" / "polymarket_strategy_audit.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _profile_tokens(profile: dict[str, Any]) -> list[str]:
    return [
        str(profile.get("wallet") or "").lower(),
        str(profile.get("user_name") or "").lower(),
        str(profile.get("alias") or "").lower(),
    ]


def _leaderboard_tokens(row: dict[str, Any]) -> list[str]:
    return [
        str(row.get("proxyWallet") or "").lower(),
        str(row.get("userName") or row.get("name") or "").lower(),
    ]


def _matches_focus(tokens: list[str], focus_key: str) -> bool:
    focus_key_l = focus_key.lower()
    return any(focus_key_l in token for token in tokens if token)


def _index_outputs(
    picks: list[dict[str, Any]],
    whale_signals: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    picks_by_wallet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pick in picks:
        wallet = str(pick.get("trader_address") or "").lower()
        if wallet:
            picks_by_wallet[wallet].append(pick)

    signals_by_wallet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signal in whale_signals:
        wallet = str(signal.get("whale_data", {}).get("wallet") or "").lower()
        if wallet:
            signals_by_wallet[wallet].append(signal)

    return picks_by_wallet, signals_by_wallet


def _derive_verdict(
    profile: dict[str, Any],
    wallet_picks: list[dict[str, Any]],
    wallet_signals: list[dict[str, Any]],
) -> str:
    if not profile.get("copyable_archetype", True):
        return "blocked"
    if wallet_picks:
        return "copyable_live"
    if wallet_signals:
        return "direct_only"
    return "watch_only"


def _derive_risks(profile: dict[str, Any], verdict: str) -> list[str]:
    risks: list[str] = []
    gate_reason = str(profile.get("copyability_gate_reason") or "")
    if gate_reason:
        risks.append(gate_reason)
    if bool(profile.get("crypto_concentration_flag")):
        risks.append("concentrated")
    if float(profile.get("latency_arb_score") or 0.0) >= 0.55:
        risks.append("latency_risk")
    if int(profile.get("crypto_recent_decisions_30d") or 0) >= 3 and float(profile.get("crypto_recent_score_30d") or 0.0) < 0.15:
        risks.append("weak_recent_form")
    if verdict == "watch_only":
        risks.append("no_live_copy_signal")
    return risks


def _summarize_profile(
    focus_key: str,
    profile: dict[str, Any],
    wallet_picks: list[dict[str, Any]],
    wallet_signals: list[dict[str, Any]],
    *,
    source: str,
) -> dict[str, Any]:
    wallet = str(profile.get("wallet") or "").lower()
    verdict = _derive_verdict(profile, wallet_picks, wallet_signals)
    risks = _derive_risks(profile, verdict)
    qualified_symbols = sorted((profile.get("qualified_symbols") or {}).keys())
    live_symbols = sorted({str(pick.get("symbol") or "") for pick in wallet_picks if pick.get("symbol")})
    live_signal_symbols = sorted({str(signal.get("symbol") or "") for signal in wallet_signals if signal.get("symbol")})

    return {
        "focus_key": focus_key,
        "source": source,
        "user_name": profile.get("user_name"),
        "wallet": wallet,
        "wallet_archetype": profile.get("wallet_archetype"),
        "copyable_archetype": profile.get("copyable_archetype", True),
        "copyability_gate_reason": profile.get("copyability_gate_reason") or "ok",
        "audit_verdict": verdict,
        "risk_flags": risks,
        "latency_arb_score": profile.get("latency_arb_score"),
        "crypto_profile_score": profile.get("crypto_profile_score"),
        "crypto_decisions": profile.get("crypto_decisions"),
        "crypto_win_rate_bayes": profile.get("crypto_win_rate_bayes"),
        "crypto_recent_decisions_30d": profile.get("crypto_recent_decisions_30d"),
        "crypto_recent_score_30d": profile.get("crypto_recent_score_30d"),
        "crypto_top_symbol": profile.get("crypto_top_symbol"),
        "crypto_top_symbol_pnl_share": profile.get("crypto_top_symbol_pnl_share"),
        "qualified_symbols": qualified_symbols,
        "style_mix": profile.get("wallet_archetype_styles") or {},
        "live_pick_count": len(wallet_picks),
        "live_pick_symbols": live_symbols,
        "live_pick_entry_quality": [pick.get("entry_quality_score") for pick in wallet_picks],
        "live_signal_count": len(wallet_signals),
        "live_signal_symbols": live_signal_symbols,
    }


def _find_snapshot_matches(
    profiles: list[dict[str, Any]],
    focus_keys: tuple[str, ...],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    matched: dict[str, dict[str, Any]] = {}
    missing = set(focus_keys)
    for key in focus_keys:
        for profile in profiles:
            if _matches_focus(_profile_tokens(profile), key):
                matched[key] = profile
                missing.discard(key)
                break
    return matched, missing


def _backfill_missing_focus_profiles(
    focus_keys: set[str],
    existing_wallets: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not focus_keys:
        return {}, []

    found: dict[str, dict[str, Any]] = {}
    unresolved = sorted(focus_keys)
    leaderboard = fetch_candidate_leaderboard(limit=150)
    for key in sorted(focus_keys):
        for row in leaderboard:
            if not _matches_focus(_leaderboard_tokens(row), key):
                continue
            wallet = str(row.get("proxyWallet") or "").lower()
            if wallet in existing_wallets:
                break
            profile = _score_wallet(row)
            if profile:
                found[key] = profile
                existing_wallets.add(wallet)
            break

    unresolved = [key for key in sorted(focus_keys) if key not in found]
    return found, unresolved


def generate_audit(
    *,
    root_dir: Path = ROOT_DIR,
    focus_keys: tuple[str, ...] = FOCUS_KEYS,
) -> dict[str, Any]:
    profiles_payload = _load_json(
        root_dir / "copy_trader_intel" / "data" / "polymarket_trader_profiles.json",
        {},
    )
    picks = _load_json(root_dir / "copy_trader_intel" / "data" / "polymarket_picks.json", [])
    whale_tracker = _load_json(
        root_dir / "prediction_market_agents" / "data" / "whale_tracker.json",
        {},
    )

    profiles = list(profiles_payload.get("qualified_traders") or [])
    whale_signals = list(whale_tracker.get("signals") or [])
    picks_by_wallet, signals_by_wallet = _index_outputs(picks, whale_signals)

    snapshot_matches, missing_focus = _find_snapshot_matches(profiles, focus_keys)
    backfilled_matches, unresolved_focus = _backfill_missing_focus_profiles(
        missing_focus,
        existing_wallets={str(profile.get("wallet") or "").lower() for profile in snapshot_matches.values()},
    )

    focus_audit: list[dict[str, Any]] = []
    for focus_key in focus_keys:
        profile = snapshot_matches.get(focus_key)
        source = "snapshot"
        if profile is None:
            profile = backfilled_matches.get(focus_key)
            source = "live_backfill"
        if profile is None:
            focus_audit.append(
                {
                    "focus_key": focus_key,
                    "source": "missing",
                    "audit_verdict": "missing",
                    "risk_flags": ["not_in_snapshot_or_backfill"],
                }
            )
            continue

        wallet = str(profile.get("wallet") or "").lower()
        focus_audit.append(
            _summarize_profile(
                focus_key,
                profile,
                picks_by_wallet.get(wallet, []),
                signals_by_wallet.get(wallet, []),
                source=source,
            )
        )

    archetype_counts = Counter(str(profile.get("wallet_archetype") or "unknown") for profile in profiles)
    gate_reason_counts = Counter(str(profile.get("copyability_gate_reason") or "ok") for profile in profiles)
    live_pick_counts = Counter(str(pick.get("wallet_archetype") or "unknown") for pick in picks)
    top_copyable_profiles = sorted(
        (
            {
                "user_name": profile.get("user_name"),
                "wallet": profile.get("wallet"),
                "wallet_archetype": profile.get("wallet_archetype"),
                "crypto_profile_score": profile.get("crypto_profile_score"),
                "latency_arb_score": profile.get("latency_arb_score"),
                "crypto_top_symbol_pnl_share": profile.get("crypto_top_symbol_pnl_share"),
            }
            for profile in profiles
            if profile.get("copyable_archetype", True)
        ),
        key=lambda row: (
            float(row.get("crypto_profile_score") or 0.0),
            -float(row.get("latency_arb_score") or 0.0),
        ),
        reverse=True,
    )[:10]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_updated_at": profiles_payload.get("updated_at"),
        "focus_keys": list(focus_keys),
        "focus_missing_keys": unresolved_focus,
        "focus_audit": focus_audit,
        "cohort_summary": {
            "snapshot_profile_count": len(profiles),
            "snapshot_pick_count": len(picks),
            "snapshot_whale_signal_count": len(whale_signals),
            "archetype_counts": dict(sorted(archetype_counts.items())),
            "gate_reason_counts": dict(sorted(gate_reason_counts.items())),
            "live_pick_archetype_counts": dict(sorted(live_pick_counts.items())),
            "top_copyable_profiles": top_copyable_profiles,
        },
    }


def save_audit(payload: dict[str, Any], path: Path = DATA_OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def main() -> int:
    payload = generate_audit()
    output_path = save_audit(payload)
    print(f"[PM AUDIT] saved {len(payload['focus_audit'])} focus rows -> {output_path}")
    for row in payload["focus_audit"]:
        print(
            f"  - {row.get('focus_key')}: {row.get('audit_verdict')} "
            f"({row.get('wallet_archetype')}, {row.get('copyability_gate_reason')})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
