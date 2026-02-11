<?php
/**
 * News Feed Aggregator — Database Schema
 * Separate DB: ejaguiar1_news on mysql.50webs.com
 * PHP 5.2 compatible
 */

function _nf_db_connect() {
    $host = 'mysql.50webs.com';
    $user = 'ejaguiar1_news';
    $pass = 'newsnews';
    $db   = 'ejaguiar1_news';

    $conn = @new mysqli($host, $user, $pass, $db);
    if ($conn->connect_error) {
        return null;
    }
    $conn->set_charset('utf8');
    return $conn;
}

function _nf_ensure_tables($conn) {
    if (!$conn) return false;

    $sqls = array(
        "CREATE TABLE IF NOT EXISTS news_articles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(512) NOT NULL,
            link VARCHAR(1024) NOT NULL,
            source_name VARCHAR(128) NOT NULL,
            source_key VARCHAR(64) NOT NULL,
            source_logo VARCHAR(512) DEFAULT '',
            category VARCHAR(16) NOT NULL,
            pub_date DATETIME NOT NULL,
            description TEXT,
            image_url VARCHAR(1024) DEFAULT '',
            tags VARCHAR(512) DEFAULT '',
            fetched_at DATETIME NOT NULL,
            UNIQUE KEY uq_link (link(255)),
            INDEX idx_category (category),
            INDEX idx_source_key (source_key),
            INDEX idx_pub_date (pub_date)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

        "CREATE TABLE IF NOT EXISTS news_sources (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            source_key VARCHAR(64) NOT NULL,
            feed_url VARCHAR(512) NOT NULL,
            category VARCHAR(16) NOT NULL,
            logo_url VARCHAR(512) DEFAULT '',
            is_active TINYINT NOT NULL DEFAULT 1,
            last_fetched DATETIME DEFAULT NULL,
            article_count INT DEFAULT 0,
            last_error VARCHAR(512) DEFAULT '',
            UNIQUE KEY uq_source_key (source_key),
            INDEX idx_category (category)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8"
    );

    foreach ($sqls as $sql) {
        $conn->query($sql);
    }

    // Migration: add tags column if missing
    $chk = $conn->query("SHOW COLUMNS FROM news_articles LIKE 'tags'");
    if ($chk && $chk->num_rows === 0) {
        $conn->query("ALTER TABLE news_articles ADD COLUMN tags VARCHAR(512) DEFAULT '' AFTER image_url");
    }

    return true;
}
