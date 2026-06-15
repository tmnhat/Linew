import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { SymbolTabs } from './components/SymbolTabs';
import { PredictionChart } from './components/PredictionChart';
import { PredictionCards } from './components/PredictionCards';
import { AnalysisCard } from './components/AnalysisCard';
import { FearGreedIndicator } from './components/FearGreedIndicator';
import { AccuracyStats } from './components/AccuracyStats';

interface SymbolInfo {
    symbol: string;
    name: string;
    type: string;
}

interface Prediction {
    horizon: number;
    predicted_price: number;
    predicted_low?: number;
    predicted_high?: number;
    change_pct?: number;
    confidence_score?: number;
    ai_sentiment?: string;
    ai_sentiment_score?: number;
}

interface Analysis {
    sentiment?: string;
    sentiment_score?: number;
    analysis_vi?: string;
    key_factors?: Array<{ factor: string; impact: string }>;
    risk_factors?: Array<{ risk: string; severity: string }>;
    support_levels?: number[];
    resistance_levels?: number[];
    fear_greed_index?: number;
    fear_greed_value?: string;
}

interface PredictionResponse {
    symbol: string;
    current_price?: number;
    predictions: Record<string, Prediction>;
    analysis?: Analysis;
    accuracy?: {
        avg_error_pct?: number;
        direction_accuracy?: number;
        within_bounds_pct?: number;
    };
    chart_data?: {
        points: Array<{
            date: string;
            actual?: number;
            predicted_1d?: number;
            predicted_7d?: number;
            predicted_30d?: number;
        }>;
        labels: string[];
    };
    last_updated?: string;
}

const DEFAULT_SYMBOLS: SymbolInfo[] = [
    { symbol: 'BTC-USD', name: 'Bitcoin', type: 'crypto' },
    { symbol: 'ETH-USD', name: 'Ethereum', type: 'crypto' },
    { symbol: '^VNINDEX', name: 'VN-Index', type: 'stock' },
];

const App: React.FC = () => {
    const [symbols] = useState<SymbolInfo[]>(DEFAULT_SYMBOLS);
    const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC-USD');
    const [data, setData] = useState<PredictionResponse | null>(null);
    const [aiAnalysis, setAiAnalysis] = useState<Analysis | null>(null);
    const [aiLoading, setAiLoading] = useState<boolean>(false);
    const [aiSource, setAiSource] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const apiUrl = (window as any).linewConfig?.apiUrl || '/wp-json/linew/v1';

    const fetchPrediction = useCallback(async (symbol: string) => {
        setLoading(true);
        setError(null);

        try {
            const apiSymbol = symbol.startsWith('^') ? symbol.substring(1) : symbol;
            const response = await axios.get<PredictionResponse>(
                `${apiUrl}/prediction/${encodeURIComponent(apiSymbol)}`
            );
            setData(response.data);
        } catch (err) {
            console.error('Failed to fetch prediction:', err);
            setError('Không thể tải dữ liệu dự đoán');
        } finally {
            setLoading(false);
        }
    }, []);

    // AI On-Demand Analysis - chỉ chạy khi user load widget
    const fetchAIAnalysis = useCallback(async (symbol: string, forceRefresh: boolean = false) => {
        setAiLoading(true);
        setAiSource('');

        try {
            const apiSymbol = symbol.startsWith('^') ? symbol.substring(1) : symbol;
            const params = forceRefresh ? '?force_refresh=true' : '';
            const response = await axios.get<AIAnalysisResponse>(
                `${apiUrl}/prediction/${encodeURIComponent(apiSymbol)}/analyze${params}`
            );

            if (response.data?.analysis) {
                setAiAnalysis(response.data.analysis);
                setAiSource(response.data.source || 'fresh');
            }
        } catch (err) {
            console.error('Failed to fetch AI analysis:', err);
            setAiAnalysis(null);
        } finally {
            setAiLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPrediction(selectedSymbol);
        fetchAIAnalysis(selectedSymbol);

        return () => {};
    }, [selectedSymbol, fetchPrediction, fetchAIAnalysis]);

    const handleSymbolChange = (symbol: string) => {
        setSelectedSymbol(symbol);
    };

    const currency = selectedSymbol === '^VNINDEX' ? 'VND' : 'USD';
    const currencySymbol = currency === 'VND' ? '₫' : '$';

    const formatPrice = (price: number | undefined): string => {
        if (!price) return 'N/A';
        return `${currencySymbol}${price.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
    };

    if (loading) {
        return (
            <div className="linew-homepage-widget">
                <div className="linew-loading">
                    <span className="linew-spinner"></span>
                    Đang tải dữ liệu...
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="linew-homepage-widget">
                <h2 className="linew-widget-title">Dự đoán thị trường</h2>
                <div className="linew-error">{error || 'Chưa có dữ liệu'}</div>
            </div>
        );
    }

    return (
        <div className="linew-homepage-widget">
            <div className="linew-widget-header">
                <h2 className="linew-widget-title">Dự đoán thị trường</h2>
                <FearGreedIndicator apiUrl={apiUrl} />
            </div>

            <SymbolTabs
                symbols={symbols}
                selectedSymbol={selectedSymbol}
                onSymbolChange={handleSymbolChange}
            />

            <div className="linew-prediction-content">
                {data.current_price && (
                    <div className="linew-price-header">
                        <span className="linew-current-price">
                            {formatPrice(data.current_price)}
                        </span>
                        {data.predictions?.['1d']?.change_pct !== undefined && (
                            <span className={`linew-price-change ${data.predictions['1d'].change_pct > 0 ? 'positive' : 'negative'}`}>
                                {data.predictions['1d'].change_pct > 0 ? '+' : ''}
                                {data.predictions['1d'].change_pct.toFixed(2)}%
                            </span>
                        )}
                    </div>
                )}

                {aiLoading && (
                    <div className="linew-ai-loading">
                        <span className="linew-spinner-small"></span>
                        <span>AI đang phân tích...</span>
                    </div>
                )}

                {(aiAnalysis || data?.analysis) && (
                    <AnalysisCard analysis={aiAnalysis || data?.analysis} />
                )}

                {aiSource && (
                    <div className="linew-ai-source">
                        {aiSource === 'cache' && 'Phân tích từ cache'}
                        {aiSource === 'database' && 'Phân tích từ database'}
                        {aiSource === 'fresh' && 'Phân tích AI mới'}
                    </div>
                )}

                <PredictionChart
                    data={data}
                    currencySymbol={currencySymbol}
                />

                <PredictionCards
                    predictions={data.predictions}
                    currencySymbol={currencySymbol}
                    formatPrice={formatPrice}
                />

                {data.accuracy && (
                    <AccuracyStats accuracy={data.accuracy} />
                )}

                {data.last_updated && (
                    <div className="linew-last-update">
                        Cập nhật: {new Date(data.last_updated).toLocaleString('vi-VN')}
                    </div>
                )}
            </div>

            <div className="linew-prediction-legend">
                <span className="legend-item">
                    <span className="legend-dot actual"></span>
                    Giá thực
                </span>
                <span className="legend-item">
                    <span className="legend-dot predicted"></span>
                    Dự đoán
                </span>
                <span className="legend-item">
                    <span className="legend-dot range"></span>
                    Khoảng dự đoán
                </span>
            </div>

            <p className="linew-disclaimer">
                Đây là dự đoán tham khảo, không phải tư vấn đầu tư. Hãy giao dịch có trách nhiệm.
            </p>
        </div>
    );
};

export default App;
