<?php
/**
 * Footer Template - NYTimes Style Redesign
 *
 * @package Linew_Viral
 */

if (!defined('ABSPATH')) {
    exit;
}
?>
    </main><!-- #lv-main-content -->

    <!-- Footer -->
    <footer class="lv-footer">
        <div class="lv-footer-main">
            <div class="lv-container">
                <div class="lv-footer-brand">
                    <a href="<?php echo esc_url(home_url('/')); ?>" class="lv-footer-logo">
                        Litimez<span>.</span>
                    </a>
                    <p class="lv-footer-tagline">
                        Fastest News - Deepest Analysis - Latest Trends
                    </p>
                </div>

                <div class="lv-footer-sections">
                    <div class="lv-footer-section">
                        <h4>Categories</h4>
                        <ul>
                            <?php
                            $categories = get_categories(array('hide_empty' => true, 'number' => 6));
                            foreach ($categories as $category) {
                                printf(
                                    '<li><a href="%s">%s</a></li>',
                                    esc_url(get_category_link($category->term_id)),
                                    esc_html(linew_translate_category($category->name, 'en'))
                                );
                            }
                            ?>
                        </ul>
                    </div>

                    <div class="lv-footer-section">
                        <h4>About Litimez</h4>
                        <ul>
                            <li><a href="<?php echo esc_url(home_url('/about')); ?>">About Us</a></li>
                            <li><a href="<?php echo esc_url(home_url('/contact')); ?>">Contact</a></li>
                            <li><a href="<?php echo esc_url(home_url('/careers')); ?>">Careers</a></li>
                            <li><a href="<?php echo esc_url(home_url('/advertise')); ?>">Advertise</a></li>
                        </ul>
                    </div>

                    <div class="lv-footer-section">
                        <h4>Support</h4>
                        <ul>
                            <li><a href="<?php echo esc_url(home_url('/faq')); ?>">FAQ</a></li>
                            <li><a href="<?php echo esc_url(home_url('/contact')); ?>">Help</a></li>
                            <li><a href="<?php echo esc_url(home_url('/trust')); ?>">Trust & Safety</a></li>
                            <li><a href="<?php echo esc_url(home_url('/accessibility')); ?>">Accessibility</a></li>
                        </ul>
                    </div>

                    <div class="lv-footer-section">
                        <h4>Connect</h4>
                        <div class="lv-footer-social">
                            <a href="https://facebook.com/litimez" target="_blank" rel="noopener" class="lv-social-link" aria-label="Facebook">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>
                                </svg>
                            </a>
                            <a href="https://twitter.com/litimez" target="_blank" rel="noopener" class="lv-social-link" aria-label="Twitter/X">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                </svg>
                            </a>
                            <a href="https://instagram.com/litimez" target="_blank" rel="noopener" class="lv-social-link" aria-label="Instagram">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
                                    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
                                    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
                                </svg>
                            </a>
                            <a href="https://youtube.com/litimez" target="_blank" rel="noopener" class="lv-social-link" aria-label="YouTube">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"/>
                                    <polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02" fill="#fff"/>
                                </svg>
                            </a>
                            <a href="<?php echo esc_url(home_url('/feed')); ?>" class="lv-social-link" aria-label="RSS Feed">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M4 11a9 9 0 0 1 9 9"/>
                                    <path d="M4 4a16 16 0 0 1 16 16"/>
                                    <circle cx="5" cy="19" r="1"/>
                                </svg>
                            </a>
                        </div>
                    </div>
                </div>

                <div class="lv-footer-subscribe">
                    <div class="lv-subscribe-content">
                        <h3>Subscribe to Litimez</h3>
                        <p>Get the latest news delivered to your inbox daily.</p>
                    </div>
                    <form class="lv-subscribe-form">
                        <input type="email" placeholder="Enter your email" required>
                        <button type="submit">
                            <span>Subscribe</span>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M5 12h14M12 5l7 7-7 7"/>
                            </svg>
                        </button>
                    </form>
                </div>
            </div>
        </div>

        <div class="lv-footer-bottom">
            <div class="lv-container">
                <div class="lv-footer-bottom-inner">
                    <div class="lv-footer-legal">
                        <p>&copy; <?php echo date('Y'); ?> <?php bloginfo('name'); ?>. All rights reserved.</p>
                    </div>
                    <div class="lv-footer-links">
                        <a href="<?php echo esc_url(home_url('/privacy-policy')); ?>">Privacy Policy</a>
                        <a href="<?php echo esc_url(home_url('/terms-of-service')); ?>">Terms of Service</a>
                        <a href="<?php echo esc_url(home_url('/cookie-policy')); ?>">Cookie Policy</a>
                        <a href="<?php echo esc_url(home_url('/sitemap')); ?>">Sitemap</a>
                    </div>
                </div>
            </div>
        </div>
    </footer>

</div><!-- #lv-page -->

<?php wp_footer(); ?>
</body>
</html>
