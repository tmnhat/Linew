// Market Ticker Script - Updates live prices
(function($) {
    'use strict';

    const MarketTicker = {
        symbols: {
            'BTC-USD': { selector: '#ticker-btc', changeSelector: '#ticker-btc-change' },
            'ETH-USD': { selector: '#ticker-eth', changeSelector: '#ticker-eth-change' },
            '^VNINDEX': { selector: '#ticker-vn', changeSelector: '#ticker-vn-change' }
        },
        updateInterval: 60000, // Update every minute
        cache: new Map(),
        cacheTime: 30000, // Cache for 30 seconds

        init: function() {
            // Check if ticker elements exist
            if (!$('#ticker-btc').length) return;
            this.updateAllPrices();
            setInterval(() => this.updateAllPrices(), this.updateInterval);
        },

        updateAllPrices: function() {
            const apiUrl = window.linewConfig?.apiUrl || '/wp-json/linew/v1';

            Object.keys(this.symbols).forEach(symbol => {
                this.updateSymbolPrice(symbol, apiUrl);
            });
        },

        updateSymbolPrice: function(symbol, apiUrl) {
            // Check cache
            const cached = this.cache.get(symbol);
            if (cached && Date.now() - cached.timestamp < this.cacheTime) {
                this.renderPrice(symbol, cached.data);
                return;
            }

            const self = this;
            const config = this.symbols[symbol];

            $.ajax({
                url: `${apiUrl}/prediction/${encodeURIComponent(symbol)}`,
                method: 'GET',
                dataType: 'json',
                success: function(data) {
                    self.cache.set(symbol, { data, timestamp: Date.now() });
                    self.renderPrice(symbol, data);
                },
                error: function() {
                    // Silently fail - keep existing values
                }
            });
        },

        renderPrice: function(symbol, data) {
            const config = this.symbols[symbol];
            if (!config) return;

            const $price = $(config.selector);
            const $change = $(config.changeSelector);

            if (!data || !data.current_price) return;

            const price = data.current_price;
            const currency = symbol === '^VNINDEX' ? '₫' : '$';

            // Format price
            let formattedPrice;
            if (symbol === '^VNINDEX') {
                formattedPrice = price.toLocaleString('vi-VN');
            } else {
                formattedPrice = '$' + price.toLocaleString('en-US', { maximumFractionDigits: 2 });
            }
            $price.text(formattedPrice);

            // Update change
            if (data.predictions && data.predictions['1d']) {
                const changePct = data.predictions['1d'].change_pct;
                if (changePct !== undefined) {
                    const sign = changePct >= 0 ? '+' : '';
                    $change.text(`${sign}${changePct.toFixed(2)}%`);
                    $change.removeClass('positive negative');
                    $change.addClass(changePct >= 0 ? 'positive' : 'negative');
                }
            }
        }
    };

    // Initialize when DOM is ready
    $(document).ready(function() {
        MarketTicker.init();
    });

})(jQuery);
