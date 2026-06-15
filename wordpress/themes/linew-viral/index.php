<?php
/**
 * Main Index Template - Masonry Infinite Scroll Feed
 *
 * @package Linew_Viral
 */

if (!defined('ABSPATH')) {
    exit;
}

get_header();

// Check if masonry feed should be shown
$show_masonry_feed = apply_filters('linew_show_masonry_feed', true);

// Check if prediction widget should be shown
$show_prediction = apply_filters('linew_show_prediction_widget', true);
?>

<!-- ================================================
     HERO SECTION - Featured Post (Optional)
     ================================================ -->
<section class="lv-hero-section">
    <div class="lv-container">
        <?php
        $featured_posts = get_posts(array(
            'posts_per_page' => 1,
            'post_status'   => 'publish',
            'orderby'       => 'date',
            'order'         => 'DESC',
        ));
        ?>
        <?php if (!empty($featured_posts)) : ?>
        <?php foreach ($featured_posts as $post) : setup_postdata($post); ?>
        <?php
            $category = linew_get_category($post->ID);
            $featured_image = linew_get_featured_image('linew-hero', $post->ID);
        ?>
        <article class="lv-hero-card">
            <a href="<?php the_permalink(); ?>" class="lv-hero-link">
                <?php if ($featured_image) : ?>
                <div class="lv-hero-image" style="background-image: url('<?php echo esc_url($featured_image); ?>')">
                    <div class="lv-hero-overlay"></div>
                <?php else : ?>
                <div class="lv-hero-image lv-hero-placeholder">
                    <div class="lv-hero-overlay"></div>
                <?php endif; ?>
                    <div class="lv-hero-content">
                        <?php if ($category) : ?>
                        <span class="lv-hero-category"><?php echo esc_html($category['name']); ?></span>
                        <?php endif; ?>
                        <h1 class="lv-hero-title"><?php the_title(); ?></h1>
                        <p class="lv-hero-excerpt"><?php echo esc_html(wp_trim_words(get_the_excerpt(), 30)); ?></p>
                        <div class="lv-hero-meta">
                            <span class="lv-hero-author"><?php the_author(); ?></span>
                            <span class="lv-hero-date"><?php echo linew_format_date(); ?></span>
                        </div>
                    </div>
                </div>
            </a>
        </article>
        <?php wp_reset_postdata(); endforeach; ?>
        <?php endif; ?>
    </div>
</section>

<!-- ================================================
     PREDICTION WIDGET
     ================================================ -->
