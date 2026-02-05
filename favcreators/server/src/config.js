import "dotenv/config";

const required = (value, name) => {
  if (!value) throw new Error(`Missing required env var: ${name}`);
  return value;
};

export const config = {
  env: process.env.NODE_ENV || "development",
  port: Number(process.env.PORT || 4000),
  clientOrigin: process.env.CLIENT_ORIGIN || "http://localhost:5173",
  sessionSecret: required(process.env.SESSION_SECRET, "SESSION_SECRET"),
  mysql: {
    host: required(process.env.MYSQL_HOST, "MYSQL_HOST"),
    port: Number(process.env.MYSQL_PORT || 3306),
    user: required(process.env.MYSQL_USER, "MYSQL_USER"),
    password: required(process.env.MYSQL_PASSWORD, "MYSQL_PASSWORD"),
    database: required(process.env.MYSQL_DATABASE, "MYSQL_DATABASE"),
    ssl: (process.env.MYSQL_SSL || "false").toLowerCase() === "true",
  },
  google: {
    clientId: required(process.env.GOOGLE_CLIENT_ID, "GOOGLE_CLIENT_ID"),
    clientSecret: required(process.env.GOOGLE_CLIENT_SECRET, "GOOGLE_CLIENT_SECRET"),
    callbackUrl: required(process.env.GOOGLE_CALLBACK_URL, "GOOGLE_CALLBACK_URL"),
  },
  admin: {
    username: process.env.ADMIN_USERNAME || "admin",
    password: process.env.ADMIN_PASSWORD || "admin",
  },
};
