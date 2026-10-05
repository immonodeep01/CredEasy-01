/**
 * Runtime config for the CredEasy web app.
 *
 * Loaded BEFORE app.js. All values are non-secret — the Supabase ANON key is
 * designed to be public, and access is enforced by RLS. Never put the
 * service_role key here.
 */
window._env = {
  SUPABASE_URL:      'https://idhdyusswxlbuhpjkrwm.supabase.co',
  SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlkaGR5dXNzd3hsYnVocGprcndtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc2NzEzNDUsImV4cCI6MjEwMzI0NzM0NX0.tpE9-6JYeI8ocIktyy6t15-uQvsO0jPUxBK3SfilYOk',
  BACKEND_URL:       'https://credeasy-01.onrender.com',
  WEB_URL:           'https://credeasy-app.onrender.com',
};