<?php if ($show_prediction) : ?>
<div id="lv-prediction-section" style="max-width:720px; margin:24px auto; padding:0 16px;">
    <!-- Iframe wrapper with improved loading and error states -->
    <div id="lv-prediction-wrapper">
        <!-- Loading skeleton -->
        <div id="lv-prediction-loading" class="lv-prediction-loading" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 12px; padding: 20px; min-height: 400px;">
            <div style="text-align: center; padding: 40px 0;">
                <div style="width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.1); border-top-color: #10b981; border-radius: 50%; animation: lv-spin 0.8s linear infinite; margin: 0 auto;"></div>
                <p style="color: #64748b; margin-top: 16px; font-size: 14px;">Loading Litimez Analysis...</p>
            </div>
            <!-- Skeleton elements -->
            <div style="padding: 16px;">
                <div style="height: 24px; width: 60%; background: rgba(255,255,255,0.05); border-radius: 6px; margin-bottom: 16px;"></div>
                <div style="height: 80px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 12px;"></div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <div style="height: 80px; background: rgba(255,255,255,0.05); border-radius: 8px;"></div>
                    <div style="height: 80px; background: rgba(255,255,255,0.05); border-radius: 8px;"></div>
                </div>
            </div>
        </div>
        
        <!-- Error state -->
        <div id="lv-prediction-error" class="lv-prediction-error" style="display: none; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 12px; padding: 40px 20px; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 12px;">⚠️</div>
            <p id="lv-prediction-error-msg" style="color: #f87171; margin-bottom: 16px; font-size: 14px;">Unable to load widget</p>
            <button onclick="LinewWidget.reload()" style="padding: 10px 24px; background: #334155; color: #e2e8f0; border: 1px solid #475569; border-radius: 8px; cursor: pointer; font-size: 14px;">Retry</button>
        </div>
        
        <!-- Iframe -->
        <iframe
            id="linews-iframe"
            src="/api/widget/prediction"
            width="100%"
            height="500"
            frameborder="0"
            style="border:none; border-radius: 12px; overflow:hidden; display: none; background: transparent;"
            loading="lazy"
            scrolling="no"
            title="Litimez Analysis"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups">
        </iframe>
    </div>
    
    <style>
        @keyframes lv-spin { to { transform: rotate(360deg); } }
        #lv-prediction-wrapper iframe { transition: height 0.3s ease; }
    </style>
    
    <script>
    (function() {
        'use strict';
        
        var wrapper = document.getElementById('lv-prediction-wrapper');
        var iframe = document.getElementById('linews-iframe');
        var loading = document.getElementById('lv-prediction-loading');
        var errorEl = document.getElementById('lv-prediction-error');
        var errorMsg = document.getElementById('lv-prediction-error-msg');
        
        var heightReceived = false;
        var retryCount = 0;
        var maxRetries = 3;
        
        // Listen for height messages from iframe
        window.addEventListener('message', function(e) {
            if (!e.data || e.data.type !== 'linews-widget-height') return;
            
            if (e.data.height > 0 && e.data.height < 2000) {
                // Valid height received
                heightReceived = true;
                iframe.style.height = Math.min(e.data.height + 30, 900) + 'px';
                
                // Show iframe, hide loading
                if (loading) loading.style.display = 'none';
                if (errorEl) errorEl.style.display = 'none';
                iframe.style.display = 'block';
            }
        });
        
        // Iframe load event
        iframe.addEventListener('load', function() {
            // Give iframe time to load content and report height
            setTimeout(function() {
                if (!heightReceived && retryCount < maxRetries) {
                    retryCount++;
                    console.log('Height not received, retry ' + retryCount);
                    // Force iframe reload
                    iframe.src = iframe.src;
                }
            }, 3000);
        });
        
        // Iframe error handling
        iframe.addEventListener('error', function() {
            showError('Unable to connect to server');
        });
        
        function showError(msg) {
            if (loading) loading.style.display = 'none';
            if (iframe) iframe.style.display = 'none';
            if (errorEl) {
                errorEl.style.display = 'block';
                if (errorMsg) errorMsg.textContent = msg;
            }
        }
        
        // Fallback: show iframe after timeout anyway
        setTimeout(function() {
            if (iframe.style.display === 'none' && !heightReceived) {
                // Iframe exists, just show it with default height
                if (loading) loading.style.display = 'none';
                iframe.style.display = 'block';
                console.log('Fallback: Showing iframe after timeout');
            }
        }, 8000);
        
        // Global reload function
        window.LinewWidget = {
            reload: function() {
                heightReceived = false;
                retryCount = 0;
                if (loading) loading.style.display = 'block';
                if (errorEl) errorEl.style.display = 'none';
                iframe.style.display = 'none';
                iframe.src = iframe.src;
            }
        };
    })();
    </script>
</div>
<?php endif; ?>

<!-- ================================================
     MARKET TICKER
     ================================================ -->
