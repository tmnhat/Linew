<?php
/**
 * 404 Page Template
 *
 * @package Linew_Viral
 */

if (!defined('ABSPATH')) {
    exit;
}

get_header();
?>

<!-- 404 Header -->
<section style="background: var(--lv-primary); color: var(--lv-white); padding: 80px 0; text-align: center;">
    <div class="lv-container">
        <div style="font-family: var(--lv-font-sans); font-size: 8rem; font-weight: 900; line-height: 1; margin-bottom: 16px; color: var(--lv-accent);">
            404
        </div>
        <h1 style="font-size: 2rem; font-weight: 700; margin-bottom: 16px;">
            Page Not Found
        </h1>
        <p style="font-size: 1.125rem; color: var(--lv-gray-400); max-width: 500px; margin: 0 auto;">
            The page you're looking for doesn't exist or has been moved. Let's get you back on track.
        </p>
    </div>
</section>

<!-- Search & Recent Posts -->
<section class="lv-news-section">
    <div class="lv-container">
        <div class="lv-two-col">
            <!-- Search Box -->
            <div class="lv-main-content">
                <h3 class="section-title">Search</h3>
                <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>" style="display: flex; gap: 12px; margin-bottom: 40px;">
                    <input type="search" name="s" placeholder="Search articles..." style="flex: 1; padding: 16px; border: 1px solid var(--lv-gray-300); border-radius: 4px; font-size: 1rem; font-family: var(--lv-font-sans);">
                    <button type="submit" style="padding: 16px 32px; background: var(--lv-accent); color: white; border: none; border-radius: 4px; font-family: var(--lv-font-sans); font-weight: 600; cursor: pointer;">
                        Search
                    </button>
                </form>

                <h3 class="section-title">Browse Categories</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 40px;">
                    <?php
                    $categories = get_categories(array('hide_empty' => true, 'number' => 12));
                    foreach ($categories as $category) {
                        printf(
                            '<a href="%s" style="display: inline-block; padding: 10px 20px; background: var(--lv-gray-100); border-radius: 4px; font-family: var(--lv-font-sans); font-size: 0.875rem; color: var(--lv-text-primary); transition: all 0.2s;">%s <span style="color: var(--lv-gray-500);">(%d)</span></a>',
                            esc_url(get_category_link($category->term_id)),
                            esc_html($category->name),
                            $category->count
                        );
                    }
                    ?>
                </div>
            </div>

            <!-- Recent Posts -->
            <aside class="lv-sidebar">
                <div class="lv-widget">
                    <h3 class="lv-widget-title">Recent Articles</h3>
                    <ul style="list-style: none;">
                        <?php
                        $recent_posts = get_posts(array(
                            'posts_per_page' => 5,
                            'post_status'    => 'publish',
                        ));
                        foreach ($recent_posts as $post) :
                        ?>
                        <li style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--lv-gray-200);">
                            <h4 style="font-size: 0.9375rem; font-weight: 700; line-height: 1.3; margin-bottom: 4px;">
                                <a href="<?php echo esc_url(get_permalink($post->ID)); ?>"><?php echo esc_html($post->post_title); ?></a>
                            </h4>
                            <span style="font-family: var(--lv-font-sans); font-size: 0.6875rem; color: var(--lv-gray-500);">
                                <?php echo linew_format_date(get_post_time('Y-m-d', false, $post->ID)); ?>
                            </span>
                        </li>
                        <?php endforeach; wp_reset_postdata(); ?>
                    </ul>
                </div>
            </aside>
        </div>
    </div>
</section>

<!-- CTA Section -->
<section style="background: var(--lv-off-white); padding: 48px 0; text-align: center;">
    <div class="lv-container">
        <h2 style="font-size: 1.5rem; margin-bottom: 16px;">Need Help?</h2>
        <p style="color: var(--lv-text-muted); margin-bottom: 24px;">
            Try browsing our categories or return to the homepage.
        </p>
        <div style="display: flex; justify-content: center; gap: 16px; flex-wrap: wrap;">
            <a href="<?php echo esc_url(home_url('/')); ?>" style="display: inline-block; padding: 14px 28px; background: var(--lv-accent); color: white; border-radius: 4px; font-family: var(--lv-font-sans); font-weight: 600;">
                Go to Homepage
            </a>
            <a href="<?php echo admin_url(); ?>" style="display: inline-block; padding: 14px 28px; background: var(--lv-gray-700); color: white; border-radius: 4px; font-family: var(--lv-font-sans); font-weight: 600;">
                Admin Dashboard
            </a>
        </div>
    </div>
</section>

<?php get_footer(); ?>
