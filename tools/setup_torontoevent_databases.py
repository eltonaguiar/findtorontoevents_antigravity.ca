"""
Setup all database schemas on torontoevent.net (GoDaddy) remote MySQL server.

Usage:
    python tools/setup_torontoevent_databases.py

Credentials are read from environment variables:
    TORONTOEVENT_DB_HOST  - MySQL hostname (or use --host flag)
    TORONTOEVENT_DB_USER  - MySQL user (default: admin)
    TORONTOEVENT_DB_PASS  - MySQL password (or DB_PASS_SERVER_FAVCREATORS)
    TORONTOEVENT_DB_PORT  - MySQL port (default: 3306)

Databases created/configured:
    ejaguiar1_stocks         - Stocks, forex (fxp_*), goldmine (gm_*), rapid validation,
                               pair fingerprints (pf_*), spike scanner (ss_*)
    ejaguiar1_crypto         - Crypto pairs and signals
    ejaguiar1_memecoin       - Meme coin picks
    ejaguiar1_sportsbet      - Sports betting picks and odds
    ejaguiar1_tvmoviestrailers - Movies, TV shows, trailers, playlists, users
    ejaguiar1_events         - Toronto events
    ejaguiar1_favcreators    - Creator platform
"""

import os
import sys
import argparse

try:
    import pymysql
except ImportError:
    print("Installing pymysql...")
    os.system(f"{sys.executable} -m pip install pymysql")
    import pymysql


def get_connection(host, user, password, port=3306, database=None):
    kwargs = dict(host=host, user=user, password=password, port=port, charset='utf8mb4')
    if database:
        kwargs['database'] = database
    return pymysql.connect(**kwargs)


def run_sql(cursor, sql, description=""):
    """Run a SQL statement, ignoring 'already exists' errors."""
    try:
        cursor.execute(sql)
        if description:
            print(f"  ✅ {description}")
    except pymysql.err.OperationalError as e:
        if e.args[0] in (1050, 1007, 1060):  # Table/DB already exists, duplicate column
            if description:
                print(f"  ↩️  Already exists: {description}")
        else:
            print(f"  ❌ Error ({description}): {e}")
            raise


