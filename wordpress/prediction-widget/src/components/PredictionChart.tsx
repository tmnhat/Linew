import React, { useRef, useMemo } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

interface PredictionChartProps {
    data: {
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
        predictions?: Record<string, {
            predicted_price?: number;
            predicted_low?: number;
            predicted_high?: number;
        }>;
        current_price?: number;
    };
    currencySymbol: string;
}

export const PredictionChart: React.FC<PredictionChartProps> = React.memo(({ data, currencySymbol }) => {
    const chartRef = useRef<any>(null);

    const chartData = useMemo(() => {
        const labels: string[] = [];
        const actualPrices: (number | null)[] = [];
        const predictionPrices: (number | null)[] = [];
        const upperBand: (number | null)[] = [];
        const lowerBand: (number | null)[] = [];

        if (data.chart_data?.points) {
            data.chart_data.points.forEach((point) => {
                labels.push(point.date);
                actualPrices.push(point.actual ?? null);
            });
        }

        if (data.current_price && labels.length > 0) {
            predictionPrices[labels.length - 1] = data.current_price;
        }

        const pred30d = data.predictions?.['30d'];
        if (pred30d?.predicted_price) {
            labels.push('+30d');
            actualPrices.push(null);
            predictionPrices.push(pred30d.predicted_price);
            upperBand.push(pred30d.predicted_high ?? null);
            lowerBand.push(pred30d.predicted_low ?? null);
        }

        return {
            labels,
            datasets: [
                {
                    label: 'Giá thực',
                    data: actualPrices,
                    borderColor: '#4ade80',
                    backgroundColor: 'rgba(74, 222, 128, 0.1)',
                    fill: false,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                },
                {
                    label: 'Dự đoán',
                    data: predictionPrices,
                    borderColor: '#60a5fa',
                    backgroundColor: 'rgba(96, 165, 250, 0.1)',
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                },
                {
                    label: 'Khoảng dự đoán',
                    data: upperBand,
                    borderColor: 'transparent',
                    backgroundColor: 'rgba(96, 165, 250, 0.15)',
                    fill: '+1',
                    pointRadius: 0,
                },
                {
                    label: 'Khoảng dự đoán (dưới)',
                    data: lowerBand,
                    borderColor: 'transparent',
                    backgroundColor: 'transparent',
                    pointRadius: 0,
                },
            ],
        };
    }, [data.chart_data, data.predictions, data.current_price]);

    const options: ChartOptions<'line'> = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        parsing: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                backgroundColor: 'rgba(26, 26, 46, 0.9)',
                titleColor: '#fff',
                bodyColor: '#fff',
                borderColor: 'rgba(255, 255, 255, 0.2)',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: (context) => {
                        if (context.raw === null || context.raw === undefined) return '';
                        return `${context.dataset.label}: ${currencySymbol}${context.raw.toLocaleString()}`;
                    },
                },
            },
        },
        scales: {
            x: {
                display: true,
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                },
                ticks: {
                    color: 'rgba(255, 255, 255, 0.7)',
                    maxTicksLimit: 8,
                },
            },
            y: {
                display: true,
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                },
                ticks: {
                    color: 'rgba(255, 255, 255, 0.7)',
                    callback: (value) => `${currencySymbol}${(value as number).toLocaleString()}`,
                },
            },
        },
    };

    return (
        <div className="linew-chart-container" style={{ height: '280px', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}>
                <Line ref={chartRef} data={chartData} options={options} style={{ width: '100%', height: '100%' }} />
            </div>
        </div>
    );
});
