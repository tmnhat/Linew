import { useState, useEffect, useCallback, useRef } from 'react';
import { Chart, registerables } from 'chart.js';

// Register Chart.js components
Chart.register(...registerables);

// Config từ WordPress
const API_BASE = (window as any).LINEWS_CONFIG?.api_base || '/wp-json/linew/v1';
const DEFAULT_SYMBOL = (window as any).LINEWS_CONFIG?.default_symbol || 'BTC-USD';

// Symbols list
const SYMBOLS = [
    { key: 'BTC-USD', label: 'Bitcoin' },
    { key: 'ETH-USD', label: 'Ethereum' },
    { key: '^VNINDEX', label: 'VN-Index' },
];

interface Prediction {
    horizon: number;
    predicted_price?: number;
    predicted_low?: number;
    predicted_high?: number;
    change_pct?: number;
    confidence_score?: number;
}

interface ChartPoint {
    date: string;
    actual?: number;
}

interface PredictionResponse {
    symbol: string;
    current_price?: number;
    predictions?: Record<string, Prediction>;
    analysis?: {
        sentiment?: string;
        analysis_vi?: string;
        fear_greed_index?: number;
        fear_greed_value?: string;
        key_factors?: Array<{ factor: string; impact: string }>;
    };
    accuracy?: {
        avg_error_pct?: number;
        total_predictions?: number;
    };
    chart_data?: {
        points: ChartPoint[];
        labels: string[];
    };
    last_updated?: string;
}

