<?php
/**
 * Header Template - Tinh tế Style Redesign
 * Minimal, smart, edge-to-edge
 *
 * @package Linew_Viral
 */

if (!defined('ABSPATH')) {
    exit;
}

// Get breaking news
$breaking_news = linew_get_breaking_news(5);
$has_breaking = !empty($breaking_news);

// Get categories for manual menu rendering (already translated via functions.php filter)
// Show all 10 categories regardless of post count
$category_order = array('Politics', 'World', 'Business', 'Technology', 'Science', 'Health', 'Sports', 'Entertainment', 'Finance', 'Education');
$menu_categories = get_categories(array(
    'hide_empty' => false,  // Show all categories
    'number'     => 10,
));

// Sort categories by predefined order (exclude Uncategorized)
usort($menu_categories, function($a, $b) use ($category_order) {
    // Skip Uncategorized
    if ($a->slug === 'uncategorized') return 1;
    if ($b->slug === 'uncategorized') return -1;
    
    $pos_a = array_search($a->name, $category_order);
    $pos_b = array_search($b->name, $category_order);
    $pos_a = ($pos_a === false) ? 999 : $pos_a;
    $pos_b = ($pos_b === false) ? 999 : $pos_b;
    return $pos_a - $pos_b;
});

// Build category menu items array with English names
$category_menu_items = array();
foreach ($menu_categories as $cat) {
    $category_menu_items[] = array(
        'title' => linew_translate_category($cat->name, 'en'),
        'url'   => get_category_link($cat->term_id),
        'slug'  => $cat->slug,
    );
}
?>
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<div id="lv-page" class="lv-page">

    <!-- Header - Single Row, Tinh tế Style -->
    <header class="lv-header" id="lv-header">
        <div class="lv-header-container">
            <!-- Logo -->
            <a href="<?php echo esc_url(home_url('/')); ?>" class="lv-logo" aria-label="Litimez Home">
                <?php if (has_custom_logo()) : ?>
                    <?php the_custom_logo(); ?>
                <?php else : ?>
                    Litimez<span class="lv-logo-dot">.</span>
                <?php endif; ?>
            </a>

            <!-- Navigation - Desktop -->
            <nav class="lv-nav-desktop" role="navigation" aria-label="<?php esc_attr_e('Primary Menu', 'linew-viral'); ?>">
                <?php
                // Check if menu exists
                $primary_menu = wp_get_nav_menu_object('Primary Navigation');
                if ($primary_menu) {
                    wp_nav_menu(array(
                        'theme_location' => 'primary',
                        'container'      => false,
                        'menu_class'     => 'lv-nav-list',
                        'items_wrap'     => '<ul class="lv-nav-list">%3$s</ul>',
                        'depth'          => 1,
                    ));
                } else {
                    // Fallback: render categories manually
                    echo '<ul class="lv-nav-list">';
                    foreach ($category_menu_items as $item) {
                        printf(
                            '<li><a href="%s">%s</a></li>',
                            esc_url($item['url']),
                            esc_html($item['title'])
                        );
                    }
                    echo '</ul>';
                }
                ?>
            </nav>

            <!-- Actions -->
            <div class="lv-header-actions">
                <!-- Search Button -->
                <button class="lv-header-btn lv-search-btn" id="lv-search-toggle" aria-label="Search">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="M21 21l-4.35-4.35"/>
                    </svg>
                </button>

                <!-- User Menu -->
                <?php if (is_user_logged_in()) : ?>
                    <a href="<?php echo esc_url(admin_url()); ?>" class="lv-header-btn lv-user-btn" aria-label="Dashboard">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                        </svg>
                    </a>
                <?php else : ?>
                    <a href="<?php echo esc_url(wp_login_url()); ?>" class="lv-header-btn lv-user-btn" aria-label="Sign In">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                        </svg>
                    </a>
                <?php endif; ?>

                <!-- Mobile Menu Toggle -->
                <button class="lv-header-btn lv-menu-btn" id="lv-menu-toggle" aria-label="Menu">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 12h18M3 6h18M3 18h18"/>
                    </svg>
                </button>
            </div>
        </div>
    </header>

    <!-- Search Overlay -->
    <div class="lv-search-overlay" id="lv-search-overlay">
        <div class="lv-search-inner">
            <button class="lv-search-close" id="lv-search-close" aria-label="Close search">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>
            <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>" class="lv-search-form">
                <input type="search" name="s" placeholder="Search news, topics..." autocomplete="off" autofocus>
                <button type="submit">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="M21 21l-4.35-4.35"/>
                    </svg>
                </button>
            </form>
            <div class="lv-search-hints">
                <span>Trending:</span>
                <a href="#">Bitcoin</a>
                <a href="#">AI</a>
                <a href="#">Crypto</a>
                <a href="#">Markets</a>
            </div>
        </div>
    </div>

    <!-- Mobile Menu - Full Screen -->
    <div class="lv-mobile-menu" id="lv-mobile-menu">
        <div class="lv-mobile-menu-header">
            <a href="<?php echo esc_url(home_url('/')); ?>" class="lv-logo">Litimez<span>.</span></a>
            <button class="lv-mobile-menu-close" id="lv-menu-close" aria-label="Close menu">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>
        </div>

        <nav class="lv-mobile-nav">
            <ul class="lv-mobile-menu-list">
                <?php
                // Check if mobile menu exists
                $mobile_menu = wp_get_nav_menu_object('Primary Navigation');
                if ($mobile_menu) {
                    // Get menu items
                    $menu_items = wp_get_nav_menu_items($mobile_menu->term_id);
                    if ($menu_items) {
                        foreach ($menu_items as $item) {
                            printf(
                                '<li><a href="%s" class="lv-mobile-menu-link">%s</a></li>',
                                esc_url($item->url),
                                esc_html($item->title)
                            );
                        }
                    }
                } else {
                    // Fallback: render categories manually
                    foreach ($category_menu_items as $item) {
                        printf(
                            '<li><a href="%s" class="lv-mobile-menu-link">%s</a></li>',
                            esc_url($item['url']),
                            esc_html($item['title'])
                        );
                    }
                }
                ?>
            </ul>
        </nav>

        <div class="lv-mobile-menu-footer">
            <?php if (is_user_logged_in()) : ?>
                <a href="<?php echo admin_url(); ?>" class="lv-mobile-menu-link">Dashboard</a>
                <a href="<?php echo wp_logout_url(); ?>" class="lv-mobile-menu-link">Logout</a>
            <?php else : ?>
                <a href="<?php echo wp_login_url(); ?>" class="lv-mobile-menu-link">Sign In</a>
                <a href="<?php echo wp_registration_url(); ?>" class="lv-mobile-menu-link lv-mobile-menu-primary">Sign Up</a>
            <?php endif; ?>
        </div>
    </div>
    <div class="lv-mobile-menu-overlay" id="lv-mobile-menu-overlay"></div>

    <!-- Main Content -->
    <main class="lv-main" id="lv-main-content">
