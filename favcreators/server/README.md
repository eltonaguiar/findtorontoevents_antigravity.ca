# FavCreators Auth Server

Standalone auth backend for Google OAuth and email/password fallback.

## Setup

1. Copy `.env.example` to `.env` and fill in secrets.
2. Install dependencies:

```bash
cd server
npm install
```

3. Run locally:

```bash
npm run dev
```

## Frontend env

For local dev, set `VITE_AUTH_BASE_URL=http://localhost:4000` in the frontend `.env` (see [`.env`](.env:1)).

## Endpoints

- `GET /health`
- `GET /auth/google`
- `GET /auth/google/callback`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

## Render notes

Set `NODE_ENV=production` and ensure `CLIENT_ORIGIN` matches the GitHub Pages domain.

## Security notes

- Cookies are `Secure` and `SameSite=None` for cross-site GitHub Pages.
- Rate limiting applied to auth endpoints.
