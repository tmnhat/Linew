<?php
/**
 * Linew Viral Theme Functions
 *
 * @package Linew_Viral
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Theme constants
define('LINEW_VERSION', '2.1.0');

/**
 * Theme Setup
 */
function linew_viral_setup() {
    // Make theme available for translation
    load_theme_textdomain('linew-viral', get_template_directory() . '/languages');

    // Add default posts and comments RSS feed links
    add_theme_support('automatic-feed-links');

    // Let WordPress manage the document title
    add_theme_support('title-tag');

    // Enable support for Post Thumbnails
    add_theme_support('post-thumbnails');
    add_image_size('linew-hero', 1200, 600, true);
    add_image_size('linew-large', 800, 500, true);
    add_image_size('linew-medium', 600, 400, true);
    add_image_size('linew-small', 300, 200, true);
    add_image_size('linew-thumbnail', 150, 150, true);

    // Register navigation menus
    register_nav_menus(array(
        'primary'   => __('Primary Menu', 'linew-viral'),
        'footer'    => __('Footer Menu', 'linew-viral'),
        'mobile'    => __('Mobile Menu', 'linew-viral'),
    ));

    // Switch default core markup
    add_theme_support('html5', array(
        'search-form',
        'comment-form',
        'comment-list',
        'gallery',
        'caption',
        'style',
        'script',
    ));

    // Add theme support for selective refresh for widgets
    add_theme_support('customize-selective-refresh-widgets');

    // Logo support
    add_theme_support('custom-logo', array(
        'height'      => 100,
        'width'       => 300,
        'flex-height' => true,
        'flex-width'  => true,
    ));
}
add_action('after_setup_theme', 'linew_viral_setup');

/**
 * Enqueue Scripts and Styles
 */
function linew_viral_scripts() {
    // Google Fonts - Inter for clean Apple-like typography
    wp_enqueue_style(
        'linew-google-fonts',
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap',
        array(),
        null
    );

    // Main stylesheet
    wp_enqueue_style(
        'linew-style',
        get_stylesheet_uri(),
        array(),
        LINEW_VERSION
    );

    // Custom scripts
    wp_enqueue_script(
        'linew-scripts',
        get_template_directory_uri() . '/assets/js/main.js',
        array('jquery'),
        LINEW_VERSION,
        true
    );

    // Market Ticker Script (loaded on homepage)
    if (is_front_page()) {
        wp_enqueue_script(
            'linew-ticker',
            get_template_directory_uri() . '/assets/js/ticker.js',
            array('jquery'),
            LINEW_VERSION,
            true
        );

        // Localize for ticker
        $api_base = rest_url('linew/v1');
        wp_localize_script('linew-ticker', 'linewConfig', array(
            'apiUrl' => $api_base,
            'defaultSymbol' => 'BTC-USD',
        ));

        // Masonry CSS
        wp_enqueue_style(
            'linew-masonry',
            get_template_directory_uri() . '/assets/css/masonry.css',
            array('linew-style'),
            LINEW_VERSION
        );

        // Infinite Scroll JS
        wp_enqueue_script(
            'linew-infinite-scroll',
            get_template_directory_uri() . '/assets/js/infinite-scroll.js',
            array('jquery'),
            LINEW_VERSION,
            true
        );

        // Get current language
        $current_lang = linew_get_current_language();

        // Localize for infinite scroll with language support
        wp_localize_script('linew-infinite-scroll', 'linewFeedConfig', array(
            'apiBase' => rest_url('linew/v1'),
            'currentLang' => $current_lang,
        ));
    }

    // Comment reply script
    if (is_singular() && comments_open() && get_option('thread_comments')) {
        wp_enqueue_script('comment-reply');
    }
}
add_action('wp_enqueue_scripts', 'linew_viral_scripts');

/**
 * Register Widget Areas
 */
