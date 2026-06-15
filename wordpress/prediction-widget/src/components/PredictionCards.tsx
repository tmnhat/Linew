import React from 'react';

interface Prediction {
    horizon: number;
    predicted_price?: number;
    predicted_low?: number;
    predicted_high?: number;
    change_pct?: number;
    confidence_score?: number;
}

interface PredictionCardsProps {
    predictions: Record<string, Prediction> | undefined;
    currencySymbol: string;
    formatPrice: (price: number | undefined) => string;
}

export const PredictionCards: React.FC<PredictionCardsProps> = ({
    predictions,
    formatPrice,
}) => {
    if (!predictions) {
        return null;
    }

    const horizons = ['1d', '7d', '30d'];

    const getConfidenceClass = (score?: number): string => {
        if (!score) return 'conf-low';
        if (score >= 0.8) return 'conf-high';
        if (score >= 0.5) return 'conf-medium';
        return 'conf-low';
    };

    return (
        <div className="linew-predictions-grid">
            {horizons.map((key) => {
                const pred = predictions[key];
                if (!pred) return null;

                const changeClass = (pred.change_pct ?? 0) > 0 ? 'positive' : 'negative';
                const changeSign = (pred.change_pct ?? 0) > 0 ? '+' : '';

                return (
                    <div key={key} className="linew-prediction-card">
                        <div className="linew-card-horizon">{key}</div>
                        <div className="linew-card-price">
                            {formatPrice(pred.predicted_price)}
                        </div>
                        <div className={`linew-card-change ${changeClass}`}>
                            {changeSign}{(pred.change_pct ?? 0).toFixed(2)}%
                        </div>
                        <div className="linew-card-range">
                            {formatPrice(pred.predicted_low)} - {formatPrice(pred.predicted_high)}
                        </div>
                        {pred.confidence_score && (
                            <div className="linew-card-confidence">
                                <div className="confidence-bar">
                                    <div
                                        className={`confidence-fill ${getConfidenceClass(pred.confidence_score)}`}
                                        style={{ width: `${(pred.confidence_score * 100).toFixed(0)}%` }}
                                    />
                                </div>
                                <span className="confidence-label">
                                    {(pred.confidence_score * 100).toFixed(0)}%
                                </span>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
};
