<?php
/**
 * Search Results Template
 *
 * @package Linew_Viral
 */

if (!defined('ABSPATH')) {
    exit;
}

get_header();

$search_query = get_search_query();
?>

<!-- Search Header -->
<section style="background: var(--lv-primary); color: var(--lv-white); padding: 48px 0; text-align: center;">
    <div class="lv-container">
        <p style="font-family: var(--lv-font-sans); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--lv-gray-400); margin-bottom: 8px;">
            Search Results
        </p>
        <h1 style="font-size: 2rem; font-weight: 800; margin-bottom: 16px;">
            "<?php echo esc_html($search_query); ?>"
        </h1>
        <?php
        global $wp_query;
        $results_count = $wp_query->found_posts;
        ?>
        <p style="font-size: 1rem; color: var(--lv-gray-300);">
            Found <?php echo number_format($results_count); ?> <?php echo $results_count == 1 ? 'result' : 'results'; ?>
        </p>
    </div>
</section>

<!-- Search Results -->
<section class="lv-news-section">
    <div class="lv-container">
        <?php if (have_posts()) : ?>

        <!-- Search Form (for refinement) -->
        <div style="margin-bottom: 32px;">
            <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>" style="display: flex; gap: 12px; max-width: 600px; margin: 0 auto;">
                <input type="search" name="s" value="<?php echo esc_attr($search_query); ?>" placeholder="Search articles..." style="flex: 1; padding: 16px; border: 1px solid var(--lv-gray-300); border-radius: 4px; font-size: 1rem; font-family: var(--lv-font-sans);">
                <button type="submit" style="padding: 16px 24px; background: var(--lv-accent); color: white; border: none; border-radius: 4px; font-family: var(--lv-font-sans); font-weight: 600; cursor: pointer;">
                    Search
                </button>
            </form>
        </div>

        <!-- Results List -->
        <div class="lv-article-list" style="max-width: 800px; margin: 0 auto;">
            <?php while (have_posts()) : the_post(); ?>
            <?php
                $category = linew_get_category($post->ID);
                $thumb = linew_get_featured_image('linew-small', $post->ID);
            ?>
            <article style="display: flex; gap: 24px; padding: 24px 0; border-bottom: 1px solid var(--lv-gray-200);">
                <?php if ($thumb) : ?>
                <div style="flex-shrink: 0; width: 200px;">
                    <a href="<?php the_permalink(); ?>">
                        <img src="<?php echo esc_url($thumb); ?>" alt="<?php the_title_attribute(); ?>" style="width: 200px; height: 130px; object-fit: cover; border-radius: 4px;">
                    </a>
                </div>
                <?php endif; ?>
                <div style="flex: 1; min-width: 0;">
                    <?php if ($category) : ?>
                    <a href="<?php echo esc_url($category['url']); ?>" class="lv-category" style="margin-bottom: 8px; display: inline-block;">
                        <?php echo esc_html($category['name']); ?>
                    </a>
                    <?php endif; ?>
                    <h2 style="font-size: 1.375rem; line-height: 1.3; margin-bottom: 8px;">
                        <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                    </h2>
                    <p style="color: var(--lv-text-muted); font-size: 0.9375rem; line-height: 1.6; margin-bottom: 12px;">
                        <?php echo esc_html(wp_trim_words(get_the_excerpt(), 25)); ?>
                    </p>
                    <div style="font-family: var(--lv-font-sans); font-size: 0.8125rem; color: var(--lv-gray-500);">
                        <span style="font-weight: 600; color: var(--lv-text-primary);"><?php the_author(); ?></span>
                        &bull;
                        <?php echo linew_format_date(); ?>
                        &bull;
                        <?php echo linew_reading_time($post->ID); ?>
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
            'class'     => 'lv-pagination',
        ));
        ?>

        <?php else : ?>
        <!-- No Results -->
        <div style="text-align: center; padding: 64px 0; max-width: 600px; margin: 0 auto;">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--lv-gray-300)" stroke-width="1.5" style="margin: 0 auto 24px;">
                <circle cx="11" cy="11" r="8"/>
                <path d="M21 21l-4.35-4.35"/>
            </svg>
            <h2 style="font-size: 1.5rem; margin-bottom: 16px;">No results found</h2>
            <p style="color: var(--lv-text-muted); margin-bottom: 24px;">
                We couldn't find any articles matching "<?php echo esc_html($search_query); ?>". Try different keywords or browse our categories.
            </p>

            <!-- Search Again -->
            <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>" style="display: flex; gap: 12px; margin-bottom: 32px;">
                <input type="search" name="s" placeholder="Try another search..." style="flex: 1; padding: 14px; border: 1px solid var(--lv-gray-300); border-radius: 4px; font-size: 1rem; font-family: var(--lv-font-sans);">
                <button type="submit" style="padding: 14px 24px; background: var(--lv-accent); color: white; border: none; border-radius: 4px; font-family: var(--lv-font-sans); font-weight: 600; cursor: pointer;">
                    Search
                </button>
            </form>

            <!-- Browse Categories -->
            <h3 style="font-family: var(--lv-font-sans); font-size: 0.875rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 16px;">Browse Categories</h3>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 8px;">
                <?php
                $categories = get_categories(array('hide_empty' => true, 'number' => 8));
                foreach ($categories as $category) {
                    printf(
                        '<a href="%s" style="display: inline-block; padding: 8px 16px; background: var(--lv-gray-100); border-radius: 4px; font-family: var(--lv-font-sans); font-size: 0.875rem; color: var(--lv-text-primary);">%s</a>',
                        esc_url(get_category_link($category->term_id)),
                        esc_html($category->name)
                    );
                }
                ?>
            </div>
        </div>
        <?php endif; ?>
    </div>
</section>

<?php get_footer(); ?>
