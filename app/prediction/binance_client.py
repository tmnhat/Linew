"""
Binance API client cho crypto data.
Hỗ trợ lấy danh sách symbols, OHLCV data, và ticker information.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from concurrent.futures import ThreadPoolExecutor

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

# Cache cho symbols list
_symbols_cache: Optional[list[dict]] = None
_symbols_cache_time: Optional[datetime] = None
SYMBOLS_CACHE_TTL = 3600  # 1 hour


class BinanceClient:
    """
    Binance API client - sử dụng public endpoints (không cần API key).
    """
    
    BASE_URL = "https://api.binance.com"
    BASE_URL_API = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def _run_sync(self, func, *args, **kwargs):
        """Run synchronous function in thread pool for async context."""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
    
    async def get_exchange_info(self) -> list[dict]:
        """
        Lấy thông tin tất cả trading pairs đang active.
        Filter để lấy các cặp USDT.
        """
        global _symbols_cache, _symbols_cache_time
        
        # Check cache
        now = datetime.utcnow()
        if _symbols_cache and _symbols_cache_time:
            age = (now - _symbols_cache_time).total_seconds()
            if age < SYMBOLS_CACHE_TTL:
                return _symbols_cache
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.BASE_URL_API}/exchangeInfo")
                
                if response.status_code == 200:
                    data = response.json()
                    symbols = [
                        {
                            "symbol": s["symbol"],
                            "baseAsset": s["baseAsset"],
                            "quoteAsset": s["quoteAsset"],
                            "status": s["status"],
                            "minQty": s.get("filters", [{}])[0].get("minQty", "0"),
                            "stepSize": s.get("filters", [{}])[0].get("stepSize", "0"),
                        }
                        for s in data.get("symbols", [])
                        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
                    ]
                    
                    # Update cache
                    _symbols_cache = symbols
                    _symbols_cache_time = now
                    
                    logger.info(f"Cached {len(symbols)} Binance USDT symbols")
                    return symbols
                else:
                    logger.warning(f"Binance exchange info API error: {response.status_code}")
                    return _symbols_cache or []
                    
        except Exception as e:
            logger.error(f"Failed to fetch Binance exchange info: {e}")
            return _symbols_cache or []
    
    async def get_all_usdt_symbols(self) -> list[str]:
        """Lấy danh sách tất cả symbol names (USDT pairs)."""
        symbols = await self.get_exchange_info()
        return [s["symbol"] for s in symbols]
    
    async def search_symbols(self, query: str, limit: int = 20) -> list[dict]:
        """
        Tìm kiếm symbols theo query string.
        
        Args:
            query: Từ khóa tìm kiếm (VD: "BTC", "ETH", "SOL")
            limit: Số lượng kết quả tối đa
            
        Returns:
            List of matching symbols với thông tin chi tiết
        """
        symbols = await self.get_exchange_info()
        query_upper = query.upper()
        
        # Filter symbols containing the query
        matches = [
            s for s in symbols
            if query_upper in s["symbol"] or query_upper in s["baseAsset"]
        ]
        
        # Sort: exact match first, then by symbol name
        def sort_key(s):
            if s["symbol"] == query_upper:
                return (0, s["symbol"])
            elif s["baseAsset"] == query_upper:
                return (1, s["symbol"])
            else:
                return (2, s["symbol"])
        
        matches.sort(key=sort_key)
        return matches[:limit]
    
    async def get_klines(
        self,
        symbol: str,
        interval: Literal["1m", "5m", "15m", "1h", "4h", "1d", "1w"] = "1d",
        limit: int = 365,
        start_str: Optional[str] = None,
        end_str: Optional[str] = None,
    ) -> list[dict]:
        """
        Lấy OHLCV candlestick data.
        
        Args:
            symbol: Trading symbol (VD: "BTCUSDT")
            interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d, 1w)
            limit: Số lượng candles (max 1000)
            start_str: Start time (ISO format)
            end_str: End time (ISO format)
            
        Returns:
            List of candles với format: [open_time, open, high, low, close, volume, close_time, ...]
        """
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 1000),
            }
            
            if start_str:
                params["startTime"] = start_str
            if end_str:
                params["endTime"] = end_str
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.BASE_URL_API}/klines", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    candles = []
                    for candle in data:
                        candles.append({
                            "open_time": datetime.fromtimestamp(candle[0] / 1000),
                            "open": float(candle[1]),
                            "high": float(candle[2]),
                            "low": float(candle[3]),
                            "close": float(candle[4]),
                            "volume": float(candle[5]),
                            "close_time": datetime.fromtimestamp(candle[6] / 1000),
                            "quote_volume": float(candle[7]),
                            "trades": int(candle[8]),
                            "taker_buy_volume": float(candle[9]),
                        })
                    
                    return candles
                else:
                    logger.warning(f"Binance klines API error for {symbol}: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to fetch klines for {symbol}: {e}")
            return []
    
    async def get_24hr_ticker(self, symbol: str) -> Optional[dict]:
        """
        Lấy 24hr ticker statistics.
        
        Returns:
            Dict với: symbol, priceChange, priceChangePercent, lastPrice, volume, ...
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL_API}/ticker/24hr",
                    params={"symbol": symbol}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "symbol": data["symbol"],
                        "price_change": float(data["priceChange"]),
                        "price_change_pct": float(data["priceChangePercent"]),
                        "last_price": float(data["lastPrice"]),
                        "high_price": float(data["highPrice"]),
                        "low_price": float(data["lowPrice"]),
                        "volume": float(data["volume"]),
                        "quote_volume": float(data["quoteVolume"]),
                        "price_change_usd": float(data["priceChange"]) if data.get("priceChange") else 0,
                    }
                else:
                    logger.warning(f"Binance ticker API error for {symbol}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            return None
    
    async def get_price(self, symbol: str) -> Optional[float]:
        """Lấy current price cho một symbol."""
        ticker = await self.get_24hr_ticker(symbol)
        return ticker["last_price"] if ticker else None
    
    async def get_prices(self, symbols: Optional[list[str]] = None) -> dict[str, float]:
        """
        Lấy prices cho nhiều symbols.
        
        Args:
            symbols: List of symbols. Nếu None, lấy tất cả USDT pairs.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if symbols:
                    params = {"symbols": f'["{"","".join(symbols)}"]'}
                    response = await client.get(
                        f"{self.BASE_URL_API}/ticker/price",
                        params=params
                    )
                else:
                    response = await client.get(f"{self.BASE_URL_API}/ticker/price")
                
                if response.status_code == 200:
                    data = response.json()
                    return {item["symbol"]: float(item["price"]) for item in data}
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"Failed to fetch prices: {e}")
            return {}
    
    async def get_order_book_ticker(self, symbol: str) -> Optional[dict]:
        """Lấy order book ticker (best bid/ask)."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL_API}/ticker/bookTicker",
                    params={"symbol": symbol}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "symbol": data["symbol"],
                        "bid_price": float(data["bidPrice"]),
                        "ask_price": float(data["askPrice"]),
                        "bid_qty": float(data["bidQty"]),
                        "ask_qty": float(data["askQty"]),
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch order book ticker for {symbol}: {e}")
            return None
    
    async def save_to_database(
        self,
        session: AsyncSession,
        symbol: str,
        interval: str = "1d",
        limit: int = 365,
    ) -> int:
        """
        Lấy klines và lưu vào price_history table.
        
        Args:
            session: Database session
            symbol: Trading symbol
            interval: Time interval
            limit: Số lượng candles
            
        Returns:
            Số lượng records đã lưu
        """
        candles = await self.get_klines(symbol, interval=interval, limit=limit)
        
        if not candles:
            return 0
        
        saved_count = 0
        
        for candle in candles:
            try:
                record_date = candle["open_time"].date()
                
                stmt = insert(PriceHistory).values(
                    symbol=symbol,
                    date=record_date,
                    open=Decimal(str(candle["open"])),
                    high=Decimal(str(candle["high"])),
                    low=Decimal(str(candle["low"])),
                    close=Decimal(str(candle["close"])),
                    volume=int(candle["volume"]) if candle["volume"] else None,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "date"],
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                    }
                )
                await session.execute(stmt)
                saved_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to save candle for {symbol}: {e}")
                continue
        
        await session.commit()
        logger.info(f"Saved {saved_count} candles for {symbol}")
        return saved_count


# Singleton instance
binance_client = BinanceClient()


async def get_binance_symbols() -> list[str]:
    """Helper function để lấy danh sách Binance USDT symbols."""
    return await binance_client.get_all_usdt_symbols()


async def search_binance(query: str, limit: int = 20) -> list[dict]:
    """Helper function để tìm kiếm Binance symbols."""
    return await binance_client.search_symbols(query, limit)
