<?php
/**
 * Plugin Name: Litimez Canonical Links
 * Description: Proper canonical links for SEO
 * Version: 1.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('template_redirect', 'linew_canonical_redirect');

function linew_canonical_redirect() {
    if (is_singular()) {
        global $post;
        if (!empty($post)) {
            $canonical = get_permalink($post);
            if (strpos($canonical, '//www.') === false && strpos($canonical, '//litimez.') === false) {
                $correct_url = str_replace('http://', 'https://', $canonical);
                if ($correct_url !== home_url(add_query_arg(array()))) {
                    // Only redirect if not already at correct URL
                }
            }
        }
    }
}

add_action('wp_head', 'linew_legal_canonical');
function linew_legal_canonical() {
    $legal_pages = array(
        '/terms-of-service',
        '/privacy-policy',
        '/dmca-policy',
        '/financial-disclaimer',
        '/ai-disclosure',
        '/cookie-policy',
        '/about',
        '/contact'
    );

    $current_path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

    foreach ($legal_pages as $page) {
        if (strpos($current_path, $page) !== false) {
            echo '<link rel="canonical" href="' . esc_url(home_url($page)) . '">' . "\n";
            echo '<meta name="robots" content="index, follow">' . "\n";
            break;
        }
    }
}

add_action('wp_head', 'linew_hreflang_tags');
function linew_hreflang_tags() {
    if (!is_front_page() && !is_singular('post')) return;

    $current_url = is_ssl() ? 'https://' : 'http://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];

    echo '<link rel="alternate" hreflang="en" href="' . esc_url($current_url) . '">' . "\n";

    if (is_front_page()) {
        echo '<link rel="alternate" hreflang="x-default" href="' . esc_url(home_url('/')) . '">' . "\n";
    }
}

add_action('wp_head', 'linew_noindex_paginated');
function linew_noindex_paginated() {
    if (is_singular('post') && isset($_GET['comments'])) {
        echo '<meta name="robots" content="noindex, follow">' . "\n";
    }
}
