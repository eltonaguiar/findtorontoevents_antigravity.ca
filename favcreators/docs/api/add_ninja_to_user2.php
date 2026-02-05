<?php
/**
 * Add Ninja to user_id 2's creator list
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once __DIR__ . '/../db_config.php';

try {
    $pdo = getDBConnection();
    
    // Check if user 2 exists
    $checkUser = $pdo->prepare("SELECT id FROM users WHERE id = 2");
    $checkUser->execute();
    
    if ($checkUser->rowCount() === 0) {
        // Create user 2 if not exists
        $createUser = $pdo->prepare("
            INSERT INTO users (id, email, display_name, provider, created_at) 
            VALUES (2, 'zerounderscore@gmail.com', 'EA', 'google', NOW())
        ");
        $createUser->execute();
        echo json_encode(array('message' => 'Created user 2'));
    }
    
    // Check if user_creators table exists, if not create it
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS user_creators (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            creator_id VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            bio TEXT,
            avatar_url TEXT,
            is_favorite TINYINT(1) DEFAULT 0,
            is_pinned TINYINT(1) DEFAULT 0,
            category VARCHAR(100) DEFAULT 'Other',
            reason TEXT,
            note TEXT,
            tags TEXT,
            accounts TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_user_creator (user_id, creator_id),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");
    
    // Add Ninja to user 2's list
    $ninja = array(
        'id' => 'ninja-twitch',
        'name' => 'Ninja',
        'bio' => 'Professional streamer and content creator',
        'avatarUrl' => '',
        'isFavorite' => true,
        'isPinned' => false,
        'category' => 'Gaming',
        'accounts' => array(
            array(
                'id' => 'ninja-twitch-1',
                'platform' => 'twitch',
                'username' => 'ninja',
                'url' => 'https://twitch.tv/ninja',
                'followers' => '19M',
                'lastChecked' => time() * 1000
            )
        ),
        'addedAt' => time() * 1000,
        'lastChecked' => time() * 1000
    );
    
    $stmt = $pdo->prepare("
        INSERT INTO user_creators 
        (user_id, creator_id, name, bio, avatar_url, is_favorite, is_pinned, category, accounts, created_at, updated_at)
        VALUES 
        (:user_id, :creator_id, :name, :bio, :avatar_url, :is_favorite, :is_pinned, :category, :accounts, NOW(), NOW())
        ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        bio = VALUES(bio),
        avatar_url = VALUES(avatar_url),
        is_favorite = VALUES(is_favorite),
        is_pinned = VALUES(is_pinned),
        category = VALUES(category),
        accounts = VALUES(accounts),
        updated_at = NOW()
    ");
    
    $stmt->execute(array(
        ':user_id' => 2,
        ':creator_id' => $ninja['id'],
        ':name' => $ninja['name'],
        ':bio' => $ninja['bio'],
        ':avatar_url' => $ninja['avatarUrl'],
        ':is_favorite' => $ninja['isFavorite'] ? 1 : 0,
        ':is_pinned' => $ninja['isPinned'] ? 1 : 0,
        ':category' => $ninja['category'],
        ':accounts' => json_encode($ninja['accounts'])
    ));
    
    echo json_encode(array(
        'success' => true,
        'message' => 'Ninja added to user 2\'s list',
        'creator' => $ninja
    ));
    
} catch (PDOException $e) {
    error_log("Database error: " . $e->getMessage());
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'success' => false,
        'error' => 'Database error: ' . $e->getMessage()
    ));
} catch (Exception $e) {
    error_log("Error: " . $e->getMessage());
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'success' => false,
        'error' => 'Error: ' . $e->getMessage()
    ));
}