function linew_viral_widgets() {
    register_sidebar(array(
        'name'          => __('Sidebar', 'linew-viral'),
        'id'            => 'sidebar-1',
        'description'   => __('Add widgets here to appear in your sidebar.', 'linew-viral'),
        'before_widget' => '<section id="%1$s" class="lv-widget %2$s">',
        'after_widget'  => '</section>',
        'before_title'  => '<h3 class="lv-widget-title">',
        'after_title'   => '</h3>',
    ));

    register_sidebar(array(
        'name'          => __('Footer Column 1', 'linew-viral'),
        'id'            => 'footer-1',
        'description'   => __('First footer widget area.', 'linew-viral'),
        'before_widget' => '<div id="%1$s" class="lv-footer-col %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h4>',
        'after_title'   => '</h4>',
    ));

    register_sidebar(array(
        'name'          => __('Footer Column 2', 'linew-viral'),
        'id'            => 'footer-2',
        'description'   => __('Second footer widget area.', 'linew-viral'),
        'before_widget' => '<div id="%1$s" class="lv-footer-col %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h4>',
        'after_title'   => '</h4>',
    ));

    register_sidebar(array(
        'name'          => __('Footer Column 3', 'linew-viral'),
        'id'            => 'footer-3',
        'description'   => __('Third footer widget area.', 'linew-viral'),
        'before_widget' => '<div id="%1$s" class="lv-footer-col %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h4>',
        'after_title'   => '</h4>',
    ));

    register_sidebar(array(
        'name'          => __('Footer Column 4', 'linew-viral'),
        'id'            => 'footer-4',
        'description'   => __('Fourth footer widget area.', 'linew-viral'),
        'before_widget' => '<div id="%1$s" class="lv-footer-col %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h4>',
        'after_title'   => '</h4>',
    ));
}
add_action('widgets_init', 'linew_viral_widgets');

/**
 * Custom Excerpt Length
 */
function linew_excerpt_length($length) {
    return 20;
}
add_filter('excerpt_length', 'linew_excerpt_length');

/**
 * Custom Excerpt More
 */
function linew_excerpt_more($more) {
    return '...';
}
add_filter('excerpt_more', 'linew_excerpt_more');

/**
 * Get current site language
 * Check in order: URL param > Cookie > WordPress locale
 */
function linew_get_current_language() {
    // Check URL parameter first
    if (isset($_GET['lang']) && in_array($_GET['lang'], array('vi', 'en'), true)) {
        return sanitize_text_field($_GET['lang']);
    }

    // Check cookie
    if (isset($_COOKIE['linew_lang']) && in_array($_COOKIE['linew_lang'], array('vi', 'en'), true)) {
        return sanitize_text_field($_COOKIE['linew_lang']);
    }

    // Check WordPress locale
    $locale = get_locale();
    if (strpos($locale, 'en') === 0) {
        return 'en';
    }

    // Default to Vietnamese
    return 'vi';
}

/**
 * Category Translation Mapping (Vietnamese -> English)
 * Dùng để hiển thị category đúng ngôn ngữ với bài viết
 */
function linew_get_category_translations() {
    return array(
        // Vietnamese => English
        'Công nghệ' => 'Technology',
        'Công Nghiệp' => 'Technology',
        'AI' => 'AI',
        'Trí tuệ nhân tạo' => 'Artificial Intelligence',
        'Tài chính' => 'Finance',
        'Tiền điện tử' => 'Crypto',
        'Crypto' => 'Crypto',
        'Bitcoin' => 'Bitcoin',
        'Blockchain' => 'Blockchain',
        'Thị trường' => 'Markets',
        'Kinh tế' => 'Economy',
        'Chứng khoán' => 'Stock Market',
        'Startup' => 'Startup',
        'Khởi nghiệp' => 'Startup',
        'Game' => 'Gaming',
        'Gaming' => 'Gaming',
        'Esports' => 'Esports',
        'Thể thao' => 'Sports',
        'Sức khỏe' => 'Health',
        'Y tế' => 'Healthcare',
        'Giáo dục' => 'Education',
        'Du lịch' => 'Travel',
        'Ẩm thực' => 'Food',
        'Lifestyle' => 'Lifestyle',
        'Ô tô' => 'Automotive',
        'Xe hơi' => 'Automotive',
        'Bất động sản' => 'Real Estate',
        'Chính trị' => 'Politics',
        'Thế giới' => 'World',
        'Giải trí' => 'Entertainment',
        'Sao' => 'Celebrity',
        'Phim' => 'Movies',
        'Âm nhạc' => 'Music',
        'Sách' => 'Books',
        'Khoa học' => 'Science',
        'Space' => 'Space',
        'Vũ trụ' => 'Space',
        'Môi trường' => 'Environment',
        'Xã hội' => 'Society',
        'Pháp luật' => 'Legal',
        'Bảo mật' => 'Security',
        'An ninh mạng' => 'Cybersecurity',
        'Quốc tế' => 'International',
        'Quốc Tế' => 'International',
        'Khám phá' => 'Explore',
        'Khám Phá' => 'Explore',
    );
}

