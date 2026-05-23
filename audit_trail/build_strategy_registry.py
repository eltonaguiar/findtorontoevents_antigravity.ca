#!/usr/bin/env python3
"""
Build strategy_registry table in ejaguiar1_stocks from docs/ALL_STRATEGIES.md.

Parses the structured markdown tables and creates a MySQL lookup table mapping
every strategy to its system, asset class, type, win rate, and source reference.

Run:  py -m audit_trail.build_strategy_registry
"""

import re
import sys
import json
from pathlib import Path

try:
    import pymysql
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"],
                          stdout=subprocess.DEVNULL)
    import pymysql

REPO = Path(__file__).resolve().parent.parent
MD_PATH = REPO / "docs" / "ALL_STRATEGIES.md"
KILL_LIST_PATH = REPO / "alpha_engine" / "strategy_kill_list.json"


def get_kill_list():
    """Load institutional kill list from JSON and combine with legacy BANNED list."""
    legacy_banned = {
        "smart_money_fvg", "fourier_cycle_detector", "exchange_netflow_reversal",
        "price_touch_recurrence", "halloween_effect", "altcoin_season_rotation",
        "momentum_mean_rev_blend", "cross_sectional_momentum",
        "quan_engine_position",  # 0% WR, 13/13 SL exits, -$995 (2026-04-01 audit)
        "quan_engine_scalp",     # 0% WR zombie — killed 2026-04-02
        "quan_engine_swing",     # 0% WR zombie — killed 2026-04-02
        "futures_ema_stack_momentum",  # 0/4=0% WR, 7 active zombie picks — killed 2026-04-02
        "st_rsi_momentum_confluence",  # 10% WR (10W/95L), -296% PnL — killed per PEER_INTEL 2026-04-02
    }
    
    if KILL_LIST_PATH.exists():
        try:
            with open(KILL_LIST_PATH, "r") as f:
                data = json.load(f)
                institutional = set(data.get("institutional_kills", []))
                # Normalize names (strip spaces, etc.)
                institutional = {k.strip().replace(" ", "_").lower() for k in institutional}
                return legacy_banned.union(institutional)
        except Exception as e:
            print(f"Warning: Failed to load kill list: {e}")
    
    return legacy_banned

BANNED = get_kill_list()


