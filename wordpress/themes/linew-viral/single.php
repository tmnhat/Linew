<?php
/**
 * Single Post Template - NYTimes Style Redesign
 *
 * @package Linew_Viral
 */

if (!defined('ABSPATH')) {
    exit;
}

get_header();

while (have_posts()) :
    the_post();

    $category = linew_get_category($post->ID);
    $featured_image = linew_get_featured_image('large', $post->ID);
    $related_posts = linew_get_related_posts($post->ID, 3);
?>

<!-- Article -->
<article class="lv-article">

    <!-- Article Header -->
    <header class="lv-article-header">
        <div class="lv-container">
            <?php if ($category) : ?>
            <div class="lv-article-category">
                <a href="<?php echo esc_url($category['url']); ?>" class="lv-category-link">
                    <?php echo esc_html($category['name']); ?>
                </a>
            </div>
            <?php endif; ?>

            <h1 class="lv-article-title"><?php the_title(); ?></h1>

            <?php if (has_excerpt()) : ?>
            <p class="lv-article-excerpt"><?php the_excerpt(); ?></p>
            <?php endif; ?>

            <div class="lv-article-meta">
                <div class="lv-article-author-info">
                    <span class="lv-article-byline">By</span>
                    <a href="<?php echo get_author_posts_url(get_the_author_meta('ID')); ?>" class="lv-article-author">
                        <?php the_author(); ?>
                    </a>
                </div>
                <span class="lv-article-divider">|</span>
                <time class="lv-article-date" datetime="<?php echo get_the_date('c'); ?>">
                    <?php echo linew_format_date(); ?>
                </time>
                <span class="lv-article-divider">|</span>
                <span class="lv-article-reading">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 6v6l4 2"/>
                    </svg>
                    <?php echo linew_reading_time($post->ID); ?>
                </span>
            </div>
        </div>
    </header>

    <!-- Article Actions Bar -->
    <div class="lv-article-actions">
        <div class="lv-container">
            <div class="lv-article-actions-inner">
                <div class="lv-share-buttons">
                    <span class="lv-share-label">Share:</span>
                    <a href="https://www.facebook.com/sharer/sharer.php?u=<?php echo urlencode(get_permalink()); ?>"
                       target="_blank" rel="noopener noreferrer" class="lv-share-btn lv-share-facebook" aria-label="Share on Facebook">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>
                        </svg>
                    </a>
                    <a href="https://twitter.com/intent/tweet?url=<?php echo urlencode(get_permalink()); ?>&text=<?php echo urlencode(get_the_title()); ?>"
                       target="_blank" rel="noopener noreferrer" class="lv-share-btn lv-share-twitter" aria-label="Share on Twitter">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                        </svg>
                    </a>
                    <a href="https://www.linkedin.com/shareArticle?mini=true&url=<?php echo urlencode(get_permalink()); ?>&title=<?php echo urlencode(get_the_title()); ?>"
                       target="_blank" rel="noopener noreferrer" class="lv-share-btn lv-share-linkedin" aria-label="Share on LinkedIn">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>
                            <rect x="2" y="9" width="4" height="12"/>
                            <circle cx="4" cy="4" r="2"/>
                        </svg>
                    </a>
                    <a href="mailto:?subject=<?php echo urlencode(get_the_title()); ?>&body=<?php echo urlencode(get_permalink()); ?>"
                       class="lv-share-btn lv-share-email" aria-label="Share via Email">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                            <polyline points="22,6 12,13 2,6"/>
                        </svg>
                    </a>
                    <button class="lv-share-btn lv-share-copy" aria-label="Copy link" onclick="navigator.clipboard.writeText('<?php echo esc_url(get_permalink()); ?>')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                        </svg>
                    </button>
                </div>
                <div class="lv-bookmark-btn">
                    <button class="lv-bookmark" aria-label="Bookmark this article">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                        </svg>
                        <span>Save</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Featured Image - Use linew_get_featured_image() for external URL support -->
    <?php 
    $featured_img_url = linew_get_featured_image('large', $post->ID);
    if ($featured_img_url) : 
    ?>
    <div class="lv-article-featured">
        <div class="lv-article-featured-wrap">
            <img src="<?php echo esc_url($featured_img_url); ?>" 
                 alt="<?php echo esc_attr(get_the_title()); ?>" 
                 class="lv-featured-img" />
        </div>
    </div>
    <?php endif; ?>

    <!-- Article Body -->
    <div class="lv-article-body">
        <div class="lv-container">
            <div class="lv-article-content">
                <?php the_content(); ?>
            </div>
        </div>
    </div>

    <!-- Article Tags -->
    <?php
    $tags = get_the_tags();
    if ($tags) :
    ?>
    <div class="lv-article-tags">
        <div class="lv-container">
            <div class="lv-tags-wrap">
                <strong class="lv-tags-label">Topics:</strong>
                <?php foreach ($tags as $tag) : ?>
                <a href="<?php echo esc_url(get_tag_link($tag->term_id)); ?>" class="lv-tag" rel="tag">
                    <?php echo esc_html($tag->name); ?>
                </a>
                <?php endforeach; ?>
            </div>
        </div>
    </div>
    <?php endif; ?>

    <!-- Author Bio -->
    <div class="lv-author-bio">
        <div class="lv-container">
            <div class="lv-author-card">
                <div class="lv-author-avatar">
                    <?php echo get_avatar(get_the_author_meta('ID'), 96, '', '', array('class' => 'lv-author-img')); ?>
                </div>
                <div class="lv-author-info">
                    <div class="lv-author-header">
                        <div>
                            <span class="lv-author-label">Written by</span>
                            <a href="<?php echo get_author_posts_url(get_the_author_meta('ID')); ?>" class="lv-author-name">
                                <?php the_author(); ?>
                            </a>
                        </div>
                        <div class="lv-author-social">
                            <a href="#" class="lv-author-social-link" aria-label="Twitter">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                </svg>
                            </a>
                        </div>
                    </div>
                    <p class="lv-author-bio-text">
                        <?php the_author_meta('description') ?: 'Staff Writer at Linew'; ?>
                    </p>
                    <a href="<?php echo get_author_posts_url(get_the_author_meta('ID')); ?>" class="lv-author-link">
                        More articles by <?php the_author(); ?> →
                    </a>
                </div>
            </div>
        </div>
    </div>

