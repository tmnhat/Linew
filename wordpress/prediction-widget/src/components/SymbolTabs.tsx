import React from 'react';

interface SymbolInfo {
    symbol: string;
    name: string;
    type: string;
}

interface SymbolTabsProps {
    symbols: SymbolInfo[];
    selectedSymbol: string;
    onSymbolChange: (symbol: string) => void;
}

export const SymbolTabs: React.FC<SymbolTabsProps> = ({
    symbols,
    selectedSymbol,
    onSymbolChange,
}) => {
    return (
        <div className="linew-prediction-tabs">
            {symbols.map((info) => (
                <button
                    key={info.symbol}
                    className={`linew-tab ${selectedSymbol === info.symbol ? 'active' : ''}`}
                    onClick={() => onSymbolChange(info.symbol)}
                    data-symbol={info.symbol}
                    data-type={info.type}
                >
                    {info.name}
                </button>
            ))}
        </div>
    );
};