/**
 * Translate category name based on current language
 */
function linew_translate_category($category_name, $lang = 'vi') {
    if ($lang !== 'en') {
        return $category_name;
    }

    $translations = linew_get_category_translations();
    $normalized = trim($category_name);

    if (isset($translations[$normalized])) {
        return $translations[$normalized];
    }

    // Check case-insensitive match
    foreach ($translations as $vi => $en) {
        if (strtolower($vi) === strtolower($normalized)) {
            return $en;
        }
    }

    return $category_name;
}

/**
 * Get Category with Color and Translation Support
 */
function linew_get_category($post_id = null, $lang = 'vi') {
    $categories = get_the_category($post_id);
    if (!empty($categories)) {
        $category = $categories[0];
        return array(
            'name' => linew_translate_category($category->name, $lang),
            'slug' => $category->slug,
            'url' => get_category_link($category->term_id),
        );
    }
    return null;
}

/**
 * Get Featured Image URL
 * Falls back to first image in content if no featured image set
 * Falls back to default image if no images found
 */
function linew_get_featured_image($size = 'large', $post_id = null) {
    // First: Check for external featured image URL (from Linew)
    if ($post_id === null) {
        global $post;
        $post_id = $post ? $post->ID : 0;
    }
    $external_image = get_post_meta($post_id, '_external_featured_image', true);
    if ($external_image) {
        return esc_url($external_image);
    }

    // Second: Try WordPress featured image
    if (has_post_thumbnail($post_id)) {
        return get_the_post_thumbnail_url($post_id, $size);
    }

    // Fallback: get first image from content (skip SVG, icons, etc.)
    $first_image = linew_get_first_image_from_content($post_id);
    if ($first_image) {
        return $first_image;
    }

    // LAST RESORT: Use default fallback image
    return linew_get_default_fallback_image();
}

/**
 * Get default fallback image
 */
function linew_get_default_fallback_image() {
    // Multiple fallback images for variety
    $fallback_images = array(
        'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80',
        'https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&q=80',
        'https://images.unsplash.com/photo-1432821596592-e2c18b78144f?w=1200&q=80',
        'https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=1200&q=80',
        'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80',
        'https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=80',
        'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80',
        'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80',
    );

    // Use post ID as seed for consistent image per post
    global $post;
    if ($post) {
        $index = $post->ID % count($fallback_images);
        return $fallback_images[$index];
    }

    return $fallback_images[0];
}

/**
 * Get first image from post content
 * Filters out SVG, icons, and small images
 */
function linew_get_first_image_from_content($post_id = null) {
    if ($post_id === null) {
        global $post;
        $post_id = $post->ID;
    }

    $content = get_post_field('post_content', $post_id);
    $images = linew_get_all_images_from_content($post_id);

    // Return first valid image (non-SVG)
    foreach ($images as $src) {
        // Skip SVG files
        if (preg_match('/\.svg(\?|$)/i', $src)) {
            continue;
        }
        // Skip data URLs
        if (strpos($src, 'data:') === 0) {
            continue;
        }
        return $src;
    }

    return null;
}

/**
 * Get all images from post content
 * Filters out SVG, icons, and small images
 */
function linew_get_all_images_from_content($post_id = null) {
    if ($post_id === null) {
        global $post;
        $post_id = $post->ID;
    }

    $content = get_post_field('post_content', $post_id);
    $images = array();

    // Find all img tags with src
    if (preg_match_all('/<img[^>]+src=["\']([^"\']+)["\'][^>]*>/i', $content, $matches)) {
        foreach ($matches[1] as $src) {
            // Skip SVG, icons, small images
            $skip = false;
            $skip_patterns = array(
                '.svg',
                'icon',
                'logo',
                'pixel',
                'avatar',
                'favicon',
                '/1x1/',
                'spacer',
                'data:',
                'wp-image-',
                'smileys/',
                'emojis/',
                'smilies/'
            );
            foreach ($skip_patterns as $pattern) {
                if (stripos($src, $pattern) !== false) {
                    $skip = true;
                    break;
                }
            }
            if (!$skip) {
                $images[] = $src;
            }
        }
    }

    return $images;
}

