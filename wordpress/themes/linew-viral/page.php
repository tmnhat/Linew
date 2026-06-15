<?php
/**
 * Page Template - Static Pages
 *
 * @package Linew_Viral
 */

if (!defined('ABSPATH')) {
    exit;
}

get_header();
?>

<!-- Page Header -->
<section class="lv-page-header">
    <div class="lv-container">
        <h1 class="lv-page-title"><?php the_title(); ?></h1>
    </div>
</section>

<!-- Page Content -->
<section class="lv-page-content">
    <div class="lv-container">
        <div class="lv-page-wrapper">
            <?php
            while (have_posts()) : the_post();
                the_content();
            endwhile;
            ?>
        </div>
    </div>
</section>

<!-- Related Content (Optional) -->
<?php
// Only show related posts on certain pages
$show_related = apply_filters('linew_show_related_posts', false);
if ($show_related) :
?>
<section class="lv-related-posts">
    <div class="lv-container">
        <h2>Related Articles</h2>
        <div class="lv-masonry-grid">
            <?php
            $related = get_posts(array(
                'posts_per_page' => 6,
                'post_status' => 'publish',
                'orderby' => 'rand',
            ));
            foreach ($related as $post) :
                setup_postdata($post);
            ?>
            <article class="lv-feed-card">
                <a href="<?php the_permalink(); ?>">
                    <?php if (has_post_thumbnail()) : ?>
                    <div class="lv-feed-card-image">
                        <?php the_post_thumbnail('linew-medium'); ?>
                    </div>
                    <?php endif; ?>
                    <div class="lv-feed-card-body">
                        <h3><?php the_title(); ?></h3>
                    </div>
                </a>
            </article>
            <?php endforeach; wp_reset_postdata(); ?>
        </div>
    </div>
</section>
<?php endif; ?>

<?php get_footer(); ?>
