# Publish CredEasy on GoDaddy

There are two different upload packages. The provided screenshot shows **Managed WordPress**, so use the WordPress theme below, not the static-site ZIP or the cPanel instructions.

- **Managed WordPress:** install `credeasy-wordpress-theme.zip` from the WordPress dashboard.
- **Linux Web Hosting with cPanel:** upload `credeasy-live-godaddy.zip` to the domain's document root using the cPanel steps below.

Do not upload the static-site ZIP through WordPress's theme uploader. It is a set of website files, not a WordPress theme.

## Managed WordPress

1. In GoDaddy **My Products**, open **Managed WordPress → Manage**, then open the site's **WP Admin**.
2. Back up the WordPress site before switching its theme. Save the current theme name so you can switch back if needed.
3. In WordPress, open **Appearance → Themes → Add New Theme → Upload Theme**.
4. Choose `credeasy-wordpress-theme.zip`, select **Install Now**, then **Activate**.
5. Open **Pages → Add New** and publish these two pages using the exact slugs:
   - **Privacy Policy**, slug `privacy-policy`
   - **Terms & Conditions**, slug `terms-and-conditions`
   The theme provides the legal-page content automatically; the WordPress page content can be left empty.
6. Open the site homepage, `/privacy-policy/`, and `/terms-and-conditions/` in a private browser window and confirm the images and navigation load.
If `/admin` shows the theme's 404 page on an existing installation, open
**Settings → Permalinks** in WordPress Admin and select **Save Changes** once.
This refreshes rewrite rules for installations running an older theme package.

The theme displays the CredEasy homepage automatically and does not require a page builder. The package also serves the internal operations console at `/admin`; complete its separate backend setup below before making admin access available. To undo the change, use **Appearance → Themes** and reactivate the previous theme. The WordPress package does not change GoDaddy DNS, SSL or account settings.

### Enable the packaged `/admin` console

The theme includes the admin page and proxies a strict list of admin API routes
to the existing FastAPI backend. WordPress stores no Supabase service-role
secret, and the proxy accepts only verified Supabase bearer sessions on the
allowlisted endpoints.

1. In WordPress Admin, open **Settings → General** and scroll down to the
   **CredEasy Admin** section near the bottom. (A shortcut is also available at
   **Settings → CredEasy Admin**.)
2. Enter the public HTTPS origin of the deployed CredEasy FastAPI backend in
   **Admin backend URL** and select **Save Changes** at the bottom of the
   General page. Enter only the origin—no `/api`, `/admin`, credentials, or
   path. The current API service origin is `https://credeasy-app.onrender.com`;
   do not use `https://credeasy-01.onrender.com`, which hosts the static site.
   This WordPress setting replaces editing `wp-config.php`; no SFTP access is
   needed.
3. Before saving it here, open
   `https://credeasy-app.onrender.com/api/admin/config` directly.
   It must return JSON (a structured 503 JSON error is expected if backend
   Supabase variables are not configured); a plain 404 means the admin routes
   have not been deployed to the API service yet. The current
   `credeasy-app.onrender.com` deployment responds 404 for this route, so deploy
   the repository's backend changes before expecting sign-in to work.
4. On that backend host, configure `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY`, and the comma-separated, verified-owner
   `ADMIN_BOOTSTRAP_EMAILS` allowlist. Keep the service-role key in the
   backend secret store only.
5. Apply [`enable-admin-panel.sql`](./enable-admin-panel.sql) in Supabase.
6. In Supabase Auth, add `https://credeasy.live/admin` to Google OAuth's
   allowed redirect URLs. If the site uses `www.credeasy.live` as its canonical
   host, allow that exact `/admin` URL instead.
7. Deploy/restart the backend and activate the theme. Open
   `https://credeasy.live/admin`, sign in with an allowlisted account, and
   verify that the connected modules load.

Uploading the theme ZIP alone does not provision the backend or Supabase
schema. An unset backend URL shows an explicit setup error; no admin secret or
privileged data is served from the theme files.

