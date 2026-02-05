import mysql from "mysql2/promise";
import { config } from "./config.js";
import bcrypt from "bcryptjs";

export const pool = mysql.createPool({
  host: config.mysql.host,
  port: config.mysql.port,
  user: config.mysql.user,
  password: config.mysql.password,
  database: config.mysql.database,
  ssl: config.mysql.ssl ? { rejectUnauthorized: true } : undefined,
  connectionLimit: 10,
  waitForConnections: true,
  namedPlaceholders: true,
});

export const initSchema = async () => {

  await pool.execute(`
    CREATE TABLE IF NOT EXISTS users (
      id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
      email VARCHAR(320) NOT NULL,
      password_hash VARCHAR(255) NULL,
      google_id VARCHAR(255) NULL,
      display_name VARCHAR(120) NULL,
      avatar_url VARCHAR(512) NULL,
      provider ENUM('password','google') NOT NULL DEFAULT 'password',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      UNIQUE KEY uniq_users_email (email),
      UNIQUE KEY uniq_users_google_id (google_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
  `);

  await pool.execute(`
    CREATE TABLE IF NOT EXISTS creators (
      id VARCHAR(64) NOT NULL,
      name VARCHAR(120) NOT NULL,
      bio TEXT,
      avatar_url VARCHAR(512),
      is_favorite BOOLEAN DEFAULT FALSE,
      is_pinned BOOLEAN DEFAULT FALSE,
      category VARCHAR(64),
      reason VARCHAR(255),
      note TEXT,
      tags JSON,
      accounts JSON,
      added_at BIGINT,
      last_checked BIGINT,
      PRIMARY KEY (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
  `);

  try {
    await pool.execute(
      "ALTER TABLE creators ADD COLUMN note TEXT NULL",
    );
  } catch {
    // Ignore if column already exists
  }

  await pool.execute(`
    CREATE TABLE IF NOT EXISTS sessions (
      session_id VARCHAR(128) NOT NULL,
      expires INT UNSIGNED NOT NULL,
      data MEDIUMTEXT,
      PRIMARY KEY (session_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
  `);

  await pool.execute(`
    CREATE TABLE IF NOT EXISTS user_creator_lists (
      user_id BIGINT UNSIGNED NOT NULL,
      creators JSON NOT NULL,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (user_id),
      CONSTRAINT fk_user_creator_lists_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
  `);

  const [existingTest] = await pool.execute(
    "SELECT id FROM users WHERE email = ? LIMIT 1",
    ["test"],
  );
  let testUserId = existingTest?.[0]?.id;
  if (!existingTest.length) {
    const passwordHash = await bcrypt.hash("test", 12);
    const [result] = await pool.execute(
      "INSERT INTO users (email, password_hash, display_name, provider) VALUES (?, ?, ?, 'password')",
      ["test", passwordHash, "test"],
    );
    testUserId = result.insertId;
  }

  if (testUserId) {
    const [existingList] = await pool.execute(
      "SELECT user_id FROM user_creator_lists WHERE user_id = ? LIMIT 1",
      [testUserId],
    );
    if (!existingList.length) {
      await pool.execute(
        "INSERT INTO user_creator_lists (user_id, creators) VALUES (?, ?)",
        [testUserId, JSON.stringify(["pokimane", "adinross"])],
      );
    }
  }

  const [existingCreators] = await pool.execute(
    "SELECT id FROM creators WHERE id IN ('pokimane', 'adinross')",
  );
  const existingIds = new Set(existingCreators.map((r) => r.id));
  if (!existingIds.has("pokimane")) {
    await pool.execute(
      "REPLACE INTO creators (id, name, category, tags, accounts, added_at, last_checked) VALUES (?, ?, ?, ?, ?, ?, ?)",
      [
        "pokimane",
        "Pokimane",
        "Favorites",
        JSON.stringify(["DEFAULT"]),
        JSON.stringify([
          {
            id: "pokimane-twitch",
            platform: "twitch",
            username: "pokimane",
            url: "https://www.twitch.tv/pokimane",
          },
          {
            id: "pokimane-youtube",
            platform: "youtube",
            username: "pokimane",
            url: "https://www.youtube.com/@pokimane",
          },
        ]),
        Date.now(),
        Date.now(),
      ],
    );
  }
  if (!existingIds.has("adinross")) {
    await pool.execute(
      "REPLACE INTO creators (id, name, category, tags, accounts, added_at, last_checked) VALUES (?, ?, ?, ?, ?, ?, ?)",
      [
        "adinross",
        "Adin Ross",
        "Favorites",
        JSON.stringify(["DEFAULT"]),
        JSON.stringify([
          {
            id: "adinross-kick",
            platform: "kick",
            username: "adinross",
            url: "https://kick.com/adinross",
          },
          {
            id: "adinross-youtube",
            platform: "youtube",
            username: "adinross",
            url: "https://youtube.com/@adinross",
          },
        ]),
        Date.now(),
        Date.now(),
      ],
    );
  }
};