/**
 * Check if post has real images (not SVG or icons)
 */
function linew_has_real_images($post_id = null) {
    $first_image = linew_get_first_image_from_content($post_id);
    return !empty($first_image);
}

/**
 * Get Trending Posts
 */
function linew_get_trending_posts($limit = 5) {
    $args = array(
        'post_type'           => 'post',
        'posts_per_page'      => $limit,
        'post_status'         => 'publish',
        'orderby'            => 'meta_value_num',
        'meta_key'            => '_post_views_count',
        'order'               => 'DESC',
        'ignore_sticky_posts' => 1,
    );

    $query = new WP_Query($args);
    return $query->posts;
}

/**
 * Get Related Posts
 */
function linew_get_related_posts($post_id, $limit = 3) {
    $post_categories = wp_get_post_categories($post_id);

    if (empty($post_categories)) {
        return array();
    }

    $args = array(
        'post_type'           => 'post',
        'posts_per_page'      => $limit,
        'post_status'         => 'publish',
        'category__in'        => $post_categories,
        'post__not_in'        => array($post_id),
        'ignore_sticky_posts' => 1,
    );

    $query = new WP_Query($args);
    return $query->posts;
}

/**
 * Get Breaking News Posts
 */
function linew_get_breaking_news($limit = 5) {
    $args = array(
        'post_type'           => 'post',
        'posts_per_page'      => $limit,
        'post_status'         => 'publish',
        'orderby'             => 'date',
        'order'               => 'DESC',
        'ignore_sticky_posts' => 1,
        'meta_query'          => array(
            array(
                'key'     => '_is_breaking',
                'value'   => '1',
                'compare' => '=',
            ),
        ),
    );

    $query = new WP_Query($args);

    // Fallback to recent posts if no breaking news
    if (!$query->have_posts()) {
        $args['meta_query'] = array();
        $args['posts_per_page'] = $limit;
        $query = new WP_Query($args);
    }

    return $query->posts;
}

/**
 * Get Posts by Category
 */
function linew_get_posts_by_category($category_slug, $limit = 8, $exclude = array()) {
    $args = array(
        'post_type'           => 'post',
        'posts_per_page'      => $limit,
        'post_status'         => 'publish',
        'category_name'       => $category_slug,
        'post__not_in'        => $exclude,
        'ignore_sticky_posts' => 1,
    );

    $query = new WP_Query($args);
    return $query->posts;
}

/**
 * Format Date
 */
function linew_format_date($date = null, $format = 'F j, Y') {
    if ($date === null) {
        $date = get_the_date();
    }
    return date_i18n($format, strtotime($date));
}

/**
 * Reading Time
 */
function linew_reading_time($post_id = null) {
    $content = get_post_field('post_content', $post_id);
    $word_count = str_word_count(strip_tags($content));
    $reading_time = ceil($word_count / 200); // 200 words per minute

    return sprintf(
        '%d %s',
        $reading_time,
        $reading_time == 1 ? __('min read', 'linew-viral') : __('min read', 'linew-viral')
    );
}

/**
 * Social Share Buttons
 */
function linew_social_share() {
    $url = urlencode(get_permalink());
    $title = urlencode(get_the_title());

    $share_links = array(
        'facebook'  => 'https://www.facebook.com/sharer/sharer.php?u=' . $url,
        'twitter'   => 'https://twitter.com/intent/tweet?url=' . $url . '&text=' . $title,
        'linkedin'  => 'https://www.linkedin.com/shareArticle?mini=true&url=' . $url . '&title=' . $title,
        'whatsapp'  => 'https://wa.me/?text=' . $title . '%20' . $url,
        'telegram'  => 'https://t.me/share/url?url=' . $url . '&text=' . $title,
    );

    $html = '<div class="lv-share-buttons">';
    $html .= '<span class="lv-share-label">' . __('Share:', 'linew-viral') . '</span>';

    foreach ($share_links as $network => $link) {
        $html .= sprintf(
            '<a href="%s" class="lv-share-btn lv-share-%s" target="_blank" rel="noopener noreferrer">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <use href="#icon-%s"></use>
                </svg>
            </a>',
            esc_url($link),
            esc_attr($network),
            esc_attr($network)
        );
    }

    $html .= '</div>';
    return $html;
}

