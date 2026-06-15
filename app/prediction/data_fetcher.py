"""
Data fetcher — hỗ trợ 3 markets:
  - crypto: yfinance + Binance (BTC-USD, ETH-USD, ...)
  - us: yfinance (AAPL, GOOGL, ...)
  - vn: vnstock (FPT, VNM, HPG, ...)
"""
import logging
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd
import yfinance as yf
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.prediction.binance_client import binance_client, get_binance_symbols, search_binance

logger = logging.getLogger(__name__)

FEAR_GREED_API = "https://api.alternative.me/fng/"

# Cache for symbol -> market mapping from DB
_market_cache = {}
_cache_loaded = False


async def _load_market_cache():
    """Load VN market symbols from database into cache."""
    global _market_cache, _cache_loaded
    if _cache_loaded:
        return
    
    try:
        from app.core.database import async_session_maker
        from sqlalchemy import select, func
        from app.models.tracked_symbols import TrackedSymbol
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(TrackedSymbol.symbol, TrackedSymbol.market)
                .where(TrackedSymbol.market == 'vn')
            )
            rows = result.all()
            for symbol, market in rows:
                _market_cache[symbol.upper()] = market
        
        _cache_loaded = True
        logger.info(f"Loaded {_len(_market_cache)} VN symbols into market cache")
    except Exception as e:
        logger.warning(f"Failed to load market cache: {e}")


def _len(d):
    """Safe len for dict."""
    return len(d) if d else 0


# Detect market from symbol
def detect_market(symbol: str) -> str:
    """
    Detect market from symbol pattern.
    Uses cached DB lookup for VN stocks.
    """
    symbol_upper = symbol.upper()
    
    # Binance symbols: end with USDT, BTC, ETH, BNB
    if symbol_upper.endswith(("USDT", "BTC", "ETH", "BNB")):
        return 'crypto'
    
    # Index symbols
    if symbol.startswith('^'):
        if 'VN' in symbol.upper():
            return 'vn'
        return 'us'
    
    # Crypto: has -USD, -BTC, etc suffix
    if '-' in symbol:
        return 'crypto'
    
    # Check cache first (synchronous fallback)
    if symbol_upper in _market_cache:
        return _market_cache[symbol_upper]
    
    # VN stocks: check against known VN symbols (hardcoded fallback)
    vn_patterns = [
        'FPT', 'VNM', 'HPG', 'TCB', 'MBB', 'CTG', 'BID', 'VIC', 'VHM', 'MSN',
        'SSI', 'GAS', 'PLX', 'STB', 'ACB', 'REE', 'MWG', 'PNJ', 'VRE', 'VND',
        'NAV', 'HDB', 'TPB', 'VPB', 'SHB', 'EIB', 'OCB', 'VPB', 'ABB', 'SSB',
        'PGB', 'BAB', 'KLB', 'LBP', 'SBT', 'VSC', 'DXG', 'KRG', 'HDG', 'IJC',
        'VGC', 'HAG', 'GVR', 'DHC', 'DRC', 'SZL', 'PET', 'ROS', 'DIG', 'TCD',
        'VCB', 'BCM', 'BVH', 'GDB', 'HDB', 'HSG', 'INA', 'KDH', 'NBL', 'NLG',
        'NT2', 'OGC', 'PVD', 'PVS', 'PVX', 'SCR', 'VCI', 'VCR', 'VDL', 'VNE',
        'VPH', 'VPI', 'VSH', 'VTB', 'AAA', 'ABR', 'ABT', 'ACC', 'ACL', 'ADC',
        'AGG', 'AGM', 'AMC', 'AME', 'AMP', 'ANT', 'ARM', 'ASG', 'ASM', 'ASP',
        'AST', 'BAB', 'BAC', 'BBC', 'BCE', 'BCG', 'BHC', 'BHN', 'BHS', 'BIC',
        'BKG', 'BMC', 'BMI', 'BMP', 'BRC', 'BSH', 'BSR', 'BST', 'BTG', 'BTP',
        'BTS', 'BTT', 'BUA', 'BVG', 'CAC', 'C22', 'C32', 'C47', 'CAN', 'CAP',
        'CAR', 'CCT', 'CDC', 'CEE', 'CHG', 'CHP', 'CIG', 'CII', 'CJC', 'CKC',
        'CLC', 'CLG', 'CLH', 'CLL', 'CLW', 'CMG', 'CMI', 'CMV', 'CMX', 'CNG',
    ]
    
    if symbol_upper in vn_patterns:
        _market_cache[symbol_upper] = 'vn'
        return 'vn'
    
    # Default to US stock (most common)
    return 'us'