</article>

<!-- Related Posts -->
<?php if (!empty($related_posts)) : ?>
<section class="lv-related">
    <div class="lv-container">
        <h2 class="lv-related-title">
            <span>More in <?php echo esc_html($category['name'] ?? 'News'); ?></span>
        </h2>
        <div class="lv-related-grid">
            <?php foreach ($related_posts as $post) : setup_postdata($post); ?>
            <?php
                $related_image = linew_get_featured_image('linew-medium', $post->ID);
                $related_category = linew_get_category($post->ID);
            ?>
            <article class="lv-related-card">
                <a href="<?php the_permalink(); ?>" class="lv-related-image">
                    <?php if ($related_image) : ?>
                    <img src="<?php echo esc_url($related_image); ?>" alt="<?php the_title_attribute(); ?>" loading="lazy">
                    <?php else : ?>
                    <div class="lv-related-placeholder"></div>
                    <?php endif; ?>
                </a>
                <div class="lv-related-content">
                    <?php if ($related_category) : ?>
                    <a href="<?php echo esc_url($related_category['url']); ?>" class="lv-related-category">
                        <?php echo esc_html($related_category['name']); ?>
                    </a>
                    <?php endif; ?>
                    <h3>
                        <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                    </h3>
                    <div class="lv-related-meta">
                        <span><?php echo linew_format_date(); ?></span>
                        <span><?php echo linew_reading_time($post->ID); ?></span>
                    </div>
                </div>
            </article>
            <?php wp_reset_postdata(); endforeach; ?>
        </div>
    </div>
</section>
<?php endif; ?>

<!-- Comments -->
<section class="lv-comments-section">
    <div class="lv-container">
        <h2 class="lv-comments-title">Comments</h2>
        <?php
        if (comments_open() || get_comments_number()) :
            comments_template();
        endif;
        ?>
    </div>
</section>

<?php
endwhile;
get_footer();
