# Render deployment

CredEasy's standalone web app is the static site in the repository-root `app/`
directory. The Render static site (`credeasy-app.onrender.com`) should use:

- **Root directory:** repository root
- **Build command:** `echo "Static SPA — no build step needed"`
- **Publish directory:** `app`

The publish directory must contain `index.html`, `env.js`, `app.js`, and
`styles.css`. Do not set it to `website`; that directory contains the separate
marketing site. Keep `env.js` limited to public client configuration such as the
Supabase anon key. Never put `SUPABASE_SERVICE_ROLE_KEY` or other backend
secrets in static files.

The API is deployed separately at `https://credeasy-01.onrender.com`.
