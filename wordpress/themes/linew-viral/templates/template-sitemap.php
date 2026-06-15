<?php
/**
 * Template Name: Sitemap
 * Description: HTML Sitemap page for visitors
 */

if (!defined('ABSPATH')) {
    exit;
}

get_header();
?>

<section class="lv-page-header lv-sitemap-header">
    <div class="lv-container">
        <h1 class="lv-page-title">Sitemap</h1>
        <p class="lv-page-subtitle">Browse all pages and categories on Litimez</p>
    </div>
</section>

<section class="lv-sitemap-content">
    <div class="lv-container">
        <div class="lv-sitemap-grid">
            
            <!-- Static Pages -->
            <div class="lv-sitemap-section">
                <h2 class="lv-sitemap-section-title">Pages</h2>
                <ul class="lv-sitemap-list">
                    <li><a href="<?php echo esc_url(home_url('/')); ?>">Home</a></li>
                    <li><a href="<?php echo esc_url(home_url('/about/')); ?>">About Us</a></li>
                    <li><a href="<?php echo esc_url(home_url('/contact/')); ?>">Contact Us</a></li>
                </ul>
            </div>

            <!-- Legal Pages -->
            <div class="lv-sitemap-section">
                <h2 class="lv-sitemap-section-title">Legal</h2>
                <ul class="lv-sitemap-list">
                    <li><a href="<?php echo esc_url(home_url('/terms-of-service/')); ?>">Terms of Service</a></li>
                    <li><a href="<?php echo esc_url(home_url('/privacy-policy/')); ?>">Privacy Policy</a></li>
                    <li><a href="<?php echo esc_url(home_url('/dmca-policy/')); ?>">DMCA Policy</a></li>
                    <li><a href="<?php echo esc_url(home_url('/cookie-policy/')); ?>">Cookie Policy</a></li>
                    <li><a href="<?php echo esc_url(home_url('/financial-disclaimer/')); ?>">Financial Disclaimer</a></li>
                    <li><a href="<?php echo esc_url(home_url('/ai-disclosure/')); ?>">AI Content Disclosure</a></li>
                </ul>
            </div>

            <!-- Categories -->
            <div class="lv-sitemap-section lv-sitemap-section-full">
                <h2 class="lv-sitemap-section-title">Categories</h2>
                <div class="lv-sitemap-categories">
                    <?php
                    $categories = get_categories(array(
                        'hide_empty' => false,
                        'exclude' => array(1), // Exclude Uncategorized
                    ));
                    
                    $category_links = array(
                        'world' => 'World News',
                        'politics' => 'Politics',
                        'finance' => 'Finance & Markets',
                        'technology' => 'Technology',
                        'entertainment' => 'Entertainment',
                        'health' => 'Health',
                        'sports' => 'Sports',
                        'education' => 'Education',
                        'science' => 'Science',
                        'business' => 'Business',
                    );
                    
                    foreach ($category_links as $slug => $name) :
                        $count = 0;
                        foreach ($categories as $cat) {
                            if ($cat->slug === $slug) {
                                $count = $cat->count;
                                break;
                            }
                        }
                    ?>
                    <a href="<?php echo esc_url(home_url('/category/' . $slug . '/')); ?>" class="lv-sitemap-category-card">
                        <span class="lv-category-name"><?php echo esc_html($name); ?></span>
                        <span class="lv-category-count"><?php echo number_format($count); ?> articles</span>
                    </a>
                    <?php endforeach; ?>
                </div>
            </div>

        </div>
    </div>
</section>

<style>
.lv-sitemap-header {
    background: linear-gradient(135deg, var(--lv-primary) 0%, var(--lv-gray-800) 100%);
    padding: 60px 0 40px;
    text-align: center;
}

.lv-page-subtitle {
    color: var(--lv-gray-400);
    margin-top: 8px;
    font-size: 1.125rem;
}

.lv-sitemap-content {
    padding: 60px 0;
    background: var(--lv-white);
}

.lv-sitemap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 40px;
    max-width: 1200px;
    margin: 0 auto;
}

.lv-sitemap-section-full {
    grid-column: 1 / -1;
}

.lv-sitemap-section-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--lv-primary);
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 3px solid var(--lv-accent);
}

.lv-sitemap-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.lv-sitemap-list li {
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--lv-gray-100);
}

.lv-sitemap-list li:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.lv-sitemap-list a {
    color: var(--lv-text-primary);
    text-decoration: none;
    font-size: 1.0625rem;
    transition: color 0.2s ease;
}

.lv-sitemap-list a:hover {
    color: var(--lv-accent);
}

.lv-sitemap-categories {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
}

.lv-sitemap-category-card {
    display: flex;
    flex-direction: column;
    padding: 20px;
    background: var(--lv-gray-50);
    border-radius: 12px;
    text-decoration: none;
    transition: all 0.3s ease;
    border: 2px solid transparent;
}

.lv-sitemap-category-card:hover {
    background: var(--lv-white);
    border-color: var(--lv-accent);
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.1);
}

.lv-category-name {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--lv-primary);
    margin-bottom: 8px;
}

.lv-category-count {
    font-size: 0.875rem;
    color: var(--lv-gray-500);
}

@media (max-width: 768px) {
    .lv-sitemap-grid {
        grid-template-columns: 1fr;
    }
    
    .lv-sitemap-categories {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 480px) {
    .lv-sitemap-categories {
        grid-template-columns: 1fr;
    }
}
</style>

<?php get_footer(); ?>