export default function PredictionWidget() {
    const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
    const [data, setData] = useState<PredictionResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [horizon, setHorizon] = useState('7d');
    const chartRef = useRef<HTMLCanvasElement>(null);
    const chartInstance = useRef<Chart | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Fetch prediction data
    const fetchPrediction = useCallback(async (sym: string) => {
        setLoading(true);
        setError(null);

        try {
            // Normalize symbol for API (remove ^ for VNINDEX)
            const apiSymbol = sym.startsWith('^') ? sym.substring(1) : sym;

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            const resp = await fetch(`${API_BASE}/prediction/${encodeURIComponent(apiSymbol)}`, {
                signal: controller.signal,
            });
            clearTimeout(timeoutId);

            if (!resp.ok) {
                throw new Error(`API returned ${resp.status}`);
            }

            const json: PredictionResponse = await resp.json();
            setData(json);
        } catch (err: any) {
            if (err.name === 'AbortError') {
                setError('Timeout — API không phản hồi');
            } else {
                setError('Không thể tải dữ liệu');
            }
            console.error('Prediction fetch error:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch khi symbol thay đổi
    useEffect(() => {
        fetchPrediction(symbol);
    }, [symbol, fetchPrediction]);

    // Render chart — CHỈ khi data thay đổi
    useEffect(() => {
        if (!data || !data.chart_data || !chartRef.current || !containerRef.current) return;

        // Destroy chart cũ trước khi tạo mới
        if (chartInstance.current) {
            chartInstance.current.destroy();
            chartInstance.current = null;
        }

        const ctx = chartRef.current.getContext('2d');
        if (!ctx) return;

        const points = data.chart_data?.points || [];
        if (points.length === 0) return;

        const labels = points.map(p => p.date);
        const actualPrices = points.map(p => p.actual ?? null);

        // Add forecast point if available
        const pred30d = data.predictions?.['30d'];
        if (pred30d?.predicted_price) {
            labels.push('+30d');
            actualPrices.push(null);
        }

        try {
            chartInstance.current = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Giá thực tế',
                            data: actualPrices,
                            borderColor: '#3b82f6',
                            borderWidth: 2,
                            pointRadius: 0,
                            tension: 0.3,
                            spanGaps: true,
                        },
                        {
                            label: 'Dự đoán',
                            data: data.current_price ? [...Array(labels.length - 1).fill(null), data.current_price] : [],
                            borderColor: '#10b981',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            pointRadius: 3,
                            tension: 0.3,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                        },
                    },
                    scales: {
                        x: {
                            display: true,
                            ticks: {
                                maxTicksLimit: 6,
                                color: '#9ca3af',
                                font: { size: 10 },
                            },
                            grid: { display: false },
                        },
                        y: {
                            display: true,
                            ticks: {
                                color: '#9ca3af',
                                font: { size: 10 },
                                callback: (val: string | number) => '$' + Number(val).toLocaleString(),
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.05)',
                            },
                        },
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false,
                    },
                },
            });
        } catch (err) {
            console.error('Chart render error:', err);
        }

        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
                chartInstance.current = null;
            }
        };
    }, [data]);

    // Lấy prediction cho horizon hiện tại
    const prediction = data?.predictions?.[horizon];
    const analysis = data?.analysis;
    const accuracy = data?.accuracy;

    // Sentiment display
    const sentimentConfig: Record<string, { emoji: string; label: string; color: string }> = {
        bullish: { emoji: '🟢', label: 'Tích cực', color: '#10b981' },
        bearish: { emoji: '🔴', label: 'Tiêu cực', color: '#ef4444' },
        neutral: { emoji: '🟡', label: 'Trung lập', color: '#f59e0b' },
    };
    const sentiment = sentimentConfig[analysis?.sentiment || 'neutral'] || sentimentConfig.neutral;

    // Get horizon label
    const getHorizonLabel = (h: string): string => {
        const labels: Record<string, string> = {
            '1d': '1 ngày',
            '3d': '3 ngày',
            '7d': '7 ngày',
            '30d': '30 ngày',
        };
        return labels[h] || h;
    };

    return (
        <div ref={containerRef} style={{
            background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
            borderRadius: '12px',
            padding: '20px',
            maxWidth: '720px',
            margin: '0 auto 24px auto',
            color: '#e2e8f0',
            fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
            display: 'flex',
            flexDirection: 'column',
        }}>
            {/* Title */}
            <h2 style={{
                fontSize: '20px',
                fontWeight: 700,
                margin: '0 0 16px 0',
                color: '#f1f5f9',
                flexShrink: 0,
            }}>
                📊 Linews Analysis
            </h2>

            {/* Symbol tabs */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap', flexShrink: 0 }}>
                {SYMBOLS.map(s => (
                    <button
                        key={s.key}
                        onClick={() => setSymbol(s.key)}
                        style={{
                            padding: '6px 16px',
                            borderRadius: '20px',
                            border: 'none',
                            fontSize: '13px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            background: symbol === s.key ? '#10b981' : 'rgba(255,255,255,0.1)',
                            color: symbol === s.key ? '#fff' : '#94a3b8',
                            transition: 'all 0.2s',
                        }}
                    >
                        {s.label}
                    </button>
                ))}
            </div>

            {/* Loading state */}
            {loading && (
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748b' }}>
                    ⏳ Đang tải dữ liệu...
                </div>
            )}

            {/* Error state */}
            {error && !loading && (
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                    <p style={{ color: '#f87171', marginBottom: '12px' }}>⚠️ {error}</p>
                    <button
                        onClick={() => fetchPrediction(symbol)}
                        style={{
                            padding: '8px 20px',
                            background: '#334155',
                            color: '#e2e8f0',
                            border: '1px solid #475569',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '13px',
                        }}
                    >
                        🔄 Thử lại
                    </button>
                </div>
            )}

            {/* Data loaded */}
            {data && !loading && !error && (
                <>
                    {/* Price + Change */}
                    <div style={{
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: '10px',
                        padding: '16px',
                        marginBottom: '16px',
                        textAlign: 'center',
                        flexShrink: 0,
                    }}>
                        <div style={{ fontSize: '32px', fontWeight: 700, color: '#f1f5f9' }}>
                            ${data.current_price?.toLocaleString(undefined, {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 2,
                            })}
                        </div>
                        {prediction && (
                            <span style={{
                                display: 'inline-block',
                                marginTop: '8px',
                                padding: '4px 12px',
                                borderRadius: '6px',
                                fontSize: '14px',
                                fontWeight: 600,
                                background: (prediction.change_pct ?? 0) >= 0
                                    ? 'rgba(16, 185, 129, 0.2)'
                                    : 'rgba(239, 68, 68, 0.2)',
                                color: (prediction.change_pct ?? 0) >= 0 ? '#10b981' : '#ef4444',
                            }}>
                                {(prediction.change_pct ?? 0) >= 0 ? '+' : ''}{prediction.change_pct?.toFixed(2)}%
                            </span>
                        )}
                    </div>

                    {/* Horizon tabs */}
                    <div style={{ display: 'flex', gap: '6px', marginBottom: '16px', flexShrink: 0 }}>
                        {['1d', '3d', '7d', '30d'].map(h => (
                            <button
                                key={h}
                                onClick={() => setHorizon(h)}
                                style={{
                                    flex: 1,
                                    padding: '6px',
                                    borderRadius: '6px',
                                    border: '1px solid',
                                    borderColor: horizon === h ? '#10b981' : '#334155',
                                    background: horizon === h ? 'rgba(16,185,129,0.15)' : 'transparent',
                                    color: horizon === h ? '#10b981' : '#64748b',
                                    fontSize: '12px',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                }}
                            >
                                {getHorizonLabel(h)}
                            </button>
                        ))}
                    </div>

                    {/* Chart */}
                    <div style={{
                        background: 'rgba(255,255,255,0.03)',
                        borderRadius: '10px',
                        padding: '12px',
                        marginBottom: '16px',
                        height: '280px',
                        maxHeight: '280px',
                        minHeight: '280px',
                        flexShrink: 0,
                        flexBasis: '280px',
                        overflow: 'hidden',
                        position: 'relative',
                    }}>
                        <canvas ref={chartRef} style={{ width: '100%', height: '100%', display: 'block', maxHeight: '280px' }} />
                    </div>

                    {/* Prediction detail */}
                    {prediction && (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 1fr',
                            gap: '8px',
                            marginBottom: '16px',
                            flexShrink: 0,
                        }}>
                            <div style={{
                                background: 'rgba(255,255,255,0.05)',
                                borderRadius: '8px',
                                padding: '12px',
                                textAlign: 'center',
                                flexShrink: 0,
                            }}>
                                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>
                                    Dự đoán {getHorizonLabel(horizon)}
                                </div>
                                <div style={{ fontSize: '18px', fontWeight: 700, color: '#f1f5f9' }}>
                                    ${prediction.predicted_price?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                </div>
                            </div>
                            <div style={{
                                background: 'rgba(255,255,255,0.05)',
                                borderRadius: '8px',
                                padding: '12px',
                                textAlign: 'center',
                                flexShrink: 0,
                            }}>
                                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>
                                    Khoảng tin cậy
                                </div>
                                <div style={{ fontSize: '14px', fontWeight: 600, color: '#94a3b8' }}>
                                    ${prediction.predicted_low?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                    {' — '}
                                    ${prediction.predicted_high?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Sentiment + Analysis */}
                    {analysis && (
                        <div style={{
                            background: 'rgba(255,255,255,0.05)',
                            borderRadius: '10px',
                            padding: '14px',
                            marginBottom: '16px',
                            flexShrink: 0,
                        }}>
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                marginBottom: '10px',
                            }}>
                                <span style={{ fontSize: '16px' }}>{sentiment.emoji}</span>
                                <span style={{
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    color: sentiment.color,
                                }}>
                                    Xu hướng: {sentiment.label}
                                </span>
                                {analysis.fear_greed_index != null && (
                                    <span style={{
                                        marginLeft: 'auto',
                                        fontSize: '12px',
                                        color: '#64748b',
                                    }}>
                                        Fear & Greed: {analysis.fear_greed_index}/100
                                    </span>
                                )}
                            </div>

                            <p style={{
                                fontSize: '14px',
                                lineHeight: 1.6,
                                color: '#cbd5e1',
                                margin: '0 0 10px 0',
                            }}>
                                {analysis.analysis_vi}
                            </p>

                            {analysis.key_factors && analysis.key_factors.length > 0 && (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                    {analysis.key_factors.slice(0, 3).map((factor, i) => (
                                        <span key={i} style={{
                                            padding: '3px 10px',
                                            background: 'rgba(255,255,255,0.08)',
                                            borderRadius: '12px',
                                            fontSize: '11px',
                                            color: '#94a3b8',
                                        }}>
                                            {factor.factor}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Accuracy + Updated */}
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '12px',
                        fontSize: '12px',
                        color: '#64748b',
                        flexShrink: 0,
                    }}>
                        {accuracy && (accuracy.total_predictions ?? 0) >= 7 && (
                            <span>📈 Accuracy 30d: ±{accuracy.avg_error_pct?.toFixed(1)}%</span>
                        )}
                        <span>🕐 {data.last_updated
                            ? new Date(data.last_updated).toLocaleString('vi-VN', {
                                hour: '2-digit', minute: '2-digit',
                                day: '2-digit', month: '2-digit', year: 'numeric',
                            })
                            : 'N/A'
                        }</span>
                    </div>

                    {/* Disclaimer */}
                    <p style={{
                        fontSize: '11px',
                        color: '#475569',
                        textAlign: 'center',
                        margin: 0,
                        lineHeight: 1.5,
                    }}>
                        ⚠️ Đây là phân tích tham khảo của Linews, không phải tư vấn đầu tư.
                    </p>
                </>
            )}
        </div>
    );
}
