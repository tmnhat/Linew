/**
 * Linew Viral Theme JavaScript
 * Tinh tế Style - Static Header
 */

(function() {
    'use strict';

    // DOM Ready
    document.addEventListener('DOMContentLoaded', function() {
        initMobileMenu();
        initSearch();
        initLazyLoad();
        initSmoothScroll();
        initBackToTop();
    });

    /**
     * Mobile Menu - Full screen slide-in
     */
    function initMobileMenu() {
        var menuToggle = document.getElementById('lv-menu-toggle');
        var mobileMenu = document.getElementById('lv-mobile-menu');
        var menuOverlay = document.getElementById('lv-mobile-menu-overlay');
        var menuClose = document.getElementById('lv-menu-close');

        if (!menuToggle || !mobileMenu) return;

        function openMenu() {
            mobileMenu.classList.add('active');
            if (menuOverlay) menuOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeMenu() {
            mobileMenu.classList.remove('active');
            if (menuOverlay) menuOverlay.classList.remove('active');
            document.body.style.overflow = '';
        }

        menuToggle.addEventListener('click', openMenu);
        if (menuClose) menuClose.addEventListener('click', closeMenu);
        if (menuOverlay) menuOverlay.addEventListener('click', closeMenu);

        // Close on escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && mobileMenu.classList.contains('active')) {
                closeMenu();
            }
        });
    }

    /**
     * Search Overlay - Full screen
     */
    function initSearch() {
        var searchToggle = document.getElementById('lv-search-toggle');
        var searchOverlay = document.getElementById('lv-search-overlay');
        var searchClose = document.getElementById('lv-search-close');
        var searchInput = searchOverlay ? searchOverlay.querySelector('input[type="search"]') : null;

        if (!searchToggle || !searchOverlay) return;

        function openSearch() {
            searchOverlay.classList.add('active');
            setTimeout(function() {
                if (searchInput) searchInput.focus();
            }, 100);
            document.body.style.overflow = 'hidden';
        }

        function closeSearch() {
            searchOverlay.classList.remove('active');
            document.body.style.overflow = '';
        }

        searchToggle.addEventListener('click', openSearch);
        if (searchClose) searchClose.addEventListener('click', closeSearch);

        // Close on escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && searchOverlay.classList.contains('active')) {
                closeSearch();
            }
        });

        // Close on click outside
        searchOverlay.addEventListener('click', function(e) {
            if (e.target === searchOverlay) {
                closeSearch();
            }
        });
    }

    /**
     * Lazy Load Images
     */
    function initLazyLoad() {
        if ('IntersectionObserver' in window) {
            var imageObserver = new IntersectionObserver(function(entries, observer) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        var img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            img.classList.add('loaded');
                        }
                        imageObserver.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(function(img) {
                imageObserver.observe(img);
            });
        } else {
            // Fallback for older browsers
            document.querySelectorAll('img[data-src]').forEach(function(img) {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
            });
        }
    }

    /**
     * Smooth Scroll for Anchor Links
     */
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
            anchor.addEventListener('click', function(e) {
                var href = this.getAttribute('href');
                if (href === '#') return;

                var target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    window.scrollTo({
                        top: target.offsetTop - 20,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    /**
     * Back to Top Button
     */
    function initBackToTop() {
        var backToTop = document.createElement('button');
        backToTop.className = 'lv-back-to-top';
        backToTop.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 15l-6-6-6 6"/></svg>';
        backToTop.setAttribute('aria-label', 'Back to top');
        document.body.appendChild(backToTop);

        backToTop.style.cssText = [
            'position: fixed;',
            'bottom: 24px;',
            'right: 24px;',
            'width: 48px;',
            'height: 48px;',
            'background: var(--lv-accent, #c41e3a);',
            'color: white;',
            'border: none;',
            'border-radius: 50%;',
            'cursor: pointer;',
            'opacity: 0;',
            'visibility: hidden;',
            'transition: all 0.3s ease;',
            'z-index: 9998;',
            'display: flex;',
            'align-items: center;',
            'justify-content: center;',
            'box-shadow: 0 4px 12px rgba(0,0,0,0.15);',
            'padding-bottom: env(safe-area-inset-bottom);'
        ].join(' ');

        backToTop.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 500) {
                backToTop.style.opacity = '1';
                backToTop.style.visibility = 'visible';
            } else {
                backToTop.style.opacity = '0';
                backToTop.style.visibility = 'hidden';
            }
        });
    }

})();
