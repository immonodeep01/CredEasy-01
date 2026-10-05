from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


WEBSITE = Path(__file__).resolve().parent
ROOT = WEBSITE.parent
THEME_NAME = "credeasy-wordpress-theme"
THEME_DIR = ROOT / THEME_NAME
ARCHIVE = ROOT / f"{THEME_NAME}.zip"
ADMIN_STATIC_DIR = ROOT / "backend" / "admin_static"


def extract(pattern: str, text: str, description: str) -> str:
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find {description}")
    return match.group(1).strip()


def theme_urls(markup: str) -> str:
    for asset in (
        "credeasy-mark.png",
        "app-ledger.webp",
        "app-inventory.webp",
        "app-billing.webp",
    ):
        markup = markup.replace(
            f'src="assets/{asset}"',
            f'src="<?php echo esc_url(get_theme_file_uri(\'/assets/{asset}\')); ?>"',
        )

    for filename, slug in (
        ("privacy-policy.html", "privacy-policy"),
        ("terms-and-conditions.html", "terms-and-conditions"),
    ):
        markup = markup.replace(
            f'href="{filename}"',
            f'href="<?php echo esc_url(credeasy_page_url(\'{slug}\')); ?>"',
        )
    markup = markup.replace(
        'href="index.html"',
        'href="<?php echo esc_url(home_url(\'/\')); ?>"',
    )
    return markup


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def make_theme() -> None:
    homepage = (WEBSITE / "index.html").read_text(encoding="utf-8")
    inline_css = extract(r"<style>(.*?)</style>", homepage, "homepage styles")
    home_body = extract(r"<body>(.*?)</body>", homepage, "homepage body")
    home_script = extract(r"<script>(.*?)</script>", homepage, "homepage script")
    home_markup = re.sub(
        r'<a class="skip-link" href="#main">.*?</a>',
        "",
        home_body,
        count=1,
        flags=re.DOTALL,
    )
    home_header = extract(
        r'(<header class="site-header">.*?</header>)',
        home_markup,
        "homepage navigation",
    )
    home_main = extract(r"(<main id=\"main\">.*?</main>)", home_markup, "homepage content")

    css = "\n\n".join(
        (
            inline_css,
            (WEBSITE / "site.css").read_text(encoding="utf-8"),
            (WEBSITE / "legal.css").read_text(encoding="utf-8"),
        )
    )
    write(
        THEME_DIR / "style.css",
        """/*
Theme Name: CredEasy Marketing
Description: The CredEasy marketing site and legal pages.
Version: 1.3.2
Requires at least: 6.0
Requires PHP: 7.4
Text Domain: credeasy-marketing
*/
"""
        + css,
    )

    write(
        THEME_DIR / "functions.php",
        """<?php
add_action('after_setup_theme', function (): void {
    add_theme_support('title-tag');
    add_theme_support('html5', ['style', 'script']);
});

function credeasy_page_url(string $slug): string {
    $page = get_page_by_path($slug, OBJECT, 'page');
    return $page ? (string) get_permalink($page) : home_url('/' . $slug . '/');
}

add_action('wp_enqueue_scripts', function (): void {
    wp_enqueue_style(
        'credeasy-marketing',
        get_stylesheet_uri(),
        [],
        wp_get_theme()->get('Version')
    );

    if (is_front_page()) {
        wp_enqueue_script(
            'credeasy-marketing',
            get_theme_file_uri('/assets/site.js'),
            [],
            wp_get_theme()->get('Version'),
            true
        );
    }
});

add_action('wp_head', function (): void {
    $title = wp_get_document_title();
    $url = '';
    $description = '';

    if (is_front_page()) {
        $url = home_url('/');
        $description = 'CredEasy helps small businesses keep customer and supplier ledgers, transactions, inventory, billing and reports together.';
    } elseif (is_page('privacy-policy')) {
        $url = credeasy_page_url('privacy-policy');
        $description = 'Read how CredEasy handles business, account, device, backup and voice-assistant information.';
    } elseif (is_page('terms-and-conditions')) {
        $url = credeasy_page_url('terms-and-conditions');
        $description = 'Read the terms for using the CredEasy website and business ledger app.';
    }

    if (!get_site_icon_url()) {
        echo '<link rel="icon" type="image/png" href="' .
            esc_url(get_theme_file_uri('/assets/credeasy-mark.png')) . '">' . "\\n";
    }

    if ($url !== '') {
        $image = get_theme_file_uri('/assets/credeasy-mark.png');
        echo '<meta name="description" content="' . esc_attr($description) . '">' . "\\n";
        echo '<link rel="canonical" href="' . esc_url($url) . '">' . "\\n";
        echo '<meta property="og:title" content="' . esc_attr($title) . '">' . "\\n";
        echo '<meta property="og:description" content="' . esc_attr($description) . '">' . "\\n";
        echo '<meta property="og:type" content="website">' . "\\n";
        echo '<meta property="og:site_name" content="' . esc_attr(get_bloginfo('name')) . '">' . "\\n";
        echo '<meta property="og:url" content="' . esc_url($url) . '">' . "\\n";
        echo '<meta property="og:image" content="' . esc_url($image) . '">' . "\\n";
        echo '<meta name="twitter:card" content="summary">' . "\\n";
        echo '<meta name="twitter:title" content="' . esc_attr($title) . '">' . "\\n";
        echo '<meta name="twitter:description" content="' . esc_attr($description) . '">' . "\\n";
        echo '<meta name="twitter:image" content="' . esc_url($image) . '">' . "\\n";
    }
}, 1);

function credeasy_admin_uuid_pattern(): string {
    return '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}';
}

add_action('init', function (): void {
    add_rewrite_rule(
        '^admin/?$',
        'index.php?credeasy_admin=1',
        'top'
    );
    add_rewrite_rule(
        '^admin/assets/(app\\.js|styles\\.css|supabase\\.min\\.js|SUPABASE-LICENSE\\.txt)$',
        'index.php?credeasy_admin_asset=$matches[1]',
        'top'
    );
    add_rewrite_rule(
        '^api/admin/(.*)$',
        'index.php?credeasy_admin_api=$matches[1]',
        'top'
    );
});

add_filter('query_vars', function (array $vars): array {
    $vars[] = 'credeasy_admin';
    $vars[] = 'credeasy_admin_asset';
    $vars[] = 'credeasy_admin_api';
    return $vars;
});

add_action('parse_request', function ($wp): void {
    $request = trim((string) $wp->request, '/');
    if ($request === 'admin') {
        $wp->query_vars['credeasy_admin'] = '1';
        return;
    }

    if (
        preg_match(
            '#^admin/assets/(app\\.js|styles\\.css|supabase\\.min\\.js|SUPABASE-LICENSE\\.txt)$#D',
            $request,
            $matches
        ) === 1
    ) {
        $wp->query_vars['credeasy_admin_asset'] = $matches[1];
        return;
    }

    if (preg_match('#^api/admin/(.*)$#D', $request, $matches) === 1) {
        $wp->query_vars['credeasy_admin_api'] = $matches[1];
    }
}, 0);

add_action('after_switch_theme', function (): void {
    flush_rewrite_rules();
});

function credeasy_admin_sanitize_backend_url($value): string {
    $value = trim((string) $value);
    if ($value === '') {
        return '';
    }

    $url = esc_url_raw($value, ['https']);
    $parts = wp_parse_url($url);
    if (
        !$parts ||
        ($parts['scheme'] ?? '') !== 'https' ||
        empty($parts['host']) ||
        isset($parts['user']) ||
        isset($parts['pass']) ||
        (!empty($parts['path']) && $parts['path'] !== '/') ||
        isset($parts['query']) ||
        isset($parts['fragment'])
    ) {
        add_settings_error(
            'credeasy_admin_settings',
            'invalid_backend_url',
            'Enter the HTTPS origin of the deployed CredEasy FastAPI backend only.',
            'error'
        );
        return (string) get_option('credeasy_admin_backend_url', '');
    }

    return untrailingslashit($url);
}

add_action('admin_init', function (): void {
    $setting = [
        'type' => 'string',
        'sanitize_callback' => 'credeasy_admin_sanitize_backend_url',
        'default' => '',
    ];
    register_setting(
        'credeasy_admin_settings',
        'credeasy_admin_backend_url',
        $setting
    );
    register_setting('general', 'credeasy_admin_backend_url', $setting);

    $render_backend_url_field = function (): void {
        $value = (string) get_option('credeasy_admin_backend_url', '');
        echo '<input type="url" class="regular-text" ' .
            'id="credeasy_admin_backend_url" ' .
            'name="credeasy_admin_backend_url" value="' .
            esc_attr($value) . '" ' .
            'placeholder="https://your-backend-host" ' .
            'autocomplete="url">';
        echo '<p class="description">Enter only the HTTPS backend origin, ' .
            'for example <code>https://your-backend-host</code>. ' .
            'Do not add <code>/api</code> or <code>/admin</code>.</p>';
    };

    add_settings_section(
        'credeasy_admin_general',
        'CredEasy Admin',
        function (): void {
            echo '<p>Connect the CredEasy admin console to its backend.</p>';
        },
        'general'
    );
    add_settings_field(
        'credeasy_admin_backend_url',
        'Admin backend URL',
        $render_backend_url_field,
        'general',
        'credeasy_admin_general'
    );

    add_settings_section(
        'credeasy_admin_backend',
        'Admin backend connection',
        function (): void {
            echo '<p>Set the HTTPS origin of the FastAPI backend that serves ' .
                'CredEasy admin. Do not add <code>/api</code>, <code>/admin</code>, ' .
                'or credentials.</p>';
        },
        'credeasy-admin'
    );
    add_settings_field(
        'credeasy_admin_backend_url',
        'Backend URL',
        $render_backend_url_field,
        'credeasy-admin',
        'credeasy_admin_backend'
    );
});

add_action('admin_menu', function (): void {
    add_options_page(
        'CredEasy Admin',
        'CredEasy Admin',
        'manage_options',
        'credeasy-admin',
        function (): void {
            if (!current_user_can('manage_options')) {
                return;
            }
            echo '<div class="wrap"><h1>CredEasy Admin</h1>';
            settings_errors('credeasy_admin_settings');
            echo '<form action="options.php" method="post">';
            settings_fields('credeasy_admin_settings');
            do_settings_sections('credeasy-admin');
            submit_button('Save backend URL');
            echo '</form><p>Admin sign-in and permissions are still checked ' .
                'by Supabase and the backend. This setting does not grant ' .
                'admin access or contain a service-role key.</p></div>';
        }
    );
});

function credeasy_admin_security_headers(): void {
    nocache_headers();
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: same-origin');
    header('X-Frame-Options: DENY');
    header(
        "Content-Security-Policy: default-src 'self'; script-src 'self'; " .
        "style-src 'self'; img-src 'self' data:; " .
        "connect-src 'self' https://*.supabase.co wss://*.supabase.co; " .
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    );
}

add_action('template_redirect', function (): void {
    $asset = get_query_var('credeasy_admin_asset');
    if ($asset !== '') {
        $allowed = [
            'app.js' => 'text/javascript; charset=utf-8',
            'styles.css' => 'text/css; charset=utf-8',
            'supabase.min.js' => 'text/javascript; charset=utf-8',
            'SUPABASE-LICENSE.txt' => 'text/plain; charset=utf-8',
        ];
        if (!isset($allowed[$asset])) {
            status_header(404);
            exit;
        }
        $path = get_theme_file_path('/admin/' . $asset);
        if (!is_file($path)) {
            status_header(404);
            exit;
        }
        credeasy_admin_security_headers();
        header('Content-Type: ' . $allowed[$asset]);
        header('Cache-Control: public, max-age=300');
        readfile($path);
        exit;
    }

    if (get_query_var('credeasy_admin') !== '') {
        $path = get_theme_file_path('/admin/index.html');
        if (!is_file($path)) {
            status_header(503);
            exit;
        }
        $html = file_get_contents($path);
        if ($html === false) {
            status_header(503);
            exit;
        }
        credeasy_admin_security_headers();
        header('Content-Type: text/html; charset=utf-8');
        header('Cache-Control: no-store, max-age=0');
        echo str_replace(
            '/admin/assets/',
            esc_url(trailingslashit(get_theme_file_uri('/admin'))),
            $html
        );
        exit;
    }

    $route = get_query_var('credeasy_admin_api');
    if ($route === '') {
        return;
    }

    $backend_url = (string) get_option('credeasy_admin_backend_url', '');
    if ($backend_url === '') {
        status_header(503);
        header('Content-Type: application/json; charset=utf-8');
        echo wp_json_encode([
            'detail' => 'Set the backend URL in WordPress Settings → CredEasy Admin before signing in.',
        ]);
        exit;
    }

    $backend = untrailingslashit($backend_url);
    $backend_parts = wp_parse_url($backend);
    if (
        !$backend_parts ||
        ($backend_parts['scheme'] ?? '') !== 'https' ||
        empty($backend_parts['host']) ||
        isset($backend_parts['user']) ||
        isset($backend_parts['pass']) ||
        (!empty($backend_parts['path']) && $backend_parts['path'] !== '/') ||
        isset($backend_parts['query']) ||
        isset($backend_parts['fragment'])
    ) {
        status_header(503);
        header('Content-Type: application/json; charset=utf-8');
        echo wp_json_encode([
            'detail' => 'The admin backend URL must be a valid HTTPS origin.',
        ]);
        exit;
    }

    $uuid = credeasy_admin_uuid_pattern();
    $method = strtoupper((string) ($_SERVER['REQUEST_METHOD'] ?? 'GET'));
    $rules = [
        'GET' => [
            'config', 'me', 'overview', 'capabilities', 'users',
            'users/' . $uuid, 'roles', 'audit', 'ledger', 'content',
            'announcements', 'tickets', 'configuration', 'reports',
        ],
        'POST' => [
            'roles', 'users/' . $uuid . '/revoke-sessions',
            'content', 'announcements', 'tickets',
        ],
        'PATCH' => [
            'users/' . $uuid . '/status',
            'users/' . $uuid . '/verification',
            'content/' . $uuid,
            'tickets/' . $uuid,
        ],
        'PUT' => ['configuration'],
        'DELETE' => ['roles/' . $uuid],
    ];
    $route = trim((string) $route, '/');
    $is_allowed = false;
    foreach ($rules[$method] ?? [] as $rule) {
        if (preg_match('#^' . $rule . '$#D', $route) === 1) {
            $is_allowed = true;
            break;
        }
    }
    if (!$is_allowed) {
        status_header(404);
        header('Content-Type: application/json; charset=utf-8');
        echo wp_json_encode(['detail' => 'Admin API route not found.']);
        exit;
    }

    $authorization = (string) ($_SERVER['HTTP_AUTHORIZATION'] ?? '');
    if ($authorization === '' && function_exists('getallheaders')) {
        $incoming_headers = getallheaders();
        $authorization = (string) (
            $incoming_headers['Authorization'] ??
            $incoming_headers['authorization'] ??
            ''
        );
    }
    if ($route !== 'config') {
        if (
            strlen($authorization) > 8192 ||
            preg_match('/^Bearer [A-Za-z0-9._~+\\\\/-]+=*$/D', $authorization) !== 1
        ) {
            status_header(401);
            header('Content-Type: application/json; charset=utf-8');
            echo wp_json_encode([
                'detail' => 'A valid Supabase bearer token is required.',
            ]);
            exit;
        }
    }

    $query = '';
    if ($method === 'GET') {
        $query_args = [];
        if ($route === 'users') {
            $query_args = array_intersect_key(
                $_GET,
                array_flip(['page', 'search'])
            );
        } elseif ($route === 'audit') {
            $query_args = array_intersect_key($_GET, array_flip(['page']));
        } elseif ($route === 'ledger') {
            $query_args = array_intersect_key(
                $_GET,
                array_flip(['page', 'kind'])
            );
        }
        if ($query_args) {
            $query = '?' . http_build_query($query_args);
        }
    }

    $body = file_get_contents('php://input');
    if (strlen($body) > 10485760) {
        status_header(413);
        header('Content-Type: application/json; charset=utf-8');
        echo wp_json_encode(['detail' => 'Admin request body is too large.']);
        exit;
    }
    $request_args = [
        'method' => $method,
        'timeout' => 20,
        'redirection' => 0,
        'sslverify' => true,
        'headers' => [
            'Authorization' => $authorization,
            'Accept' => 'application/json',
            'Content-Type' => 'application/json',
        ],
    ];
    if ($method !== 'GET' && $method !== 'HEAD') {
        $request_args['body'] = $body;
    }

    $response = wp_safe_remote_request(
        $backend . '/api/admin/' . $route . $query,
        $request_args
    );
    if (is_wp_error($response)) {
        error_log('CredEasy admin proxy request failed: ' . $response->get_error_code());
        status_header(502);
        header('Content-Type: application/json; charset=utf-8');
        echo wp_json_encode([
            'detail' => 'The admin backend could not be reached. Check the backend URL and service status.',
        ]);
        exit;
    }

    status_header((int) wp_remote_retrieve_response_code($response));
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo wp_remote_retrieve_body($response);
    exit;
}, 0);
""",
    )

    write(
        THEME_DIR / "header.php",
        """<!doctype html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo('charset'); ?>">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<a class="skip-link" href="#main"><?php esc_html_e('Skip to content', 'credeasy-marketing'); ?></a>
"""
        + theme_urls(home_header),
    )
    write(
        THEME_DIR / "front-page.php",
        "<?php get_header(); ?>\n" + theme_urls(home_main) + "\n<?php get_footer(); ?>",
    )
    write(
        THEME_DIR / "footer.php",
        """<?php wp_footer(); ?>
</body>
</html>
""",
    )
    write(
        THEME_DIR / "header-legal.php",
        """<!doctype html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo('charset'); ?>">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<?php wp_head(); ?>
</head>
<body <?php body_class('credeasy-legal-page'); ?>>
<?php wp_body_open(); ?>
<a class="skip-link" href="#main"><?php esc_html_e('Skip to content', 'credeasy-marketing'); ?></a>
""",
    )

    for filename in ("privacy-policy.html", "terms-and-conditions.html"):
        source = (WEBSITE / filename).read_text(encoding="utf-8")
        body = extract(r"<body>(.*?)</body>", source, f"{filename} body")
        body = re.sub(
            r'<a class="skip-link" href="#main">.*?</a>',
            "",
            body,
            count=1,
            flags=re.DOTALL,
        )
        slug = filename.removesuffix(".html")
        php_filename = f"page-{slug}.php"
        write(
            THEME_DIR / php_filename,
            "<?php get_header('legal'); ?>\n"
            + theme_urls(body)
            + "\n<?php get_footer('legal'); ?>",
        )

    write(
        THEME_DIR / "footer-legal.php",
        """<?php wp_footer(); ?>
</body>
</html>
""",
    )
    write(
        THEME_DIR / "index.php",
        """<?php get_header(); ?>
<main id="main" class="container section">
    <?php if (have_posts()) : while (have_posts()) : the_post(); ?>
        <article <?php post_class(); ?>>
            <h1><?php the_title(); ?></h1>
            <?php the_content(); ?>
        </article>
    <?php endwhile; else : ?>
        <h1><?php esc_html_e('Nothing found', 'credeasy-marketing'); ?></h1>
    <?php endif; ?>
</main>
<?php get_footer(); ?>
""",
    )
    write(
        THEME_DIR / "404.php",
        """<?php get_header(); ?>
<main id="main" class="container section">
    <h1><?php esc_html_e('Page not found', 'credeasy-marketing'); ?></h1>
    <p><?php esc_html_e('The page may have moved. Return to the CredEasy homepage.', 'credeasy-marketing'); ?></p>
    <a class="button button-primary" href="<?php echo esc_url(home_url('/')); ?>">
        <?php esc_html_e('Back to CredEasy', 'credeasy-marketing'); ?>
    </a>
</main>
<?php get_footer(); ?>
""",
    )
    write(
        THEME_DIR / "README.txt",
        """CredEasy WordPress theme

INSTALL
1. Back up the current WordPress site first.
2. In WordPress, open Appearance > Themes > Add New Theme > Upload Theme.
3. Upload credeasy-wordpress-theme.zip, install it, then activate it.
4. Create and publish two WordPress pages:
   - Title: Privacy Policy; slug: privacy-policy
   - Title: Terms & Conditions; slug: terms-and-conditions
   The theme supplies the legal content on these pages.
5. In WordPress Settings > General, find the CredEasy Admin section near the bottom and save the HTTPS backend URL.
6. Open the homepage, legal pages and /admin to verify the theme.
If /admin still shows Page not found on an existing installation, open Settings >
Permalinks and select Save Changes once to refresh WordPress's route table.
The admin page assets load directly from the active theme; an API 404 means the
configured backend origin is wrong or its CredEasy admin routes are not deployed.

The theme's front-page.php provides the homepage automatically. It includes the
CredEasy Ledger, Inventory and Billing screens and does not require a page builder.
Choose a site icon in Appearance > Customize > Site Identity if desired.

To return to the previous design, activate the previous theme in Appearance > Themes.

ADMIN CONSOLE
The theme provides /admin and proxies only allowlisted admin API routes to the
HTTPS backend. To set the backend URL, sign into WordPress and open
Settings > General. Find the CredEasy Admin section near the bottom of the
page. Enter the backend's HTTPS origin only, for example:
https://credeasy-01.onrender.com
Do not include /api, /admin, credentials, or a path. Save the setting; you do
not need to edit wp-config.php or use SFTP. A shortcut is also available under
Settings > CredEasy Admin.
If the page reports that this backend host returned 404, confirm that the
configured HTTPS origin is the deployed CredEasy FastAPI service with the
admin routes deployed. The static website host credeasy-app.onrender.com is not
the API. Check https://credeasy-01.onrender.com/api/admin/config; it should
return a JSON response (including a JSON configuration error if Supabase
settings are missing), not a plain 404. Deploy the backend changes before
expecting this route to work.

On the backend host, configure SUPABASE_URL, SUPABASE_ANON_KEY,
   SUPABASE_SERVICE_ROLE_KEY and ADMIN_BOOTSTRAP_EMAILS, then apply the
repository's docs/enable-admin-panel.sql migration in Supabase. In Supabase
Auth, allow https://credeasy.live/admin as a Google OAuth redirect URL (also
add the www URL only if the site uses it). The admin session is authenticated
by Supabase; WordPress accounts are not granted CredEasy admin access.
""",
    )

    assets = THEME_DIR / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for filename in (
        "credeasy-mark.png",
        "app-ledger.webp",
        "app-inventory.webp",
        "app-billing.webp",
    ):
        (assets / filename).write_bytes((WEBSITE / "assets" / filename).read_bytes())
    write(assets / "site.js", home_script)

    if not ADMIN_STATIC_DIR.is_dir():
        raise FileNotFoundError(f"Admin static assets are missing: {ADMIN_STATIC_DIR}")
    admin_assets = THEME_DIR / "admin"
    admin_assets.mkdir(parents=True, exist_ok=True)
    for filename in (
        "index.html",
        "app.js",
        "styles.css",
        "supabase.min.js",
        "SUPABASE-LICENSE.txt",
    ):
        source = ADMIN_STATIC_DIR / filename
        if not source.is_file():
            raise FileNotFoundError(f"Required admin asset is missing: {source}")
        (admin_assets / filename).write_bytes(source.read_bytes())

    with ZipFile(ARCHIVE, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(THEME_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT).as_posix())

    with ZipFile(ARCHIVE) as archive:
        broken_file = archive.testzip()
        if broken_file:
            raise ValueError(f"Archive integrity check failed at {broken_file}")
        required = {
            f"{THEME_NAME}/style.css",
            f"{THEME_NAME}/functions.php",
            f"{THEME_NAME}/front-page.php",
            f"{THEME_NAME}/page-privacy-policy.php",
            f"{THEME_NAME}/page-terms-and-conditions.php",
            f"{THEME_NAME}/assets/site.js",
            f"{THEME_NAME}/assets/app-ledger.webp",
            f"{THEME_NAME}/assets/app-inventory.webp",
            f"{THEME_NAME}/assets/app-billing.webp",
            f"{THEME_NAME}/admin/index.html",
            f"{THEME_NAME}/admin/app.js",
            f"{THEME_NAME}/admin/styles.css",
            f"{THEME_NAME}/admin/supabase.min.js",
            f"{THEME_NAME}/admin/SUPABASE-LICENSE.txt",
        }
        missing = required - set(archive.namelist())
        if missing:
            raise ValueError(f"Archive is missing required files: {sorted(missing)}")

    print(f"Created {ARCHIVE} ({ARCHIVE.stat().st_size:,} bytes)")
    print(f"Theme source: {THEME_DIR}")


if __name__ == "__main__":
    make_theme()
