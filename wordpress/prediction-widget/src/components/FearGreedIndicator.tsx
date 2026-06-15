import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface FearGreedData {
    value: number;
    value_classification: string;
}

interface FearGreedIndicatorProps {
    apiUrl: string;
}

export const FearGreedIndicator: React.FC<FearGreedIndicatorProps> = ({ apiUrl }) => {
    const [data, setData] = useState<FearGreedData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchFearGreed = async () => {
            try {
                const response = await axios.get<FearGreedData>(`${apiUrl}/fear-greed`);
                setData(response.data);
            } catch (err) {
                console.error('Failed to fetch Fear & Greed:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchFearGreed();
    }, [apiUrl]);

    const getFearGreedClass = (value?: number): string => {
        if (!value) return '';
        if (value <= 25) return 'fg-extreme-fear';
        if (value <= 45) return 'fg-fear';
        if (value <= 55) return 'fg-neutral';
        if (value <= 75) return 'fg-greed';
        return 'fg-extreme-greed';
    };

    if (loading) {
        return (
            <div className="linew-fear-greed" id="linew-fear-greed">
                <span className="linew-fg-label">Fear & Greed:</span>
                <span className="linew-fg-value">Đang tải...</span>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="linew-fear-greed" id="linew-fear-greed">
                <span className="linew-fg-label">Fear & Greed:</span>
                <span className="linew-fg-value">N/A</span>
            </div>
        );
    }

    return (
        <div className="linew-fear-greed" id="linew-fear-greed">
            <span className="linew-fg-label">Fear & Greed:</span>
            <span className={`linew-fg-value ${getFearGreedClass(data.value)}`}>
                {data.value} - {data.value_classification}
            </span>
        </div>
    );
};
