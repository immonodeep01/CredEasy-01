CredEasy static website upload package

Upload the contents of this ZIP to the document root for credeasy.live, usually public_html.
Keep index.html, site.css, .htaccess, robots.txt, sitemap.xml, 404.html, both
legal pages, legal.css, and the assets folder directly inside that document root. Do not leave
them inside an extra website or credeasy-live-site folder.

This static ZIP is for Linux Web Hosting with cPanel, not Managed WordPress.
For Managed WordPress, install credeasy-wordpress-theme.zip using Appearance >
Themes > Add New Theme > Upload Theme. Then create the Privacy Policy page with
slug privacy-policy and Terms & Conditions page with slug terms-and-conditions.
See the Managed WordPress section in docs/WEBSITE-GODADDY-DEPLOYMENT.md.

The assets folder includes the CredEasy mark and privacy-redacted app-ledger.webp,
app-inventory.webp, and app-billing.webp screenshots used on the homepage.

The .htaccess file redirects www and HTTP traffic to https://credeasy.live/.
Activate the domain's SSL certificate before enabling this redirect.

See docs/WEBSITE-GODADDY-DEPLOYMENT.md in the project for the full GoDaddy steps.
