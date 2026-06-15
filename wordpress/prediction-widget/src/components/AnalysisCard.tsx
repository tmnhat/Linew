import React, { useState } from 'react';

interface Analysis {
    sentiment?: string;
    sentiment_score?: number;
    analysis_vi?: string;
    why_moving?: string[];
    risks?: string[];
    opportunities?: string[];
    key_factors?: string[];
    fear_greed_index?: number;
    fear_greed_value?: string;
}

interface AnalysisCardProps {
    analysis: Analysis;
}

export const AnalysisCard: React.FC<AnalysisCardProps> = ({ analysis }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const getSentimentIcon = (sentiment?: string): string => {
        const icons: Record<string, string> = {
            bullish: '📈',
            bearish: '📉',
            neutral: '➡️',
        };
        return icons[sentiment?.toLowerCase() || 'neutral'] || '➡️';
    };

    const getSentimentClass = (sentiment?: string): string => {
        const classes: Record<string, string> = {
            bullish: 'sentiment-bullish',
            bearish: 'sentiment-bearish',
            neutral: 'sentiment-neutral',
        };
        return classes[sentiment?.toLowerCase() || 'neutral'] || 'sentiment-neutral';
    };

    const truncateText = (text?: string, maxLength: number = 300): string => {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    };

    return (
        <div className="linew-analysis-card">
            <div className="linew-analysis-header">
                <span className="linew-sentiment-icon">
                    {getSentimentIcon(analysis.sentiment)}
                </span>
                <span className={`linew-sentiment ${getSentimentClass(analysis.sentiment)}`}>
                    {analysis.sentiment || 'neutral'}
                </span>
                {analysis.sentiment_score && (
                    <span className="linew-sentiment-score">
                        {(analysis.sentiment_score * 100).toFixed(0)}%
                    </span>
                )}
            </div>

            {analysis.fear_greed_index && (
                <div className="linew-fear-greed-inline">
                    Fear & Greed: {analysis.fear_greed_index} ({analysis.fear_greed_value})
                </div>
            )}

            {analysis.analysis_vi && (
                <div className="linew-analysis-content">
                    <p className={`linew-analysis-text ${isExpanded ? 'expanded' : ''}`}>
                        {isExpanded ? analysis.analysis_vi : truncateText(analysis.analysis_vi)}
                    </p>
                    {analysis.analysis_vi.length > 300 && (
                        <button
                            className="linew-expand-btn"
                            onClick={() => setIsExpanded(!isExpanded)}
                        >
                            {isExpanded ? 'Thu gọn' : 'Xem thêm'}
                        </button>
                    )}
                </div>
            )}

            {analysis.key_factors && analysis.key_factors.length > 0 && (
                <div className="linew-section linew-factors">
                    <span className="section-title">Yếu tố chính:</span>
                    <ul className="section-list">
                        {analysis.key_factors.slice(0, 5).map((factor, i) => (
                            <li key={i}>{factor}</li>
                        ))}
                    </ul>
                </div>
            )}

            {analysis.why_moving && analysis.why_moving.length > 0 && (
                <div className="linew-section">
                    <span className="section-title">Tại sao biến động:</span>
                    <ul className="section-list">
                        {analysis.why_moving.map((item, i) => (
                            <li key={i}>{item}</li>
                        ))}
                    </ul>
                </div>
            )}

            {analysis.risks && analysis.risks.length > 0 && (
                <div className="linew-section linew-risks">
                    <span className="section-title">Rủi ro:</span>
                    <ul className="section-list">
                        {analysis.risks.map((risk, i) => (
                            <li key={i}>{risk}</li>
                        ))}
                    </ul>
                </div>
            )}

            {analysis.opportunities && analysis.opportunities.length > 0 && (
                <div className="linew-section linew-opportunities">
                    <span className="section-title">Cơ hội:</span>
                    <ul className="section-list">
                        {analysis.opportunities.map((opp, i) => (
                            <li key={i}>{opp}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};
