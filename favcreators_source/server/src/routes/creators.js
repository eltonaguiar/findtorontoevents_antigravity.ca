import { Router } from "express";
import { pool } from "../db.js";

const router = Router();

function isStoredCreatorObject(value) {
  return (
    value &&
    typeof value === "object" &&
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    Array.isArray(value.accounts)
  );
}

// Middleware: Only allow admin
function requireAdmin(req, res, next) {
  if (req.user && (req.user.id === 0 || req.user.email === "admin" || req.user.provider === "admin")) {
    return next();
  }
  return res.status(403).json({ error: "Admin only" });
}

function requireUser(req, res, next) {
  if (!req.user) return res.status(401).json({ error: "Unauthorized" });
  if (req.user.id === 0) return res.status(403).json({ error: "Not available for admin" });
  return next();
}

// Public: default creators (admin-curated list)
router.get("/public", async (req, res) => {
  const [rows] = await pool.execute("SELECT * FROM creators");
  res.json({ creators: rows });
});

router.get("/mine", requireUser, async (req, res) => {
  const [rows] = await pool.execute(
    "SELECT creators FROM user_creator_lists WHERE user_id = ? LIMIT 1",
    [req.user.id],
  );
  const stored = rows.length ? rows[0].creators : [];
  if (!Array.isArray(stored) || stored.length === 0) {
    return res.json({ creators: [] });
  }

  if (stored.length && isStoredCreatorObject(stored[0])) {
    return res.json({ creators: stored });
  }

  const creatorIds = stored
    .filter((id) => typeof id === "string" && id.length > 0);
  if (creatorIds.length === 0) return res.json({ creators: [] });

  const placeholders = creatorIds.map(() => "?").join(",");
  const [creators] = await pool.execute(
    `SELECT * FROM creators WHERE id IN (${placeholders})`,
    creatorIds,
  );
  return res.json({ creators });
});

router.put("/mine", requireUser, async (req, res) => {
  const creators = Array.isArray(req.body?.creators) ? req.body.creators : [];

  const sanitized = creators
    .filter((c) => isStoredCreatorObject(c))
    .map((c) => ({
      id: c.id,
      name: c.name,
      bio: typeof c.bio === "string" ? c.bio : "",
      avatarUrl: typeof c.avatarUrl === "string" ? c.avatarUrl : "",
      isFavorite: Boolean(c.isFavorite),
      isPinned: Boolean(c.isPinned),
      category: typeof c.category === "string" ? c.category : "",
      reason: typeof c.reason === "string" ? c.reason : "",
      note: typeof c.note === "string" ? c.note : "",
      tags: Array.isArray(c.tags) ? c.tags : [],
      accounts: Array.isArray(c.accounts) ? c.accounts : [],
      addedAt: typeof c.addedAt === "number" ? c.addedAt : Date.now(),
      lastChecked: typeof c.lastChecked === "number" ? c.lastChecked : Date.now(),
    }));

  await pool.execute(
    "REPLACE INTO user_creator_lists (user_id, creators) VALUES (?, ?)",
    [req.user.id, JSON.stringify(sanitized)],
  );
  return res.json({ ok: true, count: sanitized.length });
});

// Get all creators
router.get("/", requireAdmin, async (req, res) => {
  const [rows] = await pool.execute("SELECT * FROM creators");
  res.json({ creators: rows });
});

// Add or update a creator
router.post("/", requireAdmin, async (req, res) => {
  const { id, name, bio, avatarUrl, isFavorite, isPinned, category, reason, note, tags, accounts } = req.body;
  // Upsert logic
  await pool.execute(
    `REPLACE INTO creators (id, name, bio, avatar_url, is_favorite, is_pinned, category, reason, note, tags, accounts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [id, name, bio, avatarUrl, isFavorite, isPinned, category, reason, note || null, JSON.stringify(tags), JSON.stringify(accounts)]
  );
  res.json({ ok: true });
});

// Replace all creators (admin-curated list)
router.post("/bulk", requireAdmin, async (req, res) => {
  const creators = Array.isArray(req.body?.creators) ? req.body.creators : [];
  await pool.execute("DELETE FROM creators");
  for (const c of creators) {
    const {
      id,
      name,
      bio,
      avatarUrl,
      isFavorite,
      isPinned,
      category,
      reason,
      note,
      tags,
      accounts,
      addedAt,
      lastChecked,
    } = c || {};
    if (!id || !name) continue;
    await pool.execute(
      `REPLACE INTO creators (id, name, bio, avatar_url, is_favorite, is_pinned, category, reason, note, tags, accounts, added_at, last_checked) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        name,
        bio || null,
        avatarUrl || null,
        Boolean(isFavorite),
        Boolean(isPinned),
        category || null,
        reason || null,
        note || null,
        JSON.stringify(tags || []),
        JSON.stringify(accounts || []),
        addedAt || null,
        lastChecked || null,
      ],
    );
  }
  res.json({ ok: true, count: creators.length });
});

// Delete a creator
router.delete("/:id", requireAdmin, async (req, res) => {
  await pool.execute("DELETE FROM creators WHERE id = ?", [req.params.id]);
  res.json({ ok: true });
});

export default router;