async def detect_market_async(symbol: str) -> str:
    """
    Async version of detect_market with DB lookup.
    Use this when inside an async context with DB access.
    """
    await _load_market_cache()
    
    symbol_upper = symbol.upper()
    if symbol_upper in _market_cache:
        return _market_cache[symbol_upper]
    
    # Try DB lookup
    try:
        from app.core.database import async_session_maker
        from sqlalchemy import select
        from app.models.tracked_symbols import TrackedSymbol
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(TrackedSymbol.market)
                .where(func.lower(TrackedSymbol.symbol) == symbol.lower())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                _market_cache[symbol_upper] = row
                return row
    except Exception as e:
        logger.warning(f"DB lookup failed for {symbol}: {e}")
    
    # Fallback to synchronous detection
    return detect_market(symbol)


async def fetch_current_price(symbol: str, market: str = None) -> Optional[dict]:
    """
    Fetch current/recent price for a symbol.
    """
    if market is None:
        market = detect_market(symbol)
    
    try:
        if market == 'vn':
            return await fetch_vn_current_price(symbol)
        else:
            return await fetch_yfinance_current_price(symbol)
    except Exception as e:
        logger.warning(f"Failed to fetch current price for {symbol}: {e}")
        return None


async def fetch_vn_current_price(symbol: str) -> Optional[dict]:
    """Fetch current price for VN stock via vnstock (KBS source)."""
    try:
        from vnstock import Vnstock
        
        stock = Vnstock().stock(symbol=symbol, source='KBS')
        df = stock.quote.history(
            start=(date.today() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end=date.today().strftime('%Y-%m-%d'),
            interval='1D'
        )
        
        if df is None or len(df) == 0:
            return _fetch_vn_fallback(symbol)
        
        # Handle different column naming
        close_col = None
        for col in ['close', 'Close', 'close_price']:
            if col in df.columns:
                close_col = col
                break
        
        if close_col is None:
            return _fetch_vn_fallback(symbol)
        
        current_price = float(df[close_col].iloc[-1])
        prev_close = float(df[close_col].iloc[-2]) if len(df) > 1 else current_price
        
        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        return {
            "symbol": symbol,
            "price": current_price,
            "change": change,
            "change_pct": change_pct,
            "prev_close": prev_close,
            "currency": "VND",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.warning(f"vnstock fetch error for {symbol}: {e}")
        return _fetch_vn_fallback(symbol)


def _fetch_vn_fallback(symbol: str) -> Optional[dict]:
    """Fallback: use yfinance with VN index suffix."""
    try:
        # Try common VN ETF/Index proxies
        yf_symbol = f"{symbol}.V"  # Yahoo Finance Vietnam suffix
        
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="5d")
        
        if hist.empty:
            # Try without suffix
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
        
        if not hist.empty:
            price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else price
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0
            
            return {
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "prev_close": prev_close,
                "currency": "VND",
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        logger.warning(f"VN fallback fetch error for {symbol}: {e}")
    
    return None


async def fetch_yfinance_current_price(symbol: str) -> Optional[dict]:
    """Fetch current price via yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.last_price if hasattr(info, 'last_price') else None
        prev_close = info.previous_close if hasattr(info, 'previous_close') else None

        if price is None:
            hist = ticker.history(period="5d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                if len(hist) > 1:
                    prev_close = float(hist['Close'].iloc[-2])

        if price:
            change = 0
            change_pct = 0
            if prev_close and prev_close > 0:
                change = price - prev_close
                change_pct = (change / prev_close) * 100

            return {
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "prev_close": prev_close,
                "currency": "USD",
                "timestamp": datetime.utcnow().isoformat(),
            }
        return None
    except Exception as e:
        logger.warning(f"yfinance fetch current price error for {symbol}: {e}")
        return None


async def fetch_fear_greed() -> Optional[dict]:
    """Fetch current Fear & Greed index from Alternative.me API."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(FEAR_GREED_API)
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    item = data["data"][0]
                    return {
                        "value": int(item["value"]),
                        "value_classification": item["value_classification"],
                        "timestamp": int(item["timestamp"]),
                        "time_until_update": int(item.get("time_until_update", 0)),
                    }
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch Fear & Greed: {e}")
        return None


async def get_fear_greed_data(days: int = 30) -> list[dict]:
    """Fetch Fear & Greed history for the past N days."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"{FEAR_GREED_API}?limit={days}"
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("data", []):
                    results.append({
                        "date": datetime.fromtimestamp(int(item["timestamp"])).date().isoformat(),
                        "value": int(item["value"]),
                        "classification": item["value_classification"],
                    })
                return results
        return []
    except Exception as e:
        logger.warning(f"Failed to fetch Fear & Greed history: {e}")
        return []


async def fetch_history(
    session: AsyncSession,
    symbol: str,
    market: str = None,
    period: str = "2y",
) -> list[dict]:
    """
    Fetch historical price data for a symbol.
    Saves to price_history table.
    """
    if market is None:
        market = detect_market(symbol)
    
    try:
        logger.info(f"Fetching {symbol} history ({period}, market={market})")
        
        if market == 'vn':
            return await fetch_vn_history(session, symbol, period)
        else:
            return await fetch_yfinance_history(session, symbol, period)
            
    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")
        return []


async def fetch_vn_history(
    session: AsyncSession,
    symbol: str,
    period: str = "2y",
) -> list[dict]:
    """Fetch VN stock history via vnstock with fallback."""
    try:
        from vnstock import Vnstock
        
        # Calculate date range
        end_date = date.today().strftime('%Y-%m-%d')
        if period == "2y":
            start_date = (date.today() - timedelta(days=730)).strftime('%Y-%m-%d')
        elif period == "1y":
            start_date = (date.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        elif period == "6mo":
            start_date = (date.today() - timedelta(days=180)).strftime('%Y-%m-%d')
        elif period == "3mo":
            start_date = (date.today() - timedelta(days=90)).strftime('%Y-%m-%d')
        else:
            start_date = (date.today() - timedelta(days=730)).strftime('%Y-%m-%d')
        
        stock = Vnstock().stock(symbol=symbol, source='KBS')
        df = stock.quote.history(start=start_date, end=end_date, interval='1D')
        
        if df is None or df.empty:
            return await _fetch_vn_history_fallback(session, symbol, period)
        
        # vnstock returns DataFrame with 'time' column and 'close', 'open', 'high', 'low', 'volume' columns
        if 'time' not in df.columns:
            return await _fetch_vn_history_fallback(session, symbol, period)
        
        from app.models.price_history import PriceHistory
        from sqlalchemy.dialects.postgresql import insert

        records = []
        for idx, row in df.iterrows():
            try:
                # Get date from 'time' column
                time_val = row.get('time')
                if pd.isna(time_val):
                    continue
                
                # Convert to date
                if hasattr(time_val, 'date'):
                    record_date = time_val.date()
                elif isinstance(time_val, str):
                    record_date = date.fromisoformat(time_val[:10])
                else:
                    continue
                
                # Get OHLCV values
                open_val = float(row.get('open', 0)) if not pd.isna(row.get('open')) else 0
                high_val = float(row.get('high', open_val)) if not pd.isna(row.get('high')) else open_val
                low_val = float(row.get('low', open_val)) if not pd.isna(row.get('low')) else open_val
                close_val = float(row.get('close', open_val)) if not pd.isna(row.get('close')) else open_val
                volume_val = int(row.get('volume', 0)) if not pd.isna(row.get('volume')) else None
                
                stmt = insert(PriceHistory).values(
                    symbol=symbol,
                    date=record_date,
                    open=Decimal(str(open_val)),
                    high=Decimal(str(high_val)),
                    low=Decimal(str(low_val)),
                    close=Decimal(str(close_val)),
                    volume=volume_val,
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

                records.append({
                    "date": record_date.isoformat(),
                    "close": close_val,
                })
            except Exception as e:
                logger.warning(f"Failed to save record for {symbol}: {e}")
                continue

        await session.commit()
        logger.info(f"Saved {len(records)} records for {symbol}")
        return records
        
    except Exception as e:
        logger.error(f"vnstock fetch error for {symbol}: {e}")
        return await _fetch_vn_history_fallback(session, symbol, period)


async def _fetch_vn_history_fallback(
    session: AsyncSession,
    symbol: str,
    period: str = "2y",
) -> list[dict]:
    """Fallback: use yfinance for VN stock via proxy."""
    try:
        # Map to yfinance symbol or use proxy
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return []

        records = []
        for idx, row in df.iterrows():
            try:
                # Handle different index types
                if hasattr(idx, 'date'):
                    record_date = idx.date()
                elif isinstance(idx, str):
                    record_date = date.fromisoformat(idx)
                elif isinstance(idx, (int, float)):
                    from datetime import datetime as dt
                    record_date = dt.fromtimestamp(idx).date()
                else:
                    record_date = idx.date() if hasattr(idx, 'date') else idx

                from app.models.price_history import PriceHistory
                from sqlalchemy.dialects.postgresql import insert

                open_val = float(row['Open']) if pd.notna(row['Open']) else 0
                high_val = float(row['High']) if pd.notna(row['High']) else open_val
                low_val = float(row['Low']) if pd.notna(row['Low']) else open_val
                close_val = float(row['Close']) if pd.notna(row['Close']) else open_val
                volume_val = int(row['Volume']) if pd.notna(row['Volume']) else None

                stmt = insert(PriceHistory).values(
                    symbol=symbol,
                    date=record_date,
                    open=Decimal(str(open_val)),
                    high=Decimal(str(high_val)),
                    low=Decimal(str(low_val)),
                    close=Decimal(str(close_val)),
                    volume=volume_val,
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

                records.append({
                    "date": record_date.isoformat(),
                    "close": float(row['Close']) if pd.notna(row['Close']) else None,
                })
            except Exception as e:
                logger.warning(f"Failed to save fallback record for {symbol}: {e}")
                continue

        await session.commit()
        logger.info(f"Saved {len(records)} fallback records for {symbol}")
        return records

    except Exception as e:
        logger.error(f"VN fallback history fetch error for {symbol}: {e}")
        return []


async def fetch_yfinance_history(
    session: AsyncSession,
    symbol: str,
    period: str = "2y",
) -> list[dict]:
    """Fetch history via yfinance."""
    try:
        logger.info(f"Fetching {symbol} history via yfinance ({period})")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return []

        records = []
        for idx, row in df.iterrows():
            try:
                # Handle different index types
                if hasattr(idx, 'date'):
                    record_date = idx.date()
                elif isinstance(idx, str):
                    record_date = date.fromisoformat(idx)
                elif isinstance(idx, (int, float)):
                    from datetime import datetime as dt
                    record_date = dt.fromtimestamp(idx).date()
                else:
                    record_date = idx.date() if hasattr(idx, 'date') else idx

                from app.models.price_history import PriceHistory
                from sqlalchemy.dialects.postgresql import insert

                open_val = float(row['Open']) if pd.notna(row['Open']) else 0
                high_val = float(row['High']) if pd.notna(row['High']) else open_val
                low_val = float(row['Low']) if pd.notna(row['Low']) else open_val
                close_val = float(row['Close']) if pd.notna(row['Close']) else open_val
                volume_val = int(row['Volume']) if pd.notna(row['Volume']) else None

                stmt = insert(PriceHistory).values(
                    symbol=symbol,
                    date=record_date,
                    open=Decimal(str(open_val)),
                    high=Decimal(str(high_val)),
                    low=Decimal(str(low_val)),
                    close=Decimal(str(close_val)),
                    volume=volume_val,
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

                records.append({
                    "date": record_date.isoformat(),
                    "close": float(row['Close']) if pd.notna(row['Close']) else None,
                })

            except Exception as e:
                logger.warning(f"Failed to save record for {symbol}: {e}")
                continue

        await session.commit()
        logger.info(f"Saved {len(records)} records for {symbol}")
        return records

    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")
        return []


async def get_latest_price(session: AsyncSession, symbol: str) -> dict:
    """Get the latest price for a symbol."""
    from sqlalchemy import select, desc
    from app.models.price_history import PriceHistory

    result = await session.execute(
        select(PriceHistory)
        .where(PriceHistory.symbol == symbol)
        .order_by(desc(PriceHistory.date))
        .limit(1)
    )
    price_record = result.scalar_one_or_none()

    if price_record:
        return price_record.to_dict()
    return {}


async def get_price_history(
    session: AsyncSession,
    symbol: str,
    days: int = 365,
) -> list[dict]:
    """Get price history for a symbol."""
    from sqlalchemy import select, desc
    from app.models.price_history import PriceHistory

    cutoff = datetime.utcnow().date() - timedelta(days=days)

    result = await session.execute(
        select(PriceHistory)
        .where(
            PriceHistory.symbol == symbol,
            PriceHistory.date >= cutoff,
        )
        .order_by(PriceHistory.date)
    )
    records = result.scalars().all()
    return [r.to_dict() for r in records]


# ============================================
# BINANCE METHODS (NEW)
# ============================================

async def fetch_binance_price(symbol: str) -> Optional[dict]:
    """
    Fetch current price from Binance API.
    
    Args:
        symbol: Binance symbol (e.g., "BTCUSDT", "ETHUSDT")
        
    Returns:
        Dict với price, change, change_pct, volume, etc.
    """
    try:
        # Normalize symbol (ensure USDT suffix)
        normalized = symbol.upper()
        if not normalized.endswith(("USDT", "BTC", "ETH", "BNB")):
            normalized = normalized + "USDT"
        
        ticker = await binance_client.get_24hr_ticker(normalized)
        
        if ticker:
            return {
                "symbol": ticker["symbol"],
                "price": ticker["last_price"],
                "change": ticker["price_change"],
                "change_pct": ticker["price_change_pct"],
                "high": ticker["high_price"],
                "low": ticker["low_price"],
                "volume": ticker["volume"],
                "quote_volume": ticker["quote_volume"],
                "currency": "USDT",
                "source": "binance",
                "timestamp": datetime.utcnow().isoformat(),
            }
        return None
        
    except Exception as e:
        logger.warning(f"Failed to fetch Binance price for {symbol}: {e}")
        return None


async def fetch_binance_history(
    session: AsyncSession,
    symbol: str,
    interval: str = "1d",
    limit: int = 365,
) -> list[dict]:
    """
    Fetch historical price data from Binance.
    
    Args:
        session: Database session
        symbol: Binance symbol (e.g., "BTCUSDT")
        interval: Time interval (1m, 5m, 15m, 1h, 4h, 1d, 1w)
        limit: Số lượng candles
        
    Returns:
        List of price records
    """
    try:
        # Normalize symbol
        normalized = symbol.upper()
        if not normalized.endswith(("USDT", "BTC", "ETH", "BNB")):
            normalized = normalized + "USDT"
        
        candles = await binance_client.get_klines(
            normalized, 
            interval=interval, 
            limit=min(limit, 1000)
        )
        
        if not candles:
            return []
        
        from app.models.price_history import PriceHistory
        from sqlalchemy.dialects.postgresql import insert
        
        records = []
        for candle in candles:
            try:
                record_date = candle["open_time"].date()
                
                stmt = insert(PriceHistory).values(
                    symbol=normalized,
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
                
                records.append({
                    "date": record_date.isoformat(),
                    "close": candle["close"],
                })
                
            except Exception as e:
                logger.warning(f"Failed to save Binance candle for {normalized}: {e}")
                continue
        
        await session.commit()
        logger.info(f"Saved {len(records)} Binance records for {normalized}")
        return records
        
    except Exception as e:
        logger.error(f"Failed to fetch Binance history for {symbol}: {e}")
        return []


async def search_binance_symbols(query: str, limit: int = 20) -> list[dict]:
    """
    Search Binance symbols by query.
    
    Args:
        query: Search query (e.g., "BTC", "ETH", "SOL")
        limit: Maximum results
        
    Returns:
        List of matching symbols
    """
    return await search_binance(query, limit)


async def get_all_binance_symbols(quote: str = "USDT") -> list[str]:
    """
    Get all Binance trading symbols for a quote currency.
    
    Args:
        quote: Quote currency (USDT, BTC, ETH, BNB)
        
    Returns:
        List of symbol names
    """
    try:
        symbols = await binance_client.get_exchange_info()
        return [s["symbol"] for s in symbols if s.get("quoteAsset") == quote]
    except Exception as e:
        logger.warning(f"Failed to get Binance symbols: {e}")
        return []
