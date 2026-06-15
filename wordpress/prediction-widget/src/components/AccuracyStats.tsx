import React from 'react';

interface AccuracyStats {
    avg_error_pct?: number;
    direction_accuracy?: number;
    within_bounds_pct?: number;
}

interface AccuracyStatsProps {
    accuracy: AccuracyStats;
}

export const AccuracyStats: React.FC<AccuracyStatsProps> = ({ accuracy }) => {
    if (!accuracy) return null;

    return (
        <div className="linew-accuracy-card">
            <div className="linew-accuracy-title">Độ chính xác (30 ngày)</div>
            <div className="linew-accuracy-stats">
                {accuracy.avg_error_pct !== undefined && (
                    <div className="stat-item">
                        <span className="stat-label">Sai số TB:</span>
                        <span className="stat-value">{accuracy.avg_error_pct.toFixed(2)}%</span>
                    </div>
                )}
                {accuracy.direction_accuracy !== undefined && (
                    <div className="stat-item">
                        <span className="stat-label">Hướng đúng:</span>
                        <span className="stat-value">{accuracy.direction_accuracy}%</span>
                    </div>
                )}
                {accuracy.within_bounds_pct !== undefined && (
                    <div className="stat-item">
                        <span className="stat-label">Trong khoảng:</span>
                        <span className="stat-value">{accuracy.within_bounds_pct}%</span>
                    </div>
                )}
            </div>
        </div>
    );
};
