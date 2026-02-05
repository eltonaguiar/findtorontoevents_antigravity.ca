CREATE TABLE IF NOT EXISTS creator_mentions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    creator_id INT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content_url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    thumbnail_url TEXT,
    author VARCHAR(255),
    engagement_count INT DEFAULT 0,
    posted_at INT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_creator_platform (creator_id, platform),
    INDEX idx_posted_at (posted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
