<?php
/**
 * Linew Feed API Proxy
 * Proxies requests to Linew backend API
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Category Translation Mapping (Vietnamese -> English)
 * Dùng để hiển thị category đúng ngôn ngữ với bài viết
 */
function linew_feed_get_category_translations() {
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
    );
}

/**
 * Translate category name based on current language
 */
function linew_feed_translate_category($category_name, $lang = 'vi') {
    if ($lang !== 'en') {
        return $category_name;
    }

    $translations = linew_feed_get_category_translations();
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
 * Register REST API endpoint for feed
 */
add_action('rest_api_init', function() {
    register_rest_route('linew/v1', '/feed', array(
        'methods'  => 'GET',
        'callback' => 'linew_feed_proxy',
        'permission_callback' => '__return_true',
    ));
});

/**
 * Proxy callback - fetches articles from Linew backend
 */
function linew_feed_proxy($request) {
    $backend_url = 'http://linew-api-1:8000/api/feed';

    $params = $request->get_params();

    // Build query string
    $query_args = array(
        'offset' => isset($params['offset']) ? intval($params['offset']) : 0,
        'per_page' => isset($params['per_page']) ? intval($params['per_page']) : 12,
    );

    if (!empty($params['category'])) {
        $query_args['category'] = sanitize_text_field($params['category']);
    }

    if (!empty($params['exclude_read'])) {
        $query_args['exclude_read'] = sanitize_text_field($params['exclude_read']);
    }

    $url = add_query_arg($query_args, $backend_url);

    // Make request to backend
    $response = wp_remote_get($url, array(
        'timeout' => 30,
        'headers' => array(
            'Accept' => 'application/json',
        ),
    ));

    if (is_wp_error($response)) {
        return new WP_Error(
            'backend_error',
            'Failed to fetch feed: ' . $response->get_error_message(),
            array('status' => 502)
        );
    }

    $body = wp_remote_retrieve_body($response);
    $data = json_decode($body, true);

    if (json_last_error() !== JSON_ERROR_NONE) {
        return new WP_Error(
            'invalid_json',
            'Invalid response from backend',
            array('status' => 502)
        );
    }

    // Get language from params (default: vi)
    $lang = isset($params['lang']) ? sanitize_text_field($params['lang']) : 'vi';

    // Transform to WordPress REST API format with language support
    return transform_feed_response($data, $lang);
}

/**
 * Transform backend response to frontend format with language support
 */
function transform_feed_response($data, $lang = 'vi') {
    // Handle both array and object responses
    if (is_array($data) && isset($data['articles'])) {
        $articles = $data['articles'];
    } elseif (is_array($data)) {
        $articles = $data;
    } else {
        $articles = array();
    }

    $posts = array();
    foreach ($articles as $article) {
        // Translate category if language is English
        $category = isset($article['category']) ? $article['category'] : '';
        $category = linew_feed_translate_category($category, $lang);

        $posts[] = array(
            'id' => isset($article['id']) ? $article['id'] : '',
            'title' => isset($article['title']) ? $article['title'] : '',
            'excerpt' => isset($article['excerpt']) ? $article['excerpt'] : '',
            'thumbnail' => isset($article['thumbnail']) ? $article['thumbnail'] : '',
            'category' => $category,
            'date' => isset($article['date']) ? $article['date'] : '',
            'date_ago' => isset($article['date_ago']) ? $article['date_ago'] : '',
            'url' => isset($article['url']) ? $article['url'] : '',
            'is_new' => isset($article['is_new']) ? $article['is_new'] : false,
            'is_breaking' => isset($article['is_breaking']) ? $article['is_breaking'] : false,
            'author' => isset($article['author']) ? $article['author'] : '',
            'views' => isset($article['views']) ? intval($article['views']) : 0,
        );
    }

    // Get pagination info
    $has_more = isset($data['has_more']) ? $data['has_more'] : (count($articles) >= 12);
    $total = isset($data['total']) ? $data['total'] : count($articles);

    return array(
        'posts' => $posts,
        'shown_ids' => array_map(function($p) { return $p['id']; }, $posts),
        'has_more' => $has_more,
        'total' => $total,
        'server_time' => current_time('c'),
    );
}