def create_table(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS strategy_registry (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        strategy_id     VARCHAR(100)    NOT NULL COMMENT 'Unique strategy identifier (e.g. btc_ichimoku_cloud)',
        strategy_name   VARCHAR(200)    DEFAULT NULL COMMENT 'Human-readable name or description',
        system_name     VARCHAR(100)    NOT NULL COMMENT 'Parent system (alpha_engine, kimi, baby_strategies, etc.)',
        section_name    VARCHAR(200)    DEFAULT NULL COMMENT 'Section from ALL_STRATEGIES.md',
        module_file     VARCHAR(300)    DEFAULT NULL COMMENT 'Source file path',
        asset_class     VARCHAR(20)     DEFAULT 'CRYPTO',
        strategy_type   VARCHAR(50)     DEFAULT NULL COMMENT 'Type/category (Mean Reversion, Trend, etc.)',
        win_rate        VARCHAR(30)     DEFAULT NULL COMMENT 'Documented WR (e.g. 65%, 60-70%)',
        sharpe          VARCHAR(30)     DEFAULT NULL COMMENT 'Documented Sharpe ratio',
        source_ref      VARCHAR(200)    DEFAULT NULL COMMENT 'Academic/research source',
        is_banned       TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '1 if strategy is in BANNED_STRATEGIES',
        is_active       TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1 if strategy is currently active',
        notes           TEXT            DEFAULT NULL,
        created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME        DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE INDEX idx_strategy_system (strategy_id, system_name),
        INDEX idx_system      (system_name),
        INDEX idx_asset_class (asset_class),
        INDEX idx_banned      (is_banned)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    print("Table strategy_registry ready.")


# Map section headers to (system_name, asset_class, module_file)
SECTION_MAP = {
    "1. Baby Strategies": ("baby_strategies", "CRYPTO", "baby_strategies/"),
    "1b. Paper Trading Strategies": ("paper_trading", "CRYPTO", "paper_trading/strategies/"),
    "2. Alpha Engine — Core Crypto": ("alpha_engine", "CRYPTO", "alpha_engine/crypto_strategies.py"),
    "3. Alpha Engine — On-Chain": ("alpha_engine", "CRYPTO", "alpha_engine/onchain_strategies.py"),
    "4. Alpha Engine — Quant": ("alpha_engine", "CRYPTO", "alpha_engine/quant_strategies.py"),
    "5. Alpha Engine — Advanced": ("alpha_engine", "CRYPTO", "alpha_engine/advanced_strategies.py"),
    "6. Alpha Engine — Event-Driven": ("alpha_engine", "CRYPTO", "alpha_engine/event_strategies.py"),
    "7. KIMI Rise of the Claw — Crypto Acceleration": ("kimi_riseoftheclaw", "CRYPTO", "KIMI_RISEOFTHECLAW/crypto_acceleration_engine.py"),
    "8. KIMI Rise of the Claw — Proven Crypto/Forex": ("kimi_riseoftheclaw", "CRYPTO", "KIMI_RISEOFTHECLAW/proven_crypto_forex_strategies.py"),
    "9. Coinglass DNA Bundle": ("coinglass", "CRYPTO", "coinglass_strategies/"),
    "10. ML Battleground": ("ml_battleground", "CRYPTO", "ml_battleground/"),
    "11. Crypto ML Edge": ("crypto_ml_edge", "CRYPTO", "crypto_ml_edge/"),
    "12. Mercury2 Ensemble": ("mercury2", "CRYPTO", "mercury2/"),
    "13. Crypto Signal Engine": ("crypto_signal_engine", "CRYPTO", "crypto_signal_engine/"),
    "14. ML Crypto Predictor": ("ml_crypto_predictor", "CRYPTO", "ml_crypto_predictor/"),
    "15. Claude Gainer ML": ("claude_gainer_ml", "CRYPTO", "claude_gainer_ml/"),
    "16. Root-Level Crypto": ("root_level", "CRYPTO", None),
    "17. AI-Generated Incubator": ("incubator", "CRYPTO", "incubator/"),
    "18. Alpha Engine — Forex": ("alpha_engine", "FOREX", "alpha_engine/forex_strategies.py"),
    "19. Alpha Engine — Equity": ("alpha_engine", "EQUITY", "alpha_engine/equity_strategies.py"),
    "20. Options": ("options", "EQUITY", None),
    "21. Root-Level Equity": ("root_level", "EQUITY", None),
    "22. Bundle-Optimized": ("bundle", "MULTI", None),
    "23. Sentinel Fund": ("sentinel", "MULTI", None),
    "24. Quantum Fusion": ("quantum_fusion", "MULTI", None),
    "25. DNA / Genome": ("genome", "CRYPTO", "genome/"),
    "26. Meta-Strategy": ("meta_strategy", "CRYPTO", "meta_strategy/"),
    "27. Quant Lab": ("quant_lab", "CRYPTO", None),
    "28. FreshPicks DNA": ("freshpicks_dna", "CRYPTO", None),
    "29. ML Techniques": ("ml_infrastructure", "MULTI", None),
    "30. Pine Scripts": ("pine_scripts", "MULTI", None),
    "32. Multi-Asset Strategy Engineering (600 Variants)": ("alpha_engine", "MULTI", "alpha_engine/generated_v2_bundle.py"),
}


def parse_strategies(md_text):
    """Parse ALL_STRATEGIES.md and extract strategy entries."""
    strategies = []
    current_section = None
    current_system = None
    current_asset = "CRYPTO"
    current_module = None

    for line in md_text.split("\n"):
        # Detect section headers: ## N. Name
        m = re.match(r"^## (\d+[a-z]?)\.\s+(.+)", line)
        if m:
            num = m.group(1)
            title = m.group(2).strip()
            current_section = f"{num}. {title}"
            # Find matching config
            for prefix, (sys, ac, mod) in SECTION_MAP.items():
                if current_section.startswith(prefix):
                    current_system = sys
                    current_asset = ac
                    current_module = mod
                    break
            continue

        # Parse table rows: | N | `strategy_id` | ... |
        if not line.strip().startswith("|"):
            continue
        if line.strip().startswith("|---") or line.strip().startswith("| #"):
            continue

        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 2:
            continue

        # Skip header rows
        if cols[0] in ("#", "Module", "System", "Script"):
            continue

        # Extract strategy ID from backticks
        strategy_id = None
        strategy_name = None
        strategy_type = None
        win_rate = None
        sharpe = None
        source_ref = None
        module_file = current_module

        for i, col in enumerate(cols):
            # Strategy ID in backticks
            bt_match = re.search(r"`([^`]+)`", col)
            if bt_match and i <= 1:
                val = bt_match.group(1)
                if val.endswith(".py"):
                    if i == 0 or (strategy_id is None):
                        strategy_id = val.replace(".py", "")
                        if current_system == "baby_strategies":
                            module_file = f"baby_strategies/{val}"
                        elif current_system == "paper_trading":
                            module_file = f"paper_trading/strategies/{val}"
                else:
                    strategy_id = val

            # Strategy type (if column header was "Type")
            if i >= 2 and col and not col.startswith("`"):
                if "/" in col or col in ("Trend", "Momentum", "Mean Reversion", "Breakout",
                                          "Ensemble", "Machine Learning", "Sentiment",
                                          "Pattern", "Volume", "DCA"):
                    strategy_type = col

            # Win rate
            wr_match = re.search(r"(\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?)\s*%", col)
            if wr_match:
                win_rate = wr_match.group(0)

            # Sharpe
            sh_match = re.search(r"[Ss]harpe\s*[~≈]?\s*([\d.]+)", col)
            if sh_match:
                sharpe = sh_match.group(1)

            # Source reference (parenthetical academic refs)
            ref_match = re.search(r"([A-Z][a-z]+(?:\s+(?:et al\.|&|and)\s+[A-Z][a-z]+)?\s*\(\d{4}\))", col)
            if ref_match:
                source_ref = ref_match.group(1)
            elif i >= 2 and col and not col.startswith("`") and col != "—":
                if not strategy_type and not win_rate:
                    if len(col) > 3:
                        strategy_name = col

        if not strategy_id:
            continue
        if strategy_id in ("Backtest utility",):
            continue

        # Range expansion: e.g. "forex_rsi_rev_v1-v100" -> 100 entries
        range_match = re.search(r"(.+)_v(\d+)-v(\d+)", strategy_id)
        ids_to_add = [strategy_id]
        if range_match:
            base_prefix = range_match.group(1)
            start_num = int(range_match.group(2))
            end_num = int(range_match.group(3))
            ids_to_add = [f"{base_prefix}_v{i}" for i in range(start_num, end_num + 1)]

        for sid in ids_to_add:
            # Clean up
            final_name = strategy_name
            if len(ids_to_add) > 1:
                final_name = f"{strategy_name} Variant {sid.split('_v')[-1]}"
            elif not final_name:
                final_name = sid.replace("_", " ").title()

            strategies.append({
                "strategy_id": sid,
                "strategy_name": final_name,
                "system_name": current_system or "unknown",
                "section_name": current_section,
                "module_file": module_file,
                "asset_class": current_asset,
                "strategy_type": strategy_type,
                "win_rate": win_rate,
                "sharpe": sharpe,
                "source_ref": source_ref,
                "is_banned": 1 if sid in BANNED else 0,
            })

    return strategies


def main():
    if not MD_PATH.exists():
        print(f"ERROR: {MD_PATH} not found")
        sys.exit(1)

    md_text = MD_PATH.read_text(encoding="utf-8")
    strategies = parse_strategies(md_text)
    print(f"Parsed {len(strategies)} strategies from ALL_STRATEGIES.md")

    try:
        from tools.db_env import get_stocks_creds
        _creds = get_stocks_creds()
    except Exception:
        import logging as _lg
        _lg.getLogger(__name__).warning("get_stocks_creds() failed — check DB_PASS_STOCKS env var")
        _creds = dict(host="mysql.50webs.com", user="ejaguiar1_stocks",
                      password="", database="ejaguiar1_stocks",
                      connect_timeout=15, autocommit=True)
    conn = pymysql.connect(**{**_creds, "autocommit": True})
    cur = conn.cursor()
    create_table(cur)

    inserted = 0
    updated = 0
    for s in strategies:
        try:
            cur.execute(
                "INSERT INTO strategy_registry "
                "(strategy_id, strategy_name, system_name, section_name, module_file, "
                "asset_class, strategy_type, win_rate, sharpe, source_ref, is_banned) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE "
                "strategy_name=VALUES(strategy_name), system_name=VALUES(system_name), "
                "section_name=VALUES(section_name), module_file=VALUES(module_file), "
                "asset_class=VALUES(asset_class), strategy_type=VALUES(strategy_type), "
                "win_rate=VALUES(win_rate), sharpe=VALUES(sharpe), "
                "source_ref=VALUES(source_ref), is_banned=VALUES(is_banned)",
                (s["strategy_id"], s["strategy_name"], s["system_name"],
                 s["section_name"], s["module_file"], s["asset_class"],
                 s["strategy_type"], s["win_rate"], s["sharpe"],
                 s["source_ref"], s["is_banned"]),
            )
            if cur.rowcount == 1:
                inserted += 1
            elif cur.rowcount == 2:
                updated += 1
        except Exception as e:
            print(f"  Error: {s['strategy_id']}: {e}")

    # Summary
    cur.execute("SELECT COUNT(*) FROM strategy_registry")
    total = cur.fetchone()[0]
    cur.execute("SELECT system_name, COUNT(*) FROM strategy_registry GROUP BY system_name ORDER BY 2 DESC")
    by_system = cur.fetchall()
    cur.execute("SELECT asset_class, COUNT(*) FROM strategy_registry GROUP BY asset_class ORDER BY 2 DESC")
    by_asset = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM strategy_registry WHERE is_banned=1")
    banned_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM strategy_registry WHERE win_rate IS NOT NULL")
    wr_cnt = cur.fetchone()[0]

    print(f"\n=== STRATEGY REGISTRY COMPLETE ===")
    print(f"Inserted: {inserted}, Updated: {updated}")
    print(f"Total strategies: {total}")
    print(f"With documented WR: {wr_cnt}")
    print(f"Banned: {banned_cnt}")
    print(f"\nBy system:")
    for sys, cnt in by_system:
        print(f"  {sys:<30} {cnt:>4}")
    print(f"\nBy asset class:")
    for ac, cnt in by_asset:
        print(f"  {ac:<20} {cnt:>4}")

    conn.close()


if __name__ == "__main__":
    main()
