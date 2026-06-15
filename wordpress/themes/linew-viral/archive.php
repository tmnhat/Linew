<?php
/**
 * Archive Template (Category, Tag, Author, Date) - NYTimes Style
 *
 * @package Linew_Viral
 */

if (!defined('ABSPATH')) {
    exit;
}

get_header();

// Get archive information
$archive_title = '';
$archive_description = '';

if (is_category()) {
    $archive_title = single_cat_title('', false);
    $archive_description = category_description();
} elseif (is_tag()) {
    $archive_title = single_tag_title('', false);
    $archive_description = tag_description();
} elseif (is_author()) {
    $archive_title = get_the_author();
    $archive_description = get_the_author_meta('description');
} elseif (is_year()) {
    $archive_title = get_the_date('Y');
    $archive_description = 'Posts from ' . get_the_date('Y');
} elseif (is_month()) {
    $archive_title = get_the_date('F Y');
    $archive_description = 'Posts from ' . get_the_date('F Y');
} elseif (is_day()) {
    $archive_title = get_the_date();
    $archive_description = 'Posts from ' . get_the_date();
}
?>

<!-- Archive Header -->
<section class="lv-archive-header">
    <div class="lv-container">
        <?php if (is_category()) : ?>
        <span class="lv-archive-label">Category</span>
        <?php elseif (is_tag()) : ?>
        <span class="lv-archive-label">Tag</span>
        <?php elseif (is_author()) : ?>
        <span class="lv-archive-label">Author</span>
        <div class="lv-archive-avatar">
            <?php echo get_avatar(get_queried_object_id(), 80, '', '', array('class' => 'lv-archive-avatar-img')); ?>
        </div>
        <?php elseif (is_year() || is_month() || is_day()) : ?>
        <span class="lv-archive-label">Archive</span>
        <?php endif; ?>

        <h1 class="lv-archive-title"><?php echo esc_html($archive_title); ?></h1>

        <?php if ($archive_description) : ?>
        <p class="lv-archive-description"><?php echo wp_kses_post($archive_description); ?></p>
        <?php endif; ?>
    </div>
</section>

<!-- Archive Content -->
<section class="lv-archive-content">
    <div class="lv-container">
        <?php if (have_posts()) : ?>

        <!-- Featured Post -->
        <?php if (have_posts()) : the_post(); ?>
        <?php
            $category = linew_get_category($post->ID);
            $featured_image = linew_get_featured_image('linew-hero', $post->ID);
        ?>
        <article class="lv-archive-featured">
            <a href="<?php the_permalink(); ?>" class="lv-archive-featured-image">
                <?php if ($featured_image) : ?>
                <img src="<?php echo esc_url($featured_image); ?>" alt="<?php the_title_attribute(); ?>">
                <?php else : ?>
                <div class="lv-archive-featured-placeholder"></div>
                <?php endif; ?>
            </a>
            <div class="lv-archive-featured-content">
                <?php if ($category) : ?>
                <a href="<?php echo esc_url($category['url']); ?>" class="lv-archive-category">
                    <?php echo esc_html($category['name']); ?>
                </a>
                <?php endif; ?>
                <h2 class="lv-archive-featured-title">
                    <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                </h2>
                <p class="lv-archive-featured-excerpt">
                    <?php echo esc_html(wp_trim_words(get_the_excerpt(), 30)); ?>
                </p>
                <div class="lv-archive-meta">
                    <span class="lv-archive-author"><?php the_author(); ?></span>
                    <span class="lv-archive-divider">|</span>
                    <time><?php echo linew_format_date(); ?></time>
                    <span class="lv-archive-divider">|</span>
                    <span><?php echo linew_reading_time($post->ID); ?></span>
                </div>
            </div>
        </article>
        <?php rewind_posts(); endif; ?>

        <!-- Section Header -->
        <div class="lv-section-header">
            <h2 class="lv-section-title">More Stories</h2>
        </div>

        <!-- Grid of Posts -->
        <div class="lv-archive-grid">
            <?php
            $post_count = 0;
            while (have_posts() && $post_count < 8) : the_post();
            $post_count++;
            ?>
            <?php
                $cat = linew_get_category($post->ID);
                $thumb = linew_get_featured_image('linew-medium', $post->ID);
            ?>
            <article class="lv-news-card">
                <a href="<?php the_permalink(); ?>" class="lv-news-card-image">
                    <?php if ($thumb) : ?>
                    <img src="<?php echo esc_url($thumb); ?>" alt="<?php the_title_attribute(); ?>" loading="lazy">
                    <?php else : ?>
                    <div class="lv-news-card-placeholder"></div>
                    <?php endif; ?>
                    <?php if ($cat) : ?>
                    <span class="lv-card-category"><?php echo esc_html($cat['name']); ?></span>
                    <?php endif; ?>
                </a>
                <div class="lv-news-card-body">
                    <h3 class="lv-news-card-title">
                        <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                    </h3>
                    <p class="lv-news-card-excerpt"><?php echo esc_html(wp_trim_words(get_the_excerpt(), 15)); ?></p>
                    <div class="lv-news-card-meta">
                        <span class="lv-card-author"><?php the_author(); ?></span>
                        <span class="lv-card-date"><?php echo linew_format_date(); ?></span>
                    </div>
                </div>
            </article>
            <?php endwhile; ?>
        </div>

        <!-- Pagination -->
        <?php
        the_posts_pagination(array(
            'mid_size'  => 2,
            'prev_text' => '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg> Previous',
            'next_text' => 'Next <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>',
        ));
        ?>

        <?php else : ?>
        <!-- No Results -->
        <div class="lv-no-results">
            <div class="lv-no-results-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="M21 21l-4.35-4.35"/>
                </svg>
            </div>
            <h2>No posts found</h2>
            <p>
                <?php
                if (is_category()) {
                    echo 'There are no posts in this category yet.';
                } elseif (is_tag()) {
                    echo 'There are no posts with this tag yet.';
                } elseif (is_author()) {
                    echo 'This author has not published any posts yet.';
                } else {
                    echo 'Try a different search or browse our latest articles.';
                }
                ?>
            </p>
            <a href="<?php echo esc_url(home_url('/')); ?>" class="lv-cta-button">
                Go to Homepage
            </a>
        </div>
        <?php endif; ?>
    </div>
</section>

<?php get_footer(); ?>
