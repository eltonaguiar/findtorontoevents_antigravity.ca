<?php
/**
 * sync_config.php -- Bi-directional sync configuration.
 * PHP 5.2-safe. No closures, no short array syntax, no ?:, no ??.
 *
 * Defines:
 *  - Site identity detection
 *  - Per-table merge strategies
 *  - Databases that participate in user-data sync
 *  - Safeguard thresholds
 */

// ── Site Identity ────────────────────────────────────────────────────────────

function sync_detect_site() {
    $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : '';
    if (strpos($host, 'torontoevent.net') !== false) {
        return 'torontoevent.net';
    }
    if (strpos($host, 'tdotevent.ca') !== false) {
        return 'findtorontoevents.ca'; // same DB as primary
    }
    return 'findtorontoevents.ca';
}

// ── Merge Strategies ─────────────────────────────────────────────────────────
// LWW       = Last-Write-Wins by sync_version (higher wins), timestamp tiebreaker
// UNION     = Merge rows by composite key; additions from both sites kept
// UNION_DEL = Like UNION but DELETE operations win if newer
// AGGREGATE = Special per-field merge (MAX, MIN) for metrics
// JSON_UNION = Merge JSON arrays by element ID (for user_lists.creators)

function sync_get_merge_strategies() {
    return array(
        // ejaguiar1_favcreators tables
        'users'                          => 'LWW',
        'user_lists'                     => 'LWW',
        'user_notes'                     => 'LWW',
        'user_secondary_notes'           => 'LWW',
        'user_link_lists'                => 'LWW',
        'user_preferences'               => 'LWW',
        'user_saved_events'              => 'UNION_DEL',
        'user_visit_days'                => 'AGGREGATE',
        'notification_preferences'       => 'UNION_DEL',
        'accountability_reminder_settings'   => 'LWW',
        'accountability_followup_optouts'    => 'UNION_DEL',
        'accountability_followup_log'        => 'UNION',
        'accountability_reminder_log'        => 'UNION',
        'stock_subscriptions'            => 'UNION_DEL',

        // ejaguiar1_tvmoviestrailers tables
        'user_queues'                    => 'UNION_DEL',
        'shared_playlists'               => 'LWW',
        'playlist_items'                 => 'UNION_DEL',
    );
}

// ── Aggregate merge rules for user_visit_days ────────────────────────────────
// field_name => aggregate_function
function sync_get_aggregate_rules() {
    return array(
        'user_visit_days' => array(
            'distinct_days'    => 'MAX',
            'first_visit_at'   => 'MIN',
            'last_visit_at'    => 'MAX',
            'last_day_counted' => 'MAX',
        ),
    );
}

// ── Tables that participate in bi-directional sync ───────────────────────────
// Grouped by database name.
function sync_get_user_tables() {
    return array(
        'ejaguiar1_favcreators' => array(
            'users',
            'user_lists',
            'user_notes',
            'user_secondary_notes',
            'user_link_lists',
            'user_preferences',
            'user_saved_events',
            'user_visit_days',
            'notification_preferences',
            'accountability_reminder_settings',
            'accountability_followup_optouts',
            'accountability_followup_log',
            'accountability_reminder_log',
            'stock_subscriptions',
        ),
        'ejaguiar1_tvmoviestrailers' => array(
            'user_queues',
            'user_preferences',
            'shared_playlists',
            'playlist_items',
        ),
    );
}

// ── Primary key definitions per table ────────────────────────────────────────
// Used to serialize row_key in the changelog.
function sync_get_primary_keys() {
    return array(
        'users'                              => array('id'),
        'user_lists'                         => array('user_id'),
        'user_notes'                         => array('user_id', 'creator_id'),
        'user_secondary_notes'               => array('user_id', 'creator_id'),
        'user_link_lists'                    => array('user_id', 'list_name'),
        'user_preferences'                   => array('user_id'),
        'user_saved_events'                  => array('user_id', 'event_id'),
        'user_visit_days'                    => array('user_id'),
        'notification_preferences'           => array('user_id', 'creator_id'),
        'accountability_reminder_settings'   => array('discord_user_id', 'app_user_id', 'task_id'),
        'accountability_followup_optouts'    => array('discord_user_id'),
        'accountability_followup_log'        => array('discord_user_id', 'sent_date'),
        'accountability_reminder_log'        => array('setting_id', 'channel', 'sent_at'),
        'stock_subscriptions'                => array('discord_id', 'symbol'),
        'user_queues'                        => array('user_id', 'movie_id'),
        'shared_playlists'                   => array('id'),
        'playlist_items'                     => array('id'),
    );
}

// ── Safeguard thresholds ─────────────────────────────────────────────────────
// Per-table minimum row counts. If source has fewer rows than this and dest
// has more, skip sync for that table and alert.
function sync_get_safeguard_thresholds() {
    return array(
        'users'                    => 2,   // at least admin + test user
        'user_lists'               => 1,
        'creators'                 => 5,
        'notification_preferences' => 0,
        'user_visit_days'          => 0,
        '_default'                 => 0,
    );
}

// ── Delta alert threshold ────────────────────────────────────────────────────
// Alert if any table loses more than this fraction of rows in a single sync.
function sync_get_delta_alert_threshold() {
    return 0.10; // 10%
}

// ── Changelog pagination ─────────────────────────────────────────────────────
function sync_get_batch_size() {
    return 1000;
}

// ── Changelog retention (days) ───────────────────────────────────────────────
function sync_get_retention_days() {
    return 30;
}

// ── Per-DB credential overrides ──────────────────────────────────────────────
// On hosts where each database has its own MySQL user (e.g. 50webs), the
// deployment script replaces the array below with per-DB credentials.
// On hosts where one user accesses all DBs (e.g. GoDaddy), this stays empty
// and the default DB_USER_PLACEHOLDER / DB_PASS_PLACEHOLDER are used.
$_sync_db_cred_map = array(); // SYNC_DB_CRED_MAP

function sync_get_db_creds($dbname) {
    global $_sync_db_cred_map;
    if (isset($_sync_db_cred_map[$dbname])) {
        return $_sync_db_cred_map[$dbname];
    }
    return null;
}
