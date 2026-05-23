-- =============================================================================
-- user_settings table schema
-- findtorontoevents.ca — Gear Settings persistence layer
-- =============================================================================

-- Ensure the database uses utf8mb4 for proper JSON and emoji support
ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- Table: user_settings
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS user_settings;

CREATE TABLE user_settings (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    settings_json   JSON NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Prevent duplicate rows per user
    UNIQUE KEY uk_user_settings_user_id (user_id),

    -- Fast lookup by user
    INDEX idx_user_settings_user_id (user_id),

    -- Soft reference integrity (user_id should match a row in your users table)
    -- If your users table uses a different column type, adjust accordingly.
    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Stores per-user gear/filter settings as JSON. Synced with localStorage.';

-- ------------------------------------------------------------------------------
-- Optional: trigger to keep created_at immutable on updates
-- ------------------------------------------------------------------------------
DELIMITER //
CREATE TRIGGER trg_user_settings_prevent_created_at_update
BEFORE UPDATE ON user_settings
FOR EACH ROW
BEGIN
    IF OLD.created_at != NEW.created_at THEN
        SET NEW.created_at = OLD.created_at;
    END IF;
END//
DELIMITER ;

-- ------------------------------------------------------------------------------
-- Example queries for manual verification
-- ------------------------------------------------------------------------------

-- Get settings for a specific user
-- SELECT settings_json, updated_at FROM user_settings WHERE user_id = 42;

-- List all users with saved settings
-- SELECT u.email, us.settings_json, us.updated_at
-- FROM users u
-- JOIN user_settings us ON u.id = us.user_id;

-- Find stale settings (not updated in 30 days)
-- SELECT user_id, updated_at FROM user_settings WHERE updated_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
