import express from "express";
import cors from "cors";
import helmet from "helmet";
import session from "express-session";
import MySQLStoreFactory from "express-mysql-session";
import passport from "passport";
import cookieParser from "cookie-parser";
import { config } from "./config.js";
import { initSchema, pool } from "./db.js";
import authRoutes from "./routes/auth.js";
import creatorsRoutes from "./routes/creators.js";

const app = express();

await initSchema();

const MySQLStore = MySQLStoreFactory(session);
const sessionStore = new MySQLStore(
  {
    schema: {
      tableName: "sessions",
      columnNames: {
        session_id: "session_id",
        expires: "expires",
        data: "data",
      },
    },
  },
  pool,
);

app.set("trust proxy", 1);
app.use(helmet());
app.use(
  cors({
    origin: config.clientOrigin,
    credentials: true,
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  }),
);
app.use(express.json({ limit: "100kb" }));
app.use(cookieParser());

app.use(
  session({
    name: "favcreators.sid",
    secret: config.sessionSecret,
    resave: false,
    saveUninitialized: false,
    store: sessionStore,
    cookie: {
      httpOnly: true,
      secure: config.env === "production",
      sameSite: config.env === "production" ? "none" : "lax",
      maxAge: 1000 * 60 * 60 * 24 * 7,
    },
  }),
);

app.use(passport.initialize());
app.use(passport.session());

app.get("/health", (req, res) => {
  res.json({ ok: true });
});

app.use("/auth", authRoutes);
app.use("/creators", creatorsRoutes);

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: "Server error" });
});

app.listen(config.port, () => {
  console.log(`Auth server listening on :${config.port}`);
});