<section class="lv-ticker-section">
    <div class="lv-container">
        <div class="lv-ticker-wrapper">
            <div class="lv-ticker-label">
                <span class="lv-ticker-icon">📊</span>
                <span>Markets</span>
            </div>
            <div class="lv-ticker-track">
                <div class="lv-ticker-items">
                    <div class="lv-ticker-item">
                        <span class="lv-ticker-symbol">BTC</span>
                        <span class="lv-ticker-price" id="ticker-btc">Loading...</span>
                        <span class="lv-ticker-change positive" id="ticker-btc-change">+0.00%</span>
                    </div>
                    <div class="lv-ticker-item">
                        <span class="lv-ticker-symbol">ETH</span>
                        <span class="lv-ticker-price" id="ticker-eth">Loading...</span>
                        <span class="lv-ticker-change positive" id="ticker-eth-change">+0.00%</span>
                    </div>
                    <div class="lv-ticker-item">
                        <span class="lv-ticker-symbol">VN30</span>
                        <span class="lv-ticker-price" id="ticker-vn">Loading...</span>
                        <span class="lv-ticker-change positive" id="ticker-vn-change">+0.00%</span>
                    </div>
                    <div class="lv-ticker-item">
                        <span class="lv-ticker-symbol">S&P 500</span>
                        <span class="lv-ticker-price">5,234.18</span>
                        <span class="lv-ticker-change positive">+0.45%</span>
                    </div>
                    <div class="lv-ticker-item">
                        <span class="lv-ticker-symbol">Gold</span>
                        <span class="lv-ticker-price">$2,341.50</span>
                        <span class="lv-ticker-change negative">-0.23%</span>
                    </div>
                    <!-- Duplicate for seamless loop -->
                    <div class="lv-ticker-item">
                        <span class="lv-ticker-symbol">BTC</span>
                        <span class="lv-ticker-price" data-ref="ticker-btc">Loading...</span>
                        <span class="lv-ticker-change positive" data-ref="ticker-btc-change">+0.00%</span>
                    </div>
                    <div class="lv-ticker-item">
                        <span class="lv-ticker-symbol">ETH</span>
                        <span class="lv-ticker-price" data-ref="ticker-eth">Loading...</span>
                        <span class="lv-ticker-change positive" data-ref="ticker-eth-change">+0.00%</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ================================================
     MASONRY INFINITE SCROLL FEED
     ================================================ -->
<?php if ($show_masonry_feed) : ?>
<section class="lv-masonry-section">
    <div class="lv-container">
        <!-- Masonry Grid Container -->
        <div class="lv-feed-container">
            <div class="lv-masonry-grid" id="lv-feed-grid">
                <!-- Initial posts loaded via PHP for SEO -->
                <?php
                $initial_posts = get_posts(array(
                    'posts_per_page' => 12,
                    'post_status'   => 'publish',
                    'orderby'       => 'date',
                    'order'         => 'DESC',
                ));

                // Collect initial post IDs for JS tracking
                $initial_post_ids = array();
                foreach ($initial_posts as $p) {
                    $initial_post_ids[] = $p->ID;
                }
                ?>

                <!-- Pass initial post IDs to JS -->
                <script>
                    window.linewInitialPostIds = <?php echo json_encode($initial_post_ids); ?>;
                </script>

                <?php foreach ($initial_posts as $post) :
                    setup_postdata($post);
                    $post_id = $post->ID;

                    $categories = get_the_category($post_id);
                    $primary_category = '';
                    foreach ($categories as $cat) {
                        if (empty($primary_category) && $cat->slug !== 'uncategorized') {
                            $primary_category = $cat->name;
                            break;
                        }
                    }

                    $thumbnail = '';
                    $thumbnail_id = get_post_thumbnail_id($post_id);
                    if ($thumbnail_id) {
                        $thumbnail = wp_get_attachment_image_url($thumbnail_id, 'linew-medium');
                    }
                    if (empty($thumbnail)) {
                        $external_url = get_post_meta($post_id, '_external_featured_image', true);
                        if (!empty($external_url)) {
                            $thumbnail = $external_url;
                        }
                    }

                    $post_date = get_post_time('U', false, $post_id);
                    $is_new = (time() - $post_date) < 86400;
                    $is_breaking = get_post_meta($post_id, '_is_breaking', true) === '1';
                    $views = (int) get_post_meta($post_id, '_post_views_count', true);
                ?>
                <article class="lv-feed-card" data-post-id="<?php echo $post_id; ?>">
                    <a href="<?php the_permalink(); ?>" class="lv-feed-card-image-link">
                        <div class="lv-feed-card-image">
                            <?php if ($thumbnail) : ?>
                            <img src="<?php echo esc_url($thumbnail); ?>"
                                 alt="<?php echo esc_attr(get_the_title()); ?>"
                                 loading="lazy">
                            <?php else : ?>
                            <div class="lv-feed-card-placeholder"></div>
                            <?php endif; ?>
                            <div class="lv-feed-card-badges">
                                <?php if ($is_new) : ?>
                                <span class="lv-badge-new">New</span>
                                <?php endif; ?>
                                <?php if ($is_breaking) : ?>
                                <span class="lv-badge-breaking">Breaking</span>
                                <?php endif; ?>
                            </div>
                        </div>
                    </a>
                    <div class="lv-feed-card-body">
                        <div class="lv-feed-card-category"><?php echo esc_html($primary_category ?: 'News'); ?></div>
                        <h3 class="lv-feed-card-title">
                            <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                        </h3>
                        <p class="lv-feed-card-excerpt"><?php echo esc_html(wp_trim_words(get_the_excerpt(), 20)); ?></p>
                        <div class="lv-feed-card-meta">
                            <span class="lv-feed-card-author"><?php the_author(); ?></span>
                            <span class="lv-feed-card-date"><?php echo linew_format_date(); ?></span>
                        </div>
                        <?php if ($views > 0) : ?>
                        <div class="lv-feed-card-stats">
                            <span class="lv-feed-card-stat">
                                <svg viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
                                </svg>
                                <?php echo number_format($views); ?>
                            </span>
                        </div>
                        <?php endif; ?>
                    </div>
                </article>
                <?php endforeach; ?>
                <?php wp_reset_postdata(); ?>
            </div>
            
            <!-- Loading Indicator -->
            <div class="lv-feed-loading" style="display: none;">
                <div class="lv-spinner"></div>
            </div>
            
            <!-- Error State -->
            <div class="lv-feed-error" style="display: none;">
                <p class="lv-feed-error-message">Failed to load articles</p>
                <button class="lv-feed-retry-btn">Retry</button>
            </div>
            
            <!-- Sentinel for IntersectionObserver -->
            <div class="lv-feed-sentinel"></div>
            
            <!-- Load More Button (fallback) -->
            <div class="lv-feed-load-more" style="display: none;">
                <button>Load More Articles</button>
            </div>
            
            <!-- End of Feed Message -->
            <div class="lv-feed-end" style="display: none;">
                <span class="lv-feed-end-line"></span>
                You've reached the end
                <span class="lv-feed-end-line"></span>
            </div>
        </div>
    </div>
