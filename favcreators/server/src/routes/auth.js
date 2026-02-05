import express from "express";
import bcrypt from "bcryptjs";
import passport from "passport";
import { Strategy as GoogleStrategy } from "passport-google-oauth20";
import rateLimit from "express-rate-limit";
import { pool } from "../db.js";
import { config } from "../config.js";
import { loginSchema, registerSchema } from "../validators.js";

const router = express.Router();

// Allow guests to access the main interface
router.get("/guest", (req, res) => {
  res.redirect(`${config.clientOrigin}/FAVCREATORS/FAVCREATORS_TRACKER/#/guest`);
});

const authLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
});

passport.serializeUser((user, done) => {
  done(null, user.id);
});

passport.deserializeUser(async (id, done) => {
  try {
    if (id === 0) {
      return done(null, { id: 0, email: "admin", provider: "admin" });
    }
    const [rows] = await pool.execute(
      "SELECT id, email, display_name, avatar_url, provider FROM users WHERE id = ?",
      [id],
    );
    done(null, rows[0] || null);
  } catch (error) {
    done(error);
  }
});

passport.use(
  new GoogleStrategy(
    {
      clientID: config.google.clientId,
      clientSecret: config.google.clientSecret,
      callbackURL: config.google.callbackUrl,
    },
    async (_accessToken, _refreshToken, profile, done) => {
      try {
        const email = profile.emails?.[0]?.value?.toLowerCase();
        if (!email) return done(new Error("Google account missing email"));

        const googleId = profile.id;
        const displayName = profile.displayName || email.split("@")[0];
        const avatarUrl = profile.photos?.[0]?.value || null;

        const [existing] = await pool.execute(
          "SELECT id FROM users WHERE google_id = ? OR email = ? LIMIT 1",
          [googleId, email],
        );

        if (existing.length > 0) {
          const userId = existing[0].id;
          await pool.execute(
            "UPDATE users SET google_id = ?, display_name = ?, avatar_url = ?, provider = 'google' WHERE id = ?",
            [googleId, displayName, avatarUrl, userId],
          );
          return done(null, { id: userId });
        }

        const [result] = await pool.execute(
          "INSERT INTO users (email, google_id, display_name, avatar_url, provider) VALUES (?, ?, ?, ?, 'google')",
          [email, googleId, displayName, avatarUrl],
        );

        return done(null, { id: result.insertId });
      } catch (error) {
        done(error);
      }
    },
  ),
);

router.get("/google", authLimiter, passport.authenticate("google", {
  scope: ["profile", "email"],
  prompt: "select_account",
}));

router.get(
  "/google/callback",
  passport.authenticate("google", { failureRedirect: "/auth/google/fail" }),
  (req, res) => {
    res.redirect(
      `${config.clientOrigin}/FAVCREATORS/FAVCREATORS_TRACKER/#/guest?login=success`,
    );
  },
);

router.get("/google/fail", (req, res) => {
  res.redirect(
    `${config.clientOrigin}/FAVCREATORS/FAVCREATORS_TRACKER/#/guest?login=failed`,
  );
});

router.post("/register", authLimiter, async (req, res) => {
  const parsed = registerSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "Invalid registration details" });
  }

  const { email, password, displayName } = parsed.data;
  const normalizedEmail = email.toLowerCase();

  const [existing] = await pool.execute(
    "SELECT id FROM users WHERE email = ? LIMIT 1",
    [normalizedEmail],
  );
  if (existing.length > 0) {
    return res.status(409).json({ error: "Email already registered" });
  }

  const passwordHash = await bcrypt.hash(password, 12);
  const [result] = await pool.execute(
    "INSERT INTO users (email, password_hash, display_name, provider) VALUES (?, ?, ?, 'password')",
    [normalizedEmail, passwordHash, displayName],
  );

  req.login({ id: result.insertId }, (err) => {
    if (err) return res.status(500).json({ error: "Login failed" });
    return res.json({ ok: true });
  });
});

router.post("/login", authLimiter, async (req, res) => {
  if (
    req.body?.email === config.admin.username &&
    req.body?.password === config.admin.password
  ) {
    return req.login({ id: 0, email: "admin", provider: "admin" }, (err) => {
      if (err) return res.status(500).json({ error: "Login failed" });
      return res.json({
        ok: true,
        user: { id: 0, email: "admin", provider: "admin" },
      });
    });
  }

  const parsed = loginSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "Invalid login details" });
  }

  const { email, password } = parsed.data;
  const [rows] = await pool.execute(
    "SELECT id, password_hash FROM users WHERE email = ? LIMIT 1",
    [email.toLowerCase()],
  );

  if (!rows.length || !rows[0].password_hash) {
    return res.status(401).json({ error: "Invalid credentials" });
  }

  const ok = await bcrypt.compare(password, rows[0].password_hash);
  if (!ok) return res.status(401).json({ error: "Invalid credentials" });

  req.login({ id: rows[0].id }, (err) => {
    if (err) return res.status(500).json({ error: "Login failed" });
    return res.json({ ok: true });
  });
});

router.post("/logout", (req, res) => {
  req.logout(() => {
    req.session?.destroy(() => {
      res.clearCookie("favcreators.sid");
      res.json({ ok: true });
    });
  });
});

router.get("/me", (req, res) => {
  if (!req.user) return res.json({ user: null });
  if (req.user.id === 0) {
    return res.json({ user: { id: 0, email: "admin", provider: "admin" } });
  }
  return res.json({ user: req.user });
});

export default router;