## Linux Web Hosting with cPanel

Use these steps only if the GoDaddy account also has a separate **Web Hosting with cPanel** product.

## 2. Connect the domain to the hosting account

1. Open **My Products → Web Hosting → Manage** and note the hosting server's IP address or the domain connection instructions shown for your plan.
2. Open **Domains → credeasy.live → DNS**.
3. If you are moving the domain's existing website to cPanel, point the root (`@`) A record to the cPanel hosting IP. Set `www` to a CNAME targeting `@` (or use the exact records GoDaddy recommends for your hosting plan).
4. Replace only conflicting website records after confirming the cPanel IP. Do not change nameservers or remove MX, TXT, or other records used by email or services unless you intend to move them too.
5. Wait until the domain resolves to this hosting account. DNS changes can take time to appear everywhere.

## 3. Activate HTTPS before publishing the redirect

1. In **Web Hosting → Manage**, open **cPanel Admin** and locate the SSL/TLS or SSL certificate controls. GoDaddy's exact labels and included certificate options depend on the hosting plan.
2. Issue or activate a certificate covering both `credeasy.live` and `www.credeasy.live`, then allow GoDaddy/cPanel to install it for the hosting account.
3. Confirm `https://credeasy.live` opens without a certificate warning before enabling the site's `.htaccess` redirect.

The bundle forces HTTPS. If the certificate is not active yet, do not install `.htaccess` until it is. If you already uploaded the bundle, rename `.htaccess` in File Manager until HTTPS works, then restore its name.

## 4. Upload the site files

1. Open **cPanel Admin → File Manager**.
2. Open the document root assigned to `credeasy.live`. For the primary domain it is commonly `public_html`; addon domains may have a separate folder shown in cPanel.
3. If that folder already contains a website, download a backup before replacing anything. Do not delete mail folders or unrelated hosting files.
4. Upload `credeasy-live-godaddy.zip` to the domain's document root and use **Extract** there.
5. Check the folder layout. `index.html`, `site.css`, `.htaccess`, `404.html`, `robots.txt`, `sitemap.xml`, `privacy-policy.html`, `terms-and-conditions.html`, `legal.css`, and `assets/` must be directly in the document root. They must not be nested inside a second `website/` folder.
6. If SSL was not ready earlier, keep `.htaccess` renamed. Restore `.htaccess` only after confirming the SSL certificate is active.

## 5. Test the live site

Open these addresses in a private/incognito browser window:

- `https://credeasy.live/`
- `https://www.credeasy.live/` (should redirect to the root domain)
- `http://credeasy.live/` (should redirect to HTTPS)
- `https://credeasy.live/privacy-policy.html`
- `https://credeasy.live/terms-and-conditions.html`
- `https://credeasy.live/this-page-does-not-exist` (should show the custom 404 page)
- `https://credeasy.live/robots.txt`
- `https://credeasy.live/sitemap.xml`

For Managed WordPress, the legal pages use `/privacy-policy/` and `/terms-and-conditions/`; use the WordPress sitemap generated by the site or its SEO plugin.

Check the homepage navigation, feature tabs, mobile menu, theme switch, and FAQ disclosures. If you see a GoDaddy placeholder page, confirm the domain's document root and that `index.html` is at its top level. If you see a redirect loop or certificate warning, rename `.htaccess` in File Manager and have GoDaddy verify the domain-to-hosting and SSL configuration before restoring it.

## 6. Submit the sitemap

After the site is publicly accessible, add `https://credeasy.live/sitemap.xml` in Google Search Console and verify ownership using one of Google's available methods. The public privacy policy URL is `https://credeasy.live/privacy-policy.html`.

## Upload bundle contents

The ZIP is assembled from the website's public files only, including the CredEasy mark and the privacy-redacted `app-ledger.webp`, `app-inventory.webp`, and `app-billing.webp` screenshots in `assets/`. It does not include repository code, local environment files, credentials, or internal documentation.