</section>
<?php endif; ?>

<!-- ================================================
     CTA SECTION
     ================================================ -->
<section class="lv-cta-section">
    <div class="lv-container">
        <div class="lv-cta-card">
            <div class="lv-cta-content">
                <span class="lv-cta-badge">🎯</span>
                <h2>Explore AI's Power in Market Prediction</h2>
                <p>Litimez uses TimesFM, Chronos-2 and MiniMax AI to bring you the most accurate predictions.</p>
                <div class="lv-cta-features">
                    <div class="lv-cta-feature">
                        <span class="lv-feature-icon">📊</span>
                        <span>1-30 Days Prediction</span>
                    </div>
                    <div class="lv-cta-feature">
                        <span class="lv-feature-icon">🎯</span>
                        <span>95%+ Accuracy</span>
                    </div>
                    <div class="lv-cta-feature">
                        <span class="lv-feature-icon">⚡</span>
                        <span>Real-time Updates</span>
                    </div>
                </div>
                <a href="#" class="lv-cta-button">Try Now</a>
            </div>
            <div class="lv-cta-visual">
                <div class="lv-cta-chart">
                    <div class="lv-chart-line"></div>
                    <div class="lv-chart-points">
                        <span class="lv-point lv-point-1"></span>
                        <span class="lv-point lv-point-2"></span>
                        <span class="lv-point lv-point-3"></span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- ================================================
     FOOTER NEWSLETTER
     ================================================ -->
<section class="lv-footer-newsletter">
    <div class="lv-container">
        <div class="lv-newsletter-content">
            <h2>Stay Updated with Litimez</h2>
            <p>Get the latest market predictions and news delivered daily</p>
            <form class="lv-footer-form">
                <input type="email" placeholder="Enter your email">
                <button type="submit">Subscribe Now</button>
            </form>
        </div>
    </div>
</section>

<?php get_footer(); ?>
