/**
 * Runtime config for the CredEasy web app.
 *
 * Renamed to `env.js` on deploy and values filled in. Loaded BEFORE app.js.
 * All values are non-secret — the Supabase ANON key is designed to be public,
 * and access is enforced by RLS. Never put the service_role key here.
 */
window._env = {
  SUPABASE_URL:      'https://YOUR-PROJECT.supabase.co',
  SUPABASE_ANON_KEY: 'eyJ...replace-me',
  BACKEND_URL:       'https://credeasy-backend.onrender.com',
  WEB_URL:           'https://app.credeasy.app',
};
