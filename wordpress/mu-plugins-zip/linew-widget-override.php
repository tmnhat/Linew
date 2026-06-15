<?php
/**
 * Plugin Name: Linew Widget JS Override
 * Description: Override widget.js to fix process.env error
 */

// Hook into wp_enqueue_scripts with high priority
add_action('wp_enqueue_scripts', function() {
    // Deregister old widget.js
    wp_dequeue_script('linew-prediction-react');
    wp_deregister_script('linew-prediction-react');
    
    // Create inline widget code that works
    $inline_js = <<<'JSEOF'
(function() {
    'use strict';
    
    // Fix process.env for React
    if (typeof process === 'undefined') {
        window.process = { env: { NODE_ENV: 'production' } };
    }
    
    // Simple vanilla JS widget
    var apiUrl = window.linewConfig?.apiUrl || '/wp-json/linew/v1';
    var currentSymbol = 'BTC-USD';
    
    function initWidget() {
        var containers = document.querySelectorAll('.linew-prediction-content');
        containers.forEach(function(container) {
            var symbol = container.dataset.symbol || currentSymbol;
            fetchData(container, symbol);
        });
    }
    
    function fetchData(container, symbol) {
        container.innerHTML = '<div class="linew-loading"><span class="linew-spinner"></span> Đang tải...</div>';
        
        fetch(apiUrl + '/prediction/' + symbol)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    container.innerHTML = '<div class="linew-error">Lỗi: ' + data.error + '</div>';
                    return;
                }
                renderWidget(container, data);
            })
            .catch(function(err) {
                container.innerHTML = '<div class="linew-error">Không thể tải dữ liệu</div>';
                console.error('Widget error:', err);
            });
    }
    
    function renderWidget(container, data) {
        var price = data.current_price;
        var change = data.predictions['1d']?.change_pct || 0;
        var changeClass = change >= 0 ? 'positive' : 'negative';
        var predPrice = data.predictions['1d']?.predicted_price || price;
        var confidence = ((data.predictions['1d']?.confidence_score || 0) * 100).toFixed(1);
        
        var html = '<div class="linew-price-header">';
        html += '<span class="linew-current-price">$' + Math.round(price).toLocaleString() + '</span>';
        html += '<span class="linew-price-change ' + changeClass + '">' + (change >= 0 ? '+' : '') + change.toFixed(2) + '%</span>';
        html += '</div>';
        
        html += '<div class="linew-chart-container">';
        html += '<canvas id="widget-chart-' + data.symbol + '"></canvas>';
        html += '</div>';
        
        html += '<div class="linew-prediction-details">';
        html += '<div class="linew-pred-item"><span>Dự đoán 1 ngày:</span><strong>$' + Math.round(predPrice).toLocaleString() + '</strong></div>';
        html += '<div class="linew-pred-item"><span>Độ chính xác:</span><strong>' + confidence + '%</strong></div>';
        html += '</div>';
        
        container.innerHTML = html;
        
        // Render chart if Chart.js available
        if (typeof Chart !== 'undefined' && data.chart_data) {
            renderChart('widget-chart-' + data.symbol, data.chart_data);
        } else {
            // Load Chart.js dynamically
            var script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
            script.onload = function() {
                if (data.chart_data) renderChart('widget-chart-' + data.symbol, data.chart_data);
            };
            document.head.appendChild(script);
        }
    }
    
    function renderChart(canvasId, chartData) {
        var ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Giá',
                    data: chartData.points.map(function(p) { return p.actual; }),
                    borderColor: '#4ade80',
                    backgroundColor: 'rgba(74, 222, 128, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        ticks: { color: 'rgba(255,255,255,0.7)' }
                    },
                    x: { display: false }
                }
            }
        });
    }
    
    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }
    
    // Tab switching
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('linew-tab')) {
            var symbol = e.target.dataset.symbol;
            if (symbol) {
                document.querySelectorAll('.linew-tab').forEach(function(t) {
                    t.classList.remove('active');
                });
                e.target.classList.add('active');
                
                var content = document.querySelector('.linew-prediction-content');
                if (content) {
                    content.dataset.symbol = symbol;
                    fetchData(content, symbol);
                }
            }
        }
    });
    
})();
JSEOF;
    
    wp_register_script('linew-widget-fixed', false, array(), '2.1.1', true);
    wp_enqueue_script('linew-widget-fixed');
    wp_add_inline_script('linew-widget-fixed', $inline_js);
    
}, 100);