/**
 * View Count (Custom)
 */
function linew_get_view_count($post_id = null) {
    $count = get_post_meta($post_id, '_post_views_count', true);
    return $count ? (int) $count : 0;
}

function linew_set_view_count($post_id) {
    $count = get_post_meta($post_id, '_post_views_count', true);
    if ($count == '') {
        $count = 1;
        delete_post_meta($post_id, '_post_views_count');
        add_post_meta($post_id, '_post_views_count', $count);
    } else {
        $count++;
        update_post_meta($post_id, '_post_views_count', $count);
    }
}

/**
 * Post View Tracking
 */
function linew_track_post_views($post_id) {
    if (!is_single()) {
        return;
    }
    linew_set_view_count($post_id);
}
add_action('wp_head', function() {
    if (is_single()) {
        global $post;
        linew_track_post_views($post->ID);
    }
});

/**
 * Custom Body Classes
 */
function linew_body_classes($classes) {
    if (is_singular()) {
        $classes[] = 'singular';
    }

    if (is_front_page()) {
        $classes[] = 'front-page';
    }

    if (is_active_sidebar('sidebar-1')) {
        $classes[] = 'has-sidebar';
    }

    return $classes;
}
add_filter('body_class', 'linew_body_classes');

/**
 * SVG Icons
 */
function linew_include_svg_icons() {
    $svg_icons = '
    <svg style="display: none;" xmlns="http://www.w3.org/2000/svg">
        <!-- Facebook -->
        <symbol id="icon-facebook" viewBox="0 0 24 24">
            <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>
        </symbol>
        <!-- Twitter/X -->
        <symbol id="icon-twitter" viewBox="0 0 24 24">
            <path d="M4 4l11.7 16h4.3L8.3 4H4zM4 20l6.5-7M20 4l-6.5 7"/>
        </symbol>
        <!-- LinkedIn -->
        <symbol id="icon-linkedin" viewBox="0 0 24 24">
            <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>
            <rect x="2" y="9" width="4" height="12"/>
            <circle cx="4" cy="4" r="2"/>
        </symbol>
        <!-- WhatsApp -->
        <symbol id="icon-whatsapp" viewBox="0 0 24 24">
            <path d="M17.5 6.5c0-3.5-2.9-6.5-6.5-6.5S4.5 3 4.5 6.5c0 1.2.3 2.4 1 3.4L4.5 21l4.5-1.5c.9.6 2 .9 3 .9 3.5 0 6.5-2.9 6.5-6.5z"/>
            <path d="M10 9a1 1 0 0 1 1 1M13 11a2 2 0 0 1-2 2M16 15a1 1 0 0 1-1 1"/>
        </symbol>
        <!-- Telegram -->
        <symbol id="icon-telegram" viewBox="0 0 24 24">
            <path d="M21.198 2.433a2.242 2.242 0 0 0-1.022.215l-17.15 7.593a1.6 1.6 0 0 0 .145 2.97l4.246 1.467 1.644 5.165a1.3 1.3 0 0 0 2.088.505l2.364-2.063 4.166 3.122a1.736 1.736 0 0 0 2.744-.94L22.113 3.46a2.335 2.335 0 0 0-.915-1.027z"/>
        </symbol>
        <!-- Search -->
        <symbol id="icon-search" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" fill="none" stroke="currentColor" stroke-width="2"/>
            <path d="M21 21l-4.35-4.35" fill="none" stroke="currentColor" stroke-width="2"/>
        </symbol>
        <!-- Menu -->
        <symbol id="icon-menu" viewBox="0 0 24 24">
            <path d="M3 12h18M3 6h18M3 18h18" fill="none" stroke="currentColor" stroke-width="2"/>
        </symbol>
        <!-- Close -->
        <symbol id="icon-close" viewBox="0 0 24 24">
            <path d="M18 6L6 18M6 6l12 12" fill="none" stroke="currentColor" stroke-width="2"/>
        </symbol>
        <!-- Arrow Right -->
        <symbol id="icon-arrow-right" viewBox="0 0 24 24">
            <path d="M5 12h14M12 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2"/>
        </symbol>
        <!-- Clock -->
        <symbol id="icon-clock" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>
            <path d="M12 6v6l4 2" fill="none" stroke="currentColor" stroke-width="2"/>
        </symbol>
        <!-- Eye -->
        <symbol id="icon-eye" viewBox="0 0 24 24">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" fill="none" stroke="currentColor" stroke-width="2"/>
            <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2"/>
        </symbol>
    </svg>';

    echo $svg_icons;
}
add_action('wp_footer', 'linew_include_svg_icons');