# ─────────────────────────────────────────────────────────────────────────────
# ejaguiar1_stocks schemas
# ─────────────────────────────────────────────────────────────────────────────
STOCKS_SCHEMAS = [
    # Core stock picks
    ("""CREATE TABLE IF NOT EXISTS stock_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) NOT NULL,
        ticker VARCHAR(20) NOT NULL,
        pick_date DATE NOT NULL,
        entry_price DECIMAL(18,6),
        score DECIMAL(10,4),
        rating VARCHAR(20),
        risk_level VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_algo (algorithm_name),
        INDEX idx_ticker (ticker),
        INDEX idx_date (pick_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "stock_picks"),

    ("""CREATE TABLE IF NOT EXISTS daily_prices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        trade_date DATE NOT NULL,
        open_price DECIMAL(18,6),
        high_price DECIMAL(18,6),
        low_price DECIMAL(18,6),
        close_price DECIMAL(18,6),
        volume BIGINT,
        UNIQUE KEY uniq_ticker_date (ticker, trade_date),
        INDEX idx_ticker (ticker),
        INDEX idx_date (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "daily_prices"),

    ("""CREATE TABLE IF NOT EXISTS kc_algorithms (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        asset_class VARCHAR(50),
        strategy_type VARCHAR(50),
        is_active TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "kc_algorithms"),

    # Rapid validation
    ("""CREATE TABLE IF NOT EXISTS rapid_signals (
        signal_id INT AUTO_INCREMENT PRIMARY KEY,
        strategy_name VARCHAR(100) NOT NULL,
        pair VARCHAR(30),
        signal_type VARCHAR(20),
        strength DECIMAL(5,2),
        entry_price DECIMAL(18,6),
        take_profit DECIMAL(18,6),
        stop_loss DECIMAL(18,6),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) DEFAULT 'open',
        outcome VARCHAR(20),
        closed_at TIMESTAMP NULL,
        pnl DECIMAL(10,4),
        INDEX idx_strategy (strategy_name),
        INDEX idx_status (status),
        INDEX idx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "rapid_signals"),

    ("""CREATE TABLE IF NOT EXISTS rapid_strategy_stats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        strategy_name VARCHAR(100) UNIQUE NOT NULL,
        total_trades INT DEFAULT 0,
        wins INT DEFAULT 0,
        losses INT DEFAULT 0,
        win_rate DECIMAL(5,2) DEFAULT 0,
        avg_pnl DECIMAL(10,4) DEFAULT 0,
        total_pnl DECIMAL(12,4) DEFAULT 0,
        `rank` INT DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "rapid_strategy_stats"),

    # Forex (fxp_* prefix)
    ("""CREATE TABLE IF NOT EXISTS fxp_pairs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) UNIQUE NOT NULL,
        base_currency VARCHAR(10),
        quote_currency VARCHAR(10),
        category VARCHAR(30),
        pip_value DECIMAL(10,6) DEFAULT 0.0001
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "fxp_pairs"),

    ("""CREATE TABLE IF NOT EXISTS fxp_price_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        price_date DATE NOT NULL,
        open_price DECIMAL(18,6),
        high_price DECIMAL(18,6),
        low_price DECIMAL(18,6),
        close_price DECIMAL(18,6),
        volume BIGINT DEFAULT 0,
        UNIQUE KEY uniq_symbol_date (symbol, price_date),
        INDEX idx_symbol (symbol),
        INDEX idx_date (price_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "fxp_price_history"),

    ("""CREATE TABLE IF NOT EXISTS fxp_algorithms (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        family VARCHAR(50),
        description TEXT,
        algo_type VARCHAR(50),
        ideal_timeframe VARCHAR(20)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "fxp_algorithms"),

    ("""CREATE TABLE IF NOT EXISTS fxp_pair_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        algorithm_id INT,
        algorithm_name VARCHAR(100),
        pick_date DATE NOT NULL,
        pick_time TIME,
        entry_price DECIMAL(18,6),
        direction VARCHAR(10),
        score DECIMAL(10,4),
        rating VARCHAR(20),
        risk_level VARCHAR(20),
        timeframe VARCHAR(20),
        pick_hash VARCHAR(64) UNIQUE,
        INDEX idx_symbol (symbol),
        INDEX idx_algo (algorithm_name),
        INDEX idx_date (pick_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "fxp_pair_picks"),

    ("""CREATE TABLE IF NOT EXISTS fxp_portfolios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        strategy_type VARCHAR(50),
        algorithm_filter VARCHAR(100),
        initial_capital DECIMAL(14,2) DEFAULT 10000,
        leverage DECIMAL(6,2) DEFAULT 1.0,
        spread_pips DECIMAL(6,2) DEFAULT 2.0,
        stop_loss_pips DECIMAL(8,2) DEFAULT 50,
        take_profit_pips DECIMAL(8,2) DEFAULT 100,
        max_hold_days INT DEFAULT 5,
        position_size_pct DECIMAL(5,2) DEFAULT 2.0,
        max_positions INT DEFAULT 5,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "fxp_portfolios"),

    ("""CREATE TABLE IF NOT EXISTS fxp_backtest_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        portfolio_id INT,
        run_name VARCHAR(100),
        algorithm_filter VARCHAR(100),
        start_date DATE,
        end_date DATE,
        initial_capital DECIMAL(14,2),
        final_value DECIMAL(14,2),
        total_return_pct DECIMAL(10,4),
        annualized_return_pct DECIMAL(10,4),
        total_trades INT DEFAULT 0,
        winning_trades INT DEFAULT 0,
        losing_trades INT DEFAULT 0,
        win_rate DECIMAL(5,2),
        avg_win_pips DECIMAL(10,4),
        avg_loss_pips DECIMAL(10,4),
        best_trade_pips DECIMAL(10,4),
        worst_trade_pips DECIMAL(10,4),
        max_drawdown_pct DECIMAL(10,4),
        total_spread_cost DECIMAL(14,4),
        sharpe_ratio DECIMAL(8,4),
        sortino_ratio DECIMAL(8,4),
        profit_factor DECIMAL(8,4),
        expectancy_pips DECIMAL(10,4),
        avg_hold_days DECIMAL(8,2),
        leverage_used DECIMAL(6,2),
        params_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "fxp_backtest_results"),

    # Goldmine unified picks (gm_* prefix)
    ("""CREATE TABLE IF NOT EXISTS gm_unified_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source_system VARCHAR(30) NOT NULL,
        ticker VARCHAR(30),
        pick_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        entry_price DECIMAL(18,6),
        current_price DECIMAL(18,6),
        target_price DECIMAL(18,6),
        stop_price DECIMAL(18,6),
        direction VARCHAR(10),
        status VARCHAR(20) DEFAULT 'open',
        pnl_pct DECIMAL(10,4),
        outcome VARCHAR(20),
        closed_at TIMESTAMP NULL,
        hold_hours INT DEFAULT 24,
        metadata_json TEXT,
        INDEX idx_source (source_system),
        INDEX idx_status (status),
        INDEX idx_pick_time (pick_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "gm_unified_picks"),

    ("""CREATE TABLE IF NOT EXISTS gm_failure_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source_system VARCHAR(30) NOT NULL,
        alert_type VARCHAR(50),
        alert_message TEXT,
        alert_date DATE NOT NULL,
        is_active TINYINT(1) DEFAULT 1,
        resolved_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_source (source_system),
        INDEX idx_active (is_active),
        INDEX idx_date (alert_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "gm_failure_alerts"),

    # Pair fingerprints (pf_* prefix)
    ("""CREATE TABLE IF NOT EXISTS pf_fingerprints (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        fingerprint_date DATE NOT NULL,
        pattern_type VARCHAR(50),
        confidence DECIMAL(5,2),
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol),
        INDEX idx_date (fingerprint_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "pf_fingerprints"),

    ("""CREATE TABLE IF NOT EXISTS pf_pair_patterns (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        pattern_name VARCHAR(50),
        occurrence_count INT DEFAULT 0,
        avg_outcome DECIMAL(10,4),
        last_seen DATE,
        metadata_json TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "pf_pair_patterns"),

    ("""CREATE TABLE IF NOT EXISTS pf_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30),
        alert_type VARCHAR(50),
        message TEXT,
        is_active TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "pf_alerts"),

    # Spike scanner (ss_* prefix)
    ("""CREATE TABLE IF NOT EXISTS ss_spikes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        spike_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        direction VARCHAR(10),
        magnitude_pct DECIMAL(10,4),
        volume_multiplier DECIMAL(10,4),
        spike_type VARCHAR(30),
        metadata_json TEXT,
        INDEX idx_symbol (symbol),
        INDEX idx_time (spike_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "ss_spikes"),

    ("""CREATE TABLE IF NOT EXISTS ss_baselines (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30) UNIQUE NOT NULL,
        avg_volume BIGINT,
        avg_range_pct DECIMAL(10,4),
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "ss_baselines"),
]


# ─────────────────────────────────────────────────────────────────────────────
# ejaguiar1_crypto schemas
# ─────────────────────────────────────────────────────────────────────────────
CRYPTO_SCHEMAS = [
    ("""CREATE TABLE IF NOT EXISTS cp_pairs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30) UNIQUE NOT NULL,
        base_asset VARCHAR(20),
        quote_asset VARCHAR(20),
        exchange VARCHAR(30),
        is_active TINYINT(1) DEFAULT 1
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "cp_pairs"),

    ("""CREATE TABLE IF NOT EXISTS cp_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        strategy_name VARCHAR(100),
        signal_type VARCHAR(20),
        strength DECIMAL(5,2),
        entry_price DECIMAL(18,6),
        take_profit DECIMAL(18,6),
        stop_loss DECIMAL(18,6),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) DEFAULT 'open',
        outcome VARCHAR(20),
        closed_at TIMESTAMP NULL,
        pnl_pct DECIMAL(10,4),
        INDEX idx_symbol (symbol),
        INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "cp_signals"),

    ("""CREATE TABLE IF NOT EXISTS cp_prices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        price_date DATE NOT NULL,
        open_price DECIMAL(18,6),
        high_price DECIMAL(18,6),
        low_price DECIMAL(18,6),
        close_price DECIMAL(18,6),
        volume DECIMAL(24,4),
        UNIQUE KEY uniq_symbol_date (symbol, price_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "cp_prices"),

    ("""CREATE TABLE IF NOT EXISTS cp_strategies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        win_rate DECIMAL(5,2),
        avg_pnl DECIMAL(10,4),
        is_active TINYINT(1) DEFAULT 1
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "cp_strategies"),

    ("""CREATE TABLE IF NOT EXISTS cp_backtest_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        strategy_name VARCHAR(100),
        symbol VARCHAR(30),
        start_date DATE,
        end_date DATE,
        total_trades INT DEFAULT 0,
        win_rate DECIMAL(5,2),
        total_return_pct DECIMAL(10,4),
        max_drawdown_pct DECIMAL(10,4),
        sharpe_ratio DECIMAL(8,4),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "cp_backtest_results"),
]


# ─────────────────────────────────────────────────────────────────────────────
# ejaguiar1_memecoin schemas
# ─────────────────────────────────────────────────────────────────────────────
MEMECOIN_SCHEMAS = [
    ("""CREATE TABLE IF NOT EXISTS meme_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        pick_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        entry_price DECIMAL(18,8),
        target_price DECIMAL(18,8),
        stop_price DECIMAL(18,8),
        source VARCHAR(50),
        source_url TEXT,
        sentiment_score DECIMAL(5,2),
        status VARCHAR(20) DEFAULT 'open',
        outcome VARCHAR(20),
        pnl_pct DECIMAL(10,4),
        closed_at TIMESTAMP NULL,
        INDEX idx_symbol (symbol),
        INDEX idx_status (status),
        INDEX idx_pick_time (pick_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "meme_picks"),

    ("""CREATE TABLE IF NOT EXISTS meme_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(30),
        alert_type VARCHAR(50),
        message TEXT,
        is_active TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "meme_alerts"),
]


# ─────────────────────────────────────────────────────────────────────────────
# ejaguiar1_sportsbet schemas
# ─────────────────────────────────────────────────────────────────────────────
SPORTSBET_SCHEMAS = [
    ("""CREATE TABLE IF NOT EXISTS sb_bets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sport VARCHAR(30) NOT NULL,
        league VARCHAR(50),
        event_name VARCHAR(200),
        event_date DATETIME,
        bet_type VARCHAR(50),
        pick VARCHAR(100),
        odds DECIMAL(8,4),
        stake DECIMAL(10,2) DEFAULT 1.0,
        status VARCHAR(20) DEFAULT 'open',
        result VARCHAR(20),
        pnl DECIMAL(10,2),
        clv_value DECIMAL(8,4),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_sport (sport),
        INDEX idx_status (status),
        INDEX idx_event_date (event_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "sb_bets"),

    ("""CREATE TABLE IF NOT EXISTS sb_odds (
        id INT AUTO_INCREMENT PRIMARY KEY,
        event_id VARCHAR(100),
        bookmaker VARCHAR(50),
        market VARCHAR(50),
        selection VARCHAR(100),
        odds DECIMAL(8,4),
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_event (event_id),
        INDEX idx_bookmaker (bookmaker)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "sb_odds"),

    ("""CREATE TABLE IF NOT EXISTS sb_bankroll (
        id INT AUTO_INCREMENT PRIMARY KEY,
        record_date DATE UNIQUE NOT NULL,
        starting_balance DECIMAL(12,2),
        ending_balance DECIMAL(12,2),
        bets_placed INT DEFAULT 0,
        bets_won INT DEFAULT 0,
        bets_lost INT DEFAULT 0,
        bets_pending INT DEFAULT 0,
        total_staked DECIMAL(12,2) DEFAULT 0,
        total_pnl DECIMAL(12,2) DEFAULT 0,
        roi_pct DECIMAL(8,4)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "sb_bankroll"),

    ("""CREATE TABLE IF NOT EXISTS sb_daily_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pick_date DATE NOT NULL,
        sport VARCHAR(30),
        pick_details TEXT,
        confidence DECIMAL(5,2),
        algorithm VARCHAR(100),
        status VARCHAR(20) DEFAULT 'pending',
        INDEX idx_date (pick_date),
        INDEX idx_sport (sport)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "sb_daily_picks"),
]


# ─────────────────────────────────────────────────────────────────────────────
# ejaguiar1_tvmoviestrailers schemas
# ─────────────────────────────────────────────────────────────────────────────
TVMOVIES_SCHEMAS = [
    ("""CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        email VARCHAR(200) UNIQUE,
        password_hash VARCHAR(255),
        display_name VARCHAR(100),
        avatar_url TEXT,
        discord_id VARCHAR(50),
        google_id VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "users"),

    ("""CREATE TABLE IF NOT EXISTS movies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tmdb_id INT UNIQUE,
        title VARCHAR(255) NOT NULL,
        original_title VARCHAR(255),
        release_date DATE,
        overview TEXT,
        poster_path VARCHAR(255),
        backdrop_path VARCHAR(255),
        vote_average DECIMAL(4,2),
        vote_count INT DEFAULT 0,
        popularity DECIMAL(10,3),
        genre_ids TEXT,
        media_type VARCHAR(20) DEFAULT 'movie',
        adult TINYINT(1) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_tmdb (tmdb_id),
        INDEX idx_release (release_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "movies"),

    ("""CREATE TABLE IF NOT EXISTS trailers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        movie_id INT,
        tmdb_id INT,
        youtube_key VARCHAR(20) UNIQUE,
        name VARCHAR(255),
        type VARCHAR(50),
        official TINYINT(1) DEFAULT 0,
        published_at DATETIME,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_movie (movie_id),
        INDEX idx_tmdb (tmdb_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "trailers"),

    ("""CREATE TABLE IF NOT EXISTS streaming_providers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tmdb_id INT NOT NULL,
        country VARCHAR(5) DEFAULT 'CA',
        provider_id INT,
        provider_name VARCHAR(100),
        logo_path VARCHAR(255),
        display_priority INT,
        access_type VARCHAR(20),
        INDEX idx_tmdb (tmdb_id),
        INDEX idx_provider (provider_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "streaming_providers"),

    ("""CREATE TABLE IF NOT EXISTS playlists (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        is_public TINYINT(1) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "playlists"),

    ("""CREATE TABLE IF NOT EXISTS playlist_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        playlist_id INT NOT NULL,
        movie_id INT,
        tmdb_id INT,
        position INT DEFAULT 0,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_playlist (playlist_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "playlist_items"),

    ("""CREATE TABLE IF NOT EXISTS movie_likes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        tmdb_id INT NOT NULL,
        liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_user_movie (user_id, tmdb_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "movie_likes"),

    ("""CREATE TABLE IF NOT EXISTS movie_watch_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        tmdb_id INT NOT NULL,
        watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        watch_progress_pct INT DEFAULT 0,
        INDEX idx_user (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "movie_watch_history"),

    ("""CREATE TABLE IF NOT EXISTS user_queues (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        tmdb_id INT NOT NULL,
        position INT DEFAULT 0,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_user_queue (user_id, tmdb_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "user_queues"),

    ("""CREATE TABLE IF NOT EXISTS user_preferences (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT UNIQUE NOT NULL,
        preferred_genres TEXT,
        preferred_languages TEXT,
        ui_theme VARCHAR(20) DEFAULT 'dark',
        notifications_enabled TINYINT(1) DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "user_preferences"),
]


# ─────────────────────────────────────────────────────────────────────────────
# ejaguiar1_events schemas
# ─────────────────────────────────────────────────────────────────────────────
EVENTS_SCHEMAS = [
    ("""CREATE TABLE IF NOT EXISTS events_log (
        event_id VARCHAR(100) PRIMARY KEY,
        title VARCHAR(500) NOT NULL,
        date DATETIME,
        end_date DATETIME,
        location VARCHAR(500),
        lat DECIMAL(10,7),
        lng DECIMAL(10,7),
        categories TEXT,
        tags TEXT,
        status VARCHAR(20) DEFAULT 'active',
        multi_day TINYINT(1) DEFAULT 0,
        url TEXT,
        image_url TEXT,
        organizer VARCHAR(255),
        price_min DECIMAL(10,2),
        price_max DECIMAL(10,2),
        source VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_date (date),
        INDEX idx_status (status),
        INDEX idx_source (source)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "events_log"),

    ("""CREATE TABLE IF NOT EXISTS event_pulls (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pull_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source VARCHAR(50),
        events_found INT DEFAULT 0,
        events_added INT DEFAULT 0,
        events_updated INT DEFAULT 0,
        status VARCHAR(20) DEFAULT 'success',
        error_message TEXT,
        duration_seconds DECIMAL(8,2)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "event_pulls"),

    ("""CREATE TABLE IF NOT EXISTS stats_summary (
        id INT AUTO_INCREMENT PRIMARY KEY,
        stat_date DATE UNIQUE NOT NULL,
        total_events INT DEFAULT 0,
        active_events INT DEFAULT 0,
        upcoming_events INT DEFAULT 0,
        sources_count INT DEFAULT 0,
        categories_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""", "stats_summary"),
]


def setup_database(conn, db_name, schemas):
    """Create database and all its tables."""
    cursor = conn.cursor()
    print(f"\n📦 Setting up database: {db_name}")

    run_sql(cursor, f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
            f"database {db_name}")
    run_sql(cursor, f"USE `{db_name}`", f"switched to {db_name}")

    for sql, description in schemas:
        run_sql(cursor, sql, description)

    conn.commit()
    cursor.close()
    print(f"  ✅ {db_name} setup complete ({len(schemas)} tables)")


def main():
    parser = argparse.ArgumentParser(description='Setup torontoevent.net databases')
    parser.add_argument('--host', default=os.environ.get('TORONTOEVENT_DB_HOST', 'localhost'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('TORONTOEVENT_DB_PORT', '3306')))
    parser.add_argument('--user', default=os.environ.get('TORONTOEVENT_DB_USER',
                                                          os.environ.get('DB_USER_TORONTOEVENT', 'admin')))
    parser.add_argument('--password', default=os.environ.get('TORONTOEVENT_DB_PASS',
                                                              os.environ.get('DB_PASS_SERVER_FAVCREATORS', '')))
    parser.add_argument('--only', help='Only setup specific DB (e.g. ejaguiar1_stocks)', default=None)
    args = parser.parse_args()

    if not args.password:
        print("❌ No password found. Set TORONTOEVENT_DB_PASS or DB_PASS_SERVER_FAVCREATORS env var.")
        sys.exit(1)

    print(f"🔌 Connecting to MySQL at {args.host}:{args.port} as '{args.user}'...")
    try:
        conn = get_connection(args.host, args.user, args.password, args.port)
        print("✅ Connected successfully!\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  - For local test: use --host localhost")
        print("  - For remote (GoDaddy): ensure remote MySQL access is enabled in cPanel")
        print("  - Server hostname: p3plzcpnl508313.prod.phx3.secureserver.net")
        sys.exit(1)

    databases = {
        'ejaguiar1_stocks':          STOCKS_SCHEMAS,
        'ejaguiar1_crypto':          CRYPTO_SCHEMAS,
        'ejaguiar1_memecoin':        MEMECOIN_SCHEMAS,
        'ejaguiar1_sportsbet':       SPORTSBET_SCHEMAS,
        'ejaguiar1_tvmoviestrailers': TVMOVIES_SCHEMAS,
        'ejaguiar1_events':          EVENTS_SCHEMAS,
    }

    for db_name, schemas in databases.items():
        if args.only and args.only != db_name:
            continue
        setup_database(conn, db_name, schemas)

    conn.close()

    print("\n" + "="*60)
    print("✅ All databases setup complete on torontoevent.net!")
    print("="*60)
    print("\nDatabases configured:")
    for db_name in databases:
        if not args.only or args.only == db_name:
            print(f"  ✅ {db_name}")
    print("\nNext steps:")
    print("  1. Deploy PHP API files via GitHub Actions workflows")
    print("  2. Run: gh workflow run 'torontoevent-deploy-competition.yml'")
    print("  3. Verify: https://torontoevent.net/STOCKS/competition/")


if __name__ == '__main__':
    main()