/**
 * Register Custom Rest API Endpoint for Breaking News
 */
function linew_register_rest_api() {
    register_rest_route('linew/v1', '/breaking-news', array(
        'methods'  => 'GET',
        'callback' => function() {
            $posts = linew_get_breaking_news(5);
            $data = array();

            foreach ($posts as $post) {
                setup_postdata($post);
                $data[] = array(
                    'id'      => $post->ID,
                    'title'   => get_the_title($post->ID),
                    'url'     => get_permalink($post->ID),
                    'excerpt' => get_the_excerpt($post->ID),
                    'image'   => linew_get_featured_image('medium', $post->ID),
                );
            }
            wp_reset_postdata();

            return rest_ensure_response($data);
        },
        'permission_callback' => '__return_true',
    ));
}
add_action('rest_api_init', 'linew_register_rest_api');

/**
 * Add Custom Meta Fields to REST API
 */
function linew_register_post_meta() {
    register_post_meta('post', '_post_views_count', array(
        'show_in_rest'  => true,
        'single'        => true,
        'type'          => 'integer',
    ));

    register_post_meta('post', '_is_breaking', array(
        'show_in_rest'  => true,
        'single'        => true,
        'type'          => 'string',
    ));
}
add_action('init', 'linew_register_post_meta');

/**
 * Customize Read More Link
 */
function linew_read_more_link() {
    return '<a class="lv-read-more" href="' . get_permalink() . '">' . __('Continue Reading', 'linew-viral') . '</a>';
}
add_filter('the_content_more_link', 'linew_read_more_link');

/**
 * Remove WordPress Version
 */
remove_action('wp_head', 'wp_generator');

/**
 * Disable WordPress Embeds
 */
function linew_disable_embeds() {
    wp_deregister_script('wp-embed');
}
add_action('init', 'linew_disable_embeds');

/**
 * Comment Form Modifications
 */
function linew_comment_form_defaults($defaults) {
    $defaults['title_reply'] = __('Leave a Comment', 'linew-viral');
    $defaults['label_submit'] = __('Post Comment', 'linew-viral');
    $defaults['comment_field'] = '<p class="comment-form-comment"><label for="comment">' . __('Your Comment', 'linew-viral') . '</label><textarea id="comment" name="comment" cols="45" rows="8" maxlength="65525" required="required"></textarea></p>';
    return $defaults;
}
add_filter('comment_form_defaults', 'linew_comment_form_defaults');

/**
 * Translation filters - applied after all functions are defined
 */

// Filter to translate nav menu items to English
add_filter('wp_nav_menu_objects', function($items) {
    foreach ($items as $item) {
        $item->title = linew_translate_category($item->title, 'en');
    }
    return $items;
}, 99);

// Filter to translate nav menu item title
add_filter('nav_menu_item_title', function($title, $item, $depth, $args) {
    return linew_translate_category($title, 'en');
}, 10, 4);

// Filter get_terms to translate category names
add_filter('get_terms', function($terms, $taxonomies, $args) {
    if (in_array('category', (array)$taxonomies)) {
        foreach ($terms as $term) {
            if (is_object($term)) {
                $term->name = linew_translate_category($term->name, 'en');
            }
        }
    }
    return $terms;
}, 10, 3);

// Filter get_the_categories to translate category names
add_filter('get_the_categories', function($categories) {
    foreach ($categories as $category) {
        $category->name = linew_translate_category($category->name, 'en');
    }
    return $categories;
});

// Filter single_cat_title
add_filter('single_cat_title', function($term) {
    return linew_translate_category($term, 'en');
});
